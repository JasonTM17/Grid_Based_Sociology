"""Sinh notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb — notebook nộp cuối kỳ (end-to-end).

Cách dùng: python scripts/notebooks/gen_final_analysis.py
Sau đó:      python -m nbconvert --to notebook --execute --inplace notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb
"""
from pathlib import Path

import nbformat as nbf
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "Nhom15_CuoiKy_STING_PAPI.ipynb"

nb = nbf.v4.new_notebook()
cells = []
md = cells.append
cd = cells.append

md(nbf.v4.new_markdown_cell("""# ỨNG DỤNG THUẬT TOÁN PHÂN CỤM DỰA TRÊN LƯỚI STING ĐỂ PHÂN TÍCH ĐẶC ĐIỂM VÀ SỰ BIẾN ĐỘNG CỦA CÁC CHỈ SỐ QUẢN TRỊ, HÀNH CHÍNH CÔNG TẠI 63 TỈNH, THÀNH PHỐ VIỆT NAM DỰA TRÊN DỮ LIỆU PAPI GIAI ĐOẠN 2011–2024

*APPLICATION OF STING GRID-BASED CLUSTERING TO ANALYZE GOVERNANCE AND PUBLIC ADMINISTRATION PERFORMANCE PATTERNS AND TEMPORAL CHANGES ACROSS 63 VIETNAMESE PROVINCES USING PAPI DATA (2011–2024)*

**Báo cáo cuối kỳ môn Học máy · Nhóm 15 · Chủ đề 6 — Grid-based clustering**

Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)

**Chạy lại notebook.** Giải nén toàn bộ gói và giữ thư mục
`tai_lieu_kem` cạnh notebook. Chọn **Restart Kernel → Run All** để chạy
các ô từ trên xuống. Các kết quả đã lưu có thể xem trực tiếp."""))

cd(nbf.v4.new_code_cell("""import sys
from pathlib import Path

cwd = Path.cwd().resolve()
ROOT = next((p for parent in (cwd, *cwd.parents)
             for p in (parent / "tai_lieu_kem", parent)
             if (p / "src" / "sting.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError(
        "Vui lòng giải nén toàn bộ gói và mở notebook cạnh thư mục tai_lieu_kem."
    )
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

def show_md(text):
    display(Markdown(text))

panel = pd.read_csv(ROOT / "data/processed/papi_panel_63_2011_2024.csv")
assert panel.shape == (882, 41)
assert not panel.duplicated(["province_code", "year"]).any()
print(f"Bảng PAPI có {len(panel)} quan sát tỉnh–năm và {panel.shape[1]} cột.")
print(f"Phạm vi gồm {panel.province_code.nunique()} tỉnh, thành phố giai đoạn "
      f"{panel.year.min()}–{panel.year.max()}.")"""))

md(nbf.v4.new_markdown_cell("""## 1. Dữ liệu và chất lượng

- Dữ liệu PAPI 2011–2024 gồm 882 quan sát tỉnh–năm và 41 cột.
- 0.0 quy về NaN (khớp quy ước gói replication Mendeley).
- Có 23/37 chỉ tiêu có biến động trung bình năm vượt 0,25. Các chỉ tiêu này
  được đối chiếu với workbook trước khi lựa chọn đặc trưng.
- Hai chiều nội dung `d7/d8` có từ năm 2018."""))

cd(nbf.v4.new_code_cell("""cfg = json.loads((ROOT / "models/predict_config.json").read_text(encoding="utf-8"))
print("Cặp chỉ tiêu phân cụm:", cfg["features"])
print("STING:", cfg["sting"])
print("Giao thức chọn (train-only):", cfg["selection_protocol"])"""))

cd(nbf.v4.new_code_cell("""audit = pd.read_csv(ROOT / "results/preprocessing_audit.csv")
audit_table = audit[["test", "result"]].rename(
    columns={"test": "Kiểm tra", "result": "Kết quả"}
)
audit_table["Kiểm tra"] = audit_table["Kiểm tra"].str.replace(", dedup chạy ĐẦU TIÊN", "", regex=False)
with pd.option_context("display.max_colwidth", None):
    display(audit_table)"""))

md(nbf.v4.new_markdown_cell("""### 1.1 Phương pháp STING và kiểm chứng cài đặt

STING gốc [Wang, Yang & Muntz, VLDB 1997](https://www.vldb.org/conf/1997/P186.PDF)
lưu thống kê và phân phối của từng ô lưới. Cài đặt của nhóm dùng ngưỡng số đếm,
gom các ô dày liên thông qua cạnh tại một mức lưới.

ARI trên dữ liệu giả lập được đối chiếu với nhãn đã biết. Với PAPI, ARI giữa
các phương pháp biểu thị mức đồng thuận giữa các phân hoạch."""))

cd(nbf.v4.new_code_cell("""from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from sting import STING

X_synthetic, truth = make_blobs(n_samples=240, centers=[(-6, -6), (6, 6)],
                               cluster_std=0.6, random_state=42)
synthetic = STING(n_levels=3, factor=4, min_count=3).fit(X_synthetic)
synthetic_labels = synthetic.cluster(level=2, connectivity=1)
ari = adjusted_rand_score(truth, synthetic_labels)
assert ari >= 0.9
for cells_at_level in synthetic.cells_.values():
    assert sum(cell.count for cell in cells_at_level.values()) == len(truth)
print(f"Dữ liệu giả lập: ARI = {ari:.3f}, {synthetic.n_clusters_} cụm, "
      f"{(synthetic_labels == -1).mean():.1%} điểm nhiễu.")
print("Tổng số điểm được bảo toàn tại từng mức lưới.")"""))

cd(nbf.v4.new_code_cell(r"""import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from scripts.common.fig_style import PALETTE, style_context

_counts_demo = np.array([[4, 3, 0], [1, 0, 4], [0, 0, 3]])
_offsets_demo = {
    1: [(0.38, 0.36)],
    3: [(0.24, 0.28), (0.62, 0.28), (0.43, 0.58)],
    4: [(0.24, 0.24), (0.60, 0.24), (0.24, 0.56), (0.60, 0.56)],
}
_pts_d, _cells_d = [], []
for _r in range(3):
    _cy = 2 - _r
    for _c in range(3):
        _cnt = int(_counts_demo[_r, _c])
        for _dx, _dy in _offsets_demo.get(_cnt, ()):
            _pts_d.append((_c + _dx, _cy + _dy))
            _cells_d.append((_c, _cy))
_pts_d = np.asarray(_pts_d)
_step_titles = ("1. Điểm đầu vào (n = 15)", "2. Chia lưới 3×3 & đếm ô",
                "3. Lọc ô dày (count ≥ 3)", "4. Nối kề 4 hướng → 2 cụm")
with style_context():
    fig, axes = plt.subplots(1, 4, figsize=(12.2, 3.15), dpi=150, sharex=True, sharey=True, layout="constrained")
    for s_idx, (ax, s_title) in enumerate(zip(axes, _step_titles, strict=True)):
        ax.set_xlim(0.0, 3.0)
        ax.set_ylim(0.0, 3.0)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([0, 1, 2, 3])
        ax.set_yticks([0, 1, 2, 3])
        ax.tick_params(labelsize=8)
        ax.set_title(s_title, fontsize=10.5, pad=6)
        if s_idx >= 1:
            for _r in range(3):
                _cy = 2 - _r
                for _c in range(3):
                    _cnt = int(_counts_demo[_r, _c])
                    if s_idx == 1:
                        _fill = "#EFF6F9" if _cnt > 0 else "#FFFFFF"
                    elif s_idx == 2:
                        _fill = "#D4E8EA" if _cnt >= 3 else ("#FDE8BA" if _cnt > 0 else "#F3F5F7")
                    else:
                        _fill = ("#D4E8EA" if (_c, _cy) in ((0, 2), (1, 2))
                                 else ("#DBE8F4" if (_c, _cy) in ((2, 1), (2, 0))
                                       else ("#FDE8BA" if _cnt > 0 else "#F3F5F7")))
                    ax.add_patch(Rectangle((_c, _cy), 1.0, 1.0, facecolor=_fill, edgecolor="#5D748A", linewidth=0.95))
                    _tcol = "#0F2B46" if _cnt >= 3 else ("#8A5A00" if _cnt > 0 else "#9AA5B1")
                    ax.text(_c + 0.80, _cy + 0.80, str(_cnt), ha="center", va="center", fontsize=10.5, fontweight="bold",
                            color=_tcol, bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.82), zorder=3)
        else:
            ax.grid(alpha=0.22, linestyle=":")
        if s_idx < 3:
            if s_idx == 2:
                _dm = np.array([_counts_demo[2 - _cy, _cx] >= 3 for _cx, _cy in _cells_d])
                ax.scatter(_pts_d[_dm, 0], _pts_d[_dm, 1], s=44, color=PALETTE["blue"], edgecolors="white", linewidths=0.7, zorder=4)
                ax.scatter(_pts_d[~_dm, 0], _pts_d[~_dm, 1], s=55, color=PALETTE["gray"], marker="X", zorder=4)
                ax.text(0.46, 1.13, "ô thưa → −1", ha="center", va="bottom", fontsize=8, color="#8A5A00", fontweight="bold", zorder=5)
            else:
                ax.scatter(_pts_d[:, 0], _pts_d[:, 1], s=44, color="#1E3D5E", edgecolors="white", linewidths=0.7, zorder=4)
                if s_idx == 1:
                    ax.text(2.50, 2.38, "ô lưu:\ncount, μ, σ,\nmin, max", ha="center", va="center", fontsize=7.5, color="#4A5D70", zorder=4)
        else:
            _ga = np.array([tuple(c) in ((0, 2), (1, 2)) for c in _cells_d])
            _gb = np.array([tuple(c) in ((2, 1), (2, 0)) for c in _cells_d])
            _nm = ~(_ga | _gb)
            ax.scatter(_pts_d[_ga, 0], _pts_d[_ga, 1], s=46, color=PALETTE["green"], edgecolors="white", linewidths=0.7, zorder=4)
            ax.scatter(_pts_d[_gb, 0], _pts_d[_gb, 1], s=46, color=PALETTE["blue"], edgecolors="white", linewidths=0.7, zorder=4)
            ax.scatter(_pts_d[_nm, 0], _pts_d[_nm, 1], s=60, color=PALETTE["gray"], marker="X", zorder=5)
            for (_x0, _y0), (_x1, _y1), _ca in (((0.76, 2.66), (1.24, 2.66), PALETTE["green"]), ((2.50, 1.22), (2.50, 0.78), PALETTE["blue"])):
                ax.add_patch(FancyArrowPatch((_x0, _y0), (_x1, _y1), arrowstyle="<->", mutation_scale=11, linewidth=1.5, color=_ca, zorder=5))
            ax.text(1.00, 2.06, "Cụm A (7)", ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#0F5C48", zorder=5)
            ax.text(2.44, 0.14, "Cụm B (7)", ha="center", va="bottom", fontsize=8.2, fontweight="bold", color=PALETTE["blue"], zorder=5)
            ax.text(0.46, 1.13, "Nhiễu (−1)", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#5A5A5A", zorder=5)
            ax.annotate("Chạm góc\n(≠ nối)", xy=(2.0, 2.0), xytext=(2.46, 2.34), ha="center", va="center",
                        fontsize=7.6, color="#B04E27", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#B04E27", lw=1.1), zorder=5)
    plt.show()"""))

cd(nbf.v4.new_code_cell("""features, params = cfg["features"], cfg["sting"]
train = panel[panel.year <= 2023].dropna(subset=features)
scaler = StandardScaler().fit(train[features])
train_scaled = scaler.transform(train[features])
sting = STING(n_levels=params["n_levels"], factor=params["factor"],
              min_count=params["min_count"]).fit(train_scaled)
train_labels = sting.cluster(level=params["cluster_level"], connectivity=params["connectivity"])
eligible = panel.dropna(subset=features)
scaled = scaler.transform(eligible[features])
rebuilt = eligible[["province_code", "year"]].assign(pred_cluster=sting.predict(scaled))
saved = pd.read_csv(ROOT / "results/predict_all_years.csv")
comparison = rebuilt.merge(saved, on=["province_code", "year"],
                           suffixes=("_rebuilt", "_saved"), validate="one_to_one")
assert len(comparison) == len(saved) == len(eligible)
np.testing.assert_array_equal(comparison.pred_cluster_rebuilt, comparison.pred_cluster_saved)
loaded = STING.load(ROOT / "models/sting_predict_model.pkl")
scale_info = json.loads((ROOT / "models/sting_predict_scaler.json").read_text(encoding="utf-8"))
loaded_scaled = (eligible[features].to_numpy() - np.array(scale_info["mean"])) / np.array(scale_info["scale"])
np.testing.assert_array_equal(loaded.predict(loaded_scaled), rebuilt.pred_cluster.to_numpy())
test = rebuilt[rebuilt.year == 2024]
print(f"Tái lập STING: {len(comparison)}/{len(saved)} nhãn khớp với kết quả đã lưu.")
print("Mô hình đã lưu và mô hình dựng lại cho cùng nhãn.")
test_noise = int(test.pred_cluster.eq(-1).sum())
print(f"Năm 2024: {len(test)}/63 tỉnh đủ hai chỉ tiêu. "
      f"{len(test) - test_noise} tỉnh được gán cụm, {test_noise} tỉnh nhận nhãn nhiễu.")
train_z_flag = (np.abs(train_scaled) > 3).any(axis=1)
train_noise = int((train_labels == -1).sum())
train_sparse_no_flag = int(((train_labels == -1) & ~train_z_flag).sum())
trimmed_sting = STING(n_levels=params["n_levels"], factor=params["factor"],
                      min_count=params["min_count"]).fit(train_scaled[~train_z_flag])
trimmed_train_labels = trimmed_sting.cluster(level=params["cluster_level"],
                                             connectivity=params["connectivity"])
trimmed_train_noise = int((trimmed_train_labels == -1).sum())
print(f"2011–2023: {train_z_flag.sum()} quan sát có |z| > 3; "
      f"{train_sparse_no_flag}/{train_noise} điểm nhãn −1 có |z| ≤ 3 trên cả hai trục.")
print(f"Nếu loại {train_z_flag.sum()} điểm |z| > 3 rồi dựng lại lưới trên {len(trimmed_train_labels)} điểm: "
      f"{trimmed_sting.n_clusters_} cụm, {trimmed_train_noise}/{len(trimmed_train_labels)} điểm nhiễu "
      f"({trimmed_train_noise / len(trimmed_train_labels):.1%}).")"""))

cd(nbf.v4.new_code_cell(r"""import copy

conn8_sting = copy.deepcopy(sting)
conn8_labels = conn8_sting.cluster(level=params["cluster_level"], connectivity=2)
conn8_noise = int((conn8_labels == -1).sum())
print(f"Đổi kề 8 hướng (connectivity=2) trên 2011–2023: {len(conn8_sting.label_of_)} ô dày → "
      f"{conn8_sting.n_clusters_} cụm, {conn8_noise}/{len(conn8_labels)} điểm nhiễu ({conn8_noise / len(conn8_labels):.1%}).")

def _draw_sting_grid(ax, m, *, grid_color="#CBD5E1", dense_fill="#EBF5F5"):
    res = m.factor ** m.cluster_level_
    b_lo, b_hi = m.bounds_min_, m.bounds_max_
    step = (b_hi - b_lo) / res
    for idx in m.label_of_:
        cell = m.cells_[m.cluster_level_][idx]
        ax.add_patch(Rectangle(cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                               facecolor=dense_fill, edgecolor="#94B8BC", linewidth=0.5, zorder=1))
    for i in range(res + 1):
        ax.axvline(b_lo[0] + i * step[0], color=grid_color, linewidth=0.35, zorder=0.5)
        ax.axhline(b_lo[1] + i * step[1], color=grid_color, linewidth=0.35, zorder=0.5)

_lo_t, _hi_t = sting.bounds_min_, sting.bounds_max_
_px_t, _py_t = (_hi_t[0] - _lo_t[0]) * 0.06, (_hi_t[1] - _lo_t[1]) * 0.06
with style_context():
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.35), dpi=150, sharex=True, sharey=True, layout="constrained")
    # Panel 1: |z| <= 3 vs nhiễu STING (-1)
    _draw_sting_grid(axes[0], sting)
    axes[0].add_patch(Rectangle((-3.0, -3.0), 6.0, 6.0, facecolor="none", edgecolor="#D55E00",
                                linestyle="--", linewidth=1.35, label="Khung |z| ≤ 3 ('sạch' 1D)", zorder=4))
    _nm = train_labels == -1
    _sc = _nm & ~train_z_flag
    axes[0].scatter(train_scaled[~_nm, 0], train_scaled[~_nm, 1], s=10, color=PALETTE["blue"], alpha=0.68, linewidths=0,
                    label=f"Vào cụm ({int((~_nm).sum())})", zorder=2)
    axes[0].scatter(train_scaled[_sc, 0], train_scaled[_sc, 1], s=18, color=PALETTE["gray"], marker="x", linewidths=0.95,
                    label=f"−1 trong |z|≤3 ({train_sparse_no_flag})", zorder=3)
    axes[0].scatter(train_scaled[train_z_flag, 0], train_scaled[train_z_flag, 1], s=32, color="#D55E00", marker="D",
                    edgecolors="white", linewidths=0.5, label=f"Điểm |z|>3 ({int(train_z_flag.sum())})", zorder=5)
    axes[0].set_title(f"1. Khung |z| ≤ 3 vs nhiễu −1 (2011–2023)\n{train_sparse_no_flag}/{train_noise} điểm −1 vẫn TRONG |z| ≤ 3", fontsize=10.5)
    axes[0].set_ylabel("6.1 Y tế công lập (z-score)")
    axes[0].legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    # Panel 2: BẪY xóa |z|>3
    _draw_sting_grid(axes[1], trimmed_sting, grid_color="#E2CFC9", dense_fill="#F3EEEA")
    axes[1].add_patch(Rectangle(_lo_t, *(_hi_t - _lo_t), facecolor="none", edgecolor="#64748B",
                                linestyle=":", linewidth=1.2, label="Biên [min, max] cũ", zorder=3))
    axes[1].add_patch(Rectangle(trimmed_sting.bounds_min_, *(trimmed_sting.bounds_max_ - trimmed_sting.bounds_min_),
                                facecolor="none", edgecolor="#D55E00", linestyle="--", linewidth=1.3, label="Biên mới co lại", zorder=4))
    _kept = train_scaled[~train_z_flag]
    _ta = trimmed_train_labels >= 0
    axes[1].scatter(_kept[_ta, 0], _kept[_ta, 1], s=10, color=PALETTE["green"], alpha=0.68, linewidths=0,
                    label=f"Vào cụm ({int(_ta.sum())})", zorder=2)
    axes[1].scatter(_kept[~_ta, 0], _kept[~_ta, 1], s=18, color=PALETTE["gray"], marker="x", linewidths=0.95,
                    label=f"Nhiễu mới ({trimmed_train_noise})", zorder=3)
    axes[1].scatter(train_scaled[train_z_flag, 0], train_scaled[train_z_flag, 1], s=36, facecolors="none", edgecolors="#D55E00",
                    marker="D", linewidths=1.1, label=f"Đã xóa ({int(train_z_flag.sum())})", zorder=5)
    axes[1].set_title(f"2. BẪY: Xóa |z|>3 rồi dựng lại lưới\n{trimmed_sting.n_clusters_} cụm · {trimmed_train_noise}/{len(trimmed_train_labels)} nhiễu ({trimmed_train_noise / len(trimmed_train_labels):.1%}, TĂNG!)", fontsize=10.5)
    axes[1].set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z-score)")
    axes[1].legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    # Panel 3: BẪY connectivity=2
    _draw_sting_grid(axes[2], conn8_sting, dense_fill="#E4EFF7")
    _c8a = conn8_labels >= 0
    axes[2].scatter(train_scaled[_c8a, 0], train_scaled[_c8a, 1], s=10, color=PALETTE["blue"], alpha=0.72, linewidths=0,
                    label=f"1 cụm gộp ({int(_c8a.sum())})", zorder=2)
    axes[2].scatter(train_scaled[~_c8a, 0], train_scaled[~_c8a, 1], s=18, color=PALETTE["gray"], marker="x", linewidths=0.95,
                    label=f"Nhiễu giữ nguyên ({conn8_noise})", zorder=3)
    axes[2].set_title(f"3. BẪY: Đổi kề 8 hướng (connectivity=2)\nGộp qua góc → {conn8_sting.n_clusters_} cụm · {conn8_noise}/{len(conn8_labels)} nhiễu (KHÔNG giảm)", fontsize=10.5)
    axes[2].legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    axes[0].set_xlim(min(_lo_t[0], -3.15) - _px_t, max(_hi_t[0], 3.15) + _px_t)
    axes[0].set_ylim(min(_lo_t[1], -3.15) - _py_t, max(_hi_t[1], 3.15) + _py_t)
    plt.show()"""))

md(nbf.v4.new_markdown_cell("""### 1.2 Lưới STING trên PAPI

Hình dưới cho thấy ba mức lưới của cấu hình đóng băng (`factor=4`, `min_count=5`).
Mức 0 là một ô chứa toàn bộ điểm. Mức 1 chia mỗi chiều thành 4 đoạn và ghi số điểm
trong từng ô. Mức 2 chia thành 16 đoạn; các ô có ít nhất 5 điểm là ô dày, các ô dày
kề mặt được gom thành cụm, điểm ở ô còn lại là nhiễu."""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/sting_grid_levels.png")))

rect_hi = [(0.0, 2.5), (0.0, 2.5)]
q_rect_808 = sting.query_rect(rect_hi, level=2)
q_td_808 = sting.query_top_down(rect_hi, confidence=0.95, level=2)
assert q_td_808["count"] == q_rect_808["count"]
np.testing.assert_allclose(q_td_808["mean"], q_rect_808["mean"])
occ_808 = sum(len(sting.cells_[lvl]) for lvl in range(sting.n_levels))
print(
    f"Truy vấn top-down trên lưới PAPI 2011–2023 [0; 2,5]²: khớp {q_td_808['count']} điểm "
    f"(μ = {q_td_808['mean'].round(3)}), duyệt {q_td_808['visited_cells']}/{occ_808} ô có dữ liệu, "
    f"tỉa bỏ {q_td_808['pruned_cells']} nhánh."
)"""))

md(nbf.v4.new_markdown_cell("""## 2. So sánh STING, K-means và DBSCAN trên PAPI 2011–2023

Silhouette, Davies–Bouldin và Calinski–Harabasz được tính trên các điểm thuộc cụm."""))

cd(nbf.v4.new_code_cell("""metrics = pd.read_csv(ROOT / "results/metrics.csv")
show_md(metrics[metrics.scope == "pooled 2011-2023"].to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""### Chọn k cho K-means đối chứng

K-means cần chọn trước số cụm k. Hình dưới vẽ WCSS (tổng bình phương khoảng cách
trong cụm) và silhouette theo k trên cùng hai chỉ tiêu đã chuẩn hóa. WCSS giảm
dần, không có khuỷu rõ rệt. Silhouette cao nhất tại k = 2 (0,445), nên đối chứng
dùng k = 2."""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/kmeans_elbow.png")))"""))

md(nbf.v4.new_markdown_cell("""### Kết quả so sánh

STING tạo một cụm 629 điểm, hai cụm nhỏ 16 và 5 điểm, với 19,6% nhiễu.
Để đọc kết quả trên cùng số quan sát, nhóm dùng giao các điểm mà cả STING
và DBSCAN đều gán vào cụm. Giữ nhãn từ phân hoạch đã học trên 808 quan sát
và tính lại silhouette trên tập giao. K-means gán nhãn cho cả 808 điểm nên
cũng có nhãn trên toàn bộ tập giao."""))

cd(nbf.v4.new_code_cell("""from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score

kmeans_labels = KMeans(n_clusters=2, n_init=10, random_state=42).fit_predict(train_scaled)
dbscan_labels = DBSCAN(eps=0.2, min_samples=5).fit_predict(train_scaled)
shared = (train_labels >= 0) & (dbscan_labels >= 0)
comparison_rows = []
models = [
    ("STING", "STING (frozen)", train_labels),
    ("K-means (k=2)", "k-means k=2", kmeans_labels),
    ("DBSCAN (eps=0,2)", "DBSCAN eps=0.2", dbscan_labels),
]
reference = metrics[metrics.scope == "pooled 2011-2023"].set_index("method")
for label, key, labels in models:
    assigned = labels >= 0
    score = silhouette_score(train_scaled[assigned], labels[assigned])
    score_shared = silhouette_score(train_scaled[shared], labels[shared])
    assert abs(score - reference.loc[key, "silhouette"]) <= 0.0005
    comparison_rows.append((label, int(assigned.sum()), f"{score:.3f}", f"{score_shared:.3f}"))
shared_table = pd.DataFrame(comparison_rows, columns=[
    "Phương pháp", "Điểm thuộc cụm", "Silhouette trên tập riêng", "Silhouette trên tập giao",
])
print(f"Tập giao có {shared.sum()}/{len(train_scaled)} quan sát.")
show_md(shared_table.to_markdown(index=False))
ari_all = adjusted_rand_score(train_labels, dbscan_labels)
ari_shared = adjusted_rand_score(train_labels[shared], dbscan_labels[shared])
assert abs(ari_all - reference.loc["DBSCAN eps=0.2", "ari_vs_sting"]) <= 0.0005
print(f"ARI STING–DBSCAN trên toàn bộ mẫu (gồm nhãn nhiễu): {ari_all:.3f}.")
print(f"ARI STING–DBSCAN trên tập giao các điểm thuộc cụm: {ari_shared:.3f}.")"""))

cd(nbf.v4.new_code_cell(r"""from matplotlib.patches import Ellipse
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import cdist
from scripts.common.fig_style import CLUSTER_COLORS

with style_context():
    # Hình A: So sánh phân bố 2D của STING, K-means và DBSCAN trên 808 điểm 2011-2023
    fig_cmp, axes_cmp = plt.subplots(1, 3, figsize=(13.2, 4.35), dpi=150, sharex=True, sharey=True, layout="constrained")
    n_db_clusters = len(set(dbscan_labels[dbscan_labels >= 0]))
    cmp_specs = (
        (axes_cmp[0], train_labels, f"1. STING (16×16, min_count=5)\n{sting.n_clusters_} cụm · {int((train_labels == -1).sum())} nhiễu ({(train_labels == -1).mean():.1%})"),
        (axes_cmp[1], kmeans_labels, f"2. K-Means (k=2, k-means++)\n2 cụm ({int((kmeans_labels == 0).sum())} + {int((kmeans_labels == 1).sum())}) · 0 nhiễu"),
        (axes_cmp[2], dbscan_labels, f"3. DBSCAN (ε=0,2, min_samples=5)\n{n_db_clusters} cụm · {int((dbscan_labels == -1).sum())} nhiễu ({(dbscan_labels == -1).mean():.1%})"),
    )
    for ax_c, lbls_c, ttl_c in cmp_specs:
        if ax_c is axes_cmp[0]:
            _draw_sting_grid(ax_c, sting)
        ns_c = lbls_c == -1
        if np.any(ns_c):
            ax_c.scatter(train_scaled[ns_c, 0], train_scaled[ns_c, 1], s=16, color=PALETTE["gray"],
                         marker="x", linewidths=0.85, label=f"Nhiễu −1 ({int(ns_c.sum())})", zorder=2.5)
        for cid_c in sorted(set(lbls_c[lbls_c >= 0])):
            mk_c = lbls_c == cid_c
            ax_c.scatter(train_scaled[mk_c, 0], train_scaled[mk_c, 1], s=10,
                         color=CLUSTER_COLORS.get(cid_c, PALETTE["purple"]), alpha=0.72, linewidths=0,
                         label=f"Cụm {cid_c} ({int(mk_c.sum())})", zorder=2.2)
        ax_c.set_title(ttl_c, fontsize=10.2)
        ax_c.grid(alpha=0.14)
        ax_c.legend(loc="upper left", fontsize=7.5, framealpha=0.92, ncols=2 if cid_c >= 2 or np.any(ns_c) else 1)
    axes_cmp[0].set_ylabel("6.1 Y tế công lập (z-score)")
    axes_cmp[1].set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (z-score)")
    fig_cmp.suptitle("Đối chiếu trực quan STING, K-means và DBSCAN trên 808 quan sát PAPI (2011–2023)", fontsize=12.2)
    plt.show()

    # Hình B: Bốn khoảng cách Linkage & ghép vòng lồng nhau + Dendrogram (Day 9 slides 35-47)
    a_pts = np.array([[0.7, 1.2], [1.1, 2.0], [1.5, 1.0], [1.8, 1.7], [0.9, 2.5]])
    b_pts = np.array([[4.1, 2.3], [4.5, 3.2], [5.1, 2.6], [4.8, 1.6], [5.4, 2.1]])
    d_ab = cdist(a_pts, b_pts)
    i_min, j_min = np.unravel_index(np.argmin(d_ab), d_ab.shape)
    i_max, j_max = np.unravel_index(np.argmax(d_ab), d_ab.shape)
    mu_a, mu_b = a_pts.mean(axis=0), b_pts.mean(axis=0)
    pts6 = np.array([[0.8, 1.0], [1.3, 1.25], [4.6, 3.2], [5.1, 3.45], [1.05, 1.85], [4.85, 2.55]])
    z6 = linkage(pts6, method="single")
    members6 = {i: [i] for i in range(len(pts6))}

    fig_hc, (ax_lnk, ax_2d, ax_dn) = plt.subplots(1, 3, figsize=(13.4, 4.4), dpi=150, layout="constrained")
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
    ax_lnk.set_title("1. Bốn khoảng cách Linkage (Day 9 tr.35)", fontsize=10.2)
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
        merged = members6[c1] + members6[c2]
        members6[len(pts6) + step_i] = merged
        sub = pts6[merged]
        cx, cy = sub.mean(axis=0)
        sx = max(0.82, (sub[:, 0].max() - sub[:, 0].min()) + 0.55 + 0.18 * step_i)
        sy = max(0.72, (sub[:, 1].max() - sub[:, 1].min()) + 0.50 + 0.18 * step_i)
        ax_2d.add_patch(Ellipse((cx, cy), width=sx, height=sy, facecolor="none",
                                edgecolor=ring_cols[step_i], linestyle="-" if step_i < 4 else "--",
                                linewidth=1.45, label=f"Bước {step_i + 1} (d={dist:.2f})", zorder=2))
    ax_2d.set_xlim(0.1, 6.2)
    ax_2d.set_ylim(0.2, 4.4)
    ax_2d.set_title("2. Ghép vòng từ dưới lên (tr.37–43)", fontsize=10.2)
    ax_2d.set_xlabel("x1")
    ax_2d.grid(alpha=0.16)
    ax_2d.legend(loc="lower right", fontsize=7.5, framealpha=0.94)

    heights6 = z6[:, 2]
    cut_i = int(np.argmax(np.diff(heights6)))
    thr6 = float((heights6[cut_i] + heights6[cut_i + 1]) / 2)
    k6 = len(pts6) - (cut_i + 1)
    dendrogram(z6, ax=ax_dn, labels=[f"P{i}" for i in range(len(pts6))], color_threshold=thr6)
    ax_dn.axhline(thr6, color="#D55E00", ls="--", lw=1.6, label=f"Cắt ngang d = {thr6:.2f} → k = {k6} cụm")
    ax_dn.set_ylim(0.0, float(heights6.max()) * 1.18)
    ax_dn.set_title("3. Dendrogram & mẹo chọn k (tr.44–47)", fontsize=10.2)
    ax_dn.set_ylabel("Khoảng cách ghép")
    ax_dn.legend(loc="upper left", fontsize=7.8, framealpha=0.92)
    fig_hc.suptitle("Day 9 Hierarchical Clustering: Bốn Linkage & Cắt Dendrogram trên 2D", fontsize=12.5)
    plt.show()"""))

md(nbf.v4.new_markdown_cell("## 3. STING theo từng năm"))

cd(nbf.v4.new_code_cell("""per_year = pd.read_csv(ROOT / "results/per_year.csv")
show_md(per_year.to_markdown(index=False))
print()
single_cluster_years = per_year["k"].eq(1).sum()
print(f"{single_cluster_years}/{len(per_year)} năm có một cụm với lưới 3 × 3 và min_count=3.")"""))

md(nbf.v4.new_markdown_cell("""## 4. Đối chiếu PAPI năm 2024 trên lưới đến năm 2023

Dựng lưới từ 2011–2023 để gán nhãn cho điểm PAPI đã quan sát năm 2024.
Trong 61 tỉnh đủ hai chỉ tiêu, có 48 tỉnh vào cụm lớn và 13 tỉnh nhận nhãn
nhiễu. Hai tỉnh thiếu chỉ tiêu được để trống. Bảng chuyển trạng thái dưới
đây chỉ dùng các tỉnh đủ dữ liệu ở cả hai năm."""))

cd(nbf.v4.new_code_cell("""paired = (rebuilt[rebuilt.year.isin([2023, 2024])]
          .pivot(index="province_code", columns="year", values="pred_cluster")
          .dropna().astype(int))
main_cluster = int(pd.Series(train_labels[train_labels >= 0]).mode().iat[0])
label_names = {main_cluster: "Cụm lớn", -1: "Nhiễu"}
transition = pd.crosstab(paired[2023], paired[2024], rownames=["Năm 2023"],
                         colnames=["Năm 2024"])
transition = transition.rename(index=label_names, columns=label_names)
print(f"Đối chiếu trên {len(paired)} tỉnh đủ dữ liệu ở cả hai năm.")
show_md(transition.to_markdown())
print(f"{transition.loc['Cụm lớn', 'Nhiễu']} tỉnh từ cụm lớn sang nhiễu.")
print(f"{transition.loc['Nhiễu', 'Cụm lớn']} tỉnh từ nhiễu vào cụm lớn.")"""))

cd(nbf.v4.new_code_cell("""for year in (2020, 2024):
    display(Image(filename=str(ROOT / f"results/figs/map_{year}.png")))"""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/evolution.png")))"""))

md(nbf.v4.new_markdown_cell("""**Mục đích của hình phân bổ quan sát 2024.** Đặt hai điểm PAPI đã quan
sát lên lưới đến 2023 để xem độ phủ của vùng dày và nhận diện những trường
hợp nằm ở ngoài vùng. Cùng lưới còn giúp theo dõi tỉnh đổi trạng thái giữa
hai năm. Phần dự báo dùng nhãn suy ra từ điểm quan sát làm mốc đối chiếu
với nhãn suy ra từ điểm do mô hình sinh.

Hai tỉnh thiếu chỉ tiêu được loại khỏi phép gán. Cả 13 tỉnh mang nhãn −1
đều đủ điểm và nằm trong ô có dưới 5 quan sát tham chiếu (không có tỉnh nào
rơi ngoài biên lưới hay có `|z| > 3`; `max |z| = 2,1299`). Nhóm giữ các điểm
này trong mẫu để báo đúng độ phủ 48/61 tỉnh và theo dõi cả các trường hợp đạt
điểm rất cao ở rìa phải/trên (Hà Tĩnh, Bình Thuận, Sóc Trăng, Bà Rịa - Vũng Tàu,
Quảng Ninh, Tây Ninh) lẫn các tỉnh thấp hơn ở chỉ tiêu 6.1 (Hà Nội, Cần Thơ).
Quảng Ninh và Bình Dương thiếu điểm năm 2023 nên sau khi ghép hai năm, bảng còn
59 tỉnh, gồm 48 trong vùng dày và 11 ngoài vùng dày."""))

cd(nbf.v4.new_code_cell("""from scripts.common.papi_pred_common import GRID_ASSIGNMENT_LABELS, describe_grid_assignment

display(Image(filename=str(ROOT / "results/figs/predict_2024.png")))
observed_grid = describe_grid_assignment(panel.loc[panel.year.eq(2024)], features, scaler, sting)
status_counts = observed_grid.grid_status.value_counts().rename(index=GRID_ASSIGNMENT_LABELS)
display(status_counts.rename("Số tỉnh").rename_axis("Kết quả gán").to_frame())
review_2024 = observed_grid.loc[observed_grid.grid_status.ne("in_cluster")].copy()
valid_2024 = review_2024[features].notna().all(axis=1)
review_2024["max_abs_z"] = np.nan
review_2024.loc[valid_2024, "max_abs_z"] = np.abs(
    scaler.transform(review_2024.loc[valid_2024, features])
).max(axis=1)
sparse_2024 = review_2024.loc[review_2024.grid_status.eq("sparse_cell")]
assert (sparse_2024["max_abs_z"] <= 3).all()
print(f"Cả {len(sparse_2024)}/{len(sparse_2024)} tỉnh ô thưa năm 2024 đều có |z| ≤ 3 "
      f"trên lưới tham chiếu (|z| lớn nhất = {sparse_2024['max_abs_z'].max():.4f}).")
review_2024["grid_status"] = review_2024.grid_status.map(GRID_ASSIGNMENT_LABELS)
display(review_2024[["province_vi", *features, "max_abs_z", "grid_cell", "reference_count", "grid_status"]].rename(columns={
    "province_vi": "Tỉnh/thành phố", "sd_4_2": "Điểm 4.2", "sd_6_1": "Điểm 6.1",
    "max_abs_z": "|z| lớn nhất", "grid_cell": "Ô lưới",
    "reference_count": "Số điểm tham chiếu", "grid_status": "Lý do",
}).round(4).reset_index(drop=True))
print("Bảng 63 tỉnh kèm ô, số điểm tham chiếu và lý do gán nằm trong results/papi_observed_grid_2024.csv.")
lang_son_code = panel.loc[panel.province_vi.eq("Lạng Sơn"), "province_code"].iat[0]
lang_son = paired.loc[lang_son_code]
for year, label in lang_son.items():
    region = "ngoài vùng dày" if label == -1 else f"cụm {label}"
    print(f"Lạng Sơn {year}: {region} trên cùng lưới đến năm 2023.")"""))

md(nbf.v4.new_markdown_cell("""### 4.1 Dự báo hai chỉ tiêu năm 2024 từ dữ liệu đến năm 2023

Từ tám chỉ tiêu ở năm t, nhóm dự báo **4.2 Kiểm soát tham nhũng trong cung
ứng dịch vụ công** và **6.1 Y tế công lập** ở năm t+1. Ghép cặp theo mã tỉnh
và hai năm liên tiếp. Bốn ứng viên gồm giữ điểm năm trước, Ridge, Random
Forest và trung bình 50/50 của hai mô hình. Chọn riêng cho từng chỉ tiêu
bằng MAE trung bình của sáu lượt kiểm định theo thời gian. Mỗi lượt chỉ
dùng cặp huấn luyện có năm đích đến mốc xuất phát của lượt đó.

Với mốc cuối 2023, ô dưới tạo hai điểm dự báo cho 2024 từ lịch sử. Scaler
và lưới STING cũng được dựng từ lịch sử. Điểm PAPI 2024 sẽ được dùng ở ô
đối chiếu kế tiếp. Đây là đánh giá hồi cứu trên một năm đã có số liệu."""))

cd(nbf.v4.new_code_cell("""from scripts.common.papi_forecast import (
    FEATURES, MODEL_NAMES, ORIGIN_YEAR, TARGETS, forecast_from_history, scenario_auc, score_forecast,
)

history = panel.loc[panel.year <= ORIGIN_YEAR].copy()
assert tuple(cfg["features"]) == TARGETS
run = forecast_from_history(history, cfg["sting"])
folds = run.validation[["origin_year", "target_year", "last_train_target_year",
                        "n_train", "n_validation"]].drop_duplicates()
assert folds.last_train_target_year.le(folds.origin_year).all()
assert folds.target_year.le(ORIGIN_YEAR).all()
print(f"Huấn luyện cuối: {run.train_pairs} cặp. Dự báo: {len(run.predictions)} tỉnh đủ tám đầu vào.")
print("Tám đầu vào:", ", ".join(FEATURES))
display(folds.rename(columns={
    "origin_year": "Mốc xuất phát", "target_year": "Năm đích kiểm định",
    "last_train_target_year": "Năm đích huấn luyện cuối", "n_train": "Cặp huấn luyện",
    "n_validation": "Cặp kiểm định",
}))
avg = run.validation.pivot_table(index="target", columns="method", values="mae")
display(avg.rename(columns=MODEL_NAMES).round(4))
for target, method in run.selection.items():
    print(f"{target}: {MODEL_NAMES[method]} theo MAE trung bình qua sáu lượt kiểm định.")"""))

md(nbf.v4.new_markdown_cell("""### 4.2 Đo sai số dự báo trên các tỉnh đối chiếu được

Ghép điểm PAPI 2024 theo mã tỉnh. Cùng một nhóm tỉnh có đủ hai điểm thực
tế được dùng để tính MAE, RMSE và độ lệch trung bình cho cả mô hình lẫn
mốc giữ nguyên. MAE là trung bình độ lệch tuyệt đối. RMSE nhạy hơn với
sai số lớn. Độ lệch âm cho biết dự báo thấp hơn quan sát về trung bình.

Có 61 tỉnh đủ tám đầu vào năm 2023 để tạo dự báo và 61 tỉnh đủ hai điểm
quan sát năm 2024 để gán lên lưới. Hai tiêu chí chọn được 59 tỉnh chung.
Với chỉ tiêu 4.2, Ridge giảm MAE. So với giữ điểm 2023, RMSE tăng từ
0,0953 lên 0,0972 và độ lệch trung bình từ −0,0245 xuống −0,0581."""))

cd(nbf.v4.new_code_cell("""observed = panel.loc[panel.year == ORIGIN_YEAR + 1].copy()
scored, errors, zones = score_forecast(run, observed)
archive_table = pd.read_csv(ROOT / "results/papi_forecast_provinces_2024.csv")
pd.testing.assert_frame_equal(scored.astype({"actual_cluster": "float64"}), archive_table,
                              check_dtype=False, check_exact=False, atol=1e-9, rtol=1e-9)
n_matched = int(scored.actual_cluster.notna().sum())
print(f"Có {len(scored)} dự báo, đối chiếu được {n_matched} tỉnh đủ hai điểm quan sát.")
actual_eligible = observed_grid.loc[observed_grid.cluster.notna()]
matched_codes = scored.loc[scored.actual_cluster.notna(), "province_code"]
omitted = actual_eligible.loc[~actual_eligible.province_code.isin(matched_codes), "province_vi"]
print(f"Có điểm thực tế 2024 nhưng thiếu đầu vào 2023: {', '.join(omitted)}.")
print(f"Ngoài vùng dày: {actual_eligible.cluster.eq(-1).sum()}/{len(actual_eligible)} tỉnh quan sát, "
      f"{scored.actual_cluster.eq(-1).sum()}/{n_matched} tỉnh đối chiếu dự báo.")
display(errors.rename(columns={
    "target": "Chỉ tiêu", "method": "Cách dự báo", "n": "Số tỉnh", "mae": "MAE", "rmse": "RMSE",
    "bias": "Độ lệch trung bình",
}).replace({"forecast": "Mô hình đã chọn", "carry": "Giữ điểm 2023"}).round(4))
display(Image(filename=str(ROOT / "results/figs/papi_forecast_values.png")))"""))

md(nbf.v4.new_markdown_cell("""### 4.3 Đọc vùng STING khi phần lớn điểm nằm trong cụm lớn

Chiếu các điểm dự báo, điểm giữ nguyên và điểm quan sát vào **cùng lưới
đến 2023**. Thêm đối chứng luôn chọn cụm phổ biến nhất trong lịch sử.
Tỷ lệ trùng nhãn dùng nhãn suy ra từ lưới, còn tỷ lệ phát hiện ngoài vùng
dày tính riêng trên số tỉnh có điểm quan sát ngoài vùng dày.

Điểm dự báo đưa cả 59 tỉnh vào cụm lớn và nhận ra 0/11 tỉnh ngoài vùng.
Mức trùng nhãn 48/59 và độ đúng cân bằng 0,50 bằng mốc luôn chọn cụm lớn.

Nhóm giữ nguyên từng cặp sai số ngoài lượt kiểm định của hai chỉ tiêu,
cộng chúng vào hai điểm dự báo rồi chiếu từng kịch bản lên lưới. Tỷ lệ
kịch bản ngoài vùng dày là thước đo độ nhạy theo sai số lịch sử. AUC đánh
giá việc xếp hạng các tỉnh khi đối chiếu năm 2024. Đây là kiểm tra thăm dò
trên một năm, với sai số gộp từ các tỉnh và năm trước."""))

cd(nbf.v4.new_code_cell("""zone_table = zones[["method", "n", "out_correct", "missed_out", "false_out",
                    "exact_label_agreement", "out_recall", "balanced_zone_accuracy"]]
display(zone_table.rename(columns={
    "method": "Cách gán vùng", "n": "Số tỉnh", "out_correct": "Nhận ra ngoài vùng",
    "missed_out": "Bỏ sót", "false_out": "Gán ngoài nhầm", "exact_label_agreement": "Trùng nhãn lưới",
    "out_recall": "Tỷ lệ nhận ra ngoài vùng", "balanced_zone_accuracy": "Độ đúng cân bằng hai vùng",
}).replace({"forecast": "Điểm dự báo", "carry": "Giữ điểm 2023", "majority": "Luôn chọn cụm lớn"}).round(4))
false_negatives = int(zones.loc[zones.method.eq("forecast"), "missed_out"].item())
print(f"Dự báo điểm bỏ sót {false_negatives} tỉnh ngoài vùng dày.")
print(f"{run.scenario_count} cặp sai số lịch sử mỗi tỉnh. AUC xếp hạng ngoài vùng = {scenario_auc(scored):.4f}.")
display(Image(filename=str(ROOT / "results/figs/papi_forecast_grid.png")))
probe = scored.loc[scored.province_vi.eq("Lạng Sơn")].iloc[0]
for target in TARGETS:
    print(f"Lạng Sơn, {target}: điểm 2023 = {probe[f'carry_{target}']:.4f}, "
          f"dự báo = {probe[f'forecast_{target}']:.4f}, quan sát 2024 = {probe[f'actual_{target}']:.4f}.")
print("Kết quả từng tỉnh nằm trong results/papi_forecast_provinces_2024.csv.")"""))

md(nbf.v4.new_markdown_cell("""## 5. Kết luận

- STING gom các ô dày liên thông. Trên PAPI 2011–2023, cụm lớn có 629 điểm,
  hai cụm nhỏ có 16 và 5 điểm, với 19,6% nhiễu.
- Các cấu hình lưới làm thay đổi số cụm và tỷ lệ nhiễu. Kết quả mô tả hai chỉ
  tiêu được chọn, trong phạm vi lưới và thời gian đã kiểm tra.
- Khi đọc silhouette, xem cùng tỉ lệ nhiễu. Các phương pháp có thể được đánh giá
  trên các tập điểm khác nhau.
- Dự báo điểm giảm MAE cho cả hai chỉ tiêu so với giữ nguyên năm 2023, trong
  khi RMSE của 4.2 tăng nhẹ. Khi chiếu dự báo điểm lên lưới, kết quả nghiêng
  về cụm lớn và bỏ sót các quan sát ngoài vùng dày. Sai số điểm và độ đúng
  theo vùng cần được đọc riêng.

**Nguồn:** Wang, Yang & Muntz (VLDB 1997), PAPI (CECODES/VFF-CRT/RTA/UNDP),
Le et al. (Mendeley DOI 10.17632/wbk42j9wc8.1) và Open Development Vietnam."""))

_rob = pd.read_csv(ROOT / "results" / "robustness.csv")
_pca = _rob[_rob["branch"].str.startswith("PCA")].iloc[0]
_goc = _rob[_rob["branch"].str.contains("(gốc OFAT)", regex=False)].iloc[0]
_f3 = _rob[_rob["branch"].str.contains("OFAT f=3")].iloc[0]
_mc2 = _rob[_rob["branch"].str.contains("OFAT mc=2")].iloc[0]
_lv2 = _rob[_rob["branch"].str.contains("OFAT lv=2")].iloc[0]
md(nbf.v4.new_markdown_cell(f"""## Phụ lục A. Kiểm tra bổ sung trên nhiều chỉ tiêu

- Hai thành phần PCA giữ {_pca.explained_var_total:.1%} phương sai và cho {_pca.k:.0f} cụm.
- Với 8 chiều giai đoạn 2018–2024, cấu hình gốc cho {_goc.k:.0f} cụm và {_goc.noise_ratio:.1%} nhiễu.
- Khi chỉ đổi factor thành 3, tỷ lệ nhiễu là {_f3.noise_ratio:.1%}. Khi đổi mức lưới,
  có {_lv2.k:.0f} cụm. Khi giảm min_count còn 2, có {_mc2.k:.0f} cụm và
  {_mc2.noise_ratio:.1%} nhiễu, với silhouette {_mc2.silhouette:.3f}."""))

cd(nbf.v4.new_code_cell("""rob = pd.read_csv(ROOT / "results/robustness.csv")
show_md(rob.to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""## Phụ lục B. Thí nghiệm học phần trên 6.1 và nhãn lưới

Thí nghiệm đơn chỉ tiêu này chọn mô hình theo R² và mẫu đủ 6.1. Mục 4 dùng
mẫu chung của cả hai chỉ tiêu và chọn theo MAE. Bài phân loại phụ đo mức
khớp với nhãn do STING sinh ở mốc 2023→2024."""))

cd(nbf.v4.new_code_cell("""sup = pd.read_csv(ROOT / "results/supervised_metrics.csv")
show_md(sup.to_markdown(index=False))"""))

cd(nbf.v4.new_code_cell("""import joblib
from sklearn.metrics import mean_absolute_error
from scripts.common.papi_pred_common import REGRESSION_FEATURES
from scripts.supervised.predict_supervised import build_regression_pairs, expanding_origin_folds

print("Tám chỉ tiêu dùng cho hồi quy:", ", ".join(REGRESSION_FEATURES))
regression_pairs = build_regression_pairs(panel)
training_origins = regression_pairs.loc[
    regression_pairs.year_t < 2023, "year_t"
].to_numpy()
print("Các lượt kiểm định theo thời gian dùng năm gốc trước 2023.")
folds = expanding_origin_folds(training_origins, first_validation_origin=2017)
for fold_number, (train_idx, val_idx) in enumerate(folds, start=1):
    print(
        f"Lượt {fold_number}: học đến năm gốc {training_origins[train_idx].max()}, "
        f"kiểm định tại năm gốc {training_origins[val_idx][0]}."
    )

regression_metrics = pd.read_csv(ROOT / "results/supervised_metrics.csv")
regression_models = regression_metrics[
    (regression_metrics.task == "regression")
    & ~regression_metrics.model.isin(
        ["carry-forward (giữ giá trị năm nay)", "trung bình train"]
    )
].dropna(subset=["value_cv"])
chosen = regression_models.loc[regression_models.value_cv.idxmax()]
print(f"Mô hình hồi quy được chọn qua kiểm định: {chosen.model} (R²={chosen.value_cv:.3f}).")

ridge = joblib.load(ROOT / "models/sup_ridge.joblib")
holdout = regression_pairs[regression_pairs.year_t == 2023]
ridge_mae = mean_absolute_error(holdout.y, ridge.predict(holdout[REGRESSION_FEATURES].to_numpy()))
carry_mae = mean_absolute_error(holdout.y, holdout["carry"])
ridge_row = regression_metrics[(regression_metrics.task == "regression") & (regression_metrics.model == "ridge")].iloc[0]
assert abs(ridge_mae - ridge_row.holdout_mae) < 1e-5
print(f"Tính lại trên {len(holdout)} cặp 2023→2024: MAE của Ridge = {ridge_mae:.4f}, "
      f"MAE khi giữ điểm năm trước = {carry_mae:.4f}.")"""))

cd(nbf.v4.new_code_cell(r"""from sklearn.metrics import accuracy_score, f1_score, log_loss, r2_score
from scripts.supervised.predict_supervised import build_classification_pairs

y_true_reg = holdout.y.to_numpy()
y_pred_ridge = ridge.predict(holdout[REGRESSION_FEATURES].to_numpy())
ridge_r2 = r2_score(y_true_reg, y_pred_ridge)

clf_model = joblib.load(ROOT / "models/sup_classifier.joblib")
clf_pairs = build_classification_pairs(panel, features, params)
clf_hold = clf_pairs[clf_pairs.year_t == 2023]
Xc_te = clf_hold[REGRESSION_FEATURES].to_numpy()
yc_te = clf_hold["y"].to_numpy()
probs_te = clf_model.predict_proba(Xc_te)[:, 1]
logits_te = clf_model.decision_function(Xc_te)
preds_te = clf_model.predict(Xc_te)
bce_loss = log_loss(yc_te, probs_te)
clf_acc = accuracy_score(yc_te, preds_te)
clf_mf1 = f1_score(yc_te, preds_te, average="macro", labels=[0, 1], zero_division=0)
print(f"Day 6 Logistic holdout 2023→2024 ({len(yc_te)} tỉnh): "
      f"Binary Cross-Entropy = {bce_loss:.4f} | Acc = {clf_acc:.3f} | Macro-F1 = {clf_mf1:.3f}.")

with style_context():
    fig, (ax_reg, ax_poly, ax_log) = plt.subplots(1, 3, figsize=(13.4, 4.4), dpi=150, layout="constrained")
    # Trái: Ridge + đoạn phần dư dọc ε_i
    lo_r = float(min(y_true_reg.min(), y_pred_ridge.min())) - 0.03
    hi_r = float(max(y_true_reg.max(), y_pred_ridge.max())) + 0.03
    ax_reg.plot([lo_r, hi_r], [lo_r, hi_r], "--", color="#5A6B7C", lw=1.2, label="Đường chéo y = ŷ", zorder=1)
    for idx_i, (yt, yp) in enumerate(zip(y_true_reg, y_pred_ridge, strict=True)):
        ax_reg.plot([yp, yp], [yp, yt], "-", color="#D55E00", alpha=0.58, lw=1.05,
                    label="Phần dư ε_i = y_i − ŷ_i" if idx_i == 0 else None, zorder=2)
    ax_reg.scatter(y_pred_ridge, y_true_reg, s=28, color=PALETTE["blue"], edgecolors="white", linewidths=0.5,
                   label="Quan sát 2024 (n = 59)", zorder=3)
    ax_reg.set_xlim(lo_r, hi_r)
    ax_reg.set_ylim(lo_r, hi_r)
    ax_reg.set_xlabel("Điểm dự báo Ridge ŷ (2023 → 2024)")
    ax_reg.set_ylabel("Điểm 6.1 thực tế y (2024)")
    ax_reg.set_title(f"1. Day 6 Hồi quy Ridge & phần dư ε_i\nMAE = {ridge_mae:.4f} · Holdout R² = {ridge_r2:.3f}", fontsize=10.0)
    ax_reg.grid(alpha=0.18)
    ax_reg.legend(loc="upper left", fontsize=7.8, framealpha=0.92)

    # Giữa: Polynomial Regression bậc m <= n (Day 6 tr.13-14 & 19)
    x_d6 = np.array([1.5, 2.0, 3.5, 5.0, 6.5, 7.0])
    y_d6 = np.array([-3.0, -3.5, 0.5, -1.0, 2.5, 1.5])
    x_gd = np.linspace(1.2, 7.3, 250)
    for deg_d, col_d, ls_d, lbl_d in (
        (1, "#64748B", "--", "m = 1 (tuyến tính)"),
        (2, PALETTE["green"], "-.", "m = 2 (bậc hai)"),
        (5, "#D55E00", "-", "m = 5 (6 ẩn/6 điểm: Overfit!)"),
    ):
        xp = np.column_stack([x_d6 ** p for p in range(deg_d + 1)])
        bp = np.linalg.solve(xp.T @ xp, xp.T @ y_d6)
        xg = np.column_stack([x_gd ** p for p in range(deg_d + 1)])
        ax_poly.plot(x_gd, xg @ bp, ls=ls_d, color=col_d, lw=1.8 if deg_d == 5 else 1.5, label=lbl_d, zorder=3 if deg_d == 5 else 2)
    ax_poly.scatter(x_d6, y_d6, s=44, color="#1E3D5E", edgecolors="white", linewidths=0.7, zorder=4)
    ax_poly.set_ylim(-5.2, 5.2)
    ax_poly.set_xlabel("x (ví dụ 6 điểm Day 6 tr.19)")
    ax_poly.set_ylabel("y")
    ax_poly.set_title("2. Day 6 Đa thức m = 1, 2, 5 & Bẫy Overfit\nm = 5 (MSE train = 0, dao động mạnh)", fontsize=10.0)
    ax_poly.grid(alpha=0.18)
    ax_poly.legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    # Phải: Logistic Regression Sigmoid & Binary Cross-Entropy
    z_grid = np.linspace(float(logits_te.min()) - 0.6, float(logits_te.max()) + 0.6, 200)
    sig_grid = 1.0 / (1.0 + np.exp(-z_grid))
    ax_log.plot(z_grid, sig_grid, "-", color=PALETTE["blue"], lw=2.0, label="Sigmoid f(z) = 1 / (1 + e⁻ᶻ)", zorder=2)
    ax_log.axvline(0.0, color="#64748B", linestyle="--", lw=1.0, label="Ngưỡng z = 0 (P = 0,5)", zorder=1)
    ax_log.axhline(0.5, color="#CBD5E1", linestyle=":", lw=1.0, zorder=1)
    m0 = yc_te == 0
    m1 = yc_te == 1
    rng_j = np.random.default_rng(42)
    y0_j = rng_j.uniform(-0.03, 0.03, size=int(m0.sum()))
    y1_j = 1.0 + rng_j.uniform(-0.03, 0.03, size=int(m1.sum()))
    ax_log.scatter(logits_te[m0], y0_j, s=40, color="#D55E00", marker="x", linewidths=1.3,
                   label=f"Lớp 0: nhiễu −1 ({int(m0.sum())})", zorder=4)
    ax_log.scatter(logits_te[m1], y1_j, s=28, color=PALETTE["green"], alpha=0.85, edgecolors="white", linewidths=0.45,
                   label=f"Lớp 1: vùng dày ({int(m1.sum())})", zorder=4)
    ax_log.set_ylim(-0.14, 1.15)
    ax_log.set_xlabel("Logit tuyến tính z = β₀ + wᵀx")
    ax_log.set_ylabel("Xác suất P(vùng dày | x)")
    ax_log.set_title(f"3. Day 6 Logistic Sigmoid (nhãn STING)\nBinary Cross-Entropy = {bce_loss:.4f} · Acc = {clf_acc:.3f}", fontsize=10.0)
    ax_log.grid(alpha=0.18)
    ax_log.legend(loc="center left", fontsize=7.6, framealpha=0.92)
    plt.show()"""))

md(nbf.v4.new_markdown_cell("""### Cải thiện phân loại mất cân bằng nhãn bằng `class_weight='balanced'`

Do cụm lớn chiếm đa số (~80%), mô hình mặc định dễ bỏ sót lớp rìa `0`. Nhóm kiểm chứng trực tiếp phương án cân bằng lớp trên **cùng 6 fold expanding-origin (2017–2022, 738 cặp)** và đối chiếu trên holdout 2023→2024 (59 tỉnh)."""))

cd(nbf.v4.new_code_cell(r"""from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from sklearn.pipeline import Pipeline
from scripts.supervised.predict_supervised import expanding_year_splits

clf_tr = clf_pairs[clf_pairs.year_t < 2023].reset_index(drop=True)
X_ctr, y_ctr = clf_tr[REGRESSION_FEATURES].to_numpy(), clf_tr["y"].to_numpy()
splits_cv = expanding_year_splits(clf_tr["year_t"].to_numpy(), y_ctr)

bal_specs = (
    ("LR gốc (mặc định)", lambda: Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(C=1.0, max_iter=3000, random_state=42))])),
    ("LR balanced (C=0,3)", lambda: Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(C=0.3, class_weight="balanced", max_iter=3000, random_state=42))])),
    ("RF balanced (depth=6, leaf=2)", lambda: RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=1)),
)
bal_rows = []
for bname, bfactory in bal_specs:
    cv_mf1 = [
        f1_score(y_ctr[vi], bfactory().fit(X_ctr[ti], y_ctr[ti]).predict(X_ctr[vi]),
                 average="macro", labels=[0, 1], zero_division=0)
        for ti, vi in splits_cv
    ]
    bfit = bfactory().fit(X_ctr, y_ctr)
    bpred = bfit.predict(Xc_te)
    bal_rows.append((
        bname,
        float(np.mean(cv_mf1)),
        accuracy_score(yc_te, bpred),
        f1_score(yc_te, bpred, average="macro", labels=[0, 1], zero_division=0),
        recall_score(yc_te, bpred, pos_label=0),
    ))
bal_df = pd.DataFrame(bal_rows, columns=[
    "Mô hình", "Macro-F1 CV (6 fold)", "Acc holdout", "Macro-F1 holdout", "Recall lớp 0 (nhiễu)",
])
show_md(bal_df.round(4).to_markdown(index=False))

with style_context():
    fig_b, (ax_cv, ax_ho) = plt.subplots(1, 2, figsize=(10.8, 3.8), dpi=150, layout="constrained")
    x_pos = np.arange(len(bal_df))
    cols_b = ("#64748B", PALETTE["blue"], PALETTE["green"])
    bars1 = ax_cv.bar(x_pos, bal_df["Macro-F1 CV (6 fold)"], width=0.52, color=cols_b)
    ax_cv.bar_label(bars1, fmt="%.3f", padding=3, fontsize=9)
    ax_cv.set_xticks(x_pos, bal_df["Mô hình"], rotation=12, fontsize=8.5)
    ax_cv.set_ylim(0.0, 0.66)
    ax_cv.set_ylabel("Macro-F1 trung bình")
    ax_cv.set_title("1. Kiểm định 6 fold (2017–2022, 738 cặp)", fontsize=10.2)
    ax_cv.grid(axis="y", alpha=0.18)

    w_bar = 0.34
    b_mf1 = ax_ho.bar(x_pos - w_bar / 2, bal_df["Macro-F1 holdout"], width=w_bar, color=PALETTE["blue"], label="Macro-F1 holdout")
    b_rec = ax_ho.bar(x_pos + w_bar / 2, bal_df["Recall lớp 0 (nhiễu)"], width=w_bar, color=PALETTE["orange"], label="Recall lớp 0 (11 tỉnh rìa)")
    ax_ho.bar_label(b_mf1, fmt="%.3f", padding=3, fontsize=8.2)
    ax_ho.bar_label(b_rec, fmt="%.3f", padding=3, fontsize=8.2)
    ax_ho.set_xticks(x_pos, bal_df["Mô hình"], rotation=12, fontsize=8.5)
    ax_ho.set_ylim(0.0, 0.72)
    ax_ho.set_ylabel("Điểm trên holdout 2024 (n = 59)")
    ax_ho.set_title("2. Hiệu quả khi kiểm chứng holdout 2023→2024", fontsize=10.2)
    ax_ho.grid(axis="y", alpha=0.18)
    ax_ho.legend(loc="upper right", fontsize=8.2, framealpha=0.92)
    plt.show()"""))

md(nbf.v4.new_markdown_cell("""## Phụ lục C. Đối chiếu PCI và nghèo GSO

Nguồn đối chiếu gồm PCI của VCCI–USAID và tỷ lệ hộ nghèo cấp tỉnh GSO
PX-Web V14.47. Dữ liệu nghèo 2017–2019 lấy từ Niên giám Thống kê 2020/2021.
Kiểm định gồm dữ liệu gộp thô và dữ liệu đã trừ trung vị theo năm."""))

cd(nbf.v4.new_code_cell("""pov = pd.read_csv(ROOT / "results/poverty_validation.csv")

pooled_sections = ["poverty_pooled_raw", "poverty_pooled_demeaned", "test_mw_noise_vs_c2"]
pov_pool = pov[pov.section.isin(pooled_sections)].copy()
has_stats = pov_pool["mean"].notna() & pov_pool["mean"].astype(str).str.strip().ne("")
has_note = pov_pool["note"].notna() & pov_pool["note"].astype(str).str.strip().ne("")
show_md(pov_pool[has_stats].to_markdown(index=False))
print()
show_md(pov_pool[has_note][["section", "group", "n", "note"]].to_markdown(index=False))
print()

def _pov_note(section, group):
    return str(pov[(pov.section == section) & (pov.group == group)].iloc[0]["note"])

print("Gộp thô:                ", _pov_note("poverty_pooled_raw", "Kruskal–Wallis"))
print("Đã trừ median trong năm:", _pov_note("poverty_pooled_demeaned", "Kruskal–Wallis"))
for _, r in pov[pov.section == "test_mw_noise_vs_c2"].iterrows():
    print(f"{r['group']}: {r['note']}")
print()
display(Image(filename=str(ROOT / "results/figs/external_poverty_by_cluster.png")))"""))

nb["cells"] = cells
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print("written:", OUT)
