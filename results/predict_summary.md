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

| min_count | coverage 2024 | số cụm |
|---|---|---|
| 3 | 82% | 3 |
| 5 | 79% | 3 |
| 8 | 70% | 1 |

## Lưu ý phương pháp
- Một lưới TOÀN CỤC cho mọi năm (nhãn so sánh được giữa các năm; các năm không độc lập — phù hợp cho mục tiêu dự đoán). Phân tích per-year ở Phase 5 là phương pháp KHÁC, không trộn số liệu.
- Năm 2024 KHÔNG tham gia bước chọn cấu hình (xem `predict_sweep.py`); kết quả 2024 ở trên là out-of-sample.
- Cặp chỉ tiêu nằm trong nhóm ĐÃ QUA AUDIT thang đo (xem `scripts/check_data.py`); các sub-dim có bước nhảy (sd_5_4 tại 2021, sd_2_1 tại 2018, …) đã bị loại khỏi pipeline dự đoán.
- Nhãn 2023 cũng do model gán (in-sample); dịch chuyển sát ranh giới ô lưới có thể nhạy với ngưỡng cố định — không diễn giải quá mức các dịch chuyển nhỏ.
