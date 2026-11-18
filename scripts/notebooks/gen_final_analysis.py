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

**Học máy · Báo cáo cuối kỳ · Nhóm 15 · Grid-based clustering**

Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)"""))

cd(nbf.v4.new_code_cell("""import sys
from pathlib import Path

ROOT = next((p for p in (Path.cwd(), *Path.cwd().parents)
             if (p / "src" / "sting.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("Mở notebook trong gói đã giải nén có src/sting.py")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

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

md(nbf.v4.new_markdown_cell("""### 1.2 Lưới STING trên PAPI

Hình dưới cho thấy ba mức lưới của cấu hình đóng băng (`factor=4`, `min_count=5`).
Mức 0 là một ô chứa toàn bộ điểm. Mức 1 chia mỗi chiều thành 4 đoạn và ghi số điểm
trong từng ô. Mức 2 chia thành 16 đoạn; các ô có ít nhất 5 điểm là ô dày, các ô dày
kề mặt được gom thành cụm, điểm ở ô còn lại là nhiễu."""))

cd(nbf.v4.new_code_cell("""from IPython.display import Image, display
display(Image(filename=str(ROOT / "results/figs/sting_grid_levels.png")))"""))

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
ARI giữa STING và DBSCAN ở `eps=0.2` bằng 0,647. Tỷ lệ nhiễu làm thay đổi
tập điểm được dùng để tính các chỉ số hình học."""))

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

md(nbf.v4.new_markdown_cell("### Phân bố các tỉnh năm 2024 trên lưới đã học"))

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

- Hai thành phần PCA giữ {_pca.explained_var_total:.1%} phương sai và cho {_pca.k:.0f} cụm.
- Với 8 chiều giai đoạn 2018–2024, cấu hình gốc cho {_goc.k:.0f} cụm và {_goc.noise_ratio:.1%} nhiễu.
- Khi chỉ đổi factor thành 3, tỷ lệ nhiễu là {_f3.noise_ratio:.1%}. Khi đổi mức lưới,
  có {_lv2.k:.0f} cụm. Khi giảm min_count còn 2, có {_mc2.k:.0f} cụm và
  {_mc2.noise_ratio:.1%} nhiễu, với silhouette {_mc2.silhouette:.3f}."""))

cd(nbf.v4.new_code_cell("""rob = pd.read_csv(ROOT / "results/robustness.csv")
show_md(rob.to_markdown(index=False))"""))

md(nbf.v4.new_markdown_cell("""## Phụ lục B. Mô hình giám sát bổ trợ

Ridge và Random Forest dự báo chỉ tiêu y tế năm sau. Chọn bằng CV theo
thời gian và đánh giá trên 2023→2024. Bài phân loại dùng nhãn do STING sinh.
Kết quả phân loại đo mức khớp với nhãn lưới trong một holdout."""))

cd(nbf.v4.new_code_cell("""sup = pd.read_csv(ROOT / "results/supervised_metrics.csv")
show_md(sup.to_markdown(index=False))"""))

cd(nbf.v4.new_code_cell("""import joblib
import sys
sys.path.insert(0, str(ROOT))
from scripts.common.papi_pred_common import REGRESSION_FEATURES
from scripts.supervised.predict_supervised import build_regression_pairs, expanding_origin_folds

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
