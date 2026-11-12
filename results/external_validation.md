# External validation của cụm STING — PCI · y tế 2020 · GRDP · WDI

Sinh bởi `scripts/external_validation.py` (gaps [2], [8], [9] + phần GRDP của gap [3] — reports/external_data_expansion.md §4.2). Nhãn cụm lấy từ `results/predict_all_years.csv` (model đóng băng, refit tất định được gate bởi `tests/test_artifact_reproduction.py`); thống kê bằng scipy 1.16.3 (Python 3.14.2). Mọi số liệu tính lại trực tiếp từ CSV — không hardcode.

## 1) Kiểm định CHÍNH: PCI theo nhãn cụm trên lưới đầy 2011–2022

- PCI (`pci_weighted_score`, VCCI–USAID — khảo sát **doanh nghiệp**, tách hoàn toàn khỏi PAPI là khảo sát hộ dân của CECODES/UNDP) đủ 63 tỉnh × 12 năm = **756 ô**; join với nhãn cụm được **747 điểm** (9 ô có PCI nhưng panel thiếu sd_4_2/sd_6_1 nên không có nhãn: Quang Ninh 2018; Quang Ninh 2021; Bac Giang 2014; Bac Giang 2021; Bac Giang 2022; Bac Ninh 2021; Bac Ninh 2022; Dong Thap 2014; Dong Thap 2018).
- Không nội suy 66 ô PCI trống 2023–2024; không tự tính weighted score từ sub-index.

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |   max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|------:|
|             -1 | nhiễu (–1) | 149 | 59.798 |    59.16 | 5.037 | 45.12 | 75.09 |
|              0 | cụm 0      |   5 | 58.996 |    58.47 | 1.056 | 58.28 | 60.79 |
|              1 | cụm 1      |  16 | 58.78  |    58.19 | 3.802 | 51.58 | 64.77 |
|              2 | cụm 2      | 577 | 61.66  |    62.16 | 4.292 | 47.81 | 73.4  |

- **One-way ANOVA:** F(3,743) = 9.0426, p = 6.93e-06.
- **Kruskal–Wallis** (phi tham số, có sửa tie): H = 31.7751, p = 5.84e-07; eta² = 0.0352.
- Diễn giải thận trọng: cụm 0 (n=5) và cụm 1 (n=16) quá nhỏ để tự kết luận; cặp tương phản đáng tin là **nhiễu vs cụm 2**. PCI khác biệt có ý nghĩa thống kê giữa các nhóm → cấu trúc cụm STING tương ứng với một thước đo ĐỘC LẬP chưa từng dùng khi học — kiểm chứng bên ngoài độc lập, không chứng minh nhân quả.
- Hình: `results/figs/external_pci_by_cluster.png`.

## 2) Kiểm tra PHỤ: Top-30 2023–2024 — có cảnh báo chọn mẫu

- 2023–2024 nhà xuất bản chỉ công bố Top-30 tỉnh tốt: 60 ô có điểm (58 ô có nhãn). Trung bình mẫu bị kéo lên so với tổng thể (selection bias) → KHÔNG ghép với lưới đủ 63 tỉnh trong cùng một thống kê.
- Tập Top-30 hai năm KHÔNG cùng tập: 28 tỉnh chung; chỉ 2023 có Dak Nong, Tien Giang; chỉ 2024 có Ha Nam, Thai Binh.

|   pred_cluster | nhóm       |   n |   mean |   median |   std |   min |    max |
|---------------:|:-----------|----:|-------:|---------:|------:|------:|-------:|
|             -1 | nhiễu (–1) |  13 | 69.472 |   68.916 | 1.827 | 67.15 | 73.198 |
|              2 | cụm 2      |  45 | 69.016 |   68.996 | 1.448 | 66.79 | 74.835 |

- ANOVA F(1,56) = 0.8880, p = 0.35; Kruskal–Wallis H = 0.2261, p = 0.634 — chỉ đọc như kiểm tra phụ.

## 3) Mật độ cơ sở y tế/1.000 dân theo cụm — năm 2020 (ODM + GSO)

- **423** điểm y tế trên 97.58 triệu người (63 tỉnh, join point-in-polygon với ranh giới `data/raw/boundaries/diaphantinh.geojson`). Đếm thô không so được tỉnh khác quy mô → chuẩn hóa trên 1.000 dân.

| group      |   year |   n |     mean |   median |      std |   min |      max | note                                                                             |
|:-----------|-------:|----:|---------:|---------:|---------:|------:|---------:|:---------------------------------------------------------------------------------|
| nhiễu (–1) |   2020 |   6 | 0.00174  | 0.000748 | 0.002313 |     0 | 0.005625 | tổng 16 cơ sở / 6.19 triệu người → 0.002585 cơ sở/1.000 dân (theo quy mô nhóm)   |
| cụm 2      |   2020 |  57 | 0.003924 | 0.002203 | 0.005773 |     0 | 0.034658 | tổng 407 cơ sở / 91.39 triệu người → 0.004453 cơ sở/1.000 dân (theo quy mô nhóm) |

- **10 tỉnh `count = 0` là 0-thật** (nguồn điểm không phủ tỉnh đó, KHÔNG phải lỗi map tên — dump 2.169 điểm đã point-in-polygon với bộ alias tên tỉnh đã kiểm tra): Bắc Kạn, Tuyên Quang, Điện Biên, Lai Châu, Sơn La, Bắc Giang, Quảng Trị, Ninh Thuận, Bình Phước, Bến Tre.
- Snapshot một năm duy nhất (2020), đếm số ĐIỂM không phải số giường → chỉ dùng làm external check một lần, không đưa vào feature.
- Hình: `results/figs/external_health_density_2020.png`.

## 4) GRDP/người theo cụm — chỉ cửa sổ 2018–2024 (quyết định thiết kế)

- GRDP pxweb V03.12 chỉ phủ 2018–2024 (441 ô, 0 ô trống trong cửa sổ); **không nội suy 441 ô 2011–2017** (lỗ phía nguồn, gap [3]). Thiết kế chốt: GRDP chỉ dùng cửa sổ 2018–2024, dân số là normalizer chính xuyên panel.
- Join với nhãn cụm được **430/441 ô**; 11 ô trong cửa sổ thiếu nhãn (panel PAPI thiếu sd_4_2/sd_6_1) — mask tường minh, không vẽ: Quang Ninh 2018; Quang Ninh 2021; Quang Ninh 2023; Bac Giang 2021; Bac Giang 2022; Vinh Phuc 2024; Bac Ninh 2021; Bac Ninh 2022; Binh Duong 2023; Tien Giang 2024; Dong Thap 2018.
- Trong cửa sổ này gần như chỉ còn nhiễu vs cụm 2 (cụm 0 rỗng, cụm 1 còn ít điểm) — hình nói đúng điều dữ liệu cho phép.

| group      |   year |   n |   mean |   median |    std |    min |    max |
|:-----------|-------:|----:|-------:|---------:|-------:|-------:|-------:|
| nhiễu (–1) |   2018 |   2 |  61.08 |    61.08 |   9.41 |  54.42 |  67.73 |
| nhiễu (–1) |   2019 |   7 |  63.54 |    58.85 |  38.39 |  28.19 | 144.99 |
| nhiễu (–1) |   2020 |   6 |  68.64 |    53.12 |  43.47 |  41.06 | 155.6  |
| nhiễu (–1) |   2021 |   7 |  78.07 |    68.9  |  37.85 |  47.17 | 157.4  |
| nhiễu (–1) |   2022 |   4 | 171.4  |   129.11 | 148.43 |  55.31 | 372.1  |
| nhiễu (–1) |   2023 |   9 |  92.16 |    93.17 |  31.95 |  57.83 | 149.69 |
| nhiễu (–1) |   2024 |  13 | 128.38 |   103.52 |  81.25 |  65.58 | 338.97 |
| cụm 1      |   2018 |   1 | 104.42 |   104.42 |        | 104.42 | 104.42 |
| cụm 2      |   2018 |  58 |  60.36 |    48.14 |  42.53 |  26.07 | 309.62 |
| cụm 2      |   2019 |  56 |  67.21 |    53.75 |  42.83 |  32.14 | 300.38 |
| cụm 2      |   2020 |  57 |  68.83 |    57.72 |  37.97 |  29.8  | 251.16 |
| cụm 2      |   2021 |  53 |  69.57 |    57.5  |  41.34 |  30.76 | 297.64 |
| cụm 2      |   2022 |  57 |  75.56 |    67.67 |  30.98 |  33.76 | 171.57 |
| cụm 2      |   2023 |  52 |  83.05 |    71.75 |  47.19 |  34.69 | 338.98 |
| cụm 2      |   2024 |  48 |  87.23 |    80.97 |  33.71 |  37.82 | 206.2  |

- **2024 = Sơ bộ** (GSO pxweb, chưa chính thức — có thể được sửa sau); Hình: `results/figs/external_grdp_by_cluster.png`.

## 5) WDI — bối cảnh vĩ mô quốc gia (chuỗi không đều phía nguồn)

| group             |   n |     mean |   median |      min |      max | note                                                                        |
|:------------------|----:|---------:|---------:|---------:|---------:|:----------------------------------------------------------------------------|
| NY.GDP.PCAP.CD    |  15 | 3072.16  | 2956.11  | 1683.16  | 4716.66  | cửa sổ thật 2010–2024 (15/15 năm); phần thiếu là phía nguồn — không nội suy |
| SH.MED.BEDS.ZS    |   8 |    2.34  |    2.36  |    2.02  |    2.52  | cửa sổ thật 2010–2017 (8/15 năm); phần thiếu là phía nguồn — không nội suy  |
| SH.XPD.CHEX.GD.ZS |  14 |    4.764 |    4.791 |    4.332 |    5.071 | cửa sổ thật 2010–2023 (14/15 năm); phần thiếu là phía nguồn — không nội suy |
| SP.URB.TOTL.IN.ZS |  15 |   33.94  |   33.363 |   30.25  |   38.49  | cửa sổ thật 2010–2024 (15/15 năm); phần thiếu là phía nguồn — không nội suy |

- `SH.MED.BEDS.ZS` (giường bệnh) dừng 2017 và `SH.XPD.CHEX.GD.ZS` (chi y tế) thiếu 2024 — truncate là phía nguồn; giữ ô trống, không nội suy.
- Cấp QUỐC GIA: dùng làm bối cảnh/year effects, không phải feature cấp tỉnh (giá trị giống nhau cho mọi tỉnh trong cùng một năm).
- Hình: `results/figs/external_wdi_panel.png`.

## 6) Tái lập

```powershell
python -E scripts/external_validation.py
```
- Đầu vào: `data/processed/external_{pci_63_full,gso_population_63_full,gso_grdp_63,odm_health_63,worldbank_vnm}.csv` + `results/predict_all_years.csv`.
- Đầu ra: `results/external_validation.md` (file này), `results/external_validation.csv`, 4 hình trong `results/figs/external_*`.
- Provenance nguồn: `data/processed/external_provenance.md`, `data/raw/*/PROVENANCE.md`.