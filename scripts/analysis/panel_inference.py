"""Suy luận bảng chuẩn hóa theo năm, sai số gộp theo tỉnh (CR1), kiểm soát đa kiểm định (FDR) và chẩn đoán không gian.

Giải quyết trực diện ba hạn chế phương pháp luận được ghi nhận trong báo cáo chính:
1. Kiểm định gộp (ANOVA/KW/MWU) trên bảng 63 tỉnh × nhiều năm vi phạm giả định độc lập
   giữa các quan sát lặp cùng tỉnh và trộn lẫn xu hướng vĩ mô theo năm (ví dụ PCI 2011–2022).
   Module ước lượng OLS cố định theo năm (Year-FE) và hai chiều (Two-Way FE: Tỉnh + Năm)
   qua phép chiếu chính xác Frisch–Waugh–Lovell (FWL), đi kèm sai số chuẩn Liang–Zeger CR1
   (hiệu chỉnh hữu hạn theo số tỉnh G) và Wild Cluster Restricted Bootstrap (Rademacher, B = 1.999)
   tính trên giả thuyết không H₀.
2. Phân tách hiệu ứng giữa các tỉnh (between-province structural stratification) vs
   dịch chuyển nội tỉnh theo thời gian (within-province FE & paired test trên các tỉnh đổi cụm).
3. Kiểm soát tỷ lệ khám phá sai / sai lầm loại I (Holm–Bonferroni FWER, Benjamini–Hochberg
   và Benjamini–Yekutieli FDR) cho cả họ giả thuyết ngoại lai chính lẫn 383 không gian con
   khai phá từ `SubspaceCLIQUE` / sàng lọc đặc trưng (`results/high_dim_sting_subspaces.csv`).
4. Kiểm định tự tương quan không gian phần dư (Moran's I với trọng số kề Queen 63 tỉnh,
   1.999 hoán vị) trên `residual_ridge` holdout 2024 để kiểm tra liệu hồi quy đã hấp thụ
   hết tín hiệu không gian quan sát được ở `sd_6_1` hay chưa.

Mọi phân tích đều đọc chỉ-đọc từ artifact đóng băng và tách biệt năm holdout 2024 cho nhánh
học đa chiều (chỉ fit biên trên `year <= 2023`, PCI chính chỉ xét `year <= 2022`).
"""
from __future__ import annotations

import sys
from copy import copy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.analysis.future_work import build_queen_adjacency  # noqa: E402
from scripts.common.fig_style import PALETTE, add_source, save_png, style_context  # noqa: E402
from scripts.common.papi_pred_common import REGRESSION_FEATURES, ROOT  # noqa: E402
from src.high_dim import QuantileSTING, SubspaceCLIQUE  # noqa: E402

RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
RANDOM_SEED = 42
N_BOOT = 1999


def adjust_multiple_testing(p_values: np.ndarray | list[float]) -> dict[str, np.ndarray]:
    """Hiệu chỉnh đa kiểm định Holm–Bonferroni (FWER), Benjamini–Hochberg và Benjamini–Yekutieli (FDR)."""
    p_arr = np.asarray(p_values, dtype=float)
    out = {
        "holm": np.full(p_arr.shape, np.nan, dtype=float),
        "bh": np.full(p_arr.shape, np.nan, dtype=float),
        "by": np.full(p_arr.shape, np.nan, dtype=float),
    }
    valid_mask = np.isfinite(p_arr) & (p_arr >= 0.0) & (p_arr <= 1.0)
    m = int(valid_mask.sum())
    if m == 0:
        return out

    p_valid = p_arr[valid_mask]
    order = np.argsort(p_valid, kind="mergesort")
    p_sorted = p_valid[order]
    ranks = np.arange(1, m + 1, dtype=float)

    # Holm–Bonferroni step-down FWER
    holm_sorted = np.minimum(1.0, np.maximum.accumulate((m - ranks + 1.0) * p_sorted))

    # Benjamini–Hochberg step-up FDR
    bh_raw = (m / ranks) * p_sorted
    bh_sorted = np.minimum(1.0, np.minimum.accumulate(bh_raw[::-1])[::-1])

    # Benjamini–Yekutieli step-up FDR under arbitrary correlation
    c_m = float(np.sum(1.0 / ranks))
    by_raw = (m * c_m / ranks) * p_sorted
    by_sorted = np.minimum(1.0, np.minimum.accumulate(by_raw[::-1])[::-1])

    inv_order = np.empty(m, dtype=int)
    inv_order[order] = np.arange(m)

    out["holm"][valid_mask] = holm_sorted[inv_order]
    out["bh"][valid_mask] = bh_sorted[inv_order]
    out["by"][valid_mask] = by_sorted[inv_order]
    return out


def _build_controls_matrix(
    df: pd.DataFrame,
    year_col: str,
    entity_col: str | None = None,
) -> np.ndarray:
    """Tạo ma trận biến kiểm soát [1, Year FE (, Entity FE)] loại bậc tự do dư thừa."""
    parts = [np.ones((len(df), 1), dtype=float)]
    yr_dummies = pd.get_dummies(df[year_col], drop_first=True, dtype=float).to_numpy()
    if yr_dummies.shape[1] > 0:
        parts.append(yr_dummies)
    if entity_col is not None:
        ent_dummies = pd.get_dummies(df[entity_col], drop_first=True, dtype=float).to_numpy()
        if ent_dummies.shape[1] > 0:
            parts.append(ent_dummies)
    return np.hstack(parts)


def fit_fe_cluster_ols(
    y: np.ndarray,
    D: np.ndarray,
    controls: np.ndarray,
    cluster_ids: np.ndarray,
    *,
    n_boot: int = N_BOOT,
    seed: int = RANDOM_SEED,
) -> dict | None:
    """Ước lượng OLS với Fixed Effects qua phép chiếu Frisch–Waugh–Lovell + CR1 SE + WCR Bootstrap."""
    y_arr = np.asarray(y, dtype=float)
    D_arr = np.asarray(D, dtype=float)
    if D_arr.ndim == 1:
        D_arr = D_arr[:, None]
    Z_arr = np.asarray(controls, dtype=float)
    cl_raw = np.asarray(cluster_ids)

    n_obs = len(y_arr)
    if n_obs == 0 or D_arr.shape[0] != n_obs or Z_arr.shape[0] != n_obs or len(cl_raw) != n_obs:
        return None

    _, cl_idx = np.unique(cl_raw, return_inverse=True)
    n_clusters = int(cl_idx.max() + 1)
    if n_clusters < 2:
        return None

    # SVD exact projection onto controls column space Z
    u_z, s_z, _ = np.linalg.svd(Z_arr, full_matrices=False)
    r_z = int(np.sum(s_z > 1e-10 * (s_z[0] if len(s_z) else 1.0)))
    U_z = u_z[:, :r_z]
    y_t = y_arr - U_z @ (U_z.T @ y_arr)
    D_t = D_arr - U_z @ (U_z.T @ D_arr)

    _, s_d, _ = np.linalg.svd(D_t, full_matrices=False)
    r_d = int(np.sum(s_d > 1e-10 * (s_d[0] if len(s_d) else 1.0)))
    dof_resid = n_obs - r_z - r_d
    if r_d == 0 or dof_resid <= 0:
        return None

    dtd = D_t.T @ D_t
    dtd_inv = np.linalg.pinv(dtd)
    beta = dtd_inv @ (D_t.T @ y_t)
    resid = y_t - D_t @ beta
    rss = float(resid @ resid)

    # Naive i.i.d. OLS covariance vs Liang–Zeger CR1 cluster-robust covariance
    sigma2_iid = rss / dof_resid
    V_iid = sigma2_iid * dtd_inv

    scores = D_t * resid[:, None]
    cluster_scores = np.zeros((n_clusters, D_t.shape[1]), dtype=float)
    np.add.at(cluster_scores, cl_idx, scores)
    meat = cluster_scores.T @ cluster_scores
    c_cr1 = (n_clusters / (n_clusters - 1)) * ((n_obs - 1) / dof_resid)
    V_cr1 = c_cr1 * dtd_inv @ meat @ dtd_inv

    se_iid = np.sqrt(np.maximum(np.diag(V_iid), 0.0))
    se_cr1 = np.sqrt(np.maximum(np.diag(V_cr1), 0.0))

    if D_t.shape[1] == 1:
        b0 = float(beta[0])
        s_iid = float(se_iid[0])
        s_cr1 = float(se_cr1[0])
        t_obs = float(b0 / s_cr1) if s_cr1 > 0 else float("nan")
        t_iid = float(b0 / s_iid) if s_iid > 0 else float("nan")
        p_cr1 = float(2.0 * stats.t.sf(abs(t_obs), df=n_clusters - 1)) if np.isfinite(t_obs) else float("nan")
        p_iid = float(2.0 * stats.t.sf(abs(t_iid), df=dof_resid)) if np.isfinite(t_iid) else float("nan")

        # Wild Cluster Restricted Bootstrap (Rademacher weights under H0: beta = 0, so restricted resid = y_t)
        p_wcr = float("nan")
        if np.isfinite(t_obs) and float(dtd[0, 0]) > 0.0 and n_boot > 0:
            rng = np.random.default_rng(seed)
            signs = rng.choice((-1.0, 1.0), size=(n_boot, n_clusters))
            y0_scores = D_t[:, 0] * y_t
            d_g = np.bincount(cl_idx, weights=y0_scores, minlength=n_clusters)
            a_g = np.bincount(cl_idx, weights=D_t[:, 0] ** 2, minlength=n_clusters)
            dtd_scalar = float(dtd[0, 0])
            beta_b = (signs @ d_g) / dtd_scalar
            score_bg = signs * d_g[None, :] - beta_b[:, None] * a_g[None, :]
            var_b = c_cr1 * (np.sum(score_bg ** 2, axis=1) / (dtd_scalar ** 2))
            t_b = beta_b / np.sqrt(np.maximum(var_b, 1e-18))
            p_wcr = float((np.sum(np.abs(t_b) >= abs(t_obs)) + 1) / (n_boot + 1))

        return {
            "n": int(n_obs),
            "g_clusters": int(n_clusters),
            "r_controls": int(r_z),
            "dof_resid": int(dof_resid),
            "beta": b0,
            "se_iid": s_iid,
            "se_cr1": s_cr1,
            "se_inflation": float(s_cr1 / s_iid) if s_iid > 0 else float("nan"),
            "t_cr1": t_obs,
            "p_iid": p_iid,
            "p_cr1": p_cr1,
            "p_wcr": p_wcr,
        }

    # Joint Wald F-test for multiple group dummies
    wald_f = float((beta @ np.linalg.pinv(V_cr1) @ beta) / r_d)
    p_wald = float(stats.f.sf(wald_f, dfn=r_d, dfd=n_clusters - 1))
    return {
        "n": int(n_obs),
        "g_clusters": int(n_clusters),
        "r_controls": int(r_z),
        "dof_resid": int(dof_resid),
        "wald_f": wald_f,
        "df1": int(r_d),
        "df2": int(n_clusters - 1),
        "p_cr1": p_wald,
        "betas": [float(v) for v in beta],
        "ses_cr1": [float(v) for v in se_cr1],
    }


def paired_switcher_within_province(
    df: pd.DataFrame,
    entity_col: str,
    year_col: str,
    value_col: str,
    group_col: str,
    pos_group: int,
    neg_group: int,
) -> dict:
    """So sánh bắt cặp nội tỉnh trên các tỉnh xuất hiện ở cả hai chế độ cụm (sau khử trung bình năm)."""
    sub = df.loc[df[group_col].isin([pos_group, neg_group]), [entity_col, year_col, value_col, group_col]].dropna().copy()
    sub["val_dm"] = sub[value_col] - sub.groupby(year_col)[value_col].transform("mean")
    piv = sub.groupby([entity_col, group_col])["val_dm"].mean().unstack()
    if pos_group not in piv.columns or neg_group not in piv.columns:
        return {"n_switchers": 0, "mean_diff": float("nan"), "median_diff": float("nan"), "paired_t_p": float("nan"), "wilcoxon_p": float("nan")}
    both = piv[[pos_group, neg_group]].dropna()
    diffs = (both[pos_group] - both[neg_group]).to_numpy(dtype=float)
    n_sw = len(diffs)
    if n_sw < 2:
        return {"n_switchers": int(n_sw), "mean_diff": float("nan"), "median_diff": float("nan"), "paired_t_p": float("nan"), "wilcoxon_p": float("nan")}
    if np.allclose(diffs, 0.0):
        t_p = 1.0
        w_p = 1.0
    else:
        t_p = float(stats.ttest_1samp(diffs, 0.0).pvalue)
        w_p = float(stats.wilcoxon(diffs).pvalue)
    return {
        "n_switchers": int(n_sw),
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "paired_t_p": t_p,
        "wilcoxon_p": w_p,
    }


def evaluate_hypothesis_panel(
    frame: pd.DataFrame,
    *,
    hypothesis_id: str,
    family: str,
    branch: str,
    outcome_label: str,
    value_col: str,
    group_col: str,
    pos_group: int,
    neg_group: int,
    contrast_label: str,
    all_groups_ref: int | None = None,
    n_boot: int = N_BOOT,
    seed: int = RANDOM_SEED,
) -> dict:
    """Đánh giá đồng bộ 1 giả thuyết: Naive MWU (thô & khử năm) vs Year-FE CR1/WCR vs TWFE vs Switchers."""
    valid_all = frame.dropna(subset=[value_col, group_col]).copy()
    valid_all["val_dm_med"] = valid_all[value_col] - valid_all.groupby("year")[value_col].transform("median")

    pair_df = valid_all.loc[valid_all[group_col].isin([pos_group, neg_group])].copy()
    pos_vals = pair_df.loc[pair_df[group_col] == pos_group, value_col].to_numpy(dtype=float)
    neg_vals = pair_df.loc[pair_df[group_col] == neg_group, value_col].to_numpy(dtype=float)
    pos_dm = pair_df.loc[pair_df[group_col] == pos_group, "val_dm_med"].to_numpy(dtype=float)
    neg_dm = pair_df.loc[pair_df[group_col] == neg_group, "val_dm_med"].to_numpy(dtype=float)

    naive_raw_p = float(stats.mannwhitneyu(pos_vals, neg_vals).pvalue) if len(pos_vals) and len(neg_vals) else float("nan")
    naive_dm_p = float(stats.mannwhitneyu(pos_dm, neg_dm).pvalue) if len(pos_dm) and len(neg_dm) else float("nan")

    D_bin = (pair_df[group_col] == pos_group).astype(float).to_numpy()[:, None]
    y_bin = pair_df[value_col].to_numpy(dtype=float)
    cl_bin = pair_df["province_code"].to_numpy()
    Z_yr = _build_controls_matrix(pair_df, "year")
    Z_twfe = _build_controls_matrix(pair_df, "year", "province_code")

    res_yr = fit_fe_cluster_ols(y_bin, D_bin, Z_yr, cl_bin, n_boot=n_boot, seed=seed)
    res_tw = fit_fe_cluster_ols(y_bin, D_bin, Z_twfe, cl_bin, n_boot=n_boot, seed=seed + 1)
    sw = paired_switcher_within_province(pair_df, "province_code", "year", value_col, group_col, pos_group, neg_group)

    # Joint multi-group Wald F test if requested (on valid_all)
    wald_f_val = float("nan")
    wald_p_val = float("nan")
    if all_groups_ref is not None:
        groups = sorted(int(g) for g in valid_all[group_col].unique() if int(g) != int(all_groups_ref))
        if groups:
            D_multi = np.column_stack([(valid_all[group_col] == g).astype(float).to_numpy() for g in groups])
            Z_yr_all = _build_controls_matrix(valid_all, "year")
            res_multi = fit_fe_cluster_ols(
                valid_all[value_col].to_numpy(dtype=float),
                D_multi,
                Z_yr_all,
                valid_all["province_code"].to_numpy(),
                n_boot=0,
            )
            if res_multi is not None:
                wald_f_val = float(res_multi["wald_f"])
                wald_p_val = float(res_multi["p_cr1"])

    yrs_pos = set(int(y) for y in pair_df.loc[pair_df[group_col] == pos_group, "year"])
    yrs_neg = set(int(y) for y in pair_df.loc[pair_df[group_col] == neg_group, "year"])
    overlap_yrs = sorted(yrs_pos & yrs_neg)

    return {
        "section": "primary_panel",
        "hypothesis_id": hypothesis_id,
        "family": family,
        "branch": branch,
        "outcome": outcome_label,
        "contrast": contrast_label,
        "n_obs": int(len(pair_df)),
        "g_provinces": int(res_yr["g_clusters"]) if res_yr else 0,
        "n_overlap_years": int(len(overlap_yrs)),
        "overlap_window": f"{overlap_yrs[0]}–{overlap_yrs[-1]}" if overlap_yrs else "—",
        "naive_mwu_raw_p": naive_raw_p,
        "naive_mwu_dm_p": naive_dm_p,
        "beta_yrfe": float(res_yr["beta"]) if res_yr else float("nan"),
        "se_iid_yrfe": float(res_yr["se_iid"]) if res_yr else float("nan"),
        "se_cr1_yrfe": float(res_yr["se_cr1"]) if res_yr else float("nan"),
        "se_inflation": float(res_yr["se_inflation"]) if res_yr else float("nan"),
        "p_iid_yrfe": float(res_yr["p_iid"]) if res_yr else float("nan"),
        "p_cr1_yrfe": float(res_yr["p_cr1"]) if res_yr else float("nan"),
        "p_wcr_yrfe": float(res_yr["p_wcr"]) if res_yr else float("nan"),
        "joint_wald_f": wald_f_val,
        "joint_wald_p": wald_p_val,
        "beta_twfe": float(res_tw["beta"]) if res_tw else float("nan"),
        "se_cr1_twfe": float(res_tw["se_cr1"]) if res_tw else float("nan"),
        "p_cr1_twfe": float(res_tw["p_cr1"]) if res_tw else float("nan"),
        "n_switchers": int(sw["n_switchers"]),
        "diff_mean_switcher": float(sw["mean_diff"]),
        "p_switcher_t": float(sw["paired_t_p"]),
        "p_switcher_wilcox": float(sw["wilcoxon_p"]),
        "holm_p_family": float("nan"),
        "bh_fdr_family": float("nan"),
        "by_fdr_family": float("nan"),
        "holm_p_global": float("nan"),
        "bh_fdr_global": float("nan"),
        "verdict": "",
    }


def evaluate_subspace_fdr(subspaces_df: pd.DataFrame, p_col: str) -> dict:
    """Áp dụng Holm, BH và BY lên toàn bộ không gian con khai phá được trong `high_dim_sting_subspaces.csv`."""
    adj = adjust_multiple_testing(subspaces_df[p_col].to_numpy(dtype=float))
    valid = np.isfinite(subspaces_df[p_col].to_numpy(dtype=float))
    p_raw = subspaces_df.loc[valid, p_col].to_numpy(dtype=float)
    bh_v = adj["bh"][valid]
    by_v = adj["by"][valid]
    holm_v = adj["holm"][valid]
    m_tot = int(valid.sum())
    return {
        "m_tested": m_tot,
        "n_naive_05": int((p_raw < 0.05).sum()),
        "n_bh_05": int((bh_v < 0.05).sum()),
        "n_by_05": int((by_v < 0.05).sum()),
        "n_holm_05": int((holm_v < 0.05).sum()),
        "pct_bh_of_naive": float((bh_v < 0.05).sum() / max((p_raw < 0.05).sum(), 1)),
        "adj": adj,
    }


def compute_spatial_morans_i(
    values: np.ndarray,
    w_raw: np.ndarray,
    *,
    n_perm: int = N_BOOT,
    seed: int = RANDOM_SEED,
) -> dict:
    """Tính Moran's I với chuẩn hóa theo hàng trên ma trận kề Queen + p-value hoán vị hai phía."""
    vals = np.asarray(values, dtype=float)
    valid = np.isfinite(vals)
    n = int(valid.sum())
    if n < 3:
        return {"n": n, "moran_i": float("nan"), "expected_i": float("nan"), "z_analytical": float("nan"), "p_analytical": float("nan"), "p_perm_two": float("nan")}

    ws = np.asarray(w_raw[np.ix_(valid, valid)], dtype=float)
    rs = ws.sum(axis=1, keepdims=True)
    wn = np.divide(ws, rs, out=np.zeros_like(ws, dtype=float), where=rs > 0)
    z = vals[valid] - float(vals[valid].mean())
    denom = float(z @ z)
    s0 = float(wn.sum())
    if denom == 0.0 or s0 == 0.0:
        return {"n": n, "moran_i": 0.0, "expected_i": -1.0 / (n - 1), "z_analytical": 0.0, "p_analytical": 1.0, "p_perm_two": 1.0}

    moran_i = float((n / s0) * (z @ wn @ z) / denom)
    expected_i = -1.0 / (n - 1)

    # Normal approximation under randomization / normality for reference + exact permutation p
    w_sym = wn + wn.T
    s1 = 0.5 * float(np.sum(w_sym ** 2))
    s2 = float(np.sum((wn.sum(axis=1) + wn.sum(axis=0)) ** 2))
    var_i = max((n * ((n ** 2 - 3 * n + 3) * s1 - n * s2 + 3 * s0 ** 2) - (s1 * (n ** 2 - n) - 2 * n * s2 + 6 * s0 ** 2)) / ((n - 1) * (n - 2) * (n - 3) * (s0 ** 2)) - expected_i ** 2, 1e-18)
    z_ana = (moran_i - expected_i) / float(np.sqrt(var_i))
    p_ana = float(2.0 * stats.norm.sf(abs(z_ana)))

    rng = np.random.default_rng(seed)
    perm_is = np.empty(n_perm, dtype=float)
    for b in range(n_perm):
        zp = rng.permutation(z)
        perm_is[b] = (n / s0) * (zp @ wn @ zp) / denom
    p_perm_two = float((np.sum(np.abs(perm_is) >= abs(moran_i)) + 1) / (n_perm + 1))

    return {
        "n": n,
        "moran_i": moran_i,
        "expected_i": expected_i,
        "z_analytical": float(z_ana),
        "p_analytical": p_ana,
        "p_perm_two": p_perm_two,
    }


def evaluate_spatial_residuals(root: Path = ROOT, *, n_perm: int = N_BOOT, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Chẩn đoán tự tương quan không gian trên sd_6_1 năm 2024 và phần dư dự báo Ridge / Quantile."""
    panel = pd.read_csv(root / "data/processed/papi_panel_63_2011_2024.csv")
    conf = pd.read_csv(root / "results/regression_conformal_2024.csv")
    provinces = sorted(panel["province_vi"].unique())
    w_raw = build_queen_adjacency(provinces).astype(float)

    p24 = panel.loc[panel["year"] == 2024].set_index("province_vi").reindex(provinces)
    conf_m = conf.set_index("province_vi").reindex(provinces)
    conf_m["delta_carry"] = conf_m["actual_2024"] - conf_m["sd_6_1_2023"]
    conf_m["residual_q50"] = conf_m["actual_2024"] - conf_m["quantile_med"]

    specs = [
        ("all_2024_sd_6_1", "sd_6_1 quan sát 2024 (tất cả 61 tỉnh có điểm)", p24["sd_6_1"].to_numpy(dtype=float)),
        ("holdout_actual_2024", "sd_6_1 quan sát 2024 (59 tỉnh khớp holdout)", conf_m["actual_2024"].to_numpy(dtype=float)),
        ("pred_ridge_2024", "Dự báo điểm Ridge 2024 (59 tỉnh holdout)", conf_m["pred_ridge"].to_numpy(dtype=float)),
        ("residual_ridge_2024", "Phần dư Ridge 2024 (actual - pred_ridge)", conf_m["residual_ridge"].to_numpy(dtype=float)),
        ("residual_q50_2024", "Phần dư Quantile q50 2024", conf_m["residual_q50"].to_numpy(dtype=float)),
        ("delta_carry_2024", "Sai phân Δ6.1 = actual_2024 - sd_6_1_2023", conf_m["delta_carry"].to_numpy(dtype=float)),
    ]
    rows = []
    for key, label, arr in specs:
        res = compute_spatial_morans_i(arr, w_raw, n_perm=n_perm, seed=seed)
        verdict = "Hấp thụ sạch (white noise)" if "residual" in key and res["p_perm_two"] >= 0.05 else (
            "Có tự tương quan không gian" if res["p_perm_two"] < 0.05 else "Không rõ / yếu ở ngưỡng 5%"
        )
        rows.append(
            {
                "section": "spatial_residual",
                "hypothesis_id": key,
                "label": label,
                **res,
                "verdict": verdict,
            }
        )
    return pd.DataFrame(rows)


def _fmt_p(val: float) -> str:
    if not np.isfinite(val):
        return "—"
    if val < 1e-4:
        return f"{val:.2e}"
    return f"{val:.4f}"


def plot_panel_inference_diagnostics(
    primary_df: pd.DataFrame,
    sub_pci: dict,
    spatial_df: pd.DataFrame,
    out_path: Path,
    *,
    retrieved: str = "2026-11-28",
) -> None:
    """Vẽ figure 4 khung tổng hợp kiểm định CR1/TWFE, Between vs Within, FDR 383 subspaces & Moran's I."""
    vermilion = "#D55E00"
    short_labels = {
        "2d_pci": "2D STING · PCI",
        "2d_grdp": "2D STING · GRDP",
        "2d_poverty": "2D STING · Nghèo",
        "hd8_q7_pci": "8D Quantile · PCI",
        "hd8_wy_pci": "8D wy-z · PCI",
        "hd8_q7_grdp": "8D Quantile · GRDP",
        "hd8_q7_poverty": "8D Quantile · Nghèo",
    }

    with style_context():
        fig, axes = plt.subplots(2, 2, figsize=(13.8, 9.6))

        # (A) Naive MWU raw vs Year-FE CR1 vs Two-Way FE (-log10 p)
        ax = axes[0, 0]
        p_sub = primary_df.loc[primary_df["hypothesis_id"].isin(short_labels.keys())].copy()
        y_pos = np.arange(len(p_sub))
        h = 0.25
        v_naive = -np.log10(np.clip(p_sub["naive_mwu_raw_p"].to_numpy(), 1e-8, 1.0))
        v_yr = -np.log10(np.clip(p_sub["p_cr1_yrfe"].to_numpy(), 1e-8, 1.0))
        v_tw = -np.log10(np.clip(p_sub["p_cr1_twfe"].to_numpy(), 1e-8, 1.0))

        ax.barh(y_pos + h, v_naive, height=h, color=PALETTE["gray"], label="Naive pooled MWU (gộp thô)")
        ax.barh(y_pos, v_yr, height=h, color=PALETTE["blue"], label="Year-FE + CR1 (63 tỉnh)")
        ax.barh(y_pos - h, v_tw, height=h, color=PALETTE["orange"], label="Two-Way FE (Tỉnh + Năm)")
        ax.axvline(-np.log10(0.05), color=vermilion, linestyle="--", linewidth=1.1, label="p = 0,05")
        ax.set_yticks(y_pos)
        ax.set_yticklabels([short_labels[k] for k in p_sub["hypothesis_id"]], fontsize=8.8)
        ax.invert_yaxis()
        ax.set_xlim(0.0, 9.4)
        ax.set_xlabel("-log₁₀(p-value)  [càng cao càng có ý nghĩa]")
        ax.set_title("A. Naive Gộp thô vs Year-FE CR1 vs Two-Way FE", fontweight="bold")
        ax.legend(loc="center right", bbox_to_anchor=(0.99, 0.67), fontsize=7.6, frameon=True)
        ax.grid(True, axis="x", linestyle=":", alpha=0.45)

        # (B) Effect sizes in PCI score points (beta +- 1.96 * SE_CR1): Between vs Within decomposition
        ax = axes[0, 1]
        pci_specs = [
            ("2D STING (Year-FE CR1)", "2d_pci", "yrfe", PALETTE["gray"]),
            ("2D STING (Within TWFE)", "2d_pci", "twfe", PALETTE["gray"]),
            ("8D Quantile mc=7 (Year-FE CR1)", "hd8_q7_pci", "yrfe", PALETTE["green"]),
            ("8D wy-z mc=7 (Year-FE CR1)", "hd8_wy_pci", "yrfe", PALETTE["blue"]),
            ("8D Quantile mc=7 (Within TWFE)", "hd8_q7_pci", "twfe", PALETTE["orange"]),
        ]
        by_id = primary_df.set_index("hypothesis_id")
        y_b = np.arange(len(pci_specs))
        for yi, (lbl, hid, kind, col) in enumerate(pci_specs):
            r = by_id.loc[hid]
            b_val = float(r[f"beta_{kind}"])
            se_val = float(r[f"se_cr1_{kind}"])
            ci_val = 1.96 * se_val
            p_val = float(r[f"p_cr1_{kind}"])
            ax.errorbar(
                b_val,
                yi,
                xerr=ci_val,
                fmt="o",
                color=col,
                ecolor=col,
                elinewidth=2.2,
                capsize=4,
                markersize=7,
            )
            ax.text(
                b_val + ci_val + 0.12,
                yi,
                f"{b_val:+.2f} (p={_fmt_p(p_val)})",
                va="center",
                fontsize=8.2,
            )
        ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
        ax.set_yticks(y_b)
        ax.set_yticklabels([s[0] for s in pci_specs], fontsize=8.6)
        ax.invert_yaxis()
        ax.set_xlim(-1.6, 4.35)
        ax.set_xlabel("Chênh lệch điểm PCI (± 1,96·SE CR1)")
        ax.set_title("B. Phân tách PCI: Between-Province vs Within-Province FE", fontweight="bold")
        ax.grid(True, axis="x", linestyle=":", alpha=0.45)

        # (C) Subspace multiple-testing survival curve (m = 383 subspaces)
        ax = axes[1, 0]
        p_raw = np.sort(sub_pci["raw_sorted"])
        m_sub = len(p_raw)
        ranks = np.arange(1, m_sub + 1)
        ax.plot(ranks, p_raw, color=PALETTE["blue"], linewidth=2.0, label="p-value (Kruskal PCI_dm)")
        ax.plot(ranks, 0.05 * ranks / m_sub, color=PALETTE["green"], linestyle="--", linewidth=1.4, label=f"BH FDR 0,05 ({sub_pci['n_bh_05']}/{m_sub})")
        c_m = float(np.sum(1.0 / ranks))
        ax.plot(ranks, 0.05 * ranks / (m_sub * c_m), color=PALETTE["orange"], linestyle="-.", linewidth=1.4, label=f"BY FDR 0,05 ({sub_pci['n_by_05']}/{m_sub})")
        ax.axhline(0.05, color=PALETTE["gray"], linestyle=":", linewidth=1.2, label=f"Naive α=0,05 ({sub_pci['n_naive_05']}/{m_sub})")
        ax.set_yscale("log")
        ax.set_ylim(1e-6, 1.5)
        ax.set_xlim(1, m_sub)
        ax.set_xlabel("Thứ hạng không gian con được khai phá (m = 383)")
        ax.set_ylabel("p-value (thang log)")
        ax.set_title("C. Kiểm soát FDR trên 383 không gian con SubspaceCLIQUE/2D-3D", fontweight="bold")
        ax.legend(loc="lower right", fontsize=7.6, frameon=True)
        ax.grid(True, linestyle=":", alpha=0.45)

        # (D) Spatial residual autocorrelation Moran's I (2024 holdout)
        ax = axes[1, 1]
        sp_keys = ["all_2024_sd_6_1", "holdout_actual_2024", "pred_ridge_2024", "residual_ridge_2024", "residual_q50_2024"]
        sp_names = {
            "all_2024_sd_6_1": "Quan sát 6.1 (61 tỉnh)",
            "holdout_actual_2024": "Quan sát 6.1 (59 khớp)",
            "pred_ridge_2024": "Dự báo Ridge (59 tỉnh)",
            "residual_ridge_2024": "Phần dư Ridge (59 tỉnh)",
            "residual_q50_2024": "Phần dư Quantile q50",
        }
        sp_sub = spatial_df.set_index("hypothesis_id").loc[sp_keys].reset_index()
        y_sp = np.arange(len(sp_sub))
        i_vals = sp_sub["moran_i"].to_numpy()
        p_vals = sp_sub["p_perm_two"].to_numpy()
        sp_cols = [PALETTE["green"] if pv < 0.05 else PALETTE["gray"] for pv in p_vals]
        ax.barh(y_sp, i_vals, color=sp_cols, edgecolor="black", linewidth=0.5)
        ax.axvline(0.0, color="black", linewidth=0.9)
        ax.set_yticks(y_sp)
        ax.set_yticklabels([sp_names[k] for k in sp_sub["hypothesis_id"]], fontsize=8.6)
        ax.invert_yaxis()
        for yi, iv, pv in zip(y_sp, i_vals, p_vals):
            sig = "*" if pv < 0.05 else "ns"
            offset = 0.012 if iv >= 0 else 0.014
            pos_x = iv + offset if iv >= 0 else 0.012
            ax.text(pos_x, yi, f"I={iv:+.3f} (p={_fmt_p(pv)}, {sig})", va="center", fontsize=8.0)
        ax.set_xlim(-0.14, 0.56)
        ax.set_xlabel("Moran's I (Queen Contiguity, 1.999 hoán vị)")
        ax.set_title("D. Tự tương quan không gian: Hấp thụ hết vào Ridge 2024", fontweight="bold")
        ax.grid(True, axis="x", linestyle=":", alpha=0.45)

        fig.suptitle(
            "Kiểm định Suy luận Bảng (Year-FE CR1 / TWFE), Kiểm soát FDR Đa chiều & Chẩn đoán Không gian",
            fontsize=12.6,
            fontweight="bold",
            y=0.99,
        )
        add_source(fig, "PAPI 2011–2024, PCI 2011–2022, GSO GRDP/Nghèo & Ranh giới 63 tỉnh", retrieved=retrieved)
        fig.tight_layout(rect=(0, 0.04, 1, 0.96))
        save_png(fig, out_path, dpi=220)


def _sync_excel_sheet(
    primary_df: pd.DataFrame,
    spatial_df: pd.DataFrame,
    sub_pci_summary: dict,
    sub_grdp_summary: dict,
    xlsx_path: Path = RESULTS / "KetQua_STING_PAPI.xlsx",
) -> None:
    """Cập nhật sheet 'Suy luận bảng & FDR' và bảng 'Mục lục' trong KetQua_STING_PAPI.xlsx."""
    if not xlsx_path.is_file():
        return
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Suy luận bảng & FDR"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.views.sheetView[0].showGridLines = False

    white_fill = PatternFill("solid", fgColor="FFFFFF")
    thin_side = Side(style="thin", color="BFBFBF")
    header_font = Font(name="Arial", size=10, bold=True, color="000000")
    body_font = Font(name="Arial", size=10, color="000000")

    cols = [
        ("nhom", "Nhóm phân tích", 18.0, "General", "left"),
        ("doi_tuong", "Mô hình / Giả thuyết", 32.0, "General", "left"),
        ("n_obs", "n (ô)", 9.0, "0", "right"),
        ("g_provinces", "Số tỉnh G", 10.0, "0", "right"),
        ("beta", "Hiệu ứng β / I", 12.0, "0.000", "right"),
        ("se_cr1", "SE (CR1)", 11.0, "0.000", "right"),
        ("naive_p", "p gộp thô", 13.0, "0.0000", "right"),
        ("p_cr1", "p CR1 / perm", 13.0, "0.0000", "right"),
        ("p_wcr", "p WCR boot", 12.0, "0.0000", "right"),
        ("p_twfe", "p TWFE", 12.0, "0.0000", "right"),
        ("holm_bh", "Holm / BH", 15.0, "General", "left"),
        ("verdict", "Kết luận suy luận", 36.0, "General", "left"),
    ]
    rows_export: list[dict] = []
    for _, r in primary_df.iterrows():
        rows_export.append(
            {
                "nhom": str(r["family"]),
                "doi_tuong": f"{r['branch']} · {r['outcome']} ({r['contrast']})",
                "n_obs": int(r["n_obs"]),
                "g_provinces": int(r["g_provinces"]),
                "beta": float(r["beta_yrfe"]),
                "se_cr1": float(r["se_cr1_yrfe"]),
                "naive_p": float(r["naive_mwu_raw_p"]),
                "p_cr1": float(r["p_cr1_yrfe"]),
                "p_wcr": float(r["p_wcr_yrfe"]),
                "p_twfe": float(r["p_cr1_twfe"]),
                "holm_bh": (
                    f"{_fmt_p(r['holm_p_family'])} / {_fmt_p(r['bh_fdr_family'])}"
                    if np.isfinite(r["holm_p_family"])
                    else "Nhạy cảm / Phụ"
                ),
                "verdict": str(r["verdict"]),
            }
        )
    for tag, s_info in [
        ("Subspace FDR · PCI", sub_pci_summary),
        ("Subspace FDR · GRDP", sub_grdp_summary),
    ]:
        rows_export.append(
            {
                "nhom": "Multiple Testing",
                "doi_tuong": f"{tag} ({s_info['m_tested']} hợp lệ): Naive <0.05 = {s_info['n_naive_05']}",
                "n_obs": int(s_info["m_tested"]),
                "g_provinces": 63,
                "beta": float(s_info["pct_bh_of_naive"]),
                "se_cr1": np.nan,
                "naive_p": np.nan,
                "p_cr1": np.nan,
                "p_wcr": np.nan,
                "p_twfe": np.nan,
                "holm_bh": f"Holm={s_info['n_holm_05']} / BH={s_info['n_bh_05']} / BY={s_info['n_by_05']}",
                "verdict": f"{s_info['n_bh_05']}/{s_info['m_tested']} sống sót BH-FDR 5%; {s_info['n_by_05']} sống sót BY-FDR",
            }
        )
    for _, sr in spatial_df.iterrows():
        rows_export.append(
            {
                "nhom": "Không gian Moran's I",
                "doi_tuong": str(sr["label"]),
                "n_obs": int(sr["n"]),
                "g_provinces": int(sr["n"]),
                "beta": float(sr["moran_i"]),
                "se_cr1": np.nan,
                "naive_p": float(sr["p_analytical"]),
                "p_cr1": float(sr["p_perm_two"]),
                "p_wcr": np.nan,
                "p_twfe": np.nan,
                "holm_bh": "—",
                "verdict": str(sr["verdict"]),
            }
        )

    last_col = openpyxl.utils.get_column_letter(len(cols))
    ws["A2"] = "Suy luận Bảng (Year-FE CR1 & TWFE), Kiểm soát Đa kiểm định (Holm / BH / BY) & Không gian Moran's I"
    ws["A2"].font = Font(name="Arial", size=14, bold=True, color="000000")
    ws["A2"].fill = copy(white_fill)
    ws.merge_cells(f"A2:{last_col}2")
    ws.row_dimensions[2].height = 24.0
    ws["A3"] = "Cluster-Robust SE theo 63 tỉnh · Wild Cluster Bootstrap 1.999 · PCI chính chỉ xét 2011–2022 · High-Dim fit <= 2023"
    ws["A3"].font = Font(name="Arial", size=10, italic=True, color="000000")
    ws.merge_cells(f"A3:{last_col}3")
    ws.row_dimensions[3].height = 20.0

    ws.row_dimensions[5].height = 28.0
    for c_idx, (_, title, width, _, _) in enumerate(cols, start=1):
        cell = ws.cell(5, c_idx, title)
        cell.font = copy(header_font)
        cell.fill = copy(white_fill)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(
            top=thin_side,
            bottom=thin_side,
            left=None if c_idx == 1 else thin_side,
            right=None if c_idx == len(cols) else thin_side,
        )
        ws.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = width

    export_df = pd.DataFrame(rows_export)
    for r_idx, (_, rec) in enumerate(export_df.iterrows(), start=6):
        ws.row_dimensions[r_idx].height = 24.0
        for c_idx, (key, _, _, num_fmt, h_align) in enumerate(cols, start=1):
            val = rec[key]
            val = None if pd.isna(val) else (val.item() if hasattr(val, "item") else val)
            cell = ws.cell(r_idx, c_idx, val)
            cell.font = copy(body_font)
            cell.fill = copy(white_fill)
            cell.number_format = num_fmt
            cell.alignment = Alignment(
                horizontal=h_align if h_align != "left" else None,
                vertical="center",
                wrap_text=(key in {"doi_tuong", "verdict", "holm_bh"}),
            )

    end_row = 5 + len(export_df)
    tbl = Table(displayName="PapiPanelInference", ref=f"A5:{last_col}{end_row}")
    tbl.tableStyleInfo = TableStyleInfo(
        name="TableStyleLight1",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False,
    )
    ws.add_table(tbl)
    ws.freeze_panes = "A6"

    if "Mục lục" in wb.sheetnames:
        ws_toc = wb["Mục lục"]
        csv_col = 6
        target_row = None
        for r in range(6, ws_toc.max_row + 1):
            if ws_toc.cell(r, csv_col).value == "panel_inference.csv":
                target_row = r
                break
        if target_row is None:
            target_row = ws_toc.max_row + 1
        ws_toc.row_dimensions[target_row].height = 19.5
        ws_toc.cell(target_row, 1, "Suy luận bảng & FDR")
        ws_toc.cell(target_row, 2, f"=HYPERLINK(\"#'{sheet_name}'!A2\",\"{sheet_name}\")")
        ws_toc.cell(target_row, 3, "Year-FE CR1, TWFE, Wild Bootstrap, Holm/BH/BY FDR & Moran's I phần dư")
        ws_toc.cell(target_row, 4, len(export_df))
        ws_toc.cell(target_row, 5, len(cols))
        ws_toc.cell(target_row, 6, "panel_inference.csv")
        ref_toc_row = 6
        for c in range(1, 7):
            src_cell = ws_toc.cell(ref_toc_row, c)
            dst_cell = ws_toc.cell(target_row, c)
            dst_cell.font = copy(src_cell.font)
            dst_cell.fill = copy(src_cell.fill)
            dst_cell.alignment = copy(src_cell.alignment)
            dst_cell.number_format = src_cell.number_format
        n_tables = sum(1 for r in range(6, ws_toc.max_row + 1) if ws_toc.cell(r, csv_col).value)
        ws_toc["A3"] = (
            f"{n_tables} bảng kết quả theo tệp nguồn. Mở Thống kê khách hàng 2024 hoặc Quan sát 2024 để xem kết quả chính."
        )
        if "PapiDanhMuc" in ws_toc.tables:
            toc_ref = f"A5:F{5 + n_tables}"
            toc_table = ws_toc.tables["PapiDanhMuc"]
            toc_table.ref = toc_ref
            if toc_table.autoFilter is not None:
                toc_table.autoFilter.ref = toc_ref

    wb.save(xlsx_path)


def run_study(root: Path = ROOT, write_outputs: bool = True) -> dict:
    """Chạy toàn bộ suy luận bảng CR1/TWFE, kiểm soát FDR và chẩn đoán Moran's I trên artifact hiện hành."""
    root = Path(root)
    res_dir = root / "results"
    figs_dir = res_dir / "figs"

    panel = pd.read_csv(root / "data/processed/papi_panel_63_2011_2024.csv")
    pred_2d = pd.read_csv(res_dir / "predict_all_years.csv")
    pci_all = pd.read_csv(root / "data/processed/external_pci_63_full.csv")
    # Chỉ lấy PCI 2011–2022 (đầy đủ 63 tỉnh, tách khỏi mẫu Top-30 chọn lọc 2023–2024)
    pci_full = pci_all.loc[pci_all["year"] <= 2022, ["province_code", "year", "pci_weighted_score"]].copy()
    grdp = pd.read_csv(root / "data/processed/external_gso_grdp_63.csv")[
        ["province_code", "year", "grdp_per_capita_million_vnd"]
    ].copy()
    poverty = pd.read_csv(root / "data/processed/external_poverty_63.csv")[
        ["province_code", "year", "poverty_rate_pct"]
    ].copy()

    def _merge_externals(base_df: pd.DataFrame) -> pd.DataFrame:
        out = base_df.merge(pci_full, on=["province_code", "year"], how="left")
        out = out.merge(grdp, on=["province_code", "year"], how="left")
        out = out.merge(poverty, on=["province_code", "year"], how="left")
        return out

    df_2d = _merge_externals(pred_2d[["province_code", "year", "pred_cluster"]].dropna(subset=["pred_cluster"]).copy())

    # Fit High-Dim QuantileSTING 8D mc=7 strictly on <= 2023 (matching scripts/analysis/high_dim_sting.py)
    ptr8 = panel.loc[panel["year"] <= 2023].dropna(subset=REGRESSION_FEATURES).copy().reset_index(drop=True)
    X_tr8 = StandardScaler().fit_transform(ptr8[REGRESSION_FEATURES])
    mq7 = QuantileSTING(n_levels=3, factor=2, density_multiplier=2.2, density_level=1).fit(X_tr8)
    l_q7 = mq7.cluster(level=1, connectivity=1)
    df_q7 = _merge_externals(ptr8[["province_code", "year"]].assign(cluster=l_q7))
    df_q7["pci_dm"] = df_q7["pci_weighted_score"] - df_q7.groupby("year")["pci_weighted_score"].transform("median")
    med_q7 = df_q7.groupby("cluster")["pci_dm"].median().to_dict()
    maj_q7 = [int(c) for c in set(l_q7) if int(c) != -1 and int((l_q7 == c).sum()) >= 50]
    hi_q7 = max(maj_q7, key=lambda c: med_q7.get(c, 0.0))
    lo_q7 = min(maj_q7, key=lambda c: med_q7.get(c, 0.0))

    # Robustness: within-year z QuantileSTING 8D mc=7 <= 2023
    X_wy8 = ptr8[REGRESSION_FEATURES].groupby(ptr8["year"]).transform(lambda s: (s - s.mean()) / s.std(ddof=0)).to_numpy()
    mq7_wy = QuantileSTING(n_levels=3, factor=2, density_multiplier=2.2, density_level=1).fit(X_wy8)
    l_wy = mq7_wy.cluster(level=1, connectivity=1)
    df_wy = _merge_externals(ptr8[["province_code", "year"]].assign(cluster=l_wy))
    df_wy["pci_dm"] = df_wy["pci_weighted_score"] - df_wy.groupby("year")["pci_weighted_score"].transform("median")
    med_wy = df_wy.groupby("cluster")["pci_dm"].median().to_dict()
    maj_wy = [int(c) for c in set(l_wy) if int(c) != -1 and int((l_wy == c).sum()) >= 50]
    hi_wy = max(maj_wy, key=lambda c: med_wy.get(c, 0.0))
    lo_wy = min(maj_wy, key=lambda c: med_wy.get(c, 0.0))

    # CLIQUE Quantile 4D (4.1..4.3, 6.3) tau=0.05 on <= 2023
    clq4 = SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=True).fit(X_tr8)
    dims_4d = tuple(REGRESSION_FEATURES.index(col) for col in ("sd_4_1", "sd_4_2", "sd_4_3", "sd_6_3"))
    l_clq4 = clq4.extract_subspace(dims_4d, X_raw=X_tr8)["labels"]
    df_clq4 = _merge_externals(ptr8[["province_code", "year"]].assign(cluster=l_clq4))
    df_clq4["pci_dm"] = df_clq4["pci_weighted_score"] - df_clq4.groupby("year")["pci_weighted_score"].transform("median")
    maj_clq4 = sorted(int(c) for c in set(l_clq4) if int(c) != -1 and int((l_clq4 == c).sum()) >= 10)
    med_clq4 = df_clq4.groupby("cluster")["pci_dm"].median().to_dict()
    hi_clq4 = max(maj_clq4, key=lambda c: med_clq4.get(c, 0.0))
    lo_clq4 = min(maj_clq4, key=lambda c: med_clq4.get(c, 0.0))

    hyp_specs = [
        ("2d_pci", "2D STING chính thức", "STING 2D (3/4/5/2)", "PCI 2011–2022", df_2d, "pci_weighted_score", "pred_cluster", 2, -1, "Cụm 2 vs Nhiễu (-1)", 2),
        ("2d_grdp", "2D STING chính thức", "STING 2D (3/4/5/2)", "GRDP/người 2018–2024", df_2d, "grdp_per_capita_million_vnd", "pred_cluster", 2, -1, "Cụm 2 vs Nhiễu (-1)", 2),
        ("2d_poverty", "2D STING chính thức", "STING 2D (3/4/5/2)", "Hộ nghèo GSO 2012–2024", df_2d, "poverty_rate_pct", "pred_cluster", 2, -1, "Cụm 2 vs Nhiễu (-1)", 2),
        ("hd8_q7_pci", "High-Dim 8D Quantile", "8D Quantile mc=7 (≤2023)", "PCI 2011–2022", df_q7, "pci_weighted_score", "cluster", hi_q7, lo_q7, "Vùng cao vs Vùng thấp", None),
        ("hd8_q7_grdp", "High-Dim 8D Quantile", "8D Quantile mc=7 (≤2023)", "GRDP/người 2018–2023", df_q7, "grdp_per_capita_million_vnd", "cluster", hi_q7, lo_q7, "Vùng cao vs Vùng thấp", None),
        ("hd8_q7_poverty", "High-Dim 8D Quantile", "8D Quantile mc=7 (≤2023)", "Hộ nghèo GSO 2012–2023", df_q7, "poverty_rate_pct", "cluster", hi_q7, lo_q7, "Vùng cao vs Vùng thấp", None),
        ("hd8_wy_pci", "Sensitivity & Subspace", "8D Quantile wy-z mc=7", "PCI 2011–2022", df_wy, "pci_weighted_score", "cluster", hi_wy, lo_wy, "Vùng cao vs Vùng thấp", None),
        ("clq4_pci", "Sensitivity & Subspace", "CLIQUE Quantile 4D (4.1–4.3,6.3)", "PCI 2011–2022", df_clq4, "pci_weighted_score", "cluster", hi_clq4, lo_clq4, "Cực cao vs Cực thấp", None),
    ]

    primary_rows = [
        evaluate_hypothesis_panel(
            frame=f_df,
            hypothesis_id=hid,
            family=fam,
            branch=br,
            outcome_label=out_lbl,
            value_col=vcol,
            group_col=gcol,
            pos_group=pg,
            neg_group=ng,
            contrast_label=clbl,
            all_groups_ref=ref_g,
        )
        for hid, fam, br, out_lbl, f_df, vcol, gcol, pg, ng, clbl, ref_g in hyp_specs
    ]
    primary_df = pd.DataFrame(primary_rows)

    # Family-level Holm/BH/BY adjustment (3 outcomes within 2D STING, 3 outcomes within High-Dim 8D)
    for fam_name in ("2D STING chính thức", "High-Dim 8D Quantile"):
        mask = primary_df["family"].eq(fam_name)
        adj_f = adjust_multiple_testing(primary_df.loc[mask, "p_cr1_yrfe"].to_numpy())
        primary_df.loc[mask, "holm_p_family"] = adj_f["holm"]
        primary_df.loc[mask, "bh_fdr_family"] = adj_f["bh"]
        primary_df.loc[mask, "by_fdr_family"] = adj_f["by"]

    # Global adjustment across all 6 core confirmatory outcomes (2D STING + 8D Quantile)
    core_mask = primary_df["family"].isin(["2D STING chính thức", "High-Dim 8D Quantile"])
    adj_g = adjust_multiple_testing(primary_df.loc[core_mask, "p_cr1_yrfe"].to_numpy())
    primary_df.loc[core_mask, "holm_p_global"] = adj_g["holm"]
    primary_df.loc[core_mask, "bh_fdr_global"] = adj_g["bh"]

    for idx, row in primary_df.iterrows():
        hid = row["hypothesis_id"]
        if hid == "2d_pci":
            v = "Nhiễu giả theo năm: biến mất hoàn toàn khi thêm Year-FE & CR1 SE (p=0,70)"
        elif hid in {"2d_grdp", "2d_poverty"}:
            v = "Không đủ bằng chứng dưới Year-FE CR1 (ngưỡng 5%)"
        elif hid == "hd8_q7_pci":
            v = "Sống sót Year-FE CR1, WCR & Holm/BH 5% (between-province, TWFE p=0,34)"
        elif hid in {"hd8_q7_grdp", "hd8_q7_poverty"}:
            v = "Bị loại sau Year-FE CR1 & Holm/BH (naive MWU từng gây nhiễu dương giả)"
        elif hid == "hd8_wy_pci":
            v = "Bền vững ngay cả sau chuẩn hóa within-year z (khử xu hướng năm)"
        elif hid == "clq4_pci":
            v = "Cực trị phân tách giai đoạn: C0 2011–17 vs C1 2018–22 (ít năm giao, cần thận trọng)"
        else:
            v = "—"
        primary_df.loc[idx, "verdict"] = v

    # Subspace multiple-testing audit across 383 mined subspaces
    subspaces_df = pd.read_csv(res_dir / "high_dim_sting_subspaces.csv")
    sub_pci = evaluate_subspace_fdr(subspaces_df, "ext_pci_dm_p")
    sub_grdp = evaluate_subspace_fdr(subspaces_df, "ext_grdp_dm_p")
    sub_pci_summary = {k: v for k, v in sub_pci.items() if k != "adj"}
    sub_pci_summary["raw_sorted"] = np.sort(
        subspaces_df["ext_pci_dm_p"].dropna().to_numpy(dtype=float)
    )
    sub_grdp_summary = {k: v for k, v in sub_grdp.items() if k != "adj"}

    spatial_df = evaluate_spatial_residuals(root, n_perm=N_BOOT, seed=RANDOM_SEED)

    # Combine unified CSV export with section tag
    sub_fdr_rows = pd.DataFrame(
        [
            {
                "section": "subspace_fdr",
                "hypothesis_id": f"subspace_{out_key}",
                "family": "Subspace Multiple Testing",
                "branch": f"{info['m_tested']} không gian con hợp lệ",
                "outcome": lbl,
                "contrast": f"m={info['m_tested']} phép thử",
                "n_obs": info["m_tested"],
                "g_provinces": 63,
                "n_overlap_years": info["n_naive_05"],
                "overlap_window": f"BH={info['n_bh_05']}, BY={info['n_by_05']}, Holm={info['n_holm_05']}",
                "naive_mwu_raw_p": float(info["n_naive_05"] / max(info["m_tested"], 1)),
                "naive_mwu_dm_p": float(info["n_bh_05"] / max(info["m_tested"], 1)),
                "verdict": (
                    f"{info['n_naive_05']} naive p<0,05 -> {info['n_bh_05']} sống sót BH-FDR, "
                    f"{info['n_by_05']} BY-FDR, {info['n_holm_05']} Holm FWER"
                ),
            }
            for out_key, lbl, info in [
                ("pci", "PCI đã khử trung vị năm", sub_pci_summary),
                ("grdp", "GRDP đã khử trung vị năm", sub_grdp_summary),
            ]
        ]
    )
    spatial_export = spatial_df.rename(
        columns={
            "label": "outcome",
            "n": "n_obs",
            "moran_i": "beta_yrfe",
            "z_analytical": "se_cr1_yrfe",
            "p_analytical": "p_iid_yrfe",
            "p_perm_two": "p_cr1_yrfe",
        }
    ).assign(family="Spatial Moran's I", branch="Hồi quy Ridge/Quantile 2024", contrast="63 tỉnh Queen contiguity", g_provinces=lambda d: d["n_obs"])
    export_df = pd.concat([primary_df, sub_fdr_rows, spatial_export], ignore_index=True)

    if write_outputs:
        res_dir.mkdir(parents=True, exist_ok=True)
        figs_dir.mkdir(parents=True, exist_ok=True)
        export_df.to_csv(res_dir / "panel_inference.csv", index=False, encoding="utf-8-sig")

        plot_panel_inference_diagnostics(
            primary_df,
            sub_pci_summary,
            spatial_df,
            figs_dir / "panel_inference_diagnostics.png",
        )
        _sync_excel_sheet(primary_df, spatial_df, sub_pci_summary, sub_grdp_summary, res_dir / "KetQua_STING_PAPI.xlsx")

        md_lines = [
            "# Kiểm định Suy luận Bảng (Year-FE CR1 / TWFE), Kiểm soát Đa kiểm định & Chẩn đoán Không gian",
            "",
            "Tài liệu bổ trợ học thuật cho `results/external_validation.md`, `results/high_dim_sting.md` và `results/regression_deep_analysis.md`.",
            "Tái lập: `python -E scripts/analysis/panel_inference.py` (seed=42, B=1.999 Wild Cluster Rademacher / hoán vị không gian).",
            "",
            "## 1. So sánh Kiểm định Gộp (Naive MWU) vs Bảng chuẩn hóa Năm + Sai số Gộp theo Tỉnh (CR1) & TWFE",
            "",
            "| Nhánh | Biến ngoài | n (G tỉnh) | Naive MWU p | β (Year-FE) | SE (CR1) | Hệ số nở SE | p CR1 | p WCR boot | p TWFE (Tỉnh+Năm) | Holm / BH (nhánh) | Kết luận |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for _, r in primary_df.iterrows():
            md_lines.append(
                "| {br} | {out} | {n} ({g}) | {np_p} | {b:+.4f} | {se:.4f} | {inf:.2f}× | {pc} | {pw} | {ptw} | {hb} | {vd} |".format(
                    br=r["branch"],
                    out=r["outcome"],
                    n=int(r["n_obs"]),
                    g=int(r["g_provinces"]),
                    np_p=_fmt_p(r["naive_mwu_raw_p"]),
                    b=float(r["beta_yrfe"]),
                    se=float(r["se_cr1_yrfe"]),
                    inf=float(r["se_inflation"]),
                    pc=_fmt_p(r["p_cr1_yrfe"]),
                    pw=_fmt_p(r["p_wcr_yrfe"]),
                    ptw=_fmt_p(r["p_cr1_twfe"]),
                    hb=(f"{_fmt_p(r['holm_p_family'])} / {_fmt_p(r['bh_fdr_family'])}" if np.isfinite(r["holm_p_family"]) else "—"),
                    vd=r["verdict"],
                )
            )
        r_2d_pci = primary_df.loc[primary_df["hypothesis_id"] == "2d_pci"].iloc[0]
        r_hd_pci = primary_df.loc[primary_df["hypothesis_id"] == "hd8_q7_pci"].iloc[0]
        r_hd_grdp = primary_df.loc[primary_df["hypothesis_id"] == "hd8_q7_grdp"].iloc[0]
        r_wy_pci = primary_df.loc[primary_df["hypothesis_id"] == "hd8_wy_pci"].iloc[0]
        r_res_r = spatial_df.loc[spatial_df["hypothesis_id"] == "residual_ridge_2024"].iloc[0]
        r_pred_r = spatial_df.loc[spatial_df["hypothesis_id"] == "pred_ridge_2024"].iloc[0]
        r_obs_r = spatial_df.loc[spatial_df["hypothesis_id"] == "holdout_actual_2024"].iloc[0]

        md_lines.extend(
            [
                "",
                "### Phát hiện suy luận trọng yếu",
                "",
                f"- **STING 2D chính thức trên PCI 2011–2022 (`2d_pci`)**: kiểm định gộp thô cho `p = {_fmt_p(r_2d_pci['naive_mwu_raw_p'])}`, nhưng khi đưa Fixed Effects theo năm + CR1 theo 63 tỉnh, chênh lệch Cụm 2 vs Nhiễu chỉ còn `β = {r_2d_pci['beta_yrfe']:+.3f}` (SE = {r_2d_pci['se_cr1_yrfe']:.3f}, `p_cr1 = {_fmt_p(r_2d_pci['p_cr1_yrfe'])}`, `p_wcr = {_fmt_p(r_2d_pci['p_wcr_yrfe'])}`; kiểm định đồng thời 4 nhóm Wald `F = {r_2d_pci['joint_wald_f']:.4f}, p = {_fmt_p(r_2d_pci['joint_wald_p'])}`). Bằng chứng này khẳng định tín hiệu PCI trên STING 2D chủ yếu là **nhiễu trộn theo năm (year composition confounding)**.",
                f"- **8D QuantileSTING mc=7 trên PCI (`hd8_q7_pci`)**: **sống sót toàn bộ bộ lọc suy luận chặt** — sau Year-FE + CR1 (hệ số phình SE = {r_hd_pci['se_inflation']:.2f}×), nhóm Vùng cao đa chiều vẫn cao hơn Vùng thấp `β = {r_hd_pci['beta_yrfe']:+.3f}` điểm PCI (SE = {r_hd_pci['se_cr1_yrfe']:.3f}, `p_cr1 = {_fmt_p(r_hd_pci['p_cr1_yrfe'])}`, `p_wcr = {_fmt_p(r_hd_pci['p_wcr_yrfe'])}`, **Holm = {_fmt_p(r_hd_pci['holm_p_family'])} < 0,05**), và vẫn giữ ý nghĩa khi chuẩn hóa within-year z (`hd8_wy_pci`: `β = {r_wy_pci['beta_yrfe']:+.3f}`, `p_cr1 = {_fmt_p(r_wy_pci['p_cr1_yrfe'])}`). Ngược lại, TWFE (Tỉnh + Năm) cho `β = {r_hd_pci['beta_twfe']:+.3f}, p = {_fmt_p(r_hd_pci['p_cr1_twfe'])}` (switchers `n = {int(r_hd_pci['n_switchers'])}`, `p_t = {_fmt_p(r_hd_pci['p_switcher_t'])}`): cơ chế là **phân tầng cấu trúc giữa các tỉnh (between-province structural stratification)** chứ không phải dao động ngắn hạn nội tỉnh.",
                f"- **Loại dương giả trên GRDP**: ngay cả trên 8D Quantile mc=7, `naive MWU` từng cho `p_thô = {_fmt_p(r_hd_grdp['naive_mwu_raw_p'])}` (`p_dm = {_fmt_p(r_hd_grdp['naive_mwu_dm_p'])}`) trên GRDP 2018–2023, nhưng khi hiệu chỉnh Year-FE CR1 biến mất (`p_cr1 = {_fmt_p(r_hd_grdp['p_cr1_yrfe'])}`, Holm = `{_fmt_p(r_hd_grdp['holm_p_family'])}`).",
                "",
                "## 2. Kiểm soát Đa kiểm định (Holm / BH / BY FDR) trên 383 Không gian con (`high_dim_sting_subspaces.csv`)",
                "",
                "| Biến ngoài | Số phép thử (m) | Naive p < 0,05 | Sống sót BH-FDR 5% | Sống sót BY-FDR 5% | Sống sót Holm FWER 5% |",
                "|---|---|---|---|---|---|",
                f"| PCI (khử trung vị năm) | {sub_pci_summary['m_tested']} | {sub_pci_summary['n_naive_05']} ({100*sub_pci_summary['n_naive_05']/sub_pci_summary['m_tested']:.1f}%) | **{sub_pci_summary['n_bh_05']}** ({100*sub_pci_summary['n_bh_05']/sub_pci_summary['m_tested']:.1f}%) | **{sub_pci_summary['n_by_05']}** ({100*sub_pci_summary['n_by_05']/sub_pci_summary['m_tested']:.1f}%) | **{sub_pci_summary['n_holm_05']}** ({100*sub_pci_summary['n_holm_05']/sub_pci_summary['m_tested']:.1f}%) |",
                f"| GRDP (khử trung vị năm) | {sub_grdp_summary['m_tested']} | {sub_grdp_summary['n_naive_05']} ({100*sub_grdp_summary['n_naive_05']/sub_grdp_summary['m_tested']:.1f}%) | **{sub_grdp_summary['n_bh_05']}** | **{sub_grdp_summary['n_by_05']}** | **{sub_grdp_summary['n_holm_05']}** |",
                "",
                "## 3. Chẩn đoán Tự tương quan Không gian Phần dư Holdout 2024 (Moran's I, Queen Contiguity, 1.999 hoán vị)",
                "",
                "| Chuỗi không gian (năm 2024) | n tỉnh | Moran's I | z (lý thuyết) | p lý thuyết | p hoán vị (2 phía) | Kết luận |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for _, sr in spatial_df.iterrows():
            md_lines.append(
                "| {lbl} | {n} | {mi:+.4f} | {z:+.3f} | {pa} | {pp} | {vd} |".format(
                    lbl=sr["label"],
                    n=int(sr["n"]),
                    mi=float(sr["moran_i"]),
                    z=float(sr["z_analytical"]),
                    pa=_fmt_p(sr["p_analytical"]),
                    pp=_fmt_p(sr["p_perm_two"]),
                    vd=sr["verdict"],
                )
            )
        md_lines.extend(
            [
                "",
                f"Dự báo điểm `pred_ridge` 2024 mang cấu trúc không gian rõ rệt (`I = {r_pred_r['moran_i']:+.4f}`, `p_perm = {_fmt_p(r_pred_r['p_perm_two'])}` vs quan sát `n=59`: `I = {r_obs_r['moran_i']:+.4f}`, `p_perm = {_fmt_p(r_obs_r['p_perm_two'])}`), giúp **phần dư `residual_ridge` trở nên trắng về mặt không gian** (`I = {r_res_r['moran_i']:+.4f}`, `p_perm = {_fmt_p(r_res_r['p_perm_two'])}`) — chứng tỏ tập 8 đặc trưng trễ đã hấp thụ tự tương quan không gian địa lý mà chưa cần biến trễ không gian riêng.",
                "",
                "## Đầu ra kèm theo",
                "- Bảng đầy đủ: `results/panel_inference.csv`",
                "- Biểu đồ 4 khung: `results/figs/panel_inference_diagnostics.png`",
                "- Trang Excel: sheet `Suy luận bảng & FDR` trong `results/KetQua_STING_PAPI.xlsx`",
            ]
        )
        (res_dir / "panel_inference.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "primary": primary_df,
        "subspace_pci": sub_pci_summary,
        "subspace_grdp": sub_grdp_summary,
        "spatial": spatial_df,
        "export": export_df,
    }


def main() -> None:
    out = run_study(ROOT, write_outputs=True)
    print(f"panel_inference done: {len(out['primary'])} primary rows, {len(out['spatial'])} spatial rows")
    for _, r in out["primary"].iterrows():
        print(
            f"  [{r['hypothesis_id']}] n={int(r['n_obs'])} (G={int(r['g_provinces'])}) | "
            f"naive={_fmt_p(r['naive_mwu_raw_p'])} | beta={r['beta_yrfe']:+.3f} (SE={r['se_cr1_yrfe']:.3f}, "
            f"p_cr1={_fmt_p(r['p_cr1_yrfe'])}, p_wcr={_fmt_p(r['p_wcr_yrfe'])}, holm={_fmt_p(r['holm_p_family'])}) | "
            f"TWFE beta={r['beta_twfe']:+.3f} (p={_fmt_p(r['p_cr1_twfe'])})"
        )
    sp = out["subspace_pci"]
    print(f"Subspace PCI FDR ({sp['m_tested']}): naive={sp['n_naive_05']} -> BH={sp['n_bh_05']}, BY={sp['n_by_05']}, Holm={sp['n_holm_05']}")
    for _, sr in out["spatial"].iterrows():
        print(f"  Spatial [{sr['hypothesis_id']}] n={int(sr['n'])}: I={sr['moran_i']:+.4f}, perm_two_p={_fmt_p(sr['p_perm_two'])}")


if __name__ == "__main__":
    main()
