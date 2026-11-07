"""Sinh notebooks/final_analysis.ipynb — notebook nộp cuối kỳ (end-to-end).

Cách dùng: python scripts/gen_final_analysis.py
Sau đó:      python -m nbconvert --to notebook --execute --inplace notebooks/final_analysis.ipynb
"""
from pathlib import Path

import nbformat as nbf
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "final_analysis.ipynb"

nb = nbf.v4.new_notebook()
cells = []
md = cells.append
cd = cells.append

md(nbf.v4.new_markdown_cell("""# Báo cáo phân tích cuối kỳ — Phân cụm 63 tỉnh Việt Nam với STING trên dữ liệu PAPI

**Đồ án môn Học máy** · Topic 6: *Grid-based (clustering)* · Sociology / History · Nhóm 2 người.

Notebook end-to-end: dữ liệu → STING tự viết → baselines → robustness → bản đồ → dự đoán → kết luận.
Mọi bước có thể chạy lại từ đầu theo thứ tự; mọi số liệu khớp các file trong `results/`."""))

cd(nbf.v4.new_code_cell("""import sys
from pathlib import Path

for cand in (Path.cwd(), Path.cwd().parent):
    if (cand / "src" / "sting.py").exists():
        sys.path.insert(0, str(cand / "src"))
        break

import json
import numpy as np
import pandas as pd
from IPython.display import Markdown, display

def show_md(text):
    try:
        display(Markdown(text))
    except Exception:
        print(text)

panel = pd.read_csv("../data/processed/papi_panel_63_2011_2024.csv")
print("panel:", panel.shape, "| tỉnh:", panel.province_code.nunique(), "| năm:", panel.year.min(), "→", panel.year.max())"""))

md(nbf.v4.new_markdown_cell("""## 1. Dữ liệu & chất lượng

- 14 workbook PAPI gốc → panel sạch `882×41`; dataset thỏa yêu cầu **≥ 500 dòng × ≥ 10 cột**.
- 0.0 quy về NaN (khớp quy ước gói replication Mendeley).
- **Audit gãy thang đo:** 23/37 cột có bước nhảy trung bình năm > 0.25 (vd `sd_5_4` tại 2021).
  Pipeline xuyên năm CHỈ dùng chỉ tiêu qua audit: `sd_1_3, sd_1_4, sd_4_1–4_4, sd_6_1, sd_6_3`.
- `d7/d8` chỉ có từ 2018 → robustness 8 chiều giới hạn 2018–2024."""))

cd(nbf.v4.new_code_cell("""cfg = json.load(open("../models/predict_config.json", encoding="utf-8"))
print("Cặp chỉ tiêu đóng băng:", cfg["features"])
print("STING:", cfg["sting"])
print("Giao thức chọn (train-only):", cfg["selection_protocol"])"""))

md(nbf.v4.new_markdown_cell("""## 2. So sánh STING vs k-means vs DBSCAN (pooled 2011–2023)

Noise (−1) **được tách khỏi** silhouette/DB/CH (metric hình học tính trên điểm thuộc cụm).
k-means luôn gán hết điểm (ép k), STING không ép — đây là khác biệt phương pháp cần nói rõ."""))

cd(nbf.v4.new_code_cell("""metrics = pd.read_csv("../results/metrics.csv")
show_md(metrics[metrics.scope == "pooled 2011-2023"].to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""**Đọc bảng (trung thực):**
- Dữ liệu PAPI rất đồng nhất — STING frozen cho 1 vùng dày lớn (629) + 2 nhóm ngoại vi nhỏ (16 và 5).
- ARI STING vs k-means thấp (0.07–0.17): hai phân vùng khác nhau trên gần như một khối điểm.
- STING đồng thuận với DBSCAN(eps=0.2) hơn (ARI ≈ 0.65) — cùng họ mật độ.
- k-means cho silhouette cao hơn (0.445) nhưng **ép mọi điểm vào cụm**; STING có nhiễu 20% tách riêng."""))

md(nbf.v4.new_markdown_cell("## 3. STING theo từng năm (fit riêng từng năm)"))

cd(nbf.v4.new_code_cell("""py = pd.read_csv("../results/per_year.csv")
show_md(py.to_markdown(index=False))
print()
print("Đa số năm: k=1 (một vùng dày) — cấu trúc tách biệt chỉ xuất hiện ở 2017 (nhóm 7 tỉnh, mc=5).")"""))

_rob = pd.read_csv(ROOT / "results" / "robustness.csv")
_pca = _rob[_rob["branch"].str.startswith("PCA")].iloc[0]
_goc = _rob[_rob["branch"].str.contains("(gốc OFAT)", regex=False)].iloc[0]
_f3 = _rob[_rob["branch"].str.contains("OFAT f=3")].iloc[0]
_mc2 = _rob[_rob["branch"].str.contains("OFAT mc=2")].iloc[0]
_lv2 = _rob[_rob["branch"].str.contains("OFAT lv=2")].iloc[0]
md(nbf.v4.new_markdown_cell(f"""## 4. Robustness đa chỉ tiêu (bước bắt buộc)

- **Nhánh chính:** PCA ≥2 thành phần trên d1–d6 toàn panel (trong-năm z để khử bước nhảy).
  Kết quả: 2 PC đầu chỉ giữ {_pca.explained_var_total:.1%} phương sai; STING trên không gian PCA → k={_pca.k:.0f} → **không nhận diện cấu trúc** (trung thực).
- **Nhánh 8 chiều OFAT** (chỉ 2018–2024, 430 điểm — lưới 8-D quá thưa; đổi MỘT tham số mỗi lần từ gốc `{_goc.branch.split(", ")[-1]}`):
  gốc → k={_goc.k:.0f}, noise={_goc.noise_ratio:.1%} (silhouette {_goc.silhouette:.3f});
  chỉ f=3 → k={_f3.k:.0f}, noise={_f3.noise_ratio:.1%}; chỉ mc=2 → k={_mc2.k:.0f}, noise={_mc2.noise_ratio:.1%} (verdict "{_mc2.verdict}" — silhouette {_mc2.silhouette:.3f}, tách yếu); chỉ lv=2 → k={_lv2.k:.0f}, noise={_lv2.noise_ratio:.0%}.
  → ablation chỉ ra **factor và cluster_level là thủ phạm**; nhánh mc=2 tuy verdict "có cấu trúc" nhưng silhouette âm nên không phải cụm dùng được.
- Kết luận: không tìm thấy cụm ổn định khi mở rộng chiều; cluster hóa hiện hữu chỉ có ý nghĩa ở không gian 2D cục bộ.
  Đây là **kết quả âm tính đáng báo cáo** — dữ liệu quản trị công PAPI ở cấp tỉnh/năm khá đồng nhất."""))

cd(nbf.v4.new_code_cell("""rob = pd.read_csv("../results/robustness.csv")
show_md(rob.to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("## 5. Bản đồ 63 tỉnh & dịch chuyển cụm 2011–2024"))

cd(nbf.v4.new_code_cell("""from IPython.display import Image, display
for year in (2020, 2024):
    display(Image(filename=f"../results/figs/map_{year}.png"))"""))

cd(nbf.v4.new_code_cell("""display(Image(filename="../results/figs/evolution.png"))"""))

md(nbf.v4.new_markdown_cell("""**Chú thích evolution:** lưới TOÀN CỤC (không refit per-year) để nhãn có thể so sánh giữa các năm;
xám = nhiễu (−1); trắng = thiếu chỉ tiêu năm đó. Đọc được xu hướng: phần lớn tỉnh nằm trong cụm lớn
trong mọi năm; một số tỉnh vào/ra vùng ngoại vi theo thời gian."""))

md(nbf.v4.new_markdown_cell("""## 6. Pipeline dự đoán (năm 2024 — out-of-sample)

1. **STING.predict:** gán tỉnh vào ô lưới đã học — 48/61 tỉnh đủ chỉ tiêu → cụm lớn, 13 → nhiễu.
2. **Model giám sát:** Ridge được chọn theo CV để dự báo *6.1 Y tế công lập* năm sau; MAE holdout 2023→2024 thấp hơn carry-forward **6.3%**
   (xem `results/supervised_metrics.csv`).
3. **Phân loại ngoại vi (âm tính):** không vượt baseline đủ tin cậy — giữ lại trung thực."""))

cd(nbf.v4.new_code_cell("""sup = pd.read_csv("../results/supervised_metrics.csv")
show_md(sup.to_markdown(index=False))"""))

cd(nbf.v4.new_code_cell("""import joblib
import sys
sys.path.insert(0, str(Path("../scripts").resolve()))
from papi_pred_common import REGRESSION_FEATURES
from predict_supervised import build_regression_pairs, expanding_origin_folds

print("8 regression features:", REGRESSION_FEATURES)
regression_pairs = build_regression_pairs(panel)
training_origins = regression_pairs.loc[
    regression_pairs.year_t < 2023, "year_t"
].to_numpy()
print("Regression folds use training origins only (year_t < 2023).")
folds = expanding_origin_folds(training_origins, first_validation_origin=2017)
for fold_number, (train_idx, val_idx) in enumerate(folds, start=1):
    print(
        f"Fold {fold_number}: max train origin={training_origins[train_idx].max()}, "
        f"validation origin={training_origins[val_idx][0]}"
    )

regression_metrics = pd.read_csv("../results/supervised_metrics.csv")
regression_models = regression_metrics[
    (regression_metrics.task == "regression")
    & ~regression_metrics.model.isin(
        ["carry-forward (giữ giá trị năm nay)", "trung bình train"]
    )
].dropna(subset=["value_cv"])
chosen = regression_models.loc[regression_models.value_cv.idxmax()]
print(f"CV-selected regression model: {chosen.model} (R²={chosen.value_cv:.3f})")

print("Loading ../models/sup_ridge.joblib")
ridge = joblib.load("../models/sup_ridge.joblib")
probe = np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])
print("Fixed 8-feature probe:", probe.tolist()[0])
print("Ridge prediction:", ridge.predict(probe).tolist())"""))

cd(nbf.v4.new_code_cell("""display(Image(filename="../results/figs/predict_2024.png"))"""))

md(nbf.v4.new_markdown_cell("""## 7. Kết luận

- STING tự viết hoạt động đúng trên dữ liệu giả lập (ARI=0.950) và trên dữ liệu thật; kết quả thật
  cho thấy **dữ liệu PAPI cấp tỉnh/năm gần như một khối** — cấu trúc tách biệt rất yếu và chỉ ở ngoại vi.
- Giá trị của nghiên cứu: (a) cài đặt STING từ đầu + bộ kiểm thử; (b) quy trình chọn cấu hình **train-only**
  chống "chọn theo test"; (c) audit thang đo dữ liệu đa năm; (d) pipeline dự đoán 2 mô hình local,
  có so sánh baseline và kết quả âm tính ghi trung thực.
- Hạn chế: lưới song song trục; metric hình học không bản địa; robustness không nhận diện cấu trúc khi mở rộng chiều;
  gãy thang đo ở 23/37 cột; dữ liệu 1 năm chỉ 61 điểm → nhiễu cao.
- Hướng phát triển: chuẩn hóa theo hạng (rank) xuyên năm; mở rộng chỉ tiêu; dự báo chuỗi thời gian nhiều năm;
  phân cụm trên không gian nhiều năm liền kề (feature trajectory).

**Tài liệu tham khảo:** Wang, Yang & Muntz (VLDB'97) — STING; PAPI (CECODES/VFF-CRT/RTA/UNDP);
Le et al., Mendeley Data (DOI 10.17632/wbk42j9wc8.1, CC BY 4.0); Open Development Vietnam (CC-BY-SA 4.0)."""))

nb["cells"] = cells
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print("written:", OUT)
