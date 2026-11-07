"""Build assets/social_preview.png — banner 2560×1280 px cho GitHub social preview.

Vẽ hoàn toàn bằng matplotlib (không cần dịch vụ ngoài) — tái tạo được:
    python scripts/build_banner.py

Trình bày theo chuẩn ``scripts/fig_style.py``: lưu qua ``save_png`` ở 400 DPI
(chuẩn repo >= 200; 400 DPI để khi in rộng ~21 cm khổ A4 vẫn còn ~310 DPI).
Bố cục dựng trên khung toạ độ dữ liệu 1280×640, figure 6.4×3.2 inch × 400 DPI
— cỡ chữ theo point giữ tỉ lệ như khung 1280 cũ (1 pt ≈ 2.78 px khung).

Dòng nguồn ``add_source`` ghi trung thực: lưới ô bên phải là MÔ PHỎNG minh hoạ
(seed cố định, không dựng từ dữ liệu), còn dữ liệu dự án được trích theo
``data/raw/papi/PROVENANCE.md`` — PAPI — CECODES, VFF-CRT, RTA & UNDP, tải
2026-11-03. Palette navy/gold là nhận diện riêng của ảnh trang trí, KHÔNG phải
palette dữ liệu Okabe–Ito của fig_style. Chữ chân trang cỡ lớn hơn bản 1280×640
để còn đọc được khi nền tảng thu nhỏ ảnh xem trước (~450 px).
"""
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")  # đặt backend trước khi import pyplot
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fig_style import add_source, apply_style, save_png  # noqa: E402

OUT = ROOT / "assets" / "social_preview.png"

NAVY = "#0F2B46"
CELL_DARK = "#16324F"
CELL_MID = "#1B6E77"
GOLD = "#E2B04A"
CREAM = "#F6F4EF"
MIST = "#B9CDDE"
DIM = "#7C93A6"
DOT = "#F2E9D8"

apply_style()  # DejaVu Sans (phủ đủ dấu tiếng Việt) + rcParams chuẩn repo

fig = plt.figure(figsize=(6.4, 3.2), dpi=400)
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
                               edgecolor="#27455F", linewidth=0.4, alpha=alpha, zorder=1))
        # điểm dữ liệu giả lập trong ô
        n_pts = int(np.clip(d, 0, 14))
        if n_pts:
            px = x + 8 + rng.random(n_pts) * (cell - 16)
            py = y + 8 + rng.random(n_pts) * (cell - 16)
            ax.scatter(px, py, s=3.5, c=DOT if (r, c) not in very_hot else "#3A2A00",
                       alpha=0.9, zorder=2, linewidths=0)

# điểm nhiễu mờ ngoài lưới (ngoại vi)
n_noise = 26
ax.scatter(rng.uniform(x0 - 60, x0 + 6.6, n_noise), rng.uniform(60, 610, n_noise),
           s=2.5, c=MIST, alpha=0.35, zorder=1, linewidths=0)

# ---------------- Chữ bên trái ----------------
# Cỡ chữ = 1/2 bản gốc (12.8×6.4 @100dpi) vì figure nhỏ đi một nửa @200dpi.
ax.text(96, 470, "STING × PAPI", fontsize=46, fontweight="bold",
        color=CREAM, va="center", zorder=3)
ax.add_patch(Rectangle((96, 408), 150, 7, color=GOLD, zorder=3))
ax.text(96, 336, "G R I D - B A S E D   C L U S T E R I N G", fontsize=9.75,
        fontweight="bold", color=GOLD, zorder=3)
ax.text(96, 268, "Phân cụm 63 tỉnh Việt Nam\ntrên dữ liệu PAPI 2011–2024",
        fontsize=10.25, color=MIST, linespacing=1.35, zorder=3)
ax.text(96, 128, "TOPIC 6  ·  MACHINE LEARNING  ·  FROM-SCRATCH STING",
        fontsize=12, fontweight="bold", color=DIM, zorder=3)

# Dòng nguồn — trung thực: lưới ô là mô phỏng minh hoạ (seed 11), KHÔNG dựng
# từ dữ liệu; dữ liệu dự án trích theo data/raw/papi/PROVENANCE.md (tải
# 2026-11-03). Dùng helper chuẩn, chỉnh màu/tạo độ cho nền navy.
add_source(
    fig,
    "lưới ô minh hoạ — mô phỏng (seed 11), không dựng từ dữ liệu\n"
    "dữ liệu dự án: PAPI — CECODES, VFF-CRT, RTA & UNDP",
    retrieved="2026-11-03",
    x=96 / 1280, y=22 / 640, color=DIM,
)

save_png(fig, OUT, dpi=400, bbox_inches=None, facecolor=NAVY)
plt.close(fig)
print("saved:", OUT)
