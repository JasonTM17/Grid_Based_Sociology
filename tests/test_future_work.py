"""Kiểm thử nhanh cho 4 thực nghiệm hướng phát triển trong scripts/analysis/future_work.py."""
from __future__ import annotations

import json

import numpy as np

from scripts.analysis import future_work as fw
from scripts.common.papi_pred_common import load_config, load_panel


def test_rank_normalization_e1():
    panel = load_panel()
    df, summary = fw.rank_normalization(panel)
    assert len(df) == 869
    assert len(df["label_rank"]) == len(df["label_ref"]) == 869
    assert -1.0 <= summary["ari_full"] <= 1.0
    assert -1.0 <= summary["ari_non_noise"] <= 1.0


def test_trajectory_clustering_e2():
    panel = load_panel()
    df, summary = fw.trajectory_clustering(panel)
    assert 1 <= len(df) <= 63
    assert summary["n_provinces"] == len(df)
    assert (df["n_years"] >= 8).all()
    assert np.isfinite(df[["mean_4_2", "mean_6_1", "slope_4_2", "slope_6_1"]]).all().all()


def test_spatial_adjacency_and_moran_e4():
    panel = load_panel()
    provinces = (
        panel[["province_code", "province_vi"]]
        .drop_duplicates()
        .sort_values("province_code")["province_vi"]
        .tolist()
    )
    assert len(provinces) == 63
    adj = fw.build_queen_adjacency(provinces, coord_decimals=4)
    assert adj.shape == (63, 63)
    assert np.array_equal(adj, adj.T)
    assert np.all(np.diag(adj) == 0)
    assert int(adj[provinces.index("Hà Nội")].sum()) >= 3

    sp_df, summary = fw.spatial_autocorrelation(panel, n_permutations=99)
    assert summary["n_provinces_total"] == 63
    assert np.isfinite(sp_df["moran_I"]).all()
    assert ((sp_df["p_perm"] > 0.0) & (sp_df["p_perm"] <= 1.0)).all()


def test_backtest_origin_2023_reproduces_2024_json():
    panel = load_panel()
    config = load_config()
    bt_2023 = fw.backtest_origin(panel, config, 2023).set_index("target")
    published = json.loads(fw.FORECAST_2024_JSON.read_text(encoding="utf-8"))
    pub_scores = {(r["target"], r["method"]): float(r["mae"]) for r in published["scores"]}
    pub_grid = {r["method"]: r for r in published["grid"]}

    for target in ("sd_4_2", "sd_6_1"):
        np.testing.assert_allclose(bt_2023.loc[target, "mae_forecast"], pub_scores[(target, "forecast")], atol=1e-6)
        np.testing.assert_allclose(bt_2023.loc[target, "mae_carry"], pub_scores[(target, "carry")], atol=1e-6)
        np.testing.assert_allclose(
            bt_2023.loc[target, "out_recall_forecast"], float(pub_grid["forecast"]["out_recall"]), atol=1e-6
        )
        np.testing.assert_allclose(
            bt_2023.loc[target, "out_recall_carry"], float(pub_grid["carry"]["out_recall"]), atol=1e-6
        )
