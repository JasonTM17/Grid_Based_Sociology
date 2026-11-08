# Ma trận ứng viên cải tiến model — REG · CLF · CLUS — [THAM KHẢO — CHƯA DUYỆT GV]

**Trạng thái tài liệu:** tổng hợp exploratory từ 3 lane ứng viên (`results/candidates_regression.md`, `results/candidates_classification.md`, `results/candidates_clustering.md`). Mọi số dưới đây là **đầu vào cho quyết định, không phải quyết định** — theo quy ước đọc hai nhãn của `reports/model_deep_dive.md:9-14`; việc thay spec/config đã công bố thuộc nhóm (b) — cần GV duyệt và re-run theo quy trình đóng băng (`reports/model_deep_dive.md:293-299`).

## 1) Mục đích và phạm vi đọc

- **Mục đích:** trả lời một câu hỏi cho iteration sau — "có ứng viên nào đáng để GV xem xét thay một phần spec đã công bố hay không?" — bằng một ma trận ứng viên chạy **cùng giao thức** với model đã công bố, không đụng artifact đóng băng.
- **Mọi so sánh CHỈ trên CV đã công bố:** hồi quy so trên R² CV ridge 0.265 / RF 0.197 / carry 0.145 (`reports/model_deep_dive.md:53`); phân loại so trên macro-F1 CV LR 0.434 / RF 0.397 / majority 0.228 / always-1 0.400 (`results/supervised_summary.md:29-32`); phân cụm so trên cửa sổ 747 tỉnh-năm ≤ 2022 với chuẩn hóa z-trong-năm. Không có số holdout nào được dùng để chọn hay chấm ứng viên.
- **Holdout 2023→2024 (59 cặp) không bị đụng:** không fit, không chọn, không chấm, không nhìn — các lane script chỉ kiểm tra kích thước 59 cặp; cột `holdout_*` của `results/supervised_metrics.csv` không được tham chiếu khi quyết định ứng viên (`results/candidates_regression.md:9`, `results/candidates_classification.md:79`).
- **Adoption cần GV:** thắng CV ≠ adopt. Ứng viên vượt ngưỡng vẫn ở trạng thái [THAM KHẢO — CHƯA DUYỆT GV] cho tới khi GV quyết (nhóm (b), `reports/model_deep_dive.md:293-299`) và re-run theo quy trình đóng băng.
- **0 tệp artifact đóng băng bị đụng:** xác nhận bằng `git diff --name-only` (mục 6).

## 2) Verdict tổng hợp 3 lane ứng viên — REG · CLF · CLUS (tất cả [THAM KHẢO — CHƯA DUYỆT GV])

| Ứng viên | Metric | Mốc | Verdict | Nhận xét ngắn |
|---|---|---|---|---|
| REG · Gate tái lập baseline (ridge / RF / carry) | R² CV (value_cv, raw) | công bố 0.265 / 0.197 / 0.145 | **KHỚP 3/3** (gate) | Refit ĐÚNG lưới công bố `scripts/predict_supervised.py:276-285` trên cùng 6 fold; lệch → exit 1 (`results/candidates_regression.md:20-22`) |
| REG · R1 ElasticNet (α=0.01, l1_ratio=0.2) | R² CV 0.267 (raw 0.266933) | ridge 0.265 | **BEAT** (ngưỡng kỹ thuật của lane — KHÔNG phải superiority) — (i) 0.267 > 0.265 VÀ (ii) beat 4/6 fold | Biên mỏng +0.0018 raw, nằm trong vùng nhiễu của best_score_ (không nested CV) — md §7 tự ghi "ĐẠT NGƯỠNG KỸ THUẬT, KHÔNG phải superiority" (`candidates_regression.md:76`); thắng CV ≠ adopt |
| REG · R2 HistGradientBoosting (lr=0.05, max_leaf=8) | 0.176 | ridge 0.265 | **WORSE** (0/6, Δ −0.089) | Boosting không thắng trên ~740 cặp tỉnh-năm; ghi kém không làm đẹp (`candidates_regression.md:77`) |
| REG · R3 KNeighbors (k=20, distance) | 0.168 | ridge 0.265 | **WORSE** (0/6, Δ −0.097) | Kém nhất lane; loại trừ giả thuyết quy nạp cục bộ |
| REG · R4 Ridge+poverty (α=1.0, lưới alpha y hệt ridge) | 0.263 | ridge 0.265 | **WORSE** (beat 3/6, Δ −0.002) | Trượt cả (i) lẫn (ii) — gần hoà nhưng không thắng; imputer là delta tiền xử lý đã khai báo (md §3:46) |
| REG · Quy tắc loại biến thiếu >30% (tính live trên 740 cặp) | % thiếu | đề bài lane ước poverty ~8.5%/63 (ước trong ask giao việc — không phải artifact repo) | poverty **GIỮ** (64/740 = 8.6%); GRDP **LOẠI** (437/740 = 59.1%); urban **LOẠI** (252/740 = 34.1%) | Loại có lý do ghi rõ trong md §3 + csv, không loại im lặng; ước đề bài 63 ≈ thực tế 64 (`candidates_regression.md:38`) — kết luận không đổi |
| CLF · Gate tái lập baseline (LR / RF / majority / always-1) | macro-F1 | công bố 0.434 / 0.397 / 0.228 / 0.400 | **KHỚP 4/4** (gate) | In-memory vs công bố khớp 3 số lẻ; per-fold LR khớp model_deep_dive.md 4.1 6/6 (báo bởi lane; đã xác minh lại trong phiên viết báo cáo tại `reports/model_deep_dive.md:226-231`) |
| CLF · C1 LR class_weight='balanced' (C=0.3, lưới y hệt công bố) | macro-F1 CV 0.4861 | LR 0.434 | **VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV]** (Δ +0.052; vs majority +0.258; beat 4/6) | Đạt cả (i)+(ii); đổi đúng 1 tham số MỚI (class_weight='balanced') trên đúng lưới công bố; prevalence validation 44–92% → bắt buộc chốt holdout 2023→2024 trước khi tin |
| CLF · C2 LR lưới C mở rộng {0.03…10} | 0.4342 (C=1.0, trùng optimum công bố) | LR 0.434 | **KHÔNG VƯỢT** (Δ +0.0000, beat 0/6 toàn hoà) | Lưới 3 điểm công bố đã chứa đỉnh; peak regularization không nằm ngoài {0.1–1.0} (spread 0.0660 vs 0.0172 — `candidates_classification.md:64`) |
| CLF · C3 RF class_weight='balanced' (depth=6, leaf=2, lưới y hệt; n_estimators=300 giữ nguyên spec công bố `predict_supervised.py:344`) | 0.5238 | LR 0.434 | **VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV]** (Δ +0.090; vs majority +0.296; beat 6/6) | Cao nhất đợt theo macro-F1 CV trên nhãn máy học (chưa qua holdout); per-fold dao động 0.4190–0.6028 (spread 0.1838 — `candidates_classification.md:26-31`) nên 0.5238 là trung bình 6 fold, không phải mức ổn định từng fold; vẫn học trên pseudo-label STING → adopt chỉ sau GV + holdout |
| CLUS · KMeans k=3 (seed 11) | ARI 0.0557 full / 0.0272 non-noise; sil 0.3360 (n=747) | mốc sil nhãn đóng băng −0.0651 (n=598) | **KHÔNG THẮNG** (ARI ≈ 0) | Silhouette cao hơn nhưng đổi câu hỏi, không tái lập cấu trúc đóng băng (`candidates_clustering.md:103`); sanity khớp kỳ vọng phiên thiết kế như lane ghi lại (sizes [307,234,206] + ARI 0.0557 — `candidates_clustering.md:68`; bản ghi kỳ vọng nằm trong file lane, không phải artifact repo riêng) |
| CLUS · Ward k=3 | ARI 0.1462 full / 0.0679 non-noise; sil 0.3336 | mốc −0.0651 | **KHÔNG THẮNG** | Cụm li ti khớp 100% (5/5, 16/16) nhưng cụm lớn chỉ 64% (370/577) → ARI thấp |
| CLUS · DBSCAN ms=5 (eps từ k-dist p50→p90) | max ARI non-noise 0.0742 (p80); sil −0.061→0.218; k 18→2 | mốc −0.0651 | **KHÔNG THẮNG** | Không combo nào tái lập; n_sil khác nhau giữa các dòng (470–706) nên silhouette không so tuyệt đối |
| CLUS · DBSCAN ms=10 (eps p50→p90) | max ARI full 0.3390 (p60); sập k=1 từ p70 | mốc −0.0651 | **KHÔNG THẮNG** | Đồng thuận cao nhất vs refit (p80: ARI non-noise 0.5432, full 0.6190) là k=1 — "cùng một khối", không phải cùng phân hoạch nhiều cụm (`candidates_clustering.md:102`) |
| CLUS · Deconfound: STING refit cfg đóng băng trên cùng z-trong-năm | ARI(refit, nhãn gốc) 0.2927 full / 0.0060 non-noise (`candidates_clustering.md:19,61-63`) | — | Không phải ứng viên — chìa khoá đọc | Chỉ đổi CHUẨN HÓA đã làm sập mức đồng thuận → mọi ARI sau này phải kèm cột "vs refit"; ghi chú trung thực: mốc ARI là ARI-với-chính-nó = 1.0 nên nội dung ràng buộc là "tái lập cấu trúc" — không ai đạt (`candidates_clustering.md:101`) |
| CLUS · Verdict tổng lane | — | ngưỡng chốt trước: thắng cả ARI full + ARI non-noise + silhouette | **KHÔNG ứng viên nào thắng** [THAM KHẢO — CHƯA DUYỆT GV] | Verdict dựa trên tiêu chí ĐÃ DIỄN GIẢI "tái lập cấu trúc" — tiêu chí nguyên văn không thể đạt vì mốc ARI = ARI-với-chính-nó = 1.0 (`candidates_clustering.md:101`); GV có quyền yêu cầu re-spec (vd ARI-vs-refit — cột sẵn có `candidates_clustering.md:19`) trước khi chấp nhận; khuyến nghị mặc định giữ nguyên cấu hình STING đóng băng cho tới khi GV quyết (`candidates_clustering.md:98`); 0 tệp artifact đóng băng bị đụng |
| Kiểm tra trong phiên viết báo cáo · Ruff toàn repo | — | — | **PASS** — `python -E -m ruff check .` → "All checks passed!" exit 0 (chạy lại 2026-11-08) | Phân xử mâu thuẫn lane: REG báo FAIL 2×F821 (clustering.py:375,378), CLF báo PASS — cây hiện tại PASS, finding F821 stale (file untracked, không truy được thời điểm sửa) |
| Kiểm tra trong phiên viết báo cáo · Repo integrity | `git diff --name-only` | 0 tệp tracked sửa | **XÁC NHẬN** (output rỗng, chạy lại 2026-11-08) | 9 tệp untracked đúng = 3 script lane + 6 artifact; models/, slides/, data/processed/, artifact đóng băng không đụng |
| Kiểm tra trong phiên viết báo cáo · Determinism hash | `sha256sum` 6 tệp results/candidates_* | hash lane khai báo | **KHỚP** (chạy lại 2026-11-08): md+csv REG khớp đủ 64 ký tự (8bbdc681…, f1a0280c…); md+csv CLF khớp prefix (b5422706…, 38e4b07b…) | 2 tệp CLUS hash lần đầu (5b27eb2d…, 1908d80b…) — lane chỉ tự báo ×2 byte-giống, không có hash mốc để đối chiếu độc lập; toàn bộ tệp đang untracked → khuyến nghị commit sớm để neo hash vĩnh viễn (mục 4.7) |

## 3) Chi tiết từng lane

### 3.1 Lane REG — ứng viên hồi quy cùng-giao-thức (nguồn: `results/candidates_regression.md` + `.csv`)

**Protocol giữ nguyên thế nào — tái dùng qua import, không sao chép:**

- `build_regression_pairs` (`scripts/predict_supervised.py:99-120`) và `expanding_origin_folds` (`scripts/predict_supervised.py:123-147`) + `HOLDOUT_YEAR = 2023` (`scripts/predict_supervised.py:71`) import nguyên văn từ pipeline công bố. Kết quả: **740 cặp train** (year_t 2011–2022) — xác minh đúng bằng 740 — và **6 fold expanding origin 2017–2022** (kích thước fold-train: 374 / 437 / 498 / 561 / 621 / 681 — tính live trong lane, `candidates_regression.md:10`).
- Holdout 59 cặp (2023→2024): **CHỈ kiểm tra kích thước** theo design; không fit, không chọn, không chấm, không nhìn.
- Đặc trưng: 8 cột `REGRESSION_FEATURES` như công bố; KHÔNG thêm PCI vào features (giữ vai trò external validation độc lập); KHÔNG chạy ablation bỏ `sd_6_1` (đổi spec — chờ GV).
- Chấm điểm: `GridSearchCV(cv=folds, scoring='r2', n_jobs=1)` y hệt pipeline công bố; `value_cv` = best_score_ làm tròn 3.

**Gate tái lập baseline (quy tắc pre-registered số 6)** — baseline TÍNH LẠI in-memory bằng refit ĐÚNG lưới công bố (`scripts/predict_supervised.py:276-285`: ridge pipeline + lưới `m__alpha {0.1, 1.0, 10.0}`; RF + lưới `max_depth {4, 6, None} × min_samples_leaf {1, 2}`) trên cùng 6 fold, đối chiếu trước khi so ứng viên; lệch → script exit 1, không ghi output:

| Baseline | Tái lập (raw) | round 3 | Công bố | Kết quả |
|---|---|---|---|---|
| ridge | 0.265168 | 0.265 | 0.265 | KHỚP |
| random forest | 0.196560 | 0.197 | 0.197 | KHỚP |
| carry-forward | 0.145295 | 0.145 | 0.145 | KHỚP |

**Từng ứng viên — kết quả và vì sao thắng/thua** (ngưỡng thắng pre-registered: (i) value_cv > 0.265 VÀ (ii) beat ridge-best per-fold ≥ 4/6 fold; `results/candidates_regression.md:50`). Quy mô dò: **21 combo ứng viên** = 6 lưới R1 + 6 R2 + 6 R3 + 3 R4 poverty (baseline gate KHÔNG tính vào 21 — `candidates_regression.md:5`), mỗi combo chấm 6 fold:

| Ứng viên | Best combo | R² CV | beat ridge | Δ vs ridge | Verdict |
|---|---|---|---|---|---|
| R1 ElasticNet | α=0.01, l1_ratio=0.2 | **0.267** (raw 0.266933) | 4/6 | +0.002 (raw +0.0018) | **BEAT** (đạt cả (i)+(ii)) |
| R2 HistGradientBoosting | lr=0.05, max_leaf_nodes=8 | 0.176 (raw 0.176431) | 0/6 | −0.089 | WORSE |
| R3 KNeighbors | k=20, weights=distance | 0.168 (raw 0.167654) | 0/6 | −0.097 | WORSE |
| R4 Ridge+poverty | α=1.0 | 0.263 (raw 0.262980) | 3/6 | −0.002 | WORSE |

- **R1 ElasticNet BEAT nhưng biên mỏng:** Ridge thuần L2 đã công bố 0.265; ElasticNet kiểm tra việc trộn L1 để cắt bớt đặc trưng nhiễu (permutation importance của 7 đặc trưng còn lại chỉ 0.006–0.031, `reports/model_deep_dive.md:244-246`). Nó đạt cả hai điều kiện, nhưng Δ raw +0.0018 nằm trong vùng nhiễu của best_score_ (GridSearchCV không nested CV nên hơi lạc quan) và thua ridge ở 1–2 fold origin sớm — lane tự ghi ở §7: verdict là **"ĐẠT NGƯỠNG KỸ THUẬT, KHÔNG phải superiority"** (`candidates_regression.md:76`), adoption vẫn thuộc GV. Đọc lướt bảng mục 2 cần phân biệt: chỉ C1/C3 là thắng rõ (biên lớn, beat 4–6/6); R1 chỉ hơn ridge +0.0018 raw trong vùng nhiễu — nhãn "beat" của lane là verdict kỹ thuật theo ngưỡng pre-registered, không phải tuyên bố model tốt hơn.
- **R2 HistGradientBoosting WORSE:** boosting có năng lực mô hình cao hơn RF (bagging) nhưng trên ~740 cặp tỉnh-năm — tập nhỏ với 8 đặc trưng — năng lực dư dễ bám nhiễu fold-train thay vì cấu trúc; lưới ngắn + cố định `max_iter=200` không đủ cứu. Ghi kém thẳng, không làm đẹp (`candidates_regression.md:77`).
- **R3 KNeighbors WORSE (kém nhất lane):** quy nạp cục bộ trong không gian 8 chiều với n nhỏ — mỗi điểm dựa vào vài hàng xóm gần nhất → phương sai lớn, cấu trúc toàn cục mà ridge nắm được thì KNN mất. Vai trò của nó là **loại trừ giả thuyết** "quy nạp cục bộ giúp gì", và giả thuyết đã bị loại trừ.
- **R4 Ridge+poverty WORSE (gần hoà):** thêm tỉ lệ nghèo GSO (imputer median trong fold) cho 0.263 — trượt cả (i) lẫn (ii), beat 3/6. Lưới alpha GIỐNG HỆT ridge công bố để tách đúng hiệu ứng ĐẶC TRÙNG khỏi hiệu ứng siêu tham số; delta tiền xử lý (imputer) được khai báo trong md §3 (`candidates_regression.md:46`).

**Quy tắc loại biến thiếu >30% (tính live trên 740 cặp thật):** poverty_rate_pct 64/740 = 8.6% → **GIỮ** (đề bài ước ~8.5%/63 — số thật trên cặp là 64, kết luận không đổi); GRDP 437/740 = 59.1% → **LOẠI**; urban 252/740 = 34.1% → **LOẠI**. Lý do loại ghi rõ trong md §3 + csv, không loại im lặng. Join theo (province_code, year_t) — không bao giờ join năm t+1 (chống rò rỉ tương lai), có gate `verify_key_alignment` so 740/740 phần tử trước khi join chạy.

### 3.2 Lane CLF — ứng viên phân loại (nguồn: `results/candidates_classification.md` + `.csv`)

**Protocol giữ nguyên thế nào:**

- Tái dùng NGUYÊN VĂN pipeline qua import: `build_classification_pairs` (`scripts/predict_supervised.py:187-211`), `expanding_year_splits` (`:214-233`), `expanding_majority_f1` (`:236-251`), `CLASSIFICATION_SCORER` (`:75-77`), spec + lưới LR/RF (`:342-348`), seed model (`:72`). Config đóng băng `models/predict_config.json` CHỈ ĐỌC.
- Phạm vi CHỈ CV train: **738 cặp** year_t ≤ 2022 (khớp ghi chú `reports/model_deep_dive.md:270`), 6 fold expanding origin 2017–2022; nhãn y = 1 nếu STING gán cụm, 0 nếu nhiễu — **pseudo-label**, không phải ground truth.
- 15 combo ứng viên + 9 combo baseline tái lập = 24 combo × 6 fold = 144 fit; `refit=False` cho mọi GridSearchCV — không fit model cuối nào ngoài CV. Holdout 59 cặp KHÔNG fit/chọn/chấm/nhìn; script không tạo biến holdout.

**Gate tái lập baseline 4/4** — không hardcode số CSV, tính lại trên cùng fold + cùng scorer; lệch → dừng:

| Baseline | In-memory | Công bố | Nguồn mốc | Khớp |
|---|---|---|---|---|
| LR lưới công bố (C {0.1, 0.3, 1.0}) | 0.4342 | 0.434 | supervised_metrics.csv | KHỚP |
| RF lưới công bố (depth {3, 6, None} × leaf {1, 2}) | 0.3972 | 0.397 | supervised_metrics.csv | KHỚP |
| majority (expanding_majority_f1 nguyên văn) | 0.2282 | 0.228 | supervised_metrics.csv | KHỚP |
| always dự đoán 1 (nguyên văn `scripts/predict_supervised.py:530-542`) | 0.4001 | 0.400 | supervised_summary.md:31 | KHỚP |

**Cross-check độc lập:** per-fold LR-best tái lập (0.3389 / 0.4089 / 0.4569 / 0.4309 / 0.4725 / 0.4968) khớp 6/6 giá trị learning-curve LR đã công bố trong `reports/model_deep_dive.md` mục 4.1 — đã xác minh lại trong phiên viết báo cáo tại `reports/model_deep_dive.md:226-231`.

**Từng ứng viên — kết quả và vì sao thắng/thua** (ngưỡng pre-registered: (i) value_cv > 0.434 VÀ (ii) beat LR-best per-fold ≥ 4/6, hoà không tính; `results/candidates_classification.md:36`):

| Ứng viên | Spec | Best combo | macro-F1 CV | Δ vs LR 0.434 | Δ vs majority 0.228 | Beat | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | LogisticRegression(class_weight='balanced'), lưới C y hệt công bố | C=0.3 | **0.4861** | +0.0519 | +0.2578 | 4/6 | **VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV]** |
| C2 | LogisticRegression, lưới C mở rộng {0.03, 0.1, 0.3, 1.0, 3.0, 10.0} | C=1 | 0.4342 | +0.0000 | +0.2059 | 0/6 (toàn hoà) | KHÔNG VƯỢT |
| C3 | RandomForestClassifier(class_weight='balanced', n_estimators=300, random_state=42, n_jobs=1) — lưới y hệt công bố; class_weight là tham số MỚI DUY NHẤT, n_estimators=300 giữ nguyên spec công bố (`scripts/predict_supervised.py:344`) | depth=6, leaf=2 | **0.5238** | +0.0896 | +0.2956 | 6/6 | **VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV]** |

- **Vì sao C1/C3 thắng:** nhãn pseudo-label STING mất cân bằng mạnh và prevalence nhãn 1 trong validation trôi 44%→92% theo năm (`results/supervised_summary.md:31`; bảng fold ở `results/candidates_classification.md:24-32`). `class_weight='balanced'` đổi hàm mất mát để phạt sai lớp hiếm nhiều hơn — đúng đúng 1 tham số, trên ĐÚNG lưới công bố, nên chênh điểm gán được về hiệu ứng class_weight chứ không phải siêu tham số (chi tiết lưới từng combo: `results/candidates_classification.md:44-75`; ví dụ C3 depth=6/leaf=2: 0.3793 → 0.5238, Δ +0.1445). Biên per-fold của C3 dao động 0.4190–0.6028 (spread 0.1838 — `candidates_classification.md:26-31`), nên 0.5238 là trung bình trên 6 fold chứ không phải mức ổn định từng fold; `value_cv` là best_score_ GridSearchCV — hơi lạc quan theo disclosure đã công bố (`results/supervised_summary.md:32`).
- **Vì sao C2 thua:** lưới C 3 điểm đã công bố ({0.1, 0.3, 1.0}) **đã chứa đỉnh** — mở rộng tới 6 điểm, optimum vẫn nằm tại C=1.0 trùng đúng optimum công bố, beat 0/6 toàn hoà. Spread điểm trong lưới C2 = 0.0660 (lưới công bố 0.0172 — `candidates_classification.md:64`) — đo độ nhạy siêu tham số, không phải cải tiến. Bài học: peak regularization KHÔNG nằm ngoài {0.1–1.0}; mở rộng lưới không phải cải tiến.
- **Sàn mù bắt buộc:** mọi ứng viên đối chiếu cả hai baseline mù — always-1 (0.4001) và majority (0.2282) — vì prevalence validation trôi mạnh theo năm; C1 (+0.2578) và C3 (+0.2956) vượt xa majority, tức lợi thế không phải do đoán lớp đa số.
- **Giới hạn ghi rõ:** cả C1/C3 vẫn học trên **pseudo-label STING** (nhãn fit tại từng cutoff, không phải ground truth) — thắng CV trên nhãn máy học ≠ năng lực dự báo thật; phải qua holdout một lần sau khi GV duyệt.

### 3.3 Lane CLUS — ứng viên phân cụm thay thế (nguồn: `results/candidates_clustering.md` + `.csv`)

**Cửa sổ và chuẩn hóa (chốt trước khi chạy):**

- Cửa sổ: **747 tỉnh-năm** year ≤ 2022 (869 tổng dòng panel − 61 dòng 2023 − 61 dòng 2024 — `candidates_clustering.md:8`); script fail-closed assert đúng phân bố nhãn đóng băng {−1: 149, 0: 5, 1: 16, 2: 577} — khớp join PCI 747 (`results/cluster_profile.md:34`). Holdout không fit/chấm/nhìn.
- Chuẩn hóa: **z-score TRONG TỪNG NĂM** trên 2 cột sd_4_2 × sd_6_1 — khác scaler pooled của model đóng băng; đây chính là điểm tạo ra deconfound dưới đây.
- Mốc tính lại trên cùng cửa sổ: STING đóng băng k=3, noise 0.1995, sizes [577, 16, 5], silhouette (non-noise, n=598) = **−0.0651** — KHÔNG so được với 0.3611 đã công bố vì 0.3611 tính trên cửa sổ/scaler khác (`results/cluster_profile.md:97`); không so chéo số giữa hai cửa sổ.

**Deconfound — chìa khoá đọc (không phải ứng viên)** (số liệu: `candidates_clustering.md:61-63`, dòng bảng :19): refit STING đúng cfg đóng băng (L=3, f=4, mc=5, lv=2, conn=1) trên cùng z-trong-năm cho k=2, noise 0.1580, sizes [624, 5], sil 0.3586; ARI(refit, nhãn gốc) đầy đủ **0.2927**, non-noise **0.0060**. Nghĩa là: chỉ đổi CHUẨN HÓA (giữ nguyên thuật toán) đã làm sập mức đồng thuận với phân hoạch công bố — phần lớn khoảng cách ARI giữa ứng viên và nhãn gốc là **hiệu ứng chuẩn hóa, không phải hiệu ứng thuật toán**. Hệ quả: mọi so sánh phân cụm tương lai phải kèm cột "vs refit" (cùng tiền xử lý), nếu không sẽ đọc nhầm hiệu ứng scaler thành hiệu ứng thuật toán.

**12 ứng viên — không ai thắng ngưỡng chốt trước (thắng cả ARI đầy đủ + ARI non-noise + silhouette):**

| Ứng viên | ARI full | ARI non-noise | Silhouette | Verdict |
|---|---|---|---|---|
| KMeans k=3 (seed 11, n_init=10) | 0.0557 | 0.0272 | 0.3360 (n=747) | KHÔNG THẮNG |
| Ward k=3 | 0.1462 | 0.0679 | 0.3336 (n=747) | KHÔNG THẮNG |
| DBSCAN ms=5, eps p50→p90 (k 18→2) | 0.1260–0.3372 | max **0.0742** (p80) | −0.0611→0.2180 | KHÔNG THẮNG |
| DBSCAN ms=10, eps p50→p90 (k 3→1, sập k=1 từ p70) | max **0.3390** (p60) | 0.0003–0.0562 | n/a từ p70 | KHÔNG THẮNG |

- **Vì sao silhouette cao mà vẫn thua:** KMeans/Ward tạo 3 cụm cân → tách biệt hình học tốt (silhouette ~0.33 vs mốc âm −0.0651) nhưng ARI ≈ 0 với cấu trúc đã công bố "1 cụm lớn [577] + 2 cụm li ti [16, 5] + nhiễu [149]". Đếm chéo: Ward khớp cụm li ti 100% (5/5, 16/16) nhưng cụm lớn chỉ 64% (370/577); KMeans cụm lớn chỉ 47% (274/577). **Thắng silhouette = đổi câu hỏi** (chất lượng hình học dưới chuẩn hóa mới), không phải tái lập cấu trúc đóng băng (`candidates_clustering.md:103`).
- **Vì sao DBSCAN không tái lập được:** không combo nào đạt ARI non-noise > 0.0742 ≈ 0. Ghi chú trung thực về mốc: ARI của mốc là ARI-với-chính-nó = 1.0, nên tiêu chí "ARI > mốc" đọc nghĩa đen là không thể đạt; nội dung ràng buộc có ý nghĩa là "tái lập cấu trúc đóng băng" — và KHÔNG ứng viên nào đạt (`candidates_clustering.md:101`). Hệ quả phương pháp: verdict "KHÔNG ứng viên nào thắng" của lane dựa trên tiêu chí ĐÃ DIỄN GIẢI, không phải tiêu chí nguyên văn (không thể đạt) — GV có quyền yêu cầu re-spec (vd chốt ARI-vs-refit; cột số liệu đã có sẵn `candidates_clustering.md:19`) trước khi chấp nhận kết luận.
- **Đồng thuận cao nhất vs refit** là DBSCAN ms=10 eps=0.3273 (p80): ARI non-noise 0.5432, đầy đủ 0.6190 — NHƯNG k=1, tức chủ yếu là "cùng mô tả một khối", không phải cùng phân hoạch nhiều cụm (`candidates_clustering.md:102`).
- **Silhouette không so tuyệt đối giữa các dòng:** DBSCAN/STING tính trên non-noise (n_sil 470–719 khác nhau), KMeans/Ward trên cả 747 điểm; 7/12 ứng viên vượt mốc −0.0651 nhưng mốc là silhouette của chính phân hoạch công bố dưới chuẩn hóa mới — nó âm nghĩa phân hoạch công bố không tách biệt hình học dưới z-trong-năm, không phải ứng viên "tốt hơn".

**Verdict tổng lane:** KHÔNG ứng viên nào thắng ngưỡng chốt trước → **khuyến nghị mặc định giữ nguyên cấu hình STING đóng băng** cho tới khi GV quyết (`candidates_clustering.md:98`). Quyền kết luận thuộc GV.

## 4) Khuyến nghị cho iteration sau (tất cả CHỜ GV DUYỆT)

### 4.1 Đáng để GV xem xét adopt

1. **C3 — RF thêm `class_weight='balanced'`** (macro-F1 CV 0.5238 vs LR 0.434, beat 6/6 fold, Δ vs majority +0.2956) — **ưu tiên 1**.
2. **C1 — LR balanced** (0.4861, beat 4/6, Δ vs majority +0.2578) — **ưu tiên 2**.

Cả hai chỉ thêm **một tham số MỚI** (class_weight='balanced') trên ĐÚNG lưới công bố — mọi siêu tham số khác giữ nguyên giá trị spec công bố (RF công bố vốn đã có n_estimators=300, `scripts/predict_supervised.py:344`); là 2 ứng viên duy nhất đạt đủ ngưỡng (i)+(ii) và đã đối chiếu cả sàn mù always-1/majority. Đây là **THẮNG CV trên pseudo-label STING, chưa phải "đáng adopt"**: adoption cần GV duyệt (nhóm (b), `reports/model_deep_dive.md:293-299`) VÀ chốt holdout 2023→2024 (59 cặp chưa từng fit/chấm/nhìn).

3. **R1 ElasticNet** (R² CV 0.267, beat 4/6) đạt nhãn "beat" thứ ba theo verdict kỹ thuật của lane nhưng **ưu tiên thấp nhất, chỉ nhận nếu GV muốn thử trộn L1** để cắt feature nhiễu: biên +0.0018 raw nằm trong vùng nhiễu của best_score_ (không nested CV) và chính lane tự ghi "ĐẠT NGƯỠNG KỸ THUẬT, KHÔNG phải superiority" (`results/candidates_regression.md:76`) — đọc bảng mục 2 cần nhớ: chỉ C1/C3 là thắng rõ; R1 chỉ hơn ridge +0.0018 raw trong vùng nhiễu.

### 4.2 Điều kiện bắt buộc nếu GV duyệt adopt

- **Thứ tự ưu tiên đề xuất:** C3 → C1 → (R1 tuỳ biên).
- Mỗi ứng viên được adopt phải **re-run theo quy trình đóng băng** (refreeze config + ghi lại artifact chính thức), rồi **kiểm holdout 2023→2024 ĐÚNG 1 LẦN sau khi GV duyệt** — holdout chưa từng bị 3 lane này fit/chọn/chấm/nhìn; kiểm xong không được lặp lại hay tinh chỉnh theo holdout (làm vậy sẽ đốt holdout).
- **Chưa chốt trước khi kiểm (open decision cho GV):** ngưỡng đậu/rớt trên holdout CHƯA có pre-registered (ngưỡng hiện có chỉ cho CV — mục 3.1/3.2) và cách chia lượt kiểm (mỗi ứng viên một lần hay một lần chung cho spec được chọn) chưa chốt — GV cần đặt cả hai TRƯỚC khi nhìn số holdout, không đặt sau.
- **Nếu holdout thất bại:** spec công bố giữ nguyên trạng thái đóng băng hiện tại — artifact mới chỉ được ghi SAU khi holdout đạt; rớt nghĩa là giữ nguyên spec cũ, không cần rollback phức tạp (lượt holdout của ứng viên đó coi như đã dùng — rủi ro GV chấp nhận khi duyệt).
- 3 ứng viên vượt ngưỡng đều vẫn ở trạng thái [THAM KHẢO — CHƯA DUYỆT GV] cho tới khi điều kiện trên hoàn tất.

### 4.3 Đã thử và KHÔNG thắng trong đợt này (bằng chứng exploratory đơn lần — không phải kết luận chắc chắn)

- **REG:** HistGradientBoosting (0.176), KNN (0.168), Ridge+poverty (0.263, gần hoà) đều worse hơn ridge 0.265 với lưới ngắn + max_iter cố định dùng trong đợt này — đọc là "chưa thấy thuật toán phức tạp hơn thắng trên ~740 cặp trong cấu hình thử", KHÔNG phải "thuật toán phức tạp hơn chắc chắn không giúp gì" (1 lần chạy, chưa điều chỉnh multiple-testing).
- **CLF:** mở rộng lưới C vô hiệu trong đợt này — lưới 3 điểm công bố đã chứa đỉnh (C2: Δ +0.0000, beat 0/6); spread 0.0660 (`candidates_classification.md:64`) cho thấy đỉnh không nằm ngoài {0.1–1.0}.
- **CLUS:** cả 12 ứng viên không tái lập phân hoạch STING đóng băng (ARI non-noise tối đa 0.0742 ≈ 0); KMeans/Ward silhouette cao hơn là đổi câu hỏi, không phải thắng.
- **Quy tắc đọc:** "đừng thử lại theo hướng này" chỉ có giá trị như ưu tiên mặc định tiết kiệm công sức; nếu GV có lý do thiết kế mới (feature mới, nhãn mới, dữ liệu mở rộng) thì hướng này mở lại bình thường — bằng chứng chống là exploratory, không phải kết luận đóng.

### 4.4 Bài học cấu trúc cho iteration sau

- **Giả thuyết làm việc (chưa phải kết luận cấu trúc):** trong đợt này, cải thiện lớn nhất đến từ xử lý mất cân bằng nhãn (class_weight: C1 +0.0519, C3 +0.0896 vs LR), không phải từ thuật toán phức tạp hơn (R2/R3 đều worse). Suy ra từ đúng 2 win CV trên pseudo-label — chưa qua holdout, không có ước lượng nhiễu; trình bày như giả thuyết chờ xác nhận (holdout + GV), không phải phát hiện chắc chắn.
- Deconfound CLUS cho thấy chỉ đổi chuẩn hóa (z-trong-năm thay scaler pooled) đã làm ARI non-noise của chính STING rơi còn **0.0060** — mọi so sánh phân cụm tương lai phải kèm cột **"vs refit"** cùng tiền xử lý, nếu không sẽ đọc nhầm hiệu ứng scaler thành hiệu ứng thuật toán.

### 4.5 Còn lại chưa làm

- RF `class_weight='balanced_subsample'` được đề bài lane nêu là tuỳ chọn nhưng **NOT_RUN** (`results/candidates_classification.md:82` — lý do: giữ đúng bộ 3 ứng viên pre-registered). Trạng thái treo chờ GV quyết: chạy như combo bổ sung (đánh dấu riêng) hoặc loại chính thức khỏi danh sách — không tự chạy khi chưa được yêu cầu.

### 4.6 Ba cửa sổ lệch nhau 740 / 738 / 747 — do định nghĩa khác nhau

- **740 (REG)** = số cặp (đặc trưng năm t → đích năm t+1) đủ điều kiện của builder hồi quy (`candidates_regression.md:10`).
- **738 (CLF)** = số cặp phân loại — builder phân loại tạo HAI TẬP DÒNG khác builder hồi quy vì điều kiện hợp lệ cặp khác nhau (nhãn cần labeler fit tới cutoff); đã ghi rõ ở `reports/model_deep_dive.md:270`.
- **747 (CLUS)** = TẤT CẢ dòng tỉnh-năm ≤ 2022, không cần ghép cặp (`candidates_clustering.md:8`).
- Ba lane trả ba câu hỏi khác nhau nên số dòng không nhằm khớp nhau; có nên thống nhất một cửa sổ chung cho iteration sau là quyết định thiết kế thuộc GV (nhóm (b)) — tài liệu này không tự thống nhất.

### 4.7 Câu hỏi mở chờ GV quyết (tài liệu ghi nhận, KHÔNG tự trả lời)

1. **Pseudo-label (sắc nhất):** macro-F1 cao hơn trên nhãn STING đo "khớp máy gán nhãn hơn", chưa chứng minh dự báo thật tốt hơn — chưa có phương án đối chứng (vd nhãn ground-truth nào đó để chấm lại C1/C3); xác nhận duy nhất hiện có là holdout 1 lần sau duyệt (mục 4.2).
2. **Ngưỡng (i) chấp nhận mọi biên:** R1 +0.0018 nhỏ hơn nhiễu best_score_ cho thấy điều kiện (i) hiện không screen được biên mỏng — đề xuất GV cân nhắc quy tắc biên tối thiểu cho các lần sau (không áp dụng hồi tố cho đợt này).
3. **Tiêu chí CLUS thoái hóa:** tiêu chí nguyên văn (ARI > mốc = 1.0) không thể đạt; re-spec thành ARI-vs-refit khả thi vì cột số liệu đã có (`candidates_clustering.md:19`) — quyết định re-spec và chạy lại thuộc GV.
4. **Metric dưới prevalence trôi 44→92%:** macro-F1 có thể ưu model học drift; balanced accuracy / F1-per-class / PR-AUC là xác nhận bổ sung nếu GV yêu cầu — NOT_RUN trong đợt này.
5. **Commit để neo hash:** 9 tệp lane + tài liệu này đều untracked — hash đối chiếu (mục 5, 6) hiện chỉ tồn tại trong tài liệu; khuyến nghị commit sớm để hash có mốc vĩnh viễn (quyết định thuộc chủ repo/GV).

## 5) Kỷ luật thực nghiệm

- **Multiple-testing:** ma trận exploratory — REG 21 combo × 6 fold (21 = 6 lưới R1 + 6 R2 + 6 R3 + 3 R4 poverty, baseline gate không tính vào 21 — `candidates_regression.md:5`), CLF 24 combo × 6 fold (144 fit), CLUS 12 combo × 1 cửa sổ — nhiều nơi có thể vượt mốc do may rủi. KHÔNG tuyên bố p-value hay hiệu chỉnh alpha hình thức; guard chống fishing là **ngưỡng thắng pre-registered trước khi chạy** (REG `candidates_regression.md:50`; CLF `candidates_classification.md:36`; CLUS `candidates_clustering.md:12`), cấm trích 1 fold/combo đẹp, cấm đổi metric/fold sau khi thấy số, và duyệt GV cuối cùng. CLUS không có fold nên tiêu chí "≥4/6 fold" không áp dụng được — chỉ so ngang chỉ số trên cùng cửa sổ như pre-registered (`candidates_clustering.md:108`). Kỷ luật hiện tại thuần **thủ tục**, không thống kê: không có permutation/null test hay nested CV để ước lượng xác suất thắng-do-may; nhận định "nằm trong vùng nhiễu" (vd R1 +0.0018) là lập luận định tính dựa trên disclosure best_score_ đã công bố (`results/supervised_summary.md:32`), không phải đo đạc.
- **Seed 11:** seed lane 11 được khai báo theo quy ước (KMeans dùng seed 11; REG/CLF dùng seed 11 phòng hờ). Model giữ `random_state=42` đúng SEED công bố (`scripts/predict_supervised.py:72`); mọi bước còn lại (StandardScaler, LogisticRegression lbfgs, GridSearchCV n_jobs=1, DBSCAN, Ward) đều tất định nên seed lane không tác động kết quả (`candidates_classification.md:7`).
- **Deterministic ×2:** mỗi lane chạy 2 lần, so sha256 md/csv — REG: md `8bbdc6811ed2ffdcde4022a38dca2bcff59fc39ed6783ee405a844ab4a702060`, csv `f1a0280ce888cd56d644b7729170e9bae8b57720b38286c262642211e13bd733` byte-giống cả 2 lần (stdout cũng giống); CLF: md `b5422706…`, csv `38e4b07b…` byte-giống (diff rỗng); CLUS: lane tự báo ×2 byte-giống, hash lần đầu được ghi ở mục 6 để các phiên sau đối chiếu.
- **Fail-closed gates:** lệch gate baseline → script exit 1 không ghi output; cửa sổ/phân bố nhãn CLUS lệch → dừng với lỗi rõ ràng (`candidates_clustering.md:124`).

## 6) Kiểm tra trong phiên viết báo cáo (2026-11-08)

Ba kiểm tra dưới đây được **chạy lại trong phiên viết tài liệu này** và tái lập đúng kết quả lane báo cáo:

1. **Ruff toàn repo:** `python -E -m ruff check .` → `All checks passed!`, exit 0. Phân xử mâu thuẫn lane: REG báo FAIL 2×F821 tại `scripts/candidates_clustering.py:375,378`, CLF báo PASS — cây hiện tại PASS, finding F821 stale (file untracked, không truy được thời điểm sửa).
2. **Repo integrity:** `git diff --name-only` → output rỗng (0 tệp tracked sửa); `git status --porcelain` → đúng 9 tệp untracked = 3 script lane (`scripts/candidates_{regression,classification,clustering}.py`) + 6 artifact (`results/candidates_*.{md,csv}`); models/, slides/, data/processed/, artifact đóng băng không đụng. Kiểm tra lại sau khi ghi tài liệu này (lần 2, cùng ngày): tổng 10 tệp untracked — thêm `results/model_improvement_candidates.md`; 0 tệp tracked sửa.
3. **Determinism hash:** `sha256sum` trên 6 tệp `results/candidates_*` → REG md `8bbdc6811ed2ffdc…` và csv `f1a0280ce888cd5…` khớp đủ 64 ký tự với hash lane khai báo trong mục 5; CLF md `b54227066421a9e6…` và csv `38e4b07b06ddcef0…` khớp prefix; CLUS md `5b27eb2de3b1cff2…` và csv `1908d80bfdc3115c…` (hash lần đầu — chưa có mốc độc lập; neo vĩnh viễn cần commit — mục 4.7).

Cross-check thêm đã chạy trong phiên này: per-fold LR của lane CLF (0.3389 / 0.4089 / 0.4569 / 0.4309 / 0.4725 / 0.4968) đối chiếu khớp 6/6 với `reports/model_deep_dive.md:226-231` (mục 4.1); các trích dẫn dòng trong mục 2–5 đã được mở file đối chiếu (`predict_supervised.py:71,99,123,276-285,342-348,530-542`; `model_deep_dive.md:9-14,53,244-246,270,293-299`; `cluster_profile.md:34,97`; `supervised_summary.md:7,31,32`).

## 7) Tái lập và tệp nguồn

```powershell
python -E scripts/candidates_regression.py
python -E scripts/candidates_classification.py
python -E scripts/candidates_clustering.py
python -E -m ruff check .
```

- **Nguồn chi tiết (mỗi lane 1 md + 1 csv):** `results/candidates_regression.{md,csv}` · `results/candidates_classification.{md,csv}` · `results/candidates_clustering.{md,csv}` — tệp này chỉ tổng hợp và không thay thế chúng.
- **Đầu vào (chỉ đọc):** `papi_panel_63_2011_2024.csv` (provenance `87404305f36b`), `models/predict_config.json` (`9d8fa43aeb9f`), `results/predict_all_years.csv`, `results/supervised_metrics.csv`, `results/supervised_summary.md`.
- **Môi trường chạy lane:** python 3.14.2, sklearn 1.8.0, pandas 2.3.3, numpy 2.4.0 (`candidates_regression.md:80`).
- Tài liệu này KHÔNG ghi bất kỳ artifact đóng băng nào; quyền adopt thuộc GV.
