# Dự đoán cụm PAPI bằng STING — train 2011–2023, dự đoán 2024

- Cặp chỉ tiêu: **4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công** × **6.1 Y tế công lập**
- Cấu hình (đóng băng trước đánh giá qua `predict_sweep.py`): STING(L=3, factor=4, min_count=5), level=2; train n=808, test n=61
- Kết quả train: 3 cụm [629, 16, 5], nhiễu 20% (nhiễu = ô không đủ dày, KHÔNG nằm trong bảng hồ sơ cụm bên dưới)
- Dự đoán 2024 (đánh giá MỘT LẦN sau khi chốt cấu hình): phủ 79%, phân bố {-1: 13, 2: 48}

## Hồ sơ cụm (train, chỉ điểm thuộc cụm)

|   cluster |   n |   sd_4_2 |   sd_6_1 |
|----------:|----:|---------:|---------:|
|         0 |   5 |     1.6  |     1.76 |
|         1 |  16 |     1.67 |     1.63 |
|         2 | 629 |     1.93 |     1.93 |

## Thành phần dự đoán 2024 (chỉ điểm thuộc cụm)

|   pred_cluster |   n | vi_du                                                        |
|---------------:|----:|:-------------------------------------------------------------|
|              2 |  48 | Hà Giang, Cao Bằng, Bắc Kạn, Tuyên Quang, Lào Cai, Điện Biên |

## Chuyển cụm 2023 → 2024

| pred_cluster_prev   |   -1 |   2 |   All |
|:--------------------|-----:|----:|------:|
| -1                  |    4 |   5 |     9 |
| 2                   |    7 |  43 |    50 |
| All                 |   11 |  48 |    59 |

- **Chuyển thật giữa 2 cụm**: 0/59 tỉnh; sang nhiễu: 7; từ nhiễu ra: 5; giữ nguyên (kể cả nhiễu): 47.
- Loại khỏi so sánh (thiếu chỉ tiêu): 4 dòng (2023 và/hoặc 2024).

## Độ nhạy coverage theo min_count (cảnh báo: coverage là ngưỡng-phụ thuộc)

| min_count | coverage 2024 | số cụm | ARI vs cấu hình chốt (2024) | đổi cụm↔nhiễu vs chốt (tỉnh) |
|---|---|---|---|---|
| 3 | 82% | 3 | 0.852 | 2 |
| 5 | 79% | 3 | 1.000 | 0 |
| 8 | 70% | 1 | 0.678 | 5 |

*Lưu ý phương pháp*: so khớp nhãn chính xác (exact agreement) giữa mc=3 và cấu hình chốt mc=5 chỉ đạt 18% — thấp do HOÁN VỊ NHÃN (nhãn 0/1/2 là quy ước gán theo thứ tự ô dày; đổi min_count là đổi lưới nên nhãn bị xáo trộn), còn ARI bất biến với hoán vị nhãn nên là thước đúng — không đọc nhầm thành gãy model.

## Hạn chế diễn giải

- Cấu trúc “k=3” thực chất là 1 cụm khổng lồ + 2 cụm li ti: 96.8% điểm non-noise thuộc cụm lớn nhất (629/650). selection_metrics trong predict_config.json (fit ≤ 2020, sizes [453, 16, 5]) ghi 95.6% — metadata đó mô tả fit ≤ 2020, còn model.pkl đóng gói là fit 2011–2023 ([629, 16, 5]).
- Hai cụm li ti (nhãn [0, 1]) chỉ có điểm trong 2011–2018 và không nhận điểm nào từ 2019 trở đi: vùng đặc trưng tạo cụm nhỏ không còn điểm mới — model fit 2011–2023 dùng cho 2024 phải đọc theo ý đó (concept drift).
- “Chuyển thật giữa 2 cụm: 0/59” là phát biểu rỗng (vacuous): cả 2023 lẫn 2024 không có điểm nào thuộc cụm 0, 1 (0 điểm) — không phải bằng chứng về độ ổn định nhãn.
- 13/61 tỉnh 2024 vào nhiễu do ô lưới thưa (count < min_count), không phải do scaler: STING bất biến với biến đổi affine từng chiều (z-score mỗi chiều), nguồn −1 là ô không đủ mật độ.

## Lưu ý phương pháp
- Một lưới TOÀN CỤC cho mọi năm (nhãn so sánh được giữa các năm; các năm không độc lập — phù hợp cho mục tiêu dự đoán). Phân tích per-year ở Phase 5 là phương pháp KHÁC, không trộn số liệu.
- Năm 2024 KHÔNG tham gia bước chọn cấu hình (xem `predict_sweep.py`); kết quả 2024 ở trên là out-of-sample.
- Cặp chỉ tiêu nằm trong nhóm ĐÃ QUA AUDIT thang đo (xem `scripts/check_data.py`); các sub-dim có bước nhảy (sd_5_4 tại 2021, sd_2_1 tại 2018, …) đã bị loại khỏi pipeline dự đoán.
- Nhãn 2023 cũng do model gán (in-sample); dịch chuyển sát ranh giới ô lưới có thể nhạy với ngưỡng cố định — không diễn giải quá mức các dịch chuyển nhỏ.
