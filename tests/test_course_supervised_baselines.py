"""Kiểm thử nhanh cho scripts/course_supervised_baselines.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix

from scripts.course_supervised_baselines import (
    BALANCED_SENSITIVITY_BASE_MODELS,
    COURSE_MODELS,
    GROUP_PRIMARY,
    GROUP_SENSITIVITY,
    MODEL_MAJORITY,
    SENSITIVITY_LABEL,
    _classification_pairs,
    _fit_balanced_sensitivity_grids,
    _fit_grids,
    build_metrics_table,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, load_config, load_panel, select_model_by_cv
from scripts.predict_supervised import (
    CLASSIFICATION_CV_YEARS,
    HOLDOUT_YEAR,
    SEED,
    expanding_year_splits,
)

REQUIRED_COLUMNS = (
    "model",
    "metric_cv",
    "value_cv",
    "holdout_acc",
    "holdout_macro_f1",
)

BASELINE_CSV_COLUMNS = (
    *REQUIRED_COLUMNS,
    "cv_std",
    "cv_folds",
)

PRIMARY_VALUE_CV_ROUNDED = {
    "gaussian naive bayes": 0.514,
    "knn": 0.486,
    "svm (linear)": 0.343,
    "svm (rbf)": 0.437,
    "decision tree": 0.426,
    "random forest": 0.394,
}


def _synthetic_pairs(n_prov: int = 16, seed: int = 0) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    for year in range(2011, HOLDOUT_YEAR + 1):
        for pc in range(1, n_prov + 1):
            row: dict[str, object] = {
                "year_t": year,
                "y": int(rng.random() > 0.35 + 0.03 * (year - 2011)),
            }
            for feat in REGRESSION_FEATURES:
                row[feat] = float(rng.normal(loc=year * 0.01 + pc * 0.02))
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def real_classification_pairs():
    """Cặp STING thật — build một lần mỗi phiên pytest (cache trong script)."""
    cfg = load_config()
    df = load_panel()
    return _classification_pairs(df, cfg)


@pytest.fixture(scope="module")
def baseline_run(real_classification_pairs):
    """Giống script chính: 50 cây RF, cặp STING đã cache qua real_classification_pairs."""
    del real_classification_pairs  # chỉ warmup _PAIRS_CACHE
    cfg = load_config()
    df = load_panel()
    metrics, grids, yte, Xte = build_metrics_table(df, cfg)
    return metrics, grids, yte, Xte


def test_determinism_same_seed_same_table():
    pairs = _synthetic_pairs()
    metrics_a, *_ = build_metrics_table(pairs=pairs.copy())
    metrics_b, *_ = build_metrics_table(pairs=pairs.copy())
    pd.testing.assert_frame_equal(
        metrics_a.reset_index(drop=True),
        metrics_b.reset_index(drop=True),
        check_exact=False,
        rtol=0,
        atol=0,
    )


def test_schema_no_nan(baseline_run):
    metrics, _, _, _ = baseline_run
    for col in REQUIRED_COLUMNS:
        assert col in metrics.columns, f"thiếu cột {col}"
    assert not metrics[list(REQUIRED_COLUMNS)].isna().any().any()


def test_confusion_matrix_totals_equal_holdout(baseline_run):
    _, grids, yte, Xte = baseline_run
    n_holdout = yte.size
    for name in COURSE_MODELS:
        yp = grids[name].best_estimator_.predict(Xte)
        cm = confusion_matrix(yte, yp, labels=[0, 1])
        assert int(cm.sum()) == n_holdout, name


def test_model_selection_uses_cv_only(baseline_run):
    metrics, _, _, _ = baseline_run
    primary = metrics[metrics["group"] == GROUP_PRIMARY]
    selectable = primary[~primary.model.isin([MODEL_MAJORITY])]
    chosen = select_model_by_cv(selectable)

    tampered = selectable.copy()
    tampered["holdout_macro_f1"] = 0.0
    tampered["holdout_acc"] = 0.0
    assert select_model_by_cv(tampered) == chosen


def test_scaler_not_fitted_on_holdout(baseline_run):
    _, grids, _, Xte = baseline_run
    holdout_means = Xte.mean(axis=0)
    for name in COURSE_MODELS:
        est = grids[name].best_estimator_
        if not hasattr(est, "named_steps") or "sc" not in est.named_steps:
            continue
        sc = est.named_steps["sc"]
        train_means = sc.mean_
        assert not np.allclose(train_means, holdout_means, rtol=0.05, atol=0.05), (
            f"{name}: scaler mean trùng holdout — có thể fit nhầm"
        )


def test_artifacts_on_disk():
    from scripts import course_supervised_baselines as mod

    root = mod.ROOT
    assert (root / "results" / "course_supervised_baselines.csv").is_file()
    assert (root / "results" / "course_supervised_sensitivity.csv").is_file()
    assert (root / "results" / "course_supervised_baselines.md").is_file()
    assert (root / "results" / "figs" / "course_confusion_matrix.png").is_file()


def test_expanding_splits_train_years_strictly_before_validation(
    real_classification_pairs,
):
    train = real_classification_pairs[real_classification_pairs.year_t < HOLDOUT_YEAR]
    years = train["year_t"].to_numpy()
    ytr = train["y"].to_numpy()
    splits = expanding_year_splits(years, ytr)
    assert len(splits) == len(CLASSIFICATION_CV_YEARS)
    for validation_year, (train_idx, validation_idx) in zip(
        CLASSIFICATION_CV_YEARS, splits, strict=True
    ):
        assert np.all(years[train_idx] < validation_year)
        assert set(years[validation_idx].tolist()) == {validation_year}


def test_primary_csv_matches_head_content():
    from scripts import course_supervised_baselines as mod

    repo_root = Path(mod.ROOT)
    diff = subprocess.run(
        ["git", "diff", "--", "results/course_supervised_baselines.csv"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == "", "course_supervised_baselines.csv phải khớp HEAD"
    on_disk = pd.read_csv(repo_root / "results" / "course_supervised_baselines.csv")
    assert list(on_disk.columns) == list(BASELINE_CSV_COLUMNS)
    assert len(on_disk) == 8


def test_primary_csv_matches_fresh_computation(baseline_run):
    from scripts import course_supervised_baselines as mod

    metrics, _, _, _ = baseline_run
    on_disk = pd.read_csv(mod.ROOT / "results" / "course_supervised_baselines.csv")
    primary_fresh = metrics[metrics["group"] == GROUP_PRIMARY]
    pd.testing.assert_frame_equal(
        on_disk[list(BASELINE_CSV_COLUMNS)].reset_index(drop=True),
        primary_fresh[list(BASELINE_CSV_COLUMNS)].reset_index(drop=True),
        check_exact=True,
    )


def test_sensitivity_csv_has_three_rows_and_no_group_column(baseline_run):
    from scripts import course_supervised_baselines as mod

    metrics, _, _, _ = baseline_run
    sens_path = mod.ROOT / "results" / "course_supervised_sensitivity.csv"
    on_disk = pd.read_csv(sens_path)
    assert "group" not in on_disk.columns
    assert len(on_disk) == 3
    sens_fresh = metrics[metrics["group"] == GROUP_SENSITIVITY]
    pd.testing.assert_frame_equal(
        on_disk[list(BASELINE_CSV_COLUMNS)].reset_index(drop=True),
        sens_fresh[list(BASELINE_CSV_COLUMNS)].reset_index(drop=True),
        check_exact=True,
    )


def test_sensitivity_rows_exist_and_count(baseline_run):
    metrics, _, _, _ = baseline_run
    assert "group" in metrics.columns
    sens = metrics[metrics["group"] == GROUP_SENSITIVITY]
    assert len(sens) == 3
    for _, row in sens.iterrows():
        assert SENSITIVITY_LABEL in row["model"]


def test_primary_value_cv_unchanged(baseline_run):
    metrics, _, _, _ = baseline_run
    primary = metrics[metrics["group"] == GROUP_PRIMARY]
    for model, expected in PRIMARY_VALUE_CV_ROUNDED.items():
        row = primary.loc[primary["model"] == model].iloc[0]
        assert round(float(row["value_cv"]), 3) == expected, model


def test_sensitivity_model_selection_uses_cv_only(baseline_run):
    metrics, _, _, _ = baseline_run
    sens = metrics[metrics["group"] == GROUP_SENSITIVITY]
    chosen = select_model_by_cv(sens)
    tampered = sens.copy()
    tampered["holdout_macro_f1"] = 0.0
    tampered["holdout_acc"] = 0.0
    assert select_model_by_cv(tampered) == chosen


def test_cv_std_non_negative_finite(baseline_run):
    metrics, _, _, _ = baseline_run
    assert "cv_std" in metrics.columns and "cv_folds" in metrics.columns
    for _, row in metrics.iterrows():
        folds = int(row["cv_folds"])
        assert folds == len(CLASSIFICATION_CV_YEARS)
        std = float(row["cv_std"])
        assert np.isfinite(std) and std >= 0.0, row["model"]


def _grid_classifier(grid):
    est = grid.estimator
    if hasattr(est, "named_steps"):
        return est.named_steps["clf"]
    return est


def _pipeline_step_names(grid) -> list[str] | None:
    est = grid.estimator
    if not hasattr(est, "steps"):
        return None
    return [name for name, _ in est.steps]


def _cv_index_splits(cv) -> list[tuple[np.ndarray, np.ndarray]]:
    if isinstance(cv, list):
        return [(np.asarray(a), np.asarray(b)) for a, b in cv]
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for train_idx, val_idx in cv.split(np.zeros(1)):
        splits.append((np.asarray(train_idx), np.asarray(val_idx)))
    return splits


def _assert_same_cv_splits(cv_a, cv_b, *, label: str) -> None:
    splits_a = _cv_index_splits(cv_a)
    splits_b = _cv_index_splits(cv_b)
    assert len(splits_a) == len(splits_b) == len(CLASSIFICATION_CV_YEARS), label
    for fold, ((ta, va), (tb, vb)) in enumerate(
        zip(splits_a, splits_b, strict=True)
    ):
        np.testing.assert_array_equal(ta, tb, err_msg=f"{label} fold {fold} train")
        np.testing.assert_array_equal(va, vb, err_msg=f"{label} fold {fold} val")


def test_sensitivity_grids_match_primary_except_class_weight(real_classification_pairs):
    """Primary và nhạy cảm: cùng CV/lưới/Pipeline; chỉ khác class_weight='balanced'."""
    train = real_classification_pairs[real_classification_pairs.year_t < HOLDOUT_YEAR]
    Xtr = train[REGRESSION_FEATURES].to_numpy()
    ytr = train["y"].to_numpy()
    clf_cv = expanding_year_splits(train["year_t"].to_numpy(), ytr)
    rf_n_estimators = 50

    primary = _fit_grids(Xtr, ytr, clf_cv, rf_n_estimators=rf_n_estimators)
    sensitivity = _fit_balanced_sensitivity_grids(
        Xtr, ytr, clf_cv, rf_n_estimators=rf_n_estimators
    )

    for name in BALANCED_SENSITIVITY_BASE_MODELS:
        p_grid = primary[name]
        s_grid = sensitivity[name]

        _assert_same_cv_splits(clf_cv, p_grid.cv, label=f"{name} primary cv")
        _assert_same_cv_splits(clf_cv, s_grid.cv, label=f"{name} sensitivity cv")
        _assert_same_cv_splits(p_grid.cv, s_grid.cv, label=name)

        assert p_grid.param_grid == s_grid.param_grid, name

        p_steps = _pipeline_step_names(p_grid)
        s_steps = _pipeline_step_names(s_grid)
        assert p_steps == s_steps, name
        if p_steps is not None:
            assert p_steps == ["sc", "clf"], name

        p_clf = _grid_classifier(p_grid)
        s_clf = _grid_classifier(s_grid)

        if "random forest" in name:
            assert p_clf.n_estimators == s_clf.n_estimators == rf_n_estimators, name
            assert p_clf.random_state == s_clf.random_state == SEED, name

        p_params = p_clf.get_params(deep=False)
        s_params = s_clf.get_params(deep=False)
        differing = sorted(
            k for k in set(p_params) | set(s_params) if p_params.get(k) != s_params.get(k)
        )
        assert differing == ["class_weight"], (name, differing)
        assert p_params.get("class_weight") is None
        assert s_params["class_weight"] == "balanced"
