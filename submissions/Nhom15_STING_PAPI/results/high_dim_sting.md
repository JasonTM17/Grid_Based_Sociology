# Phân tích mở rộng STING đa chiều trên dữ liệu PAPI (2011–2024)

## 1. Bối cảnh và vấn đề mở còn lại từ nhánh 2D

- Trong `results/robustness.csv`, nhánh 8 chiều tổng hợp `d1–d8` (`2018–2024`, `n=430`) với lưới đều `L=3, f=2, mc=10, lv=1` có **`60.5%` nhiễu** (`k=3`), còn khi hạ ngưỡng xuống `mc=2` để kéo nhiễu xuống `10.9%` thì Silhouette tụt xuống **`-0.089`** (gộp một khối 381 điểm kèm cụm 2 điểm).
- Tương tự, `PCA(2)` trên `d1–d6` (`2011–2024`, `n=869`) chỉ giữ `63,2%` phương sai và bị lưới `9×9` gộp toàn vùng lõi thành **`k=1` cụm** (`6,2%` nhiễu).
- Để giải quyết có hệ thống mà **không làm rò rỉ dữ liệu 2024** và **giữ nguyên cấu hình 2D đóng băng `3/4/5/2`**, phân tích này đối chiếu bốn hướng trên **cùng tập dữ liệu với STING 2D**: `8` tiểu chỉ tiêu đã sàng lọc nhất quán thang đo (`sd_1_3..sd_6_3`, tập train `<=2023` gồm `n=808`, tập holdout `2024` gồm `n=61`), song song với bộ `d1–d8` (`2018–2024`, `n=430`, trong đó train `<=2023` `n=369`).

## 2. Kết quả chính theo 5 hướng kỹ thuật

### 2.1. Thang thưa lưới theo số chiều (Curse of Dimensionality, d = 2..8)
- Với lưới chính thức `f=4, lv=2, mc=5` (`16` ô/trục): ở `d=2` (`256` ô) nhiễu là `19.6%`, nhưng sang `d=3` (`4.096` ô) chỉ còn `9` ô dày và nhiễu nhảy lên **`93.9%`**; tới `d=4` (`65.536` ô) còn **`0` ô dày (nhiễu `100.0%`)**; còn `d=8` cần tới `4,29 × 10^9` ô lá.

### 2.2. Chọn tập con đặc trưng (train <= 2023: 28 cặp 2D, 56 bộ ba 3D)
- Rà soát vét cạn chỉ trên `<=2023` cho thấy `23/28` cặp 2D (`f=4, lv=2, mc=5`) đạt `k>=2` và `nhiễu <= 40%`, nhưng `0/28` cặp tách thành hai khối cân bằng (`largest_cluster_share <= 90%`): bản chất phân bố PAPI cấp tỉnh trong không gian 2D–3D là **một vùng lõi dày đặc chiếm ưu thế (>90% điểm thuộc cụm) kèm các túi ngoại lai nhỏ**.

### 2.3. Khai phá không gian con CLIQUE Apriori từ dưới lên
- Thay vì duyệt lưới 8 chiều đầy đủ (`65.536` ô ở `4^8`), CLIQUE Apriori tìm thấy cấu trúc đa cụm đến **`5D–6D`** trên lưới đều (`tau=0,03`): nhánh **`5D sd_1_3+sd_4_1..4_4`** phủ **`41.0%`** (`k=2 [303, 28]`, Silhouette `0.433`, phủ `34.4%` năm 2024), còn nhánh **`6D`** tách `[61, 57]` (`Silhouette 0.368`, kiểm định mô tả `PCI_dm p=0.0112`, `GRDP_dm p=0.0118`) nhưng chỉ phủ `14.6%`.
- Kết hợp CLIQUE với chia ô quantile (`bins=4, tau=0,05`), các không gian con 4 chiều như **`sd_4_1..4_3+sd_6_3`** tách được **`2` cực đối xứng `[57, 45]` với Silhouette `0.772`** (kiểm định `PCI_dm p=6.99e-06`), nhưng đánh đổi chỉ bao phủ **`12.6%`** các điểm rơi vào vùng cực trị (`21.3%` trên 2024).

### 2.4. Chia lưới thích nghi QuantileSTING hiệu chuẩn mật độ kỳ vọng n/res^d
- Trên không gian **8 chiều sàng lọc (`n=808`)** với `L=3, f=2, lv=1` (`2^8 = 256` ô, kỳ vọng `3,16` điểm/ô):
  - **Uniform Equal-Width (`mc=10`)** bị lệch đuôi ngoại lai kéo giãn, gom toàn bộ `580` điểm thành **`k=1` cụm** (không phân tách).
  - **QuantileSTING (`mc=7`, `2,2×` kỳ vọng)**: cắt theo trung vị train trên cả 8 trục, tách được **`k=4` chế độ** (`[222, 219, 8, 8]`, phủ **`56.6%`** train và **`60.7%`** holdout 2024), phân biệt rõ chỉ số ngoài **PCI khử theo năm (`p = 0.00052`, trung vị `58,66` vs `64,43`)** và **GRDP khử theo năm (`p = 0.0248`)**.
  - **QuantileSTING (`mc=10`, `3,2×` kỳ vọng)**: tăng Silhouette lên **`0.237`** (`[168, 166, 12, 10]`, `PCI_dm p = 0.00234`), nhiễu `55.9%`.
- Trên đúng bộ **`8D d1..d8 (2018–2024, n=430)`** của `robustness.csv`, **QuantileSTING (`mc=4`)** hạ nhiễu xuống **`44.7%`** (vượt ngưỡng `<50%` so với `60,5%` của Uniform gốc) đồng thời nâng Silhouette lên **`+0.161`** (so với `-0,089` của nhánh Uniform `mc=2`).
- **Giới hạn ngược chiều (không tô hồng):** ở lưới mịn **2D `16×16` (`sd_4_2, sd_6_1`)**, Quantile chia đều biên làm vỡ cụm lõi thành 24 mảnh nhỏ và tăng nhiễu lên `49,5%` (kém hơn hẳn Uniform `19,6%`, Silhouette `0,361`). Do đó **STING 2D đóng băng tiếp tục dùng lưới đều**, còn **Quantile & CLIQUE phát huy thế mạnh riêng ở không gian 3D–8D**.

### 2.5. Mở rộng PCA(2..4) so với baseline PCA(2) k=1
- Lý giải nguyên nhân sụp 1 cụm của `PCA(2)`: `f=3, lv=2` (`81` ô) quá thô trước đám mây điểm `PCA(2)`. Khi tăng lên `f=4` (`16×16`) hoặc `PCA(3)` (`75,7%–76,1%` phương sai), STING tách được `2–5` cụm phụ nhưng vẫn chỉ là lõi lớn + túi rìa nhỏ và kém khả diễn giải trục so với Subspace CLIQUE / QuantileSTING.

## 3. Ràng buộc an toàn thời gian & phạm vi diễn giải
1. Mọi bước `StandardScaler`, biên `QuantileWarper`, sàng lọc tập con `2D/3D` và đơn vị dày `CLIQUE` chỉ khớp trên **`year <= 2023`** (`test_high_dim_sting.py` kiểm chứng bất biến khi làm nhiễu `2024`).
2. Các kiểm định `PCI_dm` và `GRDP_dm` là **đối chiếu mô tả ngoại lai đã khử hiệu ứng năm**, chưa hiệu chỉnh đa kiểm định qua nhiều không gian con và không kết luận quan hệ nhân quả.
3. Tài liệu chi tiết kèm toàn bộ không gian con lưu tại `results/high_dim_sting.csv`, `results/high_dim_sting_subspaces.csv`, hình `results/figs/high_dim_sting_analysis.png` và sheet **`STING đa chiều`** trong `results/KetQua_STING_PAPI.xlsx`.
