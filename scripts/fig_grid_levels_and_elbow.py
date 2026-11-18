"""Vẽ hai hình bổ sung cho notebook cuối kỳ.

1. results/figs/sting_grid_levels.png — lưới STING ba mức trên PAPI 2011–2023
   (cấu hình đóng băng trong models/predict_config.json).
2. results/figs/kmeans_elbow.png — WCSS và silhouette của K-means theo k, để
   giải thích vì sao đối chứng dùng k = 2.

Chạy: python scripts/fig_grid_levels_and_elbow.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from fig_style import CLUSTER_COLORS, PALETTE, save_png, style_context  # noqa: E402
from papi_pred_common import FEATURE_LABELS, load_config, load_panel  # noqa: E402
from sting import STING  # noqa: E402

FIGS = ROOT / "results" / "figs"
SEED = 42


def load_scaled() -> tuple[np.ndarray, list[str], dict]:
    cfg = load_config()
    feats, params = cfg["features"], cfg["sting"]
    panel = load_panel()
    train = panel[panel.year <= 2023].dropna(subset=feats)
    scaler = StandardScaler().fit(train[feats])
    return scaler.transform(train[feats]), feats, params


def draw_grid_levels(X: np.ndarray, feats: list[str], params: dict) -> Path:
    model = STING(n_levels=params["n_levels"], factor=params["factor"],
                  min_count=params["min_count"]).fit(X)
    labels = model.cluster(level=params["cluster_level"],
                           connectivity=params["connectivity"])
    lo, hi = model.bounds_min_, model.bounds_max_
    min_count = model.min_count_
    last = model.n_levels - 1

    with style_context():
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))
        for level, ax in enumerate(axes):
            res = model.factor ** level
            cells = model.cells_[level]
            for key, cell in cells.items():
                dense = cell.count >= min_count
                face = "#cfe3f2" if dense else "none"
                if level == last and dense:
                    face = "none"
                ax.add_patch(Rectangle(cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                                       facecolor=face, edgecolor="none", alpha=0.8))
                if res <= 4:
                    centre = (cell.bounds_min + cell.bounds_max) / 2
                    ax.text(centre[0], centre[1], str(cell.count), ha="center",
                            va="center", fontsize=9, fontweight="bold",
                            color="#1b3a57" if dense else "#666666", zorder=5,
                            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85})
            for k in range(res + 1):
                x = lo[0] + (hi[0] - lo[0]) * k / res
                y = lo[1] + (hi[1] - lo[1]) * k / res
                ax.axvline(x, color="#9aa5b1", lw=0.8 if res <= 4 else 0.4, zorder=1)
                ax.axhline(y, color="#9aa5b1", lw=0.8 if res <= 4 else 0.4, zorder=1)

            if level == last:
                noise = labels == -1
                ax.scatter(X[noise, 0], X[noise, 1], s=10, c=PALETTE["gray"], alpha=0.6,
                           marker="x", zorder=3)
                for c in range(model.n_clusters_):
                    m = labels == c
                    ax.scatter(X[m, 0], X[m, 1], s=10, c=CLUSTER_COLORS.get(c, PALETTE["purple"]),
                               alpha=0.85, zorder=3)
                dense_n = sum(c.count >= min_count for c in cells.values())
                ax.set_title(f"Mức {level}: lưới {res}×{res} — {dense_n}/{len(cells)} ô dày\n"
                             f"{model.n_clusters_} cụm, {noise.mean():.1%} nhiễu")
            else:
                ax.scatter(X[:, 0], X[:, 1], s=8, c="#444444", alpha=0.5, zorder=3)
                dense_n = sum(c.count >= min_count for c in cells.values())
                ax.set_title(f"Mức {level}: lưới {res}×{res} — số điểm mỗi ô\n"
                             f"{dense_n}/{len(cells)} ô có ≥ {min_count} điểm")
            ax.set_xlim(lo[0], hi[0])
            ax.set_ylim(lo[1], hi[1])
            ax.set_xlabel(f"{FEATURE_LABELS[feats[0]]}\n(z-score)", fontsize=9)
            if level == 0:
                ax.set_ylabel(f"{FEATURE_LABELS[feats[1]]}\n(z-score)", fontsize=9)
        fig.suptitle("STING chia lưới phân cấp rồi gom các ô dày liền kề (PAPI 2011–2023)",
                     fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        out = save_png(fig, FIGS / "sting_grid_levels.png")
        plt.close(fig)
    return out


def draw_elbow(X: np.ndarray) -> Path:
    ks = list(range(1, 9))
    wcss = [KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X).inertia_ for k in ks]
    sil = [silhouette_score(X, KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X))
           for k in ks[1:]]
    best = ks[1:][int(np.argmax(sil))]
    with style_context():
        fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2))
        a.plot(ks, wcss, "o-", color=PALETTE["blue"])
        a.axvline(2, color=PALETTE["gray"], ls="--", lw=1)
        a.set_title("WCSS (tổng bình phương trong cụm)")
        a.set_xlabel("Số cụm k")
        a.set_ylabel("WCSS")
        b.plot(ks[1:], sil, "o-", color=PALETTE["orange"])
        b.axvline(2, color=PALETTE["gray"], ls="--", lw=1)
        b.set_title(f"Silhouette — cao nhất tại k = {best}")
        b.set_xlabel("Số cụm k")
        b.set_ylabel("Silhouette")
        for ax in (a, b):
            ax.set_xticks(ks)
            ax.grid(alpha=0.25)
        fig.suptitle("Chọn k cho K-means đối chứng trên hai chỉ tiêu PAPI 2011–2023",
                     fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        out = save_png(fig, FIGS / "kmeans_elbow.png")
        plt.close(fig)
    print("WCSS:", [round(float(w), 1) for w in wcss])
    print("silhouette k=2..8:", [round(float(s), 3) for s in sil], "best k =", best)
    return out


def main() -> None:
    X, feats, params = load_scaled()
    print("saved:", draw_grid_levels(X, feats, params))
    print("saved:", draw_elbow(X))


if __name__ == "__main__":
    main()
