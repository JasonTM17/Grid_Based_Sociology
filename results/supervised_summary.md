# Model local có giám sát (scikit-learn, huấn luyện hoàn toàn local)

## 1) Hồi quy — dự báo 6.1 Y tế công lập năm t+1 (bài toán chính)

- Đặc trưng: 8 chỉ số năm t (sub-dim sạch thang đo: sd_1_4, sd_4_1, sd_4_2, …)
- Chọn bài toán/đặc trưng/mô hình bằng CV train-only; holdout 2023→2024 đánh giá một lần.
- Train: 740 cặp (2011–2022) · Holdout: 59 cặp

| task       | model                               | metric_cv                |   value_cv |   holdout_mae |   holdout_rmse |   holdout_r2 |   holdout_acc |   holdout_macro_f1 |
|:-----------|:------------------------------------|:-------------------------|-----------:|--------------:|---------------:|-------------:|--------------:|-------------------:|
| regression | carry-forward (giữ giá trị năm nay) | r2 (GroupKFold theo năm) |    nan     |        0.0683 |         0.0875 |        0.198 |           nan |                nan |
| regression | trung bình train                    | r2 (GroupKFold theo năm) |    nan     |        0.0814 |         0.1027 |       -0.105 |           nan |                nan |
| regression | ridge                               | r2 (GroupKFold theo năm) |      0.451 |        0.064  |         0.0768 |        0.382 |           nan |                nan |
| regression | random forest                       | r2 (GroupKFold theo năm) |      0.432 |        0.0616 |         0.0742 |        0.423 |           nan |                nan |

## 2) Phân loại — pseudo-label STING năm sau (bài toán phụ)

| task           | model                | metric_cv                             |   value_cv |   holdout_mae |   holdout_rmse |   holdout_r2 |   holdout_acc |   holdout_macro_f1 |
|:---------------|:---------------------|:--------------------------------------|-----------:|--------------:|---------------:|-------------:|--------------:|-------------------:|
| classification | majority (lớp đa số) | f1_macro (expanding origin 2017–2022) |      0.228 |           nan |            nan |          nan |         0.186 |              0.157 |
| classification | logistic regression  | f1_macro (expanding origin 2017–2022) |      0.434 |           nan |            nan |          nan |         0.644 |              0.541 |
| classification | random forest        | f1_macro (expanding origin 2017–2022) |      0.397 |           nan |            nan |          nan |         0.678 |              0.6   |

## Lưu ý trung thực
- Chọn hồi quy theo CV train-only (ridge, R²=0.451); trên holdout 2023→2024 MAE=0.0640 so với carry-forward 0.0683 (6.3% thấp hơn). RF có MAE holdout thấp hơn nhưng không được chọn vì R² CV thấp hơn; một holdout không chứng minh tổng quát hóa.
- Regression CV là GroupKFold theo origin trong train, không phải backtest expanding; xem R² là điểm chọn mô hình trong train.
- Chọn classifier theo forward CV (logistic regression, macro-F1=0.434; majority=0.228); so với baseline majority có chênh lệch holdout accuracy +45.8 điểm % và macro-F1 +38.4 điểm %; CV dùng expanding origins 2017–2022, warm-up origins 2011–2016. Đây là nhãn do STING fit tại từng cutoff sinh, không phải ground truth.
- Một holdout 2023→2024 và pseudo-label không đủ để khẳng định năng lực dự báo xã hội tổng quát.
- Nạp lại dự báo không cần train lại:
  `import joblib; m = joblib.load('models/sup_ridge.joblib')` rồi truyền vector 8 chỉ số.
