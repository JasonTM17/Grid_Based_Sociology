"""Kiểm thử suy luận bảng CR1, Wild Cluster Bootstrap, TWFE, FDR đa chiều và chẩn đoán Moran's I."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.analysis.panel_inference import (
    adjust_multiple_testing,
    compute_spatial_morans_i,
    fit_fe_cluster_ols,
    paired_switcher_within_province,
    run_study,
)


def test_fwl_cr1_matches_full_design_ols_and_detects_cluster_inflation():
    """FWL CR1 khớp tuyệt đối ma trận đầy đủ và phát hiện lạm phát sai số i.i.d. dưới tương quan nội tỉnh."""
    rng = np.random.default_rng(123)
    g_clusters, n_years = 25, 10
    n_obs = g_clusters * n_years
    cluster_ids = np.repeat(np.arange(g_clusters), n_years)
    years = np.tile(np.arange(n_years), g_clusters)

    # Treatment invariant within clusters + strong cluster shock -> huge CR1 vs iid inflation!
    cl_treat = rng.integers(0, 2, size=g_clusters)
    d = cl_treat[cluster_ids].astype(float)
    cl_shock = rng.normal(0.0, 2.0, size=g_clusters)[cluster_ids]
    yr_effect = 0.4 * years
    y = 0.0 * d + yr_effect + cl_shock + rng.normal(0.0, 0.3, size=n_obs)

    yr_dum = pd.get_dummies(years, drop_first=True, dtype=float).to_numpy()
    Z = np.column_stack([np.ones(n_obs), yr_dum])
    res = fit_fe_cluster_ols(y, d[:, None], Z, cluster_ids, n_boot=399, seed=42)
    assert res is not None

    # Naive full matrix CR1 parity check
    X_full = np.column_stack([d, Z])
    beta_full = np.linalg.lstsq(X_full, y, rcond=None)[0]
    u_full = y - X_full @ beta_full
    xtx_inv = np.linalg.inv(X_full.T @ X_full)
    scores = np.zeros((g_clusters, X_full.shape[1]))
    np.add.at(scores, cluster_ids, X_full * u_full[:, None])
    c_cr1 = (g_clusters / (g_clusters - 1)) * ((n_obs - 1) / (n_obs - X_full.shape[1]))
    V_full = c_cr1 * xtx_inv @ (scores.T @ scores) @ xtx_inv

    assert res["beta"] == pytest.approx(float(beta_full[0]), abs=1e-11)
    assert res["se_cr1"] == pytest.approx(float(np.sqrt(V_full[0, 0])), abs=1e-11)
    assert res["se_inflation"] > 2.5
    assert res["p_cr1"] > 0.10
    assert res["p_wcr"] > 0.10


def test_year_fe_removes_time_composition_confounding():
    """Hiệu ứng giả do xu hướng thời gian biến mất hoàn toàn sau khi đưa Year-FE vào mô hình."""
    g_clusters, n_years = 30, 8
    rows = []
    rng = np.random.default_rng(7)
    for g in range(g_clusters):
        for t in range(n_years):
            # Treatment prevalence increases over time, outcome also increases over time, zero real effect!
            treated = 1 if (t >= 4 and (g + t) % 3 != 0) or (t < 4 and g % 5 == 0) else 0
            y = 1.2 * t + rng.normal(0.0, 0.4)
            rows.append({"province_code": g, "year": 2015 + t, "cluster": treated, "y": y})
    df = pd.DataFrame(rows)
    Z_yr = np.column_stack([np.ones(len(df)), pd.get_dummies(df["year"], drop_first=True, dtype=float).to_numpy()])
    D = df["cluster"].to_numpy(dtype=float)[:, None]
    res = fit_fe_cluster_ols(df["y"].to_numpy(), D, Z_yr, df["province_code"].to_numpy(), n_boot=399, seed=42)
    assert res is not None
    assert abs(res["beta"]) < 0.25
    assert res["p_cr1"] > 0.15


def test_paired_switcher_within_province_recovers_positive_shift():
    rows = []
    for p in range(10):
        rows.append({"province_code": p, "year": 2020, "cluster": 0, "val": 50.0 + p})
        rows.append({"province_code": p, "year": 2021, "cluster": 1, "val": 53.5 + 1.1 * p})
    # Add an extra baseline province in year 2020/2021 to fix year mean slightly
    rows.append({"province_code": 99, "year": 2020, "cluster": 0, "val": 55.0})
    rows.append({"province_code": 99, "year": 2021, "cluster": 0, "val": 55.0})
    df = pd.DataFrame(rows)
    sw = paired_switcher_within_province(df, "province_code", "year", "val", "cluster", 1, 0)
    assert sw["n_switchers"] == 10
    assert sw["mean_diff"] > 0.0
    assert sw["paired_t_p"] < 0.01


def test_multiple_testing_adjustments_ordering_and_nan_preservation():
    p = np.array([0.001, np.nan, 0.02, 0.04, 0.50])
    adj = adjust_multiple_testing(p)
    assert np.isnan(adj["holm"][1]) and np.isnan(adj["bh"][1]) and np.isnan(adj["by"][1])
    valid = [0, 2, 3, 4]
    # Exact ordering: raw <= BH <= BY and raw <= Holm; Holm & BY >= BH
    assert np.all(adj["bh"][valid] <= adj["by"][valid] + 1e-12)
    assert np.all(adj["bh"][valid] <= adj["holm"][valid] + 1e-12)
    assert np.all((adj["holm"][valid] >= 0.0) & (adj["holm"][valid] <= 1.0))
    assert adj["holm"][0] == pytest.approx(0.004)
    assert adj["bh"][0] == pytest.approx(0.004)


def test_compute_spatial_morans_i_detects_positive_cluster_and_handles_missing():
    # 12-node path graph: [0..5] positive vs [6..11] negative, plus 1 NaN isolated node 12
    w = np.zeros((13, 13), dtype=int)
    for u in range(11):
        w[u, u + 1] = 1
        w[u + 1, u] = 1
    vals = np.array([3.2, 3.0, 2.8, 2.6, 2.4, 2.2, -2.2, -2.4, -2.6, -2.8, -3.0, -3.2, np.nan])
    res = compute_spatial_morans_i(vals, w, n_perm=399, seed=42)
    assert res["n"] == 12
    assert res["moran_i"] > 0.5
    assert res["p_perm_two"] < 0.01


def test_wcr_reabsorbs_year_fe_after_cluster_weights():
    """WCR-t phải chiếu lại Year-FE sau khi nhân phần dư hạn chế với trọng số tỉnh (M_Z và W không giao hoán)."""
    rng = np.random.default_rng(21)
    g_clusters, n_years = 18, 6
    cluster_ids = np.repeat(np.arange(g_clusters), n_years)
    years = np.tile(np.arange(n_years), g_clusters)
    treat = ((cluster_ids + years) % 3 == 0).astype(float)
    y = 0.8 * years + rng.normal(0.0, 0.7, size=len(years))
    Z = np.column_stack([np.ones(len(years)), pd.get_dummies(years, drop_first=True, dtype=float).to_numpy()])
    res = fit_fe_cluster_ols(y, treat[:, None], Z, cluster_ids, n_boot=399, seed=7)
    assert res is not None

    u_z, s_z, _ = np.linalg.svd(Z, full_matrices=False)
    r_z = int(np.sum(s_z > 1e-10 * s_z[0]))
    U_z = u_z[:, :r_z]
    y_t = y - U_z @ (U_z.T @ y)
    d_t = treat - U_z @ (U_z.T @ treat)
    dtd = float(d_t @ d_t)
    _, cl_idx = np.unique(cluster_ids, return_inverse=True)
    n_clusters = int(cl_idx.max() + 1)
    n_obs = len(y)
    dof = n_obs - r_z - 1
    c_cr1 = (n_clusters / (n_clusters - 1)) * ((n_obs - 1) / dof)
    signs = np.random.default_rng(7).choice((-1.0, 1.0), size=(399, n_clusters))
    ystar = y_t[None, :] * signs[:, cl_idx]
    ystar_t = ystar - (ystar @ U_z) @ U_z.T
    beta_b = (ystar_t @ d_t) / dtd
    resid_b = ystar_t - beta_b[:, None] * d_t
    score = resid_b * d_t
    cluster_scores = np.zeros((399, n_clusters))
    np.add.at(cluster_scores, (np.arange(399)[:, None], cl_idx[None, :]), score)
    var_b = c_cr1 * np.sum(cluster_scores ** 2, axis=1) / (dtd ** 2)
    t_b = beta_b / np.sqrt(np.maximum(var_b, 1e-18))
    p_refit = float((np.sum(np.abs(t_b) >= abs(res["t_cr1"])) + 1) / 400)
    assert res["p_wcr"] == pytest.approx(p_refit, abs=1e-12)


def test_province_invariant_treatment_is_unidentified_under_twfe():
    """Dummies tỉnh nuốt hết biến xử lý bất biến theo tỉnh — không được trả β nhiễu số."""
    province = np.repeat(np.arange(6), 4)
    year = np.tile(np.arange(4), 6)
    Z = np.column_stack([np.ones(24), np.eye(6)[province, 1:], np.eye(4)[year, 1:]])
    D = (province % 2 == 0).astype(float)
    y = np.random.default_rng(3).normal(size=24)
    assert fit_fe_cluster_ols(y, D, Z, province, n_boot=0) is None


def test_omnibus_wald_with_two_groups_does_not_require_wald_f_key():
    from scripts.analysis.panel_inference import evaluate_hypothesis_panel

    frame = pd.DataFrame({
        "province_code": np.arange(10),
        "year": 2020,
        "group": [2, -1] * 5,
        "y": np.random.default_rng(6).normal(size=10),
    })
    row = evaluate_hypothesis_panel(
        frame,
        hypothesis_id="demo",
        family="demo",
        branch="demo",
        outcome_label="demo",
        value_col="y",
        group_col="group",
        pos_group=2,
        neg_group=-1,
        contrast_label="demo",
        all_groups_ref=2,
        n_boot=0,
    )
    assert np.isfinite(row["joint_wald_p"])


def test_moran_permutation_centers_at_expected_i_and_n3_skips_analytical_variance():
    w = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
    res3 = compute_spatial_morans_i(np.array([1.0, 0.0, 2.0]), w, n_perm=19, seed=1)
    assert res3["n"] == 3
    assert np.isnan(res3["z_analytical"]) and np.isnan(res3["p_analytical"])
    assert np.isfinite(res3["p_perm_two"])

    path = np.zeros((8, 8), dtype=float)
    for u in range(7):
        path[u, u + 1] = path[u + 1, u] = 1.0
    vals = np.array([2.0, 3.0, 1.0, 6.0, 9.0, 4.0, 3.0, 2.0])
    res = compute_spatial_morans_i(vals, path, n_perm=199, seed=4)
    wn = path / path.sum(axis=1, keepdims=True)
    z = vals - vals.mean()
    gen = np.random.default_rng(4)
    null = np.array([(n := len(z), (n / wn.sum()) * (zp @ wn @ zp) / (z @ z))[1] for zp in (gen.permutation(z) for _ in range(199))])
    expected = res["expected_i"]
    p_centered = (np.count_nonzero(np.abs(null - expected) >= abs(res["moran_i"] - expected)) + 1) / 200
    assert res["p_perm_two"] == pytest.approx(p_centered, abs=1e-12)


def test_panel_inference_real_data_contract():
    """Chạy đầy đủ read-only trên dữ liệu thật của repo và kiểm tra bất biến học thuật."""
    out = run_study(write_outputs=False)
    prim = out["primary"].set_index("hypothesis_id")
    # 2D STING PCI collapses when Year-FE + CR1 applied
    assert prim.loc["2d_pci", "naive_mwu_raw_p"] < 1e-4
    assert prim.loc["2d_pci", "p_cr1_yrfe"] > 0.20
    assert prim.loc["2d_pci", "n_obs"] == 726
    assert prim.loc["2d_pci", "g_provinces"] == 63

    # High-Dim 8D Quantile mc=7: Year-FE CR1 and family Holm (3 outcomes) at 5%;
    # global Holm over 6 confirmatory tests does not; TWFE and GRDP do not reject.
    assert prim.loc["hd8_q7_pci", "p_cr1_yrfe"] < 0.05
    assert prim.loc["hd8_q7_pci", "holm_p_family"] < 0.05
    assert prim.loc["hd8_q7_pci", "holm_p_global"] > 0.05
    assert prim.loc["hd8_q7_pci", "beta_yrfe"] > 1.0
    assert prim.loc["hd8_q7_pci", "p_cr1_twfe"] > 0.10
    assert prim.loc["hd8_wy_pci", "p_cr1_yrfe"] < 0.05
    assert prim.loc["hd8_q7_grdp", "p_cr1_yrfe"] > 0.05

    # Subspace FDR check on all 383 subspaces
    sp = out["subspace_pci"]
    assert sp["m_tested"] == 383
    assert sp["n_bh_05"] > 50 and sp["n_bh_05"] <= sp["n_naive_05"]
    assert sp["n_by_05"] <= sp["n_bh_05"]

    # Ridge 2024 spatial residual: no detected residual autocorrelation at 5%
    spat = out["spatial"].set_index("hypothesis_id")
    assert spat.loc["pred_ridge_2024", "moran_i"] > 0.20
    assert spat.loc["pred_ridge_2024", "p_perm_two"] < 0.01
    assert spat.loc["residual_ridge_2024", "p_perm_two"] > 0.20
    assert "white noise" not in str(spat.loc["residual_ridge_2024", "verdict"]).lower()
    assert "Hấp thụ sạch" not in str(spat.loc["residual_ridge_2024", "verdict"])
