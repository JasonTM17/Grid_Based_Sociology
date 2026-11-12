"""Kiểm thử scripts/classifier_label_baselines.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts.classifier_label_baselines import (
    CSV_COLUMNS,
    N_PERMUTATIONS,
    PUBLISHED_CV,
    TARGET_MODELS,
    build_long_table,
    csv_sha256,
    shuffled_train_labels_cv,
)
from scripts.course_supervised_baselines import (
    MODEL_GAUSSIAN_NB,
    _classification_pairs,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, load_config, load_panel
from scripts.predict_supervised import HOLDOUT_YEAR, expanding_year_splits

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "results" / "classifier_label_baselines.csv"


@pytest.fixture(scope="module")
def full_table():
    return build_long_table(n_perm=N_PERMUTATIONS)


def test_reproduction_gate_matches_published(full_table):
    pub = full_table[
        (full_table.analysis == "published_cv") & (full_table.metric == "value_cv")
    ]
    for model, expected in PUBLISHED_CV.items():
        got = round(float(pub.loc[pub.model == model].iloc[0]["value"]), 3)
        assert got == expected, model


def test_csv_schema(full_table):
    assert list(full_table.columns) == list(CSV_COLUMNS)
    assert not full_table[["analysis", "model", "metric", "value"]].isna().any().any()
    for model in TARGET_MODELS:
        n_pub = (
            (full_table.analysis == "published_cv")
            & (full_table.model == model)
            & (full_table.metric == "value_cv")
        ).sum()
        assert n_pub == 1


def test_determinism_identical_csv_hash():
    a = build_long_table(n_perm=8)
    b = build_long_table(n_perm=8)
    assert csv_sha256(a) == csv_sha256(b)


def test_permutation_does_not_mutate_validation_labels():
    cfg = load_config()
    df = load_panel()
    pairs = _classification_pairs(df, cfg)
    train = pairs[pairs.year_t < HOLDOUT_YEAR]
    Xtr = train[REGRESSION_FEATURES].to_numpy()
    ytr = train["y"].to_numpy(dtype=int)
    y_snapshot = ytr.copy()
    splits = expanding_year_splits(train["year_t"].to_numpy(), ytr)
    from scripts.course_supervised_baselines import _fit_grids

    grids = _fit_grids(Xtr, ytr, splits, rf_n_estimators=50)
    shuffled_train_labels_cv(
        Xtr,
        ytr,
        splits,
        MODEL_GAUSSIAN_NB,
        grids,
        n_perm=3,
        base_seed=99,
    )
    np.testing.assert_array_equal(ytr, y_snapshot)
    for _, val_idx in splits:
        np.testing.assert_array_equal(ytr[val_idx], y_snapshot[val_idx])


def test_script_main_reproduction_gate(tmp_path):
    env = dict(os.environ)
    env["CLASSIFIER_LABEL_BASELINES_DIR"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-W", "error", "scripts/classifier_label_baselines.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert (tmp_path / "classifier_label_baselines.csv").is_file()
    assert (tmp_path / "classifier_label_baselines.md").is_file()


def test_artifacts_on_disk():
    assert OUT_CSV.is_file()
    md = ROOT / "results" / "classifier_label_baselines.md"
    assert md.is_file()
