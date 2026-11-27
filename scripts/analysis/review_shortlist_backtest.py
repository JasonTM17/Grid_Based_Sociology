"""Compare fixed-budget PAPI review shortlists; do not infer review outcomes."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from scripts.common.papi_pred_common import CONFIG_PATH, PANEL_PATH, ROOT, describe_grid_assignment
from src.sting import STING

FEATURES = ("sd_4_2", "sd_6_1")
YEARS = tuple(range(2018, 2025))
BUDGETS = (5, 10)
RULES = ("health_only", "sting_only", "combined")
REVIEW_YEAR = 2024
REVIEW_BUDGET = 5
EXTERNAL_MASTER_PATH = ROOT / "data" / "processed" / "external_master_63_2011_2024.csv"
VALID_OUTCOMES = ("confirmed", "not_confirmed", "insufficient_evidence")


def fit_grid(history: pd.DataFrame, params: dict) -> tuple[StandardScaler, STING]:
    scores = history[list(FEATURES)]
    scaler = StandardScaler().fit(scores)
    grid = STING(
        n_levels=params["n_levels"], factor=params["factor"], min_count=params["min_count"]
    ).fit(scaler.transform(scores))
    grid.cluster(level=params["cluster_level"], connectivity=params["connectivity"])
    return scaler, grid


def ranked(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    keys = {
        "health_only": ["sd_6_1"],
        "sting_only": ["zone_order", "cell_support"],
        "combined": ["zone_order", "sd_6_1"],
    }[rule]
    return frame.sort_values([*keys, "province_code"])


def overlap(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    left, right = set(a.province_code), set(b.province_code)
    return {"intersection": len(left & right), "union": len(left | right)}


def assign(target: pd.DataFrame, fitted: tuple[StandardScaler, STING]) -> pd.DataFrame:
    frame = describe_grid_assignment(target, FEATURES, *fitted)
    frame["zone_order"] = frame.grid_status.map(
        {"outside_grid": 0, "sparse_cell": 1, "in_cluster": 2}
    )
    if frame.zone_order.isna().any():
        raise ValueError("Unexpected grid status for finite scores")
    frame["cell_support"] = frame.reference_count.fillna(0)
    return frame


def analyze(panel: pd.DataFrame, params: dict) -> tuple[pd.DataFrame, dict]:
    if panel.duplicated(["year", "province_code"]).any():
        raise ValueError("Duplicate province-year keys")
    finite = np.isfinite(panel[list(FEATURES)].to_numpy(dtype=float)).all(axis=1)
    complete = panel.loc[finite].sort_values(["year", "province_code"])
    frames: dict[int, pd.DataFrame] = {}
    annual, across_years, changed_grid = [], [], []
    for year in YEARS:
        observed = panel.loc[panel.year.eq(year)]
        history = complete.loc[complete.year.lt(year)]
        target = complete.loc[complete.year.eq(year)]
        if len(target) < max(BUDGETS) or history.empty:
            raise ValueError(f"Insufficient history or target coverage for {year}")
        frame = assign(target, fit_grid(history, params))
        frames[year] = frame
        annual.append({
            "year": year,
            "period": "post_configuration_selection" if year >= 2023 else "retrospective",
            "fit_through": int(history.year.max()),
            "history_rows": len(history),
            "known_provinces": len(observed),
            "eligible": len(frame),
            "status_counts": {str(k): int(v) for k, v in frame.grid_status.value_counts().items()},
            "comparisons": {
                str(k): {
                    f"{a}__{b}": overlap(ranked(frame, a).head(k), ranked(frame, b).head(k))
                    for a, b in itertools.combinations(RULES, 2)
                }
                for k in BUDGETS
            },
        })
        if year == YEARS[0]:
            continue
        previous = frames[year - 1]
        common = set(previous.province_code) & set(frame.province_code)
        if len(common) < max(BUDGETS):
            raise ValueError(f"Insufficient common cohort for {year}")
        left = previous.loc[previous.province_code.isin(common)]
        right = frame.loc[frame.province_code.isin(common)]
        across_years.append({
            "from": year - 1, "to": year, "common_provinces": len(common),
            "comparisons": {
                str(k): {rule: overlap(ranked(left, rule).head(k), ranked(right, rule).head(k))
                         for rule in RULES}
                for k in BUDGETS
            },
        })
        older_history = history.loc[history.year.lt(year - 1)]
        if older_history.empty:
            raise ValueError(f"Missing earlier grid for {year}")
        frozen = assign(target, fit_grid(older_history, params))
        changed_grid.append({
            "year": year,
            "earlier_fit_through": int(older_history.year.max()),
            "updated_fit_through": int(history.year.max()),
            "eligible": len(frame),
            "status_changes": int(frame.grid_status.ne(frozen.grid_status).sum()),
            "comparisons": {
                str(k): {rule: overlap(ranked(frozen, rule).head(k), ranked(frame, rule).head(k))
                         for rule in RULES}
                for k in BUDGETS
            },
        })
    audit = pd.concat(frames.values(), ignore_index=True)
    for rule in RULES:
        order = ranked(audit, rule)
        audit[f"rank_{rule}"] = order.groupby("year").cumcount().add(1)
    return audit.sort_values(["year", "province_code"]), {
        "years": YEARS, "budgets": BUDGETS, "annual": annual,
        "across_years_common_cohort": across_years, "same_year_grid_refresh": changed_grid,
    }


def build_external_dossier(
    cases: pd.DataFrame, root: Path = ROOT
) -> pd.DataFrame | None:
    """Assemble non-PAPI, non-STING provincial indicators for blind case review."""
    ext_path = root / "data" / "processed" / "external_master_63_2011_2024.csv"
    pov_path = root / "data" / "processed" / "external_poverty_63.csv"
    panel_path = root / "data" / "processed" / "papi_panel_63_2011_2024.csv"
    if not ext_path.is_file() or not pov_path.is_file() or not panel_path.is_file():
        return None
    ext = pd.read_csv(ext_path)
    pov = pd.read_csv(pov_path)
    panel_codes = pd.read_csv(panel_path, usecols=["province_code", "province_vi"]).drop_duplicates()
    code_by_name = dict(zip(panel_codes["province_vi"], panel_codes["province_code"], strict=True))

    pci22 = ext.loc[ext.year.eq(2022), ["province_code", "pci_weighted_score"]].rename(
        columns={"pci_weighted_score": "pci_2022"}
    )
    pci19 = ext.loc[ext.year.eq(2019), ["province_code", "pci_weighted_score"]].rename(
        columns={"pci_weighted_score": "pci_2019"}
    )
    pov21 = pov.loc[pov.year.eq(2021), ["province_code", "poverty_rate_pct"]].rename(
        columns={"poverty_rate_pct": "poverty_2021_pct"}
    )
    pov24 = pov.loc[pov.year.eq(2024), ["province_code", "poverty_rate_pct"]].rename(
        columns={"poverty_rate_pct": "poverty_2024_pct"}
    )
    odm20 = ext.loc[
        ext.year.eq(2020), ["province_code", "hospital_count_odm2020", "gso_pop_total_thousand"]
    ].rename(columns={"gso_pop_total_thousand": "pop_2020_thousand"})
    urb22 = ext.loc[ext.year.eq(2022), ["province_code", "gso_urban_residence_pct_derived"]].rename(
        columns={"gso_urban_residence_pct_derived": "gso_urban_pct_2022"}
    )
    waste19 = ext.loc[ext.year.eq(2019), ["province_code", "kg_urb"]].rename(
        columns={"kg_urb": "waste_kg_urb_2019"}
    )
    grdp24 = ext.loc[ext.year.eq(2024), ["province_code", "grdp_per_capita_million_vnd"]].rename(
        columns={"grdp_per_capita_million_vnd": "grdp_2024_mil_vnd"}
    )
    frame = cases[["case_id", "province_vi", "year"]].copy()
    frame["province_code"] = frame["province_vi"].map(code_by_name)
    for aux in (pci22, pci19, pov24, pov21, odm20, grdp24, urb22, waste19):
        frame = frame.merge(aux, on="province_code", how="left")
    frame["pci_change_2019_2022"] = (frame["pci_2022"] - frame["pci_2019"]).round(3)
    frame["poverty_change_2021_2024"] = (frame["poverty_2024_pct"] - frame["poverty_2021_pct"]).round(3)
    frame["hospitals_per_100k_pop_2020"] = (
        100.0 * frame["hospital_count_odm2020"] / frame["pop_2020_thousand"]
    ).round(3)
    for col in ("pci_2022", "grdp_2024_mil_vnd", "poverty_2024_pct", "gso_urban_pct_2022", "waste_kg_urb_2019"):
        frame[col] = frame[col].round(3)
    cols = [
        "case_id",
        "province_vi",
        "year",
        "pci_2022",
        "pci_change_2019_2022",
        "grdp_2024_mil_vnd",
        "poverty_2024_pct",
        "poverty_change_2021_2024",
        "hospital_count_odm2020",
        "hospitals_per_100k_pop_2020",
        "gso_urban_pct_2022",
        "waste_kg_urb_2019",
    ]
    return frame[cols]


def _cohen_kappa(a: pd.Series, b: pd.Series) -> float | None:
    """Two-rater Cohen's kappa over VALID_OUTCOMES; returns None when chance agreement is 1."""
    n = len(a)
    if n == 0:
        return None
    po = float((a.to_numpy() == b.to_numpy()).mean())
    pe = float(sum((a == lab).mean() * (b == lab).mean() for lab in VALID_OUTCOMES))
    if np.isclose(1.0 - pe, 0.0):
        return None
    return float((po - pe) / (1.0 - pe))


def evaluate_review_packet(
    review_dir: Path, sheet_paths: list[Path] | None = None
) -> dict:
    """Score reconciled blind cases against restricted selection_key.csv (fail-closed if blank)."""
    key_path = review_dir / "restricted" / "selection_key.csv"
    if not key_path.is_file():
        raise FileNotFoundError(f"Thiếu khóa tuyển mẫu {key_path}")
    key = pd.read_csv(key_path)

    primary_sheet = review_dir / "for-reviewers" / "cases.csv"
    sheets = [Path(p) for p in sheet_paths] if sheet_paths else [primary_sheet]
    if not sheets:
        raise ValueError("Cần ít nhất 1 tệp phiếu đánh giá đã điền.")

    parsed: list[pd.DataFrame] = []
    for path in sheets:
        df = pd.read_csv(path, keep_default_na=False)
        if not {"case_id", "outcome"} <= set(df.columns):
            raise ValueError(f"Thiếu cột case_id hoặc outcome trong {path}")
        df = df.sort_values("case_id").reset_index(drop=True)
        outcomes = df["outcome"].astype(str).str.strip()
        if outcomes.eq("").any():
            missing_ids = df.loc[outcomes.eq(""), "case_id"].tolist()
            raise ValueError(
                f"Phiếu chưa điền đầy đủ outcome ({path.name}): còn trống {len(missing_ids)} ca {missing_ids[:5]}"
            )
        invalid = sorted(set(outcomes) - set(VALID_OUTCOMES))
        if invalid:
            raise ValueError(f"Giá trị outcome không hợp lệ trong {path.name}: {invalid}")
        if set(df["case_id"]) != set(key["case_id"]):
            raise ValueError(f"case_id trong {path.name} không khớp {key_path.name}")
        df = df.assign(outcome=outcomes)
        parsed.append(df)

    agreement: dict | None = None
    if len(parsed) == 2:
        r1, r2 = parsed[0], parsed[1]
        agree_n = int((r1["outcome"] == r2["outcome"]).sum())
        agreement = {
            "n_cases": len(r1),
            "exact_agreement_count": agree_n,
            "exact_agreement_rate": round(agree_n / len(r1), 4),
            "cohen_kappa": _cohen_kappa(r1["outcome"], r2["outcome"]),
            "disputed_case_ids": r1.loc[r1["outcome"] != r2["outcome"], "case_id"].tolist(),
        }
        # Only score method yield on unambiguous consensus or an explicit consolidated sheet.
        joined_src = r1.loc[r1["outcome"] == r2["outcome"], ["case_id", "outcome"]]
        if len(joined_src) < len(key):
            return {
                "status": "NEEDS_ADJUDICATION",
                "agreement": agreement,
                "methods": {},
                "audit_sample": {},
            }
    elif len(parsed) == 1:
        joined_src = parsed[0][["case_id", "outcome"]]
    else:
        raise ValueError("Hỗ trợ 1 phiếu đã chốt hoặc đúng 2 phiếu chuyên viên độc lập.")

    merged = key.merge(joined_src, on="case_id", how="inner", validate="one_to_one")
    methods = {}
    for rule in RULES:
        sub = merged.loc[merged[f"selected_{rule}"].astype(bool)]
        counts = {k: int((sub["outcome"] == k).sum()) for k in VALID_OUTCOMES}
        methods[rule] = {
            "selected_n": len(sub),
            **counts,
            "confirmed_rate_all_selected": round(counts["confirmed"] / len(sub), 4) if len(sub) else 0.0,
        }
    audit_sub = merged.loc[merged["audit_sample"].astype(bool)]
    audit_counts = {k: int((audit_sub["outcome"] == k).sum()) for k in VALID_OUTCOMES}
    return {
        "status": "SCORED",
        "agreement": agreement,
        "methods": methods,
        "audit_sample": {"n": len(audit_sub), **audit_counts},
    }


def prepare_review(audit: pd.DataFrame, output: Path, *, root: Path = ROOT) -> None:
    """Prepare the blinded reviewer sheet separately from the restricted selection key."""
    frame = audit.loc[audit.year.eq(REVIEW_YEAR)].copy()
    flags = [f"selected_{rule}" for rule in RULES]
    for rule, flag in zip(RULES, flags, strict=True):
        frame[flag] = frame[f"rank_{rule}"].le(REVIEW_BUDGET)
    frame["in_pool"] = frame[flags].any(axis=1)
    frame["review_order"] = frame.province_code.map(
        lambda code: hashlib.sha256(f"papi-review-v1:{REVIEW_YEAR}:{code}".encode()).hexdigest()
    )
    outside = frame.loc[~frame.in_pool].sort_values("review_order")
    if len(outside) < REVIEW_BUDGET:
        raise ValueError("Too few cases outside the review pool")
    frame["audit_sample"] = frame.index.isin(outside.head(REVIEW_BUDGET).index)
    chosen = frame.loc[frame.in_pool | frame.audit_sample].sort_values("review_order").copy()
    chosen["case_id"] = [f"R{i:02d}" for i in range(1, len(chosen) + 1)]
    reviewer = chosen[["case_id", "province_vi", "year"]].assign(
        outcome="", evidence_ref="", rationale=""
    )
    key = chosen[["case_id", "province_code", *flags, "audit_sample"]]
    # Fail closed if a prior round already exists; never overwrite completed reviews.
    output.mkdir(parents=True, exist_ok=False)
    (output / "for-reviewers").mkdir()
    (output / "restricted").mkdir()
    reviewer.to_csv(output / "for-reviewers" / "cases.csv", index=False, lineterminator="\n")
    dossier = build_external_dossier(chosen, root=root)
    if dossier is not None:
        dossier.to_csv(output / "for-reviewers" / "external_dossier.csv", index=False, lineterminator="\n")
    key.to_csv(output / "restricted" / "selection_key.csv", index=False, lineterminator="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--review-dir", type=Path, help="New directory for optional blind review packet")
    parser.add_argument(
        "--dossier-only-dir",
        type=Path,
        help="Write/refresh for-reviewers/external_dossier.csv alongside an existing cases.csv without overwriting cases.csv",
    )
    parser.add_argument(
        "--evaluate-review-dir",
        type=Path,
        help="Score completed reviewer sheet(s) against restricted/selection_key.csv",
    )
    parser.add_argument(
        "--reviewer-sheets",
        type=Path,
        nargs="+",
        help="Optional 1 consolidated CSV or 2 independent reviewer CSVs for --evaluate-review-dir",
    )
    args = parser.parse_args()
    if args.dossier_only_dir is not None:
        cases_df = pd.read_csv(args.dossier_only_dir / "for-reviewers" / "cases.csv")
        dossier = build_external_dossier(cases_df)
        if dossier is None:
            raise FileNotFoundError("Thiếu data/processed/external_master_63_2011_2024.csv để dựng external_dossier.csv")
        out_dossier = args.dossier_only_dir / "for-reviewers" / "external_dossier.csv"
        dossier.to_csv(out_dossier, index=False, lineterminator="\n")
        print(f"Saved dossier ({len(dossier)} cases): {out_dossier}")
        return
    if args.evaluate_review_dir is not None:
        result = evaluate_review_packet(args.evaluate_review_dir, args.reviewer_sheets)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if tuple(config["features"]) != FEATURES:
        raise ValueError("Published feature pair changed; review the study protocol")
    audit, summary = analyze(pd.read_csv(PANEL_PATH), config["sting"])
    summary["panel_sha256"] = hashlib.sha256(PANEL_PATH.read_bytes()).hexdigest()
    summary["config_sha256"] = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    if args.review_dir is not None:
        prepare_review(audit, args.review_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit.to_csv(args.output_dir / "review_shortlist_ranks.csv", index=False, lineterminator="\n")
    (args.output_dir / "review_shortlist_backtest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
