# Độ nhạy tiền xử lý trên CV (tham khảo)

So sánh biến thể A (dropna như công bố), B (impute median trong Pipeline), C (winsorize z=3 theo fold-train) trên cùng fold expanding origin 2017–2022.

| task           | model                | variant   | metric_cv                             |   value_cv |   cv_std |   n_train_pairs |   delta_vs_A | verdict         |   holdout_value |
|:---------------|:---------------------|:----------|:--------------------------------------|-----------:|---------:|----------------:|-------------:|:----------------|----------------:|
| regression     | ridge                | A         | r2 (expanding origin 2017–2022)       |      0.265 |    0.13  |             740 |        0     | —               |           0.381 |
| regression     | ridge                | B         | r2 (expanding origin 2017–2022)       |      0.25  |    0.104 |             749 |       -0.015 | không khác biệt |           0.381 |
| regression     | ridge                | C         | r2 (expanding origin 2017–2022)       |      0.264 |    0.133 |             740 |       -0.001 | không khác biệt |           0.382 |
| classification | logistic regression  | A         | f1_macro (expanding origin 2017–2022) |      0.434 |    0.056 |             738 |        0     | —               |           0.541 |
| classification | logistic regression  | B         | f1_macro (expanding origin 2017–2022) |      0.434 |    0.058 |             745 |        0     | không khác biệt |           0.579 |
| classification | logistic regression  | C         | f1_macro (expanding origin 2017–2022) |      0.42  |    0.074 |             738 |       -0.014 | không khác biệt |           0.541 |
| classification | gaussian naive bayes | A         | f1_macro (expanding origin 2017–2022) |      0.514 |    0.12  |             738 |        0     | —               |           0.566 |
| classification | gaussian naive bayes | B         | f1_macro (expanding origin 2017–2022) |      0.512 |    0.127 |             745 |       -0.002 | không khác biệt |           0.585 |
| classification | gaussian naive bayes | C         | f1_macro (expanding origin 2017–2022) |      0.513 |    0.117 |             738 |       -0.001 | không khác biệt |           0.566 |

## Cách đọc
- `value_cv` / `cv_std`: metric CV và độ lệch fold-to-fold của cấu hình được chọn.
- `delta_vs_A` so với biến thể A; `verdict` mô tả: «không khác biệt» khi |delta| < cv_std của A, ngược lại «khác biệt đáng kể».
- `holdout_value`: R² holdout (hồi quy) hoặc macro-F1 holdout (phân loại); không dùng để chọn biến thể.

## Lưu ý (bốn điểm)
1. Phân tích **mang tính khám phá** — không thay `build_regression_pairs` / pipeline công bố đã đóng băng.
2. Nhãn phân loại do STING gán theo cutoff; **hai fold CV cuối** có thể chồng lấn thông tin với cùng bộ tham số STING đóng băng.
3. **Không có nested CV** — lưới siêu tham số và tiền xử lý được đánh giá trên cùng các fold expanding (giống script gốc).
4. Holdout 2023→2024 **không** tham gia chọn imputation hay winsorize; chỉ báo cáo minh họa.