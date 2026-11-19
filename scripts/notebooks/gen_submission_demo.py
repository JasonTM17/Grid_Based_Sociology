"""Sinh + execute notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb — notebook nộp bài (STING × PAPI).

Chạy bằng nbconvert và kiểm tra mọi ô code có kết quả. Notebook tính lại
z-score, ô dày, số cụm, silhouette trên cùng nhóm điểm và độ nhạy từ bảng PAPI.

Cách dùng: python scripts/notebooks/gen_submission_demo.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from base64 import b64decode

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "Nhom15_GiuaKy_STING_PAPI.ipynb"

nb = nbf.v4.new_notebook()
cells = []
md = cells.append
cd = cells.append

md(nbf.v4.new_markdown_cell("""# ỨNG DỤNG THUẬT TOÁN PHÂN CỤM DỰA TRÊN LƯỚI STING ĐỂ PHÂN TÍCH ĐẶC ĐIỂM VÀ SỰ BIẾN ĐỘNG CỦA CÁC CHỈ SỐ QUẢN TRỊ, HÀNH CHÍNH CÔNG TẠI 63 TỈNH, THÀNH PHỐ VIỆT NAM DỰA TRÊN DỮ LIỆU PAPI GIAI ĐOẠN 2011–2024

*APPLICATION OF STING GRID-BASED CLUSTERING TO ANALYZE GOVERNANCE AND PUBLIC ADMINISTRATION PERFORMANCE PATTERNS AND TEMPORAL CHANGES ACROSS 63 VIETNAMESE PROVINCES USING PAPI DATA (2011–2024)*

**Báo cáo giữa kỳ môn Học máy · Nhóm 15 · Chủ đề 6 — Grid-based clustering**

Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)

Notebook trình bày cơ chế gom cụm của biến thể STING do nhóm cài đặt, kiểm
chứng bằng dữ liệu giả lập và minh họa trên hai chỉ tiêu PAPI. Kết quả đã được
lưu để theo dõi trực tiếp.

**Chạy lại notebook.** Giải nén toàn bộ gói và mở notebook cạnh thư mục
`tai_lieu_kem`. Chọn **Restart Kernel** (khởi động lại kernel), sau đó
chọn **Run All** (chạy tất cả các ô từ đầu). Các ô phía sau sử dụng thư viện,
dữ liệu và mô hình được nạp hoặc tạo ở các ô trước."""))

cd(nbf.v4.new_code_cell("""import os
import sys
from collections import Counter
from pathlib import Path

_STING_MARKER = Path("src") / "sting.py"


def _find_project_root() -> Path:
    seeds: list[Path] = [Path.cwd().resolve()]
    for env_key in ("STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH"):
        raw = os.environ.get(env_key)
        if not raw:
            continue
        seeds.append(
            Path(raw).resolve()
            if env_key == "STING_REPO_ROOT"
            else Path(raw).resolve().parent
        )
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            for key in ("__vsc_ipynb_file__", "__file__"):
                raw = ip.user_ns.get(key)
                if raw:
                    seeds.append(Path(raw).resolve().parent)
    except ImportError:
        pass
    seen: set[Path] = set()
    for seed in seeds:
        cur = seed
        for _ in range(64):
            if cur in seen:
                break
            seen.add(cur)
            for candidate in (cur / "tai_lieu_kem", cur):
                if (candidate / _STING_MARKER).is_file():
                    return candidate
            parent = cur.parent
            if parent == cur:
                break
            cur = parent
    raise FileNotFoundError(
        "Không tìm thấy mã nguồn STING. Vui lòng giải nén toàn bộ gói "
        "và giữ thư mục tai_lieu_kem cùng cấp với notebook."
    )


ROOT = _find_project_root()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Image, display
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import adjusted_rand_score, silhouette_score

from sting import STING
from scripts.common.papi_pred_common import FEATURE_LABELS, load_panel
from scripts.common.fig_style import apply_style
from scripts.common.midterm_clustering import (
    FEATURES, GRID, THRESHOLDS, K_CANDIDATES, KMEANS_OPTIONS, DBSCAN_OPTIONS, CELL_Z_EXAMPLE,
    fit_grid, clustered_silhouette, comparison_figure, raw_dbscan_radius, scaling_comparison_figure,
)

apply_style()
print("Đã nạp mã nguồn STING và các thư viện cần thiết.")"""))

md(nbf.v4.new_markdown_cell("""## 1. Lý thuyết STING

**Grid-based clustering** tìm cụm bằng cách chia không gian dữ liệu thành các ô lưới.
**STING** (Statistical Information Grid) thuộc nhóm phương pháp này và dùng lưới nhiều mức, từ thô đến mịn.
Mỗi ô lưu số điểm và các thống kê tóm tắt.

Nhóm sử dụng **biến thể STING rút gọn** để tạo cụm tại một mức lưới.

1. Gán các điểm vào lưới và đếm số điểm trong từng ô.
2. Đánh dấu ô có số điểm đạt ngưỡng là ô dày.
3. Gom mỗi vùng gồm các ô dày liên thông qua cạnh thành một cụm. Các điểm
   trong ô thưa nhận nhãn nhiễu −1.

STING gốc còn lưu loại phân phối trong các ô và duyệt lưới từ trên xuống
dựa trên độ tin cậy."""))

md(nbf.v4.new_markdown_cell("""## 2. Cài đặt từ đầu — lưới 3 × 3

Ví dụ gồm 15 điểm trên một mặt phẳng. Mỗi ô có ít nhất 3 điểm được xem là ô dày.
Trong ví dụ này, hai vùng ô dày chỉ chạm góc nên được gán vào hai cụm riêng."""))

cd(nbf.v4.new_code_cell("""counts = np.array([[4, 3, 0], [1, 0, 4], [0, 0, 3]])
positions = [(col, 2 - row) for row in range(3) for col in range(3)]
points = np.repeat(positions, counts.ravel(), axis=0)
model = STING(n_levels=2, factor=3, min_count=3).fit(points)
labels = model.cluster(level=1, connectivity=1)

cell_counts = np.zeros_like(counts)
for (x, y), cell in model.cells_[1].items():
    cell_counts[2 - y, x] = cell.count
print("Số điểm trong từng ô:")
print(cell_counts)
assert np.array_equal(cell_counts, counts)

group_sizes = sorted(np.bincount(labels[labels >= 0]).tolist())
noise_count = int((labels == -1).sum())
assert group_sizes == [7, 7] and noise_count == 1
print(f"{model.n_clusters_} cụm, mỗi cụm {group_sizes[0]} điểm. {noise_count} điểm nhiễu.")"""))

md(nbf.v4.new_markdown_cell("""## 3. Đánh giá trên dữ liệu giả lập

Nhóm sinh 240 điểm từ hai phân bố Gauss. Nhãn khi sinh dữ liệu là căn cứ
để tính Adjusted Rand Index (ARI) và kiểm tra mức độ khớp của kết quả phân cụm."""))

cd(nbf.v4.new_code_cell("""X_syn, y_true = make_blobs(n_samples=240, centers=[(-6, -6), (6, 6)],
                           cluster_std=0.6, random_state=42)
m_syn = STING(n_levels=3, factor=4, min_count=3).fit(X_syn)
lab_syn = m_syn.cluster(level=2, connectivity=1)
ari = adjusted_rand_score(y_true, lab_syn)
assert ari >= 0.9, f"ARI quá thấp: {ari:.3f}"
print(f"ARI = {ari:.3f} | Số cụm {m_syn.n_clusters_} | Tỷ lệ nhiễu {(lab_syn == -1).mean():.1%}")
"""))

md(nbf.v4.new_markdown_cell("""## 4. Phân cụm trên dữ liệu PAPI 2011–2024

Mỗi điểm là một tỉnh trong một năm. Hai tọa độ là chỉ tiêu **4.2 Kiểm soát tham
nhũng trong cung ứng dịch vụ công** và **6.1 Y tế công lập**. Mục tiêu là mô tả
vùng điểm tập trung và các vùng nhỏ tách biệt trên mặt phẳng hai chỉ tiêu.

Các tỉnh có đủ hai chỉ tiêu năm 2024 được đưa vào phân tích cùng dữ liệu các năm trước.
Các cụm mô tả những quan sát đã có trong bảng PAPI."""))

md(nbf.v4.new_markdown_cell("### 4.1 Chuẩn bị mẫu phân tích"))

cd(nbf.v4.new_code_cell("""feats = list(FEATURES)
panel = load_panel()
keys = ["province_code", "year"]
assert panel.shape == (882, 41)
assert not panel.duplicated(keys).any()
assert not (panel[feats] == 0).any().any()
complete = panel.dropna(subset=feats).copy()
total_2024 = int(panel.year.eq(2024).sum())
eligible_2024 = int(complete.year.eq(2024).sum())

prep = pd.read_csv(ROOT / "results" / "preprocessing_audit.csv")
outlier_result = prep.loc[prep["test"].str.startswith("Đánh dấu ngoại lai"), "result"].item()
print(f"PAPI có {len(panel)} dòng, {panel.shape[1]} cột và {panel.province_code.nunique()} tỉnh.")
print(f"Mẫu phân cụm gồm {len(complete)} quan sát đủ hai chỉ tiêu, loại {len(panel) - len(complete)} dòng thiếu.")
print(f"Năm 2024 đóng góp {eligible_2024}/{total_2024} quan sát vào cùng mẫu phân cụm.")
print(f"Kiểm tra ngoại lai khi tiền xử lý: {outlier_result}. Giữ điểm PAPI để phân cụm.")"""))

md(nbf.v4.new_markdown_cell("""### 4.2 Tính z-score từ số liệu thật

Điểm 0 đã được chuyển sang giá trị thiếu theo quy ước nguồn. Với mỗi chỉ tiêu,
nhóm tính trung bình **μ** và độ lệch chuẩn **σ** trên các quan sát đủ cả hai
chỉ tiêu. Tọa độ được chuẩn hóa bằng **z = (x − μ) / σ**, với σ tính theo
quy ước chia cho số quan sát n của StandardScaler. Trên hình, z = 0 là mức
trung bình của chỉ tiêu đó và z = +1 là cao hơn trung bình một độ lệch chuẩn.
Hai trục cùng dùng đơn vị độ lệch chuẩn.

Ô dưới lấy Lạng Sơn năm 2024 làm ví dụ. Sau chuẩn hóa, tọa độ 4.2 bằng 0,9005
nghĩa là chỉ tiêu này cao hơn trung bình khoảng 0,90 độ lệch chuẩn. Tọa độ
6.1 bằng 0,3737 nghĩa là y tế công lập cao hơn trung bình khoảng 0,37 độ
lệch chuẩn. Hai tọa độ tạo thành đầu vào chung cho cả ba thuật toán."""))

cd(nbf.v4.new_code_cell("""scores = complete[feats]
Xraw = scores.to_numpy()
scaler = StandardScaler().fit(scores)
Xz = scaler.transform(scores)

example_mask = complete.province_vi.eq("Lạng Sơn") & complete.year.eq(2024)
example = scores.loc[example_mask].iloc[0].to_numpy()
means = scores.mean().to_numpy()
stds = scores.std(ddof=0).to_numpy()
z_example = (example - means) / stds
np.testing.assert_allclose(z_example, scaler.transform(scores.loc[example_mask])[0])
print("Lạng Sơn năm 2024")
for feature, x, mu, sigma, z in zip(feats, example, means, stds, z_example, strict=True):
    print(f"{feature}: ({x:.6f} − {mu:.6f}) / {sigma:.6f} = {z:.4f}")

display(pd.DataFrame({
    "Chỉ tiêu": [FEATURE_LABELS[f] for f in feats],
    "Điểm gốc x": example,
    "Trung bình μ": means,
    "Độ lệch chuẩn σ": stds,
    "z-score": z_example,
}).round(4))"""))

md(nbf.v4.new_markdown_cell("""### 4.3 STING tìm được ba cụm như thế nào?

Tại mức 2, mỗi trục có 4² = 16 khoảng, tạo lưới 16 × 16. Một ô có ít nhất
**5 quan sát** là ô dày. Các ô dày nối được với nhau qua cạnh tạo thành một
cụm. Dấu và độ lớn của z-score chỉ xác định tọa độ của điểm. Quy tắc nhiễu
dựa vào **số điểm trong ô** mà điểm rơi vào.

Ô dưới in số ô dày và số quan sát trong từng cụm. Hàm thiết lập lưới gọi
STING.fit để đếm điểm và STING.cluster để gom các ô dày kề cạnh."""))

cd(nbf.v4.new_code_cell("""grid_model, lab = fit_grid(Xz)
points_per_cluster = Counter(lab)
cells_per_cluster = Counter(grid_model.label_of_.values())
cell_stats = grid_model.cells_[grid_model.cluster_level_]
grid_width = GRID["factor"] ** GRID["cluster_level"]

print(f"Lưới {grid_width} × {grid_width} | Bốn hướng kề cạnh | Ngưỡng {grid_model.min_count_} điểm/ô")
print(f"{len(grid_model.label_of_)} ô dày tạo thành {grid_model.n_clusters_} vùng liên thông.")
for group in sorted(cells_per_cluster):
    print(f"Cụm {group}: {cells_per_cluster[group]} ô dày, {points_per_cluster[group]} quan sát.")
noise = points_per_cluster[-1]
print(f"Nhiễu: {noise}/{len(lab)} quan sát ({noise / len(lab):.1%}).")

step = (grid_model.bounds_max_ - grid_model.bounds_min_) / grid_width
bin_indices = np.floor((z_example - grid_model.bounds_min_) / step).astype(int)
example_cell = tuple(np.clip(bin_indices, 0, grid_width - 1).tolist())
assert grid_model.label_of_.get(example_cell, -1) == lab[example_mask.to_numpy()][0]
print(f"Lạng Sơn 2024 vào ô {example_cell} (đếm từ 0), ô có {cell_stats[example_cell].count} quan sát.")
print(f"Nhãn cụm của điểm này: {grid_model.label_of_.get(example_cell, -1)}.")"""))

md(nbf.v4.new_markdown_cell("""### 4.4 Vì sao K-means dùng k = 2?

K-means cần chỉ định số cụm k và gán mỗi điểm vào tâm cụm gần nhất. Nhóm
thử k từ 2 đến 5 trên **cùng 869 điểm sau chuẩn hóa**. Silhouette đo độ
gần của mỗi điểm với cụm của nó so với cụm gần nhất khác. Điểm càng gần 1,
sự phân tách càng rõ theo khoảng cách Euclid. Nhóm dùng k có điểm cao nhất
trong bốn giá trị đã thử để vẽ và đối chiếu.

Trên hình STING, các hình chữ nhật đánh dấu ô dày. Cụm của STING được
đếm từ các vùng ô dày, còn số cụm K-means được chọn qua bảng silhouette.
Code cũng lấy lại tọa độ z-score của Lạng Sơn để tính khoảng cách Euclid
đến các tâm. Qua đó có thể đối chiếu cách gán điểm này với cách STING chọn ô."""))

cd(nbf.v4.new_code_cell("""models = {}
silhouette_by_k = {}
for k in K_CANDIDATES:
    fitted = KMeans(n_clusters=k, **KMEANS_OPTIONS).fit(Xz)
    models[k] = fitted
    silhouette_by_k[k] = silhouette_score(Xz, fitted.labels_)
    print(f"k={k}  |  Silhouette = {silhouette_by_k[k]:.4f}")

best_k = max(silhouette_by_k, key=silhouette_by_k.get)
km = models[best_k]
print(f"K-means chọn k={best_k} trong các giá trị đã thử và gán đủ {len(km.labels_)} điểm.")
distances = np.linalg.norm(km.cluster_centers_ - z_example, axis=1)
assert distances.argmin() == km.labels_[example_mask.to_numpy()][0]
print("Khoảng cách từ Lạng Sơn 2024 đến các tâm, theo thứ tự gần đến xa: "
      + " và ".join(f"{distance:.4f}" for distance in sorted(distances)))"""))

cd(nbf.v4.new_code_cell("""fig = comparison_figure(Xz, grid_model, lab, km)
plt.show()"""))

md(nbf.v4.new_markdown_cell("""### 4.5 Đối chiếu trên cùng nhóm quan sát

| Cách tạo cụm | Tiêu chí | Tham số chính trong bài |
|---|---|---|
| STING | Số điểm trong từng ô. Các ô dày kề cạnh tạo thành một cụm. | Lưới 16 × 16, tối thiểu 5 điểm/ô, kề theo 4 hướng. |
| K-means | Gán mọi điểm cho tâm gần nhất, giảm tổng bình phương khoảng cách đến tâm. | Thử k = 2–5 trên cùng dữ liệu. Giữ thêm k = 3 để đối chiếu cùng số cụm với STING. |
| DBSCAN | Xét mật độ lân cận quanh từng điểm. Nối các vùng qua điểm lõi. | ε = 0,2 theo khoảng cách Euclid trên tọa độ z-score, tối thiểu 5 điểm trong lân cận tính cả điểm đang xét. |

Cả ba chạy trên 869 điểm sau chuẩn hóa. Khi so **silhouette**, lấy phần giao
các điểm được cả ba phương pháp gán cụm. Dùng cùng tọa độ z-score, cùng
khoảng cách Euclid và giữ nguyên nhãn đã gán trên mẫu 869. Bảng kèm số
điểm nhiễu trên toàn mẫu và số cụm còn trong phần giao để đọc cùng điểm số.

Silhouette mô tả độ gọn và tách biệt theo khoảng cách, trên nhóm điểm được
giữ lại. Dữ liệu PAPI ở đây chưa có nhãn cụm chuẩn. Tỷ lệ nhiễu và kích thước
cụm giúp hiểu từng phương pháp đã giữ và chia dữ liệu như thế nào."""))

cd(nbf.v4.new_code_cell("""db = DBSCAN(**DBSCAN_OPTIONS).fit(Xz)
assignments = {
    "STING": lab,
    f"K-means k={best_k}": km.labels_,
    "DBSCAN": db.labels_,
}
common = np.logical_and.reduce([labels >= 0 for labels in assignments.values()])
# Đối chứng cùng số cụm với STING trên đúng phần giao đã chọn.
assignments["K-means k=3"] = models[3].labels_
print(f"Silhouette trên cùng {common.sum()}/{len(lab)} điểm, giữ nhãn đã gán trên mẫu đầy đủ.")
rows = []
for name, labels in assignments.items():
    assigned = labels >= 0
    n_noise = int((~assigned).sum())
    sil_full = clustered_silhouette(Xz, labels)
    sil_common = silhouette_score(Xz[common], labels[common])
    print(f"{name} | silhouette cùng tập = {sil_common:.4f}")
    rows.append((name, len(set(labels[assigned])), n_noise, int(assigned.sum()), sil_full,
                 len(set(labels[common])), sil_common))

comparison = pd.DataFrame(rows, columns=[
    "Phương pháp", "Cụm toàn mẫu", "Điểm nhiễu", "Điểm vào cụm",
    "Silhouette riêng", "Cụm phần giao", "Silhouette chung",
])
display(comparison.round(4))"""))

md(nbf.v4.new_markdown_cell("""**Đối chiếu các cụm trên cùng từng điểm.** Bảng chéo dùng cả 869 quan sát.
Mỗi ô cho biết số điểm vừa thuộc một hàng STING vừa thuộc một cột K-means.
Số hiệu cụm chỉ định danh trong từng phương pháp. Đọc hàng của cụm STING
lớn nhất để thấy K-means chia vùng dày này ra sao, kể cả khi đặt k = 3."""))

cd(nbf.v4.new_code_cell("""biggest = max(cells_per_cluster, key=points_per_cluster.get)
for k in (2, 3):
    table = pd.crosstab(lab, models[k].labels_, rownames=["STING (−1 là nhiễu)"],
                        colnames=[f"K-means k={k}"], margins=True, margins_name="Tổng")
    sizes = sorted(table.loc[biggest].drop("Tổng").tolist(), reverse=True)
    print(f"Cụm STING lớn nhất: {points_per_cluster[biggest]} điểm. "
          f"K-means k={k} chia các điểm này thành {' + '.join(map(str, sizes))}.")
    display(table)"""))

md(nbf.v4.new_markdown_cell("""### 4.6 Cùng thuật toán, trước và sau z-score

**STING.** Bản cài đặt dựng lại biên lưới theo min và max của từng trục.
Vị trí tương đối trên một trục là **(x − min) / (max − min)**. Khi đổi sang
z-score, x và cả hai biên đều trừ cùng μ và chia cùng σ. Vị trí tương đối
giữ nguyên với trục có σ > 0. Với cùng độ phân giải, ngưỡng và quy tắc
kề cạnh, các ô giữ cùng điểm và ghép thành cùng các cụm. Phép thử bên dưới
đếm số chỉ số ô và nhãn khớp trên dữ liệu thật.

**K-means.** Sau chuẩn hóa, độ chênh của từng chỉ tiêu khi tính khoảng cách
Euclid được chia cho σ riêng của chỉ tiêu đó. Hai chỉ tiêu có σ khác nhau
nên trọng số khoảng cách thay đổi. Giữ k = 2 và cùng cách khởi tạo để
kiểm tra ảnh hưởng của phép đổi thang. Ghép hai tên cụm theo cách khớp
nhiều điểm nhất trước khi đếm số điểm đổi nhóm.

**DBSCAN.** So sánh với cùng 5 điểm tối thiểu. Vòng lân cận bán kính ε trên
thang z tương ứng một elip có hai bán trục εσ₄.₂ và εσ₆.₁ trên thang gốc.
Trong lượt dùng điểm gốc, chọn vòng tròn cùng diện tích với elip đó, tức
ε gốc = ε × √(σ₄.₂ × σ₆.₁). Đây là cách đặt bán kính để minh họa tác động
đổi thang. Diện tích bằng nhau và hình dạng lân cận khác nhau, nên số
điểm lân cận vẫn có thể thay đổi."""))

cd(nbf.v4.new_code_cell("""raw_grid, raw_labels = fit_grid(Xraw)
level = grid_model.cluster_level_
idx_raw = raw_grid.point_cell_index(level)
idx_z = grid_model.point_cell_index(level)
same_bins = int((idx_raw == idx_z).all(axis=1).sum())
same_labels = int((raw_labels == lab).sum())
print(f"STING: {same_bins}/{len(lab)} điểm cùng chỉ số ô, {same_labels}/{len(lab)} nhãn trùng.")

km2_raw = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(Xraw)
km2_z = models[2].labels_
# Nhãn 0/1 có thể đảo tên. So cả hai cách ghép rồi dùng cách có nhiều điểm khớp nhất.
same_ids = int((km2_raw == km2_z).sum())
km2_display = km2_z if same_ids >= len(km2_z) - same_ids else 1 - km2_z
km_changed = km2_raw != km2_display
n_changed = int(km_changed.sum())
print(f"K-means k=2: {n_changed}/{len(km2_z)} điểm đổi nhóm sau ghép tên cụm.")
print(f"ARI giữa hai lần chạy K-means: {adjusted_rand_score(km2_raw, km2_z):.4f}.")
# Đánh giá cả hai bộ nhãn trên cùng tọa độ để giữ cùng thước đo khoảng cách.
print(f"Silhouette cùng thang z: {silhouette_score(Xz, km2_raw):.4f} "
      f"(chạy điểm gốc) và {silhouette_score(Xz, km2_z):.4f} (chạy điểm chuẩn hóa).")

eps_raw = raw_dbscan_radius(scaler.scale_)
db_raw = DBSCAN(eps=eps_raw, min_samples=DBSCAN_OPTIONS["min_samples"]).fit_predict(Xraw)
db_changed = (db_raw == -1) != (db.labels_ == -1)
count_db_raw = len(set(db_raw[db_raw >= 0]))
count_db_z = len(set(db.labels_[db.labels_ >= 0]))
print(f"DBSCAN: ε gốc = {eps_raw:.4f}, {count_db_raw} cụm, {(db_raw == -1).sum()} điểm nhiễu.")
print(f"DBSCAN sau chuẩn hóa: {count_db_z} cụm, {(db.labels_ == -1).sum()} điểm nhiễu, "
      f"{db_changed.sum()}/{len(db_raw)} điểm đổi trạng thái nhiễu.")"""))

md(nbf.v4.new_markdown_cell("""**Cách đọc hình.** Hàng trên lấy nhãn từ lượt chạy trên điểm gốc. Hàng dưới
lấy nhãn từ lượt chạy sau z-score. Cả sáu ô dùng cùng tọa độ hiển thị để
dễ dò cùng một quan sát. Vòng đen ở hàng dưới đánh dấu điểm đổi cụm của
K-means sau ghép tên cụm và điểm DBSCAN đổi trạng thái nhiễu. Màu cụm
DBSCAN chỉ phân biệt các cụm trong từng ô hình."""))

cd(nbf.v4.new_code_cell("""fig = scaling_comparison_figure(Xz, grid_model, (
    ("STING", raw_labels, lab, raw_labels != lab),
    ("K-means k = 2", km2_raw, km2_display, km_changed),
    ("DBSCAN", db_raw, db.labels_, db_changed),
))
plt.show()""", metadata={"tags": ["papi-zscore-comparison"]}))

md(nbf.v4.new_markdown_cell("""### 4.7 Kiểm tra hai cách thay tiêu chí ô dày

**Đổi số điểm tối thiểu.** Giữ dữ liệu, trạng thái chuẩn hóa, mức lưới, biên và
quy tắc kề cạnh. Thử 3, 5 và 8 để quan sát số cụm và tỷ lệ điểm nhiễu thay đổi."""))

cd(nbf.v4.new_code_cell("""for threshold in THRESHOLDS:
    trial, trial_labels = fit_grid(Xz, min_count=threshold)
    noise_count = int((trial_labels == -1).sum())
    print(f"Ngưỡng {threshold}  |  {trial.n_clusters_} cụm  |  "
          f"{noise_count}/{len(trial_labels)} nhiễu ({noise_count / len(trial_labels):.1%})")"""))

md(nbf.v4.new_markdown_cell("""**Thử thêm ngưỡng so ô con với ô cha.** Tham số tùy chọn
**significance_z** của bản cài đặt áp dụng sau khi ô đạt tối thiểu 5 điểm.
Ô đạt thêm điều kiện nếu có ít nhất một chỉ tiêu thỏa

**|trung bình ô con − trung bình ô cha| > t × độ lệch chuẩn ô cha / √(số điểm ô con).**

Phép thử dùng **t = 2,0** làm giá trị minh họa. Đây là quy tắc lọc mô tả.
Ô cha chứa cả điểm của ô con, nên ngưỡng minh họa chỉ dùng để khảo sát
thay đổi của lưới. Kết quả chính ở trên dùng quy tắc đếm điểm, với
significance_z ở giá trị mặc định None. Z-score ở mục 4.2 vẫn là phép đổi
tọa độ của từng quan sát."""))

cd(nbf.v4.new_code_cell("""filtered, filtered_labels = fit_grid(Xz, significance_z=CELL_Z_EXAMPLE)
print(f"Thêm significance_z={CELL_Z_EXAMPLE:.1f}: {len(filtered.label_of_)} ô đạt, "
      f"{filtered.n_clusters_} cụm, {int((filtered_labels == -1).sum())}/{len(lab)} điểm nhiễu.")

child = cell_stats[example_cell]
parent_key = tuple(i // GRID["factor"] for i in example_cell)
parent = grid_model.cells_[level - 1][parent_key]
gap = np.abs(child.mean - parent.mean)
cutoff = CELL_Z_EXAMPLE * parent.std / np.sqrt(child.count)
satisfied = gap > cutoff
assert bool(satisfied.any()) == (example_cell in filtered.label_of_)
print(f"Ô chứa Lạng Sơn 2024: ô con {example_cell}, ô cha {parent_key}.")
display(pd.DataFrame({"Chỉ tiêu": feats, "Chênh lệch tuyệt đối": gap,
                      "Mức so sánh": cutoff, "Đạt": satisfied}).round(4))"""))

md(nbf.v4.new_markdown_cell("""### 4.8 Minh họa bổ sung — dự báo điểm rồi đối chiếu trên lưới

Thử nghiệm này có mốc thời gian riêng. Sáu lượt kiểm định dùng các điểm
đích 2018–2023 để chọn mô hình cho từng chỉ tiêu. Từ tám điểm đầu vào
năm 2023, mô hình tạo hai điểm dự báo năm 2024 cho từng tỉnh đủ dữ liệu.
Sau bước đó mới ghép điểm PAPI quan sát năm 2024 để đo sai số. Lưới
STING dựng từ dữ liệu đến 2023 giúp đối chiếu vùng của hai loại điểm.
Đây là đánh giá hồi cứu tại một năm đã có số liệu."""))

cd(nbf.v4.new_code_cell("""from scripts.common.papi_forecast import MODEL_NAMES, forecast_from_history, score_forecast

origin = 2023
history = panel.loc[panel.year <= origin].copy()
forecast_run = forecast_from_history(history, GRID, origin)
print(f"{forecast_run.train_pairs} cặp lịch sử, {len(forecast_run.predictions)} tỉnh có dự báo 2024.")
for target, method in forecast_run.selection.items():
    print(f"{target}: {MODEL_NAMES[method]} theo MAE trung bình các lượt kiểm định.")"""))

cd(nbf.v4.new_code_cell("""observations = panel.loc[panel.year == origin + 1].copy()
scored, error_table, zones = score_forecast(forecast_run, observations)
display(error_table[["target", "method", "n", "mae", "rmse"]].rename(columns={
    "target": "Chỉ tiêu", "method": "Cách dự báo", "n": "Số tỉnh", "mae": "MAE", "rmse": "RMSE",
}).replace({"forecast": "Mô hình chọn", "carry": "Giữ điểm năm 2023"}).round(4))
zone = zones.set_index("method").loc["forecast"]
print(f"Dự báo điểm nhận ra {int(zone.out_correct)}/{int(zone.out_correct + zone.missed_out)} tỉnh "
      "thực tế ở ngoài vùng dày. Đọc kết quả này cùng sai số điểm PAPI.")"""))

md(nbf.v4.new_markdown_cell("""**Hình phân bổ quan sát năm 2024 dùng để làm gì?** Dùng lưới đến 2023 làm
mốc chung để đo độ phủ của vùng dày, tìm các quan sát nằm ngoài vùng đó và
theo dõi một tỉnh qua hai năm. Trong 61 tỉnh đủ hai điểm quan sát 2024,
48 tỉnh vào cụm lớn và 13 tỉnh ở ngoài vùng dày.

**Vì sao xử lý dữ liệu rồi vẫn có điểm nhiễu?** Hai tỉnh thiếu chỉ tiêu
được loại khỏi phép gán. Cả 13 tỉnh mang nhãn −1 đều đủ hai điểm và
nằm trong ô có dưới 5 quan sát tham chiếu. Bảng bên dưới ghi rõ lý do và
số quan sát có sẵn trong ô của từng tỉnh. Giữ các điểm ô thưa giúp tính
độ phủ trên đủ 61 tỉnh và tìm các trường hợp cần đối chiếu với số liệu gốc.

Khi đánh giá dự báo, nhãn từ hai điểm thực tế là kết quả tham chiếu trên
cùng lưới. Phép đánh giá còn cần đủ tám đầu vào năm 2023, nên có 59 tỉnh
đối chiếu được. Ví dụ dưới hình dùng lại tỉnh Lạng Sơn để minh họa."""))

cd(nbf.v4.new_code_cell("""from scripts.common.papi_pred_common import GRID_ASSIGNMENT_LABELS, describe_grid_assignment

display(Image(filename=str(ROOT / "results/figs/predict_2024.png")))
observed_grid = describe_grid_assignment(observations, feats, forecast_run.scaler, forecast_run.grid)
status_counts = observed_grid.grid_status.value_counts().rename(index=GRID_ASSIGNMENT_LABELS)
display(status_counts.rename("Số tỉnh").rename_axis("Kết quả gán").to_frame())
review = observed_grid.loc[observed_grid.grid_status.ne("in_cluster")].copy()
review["grid_status"] = review.grid_status.map(GRID_ASSIGNMENT_LABELS)
display(review[["province_vi", "grid_cell", "reference_count", "grid_status"]].rename(columns={
    "province_vi": "Tỉnh/thành phố", "grid_cell": "Ô lưới", "reference_count": "Số điểm tham chiếu",
    "grid_status": "Lý do",
}).reset_index(drop=True))

example_years = panel.loc[panel.province_vi.eq("Lạng Sơn") & panel.year.isin([2023, 2024])].sort_values("year")
example = describe_grid_assignment(example_years, feats, forecast_run.scaler, forecast_run.grid)
for row in example.itertuples(index=False):
    region = "ngoài vùng dày" if row.cluster == -1 else f"cụm {row.cluster}"
    print(f"Lạng Sơn {row.year}: {region} trên cùng lưới đến năm 2023. "
          f"Ô {row.grid_cell} có {row.reference_count} điểm tham chiếu.")"""))

md(nbf.v4.new_markdown_cell("""## 5. Kết luận và hạn chế

Trên dữ liệu giả lập, STING đạt ARI 0,950 khi đối chiếu với nhãn tham chiếu.
Trên 869 quan sát PAPI 2011–2024, ở ngưỡng 5, ba cụm STING có 677, 16 và
5 điểm. Cụm lớn chiếm khoảng 97% trong số 698 điểm được gán cụm. Còn
171 điểm (19,7% toàn mẫu) nằm trong các ô thưa. Kết quả nổi bật là một
vùng tập trung lớn và hai vùng nhỏ. Ở ngưỡng 8, kết quả còn một cụm.

K-means k = 2 chia 677 điểm ở vùng STING lớn nhất thành hai phần gồm
482 và 195 điểm. Ở cấu hình đang dùng, z-score giữ nguyên chỉ số ô STING
vì hai lưới đều dựng lại theo biên từng trục. Kết quả K-means có thể đổi
do phép chuẩn hóa thay đổi khoảng cách. So sánh silhouette dựa trên nhóm
điểm được cả ba phương pháp gán cụm, nên kết quả mô tả phần dữ liệu này.
Mỗi cụm gồm các quan sát tỉnh–năm. Diễn giải giới hạn trong hai chỉ tiêu,
giai đoạn và cấu hình đã xét.

Minh họa dự báo bổ sung cho thấy sai số điểm và khả năng nhận ra điểm
ngoài vùng dày trả lời hai câu hỏi riêng. Notebook cuối kỳ trình bày
phép đối chiếu dự báo chi tiết theo tỉnh và các kịch bản dao động.

**Nguồn tham khảo**

- Wang, Yang và Muntz (1997), bài báo về lưới thống kê STING tại VLDB.
  [Bài báo gốc](https://www.vldb.org/conf/1997/P186.PDF)
- Dữ liệu PAPI 2011–2024 do CECODES, VFF-CRT, RTA và UNDP công bố.
  [Nguồn dữ liệu PAPI](https://papi.org.vn/du-lieu-papi/)
- Công cụ chuẩn hóa và thước đo so sánh từ scikit-learn 1.8.
  [StandardScaler](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.StandardScaler.html) ·
  [Silhouette](https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.silhouette_score.html) ·
  [ARI](https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.adjusted_rand_score.html)
- Le và cộng sự (2026), dữ liệu đối chiếu các chỉ số nội dung PAPI.
  [Mendeley Data, DOI 10.17632/wbk42j9wc8.1](https://data.mendeley.com/datasets/wbk42j9wc8/1)"""))

nb["cells"] = cells
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print("written:", OUT)


def main() -> int:
    env = {
        **os.environ,
        "STING_REPO_ROOT": str(ROOT),
        "SUBMISSION_DEMO_NB_PATH": str(OUT),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(OUT)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        print("nbconvert FAILED:\n" + proc.stdout[-4000:])
        print("STDERR:\n" + proc.stderr[-4000:])
        return 1

    check = json.loads(OUT.read_text(encoding="utf-8"))
    code_cells = [c for c in check["cells"] if c["cell_type"] == "code"]
    n_code = len(code_cells)
    n_err = sum(1 for c in code_cells for o in c.get("outputs", [])
                if o.get("output_type") == "error")
    n_noout = sum(1 for c in code_cells if not c.get("outputs"))
    if n_err or n_noout:
        print(f"FAIL: {n_err} lỗi, {n_noout} ô code thiếu output (trong {n_code} ô)")
        return 1

    visual = next(cell for cell in code_cells if "papi-zscore-comparison" in cell["metadata"].get("tags", []))
    png = next(out["data"]["image/png"] for out in visual["outputs"] if "image/png" in out.get("data", {}))
    (ROOT / "results/figs/papi_zscore_comparison.png").write_bytes(b64decode("".join(png)))

    print(f"notebook OK: {n_code} code cells, 0 error outputs, mọi ô có output")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
