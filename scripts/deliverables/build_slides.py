"""Build the editable 15-slide Vietnamese STING–PAPI defense deck.

Python reads the committed evidence and recomputes the shared-sample comparison.
The companion ES module authors native PowerPoint tables/charts with
``@oai/artifact-tool``. It never trains a new forecasting model or modifies results.
The artifact engine also embeds Excel chart workbooks and verifies that every
cached point matches its referenced cell before publishing the output file.

Usage (from the repository root)::
    python scripts/deliverables/build_slides.py
    python scripts/deliverables/build_slides.py --data-only evidence.json
    python scripts/deliverables/build_slides.py --engine artifact --render-dir preview

The default portable engine exports the reviewed snapshot only when its evidence
and authoring source still match. The optional artifact engine needs Node and a
runtime that provides @oai/artifact-tool. Managed runtimes
can provide CODEX_PRIMARY_RUNTIME_NODE and CODEX_PRIMARY_RUNTIME_NODE_MODULES.
Outside that runtime, use ARTIFACT_NODE / ARTIFACT_NODE_MODULES when a licensed
runtime already supplies the package. Use --render-dir for optional slide previews.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal
from sklearn.cluster import DBSCAN, KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sting import STING  # noqa: E402

OUT = ROOT / "slides" / "Nhom15_STING_PAPI.pptx"
SLIDE_COUNT = 15


def _records(frame: pd.DataFrame) -> list[dict]:
    """Return strict JSON-compatible values, including missing numeric cells."""
    return json.loads(frame.to_json(orient="records", force_ascii=False, double_precision=15))


def build_evidence() -> dict:
    config = json.loads((ROOT / "models/predict_config.json").read_text(encoding="utf-8"))
    panel = pd.read_csv(ROOT / "data/processed/papi_panel_v1_LOCKED.csv")
    features = config["features"]
    pars = config["sting"]
    ref = panel.loc[panel.year.le(2023)].dropna(subset=features).copy()
    scaler = StandardScaler().fit(ref[features])
    z = scaler.transform(ref[features])
    grid = STING(n_levels=pars["n_levels"], factor=pars["factor"], min_count=pars["min_count"]).fit(z)
    labels = grid.cluster(level=pars["cluster_level"], connectivity=pars["connectivity"])
    km = KMeans(n_clusters=2, n_init=10, random_state=42).fit_predict(z)
    db = DBSCAN(eps=0.2, min_samples=5).fit_predict(z)
    common = (labels >= 0) & (db >= 0)
    comparison = [
        {"method": name, "clusters": len(set(lab[lab >= 0])),
         "noise_pct": float(100 * np.mean(lab == -1)),
         "silhouette": float(silhouette_score(z[common], lab[common]))}
        for name, lab in [("STING", labels), ("K-means (k = 2)", km), ("DBSCAN (ε = 0,2)", db)]
    ]
    recorded = pd.read_csv(ROOT / "results/predict_all_years.csv")
    joined = ref.assign(rebuilt=labels).merge(
        recorded.loc[recorded.year.le(2023), ["province_code", "year", "pred_cluster"]],
        on=["province_code", "year"], validate="one_to_one")
    if len(joined) != len(ref) or not np.array_equal(joined.rebuilt, joined.pred_cluster):
        raise ValueError("Rebuilt reference labels differ from the committed evidence")
    all_raw = panel[features].dropna().to_numpy()
    all_z = StandardScaler().fit_transform(all_raw)
    raw_grid = STING(n_levels=pars["n_levels"], factor=pars["factor"], min_count=pars["min_count"]).fit(all_raw)
    scaled_grid = STING(n_levels=pars["n_levels"], factor=pars["factor"], min_count=pars["min_count"]).fit(all_z)
    raw_labels = raw_grid.cluster(level=pars["cluster_level"], connectivity=pars["connectivity"])
    scaled_labels = scaled_grid.cluster(level=pars["cluster_level"], connectivity=pars["connectivity"])
    same_cells = int(np.all(raw_grid.point_cell_index(pars["cluster_level"]) == scaled_grid.point_cell_index(pars["cluster_level"]), axis=1).sum())
    syn_x, syn_true = make_blobs(n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    syn_grid = STING(n_levels=3, factor=4, min_count=3).fit(syn_x)
    syn_labels = syn_grid.cluster(level=2, connectivity=1)
    if any(sum(c.count for c in cells.values()) != len(syn_x) for cells in syn_grid.cells_.values()):
        raise ValueError("Synthetic count conservation failed")
    observed = pd.read_csv(ROOT / "results/papi_observed_grid_2024.csv")
    stake = pd.read_csv(ROOT / "results/stakeholder_province_summary_2024.csv")
    core = stake.loc[stake.cluster.eq(2)]
    q1, q3 = core.sd_6_1.quantile([0.25, 0.75])
    lower = float(q1 - 0.5 * (q3 - q1))
    # Use numeric labels and values rather than wording as the grouping contract.
    masks = [stake.cluster.eq(2), stake.cluster.eq(-1) & stake.sd_6_1.ge(lower),
             stake.cluster.eq(-1) & stake.sd_6_1.lt(lower), stake.cluster.isna()]
    groups = []
    for key, mask in zip(["core", "high_side", "low_61", "missing"], masks, strict=True):
        frame = stake.loc[mask]
        groups.append({"key": key, "n": len(frame), "share": len(frame) / len(stake),
                       "median_42": float(frame.sd_4_2.median()) if frame.sd_4_2.notna().any() else None,
                       "median_61": float(frame.sd_6_1.median()) if frame.sd_6_1.notna().any() else None,
                       "median_grdp": float(frame.grdp_2024_mil_vnd.median()),
                       "names": frame.province_vi.tolist()})
    prev = recorded.loc[recorded.year.eq(2023)].set_index("province_code")
    curr = recorded.loc[recorded.year.eq(2024)].set_index("province_code")
    codes = prev.index.intersection(curr.index)
    transitions = [[int(((prev.loc[codes].pred_cluster == a) & (curr.loc[codes].pred_cluster == b)).sum())
                    for b in [2, -1]] for a in [2, -1]]
    trace = []
    for year in [2023, 2024]:
        row = panel.loc[panel.year.eq(year) & panel.province_vi.eq("Lạng Sơn")].iloc[0]
        point = scaler.transform(pd.DataFrame([row[features]], columns=features))
        cell = tuple(int(v) for v in grid._assign(point, pars["factor"] ** pars["cluster_level"])[0][0])
        count = grid.cells_[pars["cluster_level"]].get(cell)
        label = int(grid.predict(point)[0])
        trace.append({"year": year, "x": float(row.sd_4_2), "y": float(row.sd_6_1),
                      "cell": str(cell), "count": count.count if count else 0, "label": label})
    external = pd.read_csv(ROOT / "results/external_validation.csv")
    poverty = pd.read_csv(ROOT / "results/poverty_validation.csv")
    pci_row = external.loc[external.section.eq("pci_2011_2022") & external.group.eq("Kruskal–Wallis")].iloc[0]
    poverty_raw = poverty.loc[poverty.section.eq("poverty_pooled_raw") & poverty.group.eq("Kruskal–Wallis")].iloc[0]
    poverty_demean = poverty.loc[poverty.section.eq("poverty_pooled_demeaned") & poverty.group.eq("Kruskal–Wallis")].iloc[0]
    poverty_eta = poverty.loc[poverty.section.eq("poverty_pooled_demeaned") & poverty.group.eq("eta squared")].iloc[0]
    def parsed_p(note: str) -> float:
        match = re.search(r"p = ([0-9.eE+-]+)", note)
        if match is None:
            raise ValueError(f"Cannot read recorded p-value: {note}")
        return float(match.group(1))
    label_keys = recorded[["province_code", "year", "pred_cluster"]]
    grdp = pd.read_csv(ROOT / "data/processed/external_gso_grdp_63.csv").merge(
        label_keys, on=["province_code", "year"], validate="one_to_one").dropna(subset=["pred_cluster", "grdp_per_capita_million_vnd"])
    grdp_test = kruskal(*[g.grdp_per_capita_million_vnd.to_numpy() for _, g in grdp.groupby("pred_cluster")])
    pop = pd.read_csv(ROOT / "data/processed/external_gso_population_63_full.csv")
    odm = pd.read_csv(ROOT / "data/processed/external_odm_health_63.csv").merge(
        pop.loc[pop.year.eq(2020), ["province_code", "gso_pop_total_thousand"]], on="province_code", validate="one_to_one").merge(
        label_keys, on=["province_code", "year"], validate="one_to_one")
    odm["density"] = odm.hospital_count_odm2020 / odm.gso_pop_total_thousand
    odm_test = kruskal(*[g.density.to_numpy() for _, g in odm.groupby("pred_cluster")])
    external_checks = {"pci_n": int(pci_row.n), "pci_p": parsed_p(pci_row.note),
                       "grdp_n": len(grdp), "grdp_p": float(grdp_test.pvalue),
                       "odm_n": len(odm), "odm_p": float(odm_test.pvalue),
                       "odm_zero_count": int(odm.hospital_count_odm2020.eq(0).sum()),
                       "poverty_n": int(poverty_raw.n), "poverty_raw_p": parsed_p(poverty_raw.note),
                       "poverty_demeaned_p": parsed_p(poverty_demean.note),
                       "poverty_eta_note": poverty_eta.note}
    source_paths = [
        "scripts/deliverables/build_slides.py", "scripts/deliverables/slides_chart_workbooks.py",
        "src/sting.py", "src/preprocessing.py", "models/predict_config.json",
        "data/processed/papi_panel_v1_LOCKED.csv", "data/processed/papi_panel_63_2011_2024.csv",
        "results/predict_all_years.csv",
        "results/papi_observed_grid_2024.csv", "results/stakeholder_province_summary_2024.csv",
        "results/papi_forecast_2024.json", "results/robustness.csv", "results/protocol_sensitivity.md",
        "results/external_validation.csv", "results/external_validation.md", "results/poverty_validation.csv",
        "results/preprocessing_audit.csv", "results/metrics.csv", "results/predict_summary.md",
        "reports/crosscheck_mendeley.md", "data/processed/papi_panel_scale_metadata.csv",
        "data/processed/external_gso_grdp_63.csv", "data/processed/external_gso_population_63_full.csv",
        "data/processed/external_odm_health_63.csv", "scripts/common/midterm_clustering.py",
        "scripts/common/papi_forecast.py", "scripts/analysis/predict_sweep.py",
    ]
    source_sha256 = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_paths}
    payload = {"slide_count": SLIDE_COUNT, "config": config, "external_checks": external_checks,
               "source_sha256": source_sha256,
               "panel_rows": len(panel), "panel_columns": len(panel.columns),
               "reference_n": len(ref), "all_complete_n": len(all_raw),
               "reference_counts": {str(int(k)): int(v) for k, v in zip(*np.unique(labels, return_counts=True), strict=True)},
               "shared_n": int(common.sum()), "comparison": comparison,
               "same_cells": same_cells, "same_labels": bool(np.array_equal(raw_labels, scaled_labels)),
               "synthetic_ari": float(adjusted_rand_score(syn_true, syn_labels)),
               "synthetic_clusters": len(set(syn_labels[syn_labels >= 0])), "synthetic_noise": int((syn_labels == -1).sum()),
               "observed": _records(observed), "stakeholders": _records(stake),
               "groups": groups, "threshold_61": lower,
               "transitions": transitions, "transition_n": len(codes), "trace": trace,
               "core_lower_n": int(core.sd_6_1.lt(lower).sum()),
               "stable_names": stake.loc[stake.years_cluster2_2011_2024.eq(14), "province_vi"].tolist(),
               "forecast": json.loads((ROOT / "results/papi_forecast_2024.json").read_text(encoding="utf-8")),
               "robustness": _records(pd.read_csv(ROOT / "results/robustness.csv"))}
    if sum(g["n"] for g in groups) != 63 or len(observed) != 63:
        raise ValueError("The provincial reporting universe must contain 63 rows")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--engine", choices=["portable", "artifact"], default="portable")
    parser.add_argument("--data-only", type=Path, help="Write evidence JSON without building the deck")
    parser.add_argument("--render-dir", type=Path, help="Optional folder for PNG previews")
    args = parser.parse_args()
    data = build_evidence()
    if args.data_only:
        args.data_only.parent.mkdir(parents=True, exist_ok=True)
        args.data_only.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(f"Evidence: {args.data_only}")
        return
    if args.engine == "portable":
        from slides_portable import export_slides
        if args.render_dir:
            raise SystemExit("--render-dir requires --engine artifact; the portable build exports the reviewed snapshot.")
        export_slides(data, args.output)
        print(f"Saved {SLIDE_COUNT} slides to {args.output}")
        return
    node = os.environ.get("ARTIFACT_NODE") or os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required to build PPTX; existing slides remain unchanged.")
    with tempfile.TemporaryDirectory(prefix="sting-papi-slides-") as temp:
        data_path = Path(temp) / "evidence.json"
        candidate_path = Path(temp) / "slides.pptx"
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        cmd = [node, str(Path(__file__).with_suffix(".mjs")), "--data", str(data_path), "--output", str(candidate_path)]
        if args.render_dir:
            cmd += ["--render-dir", str(args.render_dir.resolve())]
        subprocess.run(cmd, cwd=ROOT, check=True)
        from slides_chart_workbooks import embed_chart_workbooks
        charts = embed_chart_workbooks(candidate_path)
        if len(charts) != 2:
            raise ValueError(f"Expected two editable charts, found {len(charts)}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate_path, args.output)
        print(f"Saved {SLIDE_COUNT} slides with {len(charts)} embedded chart workbooks to {args.output}")


if __name__ == "__main__":
    main()
