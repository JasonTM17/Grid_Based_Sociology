# Phân tích hồi quy chuyên sâu — đa mô hình, AR(1) vs Δy, VIF và Conformal Prediction

**Giao thức:** Tái dùng ĐÚNG pipeline `scripts/supervised/predict_supervised.py` (`740` cặp train `year_t ≤ 2022`, `6` fold expanding origin `2017–2022`, holdout `59` cặp `2023→2024`). Siêu tham số, đặc trưng và bán kính Conformal đều hiệu chỉnh **CHỈ trên tập train/CV `≤ 2022`**, không chạm holdout `2024`.

## 1) So sánh 17 mô hình hồi quy, cơ chế và hiệu ứng cố định tỉnh (cùng CV 2017–2022 & holdout 2024)

| Mô hình | Nhóm | Siêu tham số tốt nhất (CV) | CV R² | CV MAE | Beat Ridge (/6) | Beat Carry (/6) | Holdout MAE | Holdout RMSE | Holdout R² | Bias (thực − dự báo) |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| Giữ nguyên năm trước (carry-forward) | baseline | mặc định | 0.1453 | 0.0719 | 2/6 | 0/6 | 0.0683 | 0.0875 | 0.198 | +0.0333 |
| Trung bình tập huấn luyện | baseline | mặc định | -0.7703 | 0.1076 | 0/6 | 0/6 | 0.0814 | 0.1027 | -0.105 | +0.0317 |
| AR(1) OLS (chỉ 6.1) | mechanism | mặc định | 0.2679 | 0.0675 | 4/6 | 5/6 | 0.0621 | 0.0745 | 0.419 | +0.0246 |
| AR(1) Ridge (chỉ 6.1) | mechanism | alpha=0.1 | 0.2678 | 0.0675 | 4/6 | 5/6 | 0.0621 | 0.0745 | 0.419 | +0.0246 |
| OLS LinearRegression (8 đặc trưng) | linear | mặc định | 0.2652 | 0.0671 | 2/6 | 4/6 | 0.0640 | 0.0769 | 0.381 | +0.0304 |
| Ridge (8 đặc trưng, chính thức) | linear | alpha=0.1 | 0.2652 | 0.0671 | 0/6 | 4/6 | 0.0640 | 0.0769 | 0.381 | +0.0304 |
| Lasso L1 (8 đặc trưng) | linear | alpha=0.001 | 0.2692 | 0.0671 | 4/6 | 4/6 | 0.0637 | 0.0762 | 0.391 | +0.0298 |
| ElasticNet L1+L2 (8 đặc trưng) | linear | alpha=0.005, l1_ratio=0.2 | 0.2689 | 0.0671 | 4/6 | 4/6 | 0.0637 | 0.0762 | 0.393 | +0.0297 |
| Decision Tree (8 đặc trưng) | nonlinear | max_depth=2, min_samples_leaf=5 | 0.2028 | 0.0709 | 0/6 | 4/6 | 0.0631 | 0.0783 | 0.359 | +0.0170 |
| Random Forest (8 đặc trưng, chính thức) | nonlinear | max_depth=4, min_samples_leaf=2 | 0.1966 | 0.0706 | 1/6 | 4/6 | 0.0616 | 0.0742 | 0.423 | +0.0225 |
| KNN Regressor (8 đặc trưng) | nonlinear | n_neighbors=20, weights=distance | 0.1677 | 0.0713 | 0/6 | 4/6 | 0.0586 | 0.0760 | 0.396 | +0.0144 |
| SVR RBF (8 đặc trưng) | nonlinear | C=0.1, epsilon=0.05 | 0.1846 | 0.0699 | 1/6 | 3/6 | 0.0643 | 0.0809 | 0.314 | +0.0264 |
| HistGradientBoosting (8 đặc trưng) | nonlinear | learning_rate=0.03, max_leaf_nodes=8 | 0.1811 | 0.0712 | 1/6 | 4/6 | 0.0646 | 0.0783 | 0.358 | +0.0303 |
| Ablation Ridge (7 đặc trưng, bỏ 6.1) | mechanism | alpha=0.1 | -0.2637 | 0.0881 | 1/6 | 1/6 | 0.0658 | 0.0824 | 0.289 | +0.0136 |
| Mô hình sai phân Δ6.1 = y(t+1)-y(t) (Ridge) | mechanism | alpha=50.0 | 0.2732 | 0.0667 | 3/6 | 5/6 | 0.0645 | 0.0774 | 0.372 | +0.0312 |
| Mô hình sai phân Δ6.1 = y(t+1)-y(t) (ElasticNet) | mechanism | alpha=0.01, l1_ratio=0.2 | 0.2715 | 0.0670 | 3/6 | 5/6 | 0.0640 | 0.0765 | 0.388 | +0.0299 |
| Panel FE: Ridge + OneHot 63 tỉnh | panel_fe | alpha=10.0 | 0.2686 | 0.0674 | 4/6 | 5/6 | 0.0605 | 0.0743 | 0.422 | +0.0285 |

### Đọc kết quả cốt lõi từ Bảng 1
- **Tự tương quan AR(1) vs đa chiều:** Chỉ dùng riêng `sd_6_1(t)` (`AR(1) OLS`) đã đạt CV `R² = 0.2679` (holdout MAE `0.0621`, R² `0.419`), nhỉnh hơn nhẹ so với `Ridge 8F` (`0.2652`); trong khi **bỏ `sd_6_1` (`Ablation Ridge 7F`)** làm CV `R²` sụt xuống **`-0.2637`**. Điều này xác nhận tín hiệu chính là quán tính `6.1` kèm hồi quy về trung bình.
- **Mô hình sai phân (`Δ6.1 = y_{t+1} - y_t`):** Học trực tiếp biên độ thay đổi rồi cộng lại `y_t` với `Ridge` (`α=50`) đạt **CV `R² = 0.2732`** (cao nhất bảng về CV `R²`, thắng Carry-Forward `5/6` fold), nhờ phạt mạnh hệ số của 7 biến phụ nhiễu.
- **Panel Fixed Effects (`OneHot 63 tỉnh + 8 đặc trưng`):** Cho CV `R² = 0.2686` (thắng Ridge `4/6` fold) và đạt **`Holdout MAE = 0.0605` (`R² = 0.422`)** — gợi ý đặc trưng nền riêng từng tỉnh có giá trị mô tả nếu hiệu chuẩn dài hạn.
- **Học máy điều chuẩn vs phi tuyến:** `Lasso` (`0.2692`) và `ElasticNet` (`0.2689`) nhỉnh hơn nhẹ OLS/Ridge nhờ co các chiều tham nhũng tương quan (`VIF = 3.76–5.00`), nhưng `Wilcoxon p = 0.8945` trên OOF CV (`n=366`) cho thấy mức chênh rất nhỏ chưa đủ tạo ưu thế thực chất. Nhóm phi tuyến (`DT 0.203`, `RF 0.197`, `SVR 0.185`, `HistGB 0.181`, `KNN 0.168`) đều có CV `R²` thấp hơn nhóm tuyến tính điều chuẩn.

## 2) Hệ số hồi quy chuẩn hóa (β trên Z-score train) & Đa cộng tuyến (VIF)

- **Chỉ số điều kiện (Condition Number) của ma trận tương quan 8 đặc trưng:** `5.09`.

| Đặc trưng | Tên chỉ tiêu | β OLS | β Ridge | β Lasso | β ElasticNet | VIF |
|:--|:--|--:|--:|--:|--:|--:|
| `sd_1_3` | 1.3 Chất lượng bầu cử | +0.0030 | +0.0030 | +0.0035 | +0.0035 | 1.42 |
| `sd_1_4` | 1.4 Đóng góp tự nguyện | +0.0115 | +0.0115 | +0.0106 | +0.0106 | 1.41 |
| `sd_4_1` | 4.1 Kiểm soát tham nhũng trong chính quyền địa phương | +0.0051 | +0.0051 | +0.0035 | +0.0035 | 4.21 |
| `sd_4_2` | 4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công | +0.0092 | +0.0092 | +0.0045 | +0.0046 | 5.00 |
| `sd_4_3` | 4.3 Công bằng trong tuyển dụng vào khu vực công | -0.0126 | -0.0126 | -0.0070 | -0.0069 | 3.76 |
| `sd_4_4` | 4.4 Quyết tâm chống tham nhũng của chính quyền địa phương | -0.0080 | -0.0080 | -0.0061 | -0.0060 | 1.62 |
| `sd_6_1` | 6.1 Y tế công lập | +0.0891 | +0.0891 | +0.0890 | +0.0885 | 1.48 |
| `sd_6_3` | 6.3 Cơ sở hạ tầng căn bản | -0.0030 | -0.0030 | -0.0028 | -0.0029 | 1.34 |

## 3) Kiểm định cặp (Wilcoxon signed-rank & Bootstrap CI 95% trên ΔMAE = MAE_ứng_viên − MAE_mốc)

| Cặp so sánh | n | MAE ứng viên | MAE mốc | ΔMAE | CI 95% (2000 bootstrap) | Wilcoxon p | Số cặp cải thiện |
|:--|--:|--:|--:|--:|:--|--:|--:|
| OOF CV 2017–2022: Ridge vs Carry-Forward | 366 | 0.0671 | 0.0719 | -0.00476 | [-0.00800, -0.00148] | 0.01939 | 201/366 (54.9%) |
| Holdout 2023→2024: Ridge vs Carry-Forward | 59 | 0.0640 | 0.0683 | -0.00430 | [-0.01285, +0.00356] | 0.3937 | 34/59 (57.6%) |
| OOF CV 2017–2022: AR(1) Ridge vs Carry-Forward | 366 | 0.0675 | 0.0719 | -0.00436 | [-0.00743, -0.00144] | 0.01893 | 193/366 (52.7%) |
| OOF CV 2017–2022: ElasticNet vs Ridge | 366 | 0.0671 | 0.0671 | -0.00001 | [-0.00045, +0.00043] | 0.8945 | 177/366 (48.4%) |
| Holdout 2023→2024: ElasticNet vs Ridge | 59 | 0.0637 | 0.0640 | -0.00033 | [-0.00110, +0.00039] | 0.4237 | 31/59 (52.5%) |

## 4) Hiệu chỉnh bất định: Conformal Prediction 80%/90% & Quantile Regression (không dùng 2024 để chọn bán kính)

- **Conformal 80% (OOF `2017–2022`):** bán kính ±`0.1063` → độ phủ thực tế trên 59 tỉnh holdout 2024 = **`88.1%`**.
- **Conformal 90% (OOF `2017–2022`):** bán kính ±`0.1403` → độ phủ thực tế trên 59 tỉnh holdout 2024 = **`94.9%`**.
- **Conformal 90% (gần nhất `2021–2022`):** bán kính ±`0.1219` → độ phủ thực tế 2024 = **`93.2%`**.
- **Quantile GBR `[q10, q90]` (bề rộng danh nghĩa 80%):** bề rộng trung bình `0.1955` → độ phủ thực tế 2024 = **`83.1%`**.
- **Ý nghĩa cảnh báo biên (mốc train `1.7848`):** Dự báo điểm thuần túy (`pred_ridge < 1.7848`) cảnh báo **`4`** tỉnh (bắt `1/4` ca nhóm 6.1 thấp 2024), còn dùng cận dưới Conformal 90% (`conformal_lo90 < 1.7848`) cảnh báo **`28`** tỉnh (bắt **`4/4`** ca thực tế nhóm 6.1 thấp nằm trong holdout).
- **Giới hạn trung thực:** Conformal không biến hồi quy co tâm thành bộ phân loại chính xác từng ca ngoại lệ (`bias = +0.0304` năm 2024 làm khoảng lệch trên nhẹ về phía trên), mà định lượng rõ độ bất định ±`0.14–0.16` điểm quanh đường dự báo để tránh hiểu nhầm điểm dự báo đơn lẻ.

## Tệp sinh ra
- `results/regression_deep_analysis.csv`
- `results/regression_conformal_2024.csv`
- `results/figs/regression_diagnostics_deep.png`
- Sheet `Hồi quy chuyên sâu` trong `results/KetQua_STING_PAPI.xlsx`
