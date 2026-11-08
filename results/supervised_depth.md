# Chẩn đoán chuyên sâu phần supervised — chỉ mô tả, không chọn model

- Script: `scripts/supervised_depth.py`, tái dùng pipeline `scripts/predict_supervised.py` (`build_regression_pairs` :99, `expanding_origin_folds` :123, `build_classification_pairs` :187, spec model :276-285 và :342-348; hằng số `scripts/papi_pred_common.py:15-23`).
- Provenance (sha256 12 ký tự đầu): panel `papi_panel_63_2011_2024.csv` `87404305f36b` · config `predict_config.json` `9d8fa43aeb9f` (chỉ đọc) · dân số `external_gso_population_63_full.csv` `66dde17c97df`.
- Seed: model giữ seed 42 của pipeline; permutation importance dùng seed 11, n_repeats=30 (theo yêu cầu lane). Mọi số tự tính trong bộ nhớ từ CSV provenance.
- Siêu tham số CỐ ĐỊNH (chọn một lần bởi CV train-only expanding origin 2017–2022 của pipeline, tính lại trong bộ nhớ): Ridge alpha=0.1, LogisticRegression C=1, RF max_depth=4, min_samples_leaf=2. Không chọn lại theo từng cửa sổ, không dựa vào holdout.
- Kiểm đối pipeline: tái tính trong bộ nhớ cho ridge CV R²=0.265 / holdout MAE=0.0640 và RF CV R²=0.197 — KHỚP results/supervised_metrics.csv (công bố: 0.265 / 0.064 / 0.197).

## 1) Learning curve expanding origin 2016→2022 (không đụng holdout)

Mỗi điểm = train trên mọi cặp `year_t < v` rồi chấm trên đúng origin `v` (cùng kiểu fold với `expanding_origin_folds` của pipeline, chỉ dịch gốc lên 2016). Trục x là số năm train (origin years 2011–v−1); fold đầu warm-up 2011–2015.

### Ridge hồi quy — R²

| Origin v | Số năm train | n cặp train | n cặp validation | R² |
|:--|--:|--:|--:|--:|
| 2016 | 5 | 311 | 63 | 0.4588 |
| 2017 | 6 | 374 | 63 | 0.1978 |
| 2018 | 7 | 437 | 61 | 0.1733 |
| 2019 | 8 | 498 | 63 | 0.3198 |
| 2020 | 9 | 561 | 60 | 0.0998 |
| 2021 | 10 | 621 | 60 | 0.4515 |
| 2022 | 11 | 681 | 59 | 0.3488 |

### LogisticRegression — macro-F1 (nhãn pseudo-label STING, cấu hình đóng băng)

| Origin v | Số năm train | n cặp train | n cặp validation | macro-F1 |
|:--|--:|--:|--:|--:|
| 2016 | 5 | 311 | 63 | 0.3942 |
| 2017 | 6 | 374 | 61 | 0.3389 |
| 2018 | 7 | 435 | 61 | 0.4089 |
| 2019 | 8 | 496 | 63 | 0.4569 |
| 2020 | 9 | 559 | 60 | 0.4309 |
| 2021 | 10 | 619 | 60 | 0.4725 |
| 2022 | 11 | 679 | 59 | 0.4968 |

- Hình: `results/figs/supervised_learning_curve.png`.

## 2) Permutation importance — RF hồi quy (seed 11, n_repeats=30)

`permutation_importance` (scoring R²) của RF spec pipeline, xếp hạng theo mean giảm dần; khoảng biến thiên = [min, max] trên các lần hoán vị. Bảng train là in-sample; bảng holdout chỉ mô tả ngoài mẫu — KHÔNG dùng để chọn gì.

### Trên train 2011–2022 (in-sample)

| Hạng | Đặc trưng | mean | sd | [min, max] |
|:--|--:|--:|--:|--:|
| 1 | `sd_6_1` 6.1 Y tế công lập | 0.9928 | 0.0450 | [0.8951, 1.1092] |
| 2 | `sd_1_4` 1.4 Đóng góp tự nguyện | 0.0305 | 0.0024 | [0.0249, 0.0347] |
| 3 | `sd_1_3` 1.3 Chất lượng bầu cử | 0.0241 | 0.0019 | [0.0211, 0.0280] |
| 4 | `sd_4_3` 4.3 Công bằng trong tuyển dụng vào khu vực công | 0.0184 | 0.0024 | [0.0118, 0.0227] |
| 5 | `sd_6_3` 6.3 Cơ sở hạ tầng căn bản | 0.0176 | 0.0021 | [0.0137, 0.0216] |
| 6 | `sd_4_4` 4.4 Quyết tâm chống tham nhũng của chính quyền địa phương | 0.0095 | 0.0013 | [0.0066, 0.0118] |
| 7 | `sd_4_2` 4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công | 0.0094 | 0.0011 | [0.0073, 0.0112] |
| 8 | `sd_4_1` 4.1 Kiểm soát tham nhũng trong chính quyền địa phương | 0.0058 | 0.0009 | [0.0039, 0.0077] |

### Trên holdout 2023→2024

| Hạng | Đặc trưng | mean | sd | [min, max] |
|:--|--:|--:|--:|--:|
| 1 | `sd_6_1` 6.1 Y tế công lập | 1.0063 | 0.1513 | [0.7407, 1.2962] |
| 2 | `sd_1_3` 1.3 Chất lượng bầu cử | 0.0309 | 0.0140 | [-0.0048, 0.0581] |
| 3 | `sd_1_4` 1.4 Đóng góp tự nguyện | 0.0199 | 0.0099 | [-0.0021, 0.0396] |
| 4 | `sd_6_3` 6.3 Cơ sở hạ tầng căn bản | 0.0058 | 0.0027 | [0.0004, 0.0106] |
| 5 | `sd_4_4` 4.4 Quyết tâm chống tham nhũng của chính quyền địa phương | 0.0012 | 0.0037 | [-0.0078, 0.0068] |
| 6 | `sd_4_1` 4.1 Kiểm soát tham nhũng trong chính quyền địa phương | -0.0010 | 0.0041 | [-0.0094, 0.0088] |
| 7 | `sd_4_2` 4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công | -0.0014 | 0.0037 | [-0.0092, 0.0052] |
| 8 | `sd_4_3` 4.3 Công bằng trong tuyển dụng vào khu vực công | -0.0158 | 0.0092 | [-0.0325, 0.0051] |

- Hình: `results/figs/supervised_importance.png`.

## 3) Residual diagnostics — Ridge trên holdout 2023→2024 (mô tả, không sửa dữ liệu)

- Holdout 59 cặp (origin 2023 → đích 2024): residual mean 0.0304, median 0.0342, sd 0.0712, min -0.1086, max 0.1938, MAE 0.0640 (residual = thực tế − dự báo).

### 3a) Residual theo năm

Holdout chỉ có MỘT origin year (2023) nên 'theo năm' trên holdout suy biến thành một nhóm. Bổ sung bảng out-of-sample theo năm từ chính các cửa sổ learning curve (Ridge refit trên year_t < v) để thấy trôi theo thời gian — tất cả chỉ mô tả.

| Origin | Nguồn | n cặp | resid mean | resid median | resid sd | mean abs resid |
|:--|--:|--:|--:|--:|--:|--:|
| 2023 | holdout (Ridge fit 2011–2022) | 59 | 0.0304 | 0.0342 | 0.0712 | 0.0640 |
| 2016 | cửa sổ expanding (refit < o) | 63 | 0.0274 | 0.0317 | 0.0658 | 0.0575 |
| 2017 | cửa sổ expanding (refit < o) | 63 | 0.0329 | 0.0163 | 0.0802 | 0.0654 |
| 2018 | cửa sổ expanding (refit < o) | 61 | 0.0421 | 0.0520 | 0.0737 | 0.0684 |
| 2019 | cửa sổ expanding (refit < o) | 63 | -0.0043 | 0.0087 | 0.0779 | 0.0617 |
| 2020 | cửa sổ expanding (refit < o) | 60 | -0.0215 | -0.0214 | 0.1012 | 0.0819 |
| 2021 | cửa sổ expanding (refit < o) | 60 | -0.0217 | -0.0348 | 0.0613 | 0.0525 |
| 2022 | cửa sổ expanding (refit < o) | 59 | -0.0249 | -0.0369 | 0.0844 | 0.0730 |

### 3b) Residual theo tỉnh lớn/nhỏ (median dân số GSO năm origin 2023)

Median dân số 2023 (của chính 59 tỉnh holdout) = 1248.11 nghìn người (`external_gso_population_63_full.csv`, cột `gso_pop_total_thousand`); nhóm 'lớn' = ≥ median này, 'nhỏ' = < median.

| Nhóm | n tỉnh | median dân số (nghìn) | resid mean | resid median | resid sd | mean abs resid |
|:--|--:|--:|--:|--:|--:|--:|
| lớn | 30 | 1607.08 | 0.0219 | 0.0255 | 0.0638 | 0.0538 |
| nhỏ | 29 | 880.47 | 0.0393 | 0.0521 | 0.0783 | 0.0746 |

### 3c) Top-5 tỉnh lệch nhất theo |residual| (holdout)

| Hạng | Tỉnh | Dân số 2023 (nghìn) | Nhóm | Thực tế 2024 | Dự báo | Residual |
|:--|--:|--:|--:|--:|--:|--:|
| 1 | Tây Ninh | 1194.9 | nhỏ | 1.9245 | 1.7306 | 0.1938 |
| 2 | Bình Thuận | 1258.8 | lớn | 2.1117 | 1.9386 | 0.1730 |
| 3 | Đắk Nông | 682.0 | nhỏ | 2.0266 | 1.8745 | 0.1521 |
| 4 | Phú Yên | 877.7 | nhỏ | 2.0165 | 1.8818 | 0.1347 |
| 5 | Hà Tĩnh | 1323.8 | lớn | 2.1914 | 2.0767 | 0.1147 |

## Phạm vi & trung thực

- KHÔNG chọn gì trên holdout 2023→2024: không chọn model, không chọn siêu tham số, không chọn đặc trưng; holdout chỉ xuất hiện ở mục 2/3 với vai trò mô tả.
- Caveat: siêu tham số cố định được chọn bằng CV 2017–2022 của pipeline nên với cửa sổ learning curve có origin sớm (2016–2017) thông tin đó nằm trong tương lai của cửa sổ — đây là đặc tả model đã công bố, không phải quy trình chọn lại.
- Holdout chỉ 1 năm → mọi kết luận residual ngoài mẫu chỉ mô tả cho (2023→2024), không khái quát; bảng 3a mở rộng chỉ là mô tả trên các năm CV.
- Permutation importance trên train là in-sample; trên holdout chỉ 59 cặp nên khoảng biến thiên rộng.
- Script này KHÔNG ghi `models/*`, KHÔNG chạy `scripts/predict_sweep.py`, KHÔNG sửa dữ liệu, KHÔNG ghi đè artifact đã công bố — chỉ thêm 4 file: `supervised_depth.md`, `supervised_depth.csv`, `supervised_learning_curve.png`, `supervised_importance.png`.
- Kiểm đối tái lập: ĐẠT — tái tính trong bộ nhớ cho ridge CV R²=0.265 / holdout MAE=0.0640 và RF CV R²=0.197 — KHỚP results/supervised_metrics.csv (công bố: 0.265 / 0.064 / 0.197).
