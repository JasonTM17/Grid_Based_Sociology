"""Read-only data preparation for the local PAPI Streamlit dashboard."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats

from .papi_pred_common import (
    REGRESSION_FEATURES,
    REGRESSION_TARGET,
    ROOT,
    select_model_by_cv,
)


class DashboardDataError(RuntimeError):
    """An input artifact is missing, stale, or has an unsafe schema."""


_REGRESSION_MODEL_ARTIFACTS = {
    "ridge": Path("models/sup_ridge.joblib"),
    "random_forest": Path("models/sup_rf.joblib"),
}


def _require_unique_keys(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    missing = set(keys) - set(frame.columns)
    if missing:
        raise DashboardDataError(f"{label} thiếu cột khóa: {', '.join(sorted(missing))}.")
    if frame.duplicated(keys).any():
        raise DashboardDataError(f"{label} có khóa trùng theo {', '.join(keys)}.")


def load_dashboard_assets(root: Path = ROOT, include_models: bool = True) -> dict:
    """Load only saved local artifacts; never trains or writes project files."""
    root = Path(root)
    specs = {
        "panel": (Path("data/processed/papi_panel_63_2011_2024.csv"), "python scripts/build_panel.py"),
        "config": (Path("models/predict_config.json"), "python scripts/predict_sweep.py"),
        "assignments": (Path("results/predict_all_years.csv"), "python scripts/predict_demo.py"),
        "metrics": (Path("results/supervised_metrics.csv"), "python scripts/predict_supervised.py"),
    }
    for label, (relative_path, command) in specs.items():
        path = root / relative_path
        if not path.is_file():
            raise DashboardDataError(
                f"Thiếu artifact {relative_path.as_posix()} ({label}). Tạo lại bằng `{command}`."
            )

    panel = pd.read_csv(root / specs["panel"][0])
    config = json.loads((root / specs["config"][0]).read_text(encoding="utf-8"))
    assignments = pd.read_csv(root / specs["assignments"][0])
    metrics = pd.read_csv(root / specs["metrics"][0])

    _require_unique_keys(panel, ["province_code", "year"], "Panel PAPI")
    _require_unique_keys(assignments, ["province_code", "year"], "STING assignments")
    if not set(config.get("features", [])) <= set(assignments.columns):
        raise DashboardDataError(
            "Feature trong predict_config.json không khớp results/predict_all_years.csv. "
            "Tạo lại assignment bằng `python scripts/predict_demo.py`."
        )
    if not set(config.get("features", [])) <= set(panel.columns):
        raise DashboardDataError(
            "Feature trong predict_config.json không có trong panel PAPI. "
            "Tạo lại panel bằng `python scripts/build_panel.py`."
        )
    if not {"task", "model", "value_cv"} <= set(metrics.columns):
        raise DashboardDataError("results/supervised_metrics.csv thiếu các cột task/model/value_cv.")
    assets = {
        "panel": panel,
        "config": config,
        "assignments": assignments,
        "metrics": metrics,
    }
    if include_models:
        assets.update(load_regression_models(root))
    return assets


def load_regression_models(root: Path = ROOT) -> dict:
    """Load saved regressors only when the regression view is requested."""
    root = Path(root)
    for label, relative_path in _REGRESSION_MODEL_ARTIFACTS.items():
        if not (root / relative_path).is_file():
            raise DashboardDataError(
                f"Thiếu artifact {relative_path.as_posix()} ({label}). "
                "Tạo lại bằng `python scripts/predict_supervised.py`."
            )
    return {
        label: joblib.load(root / relative_path)
        for label, relative_path in _REGRESSION_MODEL_ARTIFACTS.items()
    }


def _cluster_label(value, feature_missing: bool = False) -> str:
    if pd.isna(value):
        return (
            "Thiếu feature — chưa gán"
            if feature_missing
            else "Không có assignment trong artifact"
        )
    cluster = int(value)
    return "Nhiễu (-1)" if cluster == -1 else f"Cụm {cluster}"


def prepare_sting_view(
    panel: pd.DataFrame,
    assignments: pd.DataFrame,
    year: int,
    required_features: list[str],
    province_codes: set[int] | None = None,
    cluster_codes: set[int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Join year assignments by province/year and apply explicit STING filters."""
    keys = ["province_code", "year"]
    _require_unique_keys(panel, keys, "Panel PAPI")
    _require_unique_keys(assignments, keys, "STING assignments")
    required = {"pred_cluster", "split"}
    if not required <= set(assignments.columns):
        raise DashboardDataError("STING assignments cần các cột pred_cluster và split.")
    if not required_features or not set(required_features) <= set(panel.columns):
        raise DashboardDataError("Panel PAPI thiếu feature cần thiết để giải thích dòng chưa gán.")

    source = panel.loc[panel.year == year].copy()
    year_assignments = assignments.loc[
        assignments.year == year, keys + ["pred_cluster", "split"]
    ]
    joined = source.merge(
        year_assignments, on=keys, how="left", validate="one_to_one", indicator=True
    )
    artifact_assignment_missing = joined["_merge"].eq("left_only")
    incomplete_features = joined[required_features].isna().any(axis=1)
    joined["assignment_state"] = np.select(
        [joined["_merge"].eq("both"), incomplete_features],
        ["Đã gán", "Thiếu feature — chưa gán"],
        default="Không có assignment trong artifact",
    )
    joined["feature_missing"] = incomplete_features
    joined["artifact_assignment_missing"] = artifact_assignment_missing
    joined["cluster_label"] = [
        _cluster_label(cluster, feature_missing)
        for cluster, feature_missing in zip(joined.pred_cluster, joined.feature_missing)
    ]
    joined = joined.drop(columns="_merge")

    visible = joined
    if province_codes is not None:
        visible = visible.loc[visible.province_code.isin(province_codes)]
    if cluster_codes is not None:
        visible = visible.loc[visible.pred_cluster.isin(cluster_codes)]
    visible = visible.sort_values("province_code").reset_index(drop=True)

    counts = {
        "source_rows": int(len(joined)),
        "eligible_assignments": int(joined.pred_cluster.notna().sum()),
        "missing_feature_rows": int(incomplete_features.sum()),
        "missing_assignment_rows": int(joined.pred_cluster.isna().sum()),
        "unassigned_artifact_rows": int(
            (artifact_assignment_missing & ~incomplete_features).sum()
        ),
        "noise_rows": int(joined.pred_cluster.eq(-1).sum()),
        "covered_rows": int((joined.pred_cluster.notna() & joined.pred_cluster.ne(-1)).sum()),
        "filtered_rows": int(len(visible)),
        "filtered_noise_rows": int(visible.pred_cluster.eq(-1).sum()),
        "filtered_missing_feature_rows": int(visible.feature_missing.sum()),
        "filtered_unassigned_artifact_rows": int(
            (visible.artifact_assignment_missing & ~visible.feature_missing).sum()
        ),
    }
    return visible, counts


def prepare_regression_holdout(
    panel: pd.DataFrame,
    assignments: pd.DataFrame,
    ridge_model=None,
    random_forest_model=None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Prepare the saved 2023→2024 holdout; predict when both models are given.

    Origin clusters come from STING's 2023 assignment, available at forecast time.
    The 2024 cluster is deliberately not joined because `sd_6_1` is the target.
    """
    if (ridge_model is None) != (random_forest_model is None):
        raise DashboardDataError("Cần truyền đồng thời cả hai model hồi quy hoặc không truyền model nào.")

    keys = ["province_code", "year"]
    _require_unique_keys(panel, keys, "Panel PAPI")
    _require_unique_keys(assignments, keys, "STING assignments")
    required_panel_columns = set(REGRESSION_FEATURES) | {
        REGRESSION_TARGET, "province_vi"
    }
    missing_panel_columns = required_panel_columns - set(panel.columns)
    if missing_panel_columns:
        raise DashboardDataError(
            "Panel PAPI thiếu cột hồi quy: " + ", ".join(sorted(missing_panel_columns))
        )
    if not {"pred_cluster", "year", "province_code"} <= set(assignments.columns):
        raise DashboardDataError("STING assignments thiếu khóa hoặc cột pred_cluster.")

    origin = panel.loc[panel.year == 2023].copy()
    target = panel.loc[panel.year == 2024, ["province_code", REGRESSION_TARGET]].rename(
        columns={REGRESSION_TARGET: "actual_2024"}
    )
    if origin.empty or target.empty:
        raise DashboardDataError("Thiếu dữ liệu origin 2023 hoặc target 2024 cho holdout.")

    complete_origin = origin.dropna(subset=REGRESSION_FEATURES).copy()
    pairs = complete_origin.merge(
        target, on="province_code", how="left", validate="one_to_one"
    )
    missing_target = int(pairs.actual_2024.isna().sum())
    pairs = pairs.loc[pairs.actual_2024.notna()].copy()

    origin_assignments = assignments.loc[
        assignments.year == 2023, ["province_code", "pred_cluster"]
    ].rename(columns={"pred_cluster": "origin_cluster_2023"})
    pairs = pairs.merge(
        origin_assignments, on="province_code", how="left", validate="one_to_one"
    )
    missing_origin_cluster = int(pairs.origin_cluster_2023.isna().sum())

    pairs["carry_forward"] = pairs[REGRESSION_TARGET].astype(float)
    if ridge_model is not None:
        X = pairs[REGRESSION_FEATURES].to_numpy()
        pairs["prediction_ridge"] = np.asarray(ridge_model.predict(X), dtype=float)
        pairs["prediction_random_forest"] = np.asarray(random_forest_model.predict(X), dtype=float)
    pairs["origin_cluster_label"] = pairs.origin_cluster_2023.map(_cluster_label)
    pairs = pairs.sort_values("province_code").reset_index(drop=True)

    counts = {
        "origin_source_rows": int(len(origin)),
        "missing_origin_feature_rows": int(len(origin) - len(complete_origin)),
        "origin_feature_rows": int(len(complete_origin)),
        "missing_target_for_complete_origin": missing_target,
        "holdout_pairs": int(len(pairs)),
        "missing_origin_cluster": missing_origin_cluster,
    }
    return pairs, counts


def filter_regression_holdout(
    holdout: pd.DataFrame,
    province_codes: set[int] | None = None,
    origin_clusters: set[int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Filter holdout by province and only by STING cluster at origin year 2023."""
    visible = holdout
    if province_codes is not None:
        visible = visible.loc[visible.province_code.isin(province_codes)]
    before_cluster = visible
    if origin_clusters is not None:
        visible = visible.loc[visible.origin_cluster_2023.isin(origin_clusters)]
    visible = visible.reset_index(drop=True)
    counts = {
        "holdout_pairs": int(len(holdout)),
        "after_province_filter": int(len(before_cluster)),
        "missing_origin_cluster_after_province_filter": int(
            before_cluster.origin_cluster_2023.isna().sum()
        ),
        "after_origin_cluster_filter": int(len(visible)),
    }
    return visible, counts


def select_regression_model(metrics: pd.DataFrame) -> str:
    """Return the Ridge/RF family selected using only its train-only CV score."""
    candidates = metrics.loc[
        metrics.task.eq("regression") & metrics.model.isin(["ridge", "random forest"])
    ]
    return select_model_by_cv(candidates)


def select_classification_model(metrics: pd.DataFrame) -> str:
    """Select only tuned classifier families; keep the majority baseline as a baseline."""
    candidates = metrics.loc[
        metrics.task.eq("classification")
        & metrics.model.isin(["logistic regression", "random forest"])
    ]
    return select_model_by_cv(candidates)


# --------------------------------------------------------------------- #
# Kiểm chứng ngoại lai — PCI (VCCI–USAID) · y tế 2020 · GRDP 2018–2024.
# Nguồn: data/processed/external_pci_63_full.csv + results/external_validation.csv
# (sinh bởi scripts/external_validation.py, provenance trong
# data/processed/external_provenance.md). Mọi số tính lại từ CSV — không
# hardcode, không nội suy ô thiếu.
# --------------------------------------------------------------------- #

_EXTERNAL_PCI_CSV = Path("data/processed/external_pci_63_full.csv")
_EXTERNAL_VALIDATION_CSV = Path("results/external_validation.csv")
_EXTERNAL_REBUILD_COMMAND = "python scripts/external_validation.py"

# Cửa sổ của kiểm định CHÍNH (§1) và kiểm tra PHỤ Top-30 (§2) trong artifact.
PCI_MAIN_WINDOW = (2011, 2022)
PCI_TOP30_WINDOW = (2023, 2024)

_REQUIRED_PCI_COLUMNS = {"province_code", "year", "province_vi", "pci_weighted_score"}
_REQUIRED_VALIDATION_COLUMNS = {
    "section", "group", "year", "n", "mean", "median", "std", "min", "max", "note",
}
_REQUIRED_VALIDATION_SECTIONS = (
    "pci_2011_2022",
    "pci_top30_2023_2024",
    "odm_health_2020",
    "grdp_2018_2024",
)


def load_external_validation_assets(root: Path = ROOT) -> dict:
    """Load the two external-validation artifacts used by the dashboard tab."""
    root = Path(root)
    for label, relative_path in {
        "pci": _EXTERNAL_PCI_CSV,
        "validation": _EXTERNAL_VALIDATION_CSV,
    }.items():
        if not (root / relative_path).is_file():
            raise DashboardDataError(
                f"Thiếu artifact {relative_path.as_posix()} ({label}). "
                f"Tạo lại bằng `{_EXTERNAL_REBUILD_COMMAND}`."
            )
    pci = pd.read_csv(root / _EXTERNAL_PCI_CSV, encoding="utf-8-sig")
    validation = pd.read_csv(root / _EXTERNAL_VALIDATION_CSV, encoding="utf-8-sig")

    missing_pci = _REQUIRED_PCI_COLUMNS - set(pci.columns)
    if missing_pci:
        raise DashboardDataError(
            f"{_EXTERNAL_PCI_CSV.as_posix()} thiếu cột: {', '.join(sorted(missing_pci))}."
        )
    _require_unique_keys(pci, ["province_code", "year"], "PCI external")
    missing_validation = _REQUIRED_VALIDATION_COLUMNS - set(validation.columns)
    if missing_validation:
        raise DashboardDataError(
            f"{_EXTERNAL_VALIDATION_CSV.as_posix()} thiếu cột: "
            f"{', '.join(sorted(missing_validation))}."
        )
    present_sections = set(validation.section.dropna().astype(str).str.strip())
    missing_sections = set(_REQUIRED_VALIDATION_SECTIONS) - present_sections
    if missing_sections:
        raise DashboardDataError(
            f"{_EXTERNAL_VALIDATION_CSV.as_posix()} thiếu section: "
            f"{', '.join(sorted(missing_sections))}."
        )
    return {"pci": pci, "validation": validation}


def prepare_external_pci_view(
    pci: pd.DataFrame,
    assignments: pd.DataFrame,
    year_min: int = PCI_MAIN_WINDOW[0],
    year_max: int = PCI_MAIN_WINDOW[1],
) -> tuple[pd.DataFrame, dict]:
    """Join PCI province-year cells with frozen STING labels on a year window.

    Mirror của scripts/external_validation.py §1/§2: giữ ô có điểm PCI, nối
    trái `pred_cluster`, chỉ kiểm định trên ô CÓ nhãn; ô thiếu nhãn được đếm,
    không nội suy. `year_min/year_max` = 2023–2024 cho kiểm tra phụ Top-30.
    """
    keys = ["province_code", "year"]
    _require_unique_keys(pci, keys, "PCI external")
    _require_unique_keys(assignments, keys, "STING assignments")
    if not _REQUIRED_PCI_COLUMNS <= set(pci.columns):
        raise DashboardDataError("PCI external thiếu cột bắt buộc để nối nhãn cụm.")
    if not {"pred_cluster"} <= set(assignments.columns):
        raise DashboardDataError("STING assignments thiếu cột pred_cluster.")

    window = pci.loc[
        pci.year.between(year_min, year_max) & pci.pci_weighted_score.notna()
    ].copy()
    labels = assignments.loc[:, keys + ["pred_cluster"]]
    joined = window.merge(
        labels, on=keys, how="left", validate="one_to_one", indicator=True
    )
    missing_label = joined["_merge"].eq("left_only")
    joined = joined.drop(columns="_merge")

    view = joined.loc[joined.pred_cluster.notna()].copy()
    view["pred_cluster"] = view["pred_cluster"].astype(int)
    view["cluster_label"] = view.pred_cluster.map(_cluster_label)
    view = view.sort_values(["year", "province_code"]).reset_index(drop=True)

    n_by_cluster = {
        int(code): int(size) for code, size in view.groupby("pred_cluster").size().items()
    }
    counts = {
        "year_min": int(year_min),
        "year_max": int(year_max),
        "window_cells": int(len(window)),
        "missing_label_cells": int(missing_label.sum()),
        "tested_points": int(len(view)),
        "clusters": sorted(n_by_cluster),
        "n_by_cluster": n_by_cluster,
    }
    return view, counts


def external_pci_group_stats(view: pd.DataFrame) -> pd.DataFrame:
    """Per-cluster PCI summary, cùng quy ước bảng nhóm trong artifact."""
    rows = []
    for code, sub in view.groupby("pred_cluster"):
        values = sub.pci_weighted_score
        rows.append({
            "pred_cluster": int(code),
            "cluster_label": _cluster_label(code),
            "n": int(len(sub)),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "std": float(values.std(ddof=1)) if len(sub) > 1 else float("nan"),
            "min": float(values.min()),
            "max": float(values.max()),
        })
    return pd.DataFrame(rows).sort_values("pred_cluster").reset_index(drop=True)


def external_pci_tests(view: pd.DataFrame) -> dict:
    """Recompute one-way ANOVA + Kruskal–Wallis trên các điểm PCI đã nối nhãn.

    Cùng estimator với scripts/external_validation.py (scipy `f_oneway`,
    `kruskal`, eta² = SS giữa / SS tổng) — không đọc lại số đã công bố.
    """
    if view.pci_weighted_score.isna().any():
        raise DashboardDataError("PCI view còn ô thiếu điểm — không đưa vào kiểm định.")
    groups = [sub.pci_weighted_score.to_numpy() for _, sub in view.groupby("pred_cluster")]
    if len(groups) < 2:
        raise DashboardDataError("Kiểm định ngoại lai cần ít nhất 2 nhóm cụm.")
    f_stat, p_anova = stats.f_oneway(*groups)
    h_stat, p_kw = stats.kruskal(*groups)
    grand = view.pci_weighted_score.to_numpy()
    ss_total = float(((grand - grand.mean()) ** 2).sum())
    ss_between = float(sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in groups))
    return {
        "f": float(f_stat),
        "p_anova": float(p_anova),
        "df1": len(groups) - 1,
        "df2": len(view) - len(groups),
        "h": float(h_stat),
        "p_kw": float(p_kw),
        "eta_sq": ss_between / ss_total if ss_total > 0 else float("nan"),
        "n": int(len(view)),
    }


def format_p_value(p: float) -> str:
    """Format p-value đúng quy ước cột note trong results/external_validation.csv."""
    return "p < 1e-12" if p < 1e-12 else f"p = {p:.3g}"


def _published_group_code(group) -> int:
    """Map tên nhóm trong artifact ("nhiễu (–1)", "cụm 2") về mã cụm."""
    text = str(group).strip()
    if text.startswith("nhiễu"):
        return -1
    match = re.fullmatch(r"cụm\s+(-?\d+)", text)
    if match:
        return int(match.group(1))
    raise DashboardDataError(
        f"Không hiểu tên nhóm '{group}' trong {_EXTERNAL_VALIDATION_CSV.as_posix()}."
    )


def published_external_pci_tests(validation: pd.DataFrame, section: str) -> dict:
    """Parse các dòng kiểm định đã công bố của một section PCI trong artifact.

    p trong note theo đúng quy ước `format_p_value` (và `fmt_p` của generator
    `scripts/external_validation.py`): `p = <số>` cho p thường, và `p < 1e-12`
    khi p cực nhỏ — dạng chặn trên, không phải điểm số. Dict trả về kèm
    `p_anova_is_bound`/`p_kw_is_bound` để gate so sánh đúng loại giá trị.
    """
    rows = validation.loc[validation.section.eq(section)]
    if rows.empty:
        raise DashboardDataError(
            f"{_EXTERNAL_VALIDATION_CSV.as_posix()} không có section '{section}'."
        )

    def _single_row(prefix: str) -> pd.Series:
        hits = rows.loc[rows.group.astype(str).str.strip().str.startswith(prefix)]
        if len(hits) != 1:
            raise DashboardDataError(
                f"Section '{section}' cần đúng 1 dòng '{prefix}…', thấy {len(hits)}."
            )
        return hits.iloc[0]

    anova_row = _single_row("ANOVA F(")
    anova_df = re.fullmatch(
        r"ANOVA F\((\d+),\s*(\d+)\)", str(anova_row.group).strip()
    )
    anova_note = re.fullmatch(
        r"F\s*=\s*([0-9.eE+-]+)\s*;\s*p\s*([<=])\s*([0-9.eE+-]+)",
        str(anova_row.note).strip(),
    )
    kruskal_note = re.fullmatch(
        r"H\s*=\s*([0-9.eE+-]+)\s*;\s*p\s*([<=])\s*([0-9.eE+-]+)",
        str(_single_row("Kruskal").note).strip(),
    )
    eta_note = re.fullmatch(
        r"eta²\s*=\s*([0-9.eE+-]+)(?:\s*\(.*\))?",
        str(_single_row("eta").note).strip(),
    )
    if not (anova_df and anova_note and kruskal_note and eta_note):
        raise DashboardDataError(
            f"Section '{section}' có dòng kiểm định không đọc được định dạng."
        )
    artifact_n = anova_row["n"]
    if pd.isna(artifact_n) or str(artifact_n).strip() == "":
        raise DashboardDataError(f"Section '{section}' thiếu n cho dòng kiểm định.")
    try:
        published_n = int(float(artifact_n))
    except (TypeError, ValueError) as exc:
        raise DashboardDataError(
            f"Section '{section}' có n không đọc được cho dòng kiểm định."
        ) from exc
    return {
        "df1": int(anova_df.group(1)),
        "df2": int(anova_df.group(2)),
        "f": float(anova_note.group(1)),
        "p_anova": float(anova_note.group(3)),
        "p_anova_is_bound": anova_note.group(2) == "<",
        "h": float(kruskal_note.group(1)),
        "p_kw": float(kruskal_note.group(3)),
        "p_kw_is_bound": kruskal_note.group(2) == "<",
        "eta_sq": float(eta_note.group(1)),
        "n": published_n,
    }


def ensure_external_pci_consistency(
    view: pd.DataFrame,
    validation: pd.DataFrame,
    section: str = "pci_2011_2022",
) -> dict:
    """Tính lại kiểm định PCI và TỪ CHỐI mọi lệch vượt sai số làm tròn.

    Số công bố (ANOVA F=9.04, Kruskal H=31.78, …) không được đổi: nếu số tính
    lại từ CSV lệch artifact nhiều hơn độ làm tròn (4 số lẻ cho F/H/eta², 3 chữ
    số có nghĩa cho p, giá trị nguyên cho n/df), raise thay vì hiển thị số khác
    một cách âm thầm. p dạng chặn trên (`p < 1e-12` theo quy ước
    `format_p_value`) không so isclose — yêu cầu p tính lại cũng thỏa chặn trên
    đó. Trả về dict số tính lại để dashboard hiển thị.
    """
    recomputed = external_pci_tests(view)
    published = published_external_pci_tests(validation, section)
    problems: list[str] = []
    for key in ("df1", "df2", "n"):
        if recomputed[key] != published[key]:
            problems.append(f"{key}: tính lại {recomputed[key]} ≠ artifact {published[key]}")
    for key in ("f", "h", "eta_sq"):
        if abs(recomputed[key] - published[key]) > 5.1e-5:
            problems.append(
                f"{key}: tính lại {recomputed[key]:.6f} ≠ artifact {published[key]}"
            )
    for key in ("p_anova", "p_kw"):
        if published[f"{key}_is_bound"]:
            # Artifact ghi chặn trên dạng 'p < X' (quy ước format_p_value cho p
            # cực nhỏ) — không có điểm số để so isclose; nhất quán khi p tính
            # lại cũng nằm dưới đúng chặn trên đó.
            if recomputed[key] >= published[key]:
                problems.append(
                    f"{key}: tính lại {recomputed[key]:.3g} không thỏa "
                    f"'p < {published[key]:g}' của artifact."
                )
        elif not math.isclose(recomputed[key], published[key], rel_tol=0.006):
            problems.append(
                f"{key}: tính lại {recomputed[key]:.3g} ≠ artifact {published[key]:.3g}"
            )

    group_stats = external_pci_group_stats(view).set_index("pred_cluster")
    section_rows = validation.loc[validation.section.eq(section)]
    for _, row in section_rows.iterrows():
        try:
            code = _published_group_code(row.group)
        except DashboardDataError:
            continue  # dòng kiểm định (ANOVA/Kruskal/eta), không phải nhóm cụm
        if code not in group_stats.index:
            problems.append(f"nhóm '{row.group}' không có trong dữ liệu tính lại.")
            continue
        recomputed_row = group_stats.loc[code]
        for key in ("n", "mean", "median", "std", "min", "max"):
            artifact_value = row[key]
            artifact_missing = pd.isna(artifact_value) or str(artifact_value).strip() == ""
            recomputed_value = recomputed_row[key]
            if artifact_missing:
                if not pd.isna(recomputed_value):
                    problems.append(
                        f"{key} nhóm '{row.group}': artifact trống nhưng tính lại có giá trị."
                    )
                continue
            try:
                artifact_number = float(artifact_value)
            except (TypeError, ValueError):
                problems.append(
                    f"{key} nhóm '{row.group}': artifact không đọc được '{artifact_value}'."
                )
                continue
            if pd.isna(recomputed_value):
                problems.append(
                    f"{key} nhóm '{row.group}': tính lại trống nhưng artifact = {artifact_value}."
                )
            elif key == "n":
                if int(recomputed_value) != int(artifact_number):
                    problems.append(
                        f"n nhóm '{row.group}': tính lại {int(recomputed_value)} "
                        f"≠ artifact {int(artifact_number)}."
                    )
            elif abs(float(recomputed_value) - artifact_number) > 5.01e-4:
                problems.append(
                    f"{key} nhóm '{row.group}': tính lại {float(recomputed_value):.4f} "
                    f"≠ artifact {artifact_value}."
                )

    if problems:
        raise DashboardDataError(
            "Số PCI tính lại KHÔNG khớp artifact đã công bố ("
            + "; ".join(problems)
            + f"). Chạy lại `{_EXTERNAL_REBUILD_COMMAND}` rồi làm mới dashboard."
        )
    return recomputed


def external_section_frame(validation: pd.DataFrame, section: str) -> pd.DataFrame:
    """Rows của một section nhóm cụm (y tế 2020, GRDP 2018–2024) + nhãn dashboard.

    Chỉ dùng cho section mà mọi dòng là nhóm cụm; section PCI có thêm các dòng
    kiểm định nên sẽ bị từ chối bởi `_published_group_code`.
    """
    rows = validation.loc[validation.section.eq(section)].copy()
    if rows.empty:
        raise DashboardDataError(
            f"{_EXTERNAL_VALIDATION_CSV.as_posix()} không có section '{section}'."
        )
    rows["pred_cluster"] = [_published_group_code(group) for group in rows.group]
    rows["cluster_label"] = rows.pred_cluster.map(_cluster_label)
    rows["year"] = rows.year.astype("Int64")
    rows["n"] = rows.n.astype("Int64")
    return rows.sort_values(["pred_cluster", "year"]).reset_index(drop=True)


# --------------------------------------------------------------------- #
# Kiểm chứng bổ trợ — nghèo cấp tỉnh GSO (pxweb V14.47) theo nhãn cụm.
# Nguồn: data/processed/external_poverty_63.csv (sinh bởi
# scripts/build_poverty_63.py) + results/predict_all_years.csv (model chốt,
# gate bởi tests/test_artifact_reproduction.py). Protocol join GIỐNG
# poverty_validation.py / external_validation.py: khóa (year, province_code)
# duy nhất hai phía, left-join `validate="one_to_one"`, KHÔNG nội suy ô thiếu;
# ô thiếu được đếm và liệt kê tường minh. Hai kiểm định chính báo cáo CÙNG
# nhau — gộp thô và đã-trừ-median-năm (pov_dm) — vì chuẩn nghèo đổi theo giai
# đoạn: chỉ so GIỮA CỤM trong cùng một năm là hợp lệ. Mọi số tự tính lại từ
# CSV — không hardcode.
# --------------------------------------------------------------------- #

_POVERTY_CSV = Path("data/processed/external_poverty_63.csv")
_POVERTY_REBUILD_COMMAND = "python scripts/build_poverty_63.py"

# Cửa sổ giao thiết kế (= DESIGN_WINDOW của scripts/poverty_validation.py:88):
# chuỗi nghèo phủ 2006/2008/2010 + 2012–2025 liên tục (2017–2019 điền từ NGTK
# 2020/2021 — scripts/build_poverty_gap.py), nhãn cụm phủ 2011–2024, nên giao
# tự tính từ dữ liệu phải khớp đúng danh sách này — lệch là artifact đã đổi
# phía nguồn hoặc phía nhãn.
POVERTY_OVERLAP_YEARS = (2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
                         2020, 2021, 2022, 2023, 2024)

# Đủ để nối nhãn và liệt kê ô thiếu; load_poverty_assets yêu cầu schema đầy đủ.
_REQUIRED_POVERTY_VIEW_COLUMNS = {"province_code", "province_vi", "year", "poverty_rate_pct"}
_REQUIRED_POVERTY_CSV_COLUMNS = {
    "province_code", "province_ascii", "province_vi", "year",
    "poverty_rate_pct", "papi_province_code",
}


def load_poverty_assets(root: Path = ROOT) -> dict:
    """Load artifact nghèo cấp tỉnh dùng cho block 'Nghèo cấp tỉnh' Tab 4."""
    root = Path(root)
    if not (root / _POVERTY_CSV).is_file():
        raise DashboardDataError(
            f"Thiếu artifact {_POVERTY_CSV.as_posix()} (poverty). "
            f"Tạo lại bằng `{_POVERTY_REBUILD_COMMAND}`."
        )
    poverty = pd.read_csv(root / _POVERTY_CSV, encoding="utf-8-sig")
    missing = _REQUIRED_POVERTY_CSV_COLUMNS - set(poverty.columns)
    if missing:
        raise DashboardDataError(
            f"{_POVERTY_CSV.as_posix()} thiếu cột: {', '.join(sorted(missing))}."
        )
    _require_unique_keys(poverty, ["province_code", "year"], "Poverty GSO")
    # papi_province_code khớp province_code → khóa nối nhãn thống nhất hai bên
    # (assert tương tự poverty_validation.py:277).
    misaligned = poverty.province_code.ne(poverty.papi_province_code)
    if misaligned.any():
        raise DashboardDataError(
            f"{_POVERTY_CSV.as_posix()}: papi_province_code lệch province_code "
            f"ở {int(misaligned.sum())} dòng — khóa nối nhãn không thống nhất."
        )
    return {"poverty": poverty}


def prepare_poverty_cluster_view(
    poverty: pd.DataFrame,
    assignments: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Join poverty province-year với nhãn cụm đóng băng theo protocol.

    Mirror của prepare_external_pci_view và của khối join trong
    scripts/poverty_validation.py (255-292): giữ ô poverty CÓ giá trị trong
    cửa sổ giao, nối trái `pred_cluster`, chỉ phân tích ô CÓ nhãn; ô thiếu
    nhãn và ô thiếu giá trị nguồn được đếm và liệt kê tường minh, không nội
    suy. Cột `pov_dm` = poverty đã trừ median TRONG TỪNG NĂM trên chính panel
    phân tích — hằng số trong năm nên không đổi so sánh giữa cụm trong năm,
    chỉ tái trọng số giữa các năm khi gộp.
    """
    keys = ["year", "province_code"]
    _require_unique_keys(poverty, keys, "Poverty GSO")
    _require_unique_keys(assignments, keys, "STING assignments")
    missing_poverty = _REQUIRED_POVERTY_VIEW_COLUMNS - set(poverty.columns)
    if missing_poverty:
        raise DashboardDataError(
            "Poverty GSO thiếu cột bắt buộc: " + ", ".join(sorted(missing_poverty)) + "."
        )
    if not {"pred_cluster"} <= set(assignments.columns):
        raise DashboardDataError("STING assignments thiếu cột pred_cluster.")

    poverty_years = set(poverty.year.astype(int))
    assignment_years = set(assignments.year.astype(int))
    overlap_years = sorted(poverty_years & assignment_years)
    if tuple(overlap_years) != POVERTY_OVERLAP_YEARS:
        raise DashboardDataError(
            "Cửa sổ giao poverty ↔ nhãn cụm lệch protocol: tính lại từ CSV là "
            f"{overlap_years}, protocol yêu cầu {list(POVERTY_OVERLAP_YEARS)}. "
            "Artifact poverty hoặc nhãn đã đổi — kiểm tra lại "
            f"`{_POVERTY_REBUILD_COMMAND}` và nhãn cụm."
        )

    window = poverty.loc[poverty.year.isin(overlap_years)].copy()
    missing_source = window.loc[window.poverty_rate_pct.isna(), keys + ["province_vi"]]
    valid = window.loc[window.poverty_rate_pct.notna()].copy()

    # Cột tên của assignments không mang sang (chỉ hiển thị phía poverty).
    labels = assignments.loc[:, keys + ["pred_cluster"]]
    merged = valid.merge(labels, on=keys, how="left", validate="one_to_one")
    no_label = merged.loc[merged.pred_cluster.isna(), keys + ["province_vi"]]

    view = merged.loc[merged.pred_cluster.notna()].copy()
    view["pred_cluster"] = view["pred_cluster"].astype(int)
    view["cluster_label"] = view.pred_cluster.map(_cluster_label)
    view["pov_dm"] = view.poverty_rate_pct - view.groupby("year").poverty_rate_pct.transform(
        "median"
    )
    view = view.sort_values(keys).reset_index(drop=True)

    n_by_cluster = {
        int(code): int(size) for code, size in view.groupby("pred_cluster").size().items()
    }
    noise_by_year = {
        int(year): int(size)
        for year, size in view.loc[view.pred_cluster.eq(-1)].groupby("year").size().items()
    }
    counts = {
        "overlap_years": [int(year) for year in overlap_years],
        "pov_only_years": sorted(poverty_years - assignment_years),
        "label_only_years": sorted(assignment_years - poverty_years),
        "window_cells": int(len(window)),
        "valid_cells": int(len(valid)),
        "missing_source_cells": missing_source.sort_values(keys).to_dict("records"),
        "no_label_cells": no_label.sort_values(keys).to_dict("records"),
        "panel_rows": int(len(view)),
        "clusters": sorted(n_by_cluster),
        "n_by_cluster": n_by_cluster,
        "noise_by_year": noise_by_year,
    }
    return view, counts


def format_poverty_window(years: list[int]) -> str:
    """'2012–2016 & 2020–2024' — chạy năm liên tiếp, cùng quy ước fmt_window
    của scripts/poverty_validation.py:92."""
    years = [int(year) for year in years]
    if not years:
        raise DashboardDataError("Danh sách năm cửa sổ giao rỗng.")
    runs: list[tuple[int, int]] = []
    start = prev = years[0]
    for year in years[1:]:
        if year == prev + 1:
            prev = year
            continue
        runs.append((start, prev))
        start = prev = year
    runs.append((start, prev))
    singles = [str(a) for a, b in runs if a == b]
    spans = [f"{a}–{b}" for a, b in runs if b > a]
    return " & ".join(([", ".join(singles)] if singles else []) + spans)


def poverty_cluster_tests(view: pd.DataFrame, value_col: str = "poverty_rate_pct") -> dict:
    """One-way ANOVA + Kruskal–Wallis + eta² trên một cột poverty đã nối nhãn.

    Cùng estimator với `external_pci_tests` (scipy `f_oneway`, `kruskal`,
    eta² = SS giữa / SS tổng). Gọi HAI lần — `poverty_rate_pct` (gộp thô) và
    `pov_dm` (đã-trừ-median-năm) — và hai kết quả phải hiển thị CÙNG nhau:
    test gộp thô nhiễm hiệu ứng năm vì chuẩn nghèo đổi giai đoạn và tỷ trọng
    cụm trôi theo năm.
    """
    if value_col not in view.columns:
        raise DashboardDataError(
            f"Poverty view thiếu cột giá trị '{value_col}' — cột pov_dm chỉ có "
            "trong view sinh bởi prepare_poverty_cluster_view."
        )
    if view[value_col].isna().any():
        raise DashboardDataError("Poverty view còn ô thiếu giá trị — không đưa vào kiểm định.")
    groups = [sub[value_col].to_numpy() for _, sub in view.groupby("pred_cluster")]
    if len(groups) < 2:
        raise DashboardDataError("Kiểm định poverty cần ít nhất 2 nhóm cụm.")
    f_stat, p_anova = stats.f_oneway(*groups)
    h_stat, p_kw = stats.kruskal(*groups)
    grand = view[value_col].to_numpy()
    ss_total = float(((grand - grand.mean()) ** 2).sum())
    ss_between = float(sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in groups))
    return {
        "f": float(f_stat),
        "p_anova": float(p_anova),
        "df1": len(groups) - 1,
        "df2": len(view) - len(groups),
        "h": float(h_stat),
        "p_kw": float(p_kw),
        "eta_sq": ss_between / ss_total if ss_total > 0 else float("nan"),
        "n": int(len(view)),
    }


def poverty_noise_vs_c2(view: pd.DataFrame, value_col: str = "poverty_rate_pct") -> dict:
    """Mann–Whitney hai phía nhiễu (−1) vs cụm 2 — cặp tương phản đáng tin
    duy nhất (cụm 0 và cụm 1 quá nhỏ; đối xứng cảnh báo PCI trong
    external_validation.py)."""
    noise = view.loc[view.pred_cluster.eq(-1), value_col].to_numpy()
    cluster2 = view.loc[view.pred_cluster.eq(2), value_col].to_numpy()
    if not len(noise) or not len(cluster2):
        raise DashboardDataError("Thiếu nhóm nhiễu hoặc cụm 2 cho Mann–Whitney poverty.")
    u_stat, p_value = stats.mannwhitneyu(noise, cluster2)  # hai phía (mặc định scipy)
    return {"u": float(u_stat), "p": float(p_value), "n": int(len(noise) + len(cluster2))}
