"""Unit, invariant, and time-safety tests for high-dimensional STING extensions."""
from __future__ import annotations

import numpy as np
import openpyxl
import pandas as pd
import pytest

from scripts.analysis import high_dim_sting as study
from scripts.common.papi_pred_common import REGRESSION_FEATURES, ROOT
from src.high_dim import (
    QuantileSTING,
    QuantileWarper,
    SubspaceCLIQUE,
    high_dim_sparsity_grid,
)


def test_quantile_warper_and_quantile_sting_support_and_validation():
    rng = np.random.default_rng(12)
    c0 = rng.normal(loc=-2.0, scale=0.35, size=(60, 3))
    c1 = rng.normal(loc=+2.0, scale=0.35, size=(60, 3))
    X = np.vstack([c0, c1])

    warper = QuantileWarper.fit(X)
    w_train, ok_train = warper.transform(X)
    assert ok_train.all()
    assert w_train.min() >= 0.0 and w_train.max() <= 1.0

    # Constant feature column should not divide by zero or fail
    X_const = np.column_stack([X[:, :2], np.full(len(X), 5.0)])
    q_const = QuantileSTING(n_levels=3, factor=2, density_multiplier=1.5, density_level=1).fit(X_const)
    lbl_const = q_const.cluster(level=1)
    assert len(lbl_const) == len(X_const)
    assert q_const.effective_min_count_ >= 3

    model = QuantileSTING(n_levels=3, factor=2, density_multiplier=2.0, density_level=1).fit(X)
    labels = model.cluster(level=1)
    assert model.n_clusters_ >= 2
    assert set(labels.tolist()) - {-1} <= set(range(model.n_clusters_))

    # Predicting on training points stays deterministic; far outside support returns -1
    preds_train = model.predict(X)
    np.testing.assert_array_equal(preds_train, labels)

    outliers = np.array([[50.0, 50.0, 50.0], [-50.0, -50.0, -50.0]])
    np.testing.assert_array_equal(model.predict(outliers), np.array([-1, -1]))

    # Asymmetric ties must not distort [0, 1] quantile split boundaries
    X_asym = np.column_stack([
        np.concatenate([np.zeros(1), np.full(45, 0.2), np.full(4, 0.3), np.ones(50)]),
        np.linspace(0.0, 1.0, 100),
    ])
    q_asym = QuantileSTING(n_levels=2, factor=2, min_count=5).fit(X_asym)
    w_probe, _ = q_asym.warper_.transform(np.array([[0.3, 0.5]]))
    idx_probe, _ = q_asym.sting_._assign(w_probe, 2)
    assert w_probe[0, 0] < 0.5 and int(idx_probe[0, 0]) == 0

    with pytest.raises(ValueError):
        QuantileWarper.fit(np.empty((0, 3)))
    with pytest.raises(ValueError):
        QuantileSTING(n_levels=3, factor=2, min_count=2).fit(np.array([[1.0, np.nan]]))
    with pytest.raises(RuntimeError):
        QuantileSTING().cluster()


def test_subspace_clique_downward_closure_separation_and_prediction():
    rng = np.random.default_rng(7)
    n_per = 45
    # Dims (1, 3) have two sharp separated regimes; dims 0, 2, 4 are diffuse noise
    X = rng.uniform(-1.0, 1.0, size=(2 * n_per + 20, 5))
    X[:n_per, 1] = rng.normal(-0.75, 0.08, size=n_per)
    X[:n_per, 3] = rng.normal(-0.75, 0.08, size=n_per)
    X[n_per : 2 * n_per, 1] = rng.normal(+0.75, 0.08, size=n_per)
    X[n_per : 2 * n_per, 3] = rng.normal(+0.75, 0.08, size=n_per)

    for adapt in (False, True):
        clq = SubspaceCLIQUE(n_bins=4, tau=0.12, adaptive=adapt).fit(X)
        assert (1, 3) in clq.discovered_subspaces(min_dim=2)

        # Apriori downward closure: every dense k-unit has all (k-1)-projections in levels_[k-1]
        for k_dim, level_units in clq.levels_.items():
            if k_dim < 2:
                continue
            prev_units = clq.levels_[k_dim - 1]
            for dims, coords in level_units:
                for drop in range(k_dim):
                    sub_d = dims[:drop] + dims[drop + 1 :]
                    sub_c = coords[:drop] + coords[drop + 1 :]
                    assert (sub_d, sub_c) in prev_units

        info = clq.extract_subspace((1, 3))
        assert info["n_clusters"] == 2
        assert info["silhouette"] > 0.70
        # Unsorted dims must canonicalize identically instead of silently returning empty
        info_rev = clq.extract_subspace((3, 1))
        assert info_rev["dims"] == (1, 3)
        np.testing.assert_array_equal(info_rev["labels"], info["labels"])

        holdout = np.zeros((3, 5))
        holdout[0, [1, 3]] = [-0.75, -0.75]
        holdout[1, [1, 3]] = [+0.75, +0.75]
        holdout[2, [1, 3]] = [99.0, 99.0]  # out of bounds -> -1
        pred = clq.predict_subspace((1, 3), holdout)
        assert pred[0] in (0, 1) and pred[1] in (0, 1) and pred[0] != pred[1]
        assert pred[2] == -1
        np.testing.assert_array_equal(clq.predict_subspace((3, 1), holdout), pred)

        with pytest.raises(ValueError):
            clq.extract_subspace((1, 1))
        with pytest.raises(ValueError):
            clq.extract_subspace((0, 99))

    # Scale-aware edge handling under tiny range (1e-10) and huge constant (1e16)
    X_tiny = np.column_stack([np.concatenate([np.zeros(90), np.full(10, 1e-10)]), np.linspace(0, 1, 100)])
    clq_tiny = SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=True).fit(X_tiny)
    edges_tiny = clq_tiny.edges_[0][2]
    assert np.all(np.diff(edges_tiny) > 0)
    assert len(np.unique(clq_tiny.train_bins_[:, 0])) >= 2

    X_huge = np.column_stack([np.full(100, 1e16), np.linspace(0, 1, 100)])
    clq_huge = SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=True).fit(X_huge)
    assert np.all(np.diff(clq_huge.edges_[0][2]) > 0)
    assert np.all(clq_huge.train_bins_[:, 0] == 0)


def test_high_dim_sparsity_grid_guards_overflow_and_computes_metrics():
    rng = np.random.default_rng(99)
    X = rng.normal(size=(120, 8))
    rows = high_dim_sparsity_grid(X, dims_list=[2, 3, 8], n_levels=3, factor=4, min_count=5, level=2)
    assert len(rows) == 3
    assert rows[0]["skipped"] is False and 0.0 <= rows[0]["noise_ratio"] <= 1.0
    assert rows[2]["d"] == 8 and rows[2]["skipped"] is True
    with pytest.raises(ValueError):
        high_dim_sparsity_grid(X, dims_list=[2], n_levels=2, factor=2, min_count=5, level=2)


def _stage_high_dim_tree(dest, panel_df: pd.DataFrame) -> None:
    (dest / "data/processed").mkdir(parents=True)
    (dest / "results").mkdir(parents=True)
    panel_df.to_csv(dest / "data/processed/papi_panel_63_2011_2024.csv", index=False)
    for rel in (
        "results/predict_all_years.csv",
        "data/processed/external_pci_63_full.csv",
        "data/processed/external_gso_grdp_63.csv",
    ):
        (dest / rel).write_text((ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8")


def test_high_dim_study_does_not_leak_2024_data(tmp_path):
    panel = pd.read_csv(ROOT / "data/processed/papi_panel_63_2011_2024.csv")
    perturbed = panel.copy()
    mask_2024 = perturbed["year"] == 2024
    for col in [*REGRESSION_FEATURES, *[f"d{i}" for i in range(1, 9)]]:
        perturbed.loc[mask_2024, col] = perturbed.loc[mask_2024, col] + 5.0

    base_dir = tmp_path / "base"
    tampered_dir = tmp_path / "tampered"
    _stage_high_dim_tree(base_dir, panel)
    _stage_high_dim_tree(tampered_dir, perturbed)

    base = study.run_study(base_dir, write_outputs=False)
    tampered = study.run_study(tampered_dir, write_outputs=False)

    # Strict <=2023 training splits (sparsity_ladder, feature_selection, subspace_clique, screened/time-split quantile)
    # must stay completely unchanged when unseen 2024 holdout values are shifted out of range.
    train_only_mask = (
        base["summary"]["dataset"].str.contains("<=2023")
        | base["summary"]["dataset"].eq("8D d1..d8 2018–2023")
    )
    b_train = base["summary"].loc[train_only_mask].reset_index(drop=True)
    t_train = tampered["summary"].loc[train_only_mask].reset_index(drop=True)

    np.testing.assert_array_equal(b_train["n_clusters"].to_numpy(), t_train["n_clusters"].to_numpy())
    np.testing.assert_allclose(b_train["noise_ratio"].to_numpy(), t_train["noise_ratio"].to_numpy(), atol=1e-12)
    np.testing.assert_allclose(
        b_train["silhouette_orig"].fillna(-999.0).to_numpy(),
        t_train["silhouette_orig"].fillna(-999.0).to_numpy(),
        atol=1e-12,
    )
    assert list(base["subspaces"]["features"]) == list(tampered["subspaces"]["features"])

    # Shifting 2024 points by +5.0 should reduce 2024 holdout assignment coverage
    q_idx = b_train.loc[b_train["method"] == "8D Quantile L=3 f=2 lv=1 mc=7 (2.2x exp)"].index[0]
    assert t_train.loc[q_idx, "holdout_2024_cov"] < b_train.loc[q_idx, "holdout_2024_cov"]

    # Non-noise edge clusters must not be folded into the noise label in ext_plot
    ep = base["ext_plot"]
    assert set(ep.loc[ep["cluster"] == -1, "regime_label"]) == {"Nhiễu (-1)"}
    assert "Nhiễu (-1)" not in set(ep.loc[ep["cluster"] >= 0, "regime_label"])


def test_published_high_dim_artifacts_and_excel_sheet_exist():
    csv_main = ROOT / "results/high_dim_sting.csv"
    csv_sub = ROOT / "results/high_dim_sting_subspaces.csv"
    md_path = ROOT / "results/high_dim_sting.md"
    fig_path = ROOT / "results/figs/high_dim_sting_analysis.png"
    xlsx_path = ROOT / "results/KetQua_STING_PAPI.xlsx"

    assert csv_main.is_file() and csv_main.stat().st_size > 1000
    assert csv_sub.is_file() and csv_sub.stat().st_size > 1000
    assert md_path.is_file() and md_path.stat().st_size > 1000
    assert fig_path.is_file() and fig_path.stat().st_size > 20_000

    df = pd.read_csv(csv_main)
    assert {"baseline_robustness", "sparsity_ladder", "feature_selection", "subspace_clique", "adaptive_quantile", "pca_followup"} <= set(df["section"])

    # No contradictory overflow verdict (e.g. claiming 6,561 > 10M) and f=3 lv=1 covers d=8
    overflow_rows = df.loc[df["verdict"].str.contains("Bùng nổ", na=False)]
    for _, row in overflow_rows.iterrows():
        assert "leaf=" in str(row["grid_spec"])
        leaf_count = int(str(row["grid_spec"]).split("leaf=")[1].replace(",", ""))
        assert leaf_count > 10_000_000
    row_res3_d8 = df.loc[df["method"] == "Thang thưa d=8 (f=3 lv=1 mc=10 (res=3))"].iloc[0]
    assert int(row_res3_d8["n_clusters"]) >= 1 and float(row_res3_d8["noise_ratio"]) < 1.0

    # No 1-cluster collapse may claim multi-cluster generalization
    for _, row in df.iterrows():
        if int(row["n_clusters"]) < 2:
            assert "Đa cụm" not in str(row["verdict"]) and "Tổng quát hóa" not in str(row["verdict"])

    row_q8 = df.loc[df["method"] == "8D Quantile L=3 f=2 lv=1 mc=7 (2.2x exp)"].iloc[0]
    assert int(row_q8["n_clusters"]) >= 2 and float(row_q8["noise_ratio"]) < 0.50

    row_wy = df.loc[df["method"] == "8D Quantile within-year z L=3 f=2 lv=1 mc=7"].iloc[0]
    assert int(row_wy["n_clusters"]) >= 2 and float(row_wy["ext_pci_dm_p"]) < 0.01

    row_d8_q = df.loc[df["method"] == "8D d1..d8 Quantile L=3 f=2 lv=1 mc=4"].iloc[0]
    assert float(row_d8_q["noise_ratio"]) < 0.50 and float(row_d8_q["silhouette_orig"]) > 0.0

    row_d8_ts = df.loc[df["method"] == "8D d1..d8 Quantile mc=5 (time-split -> 2024)"].iloc[0]
    assert int(row_d8_ts["n_clusters"]) >= 2 and float(row_d8_ts["silhouette_orig"]) > 0.0 and float(row_d8_ts["holdout_2024_cov"]) > 0.30

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    assert "STING đa chiều" in wb.sheetnames
    wb.close()
