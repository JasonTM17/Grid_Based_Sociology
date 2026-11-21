"""Tham số và biểu đồ cho thực nghiệm phân cụm mô tả ở giữa kỳ."""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from scripts.common.fig_style import CLUSTER_COLORS, PALETTE, style_context
from scripts.common.papi_pred_common import FEATURE_LABELS, describe_grid_assignment
from sting import STING

FEATURES = ("sd_4_2", "sd_6_1")
GRID = {"n_levels": 3, "factor": 4, "min_count": 5, "cluster_level": 2, "connectivity": 1}
THRESHOLDS = (3, 5, 8)
K_CANDIDATES = (2, 3, 4, 5)
KMEANS_OPTIONS = {"n_init": 10, "random_state": 42}
DBSCAN_OPTIONS = {"eps": 0.2, "min_samples": 5}
CELL_Z_EXAMPLE = 2.0


def fit_grid(
    points: np.ndarray, min_count: int = GRID["min_count"], *, significance_z: float | None = None,
) -> tuple[STING, np.ndarray]:
    """Dựng lưới theo biên từng trục và gom các ô dày kề cạnh."""
    model = STING(n_levels=GRID["n_levels"], factor=GRID["factor"], min_count=min_count,
                  significance_z=significance_z).fit(points)
    labels = model.cluster(level=GRID["cluster_level"], connectivity=GRID["connectivity"])
    return model, labels


def reference_grid_assignments(panel: pd.DataFrame, reference_year: int) -> tuple[pd.DataFrame, int]:
    """Gán hai năm liên tiếp lên lưới dựng từ dữ liệu đến hết năm tham chiếu."""
    scores = panel.loc[panel.year.le(reference_year), list(FEATURES)].dropna()
    scaler = StandardScaler().fit(scores)
    grid, _ = fit_grid(scaler.transform(scores))
    recent = panel.loc[panel.year.isin([reference_year, reference_year + 1])]
    return describe_grid_assignment(recent, FEATURES, scaler, grid), len(scores)


def clustered_silhouette(points: np.ndarray, labels: np.ndarray) -> float:
    """Tính silhouette trên các điểm thuộc cụm, theo khoảng cách Euclid."""
    assigned = labels >= 0
    return float(silhouette_score(points[assigned], labels[assigned]))


def raw_dbscan_radius(scale: np.ndarray) -> float:
    """Bán kính hình tròn có cùng diện tích với elip lân cận gốc của ε trên hai trục z."""
    return float(DBSCAN_OPTIONS["eps"] * np.sqrt(scale[0] * scale[1]))


def scaling_comparison_figure(points: np.ndarray, model: STING, comparisons):
    """Vẽ nhãn trước và sau chuẩn hóa trên cùng tọa độ hiển thị z."""
    with style_context():
        fig, axes = plt.subplots(2, 3, figsize=(12.8, 7.1), dpi=140, sharex=True, sharey=True,
                                 layout="constrained")
        for column, (name, before, after, changed) in enumerate(comparisons):
            for row, labels in enumerate((before, after)):
                ax = axes[row, column]
                clusters = np.unique(labels[labels >= 0])
                noise = labels == -1
                if column == 0:
                    for index in model.label_of_:
                        cell = model.cells_[model.cluster_level_][index]
                        ax.add_patch(Rectangle(cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                                               facecolor="#EFF4F6", edgecolor="#BACBD2", linewidth=0.45))
                ax.scatter(*points[noise].T, s=10, color=PALETTE["gray"], alpha=0.6, linewidths=0)
                for label in clusters:
                    color = plt.get_cmap("tab10")(int(label) % 10)
                    ax.scatter(*points[labels == label].T, s=11, color=color, alpha=0.74, linewidths=0)
                if row == 1 and changed.any():
                    ax.scatter(*points[changed].T, s=36, facecolors="none", edgecolors="#172433",
                               linewidths=0.65, zorder=4)
                ax.set_title(f"{name} · {len(clusters)} cụm · {int(noise.sum())} nhiễu", fontsize=12)
                ax.grid(alpha=0.16)
                if column == 0:
                    stage = "Chạy điểm gốc" if row == 0 else "Chạy sau z-score"
                    ax.set_ylabel(f"{stage}\n6.1 Y tế công lập (z)", fontsize=11)
                if row == 1:
                    ax.set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z)", fontsize=10)
        fig.suptitle(f"Cùng {len(points)} quan sát PAPI trước và sau chuẩn hóa", fontsize=16)
        legend = [
            Rectangle((0, 0), 1, 1, facecolor="#EFF4F6", edgecolor="#BACBD2", label="Ô dày của STING"),
            Line2D([], [], marker="o", color=PALETTE["gray"], linestyle="none", label="Nhiễu"),
            Line2D([], [], marker="o", markerfacecolor="none", markeredgecolor="#172433",
                   linestyle="none", label="Đổi cụm K-means hoặc đổi trạng thái nhiễu DBSCAN"),
        ]
        fig.legend(handles=legend, loc="outside lower center", ncol=3)
        return fig


def comparison_figure(points: np.ndarray, model: STING, labels: np.ndarray, kmeans):
    """Vẽ hai cách phân cụm trên cùng hệ trục, kèm ô dày và tâm cụm."""
    with style_context():
        fig, (grid_ax, km_ax) = plt.subplots(
            1, 2, figsize=(11.6, 4.65), sharex=True, sharey=True, layout="constrained",
        )
        for key, label in model.label_of_.items():
            cell = model.cells_[model.cluster_level_][key]
            width, height = cell.bounds_max - cell.bounds_min
            color = CLUSTER_COLORS.get(label, PALETTE["purple"])
            grid_ax.add_patch(Rectangle(
                cell.bounds_min, width, height, facecolor="none", edgecolor=color,
                linewidth=0.85, alpha=0.68,
            ))
        for ax, assignments in ((grid_ax, labels), (km_ax, kmeans.labels_)):
            for group in np.unique(assignments):
                inside = assignments == group
                name = "Nhiễu" if group == -1 else f"Cụm {group}"
                ax.scatter(
                    points[inside, 0], points[inside, 1], s=10, alpha=0.78, linewidths=0,
                    color=CLUSTER_COLORS.get(group, PALETTE["purple"]),
                    label=f"{name} ({inside.sum()})",
                )
            ax.grid(alpha=0.18)
            ax.set_xlabel("4.2 Kiểm soát tham nhũng trong dịch vụ công (z)")

        centers = kmeans.cluster_centers_
        km_ax.scatter(*centers.T, color="#1A1A1A", marker="X", s=54,
                      edgecolor="white", linewidths=0.8, label="Tâm cụm", zorder=3)
        if kmeans.n_clusters == 2 and not np.array_equal(centers[0], centers[1]):
            mid = centers.mean(axis=0)
            dx, dy = centers[1] - centers[0]
            km_ax.axline(mid, mid + [-dy, dx], color="#444444", linestyle="--", linewidth=1.1,
                         label="Ranh giới", zorder=2.2)
        grid_ax.set_ylabel(f"{FEATURE_LABELS[FEATURES[1]]} (z-score)")
        grid_ax.set_title(f"STING · {model.n_clusters_} cụm từ các ô dày")
        km_ax.set_title(f"K-means · k = {kmeans.n_clusters}")
        for ax in (grid_ax, km_ax):
            ax.legend(loc="upper left", ncols=2, frameon=True, framealpha=0.95, fontsize=9)
        return fig


def sting_steps_figure(figsize: tuple[float, float] = (12.2, 3.15), dpi: int = 160):
    """Vẽ 4 bước STING trên đồ thị 2D cho ví dụ lưới 3×3 (15 điểm, min_count=3)."""
    counts = np.array([[4, 3, 0], [1, 0, 4], [0, 0, 3]])
    offsets = {
        1: [(0.38, 0.36)],
        3: [(0.24, 0.28), (0.62, 0.28), (0.43, 0.58)],
        4: [(0.24, 0.24), (0.60, 0.24), (0.24, 0.56), (0.60, 0.56)],
    }
    pts_list: list[tuple[float, float]] = []
    cell_of_pt: list[tuple[int, int]] = []
    for row in range(3):
        cell_y = 2 - row
        for col in range(3):
            cnt = int(counts[row, col])
            for dx, dy in offsets.get(cnt, ()):
                pts_list.append((col + dx, cell_y + dy))
                cell_of_pt.append((col, cell_y))
    pts = np.asarray(pts_list, dtype=float)
    pt_cells = np.asarray(cell_of_pt, dtype=int)

    model = STING(n_levels=2, factor=3, min_count=3).fit(pts)
    labels = model.cluster(level=1, connectivity=1)
    assert model.n_clusters_ == 2 and int((labels == -1).sum()) == 1

    titles = (
        "1. Điểm đầu vào (n = 15)",
        "2. Phủ lưới 3×3 & đếm ô",
        "3. Lọc ô dày (count ≥ 3)",
        "4. Nối kề 4 hướng → 2 cụm",
    )
    teal_hi = "#D4E8EA"
    blue_hi = "#DBE8F4"
    gold_hi = "#FDE8BA"
    empty_hi = "#F3F5F7"

    with style_context():
        fig, axes = plt.subplots(
            1, 4, figsize=figsize, dpi=dpi, sharex=True, sharey=True, layout="constrained"
        )
        for step_idx, (ax, title) in enumerate(zip(axes, titles, strict=True)):
            ax.set_xlim(0.0, 3.0)
            ax.set_ylim(0.0, 3.0)
            ax.set_aspect("equal", adjustable="box")
            ax.set_xticks([0, 1, 2, 3])
            ax.set_yticks([0, 1, 2, 3])
            ax.tick_params(labelsize=8)
            ax.set_title(title, fontsize=10.5, pad=6)

            if step_idx >= 1:
                for row in range(3):
                    cy = 2 - row
                    for col in range(3):
                        cnt = int(counts[row, col])
                        if step_idx == 1:
                            fill = "#EFF6F9" if cnt > 0 else "#FFFFFF"
                        elif step_idx == 2:
                            fill = teal_hi if cnt >= 3 else (gold_hi if cnt > 0 else empty_hi)
                        else:
                            if (col, cy) in ((0, 2), (1, 2)):
                                fill = teal_hi
                            elif (col, cy) in ((2, 1), (2, 0)):
                                fill = blue_hi
                            elif cnt > 0:
                                fill = gold_hi
                            else:
                                fill = empty_hi
                        ax.add_patch(
                            Rectangle(
                                (col, cy), 1.0, 1.0,
                                facecolor=fill, edgecolor="#5D748A", linewidth=0.95, zorder=1,
                            )
                        )
                        txt_col = "#0F2B46" if cnt >= 3 else ("#8A5A00" if cnt > 0 else "#9AA5B1")
                        ax.text(
                            col + 0.80, cy + 0.80, str(cnt),
                            ha="center", va="center", fontsize=10.5, fontweight="bold",
                            color=txt_col,
                            bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.82),
                            zorder=3,
                        )
            else:
                ax.grid(alpha=0.22, linestyle=":")

            if step_idx < 3:
                if step_idx == 2:
                    dense_mask = np.array([counts[2 - cy, cx] >= 3 for cx, cy in pt_cells])
                    ax.scatter(pts[dense_mask, 0], pts[dense_mask, 1], s=44,
                               color=PALETTE["blue"], edgecolors="white", linewidths=0.7, zorder=4)
                    ax.scatter(pts[~dense_mask, 0], pts[~dense_mask, 1], s=55,
                               color=PALETTE["gray"], marker="X", zorder=4)
                    ax.text(0.46, 1.13, "ô thưa → −1", ha="center", va="bottom",
                            fontsize=8, color="#8A5A00", fontweight="bold", zorder=5)
                else:
                    ax.scatter(pts[:, 0], pts[:, 1], s=44,
                               color="#1E3D5E", edgecolors="white", linewidths=0.7, zorder=4)
                    if step_idx == 1:
                        ax.text(2.50, 2.38, "ô lưu:\ncount, μ, σ,\nmin, max",
                                ha="center", va="center", fontsize=7.5, color="#4A5D70", zorder=4)
            else:
                grp_a = np.array([tuple(c) in ((0, 2), (1, 2)) for c in pt_cells])
                grp_b = np.array([tuple(c) in ((2, 1), (2, 0)) for c in pt_cells])
                noise_m = ~(grp_a | grp_b)
                ax.scatter(pts[grp_a, 0], pts[grp_a, 1], s=46, color=PALETTE["green"],
                           edgecolors="white", linewidths=0.7, zorder=4)
                ax.scatter(pts[grp_b, 0], pts[grp_b, 1], s=46, color=PALETTE["blue"],
                           edgecolors="white", linewidths=0.7, zorder=4)
                ax.scatter(pts[noise_m, 0], pts[noise_m, 1], s=60, color=PALETTE["gray"],
                           marker="X", zorder=5)
                for (x0, y0), (x1, y1), col_ar in (
                    ((0.76, 2.66), (1.24, 2.66), PALETTE["green"]),
                    ((2.50, 1.22), (2.50, 0.78), PALETTE["blue"]),
                ):
                    ax.add_patch(FancyArrowPatch(
                        (x0, y0), (x1, y1), arrowstyle="<->", mutation_scale=11,
                        linewidth=1.5, color=col_ar, zorder=5,
                    ))
                ax.text(1.00, 2.06, "Cụm A (7)", ha="center", va="bottom",
                        fontsize=8.2, fontweight="bold", color="#0F5C48", zorder=5)
                ax.text(2.44, 0.14, "Cụm B (7)", ha="center", va="bottom",
                        fontsize=8.2, fontweight="bold", color=PALETTE["blue"], zorder=5)
                ax.text(0.46, 1.13, "Nhiễu (−1)", ha="center", va="bottom",
                        fontsize=8, fontweight="bold", color="#5A5A5A", zorder=5)
                ax.annotate(
                    "Chạm góc\n(≠ nối)",
                    xy=(2.0, 2.0), xytext=(2.46, 2.34),
                    ha="center", va="center", fontsize=7.6, color="#B04E27", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#B04E27", lw=1.1),
                    zorder=5,
                )
        return fig


def kmeans_elbow_figure(points: np.ndarray, ks=range(1, 7), sil_ks=K_CANDIDATES):
    """Vẽ WCSS (Elbow) và Silhouette theo k cho K-means đối chứng."""
    ks_list = list(ks)
    wcss = [float(KMeans(n_clusters=k, **KMEANS_OPTIONS).fit(points).inertia_) for k in ks_list]
    sil_list = list(sil_ks)
    sils = [
        float(silhouette_score(points, KMeans(n_clusters=k, **KMEANS_OPTIONS).fit_predict(points)))
        for k in sil_list
    ]
    best_k = sil_list[int(np.argmax(sils))]
    best_sil = max(sils)

    with style_context():
        fig, (ax_wcss, ax_sil) = plt.subplots(1, 2, figsize=(10.6, 3.8), dpi=150, layout="constrained")
        ax_wcss.plot(ks_list, wcss, "o-", color=PALETTE["blue"], linewidth=1.8, markersize=6)
        ax_wcss.axvline(best_k, color="#667788", linestyle="--", linewidth=1.1)
        ax_wcss.set_xticks(ks_list)
        ax_wcss.set_title("WCSS theo k (giảm dần đều, không gãy gập rõ)", fontsize=11)
        ax_wcss.set_xlabel("Số cụm k")
        ax_wcss.set_ylabel("WCSS (Inertia)")
        ax_wcss.grid(alpha=0.2)

        ax_sil.plot(sil_list, sils, "o-", color=PALETTE["orange"], linewidth=1.8, markersize=6)
        ax_sil.axvline(best_k, color="#667788", linestyle="--", linewidth=1.1)
        ax_sil.annotate(
            f"k = {best_k} ({best_sil:.4f})",
            xy=(best_k, best_sil), xytext=(best_k + 0.38, best_sil - 0.015),
            fontsize=9.5, fontweight="bold", color="#8A5A00",
            arrowprops=dict(arrowstyle="->", color=PALETTE["orange"], lw=1.1),
        )
        ax_sil.set_xticks(sil_list)
        ax_sil.set_title(f"Silhouette theo k — cao nhất tại k = {best_k}", fontsize=11)
        ax_sil.set_xlabel("Số cụm k")
        ax_sil.set_ylabel("Silhouette trung bình")
        ax_sil.grid(alpha=0.2)
        return fig


def noise_and_trap_figure(
    points: np.ndarray, grid_model: STING, labels: np.ndarray, *, title_prefix: str = "PAPI 2011–2024",
):
    """3 panel đồ thị giải thích nhiễu STING (−1) và hai cái bẫy hay gặp."""
    import copy

    z_flag = (np.abs(points) > 3).any(axis=1)
    noise_mask = labels == -1
    sparse_clean = noise_mask & ~z_flag
    n_noise = int(noise_mask.sum())
    n_clean_noise = int(sparse_clean.sum())
    n_zflag = int(z_flag.sum())

    trimmed_model, trimmed_labels = fit_grid(points[~z_flag])
    trimmed_noise = int((trimmed_labels == -1).sum())

    conn8_model = copy.deepcopy(grid_model)
    conn8_labels = conn8_model.cluster(level=conn8_model.cluster_level_, connectivity=2)
    conn8_noise = int((conn8_labels == -1).sum())

    lo, hi = grid_model.bounds_min_, grid_model.bounds_max_
    pad_x = (hi[0] - lo[0]) * 0.06
    pad_y = (hi[1] - lo[1]) * 0.06

    def _draw_grid(ax, m: STING, *, grid_color: str = "#CBD5E1", dense_fill: str = "#EBF5F5") -> None:
        res = m.factor ** m.cluster_level_
        b_lo, b_hi = m.bounds_min_, m.bounds_max_
        step = (b_hi - b_lo) / res
        for idx in m.label_of_:
            cell = m.cells_[m.cluster_level_][idx]
            ax.add_patch(Rectangle(
                cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                facecolor=dense_fill, edgecolor="#94B8BC", linewidth=0.5, zorder=1,
            ))
        for i in range(res + 1):
            ax.axvline(b_lo[0] + i * step[0], ymin=0, ymax=1, color=grid_color, linewidth=0.35, zorder=0.5)
            ax.axhline(b_lo[1] + i * step[1], xmin=0, xmax=1, color=grid_color, linewidth=0.35, zorder=0.5)

    with style_context():
        fig, axes = plt.subplots(
            1, 3, figsize=(13.0, 4.35), dpi=150, sharex=True, sharey=True, layout="constrained"
        )


        ax = axes[0]
        _draw_grid(ax, grid_model)
        ax.add_patch(Rectangle(
            (-3.0, -3.0), 6.0, 6.0,
            facecolor="none", edgecolor="#D55E00", linestyle="--", linewidth=1.35,
            label="Khung |z| ≤ 3 (vùng 'sạch' 1D)", zorder=4,
        ))
        ax.scatter(points[~noise_mask, 0], points[~noise_mask, 1], s=10,
                   color=PALETTE["blue"], alpha=0.68, linewidths=0, label=f"Vào cụm ({int((~noise_mask).sum())})", zorder=2)
        ax.scatter(points[sparse_clean, 0], points[sparse_clean, 1], s=18,
                   color=PALETTE["gray"], marker="x", linewidths=0.95,
                   label=f"−1 trong |z|≤3 ({n_clean_noise})", zorder=3)
        ax.scatter(points[z_flag, 0], points[z_flag, 1], s=32,
                   color="#D55E00", marker="D", edgecolors="white", linewidths=0.5,
                   label=f"Điểm |z|>3 ({n_zflag})", zorder=5)
        ax.set_title(
            f"1. Khung |z| ≤ 3 vs nhiễu −1 ({title_prefix})\n"
            f"{n_clean_noise}/{n_noise} điểm −1 vẫn nằm TRONG |z| ≤ 3",
            fontsize=10.5,
        )
        ax.set_ylabel("6.1 Y tế công lập (z-score)")
        ax.legend(loc="upper left", fontsize=7.6, framealpha=0.92)


        ax = axes[1]
        _draw_grid(ax, trimmed_model, grid_color="#E2CFC9", dense_fill="#F3EEEA")
        ax.add_patch(Rectangle(
            lo, *(hi - lo), facecolor="none", edgecolor="#64748B", linestyle=":", linewidth=1.2,
            label="Biên [min, max] cũ", zorder=3,
        ))
        t_lo, t_hi = trimmed_model.bounds_min_, trimmed_model.bounds_max_
        ax.add_patch(Rectangle(
            t_lo, *(t_hi - t_lo), facecolor="none", edgecolor="#D55E00", linestyle="--", linewidth=1.3,
            label="Biên mới co lại", zorder=4,
        ))
        kept = points[~z_flag]
        t_ass = trimmed_labels >= 0
        ax.scatter(kept[t_ass, 0], kept[t_ass, 1], s=10, color=PALETTE["green"],
                   alpha=0.68, linewidths=0, label=f"Vào cụm ({int(t_ass.sum())})", zorder=2)
        ax.scatter(kept[~t_ass, 0], kept[~t_ass, 1], s=18, color=PALETTE["gray"], marker="x",
                   linewidths=0.95, label=f"Nhiễu mới ({trimmed_noise})", zorder=3)
        ax.scatter(points[z_flag, 0], points[z_flag, 1], s=36, facecolors="none", edgecolors="#D55E00",
                   marker="D", linewidths=1.1, label=f"Đã xóa ({n_zflag})", zorder=5)
        ax.set_title(
            f"2. BẪY: Xóa |z|>3 rồi dựng lại lưới\n"
            f"{trimmed_model.n_clusters_} cụm · {trimmed_noise}/{len(trimmed_labels)} nhiễu "
            f"({trimmed_noise / len(trimmed_labels):.1%}, TĂNG!)",
            fontsize=10.5,
        )
        ax.set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z-score)")
        ax.legend(loc="upper left", fontsize=7.6, framealpha=0.92)


        ax = axes[2]
        _draw_grid(ax, conn8_model, dense_fill="#E4EFF7")
        c8_ass = conn8_labels >= 0
        ax.scatter(points[c8_ass, 0], points[c8_ass, 1], s=10, color=PALETTE["blue"],
                   alpha=0.72, linewidths=0, label=f"1 cụm gộp ({int(c8_ass.sum())})", zorder=2)
        ax.scatter(points[~c8_ass, 0], points[~c8_ass, 1], s=18, color=PALETTE["gray"], marker="x",
                   linewidths=0.95, label=f"Nhiễu giữ nguyên ({conn8_noise})", zorder=3)
        ax.set_title(
            f"3. BẪY: Đổi kề 8 hướng (connectivity=2)\n"
            f"Gộp qua góc → {conn8_model.n_clusters_} cụm · {conn8_noise}/{len(conn8_labels)} nhiễu (KHÔNG giảm)",
            fontsize=10.5,
        )
        ax.legend(loc="upper left", fontsize=7.6, framealpha=0.92)

        axes[0].set_xlim(min(lo[0], -3.15) - pad_x, max(hi[0], 3.15) + pad_x)
        axes[0].set_ylim(min(lo[1], -3.15) - pad_y, max(hi[1], 3.15) + pad_y)
        return fig


def sensitivity_grid_figure(points: np.ndarray):
    """Vẽ 4 cấu hình trên cùng 869 điểm để thấy tác động của ngưỡng và độ mịn lưới."""
    configs = (
        (2, 3, "Ngưỡng min_count = 3 (lưới 16×16)"),
        (2, 5, "Cấu hình chính: min_count = 5 (lưới 16×16)"),
        (2, 8, "Ngưỡng min_count = 8 (lưới 16×16)"),
        (1, 5, "Đổi mức lưới: level = 1 (lưới 4×4, mc = 5)"),
    )
    with style_context():
        fig, axes = plt.subplots(
            2, 2, figsize=(10.8, 7.6), dpi=150, sharex=True, sharey=True, layout="constrained"
        )
        for ax, (lvl, mc, caption) in zip(axes.ravel(), configs, strict=True):
            m = STING(n_levels=GRID["n_levels"], factor=GRID["factor"], min_count=mc).fit(points)
            lab = m.cluster(level=lvl, connectivity=GRID["connectivity"])
            res = m.factor ** lvl
            b_lo, b_hi = m.bounds_min_, m.bounds_max_
            step = (b_hi - b_lo) / res
            for i in range(1, res):
                ax.axvline(b_lo[0] + i * step[0], color="#DDE5EC", linewidth=0.45, zorder=0.5)
                ax.axhline(b_lo[1] + i * step[1], color="#DDE5EC", linewidth=0.45, zorder=0.5)
            for idx, cid in m.label_of_.items():
                cell = m.cells_[lvl][idx]
                col = CLUSTER_COLORS.get(cid, PALETTE["purple"])
                ax.add_patch(Rectangle(
                    cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                    facecolor="none", edgecolor=col, linewidth=0.85, alpha=0.65, zorder=1.5,
                ))
            noise = lab == -1
            ax.scatter(points[noise, 0], points[noise, 1], s=14, color=PALETTE["gray"], marker="x",
                       linewidths=0.85, label=f"Nhiễu ({int(noise.sum())})", zorder=2)
            for cid in sorted(set(lab[lab >= 0])):
                in_c = lab == cid
                ax.scatter(points[in_c, 0], points[in_c, 1], s=10,
                           color=CLUSTER_COLORS.get(cid, PALETTE["purple"]), alpha=0.75, linewidths=0,
                           label=f"Cụm {cid} ({int(in_c.sum())})", zorder=2.5)
            ax.set_title(
                f"{caption}\n{m.n_clusters_} cụm · {len(m.label_of_)} ô dày · "
                f"{int(noise.sum())}/{len(lab)} nhiễu ({noise.mean():.1%})",
                fontsize=10.5,
            )
            ax.grid(alpha=0.14)
            ax.legend(loc="upper left", fontsize=8, framealpha=0.92, ncols=2)

        for ax in axes[1, :]:
            ax.set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z-score)")
        for ax in axes[:, 0]:
            ax.set_ylabel("6.1 Y tế công lập (z-score)")
        fig.suptitle(f"Độ nhạy tham số STING trên {len(points)} quan sát PAPI", fontsize=13)
        return fig


def hierarchy_levels_figure(points: np.ndarray):
    """Vẽ đủ 3 mức lưới phân cấp STING (Level 0: 1×1, Level 1: 4×4, Level 2: 16×16)."""
    model = STING(n_levels=GRID["n_levels"], factor=GRID["factor"], min_count=GRID["min_count"]).fit(points)
    lo, hi = model.bounds_min_, model.bounds_max_
    pad_x, pad_y = (hi[0] - lo[0]) * 0.06, (hi[1] - lo[1]) * 0.06
    with style_context():
        fig, axes = plt.subplots(
            1, 3, figsize=(13.2, 4.35), dpi=150, sharex=True, sharey=True, layout="constrained"
        )
        for ax, lvl in zip(axes, (0, 1, 2), strict=True):
            lab = model.cluster(level=lvl, connectivity=GRID["connectivity"])
            res = model.factor ** lvl
            step = (hi - lo) / res
            for i in range(res + 1):
                lw = 0.7 if lvl == 0 else (0.6 if lvl == 1 else 0.35)
                ax.axvline(lo[0] + i * step[0], color="#CFD9E3", linewidth=lw, zorder=0.5)
                ax.axhline(lo[1] + i * step[1], color="#CFD9E3", linewidth=lw, zorder=0.5)
            for idx, cid in model.label_of_.items():
                cell = model.cells_[lvl][idx]
                col = CLUSTER_COLORS.get(cid, PALETTE["purple"])
                ax.add_patch(Rectangle(
                    cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                    facecolor="#EBF5F5" if lvl == 0 else "none",
                    edgecolor=col, linewidth=1.0 if lvl < 2 else 0.8, alpha=0.8, zorder=1.5,
                ))
            noise = lab == -1
            if np.any(noise):
                ax.scatter(
                    points[noise, 0], points[noise, 1], s=16, color=PALETTE["gray"],
                    marker="x", linewidths=0.9, label=f"Nhiễu ({int(noise.sum())})", zorder=2.5,
                )
            for cid in sorted(set(lab[lab >= 0])):
                in_c = lab == cid
                ax.scatter(
                    points[in_c, 0], points[in_c, 1], s=10,
                    color=CLUSTER_COLORS.get(cid, PALETTE["purple"]), alpha=0.72,
                    linewidths=0, label=f"Cụm {cid} ({int(in_c.sum())})", zorder=2.2,
                )
            if lvl == 1:
                for cell in model.cells_[1].values():
                    if cell.count > 0:
                        cx, cy = (cell.bounds_min + cell.bounds_max) / 2.0
                        dense = cell.count >= model.min_count_
                        ax.text(
                            cx, cy, str(cell.count), ha="center", va="center", fontsize=8.5,
                            fontweight="bold" if dense else "normal",
                            color="#0F2B46" if dense else "#8A5A00",
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.78),
                            zorder=4,
                        )
            titles = {
                0: f"Mức 0: Lưới 1 × 1 (Ô gốc)\n1 ô · {len(points)} điểm · {model.n_clusters_} cụm",
                1: f"Mức 1: Lưới 4 × 4 (16 ô)\n{len(model.label_of_)} ô dày · {model.n_clusters_} cụm · {int(noise.sum())} nhiễu",
                2: f"Mức 2: Lưới 16 × 16 (256 ô)\n{len(model.label_of_)} ô dày · {model.n_clusters_} cụm · {int(noise.sum())} nhiễu",
            }
            ax.set_title(titles[lvl], fontsize=10.5)
            ax.grid(alpha=0.12)
            ax.legend(loc="upper left", fontsize=7.6, framealpha=0.92, ncols=2 if lvl == 2 else 1)

        axes[0].set_xlim(lo[0] - pad_x, hi[0] + pad_x)
        axes[0].set_ylim(lo[1] - pad_y, hi[1] + pad_y)
        axes[0].set_ylabel("6.1 Y tế công lập (z-score)")
        axes[1].set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z-score)")
        fig.suptitle(f"Lưới phân cấp 3 mức của STING trên {len(points)} quan sát PAPI", fontsize=12.5)
        return fig


def kmeans_mechanism_and_trap_figure():
    """Minh họa K-means qua bước cập nhật tâm, ảnh hưởng của khởi tạo và WCSS."""
    from scipy.spatial.distance import cdist
    from sklearn.datasets import make_blobs

    rng = np.random.default_rng(42)
    X_blobs, _ = make_blobs(
        n_samples=150, centers=[(-4, -3), (0, 4), (5, -1)],
        cluster_std=[0.9, 0.8, 1.0], random_state=42,
    )
    X_noise = rng.uniform(low=[-8, -7], high=[9, 8], size=(12, 2))
    Xs = StandardScaler().fit_transform(np.vstack([X_blobs, X_noise]))

    c0 = np.array([[-1.6, 0.2], [0.2, -1.5], [1.2, 0.8]], dtype=float)
    cur = c0.copy()
    for _ in range(25):
        labs = np.argmin(cdist(Xs, cur), axis=1)
        nxt = np.array([Xs[labs == i].mean(axis=0) for i in range(3)])
        if np.allclose(nxt, cur, atol=1e-4):
            cur = nxt
            break
        cur = nxt
    wcss_ok = float(np.sum((Xs - cur[labs]) ** 2))

    bad_init = np.array([[-1.10, -0.80], [-1.10, -1.20], [0.60, 0.40]])
    km_trap = KMeans(n_clusters=3, init=bad_init, n_init=1, max_iter=50, random_state=42).fit(Xs)
    pal3 = (PALETTE["blue"], PALETTE["orange"], PALETTE["green"])

    with style_context():
        fig, axes = plt.subplots(
            1, 3, figsize=(13.2, 4.35), dpi=150, sharex=True, sharey=True, layout="constrained"
        )

        for g in range(3):
            mk = labs == g
            axes[0].scatter(Xs[mk, 0], Xs[mk, 1], s=14, color=pal3[g], alpha=0.72, linewidths=0)
            axes[0].add_patch(FancyArrowPatch(
                c0[g], cur[g], arrowstyle="->", mutation_scale=12, lw=1.7, color="#111111", zorder=5,
            ))
        axes[0].scatter(c0[:, 0], c0[:, 1], marker="*", s=160, facecolors="white",
                        edgecolors="#111111", linewidths=1.1, label="Tâm ban đầu μ⁽⁰⁾", zorder=6)
        axes[0].scatter(cur[:, 0], cur[:, 1], marker="X", s=140, color="#111111",
                        edgecolors="white", linewidths=0.9, label="Tâm hội tụ μ*", zorder=7)
        axes[0].set_title(f"1. K-means cập nhật tâm cụm\nHội tụ 3 nhóm chuẩn · WCSS = {wcss_ok:.2f}", fontsize=10.2)
        axes[0].set_ylabel("x2 (z-score)")
        axes[0].legend(loc="upper left", fontsize=7.8, framealpha=0.92)


        for g in range(3):
            mk = km_trap.labels_ == g
            axes[1].scatter(Xs[mk, 0], Xs[mk, 1], s=14, color=pal3[g], alpha=0.72, linewidths=0)
        axes[1].scatter(bad_init[:, 0], bad_init[:, 1], marker="^", s=95, facecolors="#FDE047",
                        edgecolors="#B04E27", linewidths=1.1, label="Khởi tạo xấu", zorder=6)
        axes[1].scatter(km_trap.cluster_centers_[:, 0], km_trap.cluster_centers_[:, 1], marker="X",
                        s=140, color="#111111", edgecolors="white", linewidths=0.9, label="Tâm kẹt bẫy", zorder=7)
        axes[1].set_title(f"2. BẪY khởi tạo xấu (TRAP! — tr.19–24)\nWCSS = {km_trap.inertia_:.2f} (chẻ 1, gộp nhầm 2 nhóm)", fontsize=10.2)
        axes[1].set_xlabel("x1 (z-score)")
        axes[1].legend(loc="upper left", fontsize=7.8, framealpha=0.92)


        for pt, lbl in zip(Xs, labs, strict=True):
            c = cur[int(lbl)]
            axes[2].plot([pt[0], c[0]], [pt[1], c[1]], "-", color=pal3[int(lbl)], alpha=0.25, lw=0.8, zorder=1)
        for g in range(3):
            mk = labs == g
            axes[2].scatter(Xs[mk, 0], Xs[mk, 1], s=14, color=pal3[g], alpha=0.82, linewidths=0, zorder=3)
        axes[2].scatter(cur[:, 0], cur[:, 1], marker="X", s=140, color="#111111",
                        edgecolors="white", linewidths=0.9, label="Tâm cụm", zorder=6)
        axes[2].set_title(f"3. WCSS trên đồ thị 2D (tr.27–30)\nTổng Σ‖xᵢ − μ‖² = {wcss_ok:.2f}", fontsize=10.2)
        axes[2].legend(loc="upper left", fontsize=7.8, framealpha=0.92)

        for ax in axes:
            ax.grid(alpha=0.16)
        fig.suptitle("Cập nhật tâm cụm, khởi tạo và WCSS trong K-means", fontsize=12.5)
        return fig


def hc_linkage_and_dendrogram_figure():
    """Minh họa bốn cách tính khoảng cách liên kết và cách cắt cây phân cụm phân cấp."""
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import cdist

    a_pts = np.array([[0.7, 1.2], [1.1, 2.0], [1.5, 1.0], [1.8, 1.7], [0.9, 2.5]])
    b_pts = np.array([[4.1, 2.3], [4.5, 3.2], [5.1, 2.6], [4.8, 1.6], [5.4, 2.1]])
    d_ab = cdist(a_pts, b_pts)
    i_min, j_min = np.unravel_index(np.argmin(d_ab), d_ab.shape)
    i_max, j_max = np.unravel_index(np.argmax(d_ab), d_ab.shape)
    mu_a, mu_b = a_pts.mean(axis=0), b_pts.mean(axis=0)

    pts6 = np.array([
        [0.8, 1.0], [1.3, 1.25],
        [4.6, 3.2], [5.1, 3.45],
        [1.05, 1.85],
        [4.85, 2.55],
    ])
    z6 = linkage(pts6, method="single")
    n6 = len(pts6)
    members = {i: [i] for i in range(n6)}

    with style_context():
        fig, (ax_lnk, ax_2d, ax_dn) = plt.subplots(1, 3, figsize=(13.4, 4.4), dpi=150, layout="constrained")

        for pa in a_pts:
            for pb in b_pts:
                ax_lnk.plot([pa[0], pb[0]], [pa[1], pb[1]], "-", color="#94A3B8", alpha=0.22, lw=0.75, zorder=1)
        ax_lnk.plot([], [], "-", color="#94A3B8", lw=1.4, label=f"#4 Average = {d_ab.mean():.2f}")
        ax_lnk.plot([a_pts[i_min, 0], b_pts[j_min, 0]], [a_pts[i_min, 1], b_pts[j_min, 1]],
                    "-", color="#D55E00", lw=2.4, label=f"#1 Single = {d_ab[i_min, j_min]:.2f}", zorder=4)
        ax_lnk.plot([a_pts[i_max, 0], b_pts[j_max, 0]], [a_pts[i_max, 1], b_pts[j_max, 1]],
                    "--", color=PALETTE["purple"], lw=2.0, label=f"#2 Complete = {d_ab[i_max, j_max]:.2f}", zorder=4)
        ax_lnk.scatter([mu_a[0], mu_b[0]], [mu_a[1], mu_b[1]], marker="*", s=160, color="#0F766E", zorder=6)
        ax_lnk.plot([mu_a[0], mu_b[0]], [mu_a[1], mu_b[1]], "-.", color="#0F766E", lw=2.0,
                    label=f"#3 Centroid = {np.linalg.norm(mu_a - mu_b):.2f}", zorder=5)
        ax_lnk.scatter(a_pts[:, 0], a_pts[:, 1], s=48, color=PALETTE["blue"], label="Cụm A", zorder=5)
        ax_lnk.scatter(b_pts[:, 0], b_pts[:, 1], s=48, color=PALETTE["green"], label="Cụm B", zorder=5)
        ax_lnk.set_xlim(0.2, 5.9)
        ax_lnk.set_ylim(0.5, 4.1)
        ax_lnk.set_title("1. Bốn cách tính khoảng cách liên kết", fontsize=10.2)
        ax_lnk.set_xlabel("x1")
        ax_lnk.set_ylabel("x2")
        ax_lnk.grid(alpha=0.16)
        ax_lnk.legend(loc="upper left", fontsize=7.3, framealpha=0.92, ncols=2)


        ax_2d.scatter(pts6[:, 0], pts6[:, 1], s=65, color="#1E3D5E", zorder=5)
        for idx_p, (px, py) in enumerate(pts6):
            ax_2d.text(px + 0.12, py + 0.08, f"P{idx_p}", fontsize=9, fontweight="bold", color="#0F2B46")
        ring_cols = (PALETTE["blue"], PALETTE["green"], PALETTE["orange"], PALETTE["purple"], "#64748B")
        for step_i, row in enumerate(z6):
            c1, c2, dist, _ = int(row[0]), int(row[1]), float(row[2]), row[3]
            merged = members[c1] + members[c2]
            members[n6 + step_i] = merged
            sub = pts6[merged]
            cx, cy = sub.mean(axis=0)
            span_x = max(0.82, (sub[:, 0].max() - sub[:, 0].min()) + 0.55 + 0.18 * step_i)
            span_y = max(0.72, (sub[:, 1].max() - sub[:, 1].min()) + 0.50 + 0.18 * step_i)
            ax_2d.add_patch(Ellipse(
                (cx, cy), width=span_x, height=span_y, facecolor="none",
                edgecolor=ring_cols[step_i], linestyle="-" if step_i < 4 else "--",
                linewidth=1.45, label=f"Bước {step_i + 1} (d={dist:.2f})", zorder=2,
            ))
        ax_2d.set_xlim(0.1, 6.2)
        ax_2d.set_ylim(0.2, 4.4)
        ax_2d.set_title("2. Ghép vòng từ dưới lên (tr.37–43)", fontsize=10.2)
        ax_2d.set_xlabel("x1")
        ax_2d.grid(alpha=0.16)
        ax_2d.legend(loc="lower right", fontsize=7.5, framealpha=0.94)


        heights6 = z6[:, 2]
        cut_i = int(np.argmax(np.diff(heights6)))
        thr6 = float((heights6[cut_i] + heights6[cut_i + 1]) / 2)
        k6 = n6 - (cut_i + 1)
        dendrogram(z6, ax=ax_dn, labels=[f"P{i}" for i in range(n6)], color_threshold=thr6)
        ax_dn.axhline(thr6, color="#D55E00", ls="--", lw=1.6, label=f"Cắt ngang d = {thr6:.2f} → k = {k6} cụm")
        ax_dn.set_ylim(0.0, float(heights6.max()) * 1.18)
        ax_dn.set_title("3. Dendrogram & mẹo chọn k (tr.44–47)", fontsize=10.2)
        ax_dn.set_ylabel("Khoảng cách ghép")
        ax_dn.legend(loc="upper left", fontsize=7.8, framealpha=0.92)

        fig.suptitle("Cách liên kết, ghép cụm và cắt cây phân cụm phân cấp", fontsize=12.5)
        return fig
