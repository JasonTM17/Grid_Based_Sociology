"""Tham số và biểu đồ cho thực nghiệm phân cụm mô tả ở giữa kỳ."""
from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from sklearn.metrics import silhouette_score

from scripts.common.fig_style import CLUSTER_COLORS, PALETTE, style_context
from scripts.common.papi_pred_common import FEATURE_LABELS
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
