# Model local có giám sát (scikit-learn, huấn luyện hoàn toàn local)

## 1) Hồi quy — dự báo 6.1 Y tế công lập năm t+1 (bài toán chính)

- Đặc trưng: 8 chỉ số năm t (sub-dim sạch thang đo: sd_1_4, sd_4_1, sd_4_2, …)
- Hồi quy: chọn model bằng CV expanding origin 2017–2022 trên tập train; holdout 2023→2024 được tách khỏi bước chọn model. Phân loại: hai chỉ tiêu tạo nhãn và tham số STING do predict_sweep.py chọn bằng cách chấm coverage trên 2021–2022, có phần dữ liệu trùng với các fold CV cuối. Vì vậy CV phân loại là kết quả phục vụ lựa chọn và khám phá, chưa phải ước lượng tổng quát hóa độc lập.
- Train: 740 cặp (2011–2022) · Holdout: 59 cặp

| task       | model                               | metric_cv                       |   value_cv |   holdout_mae |   holdout_rmse |   holdout_r2 |   holdout_acc |   holdout_macro_f1 |
|:-----------|:------------------------------------|:--------------------------------|-----------:|--------------:|---------------:|-------------:|--------------:|-------------------:|
| regression | carry-forward (giữ giá trị năm nay) | r2 (expanding origin 2017–2022) |      0.145 |        0.0683 |         0.0875 |        0.198 |           nan |                nan |
| regression | trung bình train                    | r2 (expanding origin 2017–2022) |     -0.77  |        0.0814 |         0.1027 |       -0.105 |           nan |                nan |
| regression | ridge                               | r2 (expanding origin 2017–2022) |      0.265 |        0.064  |         0.0769 |        0.381 |           nan |                nan |
| regression | random forest                       | r2 (expanding origin 2017–2022) |      0.197 |        0.0616 |         0.0742 |        0.423 |           nan |                nan |

- Baseline hồi quy có CV thật trên cùng fold, không tranh selection: (CV: carry 0.145 vs ridge 0.265).

## 2) Phân loại — pseudo-label STING năm sau (bài toán phụ)

| task           | model                | metric_cv                             |   value_cv |   holdout_mae |   holdout_rmse |   holdout_r2 |   holdout_acc |   holdout_macro_f1 |
|:---------------|:---------------------|:--------------------------------------|-----------:|--------------:|---------------:|-------------:|--------------:|-------------------:|
| classification | majority (lớp đa số) | f1_macro (expanding origin 2017–2022) |      0.228 |           nan |            nan |          nan |         0.186 |              0.157 |
| classification | logistic regression  | f1_macro (expanding origin 2017–2022) |      0.434 |           nan |            nan |          nan |         0.644 |              0.541 |
| classification | random forest        | f1_macro (expanding origin 2017–2022) |      0.397 |           nan |            nan |          nan |         0.678 |              0.6   |

## Lưu ý trung thực
- Chọn hồi quy theo CV train-only (ridge, R²=0.265); trên holdout 2023→2024 MAE=0.0640 so với carry-forward 0.0683 (6.3% thấp hơn). RF có MAE holdout thấp hơn nhưng không được chọn vì R² CV thấp hơn; một holdout không chứng minh tổng quát hóa.
- Regression CV là expanding origin 2017–2022 với warm-up 2011–2016; holdout không được dùng để chọn mô hình.
- Chọn classifier theo forward CV (logistic regression, macro-F1=0.434; majority=0.228); so với baseline majority có chênh lệch holdout accuracy +45.8 điểm % và macro-F1 +38.4 điểm %; CV dùng expanding origins 2017–2022, warm-up origins 2011–2016. Đây là nhãn do STING fit tại từng cutoff sinh, không phải ground truth.
- Nhãn phân loại phụ thuộc allowlist + tham số STING do predict_sweep.py chọn bằng cách chấm coverage trên 2021–2022; các fold CV cuối dùng lại một phần dữ liệu này. Macro-F1 CV 0.434 có thể chịu thiên lệch lựa chọn; độ lớn thiên lệch chưa được đo.
- Prevalence nhãn 1 trôi mạnh theo năm: 0.000 (2011) → 0.917 (2021); trong mọi fold CV (2017–2022) lớp đa số train là 0 ở cả 6 fold; lớp 1 chiếm đa số ở 5/6 fold validation (prevalence 44%–92%). Biến động tỷ lệ nhãn ảnh hưởng đến so sánh với baseline đa số train; baseline mù thời gian “always dự đoán 1” đạt macro-F1 0.400 (chỉ thấp hơn LR 0.034).
- value_cv là best_score_ của GridSearchCV: hiệu năng CV trung bình của cấu hình được chọn trên chính các fold đó (không nested CV), nên có thể lạc quan. Chênh lệch điểm giữa các alpha Ridge {0.1, 1, 10} xấp xỉ 0.001 chỉ mô tả độ nhạy trong lưới thử, không đo được thiên lệch lựa chọn.
- REGRESSION_TARGET (sd_6_1) nằm trong REGRESSION_FEATURES (scripts/common/papi_pred_common.py:19-23): không leakage thời gian (target lấy từ năm t+1) nhưng lợi thế 6.3% so với carry-forward chủ yếu là thông tin lag-1 của chính target — bỏ sd_6_1 khỏi features, CV R² 0.265 → -0.264; corr(dự báo, carry-forward) holdout = 0.99.
- Một holdout 2023→2024 và pseudo-label không đủ để khẳng định năng lực dự báo xã hội tổng quát.
- Nạp lại dự báo không cần train lại:
  `import joblib; m = joblib.load('models/sup_ridge.joblib')` rồi truyền vector 8 chỉ số; classifier tương tự qua `models/sup_classifier.joblib` (logistic regression, nhãn 0/1).
