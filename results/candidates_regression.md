# Ứng viên hồi quy cùng-giao-thức — [THAM KHẢO — CHƯA DUYỆT GV]

**Trạng thái:** lane nghiên cứu ứng viên — KHÔNG thay model production, KHÔNG ghi artifact đóng băng (`models/predict_config.json`, `results/supervised_metrics.csv`, `results/predict_all_years.csv`, `models/*.joblib`). Nhãn theo quy ước `reports/model_deep_dive.md:9-14`; việc thay spec/config công bố (chọn model mới, thêm feature ngoài, đổi thuật toán cụm) thuộc nhóm (b) — cần GV duyệt và re-run theo quy trình đóng băng (`reports/model_deep_dive.md:293-299`).

**Tính EXPLORATORY — không phải kết luận:** ma trận hồi quy này gồm 21 combo (6 + 6 + 6 + 3), mỗi combo chấm 6 fold — nhiều nơi có thể vượt mốc do may rủi. KHÔNG tuyên bố p-value hay hiệu chỉnh alpha hình thức; guard chống fishing là quy tắc nhất quán pre-registered (mục 4) + duyệt GV.

## 1) Giao thức — tái dùng qua import (không sao chép)

- `build_regression_pairs` (`scripts/predict_supervised.py:99-120`) → 740 cặp **train** (year_t 2011–2022) + 59 cặp holdout (2023→2024). Holdout: KHÔNG fit, KHÔNG chọn, KHÔNG chấm, KHÔNG nhìn — script chỉ kiểm tra kích thước 59 cặp theo design; số holdout của `results/supervised_metrics.csv` không được tham chiếu khi quyết định ứng viên (`select_model_by_cv` vốn chỉ đọc `value_cv`, `scripts/papi_pred_common.py:60-66`).
- Folds: `expanding_origin_folds(tr.year_t, first_validation_origin=2017)` (`scripts/predict_supervised.py:123-147`) → 6 fold validation origin 2017–2022, warm-up 2011–2016; kích thước fold-train: 374, 437, 498, 561, 621, 681.
- Chấm điểm: `GridSearchCV(cv=folds, scoring='r2', n_jobs=1)` như `scripts/predict_supervised.py:278-285`; cột báo cáo y hệt `reg_metrics` (`scripts/predict_supervised.py:309-316`): `metric_cv` = 'r2 (expanding origin 2017–2022)', `value_cv` = best_score_ làm tròn 3.
- Đặc trưng: 8 cột `REGRESSION_FEATURES` (`scripts/papi_pred_common.py:19-22`), target `sd_6_1` năm t+1. KHÔNG đưa PCI vào features (giữ vai trò external validation độc lập đã công bố, H=31.7751 — `reports/model_deep_dive.md:53`). KHÔNG chạy ablation bỏ `sd_6_1` (đổi spec công bố — đề xuất (b).1 chờ GV, `reports/model_deep_dive.md:295`).

## 2) Gate tái lập baseline (quy tắc pre-registered số 6)

Mọi baseline được TÍNH LẠI in-memory trên cùng fold bằng refit ĐÚNG lưới công bố (`scripts/predict_supervised.py:276-285`) — không hardcode số từ CSV. Đối chiếu mean với `results/supervised_metrics.csv` trước khi so ứng viên; nếu lệch → script DỪNG, không ghi output.

| Baseline | Tái lập (raw) | round 3 | Công bố CSV | Kết quả |
| --- | --- | --- | --- | --- |
| ridge — alpha {0.1, 1, 10} | 0.265168 | 0.265 | 0.265 | KHỚP |
| random forest — depth {4,6,None} × leaf {1,2} | 0.196560 | 0.197 | 0.197 | KHỚP |
| carry-forward (không fit) | 0.145295 | 0.145 | 0.145 | KHỚP |

Per-fold R² của combo best (mốc cho điều kiện nhất quán (ii)):

| Baseline | origin 2017 | origin 2018 | origin 2019 | origin 2020 | origin 2021 | origin 2022 | mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ridge-best | 0.1978 | 0.1733 | 0.3198 | 0.0998 | 0.4515 | 0.3488 | 0.2652 |
| RF-best | 0.2621 | -0.0426 | 0.2303 | 0.0702 | 0.3765 | 0.2829 | 0.1966 |
| carry-forward | -0.0205 | 0.2679 | 0.1897 | -0.0940 | 0.1736 | 0.3550 | 0.1453 |

## 3) Biến ngoài — quy tắc loại pre-registered

Quy tắc (pre-registered trước khi chạy): cột ngoài thiếu >30% trên 740 cặp train → ứng viên ĐÓ BỊ LOẠI khỏi ma trận cùng-protocol. Join theo (province_code, year_t) — KHÔNG BAO GIỜ join năm t+1 (chống tin tức tương lai). `build_regression_pairs` không trả province_code trong frame cặp (`scripts/predict_supervised.py:112-119`), nên script dựng lại join-key (province_code, year_t) theo đúng điều kiện cặp hợp lệ của builder và gate `verify_key_alignment` so từng phần tử (8 features + carry + y + year_t, position-wise) với frame cặp thật — khớp 740/740 thì join mới được phép chạy, lệch thì script DỪNG.

| Ứng viên | Cột | Nguồn | Thiếu trên 740 cặp | % | Quy tắc |
| --- | --- | --- | --- | --- | --- |
| R4 Ridge+poverty | `poverty_rate_pct` | external_poverty_63.csv | 64/740 | 8.6% | GIỮ — impute trong fold |
| R4 Ridge+GRDP | `grdp_per_capita_million_vnd` | external_gso_grdp_63.csv | 437/740 | 59.1% | LOẠI — lý do ghi rõ, không loại im lặng |
| R4 Ridge+urban | `gso_urban_residence_pct_derived` | external_gso_population_63_full.csv | 252/740 | 34.1% | LOẠI — lý do ghi rõ, không loại im lặng |

- **LOẠI R4 Ridge+GRDP:** cột `grdp_per_capita_million_vnd` thiếu 59.1% (437/740 cặp train) > 30% (nguồn external_gso_grdp_63.csv) — KHÔNG chạy, không im lặng.
- **LOẠI R4 Ridge+urban:** cột `gso_urban_residence_pct_derived` thiếu 34.1% (252/740 cặp train) > 30% (nguồn external_gso_population_63_full.csv) — KHÔNG chạy, không im lặng.
- **GIỮ R4 Ridge+poverty:** cột `poverty_rate_pct` thiếu 8.6% (64/740 cặp train) ≤ 30% (nguồn external_poverty_63.csv) — được chạy với impute trong fold.

**Delta tiền xử lý được khai báo:** pipeline R4 có `SimpleImputer(strategy='median', add_indicator=True)` — pipeline công bố KHÔNG có imputer. Imputer nằm trong Pipeline nên GridSearchCV refit từng fold = imputer fit trên fold-train thôi → không rò rỉ. Lưới alpha của R4 GIỐNG HỆT lưới ridge công bố ({0.1, 1.0, 10.0}) để tách đúng hiệu ứng ĐẶC TRÙNG khỏi hiệu ứng siêu tham số.

## 4) Ngưỡng thắng (pre-registered trước khi chạy)

Ứng viên thắng CHỈ khi (i) `value_cv` > mốc đã công bố trên CÙNG metric (ridge R² 0.265) VÀ (ii) nhất quán từng fold: beat per-fold score của ridge-best (tái lập in-memory, mục 2) trên ≥ 4/6 fold. Verdict: `beat` = (i)+(ii) đều đạt; `noise` = đúng một trong hai; `worse` = không cái nào. Cấm trích 1 fold đẹp; cấm đổi metric/fold sau khi thấy số. So thêm với carry-forward 0.145 (mốc yếu hơn) chỉ để tham khảo.

## 5) Bảng kết quả (CV train expanding origin 2017–2022)

| Ứng viên | combos | best combo | R² CV | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | beat ridge /6 | Δ vs ridge 0.265 | Δ vs carry 0.145 | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline: ridge (lưới công bố, tái lập) | 3 | m__alpha=0.1 | 0.265 | 0.1978 | 0.1733 | 0.3198 | 0.0998 | 0.4515 | 0.3488 | — | +0.000 | +0.120 | **baseline** |
| baseline: random forest (lưới công bố, tái lập) | 6 | max_depth=4 min_samples_leaf=2 | 0.197 | 0.2621 | -0.0426 | 0.2303 | 0.0702 | 0.3765 | 0.2829 | — | -0.068 | +0.052 | **baseline** |
| baseline: carry-forward (giữ giá trị năm nay) | 1 | — | 0.145 | -0.0205 | 0.2679 | 0.1897 | -0.0940 | 0.1736 | 0.3550 | — | -0.120 | +0.000 | **baseline** |
| R1 ElasticNet | 6 | m__alpha=0.01 m__l1_ratio=0.2 | 0.267 | 0.1655 | 0.1641 | 0.3507 | 0.1081 | 0.4599 | 0.3533 | 4/6 | +0.002 | +0.122 | **beat** |
| R2 HistGradientBoosting | 6 | learning_rate=0.05 max_leaf_nodes=8 | 0.176 | 0.1887 | -0.1085 | 0.2324 | 0.0579 | 0.4486 | 0.2397 | 0/6 | -0.089 | +0.031 | **worse** |
| R3 KNeighbors | 6 | m__n_neighbors=20 m__weights=distance | 0.168 | 0.0926 | -0.1135 | 0.2852 | 0.0901 | 0.4125 | 0.2389 | 0/6 | -0.097 | +0.023 | **worse** |
| R4 Ridge+poverty | 3 | m__alpha=1.0 | 0.263 | 0.2069 | 0.1554 | 0.3219 | 0.1010 | 0.4490 | 0.3437 | 3/6 | -0.002 | +0.118 | **worse** |
| R4 Ridge+GRDP | 3 | — | — |  |  |  |  |  |  | — | — | — | **EXCLUDED** |
| R4 Ridge+urban | 3 | — | — |  |  |  |  |  |  | — | — | — | **EXCLUDED** |

## 6) Ghi chú nguồn cột ứng viên (lý do thiết kế)

- **R1 ElasticNet:** Ridge (best CV 0.265) là thuần L2; ElasticNet kiểm tra xem trộn L1 có cắt bớt 7 đặc trưng nhiễu (mỗi cái chỉ đóng góp 0.006–0.031 theo permutation, `reports/model_deep_dive.md:244-246`) và tổng quát hóa tốt hơn không, cùng pipeline chuẩn hóa.
- **R2 HistGradientBoosting:** boosting là bias quy nạp khác RF (bagging) — kiểm tra trực tiếp liệu nonlinear/interaction có vượt RF CV 0.197 và ridge 0.265 hay không; n≈740 dễ overfit nên lưới ngắn + cố định số vòng (max_iter=200) + early_stopping=False.
- **R3 KNeighbors:** quy nạp cục bộ (hàng xóm trong không gian 8 chiều đã scale) — bias hoàn toàn khác linear toàn cục và cây; dự kiến yếu trong 8-D n nhỏ nhưng rẻ và đủ để loại trừ giả thuyết.
- **R4 Ridge+poverty:** tách hiệu ứng đặc trưng ngoài (tỉ lệ nghèo GSO) khỏi hiệu ứng siêu tham số bằng cách giữ nguyên lưới alpha công bố; imputer trong pipeline (delta tiền xử lý — khai báo ở mục 3).

## 7) Trung thực + determinism

- `value_cv` là best_score_ của GridSearchCV trên chính 6 fold (không nested CV) → hơi lạc quan, đúng disclosure đã công bố trong `results/supervised_summary.md`.
- **Đọc kết quả `beat` biên mỏng:** R1 ElasticNet raw 0.266933 (Δ vs ridge-best tái lập = +0.0018, beat 4/6) — đạt ngưỡng pre-registered nhưng biên nằm trong vùng nhiễu của best_score_ (bullet trên) và thua ridge ở 1–2 fold origin sớm; verdict `beat` ở đây là ĐẠT NGƯỠNG KỸ THUẬT, KHÔNG phải bằng chứng superiority. Adoption vẫn thuộc GV (nhóm (b)).
- **Ứng viên kém — ghi kém, không làm đẹp:** R2 HistGradientBoosting value_cv 0.176 (Δ vs ridge -0.089, beat 0/6); R3 KNeighbors value_cv 0.168 (Δ vs ridge -0.097, beat 0/6); R4 Ridge+poverty value_cv 0.263 (Δ vs ridge -0.002, beat 3/6).
- Kết quả là **THAM KHẢO [CHƯA DUYỆT GV]** — adoption cần GV duyệt (nhóm (b)); script KHÔNG ghi bất kỳ artifact đóng băng nào.
- Determinism: numpy seed 11 (phòng hờ); estimator dùng đúng `random_state=42` theo thiết kế ứng viên và khớp SEED công bố (`scripts/predict_supervised.py:72`) cho baseline RF; ElasticNet (coordinate descent), HGB (early_stopping=False), KNN, Ridge đều deterministic và không tiêu thụ seed tự do. Yêu cầu kiểm chứng: chạy 2 lần → md/csv sha256 byte-giống (kiểm chứng do verify lane thực hiện ngoài tệp này).
- Môi trường chạy: python 3.14.2, sklearn 1.8.0, pandas 2.3.3, numpy 2.4.0.
- Tệp ghi: `results/candidates_regression.csv` + tệp này. Không tệp khác.
