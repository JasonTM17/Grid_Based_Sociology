# [THAM KHẢO — THỰC NGHIỆM HƯỚNG PHÁT TRIỂN, CHƯA DUYỆT GV]

Tài liệu tổng hợp kết quả chạy thực nghiệm 4 hướng mở rộng định lượng (`E1–E4`) và danh sách gợi ý khảo sát định tính (`Hướng 5`) cho đồ án STING × PAPI, **không làm thay đổi các artifact đóng băng**.

## Hướng 1 (`E1`): Chuẩn hóa thứ hạng phần trăm trong từng năm (Rank-normalization)

- **Thiết lập:** Trên đủ **869 quan sát** (`sd_4_2`, `sd_6_1`), tính `rank(pct=True)` trong từng năm rồi chạy đúng cấu hình STING đóng băng (`16×16`, `min_count=5`, `connectivity=1`).
- **Kết quả:** **25 cụm** (kích thước `{0: 62, 1: 13, 2: 8, 3: 6, 4: 31, 5: 5, 6: 5, 7: 17, 8: 5, 9: 5, 10: 5, 11: 7, 12: 16, 13: 11, 14: 5, 15: 6, 16: 5, 17: 7, 18: 9, 19: 5, 20: 5, 21: 31, 22: 11, 23: 113, 24: 6}`), **470/869 nhiễu (54.1%)**.
- **Đối chiếu với STING z-score gộp (`3` cụm, `171` nhiễu):** `ARI (đầy đủ 869)` = **-0.0091**, `ARI (giao không nhiễu, n=327)` = **0.0085**.
- **Đọc kết quả trung thực:** Chuẩn hóa hạng trong năm **thay đổi chính câu hỏi nghiên cứu** (từ *mức điểm tuyệt đối xuyên 14 năm* sang *vị thế tương đối trong từng năm*), nên phân hoạch khác biệt rõ rệt (`ARI non-noise` thấp) là điều hợp lý về mặt hình học, không chứng minh cách nào đúng hơn một cách tuyệt đối và không suy ra nguyên nhân đổi thang đo.

## Hướng 2 (`E2`): Phân cụm quỹ đạo tuyến tính cấp tỉnh 2011–2024 (Feature trajectory)

- **Thiết lập:** Lọc các tỉnh có tối thiểu **8 năm** đủ cả `4.2` & `6.1` (**63 tỉnh**), lấy độ dốc OLS (`slope_4_2`, `slope_6_1`) chuẩn hóa Z-score rồi chạy STING (`4×4`, `min_count=3`) và K-Means (`k=3`, `seed=42`).
- **Kết quả:** STING tìm được **1 cụm**, **2 tỉnh nhiễu (3.2%)**, silhouette (non-noise) = **n/a (< 2 cụm)** | K-Means (`k=3`) kích thước `{0: 18, 1: 25, 2: 20}`, silhouette = **0.3430**.
- **Top-3 tỉnh tăng nhanh nhất theo `slope_6_1`:** Ninh Bình (`+0.0350`/năm), Vĩnh Phúc (`+0.0336`/năm), Bắc Ninh (`+0.0332`/năm).
- **Top-3 tỉnh giảm / chậm nhất theo `slope_6_1`:** Lào Cai (`-0.0133`/năm), Quảng Nam (`-0.0114`/năm), Trà Vinh (`-0.0058`/năm).
- **Đọc kết quả trung thực:** Độ dốc OLS gom 14 năm thành xu hướng tuyến tính trung bình để loại bỏ lặp quan sát tỉnh-năm, nhưng có thể che khuất bước ngoặt phi tuyến hoặc thay đổi thiết kế khảo sát giữa kỳ; không suy diễn thành hiệu quả điều hành nhân quả.

## Hướng 3 (`E3`): Backtest cuốn chiếu nhiều mốc (`2018 → 2023`, năm mục tiêu `2019–2024`)

- **Thiết lập:** Tái dùng nguyên văn `forecast_from_history` và `score_forecast` tại 6 mốc xuất phát `2018..2023` (chỉ dùng dữ liệu `<= origin_year`; mốc `2023→2024` trùng khớp `results/papi_forecast_2024.json`).

| Năm gốc | Mục tiêu | Chỉ tiêu | Chọn theo CV | MAE Dự báo | MAE Giữ năm trước | Lợi thế MAE | Out-recall (Dự báo vs Giữ năm trước) |
|---:|---:|---|---|---:|---:|---:|---:|
| 2018 | 2019 | `sd_4_2` | `ridge` | 0.1279 | 0.1060 | -0.0220 | 0.265 vs 0.294 |
| 2018 | 2019 | `sd_6_1` | `ridge` | 0.0693 | 0.0623 | -0.0071 | 0.265 vs 0.294 |
| 2019 | 2020 | `sd_4_2` | `ridge` | 0.0871 | 0.0845 | -0.0025 | 0.115 vs 0.500 |
| 2019 | 2020 | `sd_6_1` | `ridge` | 0.0616 | 0.0666 | +0.0049 | 0.115 vs 0.500 |
| 2020 | 2021 | `sd_4_2` | `ridge` | 0.1090 | 0.1272 | +0.0182 | 0.000 vs 0.091 |
| 2020 | 2021 | `sd_6_1` | `ridge` | 0.0816 | 0.0895 | +0.0079 | 0.000 vs 0.091 |
| 2021 | 2022 | `sd_4_2` | `ridge` | 0.0705 | 0.0942 | +0.0237 | 0.000 vs 0.000 |
| 2021 | 2022 | `sd_6_1` | `ridge` | 0.0522 | 0.0644 | +0.0122 | 0.000 vs 0.000 |
| 2022 | 2023 | `sd_4_2` | `ridge` | 0.0876 | 0.0943 | +0.0067 | 0.000 vs 0.231 |
| 2022 | 2023 | `sd_6_1` | `ridge` | 0.0728 | 0.0728 | -0.0000 | 0.000 vs 0.231 |
| 2023 | 2024 | `sd_4_2` | `ridge` | 0.0736 | 0.0763 | +0.0026 | 0.000 vs 0.364 |
| 2023 | 2024 | `sd_6_1` | `ridge` | 0.0641 | 0.0683 | +0.0042 | 0.000 vs 0.364 |

- **Tổng hợp 6 mốc:** `sd_4_2` có MAE dự báo TB **0.0926** vs giữ năm trước **0.0971** (thắng **4/6** năm); `sd_6_1` đạt **0.0670** vs **0.0706** (thắng **4/6** năm).
- **Nhận diện ngoài vùng dày (`out_recall` TB 6 mốc):** Dự báo = **0.063** vs Giữ năm trước = **0.247** (`balanced_zone_accuracy` TB: **0.522** vs **0.566**).
- **Phạm vi đánh giá:** Tại mỗi mốc, mô hình và scaler chỉ fit từ lịch sử đến năm xuất phát; bước chọn mô hình không dùng năm mục tiêu. Tuy nhiên, cặp chỉ tiêu và thiết kế lưới được chọn bằng thông tin tới 2021–2022. Các mốc mục tiêu 2019–2022 vì vậy là hồi cứu theo thiết kế cố định, chưa đánh giá độc lập toàn bộ quy trình lựa chọn. Mốc `2023→2024` tái lập kết quả holdout đã công bố, không tạo thêm một phép kiểm định độc lập. Tổng hợp 6 mốc chỉ cho thấy MAE trung bình giảm nhẹ và thắng 4/6 năm ở mỗi chỉ tiêu; dự báo vẫn bỏ sót phần lớn quan sát ngoài vùng dày. Cần chọn lại cả đặc trưng và cấu hình bên trong từng cửa sổ huấn luyện hoặc đánh giá trên giai đoạn mới để đo khả năng tổng quát hóa của toàn quy trình.

## Hướng 4 (`E4`): Tự tương quan không gian (Moran's I) & Cân bằng lớp (`class_weight`)

- **Thiết lập không gian:** Ma trận kề Queen 63 tỉnh từ `data/raw/boundaries/diaphantinh.geojson` (chuẩn hóa tên khớp 63/63 tỉnh; trung bình **4.29** láng giềng/tỉnh; Hà Nội có **8** láng giềng; đảo/rời trong mẫu 2024 = `[]`).
- **Bản đồ Choropleth & Phiếu tỉnh:** Đã hiện hữu sẵn tại `scripts/analysis/client_product.py` và tab **Thống kê khách hàng** trên `app.py` (không làm trùng).

| Biến phân tích (2024) | Số tỉnh (`n`) | Moran's I | Kỳ vọng `E[I]` | `p_perm` (999 hoán vị) | Số đảo loại trừ |
|---|---:|---:|---:|---:|---:|
| `sd_4_2` | 61 | -0.0537 | -0.0167 | 0.6680 | 0 |
| `sd_6_1` | 61 | 0.1834 | -0.0167 | 0.0240 | 0 |
| `in_cluster` | 61 | -0.0324 | -0.0167 | 0.8600 | 0 |

- **Cân bằng lớp (`class_weight='balanced'`) — Trích kết quả đã đánh giá tại [results/candidates_classification.md](https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/results/candidates_classification.md) (`CLF` CV `2017–2022`, CHƯA DUYỆT GV & KHÔNG chạm holdout 2024):**
  - `C3`: Random Forest + `class_weight='balanced'` đạt `macro-F1 CV = 0.5238` (so với LR gốc `0.434`, thắng `6/6` fold).
  - `C1`: Logistic Regression + `class_weight='balanced'` đạt `macro-F1 CV = 0.4861` (thắng `4/6` fold).
- **Đọc kết quả trung thực:** Moran's I chỉ đo tương quan không gian mô tả ở lát cắt năm 2024 theo kề ranh giới hành chính, không chứng minh hiệu ứng lan tỏa nhân quả giữa các tỉnh. Các p-value hoán vị mang tính thăm dò, chưa hiệu chỉnh nhiều phép thử; `C1`/`C3` vẫn là ứng viên [CHƯA DUYỆT GV] trên pseudo-label STING.

## Hướng 5: Gợi ý đối chiếu định tính (ngoài phạm vi code tự động)

- Đối chiếu danh sách **8 tỉnh ngoài vùng dày phía điểm cao** (nhãn CSV lịch sử: `Biên bứt phá vượt chuẩn`) trong [`results/stakeholder_summary.md`](stakeholder_summary.md) và quy trình chấm phiếu độc lập tại [`reports/quy-trinh-tham-dinh-danh-sach-papi.md`](https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/reports/quy-trinh-tham-dinh-danh-sach-papi.md) (tuyệt đối không dùng điểm/nhãn STING để tự xác nhận).
- Dưới đây là hợp của các tỉnh có độ dốc `6.1` cực trị (`E2`) và các tỉnh ô thưa năm 2024 (`-1`) làm **bảng ứng viên tham khảo** cho bước phỏng vấn / rà soát hồ sơ địa phương (không kết luận đúng/sai hay nhân quả):

| Tỉnh | Tiêu chí gợi ý | Nhóm hành động 2024 | Độ dốc `4.2` | Độ dốc `6.1` | Điểm `6.1` (2024) |
|---|---|---|---:|---:|---:|
| An Giang | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0280 | +0.0105 | 1.911 |
| Bà Rịa - Vũng Tàu | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0226 | +0.0150 | 2.002 |
| Bình Dương | Ô thưa (-1) 2024 | Ngoài vùng dày, 6.1 thấp | +0.0246 | +0.0130 | 1.808 |
| Bình Thuận | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0282 | +0.0269 | 2.112 |
| Bắc Ninh | Top-3 tăng nhanh 6.1 | Trong vùng dày (Cụm 2) | +0.0454 | +0.0332 | 2.016 |
| Cà Mau | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0179 | +0.0117 | 1.888 |
| Cần Thơ | Ô thưa (-1) 2024 | Ngoài vùng dày, 6.1 thấp | +0.0064 | -0.0009 | 1.698 |
| Gia Lai | Ô thưa (-1) 2024 | Ngoài vùng dày, 6.1 thấp | +0.0166 | +0.0255 | 1.787 |
| Hà Nội | Ô thưa (-1) 2024 | Ngoài vùng dày, 6.1 thấp | +0.0402 | +0.0125 | 1.686 |
| Hà Tĩnh | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0269 | +0.0190 | 2.191 |
| Long An | Ô thưa (-1) 2024 | Ngoài vùng dày, 6.1 thấp | +0.0013 | +0.0013 | 1.807 |
| Lào Cai | Top-3 giảm nhanh 6.1 | Trong vùng dày (Cụm 2) | +0.0320 | -0.0133 | 1.896 |
| Ninh Bình | Top-3 tăng nhanh 6.1 | Trong vùng dày (Cụm 2) | +0.0302 | +0.0350 | 1.966 |
| Quảng Nam | Top-3 giảm nhanh 6.1 | Trong vùng dày (Cụm 2) | +0.0143 | -0.0114 | 2.009 |
| Quảng Ninh | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0705 | +0.0131 | 1.889 |
| Sóc Trăng | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0092 | +0.0123 | 2.048 |
| Trà Vinh | Top-3 giảm nhanh 6.1 | Trong vùng dày (Cụm 2) | +0.0190 | -0.0058 | 1.856 |
| Tây Ninh | Ô thưa (-1) 2024 | Ngoài vùng dày phía điểm cao | +0.0275 | +0.0139 | 1.924 |
| Vĩnh Phúc | Top-3 tăng nhanh 6.1 | Thiếu dữ liệu 2024 | +0.0341 | +0.0336 | — |

## Lệnh tái lập & Tệp đầu ra

- Lệnh chạy: `python scripts/analysis/future_work.py`
- Các tệp đầu ra:
  - `results/future_work_rank.csv`
  - `results/future_work_trajectory.csv`
  - `results/future_work_backtest.csv`
  - `results/future_work_spatial.csv`
  - `results/future_work.md`
  - `results/figs/future_work_overview.png`
