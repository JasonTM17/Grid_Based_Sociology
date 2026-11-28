"""Sinh + execute notebooks/Nhom15_STING_PAPI.ipynb — notebook hoàn chỉnh duy nhất của đồ án.

Hợp nhất đầy đủ phần demo cơ chế STING 3×3 / dữ liệu giả lập / z-score / so sánh 680 điểm
(từ giai đoạn giữa kỳ) cùng toàn bộ pipeline tiền xử lý 6 bước, phân tích từng năm 2011–2024,
thống kê bàn giao 63 tỉnh cho khách hàng, thí nghiệm dự báo thăm dò, kiểm chứng ngoại lai và
các phụ lục có giám sát.

Cách dùng:
    python scripts/notebooks/gen_final_analysis.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from base64 import b64decode
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat as nbf
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "Nhom15_STING_PAPI.ipynb"


@contextmanager
def _publication_lock(target: Path) -> Iterator[None]:
    lock_path = target.parent / ".ipynb_checkpoints" / f".{target.name}.publish.lock"
    lock_path.parent.mkdir(exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        try:
            if os.name == "nt":
                import msvcrt

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Không giữ được khóa cập nhật notebook.") from error
        yield


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells: list = []
    md = cells.append
    cd = cells.append

    md(nbf.v4.new_markdown_cell("""# ỨNG DỤNG THUẬT TOÁN PHÂN CỤM DỰA TRÊN LƯỚI STING ĐỂ PHÂN TÍCH ĐẶC ĐIỂM VÀ SỰ BIẾN ĐỘNG CỦA CÁC CHỈ SỐ QUẢN TRỊ, HÀNH CHÍNH CÔNG TẠI 63 TỈNH, THÀNH PHỐ VIỆT NAM DỰA TRÊN DỮ LIỆU PAPI GIAI ĐOẠN 2011–2024

*APPLICATION OF STING GRID-BASED CLUSTERING TO ANALYZE GOVERNANCE AND PUBLIC ADMINISTRATION PERFORMANCE PATTERNS AND TEMPORAL CHANGES ACROSS 63 VIETNAMESE PROVINCES USING PAPI DATA (2011–2024)*

**Đồ án môn Học máy · Nhóm 15 · Chủ đề 6 — Grid-based clustering (STING)**<br>
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051) · GVHD: ThS. Lê Minh Tân

**Hướng dẫn chạy lại.** Giải nén toàn bộ gói nộp (hoặc mở trong thư mục gốc repo) tại thư mục chứa `src/`, `data/`, `scripts/`, `models/`, `results/`, chọn **Restart Kernel → Run All** để thực thi từ đầu đến cuối (toàn bộ bảng và hình được tái lập tất định; notebook đi kèm về 6 bước làm sạch từ 14 Excel gốc là `Nhom15_TienXuLy_PAPI.ipynb`)."""))

    cd(nbf.v4.new_code_cell("""import json
import sys
from collections import Counter
from pathlib import Path

_PROJECT_MARKERS = (
    "src/sting.py",
    "src/preprocessing.py",
    "scripts/common/midterm_clustering.py",
    "data/processed/papi_panel_63_2011_2024.csv",
    "models/predict_config.json",
)


def _find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if all((candidate / marker).is_file() for marker in _PROJECT_MARKERS):
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy thư mục chứa mã nguồn và dữ liệu PAPI. "
        "Hãy mở notebook tại thư mục gốc đồ án hoặc thư mục gói đã giải nén."
    )


ROOT = _find_project_root()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display
from matplotlib.patches import FancyArrowPatch, Rectangle
from sklearn.cluster import DBSCAN, KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from preprocessing import (
    ALLOWLIST_FEATURES,
    FEATURE_LABELS,
    PREPROCESSING_PIPELINE,
    check_external_integration,
    feature_selection_summary,
    run_preprocessing_pipeline,
    run_sting_preprocessing_experiments,
    scale_audit,
)
from scripts.common.fig_style import CLUSTER_COLORS, PALETTE, apply_style, style_context
from scripts.common.midterm_clustering import (
    CELL_Z_EXAMPLE,
    DBSCAN_OPTIONS,
    FEATURES,
    GRID,
    K_CANDIDATES,
    KMEANS_OPTIONS,
    THRESHOLDS,
    clustered_silhouette,
    comparison_figure,
    fit_grid,
    hierarchy_levels_figure,
    kmeans_elbow_figure,
    noise_and_trap_figure,
    raw_dbscan_radius,
    reference_grid_assignments,
    scaling_comparison_figure,
    sensitivity_grid_figure,
    sting_steps_figure,
)
from scripts.common.papi_pred_common import load_panel
from sting import STING

apply_style()


def show_md(text: str) -> None:
    display(Markdown(text))


panel = load_panel()
assert panel.shape == (882, 41)
assert not panel.duplicated(["province_code", "year"]).any()
print(f"Bảng PAPI có {len(panel)} quan sát tỉnh–năm và {panel.shape[1]} cột.")
print(
    f"Phạm vi gồm {panel.province_code.nunique()} tỉnh, thành phố giai đoạn "
    f"{panel.year.min()}–{panel.year.max()}."
)"""))

    md(nbf.v4.new_markdown_cell("""## Phần 1. Lý thuyết STING, cài đặt từ đầu và kiểm chứng giả lập

### 1.1 Phương pháp STING và ví dụ lưới 3 × 3

STING gốc ([Wang, Yang & Muntz, VLDB 1997](https://www.vldb.org/conf/1997/P186.PDF)) chia không gian nhiều chiều thành hệ lưới phân cấp, lưu số đếm và thống kê phân phối trong từng ô rồi truy vấn từ tầng thô xuống tầng mịn. Trong biến thể cài đặt của nhóm (`src/sting.py`):

1. `fit(X)` đưa từng điểm vào hệ ô lưới phân cấp và tính `count`, `mean`, `std`, `min`, `max` cho mỗi ô.
2. `cluster(level, connectivity=1)` giữ các ô đạt ngưỡng `min_count` rồi dùng duyệt sâu (DFS) theo kề 4 hướng chung cạnh để gán nhãn cụm; điểm thuộc ô thưa hoặc ngoài biên mang nhãn `−1`.
3. `predict(X_moi)` ánh xạ dữ liệu mới vào cùng khung lưới đã khóa.

Ví dụ tối thiểu 15 điểm trên lưới `3 × 3` với ngưỡng `min_count = 3` minh họa cơ chế: các ô dày của hai nhóm `7` điểm chỉ kề góc nên tách thành **2 cụm riêng**, còn `1` điểm lẻ ở `(0, 1)` mang nhãn nhiễu `−1`."""))

    cd(nbf.v4.new_code_cell("""counts_3x3 = np.array([[4, 3, 0], [1, 0, 4], [0, 0, 3]])
positions_3x3 = [(col, 2 - row) for row in range(3) for col in range(3)]
points_3x3 = np.repeat(positions_3x3, counts_3x3.ravel(), axis=0)
model_3x3 = STING(n_levels=2, factor=3, min_count=3).fit(points_3x3)
labels_3x3 = model_3x3.cluster(level=1, connectivity=1)

cell_counts = np.zeros_like(counts_3x3)
for (x_idx, y_idx), cell in model_3x3.cells_[1].items():
    cell_counts[2 - y_idx, x_idx] = cell.count
print("Số điểm trong từng ô lưới 3×3:")
print(cell_counts)
assert np.array_equal(cell_counts, counts_3x3)

group_sizes = sorted(np.bincount(labels_3x3[labels_3x3 >= 0]).tolist())
noise_count_3x3 = int((labels_3x3 == -1).sum())
assert group_sizes == [7, 7] and noise_count_3x3 == 1
print(f"{model_3x3.n_clusters_} cụm, mỗi cụm {group_sizes[0]} điểm. {noise_count_3x3} điểm nhiễu.")
fig_steps = sting_steps_figure()
plt.show()"""))

    md(nbf.v4.new_markdown_cell("""### 1.2 Kiểm chứng trên dữ liệu giả lập (240 điểm Gauss)

Nhóm sinh 240 điểm từ 2 cụm Gauss (`make_blobs`) để kiểm chứng bảo toàn số điểm qua mọi tầng lưới và đo mức khớp `ARI` (Adjusted Rand Index) với nhãn tham chiếu."""))

    cd(nbf.v4.new_code_cell("""X_syn, y_syn_true = make_blobs(
    n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
)
m_syn = STING(n_levels=3, factor=4, min_count=3).fit(X_syn)
lab_syn = m_syn.cluster(level=2, connectivity=1)
for cells_at_level in m_syn.cells_.values():
    assert sum(cell.count for cell in cells_at_level.values()) == len(y_syn_true)
ari_syn = adjusted_rand_score(y_syn_true, lab_syn)
assert ari_syn >= 0.9
print(
    f"Dữ liệu giả lập 240 điểm: ARI = {ari_syn:.3f} | {m_syn.n_clusters_} cụm | "
    f"Tỷ lệ nhiễu {(lab_syn == -1).mean():.1%} (bảo toàn 240 điểm qua mọi mức lưới)."
)

res_syn = m_syn.factor ** 2
lo_s, hi_s = m_syn.bounds_min_, m_syn.bounds_max_
step_s = (hi_s - lo_s) / res_syn
with style_context():
    fig_s, axes_s = plt.subplots(1, 2, figsize=(9.6, 4.0), dpi=140, sharex=True, sharey=True, layout="constrained")
    for gid in sorted(set(y_syn_true)):
        mk = y_syn_true == gid
        axes_s[0].scatter(X_syn[mk, 0], X_syn[mk, 1], s=18, color=CLUSTER_COLORS[gid], label=f"Nhóm {gid} ({int(mk.sum())})")
    axes_s[0].set_title("Nhãn tham chiếu (240 điểm Gauss)")
    axes_s[0].set_xlabel("x1")
    axes_s[0].set_ylabel("x2")
    axes_s[0].grid(alpha=0.18)
    axes_s[0].legend(loc="upper left", fontsize=8.5)

    for i in range(1, res_syn):
        axes_s[1].axvline(lo_s[0] + i * step_s[0], color="#DCE4EC", linewidth=0.45, zorder=0.5)
        axes_s[1].axhline(lo_s[1] + i * step_s[1], color="#DCE4EC", linewidth=0.45, zorder=0.5)
    for idx_cell, cid in m_syn.label_of_.items():
        cell = m_syn.cells_[2][idx_cell]
        axes_s[1].add_patch(Rectangle(cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                                      facecolor="none", edgecolor=CLUSTER_COLORS[cid], linewidth=0.9, zorder=1.5))
    ns_s = lab_syn == -1
    axes_s[1].scatter(X_syn[ns_s, 0], X_syn[ns_s, 1], s=26, color=PALETTE["gray"], marker="x",
                      label=f"Nhiễu −1 ({int(ns_s.sum())})", zorder=3)
    for cid in sorted(set(lab_syn[lab_syn >= 0])):
        mk = lab_syn == cid
        axes_s[1].scatter(X_syn[mk, 0], X_syn[mk, 1], s=18, color=CLUSTER_COLORS[cid],
                          label=f"Cụm {cid} ({int(mk.sum())})", zorder=2.5)
    axes_s[1].set_title(f"STING mức 2 (16×16) · ARI = {ari_syn:.3f}")
    axes_s[1].set_xlabel("x1")
    axes_s[1].grid(alpha=0.18)
    axes_s[1].legend(loc="upper left", fontsize=8.5)
    plt.show()"""))

    md(nbf.v4.new_markdown_cell("""## Phần 2. Dữ liệu PAPI 2011–2024, tiền xử lý và chuẩn hóa z-score

### 2.1 Chuỗi tiền xử lý 6 bước và sàng lọc thang đo

- **Bảng PAPI 2011–2024** (`papi_panel_63_2011_2024.csv`): **882 quan sát** (`63 tỉnh × 14 năm`) và **41 cột** (`39` cột số — đạt yêu cầu tối thiểu `≥ 500 × 10`).
- **Chuỗi `PREPROCESSING_PIPELINE` (`src/preprocessing.py`)**:
  1. **Làm sạch:** khử trùng khóa `(province_code, year)` (`0` trùng), quy `109` ô `0.0 → NaN` khớp quy ước Mendeley, tách `4.284` ô thiếu cấu trúc (`d7/d8` từ 2018) khỏi `365` ô thiếu trong cửa sổ (`13` dòng thiếu `sd_4_2` hoặc `sd_6_1`), giữ `869` quan sát đủ cả hai chỉ tiêu (gồm `61/63` tỉnh năm 2024); kiểm tra miền `[0, 10]` và `scale_audit` (`23/37` cột có bước nhảy cần đối chiếu workbook); đánh dấu ngoại lai `|z| > 3` nhưng **giữ nguyên điểm thật** vì xóa làm co biên lưới.
  2. **Tích hợp & chống rò rỉ:** khớp `1–1` với `external_master_63_2011_2024.csv` (`882 × 59`); học `StandardScaler` duy nhất trên `2011–2023` khi dựng lưới dự báo/gán 2024."""))

    cd(nbf.v4.new_code_cell("""cfg = json.loads((ROOT / "models/predict_config.json").read_text(encoding="utf-8"))
feats = list(FEATURES)
assert feats == list(cfg["features"])
print("Hai chỉ tiêu PAPI dùng cho STING:")
for feature in feats:
    print(f"  • {cfg['feature_labels'][feature]} ({feature})")
print("Cấu hình STING:", cfg["sting"])

prep_state = run_preprocessing_pipeline(ROOT, features=feats)
pd.testing.assert_frame_equal(
    prep_state["panel"],
    panel.sort_values(["province_code", "year"]).reset_index(drop=True),
    check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12,
)
print(f"Đã chạy lại {len(PREPROCESSING_PIPELINE)} bước PREPROCESSING_PIPELINE từ 14 Excel gốc — khớp 100% bảng 882×41.")
display(pd.DataFrame(prep_state["log"], columns=["Bước trong PREPROCESSING_PIPELINE", "Kết quả thực thi"]))

audit = pd.read_csv(ROOT / "results/preprocessing_audit.csv")
display(audit[["stage", "test", "result", "decision"]].rename(columns={
    "stage": "Giai đoạn", "test": "Kiểm tra", "result": "Kết quả", "decision": "Quyết định",
}))

scale_meta = pd.read_csv(ROOT / "data/processed/papi_panel_scale_metadata.csv")
scale_flags = scale_audit(panel)
assert len(scale_meta) == 37 and len(scale_flags) == 23
chosen_meta = scale_meta.loc[scale_meta["cot"].isin(feats)]
assert (chosen_meta["thang_2011_2020"] == chosen_meta["thang_2021_2024"]).all()

ext_info = check_external_integration(panel, ROOT / "data/processed/external_master_63_2011_2024.csv")
assert ext_info["shape"] == (882, 59) and ext_info["cardinality"] == "one_to_one" and ext_info["same_keys"]

fs_summary, _ = feature_selection_summary(
    panel, prep_state["score_cols"], candidate_features=ALLOWLIST_FEATURES,
    flagged_names=prep_state["training_flagged_names"],
)
display(fs_summary[["Tên chỉ tiêu", "Min (≤cutoff)", "Max (≤cutoff)", "Phương sai (ddof=0)", "|r| max với biến khác", "Bị cờ scale_audit"]].round(4))
exp_df, _ = run_sting_preprocessing_experiments(panel, sting_cfg=cfg["sting"], features=feats)
display(exp_df)"""))

    cd(nbf.v4.new_code_cell(r"""sens = pd.read_csv(ROOT / "results/preprocessing_sensitivity.csv")
by_year = prep_state["missing_summary"]["by_year"]
yearly_means = panel.groupby("year")[["sd_5_4", "sd_2_1", "sd_4_2", "sd_6_1"]].mean()

with style_context():
    fig, (ax_m, ax_s, ax_cv) = plt.subplots(1, 3, figsize=(13.6, 3.95), dpi=140, layout="constrained")
    yrs = by_year["Năm"].to_numpy()
    s_miss = by_year["Thiếu cấu trúc (ngoài cửa sổ)"].to_numpy()
    w_miss = by_year["Thiếu trong cửa sổ"].to_numpy()
    ax_m.bar(yrs, s_miss, color="#CBD5E1", label=f"Ngoài cửa sổ ({int(s_miss.sum())})")
    ax_m.bar(yrs, w_miss, bottom=s_miss, color="#D55E00", label=f"Trong cửa sổ ({int(w_miss.sum())})")
    ax_m.set_title("1. Ô thiếu cấu trúc vs trong giai đoạn", fontsize=10.2)
    ax_m.set_xlabel("Năm")
    ax_m.set_ylabel("Số ô thiếu / 37 cột")
    ax_m.set_xticks(yrs[::3])
    ax_m.grid(axis="y", alpha=0.18)
    ax_m.legend(loc="upper right", fontsize=7.8, framealpha=0.92)

    ax_s.plot(yearly_means.index, yearly_means["sd_5_4"], "o-", color="#D55E00", lw=1.6, label="sd_5_4 (đổi thang 2021)")
    ax_s.plot(yearly_means.index, yearly_means["sd_2_1"], "s--", color=PALETTE["purple"], lw=1.5, label="sd_2_1 (nhảy 2018)")
    ax_s.plot(yearly_means.index, yearly_means["sd_4_2"], "o-", color=PALETTE["blue"], lw=1.9, label="sd_4_2 (chọn)")
    ax_s.plot(yearly_means.index, yearly_means["sd_6_1"], "^-", color=PALETTE["green"], lw=1.9, label="sd_6_1 (chọn)")
    ax_s.axvline(2021, color="#94A3B8", linestyle=":", lw=1.1)
    ax_s.set_title("2. Kiểm tra bước nhảy thang đo", fontsize=10.2)
    ax_s.set_xlabel("Năm")
    ax_s.set_ylabel("Trung bình 63 tỉnh")
    ax_s.set_xticks(yrs[::3])
    ax_s.grid(alpha=0.18)
    ax_s.legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    models_order = [("regression", "ridge", "Ridge\n(R²)"), ("classification", "logistic regression", "Logistic\n(F1)"), ("classification", "gaussian naive bayes", "GNB\n(F1)")]
    x_m = np.arange(len(models_order))
    w_m = 0.25
    colors_v = {"A": PALETTE["blue"], "B": PALETTE["orange"], "C": PALETTE["green"]}
    labels_v = {"A": "A: dropna (chọn)", "B": "B: SimpleImputer(median)", "C": "C: Winsorize |z|≤3"}
    for idx_v, var in enumerate(("A", "B", "C")):
        vals = [float(sens.loc[(sens.task == t) & (sens.model == m) & (sens.variant == var), "value_cv"].iat[0]) for t, m, _ in models_order]
        errs = [float(sens.loc[(sens.task == t) & (sens.model == m) & (sens.variant == var), "cv_std"].iat[0]) for t, m, _ in models_order]
        ax_cv.bar(x_m + (idx_v - 1) * w_m, vals, width=w_m, color=colors_v[var], yerr=errs if var == "A" else None,
                  capsize=3, label=labels_v[var], alpha=0.9)
    ax_cv.set_xticks(x_m, [lbl for _, _, lbl in models_order], fontsize=8.8)
    ax_cv.set_ylim(0.0, 0.72)
    ax_cv.set_ylabel("Điểm CV (± std biến thể A)")
    ax_cv.set_title("3. Độ nhạy tiền xử lý (CV 2017–2022)", fontsize=10.2)
    ax_cv.grid(axis="y", alpha=0.18)
    ax_cv.legend(loc="upper left", fontsize=7.4, framealpha=0.92)
    fig.suptitle("Tổng hợp tiền xử lý PAPI: Làm sạch, Sàng lọc thang đo và Độ nhạy", fontsize=12.0)
    plt.show()"""))

    md(nbf.v4.new_markdown_cell("""### 2.2 Chuẩn hóa z-score từ số liệu thật (ví dụ Lạng Sơn 2024)

Trên `869` quan sát đủ hai chỉ tiêu giai đoạn 2011–2024 (trong đó năm 2024 đóng góp `61/63` tỉnh), mỗi trục được chuẩn hóa bằng **z = (x − μ) / σ** (`StandardScaler`, chia `n` tức `ddof=0`). Ví dụ **Lạng Sơn năm 2024** đạt `z_4.2 = 0,9005` và `z_6.1 = 0,3737`."""))

    cd(nbf.v4.new_code_cell("""complete = panel.dropna(subset=feats).copy()
Xraw = complete[feats].to_numpy(dtype=float)
full_scaler = StandardScaler().fit(complete[feats])
Xz = full_scaler.transform(complete[feats])

total_2024 = int(panel.year.eq(2024).sum())
eligible_2024_cnt = int(complete.year.eq(2024).sum())
missing_cells = int(panel[feats].isna().sum().sum())
print(f"869 quan sát đủ hai chỉ tiêu ({len(complete)}/882); năm 2024 đóng góp {eligible_2024_cnt}/{total_2024} quan sát.")
print(f"Hai chỉ tiêu có {missing_cells} ô thiếu trên {len(panel) - len(complete)} dòng tỉnh–năm.")

example_mask = complete.province_vi.eq("Lạng Sơn") & complete.year.eq(2024)
example_raw = complete.loc[example_mask, feats].iloc[0].to_numpy()
means_full = complete[feats].mean().to_numpy()
stds_full = complete[feats].std(ddof=0).to_numpy()
z_example = (example_raw - means_full) / stds_full
np.testing.assert_allclose(z_example, full_scaler.transform(complete.loc[example_mask, feats])[0])
for feature, x_v, mu_v, sig_v, z_v in zip(feats, example_raw, means_full, stds_full, z_example, strict=True):
    print(f"Lạng Sơn 2024 · {feature}: ({x_v:.6f} − {mu_v:.6f}) / {sig_v:.6f} = {z_v:.4f}")
display(pd.DataFrame({
    "Chỉ tiêu": [FEATURE_LABELS[f] for f in feats],
    "Điểm gốc x": example_raw,
    "Trung bình μ": means_full,
    "Độ lệch chuẩn σ": stds_full,
    "z-score": z_example,
}).round(4))"""))

    md(nbf.v4.new_markdown_cell("""## Phần 3. Phân cụm STING trên PAPI, đối chiếu K-Means/DBSCAN & độ nhạy

### 3.1 STING trên toàn kỳ 869 quan sát vs lưới tham chiếu 2011–2023 (808 quan sát)

- Trên toàn mẫu **869 quan sát (2011–2024)**, lưới `16 × 16` (`min_count = 5`, kề 4 hướng) tạo **56 ô dày thành 3 vùng liên thông**: cụm lớn **677 quan sát (52 ô dày)**, hai cụm nhỏ **16 (3 ô)** và **5 (1 ô)**, còn lại **171/869 điểm nhiễu (19,7%)**. Trong `171` điểm `−1`, có tới **`162/171` điểm nằm trong khung `|z| ≤ 3`** (nhiễu là ô thưa hợp lệ chứ không phải ngoại lai `|z| > 3`!). Nếu xóa `9` điểm `|z| > 3` rồi dựng lại lưới trên `860` điểm, biên co lại khiến số cụm thành `4` và nhiễu tăng lên `173/860 (20,1%)`.
- Để kiểm tra ngoài mẫu cho năm 2024, nhánh chính của đồ án tách rạch ròi: **fit `StandardScaler` và lưới STING duy nhất trên 808 quan sát giai đoạn 2011–2023** (tạo `629 + 16 + 5` điểm vào cụm, `158` điểm nhiễu `19,6%`) và khớp 100% nhãn đã khóa trong `results/predict_all_years.csv`."""))

    cd(nbf.v4.new_code_cell("""grid_model, lab = fit_grid(Xz)
points_per_cluster = Counter(lab)
cells_per_cluster = Counter(grid_model.label_of_.values())
cell_stats = grid_model.cells_[grid_model.cluster_level_]
grid_width = GRID["factor"] ** GRID["cluster_level"]

print(f"{len(grid_model.label_of_)} ô dày tạo thành {grid_model.n_clusters_} vùng liên thông.")
for grp in sorted(cells_per_cluster):
    print(f"Cụm {grp}: {cells_per_cluster[grp]} ô dày, {points_per_cluster[grp]} quan sát.")
noise_all = points_per_cluster[-1]
print(f"Nhiễu: {noise_all}/{len(lab)} quan sát ({noise_all / len(lab):.1%}).")

z_flag = (np.abs(Xz) > 3).any(axis=1)
sparse_no_flag = int(((lab == -1) & ~z_flag).sum())
print(f"{sparse_no_flag}/{noise_all} điểm nhãn −1 có |z| ≤ 3 trên cả hai trục.")
trimmed_all, trimmed_all_lab = fit_grid(Xz[~z_flag])
trimmed_all_noise = int((trimmed_all_lab == -1).sum())
print(
    f"Nếu loại {z_flag.sum()} điểm |z| > 3 rồi dựng lại lưới trên {len(trimmed_all_lab)} điểm: "
    f"{trimmed_all.n_clusters_} cụm, {trimmed_all_noise}/{len(trimmed_all_lab)} điểm nhiễu "
    f"({trimmed_all_noise / len(trimmed_all_lab):.1%})."
)

step_grid = (grid_model.bounds_max_ - grid_model.bounds_min_) / grid_width
rel_pos = (z_example - grid_model.bounds_min_) / step_grid
example_cell = tuple(np.clip(np.floor(rel_pos).astype(int), 0, grid_width - 1).tolist())
example_label = grid_model.label_of_.get(example_cell, -1)
print(f"Lạng Sơn 2024 vào ô {example_cell} (đếm từ 0), ô có {cell_stats[example_cell].count} quan sát, nhãn cụm {example_label}.")

# Dựng lưới đóng băng 2011-2023 và kiểm tra tái lập artifact predict_all_years.csv
params = cfg["sting"]
train = panel[panel.year <= 2023].dropna(subset=feats)
scaler = StandardScaler().fit(train[feats])
train_scaled = scaler.transform(train[feats])
sting = STING(n_levels=params["n_levels"], factor=params["factor"], min_count=params["min_count"]).fit(train_scaled)
train_labels = sting.cluster(level=params["cluster_level"], connectivity=params["connectivity"])

eligible = panel.dropna(subset=feats)
rebuilt = eligible[["province_code", "year"]].assign(pred_cluster=sting.predict(scaler.transform(eligible[feats])))
saved = pd.read_csv(ROOT / "results/predict_all_years.csv")
comparison = rebuilt.merge(saved, on=["province_code", "year"], suffixes=("_rebuilt", "_saved"), validate="one_to_one")
assert len(comparison) == len(saved) == len(eligible)
np.testing.assert_array_equal(comparison.pred_cluster_rebuilt, comparison.pred_cluster_saved)
loaded_sting = STING.load(ROOT / "models/sting_predict_model.pkl")
scale_info = json.loads((ROOT / "models/sting_predict_scaler.json").read_text(encoding="utf-8"))
loaded_scaled = (eligible[feats].to_numpy() - np.array(scale_info["mean"])) / np.array(scale_info["scale"])
np.testing.assert_array_equal(loaded_sting.predict(loaded_scaled), rebuilt.pred_cluster.to_numpy())
print(f"Tái lập lưới 2011–2023: {len(comparison)}/{len(saved)} nhãn khớp tuyệt đối với results/predict_all_years.csv.")"""))

    cd(nbf.v4.new_code_cell("""fig_h = hierarchy_levels_figure(Xz)
plt.show()

q_box = [(0.0, 2.5), (0.0, 2.5)]
res_full = grid_model.query_rect(q_box, level=grid_model.cluster_level_)
res_td = grid_model.query_top_down(q_box, confidence=0.95, level=grid_model.cluster_level_)
assert res_td["count"] == res_full["count"]
np.testing.assert_allclose(res_td["mean"], res_full["mean"])
exact_q = int(((Xz >= [0.0, 0.0]) & (Xz <= [2.5, 2.5])).all(axis=1).sum())
print(f"Truy vấn từ trên xuống tổng hợp {res_td['count']} điểm trong các ô nằm trọn vùng [0; 2,5]².")
print(f"Đếm trực tiếp từng điểm trong vùng: {exact_q} điểm.")

fig_n = noise_and_trap_figure(Xz, grid_model, lab, title_prefix="PAPI 2011–2024")
plt.show()"""))

    md(nbf.v4.new_markdown_cell("""### 3.2 Đối chiếu K-Means, DBSCAN, bất biến chuẩn hóa z-score và độ nhạy tham số

1. **Chọn `k = 2` cho K-Means** qua cực đại silhouette (`k = 2: 0,4472` trên 869 điểm; `0,445` trên 808 điểm train).
2. **So sánh công bằng trên cùng tập giao không nhiễu** (cả mẫu toàn kỳ `680/869` lẫn mẫu train `631/808`): đọc silhouette kèm tỉ lệ nhiễu và số cụm.
3. **Vai trò z-score (`StandardScaler`):** Vì lưới chia đều theo biên `[min, max]` từng trục, biến đổi tuyến tính giữ nguyên **869/869 chỉ số ô** của STING, trong khi K-Means `k = 2` làm **68/869 điểm đổi nhóm** (`ARI = 0,7103`) và DBSCAN có bán kính tương đương làm **8/869 điểm đổi trạng thái nhiễu**.
4. **Độ nhạy cấu hình STING** theo ngưỡng `min_count` (3 / 5 / 8), mức lưới (0 / 1 / 2), quy tắc kề 8 hướng (`connectivity = 2`) và bộ lọc heuristic ô con–ô cha `significance_z = 2,0`. Bộ lọc này không phải kiểm định z độc lập ở mức tin cậy 95%, vì ô con nằm trong ô cha; cấu hình chính không bật bộ lọc."""))

    cd(nbf.v4.new_code_cell("""models_km = {}
sil_by_k = {}
for k_val in K_CANDIDATES:
    fit_k = KMeans(n_clusters=k_val, **KMEANS_OPTIONS).fit(Xz)
    models_km[k_val] = fit_k
    sil_by_k[k_val] = silhouette_score(Xz, fit_k.labels_)
    print(f"k={k_val}  |  Silhouette = {sil_by_k[k_val]:.4f}")

best_k = max(sil_by_k, key=sil_by_k.get)
km_all = models_km[best_k]
print(f"K-means chọn k={best_k} trong các giá trị đã thử và gán đủ {len(km_all.labels_)} điểm.")

db_all = DBSCAN(**DBSCAN_OPTIONS).fit(Xz)
assign_869 = {"STING": lab, f"K-means k={best_k}": km_all.labels_, "DBSCAN": db_all.labels_, "K-means k=3": models_km[3].labels_}
common_680 = (lab >= 0) & (db_all.labels_ >= 0)
print(f"Silhouette trên cùng {common_680.sum()}/{len(lab)} điểm (toàn kỳ 869):")
rows_cmp = []
for mname, lbls in assign_869.items():
    sil_c = silhouette_score(Xz[common_680], lbls[common_680])
    print(f"  {mname} | silhouette cùng tập = {sil_c:.4f}")
    rows_cmp.append((mname, len(set(lbls[lbls >= 0])), int((lbls == -1).sum()), clustered_silhouette(Xz, lbls), sil_c))
display(pd.DataFrame(rows_cmp, columns=["Phương pháp (869)", "Số cụm", "Điểm nhiễu", "Silhouette riêng", "Silhouette trên 680 điểm"]).round(4))

biggest_cid = max(cells_per_cluster, key=points_per_cluster.get)
for k_val in (2, 3):
    ct = pd.crosstab(lab, models_km[k_val].labels_)
    sizes = sorted(ct.loc[biggest_cid].tolist(), reverse=True)
    print(f"K-means k={k_val} chia {points_per_cluster[biggest_cid]} điểm Cụm lớn STING thành {' + '.join(map(str, sizes))}.")

fig_elb = kmeans_elbow_figure(Xz)
plt.show()
fig_cmp_mid = comparison_figure(Xz, grid_model, lab, km_all)
plt.show()"""))

    cd(nbf.v4.new_code_cell("""raw_grid, raw_labels = fit_grid(Xraw)
idx_raw = raw_grid.point_cell_index(grid_model.cluster_level_)
idx_z = grid_model.point_cell_index(grid_model.cluster_level_)
print(f"STING: {int((idx_raw == idx_z).all(axis=1).sum())}/{len(lab)} điểm cùng chỉ số ô, {int((raw_labels == lab).sum())}/{len(lab)} nhãn trùng.")

km2_raw = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(Xraw)
km2_z = models_km[2].labels_
same_ids = int((km2_raw == km2_z).sum())
km2_disp = km2_z if same_ids >= len(km2_z) - same_ids else 1 - km2_z
km_changed = km2_raw != km2_disp
print(f"K-means k=2: {int(km_changed.sum())}/{len(km2_z)} điểm đổi nhóm sau ghép tên cụm. ARI = {adjusted_rand_score(km2_raw, km2_z):.4f}.")

eps_raw = raw_dbscan_radius(full_scaler.scale_)
db_raw = DBSCAN(eps=eps_raw, min_samples=DBSCAN_OPTIONS["min_samples"]).fit_predict(Xraw)
db_changed = (db_raw == -1) != (db_all.labels_ == -1)
print(
    f"DBSCAN: ε gốc = {eps_raw:.4f}, {len(set(db_raw[db_raw >= 0]))} cụm, {(db_raw == -1).sum()} nhiễu → "
    f"sau chuẩn hóa {len(set(db_all.labels_[db_all.labels_ >= 0]))} cụm, {(db_all.labels_ == -1).sum()} nhiễu, "
    f"{int(db_changed.sum())}/{len(db_raw)} điểm đổi trạng thái nhiễu "
    f"({int(((db_raw >= 0) & (db_all.labels_ == -1)).sum())} sang nhiễu, {int(((db_raw == -1) & (db_all.labels_ >= 0)).sum())} vào cụm)."
)

fig_scale = scaling_comparison_figure(Xz, grid_model, (
    ("STING", raw_labels, lab, raw_labels != lab),
    ("K-means k = 2", km2_raw, km2_disp, km_changed),
    ("DBSCAN", db_raw, db_all.labels_, db_changed),
))
plt.show()""", metadata={"tags": ["papi-zscore-comparison"]}))

    cd(nbf.v4.new_code_cell("""for th in THRESHOLDS:
    t_m, t_l = fit_grid(Xz, min_count=th)
    t_n = int((t_l == -1).sum())
    print(f"Ngưỡng {th}  |  {t_m.n_clusters_} cụm  |  {t_n}/{len(t_l)} nhiễu ({t_n / len(t_l):.1%})")
lv_m = STING(n_levels=GRID["n_levels"], factor=GRID["factor"], min_count=GRID["min_count"]).fit(Xz)
for gl in range(lv_m.n_levels):
    gl_l = lv_m.cluster(level=gl, connectivity=GRID["connectivity"])
    w_g = lv_m.factor ** gl
    print(f"Lưới {w_g} × {w_g} | {len(lv_m.label_of_)} ô dày | {lv_m.n_clusters_} cụm | {int((gl_l == -1).sum())}/{len(gl_l)} nhiễu")
c8_l = lv_m.cluster(level=GRID["cluster_level"], connectivity=2)
print(f"Kề 8 hướng (connectivity=2) | {len(lv_m.label_of_)} ô dày | {lv_m.n_clusters_} cụm | {int((c8_l == -1).sum())}/{len(c8_l)} nhiễu")
flt_m, flt_l = fit_grid(Xz, significance_z=CELL_Z_EXAMPLE)
print(f"Thêm significance_z={CELL_Z_EXAMPLE:.1f}: {len(flt_m.label_of_)} ô đạt, {flt_m.n_clusters_} cụm, {int((flt_l == -1).sum())}/{len(lab)} điểm nhiễu.")
fig_sens = sensitivity_grid_figure(Xz)
plt.show()

# Đối chiếu trên 808 điểm huấn luyện (2011–2023)
metrics_csv = pd.read_csv(ROOT / "results/metrics.csv")
show_md(metrics_csv[metrics_csv.scope == "pooled 2011-2023"].to_markdown(index=False))"""))

    md(nbf.v4.new_markdown_cell("""## Phần 4. STING theo từng năm (2011–2024) & Dịch chuyển trên lưới cố định

Phân cụm độc lập từng năm (`61–63` điểm/năm trên lưới `3 × 3`, `min_count = 3`) và theo dõi các tỉnh qua 14 năm cũng như chuyển dịch 2023 → 2024 trên cùng lưới cố định 2011–2023 (`808` quan sát)."""))

    cd(nbf.v4.new_code_cell("""per_year = pd.read_csv(ROOT / "results/per_year.csv")
show_md(per_year.to_markdown(index=False))
single_cluster_years = int(per_year["k"].eq(1).sum())
print(f"{single_cluster_years}/{len(per_year)} năm có một cụm với lưới 3 × 3 và min_count=3.")

from scripts.common.papi_pred_common import GRID_ASSIGNMENT_LABELS, describe_grid_assignment

observed_grid = describe_grid_assignment(panel.loc[panel.year.eq(2024)], feats, scaler, sting)
status_counts = observed_grid.grid_status.value_counts().rename(index=GRID_ASSIGNMENT_LABELS)
display(status_counts.rename("Số tỉnh").rename_axis("Kết quả gán 2024").to_frame())

paired = (
    rebuilt[rebuilt.year.isin([2023, 2024])]
    .pivot(index="province_code", columns="year", values="pred_cluster")
    .dropna()
    .astype(int)
)
transition = pd.crosstab(paired[2023], paired[2024], rownames=["Năm 2023"], colnames=["Năm 2024"])
transition = transition.rename(index={2: "Cụm lớn", -1: "Nhiễu"}, columns={2: "Cụm lớn", -1: "Nhiễu"})
print(f"Đối chiếu {len(paired)} tỉnh ghép cặp 2023→2024: {transition.loc['Cụm lớn', 'Nhiễu']} tỉnh sang ô thưa, {transition.loc['Nhiễu', 'Cụm lớn']} tỉnh vào cụm.")
display(transition)

lang_son_code = panel.loc[panel.province_vi.eq("Lạng Sơn"), "province_code"].iat[0]
print("Quỹ đạo Lạng Sơn 2023→2024 trên cùng lưới cố định:", paired.loc[lang_son_code].to_dict())

for fig_name in ("map_2020.png", "map_2024.png", "evolution.png", "predict_2024.png"):
    display(Image(filename=str(ROOT / "results/figs" / fig_name)))"""))

    md(nbf.v4.new_markdown_cell("""## Phần 5. Thống kê bàn giao cho khách hàng trên 63 tỉnh năm 2024

Trả lời trực tiếp yêu cầu thực tiễn từ phía giảng viên và khách hàng sử dụng báo cáo: **sau khi chạy phân cụm ra các nhãn kỹ thuật (`-1, 0, 1, 2`) và ô lưới `(i, j)`, nhóm thống kê và bàn giao những giá trị gì cụ thể cho cơ quan quản lý địa phương?**

1. **Mô tả 63 tỉnh bằng bốn nhóm:** 48 tỉnh trong vùng dày, 8 tỉnh ngoài vùng dày về phía điểm cao, 5 tỉnh ngoài vùng dày có điểm `6.1` thấp và 2 tỉnh thiếu dữ liệu. Ngưỡng `6.1 = Q25 − 0,5 × IQR = 1,8791` tính từ 48 tỉnh trong Cụm 2 năm 2024, nên là quy tắc mô tả hồi cứu, không phải chuẩn chất lượng hay bốn cụm học được.
2. **Theo dõi việc giữ nhãn:** 5 tỉnh thuộc Cụm 2 ở cả 14 năm (`Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long`) trên cùng lưới tham chiếu. Giữ nhãn không chứng minh chất lượng dịch vụ ổn định. Có 7 tỉnh trong Cụm 2 cũng thấp hơn ngưỡng `6.1` trên.
3. **Mô tả dịch chuyển 2023 → 2024:** trong 59 tỉnh đủ dữ liệu cả hai năm, 7 tỉnh rời vùng dày và 5 tỉnh đi vào. Trong 7 tỉnh rời vùng dày, 5 thuộc phía điểm cao và 2 có `6.1` thấp theo quy tắc 2024; nhãn không xác định nguyên nhân thay đổi.
4. **Kịch bản ngoài vùng năm 2024** (`outside_scenario_share`) là chỉ số xếp hạng hồi kiểm 2023→2024, chưa phải xác suất hiệu chỉnh hoặc bằng chứng dự báo tiền cứu. Chênh lệch GRDP/người và điểm `6.1` chỉ mang tính mô tả.

Các khóa nhóm cũ được giữ trong CSV để tương thích mã nguồn; bảng hiển thị dưới đây dùng tên mô tả thống nhất với Word và slide."""))

    cd(nbf.v4.new_code_cell("""from scripts.analysis.stakeholder_summary import build_stakeholder_tables

stake = build_stakeholder_tables(ROOT)
s_df = stake["summary"]
g_df = stake["group_stats"]
bench = stake["bench"]
transitions_df = stake["transitions"]
benchmarks_14y = stake["benchmarks_14y"]
watchlist_df = stake["watchlist"]

DISPLAY_LABELS = {
    "Vùng lõi ổn định (Cụm 2)": "Trong vùng dày (Cụm 2)",
    "Biên bứt phá vượt chuẩn": "Ngoài vùng dày, phía điểm cao",
    "Ưu tiên cải thiện Y tế 6.1": "Ngoài vùng dày, điểm 6.1 thấp",
    "Giữ vững Cụm 2": "Giữ nhãn Cụm 2",
    "Rời Cụm 2 lên biên bứt phá": "Rời vùng dày, phía điểm cao",
    "Rời Cụm 2 xuống rìa Y tế 6.1": "Rời vùng dày, điểm 6.1 thấp",
}


def descriptive_table(frame):
    view = frame.copy()
    for column in ("action_group", "transition_2023_2024"):
        if column in view:
            view[column] = view[column].replace(DISPLAY_LABELS)
    return view


print(
    f"Tổng hợp 63 tỉnh năm 2024 | Trung vị Cụm 2: 4.2 = {bench['med_42']:.4f}, "
    f"6.1 = {bench['med_61']:.4f} | Ngưỡng tách dưới 6.1 = {bench['lower_61_fence']:.4f}."
)
show_md(descriptive_table(g_df[[
    "action_group", "n_provinces", "share_63_pct", "median_sd_4_2", "median_sd_6_1",
    "median_years_c2", "median_risk_outside_pct", "median_grdp_2024_mil", "median_pci_2022",
]]).to_markdown(index=False))

print("5 tỉnh giữ nhãn Cụm 2 ở 14/14 năm:", ", ".join(benchmarks_14y["province_vi"].tolist()))
display(descriptive_table(s_df.loc[
    s_df["action_group"].isin(["Biên bứt phá vượt chuẩn", "Ưu tiên cải thiện Y tế 6.1", "Thiếu dữ liệu 2024"]),
    ["province_vi", "action_group", "sd_4_2", "sd_6_1", "grid_cell", "grdp_2024_mil_vnd"],
]).round(4).reset_index(drop=True))
show_md(descriptive_table(transitions_df).to_markdown(index=False))
show_md(descriptive_table(watchlist_df).round(4).to_markdown(index=False))
display(Image(filename=str(ROOT / "results/figs/stakeholder_quadrants_2024.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phần 6. Thí nghiệm dự báo 2024 (thăm dò) & Đối chiếu nguồn ngoài PAPI

### 6.1 Dự báo hai chỉ tiêu 2024 bằng Ridge & xếp hạng kịch bản rời vùng dày

- Ridge giảm MAE nhẹ hơn giữ nguyên điểm 2023 trên 59 tỉnh (`4.2`: `0,0736` vs `0,0763`; `6.1`: `0,0641` vs `0,0683`), nhưng RMSE của `4.2` cao hơn (`0,0972` vs `0,0953`). Tất cả dự báo điểm vào vùng dày, nên chỉ nhận ra **`0/11` tỉnh ngoài vùng dày** trong mẫu đối chiếu.
- Nhóm ghép `364` cặp phần dư CV lịch sử vào dự báo điểm để đo tỉ lệ kịch bản rời vùng (`outside_scenario_share`). `AUC = 0,816` là kết quả hồi cứu thăm dò, chưa phải xác suất hiệu chỉnh hay kiểm chứng tiền cứu; không dùng năm 2024 để chọn cấu hình trong mã nguồn không chứng minh rằng năm này chưa từng được xem trong quá trình làm đồ án."""))

    cd(nbf.v4.new_code_cell("""from scripts.common.papi_forecast import (
    ORIGIN_YEAR, TARGETS, forecast_from_history, scenario_auc, score_forecast,
)

history = panel.loc[panel.year <= ORIGIN_YEAR].copy()
run_fc = forecast_from_history(history, params)
observed_2024 = panel.loc[panel.year == ORIGIN_YEAR + 1].copy()
scored_fc, errors_fc, zones_fc = score_forecast(run_fc, observed_2024)
archive_fc = pd.read_csv(ROOT / "results/papi_forecast_provinces_2024.csv")
pd.testing.assert_frame_equal(
    scored_fc.astype({"actual_cluster": "float64"}), archive_fc,
    check_dtype=False, check_exact=False, atol=1e-9, rtol=1e-9,
)
display(errors_fc.round(4))
display(zones_fc[[
    "method", "n", "out_correct", "missed_out", "exact_label_agreement", "out_recall", "balanced_zone_accuracy",
]].round(4))
print(f"Kịch bản sai số lịch sử ({run_fc.scenario_count} kịch bản/tỉnh): AUC = {scenario_auc(scored_fc):.4f}.")
display(Image(filename=str(ROOT / "results/figs/papi_forecast_values.png")))
display(Image(filename=str(ROOT / "results/figs/papi_forecast_grid.png")))"""))

    md(nbf.v4.new_markdown_cell("""### 6.2 Đối chiếu nguồn ngoài PAPI (PCI, Y tế ODM 2020, GRDP & WDI)

Đối chiếu nhãn STING đóng băng với nguồn thu thập bên ngoài PAPI để mô tả đặc trưng kinh tế–xã hội. Nguồn ngoài không cung cấp nhãn đúng cho các cụm. Quan sát lặp theo tỉnh, khác biệt năm và nhiều phép thử hạn chế ý nghĩa suy luận của p-value gộp. Số điểm cơ sở y tế ODM bằng 0 là nguồn không ghi nhận điểm, không chứng minh địa phương không có cơ sở y tế."""))

    cd(nbf.v4.new_code_cell("""ext_val = pd.read_csv(ROOT / "results/external_validation.csv")
show_md(ext_val[["section", "group", "n", "median", "mean", "note"]].fillna("").to_markdown(index=False))
for fig_name in (
    "external_pci_by_cluster.png",
    "external_health_density_2020.png",
    "external_grdp_by_cluster.png",
    "external_wdi_panel.png",
):
    display(Image(filename=str(ROOT / "results/figs" / fig_name)))"""))

    md(nbf.v4.new_markdown_cell("""## Phần 7. Kết luận tổng hợp và giới hạn diễn giải

1. **Ý nghĩa thuật toán:** Biến thể STING (`16 × 16`, `min_count = 5`, kề 4 hướng) mô tả vùng dày chiếm ưu thế và các ô thưa. Khi dựng lại lưới đều trên cùng mẫu toàn kỳ, `869/869` điểm giữ nguyên chỉ số ô sau z-score; kết quả này không áp dụng cho mọi phép biến đổi hoặc mọi thuật toán.
2. **Giá trị bàn giao:** Bảng mô tả 63 tỉnh gồm **48 trong vùng dày, 8 ngoài vùng dày về phía điểm cao, 5 ngoài vùng dày có điểm 6.1 thấp và 2 thiếu dữ liệu**. Bảng đi kèm dịch chuyển 2023→2024, chỉ số kịch bản hồi cứu và đối chiếu GRDP/PCI để gợi ý rà soát; chưa xếp hạng chất lượng hoặc xác định nguyên nhân.
3. **Giới hạn:** Trên 808 quan sát lịch sử, 629/650 điểm đã vào cụm thuộc Cụm 2; các cụm 0 (`n=5`) và 1 (`n=16`) nhỏ. Kết quả nhạy với tham số và biểu diễn, còn một giai đoạn đối chiếu `2023→2024` chưa xác lập khả năng dự báo dài hạn. Cần dữ liệu độc lập và đánh giá cuốn chiếu trước khi dùng để ra quyết định.

**Nguồn:** Wang, Yang & Muntz (VLDB 1997), PAPI (CECODES/VFF-CRT/RTA/UNDP), Mendeley DOI `10.17632/wbk42j9wc8.1`, VCCI–USAID PCI, GSO PX-Web & OD Mekong."""))

    rob = pd.read_csv(ROOT / "results/robustness.csv")
    pca_row = rob[rob["branch"].str.startswith("PCA")].iloc[0]
    goc_row = rob[rob["branch"].str.contains("(gốc OFAT)", regex=False)].iloc[0]
    md(nbf.v4.new_markdown_cell(f"""## Phụ lục A. Kiểm tra bổ sung trên nhiều chỉ tiêu (PCA & 8D OFAT)

- Hai thành phần PCA từ 6 chiều 2011–2024 giữ `{pca_row.explained_var_total:.1%}` phương sai và chỉ cho `{pca_row.k:.0f}` cụm.
- Không gian 8 chiều giai đoạn 2018–2024 tại cấu hình gốc cho `{goc_row.k:.0f}` cụm với `{goc_row.noise_ratio:.1%}` nhiễu.
- Nhãn verdict trong bảng là quy tắc lọc theo số cụm và nhiễu, chưa xác nhận chất lượng phân cụm. Ví dụ `min_count = 2` giảm nhiễu nhưng silhouette âm (`−0,089`), cho thấy độ tách yếu."""))

    cd(nbf.v4.new_code_cell("""rob_tbl = pd.read_csv(ROOT / "results/robustness.csv")
show_md(rob_tbl.to_markdown(index=False))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục B. Thí nghiệm học phần có giám sát trên 6.1, nhãn lưới và cân bằng lớp

Thí nghiệm đơn chỉ tiêu chọn mô hình hồi quy `6.1` theo CV R², bài toán phân loại đo mức khớp pseudo-label vùng dày STING (kèm `class_weight='balanced'` trên 6 fold expanding-origin 2017–2022) và đối chiếu 6 bộ phân loại chuẩn của học phần. Đây không phải nhãn chất lượng quản trị do chuyên gia cung cấp. Việc chọn tham số và báo cáo điểm trên cùng các fold có thể lạc quan; thông tin 2021–2022 từng dùng để chọn cấu hình STING còn chồng lấn các fold sau. Chưa định lượng độ lớn thiên lệch này."""))

    cd(nbf.v4.new_code_cell(r"""import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss, mean_absolute_error, r2_score, recall_score
from sklearn.pipeline import Pipeline
from scripts.common.papi_pred_common import REGRESSION_FEATURES
from scripts.supervised.predict_supervised import (
    build_classification_pairs,
    build_regression_pairs,
    expanding_year_splits,
)

sup_tbl = pd.read_csv(ROOT / "results/supervised_metrics.csv")
show_md(sup_tbl.to_markdown(index=False))

reg_pairs = build_regression_pairs(panel)
ridge_m = joblib.load(ROOT / "models/sup_ridge.joblib")
holdout_reg = reg_pairs[reg_pairs.year_t == 2023]
y_true_r = holdout_reg.y.to_numpy()
y_pred_r = ridge_m.predict(holdout_reg[REGRESSION_FEATURES].to_numpy())
print(
    f"Ridge holdout 2023→2024 ({len(holdout_reg)} cặp): MAE = {mean_absolute_error(y_true_r, y_pred_r):.4f}, "
    f"R² = {r2_score(y_true_r, y_pred_r):.4f}."
)

clf_m = joblib.load(ROOT / "models/sup_classifier.joblib")
from scripts.analysis.dashboard_data import select_classification_model
clf_name = select_classification_model(sup_tbl)
clf_pairs = build_classification_pairs(panel, feats, params)
clf_hold = clf_pairs[clf_pairs.year_t == 2023]
Xc_te, yc_te = clf_hold[REGRESSION_FEATURES].to_numpy(), clf_hold["y"].to_numpy()
print(
    f"Classifier chính ({clf_name}) holdout 2023→2024 ({len(yc_te)} cặp): "
    f"LogLoss = {log_loss(yc_te, clf_m.predict_proba(Xc_te)[:, 1]):.4f}, "
    f"Acc = {accuracy_score(yc_te, clf_m.predict(Xc_te)):.3f}, "
    f"Macro-F1 = {f1_score(yc_te, clf_m.predict(Xc_te), average='macro', labels=[0, 1], zero_division=0):.3f}."
)

clf_tr = clf_pairs[clf_pairs.year_t < 2023].reset_index(drop=True)
X_ctr, y_ctr = clf_tr[REGRESSION_FEATURES].to_numpy(), clf_tr["y"].to_numpy()
splits_cv = expanding_year_splits(clf_tr["year_t"].to_numpy(), y_ctr)
bal_rows = []
for bname, bfactory in (
    ("LR gốc", lambda: Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(C=1.0, max_iter=3000, random_state=42))])),
    ("LR balanced (C=0,3)", lambda: Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(C=0.3, class_weight="balanced", max_iter=3000, random_state=42))])),
    ("RF balanced (depth=6, leaf=2)", lambda: RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=1)),
):
    cv_mf1 = [
        f1_score(y_ctr[vi], bfactory().fit(X_ctr[ti], y_ctr[ti]).predict(X_ctr[vi]), average="macro", labels=[0, 1], zero_division=0)
        for ti, vi in splits_cv
    ]
    bfit = bfactory().fit(X_ctr, y_ctr)
    bpred = bfit.predict(Xc_te)
    bal_rows.append((bname, float(np.mean(cv_mf1)), accuracy_score(yc_te, bpred),
                     f1_score(yc_te, bpred, average="macro", labels=[0, 1], zero_division=0),
                     recall_score(yc_te, bpred, pos_label=0)))
show_md(pd.DataFrame(bal_rows, columns=["Mô hình", "Macro-F1 CV (6 fold)", "Acc holdout", "Macro-F1 holdout", "Recall lớp 0"]).round(4).to_markdown(index=False))

course_tbl = pd.read_csv(ROOT / "results/course_supervised_baselines.csv")
show_md(course_tbl.to_markdown(index=False))
display(Image(filename=str(ROOT / "results/figs/course_confusion_matrix.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục C. Đối chiếu tỷ lệ hộ nghèo cấp tỉnh GSO (2012–2024)

Đối chiếu cả dữ liệu gộp thô và dữ liệu đã trừ trung vị theo năm. Phép trừ chỉ loại vị trí trung tâm chung của từng năm; không bảo đảm khử thay đổi chuẩn nghèo, phụ thuộc theo tỉnh hay các yếu tố gây nhiễu. Các kiểm định gộp mang tính thăm dò và không cung cấp nhãn đúng cho STING."""))

    cd(nbf.v4.new_code_cell("""pov = pd.read_csv(ROOT / "results/poverty_validation.csv")
pov_pool = pov[pov.section.isin(["poverty_pooled_raw", "poverty_pooled_demeaned", "test_mw_noise_vs_c2"])].copy()
has_stats = pov_pool["mean"].notna() & pov_pool["mean"].astype(str).str.strip().ne("")
show_md(pov_pool[has_stats].to_markdown(index=False))
for _, r in pov[pov.section == "test_mw_noise_vs_c2"].iterrows():
    print(f"{r['group']}: {r['note']}")
display(Image(filename=str(ROOT / "results/figs/external_poverty_by_cluster.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục D. Thực nghiệm mở rộng tích hợp (E2–E4 & Hướng 5)

Tổng hợp các nhánh mở rộng định lượng đã được tích hợp từ `scripts/analysis/future_work.py`: (i) phân cụm quỹ đạo tuyến tính OLS 63 tỉnh 2011–2024 (`E2`); (ii) backtest cuốn chiếu 6 mốc `2018→2023` (`E3`); và (iii) tự tương quan không gian Queen năm 2024 (`E4`, Moran's I). Nhánh `E1` (chuẩn hóa hạng trong năm) được giữ làm đối chiếu tham khảo do phân mảnh thành `25` cụm với `54,1%` nhiễu."""))

    cd(nbf.v4.new_code_cell("""fw_bt = pd.read_csv(ROOT / "results/future_work_backtest.csv")
fw_sp = pd.read_csv(ROOT / "results/future_work_spatial.csv")
fw_tr = pd.read_csv(ROOT / "results/future_work_trajectory.csv")
show_md(fw_bt[["origin_year", "target_year", "target", "selected_method", "mae_forecast", "mae_carry", "mae_gain", "out_recall_forecast", "out_recall_carry"]].round(4).to_markdown(index=False))
show_md(fw_sp.round(4).to_markdown(index=False))
top_bot = pd.concat([fw_tr.nlargest(3, "slope_6_1"), fw_tr.nsmallest(3, "slope_6_1")])
show_md(top_bot[["province_vi", "n_years", "slope_4_2", "slope_6_1", "sting_label", "kmeans_label"]].round(4).to_markdown(index=False))
display(Image(filename=str(ROOT / "results/figs/future_work_overview.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục E. Phân tích hồi quy chuyên sâu (17 cấu hình, AR(1) vs Δ6.1, VIF & Conformal 90%)

Tổng hợp nghiên cứu mở rộng nhánh hồi quy `6.1` trên cùng `740` cặp train (`2011–2022`), `6` fold expanding origin (`2017–2022`) và `59` tỉnh holdout (`2023→2024`) từ `scripts/supervised/regression_deep_analysis.py`: (i) đối chiếu OLS, Ridge, Lasso, ElasticNet, Decision Tree, RF, KNN, SVR, HistGB, Panel FE (`OneHot 63 tỉnh`) và cơ chế `AR(1)` vs mô hình sai phân `Δ6.1 = y_{t+1} - y_t`; (ii) hệ số chuẩn hóa Z-score & đa cộng tuyến VIF; (iii) kiểm định cặp Wilcoxon & Bootstrap CI 95%; và (iv) khoảng dự báo Conformal 80%/90% hiệu chỉnh thuần trên CV `≤ 2022`."""))

    cd(nbf.v4.new_code_cell("""reg_deep = pd.read_csv(ROOT / "results/regression_deep_analysis.csv")
reg_conf = pd.read_csv(ROOT / "results/regression_conformal_2024.csv")
print("So sánh các cấu hình hồi quy (CV R2, CV MAE, Holdout MAE/RMSE/R2):")
show_md(reg_deep[reg_deep["section"].str.startswith("model_")].drop(columns=["section"]).to_markdown(index=False))
print("Hệ số chuẩn hóa (beta_ridge, beta_elasticnet, beta_lasso, beta_ols) & VIF:")
show_md(reg_deep[reg_deep["section"] == "coef_and_vif"][["item", "metric_primary", "metric_secondary", "holdout_mae", "holdout_rmse", "holdout_r2"]].rename(columns={
    "item": "Chỉ tiêu", "metric_primary": "β Ridge", "metric_secondary": "β ElasticNet",
    "holdout_mae": "β Lasso", "holdout_rmse": "β OLS", "holdout_r2": "VIF"
}).to_markdown(index=False))
print("Kiểm định cặp Wilcoxon + Bootstrap CI95 và hiệu chỉnh Conformal 80%/90%:")
show_md(reg_deep[reg_deep["section"].isin(["paired_test", "conformal"])].to_markdown(index=False))
print(f"Độ phủ Conformal 90% trên 59 tỉnh holdout 2024: {reg_conf['covered_conformal_90'].mean():.1%}")
display(Image(filename=str(ROOT / "results/figs/regression_diagnostics_deep.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục F. Mở rộng STING đa chiều (Thang thưa d=2..8, Chọn đặc trưng, Subspace CLIQUE & QuantileSTING)

Tổng hợp nghiên cứu giải quyết giới hạn nhiễu `60,5%` của nhánh 8 chiều đều và trạng thái `k=1` của `PCA(2) d1–d6` trong `results/robustness.csv` từ `scripts/analysis/high_dim_sting.py` và `src/high_dim.py`: (i) thang thưa lưới `d = 2..8`; (ii) rà soát vét cạn tập con `2D/3D` chỉ trên `year <= 2023`; (iii) khai phá không gian con từ dưới lên **Subspace CLIQUE Apriori** (`3D–6D`); (iv) chia lưới thích nghi **QuantileSTING** hiệu chuẩn theo mật độ kỳ vọng `n / res^d` trên cả `8D` sàng lọc (`n=808` train `<=2023`, `n=61` holdout `2024`) và `8D d1..d8` (`2018–2024`, `n=430`), kèm đối chiếu `PCA(2..4)` và kiểm định mô tả `PCI`/`GRDP` khử trung vị theo năm."""))

    cd(nbf.v4.new_code_cell("""hd_sum = pd.read_csv(ROOT / "results/high_dim_sting.csv")
hd_sub = pd.read_csv(ROOT / "results/high_dim_sting_subspaces.csv")
print("Tổng hợp mở rộng STING đa chiều (trích các nhánh chính):")
keep_sec = ["baseline_robustness", "feature_selection", "subspace_clique", "adaptive_quantile", "pca_followup"]
disp_hd = hd_sum[hd_sum["section"].isin(keep_sec)][[
    "section", "dataset", "method", "dims_d", "n_clusters", "noise_ratio", "silhouette_orig", "holdout_2024_cov", "ext_pci_dm_p"
]].copy()
disp_hd["noise_ratio"] = disp_hd["noise_ratio"].map(lambda v: f"{100*v:.1f}%")
disp_hd["silhouette_orig"] = disp_hd["silhouette_orig"].map(lambda v: "—" if pd.isna(v) else f"{v:.3f}")
disp_hd["holdout_2024_cov"] = disp_hd["holdout_2024_cov"].map(lambda v: "—" if pd.isna(v) else f"{100*v:.1f}%")
disp_hd["ext_pci_dm_p"] = disp_hd["ext_pci_dm_p"].map(lambda v: "—" if pd.isna(v) else f"{v:.4g}")
show_md(disp_hd.to_markdown(index=False))

top_clq = hd_sub[(hd_sub["kind"] == "clique_subspace") & (hd_sub["n_clusters"] >= 2)].sort_values(
    ["k_dim", "silhouette_orig"], ascending=[False, False]
).head(8).copy()
top_clq["coverage_train"] = top_clq["coverage_train"].map(lambda v: f"{100*v:.1f}%")
top_clq["silhouette_orig"] = top_clq["silhouette_orig"].map(lambda v: "—" if pd.isna(v) else f"{v:.3f}")
top_clq["holdout_2024_cov"] = top_clq["holdout_2024_cov"].map(lambda v: "—" if pd.isna(v) else f"{100*v:.1f}%")
top_clq["ext_pci_dm_p"] = top_clq["ext_pci_dm_p"].map(lambda v: "—" if pd.isna(v) else f"{v:.4g}")
print("Top 8 không gian con đa cụm nổi bật từ Subspace CLIQUE Apriori:")
show_md(top_clq[["dataset", "adaptive", "k_dim", "features", "coverage_train", "silhouette_orig", "holdout_2024_cov", "ext_pci_dm_p", "cluster_sizes"]].to_markdown(index=False))
display(Image(filename=str(ROOT / "results/figs/high_dim_sting_analysis.png")))"""))

    md(nbf.v4.new_markdown_cell("""## Phụ lục G. Suy luận Bảng (Year-FE CR1 / TWFE), Kiểm soát Đa kiểm định (Holm / BH / BY) & Chẩn đoán Không gian

Xử lý trực diện hạn chế p-value gộp khi các quan sát lặp lại theo 63 tỉnh và chịu tác động xu hướng thời gian (`scripts/analysis/panel_inference.py`):
1. **Year-FE + Sai số chuẩn Liang–Zeger CR1 (`63 tỉnh`) & Wild Cluster Bootstrap (`B = 1.999`, chiếu lại FE mỗi lượt):** tín hiệu PCI ở STING 2D (`8.14e-7`) là nhiễu trộn theo năm (`p_cr1 = 0,7007`). **8D QuantileSTING mc=7** có chênh lệch Year-FE CR1 giữa vùng cao và vùng thấp (`β = +1,561`, `p_cr1 = 0,0156`); **Holm nội họ 8D (3 phép) = 0,0468**, **Holm 6 phép chính = 0,0937 (không đạt 5%)**. `within-year z` là độ nhạy ngoài Holm.
2. **Two-Way FE Tỉnh + Năm:** `TWFE` cho `p = 0,3420` (49 tỉnh chuyển cụm) nên **chưa đủ bằng chứng** cho dao động ngắn hạn nội tỉnh; không tự chứng minh phân tầng cấu trúc.
3. **Sàng lọc thăm dò 383 p-value KW xếp chồng (`high_dim_sting_subspaces.csv`, 223 bộ đặc trưng PCI):** `161` naive `< 0,05` → **`117` BH-FDR 5%**. Không đưa vào Holm xác nhận.
4. **Moran's I phần dư Holdout 2024 (hoán vị quanh `E[I]`):** `pred_ridge` còn cấu trúc không gian; `residual_ridge` **chưa phát hiện** tự tương quan ở ngưỡng 5% trên 59 tỉnh đối chiếu."""))

    cd(nbf.v4.new_code_cell("""pi_df = pd.read_csv(ROOT / "results/panel_inference.csv")
prim_pi = pi_df[pi_df["section"] == "primary_panel"][[
    "branch", "outcome", "n_obs", "g_provinces", "naive_mwu_raw_p", "beta_yrfe", "se_cr1_yrfe", "p_cr1_yrfe", "p_wcr_yrfe", "p_cr1_twfe", "holm_p_family", "holm_p_global"
]].copy()
for c in ("naive_mwu_raw_p", "p_cr1_yrfe", "p_wcr_yrfe", "p_cr1_twfe", "holm_p_family", "holm_p_global"):
    prim_pi[c] = prim_pi[c].map(lambda v: "—" if pd.isna(v) else (f"{v:.2e}" if v < 1e-4 else f"{v:.4f}"))
prim_pi["beta_yrfe"] = prim_pi["beta_yrfe"].map(lambda v: f"{v:+.3f}")
prim_pi["se_cr1_yrfe"] = prim_pi["se_cr1_yrfe"].map(lambda v: f"{v:.3f}")
print("Bảng suy luận bảng chuẩn hóa năm (CR1 / WCR / TWFE / Holm):")
show_md(prim_pi.to_markdown(index=False))

spat_pi = pi_df[pi_df["section"] == "spatial_residual"][["outcome", "n_obs", "beta_yrfe", "p_cr1_yrfe", "verdict"]].copy()
spat_pi.columns = ["Chuỗi 2024", "n", "Moran's I", "p hoán vị (2 phía)", "Kết luận"]
spat_pi["Moran's I"] = spat_pi["Moran's I"].map(lambda v: f"{v:+.4f}")
spat_pi["p hoán vị (2 phía)"] = spat_pi["p hoán vị (2 phía)"].map(lambda v: f"{v:.4f}")
print("Chẩn đoán Moran's I phần dư Holdout 2024:")
show_md(spat_pi.to_markdown(index=False))
display(Image(filename=str(ROOT / "results/figs/panel_inference_diagnostics.png")))"""))

    nb["cells"] = cells
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return nb


def main() -> int:
    # Prepare the font cache before execution so first-run setup messages do
    # not become notebook stderr; actual cell warnings remain visible.
    import matplotlib.font_manager  # noqa: F401

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ROOT))
    from scripts.common.notebook_checks import notebook_issues

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = ROOT / "results/figs/papi_zscore_comparison.png"
    nb = build_notebook()

    with TemporaryDirectory(prefix=".unified-", dir=OUT.parent) as directory:
        staged = Path(directory) / OUT.name
        nbf.write(nb, str(staged))
        env = {
            **os.environ,
            "STING_REPO_ROOT": str(ROOT),
            "SUBMISSION_DEMO_NB_PATH": str(staged),
        }
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(staged)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            encoding="utf-8",
            timeout=600,
        )
        if proc.returncode != 0:
            print("nbconvert FAILED:\n" + proc.stdout[-4000:])
            print("STDERR:\n" + proc.stderr[-4000:])
            return 1

        executed = staged.read_text(encoding="utf-8")
        checked = json.loads(executed)
        issues = notebook_issues(checked)
        if issues:
            print("Notebook chưa đạt:", "; ".join(issues))
            return 1

        code_cells = [cell for cell in checked["cells"] if cell["cell_type"] == "code"]
        png = next(
            (
                output["data"]["image/png"]
                for cell in code_cells
                if "papi-zscore-comparison" in cell["metadata"].get("tags", [])
                for output in cell["outputs"]
                if "image/png" in output.get("data", {})
            ),
            None,
        )
        if png is None:
            print("Notebook thiếu hình đối chiếu z-score.")
            return 1

        staged.write_text(executed, encoding="utf-8", newline="\n")
        staged_img = staged.with_name(image.name)
        staged_img.write_bytes(b64decode("".join(png), validate=True))
        with _publication_lock(OUT):
            prior_image = image.read_bytes() if image.exists() else None
            staged_img.replace(image)
            try:
                staged.replace(OUT)
            except OSError:
                if prior_image is None:
                    image.unlink(missing_ok=True)
                else:
                    staged_img.write_bytes(prior_image)
                    staged_img.replace(image)
                raise

    print(f"notebook OK ({OUT.name}): {len(code_cells)} code cells, 0 error outputs, mọi ô có output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
