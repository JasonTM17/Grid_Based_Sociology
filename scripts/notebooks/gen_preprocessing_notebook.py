"""Sinh + execute notebooks/Nhom15_TienXuLy_PAPI.ipynb (notebook tiền xử lý PAPI 6 bước).

Chạy từ thư mục gốc dự án:
    python scripts/notebooks/gen_preprocessing_notebook.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "Nhom15_TienXuLy_PAPI.ipynb"


def _build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells = []
    md = cells.append
    cd = cells.append

    md(nbf.v4.new_markdown_cell("""# Tiền xử lý dữ liệu PAPI (2011–2024)

**Học máy · Nhóm 15 · Chủ đề 6 (Grid-based clustering — STING)**  
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051) · GVHD: ThS. Lê Minh Tân

**Bài toán & thuật toán trước khi tiền xử lý.** Nhóm dùng thuật toán phân cụm dựa trên lưới **STING** trên dữ liệu quản trị hành chính công cấp tỉnh PAPI (63 tỉnh × 14 năm, 2011–2024) và đối chiếu hồi quy/phân loại bổ trợ. Vì STING chia không gian liên tục thành các ô lưới theo biên `[min, max]` từng chiều và đếm mật độ ô, dữ liệu đầu vào cần: (i) không trùng khóa tỉnh–năm, (ii) phân biệt giá trị thiếu cấu trúc với thiếu ngẫu nhiên thay vì bịa giá trị khảo sát, (iii) rà soát nhất quán thang đo xuyên năm, (iv) đánh dấu ngoại lai thay vì xóa cực trị hợp lệ làm co biên lưới, và (v) tách mốc chuẩn hóa `≤ 2023` khỏi `2024` để tránh rò rỉ dữ liệu.

Toàn bộ hàm xử lý chuẩn được cài đặt thành mô-đun tái sử dụng trong `src/preprocessing.py` (`PREPROCESSING_PIPELINE`) và thực thi trực tiếp từ 14 bảng tính Excel gốc theo ba giai đoạn: **Làm sạch (khử trùng khóa đầu tiên → xử lý giá trị thiếu → kiểm tra nhất quán & thang đo → đánh dấu ngoại lai cuối cùng) → Tích hợp → Chọn đặc trưng, chuẩn hóa & thử nghiệm độ nhạy**."""))

    md(nbf.v4.new_markdown_cell("""## 1. Đọc 14 workbook PAPI gốc

Dữ liệu thô gồm hai định dạng bảng tính từ `papi.org.vn`:
- **2011–2019** (`parse_old`): mỗi hàng là một tỉnh (nhận diện bằng tên ASCII), mỗi cột là một chỉ số (6 chiều giai đoạn 2011–2017; 8 chiều từ 2018).
- **2020–2024** (`parse_new`): ma trận chuyển vị trên sheet `<năm>…VIE_ENG` (header 2 dòng: mã tỉnh và tên tỉnh), chọn block chính đầu tiên để không cộng dồn sheet trùng."""))

    cd(nbf.v4.new_code_cell("""import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display
from matplotlib.patches import Rectangle

cwd = Path.cwd().resolve()
root = next(
    (
        cand
        for cand in (cwd, *cwd.parents)
        if (cand / "src" / "preprocessing.py").is_file()
        and (cand / "data" / "raw" / "papi").is_dir()
    ),
    None,
)
if root is None:
    raise FileNotFoundError(
        "Hãy mở notebook từ thư mục dự án hoặc thư mục gói đã giải nén submissions/Nhom15_STING_PAPI."
    )

sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root))

from preprocessing import (
    ALLOWLIST_FEATURES,
    DEFAULT_CUTOFF_YEAR,
    FEATURE_LABELS,
    NEW_FILES,
    OLD_FILES,
    PREPROCESSING_PIPELINE,
    analyze_missingness,
    check_external_integration,
    count_range_violations,
    feature_selection_summary,
    load_crosswalk,
    load_raw_papi,
    run_preprocessing_pipeline,
    run_sting_preprocessing_experiments,
    scale_audit,
    score_columns,
    step_check_consistency,
    step_clean_codes_and_zeros,
    step_deduplicate,
    step_flag_outliers,
    step_integrate_panel,
    step_select_and_scale,
)
from scripts.common.fig_style import CLUSTER_COLORS, PALETTE, apply_style, style_context

apply_style()

cfg = json.loads((root / "models" / "predict_config.json").read_text(encoding="utf-8"))
features = list(cfg["features"])
raw, diagnostics = load_raw_papi(root / "data" / "raw" / "papi")
print("Đã nạp src/preprocessing.py và cấu hình tiền xử lý PAPI.")
print(f"Đã đọc {len(OLD_FILES) + len(NEW_FILES)} workbook: {len(raw)} dòng × {raw.shape[1]} cột thô.")
display(diagnostics.set_index("year").T)"""))

    md(nbf.v4.new_markdown_cell("""## 2. Giai đoạn 1 — Làm sạch (Cleaning)

Thực hiện đúng thứ tự bắt buộc qua các bước của `src/preprocessing.py`: **(a) khử trùng lặp đầu tiên → (b) giá trị thiếu & quy ước `0.0 → NaN` → (c) tính nhất quán & rà soát thang đo → (d) đánh dấu ngoại lai cuối cùng**."""))

    cd(nbf.v4.new_code_cell("""crosswalk_path = (
    root / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
)
metadata_path = root / "data" / "processed" / "papi_panel_scale_metadata.csv"
metadata = pd.read_csv(metadata_path)
crosswalk = pd.read_csv(crosswalk_path)
crosswalk_codes = crosswalk["province_code"].astype(int).unique()
s_cols = score_columns(raw)

ctx = {
    "root": root,
    "raw": raw,
    "crosswalk_maps": load_crosswalk(crosswalk_path),
    "crosswalk_codes": crosswalk_codes,
    "metadata": metadata,
    "score_cols": s_cols,
    "features": features,
    "cutoff_year": DEFAULT_CUTOFF_YEAR,
    "z_threshold": 3.0,
    "log": [],
}

ctx = step_deduplicate(ctx)
dedup = ctx["dedup_stats"]
print(f"[2a. Trùng lặp] Trùng toàn dòng: {dedup['exact_duplicates']} | "
      f"Trùng khóa (province_code, year): {dedup['key_duplicates']}/{dedup['rows']} dòng.")

ctx = step_clean_codes_and_zeros(ctx)
miss = ctx["missing_summary"]
print(f"[2b. Giá trị thiếu] {miss['total_zeros']} ô 0.0 → NaN | "
      f"Tổng {miss['total_missing']}/{miss['total_cells']} ô thiếu: "
      f"{miss['structural_missing']} ô ngoài giai đoạn khảo sát + "
      f"{miss['in_window_missing']} ô trong giai đoạn khảo sát trên {miss['in_window_rows']} dòng.")
display(miss["per_column"].loc[[*features, "Toàn bộ 37 cột chỉ tiêu"]])

ctx = step_check_consistency(ctx)
cons = ctx["consistency_stats"]
jump_flags = ctx["scale_flags"]
training_flags = ctx["training_flagged_names"]
print(f"[2c. Nhất quán & thang đo] Lệch mã tỉnh crosswalk: {cons['code_mismatch']} | "
      f"Ô ngoài khoảng metadata: {cons['range_violations']} | "
      f"Cờ biến động TB năm > 0.25: {cons['scale_flagged_count']}/37 cột.")
print("  Chỉ tiêu trong allowlist có cờ trên tập huấn luyện", [c for c in ALLOWLIST_FEATURES if c in training_flags])
display(pd.DataFrame(jump_flags, columns=["Chỉ tiêu", "Bước nhảy |Δmean| lớn nhất", "Tại năm"]).head(8))

ctx = step_flag_outliers(ctx)
out_st = ctx["outlier_stats"]
print(f"[2d. Ngoại lai (cuối cùng)] Toàn panel 37 chỉ tiêu: {out_st['panel_cells']} ô |z| > 3 "
      f"trên {out_st['panel_rows']} dòng / {out_st['panel_cols']} cột → GIỮ (chỉ đánh dấu, không xóa).")"""))

    cd(nbf.v4.new_code_cell("""by_year = miss["by_year"]
clean_df = ctx["clean"]
yearly_means = clean_df.groupby("year")[["sd_5_4", "sd_2_1", "sd_4_2", "sd_6_1"]].mean()

with style_context():
    fig, (ax_m, ax_s) = plt.subplots(1, 2, figsize=(12.4, 4.35), dpi=140, layout="constrained")

    yrs = by_year["Năm"].to_numpy()
    s_miss = by_year["Thiếu cấu trúc (ngoài cửa sổ)"].to_numpy()
    w_miss = by_year["Thiếu trong cửa sổ"].to_numpy()
    ax_m.bar(yrs, s_miss, color="#CBD5E1", label=f"Ngoài cửa sổ thu thập ({int(s_miss.sum())} ô)")
    ax_m.bar(yrs, w_miss, bottom=s_miss, color="#D55E00", label=f"Trong cửa sổ thu thập ({int(w_miss.sum())} ô)")
    ax_m.set_title("1. Phân tách ô thiếu theo năm (giữ NaN, không nội suy)", fontsize=10.5)
    ax_m.set_xlabel("Năm khảo sát")
    ax_m.set_ylabel("Số ô thiếu trên 37 chỉ tiêu")
    ax_m.set_xticks(yrs[::2])
    ax_m.grid(axis="y", alpha=0.18)
    ax_m.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    ax_s.plot(yearly_means.index, yearly_means["sd_5_4"], "o-", color="#D55E00", lw=1.8,
              label="sd_5_4 (đổi thang 2021: +0.576)")
    ax_s.plot(yearly_means.index, yearly_means["sd_2_1"], "s--", color=PALETTE["purple"], lw=1.6,
              label="sd_2_1 (nhảy 2018: +1.355)")
    ax_s.plot(yearly_means.index, yearly_means["sd_4_2"], "o-", color=PALETTE["blue"], lw=2.0,
              label="sd_4_2 (chọn — ổn định 0.25–2.5)")
    ax_s.plot(yearly_means.index, yearly_means["sd_6_1"], "^-", color=PALETTE["green"], lw=2.0,
              label="sd_6_1 (chọn — ổn định 0.25–2.5)")
    ax_s.axvline(2021, color="#94A3B8", linestyle=":", lw=1.1)
    ax_s.set_title("2. Kiểm tra bước nhảy trung bình năm (scale_audit > 0.25)", fontsize=10.5)
    ax_s.set_xlabel("Năm")
    ax_s.set_ylabel("Trung bình 63 tỉnh")
    ax_s.set_xticks(yrs[::2])
    ax_s.grid(alpha=0.18)
    ax_s.legend(loc="upper left", fontsize=8.0, framealpha=0.92)
    plt.show()"""))

    md(nbf.v4.new_markdown_cell("""## 3. Giai đoạn 2 — Tích hợp & Kiểm chứng chống rò rỉ (Integration)

Ghép bảng tên tỉnh chuẩn (`many_to_one` theo `province_code`, kiểm tra không nhân dòng), sắp xếp theo khóa `(province_code, year)` và đối chiếu từng ô với file `papi_panel_63_2011_2024.csv` đã khóa. Khi có bảng tổng hợp ngoại lai `external_master_63_2011_2024.csv`, kiểm chứng thêm phép nối `one_to_one` và các cột mask thiếu tường minh; đồng thời tách rõ giai đoạn huấn luyện `2011–2023` với năm kiểm định `2024` trước khi biến đổi."""))

    cd(nbf.v4.new_code_cell("""reference = pd.read_csv(root / "data" / "processed" / "papi_panel_63_2011_2024.csv")
ctx["column_order"] = list(reference.columns)
ctx = step_integrate_panel(ctx)
panel = ctx["panel"]

reference_sorted = reference.sort_values(["province_code", "year"]).reset_index(drop=True)
pd.testing.assert_frame_equal(panel, reference_sorted, check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)

n_rows, n_cols = panel.shape
n_num = panel.select_dtypes("number").shape[1]
assert n_rows >= 500 and n_num >= 10
print(f"Panel tích hợp khớp CSV công bố: {n_rows} dòng × {n_cols} cột ({n_num} cột số), {panel['province_code'].nunique()} tỉnh.")

ctx = step_select_and_scale(ctx)
train_df = ctx["train_df"]
holdout_df = ctx["holdout_df"]
print(f"Tách chống rò rỉ: {len(panel) - len(ctx['complete_df'])} dòng thiếu cặp {features} → "
      f"Train (2011–2023): {len(train_df)} dòng | Holdout (2024): {len(holdout_df)} dòng.")

master_path = root / "data" / "processed" / "external_master_63_2011_2024.csv"
if master_path.is_file():
    ext_info = check_external_integration(panel, master_path)
    print(f"Đối chiếu bảng ngoại lai external_master: {ext_info['shape']}, quan hệ {ext_info['cardinality']}, "
          f"khớp khóa={ext_info['same_keys']}, lệch max={ext_info['max_shared_diff']:.2e}.")
    display(ext_info["masks"])
else:
    print("Môi trường chạy PAPI độc lập (không kèm bảng ngoại lai cuối kỳ) — chỉ kiểm chứng panel 882×41.")
display(panel[["province_code", "year", "province_vi", *features]].head())"""))

    md(nbf.v4.new_markdown_cell("""## 4. Giai đoạn 3 — Chọn đặc trưng, Chuẩn hóa & Thử nghiệm tiền xử lý

### 4.1 Sàng lọc đặc trưng và chuẩn hóa z-score (`StandardScaler` fit chỉ trên 2011–2023)
Nhóm dùng danh sách 8 tiểu chỉ tiêu đã rà soát thang đo trong `ALLOWLIST_FEATURES`.
`scale_audit` đánh cờ 23/37 cột có bước nhảy trung bình năm đáng kiểm tra trên toàn kỳ. Cột cờ trong bảng chọn đặc trưng chỉ dùng dữ liệu đến 2023.
Phương sai và tương quan Pearson trên 2011–2023 dùng để mô tả các biến trong
danh sách. Cặp `(sd_4_2, sd_6_1)` lấy từ cấu hình được chọn bằng khảo sát
đến năm 2020 và đối chiếu độ phủ năm 2021–2022. `StandardScaler` fit trên mẫu
2011–2023 rồi dùng lại bộ tham số đó cho năm 2024."""))

    cd(nbf.v4.new_code_cell("""fs_summary, corr_8 = feature_selection_summary(
    panel, s_cols, candidate_features=ALLOWLIST_FEATURES, cutoff_year=DEFAULT_CUTOFF_YEAR, flagged_names=training_flags
)
variances = fs_summary["Phương sai (ddof=0)"]
assert (variances > 0.01).all(), "Phát hiện đặc trưng gần hằng số."
corr_42_61 = float(corr_8.loc["sd_4_2", "sd_6_1"])
print(f"Loại {len(s_cols) - len(ALLOWLIST_FEATURES)}/37 cột điểm → giữ {len(ALLOWLIST_FEATURES)} chỉ tiêu sạch (2011–2023):")
print(f"  min var = {variances.min():.4f} > 0.01 | max |r| cặp bất kỳ = {fs_summary['|r| max với biến khác'].max():.4f} | "
      f"Pearson r(sd_4_2, sd_6_1) = {corr_42_61:.4f}.")
display(fs_summary.round(4))

scaler = ctx["scaler"]
train_scaled = pd.DataFrame(ctx["X_train"], columns=features, index=train_df.index)
holdout_scaled = pd.DataFrame(ctx["X_holdout"], columns=features, index=holdout_df.index)
np.testing.assert_allclose(train_scaled.mean(), 0.0, atol=1e-12)
np.testing.assert_allclose(train_scaled.std(ddof=0), 1.0, atol=1e-12)

scaler_json_path = root / "models" / "sting_predict_scaler.json"
if scaler_json_path.is_file():
    saved_sc = json.loads(scaler_json_path.read_text(encoding="utf-8"))
    np.testing.assert_allclose(scaler.mean_, saved_sc["mean"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(scaler.scale_, saved_sc["scale"], rtol=0, atol=1e-12)
    print("Tham số StandardScaler khớp models/sting_predict_scaler.json với dung sai tuyệt đối 1e-12.")

extreme = train_scaled.abs().gt(3.0).any(axis=1)
assert int(extreme.sum()) == int(ctx["train_outlier_mask"].sum())
holdout_max_z = float(holdout_scaled.abs().to_numpy().max())
print(f"Ngoại lai |z| > 3 trên hai chỉ tiêu (2011–2023): {int(extreme.sum())}/{len(train_df)} dòng | "
      f"2024: {int(holdout_scaled.abs().gt(3).any(axis=1).sum())}/{len(holdout_df)} dòng (max |z| = {holdout_max_z:.4f}).")
display(
    panel.loc[train_df.index[extreme], ["province_vi", "year", *features]]
    .join(train_scaled.loc[extreme].rename(columns={"sd_4_2": "sd_4_2_z", "sd_6_1": "sd_6_1_z"}))
    .round(4)
    .reset_index(drop=True)
)"""))

    cd(nbf.v4.new_code_cell("""with style_context():
    fig, (ax_h, ax_o) = plt.subplots(1, 2, figsize=(12.6, 4.6), dpi=140, layout="constrained")

    im = ax_h.imshow(corr_8.to_numpy(), cmap="Blues", vmin=0.0, vmax=1.0)
    short_names = [c.removeprefix("sd_").replace("_", ".") for c in corr_8.columns]
    ax_h.set_xticks(range(len(short_names)), short_names, fontsize=9)
    ax_h.set_yticks(range(len(short_names)), short_names, fontsize=9)
    for i in range(len(short_names)):
        for j in range(len(short_names)):
            val = corr_8.iloc[i, j]
            ax_h.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8,
                      color="white" if val > 0.6 else "#1A1A1A")
    fig.colorbar(im, ax=ax_h, fraction=0.046, pad=0.04)
    ax_h.set_title("1. Tương quan Pearson 8 chỉ tiêu sạch (≤2023)", fontsize=10.5)

    X_z_tr = train_scaled.to_numpy()
    ex_arr = extreme.to_numpy()
    ax_o.scatter(X_z_tr[~ex_arr, 0], X_z_tr[~ex_arr, 1], s=12, color=PALETTE["blue"], alpha=0.55,
                 linewidths=0, label=f"Điểm trong |z|≤3 ({int((~ex_arr).sum())})")
    ax_o.scatter(X_z_tr[ex_arr, 0], X_z_tr[ex_arr, 1], s=42, color="#D55E00", marker="D",
                 edgecolors="white", linewidths=0.6, label=f"Ngoại lai |z|>3 ({int(ex_arr.sum())}, giữ)", zorder=4)
    ax_o.add_patch(Rectangle((-3.0, -3.0), 6.0, 6.0, fill=False, edgecolor="#D55E00",
                             linestyle="--", linewidth=1.2, label="Ngưỡng |z|=3"))
    kept = X_z_tr[~ex_arr]
    ax_o.add_patch(Rectangle(
        (kept[:, 0].min(), kept[:, 1].min()),
        kept[:, 0].max() - kept[:, 0].min(),
        kept[:, 1].max() - kept[:, 1].min(),
        fill=False, edgecolor=PALETTE["green"], linestyle=":", linewidth=1.4, label="Biên lưới nếu xóa |z|>3",
    ))
    ax_o.set_title("2. Ngoại lai |z|>3 vs biên lưới STING (2011–2023)", fontsize=10.5)
    ax_o.set_xlabel("4.2 Kiểm soát tham nhũng (z-score)")
    ax_o.set_ylabel("6.1 Y tế công lập (z-score)")
    ax_o.grid(alpha=0.16)
    ax_o.legend(loc="upper left", fontsize=8.0, framealpha=0.92)
    plt.show()"""))

    md(nbf.v4.new_markdown_cell("""### 4.2 Thử nghiệm Làm sạch & Biến đổi trên dữ liệu huấn luyện (2011–2023)

Kiểm chứng định lượng bằng **chính lưới STING (`n_levels=3, factor=4, min_count=5, level=2`)** qua `run_sting_preprocessing_experiments` để giải thích vì sao chọn `dropna` + giữ `|z| > 3` + `StandardScaler`:
1. **Thử nghiệm Cleaning (giữ vs xóa `|z| > 3`, và `dropna` vs điền `SimpleImputer(median)`)**: xóa 7 điểm `|z| > 3` làm co biên `[min, max]` của lưới 16×16 và khiến tỷ lệ nhiễu STING **tăng `19.6% → 24.6%`**; còn điền median đẩy nhân tạo 11 dòng thiếu về trung vị `sd_4_2` (làm điểm nhiễu tăng `158 → 160`).
2. **Thử nghiệm biến đổi và rời rạc hóa.** Lưới STING mức 2 chia đều mỗi
   trục thành 16 đoạn. `StandardScaler` và `MinMaxScaler` giữ nguyên **808/808**
   chỉ số ô khi dựng lại lưới theo biên mới. Với `QuantileTransformer`, mật độ
   ô thay đổi và số cụm tăng từ 3 lên 24 trong phép thử này."""))

    cd(nbf.v4.new_code_cell("""exp_df, exp_arts = run_sting_preprocessing_experiments(
    panel, sting_cfg=cfg["sting"], features=features, cutoff_year=DEFAULT_CUTOFF_YEAR
)
display(exp_df)

sens_path = root / "results" / "preprocessing_sensitivity.csv"
if sens_path.is_file():
    print("Đối chiếu độ nhạy mở rộng trên học có giám sát (results/preprocessing_sensitivity.csv):")
    display(pd.read_csv(sens_path)[["task", "model", "variant", "n_train_pairs", "value_cv", "delta_vs_A", "verdict"]])"""))

    cd(nbf.v4.new_code_cell(r"""panels = [
    ("standard", "1. Phương án chọn: dropna + giữ |z|>3 + z-score", "z (4.2)", "z (6.1)"),
    ("trimmed", "2. Loại 7 điểm |z| > 3 rồi dựng lại lưới", "z (4.2)", "z (6.1)"),
    ("imputed", "3. Điền thiếu bằng SimpleImputer(median)", "z (4.2)", "z (6.1)"),
    ("quantile", "4. Biến đổi phi tuyến QuantileTransformer", "Phân vị 4.2", "Phân vị 6.1"),
]

with style_context():
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 8.2), dpi=140, layout="constrained")
    for ax, (key, title, xlab, ylab) in zip(axes.ravel(), panels, strict=True):
        art = exp_arts[key]
        X_arr, m, lab = art["X"], art["model"], art["labels"]
        res = m.factor ** m.cluster_level_
        lo_g, hi_g = m.bounds_min_, m.bounds_max_
        step_g = (hi_g - lo_g) / res
        for idx_c, cid in m.label_of_.items():
            cell = m.cells_[m.cluster_level_][idx_c]
            ax.add_patch(Rectangle(
                cell.bounds_min, *(cell.bounds_max - cell.bounds_min),
                facecolor="none", edgecolor=CLUSTER_COLORS.get(cid, PALETTE["sky"]), linewidth=0.75, alpha=0.6,
            ))
        for i in range(1, res):
            ax.axvline(lo_g[0] + i * step_g[0], color="#E2E8F0", linewidth=0.35, zorder=0.5)
            ax.axhline(lo_g[1] + i * step_g[1], color="#E2E8F0", linewidth=0.35, zorder=0.5)
        ns = lab == -1
        ax.scatter(X_arr[ns, 0], X_arr[ns, 1], s=14, color=PALETTE["gray"], marker="x",
                   linewidths=0.8, label=f"Nhiễu ({int(ns.sum())}, {ns.mean():.1%})", zorder=2)
        ax.scatter(X_arr[~ns, 0], X_arr[~ns, 1], s=10, color=PALETTE["blue"], alpha=0.68,
                   linewidths=0, label=f"{m.n_clusters_} cụm ({int((~ns).sum())})", zorder=2)
        ax.set_title(f"{title}\n{m.n_clusters_} cụm · {int(ns.sum())}/{len(lab)} nhiễu ({ns.mean():.1%})", fontsize=10.2)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.legend(loc="upper left", fontsize=8.0, framealpha=0.92)
    fig.suptitle("Ảnh hưởng của phương án Làm sạch & Biến đổi lên lưới STING 16×16", fontsize=12.5)
    plt.show()"""))

    md(nbf.v4.new_markdown_cell("""## 5. Đóng gói Pipeline (`PREPROCESSING_PIPELINE`) & Kết luận

Chạy `run_preprocessing_pipeline(root)` để tái lập từ 14 bảng tính gốc.
Đối chiếu số điểm được gắn cờ, hai ma trận đã chuẩn hóa và giá trị trong panel."""))

    cd(nbf.v4.new_code_cell("""print("Các bước trong src/preprocessing.py::PREPROCESSING_PIPELINE:")
for idx, (step_name, fn) in enumerate(PREPROCESSING_PIPELINE, start=1):
    print(f"  {idx}. {step_name} -> {fn.__name__}()")

state = run_preprocessing_pipeline(root, features=features, cutoff_year=DEFAULT_CUTOFF_YEAR)

assert int(state["panel_outlier_mask"].sum().sum()) == int(ctx["panel_outlier_mask"].sum().sum())
assert int(state["train_outlier_mask"].sum()) == int(extreme.sum())
np.testing.assert_allclose(state["X_train"], train_scaled.to_numpy(), rtol=0, atol=1e-12)
np.testing.assert_allclose(state["X_holdout"], holdout_scaled.to_numpy(), rtol=0, atol=1e-12)
pd.testing.assert_frame_equal(state["panel"], reference_sorted, check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)

print("Pipeline tái lập kết quả từng bước và các giá trị trong CSV trong dung sai 1e-12.")
display(pd.DataFrame(state["log"], columns=["Bước trong pipeline", "Kết quả thực thi"]))"""))

    md(nbf.v4.new_markdown_cell("""## Kết luận (Danh sách các bước tiền xử lý đã chọn)

1. **Đọc & hợp nhất định dạng nguồn**: đọc 14 workbook PAPI (`2011–2019` hàng là tỉnh và `2020–2024` ma trận chuyển vị), thu `882` dòng thô.
2. **Khử trùng lặp đầu tiên**: kiểm tra trùng toàn dòng (`0`) và trùng khóa `(province_code, year)` (`0`) sau khi quy đổi mã tỉnh qua `province_crosswalk_63.csv`.
3. **Làm sạch giá trị thiếu theo ngữ cảnh**: chuyển `109` ô điểm `0.0` (quy ước tỉnh không xếp hạng) về `NaN`; phân tách `4.284` ô thiếu cấu trúc ngoài giai đoạn khảo sát và `365` ô thiếu trong giai đoạn (`13` dòng thiếu `sd_4_2`/`sd_6_1`); **không nội suy**, chỉ `dropna` khi dựng ma trận đặc trưng.
4. **Kiểm tra nhất quán và thang đo.** Có 0 sai khác mã tỉnh và 0 điểm vượt
   miền theo metadata. Cờ 23/37 cột từ `scale_audit` hỗ trợ đối chiếu workbook.
   Phân cụm dùng cặp tiểu chỉ tiêu đã chốt trong cấu hình.
5. **Đánh dấu ngoại lai cuối cùng**: gắn cờ `7/808` dòng huấn luyện có `|z| > 3` nhưng **giữ nguyên** vì đều là điểm khảo sát hợp lệ và thực nghiệm chứng minh xóa cực trị làm co biên lưới và tăng tỷ lệ nhiễu STING từ `19,6%` lên `24,6%`.
6. **Tích hợp và chuẩn hóa.** Nối tên tỉnh chuẩn theo quan hệ `many_to_one`.
   Bảng 882 × 41 khớp về giá trị với bảng đối chiếu khi dùng `rtol=atol=1e-12`
   cho giá trị số. Fit `StandardScaler` trên 808 dòng giai đoạn 2011–2023,
   sau đó transform 61 dòng năm 2024."""))

    nb["cells"] = cells
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return nb


def _execute_and_check(path: Path) -> int:
    env = {
        **os.environ,
        "STING_REPO_ROOT": str(ROOT),
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(path)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=600,
    )
    if proc.returncode != 0:
        print(f"nbconvert FAILED ({path.name}):\n" + proc.stdout[-4000:])
        print("STDERR:\n" + proc.stderr[-4000:])
        return 1

    executed = path.read_text(encoding="utf-8")
    path.write_text(executed, encoding="utf-8", newline="\n")
    check = json.loads(executed)
    code_cells = [c for c in check["cells"] if c["cell_type"] == "code"]
    n_code = len(code_cells)
    n_err = sum(
        1 for c in code_cells for o in c.get("outputs", [])
        if o.get("output_type") == "error"
    )
    n_noout = sum(1 for c in code_cells if not c.get("outputs"))
    if n_err or n_noout:
        print(f"FAIL ({path.name}): {n_err} lỗi, {n_noout} ô code thiếu output (trong {n_code} ô)")
        return 1
    print(f"notebook OK ({path.name}): {n_code} code cells, 0 error outputs, mọi ô có output")
    return 0


def main() -> int:
    # Build the real font cache before notebook execution; keep cell stderr
    # intact so errors and warnings still fail the publication gate.
    import matplotlib.font_manager  # noqa: F401

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(_build_notebook(), str(OUT))
    print("written:", OUT)
    return _execute_and_check(OUT)


if __name__ == "__main__":
    raise SystemExit(main())
