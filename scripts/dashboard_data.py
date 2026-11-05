"""Read-only data preparation for the local PAPI Streamlit dashboard."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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
