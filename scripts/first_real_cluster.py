"""Hình phân cụm STING thật đầu tiên (Phase 2 bước 8).

Fit STING trực tiếp trên 1 năm dữ liệu PAPI thật (mặc định 2023), 2 chiều
đã chốt trong `models/predict_config.json`. Hai mức phân giải để thấy độ nhạy:
  (a) lưới thô 3×3 ô (L=2, f=3, mc=5)  → 1 vùng dày + ngoại vi;
  (b) lưới mịn 9×9 ô (L=3, f=3, mc=2) → nhiều nhóm nhỏ + nhiều nhiễu.
Kết luận trình bày: mẫu 1 năm chỉ 61 điểm; dữ liệu thật khá đồng nhất —
phân tích chính dùng nhiều năm (xem `predict_demo.py`, `phase-05`).

Chạy: python scripts/first_real_cluster.py
Đầu ra: results/figs/sting_first_real.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from papi_pred_common import ROOT, load_config, load_panel  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

YEAR = 2023
OUT = ROOT / "results" / "figs" / "sting_first_real.png"
COLORS = {0: "#4c72b0", 1: "#dd8452", 2: "#55a868", 3: "#8172b3", 4: "#937860"}


def panel(ax, x, y, labels, model, res, title):
    xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    pad_x, pad_y = (xmax - xmin) * 0.03, (ymax - ymin) * 0.03
    step_x, step_y = (xmax - xmin) / res, (ymax - ymin) / res
    for i in range(res + 1):
        ax.plot([xmin + i * step_x] * 2, [ymin - pad_y, ymax + pad_y],
                color="#e3e3e3", lw=0.7, zorder=0)
        ax.plot([xmin - pad_x, xmax + pad_x], [ymin + i * step_y] * 2,
                color="#e3e3e3", lw=0.7, zorder=0)
    noise = labels == -1
    ax.scatter(x[noise], y[noise], s=40, marker="x", c="#999999", linewidths=1.3,
               label=f"nhiễu ({int(noise.sum())})", zorder=3)
    for c in range(model.n_clusters_):
        m = labels == c
        if not m.any():
            continue
        ax.scatter(x[m], y[m], s=56, c=COLORS[c % 5], edgecolors="black",
                   linewidths=0.5, label=f"cụm {c} ({int(m.sum())})", zorder=4)
    ax.set_title(title, fontsize=10)
    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)
    ax.legend(loc="best", fontsize=7.5)


def main() -> int:
    cfg = load_config()
    feats = cfg["features"]
    labels_map = cfg["feature_labels"]
    df = load_panel()
    sub = df[df.year == YEAR].dropna(subset=feats)
    X = sub[feats].to_numpy()
    x, y = X[:, 0], X[:, 1]

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.6))

    m_coarse = STING(n_levels=2, factor=3, min_count=5).fit(X)
    lab_coarse = m_coarse.cluster(level=1, connectivity=1)
    s1 = sorted([int((lab_coarse == c).sum()) for c in range(m_coarse.n_clusters_)], reverse=True)
    panel(axes[0], x, y, lab_coarse, m_coarse, res=3,
          title=f"(a) lưới thô 3×3, min_count=5 — k={m_coarse.n_clusters_} "
                f"sizes={s1}, nhiễu {(lab_coarse == -1).mean():.0%}")

    m_fine = STING(n_levels=3, factor=3, min_count=2).fit(X)
    lab_fine = m_fine.cluster(level=2, connectivity=1)
    s2 = sorted([int((lab_fine == c).sum()) for c in range(m_fine.n_clusters_)], reverse=True)
    panel(axes[1], x, y, lab_fine, m_fine, res=9,
          title=f"(b) lưới mịn 9×9, min_count=2 — k={m_fine.n_clusters_} "
                f"sizes={s2}, nhiễu {(lab_fine == -1).mean():.0%}")

    for ax in axes:
        ax.set_xlabel(labels_map[feats[0]], fontsize=8.5)
    axes[0].set_ylabel(labels_map[feats[1]], fontsize=8.5)
    fig.suptitle(f"STING trên dữ liệu thật — {YEAR} (61 tỉnh, 2 chỉ tiêu): "
                 "độ phân giải lưới thay đổi kết quả; dữ liệu khá đồng nhất",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, dpi=150)
    plt.close(fig)

    print(f"{YEAR}: n={len(sub)}")
    print(f"(a) k={m_coarse.n_clusters_} sizes={s1} noise={(lab_coarse==-1).mean():.0%}")
    print(f"(b) k={m_fine.n_clusters_} sizes={s2} noise={(lab_fine==-1).mean():.0%}")
    print(f"đã lưu {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
