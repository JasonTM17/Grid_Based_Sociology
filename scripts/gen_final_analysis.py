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

Phần chính trình bày tiền xử lý, STING, đối chứng phân cụm và kết quả PAPI.
Phần phụ lục gồm kiểm tra nhiều chiều, bài toán giám sát và đối chiếu nguồn ngoài.

Chạy tất cả các ô từ thư mục gói đã giải nén. Notebook tính lại STING trên dữ liệu
giả lập, đối chiếu nhãn đã công bố và tính MAE Ridge ở phụ lục B. Các bảng và hình
mở rộng đọc từ thư mục `results/`."""))

cd(nbf.v4.new_code_cell("""import sys
from pathlib import Path

ROOT = next((p for p in (Path.cwd(), *Path.cwd().parents)
             if (p / "src" / "sting.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("Mở notebook trong gói đã giải nén có src/sting.py")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import json
import numpy as np
import pandas as pd
from IPython.display import Markdown, display

def show_md(text):
    try:
        display(Markdown(text))
    except Exception:
        print(text)

panel = pd.read_csv(ROOT / "data/processed/papi_panel_63_2011_2024.csv")
assert panel.shape == (882, 41)
assert not panel.duplicated(["province_code", "year"]).any()
print("panel:", panel.shape, "| tỉnh:", panel.province_code.nunique(), "| năm:", panel.year.min(), "→", panel.year.max())"""))

md(nbf.v4.new_markdown_cell("""## 1. Dữ liệu & chất lượng

- 14 workbook PAPI gốc → panel sạch `882×41`; đạt yêu cầu quy mô cuối kỳ.
- 0.0 quy về NaN (khớp quy ước gói replication Mendeley).
- **Kiểm tra thang đo:** 23/37 cột có bước nhảy trung bình năm > 0.25. Đây là cờ sàng lọc, cần đối chiếu workbook.
  Pipeline xuyên năm CHỈ dùng chỉ tiêu qua audit: `sd_1_3, sd_1_4, sd_4_1–4_4, sd_6_1, sd_6_3`.
- `d7/d8` chỉ có từ 2018 → robustness 8 chiều giới hạn 2018–2024."""))

cd(nbf.v4.new_code_cell("""cfg = json.loads((ROOT / "models/predict_config.json").read_text(encoding="utf-8"))
print("Cặp chỉ tiêu đóng băng:", cfg["features"])
print("STING:", cfg["sting"])
print("Giao thức chọn (train-only):", cfg["selection_protocol"])"""))

cd(nbf.v4.new_code_cell("""audit = pd.read_csv(ROOT / "results/preprocessing_audit.csv")
show_md(audit[["stage", "test", "result", "decision"]].to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""### 1.1 Kiểm chứng cài đặt STING và tái lập model

STING gốc [Wang, Yang & Muntz, VLDB 1997](https://www.vldb.org/conf/1997/P186.PDF)
lưu cả loại phân phối và duyệt truy vấn top-down theo confidence. Bản nhóm tự viết là
**biến thể rút gọn**: count/mean/std/min/max từng ô, chọn ô có `count >= min_count`,
gom thành phần liên thông ở **một mức**; không triển khai pruning top-down.
Cây lưới hình học này khác dendrogram của Hierarchical Clustering trong Day 9.

Hai ô sau **thực sự chạy STING**: kiểm chứng với nhãn tổng hợp, rồi fit scaler/lưới chỉ
trên 2011–2023 và so mọi nhãn với artifact/model đã lưu. Không chọn lại tham số trên 2024.
Các metric silhouette/DB/CH ở phần sau là đánh giá nội tại; ARI trên PAPI chỉ đo đồng
thuận giữa hai phân hoạch, không phải accuracy so với nhãn xã hội chuẩn."""))

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
print(f"STING synthetic: ARI={ari:.3f}; k={synthetic.n_clusters_}; "
      f"nhiễu={(synthetic_labels == -1).mean():.1%}; thống kê count bảo toàn")"""))

cd(nbf.v4.new_code_cell("""features, params = cfg["features"], cfg["sting"]
train = panel[panel.year <= 2023].dropna(subset=features)
scaler = StandardScaler().fit(train[features])
sting = STING(n_levels=params["n_levels"], factor=params["factor"],
              min_count=params["min_count"]).fit(scaler.transform(train[features]))
sting.cluster(level=params["cluster_level"], connectivity=params["connectivity"])
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
print(f"Refit STING: {len(comparison)}/{len(saved)} nhãn khớp; model đã lưu khớp")
print(f"2024: {len(test)}/63 tỉnh đủ chỉ tiêu; phân bố {test.pred_cluster.value_counts().sort_index().to_dict()}")"""))

md(nbf.v4.new_markdown_cell("""## 2. So sánh STING vs k-means vs DBSCAN (pooled 2011–2023)

Noise (−1) **được tách khỏi** silhouette/DB/CH (metric hình học tính trên điểm thuộc cụm).
k-means luôn gán hết điểm (ép k), STING không ép — đây là khác biệt phương pháp cần nói rõ."""))

cd(nbf.v4.new_code_cell("""metrics = pd.read_csv(ROOT / "results/metrics.csv")
show_md(metrics[metrics.scope == "pooled 2011-2023"].to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""**Đọc bảng (trung thực):**
- Dữ liệu PAPI rất đồng nhất — STING frozen cho 1 vùng dày lớn (629) + 2 nhóm ngoại vi nhỏ (16 và 5).
- ARI STING vs k-means thấp (0.07–0.17): hai phân vùng khác nhau trên gần như một khối điểm.
- STING đồng thuận với DBSCAN(eps=0.2) hơn (ARI ≈ 0.65) — cùng họ mật độ.
- k-means cho silhouette cao hơn (0.445) nhưng **ép mọi điểm vào cụm**; STING có nhiễu 20% tách riêng."""))

md(nbf.v4.new_markdown_cell("## 3. STING theo từng năm"))

cd(nbf.v4.new_code_cell("""per_year = pd.read_csv(ROOT / "results/per_year.csv")
show_md(per_year.to_markdown(index=False))
print()
single_cluster_years = per_year["k"].eq(1).sum()
print(f"{single_cluster_years}/{len(per_year)} năm có một cụm với lưới 3 × 3 và min_count=3.")"""))

md(nbf.v4.new_markdown_cell("""## 4. Gán cụm năm 2024 và xem dịch chuyển theo thời gian

Dùng lưới học từ 2011–2023. Trên 61 tỉnh đủ hai chỉ tiêu năm 2024, có 48 tỉnh
vào cụm lớn và 13 tỉnh nhận nhãn nhiễu. Hai tỉnh thiếu chỉ tiêu được để trống."""))

cd(nbf.v4.new_code_cell("""from IPython.display import Image, display
for year in (2020, 2024):
    display(Image(filename=str(ROOT / f"results/figs/map_{year}.png")))"""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/evolution.png")))"""))

md(nbf.v4.new_markdown_cell("""**Chú thích evolution:** lưới TOÀN CỤC (không refit per-year) để nhãn có thể so sánh giữa các năm;
xám = nhiễu (−1); trắng = thiếu chỉ tiêu năm đó. Đọc được xu hướng: phần lớn tỉnh nằm trong cụm lớn
trong mọi năm; một số tỉnh vào/ra vùng ngoại vi theo thời gian."""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/predict_2024.png")))"""))

md(nbf.v4.new_markdown_cell("""## 5. Kết luận

- STING gom các ô dày liên thông. Trên PAPI 2011–2023, cụm lớn có 629 điểm,
  hai cụm nhỏ có 16 và 5 điểm, với 19,6% nhiễu.
- Các cấu hình lưới làm thay đổi số cụm và tỷ lệ nhiễu. Kết quả mô tả hai chỉ
  tiêu được chọn, trong phạm vi lưới và thời gian đã kiểm tra.
- Khi đọc silhouette, xem cùng tỉ lệ nhiễu. Các phương pháp có thể được đánh giá
  trên các tập điểm khác nhau.

**Nguồn:** Wang, Yang & Muntz (VLDB 1997), PAPI (CECODES/VFF-CRT/RTA/UNDP),
Le et al. (Mendeley DOI 10.17632/wbk42j9wc8.1) và Open Development Vietnam."""))

_rob = pd.read_csv(ROOT / "results" / "robustness.csv")
_pca = _rob[_rob["branch"].str.startswith("PCA")].iloc[0]
_goc = _rob[_rob["branch"].str.contains("(gốc OFAT)", regex=False)].iloc[0]
_f3 = _rob[_rob["branch"].str.contains("OFAT f=3")].iloc[0]
_mc2 = _rob[_rob["branch"].str.contains("OFAT mc=2")].iloc[0]
_lv2 = _rob[_rob["branch"].str.contains("OFAT lv=2")].iloc[0]
md(nbf.v4.new_markdown_cell(f"""## Phụ lục A. Kiểm tra bổ sung trên nhiều chỉ tiêu

- **Thử PCA:** ≥2 thành phần trên d1–d6 toàn panel (trong-năm z để khử bước nhảy).
  Kết quả: 2 PC đầu chỉ giữ {_pca.explained_var_total:.1%} phương sai; STING trên không gian PCA → k={_pca.k:.0f} → **không nhận diện cấu trúc** (trung thực).
- **Nhánh 8 chiều OFAT** (chỉ 2018–2024, 430 điểm — lưới 8-D quá thưa; đổi MỘT tham số mỗi lần từ gốc `{_goc.branch.split(", ")[-1]}`):
  gốc → k={_goc.k:.0f}, noise={_goc.noise_ratio:.1%} (silhouette {_goc.silhouette:.3f});
  chỉ f=3 → k={_f3.k:.0f}, noise={_f3.noise_ratio:.1%}; chỉ mc=2 → k={_mc2.k:.0f}, noise={_mc2.noise_ratio:.1%} (verdict "{_mc2.verdict}" — silhouette {_mc2.silhouette:.3f}, tách yếu); chỉ lv=2 → k={_lv2.k:.0f}, noise={_lv2.noise_ratio:.0%}.
  → ablation chỉ ra **kết quả nhạy với factor và cluster_level**; nhánh mc=2 tuy verdict "có cấu trúc" nhưng silhouette âm nên không phải cụm dùng được.
- Kết luận: không tìm thấy cụm ổn định khi mở rộng chiều; cluster hóa hiện hữu chỉ có ý nghĩa ở không gian 2D cục bộ.
  Đây là **kết quả âm tính đáng báo cáo** — dữ liệu quản trị công PAPI ở cấp tỉnh/năm khá đồng nhất."""))

cd(nbf.v4.new_code_cell("""rob = pd.read_csv(ROOT / "results/robustness.csv")
show_md(rob.to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""## Phụ lục B. Mô hình giám sát bổ trợ

Ridge và Random Forest minh họa dự báo chỉ tiêu y tế năm sau. Chọn bằng CV theo
thời gian và đánh giá trên 2023→2024. Bài phân loại dùng nhãn do STING sinh.
Kết quả phân loại đo mức khớp với nhãn lưới trong một holdout."""))

cd(nbf.v4.new_code_cell("""sup = pd.read_csv(ROOT / "results/supervised_metrics.csv")
show_md(sup.to_markdown(index=False))"""))

cd(nbf.v4.new_code_cell("""import joblib
import sys
sys.path.insert(0, str(ROOT / "scripts"))
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

regression_metrics = pd.read_csv(ROOT / "results/supervised_metrics.csv")
regression_models = regression_metrics[
    (regression_metrics.task == "regression")
    & ~regression_metrics.model.isin(
        ["carry-forward (giữ giá trị năm nay)", "trung bình train"]
    )
].dropna(subset=["value_cv"])
chosen = regression_models.loc[regression_models.value_cv.idxmax()]
print(f"CV-selected regression model: {chosen.model} (R²={chosen.value_cv:.3f})")

print("Loading ../models/sup_ridge.joblib")
ridge = joblib.load(ROOT / "models/sup_ridge.joblib")
probe = np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])
print("Fixed 8-feature probe:", probe.tolist()[0])
print("Ridge prediction:", ridge.predict(probe).tolist())
from sklearn.metrics import mean_absolute_error
holdout = regression_pairs[regression_pairs.year_t == 2023]
ridge_mae = mean_absolute_error(holdout.y, ridge.predict(holdout[REGRESSION_FEATURES].to_numpy()))
carry_mae = mean_absolute_error(holdout.y, holdout["carry"])
ridge_row = regression_metrics[(regression_metrics.task == "regression") & (regression_metrics.model == "ridge")].iloc[0]
assert abs(ridge_mae - ridge_row.holdout_mae) < 1e-5
print(f"Ridge holdout recalculated: n={len(holdout)}, MAE={ridge_mae:.4f}; carry-forward={carry_mae:.4f}")"""))

md(nbf.v4.new_markdown_cell("""## Phụ lục C. Đối chiếu PCI và nghèo GSO

- Bảng đối chiếu PCI có trong `results/external_validation.md`.
- Nguồn GSO: tỷ lệ hộ nghèo cấp tỉnh **GSO pxweb V14.47** (thống kê chính thức,
  tách khỏi PAPI); 2017–2019 lấy từ Niên giám Thống kê 2020/2021.
  KHÔNG vào feature, KHÔNG nội suy ô thiếu (TP.HCM 2016 thiếu phía nguồn).
- Mọi số dưới đây **đọc trực tiếp từ `results/poverty_validation.csv`** (sinh bởi `scripts/poverty_validation.py`) — không hardcode.
- Nên đọc hai kiểm định cùng nhau: gộp thô (nhiễm hiệu ứng năm — chuẩn nghèo đổi theo giai đoạn,
  median nghèo giảm sâu xuyên giai đoạn) và đã-trừ-median-trong-năm (tách hiệu ứng năm)."""))

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
_c0 = int(pov_pool[has_stats & pov_pool["group"].str.contains("cụm 0", regex=False)].iloc[0]["n"])
_c1 = int(pov_pool[has_stats & pov_pool["group"].str.contains("cụm 1", regex=False)].iloc[0]["n"])
print("Đọc trung thực: gộp thô KHÔNG đáng kể (nhiễm hiệu ứng năm); đã-trừ-median-năm đáng kể ở mức yếu.")
print(f"Cặp tương phản đáng tin duy nhất là nhiễu vs cụm 2 (cụm 0 n={_c0}, cụm 1 n={_c1} quá nhỏ):")
print("Các p-value Mann–Whitney ở trên không cho bằng chứng khác biệt ở mức 0.05;")
print("Đọc bảng PCI và nghèo GSO như phân tích bổ trợ theo nguồn độc lập.")

display(Image(filename=str(ROOT / "results/figs/external_poverty_by_cluster.png")))"""))

nb["cells"] = cells
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print("written:", OUT)
