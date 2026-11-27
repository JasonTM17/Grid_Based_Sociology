"""Thực nghiệm các hướng phát triển (Future Work) cho đồ án STING × PAPI.

Tự chứa 4 thực nghiệm khám phá độc lập (không chạm artifact đóng băng):
- E1 (`rank_normalization`): Chuẩn hóa thứ hạng phần trăm trong từng năm.
- E2 (`trajectory_clustering`): Phân cụm quỹ đạo 14 năm cấp tỉnh (OLS slope 4.2 & 6.1).
- E3 (`rolling_backtest`): Đánh giá dự báo cuốn chiếu 2018→2023 (đối chứng 6 mốc).
- E4 (`spatial_autocorrelation`): Tự tương quan không gian Moran's I toàn cục năm 2024.

Chạy: python scripts/analysis/future_work.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.analysis.client_product import load_vietnam_geojson  # noqa: E402
from scripts.common.fig_style import CLUSTER_COLORS, PALETTE, style_context  # noqa: E402
from scripts.common.midterm_clustering import FEATURES, fit_grid  # noqa: E402
from scripts.common.papi_forecast import forecast_from_history, score_forecast  # noqa: E402
from scripts.common.papi_pred_common import load_config, load_panel  # noqa: E402
from sting import STING  # noqa: E402

SEED = 42
RESULTS_DIR = ROOT / "results"
FIGS_DIR = RESULTS_DIR / "figs"
FORECAST_2024_JSON = RESULTS_DIR / "papi_forecast_2024.json"
STAKEHOLDER_2024_CSV = RESULTS_DIR / "stakeholder_province_summary_2024.csv"


def compute_reference_sample(panel: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Lấy 869 dòng đủ hai chỉ tiêu và gán nhãn STING tham chiếu chuẩn hóa gộp."""
    complete = panel.dropna(subset=list(FEATURES)).sort_values(["province_code", "year"]).reset_index(drop=True)
    if len(complete) != 869:
        raise ValueError(f"Kỳ vọng 869 quan sát đủ 4.2 & 6.1, nhận được {len(complete)}.")
    z_pooled = StandardScaler().fit_transform(complete[list(FEATURES)].to_numpy(dtype=float))
    model, labels = fit_grid(z_pooled)
    n_noise = int((labels == -1).sum())
    if model.n_clusters_ != 3 or n_noise != 171:
        raise ValueError(
            f"Nhãn STING tham chiếu không khớp mốc (3 cụm, 171 nhiễu): "
            f"{model.n_clusters_} cụm, {n_noise} nhiễu."
        )
    return complete, labels


def rank_normalization(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """E1 (Hướng 1): Chuẩn hóa thứ hạng phần trăm trong từng năm rồi chạy STING."""
    complete, label_ref = compute_reference_sample(panel)
    ranked = complete.copy()
    ranked["rank_4_2"] = ranked.groupby("year")["sd_4_2"].rank(pct=True)
    ranked["rank_6_1"] = ranked.groupby("year")["sd_6_1"].rank(pct=True)

    rank_matrix = ranked[["rank_4_2", "rank_6_1"]].to_numpy(dtype=float)
    model_rank, label_rank = fit_grid(rank_matrix)

    both_assigned = (label_ref >= 0) & (label_rank >= 0)
    ari_full = float(adjusted_rand_score(label_ref, label_rank))
    ari_non_noise = float(adjusted_rand_score(label_ref[both_assigned], label_rank[both_assigned]))
    n_noise = int((label_rank == -1).sum())
    sizes = (
        pd.Series(label_rank[label_rank >= 0]).value_counts().sort_index().to_dict()
        if (label_rank >= 0).any()
        else {}
    )

    out_df = pd.DataFrame(
        {
            "province_code": ranked["province_code"].astype(int),
            "province_vi": ranked["province_vi"],
            "year": ranked["year"].astype(int),
            "rank_4_2": ranked["rank_4_2"],
            "rank_6_1": ranked["rank_6_1"],
            "label_ref": label_ref.astype(int),
            "label_rank": label_rank.astype(int),
        }
    )
    summary = {
        "n_rows": len(out_df),
        "n_clusters": int(model_rank.n_clusters_),
        "cluster_sizes": {int(k): int(v) for k, v in sizes.items()},
        "n_noise": n_noise,
        "noise_ratio": float(n_noise / len(out_df)),
        "n_both_assigned": int(both_assigned.sum()),
        "ari_full": ari_full,
        "ari_non_noise": ari_non_noise,
    }
    return out_df, summary


def trajectory_clustering(panel: pd.DataFrame, min_years: int = 8) -> tuple[pd.DataFrame, dict]:
    """E2 (Hướng 2): Tóm tắt quỹ đạo tuyến tính 2011–2024 cấp tỉnh và phân cụm trên độ dốc."""
    complete = panel.dropna(subset=list(FEATURES)).sort_values(["province_code", "year"])
    records: list[dict] = []
    for code, grp in complete.groupby("province_code", sort=True):
        if len(grp) < min_years:
            continue
        years = grp["year"].to_numpy(dtype=float)
        y_42 = grp["sd_4_2"].to_numpy(dtype=float)
        y_61 = grp["sd_6_1"].to_numpy(dtype=float)
        slope_42 = float(np.polyfit(years, y_42, 1)[0])
        slope_61 = float(np.polyfit(years, y_61, 1)[0])
        records.append(
            {
                "province_code": int(code),
                "province_vi": str(grp["province_vi"].iloc[0]),
                "n_years": int(len(grp)),
                "mean_4_2": float(y_42.mean()),
                "mean_6_1": float(y_61.mean()),
                "slope_4_2": slope_42,
                "slope_6_1": slope_61,
            }
        )

    traj_df = pd.DataFrame(records).sort_values("province_code").reset_index(drop=True)
    if traj_df.empty:
        raise ValueError("Không có tỉnh nào đủ số năm quan sát tối thiểu cho quỹ đạo.")

    z_slopes = StandardScaler().fit_transform(traj_df[["slope_4_2", "slope_6_1"]].to_numpy(dtype=float))
    sting_traj = STING(n_levels=2, factor=4, min_count=3).fit(z_slopes)
    sting_labels = sting_traj.cluster(level=1, connectivity=1)
    km = KMeans(n_clusters=3, n_init=10, random_state=SEED).fit(z_slopes)

    traj_df["sting_label"] = sting_labels.astype(int)
    traj_df["kmeans_label"] = km.labels_.astype(int)

    sting_non_noise = sting_labels >= 0
    sting_sil: float | None = None
    if sting_non_noise.sum() >= 3 and len(set(sting_labels[sting_non_noise])) >= 2:
        sting_sil = float(silhouette_score(z_slopes[sting_non_noise], sting_labels[sting_non_noise]))

    ordered_61 = traj_df.sort_values("slope_6_1", ascending=False)
    top3_rising = [
        {"province_vi": r.province_vi, "slope_6_1": float(r.slope_6_1), "slope_4_2": float(r.slope_4_2)}
        for r in ordered_61.head(3).itertuples()
    ]
    top3_falling = [
        {"province_vi": r.province_vi, "slope_6_1": float(r.slope_6_1), "slope_4_2": float(r.slope_4_2)}
        for r in ordered_61.tail(3).iloc[::-1].itertuples()
    ]

    summary = {
        "n_provinces": len(traj_df),
        "min_years": int(min_years),
        "sting_n_clusters": int(sting_traj.n_clusters_),
        "sting_n_noise": int((sting_labels == -1).sum()),
        "sting_noise_ratio": float((sting_labels == -1).mean()),
        "sting_silhouette_non_noise": sting_sil,
        "kmeans_k": 3,
        "kmeans_silhouette": float(silhouette_score(z_slopes, km.labels_)),
        "kmeans_sizes": pd.Series(km.labels_).value_counts().sort_index().to_dict(),
        "top3_rising_6_1": top3_rising,
        "top3_falling_6_1": top3_falling,
    }
    return traj_df, summary


def backtest_origin(panel: pd.DataFrame, config: dict, origin: int) -> pd.DataFrame:
    """Chạy đúng 1 mốc xuất phát `origin` (dự báo `origin + 1`) và trả về bảng dài."""
    history = panel.loc[panel["year"] <= origin]
    observed = panel.loc[panel["year"] == origin + 1]
    run = forecast_from_history(history, config["sting"], origin_year=origin)
    _, metrics, grid_table = score_forecast(run, observed)

    grid_idx = grid_table.set_index("method")
    fc_recall = float(grid_idx.loc["forecast", "out_recall"])
    ca_recall = float(grid_idx.loc["carry", "out_recall"])
    fc_bacc = float(grid_idx.loc["forecast", "balanced_zone_accuracy"])
    ca_bacc = float(grid_idx.loc["carry", "balanced_zone_accuracy"])
    n_grid = int(grid_idx.loc["forecast", "n"])

    rows: list[dict] = []
    for target in FEATURES:
        sub = metrics.loc[metrics["target"] == target].set_index("method")
        mae_fc = float(sub.loc["forecast", "mae"])
        mae_ca = float(sub.loc["carry", "mae"])
        rows.append(
            {
                "origin_year": int(origin),
                "target_year": int(origin + 1),
                "target": target,
                "selected_method": run.selection[target],
                "n": int(sub.loc["forecast", "n"]),
                "mae_forecast": mae_fc,
                "mae_carry": mae_ca,
                "mae_gain": float(mae_ca - mae_fc),
                "forecast_beats_carry": bool(mae_fc < mae_ca),
                "n_grid": n_grid,
                "out_recall_forecast": fc_recall,
                "out_recall_carry": ca_recall,
                "balanced_zone_acc_forecast": fc_bacc,
                "balanced_zone_acc_carry": ca_bacc,
            }
        )
    return pd.DataFrame(rows)


def rolling_backtest(
    panel: pd.DataFrame,
    config: dict,
    origins: tuple[int, ...] = tuple(range(2018, 2024)),
) -> tuple[pd.DataFrame, dict]:
    """E3 (Hướng 3): Kiểm tra dự báo cuốn chiếu nhiều mốc (2018→2023)."""
    frames = [backtest_origin(panel, config, origin) for origin in origins]
    bt_df = pd.concat(frames, ignore_index=True)

    # Đối chiếu mốc 2023 khớp đúng kết quả đã công bố trong results/papi_forecast_2024.json
    if 2023 in origins and FORECAST_2024_JSON.is_file():
        published = json.loads(FORECAST_2024_JSON.read_text(encoding="utf-8"))
        pub_scores = {(r["target"], r["method"]): float(r["mae"]) for r in published["scores"]}
        pub_grid = {r["method"]: r for r in published["grid"]}
        r23 = bt_df.loc[bt_df["origin_year"] == 2023].set_index("target")
        for target in FEATURES:
            np.testing.assert_allclose(r23.loc[target, "mae_forecast"], pub_scores[(target, "forecast")], atol=1e-6)
            np.testing.assert_allclose(r23.loc[target, "mae_carry"], pub_scores[(target, "carry")], atol=1e-6)
            np.testing.assert_allclose(
                r23.loc[target, "out_recall_forecast"], float(pub_grid["forecast"]["out_recall"]), atol=1e-6
            )
            np.testing.assert_allclose(
                r23.loc[target, "out_recall_carry"], float(pub_grid["carry"]["out_recall"]), atol=1e-6
            )

    by_target = {}
    for target in FEATURES:
        sub = bt_df.loc[bt_df["target"] == target]
        by_target[target] = {
            "mean_mae_forecast": float(sub["mae_forecast"].mean()),
            "mean_mae_carry": float(sub["mae_carry"].mean()),
            "mean_mae_gain": float(sub["mae_gain"].mean()),
            "n_years_forecast_wins": int(sub["forecast_beats_carry"].sum()),
            "n_years_total": int(len(sub)),
        }

    unique_years = bt_df.drop_duplicates(subset=["origin_year"])
    summary = {
        "origins": [int(o) for o in origins],
        "by_target": by_target,
        "mean_mae_gain_overall": float(bt_df["mae_gain"].mean()),
        "mean_out_recall_forecast": float(unique_years["out_recall_forecast"].mean()),
        "mean_out_recall_carry": float(unique_years["out_recall_carry"].mean()),
        "mean_balanced_acc_forecast": float(unique_years["balanced_zone_acc_forecast"].mean()),
        "mean_balanced_acc_carry": float(unique_years["balanced_zone_acc_carry"].mean()),
    }
    return bt_df, summary


def _extract_rounded_vertices(geometry: dict, decimals: int = 4) -> set[tuple[float, float]]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    vertices: set[tuple[float, float]] = set()
    if gtype == "Polygon":
        rings = coords
    elif gtype == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        raise ValueError(f"Kiểu hình học không hỗ trợ: {gtype}")
    for ring in rings:
        for pt in ring:
            vertices.add((round(float(pt[0]), decimals), round(float(pt[1]), decimals)))
    return vertices


def build_queen_adjacency(provinces_order: list[str], coord_decimals: int = 4) -> np.ndarray:
    """Dựng ma trận kề Queen 63×63 (chung >= 1 đỉnh sau làm tròn `coord_decimals`) từ GeoJSON."""
    geojson = load_vietnam_geojson(simplify_step=1, coord_decimals=coord_decimals)
    verts_by_name: dict[str, set[tuple[float, float]]] = {}
    for feat in geojson["features"]:
        name = str((feat.get("properties") or {}).get("province_vi", "")).strip()
        verts_by_name[name] = _extract_rounded_vertices(feat["geometry"], decimals=coord_decimals)

    missing = sorted(set(provinces_order) - set(verts_by_name))
    extra = sorted(set(verts_by_name) - set(provinces_order))
    if missing or extra:
        raise ValueError(f"Không khớp tên tỉnh GeoJSON vs panel — thiếu: {missing}, dư: {extra}")

    n = len(provinces_order)
    adj = np.zeros((n, n), dtype=int)
    for i in range(n):
        vi = verts_by_name[provinces_order[i]]
        for j in range(i + 1, n):
            if vi & verts_by_name[provinces_order[j]]:
                adj[i, j] = 1
                adj[j, i] = 1
    return adj


def _morans_i_row_standardized(values: np.ndarray, w_std: np.ndarray) -> float:
    z = values - values.mean()
    denom = float(np.dot(z, z))
    if denom == 0.0:
        return 0.0
    n = len(values)
    s0 = float(w_std.sum())
    num = float(z @ w_std @ z)
    return float((n / s0) * (num / denom))


def spatial_autocorrelation(
    panel: pd.DataFrame,
    n_permutations: int = 999,
) -> tuple[pd.DataFrame, dict]:
    """E4 (Hướng 4 không gian): Tính Moran's I toàn cục năm 2024 trên ma trận kề Queen."""
    complete, label_ref = compute_reference_sample(panel)
    complete_with_lbl = complete.copy()
    complete_with_lbl["in_cluster"] = (label_ref >= 0).astype(float)

    sub_2024 = (
        complete_with_lbl.loc[complete_with_lbl["year"] == 2024]
        .sort_values("province_code")
        .reset_index(drop=True)
    )
    all_provinces = (
        panel[["province_code", "province_vi"]]
        .drop_duplicates()
        .sort_values("province_code")["province_vi"]
        .tolist()
    )
    full_adj = build_queen_adjacency(all_provinces, coord_decimals=4)
    idx_by_name = {name: i for i, name in enumerate(all_provinces)}

    active_names = sub_2024["province_vi"].tolist()
    active_idx = [idx_by_name[name] for name in active_names]
    sub_adj = full_adj[np.ix_(active_idx, active_idx)]

    deg = sub_adj.sum(axis=1)
    islands = [active_names[i] for i, d in enumerate(deg) if d == 0]
    keep_mask = deg > 0
    sub_adj_conn = sub_adj[np.ix_(keep_mask, keep_mask)].astype(float)
    row_sums = sub_adj_conn.sum(axis=1, keepdims=True)
    w_std = sub_adj_conn / row_sums
    sub_conn = sub_2024.loc[keep_mask].reset_index(drop=True)

    rng = np.random.default_rng(SEED)
    n = len(sub_conn)
    expected_i = -1.0 / (n - 1)
    rows: list[dict] = []
    for var in ("sd_4_2", "sd_6_1", "in_cluster"):
        vals = sub_conn[var].to_numpy(dtype=float)
        obs_i = _morans_i_row_standardized(vals, w_std)
        perm_vals = np.array(
            [
                _morans_i_row_standardized(vals[rng.permutation(n)], w_std)
                for _ in range(n_permutations)
            ],
            dtype=float,
        )
        # Kiểm định hoán vị hai phía quanh kỳ vọng E[I]
        p_perm = float((np.sum(np.abs(perm_vals - expected_i) >= abs(obs_i - expected_i)) + 1) / (n_permutations + 1))
        rows.append(
            {
                "variable": var,
                "n": int(n),
                "moran_I": float(obs_i),
                "expected_I": float(expected_i),
                "p_perm": p_perm,
                "n_islands": int(len(islands)),
            }
        )

    sp_df = pd.DataFrame(rows)
    hanoi_neighbors = int(full_adj[idx_by_name["Hà Nội"]].sum())
    summary = {
        "n_provinces_total": len(all_provinces),
        "n_2024_complete": len(sub_2024),
        "n_connected": int(n),
        "islands_excluded": islands,
        "hanoi_neighbors": hanoi_neighbors,
        "mean_neighbors_63": float(full_adj.sum(axis=1).mean()),
    }
    return sp_df, summary


def build_overview_figure(
    rank_df: pd.DataFrame,
    traj_df: pd.DataFrame,
    bt_df: pd.DataFrame,
    sp_df: pd.DataFrame,
) -> plt.Figure:
    """Vẽ hình tổng hợp 2×2 cho E1–E4."""
    with style_context():
        fig, axes = plt.subplots(2, 2, figsize=(11.6, 8.2), dpi=160, layout="constrained")

        # Panel 1: E1 rank-normalization scatter
        ax = axes[0, 0]
        noise_m = rank_df["label_rank"] == -1
        ax.scatter(
            rank_df.loc[noise_m, "rank_4_2"],
            rank_df.loc[noise_m, "rank_6_1"],
            s=12, color=PALETTE["gray"], marker="x", alpha=0.65,
            label=f"Nhiễu ({int(noise_m.sum())})",
        )
        cids_sorted = sorted(
            (c for c in rank_df["label_rank"].unique() if c >= 0),
            key=lambda c: int((rank_df["label_rank"] == c).sum()),
            reverse=True,
        )
        n_assigned_e1 = int((~noise_m).sum())
        top_n_e1 = int((rank_df["label_rank"] == cids_sorted[0]).sum()) if cids_sorted else 0
        for rank_i, cid in enumerate(cids_sorted):
            m = rank_df["label_rank"] == cid
            lbl = None
            if rank_i == 0:
                lbl = f"Cụm lớn nhất #{cid} ({top_n_e1})"
            elif rank_i == 1 and len(cids_sorted) > 1:
                lbl = f"{len(cids_sorted) - 1} cụm khác ({n_assigned_e1 - top_n_e1})"
            ax.scatter(
                rank_df.loc[m, "rank_4_2"],
                rank_df.loc[m, "rank_6_1"],
                s=12, color=CLUSTER_COLORS.get(int(cid), PALETTE["purple"]), alpha=0.75, linewidths=0,
                label=lbl,
            )
        ax.set_title("E1. Chuẩn hóa hạng trong từng năm (lưới 16×16)", fontsize=10.5)
        ax.set_xlabel("Thứ hạng phần trăm 4.2")
        ax.set_ylabel("Thứ hạng phần trăm 6.1")
        ax.set_ylim(-0.04, 1.15)
        ax.grid(alpha=0.18)
        ax.legend(loc="upper left", fontsize=7.5, ncols=3, framealpha=0.92)

        # Panel 2: E2 trajectory slope scatter colored by STING label
        ax = axes[0, 1]
        noise_t = traj_df["sting_label"] == -1
        ax.scatter(
            traj_df.loc[noise_t, "slope_4_2"],
            traj_df.loc[noise_t, "slope_6_1"],
            s=26, color=PALETTE["gray"], marker="x", label=f"Nhiễu ({int(noise_t.sum())})",
        )
        for cid in sorted(c for c in traj_df["sting_label"].unique() if c >= 0):
            m = traj_df["sting_label"] == cid
            ax.scatter(
                traj_df.loc[m, "slope_4_2"],
                traj_df.loc[m, "slope_6_1"],
                s=28, color=CLUSTER_COLORS.get(int(cid), PALETTE["blue"]), alpha=0.85,
                label=f"Cụm {cid} ({int(m.sum())})",
            )
        ax.axhline(0.0, color="#9AA5B1", linestyle="--", linewidth=0.8)
        ax.axvline(0.0, color="#9AA5B1", linestyle="--", linewidth=0.8)
        ax.set_title("E2. Độ dốc quỹ đạo 63 tỉnh 2011–2024 (STING 4×4, mc=3)", fontsize=10.5)
        ax.set_xlabel("Độ dốc 4.2 (điểm/năm)")
        ax.set_ylabel("Độ dốc 6.1 (điểm/năm)")
        ax.grid(alpha=0.18)
        ax.legend(loc="upper left", fontsize=7.5)

        # Panel 3: E3 rolling backtest MAE forecast vs carry for both targets
        ax = axes[1, 0]
        styles = {
            "sd_4_2": (PALETTE["blue"], "o", "4.2"),
            "sd_6_1": (PALETTE["green"], "s", "6.1"),
        }
        for target, (col, mk, short) in styles.items():
            sub = bt_df.loc[bt_df["target"] == target].sort_values("target_year")
            ax.plot(sub["target_year"], sub["mae_forecast"], color=col, marker=mk, linewidth=1.8, label=f"{short} Dự báo")
            ax.plot(sub["target_year"], sub["mae_carry"], color=col, marker=mk, linestyle="--", alpha=0.65, linewidth=1.4, label=f"{short} Giữ năm trước")
        ax.set_title("E3. Backtest cuốn chiếu MAE (mục tiêu 2019–2024)", fontsize=10.5)
        ax.set_xlabel("Năm mục tiêu")
        ax.set_ylabel("MAE")
        ax.set_xticks(sorted(bt_df["target_year"].unique()))
        ax.grid(alpha=0.18)
        ax.legend(loc="upper right", fontsize=7.2, ncols=2)

        # Panel 4: E4 Moran's I bars with permutation p-values
        ax = axes[1, 1]
        var_labels = {"sd_4_2": "4.2 Tham nhũng", "sd_6_1": "6.1 Y tế công", "in_cluster": "Trong vùng dày"}
        x_pos = np.arange(len(sp_df))
        colors = [PALETTE["blue"], PALETTE["green"], PALETTE["orange"]]
        bars = ax.bar(x_pos, sp_df["moran_I"], color=colors, width=0.52)
        ax.axhline(0.0, color="#667788", linewidth=0.9)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([var_labels.get(v, v) for v in sp_df["variable"]])
        for bar, row in zip(bars, sp_df.itertuples(), strict=True):
            y_txt = bar.get_height() + 0.015 if bar.get_height() >= 0 else bar.get_height() - 0.04
            ax.text(bar.get_x() + bar.get_width() / 2, y_txt, f"I={row.moran_I:.3f}\np={row.p_perm:.3f}",
                    ha="center", va="bottom", fontsize=8)
        ax.set_ylim(min(-0.08, float(sp_df["moran_I"].min()) - 0.08), max(0.32, float(sp_df["moran_I"].max()) + 0.10))
        ax.set_title("E4. Tự tương quan không gian Moran's I (năm 2024)", fontsize=10.5)
        ax.set_ylabel("Moran's I toàn cục")
        ax.grid(axis="y", alpha=0.18)

        fig.suptitle("Tổng hợp thực nghiệm 4 hướng phát triển tiếp theo (STING × PAPI)", fontsize=13)
        return fig


def _qualitative_candidates(panel: pd.DataFrame, traj_df: pd.DataFrame) -> pd.DataFrame:
    """Hợp tỉnh độ dốc 6.1 cực trị (top/bottom 3) và các tỉnh ô thưa năm 2024 để gợi ý khảo sát."""
    complete, label_ref = compute_reference_sample(panel)
    sub_24 = complete.loc[complete["year"] == 2024].copy()
    sub_24["label_ref"] = label_ref[complete["year"] == 2024]
    noise_24 = set(sub_24.loc[sub_24["label_ref"] == -1, "province_vi"])

    action_map: dict[str, str] = {}
    if STAKEHOLDER_2024_CSV.is_file():
        sh = pd.read_csv(STAKEHOLDER_2024_CSV)
        action_map = dict(zip(sh["province_vi"], sh["action_group"]))

    ord_61 = traj_df.sort_values("slope_6_1", ascending=False)
    top3 = set(ord_61.head(3)["province_vi"])
    bot3 = set(ord_61.tail(3)["province_vi"])
    union_provs = sorted(top3 | bot3 | noise_24)

    rows = []
    traj_idx = traj_df.set_index("province_vi")
    sub24_idx = sub_24.set_index("province_vi")
    for p in union_provs:
        reasons = []
        if p in top3:
            reasons.append("Top-3 tăng nhanh 6.1")
        if p in bot3:
            reasons.append("Top-3 giảm nhanh 6.1")
        if p in noise_24:
            reasons.append("Ô thưa (-1) 2024")
        rows.append(
            {
                "province_vi": p,
                "reasons": "; ".join(reasons),
                "action_group_2024": action_map.get(p, "—"),
                "slope_4_2": float(traj_idx.loc[p, "slope_4_2"]) if p in traj_idx.index else np.nan,
                "slope_6_1": float(traj_idx.loc[p, "slope_6_1"]) if p in traj_idx.index else np.nan,
                "sd_6_1_2024": float(sub24_idx.loc[p, "sd_6_1"]) if p in sub24_idx.index else np.nan,
            }
        )
    return pd.DataFrame(rows)


def render_markdown(
    e1_sum: dict,
    e2_sum: dict,
    e3_sum: dict,
    e4_sum: dict,
    bt_df: pd.DataFrame,
    sp_df: pd.DataFrame,
    qual_df: pd.DataFrame,
) -> str:
    """Sinh báo cáo `results/future_work.md` bằng tiếng Việt với số liệu chạy thật."""
    sting_sil_str = (
        f"{e2_sum['sting_silhouette_non_noise']:.4f}"
        if e2_sum["sting_silhouette_non_noise"] is not None
        else "n/a (< 2 cụm)"
    )
    lines = [
        "# [THAM KHẢO — THỰC NGHIỆM HƯỚNG PHÁT TRIỂN, CHƯA DUYỆT GV]",
        "",
        "Tài liệu tổng hợp kết quả chạy thực nghiệm 4 hướng mở rộng định lượng (`E1–E4`) và danh sách gợi ý khảo sát định tính (`Hướng 5`) cho đồ án STING × PAPI, **không làm thay đổi các artifact đóng băng**.",
        "",
        "## Hướng 1 (`E1`): Chuẩn hóa thứ hạng phần trăm trong từng năm (Rank-normalization)",
        "",
        f"- **Thiết lập:** Trên đủ **{e1_sum['n_rows']} quan sát** (`sd_4_2`, `sd_6_1`), tính `rank(pct=True)` trong từng năm rồi chạy đúng cấu hình STING đóng băng (`16×16`, `min_count=5`, `connectivity=1`).",
        f"- **Kết quả:** **{e1_sum['n_clusters']} cụm** (kích thước `{e1_sum['cluster_sizes']}`), **{e1_sum['n_noise']}/{e1_sum['n_rows']} nhiễu ({e1_sum['noise_ratio']:.1%})**.",
        f"- **Đối chiếu với STING z-score gộp (`3` cụm, `171` nhiễu):** `ARI (đầy đủ 869)` = **{e1_sum['ari_full']:.4f}**, `ARI (giao không nhiễu, n={e1_sum['n_both_assigned']})` = **{e1_sum['ari_non_noise']:.4f}**.",
        "- **Đọc kết quả trung thực:** Chuẩn hóa hạng trong năm **thay đổi chính câu hỏi nghiên cứu** (từ *mức điểm tuyệt đối xuyên 14 năm* sang *vị thế tương đối trong từng năm*), nên phân hoạch khác biệt rõ rệt (`ARI non-noise` thấp) là điều hợp lý về mặt hình học, không chứng minh cách nào đúng hơn một cách tuyệt đối và không suy ra nguyên nhân đổi thang đo.",
        "",
        "## Hướng 2 (`E2`): Phân cụm quỹ đạo tuyến tính cấp tỉnh 2011–2024 (Feature trajectory)",
        "",
        f"- **Thiết lập:** Lọc các tỉnh có tối thiểu **{e2_sum['min_years']} năm** đủ cả `4.2` & `6.1` (**{e2_sum['n_provinces']} tỉnh**), lấy độ dốc OLS (`slope_4_2`, `slope_6_1`) chuẩn hóa Z-score rồi chạy STING (`4×4`, `min_count=3`) và K-Means (`k=3`, `seed=42`).",
        f"- **Kết quả:** STING tìm được **{e2_sum['sting_n_clusters']} cụm**, **{e2_sum['sting_n_noise']} tỉnh nhiễu ({e2_sum['sting_noise_ratio']:.1%})**, silhouette (non-noise) = **{sting_sil_str}** | K-Means (`k=3`) kích thước `{e2_sum['kmeans_sizes']}`, silhouette = **{e2_sum['kmeans_silhouette']:.4f}**.",
        "- **Top-3 tỉnh tăng nhanh nhất theo `slope_6_1`:** "
        + ", ".join(f"{r['province_vi']} (`{r['slope_6_1']:+.4f}`/năm)" for r in e2_sum["top3_rising_6_1"])
        + ".",
        "- **Top-3 tỉnh giảm / chậm nhất theo `slope_6_1`:** "
        + ", ".join(f"{r['province_vi']} (`{r['slope_6_1']:+.4f}`/năm)" for r in e2_sum["top3_falling_6_1"])
        + ".",
        "- **Đọc kết quả trung thực:** Độ dốc OLS gom 14 năm thành xu hướng tuyến tính trung bình để loại bỏ lặp quan sát tỉnh-năm, nhưng có thể che khuất bước ngoặt phi tuyến hoặc thay đổi thiết kế khảo sát giữa kỳ; không suy diễn thành hiệu quả điều hành nhân quả.",
        "",
        "## Hướng 3 (`E3`): Backtest cuốn chiếu nhiều mốc (`2018 → 2023`, năm mục tiêu `2019–2024`)",
        "",
        "- **Thiết lập:** Tái dùng nguyên văn `forecast_from_history` và `score_forecast` tại 6 mốc xuất phát `2018..2023` (chỉ dùng dữ liệu `<= origin_year`; mốc `2023→2024` trùng khớp `results/papi_forecast_2024.json`).",
        "",
        "| Năm gốc | Mục tiêu | Chỉ tiêu | Chọn theo CV | MAE Dự báo | MAE Giữ năm trước | Lợi thế MAE | Out-recall (Dự báo vs Giữ năm trước) |",
        "|---:|---:|---|---|---:|---:|---:|---:|",
    ]
    for r in bt_df.itertuples():
        lines.append(
            f"| {r.origin_year} | {r.target_year} | `{r.target}` | `{r.selected_method}` | "
            f"{r.mae_forecast:.4f} | {r.mae_carry:.4f} | {r.mae_gain:+.4f} | "
            f"{r.out_recall_forecast:.3f} vs {r.out_recall_carry:.3f} |"
        )
    b42 = e3_sum["by_target"]["sd_4_2"]
    b61 = e3_sum["by_target"]["sd_6_1"]
    lines.extend(
        [
            "",
            f"- **Tổng hợp 6 mốc:** `sd_4_2` có MAE dự báo TB **{b42['mean_mae_forecast']:.4f}** vs giữ năm trước **{b42['mean_mae_carry']:.4f}** (thắng **{b42['n_years_forecast_wins']}/{b42['n_years_total']}** năm); `sd_6_1` đạt **{b61['mean_mae_forecast']:.4f}** vs **{b61['mean_mae_carry']:.4f}** (thắng **{b61['n_years_forecast_wins']}/{b61['n_years_total']}** năm).",
            f"- **Nhận diện vùng ngoài lưới (`out_recall` TB 6 mốc):** Dự báo = **{e3_sum['mean_out_recall_forecast']:.3f}** vs Giữ năm trước = **{e3_sum['mean_out_recall_carry']:.3f}** (`balanced_zone_accuracy` TB: **{e3_sum['mean_balanced_acc_forecast']:.3f}** vs **{e3_sum['mean_balanced_acc_carry']:.3f}**).",
            "- **Đọc kết quả trung thực:** Mốc `2023→2024` là holdout đã công bố từ trước, không dùng dữ liệu 2024 để chỉnh sửa mô hình. Backtest cuốn chiếu xác nhận nhất quán hiện tượng: hồi quy điểm giảm nhẹ MAE liên tục nhưng co dự báo về tâm nên bỏ sót hầu hết các ca rơi ra ô thưa `-1`.",
            "",
            "## Hướng 4 (`E4`): Tự tương quan không gian (Moran's I) & Cân bằng lớp (`class_weight`)",
            "",
            f"- **Thiết lập không gian:** Ma trận kề Queen 63 tỉnh từ `data/raw/boundaries/diaphantinh.geojson` (chuẩn hóa tên khớp 63/63 tỉnh; trung bình **{e4_sum['mean_neighbors_63']:.2f}** láng giềng/tỉnh; Hà Nội có **{e4_sum['hanoi_neighbors']}** láng giềng; đảo/rời trong mẫu 2024 = `{e4_sum['islands_excluded']}`).",
            "- **Bản đồ Choropleth & Phiếu tỉnh:** Đã hiện hữu sẵn tại `scripts/analysis/client_product.py` và tab **Thống kê khách hàng** trên `app.py` (không làm trùng).",
            "",
            "| Biến phân tích (2024) | Số tỉnh (`n`) | Moran's I | Kỳ vọng `E[I]` | `p_perm` (999 hoán vị) | Số đảo loại trừ |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for r in sp_df.itertuples():
        lines.append(
            f"| `{r.variable}` | {r.n} | {r.moran_I:.4f} | {r.expected_I:.4f} | {r.p_perm:.4f} | {r.n_islands} |"
        )
    lines.extend(
        [
            "",
            "- **Cân bằng lớp (`class_weight='balanced'`) — Trích kết quả đã đánh giá tại `results/candidates_classification.md` (`CLF` CV `2017–2022`, CHƯA DUYỆT GV & KHÔNG chạm holdout 2024):**",
            "  - `C3`: Random Forest + `class_weight='balanced'` đạt `macro-F1 CV = 0.5238` (so với LR gốc `0.434`, thắng `6/6` fold).",
            "  - `C1`: Logistic Regression + `class_weight='balanced'` đạt `macro-F1 CV = 0.4861` (thắng `4/6` fold).",
            "- **Đọc kết quả trung thực:** Moran's I chỉ đo tương quan không gian mô tả ở lát cắt năm 2024 theo kề ranh giới hành chính, không chứng minh hiệu ứng lan tỏa nhân quả giữa các tỉnh; `C1`/`C3` vẫn là ứng viên [CHƯA DUYỆT GV] trên pseudo-label STING.",
            "",
            "## Hướng 5: Gợi ý đối chiếu định tính (ngoài phạm vi code tự động)",
            "",
            "- Đối chiếu danh sách **8 tỉnh Biên bứt phá** trong [`results/stakeholder_summary.md`](stakeholder_summary.md) và quy trình chấm phiếu độc lập tại [`reports/quy-trinh-tham-dinh-danh-sach-papi.md`](../reports/quy-trinh-tham-dinh-danh-sach-papi.md) (tuyệt đối không dùng điểm/nhãn STING để tự xác nhận).",
            "- Dưới đây là hợp của các tỉnh có độ dốc `6.1` cực trị (`E2`) và các tỉnh ô thưa năm 2024 (`-1`) làm **bảng ứng viên tham khảo** cho bước phỏng vấn / rà soát hồ sơ địa phương (không kết luận đúng/sai hay nhân quả):",
            "",
            "| Tỉnh | Tiêu chí gợi ý | Nhóm hành động 2024 | Độ dốc `4.2` | Độ dốc `6.1` | Điểm `6.1` (2024) |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for r in qual_df.itertuples():
        s61_24 = f"{r.sd_6_1_2024:.3f}" if pd.notna(r.sd_6_1_2024) else "—"
        s42 = f"{r.slope_4_2:+.4f}" if pd.notna(r.slope_4_2) else "—"
        s61 = f"{r.slope_6_1:+.4f}" if pd.notna(r.slope_6_1) else "—"
        lines.append(f"| {r.province_vi} | {r.reasons} | {r.action_group_2024} | {s42} | {s61} | {s61_24} |")

    lines.extend(
        [
            "",
            "## Lệnh tái lập & Tệp đầu ra",
            "",
            "- Lệnh chạy: `python scripts/analysis/future_work.py`",
            "- Các tệp đầu ra:",
            "  - `results/future_work_rank.csv`",
            "  - `results/future_work_trajectory.csv`",
            "  - `results/future_work_backtest.csv`",
            "  - `results/future_work_spatial.csv`",
            "  - `results/future_work.md`",
            "  - `results/figs/future_work_overview.png`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    config = load_config()

    rank_df, e1_sum = rank_normalization(panel)
    traj_df, e2_sum = trajectory_clustering(panel)
    bt_df, e3_sum = rolling_backtest(panel, config)
    sp_df, e4_sum = spatial_autocorrelation(panel)
    qual_df = _qualitative_candidates(panel, traj_df)

    rank_df.to_csv(RESULTS_DIR / "future_work_rank.csv", index=False, encoding="utf-8-sig", float_format="%.6f", lineterminator="\n")
    traj_df.to_csv(RESULTS_DIR / "future_work_trajectory.csv", index=False, encoding="utf-8-sig", float_format="%.6f", lineterminator="\n")
    bt_df.to_csv(RESULTS_DIR / "future_work_backtest.csv", index=False, encoding="utf-8-sig", float_format="%.6f", lineterminator="\n")
    sp_df.to_csv(RESULTS_DIR / "future_work_spatial.csv", index=False, encoding="utf-8-sig", float_format="%.6f", lineterminator="\n")

    fig = build_overview_figure(rank_df, traj_df, bt_df, sp_df)
    fig.savefig(FIGS_DIR / "future_work_overview.png", dpi=200, facecolor="white")
    plt.close(fig)

    md_text = render_markdown(e1_sum, e2_sum, e3_sum, e4_sum, bt_df, sp_df, qual_df)
    (RESULTS_DIR / "future_work.md").write_text(md_text, encoding="utf-8")

    print("=== E1 RANK ===", json.dumps(e1_sum, ensure_ascii=False))
    print("=== E2 TRAJECTORY ===", json.dumps(e2_sum, ensure_ascii=False))
    print("=== E3 ROLLING BACKTEST ===", json.dumps(e3_sum, ensure_ascii=False))
    print("=== E4 SPATIAL MORAN'S I ===", json.dumps(e4_sum, ensure_ascii=False))
    print(sp_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
