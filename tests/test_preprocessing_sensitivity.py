"""Kiểm thử scripts/preprocessing_sensitivity.py."""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.papi_pred_common import REGRESSION_FEATURES, load_panel
from scripts.preprocessing_sensitivity import (
    CSV_COLUMNS,
    PUBLISHED_GATE,
    TrainFoldWinsorizer,
    build_regression_pairs_keep_missing,
    run_sensitivity,
    verify_published_gate,
)
from scripts.predict_supervised import (
    CLASSIFICATION_CV_FIRST_YEAR,
    HOLDOUT_YEAR,
    build_regression_pairs,
    expanding_origin_folds,
)


def test_variant_a_reproduces_published_gate():
    frame = run_sensitivity()
    assert verify_published_gate(frame)
    for (task, model, variant), expected in PUBLISHED_GATE.items():
        row = frame[
            (frame.task == task) & (frame.model == model) & (frame.variant == variant)
        ].iloc[0]
        assert float(row["value_cv"]) == expected


def test_imputer_fits_train_fold_only():
    df = load_panel()
    pairs = build_regression_pairs(df)
    train = pairs[pairs.year_t < HOLDOUT_YEAR]
    X = train[REGRESSION_FEATURES].to_numpy(dtype=float)
    y = train["y"].to_numpy(dtype=float)
    reg_cv = expanding_origin_folds(
        train["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
    )
    train_idx, val_idx = reg_cv[0]
    X_train_fold = X[train_idx]
    pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
        ]
    )
    pipe.fit(X_train_fold, y[train_idx])
    train_medians = pipe.named_steps["impute"].statistics_.copy()
    # Thêm giá trị cực đoan chỉ ở validation — median train không được đổi.
    X_spy = X.copy()
    if val_idx.size > 0:
        X_spy[val_idx, 0] = 1e6
    pipe2 = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
        ]
    )
    pipe2.fit(X_spy[train_idx], y[train_idx])
    assert np.allclose(pipe2.named_steps["impute"].statistics_, train_medians)


def test_winsorizer_uses_train_bounds_only():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 4))
    train_idx = np.arange(30)
    val_idx = np.arange(30, 40)
    w = TrainFoldWinsorizer(z=3.0)
    w.fit(X[train_idx])
    X_val = X[val_idx].copy()
    X_val[0, 0] = 1e6
    clipped = w.transform(X_val)
    assert clipped[0, 0] <= w.upper_[0] + 1e-9
    assert clipped[0, 0] >= w.lower_[0] - 1e-9


def test_gridsearch_imputer_fold_median_excludes_validation_rows():
    """Median imputer trong CV fold 0 không được ảnh hưởng bởi giá trị validation."""
    df = load_panel()
    pairs = build_regression_pairs_keep_missing(df)
    train = pairs[pairs.year_t < HOLDOUT_YEAR]
    X = train[REGRESSION_FEATURES].to_numpy(dtype=float)
    reg_cv = expanding_origin_folds(
        train["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
    )
    train_idx, val_idx = reg_cv[0]
    assert val_idx.size > 0
    baseline = SimpleImputer(strategy="median").fit(X[train_idx]).statistics_
    X_poisoned = X.copy()
    X_poisoned[val_idx] = 9_999.0
    poisoned = SimpleImputer(strategy="median").fit(X_poisoned[train_idx]).statistics_
    assert np.allclose(baseline, poisoned)


def test_csv_schema_after_run(tmp_path, monkeypatch):
    mod = importlib.import_module("scripts.preprocessing_sensitivity")
    tmp_csv = tmp_path / "preprocessing_sensitivity.csv"
    tmp_md = tmp_path / "preprocessing_sensitivity.md"
    monkeypatch.setattr(mod, "CSV_PATH", tmp_csv)
    monkeypatch.setattr(mod, "MD_PATH", tmp_md)
    monkeypatch.setattr(mod, "RESULTS", tmp_path)
    rc = mod.main()
    assert rc == 0
    assert tmp_csv.is_file()
    assert tmp_md.is_file()
    frame = pd.read_csv(tmp_csv)
    assert list(frame.columns) == list(CSV_COLUMNS)
    assert len(frame) == 3 + 2 * 3  # ridge + (LR, GNB) × 3 variants


def test_determinism_two_runs_identical_csv(tmp_path):
    out_a = tmp_path / "a.csv"
    out_b = tmp_path / "b.csv"

    def run_to(path: Path) -> str:
        frame = run_sensitivity()
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    h1 = run_to(out_a)
    h2 = run_to(out_b)
    assert h1 == h2


def test_variant_b_has_more_pairs_than_a():
    df = load_panel()
    na = len(build_regression_pairs(df).query(f"year_t < {HOLDOUT_YEAR}"))
    nb = len(build_regression_pairs_keep_missing(df).query(f"year_t < {HOLDOUT_YEAR}"))
    assert nb >= na
    assert nb > na
