# Kiểm định bổ trợ — tỷ lệ hộ nghèo GSO theo nhãn cụm STING (cửa sổ giao 2012–2024)

Sinh bởi `scripts/poverty_validation.py`. Kiểm chứng ngoại lai thứ hai của cụm STING sau PCI (nguồn độc lập với PAPI): nghèo GSO là số liệu thống kê chính thức, không phải khảo sát hộ dân. Nhãn cụm lấy từ `results/predict_all_years.csv` (model đóng băng, gate bởi `tests/test_artifact_reproduction.py`); join khóa (year, province_code) `validate="one_to_one"` đúng protocol `scripts/external_validation.py`. Thống kê bằng scipy 1.16.3 (Python 3.14.2), helper tái dùng nguyên xi (`group_table`, `anova_kruskal`, `source_note`, `place_n_labels`). Mọi số tự tính lại từ CSV — không hardcode, không nội suy.

## 1) Dữ liệu và join — cửa sổ giao 2012–2024

- `external_poverty_63.csv`: 1071 dòng × 17 năm (2006, 2008, 2010 & 2012–2025); cửa sổ giao có nhãn: **819 ô**, trong đó **818 ô có giá trị** `poverty_rate_pct`.
- Thiếu phía nguồn (dòng có trong CSV, giá trị trống — nguồn pxweb ghi `".."`): TP. Hồ Chí Minh 2016 (code 79). KHÔNG nội suy (data/raw/gso/PROVENANCE.md:90).
- Left-join nhãn cụm: **805 ô vào kiểm định**; **13 ô tỉnh-năm có poverty nhưng KHÔNG có nhãn** (panel PAPI thiếu sd_4_2/sd_6_1) — loại KHỎI kiểm định, mask tường minh (pattern GRDP, external_validation.py:477-486): Bắc Giang 2014; Đồng Tháp 2014; Quảng Ninh 2018; Đồng Tháp 2018; Quảng Ninh 2021; Bắc Giang 2021; Bắc Ninh 2021; Bắc Giang 2022; Bắc Ninh 2022; Quảng Ninh 2023; Bình Dương 2023; Vĩnh Phúc 2024; Tiền Giang 2024.
- Panel theo cụm: nhiễu (–1) n=144, cụm 0 n=2, cụm 1 n=10, cụm 2 n=649.

## 2) Kiểm định gộp — HAI kết quả báo cáo CÙNG nhau

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |   max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|------:|
|             -1 | nhiễu (–1) | 144 |  9.872 |     6.6  | 9.937 |   0   |  42.3 |
|              0 | cụm 0      |   2 | 14.95  |    14.95 | 3.748 |  12.3 |  17.6 |
|              1 | cụm 1      |  10 |  4.55  |     3.25 | 3.641 |   1.2 |  12.1 |
|              2 | cụm 2      | 649 |  9.008 |     6.2  | 8.729 |   0   |  50.2 |

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |   max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|------:|
|             -1 | nhiễu (–1) | 144 |  2.124 |    -1.05 | 9.071 | -12.8 |  33.7 |
|              0 | cụm 0      |   2 |  4.5   |     4.5  | 0.283 |   4.3 |   4.7 |
|              1 | cụm 1      |  10 | -6.035 |    -6.2  | 2.848 |  -9   |   0.2 |
|              2 | cụm 2      | 649 |  2.444 |     0    | 8.378 | -12.8 |  42.3 |

- **Gộp thô** (poverty gốc, nhiễm xu hướng năm): Kruskal–Wallis H = 4.6670, p = 0.198; One-way ANOVA F(3,801) = 1.5376, p = 0.203; eta² = 0.0057 — KHÔNG đáng kể thống kê.
- **Đã trừ median trong năm** (tách hiệu ứng năm): Kruskal–Wallis H = 20.6285, p = 0.000126; ANOVA F(3,801) = 3.3629, p = 0.0183; eta² = 0.0124 — đáng kể.
- Median nghèo toàn panel giảm rất mạnh xuyên năm: 12.9% (2012) → 2.3% (2024); tỷ trọng cụm cũng trôi theo năm (nhiễu 17/63 năm 2012 → 2–27/63 trong các năm của cửa sổ). Test gộp thô phối trộn hiệu ứng năm với khác biệt cụm — hai số trên PHẢI đọc cùng nhau, không chọn trình bày một kết quả.
- Diễn giải thận trọng: cụm 0 (n=2) và cụm 1 (n=10) quá nhỏ để tự kết luận; cặp tương phản đáng tin duy nhất là **nhiễu vs cụm 2** (đối xứng cảnh báo PCI — external_validation.py:608-610). Đọc eta²/ANOVA chỉ như mô tả bổ sung.

## 3) Mann–Whitney nhiễu vs cụm 2 (hai phía)

- Thô: U = 47464, p = 0.767 — không khác biệt.
- Đã trừ median trong năm: U = 43978, p = 0.269 — không khác biệt.
- Kết luận an toàn: ở mức gộp, Mann–Whitney nhiễu vs cụm 2 không khác biệt (thô) và không khác biệt (đã trừ median năm) — nghèo GSO đọc như kiểm chứng bổ trợ, không phải bằng chứng độc lập mạnh như PCI; tín hiệu cụm (nếu có) nằm trong kiểm định đã-trừ-median-năm ở mục 2, so phân phối toàn bộ các nhóm.

## 4) Thống kê từng nhóm — RIÊNG TỪNG năm giao và pooled

### 4a) Pooled gộp thô (n=805)

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |   max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|------:|
|             -1 | nhiễu (–1) | 144 |  9.872 |     6.6  | 9.937 |   0   |  42.3 |
|              0 | cụm 0      |   2 | 14.95  |    14.95 | 3.748 |  12.3 |  17.6 |
|              1 | cụm 1      |  10 |  4.55  |     3.25 | 3.641 |   1.2 |  12.1 |
|              2 | cụm 2      | 649 |  9.008 |     6.2  | 8.729 |   0   |  50.2 |

### 4b) Pooled đã trừ median trong năm (n=805)

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |   max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|------:|
|             -1 | nhiễu (–1) | 144 |  2.124 |    -1.05 | 9.071 | -12.8 |  33.7 |
|              0 | cụm 0      |   2 |  4.5   |     4.5  | 0.283 |   4.3 |   4.7 |
|              1 | cụm 1      |  10 | -6.035 |    -6.2  | 2.848 |  -9   |   0.2 |
|              2 | cụm 2      | 649 |  2.444 |     0    | 8.378 | -12.8 |  42.3 |

### 4c) Theo từng năm × cụm (giá trị thô)

| section             | group      |   year |   n |   mean |   median |     std |   min |   max | note   |
|:--------------------|:-----------|-------:|----:|-------:|---------:|--------:|------:|------:|:-------|
| poverty_by_year_raw | cụm 0      |   2012 |   1 | 17.6   |    17.6  | nan     |  17.6 |  17.6 |        |
| poverty_by_year_raw | cụm 1      |   2012 |   2 |  6.15  |     6.15 |   2.333 |   4.5 |   7.8 |        |
| poverty_by_year_raw | cụm 2      |   2012 |  43 | 15.23  |    14.1  |   9.484 |   0.1 |  43.5 |        |
| poverty_by_year_raw | nhiễu (–1) |   2012 |  17 | 13.876 |     9    |  12.049 |   0.1 |  42.3 |        |
| poverty_by_year_raw | cụm 1      |   2013 |   4 |  6.675 |     5.85 |   4.288 |   2.9 |  12.1 |        |
| poverty_by_year_raw | cụm 2      |   2013 |  43 | 13.16  |    12    |   8.875 |   0.1 |  38.6 |        |
| poverty_by_year_raw | nhiễu (–1) |   2013 |  16 | 14.506 |    12.55 |  11.056 |   0   |  40.6 |        |
| poverty_by_year_raw | cụm 1      |   2014 |   2 |  1.9   |     1.9  |   0.99  |   1.2 |   2.6 |        |
| poverty_by_year_raw | cụm 2      |   2014 |  42 | 10.49  |     9.8  |   6.803 |   0   |  35.3 |        |
| poverty_by_year_raw | nhiễu (–1) |   2014 |  17 | 13.794 |    11.1  |  10.713 |   0   |  33   |        |
| poverty_by_year_raw | cụm 0      |   2015 |   1 | 12.3   |    12.3  | nan     |  12.3 |  12.3 |        |
| poverty_by_year_raw | cụm 2      |   2015 |  35 |  8.366 |     7.2  |   6.262 |   0.7 |  29.1 |        |
| poverty_by_year_raw | nhiễu (–1) |   2015 |  27 | 10.53  |     9.3  |   8.312 |   0   |  31.5 |        |
| poverty_by_year_raw | cụm 1      |   2016 |   1 |  1.3   |     1.3  | nan     |   1.3 |   1.3 |        |
| poverty_by_year_raw | cụm 2      |   2016 |  50 |  8.54  |     6.7  |   6.674 |   0.5 |  27.9 |        |
| poverty_by_year_raw | nhiễu (–1) |   2016 |  11 |  5.6   |     4.3  |   4.543 |   0   |  12   |        |
| poverty_by_year_raw | cụm 2      |   2017 |  55 | 10.782 |     7.4  |  10.318 |   0.1 |  50.2 |        |
| poverty_by_year_raw | nhiễu (–1) |   2017 |   8 | 17.625 |    14.15 |  16.008 |   0.9 |  41.6 |        |
| poverty_by_year_raw | cụm 1      |   2018 |   1 |  1.4   |     1.4  | nan     |   1.4 |   1.4 |        |
| poverty_by_year_raw | cụm 2      |   2018 |  58 | 10.116 |     6.6  |  10.426 |   0.1 |  44.5 |        |
| poverty_by_year_raw | nhiễu (–1) |   2018 |   2 | 11.4   |    11.4  |   1.838 |  10.1 |  12.7 |        |
| poverty_by_year_raw | cụm 2      |   2019 |  56 |  8.409 |     5    |   9.13  |   0.1 |  39.9 |        |
| poverty_by_year_raw | nhiễu (–1) |   2019 |   7 |  9.429 |     8.4  |   9.22  |   0.8 |  29.1 |        |
| poverty_by_year_raw | cụm 2      |   2020 |  57 |  7.379 |     4.1  |   8.543 |   0   |  36.7 |        |
| poverty_by_year_raw | nhiễu (–1) |   2020 |   6 |  9.633 |     8.65 |   6.964 |   2.1 |  21.5 |        |
| poverty_by_year_raw | cụm 2      |   2021 |  53 |  7.625 |     4.7  |   8.276 |   0   |  34.5 |        |
| poverty_by_year_raw | nhiễu (–1) |   2021 |   7 |  4.071 |     3    |   3.782 |   0   |  10.7 |        |
| poverty_by_year_raw | cụm 2      |   2022 |  57 |  7.439 |     4.1  |   8.243 |   0   |  33.6 |        |
| poverty_by_year_raw | nhiễu (–1) |   2022 |   4 |  2.575 |     1.7  |   2.438 |   0.8 |   6.1 |        |
| poverty_by_year_raw | cụm 2      |   2023 |  52 |  6.46  |     3.8  |   7.538 |   0   |  29.5 |        |
| poverty_by_year_raw | nhiễu (–1) |   2023 |   9 |  2.367 |     1.7  |   2.112 |   0.1 |   6.1 |        |
| poverty_by_year_raw | cụm 2      |   2024 |  48 |  4.788 |     2.75 |   5.88  |   0   |  23.2 |        |
| poverty_by_year_raw | nhiễu (–1) |   2024 |  13 |  1.962 |     0.6  |   2.717 |   0.1 |  10.1 |        |

### 4d) Cỡ nhóm theo năm (n ô)

|   năm |   nhiễu (–1) |   cụm 0 |   cụm 1 |   cụm 2 |
|------:|-------------:|--------:|--------:|--------:|
|  2012 |           17 |       1 |       2 |      43 |
|  2013 |           16 |       0 |       4 |      43 |
|  2014 |           17 |       0 |       2 |      42 |
|  2015 |           27 |       1 |       0 |      35 |
|  2016 |           11 |       0 |       1 |      50 |
|  2017 |            8 |       0 |       0 |      55 |
|  2018 |            2 |       0 |       1 |      58 |
|  2019 |            7 |       0 |       0 |      56 |
|  2020 |            6 |       0 |       0 |      57 |
|  2021 |            7 |       0 |       0 |      53 |
|  2022 |            4 |       0 |       0 |      57 |
|  2023 |            9 |       0 |       0 |      52 |
|  2024 |           13 |       0 |       0 |      48 |

### 4e) Kruskal–Wallis từng năm — CHỈ mô tả, không phải kiểm định chính

|   year |   n | note                                                                                       |
|-------:|----:|:-------------------------------------------------------------------------------------------|
|   2012 |  63 | k = 4 nhóm, min n = 1; H = 3.1067; p = 0.375; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2013 |  63 | k = 3 nhóm, min n = 4; H = 2.3814; p = 0.304                                               |
|   2014 |  61 | k = 3 nhóm, min n = 2; H = 4.8289; p = 0.0894                                              |
|   2015 |  63 | k = 3 nhóm, min n = 1; H = 1.4569; p = 0.483; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2016 |  62 | k = 3 nhóm, min n = 1; H = 3.9493; p = 0.139; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2017 |  63 | k = 2 nhóm, min n = 8; H = 0.7881; p = 0.375; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2018 |  61 | k = 3 nhóm, min n = 1; H = 2.8373; p = 0.242; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2019 |  63 | k = 2 nhóm, min n = 7; H = 0.5054; p = 0.477; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2020 |  63 | k = 2 nhóm, min n = 6; H = 1.8778; p = 0.171; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2021 |  60 | k = 2 nhóm, min n = 7; H = 1.0506; p = 0.305; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2022 |  61 | k = 2 nhóm, min n = 4; H = 2.1229; p = 0.145; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả   |
|   2023 |  61 | k = 2 nhóm, min n = 9; H = 3.4654; p = 0.0627; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả  |
|   2024 |  61 | k = 2 nhóm, min n = 13; H = 5.5328; p = 0.0187; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả |

- Trừ median trong năm là HẰNG SỐ trong năm nên không đổi so sánh giữa cụm trong từng năm — thống kê theo năm chỉ cần trình bày trên giá trị thô.
- Năm 2013, 2014 có test ≥3 nhóm không suy biến; năm 2012, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024 suy biến (n<2 hoặc chỉ 2 nhóm — cụm 0/1 rỗng) → KW từng năm không phải bằng chứng độc lập.

## 5) Caveats

1. TP. Hồ Chí Minh 2016 (code 79) thiếu `poverty_rate_pct` phía nguồn (pxweb ghi `".."`) — dòng có trong CSV nhưng bị loại khỏi kiểm định vì NaN; KHÔNG nội suy (data/raw/gso/PROVENANCE.md:90).

2. Các năm 2006, 2008, 2010, 2025 có poverty nhưng KHÔNG có nhãn cụm (`predict_all_years.csv` chỉ phủ 2011–2024; 2025 còn là Sơ bộ) → loại khỏi mọi thống kê theo cụm.

3. Các năm 2011 KHÔNG có poverty: bảng pxweb V14.47 không có cột năm đó (data/raw/gso/PROVENANCE.md:25) → loại.

4. 13 ô tỉnh-năm trong cửa sổ giao có poverty nhưng không có nhãn (panel PAPI thiếu sd_4_2/sd_6_1): Bắc Giang 2014; Đồng Tháp 2014; Quảng Ninh 2018; Đồng Tháp 2018; Quảng Ninh 2021; Bắc Giang 2021; Bắc Ninh 2021; Bắc Giang 2022; Bắc Ninh 2022; Quảng Ninh 2023; Bình Dương 2023; Vĩnh Phúc 2024; Tiền Giang 2024 — mask tường minh, không vẽ không test.

5. Chuẩn nghèo ĐỔI theo giai đoạn (thu nhập 2011–2015 vs đa chiều từ ~2020 — data/raw/gso/PROVENANCE.md:48-58); các năm 2017–2019 điền thêm là ĐA CHIỀU theo footnote (*) của bảng Niên giám — cùng chuẩn với phần pxweb từ 2020, khớp 124/124 ở cột giao 2020/2021 (scripts/build_poverty_gap.py): so MỨC tuyệt đối xuyên năm không like-for-like; chỉ so GIỮA CỤM trong cùng một năm là hợp lệ — lý do bắt buộc phải có test đã-trừ-median-năm song song với test gộp.

6. KW gộp thô KHÔNG đáng kể (p = 0.198) trong khi đã-trừ-median-năm đáng kể (p = 0.000126): hai kết quả phải báo cáo cùng nhau; không được chọn trình bày một kết quả duy nhất (nguyên tắc trung thực của repo, build_report.py:628).

7. Cụm 0 (n=2) và cụm 1 (n=10) quá nhỏ để tự kết luận — cặp tương phản đáng tin duy nhất là nhiễu vs cụm 2; đọc eta²/ANOVA chỉ như mô tả.

8. KW theo từng năm không khả thi ở 2012/2015/2016 (nhóm n<2) và suy biến 2 nhóm ở 2020–2024 — chỉ dạng bảng mô tả, không làm kiểm định chính.

9. Tỷ trọng cụm trôi mạnh theo năm (nhiễu 17/63 năm 2012 → 2–27/63 trong các năm của cửa sổ) — test gộp phối trộn năm với cụm; limitation khai báo, không phải lỗi dữ liệu.

10. External check bằng thước đo độc lập (GSO thống kê chính thức, tách khỏi PAPI khảo sát hộ dân) — KHÔNG đưa vào feature, KHÔNG chứng minh nhân quả; poverty là kết quả thứ hai sau PCI nên đọc như kiểm chứng bổ trợ, không thay thế kiểm định chính PCI.

11. Hà Nội bao gồm Hà Tây từ 2008 (chú thích gốc bảng, data/raw/gso/PROVENANCE.md:48) — ngoài cửa sổ phân tích nhưng ghi trong provenance để tránh nhầm khi mở rộng cửa sổ.

## 6) Tái lập

```powershell
python -E scripts/poverty_validation.py
```
- Đầu vào: `data/processed/external_poverty_63.csv` + `results/predict_all_years.csv`.
- Đầu ra: `results/poverty_validation.md` (file này), `results/poverty_validation.csv`, `results/figs/external_poverty_by_cluster.png`.
- Determinism: chạy 2 lần — md/csv byte-giống (sha256); hình vẽ bằng rng seed 11.
- Provenance nguồn: `data/raw/gso/PROVENANCE.md` (tải 2026-11-07), `data/processed/external_provenance.md`; kiểm định chính PCI: `results/external_validation.md`.