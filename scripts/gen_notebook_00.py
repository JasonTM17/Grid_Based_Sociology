"""Sinh notebook 00_synthetic_check.ipynb (chạy một lần khi tạo dự án).

Cách dùng: python scripts/gen_notebook_00.py
Ghi ra: notebooks/00_synthetic_check.ipynb
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "00_synthetic_check.ipynb"

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell("""# Demo STING trên dữ liệu giả lập (Phase 1)

Notebook kiểm tra trực quan thuật toán **STING tự viết** (`src/sting.py`):
lưới phân cấp → thống kê từng ô → ô "dày" → gom cụm liền kề.

- Dữ liệu: 2 cụm blob 2D tách biệt (tổng 240 điểm), seed cố định.
- Kỳ vọng: STING tách đúng 2 cụm (ARI >= 0.9); độ nhạy tham số sẽ khảo sát ở Phase 4.
"""))

cells.append(nbf.v4.new_code_cell("""import sys
from pathlib import Path

# Cho phép import `sting` dù kernel chạy từ notebooks/ hay từ gốc repo
for cand in (Path.cwd(), Path.cwd().parent):
    if (cand / "src" / "sting.py").exists():
        sys.path.insert(0, str(cand / "src"))
        break

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from sting import STING

print("import OK")"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. Sinh dữ liệu giả lập

Hai cụm Gauss tách biệt hoàn toàn — trường hợp "dễ" để kiểm tra thuật toán chạy đúng trước khi dùng dữ liệu thật."""))

cells.append(nbf.v4.new_code_cell("""X, y_true = make_blobs(
    n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
)

fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(X[:, 0], X[:, 1], c=y_true, s=12, cmap="coolwarm")
ax.set_title("Dữ liệu giả lập: 2 cụm")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.tight_layout()
plt.show()

print("shape:", X.shape)"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. Xây lưới phân cấp STING

- Mức 0: 1 ô bao trùm toàn bộ dữ liệu.
- Mỗi mức kế tiếp chia mỗi chiều thành `factor` phần (ở đây factor = 4).
- Mỗi ô lưu thống kê count/mean/std/min/max theo từng chiều — dữ liệu chỉ bị quét 1 lượt cho mỗi mức."""))

cells.append(nbf.v4.new_code_cell("""model = STING(n_levels=3, factor=4, min_count=3).fit(X)

for level in range(3):
    cells = model.cells_[level]
    counts = np.array([c.count for c in cells.values()])
    print(f"mức {level}: {len(cells)} ô có dữ liệu, tổng điểm = {counts.sum()}, ô dày nhất = {counts.max()} điểm")"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Trực quan hóa lưới mức 2 và mật độ ô

Mỗi ô vẽ một hình chữ nhật; độ đậm thể hiện số điểm trong ô (mật độ)."""))

cells.append(nbf.v4.new_code_cell("""level = 2
step_x = (model.bounds_max_[0] - model.bounds_min_[0]) / (model.factor ** level)
step_y = (model.bounds_max_[1] - model.bounds_min_[1]) / (model.factor ** level)

fig, ax = plt.subplots(figsize=(6, 6))
for cell in model.cells_[level].values():
    x0, y0 = cell.bounds_min
    ax.add_patch(plt.Rectangle((x0, y0), step_x, step_y,
                               facecolor="tab:blue", alpha=min(0.08 * cell.count, 0.9),
                               edgecolor="gray", linewidth=0.4))
ax.scatter(X[:, 0], X[:, 1], s=8, c="black")
ax.set_title(f"Lưới mức {level} (màu đậm = nhiều điểm hơn)")
plt.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. Gom cụm và đối chiếu nhãn thật

Ô "dày" = count >= `min_count`. Các ô dày liền kề (kề mặt) gom thành một cụm;
điểm thuộc ô không dày nhận nhãn -1 (nhiễu)."""))

cells.append(nbf.v4.new_code_cell("""labels = model.cluster(level=2, connectivity=1)
ari = adjusted_rand_score(y_true, labels)
noise = (labels == -1).mean()
print(f"ARI = {ari:.3f} | tỷ lệ nhiễu = {noise:.1%} | số cụm = {model.n_clusters_}")

fig, axes = plt.subplots(1, 2, figsize=(11, 5))
axes[0].scatter(X[:, 0], X[:, 1], c=y_true, s=12, cmap="coolwarm")
axes[0].set_title("Nhãn thật")
axes[1].scatter(X[:, 0], X[:, 1], c=labels, s=12, cmap="viridis")
axes[1].set_title(f"STING (ARI={ari:.3f})")
for ax in axes:
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.tight_layout()
fig.savefig("../results/figs/00_synthetic_sting.png", dpi=120, bbox_inches="tight")
plt.show()"""))

cells.append(nbf.v4.new_markdown_cell("""## 5. Xem trước độ nhạy tham số

Tham số ảnh hưởng mạnh tới kết quả — Phase 4 sẽ khảo sát kỹ (parameter sweep) và ghi lại quy tắc chọn mặc định."""))

cells.append(nbf.v4.new_code_cell("""rows = []
for mc in (2, 3, 5, 8, 12):
    m = STING(n_levels=3, factor=4, min_count=mc).fit(X)
    lab = m.cluster(level=2, connectivity=1)
    rows.append((mc, adjusted_rand_score(y_true, lab), (lab == -1).mean(), m.n_clusters_))

print(f"{'min_count':>9} | {'ARI':>6} | {'noise':>6} | cụm")
for mc, ari, noise, k in rows:
    print(f"{mc:>9} | {ari:>6.3f} | {noise:>6.1%} | {k}")"""))

cells.append(nbf.v4.new_markdown_cell("""## 6. Kết luận Phase 1

- STING tự viết hoạt động đúng trên dữ liệu giả lập: phân cấp lưới, thống kê ô, gom cụm.
- Kết quả **nhạy với `min_count` và mức lưới** — sẽ khảo sát ở Phase 4 và báo cáo trung thực.
- Tiếp theo (Phase 2): parse 14 file PAPI thật → panel 63 tỉnh × 2011–2024 → chạy STING trên dữ liệu thật."""))

nb["cells"] = cells
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print("written:", OUT)
