# Audit tiền xử lý theo thứ tự Day 4

Sinh bởi `scripts/preprocessing_audit.py` — CHỈ ĐỌC dữ liệu, không ghi lại panel hay master.

- Panel: `data/processed/papi_panel_63_2011_2024.csv` — 882 dòng × 41 cột, 63 tỉnh × 14 năm (2011–2024)
- Master ngoại lai: `data/processed/external_master_63_2011_2024.csv` — 882 dòng × 59 cột
- Crosswalk: `data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv`
- Metadata thang đo: `data/processed/papi_panel_scale_metadata.csv`
- Tham số chuẩn hóa đóng băng: `models/sting_predict_scaler.json`

Mỗi bảng dưới đây là một giai đoạn: **Test | Result | Decision | Evidence**. Result là số đo trên file thật; Decision là quyết định pipeline đang áp dụng; Evidence là `file:dòng` của quyết định đó.

## 1. Cleaning

Thứ tự trong Day 4: trùng khóa → thiếu → nhất quán → ngoại lai CUỐI CÙNG.

| Test | Result | Decision | Evidence file:line |
|---|---|---|---|
| Trùng khóa (province_code, year), dedup chạy ĐẦU TIÊN | 0 dòng trùng / 882 dòng (882 khóa duy nhất); trùng toàn dòng: 0 | Giữ đúng 1 dòng/khóa. Pipeline chặn cứng nếu phát hiện trùng (không tự bỏ dòng) — dedup nằm ở bước đầu của Cleaning. | scripts/build_external_master.py:139-140; scripts/predict_supervised.py:101-102 |
| Ô thiếu trong 37 cột chỉ tiêu (8 chiều + tiểu chiều) | 4649/32634 ô (14.2%); 4284 ô nằm NGOÀI cửa sổ thu thập của cột (d7/sd_7_*/sd_8_*/sd_5_2) | KHÔNG nội suy, không điền: giữ NaN. Chỉ loại dòng khi ghép cặp / dựng ma trận feature. | scripts/papi_pred_common.py:56; scripts/predict_demo.py:67-68 |
| Dòng thiếu ≥1 chỉ tiêu TRONG cửa sổ thu thập | 13/882 dòng, 365 ô; 13 dòng thiếu sd_4_2 hoặc sd_6_1 | Loại khỏi train/dự đoán bằng dropna trên đúng cột đang dùng; không điền, không nội suy. | scripts/predict_demo.py:67-68; scripts/predict_supervised.py:106 |
| Tên tỉnh vs crosswalk 63 tỉnh | 0 xung đột; 63/63 mã khớp crosswalk | Tên/mã lấy từ crosswalk; mã không map được là lỗi chặn (build dừng). | scripts/build_panel.py:204-217; scripts/build_panel.py:210-213; data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv:2-64 |
| Khoảng giá trị vs metadata thang đo | 0 ô ngoài khoảng / 32634 ô (37 cột × 882 dòng) | Giữ nguyên giá trị; không cắt, không sửa theo metadata. | data/processed/papi_panel_scale_metadata.csv:2-38 (cột thang_2011_2020, thang_2021_2024); scripts/check_data.py:34-58 |
| Giá trị ngoài cửa sổ thu thập của từng cột | 0 ô | Giữ; cửa sổ năm là metadata kiểm chứng, không dùng để xóa ô. | data/processed/papi_panel_scale_metadata.csv:2-38 (cột nam_bat_dau, nam_ket_thuc) |
| Điểm 0.0 (quy ước 'tỉnh không được xếp hạng') | 0 ô điểm = 0.0 còn lại | 0.0 → NaN ngay khi dựng panel để không lẫn với điểm thật. | scripts/build_panel.py:218-226 |
| Đánh dấu ngoại lai z-score > 3 (trị tuyệt đối) | 122 ô (0.4%), 98 dòng, 29 cột | GIỮ toàn bộ — chỉ đánh dấu, không xóa. Đây là điểm khảo sát thật; điểm cực trị rơi vào ô lưới thưa và tự nhận nhãn nhiễu (-1) theo cơ chế min_count của STING, dữ liệu gốc không bị loại. | src/sting.py:12-13; src/sting.py:334; scripts/predict_demo.py:110 |

### 1.1 Thiếu theo năm (chỉ cột còn trong cửa sổ thu thập)

| Năm | Số cột trong cửa sổ | Ô thiếu | Tỷ lệ | Dòng thiếu ≥1 |
|---|---|---|---|---|
| 2011 | 28 | 0 | 0.00% | 0 |
| 2012 | 28 | 0 | 0.00% | 0 |
| 2013 | 28 | 0 | 0.00% | 0 |
| 2014 | 28 | 56 | 3.17% | 2 |
| 2015 | 28 | 0 | 0.00% | 0 |
| 2016 | 28 | 0 | 0.00% | 0 |
| 2017 | 28 | 0 | 0.00% | 0 |
| 2018 | 36 | 20 | 0.88% | 2 |
| 2019 | 37 | 0 | 0.00% | 0 |
| 2020 | 37 | 0 | 0.00% | 0 |
| 2021 | 36 | 108 | 4.76% | 3 |
| 2022 | 36 | 37 | 1.63% | 2 |
| 2023 | 36 | 72 | 3.17% | 2 |
| 2024 | 36 | 72 | 3.17% | 2 |

### 1.2 Thiếu theo cột

| Cột | Ô thiếu | Tỷ lệ | Năm có thiếu |
|---|---|---|---|
| d1 | 10 | 1.1% | 2014–2024 (5 năm) |
| d2 | 13 | 1.5% | 2014–2024 (6 năm) |
| d3 | 10 | 1.1% | 2014–2024 (5 năm) |
| d4 | 13 | 1.5% | 2014–2024 (6 năm) |
| d5 | 10 | 1.1% | 2014–2024 (5 năm) |
| d6 | 9 | 1.0% | 2014–2024 (4 năm) |
| d7 | 448 | 50.8% | 2011–2024 (10 năm) |
| d8 | 449 | 50.9% | 2011–2024 (11 năm) |
| sd_1_1 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_1_2 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_1_3 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_1_4 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_2_1 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_2_2 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_2_3 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_2_4 | 452 | 51.2% | 2011–2024 (12 năm) |
| sd_3_1 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_3_2 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_3_3 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_4_1 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_4_2 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_4_3 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_4_4 | 13 | 1.5% | 2014–2024 (6 năm) |
| sd_5_1 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_5_2 | 254 | 28.8% | 2014–2024 (5 năm) |
| sd_5_3 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_5_4 | 10 | 1.1% | 2014–2024 (5 năm) |
| sd_6_1 | 9 | 1.0% | 2014–2024 (4 năm) |
| sd_6_2 | 9 | 1.0% | 2014–2024 (4 năm) |
| sd_6_3 | 9 | 1.0% | 2014–2024 (4 năm) |
| sd_6_4 | 9 | 1.0% | 2014–2024 (4 năm) |
| sd_7_1 | 448 | 50.8% | 2011–2024 (10 năm) |
| sd_7_2 | 448 | 50.8% | 2011–2024 (10 năm) |
| sd_7_3 | 448 | 50.8% | 2011–2024 (10 năm) |
| sd_8_1 | 449 | 50.9% | 2011–2024 (11 năm) |
| sd_8_2 | 449 | 50.9% | 2011–2024 (11 năm) |
| sd_8_3 | 512 | 58.0% | 2011–2024 (12 năm) |

## 2. Integration

Khóa nối, cardinality, số dòng, xung đột tên/giá trị, rò rỉ dữ liệu.

| Test | Result | Decision | Evidence file:line |
|---|---|---|---|
| Khóa nối duy nhất hai phía + quan hệ bản ghi | panel 0 trùng; master 0 trùng; quan hệ one_to_one (không one-to-many/many-to-many) | Nối one-to-one theo (province_code, year); không nhân dòng. | scripts/build_external_master.py:148; scripts/build_external_master.py:139-140 |
| Số dòng trước/sau khi nối panel × master | 882 → 882; 63 tỉnh; lưới khóa giống nhau: True | LEFT join giữ đúng lưới panel; ô ngoại lai thiếu để trống, có mask. | scripts/build_external_master.py:149-150; scripts/build_external_master.py:180-183 |
| Tên và giá trị trùng giữa panel và master | 0 lệch tên/63 mã; papi_province_code≠province_code: 0; 37 cột số chung lệch tối đa 8.88e-16 (sai số biểu diễn CSV); 0 ô lệch > 1e-09 | Không sửa; dung sai 1e-9 xác nhận hai file cùng một dữ liệu. | scripts/build_external_master.py:161; scripts/build_external_master.py:70-82 |
| Scaler/lưới dự đoán có fit ngoài cutoff không | JSON khớp thống kê ≤2023: 808 dòng, Δmean=0, Δscale=0; nếu fit cả 869 dòng thì Δmean=0.011456 → không khớp JSON | Không rò rỉ: scaler + lưới STING chỉ fit ≤2023; 2024 (63 dòng, 61 đủ 2 chỉ tiêu) chỉ được transform/predict. | scripts/predict_demo.py:65-70; scripts/predict_demo.py:75-77; scripts/predict_demo.py:113; scripts/predict_sweep.py:112-113; scripts/predict_supervised.py:156-159 |

## 3. Transformation

Chuẩn hóa (scaling) — fit ở đâu, kiểm chứng số học.

| Test | Result | Decision | Evidence file:line |
|---|---|---|---|
| Phương pháp chuẩn hóa | StandardScaler z-score (ddof=0), 2 chỉ tiêu sd_4_2, sd_6_1; fit một lần trên gộp 2011–2023 | Dùng tham số đã đóng băng trong models/sting_predict_scaler.json; không fit lại trên 2024. | scripts/predict_demo.py:70-72; models/sting_predict_scaler.json:10-17 |
| Đối chiếu số học mean/scale với panel thật | Δmean=0; Δscale=0; ddof=1 lệch 1.13e-04 → xác nhận ddof=0 | Tham số JSON tái lập được từ đúng các năm lịch sử; giữ nguyên trạng. | models/sting_predict_scaler.json:10-17 (mean, scale); scripts/predict_demo.py:86-99 |

## Kết luận

- Không phát hiện lỗi chặn: 0 dòng trùng khóa, 0 xung đột tên, 0 ô ngoài khoảng metadata, rò rỉ scaler: False.
- Thiếu dữ liệu là cấu trúc: 4284/4649 ô thiếu nằm ngoài cửa sổ thu thập của cột; 365 ô trong cửa sổ, trên 13 dòng — đúng bằng số dòng thiếu chỉ tiêu mô hình (13).
- Ngoại lai chỉ đánh dấu (122 ô), không xóa; quyết định giữ dựa trên bản chất điểm khảo sát và cơ chế nhãn nhiễu của STING.
- z-score > 3 tính gộp toàn panel nên trộn cả bước nhảy thang đo giữa các năm (metadata ghi rõ vài cột đổi thang 2021); audit này không kết luận tương đương thang đo xuyên năm.
- Ngoài pipeline chính: `scripts/candidates_regression.py:172` dùng SimpleImputer(median) cho một ứng viên tham khảo — không thuộc pipeline đã công bố.
