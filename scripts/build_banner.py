"""Build assets/social_preview.png — banner 1280×640 cho GitHub social preview.

Vẽ hoàn toàn bằng matplotlib (không cần dịch vụ ngoài) — tái tạo được:
    python scripts/build_banner.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "social_preview.png"

NAVY = "#0F2B46"
CELL_DARK = "#16324F"
CELL_MID = "#1B6E77"
GOLD = "#E2B04A"
CREAM = "#F6F4EF"
MIST = "#B9CDDE"
DIM = "#7C93A6"
DOT = "#F2E9D8"

fig = plt.figure(figsize=(12.8, 6.4), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1280)
ax.set_ylim(0, 640)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1280, 640, color=NAVY, zorder=0))

# ---------------- Lưới STING phía bên phải ----------------
rng = np.random.default_rng(11)
cell, gap = 60, 11
cols, rows = 8, 7
x0 = 708
y0 = 78

# mật độ giả định: phần lớn thấp, vài ô teal, một cụm gold cháy sáng
density = rng.gamma(1.6, 2.2, size=(rows, cols))
hot = {(2, 4), (2, 5), (3, 4), (4, 5), (1, 5)}      # cụm chính (teal)
very_hot = {(3, 5), (2, 5)}                          # vàng cháy nhất

for r in range(rows):
    for c in range(cols):
        x = x0 + c * (cell + gap)
        y = y0 + (rows - 1 - r) * (cell + gap)
        d = density[r, c]
        if (r, c) in very_hot:
            fill, alpha = GOLD, 0.95
        elif (r, c) in hot:
            fill, alpha = CELL_MID, 0.9
        elif d > density.mean() + 0.8:
            fill, alpha = CELL_MID, 0.55
        else:
            fill, alpha = CELL_DARK, 0.9
        ax.add_patch(Rectangle((x, y), cell, cell, facecolor=fill,
                               edgecolor="#27455F", linewidth=0.8, alpha=alpha, zorder=1))
        # điểm dữ liệu giả lập trong ô
        n_pts = int(np.clip(d, 0, 14))
        if n_pts:
            px = x + 8 + rng.random(n_pts) * (cell - 16)
            py = y + 8 + rng.random(n_pts) * (cell - 16)
            ax.scatter(px, py, s=7, c=DOT if (r, c) not in very_hot else "#3A2A00",
                       alpha=0.9, zorder=2, linewidths=0)

# điểm nhiễu mờ ngoài lưới (ngoại vi)
n_noise = 26
ax.scatter(rng.uniform(x0 - 60, x0 + 6.6, n_noise), rng.uniform(60, 610, n_noise),
           s=5, c=MIST, alpha=0.35, zorder=1, linewidths=0)

# ---------------- Chữ bên trái ----------------
ax.text(96, 470, "STING × PAPI", fontsize=92, fontweight="bold",
        color=CREAM, family="DejaVu Sans", va="center", zorder=3)
ax.add_patch(Rectangle((96, 408), 150, 7, color=GOLD, zorder=3))
ax.text(96, 336, "G R I D - B A S E D   C L U S T E R I N G", fontsize=19.5,
        fontweight="bold", color=GOLD, family="DejaVu Sans", zorder=3)
ax.text(96, 268, "Phân cụm 63 tỉnh Việt Nam\ntrên dữ liệu PAPI 2011–2024",
        fontsize=20.5, color=MIST, family="DejaVu Sans", linespacing=1.35, zorder=3)
ax.text(96, 128, "TOPIC 6  ·  MACHINE LEARNING  ·  FROM-SCRATCH STING",
        fontsize=12, fontweight="bold", color=DIM, family="DejaVu Sans", zorder=3)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=100, facecolor=NAVY)
plt.close(fig)
print("saved:", OUT)
