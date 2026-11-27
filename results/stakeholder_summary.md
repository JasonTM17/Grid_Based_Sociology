# Thống kê bàn giao cho khách hàng từ kết quả phân cụm STING (63 tỉnh PAPI)

Tài liệu này trả lời trực tiếp câu hỏi nghiệp vụ: **sau khi chạy phân cụm STING ra các nhãn kỹ thuật (`-1, 0, 1, 2`) và chỉ số ô lưới `(i, j)`, cuối cùng thống kê được gì để bàn giao cho khách hàng (cơ quan quản lý địa phương / đơn vị tư vấn cải cách hành chính công)?**

Mọi số liệu dưới đây được tính tất định từ bộ nhãn đóng băng (`results/papi_observed_grid_2024.csv`, `results/predict_all_years.csv`, `results/papi_forecast_provinces_2024.csv`) và dữ liệu độc lập (`PCI 2022`, `GRDP/người 2024`, `Nghèo GSO 2024`).

## 1. Phân loại hành động 63 tỉnh năm 2024 (không gộp chung nhãn nhiễu `-1`)

- **Mốc chuẩn thực nghiệm từ Cụm 2 (`n = 48` tỉnh trong vùng dày năm 2024):** trung vị **4.2 = 2.0317** (IQR 1.9928–2.0844); trung vị **6.1 = 1.9629** (IQR 1.9230–2.0107).
- **Ngưỡng tách hai cực bên trong 13 tỉnh ô thưa (`-1`):** `sd_6_1 < Q25 − 0.5 × IQR = 1.8791` phân tách rạch ròi 5 tỉnh tụt sâu về y tế công lập (thực tế đều `≤ 1.808`) khỏi 8 tỉnh biên tăng trưởng vượt chuẩn (`4.2 > trung vị lõi`, `6.1 ≥ 1.888`).

| Nhóm hành động bàn giao | Số tỉnh | Tỉ lệ /63 | Trung vị 4.2 | Trung vị 6.1 | Trung vị số năm Cụm 2 | Trung vị kịch bản ngoài vùng 2024 (%) | Trung vị GRDP 2024 (tr.đ) | Trung vị PCI 2022 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Biên bứt phá vượt chuẩn** | 8 | 12.7% | 2.235 | 1.963 | 10.0 | 39.8% | 87.38 | 64.78 |
| **Vùng lõi ổn định (Cụm 2)** | 48 | 76.2% | 2.032 | 1.963 | 11.5 | 18.5% | 80.97 | 65.25 |
| **Ưu tiên cải thiện Y tế 6.1** | 5 | 7.9% | 2.050 | 1.788 | 8.0 | 31.3% | 104.26 | 66.74 |
| **Thiếu dữ liệu 2024** | 2 | 3.2% | — | — | 11.5 | 22.3% | 108.94 | 66.04 |

### Danh sách chi tiết từng nhóm ngoài vùng lõi và nhóm chuẩn

#### Biên bứt phá vượt chuẩn (`n = 8`)

| Tỉnh | 4.2 | 6.1 | Ô lưới 2024 | Phân tầng cụ thể | Khuyến nghị hành động |
|---|---:|---:|:---:|---|---|
| Cà Mau | 2.178 | 1.888 | `(13, 9)` | Dẫn đầu trục 4.2 (6.1 quanh vùng cụm) | Nhân rộng thực hành tốt về kiểm soát tham nhũng trong dịch vụ công 4.2 và giữ ổn định y tế 6.1. |
| Quảng Ninh | 2.260 | 1.889 | `(14, 9)` | Dẫn đầu trục 4.2 (6.1 quanh vùng cụm) | Nhân rộng thực hành tốt về kiểm soát tham nhũng trong dịch vụ công 4.2 và giữ ổn định y tế 6.1. |
| An Giang | 2.159 | 1.911 | `(13, 9)` | Dẫn đầu trục 4.2 (6.1 quanh vùng cụm) | Nhân rộng thực hành tốt về kiểm soát tham nhũng trong dịch vụ công 4.2 và giữ ổn định y tế 6.1. |
| Tây Ninh | 2.285 | 1.924 | `(15, 10)` | Dẫn đầu trục 4.2 (6.1 quanh vùng cụm) | Nhân rộng thực hành tốt về kiểm soát tham nhũng trong dịch vụ công 4.2 và giữ ổn định y tế 6.1. |
| Bà Rịa - Vũng Tàu | 2.258 | 2.002 | `(14, 11)` | Vượt trội kép (4.2 & 6.1 > trung vị lõi) | Khảo sát điển hình quản trị tốt trên cả hai trục để chia sẻ kinh nghiệm liên tỉnh. |
| Sóc Trăng | 2.252 | 2.048 | `(14, 12)` | Vượt trội kép (4.2 & 6.1 > trung vị lõi) | Khảo sát điển hình quản trị tốt trên cả hai trục để chia sẻ kinh nghiệm liên tỉnh. |
| Bình Thuận | 2.218 | 2.112 | `(14, 13)` | Vượt trội kép (4.2 & 6.1 > trung vị lõi) | Khảo sát điển hình quản trị tốt trên cả hai trục để chia sẻ kinh nghiệm liên tỉnh. |
| Hà Tĩnh | 2.050 | 2.191 | `(11, 15)` | Vượt trội kép (4.2 & 6.1 > trung vị lõi) | Khảo sát điển hình quản trị tốt trên cả hai trục để chia sẻ kinh nghiệm liên tỉnh. |

#### Ưu tiên cải thiện Y tế 6.1 (`n = 5`)

| Tỉnh | 4.2 | 6.1 | Ô lưới 2024 | Phân tầng cụ thể | Khuyến nghị hành động |
|---|---:|---:|:---:|---|---|
| Hà Nội | 1.931 | 1.686 | `(10, 5)` | Thấp hơn lõi trên cả 2 trục (đặc biệt 6.1) | Ưu tiên rà soát toàn diện chất lượng y tế công lập 6.1 và kiểm soát tham nhũng 4.2. |
| Cần Thơ | 2.016 | 1.698 | `(11, 5)` | Thấp hơn lõi trên cả 2 trục (đặc biệt 6.1) | Ưu tiên rà soát toàn diện chất lượng y tế công lập 6.1 và kiểm soát tham nhũng 4.2. |
| Gia Lai | 2.050 | 1.787 | `(11, 7)` | Lệch pha: 4.2 đạt/vượt chuẩn, 6.1 tụt sâu | Rà soát các thành phần của chỉ tiêu y tế công lập 6.1 và xác minh bằng dữ liệu địa phương. |
| Long An | 2.074 | 1.807 | `(12, 7)` | Lệch pha: 4.2 đạt/vượt chuẩn, 6.1 tụt sâu | Rà soát các thành phần của chỉ tiêu y tế công lập 6.1 và xác minh bằng dữ liệu địa phương. |
| Bình Dương | 2.177 | 1.808 | `(13, 7)` | Lệch pha: 4.2 đạt/vượt chuẩn, 6.1 tụt sâu | Rà soát các thành phần của chỉ tiêu y tế công lập 6.1 và xác minh bằng dữ liệu địa phương. |

#### Thiếu dữ liệu 2024 (`n = 2`)

| Tỉnh | 4.2 | 6.1 | Ô lưới 2024 | Phân tầng cụ thể | Khuyến nghị hành động |
|---|---:|---:|:---:|---|---|
| Vĩnh Phúc | — | — | `—` | Thiếu chỉ tiêu 4.2 hoặc 6.1 | Kiểm tra lại mẫu khảo sát PAPI 2024 và thu thập bổ sung trước khi xếp nhóm. |
| Tiền Giang | — | — | `—` | Thiếu chỉ tiêu 4.2 hoặc 6.1 | Kiểm tra lại mẫu khảo sát PAPI 2024 và thu thập bổ sung trước khi xếp nhóm. |

#### 5 tỉnh chuẩn tham chiếu bền vững 14/14 năm trong Cụm 2 (`n = 5`)

**Phú Thọ** (`4.2=2.205`, `6.1=1.947`), **Đà Nẵng** (`4.2=2.023`, `6.1=1.923`), **Bình Định** (`4.2=2.113`, `6.1=2.009`), **Ninh Thuận** (`4.2=2.194`, `6.1=1.995`), **Vĩnh Long** (`4.2=2.071`, `6.1=1.924`).

#### Nhóm rìa dưới ngay trong Cụm 2 cần giữ nhịp Y tế 6.1 (`sd_6_1 < 1.879`, `n = 7`)

**TP. Hồ Chí Minh** (`4.2=2.005`, `6.1=1.759`, ô `(11, 6)`), **Đồng Nai** (`4.2=2.009`, `6.1=1.764`, ô `(11, 6)`), **Lâm Đồng** (`4.2=1.853`, `6.1=1.826`, ô `(9, 8)`), **Bình Phước** (`4.2=1.940`, `6.1=1.840`, ô `(10, 8)`), **Hải Phòng** (`4.2=1.897`, `6.1=1.842`, ô `(9, 8)`), **Điện Biên** (`4.2=2.053`, `6.1=1.846`, ô `(11, 8)`), **Trà Vinh** (`4.2=2.027`, `6.1=1.856`, ô `(11, 8)`).

## 2. Dịch chuyển trạng thái 2023 → 2024 (tách rõ hướng rời cụm)

| Xu hướng dịch chuyển 2023 → 2024 | Số tỉnh | Danh sách tỉnh |
|---|---:|---|
| Giữ vững Cụm 2 | 43 | TP. Hồ Chí Minh, Hải Phòng, Điện Biên, Trà Vinh, Kon Tum, Lào Cai, Lai Châu, Bến Tre, Quảng Ngãi, Đà Nẵng, Vĩnh Long, Bạc Liêu, Hà Giang, Hà Nam, Kiên Giang, Bắc Giang, Đồng Tháp, Phú Thọ, Đắk Lắk, Cao Bằng, Ninh Bình, Sơn La, Yên Bái, Hải Dương, Hậu Giang, Nghệ An, Thái Nguyên, Nam Định, Khánh Hòa, Ninh Thuận, Quảng Nam, Bình Định, Bắc Ninh, Phú Yên, Quảng Trị, Hưng Yên, Thanh Hóa, Đắk Nông, Thái Bình, Quảng Bình, Tuyên Quang, Bắc Kạn, Hòa Bình |
| Vào Cụm 2 từ ngoài lõi | 5 | Đồng Nai, Lâm Đồng, Bình Phước, Lạng Sơn, Thừa Thiên Huế |
| Rời Cụm 2 lên biên bứt phá | 5 | Cà Mau, An Giang, Bà Rịa - Vũng Tàu, Bình Thuận, Hà Tĩnh |
| Duy trì ngoài lõi (−1) | 4 | Tây Ninh, Sóc Trăng, Hà Nội, Cần Thơ |
| Thiếu dữ liệu 2023 | 2 | Quảng Ninh, Bình Dương |
| Rời Cụm 2 xuống rìa Y tế 6.1 | 2 | Gia Lai, Long An |
| Thiếu dữ liệu 2024 | 2 | Vĩnh Phúc, Tiền Giang |

## 3. Kịch bản ngoài vùng năm 2024 (Top 10 `outside_scenario_share`)

Trong hồi kiểm 2023→2024, dự báo điểm phát hiện 0/11 tỉnh ngoài vùng dày trên 59 tỉnh đối chiếu được. Tỉ lệ kịch bản dùng phần dư lịch sử để xếp hạng rủi ro biến động (AUC thăm dò = `0.816` trên năm 2024). Đây không phải xác suất đã hiệu chỉnh hay dự báo cho năm sau 2024.

| Hạng | Tỉnh | Nhóm 2024 | 4.2 | 6.1 | Tỉ lệ kịch bản ngoài vùng (%) |
|---:|---|---|---:|---:|---:|
| 1 | Sóc Trăng | Biên bứt phá vượt chuẩn | 2.252 | 2.048 | 71.4% |
| 2 | Tây Ninh | Biên bứt phá vượt chuẩn | 2.285 | 1.924 | 60.4% |
| 3 | Bạc Liêu | Vùng lõi ổn định (Cụm 2) | 2.155 | 1.927 | 47.5% |
| 4 | Thừa Thiên Huế | Vùng lõi ổn định (Cụm 2) | 2.149 | 2.118 | 46.2% |
| 5 | Đồng Nai | Vùng lõi ổn định (Cụm 2) | 2.009 | 1.764 | 42.6% |
| 6 | Cà Mau | Biên bứt phá vượt chuẩn | 2.178 | 1.888 | 42.6% |
| 7 | Hà Nội | Ưu tiên cải thiện Y tế 6.1 | 1.931 | 1.686 | 40.7% |
| 8 | An Giang | Biên bứt phá vượt chuẩn | 2.159 | 1.911 | 39.8% |
| 9 | Đồng Tháp | Vùng lõi ổn định (Cụm 2) | 2.036 | 1.940 | 38.7% |
| 10 | Hà Tĩnh | Biên bứt phá vượt chuẩn | 2.050 | 2.191 | 37.6% |

## 4. Ý nghĩa kinh tế–xã hội bàn giao cho khách hàng (chỉ mô tả, không suy nhân quả)

- **Tách được hai câu chuyện trái ngược trong mã kỹ thuật `-1`:** 8 tỉnh vùng biên bứt phá đạt trung vị GRDP 2024 là `87.38` triệu/người và PAPI `4.2 = 2.235` (cao hơn hẳn vùng lõi), trong khi 5 tỉnh ưu tiên Y tế `6.1` có trung vị GRDP 2024 tới `104.26` triệu/người (cao hơn vùng lõi `80.97` triệu/người) nhưng `6.1 = 1.788` — chênh lệch mô tả, không chứng minh quá tải hay quan hệ nhân quả.
- Toàn bộ bảng chi tiết 63 tỉnh nằm tại `results/stakeholder_province_summary_2024.csv` và hình minh họa tại `results/figs/stakeholder_quadrants_2024.png`.
