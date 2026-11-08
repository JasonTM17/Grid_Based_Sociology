# Ứng viên phân loại (lane CLF) — chỉ CV train, holdout không tham gia

**Trạng thái: [THAM KHẢO — CHƯA DUYỆT GV]** — số dưới đây là đầu vào cho quyết định, không phải quyết định (quy ước `reports/model_deep_dive.md:9-14`); thay spec/config công bố thuộc nhóm (b) — cần GV duyệt và re-run theo quy trình đóng băng (`reports/model_deep_dive.md:293-299`).

- Script: `scripts/candidates_classification.py`, tái dùng NGUYÊN VĂN pipeline `scripts/predict_supervised.py` qua import: `build_classification_pairs` (:187-211), `expanding_year_splits` (:214-233), `expanding_majority_f1` (:236-251), `CLASSIFICATION_SCORER` (:75-77), spec + lưới LR/RF (:342-348), seed model (:72). Cấu hình đóng băng `models/predict_config.json` CHỈ ĐỌC — features sd_4_2+sd_6_1 và STING 3/4/5/2, connectivity=1 là không gian NHÃN STING; ma trận X của classifier là 8 cột REGRESSION_FEATURES theo đúng pipeline (:338).
- Provenance (sha256 12 ký tự đầu): panel `papi_panel_63_2011_2024.csv` `87404305f36b` · config `predict_config.json` `9d8fa43aeb9f` (chỉ đọc).
- Seed: model giữ random_state=42 (đặc tả công bố); seed lane 11 khai báo theo quy ước — mọi bước (StandardScaler, STING lưới thống kê, LogisticRegression lbfgs, GridSearchCV n_jobs=1) đều tất định nên seed lane không tác động kết quả. `refit=False` cho mọi GridSearchCV: không fit model cuối nào ngoài CV.
- Phạm vi CHỈ CV train: 738 cặp year_t ≤ 2022 (warm-up 2011–2016), 6 fold expanding origin 2017–2022; nhãn y = 1 nếu STING gán cụm (vùng dày), 0 nếu nhiễu (ngoại vi) — pseudo-label, không phải ground truth (:208). Holdout 2023→2024 (59 cặp, theo `results/supervised_summary.md:7`) KHÔNG fit, KHÔNG chọn, KHÔNG chấm, KHÔNG nhìn; cột holdout_* của `results/supervised_metrics.csv` không được tham chiếu khi quyết định ứng viên.
- Số combo chấm CV: 15 combo ứng viên (3 + 6 + 6) + 9 combo baseline tái lập lưới công bố (3 LR + 6 RF) = 24 combo × 6 fold = 144 fit. Đây là phân tích exploratory — KHÔNG tuyên bố p-value hay hiệu chỉnh alpha hình thức; guard chống fishing là ngưỡng pre-registered (mục 3) + duyệt GV.

## 1) Baseline tái lập in-memory trên cùng fold — gate trước khi so

Baseline KHÔNG hardcode từ CSV — tính lại bằng refit đúng lưới công bố (:342-348) trên đúng fold + đúng scorer. Đối chiếu round(mean, 3) với cột `value_cv` (task=classification) của `results/supervised_metrics.csv`; always-1 đối chiếu mốc 0.400 từ `results/supervised_summary.md:31`. Lệch → script dừng, không ghi kết quả ứng viên.

| Baseline | Cách tính | In-memory | Công bố | Nguồn mốc | Khớp |
|:--|--:|--:|--:|--:|--:|
| LR lưới công bố | GridSearchCV C {0.1, 0.3, 1.0} (:342-346) | 0.4342 | 0.434 | supervised_metrics.csv | KHỚP |
| RF lưới công bố | GridSearchCV depth {3, 6, None} × leaf {1, 2} (:344, :347-348) | 0.3972 | 0.397 | supervised_metrics.csv | KHỚP |
| majority | expanding_majority_f1 (:236-251) | 0.2282 | 0.228 | supervised_metrics.csv | KHỚP |
| always dự đoán 1 | f1(ones) từng fold, nguyên văn :530-542 | 0.4001 | 0.400 | supervised_summary.md:31 | KHỚP |

## 2) Cấu trúc fold và điểm từng fold (macro-F1, cùng scorer)

| Fold origin | n train | n val | Đa số train | Prevalence nhãn 1 (val) | LR-best | RF-best | majority | always-1 | C1 | C2 | C3 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 2017 | 374 | 61 | 0 | 56% | 0.3389 | 0.3068 | 0.3068 | 0.3579 | 0.5909 | 0.3389 | 0.4895 |
| 2018 | 435 | 61 | 0 | 44% | 0.4089 | 0.3812 | 0.3579 | 0.3068 | 0.3838 | 0.4089 | 0.4190 |
| 2019 | 496 | 63 | 0 | 59% | 0.4569 | 0.3837 | 0.2921 | 0.3700 | 0.3438 | 0.4569 | 0.6028 |
| 2020 | 559 | 60 | 0 | 82% | 0.4309 | 0.3748 | 0.1549 | 0.4495 | 0.5425 | 0.4309 | 0.4563 |
| 2021 | 619 | 60 | 0 | 92% | 0.4725 | 0.3658 | 0.0769 | 0.4783 | 0.5370 | 0.4725 | 0.5935 |
| 2022 | 679 | 59 | 0 | 78% | 0.4968 | 0.5712 | 0.1806 | 0.4381 | 0.5184 | 0.4968 | 0.5816 |
| **mean (value_cv)** |  |  |  |  | **0.4342** | **0.3972** | **0.2282** | **0.4001** | **0.4861** | **0.4342** | **0.5238** |

## 3) Verdict ứng viên — ngưỡng pre-registered trước khi chạy

Ứng viên thắng CHỈ khi: **(i)** value_cv (mean 6 fold của combo best) > mốc LR công bố 0.434 — đối chiếu bằng LR tái lập in-memory trên cùng fold (KHỚP 3 số lẻ, mục 1; so sánh dùng mean chưa làm tròn của refit đó) — VÀ **(ii)** nhất quán từng fold: beat per-fold của LR-best tái lập trên ≥ 4/6 fold (đếm chặt: hoà không tính là beat). Cấm trích 1 fold đẹp; cấm đổi metric/fold sau khi thấy số. Delta tính theo refit in-memory; mốc đã công bố hiển thị trong tiêu đề cột.

| Ứng viên | Spec | Best combo | macro-F1 CV | Δ vs LR 0.434 | Δ vs majority 0.228 | Beat LR-best (fold) | Verdict |
|:--|--:|--:|--:|--:|--:|--:|--:|
| C1 | LogisticRegression(class_weight='balanced') — lưới C {0.1, 0.3, 1.0} y hệt lưới công bố | C=0.3 | 0.4861 | +0.0519 | +0.2578 | 4/6 | VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV] |
| C2 | LogisticRegression — lưới C {0.03, 0.1, 0.3, 1.0, 3.0, 10.0} (superset của lưới công bố) | C=1 | 0.4342 | +0.0000 | +0.2059 | 0/6 | KHÔNG VƯỢT — value_cv không vượt mốc LR công bố; beat per-fold LR-best < 4/6 fold |
| C3 | RandomForestClassifier(class_weight='balanced', n_estimators=300, random_state=42, n_jobs=1) — lưới max_depth {3, 6, None} × min_samples_leaf {1, 2} y hệt lưới công bố | depth=6, leaf=2 | 0.5238 | +0.0896 | +0.2956 | 6/6 | VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV] |

### 3.1 Chi tiết lưới — chênh điểm chỉ do class_weight / siêu tham số

#### C1 vs LR công bố (cùng lưới, khác class_weight)

| C | LR công bố (mean CV) | C1 balanced (mean CV) | Δ |
|:--|--:|--:|--:|
| 0.1 | 0.4169 | 0.4798 | +0.0628 |
| 0.3 | 0.4216 | 0.4861 | +0.0645 |
| 1 | 0.4342 | 0.4861 | +0.0519 |

#### C2 — C mở rộng (superset; điểm tại C dùng chung trùng LR công bố ≤1e-12)

| C | Trong lưới công bố? | LR công bố (mean CV) | C2 (mean CV) | Δ vs LR-best |
|:--|--:|--:|--:|--:|
| 0.03 | mới | — | 0.3681 | -0.0660 |
| 0.1 | có | 0.4169 | 0.4169 | -0.0172 |
| 0.3 | có | 0.4216 | 0.4216 | -0.0126 |
| 1 | có | 0.4342 | 0.4342 | +0.0000 |
| 3 | mới | — | 0.4306 | -0.0035 |
| 10 | mới | — | 0.4289 | -0.0052 |
- Spread điểm trong lưới C2 = 0.0660 (lưới công bố 3 điểm: 0.0172) — đo độ nhạy siêu tham số; đối chiếu ghi chú bias lạc quan value_cv ở `results/supervised_summary.md:32`.

#### C3 vs RF công bố (cùng lưới, khác class_weight)

| max_depth, min_samples_leaf | RF công bố (mean CV) | C3 balanced (mean CV) | Δ |
|:--|--:|--:|--:|
| depth=3, leaf=1 | 0.3345 | 0.4644 | +0.1298 |
| depth=3, leaf=2 | 0.3300 | 0.4650 | +0.1351 |
| depth=6, leaf=1 | 0.3697 | 0.5183 | +0.1486 |
| depth=6, leaf=2 | 0.3793 | 0.5238 | +0.1445 |
| depth=None, leaf=1 | 0.3972 | 0.3904 | -0.0068 |
| depth=None, leaf=2 | 0.3917 | 0.4235 | +0.0319 |

## Phạm vi & trung thực

- KHÔNG có số holdout nào trong tài liệu này: holdout 2023→2024 không fit, không chọn, không chấm cho bất kỳ ứng viên nào; `select_model_by_cv` vốn chỉ đọc `value_cv` (`scripts/papi_pred_common.py:60-66`) — mọi quyết định ở đây chỉ dùng CV train.
- Exploratory: 24 combo × 6 fold — nhiều combo sẽ vượt mốc do may rủi; verdict ở mục 3 theo đúng ngưỡng pre-registered, không chọn lại sau khi thấy số.
- Baseline 'always dự đoán 1' (0.4001) và majority (0.2282) là sàn mù: mọi ứng viên phải đối chiếu cả hai, vì prevalence nhãn 1 trong validation trôi 44%–92% theo năm (bảng mục 2).
- Biến thể RF `class_weight='balanced_subsample'` được đề bài nêu là TUỲ CHỌN ('có thể chạy song song, không thay C3') — KHÔNG chạy trong pha này để giữ đúng bộ 3 ứng viên pre-registered; nếu GV yêu cầu thì chạy như combo bổ sung đánh dấu riêng (NOT_RUN).
- Script này chỉ ghi 2 tệp mới (`results/candidates_classification.md`, `.csv`); KHÔNG ghi `models/predict_config.json`, `results/supervised_metrics.csv`, `results/predict_all_years.csv`, KHÔNG ghi models/*.pkl|joblib, KHÔNG chạy `scripts/predict_sweep.py`, KHÔNG đổi số đã công bố (Ridge 0.265, carry 0.145, LR 0.434, k=3).
- Ứng viên vượt ngưỡng (nếu có) vẫn chỉ là kết quả THAM KHẢO [CHƯA DUYỆT GV] — adoption thuộc quyền GV theo nhóm (b) của `reports/model_deep_dive.md:293-299`.
