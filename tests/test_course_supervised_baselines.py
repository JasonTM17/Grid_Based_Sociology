"""Kiểm thử nhanh cho scripts/course_supervised_baselines.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix

from scripts.course_supervised_baselines import (
    COURSE_MODELS,
    MODEL_MAJORITY,
    _classification_pairs,
    build_metrics_table,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, load_config, load_panel, select_model_by_cv
from scripts.predict_supervised import HOLDOUT_YEAR

REQUIRED_COLUMNS = (
    "model",
    "metric_cv",
    "value_cv",
    "holdout_acc",
    "holdout_macro_f1",
)


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
    metrics, grids, yte, Xte = build_metrics_table(
        pairs=real_classification_pairs
    )
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
    selectable = metrics[~metrics.model.isin([MODEL_MAJORITY])]
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
    assert (root / "results" / "course_supervised_baselines.md").is_file()
    assert (root / "results" / "figs" / "course_confusion_matrix.png").is_file()
