# Baseline nhãn hoán vị và drift thời gian (classifier pseudo-label)

## Phương pháp
- CV: expanding origin 2017–2022, warm-up 2011–2016; giống `scripts/course_supervised_baselines.py`.
- Hoán vị nhãn: 200 lần, seed gốc 42; chỉ hoán vị nhãn **train** từng fold; fit bằng **fixed_best_params** (Pipeline/ siêu tham số từ GridSearchCV đã công bố, không chạy lại lưới).
- Baseline thời gian: chỉ `year_t` hoặc chỉ prevalence nhãn 1 năm *t−1*.
- Holdout 2023→2024 **không** dùng cho bất kỳ lựa chọn nào trong script này.

## Kết quả chính (CV macro-F1)

| model                | analysis     | comparator   | feature_set   | fold_year   | metric   |    value | n_permutations   | permutation_fit   |
|:---------------------|:-------------|:-------------|:--------------|:------------|:---------|---------:|:-----------------|:------------------|
| gaussian naive bayes | published_cv |              |               |             | value_cv | 0.514368 |                  |                   |
| knn                  | published_cv |              |               |             | value_cv | 0.48589  |                  |                   |
| logistic regression  | published_cv |              |               |             | value_cv | 0.434155 |                  |                   |

### Hoán vị nhãn train

| model                |   empirical_p |   observed_cv |   perm_mean_macro_f1 |   perm_p95_macro_f1 |
|:---------------------|--------------:|--------------:|---------------------:|--------------------:|
| gaussian naive bayes |      0.004975 |      0.514368 |             0.251048 |            0.293629 |
| knn                  |      0.004975 |      0.48589  |             0.34346  |            0.38216  |
| logistic regression  |      0.004975 |      0.434155 |             0.228974 |            0.233905 |

### Chỉ đặc trưng thời gian / prevalence

| analysis   | model                | comparator   | feature_set          | fold_year   | metric   |    value | n_permutations   | permutation_fit   |
|:-----------|:---------------------|:-------------|:---------------------|:------------|:---------|---------:|:-----------------|:------------------|
| year_only  | gaussian naive bayes |              | year_t               |             | value_cv | 0.391589 |                  |                   |
| year_only  | knn                  |              | year_t               |             | value_cv | 0.378611 |                  |                   |
| year_only  | logistic regression  |              | year_t               |             | value_cv | 0.400102 |                  |                   |
| year_only  | gaussian naive bayes |              | prev_year_prevalence |             | value_cv | 0.400102 |                  |                   |
| year_only  | knn                  |              | prev_year_prevalence |             | value_cv | 0.391589 |                  |                   |
| year_only  | logistic regression  |              | prev_year_prevalence |             | value_cv | 0.387124 |                  |                   |

### So sánh cặp theo fold: Naive Bayes trừ model khác

| analysis   | model                | comparator          | feature_set   | fold_year   | metric           |    value | n_permutations   | permutation_fit   |
|:-----------|:---------------------|:--------------------|:--------------|:------------|:-----------------|---------:|:-----------------|:------------------|
| paired_nb  | gaussian naive bayes | knn                 |               |             | nb_wins          | 4        |                  |                   |
| paired_nb  | gaussian naive bayes | knn                 |               |             | mean_paired_diff | 0.028478 |                  |                   |
| paired_nb  | gaussian naive bayes | knn                 |               |             | std_paired_diff  | 0.085744 |                  |                   |
| paired_nb  | gaussian naive bayes | logistic regression |               |             | nb_wins          | 5        |                  |                   |
| paired_nb  | gaussian naive bayes | logistic regression |               |             | mean_paired_diff | 0.080213 |                  |                   |
| paired_nb  | gaussian naive bayes | logistic regression |               |             | std_paired_diff  | 0.078934 |                  |                   |

Với chỉ sáu fold validation theo thời gian, số fold mà NB thắng hoặc chênh lệch trung bình **không** đủ để kết luận ý nghĩa thống kê.

## Bốn lưu ý
- Phân tích **thăm dò** (exploratory); không thay thế bảng classifier đã công bố.
- Cấu hình STING/labeler được chọn có tham chiếu metric trên 2021–2022; hai fold CV cuối trùng các năm đó nên nhãn và đánh giá không hoàn toàn độc lập.
- Không có nested CV; `empirical_p` chỉ so với phân phối hoán vị nhãn train.
- Holdout không dùng trong script; không khẳng định tổng quát hóa ngoài CV.

## Cách đọc trung thực
- Macro-F1 CV của NB/KNN/LR tái lập đúng bảng đã công bố; chênh lệch NB−KNN (0.028) nhỏ hơn độ lệch fold-to-fold điển hình (~0.06–0.12 trên các model chính), nên dẫn đầu NB chủ yếu mô tả trên pseudo-label STING, không chứng minh ưu thế bền vững. Hoán vị nhãn cho thấy điểm quan sát cao hơn phần lớn hoán vị khi nhãn vẫn mang cấu trúc năm/tỉnh trong feature — đọc cùng baseline `year_t` và prevalence năm trước để ước lượng phần drift.
