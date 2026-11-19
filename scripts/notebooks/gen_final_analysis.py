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
      f"{len(test) - test_noise} tỉnh được gán cụm, {test_noise} tỉnh nhận nhãn nhiễu.")"""))

md(nbf.v4.new_markdown_cell("""### 1.2 Lưới STING trên PAPI

Hình dưới cho thấy ba mức lưới của cấu hình đóng băng (`factor=4`, `min_count=5`).
Mức 0 là một ô chứa toàn bộ điểm. Mức 1 chia mỗi chiều thành 4 đoạn và ghi số điểm
trong từng ô. Mức 2 chia thành 16 đoạn; các ô có ít nhất 5 điểm là ô dày, các ô dày
kề mặt được gom thành cụm, điểm ở ô còn lại là nhiễu."""))

cd(nbf.v4.new_code_cell("""display(Image(filename=str(ROOT / "results/figs/sting_grid_levels.png")))"""))

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
đều đủ điểm và nằm trong ô có dưới 5 quan sát tham chiếu. Nhóm giữ các điểm
này trong mẫu để báo đúng độ phủ 48/61 tỉnh và theo dõi các trường hợp ngoài
vùng dày."""))

cd(nbf.v4.new_code_cell("""from scripts.common.papi_pred_common import GRID_ASSIGNMENT_LABELS, describe_grid_assignment

display(Image(filename=str(ROOT / "results/figs/predict_2024.png")))
observed_grid = describe_grid_assignment(panel.loc[panel.year.eq(2024)], features, scaler, sting)
status_counts = observed_grid.grid_status.value_counts().rename(index=GRID_ASSIGNMENT_LABELS)
display(status_counts.rename("Số tỉnh").rename_axis("Kết quả gán").to_frame())
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
sai số lớn. Độ lệch âm cho biết dự báo thấp hơn quan sát về trung bình."""))

cd(nbf.v4.new_code_cell("""observed = panel.loc[panel.year == ORIGIN_YEAR + 1].copy()
scored, errors, zones = score_forecast(run, observed)
archive_table = pd.read_csv(ROOT / "results/papi_forecast_provinces_2024.csv")
pd.testing.assert_frame_equal(scored.astype({"actual_cluster": "float64"}), archive_table,
                              check_dtype=False, check_exact=False, atol=1e-9, rtol=1e-9)
n_matched = int(scored.actual_cluster.notna().sum())
print(f"Có {len(scored)} dự báo, đối chiếu được {n_matched} tỉnh đủ hai điểm quan sát.")
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
