"""Unit tests & time-safety invariants for scripts/supervised/regression_deep_analysis.py."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.common.papi_pred_common import ROOT, load_config
from scripts.supervised import regression_deep_analysis as study


def test_conformal_quantile_finite_sample_and_validation():
    errs = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    # ceil((10 + 1) * 0.80) = ceil(8.8) = 9 -> 9th value = 0.9
    assert study.conformal_quantile(errs, alpha=0.20) == pytest.approx(0.9)
    with pytest.raises(ValueError):
        study.conformal_quantile(np.array([]), alpha=0.10)
    with pytest.raises(ValueError):
        study.conformal_quantile(errs, alpha=1.2)


def test_compute_vif_table_detects_orthogonality_and_collinearity():
    rng = np.random.default_rng(7)
    x1 = rng.normal(size=120)
    x2 = rng.normal(size=120)
    x3 = 0.9 * x1 + 0.1 * rng.normal(size=120)
    vif = study.compute_vif_table(np.column_stack([x1, x2, x3]), ["f1", "f2", "f3"])
    assert vif.loc[vif["feature"] == "f2", "vif"].iloc[0] < 1.2
    assert vif.loc[vif["feature"] == "f1", "vif"].iloc[0] > 4.0
    assert vif.loc[vif["feature"] == "f3", "vif"].iloc[0] > 4.0


def test_paired_mae_comparison_zero_and_improvement():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    eq = study.paired_mae_comparison(y, y + 0.2, y + 0.2, n_boot=100, seed=5)
    assert eq["mean_diff"] == pytest.approx(0.0)
    assert eq["wilcoxon_p"] == pytest.approx(1.0)

    better = study.paired_mae_comparison(y, y + 0.05, y + 0.30, n_boot=200, seed=5)
    assert better["mean_diff"] == pytest.approx(-0.25)
    assert better["improved_count"] == 6
    assert better["ci95_hi"] < 0.0


def _stage_tree(dest, panel_df: pd.DataFrame) -> None:
    (dest / "data/processed").mkdir(parents=True)
    (dest / "models").mkdir(parents=True)
    (dest / "results").mkdir(parents=True)
    panel_df.to_csv(dest / "data/processed/papi_panel_63_2011_2024.csv", index=False)
    (dest / "models/predict_config.json").write_text(
        (ROOT / "models/predict_config.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (dest / "data/processed/external_gso_population_63_full.csv").write_text(
        (ROOT / "data/processed/external_gso_population_63_full.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def test_deep_regression_selection_and_conformal_do_not_leak_2024_targets(monkeypatch, tmp_path):
    panel = pd.read_csv(ROOT / "data/processed/papi_panel_63_2011_2024.csv")
    perturbed = panel.copy()
    perturbed.loc[perturbed["year"] == 2024, "sd_6_1"] += 5.0

    # Stage both trees through identical CSV serialization on <=2023 rows so float formatting matches.
    base_dir = tmp_path / "base"
    tampered_dir = tmp_path / "tampered"
    _stage_tree(base_dir, panel)
    _stage_tree(tampered_dir, perturbed)

    monkeypatch.setattr(study, "load_config", lambda: load_config())
    baseline = study.run_study(base_dir, write_outputs=False)
    tampered = study.run_study(tampered_dir, write_outputs=False)

    np.testing.assert_allclose(
        baseline["models"]["cv_r2_raw"].to_numpy(),
        tampered["models"]["cv_r2_raw"].to_numpy(),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        baseline["coef_vif"]["beta_ridge"].to_numpy(),
        tampered["coef_vif"]["beta_ridge"].to_numpy(),
        atol=1e-12,
    )
    assert baseline["conformal_summary"]["q90_oof_radius"] == pytest.approx(
        tampered["conformal_summary"]["q90_oof_radius"], abs=1e-12
    )
    assert baseline["conformal_summary"]["train_fence"] == pytest.approx(
        tampered["conformal_summary"]["train_fence"], abs=1e-12
    )


def test_published_deep_regression_artifacts_and_excel_sheet_exist():
    import openpyxl

    deep_csv = ROOT / "results/regression_deep_analysis.csv"
    conf_csv = ROOT / "results/regression_conformal_2024.csv"
    fig = ROOT / "results/figs/regression_diagnostics_deep.png"
    xlsx = ROOT / "results/KetQua_STING_PAPI.xlsx"

    assert deep_csv.is_file() and deep_csv.stat().st_size > 500
    assert conf_csv.is_file() and len(pd.read_csv(conf_csv)) == 59
    assert fig.is_file() and fig.stat().st_size > 10_000

    wb = openpyxl.load_workbook(xlsx, read_only=True)
    assert "Hồi quy chuyên sâu" in wb.sheetnames
    wb.close()
