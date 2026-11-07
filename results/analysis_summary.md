# Phân tích cuối kỳ — tóm tắt số liệu

## 1) STING theo từng năm (lưới thô 3×3, mc=3; trong-năm z)

|   year |   n |   k |   noise_ratio | cluster_sizes   |
|-------:|----:|----:|--------------:|:----------------|
|   2011 |  63 |   1 |         0.063 | [59]            |
|   2012 |  63 |   1 |         0     | [63]            |
|   2013 |  63 |   1 |         0.048 | [60]            |
|   2014 |  61 |   1 |         0.016 | [60]            |
|   2015 |  63 |   1 |         0.032 | [61]            |
|   2016 |  63 |   1 |         0.032 | [61]            |
|   2017 |  63 |   1 |         0.063 | [59]            |
|   2018 |  61 |   1 |         0.049 | [58]            |
|   2019 |  63 |   1 |         0.016 | [62]            |
|   2020 |  63 |   1 |         0.063 | [59]            |
|   2021 |  60 |   1 |         0.067 | [56]            |
|   2022 |  61 |   1 |         0.033 | [59]            |
|   2023 |  61 |   1 |         0     | [61]            |
|   2024 |  61 |   1 |         0.049 | [58]            |

## 2) Pooled 2011–2023 (frozen): STING vs baselines

| scope            | method         |   k |   noise_ratio |   silhouette |   davies_bouldin |   calinski_harabasz |   ari_vs_sting | note                                             |
|:-----------------|:---------------|----:|--------------:|-------------:|-----------------:|--------------------:|---------------:|:-------------------------------------------------|
| pooled 2011-2023 | STING (frozen) |   3 |         0.196 |        0.361 |            0.472 |                62   |        nan     | k=3: [629,16,5]; noise tách khỏi metric hình học |
| pooled 2011-2023 | k-means k=2    |   2 |         0     |        0.445 |            0.876 |               812.3 |          0.166 | tất cả điểm được gán cụm                         |
| pooled 2011-2023 | k-means k=3    |   3 |         0     |        0.336 |            1.05  |               665.7 |          0.139 | tất cả điểm được gán cụm                         |
| pooled 2011-2023 | k-means k=4    |   4 |         0     |        0.364 |            0.879 |               669.1 |          0.082 | tất cả điểm được gán cụm                         |
| pooled 2011-2023 | k-means k=5    |   5 |         0     |        0.334 |            0.945 |               647.9 |          0.07  | tất cả điểm được gán cụm                         |
| pooled 2011-2023 | DBSCAN eps=0.2 |   5 |         0.142 |        0.218 |            0.505 |                35.3 |          0.647 | nan                                              |
| pooled 2011-2023 | DBSCAN eps=0.4 |   1 |         0.027 |      nan     |          nan     |               nan   |          0.135 | metric n/a khi <2 cụm                            |
| pooled 2011-2023 | DBSCAN eps=0.6 |   1 |         0.009 |      nan     |          nan     |               nan   |          0.043 | metric n/a khi <2 cụm                            |
| pooled 2011-2023 | DBSCAN eps=0.8 |   1 |         0.002 |      nan     |          nan     |               nan   |          0.012 | metric n/a khi <2 cụm                            |
| pooled 2011-2023 | DBSCAN eps=1.0 |   1 |         0.001 |      nan     |          nan     |               nan   |          0.006 | metric n/a khi <2 cụm                            |

## 3) Robustness đa chỉ tiêu

| branch                                               |   n |   explained_var_total |   k |   noise_ratio | silhouette   | db   | ch   |   ari_vs_2d | verdict         |
|:-----------------------------------------------------|----:|----------------------:|----:|--------------:|:-------------|:-----|:-----|------------:|:----------------|
| PCA(2) d1–d6, within-year z, pooled                  | 869 |                 0.632 |   1 |         0.062 |              |      |      |       0.008 | không nhận diện |
| 8 chiều 2018–2024, within-year z, L=3 f=2 mc=10 lv=1 | 430 |               nan     |   3 |         0.605 |              |      |      |     nan     | không nhận diện |
| 8 chiều 2018–2024, within-year z, L=3 f=3 mc=2 lv=2  | 430 |               nan     |   1 |         0.995 |              |      |      |     nan     | không nhận diện |

## Ghi chú trung thực
- Dữ liệu PAPI cấp tỉnh/năm **rất đồng nhất**: STING per-year đa số cho 1 vùng dày; cấu trúc tách biệt chỉ xuất hiện ở hai cụm ngoại vi nhỏ (ví dụ cụm 16 và 5 điểm, tổng 21, trong pooled).
- Metric hình học tính trên điểm thuộc cụm (loại −1); khi k<2 metric = n/a.
- ARIt vs k-means thấp (≈0.07–0.17): hai phương pháp phân vùng khác nhau trên dữ liệu gần như một khối.
- STING ≈ DBSCAN(eps=0.2) đồng thuận hơn (ARI≈0.65) — cùng họ mật độ-lưới.
- 8 chiều chỉ 2018–2024: cấu trúc không nhận diện được (ghi nhận âm tính).