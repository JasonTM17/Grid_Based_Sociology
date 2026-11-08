# Báo cáo phân tích chuyên sâu model — `model_deep_dive` (v2)

**Ngày:** 2026-11-08 · **Phiên bản 2** — sửa theo góp ý của độc giả (khảo chỉ-đọc; nhật ký sửa ở 6.6) · **Nhánh:** `main` (`daaa214`)
**Đối tượng đọc:** sinh viên học Học máy (đọc để học cách phân tích một model đã đóng băng) + giảng viên (đọc để ra quyết định).
**Phạm vi:** 3 lane phân tích MỚI — A (độ nhạy giao thức chọn cấu hình), B (hồ sơ cụm × chỉ số ngoài + ổn định bootstrap), C (chiều sâu phần supervised). Toàn bộ lane **CHỈ THÊM** tệp phân tích mới vào `results/`, không thay đổi model đã đóng băng.

---

## Quy ước đọc — phân biệt hai loại kết quả

| Nhãn | Nghĩa là | Được dùng làm gì |
| --- | --- | --- |
| **[ĐÃ ÁP DỤNG]** | Số nằm trong artifact đã công bố, không đổi từ khi đóng băng (`models/predict_config.json`, `results/predict_config_search.csv`, `results/supervised_metrics.csv`, …) | Số chính thức của báo cáo/điểm số |
| **[THAM KHẢO — CHƯA DUYỆT GV]** | Lane chỉ chạy script mới / tính in-memory; **không đụng artifact đóng băng**; là đầu vào cho quyết định, không phải quyết định | Cân nhắc thay giao thức/cách diễn giải — quyền duyệt thuộc GV |

**Trạng thái repo** (tự báo cáo từ lệnh `git status --porcelain` — độc giả tái kiểm được bằng cách tự chạy lệnh này): **0 tệp tracked bị sửa**; tệp untracked gồm **13 tệp của 3 lane** + tệp báo cáo này:

- 3 script: `scripts/protocol_sensitivity.py`, `scripts/cluster_profile.py`, `scripts/supervised_depth.py`;
- 6 tệp md/csv: `results/protocol_sensitivity.{md,csv}`, `results/cluster_profile.{md,csv}`, `results/supervised_depth.{md,csv}`;
- 4 hình: `results/figs/protocol_sensitivity_grid.png`, `results/figs/deep_cluster_profile.png`, `results/figs/supervised_learning_curve.png`, `results/figs/supervised_importance.png`.

## Thuật ngữ dùng trong báo cáo (dành cho sinh viên)

| Thuật ngữ | Nghĩa trong báo cáo |
| --- | --- |
| **lane / ask / verify lane** | Quy trình của đợt phân tích: *lane* = một nhiệm vụ phân tích độc lập; *ask* = một lượt giao việc cho agent viết; *verify lane* = bước kiểm định độc lập sau lane. |
| **artifact đóng băng** | Tệp kết quả đã chốt và công bố (vd `models/predict_config.json`, `results/supervised_metrics.csv`) — mọi lane bị cấm GHI/SỬA các tệp này. |
| **PAPI · sd_X_Y** | sd_X_Y = tiểu chỉ số X.Y của PAPI. 8 tiểu chỉ số trong allowlist (tên đầy đủ, `results/supervised_depth.md:45-54`): sd_1_3 = 1.3 Chất lượng bầu cử · sd_1_4 = 1.4 Đóng góp tự nguyện · sd_4_1 = 4.1 Kiểm soát tham nhũng trong chính quyền địa phương · **sd_4_2 = 4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công** · sd_4_3 = 4.3 Công bằng trong tuyển dụng vào khu vực công · sd_4_4 = 4.4 Quyết tâm chống tham nhũng của chính quyền địa phương · **sd_6_1 = 6.1 Y tế công lập** · sd_6_3 = 6.3 Cơ sở hạ tầng căn bản. "28 cặp" = C(8,2) = 28 cách chọn 2 trong 8 tiểu chỉ số (`results/protocol_sensitivity.md:24-25`). |
| **PCI** | Provincial Competitiveness Index — Chỉ số Năng lực Cạnh tranh Cấp tỉnh, khảo sát doanh nghiệp (VCCI–USAID); thước đo NGOÀI panel. |
| **STING** | Thuật toán phân cụm dựa trên lưới thống kê (grid-based). Tham số: `n_levels` (số mức lưới), `factor` (hệ số chia lưới giữa hai mức liên tiếp), `min_count` (số dòng tối thiểu để một ô lưới đủ dày; ô không đủ → nhiễu −1), `cluster_level` (mức lưới dùng để trích cụm), `connectivity` (tùy chọn kết nối ô; đóng băng = 1). Ký hiệu **cfg "3/4/5/2"** = (n_levels, factor, min_count, cluster_level) = (3, 4, 5, 2) (`models/predict_config.json:12-18`; `results/protocol_sensitivity.md:24-25`). |
| **pseudo-label STING** | Nhãn cụm do STING sinh (không phải nhãn người gán) — dùng làm nhãn lớp cho LogisticRegression. |
| **train — HAI nghĩa (quan trọng)** | (i) *train của sweep/chọn cấu hình*: các cặp `year_t` ≤ 2020 — nguyên văn `models/predict_config.json:3` "Fit ≤2020"; `sizes_top5 [453, 16, 5]` trong `models/predict_config.json:21` và `results/predict_config_search.csv` là cụm trên cửa sổ này. (ii) *train của model đóng băng*: 808 dòng fit 2011–2023; cụm **[629, 16, 5]** là cấu trúc trên cửa sổ này (xem mục 1). Cùng một cấu hình, hai phạm vi dữ liệu. |
| **holdout** | Origin 2023 → đích 2024 (59 cặp). |
| **coverage_2021_2022** | Tỉ lệ ô thuộc "tương lai giả" 2021–2022 được gán nhãn cụm (không rơi vào nhiễu/thiếu chỉ tiêu). |
| **largest / largest_sửa / min_share / mcs** | `largest` = tỉ lệ dòng của cụm lớn nhất **trên tổng n**; `largest_sửa` = trên **n non-noise**; `min_share` = tỉ lệ cụm nhỏ nhất trên n non-noise; `mcs` = `MIN_CLUSTER_SHARE`, ngưỡng cho min_share (`results/protocol_sensitivity.md:34-40`). |
| **Bộ lọc CŨ (đóng băng)** | k ∈ [2, 6]; noise_train ≤ 0.25; largest (trên tổng n) ≤ 0.85; coverage ≥ 0.75; không có ràng buộc cụm nhỏ nhất (`models/predict_config.json:3`; `results/protocol_sensitivity.md:34-41`). |
| **score / score_sửa / stable_mc_pm1** | Công thức đóng băng (`models/predict_config.json:3`): **score = coverage − 0.5·noise − 0.15·largest − 0.02·&#124;k−3&#124; + 0.03·stable** (stable = cờ "ổn định khi đổi min_count ±1" — `stable(mc±1)`; True → +0.03, False → +0). `score_sửa` = cùng trọng số, thay `largest` bằng `largest_sửa` (`results/protocol_sensitivity.md:41-47`). |
| **B5** | Mã câu hỏi nghiên cứu của lane A — "largest trên tổng n vs trên non-noise". Nguồn hiện có trong repo: tiêu đề `results/protocol_sensitivity.md:1`; mã được đặt bởi đề bài đợt phân tích. |
| **Jaccard / k′ / giữ nhãn** | Jaccard = &#124;A∩B&#124;/&#124;A∪B&#124; của hai tập dòng — đo độ giống hai cụm khi ghép nhãn mẫu↔gốc. `k′` = số cụm của phân hoạch refit trên mẫu bootstrap (ký hiệu riêng, không nhầm k=3 của model gốc). Một dòng "giữ nhãn" khi về đúng trạng thái gốc (nhiễu→nhiễu hoặc cụm c→cụm ghép về c) (`results/cluster_profile.md:90`). |
| **0-thật** | Giá trị 0 là số liệu thật (nguồn điểm không phủ tỉnh đó), không phải missing do nối tên lỗi (`results/cluster_profile.md:60`). |
| **carry-forward** | Baseline hồi quy "dự báo năm sau = giá trị năm nay" — CV R² = 0.145 (`results/supervised_metrics.csv`, dòng `carry-forward (giữ giá trị năm nay)`). |
| **permutation importance** | Mean của (R² trước − R² sau khi hoán vị ngẫu nhiên cột) qua n_repeats lần; cột càng quan trọng, R² giảm càng nhiều. Có thể **>1** khi R² sau hoán vị âm sâu (giải thích tại mục 4.2). |
| **in-sample vs holdout** | Tính trên tập đã học vs tập ngoài mẫu. |
| **cluster bootstrap** | Resample có hoàn lại theo ĐƠN VỊ cụm (tỉnh), không theo từng dòng — giữ tương quan trong tỉnh. |

---

## 1. Tóm tắt điều hành

**Model đang ở đâu [ĐÃ ÁP DỤNG — không đổi].** Cấu hình đóng băng ghi trong `models/predict_config.json` (nguồn gốc chính thức): features **sd_4_2+sd_6_1** (`models/predict_config.json:4-11`) × STING(3, 4, 5; cluster_level=2, connectivity=1) (`models/predict_config.json:12-18`).

- **Hai bộ "train" của cùng một cấu hình** (giảng viên thường hỏi): chỉ số lựa chọn lưu chính thức trong config là trên cửa sổ fit ≤2020 — `k=3, sizes [453, 16, 5], noise 0.243, coverage 0.851, score 0.6213` (`models/predict_config.json:19-26` = `results/predict_config_search.csv` dòng pass đầu). Còn **k=3, cụm [629, 16, 5]** là cấu trúc khi model đóng băng được fit trên **808 dòng 2011–2023** — cấu trúc này KHÔNG nằm trong tệp config; nó được tái lập từ `results/predict_all_years.csv` (nhãn của model đóng băng) và kiểm chứng 808/808 nhãn trong `results/cluster_profile.md:13-15`, `:6`. Hai bộ số khác **phạm vi dữ liệu**, không mâu thuẫn (xem Thuật ngữ "train").
- Supervised [ĐÃ ÁP DỤNG]: Ridge CV R² **0.265** · holdout MAE **0.0640** · RF CV R² **0.197** (`results/supervised_metrics.csv`, dòng `ridge` cột `metric_cv`/`holdout_mae` và dòng `random forest` cột `metric_cv`); baseline carry-forward (dự báo năm sau = năm nay) CV R² **0.145** (cùng tệp, dòng `carry-forward`). External validation PCI đã công bố: ANOVA F(3,743) = 9.0426, Kruskal H = 31.7751 (`results/external_validation.md:16-17`).

**Ba phát hiện mới — tất cả [THAM KHẢO — CHƯA DUYỆT GV]:**

1. **Lane A — không có ứng viên thay thế theo bộ lọc sửa.** Mô phỏng bộ lọc chặt hơn (cân bằng cụm tính trên non-noise + ngưỡng `MIN_CLUSTER_SHARE`) trên đúng 224 tổ hợp: **0/224 pass tại cả ba mcs {0.02, 0.05, 0.10}**; điểm cao nhất toàn bảng là giải suy biến k=1; cấu hình đóng băng tự nó cũng fail bộ lọc sửa (`results/protocol_sensitivity.md:68`, `:122-128`). → Kết luận **đúng trong phạm vi giả định B5**: nếu coi "cân bằng trên non-noise" là chuẩn đánh giá đúng thì không có ứng viên thay thế. Việc bộ lọc sửa có nên trở thành chuẩn hay không **là quyết định của GV (mục 5b.2)** — tóm tắt này không chốt hướng.
2. **Lane B — external validation giữ ở cặp tương phản lớn, vỡ ở cụm li ti.** PCI vẫn khác biệt mạnh (H = 31.7751, tái hiện đúng số công bố trên cùng join 747 ô); nghèo, GRDP, y tế, đô thị không phân hóa theo cụm. Bootstrap 200 lần (seed 11, resample theo tỉnh): giữ nhãn trung bình 0.8742, nhưng cụm li ti 0/1 chỉ giữ nhãn 14.5% / 49.8% — chỉ cặp **nhiễu vs cụm 2** đáng tin (`results/cluster_profile.md:34`, `:94-104`, `:127`).
3. **Lane C — phần supervised chủ yếu là tự tương quan thời gian.** Permutation importance bị `sd_6_1` chiếm áp đảo (mean giảm R² = 0.9928 trên train; #2 chỉ 0.0305) — và `sd_6_1` chính là biến đích năm trước của pipeline (`scripts/papi_pred_common.py:19-23`). macro-F1 phân loại tăng tổng thể 0.3942 → 0.4968 (2/6 bước giảm); residual trên holdout dương (dự báo THẤP hơn thực tế 2024), tỉnh nhỏ lệch hơn tỉnh lớn (`results/supervised_depth.md:47-49`, `:29-35`, `:73-97`).

**Đọc gộp (mô tả, chưa duyệt):** những gì vững là cụm lớn + tương phản nhiễu; những gì mong manh là cụm li ti và độ quan trọng của các đặc trưng ngoài `sd_6_1`. Danh sách hành động đã tách theo quyền duyệt ở mục 5; **nhóm viết báo cáo không tự chốt thay đổi nào**.

---

## 2. Lane A — Độ nhạy giao thức chọn cấu hình (kết quả MÔ PHỎNG)

> **⚠️ TRẠNG THÁI: PHÂN TÍCH THAM KHẢO CHO QUYẾT ĐỊNH THAY CẤU HÌNH — CẦN GV DUYỆT. KHÔNG phải thay đổi đã áp dụng.** Script chạy in-memory: không ghi `models/predict_config.json`, không lưu model, không thực thi `scripts/predict_sweep.py` (`results/protocol_sensitivity.md:3-5`). *Ngoại lệ*: các số tái lập bộ lọc CŨ ở 2.1 là giá trị **[ĐÃ ÁP DỤNG]** (đã công bố) được script tái tạo nguyên vẹn — được gắn nhãn riêng tại bảng.

**Câu hỏi nghiên cứu (B5 — mã đề bài của lane A, xem Thuật ngữ):** nếu định nghĩa "cụm lớn nhất chiếm bao nhiêu" trên **n non-noise** thay vì **n tổng**, và thêm ràng buộc cụm nhỏ nhất ≥ `MIN_CLUSTER_SHARE` (mcs) — bộ chọn cấu hình sẽ pick ai? Độ nhạy trên mcs ∈ {0.02, 0.05, 0.10}.

### 2.1 Bước bắt buộc: tái lập bộ lọc CŨ trước khi tin bộ lọc SỬA

Script tái hiện nguyên văn preprocessing của `scripts/predict_sweep.py` (train ≤ 2020, dropna có cột `year` `predict_sweep.py:118`, ngưỡng 500/100 `predict_sweep.py:120`, 224 tổ hợp = 28 cặp × 8 cấu hình STING `predict_sweep.py:49-52`) — `results/protocol_sensitivity.md:15-28`.

- **224/224 dòng khớp từng trường** (k, sizes_top5, noise, largest, coverage, stable, score, pass) và **khớp cả THỨ TỰ** 224 dòng sau sort (`results/protocol_sensitivity.md:51-54`).

**[ĐÃ ÁP DỤNG]** Bốn dòng pass dưới đây là số công bố của `results/predict_config_search.csv` (4 dòng có `pass=True`), được script mô phỏng tái lập nguyên vẹn (`results/protocol_sensitivity.md:59-64`):

| features | cfg | k | sizes_top5 (fit ≤2020) | noise | largest | coverage | stable | score |
|---|---|---|---|---|---|---|---|---|
| sd_4_2+sd_6_1 | 3/4/5/2 | 3 | [453, 16, 5] | 0.243 | 0.724 | 0.851 | False | **0.6213** |
| sd_1_3+sd_6_3 | 3/3/8/2 | 2 | [485, 11] | 0.210 | 0.772 | 0.844 | False | 0.6033 |
| sd_4_3+sd_6_3 | 3/3/8/2 | 2 | [483, 8] | 0.216 | 0.772 | 0.843 | False | 0.5994 |
| sd_1_4+sd_4_2 | 3/4/5/2 | 2 | [479, 6] | 0.225 | 0.765 | 0.802 | False | 0.5543 |

*Lưu ý hai bộ sizes*: `sizes_top5` ở đây là trên tập **fit ≤2020** của sweep (`models/predict_config.json:3`); trên bộ fit 2011–2023 của model đóng băng, cùng cấu hình cho **[629, 16, 5]** (mục 1) — khác phạm vi dữ liệu, không phải mâu thuẫn.

**Kiểm tra số học ngay trong văn bản** (dòng 1, công thức ở Thuật ngữ — độc giả tự cộng được): k=3 ∈ [2,6] ✓ · noise 0.243 ≤ 0.25 ✓ · largest 0.724 ≤ 0.85 ✓ · coverage 0.851 ≥ 0.75 ✓; score ≈ 0.851 − 0.5×0.243 − 0.15×0.724 − 0.02×0 + 0 = **0.6209** so với công bố **0.6213** — chênh 0.0004 do các thành phần hiển thị đã làm tròn 3 số lẻ (script tính từ giá trị chưa làm tròn). Đây là kiểm tra tính nhất quán, không phải tái tính chính xác.

### 2.2 Phát hiện chính B5: KHÔNG có ứng viên nào pass bộ lọc sửa — 0/224

**[THAM KHẢO — CẦN GV DUYỆT]** (`results/protocol_sensitivity.md:66-69`)

- **0/224 pass tại mcs = 0.05; 0/224 tại mcs = 0.02; 0/224 tại mcs = 0.10** (`results/protocol_sensitivity.md:122-126`). Do đó **không có "winner mới" hợp lệ** — đây được ghi đúng như phát hiện, không bịa winner.
- Số tổ hợp phạm từng điều kiện (một tổ hợp có thể phạm nhiều): coverage 59, k 168, largest 219, min_share 57, noise 57 (`results/protocol_sensitivity.md:69`). Ràng buộc gắt nhất là **largest_sửa** (219/224 phạm).

**Top-1 theo điểm toàn bảng là giải suy biến k=1** (`results/protocol_sensitivity.md:78-84`): `sd_1_3+sd_6_3` (2/3/12/1), k=1, sizes [628], noise 0.000, largest = largest_sửa = 1.0000. Quy ước gọi số trong báo cáo này: với tổ hợp k=1 này **score cũ = score_sửa = 0.8400** (hai công thức cho cùng số vì largest = largest_sửa = 1.0) — mọi chỗ dưới đây chỉ gọi "score". Tổ hợp fail ngay `k+largest`, không phải ứng viên (md gắn nhãn rõ).

**Contender hợp lệ gần đạt nhất** (trong nhóm đạt k/noise/coverage — 16/224 tổ hợp; `results/protocol_sensitivity.md:71`): `sd_1_3+sd_6_3` (3/3/8/2) — vẫn fail 2 điều kiện: min_share = 0.0222 (thiếu 0.0278 để đạt 0.05), largest_sửa = 0.9778 (vượt 0.1278). Score công thức cũ của nó là 0.6033 — **thấp hơn** cấu hình đóng băng 0.0180.

### 2.3 Vì sao nới mcs không cứu được

Chỉ **5/224** tổ hợp có largest_sửa ≤ 0.85, và cả 5 đều có noise_train 0.401–0.712 cùng coverage 0.322–0.525 — cụm "cân bằng" trên non-noise chỉ xuất hiện kèm mức nhiễu và mất phủ không chấp nhận được (`results/protocol_sensitivity.md:128`). Nới mcs xuống 0.02 không đổi số pass vì ràng buộc bị phạm là largest, không phải min_share.

### 2.4 Cấu hình đóng băng tự nó dưới bộ lọc sửa

Định danh đóng băng **không hardcode** — script suy ra lúc chạy từ dòng pass điểm cao nhất của `results/predict_config_search.csv` và đối chiếu với tên trong đề bài: khớp (`results/protocol_sensitivity.md:102-103`).

| Đại lượng | Giá trị | Nguồn |
| --- | --- | --- |
| score công bố (bộ lọc cũ) | 0.6213 | `models/predict_config.json:25` = `results/protocol_sensitivity.md:107` |
| largest theo tổng n (cũ) / largest_sửa (non-noise) | 0.7236 / **0.9557** (vượt 0.85 thêm 0.1057) | `results/protocol_sensitivity.md:109-110` |
| min_share (non-noise) | 0.0105 (thiếu 0.0395 so với mcs=0.05) | `results/protocol_sensitivity.md:111` |
| score_sửa của cấu hình đóng băng | 0.5865 | `results/protocol_sensitivity.md:112` |
| pass bộ lọc sửa (mcs 0.02/0.05/0.10) | False / False / False | `results/protocol_sensitivity.md:113` |
| khoảng cách score_sửa: top-1 toàn bảng − đóng băng | 0.2535 | `results/protocol_sensitivity.md:114` |
| khoảng cách score cũ: top-1 (0.8400) − 0.6213 | 0.2187 | `results/protocol_sensitivity.md:115` |

→ Cấu hình đóng băng được chọn theo bộ lọc cũ nằm ngoài vùng "cân bằng trên non-noise": cụm nhỏ nhất chỉ ~1% non-noise. Đây **không phải lỗi** — đó là hệ quả của một định nghĩa khác — nhưng nó là bằng chứng định lượng cho quyết định của GV (mục 5b.2).

### 2.5 stable_mc_pm1 và các quyết định diễn giải (execution ruling)

- Top-1 toàn bảng (k=1): stable_mc_pm1 = **True**; contender gần đạt nhất (3/3/8/2): **False** — trùng stable=False của cả 4 dòng pass cũ (`results/protocol_sensitivity.md:130-133`).
- **Ruling (ghi rõ trong md mục 2):** score_sửa dùng cùng trọng số nhưng thay biến `largest` bằng `largest_sửa` vì đề bài B5 định nghĩa lại biến này ở bộ lọc sửa; CSV giữ **cả hai cột** `score`/`score_mod` để đối chiếu (`results/protocol_sensitivity.md:44-47`; cột thấy trong `results/protocol_sensitivity.csv` header).
- **Seed 11 không tác động kết quả** — pipeline không có bước ngẫu nhiên (STING lưới thống kê + StandardScaler đều deterministic; không bootstrap/permutation) (`results/protocol_sensitivity.md:26-28`).

### 2.6 Bài học ML (cho sinh viên)

1. **Điểm số không thay thế được ràng buộc.** Giải k=1 đạt score cao nhất (0.84) vì công thức điểm thưởng cho coverage/noise hoàn hảo của một cụm duy nhất. Điểm + bộ lọc k∈[2,6] phải đi cùng nhau; khi thêm điều kiện mới, hãy kiểm tra lại top điểm nằm ở đâu.
2. **Thay đổi định nghĩa biến quan trọng hơn thay đổi ngưỡng.** Nới mcs 0.02→0.10 không đổi gì; đổi mốc chia mẫu (tổng n → non-noise) đảo ngược thứ hạng toàn bộ. Đọc kỹ định nghĩa trước khi tối ưu ngưỡng.
3. **Luôn tái lập baseline trước khi tin số mới.** 224/224 khớp + khớp thứ tự là điều kiện để kết quả bộ lọc sửa đáng tin.

### 2.7 Kiểm định lane A

- Deterministic: lane **tự báo cáo** chạy `python -E scripts/protocol_sensitivity.py` 2 lần cho md/csv/png sha256 byte-giống (`results/protocol_sensitivity.md:148-151`). Ask v1 **không tái diễn được** kiểm chứng này vì chạy lại sẽ ghi đè artifact; bằng chứng thay thế: hash hiện tại khớp tuyên bố (6.3) + code không có nguồn thời hệ thống/ngẫu nhiên. Phương án kiểm chứng không-ghi-đè (chạy script với thư mục output tạm) **chưa làm — NOT_RUN**, xem 6.4.
- Gate: `python -m ruff check .` → *All checks passed!*; `python -E -m pytest -q` → *101 passed*; `git diff --stat` rỗng (lane báo cáo; **ask v1 đã chạy lại cả hai gate — phụ lục 6.4**).
- **Hình PNG**: nhãn "mcs=0.02" chồng nhẹ lên mũi tên chú thích cấu hình đóng băng (vẫn đọc được). Quyết định **giữ nguyên để bảo toàn hash** là đánh đổi cụ thể: hash chỉ chứng minh *tệp không đổi*, không chứng minh *hình đúng/đẹp* — nguyên tắc này KHÔNG nên là mặc định chung; sửa hình chỉ làm trong đợt re-run được duyệt để sinh hash mới (5b.5).

---

## 3. Lane B — Hồ sơ cụm × chỉ số ngoài + ổn định bootstrap

> **⚠️ TRẠNG THÁI: [THAM KHẢO — CHƯA DUYỆT GV].** Phân tích MỚI, đọc-only — đọc `results/predict_all_years.csv`, panel, 5 tệp external CSV và `models/predict_config.json` (chỉ đọc); không thay artifact nào (`results/cluster_profile.md:3`, `:135-138`). Các số dưới đây **chưa phải số chính thức** cho tới khi GV duyệt.

### 3.0 Cấu trúc nhãn trước khi đọc các bảng

Nhãn cụm tỉnh-năm từ model đóng băng (fit 2011–2023): `results/cluster_profile.md:10-17` —
nhiễu (−1): **171** tỉnh-năm / 56 tỉnh · cụm 0: **5** / 5 tỉnh (chỉ 2011–2015) · cụm 1: **16** / 12 tỉnh (chỉ 2011–2018) · cụm 2: **677** / 63 tỉnh.

**Đối chiếu với "808 dòng train"** (giảng viên sẽ hỏi): bảng phổ nhãn tính trên `results/predict_all_years.csv` — **toàn bộ 2011–2024, tổng 869 tỉnh-năm**. Phần fit của model đóng băng là **2011–2023 = 808 dòng** (cột split trong md nguồn): nhiễu train 158 / cụm 0 train 5 / cụm 1 train 16 / cụm 2 train 629 — tổng đúng 808, và **[629, 16, 5]** là cấu trúc trên bộ này. Phần ngoài fit = 61 dòng năm 2024 (13 nhiễu + 48 cụm 2); nhiễu train = 158.

> Đọc trục này trước: 1 cụm lớn + 2 cụm li ti + vùng nhiễu. p-value với nhóm n=5 hay n=16 **không chứng minh** cụm nhỏ là "kiểu tỉnh" độc lập (`results/cluster_profile.md:21`).

### 3.1 Kruskal–Wallis: nhóm cụm × 5 chỉ số ngoài

Tổng hợp từ `results/cluster_profile.md` mục 2 (mỗi chỉ số có bảng trung vị/mean/sd theo nhóm trong md); thống kê tất định (không dùng seed).

| Chỉ số (nguồn) | Khoảng dữ liệu | n (df) | H | p | Đọc |
| --- | --- | --- | --- | --- | --- |
| PCI weighted (VCCI–USAID) | 2011–2022 | 747 (3) | **31.7751** | **5.84e-07** | Khác biệt có ý nghĩa — tái hiện đúng H=31.78 đã công bố (`results/cluster_profile.md:34`; đối chiếu `results/external_validation.md:16`) |
| Tỷ lệ nghèo (GSO V14.47) | 2012–2024 (13 năm giao) | 805 (3) | 4.6670 | 0.198 | Không đáng kể; trùng "gộp thô" của `results/poverty_validation.md:28` |
| Mật độ y tế/1000 dân (OD Mekong) | 2020 (1 năm) | 63 (1) | 2.0147 | 0.156 | Không đáng kể; chỉ nhóm −1 (6) vs 2 (57); 10 tỉnh count=0 là 0-thật (`results/cluster_profile.md:60`) |
| GRDP/người (GSO V03.12) | 2018–2024 | 430 (2) | 9.4963 | 0.00867 | Đáng kể về số, **nhưng cụm 1 chỉ có n=1** (trung vị 104.42) — nhóm n=1 không mang thông tin thống kê; md nguồn tự xếp "chỉ đọc mô tả" (`results/cluster_profile.md:66-72`). Loại nhóm n=1 rồi tính lại là phân tích mới — chưa làm (NOT_RUN) |
| % dân số đô thị (GSO V02.01) | 2012–2022 (các năm nguồn có số) | 495 (3) | 2.1520 | 0.541 | Không khác biệt |

Trung vị PCI theo nhóm — nhiễu 59.16 · cụm 0 58.47 (n=5) · cụm 1 58.19 (n=16) · cụm 2 **62.16** (n=577): cụm lớn có PCI cao hơn vùng nhiễu; hai cụm li ti nằm giữa (`results/cluster_profile.md:27-34`).

**Điểm external validation** (nguyên văn là nhận định của `results/external_validation.md:19`, không phải kiểm chứng độc lập của báo cáo này): PCI là thước đo ĐỘC LẬP chưa từng dùng khi học — cấu trúc cụm STING tương ứng với nó trên cặp tương phản đáng tin (nhiễu vs cụm 2). KHÔNG chứng minh quan hệ nhân quả.

### 3.2 Ổn định bootstrap — 200 lần, seed 11, resample theo TỈNH

**Phương pháp** (`results/cluster_profile.md:5`, `:89-90`; seed tại `scripts/cluster_profile.py:61`, `:317`): mỗi lần rút 63 tỉnh **có hoàn lại**, mẫu = toàn bộ dòng fit (2011–2023, 808 dòng gốc) của các tỉnh được rút (cluster bootstrap panel — tôn trọng tương quan trong tỉnh). Refit ĐỒNG CẤU HÌNH đóng băng (scaler fit trên mẫu + STING + cluster(level=2, connectivity=1)). Khớp nhãn mẫu → gốc bằng ghép cặp 1-1 tối ưu tổng Jaccard (`scipy.optimize.linear_sum_assignment`). Kiểm chứng tất định: refit đúng công thức cho lại **808/808** nhãn train (`results/cluster_profile.md:6`).

| Đại lượng | mean | median | sd | CI95 | Nguồn |
| --- | --- | --- | --- | --- | --- |
| Tỉ lệ giữ nhãn — toàn bộ dòng | **0.8742** | 0.8746 | 0.0340 | [0.8138, 0.9407] | `results/cluster_profile.md:94` |
| Silhouette (non-noise) | **0.1675** | 0.1619 | 0.1352 | [−0.0602, 0.4198] | `results/cluster_profile.md:95` |

- Silhouette chỉ tính được khi refit cho **≥2 cụm non-noise**: **198/200 lần hợp lệ, 2/200 bị loại** khỏi phân bố silhouette (`results/cluster_profile.md:90`, `:95`).
- Tham chiếu silhouette model gốc trên train (non-noise) = **0.3611** (`results/cluster_profile.md:97`). Md nguồn **diễn giải** phân bố bootstrap thấp hơn là "chi phí của việc rút lại tỉnh (mẫu lệch + trùng bản sao), không phải lỗi cài đặt" — đây là **diễn giải của nguồn**, lane không có thí nghiệm đối chứng (vd một kiểu resample khác) để tách biến; đọc như giả thuyết giải thích.

**Giữ nhãn gộp theo nhãn gốc (200 lần):** `results/cluster_profile.md:99-110`

| Nhãn gốc | Tỉ lệ giữ nhãn gộp | Được ghép (Jaccard>0) | Jaccard TB |
| --- | --- | --- | --- |
| nhiễu (−1) | 66.8% | 200/200 | – |
| cụm 0 | **14.5%** | **29/200** | 0.085 |
| cụm 1 | **49.8%** | **161/200** | 0.440 |
| cụm 2 | **94.1%** | 200/200 | 0.889 |

**Phân bố k′ của refit:** thường >3 (mode ở k′=5: 42/200; trải tới k′=13: 1/200) — vì min_count=5 tuyệt đối dưới resample làm nhiều ô đạt ngưỡng dày (`results/cluster_profile.md:112-127`).

**Đọc tỉ lệ giữ nhãn LUÔN kèm hình dạng phân hoạch** (giảng viên sẽ hỏi): 0.8742 đo việc các dòng về đúng cụm gốc qua ghép cặp tối ưu, trong khi phân hoạch mẫu thường có k′=5 ≠ k=3 — hai phân hoạch **khác hình dạng**; chỉ số vẫn có nghĩa (dòng có về đúng cụm gốc nào không) nhưng không mô tả "model tái lập đúng 3 cụm". Đọc kèm bảng k′ và bảng Jaccard theo cụm ở trên.

**Đọc kết quả** (`results/cluster_profile.md:127`): cụm lớn + nhiễu tái lập gần như chắc chắn; cụm li ti 0/1 phụ thuộc việc các tỉnh "sáng lập" chúng có được rút vào mẫu hay không. **Kết luận vững chỉ nên dựa trên tương phản nhiễu vs cụm 2** — nhất quán với cảnh báo đã có sẵn: cụm 0 (n=5) và cụm 1 (n=16) quá nhỏ để tự kết luận (`results/external_validation.md:19`).

### 3.3 Các quyết định diễn giải khi đặc tả thiếu chi tiết (đã ghi trong md nguồn)

Đơn vị resample = tỉnh trên bộ dòng fit gốc 2011–2023 (không dùng panel đã làm tròn vì CSV nhãn chỉ lưu feature làm tròn 3 số thập phân — panel được đọc-only); silhouette tính trên điểm non-noise với scaler của mẫu, lần refit ra <2 cụm non-noise bị loại (198/200 hợp lệ — `results/cluster_profile.md:90`, `:95`); `add_source` truyền phần text sau "Nguồn:" để tránh double prefix (chi tiết trong md nguồn).

### 3.4 Bài học ML (cho sinh viên)

1. **Cluster bootstrap ≠ row bootstrap.** Với panel, rút lại **đơn vị cụm** (tỉnh) chứ không rút từng dòng — rút dòng sẽ phá tương quan trong tỉnh và làm ảo độ tin cậy.
2. **Ổn định là thuộc tính của từng cụm, không phải của model.** Một model có tỉ lệ giữ nhãn trung bình 0.87 vẫn có thể có cụm giữ nhãn 14.5% — luôn xem phân bố theo thành phần.
3. **Silhouette dưới resampling thấp hơn silhouette gốc là bình thường**; so sánh phải cùng điều kiện (gốc 0.3611 trên train vs bootstrap mean 0.1675) — và lời giải thích nhân quả cho chênh lệch cần thí nghiệm đối chứng, không chỉ lập luận.

---

## 4. Lane C — Chiều sâu supervised (learning curve, importance, residual)

> **⚠️ TRẠNG THÁI: [THAM KHẢO — CHƯA DUYỆT GV].** Chỉ MÔ TẢ, không chọn model — không chọn model/siêu tham số/đặc trưng trên holdout; tái dùng nguyên pipeline `scripts/predict_supervised.py` (`results/supervised_depth.md:1`, `:109-116`). Các số dưới đây **chưa phải số chính thức** cho tới khi GV duyệt.

### 4.0 Siêu tham số cố định + kiểm đối pipeline (bắt buộc trước khi đọc tiếp)

- Siêu tham số CỐ ĐỊNH (chọn một lần bởi CV train-only expanding origin 2017–2022 của pipeline, tính lại trong bộ nhớ, không dựa holdout): **Ridge alpha=0.1 · LogisticRegression C=1.0 · RF max_depth=4, min_samples_leaf=2** (`results/supervised_depth.md:6`).
- Kiểm đối: tái tính trong bộ nhớ cho **ridge CV R² = 0.265 / holdout MAE = 0.0640 / RF CV R² = 0.197 — KHỚP 100%** `results/supervised_metrics.csv` (dòng `ridge`: cột `metric_cv` = 0.265, cột `holdout_mae` = 0.064; dòng `random forest`: cột `metric_cv` = 0.197) (`results/supervised_depth.md:7`).
- Seed: model giữ seed **42** của pipeline (`scripts/predict_supervised.py:72` — đặc tả đã công bố); permutation importance dùng seed **11**, n_repeats=30 (`scripts/supervised_depth.py:96`, `results/supervised_depth.md:5`).

### 4.1 Learning curve expanding origin 2016→2022 (không đụng holdout)

Mỗi điểm = train trên mọi cặp `year_t < v`, chấm trên đúng origin `v`; trục x = số năm train. Holdout 2023→2024 không tham gia (`results/supervised_depth.md:9-11`).

| Origin | Số năm train | Ridge R² | LR macro-F1 | Nguồn |
| --- | --- | --- | --- | --- |
| 2016 | 5 | 0.4588 | 0.3942 | `results/supervised_depth.md:17,29` |
| 2017 | 6 | 0.1978 | 0.3389 | `:18,30` |
| 2018 | 7 | 0.1733 | 0.4089 | `:19,31` |
| 2019 | 8 | 0.3198 | 0.4569 | `:20,32` |
| 2020 | 9 | 0.0998 | 0.4309 | `:21,33` |
| 2021 | 10 | 0.4515 | 0.4725 | `:22,34` |
| 2022 | 11 | 0.3488 | **0.4968** | `:23,35` |

**Đọc (mô tả, không có kiểm định xu hướng — hai đường dùng cùng một tiêu chuẩn):**
- **Ridge R²** dao động 0.0998–0.4588, **không thấy xu hướng đơn điệu** trong 7 điểm. Nguyên nhân khả dĩ là phân phối theo năm thay đổi giữa các cửa sổ — **giả thuyết**, lane không kiểm định.
- **LR macro-F1** tăng tổng thể 0.3942 → 0.4968 với **2/6 bước giảm** (2016→2017: −0.0553; 2019→2020: −0.0260). Cơ chế "dữ liệu dài hơn" là **giả thuyết** (khả dĩ khác: pseudo-label ổn định dần theo năm) — lane không tách biến. Hình: `results/figs/supervised_learning_curve.png`.

### 4.2 Permutation importance — RF hồi quy (seed 11, n_repeats=30)

`results/supervised_depth.md:39-69`. Bảng train là **in-sample**; bảng holdout chỉ mô tả ngoài mẫu. **Cả hai cột đều đo "mean giảm R²"** (mean của R² trước − R² sau khi hoán vị cột; khoảng biến thiên [min, max] trong md nguồn).

| Hạng | Đặc trưng | Train (mean giảm R², in-sample) | Holdout (mean giảm R², mô tả) |
| --- | --- | --- | --- |
| 1 | `sd_6_1` 6.1 Y tế công lập | **0.9928** | **1.0063** |
| 2 | `sd_1_4` 1.4 Đóng góp tự nguyện | 0.0305 | 0.0199 (hạng 3) |
| 3 | `sd_1_3` 1.3 Chất lượng bầu cử | 0.0241 | 0.0309 (hạng 2) |

**Vì sao holdout = 1.0063 > 1?** (sinh viên sẽ hỏi đầu tiên): mean giảm R² có thể vượt 1 vì R² **sau hoán vị** có thể âm sâu. Số học nhất quán với số công bố: RF có holdout R² = 0.423 (`results/supervised_metrics.csv`, dòng `random forest`, cột `holdout_r2`); mean giảm 1.0063 hàm ý R² sau hoán vị trung bình ≈ 0.423 − 1.0063 ≈ **−0.58** — tức sau khi phá cột `sd_6_1`, dự báo tệ hơn cả dự báo bằng trung bình. Giải thích này là đọc mô tả, không phải tái tính.

**Đọc quan trọng (diễn giải từ spec đã công bố):** `sd_6_1` là biến đích của hồi quy (`REGRESSION_TARGET = "sd_6_1"`, `scripts/papi_pred_common.py:23`) đồng thời nằm trong danh sách features (`scripts/papi_pred_common.py:19-22`) — tức model được dự báo **sd_6_1 năm sau từ sd_6_1 năm nay**. Permutation importance ≈ 1.0 nghĩa là hoán vị cột này gần như phá hết sức dự báo: phần lớn năng lực của Ridge là **tự tương quan thời gian** (giá trị năm nay là proxy tốt cho năm sau), không phải "kiến thức" về 7 chỉ tiêu còn lại (đóng góp mỗi chỉ tiêu chỉ 0.006–0.031, `results/supervised_depth.md:47-54`). Đây là đọc mô tả của lane — bất kỳ thay đổi spec (ablation bỏ `sd_6_1`) thuộc quyền GV (mục 5b.1 — đề xuất ưu tiên cao nhất).

- Lưu ý độ ổn định: kiểm định viên lane C spot-check với n_repeats=5 thấy **thứ tự hạng 2/3 trên holdout đổi chỗ** (sd_1_4 > sd_1_3) so với 30-repeat; hạng #1 không đổi. Hạng 2/3 holdout chỉ mô tả và không ổn định khi giảm repeats — không đưa vào kết luận (báo cáo của verify lane C, phụ lục 6.4).
- Hình: `results/figs/supervised_importance.png`.

### 4.3 Residual diagnostics — Ridge trên holdout 2023→2024 (59 cặp)

`results/supervised_depth.md:71-107`. Residual = thực tế − dự báo (dương = model dự báo THẤP hơn thực tế).

- Tổng quan: mean **0.0304**, median 0.0342, sd 0.0712, min −0.1086, max 0.1938, MAE **0.0640** (trùng published 0.0640) (`results/supervised_depth.md:73`).
- **Residual theo năm:** trên holdout suy biến (chỉ 1 origin 2023) — md ghi rõ và bổ sung bảng out-of-sample theo năm từ chính các cửa sổ learning curve, tất cả chỉ mô tả (`results/supervised_depth.md:77-88`). **Trích đủ 7/7 origin** (mean residual): 2016 +0.0274 · 2017 +0.0329 · 2018 +0.0421 · 2019 −0.0043 · 2020 −0.0215 · 2021 −0.0217 · 2022 −0.0249 — dấu dương ở 2016–2018 và âm ở 2019–2022 (thay dấu đúng một lần giữa 2018 và 2019). Không có kiểm định thống kê cho "xu hướng" — mô tả.
- **Tỉnh lớn/nhỏ** (median dân số 2023 = 1248.11 nghìn, tính trên chính 59 tỉnh holdout — md ghi rõ): lớn 30 tỉnh, resid mean **0.0219**; nhỏ 29 tỉnh, resid mean **0.0393** — tỉnh nhỏ lệch nhiều hơn gấp ~1.8 lần (`results/supervised_depth.md:92-97`). **Lưu ý bản chất post hoc**: median-split được tính trên chính 59 tỉnh holdout sau khi có dữ liệu — đây là quan sát phân tích-sau (post hoc) với n nhỏ (30/29) và chỉ 1 năm holdout, KHÔNG phải hạn chế đã được xác nhận độc lập.
- **Top-5 tỉnh lệch nhất — cả 5 đều dự báo THẤP hơn thực tế** (`results/supervised_depth.md:101-107`): Tây Ninh +0.1938 · Bình Thuận +0.1730 · Đắk Nông +0.1521 · Phú Yên +0.1347 · Hà Tĩnh +0.1147.

### 4.4 Caveats đã ghi trong md nguồn (bắt buộc đọc kèm)

`results/supervised_depth.md:109-116`:
1. **Leakage trong learning curve — phạm vi đầy đủ:** siêu tham số được chọn bằng CV có các origin đánh giá 2017–2022 (`results/supervised_depth.md:6`) nên **tất cả 7 origin của learning curve đều chịu rò rỉ ở mức này**: origin 2016 — thông tin chọn nằm trong tương lai của cửa sổ; origin 2017–2022 — năm đang đánh giá chính nằm trong tập chọn siêu tham số. (Bản v1 chỉ nêu 2016–2017 — đã sửa.) Đây là **đặc tả model đã công bố**, không phải quy trình chọn lại (md:112).
2. Holdout chỉ 1 năm (2023→2024, 59 cặp) → mọi kết luận residual ngoài mẫu chỉ mô tả, không khái quát (md:113).
3. Permutation importance trên train là in-sample; trên holdout chỉ 59 cặp nên khoảng biến thiên rộng (md:114).
4. Script KHÔNG ghi `models/*`, KHÔNG chạy `scripts/predict_sweep.py`, KHÔNG ghi đè artifact công bố (md:115).
5. Ghi chú quy trình của lane: "LR" = LogisticRegression trên pseudo-label STING (metric macro-F1, cùng `CLASSIFICATION_SCORER`); bug đã sửa trong lúc chạy — cặp hồi quy (740 train) và cặp phân loại (738 train) là hai tập dòng khác nhau nên mỗi tập có fold expanding riêng (lần chạy đầu dùng chung index gây IndexError) (báo cáo lane, ghi ở md nguồn và mô tả lane).

### 4.5 Bài học ML (cho sinh viên)

1. **Permutation importance với biến đích trễ trong features** sẽ "ăn" gần hết trọng số — luôn hỏi: đặc trưng đầu bảng có phải chính là target bị trễ thời gian không, trước khi kết luận "chỉ số này quan trọng nhất". Và mean giảm R² có thể >1 khi R² sau hoán vị âm sâu — đừng bỏ qua chỉ vì "trên 100%".
2. **Learning curve theo origin thời gian ≠ learning curve theo n ngẫu nhiên.** R² dao động mạnh vì phân phối năm thay đổi; đọc hai đường Ridge/LR bằng **cùng một tiêu chuẩn mô tả** — nếu gán nguyên nhân cho đường này thì phải nhận đường kia cũng cần kiểm chứng.
3. **Residual có dấu hệ thống theo thời gian và theo quy mô tỉnh** là tín hiệu mô hình hóa đáng đuổi, nhưng với 1 năm holdout và phân nhóm post hoc thì chỉ ghi nhận, không retune.

---

## 5. Khuyến nghị có thứ tự

**Quy tắc tách (a)/(b) — kiểm tra được:** một khuyến nghị thuộc **(a)** khi và chỉ khi thực hiện nó **không ghi/sửa tệp nào trong repo và không thay đổi nội dung artifact công bố** (chỉ thêm ghi chú đọc-hiểu trong tài liệu nội bộ/học tập). Thuộc **(b)** khi nó **thay đổi giao thức/spec/cấu hình, đòi hỏi re-run script sinh artifact, hoặc thay đổi nội dung/cách render của artifact công bố** (kể cả báo cáo chính thức của đề tài). Mọi hành động "trình bày" đụng tới đầu ra công bố ⇒ luôn (b).

### (a) Không cần GV duyệt — hành động không-làm / ghi chú nội bộ (theo quy tắc trên)

1. **Không có hành động nào được thực hiện từ lane A:** mặc định là **giữ nguyên cấu hình cho tới khi GV quyết định** (5b.2). Nhóm phân tích không tự chốt "giữ nguyên" như một quyết định đã duyệt — mục này nằm ở (a) vì *không có thay đổi nào diễn ra*, không phải vì đã qua duyệt.
2. **Trong tài liệu phân tích nội bộ/học tập:** chỉ dùng cặp tương phản nhiễu vs cụm 2 khi diễn giải phân cụm (căn cứ bootstrap lane B — kết quả tham khảo). **Không áp dụng cho báo cáo công bố** — thay đổi cách trình bày công bố thuộc (b).3.
3. **Khi trích permutation importance (tài liệu nội bộ): luôn kèm nhãn in-sample/holdout** và ghi chú `sd_6_1` là biến đích trễ; không trích bảng holdout như bằng chứng lựa chọn đặc trưng (`results/supervised_depth.md:41`, `:109-111`).
4. **Ghi quan sát residual theo nhóm tỉnh vào tài liệu nội bộ** với nhãn "post hoc: median-split tính trên chính 59 tỉnh holdout (30/29), n nhỏ, 1 năm holdout" (`results/supervised_depth.md:92-97`). KHÔNG đưa vào báo cáo công bố như "hạn chế đã biết" đã xác nhận — nếu muốn đưa vào công bố ⇒ qua (b).3.
5. **Khi trích bảng GRDP lane B:** ghi kèm "cụm 1 n=1" hoặc bỏ hàng đó khỏi phần trích; chạy lại với loại nhóm n=1 là phân tích mới (chưa làm — NOT_RUN).
6. **Không chỉnh PNG `protocol_sensitivity_grid.png`** trong đợt này — việc sửa hình cần đợt re-run được duyệt để sinh hash mới (5b.5).

### (b) Cần GV duyệt — liên quan giao thức / cấu hình production / đầu ra công bố

1. **[ĐỀ XUẤT ƯU TIÊN CAO NHẤT về giá trị thông tin] Ablation bỏ `sd_6_1` khỏi features.** Lý do lên đầu: perm importance cho thấy năng lực Ridge phần lớn là tự tương quan thời gian (mục 4.2), nên câu hỏi kế tiếp giá trị nhất là "7 chỉ tiêu còn lại đóng góp gì" — quyết định được rồi mới nói được giá trị của phần supervised cho công bố. Thay đổi spec model đã công bố ⇒ cần duyệt.
2. **Quyết định về bộ lọc chọn cấu hình (B5):** giữ nguyên bộ lọc cũ (khuyến nghị mặc định — Lane A không cho ra ứng viên thay thế), hoặc nới giao thức (ví dụ chấp nhận largest_sửa > 0.85, hoặc đổi mốc chia mẫu). **Lane A chỉ mô phỏng — KHÔNG tự áp dụng; việc nới/đổi ngưỡng thuộc quyền GV** (`results/protocol_sensitivity.md:153-155`). Nếu GV quyết định thay: phải re-run `scripts/predict_sweep.py` theo quy trình đóng băng mới (script này bị cấm chạy trong lane phân tích).
3. **Quyết định những gì được đưa vào CÔNG BỐ từ kết quả tham khảo:** (i) render nhãn cụm — giữ nguyên hay gộp cụm li ti 0/1 vào nhiễu (dữ liệu quyết định: giữ nhãn 14.5%/49.8% + k′ thường >3, `results/cluster_profile.md:99-125`); (ii) các quan sát lane C (residual post hoc) có vào báo cáo chính thức không; (iii) trạng thái của bộ lọc sửa trong văn bản công bố.
4. **Re-freeze / re-fit model với dữ liệu mở rộng** (ví dụ sau khi panel cập nhật) — ngoài phạm vi 3 lane này, phải do GV chỉ định quy trình.
5. **Chỉnh PNG lane A (chồng-nhãn)** — làm kèm re-run lane A được duyệt để sinh lại hash mới; nguyên tắc: chất lượng hình ưu tiên hơn bảo toàn hash **khi đã có đợt re-run**.

---

## 6. Phụ lục — seed, lệnh chạy, hash deterministic

### 6.1 Seed

| Dùng ở | Giá trị | Nguồn |
| --- | --- | --- |
| Bootstrap lane B (200 lần resample theo tỉnh) | **11** — `numpy.random.default_rng(11)` | `scripts/cluster_profile.py:61`, `:317`; `results/cluster_profile.md:5` |
| Permutation importance lane C | **11**, n_repeats=30 | `scripts/supervised_depth.py:96`; `results/supervised_depth.md:5` |
| Pipeline model (Ridge/RF/Logistic `random_state`) | **42** — đặc tả đã công bố, không đổi | `scripts/predict_supervised.py:72`; `results/supervised_depth.md:5` |
| Lane A | Seed 11 được khai theo quy định nhưng **không tác động kết quả** — pipeline không có bước ngẫu nhiên | `results/protocol_sensitivity.md:26-28` |

### 6.2 Lệnh chạy (từ thư mục gốc repo, `python -E` theo ràng buộc — không `-I` vì pandas ở user site)

**Lane A** (`scripts/protocol_sensitivity.py`):
```
python -E scripts/protocol_sensitivity.py            # chạy 2 lần — kiểm định deterministic
python -m ruff check .
python -E -m pytest -q
sha256sum results/protocol_sensitivity.{md,csv} results/figs/protocol_sensitivity_grid.png   # ×2, diff → byte-giống
git status --porcelain && git diff --stat            # 0 file tracked bị sửa
```

**Lane B** (`scripts/cluster_profile.py`):
```
python -E scripts/cluster_profile.py                 # chạy 2 lần (run 1 ~8s) — stdout identical, 3 artifact byte-giống
python -E -m ruff check .
python -E -m pytest -q                               # 101 passed
git status --porcelain                               # 0 modified tracked
```

**Lane C** (`scripts/supervised_depth.py`):
```
python -E scripts/supervised_depth.py                # tổng 5 lần chạy (lần 1 lộ bug index folds — đã sửa; 2 lần cuối dùng kiểm định)
python -E -m ruff check .
python -E -m pytest -q                               # 101 passed, exit 0
sha256sum results/supervised_depth.{md,csv} results/figs/supervised_{learning_curve,importance}.png
```

**Ask v1 (viết báo cáo)** — kiểm chứng độc lập:
```
sha256sum results/protocol_sensitivity.md results/protocol_sensitivity.csv results/figs/protocol_sensitivity_grid.png results/cluster_profile.md results/cluster_profile.csv results/figs/deep_cluster_profile.png results/supervised_depth.md results/supervised_depth.csv results/figs/supervised_learning_curve.png results/figs/supervised_importance.png
python -E -m ruff check .          # → All checks passed! (exit 0)
python -E -m pytest -q             # → 101 passed in 24.21s (exit 0)
git status --porcelain             # → 0 tracked modified (trước và sau pytest)
```

**Ask v2 (sửa theo góp ý độc giả — ask này):** chỉ đọc lại `reports/model_deep_dive.md` và `models/predict_config.json` (read-only, để sửa chuỗi trỏ nguồn của cấu hình đóng băng) + chạy `git status --porcelain` xác nhận repo không đổi. KHÔNG chạy lại ruff/pytest/sha256 (markdown thay đổi không đụng gate; giữ nguyên kết quả v1 — NOT_RUN ở v2, ghi trong 6.4).

### 6.3 sha256 (tự đo bằng lệnh ở 6.2, ask v1 — KHÔNG có log đính kèm; độc giả kiểm chứng bằng cách chạy lại lệnh. Ask v2 không chạy lại — NOT_RUN)

| Tệp | sha256 (đầy đủ) |
| --- | --- |
| `results/protocol_sensitivity.md` | `fbe02329a4eb23628ded30bed40c2bf520446188bf7c34b83f2f40151189392e` |
| `results/protocol_sensitivity.csv` | `05cf028ae34d38ca524cad197ade8ef046e712e5cfd27b23b137e2733cec609a` |
| `results/figs/protocol_sensitivity_grid.png` | `472f584483a198a1f75aae2cbaba404998618e9b8227b6995c3e2c1082e90027` |
| `results/cluster_profile.md` | `d034a7e4ed862050c9c11cf745cba60e21b2ae57c26a0dad1d9c9387640ecf2d` |
| `results/cluster_profile.csv` | `1d2eb62dfdbcf395d52761757cac94c26cc49f55f0aba91c67aecf178fdb13bb` |
| `results/figs/deep_cluster_profile.png` | `bfb4d2acf7e3347038f9087465224df743e691656ac7de7b710acb7801ae038f` |
| `results/supervised_depth.md` | `721720066ccaa0af3de4c6049d98383fa7f88b18c58251dacdb29d5698168bdd` |
| `results/supervised_depth.csv` | `1d6bec508c68d679235125e51ca55ac2ff8f23d061d411596444d05bb289924e` |
| `results/figs/supervised_learning_curve.png` | `71c333c686bb759a578e1bc2428245139440a2414dc1f243a88c4e9e1d7c57cc` |
| `results/figs/supervised_importance.png` | `5147bf1cd74de824644bfc82e7726b1ca7756cd20be1c91f67948437dc5483e7` |

### 6.4 Bảng trạng thái kiểm chứng — trung thực về cái gì đã chạy, cái gì được báo cáo lại, chứng cứ nằm ở đâu

| Hạng mục | Trạng thái | Chứng cứ nằm ở đâu / cách tái kiểm |
| --- | --- | --- |
| sha256 của 10 tệp output khớp giá trị lane tuyên bố | **CHẠY ở ask v1** (ask v2: NOT_RUN) | Lệnh + kết quả ghi nguyên văn ở 6.2/6.3; tái kiểm = chạy lại lệnh (không cần artifact riêng) |
| Gate lint toàn repo | **CHẠY ở ask v1** | `python -E -m ruff check .` → "All checks passed!", exit 0; tái kiểm = chạy lại |
| Gate test toàn repo | **CHẠY ở ask v1** | `python -E -m pytest -q` → "101 passed in 24.21s", exit 0; tái kiểm = chạy lại |
| Không đụng artifact đóng băng | **CHẠY ở ask v1; xác nhận lại ở ask v2 sau khi ghi v2** | `git status --porcelain` → 0 tracked modified (v1: trước và sau pytest; v2: sau khi ghi bản này) |
| Đối chiếu số với tệp nguồn | **CHẠY ở ask v1** (đọc nguyên văn); bổ sung ask v2: đọc `models/predict_config.json` | Các tệp `results/*.md`, CSV, `models/predict_config.json` còn nguyên trong repo — độc giả mở trực tiếp; mọi số trong báo cáo trỏ về đó |
| Deterministic 2 lần chạy của 3 lane (md/csv/png byte-giống) | **TỰ BÁO CÁO của lane — NOT_RUN ở ask v1 và v2**: chạy lại script sẽ GHI ĐÈ artifact đã kiểm định hash. Phương án kiểm chứng không-ghi-đè (chạy với thư mục output tạm, vd chỉnh `--out-dir` hoặc chạy trên bản sao repo) **chưa thực hiện** | Chứng cứ hiện có: log phiên lane (KHÔNG lưu artifact) + hai suy luận gián tiếp: hash hiện tại khớp tuyên bố (6.3); code không có nguồn thời hệ thống/ngẫu nhiên ngoài `SEED=11` (`scripts/cluster_profile.py:61`, `:317`). Với độc giả chỉ-đọc: đây là niềm tin có căn cứ, KHÔNG phải kết quả đã kiểm chứng |
| Phân bố bootstrap 200 lần (mean 0.8742, CI95 [0.8138, 0.9407], bảng per-label, k′) | **KẾT QUẢ lưu trong artifact** `results/cluster_profile.{md,csv}` (mở đọc được); nhưng tính lại từ đầu = chạy lại script (ghi đè) — NOT_RUN. Verify lane B chỉ tái lập được **rep-0** trong phiên | Kết quả: tệp artifact. Rep-0 (0.8892 trong CI95, lệch mean ~0.4 sd; giữ nhãn cụm 2 rep-0 93.7% ≈ pooled 94.1%): **chỉ trong log phiên verify — KHÔNG có tệp trong repo**; coi là báo cáo phiên, không dùng làm bằng chứng duyệt chính thức |
| Learning curve điểm đầu Ridge (origin 2016, R²=0.4588) + siêu tham số + kiểm đối metrics (0.265/0.0640/0.197; 740/59 cặp) | ĐÃ TÍNH LẠI **trong phiên** bởi verify lane C: builder riêng → 311 train / 63 val, R²=0.4588 KHỚP; siêu tham số khớp; metrics khớp `results/supervised_metrics.csv` | Tính lại trong phiên — **chỉ log phiên, KHÔNG có tệp trong repo**; kết quả cuối cùng đối chiếu được với artifact `results/supervised_depth.md:15-23` + `results/supervised_metrics.csv` |
| Permutation importance spot-check n_repeats=5 | ĐÃ TÍNH LẠI trong phiên bởi verify lane C: top-3 train cùng thứ tự, lệch ≤0.009; **holdout hạng 2/3 đổi chỗ khi 5 repeats** | Chỉ log phiên — không có tệp; ghi chú ở mục 4.2 |
| 6 điểm LC Ridge còn lại, 7 điểm LR macro-F1, bảng residual, top-5 tỉnh, perm n_repeats=30 chính xác | BÁO CÁO LẠI — đối chiếu nguyên văn với `results/supervised_depth.md:15-116` + `results/supervised_depth.csv` (verify lane C cũng chỉ đối chiếu, không tính lại) | Tệp artifact — độc giả mở trực tiếp |
| Cấu hình đóng băng suy ra lúc chạy (không hardcode) | BÁO CÁO LẠI từ lane A; ask v2 đối chiếu trực tiếp với `models/predict_config.json:4-26` (features sd_4_2+sd_6_1; STING 3/4/5/2; k=3; sizes [453,16,5]; score 0.6213) | Tệp `models/predict_config.json` — độc giả mở trực tiếp (read-only) |

### 6.5 Giới hạn của báo cáo này

- Mọi số lane A/B/C là **kết quả tham khảo mới** — chưa được GV duyệt và không nằm trong số đã công bố; chỉ các số có nhãn `[ĐÃ ÁP DỤNG]` ở mục 1 và 2.1 là chính thức.
- Không có kiểm định thống kê mới nào ngoài những gì 3 lane đã chạy; báo cáo này không tính lại số nào từ dữ liệu thô — nó đối chiếu, trỏ nguồn, và ghi rõ bằng chứng nào nằm trong artifact, nào chỉ nằm trong log phiên.
- 2024 chỉ xuất hiện vai trò đích holdout/mô tả; không có lane nào dùng 2024 khi học.
- Mọi pointer nguồn là tệp ngoài văn bản — độc giả chỉ-đọc không kiểm chứng được ngay; mục 2.1 có một kiểm tra số học làm ngay trong văn bản (score ≈ 0.6209 vs 0.6213, chênh do làm tròn hiển thị) để minh họa cách tự kiểm.

### 6.6 Nhật ký sửa v1 → v2 (theo góp ý độc giả)

| Góp ý | Sửa |
| --- | --- |
| (1) Số tự báo cáo không kiểm chứng được (:16, :305-314) | Nhúng danh sách 13 tệp untracked vào văn bản; ghi rõ "tự báo cáo từ lệnh `git status --porcelain`, độc giả tái kiểm được"; bảng hash ghi rõ "tự đo, không log đính kèm" |
| (1) Số verify-lane không có artifact (:326-328) | 6.4 thêm cột "Chứng cứ nằm ở đâu"; các số rep-0 / 311/63 / spot-check được đánh dấu "chỉ log phiên — KHÔNG có tệp trong repo, không dùng làm bằng chứng duyệt chính thức" |
| (1) :158 đọc ngược nghĩa 198/200 | Sửa thành "198/200 lần hợp lệ, 2/200 bị loại (<2 cụm non-noise)" — `results/cluster_profile.md:90`, `:95` |
| (1) :22 số chính thức đi qua tệp lane | Số chính thức trỏ trực tiếp `models/predict_config.json` (đã mở read-only ở ask v2); chuỗi cho [629,16,5] nêu rõ: KHÔNG nằm trong config, tái lập từ `results/predict_all_years.csv` qua kiểm chứng 808/808 |
| (1) :175 kiểm đối không kèm dòng/cột; carry-forward không định nghĩa | Trỏ cột cụ thể của `results/supervised_metrics.csv`; carry-forward định nghĩa ở Thuật ngữ + mục 1 |
| (2)a Tóm tắt lẫn giọng kết luận | Thêm nhãn [THAM KHẢO] cho cả 3 phát hiện; kết luận lane A thu về phạm vi giả định B5 + chuyển quyền quyết định cho GV; "đọc gộp" ghi rõ chưa duyệt |
| (2)b Banner lane B/C thiếu nhãn | Thêm "[THAM KHẢO — CHƯA DUYỆT GV]" đồng nhất cho lane B (:107) và lane C (:170) |
| (2)c + (4) Tiêu chí 5a/5b; (a).2/(a).4 đụng "công bố" nhưng cổng khác (b).3 | Thêm quy tắc tách (a)/(b) kiểm tra được; (a).2/(a).4 thu về "tài liệu nội bộ"; mọi hành động trình bày công bố gom về (b).3 |
| (2)d Bảng 4 dòng pass là số công bố nằm trong section mô phỏng | Gắn nhãn [ĐÃ ÁP DỤNG] riêng cho bảng 2.1 + ghi rõ "script mô phỏng tái lập nguyên vẹn" |
| (2)e ":26 chốt 'đứng vững' trước tiền đề chưa duyệt" | Sửa kết luận tóm tắt thành điều kiện theo giả định B5 |
| (2)f/:141, (2)j/:130 giải thích nhân quả & "ĐỘC LẬP" | Ghi rõ là diễn giải/nhận định của md nguồn, không phải kiểm chứng của báo cáo; không có thí nghiệm tách biến |
| (2)g/:192, (2)h/:28 Ridge/LR mạnh hơn dữ liệu | Ridge: "không thấy xu hướng" + không kiểm định; LR: 2/6 bước giảm được liệt kê; hai đường dùng cùng tiêu chuẩn mô tả (giả thuyết cơ chế) |
| (2)i/:214 trích chọn 5/7 origin | Trích đủ 7/7 giá trị residual theo origin |
| (2)k/:239 (a).1 tự quyết hộ GV | (a).1 viết lại: mặc định không-làm, quyền thay đổi thuộc GV (5b.2) |
| (3) Thuật ngữ | Thêm bảng Thuật ngữ: lane/ask/verify/artifact, sd_X_Y (đủ 8), PCI, STING + cfg 3/4/5/2, score + bộ lọc cũ + stable_mc_pm1, B5, Jaccard/k′/giữ nhãn, 0-thật, carry-forward, permutation importance, cluster bootstrap, train (hai nghĩa) |
| (4) Hai bộ train [629,16,5] vs [453,16,5] | Giải thích ở mục 1 + chú thích bảng 2.1 + Thuật ngữ; nêu rõ số nào nằm ở artifact nào |
| (4) 869 ≠ 808 | Giải thích ở 3.0: phổ nhãn trên 2011–2024 (869), fit 2011–2023 = 808, 2024 = 61 dòng ngoài fit, nhiễu train 158 |
| (4) 0.8400 ba cách gọi | Quy ước gọi số thống nhất ở 2.2 (score cũ = score_sửa = 0.8400 cho tổ hợp k=1) |
| (4) Perm importance holdout > 1 | Giải thích bằng số học với RF holdout R² 0.423 (4.2); cột holdout được gắn nhãn "mean giảm R²" |
| (4) Leakage phủ mọi origin | 4.4.1 viết lại: tất cả 7 origin chịu rò rỉ (2016 = tương lai; 2017–2022 = năm đánh giá nằm trong tập chọn) |
| (4) 0.8742 vs k′=5 | 3.2 thêm "đọc tỉ lệ giữ nhãn kèm hình dạng phân hoạch" |
| (4) Determinism tự báo + kiểm chứng không-ghi-đè | 2.7 + 6.4: ghi rõ tự báo cáo, phương án temp-dir, trạng thái NOT_RUN |
| (4) Hash ≠ hình đúng | 2.7 + 5b.5: hash chỉ chứng minh tệp không đổi; nguyên tắc chất lượng hình > bảo toàn hash khi có re-run |
| (4) GRDP n=1 trong test | 3.1 ghi rõ giới hạn + phương án loại n=1 là phân tích mới (NOT_RUN); thêm (a).5 |
| (4) Ablation sd_6_1 nên ưu tiên cao nhất | (b).1 nâng lên đầu với lý do giá trị thông tin |
| (4) Median-split post hoc đưa vào "báo cáo chính thức" | 4.3 gắn nhãn post hoc (n=30/29, 1 năm); (a).4 thu về tài liệu nội bộ, công bố qua (b).3 |
