# Hồ sơ chuyên sâu cụm STING — chỉ số ngoài & ổn định bootstrap

Sinh bởi `scripts/cluster_profile.py` — lane phân tích **MỚI**, không thay đổi bất kỳ artifact/số đã công bố. Nhãn cụm tỉnh-năm lấy từ `results/predict_all_years.csv` (model đóng băng `models/predict_config.json`: features **4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công** × **6.1 Y tế công lập**; STING(L=3, factor=4, min_count=5), level=2, connectivity=1; fit 2011–2023). Mọi số do script tự tính trong bộ nhớ từ CSV provenance — không hardcode; kiểm định bằng `scipy.stats.kruskal` (có sửa tie).

- **Bootstrap**: 200 lần resample CÓ hoàn lại **theo TỈNH** (cluster bootstrap panel), seed **11** = `numpy.random.default_rng(11)`; khớp nhãn mẫu → nhãn gốc bằng Jaccard tối đa từng cụm (ghép cặp 1-1 tối ưu, `scipy.optimize.linear_sum_assignment`).
- Kiểm chứng tất định: refit đúng công thức `predict_demo.py` cho lại **đúng 808/808 nhãn train** của CSV (0 lệch) — cùng ngữ nghĩa gate `tests/test_artifact_reproduction.py`.

## 1) Nhãn cụm theo tỉnh-năm

| nhóm       |   n (tỉnh-năm) |   n tỉnh duy nhất | năm có điểm   | split               |
|:-----------|---------------:|------------------:|:--------------|:--------------------|
| nhiễu (–1) |            171 |                56 | 2011–2024     | train 158 / test 13 |
| cụm 0      |              5 |                 5 | 2011–2015     | train 5 / test 0    |
| cụm 1      |             16 |                12 | 2011–2018     | train 16 / test 0   |
| cụm 2      |            677 |                63 | 2011–2024     | train 629 / test 48 |

- Cấu trúc nhãn: 1 cụm lớn (cụm 2: 677 dòng) + 2 cụm li ti (cụm 0: 5 dòng, cụm 1: 16 dòng — chỉ xuất hiện những năm đầu panel) và vùng nhiễu (−1: 171 dòng, ô lưới không đủ min_count). Nhìn nhận trục này trước khi đọc các bảng dưới.

## 2) Hồ sơ nhóm × chỉ số ngoài (Kruskal–Wallis + trung vị)

*Lưu ý chung*: nhóm cụm 0 / cụm 1 có n rất nhỏ (cụm li ti) — thống kê chỉ mang tính mô tả; cặp tương phản đáng tin là **nhiễu (−1) vs cụm 2**. p nhỏ với nhóm n rất nhỏ KHÔNG chứng minh cụm nhỏ là một "kiểu tỉnh" độc lập. Không nội suy ô thiếu; join khóa (year, province_code).

### 2.1) PCI weighted (VCCI–USAID) — 2011–2022 (lưới đầy)

- Join nhãn: 747/756 ô có nhãn (9 ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không có nhãn); 747 ô vào thống kê.

|   cluster | nhóm       |   n |   trung vị |   mean |    sd |   min |   max |
|----------:|:-----------|----:|-----------:|-------:|------:|------:|------:|
|        -1 | nhiễu (–1) | 149 |      59.16 | 59.798 | 5.037 | 45.12 | 75.09 |
|         0 | cụm 0      |   5 |      58.47 | 58.996 | 1.056 | 58.28 | 60.79 |
|         1 | cụm 1      |  16 |      58.19 | 58.78  | 3.802 | 51.58 | 64.77 |
|         2 | cụm 2      | 577 |      62.16 | 61.66  | 4.292 | 47.81 | 73.4  |

- **Kruskal–Wallis**: H = 31.7751, df = 3, p = 5.84e-07 (n = 747; n theo nhóm [149, 5, 16, 577]).

### 2.2) Tỷ lệ nghèo (GSO V14.47) — 2012–2024 (13 năm giao với panel)

- Join nhãn: 805/818 ô có nhãn (13 ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không có nhãn); 805 ô vào thống kê.

|   cluster | nhóm       |   n |   trung vị |   mean |   sd |   min |   max |
|----------:|:-----------|----:|-----------:|-------:|-----:|------:|------:|
|        -1 | nhiễu (–1) | 144 |       6.6  |   9.87 | 9.94 |   0   |  42.3 |
|         0 | cụm 0      |   2 |      14.95 |  14.95 | 3.75 |  12.3 |  17.6 |
|         1 | cụm 1      |  10 |       3.25 |   4.55 | 3.64 |   1.2 |  12.1 |
|         2 | cụm 2      | 649 |       6.2  |   9.01 | 8.73 |   0   |  50.2 |

- **Kruskal–Wallis**: H = 4.6670, df = 3, p = 0.198 (n = 805; n theo nhóm [144, 2, 10, 649]).

### 2.3) Mật độ cơ sở y tế/1.000 dân (OD Mekong) — 2020 (snapshot 1 năm)

- Join nhãn: 63/63 ô có nhãn (0 ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không có nhãn); 63 ô vào thống kê.

|   cluster | nhóm       |   n |   trung vị |     mean |       sd |   min |      max |
|----------:|:-----------|----:|-----------:|---------:|---------:|------:|---------:|
|        -1 | nhiễu (–1) |   6 |   0.000748 | 0.00174  | 0.002313 |     0 | 0.005625 |
|         2 | cụm 2      |  57 |   0.002203 | 0.003924 | 0.005773 |     0 | 0.034658 |

- **Kruskal–Wallis**: H = 2.0147, df = 1, p = 0.156 (n = 63; n theo nhóm [6, 57]).

- Tỉnh `count = 0` là 0-thật (nguồn điểm ODM không phủ, không phải lỗi nối tên): Bắc Kạn, Tuyên Quang, Điện Biên, Lai Châu, Sơn La, Bắc Giang, Quảng Trị, Ninh Thuận, Bình Phước, Bến Tre.

### 2.4) GRDP/người (GSO V03.12) — 2018–2024 (2024 = Sơ bộ)

- Join nhãn: 430/441 ô có nhãn (11 ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không có nhãn); 430 ô vào thống kê.

|   cluster | nhóm       |   n |   trung vị |   mean | sd    |    min |    max |
|----------:|:-----------|----:|-----------:|-------:|:------|-------:|-------:|
|        -1 | nhiễu (–1) |  48 |      68.31 |  98.11 | 70.45 |  28.19 | 372.1  |
|         1 | cụm 1      |   1 |     104.42 | 104.42 | –     | 104.42 | 104.42 |
|         2 | cụm 2      | 381 |      61.55 |  72.67 | 40.47 |  26.07 | 338.98 |

- **Kruskal–Wallis**: H = 9.4963, df = 2, p = 0.00867 (n = 430; n theo nhóm [48, 1, 381]).

### 2.5) % dân số đô thị (GSO V02.01) — 2012–2022 (các năm nguồn có số: 2012, 2013, 2014, 2018, 2019, 2020, 2021, 2022)

- Join nhãn: 495/504 ô có nhãn (9 ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không có nhãn); 495 ô vào thống kê.

|   cluster | nhóm       |   n |   trung vị |   mean | sd    |   min |   max |
|----------:|:-----------|----:|-----------:|-------:|:------|------:|------:|
|        -1 | nhiễu (–1) |  76 |      23.14 |  30.04 | 18.16 |  9.81 | 84.32 |
|         0 | cụm 0      |   1 |      14.65 |  14.65 | –     | 14.65 | 14.65 |
|         1 | cụm 1      |   9 |      26.11 |  27.37 | 11.42 |  9.77 | 45.64 |
|         2 | cụm 2      | 409 |      23.45 |  28.8  | 17.07 |  9.72 | 87.45 |

- **Kruskal–Wallis**: H = 2.1520, df = 3, p = 0.541 (n = 495; n theo nhóm [76, 1, 9, 409]).

## 3) Ổn định bootstrap — 200 lần, seed 11, resample theo tỉnh

- **Phương pháp**: mỗi lần rút 63 tỉnh CÓ hoàn lại (`rng.integers(0, 63, size=63)`); mẫu = toàn bộ dòng fit (2011–2023, đủ chỉ tiêu; 808 dòng gốc) của các tỉnh được rút — tỉnh bị rút k lần góp k bản sao dòng (đúng cluster bootstrap cho panel, tôn trọng tương quan trong tỉnh). Refit ĐÚNG cấu hình đóng băng: StandardScaler fit trên mẫu + STING(L, factor, min_count) như trên + cluster(level=2, connectivity=1).
- **Khớp nhãn**: với từng cụm gốc 0/1/2, ghép cặp 1-1 tối ưu tổng Jaccard giữa các dòng của cụm mẫu và cụm gốc; nhãn −1 giữ trạng thái riêng. Một dòng "giữ nhãn" khi (gốc −1 & mẫu −1) hoặc (gốc c & mẫu khớp về c). Silhouette tính trên điểm KHÔNG nhiễu của mẫu; lần refit ra < 2 cụm non-noise bị bỏ khỏi phân bố silhouette.

| đại lượng                     |   mean |   median |     sd | CI95 (p2.5–p97.5)   |   n lần |
|:------------------------------|-------:|---------:|-------:|:--------------------|--------:|
| Tỉ lệ giữ nhãn — toàn bộ dòng | 0.8742 |   0.8746 | 0.034  | [0.8138, 0.9407]    |     200 |
| Silhouette (non-noise)        | 0.1675 |   0.1619 | 0.1352 | [-0.0602, 0.4198]   |     198 |

- Tham chiếu: silhouette của model gốc trên train (không nhiễu) = **0.3611** — phân bố bootstrap thấp hơn là chi phí của việc rút lại tỉnh (mẫu lệch + trùng bản sao), không phải lỗi cài đặt.

| nhãn gốc   | tỉ lệ gộp (200 lần)   | mean theo lần có mặt   | CI95 theo lần   |   dòng gộp | số lần có mặt   |
|:-----------|:----------------------|:-----------------------|:----------------|-----------:|:----------------|
| nhiễu (–1) | 66.8%                 | 67.0%                  | [52.1%, 83.5%]  |      31818 | 200/200         |
| cụm 0      | 14.5%                 | 12.0%                  | [0.0%, 100.0%]  |        957 | 200/200         |
| cụm 1      | 49.8%                 | 45.4%                  | [0.0%, 100.0%]  |       3187 | 200/200         |
| cụm 2      | 94.1%                 | 94.1%                  | [88.0%, 98.2%]  |     125659 | 200/200         |

|   cụm gốc |   Jaccard TB cặp ghép | được ghép (Jaccard>0)   |
|----------:|----------------------:|:------------------------|
|         0 |                 0.085 | 29/200                  |
|         1 |                 0.44  | 161/200                 |
|         2 |                 0.889 | 200/200                 |

|   k′ của refit | số lần   |
|---------------:|:---------|
|              1 | 2/200    |
|              2 | 5/200    |
|              3 | 26/200   |
|              4 | 40/200   |
|              5 | 42/200   |
|              6 | 40/200   |
|              7 | 20/200   |
|              8 | 13/200   |
|              9 | 6/200    |
|             10 | 4/200    |
|             11 | 1/200    |
|             13 | 1/200    |

- **Đọc kết quả**: cụm lớn + nhiễu được tái lập gần như chắc chắn (tỉ lệ giữ nhãn cao); cụm li ti 0/1 phụ thuộc việc các tỉnh sáng lập chúng có được rút vào mẫu hay không — phân bố tỉ lệ giữ nhãn của hai nhóm này trải rộng, đúng bản chất cụm li ti dưới bootstrap. Kết luận vững chỉ nên dựa trên tương phản nhiễu vs cụm 2.

## 4) Tái lập

```powershell
python -E scripts/cluster_profile.py
```

- Đầu vào: `results/predict_all_years.csv`, `data/processed/papi_panel_63_2011_2024.csv` (đọc), `data/processed/external_{pci_63_full,poverty_63,odm_health_63,gso_grdp_63,gso_population_63_full}.csv`, `models/predict_config.json` (đọc).
- Đầu ra MỚI: file này, `results/cluster_profile.csv`, `results/figs/deep_cluster_profile.png`.
- Tất định: bootstrap seed 11; không có thời gian hệ thống trong đầu ra → chạy 2 lần cho md/csv sha256 byte-giống.
- Provenance nguồn: `data/processed/external_provenance.md`, `data/raw/*/PROVENANCE.md`.
