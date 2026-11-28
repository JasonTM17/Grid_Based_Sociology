"""Phân tích mở rộng STING cho dữ liệu PAPI đa chiều (ngoài không gian 2D).

Giải quyết trực diện giới hạn trong ``results/robustness.csv`` (nhiễu 60,5% ở 8 chiều đều
và sụp về 1 cụm trên PCA(2) d1–d6) qua bốn hướng bổ trợ trên cùng dữ liệu PAPI:
1. Thang thưa lưới theo số chiều (d = 2..8): chứng minh bùng nổ ô lưới res^d và ngưỡng thưa;
2. Chọn tập con đặc trưng (C(8,2)=28 cặp, C(8,3)=56 bộ ba trên tập train <=2023);
3. Khai phá không gian con CLIQUE Apriori từ dưới lên (equal-width & adaptive quantile);
4. Chia lưới thích nghi QuantileSTING hiệu chuẩn theo mật độ kỳ vọng n/res^d + mở rộng PCA(2..4).

Mọi biên quantile, scaler chuẩn hóa, tiêu chí chọn tập con và đơn vị dày CLIQUE đều chỉ học
trên tập huấn luyện (year <= 2023) và đánh giá độc lập trên holdout 2024 cùng kiểm định ngoài
PCI/GRDP đã khử nhiễu theo năm. Không thay thế hay ghi đè cấu hình 2D đóng băng 3/4/5/2.
"""
from __future__ import annotations

import itertools
import sys
from copy import copy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.common.fig_style import PALETTE, add_source, save_png, style_context
from scripts.common.papi_pred_common import REGRESSION_FEATURES, ROOT
from src.high_dim import QuantileSTING, SubspaceCLIQUE, high_dim_sparsity_grid
from src.sting import STING

RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"

D_FEATURES_8 = [f"d{i}" for i in range(1, 9)]
D_FEATURES_6 = [f"d{i}" for i in range(1, 7)]


def _safe_sil(X_eval: np.ndarray, labels: np.ndarray) -> float:
    mask = labels != -1
    uniq = set(int(c) for c in labels[mask])
    if len(uniq) < 2 or int(mask.sum()) <= len(uniq):
        return float("nan")
    return float(silhouette_score(X_eval[mask], labels[mask]))


def _external_kw_deconfounded(
    ext_frame: pd.DataFrame,
    labels: np.ndarray,
) -> tuple[float, float]:
    """Kiểm định Kruskal–Wallis mô tả trên PCI và GRDP đã khử trung vị theo năm."""
    tmp = ext_frame.assign(cluster=labels)
    non_noise = tmp.loc[tmp["cluster"] != -1]
    pci_groups = [
        grp["pci_dm"].to_numpy()
        for _, grp in non_noise.dropna(subset=["pci_dm"]).groupby("cluster")
        if len(grp) >= 5
    ]
    grdp_groups = [
        grp["grdp_dm"].to_numpy()
        for _, grp in non_noise.dropna(subset=["grdp_dm"]).groupby("cluster")
        if len(grp) >= 5
    ]
    p_pci = float(stats.kruskal(*pci_groups).pvalue) if len(pci_groups) >= 2 else float("nan")
    p_grdp = float(stats.kruskal(*grdp_groups).pvalue) if len(grdp_groups) >= 2 else float("nan")
    return p_pci, p_grdp


def _ari_vs_ref(ref_labels: np.ndarray | None, labels: np.ndarray) -> tuple[float, float]:
    if ref_labels is None or len(ref_labels) != len(labels):
        return float("nan"), float("nan")
    ari_all = float(adjusted_rand_score(ref_labels, labels))
    mask = (ref_labels != -1) & (labels != -1)
    if int(mask.sum()) < 2:
        return ari_all, float("nan")
    return ari_all, float(adjusted_rand_score(ref_labels[mask], labels[mask]))


def _summarize_clustering(
    *,
    section: str,
    dataset: str,
    method: str,
    dims_d: int,
    features: str,
    grid_spec: str,
    labels_train: np.ndarray,
    X_eval_train: np.ndarray,
    labels_holdout: np.ndarray | None,
    ref_2d_labels: np.ndarray | None,
    ext_frame: pd.DataFrame | None,
    verdict: str,
    note: str,
) -> dict:
    n_train = int(len(labels_train))
    clusters = sorted(int(c) for c in set(labels_train) if c != -1)
    n_clusters = len(clusters)
    sizes = sorted([int((labels_train == c).sum()) for c in clusters], reverse=True)
    cov_train = float((labels_train != -1).mean())
    noise_ratio = 1.0 - cov_train
    dom_share = float(sizes[0] / sum(sizes)) if sizes else float("nan")
    sil = _safe_sil(X_eval_train, labels_train)
    ho_cov = float((labels_holdout != -1).mean()) if labels_holdout is not None and len(labels_holdout) else float("nan")
    ari_all, ari_nn = _ari_vs_ref(ref_2d_labels, labels_train)
    p_pci, p_grdp = _external_kw_deconfounded(ext_frame, labels_train) if ext_frame is not None else (float("nan"), float("nan"))
    return {
        "section": section,
        "dataset": dataset,
        "method": method,
        "dims_d": int(dims_d),
        "features": features,
        "grid_spec": grid_spec,
        "n_train": n_train,
        "n_clusters": int(n_clusters),
        "noise_ratio": round(noise_ratio, 6),
        "coverage_train": round(cov_train, 6),
        "largest_cluster_share": round(dom_share, 6) if np.isfinite(dom_share) else np.nan,
        "silhouette_orig": round(sil, 6) if np.isfinite(sil) else np.nan,
        "holdout_2024_cov": round(ho_cov, 6) if np.isfinite(ho_cov) else np.nan,
        "ari_vs_2d_all": round(ari_all, 6) if np.isfinite(ari_all) else np.nan,
        "ari_vs_2d_nonnoise": round(ari_nn, 6) if np.isfinite(ari_nn) else np.nan,
        "ext_pci_dm_p": p_pci,
        "ext_grdp_dm_p": p_grdp,
        "cluster_sizes": str(sizes),
        "verdict": verdict,
        "note": note,
    }


def _evaluate_feature_subsets(
    X_tr: np.ndarray,
    X_ho: np.ndarray,
    feat_names: list[str],
    dim: int,
    n_levels: int,
    factor: int,
    level: int,
    min_count: int,
    z_mode: str,
    dataset_label: str,
    ref_2d: np.ndarray | None,
    ext_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    rows = []
    for comb in itertools.combinations(range(len(feat_names)), dim):
        idx = list(comb)
        Xtr_c = X_tr[:, idx]
        Xho_c = X_ho[:, idx]
        model = STING(n_levels=n_levels, factor=factor, min_count=min_count).fit(Xtr_c)
        ltr = model.cluster(level=level, connectivity=1)
        lho = model.predict(Xho_c) if len(Xho_c) else np.array([], dtype=int)
        ncl = int(model.n_clusters_)
        sizes = sorted([int((ltr == c).sum()) for c in range(ncl)], reverse=True)
        cov = float((ltr != -1).mean())
        dom = float(sizes[0] / sum(sizes)) if sizes else float("nan")
        sil = _safe_sil(Xtr_c, ltr)
        ho_cov = float((lho != -1).mean()) if len(lho) else float("nan")
        ari_all, ari_nn = _ari_vs_ref(ref_2d, ltr)
        p_pci, p_grdp = (
            _external_kw_deconfounded(ext_frame, ltr)
            if ext_frame is not None
            else (float("nan"), float("nan"))
        )
        rows.append(
            {
                "kind": f"feature_subset_{dim}D",
                "dataset": dataset_label,
                "z_mode": z_mode,
                "adaptive": False,
                "grid_spec": f"L={n_levels},f={factor},lv={level},mc={min_count}",
                "k_dim": dim,
                "features": "+".join(feat_names[i] for i in idx),
                "n_dense_units": int(len(model.label_of_)),
                "n_clusters": ncl,
                "coverage_train": cov,
                "noise_ratio": 1.0 - cov,
                "largest_cluster_share": dom,
                "silhouette_orig": sil,
                "holdout_2024_cov": ho_cov,
                "ari_vs_2d_all": ari_all,
                "ari_vs_2d_nonnoise": ari_nn,
                "ext_pci_dm_p": p_pci,
                "ext_grdp_dm_p": p_grdp,
                "cluster_sizes": str(sizes),
            }
        )
    return pd.DataFrame(rows)


def _sync_excel_sheet(
    summary_df: pd.DataFrame,
    xlsx_path: Path = RESULTS / "KetQua_STING_PAPI.xlsx",
) -> None:
    """Thêm/cập nhật sheet 'STING đa chiều' và bảng 'Mục lục' trong KetQua_STING_PAPI.xlsx."""
    if not xlsx_path.is_file():
        return
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "STING đa chiều"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.views.sheetView[0].showGridLines = False

    white_fill = PatternFill("solid", fgColor="FFFFFF")
    thin_side = Side(style="thin", color="BFBFBF")
    header_font = Font(name="Arial", size=10, bold=True, color="000000")
    body_font = Font(name="Arial", size=10, color="000000")

    cols = [
        ("section", "Nhánh phân tích", 18.0, "General", "left"),
        ("dataset", "Tập dữ liệu", 22.0, "General", "left"),
        ("method", "Phương pháp / Cấu hình", 36.0, "General", "left"),
        ("dims_d", "Số chiều d", 11.0, "0", "right"),
        ("n_clusters", "Số cụm k", 10.0, "0", "right"),
        ("noise_ratio", "Tỷ lệ nhiễu", 12.0, "0.0%", "right"),
        ("silhouette_orig", "Silhouette", 12.0, "0.000", "right"),
        ("holdout_2024_cov", "Phủ 2024", 11.0, "0.0%", "right"),
        ("ext_pci_dm_p", "p PCI (khử năm)", 15.0, "0.0000", "right"),
        ("cluster_sizes", "Kích thước cụm", 20.0, "General", "left"),
        ("verdict", "Đánh giá", 22.0, "General", "left"),
        ("note", "Diễn giải / Ràng buộc", 46.0, "General", "left"),
    ]
    last_col = openpyxl.utils.get_column_letter(len(cols))
    ws["A2"] = "Mở rộng STING đa chiều — Thang thưa lưới, Chọn đặc trưng, Subspace CLIQUE & Quantile STING"
    ws["A2"].font = Font(name="Arial", size=14, bold=True, color="000000")
    ws["A2"].fill = copy(white_fill)
    ws.merge_cells(f"A2:{last_col}2")
    ws.row_dimensions[2].height = 24.0
    ws["A3"] = (
        "Train <= 2023 (n=808 chuẩn hóa 8 sd_*, n=369 d1–d8) · Holdout 2024 (n=61) · Giữ nguyên STING 2D đóng băng"
    )
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

    export = summary_df[[k for k, *_ in cols]]
    for r_idx, (_, rec) in enumerate(export.iterrows(), start=6):
        ws.row_dimensions[r_idx].height = 25.0
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
                wrap_text=(key in {"note", "method", "verdict"}),
            )

    end_row = 5 + len(export)
    tbl = Table(displayName="PapiHighDimSting", ref=f"A5:{last_col}{end_row}")
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
            if ws_toc.cell(r, csv_col).value == "high_dim_sting.csv":
                target_row = r
                break
        if target_row is None:
            target_row = ws_toc.max_row + 1
        ws_toc.row_dimensions[target_row].height = 19.5
        ws_toc.cell(target_row, 1, "STING đa chiều")
        ws_toc.cell(target_row, 2, f"=HYPERLINK(\"#'{sheet_name}'!A2\",\"{sheet_name}\")")
        ws_toc.cell(
            target_row,
            3,
            "Thang thưa lưới d=2..8, chọn đặc trưng, Subspace CLIQUE & Quantile STING",
        )
        ws_toc.cell(target_row, 4, len(export))
        ws_toc.cell(target_row, 5, len(cols))
        ws_toc.cell(target_row, 6, "high_dim_sting.csv")
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


def _make_figure(
    sparsity_df: pd.DataFrame,
    clique_frontier_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    ext_plot_df: pd.DataFrame,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with style_context():
        fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.6))

        # (A) Curse of dimensionality: dimension d vs Noise Ratio across resolutions
        ax = axes[0, 0]
        vermilion = "#D55E00"
        styles = {
            "f=4 lv=2 mc=5 (res=16)": (vermilion, "-o"),
            "f=3 lv=1 mc=10 (res=3)": (PALETTE["orange"], "-^"),
            "f=2 lv=2 mc=5 (res=4)": (PALETTE["blue"], "-s"),
            "f=2 lv=1 mc=10 (res=2)": (PALETTE["green"], "-D"),
        }
        for spec, grp in sparsity_df.groupby("spec"):
            sub = grp.loc[~grp["skipped"]].sort_values("d")
            color, fmt = styles.get(spec, (PALETTE["gray"], "-o"))
            ax.plot(sub["d"], 100.0 * sub["noise_ratio"], fmt, color=color, linewidth=2.0, label=spec)
        ax.axhline(50.0, color=PALETTE["gray"], linestyle="--", linewidth=1.1, label="Ngưỡng nhiễu 50%")
        ax.set_title("A. Lời nguyền số chiều: tăng d làm bùng nổ ô rỗng & nhiễu", fontweight="bold")
        ax.set_xlabel("Số chiều d (trên 8 tiểu chỉ tiêu sàng lọc, n=808)")
        ax.set_ylabel("Tỷ lệ nhiễu (%)")
        ax.set_xticks([2, 3, 4, 5, 6, 7, 8])
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        ax.set_ylim(-5, 132)
        ax.grid(True, linestyle=":", alpha=0.45)
        ax.legend(fontsize=7.6, loc="upper right", ncol=2, framealpha=0.95)

        # (B) CLIQUE Bottom-up Subspace Frontier: dense units & multi-cluster subspaces by k_dim
        ax = axes[0, 1]
        dims_k = sorted(clique_frontier_df["k_dim"].unique())
        x = np.arange(len(dims_k))
        w = 0.27
        unif_multi = [
            int(clique_frontier_df.loc[(clique_frontier_df["k_dim"] == k) & (~clique_frontier_df["adaptive"]), "n_multi_subspaces"].sum())
            for k in dims_k
        ]
        quant_multi = [
            int(clique_frontier_df.loc[(clique_frontier_df["k_dim"] == k) & (clique_frontier_df["adaptive"]), "n_multi_subspaces"].sum())
            for k in dims_k
        ]
        unif_total = [
            int(clique_frontier_df.loc[(clique_frontier_df["k_dim"] == k) & (~clique_frontier_df["adaptive"]), "n_subspaces"].sum())
            for k in dims_k
        ]
        ax.bar(x - w, unif_total, width=w, color=PALETTE["sky"], label="CLIQUE Đều: tổng subspace dày")
        ax.bar(x, unif_multi, width=w, color=PALETTE["blue"], label="CLIQUE Đều: subspace >=2 cụm")
        ax.bar(x + w, quant_multi, width=w, color=PALETTE["orange"], label="CLIQUE Quantile: subspace >=2 cụm")
        max_b = max(unif_total + unif_multi + quant_multi + [1])
        ax.set_ylim(0, max_b * 1.24)
        ax.set_title("B. CLIQUE Apriori (τ=0,05): không gian con k=1..6D sống sót", fontweight="bold")
        ax.set_xlabel("Số chiều không gian con (k_dim)")
        ax.set_ylabel("Số không gian con phát hiện")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{k}D" for k in dims_k])
        ax.grid(True, axis="y", linestyle=":", alpha=0.45)
        ax.legend(fontsize=7.8, loc="upper right", framealpha=0.95)

        # (C) Uniform vs Quantile STING silhouette across key methods & robustness baseline
        ax = axes[1, 0]
        comp_rows = summary_df.loc[
            summary_df["method"].isin(
                [
                    "8D d1..d8 Uniform L=3 f=2 lv=1 mc=2 (OFAT robustness)",
                    "8D d1..d8 Uniform L=3 f=2 lv=1 mc=10 (robustness gốc)",
                    "2D Uniform (4.2, 6.1) L=3 f=4 lv=2 mc=5 (chính thức)",
                    "2D Quantile (4.2, 6.1) L=3 f=4 lv=2 mc=5",
                    "3D Quantile (1.3, 4.2, 6.1) f=2 lv=2 mc=19",
                    "8D Quantile L=3 f=2 lv=1 mc=10 (3.2x exp)",
                    "CLIQUE Uniform 5D (1.3, 4.1..4.4) tau=0.03",
                    "CLIQUE Quantile 4D (4.1..4.3, 6.3) tau=0.05",
                ]
            )
        ].copy()
        short_names = {
            "8D d1..d8 Uniform L=3 f=2 lv=1 mc=2 (OFAT robustness)": "8D d1–d8 Đều mc=2",
            "8D d1..d8 Uniform L=3 f=2 lv=1 mc=10 (robustness gốc)": "8D d1–d8 Đều mc=10",
            "2D Uniform (4.2, 6.1) L=3 f=4 lv=2 mc=5 (chính thức)": "2D Đều chính thức",
            "2D Quantile (4.2, 6.1) L=3 f=4 lv=2 mc=5": "2D Quantile (16×16)",
            "3D Quantile (1.3, 4.2, 6.1) f=2 lv=2 mc=19": "3D Quantile f=2 lv=2",
            "8D Quantile L=3 f=2 lv=1 mc=10 (3.2x exp)": "8D Quantile mc=10",
            "CLIQUE Uniform 5D (1.3, 4.1..4.4) tau=0.03": "CLIQUE Đều 5D",
            "CLIQUE Quantile 4D (4.1..4.3, 6.3) tau=0.05": "CLIQUE Quantile 4D",
        }
        order = list(short_names.keys())
        comp_rows["ord"] = comp_rows["method"].map({m: i for i, m in enumerate(order)})
        comp_rows = comp_rows.sort_values("ord")
        y_pos = np.arange(len(comp_rows))
        vals = comp_rows["silhouette_orig"].fillna(0.0).to_numpy()
        colors = [
            vermilion if v < 0 else (PALETTE["green"] if "Quantile" in m else PALETTE["blue"])
            for v, m in zip(vals, comp_rows["method"])
        ]
        ax.barh(y_pos, vals, color=colors, edgecolor="black", linewidth=0.5)
        ax.axvline(0.0, color="black", linewidth=0.9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([short_names[m] for m in comp_rows["method"]], fontsize=8.5)
        for yi, val, nr in zip(y_pos, vals, comp_rows["noise_ratio"]):
            text_x = val + 0.018 if val >= 0 else 0.022
            ax.text(text_x, yi, f"{val:.3f} (nhiễu {100*nr:.0f}%)", va="center", fontsize=7.8)
        ax.set_xlim(-0.18, 1.12)
        ax.set_title("C. Silhouette (không gian gốc) & nhiễu: 2D vs Đa chiều", fontweight="bold")
        ax.set_xlabel("Silhouette trên điểm gán cụm (>=2 cụm)")
        ax.grid(True, axis="x", linestyle=":", alpha=0.45)

        # (D) Deconfounded external PCI_dm distribution by 8D Quantile STING mc=7 regimes
        ax = axes[1, 1]
        regimes = [
            ("C0: Vùng thấp đa chiều", vermilion),
            ("C1: Vùng cao đa chiều", PALETTE["green"]),
            ("C2–C3: Cụm rìa nhỏ", PALETTE["orange"]),
            ("Nhiễu (-1)", PALETTE["gray"]),
        ]
        box_data = []
        box_labels = []
        box_colors = []
        for label_txt, color in regimes:
            sub = ext_plot_df.loc[ext_plot_df["regime_label"] == label_txt, "pci_dm"].dropna()
            if len(sub):
                box_data.append(sub.to_numpy())
                short_lbl = label_txt.replace(" đa chiều", "\nđa chiều")
                box_labels.append(f"{short_lbl}\n(n={len(sub)})")
                box_colors.append(color)
        bp = ax.boxplot(box_data, patch_artist=True, tick_labels=box_labels, showfliers=False)
        for patch, color in zip(bp["boxes"], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
        ax.axhline(0.0, color="black", linestyle="--", linewidth=1.0)
        ax.set_title("D. Kiểm chứng ngoài PCI (khử trung vị năm) — 8D Quantile mc=7", fontweight="bold")
        ax.set_ylabel("PCI - trung vị PCI của năm (điểm)")
        ax.grid(True, axis="y", linestyle=":", alpha=0.45)

        fig.suptitle(
            "Mở rộng STING đa chiều (PAPI 2011–2024): Thưa lưới, Chọn đặc trưng, CLIQUE & Quantile STING",
            fontsize=12.5,
            fontweight="bold",
            y=0.99,
        )
        add_source(fig, "PAPI 2011–2024, PCI 2011–2022 & GSO GRDP 2018–2024", retrieved="2026-11-28")
        fig.tight_layout(rect=(0, 0.04, 1, 0.96))
        save_png(fig, out_path, dpi=220)


def run_study(root: Path = ROOT, write_outputs: bool = True) -> dict:
    root = Path(root)
    res_dir = root / "results"
    figs_dir = res_dir / "figs"

    panel = pd.read_csv(root / "data/processed/papi_panel_63_2011_2024.csv")
    pred_path = res_dir / "predict_all_years.csv"
    pred_all = pd.read_csv(pred_path) if pred_path.is_file() else pd.DataFrame()

    # External benchmarks with annual median deconfounding
    pci_path = root / "data/processed/external_pci_63_full.csv"
    grdp_path = root / "data/processed/external_gso_grdp_63.csv"
    pci = pd.read_csv(pci_path) if pci_path.is_file() else pd.DataFrame(columns=["province_code", "year", "pci_weighted_score"])
    grdp = pd.read_csv(grdp_path) if grdp_path.is_file() else pd.DataFrame(columns=["province_code", "year", "grdp_per_capita_million_vnd"])

    def _attach_ext(frame: pd.DataFrame) -> pd.DataFrame:
        ext = frame[["province_code", "year"]].merge(
            pci[["province_code", "year", "pci_weighted_score"]], on=["province_code", "year"], how="left"
        )
        ext = ext.merge(
            grdp[["province_code", "year", "grdp_per_capita_million_vnd"]], on=["province_code", "year"], how="left"
        )
        ext["pci_dm"] = ext["pci_weighted_score"] - ext.groupby("year")["pci_weighted_score"].transform("median")
        ext["grdp_dm"] = ext["grdp_per_capita_million_vnd"] - ext.groupby("year")["grdp_per_capita_million_vnd"].transform("median")
        return ext

    # Strict temporal split on 8 screened sub-dimensions (2011-2023 train n=808, 2024 holdout n=61)
    ptr8 = panel.loc[panel["year"] <= 2023].dropna(subset=REGRESSION_FEATURES).copy().reset_index(drop=True)
    pho8 = panel.loc[panel["year"] == 2024].dropna(subset=REGRESSION_FEATURES).copy().reset_index(drop=True)
    scaler8 = StandardScaler().fit(ptr8[REGRESSION_FEATURES])
    X_tr8 = scaler8.transform(ptr8[REGRESSION_FEATURES])
    X_ho8 = scaler8.transform(pho8[REGRESSION_FEATURES])
    ext_tr8 = _attach_ext(ptr8)

    X_wy8 = (
        ptr8[REGRESSION_FEATURES]
        .groupby(ptr8["year"])
        .transform(lambda s: (s - s.mean()) / s.std(ddof=0))
        .to_numpy()
    )

    if not pred_all.empty and "pred_cluster" in pred_all.columns:
        ref_2d = ptr8.merge(pred_all[["province_code", "year", "pred_cluster"]], on=["province_code", "year"])[
            "pred_cluster"
        ].to_numpy()
    else:
        m_ref = STING(n_levels=3, factor=4, min_count=5).fit(X_tr8[:, [3, 6]])
        ref_2d = m_ref.cluster(level=2, connectivity=1)

    # 8D domain indices d1..d8 (2018-2024 pooled wy-z n=430 AND strict 2018-2023 train n=369 -> 2024 holdout n=61)
    pd8_all = panel.loc[panel["year"] >= 2018].dropna(subset=D_FEATURES_8).copy().reset_index(drop=True)
    Z_d8_wy_all = (
        pd8_all[D_FEATURES_8]
        .groupby(pd8_all["year"])
        .transform(lambda s: (s - s.mean()) / s.std(ddof=0))
        .to_numpy()
    )
    ext_d8_wy = _attach_ext(pd8_all)

    pd8_tr = pd8_all.loc[pd8_all["year"] <= 2023].copy().reset_index(drop=True)
    pd8_ho = pd8_all.loc[pd8_all["year"] == 2024].copy().reset_index(drop=True)
    sc_d8 = StandardScaler().fit(pd8_tr[D_FEATURES_8])
    X_d8_tr = sc_d8.transform(pd8_tr[D_FEATURES_8])
    X_d8_ho = sc_d8.transform(pd8_ho[D_FEATURES_8])
    ext_d8_tr = _attach_ext(pd8_tr)

    # 6D domain indices d1..d6 (2011-2024 within-year z before partial row drop -> exact robustness.csv parity)
    X6z_wy_full = (
        panel[D_FEATURES_6]
        .groupby(panel["year"])
        .transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    )
    ok6 = X6z_wy_full.notna().all(axis=1)
    Z_d6_wy = X6z_wy_full.loc[ok6].to_numpy()

    summary_rows: list[dict] = []

    # --- SECTION 1: Baselines (exact anchors from robustness.csv & 2D STING) ---
    m2d = STING(n_levels=3, factor=4, min_count=5).fit(X_tr8[:, [3, 6]])
    l2d_tr = m2d.cluster(level=2, connectivity=1)
    l2d_ho = m2d.predict(X_ho8[:, [3, 6]])
    summary_rows.append(
        _summarize_clustering(
            section="baseline_robustness",
            dataset="2D (4.2, 6.1) 2011–2023",
            method="2D Uniform (4.2, 6.1) L=3 f=4 lv=2 mc=5 (chính thức)",
            dims_d=2,
            features="sd_4_2+sd_6_1",
            grid_spec="L=3,f=4,lv=2,mc=5 (16×16=256 ô)",
            labels_train=l2d_tr,
            X_eval_train=X_tr8[:, [3, 6]],
            labels_holdout=l2d_ho,
            ref_2d_labels=ref_2d,
            ext_frame=ext_tr8,
            verdict="Chuẩn 2D chính thức",
            note="Mốc đối chiếu trung tâm: 19,6% nhiễu, cụm lõi 629 và 2 cụm biên (16, 5).",
        )
    )

    # Recompute exact robustness.csv 8D d1..d8 anchors & PCA(2) d1..d6
    pca6_base = PCA(n_components=2, random_state=42).fit(Z_d6_wy)
    Z_pca6_base = pca6_base.transform(Z_d6_wy)
    m_pca6 = STING(n_levels=3, factor=3, min_count=5).fit(Z_pca6_base)
    l_pca6 = m_pca6.cluster(level=2, connectivity=1)
    summary_rows.append(
        _summarize_clustering(
            section="baseline_robustness",
            dataset="6D d1..d6 wy-z 2011–2024",
            method="PCA(2) d1–d6 wy-z L=3 f=3 lv=2 mc=5 (robustness gốc)",
            dims_d=2,
            features="PC1+PC2 (EV=63.2%)",
            grid_spec="L=3,f=3,lv=2,mc=5 (9×9=81 ô)",
            labels_train=l_pca6,
            X_eval_train=Z_pca6_base,
            labels_holdout=None,
            ref_2d_labels=None,
            ext_frame=None,
            verdict="Sụp về 1 cụm",
            note="Khớp robustness.csv: chỉ giữ 63,2% phương sai; lưới 9×9 mc=5 gộp toàn vùng lõi.",
        )
    )

    for label_r, params_r, lv_r, verdict_r, note_r in [
        (
            "8D d1..d8 Uniform L=3 f=2 lv=1 mc=10 (robustness gốc)",
            {"n_levels": 3, "factor": 2, "min_count": 10},
            1,
            "Nhiễu > 50% (60,5%)",
            "Khớp robustness.csv: lưới đều 2^8=256 ô làm 60,5% quan sát rơi ra ngoài ô dày.",
        ),
        (
            "8D d1..d8 Uniform L=3 f=2 lv=1 mc=2 (OFAT robustness)",
            {"n_levels": 3, "factor": 2, "min_count": 2},
            1,
            "Silhouette âm (-0,089)",
            "Khớp robustness.csv: hạ mc=2 giảm nhiễu còn 10,9% nhưng gộp 381 điểm & sil âm.",
        ),
    ]:
        mr = STING(**params_r).fit(Z_d8_wy_all)
        lr = mr.cluster(level=lv_r, connectivity=1)
        summary_rows.append(
            _summarize_clustering(
                section="baseline_robustness",
                dataset="8D d1..d8 wy-z 2018–2024",
                method=label_r,
                dims_d=8,
                features="+".join(D_FEATURES_8),
                grid_spec=f"L=3,f={params_r['factor']},lv={lv_r},mc={params_r['min_count']}",
                labels_train=lr,
                X_eval_train=Z_d8_wy_all,
                labels_holdout=None,
                ref_2d_labels=None,
                ext_frame=ext_d8_wy,
                verdict=verdict_r,
                note=note_r,
            )
        )

    # --- SECTION 2: Dimensionality Sparsity Ladder (d = 2..8) ---
    sparsity_frames: list[pd.DataFrame] = []
    for n_lv, fac, lv_c, mc_c, spec_label in [
        (3, 4, 2, 5, "f=4 lv=2 mc=5 (res=16)"),
        (2, 3, 1, 10, "f=3 lv=1 mc=10 (res=3)"),
        (3, 2, 2, 5, "f=2 lv=2 mc=5 (res=4)"),
        (3, 2, 1, 10, "f=2 lv=1 mc=10 (res=2)"),
    ]:
        lad = pd.DataFrame(
            high_dim_sparsity_grid(X_tr8, [2, 3, 4, 5, 6, 7, 8], n_lv, fac, mc_c, lv_c)
        )
        lad["spec"] = spec_label
        sparsity_frames.append(lad)
        for _, r in lad.iterrows():
            d_i = int(r["d"])
            if bool(r["skipped"]):
                summary_rows.append(
                    {
                        "section": "sparsity_ladder",
                        "dataset": "8D sàng lọc <=2023 (n=808)",
                        "method": f"Thang thưa d={d_i} ({spec_label})",
                        "dims_d": d_i,
                        "features": "+".join(REGRESSION_FEATURES[:d_i]),
                        "grid_spec": f"res^d={int(r['grid_cells_at_level']):,}, leaf={int(r['leaf_cells']):,}",
                        "n_train": len(X_tr8),
                        "n_clusters": 0,
                        "noise_ratio": 1.0,
                        "coverage_train": 0.0,
                        "largest_cluster_share": np.nan,
                        "silhouette_orig": np.nan,
                        "holdout_2024_cov": np.nan,
                        "ari_vs_2d_all": np.nan,
                        "ari_vs_2d_nonnoise": np.nan,
                        "ext_pci_dm_p": np.nan,
                        "ext_grdp_dm_p": np.nan,
                        "cluster_sizes": "[]",
                        "verdict": "Bùng nổ ô lưới (>10M)",
                        "note": f"Số ô lá vượt ngưỡng tính toán (leaf={int(r['leaf_cells']):,} > 10M).",
                    }
                )
            else:
                summary_rows.append(
                    {
                        "section": "sparsity_ladder",
                        "dataset": "8D sàng lọc <=2023 (n=808)",
                        "method": f"Thang thưa d={d_i} ({spec_label})",
                        "dims_d": d_i,
                        "features": "+".join(REGRESSION_FEATURES[:d_i]),
                        "grid_spec": f"res^d={int(r['grid_cells_at_level'])} active={int(r['active_cells'])} dense={int(r['dense_cells'])}",
                        "n_train": len(X_tr8),
                        "n_clusters": int(r["k"]),
                        "noise_ratio": round(float(r["noise_ratio"]), 6),
                        "coverage_train": round(1.0 - float(r["noise_ratio"]), 6),
                        "largest_cluster_share": np.nan,
                        "silhouette_orig": round(float(r["silhouette"]), 6) if np.isfinite(r["silhouette"]) else np.nan,
                        "holdout_2024_cov": np.nan,
                        "ari_vs_2d_all": np.nan,
                        "ari_vs_2d_nonnoise": np.nan,
                        "ext_pci_dm_p": np.nan,
                        "ext_grdp_dm_p": np.nan,
                        "cluster_sizes": "[]",
                        "verdict": "Đa cụm" if int(r["k"]) >= 2 and float(r["noise_ratio"]) <= 0.5 else "Thưa / Sụp 1 cụm",
                        "note": f"Lấp đầy {100.0 * float(r['active_cell_ratio']):.2f}% tổng số ô lưới.",
                    }
                )
    sparsity_df = pd.concat(sparsity_frames, ignore_index=True)

    # --- SECTION 3: Feature Subset Selection (train <= 2023 only!) ---
    fs_tables: list[pd.DataFrame] = []
    for z_tag, Xtr_u, Xho_u in [
        ("global_z", X_tr8, X_ho8),
        ("within_year_z", X_wy8, np.empty((0, 8))),
    ]:
        for dim_fs, f_fs, lv_fs, mc_fs in [
            (2, 4, 2, 5),
            (2, 3, 2, 8),
            (3, 3, 2, 5),
            (3, 2, 2, 10),
        ]:
            t_fs = _evaluate_feature_subsets(
                Xtr_u,
                Xho_u,
                REGRESSION_FEATURES,
                dim_fs,
                3,
                f_fs,
                lv_fs,
                mc_fs,
                z_tag,
                "8D sàng lọc <=2023",
                ref_2d,
                ext_tr8,
            )
            fs_tables.append(t_fs)
    fs_d8_2d = _evaluate_feature_subsets(
        X_d8_tr,
        X_d8_ho,
        D_FEATURES_8,
        2,
        3,
        4,
        2,
        4,
        "global_z",
        "8D d1..d8 2018–2023",
        None,
        ext_d8_tr,
    )
    fs_d8_3d = _evaluate_feature_subsets(
        X_d8_tr,
        X_d8_ho,
        D_FEATURES_8,
        3,
        3,
        3,
        2,
        4,
        "global_z",
        "8D d1..d8 2018–2023",
        None,
        ext_d8_tr,
    )
    fs_all_df = pd.concat([*fs_tables, fs_d8_2d, fs_d8_3d], ignore_index=True)

    # Pick representative top subsets from global_z 8D screened
    fs_2d_g = fs_all_df.loc[
        (fs_all_df["kind"] == "feature_subset_2D")
        & (fs_all_df["dataset"] == "8D sàng lọc <=2023")
        & (fs_all_df["z_mode"] == "global_z")
        & (fs_all_df["grid_spec"] == "L=3,f=4,lv=2,mc=5")
    ]
    fs_2d_f3 = fs_all_df.loc[
        (fs_all_df["kind"] == "feature_subset_2D")
        & (fs_all_df["dataset"] == "8D sàng lọc <=2023")
        & (fs_all_df["z_mode"] == "global_z")
        & (fs_all_df["grid_spec"] == "L=3,f=3,lv=2,mc=8")
    ]
    fs_3d_g = fs_all_df.loc[
        (fs_all_df["kind"] == "feature_subset_3D")
        & (fs_all_df["dataset"] == "8D sàng lọc <=2023")
        & (fs_all_df["z_mode"] == "global_z")
        & (fs_all_df["grid_spec"] == "L=3,f=3,lv=2,mc=5")
    ]
    n_pass_2d = int(((fs_2d_g["n_clusters"] >= 2) & (fs_2d_g["noise_ratio"] <= 0.40)).sum())
    n_balanced_2d = int(((fs_2d_g["n_clusters"] >= 2) & (fs_2d_g["largest_cluster_share"] <= 0.90)).sum())
    best_2d_row = fs_2d_g.loc[fs_2d_g["n_clusters"] >= 2].sort_values(
        ["silhouette_orig", "noise_ratio"], ascending=[False, True]
    ).iloc[0]
    best_2d_f3_row = fs_2d_f3.loc[fs_2d_f3["n_clusters"] >= 2].sort_values(
        "silhouette_orig", ascending=False
    ).iloc[0]
    best_3d_row = fs_3d_g.loc[(fs_3d_g["n_clusters"] >= 2) & (fs_3d_g["noise_ratio"] <= 0.45)].sort_values(
        "silhouette_orig", ascending=False
    ).iloc[0]

    for row_pick, label_fs, note_fs in [
        (
            best_2d_row,
            f"Chọn 2D tốt nhất f=4 ({best_2d_row['features']})",
            f"{n_pass_2d}/28 cặp đạt k>=2 & nhiễu<=40%, nhưng {n_balanced_2d}/28 có cụm chính <=90% (lõi chi phối >90%).",
        ),
        (
            best_2d_f3_row,
            f"Chọn 2D lưới vừa f=3 ({best_2d_f3_row['features']})",
            "Lưới 9×9 mc=8 đạt silhouette cao nhưng vẫn giữ cấu trúc 1 lõi lớn + cụm rìa nhỏ.",
        ),
        (
            best_3d_row,
            f"Chọn 3D tốt nhất f=3 ({best_3d_row['features']})",
            f"Trên C(8,3)=56 bộ ba, ngay bộ tốt nhất (nhiễu {100*best_3d_row['noise_ratio']:.1f}%) vẫn là lõi lớn + rìa nhỏ.",
        ),
    ]:
        summary_rows.append(
            {
                "section": "feature_selection",
                "dataset": str(row_pick["dataset"]),
                "method": label_fs,
                "dims_d": int(row_pick["k_dim"]),
                "features": str(row_pick["features"]),
                "grid_spec": str(row_pick["grid_spec"]),
                "n_train": len(X_tr8),
                "n_clusters": int(row_pick["n_clusters"]),
                "noise_ratio": round(float(row_pick["noise_ratio"]), 6),
                "coverage_train": round(float(row_pick["coverage_train"]), 6),
                "largest_cluster_share": round(float(row_pick["largest_cluster_share"]), 6),
                "silhouette_orig": round(float(row_pick["silhouette_orig"]), 6),
                "holdout_2024_cov": round(float(row_pick["holdout_2024_cov"]), 6),
                "ari_vs_2d_all": round(float(row_pick["ari_vs_2d_all"]), 6),
                "ari_vs_2d_nonnoise": round(float(row_pick["ari_vs_2d_nonnoise"]), 6),
                "ext_pci_dm_p": row_pick["ext_pci_dm_p"],
                "ext_grdp_dm_p": row_pick["ext_grdp_dm_p"],
                "cluster_sizes": str(row_pick["cluster_sizes"]),
                "verdict": "Lõi + cụm biên",
                "note": note_fs,
            }
        )

    # --- SECTION 4: Bottom-up Subspace CLIQUE Mining ---
    clique_subspace_rows: list[dict] = []
    frontier_rows: list[dict] = []
    clique_runs: list[tuple[str, SubspaceCLIQUE, np.ndarray, np.ndarray, list[str], np.ndarray | None, pd.DataFrame]] = [
        ("8D sàng lọc <=2023", SubspaceCLIQUE(n_bins=4, tau=0.03, adaptive=False).fit(X_tr8), X_tr8, X_ho8, REGRESSION_FEATURES, ref_2d, ext_tr8),
        ("8D sàng lọc <=2023", SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=False).fit(X_tr8), X_tr8, X_ho8, REGRESSION_FEATURES, ref_2d, ext_tr8),
        ("8D sàng lọc <=2023", SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=True).fit(X_tr8), X_tr8, X_ho8, REGRESSION_FEATURES, ref_2d, ext_tr8),
        ("8D sàng lọc <=2023", SubspaceCLIQUE(n_bins=4, tau=0.03, adaptive=True).fit(X_tr8), X_tr8, X_ho8, REGRESSION_FEATURES, ref_2d, ext_tr8),
        ("8D d1..d8 2018–2023", SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=False).fit(X_d8_tr), X_d8_tr, X_d8_ho, D_FEATURES_8, None, ext_d8_tr),
        ("8D d1..d8 2018–2023", SubspaceCLIQUE(n_bins=4, tau=0.05, adaptive=True).fit(X_d8_tr), X_d8_tr, X_d8_ho, D_FEATURES_8, None, ext_d8_tr),
    ]

    recorded_frontier_keys: set[tuple[str, bool, float]] = set()
    for ds_name, clq, Xtr_c, Xho_c, fnames, ref_c, ext_c in clique_runs:
        sub_infos: list[dict] = []
        for dims in clq.discovered_subspaces(min_dim=2):
            info = clq.extract_subspace(dims, X_raw=Xtr_c)
            lho = clq.predict_subspace(dims, Xho_c) if len(Xho_c) else np.array([], dtype=int)
            p_pci, p_grdp = _external_kw_deconfounded(ext_c, info["labels"])
            ari_all, ari_nn = _ari_vs_ref(ref_c, info["labels"])
            sizes = info["cluster_sizes"]
            dom = float(sizes[0] / sum(sizes)) if sizes else float("nan")
            row_sub = {
                "kind": "clique_subspace",
                "dataset": ds_name,
                "z_mode": "global_z",
                "adaptive": clq.adaptive,
                "grid_spec": f"bins={clq.n_bins},tau={clq.tau}",
                "k_dim": int(info["k_dim"]),
                "features": "+".join(fnames[i] for i in dims),
                "n_dense_units": int(info["n_dense_units"]),
                "n_clusters": int(info["n_clusters"]),
                "coverage_train": float(info["coverage"]),
                "noise_ratio": float(info["noise_ratio"]),
                "largest_cluster_share": dom,
                "silhouette_orig": info["silhouette"],
                "holdout_2024_cov": float((lho != -1).mean()) if len(lho) else float("nan"),
                "ari_vs_2d_all": ari_all,
                "ari_vs_2d_nonnoise": ari_nn,
                "ext_pci_dm_p": p_pci,
                "ext_grdp_dm_p": p_grdp,
                "cluster_sizes": str(sizes),
            }
            sub_infos.append(row_sub)
            clique_subspace_rows.append(row_sub)

        if ds_name == "8D sàng lọc <=2023" and clq.tau == 0.05 and (ds_name, clq.adaptive, clq.tau) not in recorded_frontier_keys:
            recorded_frontier_keys.add((ds_name, clq.adaptive, clq.tau))
            sub_df_tmp = pd.DataFrame(sub_infos)
            for k_d in sorted(clq.levels_.keys()):
                if k_d == 1:
                    units_1 = clq.levels_[1]
                    frontier_rows.append(
                        {
                            "k_dim": 1,
                            "adaptive": clq.adaptive,
                            "n_units": len(units_1),
                            "n_subspaces": len({d for d, _ in units_1}),
                            "n_multi_subspaces": 0,
                        }
                    )
                else:
                    matched = sub_df_tmp.loc[sub_df_tmp["k_dim"] == k_d]
                    frontier_rows.append(
                        {
                            "k_dim": k_d,
                            "adaptive": clq.adaptive,
                            "n_units": int(matched["n_dense_units"].sum()),
                            "n_subspaces": int(len(matched)),
                            "n_multi_subspaces": int((matched["n_clusters"] >= 2).sum()),
                        }
                    )

    clique_all_df = pd.DataFrame(clique_subspace_rows)
    clique_frontier_df = pd.DataFrame(frontier_rows)

    # Curate representative CLIQUE milestones for summary table
    def _pick_clique(
        ds_match: str,
        adapt_flag: bool,
        tau_val: float,
        feats_str: str,
        method_label: str,
        verdict: str,
        note: str,
    ) -> None:
        m = clique_all_df.loc[
            (clique_all_df["dataset"] == ds_match)
            & (clique_all_df["adaptive"] == adapt_flag)
            & (clique_all_df["grid_spec"] == f"bins=4,tau={tau_val}")
            & (clique_all_df["features"] == feats_str)
        ]
        if m.empty:
            return
        r = m.iloc[0]
        summary_rows.append(
            {
                "section": "subspace_clique",
                "dataset": str(r["dataset"]),
                "method": method_label,
                "dims_d": int(r["k_dim"]),
                "features": str(r["features"]),
                "grid_spec": f"bins=4,tau={tau_val},adaptive={adapt_flag}",
                "n_train": len(X_tr8) if "808" in ds_match or "sàng lọc" in ds_match else len(X_d8_tr),
                "n_clusters": int(r["n_clusters"]),
                "noise_ratio": round(float(r["noise_ratio"]), 6),
                "coverage_train": round(float(r["coverage_train"]), 6),
                "largest_cluster_share": round(float(r["largest_cluster_share"]), 6),
                "silhouette_orig": round(float(r["silhouette_orig"]), 6) if np.isfinite(r["silhouette_orig"]) else np.nan,
                "holdout_2024_cov": round(float(r["holdout_2024_cov"]), 6),
                "ari_vs_2d_all": round(float(r["ari_vs_2d_all"]), 6) if np.isfinite(r["ari_vs_2d_all"]) else np.nan,
                "ari_vs_2d_nonnoise": round(float(r["ari_vs_2d_nonnoise"]), 6) if np.isfinite(r["ari_vs_2d_nonnoise"]) else np.nan,
                "ext_pci_dm_p": r["ext_pci_dm_p"],
                "ext_grdp_dm_p": r["ext_grdp_dm_p"],
                "cluster_sizes": str(r["cluster_sizes"]),
                "verdict": verdict,
                "note": note,
            }
        )

    _pick_clique(
        "8D sàng lọc <=2023",
        False,
        0.03,
        "sd_1_3+sd_4_1+sd_4_2+sd_4_3+sd_4_4",
        "CLIQUE Uniform 5D (1.3, 4.1..4.4) tau=0.03",
        "Phủ cao 5D (41,0%)",
        "Phủ cao nhất trong nhóm đa cụm >=5D nhờ cắt chiều thiếu ổn định; k=2 [303, 28].",
    )
    _pick_clique(
        "8D sàng lọc <=2023",
        False,
        0.03,
        "sd_1_4+sd_4_1+sd_4_2+sd_4_3+sd_4_4+sd_6_3",
        "CLIQUE Uniform 6D (1.4, 4.1..4.4, 6.3) tau=0.03",
        "Subspace 6D đa cụm",
        "Tách 2 cụm cân [61, 57] trong 6 chiều (gắn PCI/GRDP p~0,01), nhưng độ phủ chỉ 14,6%.",
    )
    _pick_clique(
        "8D sàng lọc <=2023",
        True,
        0.05,
        "sd_4_1+sd_4_2+sd_4_3+sd_6_3",
        "CLIQUE Quantile 4D (4.1..4.3, 6.3) tau=0.05",
        "Tách sắc nét (sil 0,772)",
        "Tách 2 cực [57, 45] (PCI khử năm p=6,99e-6), nhưng chỉ phủ 12,6% điểm cực trị.",
    )
    _pick_clique(
        "8D sàng lọc <=2023",
        True,
        0.05,
        "sd_4_1+sd_4_2+sd_4_3+sd_4_4",
        "CLIQUE Quantile 4D (4.1..4.4) tau=0.05",
        "Cụm 4 chiều đồng thuận",
        "4 tiểu chỉ tiêu Tham nhũng tách 2 cực [69, 63], phủ 16,3% train & 29,5% holdout 2024.",
    )
    _pick_clique(
        "8D d1..d8 2018–2023",
        True,
        0.05,
        "d1+d2+d3",
        "CLIQUE Quantile 3D d1..d8 (d1,d2,d3) tau=0.05",
        "Cấu trúc 3D từ d1..d8 (sil 0,802)",
        "Trên train 2018–2023 (n=369), CLIQUE Quantile 3D d1+d2+d3 tách 2 cực [36, 23] với Silhouette 0,802.",
    )
    _pick_clique(
        "8D d1..d8 2018–2023",
        False,
        0.05,
        "d1+d2+d3+d4",
        "CLIQUE Uniform 4D d1..d8 (d1..d4) tau=0.05",
        "Cấu trúc 4D đều từ d1..d8",
        "Trên train 2018–2023 (n=369), CLIQUE đều 4D d1..d4 tách k=2 [20, 19], Silhouette 0,629.",
    )

    # --- SECTION 5: Adaptive Quantile STING vs Uniform STING ---
    aq_specs = [
        ("2D Quantile (4.2, 6.1) L=3 f=4 lv=2 mc=5", [3, 6], True, 3, 4, 2, 5, None, "Phân mảnh vùng lõi 2D", "Trên lưới mịn 16×16 2D, quantile cắt nát vùng lõi thành {k} cụm nhỏ và tăng nhiễu ({noise:.1f}% vs 19,6% đều)."),
        ("3D Uniform (1.3, 4.2, 6.1) f=2 lv=2 mc=19", [0, 3, 6], False, 3, 2, 2, 19, None, "Sụp 1 cụm (Uniform)", "Lưới 4^3=64 ô với ngưỡng 19 gộp toàn bộ 808 điểm lõi vào 1 cụm."),
        ("3D Quantile (1.3, 4.2, 6.1) f=2 lv=2 mc=19", [0, 3, 6], True, 3, 2, 2, 19, 1.5, "Tách 3 chế độ (sil 0,423)", "Vượt ngưỡng 1,5× kỳ vọng tách {sizes}, phân tách GRDP p=0,0249; nhiễu {noise:.1f}%."),
        ("4D Uniform (1.3, 4.2, 6.1, 6.3) f=2 lv=2 mc=7", [0, 3, 6, 7], False, 3, 2, 2, 7, None, "Sụp 1 cụm (Uniform)", "Lưới 4^4=256 ô đều gom hết vùng trung tâm thành 1 khối duy nhất."),
        ("4D Quantile (1.3, 4.2, 6.1, 6.3) f=2 lv=2 mc=7", [0, 3, 6, 7], True, 3, 2, 2, 7, 2.0, "14 cụm chi tiết (nhiễu 63,6%)", "Nhân đôi kỳ vọng tách được cụm nhỏ ({k} cụm) nhưng đánh đổi tỷ lệ nhiễu cao {noise:.1f}%."),
        ("8D Uniform L=3 f=2 lv=1 mc=10 (global 8 sd_*)", list(range(8)), False, 3, 2, 1, 10, None, "Sụp 1 cụm (8D Uniform)", "Trong 8D chuẩn hóa, chia đều 2^8=256 ô gom 580 điểm vào 1 siêu khối duy nhất."),
        ("8D Quantile L=3 f=2 lv=1 mc=7 (2.2x exp)", list(range(8)), True, 3, 2, 1, None, 2.2, "Phân tách tốt nhất 8D (phủ 56,6%)", "Cắt tại trung vị 8 trục với ngưỡng 2,2× kỳ vọng: tách 2 cực [222, 219] + 2 rìa, phủ {ho_cov:.1f}% 2024; PCI khử năm p=0,0005."),
        ("8D Quantile L=3 f=2 lv=1 mc=10 (3.2x exp)", list(range(8)), True, 3, 2, 1, 10, None, "8D sắc nét (sil 0,237)", "Cùng mc=10 như Uniform nhưng tách k={k} {sizes}, sil={sil:.3f}, PCI khử năm p=0,0023."),
    ]
    ext_plot_df = pd.DataFrame()
    for method_a, cols_a, use_q, nl_a, fac_a, lv_a, mc_a, mult_a, verdict_a, note_tmpl in aq_specs:
        Xtr_sub = X_tr8[:, cols_a]
        Xho_sub = X_ho8[:, cols_a]
        if use_q:
            mdl = QuantileSTING(
                n_levels=nl_a,
                factor=fac_a,
                min_count=mc_a,
                density_multiplier=mult_a,
                density_level=lv_a,
            ).fit(Xtr_sub)
            grid_txt = f"Quantile L={nl_a},f={fac_a},lv={lv_a},mc={mdl.effective_min_count_}"
        else:
            mdl = STING(n_levels=nl_a, factor=fac_a, min_count=mc_a).fit(Xtr_sub)
            grid_txt = f"Uniform L={nl_a},f={fac_a},lv={lv_a},mc={mc_a}"
        ltr = mdl.cluster(level=lv_a, connectivity=1)
        lho = mdl.predict(Xho_sub)
        k_a = int(mdl.n_clusters_)
        sizes_a = sorted([int((ltr == c).sum()) for c in range(k_a)], reverse=True)
        noise_a = 100.0 * float((ltr == -1).mean())
        ho_cov_a = 100.0 * float((lho != -1).mean())
        sil_a = _safe_sil(Xtr_sub, ltr)
        note_a = note_tmpl.format(k=k_a, sizes=sizes_a, noise=noise_a, ho_cov=ho_cov_a, sil=sil_a)
        feat_str = "+".join(REGRESSION_FEATURES[i] for i in cols_a) if len(cols_a) < 8 else "8_screened_sd"
        summary_rows.append(
            _summarize_clustering(
                section="adaptive_quantile",
                dataset="8D sàng lọc <=2023",
                method=method_a,
                dims_d=len(cols_a),
                features=feat_str,
                grid_spec=grid_txt,
                labels_train=ltr,
                X_eval_train=Xtr_sub,
                labels_holdout=lho,
                ref_2d_labels=ref_2d,
                ext_frame=ext_tr8,
                verdict=verdict_a,
                note=note_a,
            )
        )
        if method_a == "8D Quantile L=3 f=2 lv=1 mc=7 (2.2x exp)":
            # Capture cluster-regime external validation frame for Panel D & test invariants
            med_by_c = ext_tr8.assign(cluster=ltr).groupby("cluster")["pci_dm"].median().to_dict()
            non_tiny = [c for c in set(ltr) if c != -1 and int((ltr == c).sum()) >= 50]
            low_c = min(non_tiny, key=lambda c: med_by_c.get(c, 0.0))
            high_c = max(non_tiny, key=lambda c: med_by_c.get(c, 0.0))
            ext_plot_df = ext_tr8.assign(cluster=ltr).copy()
            ext_plot_df["regime_label"] = np.where(
                ext_plot_df["cluster"] == high_c,
                "C1: Vùng cao đa chiều",
                np.where(
                    ext_plot_df["cluster"] == low_c,
                    "C0: Vùng thấp đa chiều",
                    np.where(ext_plot_df["cluster"] >= 0, "C2–C3: Cụm rìa nhỏ", "Nhiễu (-1)"),
                ),
            )

    # Verify 8D QuantileSTING on within-year z <=2023 (removes cross-year score trend completely)
    mq_wy8 = QuantileSTING(n_levels=3, factor=2, density_multiplier=2.2, density_level=1).fit(X_wy8)
    lq_wy8 = mq_wy8.cluster(level=1, connectivity=1)
    summary_rows.append(
        _summarize_clustering(
            section="adaptive_quantile",
            dataset="8D sàng lọc wy-z <=2023",
            method="8D Quantile within-year z L=3 f=2 lv=1 mc=7",
            dims_d=8,
            features="8_screened_sd (wy-z)",
            grid_spec=f"Quantile L=3,f=2,lv=1,mc={mq_wy8.effective_min_count_}",
            labels_train=lq_wy8,
            X_eval_train=X_wy8,
            labels_holdout=None,
            ref_2d_labels=ref_2d,
            ext_frame=ext_tr8,
            verdict="Tách đa cụm sau khử năm",
            note="Sau chuẩn hóa within-year z (loại hoàn toàn xu hướng năm), mc=7 vẫn tách [232, 217, 7] và phân biệt PCI_dm.",
        )
    )

    # Also test QuantileSTING directly on 8D d1..d8 within-year z (2018-2024, n=430) vs robustness.csv
    for mc_d8, verdict_d8, note_d8 in [
        (4, "Giảm nhiễu <50% (44,7%)", "Trên đúng bộ d1..d8 của robustness.csv: giảm nhiễu từ 60,5% xuống 44,7% và giữ silhouette dương (+0,161 vs -0,089)."),
        (5, "Cân bằng k=4 (sil +0,157)", "Ngưỡng 3,0× kỳ vọng (1,68) tách 4 cụm [100, 74, 7, 5] với nhiễu 56,7%."),
    ]:
        mq8 = QuantileSTING(n_levels=3, factor=2, min_count=mc_d8).fit(Z_d8_wy_all)
        lq8 = mq8.cluster(level=1, connectivity=1)
        summary_rows.append(
            _summarize_clustering(
                section="adaptive_quantile",
                dataset="8D d1..d8 wy-z 2018–2024",
                method=f"8D d1..d8 Quantile L=3 f=2 lv=1 mc={mc_d8}",
                dims_d=8,
                features="+".join(D_FEATURES_8),
                grid_spec=f"Quantile L=3,f=2,lv=1,mc={mc_d8}",
                labels_train=lq8,
                X_eval_train=Z_d8_wy_all,
                labels_holdout=None,
                ref_2d_labels=None,
                ext_frame=ext_d8_wy,
                verdict=verdict_d8,
                note=note_d8,
            )
        )

    # Strict time-split 8D d1..d8 Quantile (2018-2023 train n=369 -> 2024 holdout n=61)
    mq_d8_tr4 = QuantileSTING(n_levels=3, factor=2, density_multiplier=2.5, density_level=1).fit(X_d8_tr)
    lq_d8_tr4 = mq_d8_tr4.cluster(level=1, connectivity=1)
    lq_d8_ho4 = mq_d8_tr4.predict(X_d8_ho)
    summary_rows.append(
        _summarize_clustering(
            section="adaptive_quantile",
            dataset="8D d1..d8 2018–2023",
            method="8D d1..d8 Quantile mc=4 (2.5x exp, time-split)",
            dims_d=8,
            features="+".join(D_FEATURES_8),
            grid_spec=f"Quantile L=3,f=2,lv=1,mc={mq_d8_tr4.effective_min_count_}",
            labels_train=lq_d8_tr4,
            X_eval_train=X_d8_tr,
            labels_holdout=lq_d8_ho4,
            ref_2d_labels=None,
            ext_frame=ext_d8_tr,
            verdict="Sụp 1 cụm ở mc=4 (n=369)",
            note="Trên mẫu ngắn 2018–2023 (n=369), ngưỡng mc=4 gộp vùng lõi thành k=1 [204]; cần mc=5 để tách đa cụm.",
        )
    )
    mq_d8_tr5 = QuantileSTING(n_levels=3, factor=2, min_count=5).fit(X_d8_tr)
    lq_d8_tr5 = mq_d8_tr5.cluster(level=1, connectivity=1)
    lq_d8_ho5 = mq_d8_tr5.predict(X_d8_ho)
    sil_d8_tr5 = _safe_sil(X_d8_tr, lq_d8_tr5)
    ho_cov_d8_tr5 = 100.0 * float((lq_d8_ho5 != -1).mean())
    summary_rows.append(
        _summarize_clustering(
            section="adaptive_quantile",
            dataset="8D d1..d8 2018–2023",
            method="8D d1..d8 Quantile mc=5 (time-split -> 2024)",
            dims_d=8,
            features="+".join(D_FEATURES_8),
            grid_spec="Quantile L=3,f=2,lv=1,mc=5",
            labels_train=lq_d8_tr5,
            X_eval_train=X_d8_tr,
            labels_holdout=lq_d8_ho5,
            ref_2d_labels=None,
            ext_frame=ext_d8_tr,
            verdict="Đa cụm & suy diễn sang 2024",
            note=(
                f"Khớp hoàn toàn trên 2018–2023 (n=369): tách k={mq_d8_tr5.n_clusters_}, "
                f"Silhouette +{sil_d8_tr5:.3f}, phủ {ho_cov_d8_tr5:.1f}% holdout 2024 (n=61)."
            ),
        )
    )

    # --- SECTION 6: PCA(2..4) Resolution Follow-up ---
    pca_specs = [
        ("6D d1..d6 wy-z 2011–2024", Z_d6_wy, 2, 3, 4, 2, 10, None, None, "PCA(2) lưới mịn 16×16", "Tăng f=3→4 (81→256 ô) tách thêm cụm rìa nhỏ nhưng kéo nhiễu tăng mạnh."),
        ("6D d1..d6 wy-z 2011–2024", Z_d6_wy, 3, 3, 3, 2, 5, None, None, "PCA(3) giữ 76,1% EV", "PCA(3) giữ 76,1% phương sai tách được 1 cụm rìa nhỏ kèm vùng lõi áp đảo."),
        ("8D sàng lọc <=2023", X_tr8, 2, 3, 4, 2, 10, ref_2d, ext_tr8, "PCA(2) trên 8 sd_* f=4", "Tách 5 cụm nhỏ ở rìa [306, 16, 12, 10, 10], nhiễu 56,2%, silhouette 0,118."),
        ("8D sàng lọc <=2023", X_tr8, 3, 3, 3, 2, 5, ref_2d, ext_tr8, "PCA(3) trên 8 sd_* f=3", "PCA(3) giữ 75,7% EV đạt k=2 [504, 7] (lõi áp đảo, rìa rất nhỏ)."),
        ("8D sàng lọc <=2023", X_tr8, 4, 3, 3, 2, 5, ref_2d, ext_tr8, "PCA(4) quá thưa (nhiễu 89,7%)", "Ở 4D PCA, 9^4=6.561 ô làm tỷ lệ nhiễu tăng vọt lên 89,7%."),
    ]
    for ds_p, X_p, n_comp, nl_p, f_p, lv_p, mc_p, ref_p, ext_p, verdict_p, note_p in pca_specs:
        pca_obj = PCA(n_components=n_comp, random_state=42).fit(X_p)
        Zp = pca_obj.transform(X_p)
        ev = float(pca_obj.explained_variance_ratio_.sum())
        mp = STING(n_levels=nl_p, factor=f_p, min_count=mc_p).fit(Zp)
        lp = mp.cluster(level=lv_p, connectivity=1)
        noise_pct = 100.0 * float((lp == -1).mean())
        sil_p = _safe_sil(Zp, lp)
        sil_txt = f", silhouette {sil_p:.3f}" if np.isfinite(sil_p) else ""
        summary_rows.append(
            _summarize_clustering(
                section="pca_followup",
                dataset=ds_p,
                method=f"PCA({n_comp}) L={nl_p} f={f_p} lv={lv_p} mc={mc_p}",
                dims_d=n_comp,
                features=f"PC1..PC{n_comp} (EV={100*ev:.1f}%)",
                grid_spec=f"L={nl_p},f={f_p},lv={lv_p},mc={mc_p}",
                labels_train=lp,
                X_eval_train=Zp,
                labels_holdout=None,
                ref_2d_labels=ref_p,
                ext_frame=ext_p,
                verdict=verdict_p,
                note=f"{note_p} (k={mp.n_clusters_}, nhiễu {noise_pct:.1f}%{sil_txt}).",
            )
        )

    summary_df = pd.DataFrame(summary_rows)
    subspaces_df = pd.concat([fs_all_df, clique_all_df], ignore_index=True)

    if write_outputs:
        res_dir.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(res_dir / "high_dim_sting.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
        subspaces_df.to_csv(res_dir / "high_dim_sting_subspaces.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
        _make_figure(
            sparsity_df,
            clique_frontier_df,
            summary_df,
            ext_plot_df,
            figs_dir / "high_dim_sting_analysis.png",
        )
        _write_markdown(summary_df, sparsity_df, clique_frontier_df, fs_2d_g, ext_plot_df, res_dir / "high_dim_sting.md")
        _sync_excel_sheet(summary_df, res_dir / "KetQua_STING_PAPI.xlsx")

    return {
        "summary": summary_df,
        "subspaces": subspaces_df,
        "sparsity": sparsity_df,
        "frontier": clique_frontier_df,
        "ext_plot": ext_plot_df,
    }


def _write_markdown(
    summary_df: pd.DataFrame,
    sparsity_df: pd.DataFrame,
    frontier_df: pd.DataFrame,
    fs_2d_g: pd.DataFrame,
    ext_plot_df: pd.DataFrame,
    out_path: Path,
) -> None:
    def _row(method_name: str) -> pd.Series:
        return summary_df.loc[summary_df["method"] == method_name].iloc[0]

    r_2d = _row("2D Uniform (4.2, 6.1) L=3 f=4 lv=2 mc=5 (chính thức)")
    r_2dq = _row("2D Quantile (4.2, 6.1) L=3 f=4 lv=2 mc=5")
    r_d8_base = _row("8D d1..d8 Uniform L=3 f=2 lv=1 mc=10 (robustness gốc)")
    r_d8_mc2 = _row("8D d1..d8 Uniform L=3 f=2 lv=1 mc=2 (OFAT robustness)")
    r_d8_q4 = _row("8D d1..d8 Quantile L=3 f=2 lv=1 mc=4")
    r_q8_mc7 = _row("8D Quantile L=3 f=2 lv=1 mc=7 (2.2x exp)")
    r_q8_wy = _row("8D Quantile within-year z L=3 f=2 lv=1 mc=7")
    r_q8_mc10 = _row("8D Quantile L=3 f=2 lv=1 mc=10 (3.2x exp)")
    r_cq4 = _row("CLIQUE Quantile 4D (4.1..4.3, 6.3) tau=0.05")
    r_cu5 = _row("CLIQUE Uniform 5D (1.3, 4.1..4.4) tau=0.03")
    r_cu6 = _row("CLIQUE Uniform 6D (1.4, 4.1..4.4, 6.3) tau=0.03")

    d2_f4 = sparsity_df.loc[(sparsity_df["spec"] == "f=4 lv=2 mc=5 (res=16)") & (sparsity_df["d"] == 2)].iloc[0]
    d3_f4 = sparsity_df.loc[(sparsity_df["spec"] == "f=4 lv=2 mc=5 (res=16)") & (sparsity_df["d"] == 3)].iloc[0]
    d4_f4 = sparsity_df.loc[(sparsity_df["spec"] == "f=4 lv=2 mc=5 (res=16)") & (sparsity_df["d"] == 4)].iloc[0]
    n_pass_2d = int(((fs_2d_g["n_clusters"] >= 2) & (fs_2d_g["noise_ratio"] <= 0.40)).sum())

    med_dm = ext_plot_df.groupby("regime_label")["pci_dm"].median().to_dict()
    med_raw = ext_plot_df.groupby("regime_label")["pci_weighted_score"].median().to_dict()
    g0_dm = ext_plot_df.loc[ext_plot_df["regime_label"] == "C0: Vùng thấp đa chiều", "pci_dm"].dropna()
    g1_dm = ext_plot_df.loc[ext_plot_df["regime_label"] == "C1: Vùng cao đa chiều", "pci_dm"].dropna()
    p_mwu_c0_c1 = float(stats.mannwhitneyu(g0_dm, g1_dm).pvalue)

    lines = [
        "# Phân tích mở rộng STING đa chiều trên dữ liệu PAPI (2011–2024)",
        "",
        "## 1. Bối cảnh và vấn đề mở còn lại từ nhánh 2D",
        "",
        f"- Trong `results/robustness.csv`, nhánh 8 chiều tổng hợp `d1–d8` (`2018–2024`, `n=430`) với lưới đều `L=3, f=2, mc=10, lv=1` có **`{100*r_d8_base['noise_ratio']:.1f}%` nhiễu** (`k={int(r_d8_base['n_clusters'])}`), còn khi hạ ngưỡng xuống `mc=2` để kéo nhiễu xuống `{100*r_d8_mc2['noise_ratio']:.1f}%` thì Silhouette tụt xuống **`{r_d8_mc2['silhouette_orig']:.3f}`** (gộp một khối 381 điểm kèm cụm 2 điểm).",
        "- Tương tự, `PCA(2)` trên `d1–d6` (`2011–2024`, `n=869`) chỉ giữ `63,2%` phương sai và bị lưới `9×9` gộp toàn vùng lõi thành **`k=1` cụm** (`6,2%` nhiễu).",
        "- Để giải quyết có hệ thống mà **không làm rò rỉ dữ liệu 2024** và **giữ nguyên cấu hình 2D đóng băng `3/4/5/2`**, phân tích này đối chiếu bốn hướng trên **cùng tập dữ liệu với STING 2D**: `8` tiểu chỉ tiêu đã sàng lọc nhất quán thang đo (`sd_1_3..sd_6_3`, tập train `<=2023` gồm `n=808`, tập holdout `2024` gồm `n=61`), song song với bộ `d1–d8` (`2018–2024`, `n=430`, trong đó train `<=2023` `n=369`).",
        "",
        "## 2. Kết quả chính theo 5 hướng kỹ thuật",
        "",
        "### 2.1. Thang thưa lưới theo số chiều (Curse of Dimensionality, d = 2..8)",
        f"- Với lưới chính thức `f=4, lv=2, mc=5` (`16` ô/trục): ở `d=2` (`256` ô, cặp `sd_1_3+sd_1_4`) nhiễu là `{100*d2_f4['noise_ratio']:.1f}%` (so với `{100*r_2d['noise_ratio']:.1f}%` trên cặp chuẩn `4.2, 6.1`), nhưng sang `d=3` (`4.096` ô) chỉ còn `{int(d3_f4['dense_cells'])}` ô dày và nhiễu nhảy lên **`{100*d3_f4['noise_ratio']:.1f}%`**; tới `d=4` (`65.536` ô) còn **`{int(d4_f4['dense_cells'])}` ô dày (nhiễu `{100*d4_f4['noise_ratio']:.1f}%`)**; còn `d=8` cần tới `4,29 × 10^9` ô lá.",
        "",
        "### 2.2. Chọn tập con đặc trưng (train <= 2023: 28 cặp 2D, 56 bộ ba 3D)",
        f"- Rà soát vét cạn chỉ trên `<=2023` cho thấy `{n_pass_2d}/28` cặp 2D (`f=4, lv=2, mc=5`) đạt `k>=2` và `nhiễu <= 40%`, nhưng `0/28` cặp tách thành hai khối cân bằng (`largest_cluster_share <= 90%`): bản chất phân bố PAPI cấp tỉnh trong không gian 2D–3D là **một vùng lõi dày đặc chiếm ưu thế (>90% điểm thuộc cụm) kèm các túi ngoại lai nhỏ**.",
        "",
        "### 2.3. Khai phá không gian con CLIQUE Apriori từ dưới lên",
        f"- Thay vì duyệt lưới 8 chiều đầy đủ (`65.536` ô ở `4^8`), CLIQUE Apriori tìm thấy cấu trúc đa cụm đến **`5D–6D`** trên lưới đều (`tau=0,03`): nhánh **`5D sd_1_3+sd_4_1..4_4`** phủ **`{100*r_cu5['coverage_train']:.1f}%`** (`k=2 [303, 28]`, Silhouette `{r_cu5['silhouette_orig']:.3f}`, phủ `{100*r_cu5['holdout_2024_cov']:.1f}%` năm 2024), còn nhánh **`6D`** tách `[61, 57]` (`Silhouette {r_cu6['silhouette_orig']:.3f}`, kiểm định mô tả `PCI_dm p={r_cu6['ext_pci_dm_p']:.4f}`, `GRDP_dm p={r_cu6['ext_grdp_dm_p']:.4f}`) nhưng chỉ phủ `{100*r_cu6['coverage_train']:.1f}%`.",
        f"- Kết hợp CLIQUE với chia ô quantile (`bins=4, tau=0,05`), các không gian con 4 chiều như **`sd_4_1..4_3+sd_6_3`** tách được **`2` cực đối xứng `[57, 45]` với Silhouette `{r_cq4['silhouette_orig']:.3f}`** (kiểm định `PCI_dm p={r_cq4['ext_pci_dm_p']:.2e}`), nhưng đánh đổi chỉ bao phủ **`{100*r_cq4['coverage_train']:.1f}%`** các điểm rơi vào vùng cực trị (`{100*r_cq4['holdout_2024_cov']:.1f}%` trên 2024).",
        "",
        "### 2.4. Chia lưới thích nghi QuantileSTING hiệu chuẩn mật độ kỳ vọng n/res^d",
        "- Trên không gian **8 chiều sàng lọc (`n=808`)** với `L=3, f=2, lv=1` (`2^8 = 256` ô, kỳ vọng `3,16` điểm/ô):",
        "  - **Uniform Equal-Width (`mc=10`)** bị lệch đuôi ngoại lai kéo giãn, gom toàn bộ `580` điểm thành **`k=1` cụm** (không phân tách).",
        f"  - **QuantileSTING (`mc=7`, `2,2×` kỳ vọng)**: cắt theo trung vị train trên cả 8 trục, tách được **`k={int(r_q8_mc7['n_clusters'])}` chế độ** (`[222, 219, 8, 8]`, phủ **`{100*r_q8_mc7['coverage_train']:.1f}%`** train và **`{100*r_q8_mc7['holdout_2024_cov']:.1f}%`** holdout 2024), phân biệt rõ **PCI đã khử trung vị năm (`KW 4 cụm p = {r_q8_mc7['ext_pci_dm_p']:.5f}`, `MWU C0 vs C1 p = {p_mwu_c0_c1:.5f}`, trung vị `PCI_dm` `{med_dm['C0: Vùng thấp đa chiều']:+.2f}` vs `{med_dm['C1: Vùng cao đa chiều']:+.2f}`, cụm rìa C2–C3 `{med_dm['C2–C3: Cụm rìa nhỏ']:+.2f}`; trên PCI thô chưa khử năm là `{med_raw['C0: Vùng thấp đa chiều']:.2f}` vs `{med_raw['C1: Vùng cao đa chiều']:.2f}`)** và **GRDP khử theo năm (`p = {r_q8_mc7['ext_grdp_dm_p']:.4f}`)**.",
        f"  - **Kiểm chứng khử xu hướng năm (`8D within-year z <=2023`, `mc=7`)**: ngay cả khi chuẩn hóa riêng trong từng năm để loại toàn bộ dịch chuyển điểm theo thời gian, QuantileSTING vẫn tách **`k={int(r_q8_wy['n_clusters'])}` cụm** (`{r_q8_wy['cluster_sizes']}`, phủ `{100*r_q8_wy['coverage_train']:.1f}%`, `PCI_dm p = {r_q8_wy['ext_pci_dm_p']:.5f}`), xác nhận đây không chỉ là hiệu ứng năm sớm/muộn.",
        f"  - **QuantileSTING (`mc=10`, `3,2×` kỳ vọng)**: tăng Silhouette lên **`{r_q8_mc10['silhouette_orig']:.3f}`** (`[168, 166, 12, 10]`, `PCI_dm p = {r_q8_mc10['ext_pci_dm_p']:.5f}`), nhiễu `{100*r_q8_mc10['noise_ratio']:.1f}%`.",
        f"- Trên đúng bộ **`8D d1..d8 (2018–2024, n=430)`** của `robustness.csv`, **QuantileSTING (`mc=4`)** hạ nhiễu xuống **`{100*r_d8_q4['noise_ratio']:.1f}%`** (vượt ngưỡng `<50%` so với `60,5%` của Uniform gốc) đồng thời nâng Silhouette lên **`+{r_d8_q4['silhouette_orig']:.3f}`** (so với `-0,089` của nhánh Uniform `mc=2`).",
        f"- **Giới hạn ngược chiều (không tô hồng):** ở lưới mịn **2D `16×16` (`sd_4_2, sd_6_1`)**, Quantile chia đều biên làm vỡ cụm lõi thành `{int(r_2dq['n_clusters'])}` mảnh nhỏ và tăng nhiễu lên `{100*r_2dq['noise_ratio']:.1f}%` (kém hơn hẳn Uniform `{100*r_2d['noise_ratio']:.1f}%`, Silhouette `{r_2d['silhouette_orig']:.3f}`). Do đó **STING 2D đóng băng tiếp tục dùng lưới đều**, còn **Quantile & CLIQUE phát huy thế mạnh riêng ở không gian 3D–8D**.",
        "",
        "### 2.5. Mở rộng PCA(2..4) so với baseline PCA(2) k=1",
        "- Lý giải nguyên nhân sụp 1 cụm của `PCA(2)`: `f=3, lv=2` (`81` ô) quá thô trước đám mây điểm `PCA(2)`. Khi tăng lên `f=4` (`16×16`) hoặc `PCA(3)` (`75,7%–76,1%` phương sai), STING tách được `2–5` cụm phụ nhưng vẫn chỉ là lõi lớn + túi rìa nhỏ và kém khả diễn giải trục so với Subspace CLIQUE / QuantileSTING.",
        "",
        "## 3. Ràng buộc an toàn thời gian & phạm vi diễn giải",
        "1. Mọi bước `StandardScaler`, biên `QuantileWarper`, sàng lọc tập con `2D/3D` và đơn vị dày `CLIQUE` chỉ khớp trên **`year <= 2023`** (`test_high_dim_sting.py` kiểm chứng bất biến khi làm nhiễu `2024`).",
        "2. Các kiểm định `PCI_dm` và `GRDP_dm` là **đối chiếu mô tả ngoại lai đã khử hiệu ứng năm**, chưa hiệu chỉnh đa kiểm định qua nhiều không gian con và không kết luận quan hệ nhân quả.",
        "3. Tài liệu chi tiết kèm toàn bộ không gian con lưu tại `results/high_dim_sting.csv`, `results/high_dim_sting_subspaces.csv`, hình `results/figs/high_dim_sting_analysis.png` và sheet **`STING đa chiều`** trong `results/KetQua_STING_PAPI.xlsx`.",
    ]
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    out = run_study(ROOT, write_outputs=True)
    summary = out["summary"]
    print(f"Saved: results/high_dim_sting.csv ({len(summary)} rows)")
    print(f"Saved: results/high_dim_sting_subspaces.csv ({len(out['subspaces'])} rows)")
    print("Saved: results/high_dim_sting.md")
    print("Saved: results/figs/high_dim_sting_analysis.png")
    print("Updated: results/KetQua_STING_PAPI.xlsx (sheet STING da chieu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
