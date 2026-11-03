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

## 2) Phân loại — trạng thái cấu trúc năm sau (bài toán phụ, KẾT QUẢ ÂM TÍNH)

| task           | model                | metric_cv                      |   value_cv |   holdout_mae |   holdout_rmse |   holdout_r2 |   holdout_acc |   holdout_macro_f1 |
|:---------------|:---------------------|:-------------------------------|-----------:|--------------:|---------------:|-------------:|--------------:|-------------------:|
| classification | majority (lớp đa số) | f1_macro (GroupKFold theo năm) |    nan     |           nan |            nan |          nan |         0.814 |              0.449 |
| classification | logistic regression  | f1_macro (GroupKFold theo năm) |      0.525 |           nan |            nan |          nan |         0.814 |              0.449 |
| classification | random forest        | f1_macro (GroupKFold theo năm) |      0.589 |           nan |            nan |          nan |         0.831 |              0.536 |

## Lưu ý trung thực
- Hồi quy có tín hiệu thật: mô hình tốt nhất giảm ~10% MAE so với baseline carry-forward (giữ nguyên giá trị năm nay) trên holdout — nhưng vẫn là một holdout duy nhất.
- Phân loại trạng thái ngoại vi chỉ nhích nhẹ so với baseline lớp đa số (≤~2 điểm phần trăm) — không đủ cơ sở kết luận có tín hiệu thật; giữ lại làm bằng chứng trung thực.
- Nhãn phân loại do STING sinh (model không giám sát) → sai số lan truyền, đã khai báo.
- Nạp lại dự báo không cần train lại:
  `import joblib; m = joblib.load('models/sup_ridge.joblib')` rồi truyền vector 8 chỉ số.
