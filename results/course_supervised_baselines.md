# Baseline classifier theo nội dung học phần (pseudo-label STING)

## Quy trình
- Nhãn: STING fit tới cutoff năm *t* gán tỉnh năm *t+1* vào **vùng dày** (1) hay **ngoại vi** (0) — pseudo-label, không phải ground truth khảo sát.
- Đặc trưng: cùng 8 chỉ tiêu sub-dimension năm *t* như `scripts/predict_supervised.py`.
- Huấn luyện/CV: expanding origin 2017–2022, warm-up 2011–2016; scaler trong Pipeline, fit chỉ trên phần train từng fold.
- Holdout: một lần duy nhất cặp 2023→2024 (59 tỉnh); **không** dùng để chọn model.
- Chọn model theo macro-F1 CV (cột `value_cv`); so sánh với majority và logistic regression có sẵn trong repo.

## Kết quả

| model                | metric_cv                             |   value_cv |   holdout_acc |   holdout_macro_f1 |   cv_std |   cv_folds |
|:---------------------|:--------------------------------------|-----------:|--------------:|-------------------:|---------:|-----------:|
| majority (lớp đa số) | f1_macro (expanding origin 2017–2022) |      0.228 |         0.186 |              0.157 |    0.107 |          6 |
| gaussian naive bayes | f1_macro (expanding origin 2017–2022) |      0.514 |         0.746 |              0.566 |    0.12  |          6 |
| knn                  | f1_macro (expanding origin 2017–2022) |      0.486 |         0.593 |              0.534 |    0.066 |          6 |
| svm (linear)         | f1_macro (expanding origin 2017–2022) |      0.343 |         0.695 |              0.556 |    0.127 |          6 |
| svm (rbf)            | f1_macro (expanding origin 2017–2022) |      0.437 |         0.678 |              0.566 |    0.126 |          6 |
| decision tree        | f1_macro (expanding origin 2017–2022) |      0.426 |         0.559 |              0.508 |    0.091 |          6 |
| random forest        | f1_macro (expanding origin 2017–2022) |      0.394 |         0.627 |              0.56  |    0.07  |          6 |
| logistic regression  | f1_macro (expanding origin 2017–2022) |      0.434 |         0.644 |              0.541 |    0.056 |          6 |

- Theo **quy tắc chọn** của pipeline (macro-F1 CV cao nhất, không tính majority): **gaussian naive bayes** (macro-F1 CV = 0.514).
- Khoảng cách macro-F1 CV giữa hai model đầu bảng (0.028) nhỏ hơn độ lệch fold-to-fold của model dẫn đầu (`cv_std` = 0.120), nên thứ hạng chỉ mang tính mô tả, không khẳng định một model vượt trội.

## Hình
- **Hình:** `results/figs/course_confusion_matrix.png` — ma trận nhầm lẫn holdout cho từng classifier học phần.
- Đọc ma trận nhầm lẫn (bài Day 2–3): **hàng** = nhãn STING thực tế, **cột** = nhãn dự báo; ô trên đường chéo là dự đoán đúng.
- Cân bằng lớp holdout 2023→2024: lớp 0 = 11 tỉnh, lớp 1 = 48 tỉnh (baseline majority luôn dự báo lớp chiếm đa số).

## Cách đọc
- `value_cv`: macro-F1 trung bình trên các fold validation thời gian.
- `cv_std`: độ lệch chuẩn mẫu (ddof=1) của macro-F1 các fold cho cấu hình được CV chọn; `cv_folds`: số fold.
- `holdout_acc` / `holdout_macro_f1`: đánh giá một năm giữ lại; độ đồng thuận với nhãn STING, không khẳng định độ chính xác thực tế ngoài đời.

## Lưu ý
- Một holdout không chứng minh mô hình nào vượt trội tổng quát.
- Nhãn phụ thuộc cấu hình STING đóng băng trong `models/predict_config.json`.
- Train: 738 cặp · Holdout: 59 cặp.