# B5 — Protocol sensitivity: largest trên tổng n vs trên non-noise

> **Trạng thái: PHÂN TÍCH THAM KHẢO cho GV duyệt B5.** Script chạy
> in-memory, KHÔNG ghi `models/predict_config.json`, không lưu model,
> không thực thi `scripts/predict_sweep.py`, không sửa số đã công bố.

## 0. Tóm tắt

- Bộ lọc CŨ: 4/224 tổ hợp pass — tái lập đúng (mục 3).
- Bộ lọc SỬA (mcs=0.05): **KHÔNG có ứng viên nào trong 224 tổ hợp pass** — đây chính là phát hiện quan trọng của B5: kết
  quả phân cụm của giao thức đóng băng KHÔNG vững dưới một bộ lọc cân bằng cụm chặt hơn (cụm "nhỏ" hiện có chỉ là đơn vị
  vài điểm, tương đương nhiễu).
- Cấu hình đóng băng sd_4_2+sd_6_1 (3/4/5/2) tự nó cũng fail bộ lọc sửa: largest_sửa = 0.9557 > 0.85, min_share = 0.0105 < 0.05.

## 1. Phạm vi & phương pháp

- Dữ liệu: `data/processed/papi_panel_63_2011_2024.csv` (chỉ ĐỌC).
- Preprocessing tái hiện nguyên văn `scripts/predict_sweep.py`:
  train ≤ 2020, tương lai giả 2021–2022 (2024 không tham gia);
  StandardScaler fit trên train của từng cặp; dropna cặp gồm cột
  `year` (`predict_sweep.py:118`); ngưỡng 500/100 dòng
  (`predict_sweep.py:120`); allowlist 8 sub-dimension sau sàng
  mean-jump trên train (`predict_sweep.py:48`, `:65-77`).
- 224 tổ hợp = 28 cặp × 8 cấu hình STING
  `(n_levels, factor, min_count, level)` (`predict_sweep.py:49-52`).
- Seed: 11 (quy định). Pipeline không có bước ngẫu nhiên nào
  (STING lưới thống kê + StandardScaler đều deterministic); không
  dùng bootstrap/permutation, nên seed không tác động kết quả.
- Kết quả render không chứa thời gian chạy → chạy script 2 lần cho
  md/csv/png sha256 byte-giống (bảng hash ở mục 10).

## 2. Hai bộ lọc được so sánh

| Thành phần | Bộ lọc CŨ (đóng băng) | Bộ lọc SỬA (B5) |
| --- | --- | --- |
| k | ∈ [2, 6] | ∈ [2, 6] (giữ nguyên) |
| noise_train | ≤ 0.25 | ≤ 0.25 (giữ nguyên) |
| largest | sizes[0] / n_tổng ≤ 0.85 | sizes[0] / max(1, n_non-noise) ≤ 0.85 |
| cụm nhỏ nhất | (không có) | sizes[-1] / max(1, n_non-noise) ≥ mcs |
| coverage 21–22 | ≥ 0.75 | ≥ 0.75 (giữ nguyên) |
| điểm | cov − 0.5·noise − 0.15·largest − 0.02·&#124;k−3&#124; + 0.03·stable | cùng trọng số, largest → largest_sửa |

Công thức điểm bộ lọc cũ: `predict_sweep.py:133-136`; điều kiện pass
cũ: `predict_sweep.py:127-132`. Điểm sửa chỉ thay biến `largest`
bằng định nghĩa non-noise — lựa chọn này được ghi rõ vì đề bài B5
định nghĩa lại biến `largest` ở bộ lọc sửa; bảng CSV giữ cả hai điểm
(`score`, `score_mod`) để đối chiếu.

## 3. Đối chiếu tái lập bộ lọc CŨ (bắt buộc)

- N dòng: published = 224, tái lập = 224, khớp khóa = 224.
- Khớp giá trị từng trường trên 224/224 dòng (k, sizes_top5, noise_train, largest_share,
  coverage_2021_2022, stable_mc_pm1, score, pass).
- Khớp cả THỨ TỰ 224 dòng sau sort như gốc: True.

Bảng 4 dòng pass của `results/predict_config_search.csv` — giá trị
published (đọc từ CSV) và tái lập (tính in-memory lần này) trùng nhau:

| features | cfg | k | sizes_top5 | noise | largest | coverage | stable | score (công bố) |
|---|---|---|---|---|---|---|---|---|
| sd_4_2+sd_6_1 | 3/4/5/2 | 3 | [453, 16, 5] | 0.243 | 0.724 | 0.851 | False | 0.6213 |
| sd_1_3+sd_6_3 | 3/3/8/2 | 2 | [485, 11] | 0.210 | 0.772 | 0.844 | False | 0.6033 |
| sd_4_3+sd_6_3 | 3/3/8/2 | 2 | [483, 8] | 0.216 | 0.772 | 0.843 | False | 0.5994 |
| sd_1_4+sd_4_2 | 3/4/5/2 | 2 | [479, 6] | 0.225 | 0.765 | 0.802 | False | 0.5543 |

## 4. Bộ lọc SỬA — kết quả chính (mcs = 0.05)

**KHÔNG có ứng viên nào pass bộ lọc sửa (0/224).** Ghi đúng như vậy theo yêu cầu B5. Số tổ hợp phạm từng điều kiện
(một tổ hợp có thể phạm nhiều điều kiện): coverage: 59, k: 168, largest: 219, min_share: 57, noise: 57.

Tổ hợp gần đạt nhất (trong nhóm đạt k/noise/coverage, 16/224 tổ hợp): `sd_1_3+sd_6_3` (3/3/8/2) — min_share = 0.0222 (còn thiếu 0.0278 để đạt 0.05), largest_sửa = 0.9778.

## 5. Top-5 theo điểm bộ lọc sửa

Vì không có tổ hợp nào pass, bảng dưới là **top-5 toàn bộ 224**
theo score_sửa (không phải ứng viên đạt lọc) — dùng để thấy điểm cao nhất nằm ở đâu và vì sao vẫn bị loại.

| # | features | cfg | k | sizes_top5 | noise | largest_sửa | min_share | coverage | stable | score (cũ) | score_sửa | fail (mcs=0.05) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sd_1_3+sd_6_3 | 2/3/12/1 | 1 | [628] | 0.000 | 1.0000 | 1.0000 | 1.000 | True | 0.8400 | 0.8400 | k+largest |
| 2 | sd_4_1+sd_4_2 | 2/3/12/1 | 1 | [626] | 0.000 | 1.0000 | 1.0000 | 1.000 | True | 0.8400 | 0.8400 | k+largest |
| 3 | sd_4_1+sd_6_3 | 2/3/12/1 | 1 | [626] | 0.000 | 1.0000 | 1.0000 | 1.000 | True | 0.8400 | 0.8400 | k+largest |
| 4 | sd_6_1+sd_6_3 | 2/3/12/1 | 1 | [628] | 0.000 | 1.0000 | 1.0000 | 1.000 | True | 0.8400 | 0.8400 | k+largest |
| 5 | sd_1_4+sd_6_3 | 2/3/12/1 | 1 | [627] | 0.002 | 1.0000 | 1.0000 | 1.000 | True | 0.8394 | 0.8392 | k+largest |

Top-8 tổ hợp đạt k/noise/coverage, xếp theo min_share giảm dần
(gần đạt bộ lọc sửa nhất — cho thấy khoảng cách còn bao xa):

| features | cfg | k | noise | largest_sửa | min_share | còn thiếu để đạt mcs=0.05 | vượt ngưỡng largest |
|---|---|---|---|---|---|---|---|
| sd_1_3+sd_6_3 | 3/3/8/2 | 2 | 0.210 | 0.9778 | 0.0222 | 0.0278 | 0.1278 |
| sd_4_3+sd_6_3 | 3/3/8/2 | 2 | 0.216 | 0.9837 | 0.0163 | 0.0337 | 0.1337 |
| sd_1_4+sd_4_2 | 3/4/5/2 | 2 | 0.225 | 0.9876 | 0.0124 | 0.0376 | 0.1376 |
| sd_4_1+sd_4_2 | 3/4/5/2 | 2 | 0.133 | 0.9890 | 0.0110 | 0.0390 | 0.1390 |
| sd_4_1+sd_6_3 | 3/3/5/2 | 2 | 0.101 | 0.9893 | 0.0107 | 0.0393 | 0.1393 |
| sd_1_3+sd_4_3 | 3/3/5/2 | 2 | 0.091 | 0.9895 | 0.0105 | 0.0395 | 0.1395 |
| sd_4_2+sd_6_1 | 3/4/5/2 | 3 | 0.243 | 0.9557 | 0.0105 | 0.0395 | 0.1057 |
| sd_1_3+sd_4_3 | 3/3/4/2 | 2 | 0.065 | 0.9897 | 0.0103 | 0.0397 | 0.1397 |

## 6. Khoảng cách với cấu hình đóng băng `sd_4_2+sd_6_1` (3/4/5/2)

Định danh đóng băng suy ra từ `results/predict_config_search.csv`
(dòng pass điểm cao nhất) — trùng định danh đề bài B5: True.

| Đại lượng | Giá trị |
| --- | --- |
| score công bố (bộ lọc cũ) | 0.6213 |
| score tái lập (cùng công thức) | 0.6213 |
| largest theo tổng n (cũ) | 0.7236 |
| largest_sửa (non-noise) | 0.9557 — vượt ngưỡng 0.85 thêm 0.1057 |
| min_share (non-noise) | 0.0105 — thiếu 0.0395 so với mcs=0.05 |
| score_sửa của cấu hình đóng băng | 0.5865 |
| pass bộ lọc sửa (mcs=0.02/0.05/0.10) | False / False / False |
| khoảng cách score_sửa: top-1 toàn bảng (không pass bộ lọc sửa) − đóng băng | 0.2535 |
| khoảng cách score (công thức cũ): top-1 − 0.6213 | 0.2187 |

Không có ứng viên mới; top-1 toàn bảng là **sd_1_3+sd_6_3** (2/3/12/1) với score_sửa 0.8400 (công thức cũ: 0.8400, so với 0.6213: 0.2187) — nhưng tổ hợp
này vẫn fail bộ lọc sửa nên không thể thay cấu hình đóng băng mà không nới thêm giao thức (quyền của GV).

## 7. Độ nhạy MIN_CLUSTER_SHARE ∈ {0.02, 0.05, 0.10}

| mcs | số tổ hợp pass | tổ hợp điểm cao nhất | score_sửa | ghi chú |
|---|---|---|---|---|
| 0.02 | 0 | sd_1_3+sd_6_3 (2/3/12/1) | 0.8400 | không pass: k+largest |
| 0.05 | 0 | sd_1_3+sd_6_3 (2/3/12/1) | 0.8400 | không pass: k+largest |
| 0.1 | 0 | sd_1_3+sd_6_3 (2/3/12/1) | 0.8400 | không pass: k+largest |

Kết quả không đổi theo mcs vì ràng buộc gắt nhất không phải min_share: chỉ 5/224 tổ hợp có largest_sửa ≤ 0.85, và cả nhóm này có noise_train 0.401–0.712, coverage 0.322–0.525 — cụm cân bằng trên non-noise chỉ xuất hiện kèm mức nhiễu và mất phủ không chấp nhận được, nên nới mcs xuống 0.02 cũng không cứu được.

## 8. stable_mc_pm1 của ứng viên

- Không có ứng viên pass; top-1 toàn bảng `sd_1_3+sd_6_3` (2/3/12/1) có stable_mc_pm1 = **True**.
- Contender gần đạt bộ lọc sửa nhất trong nhóm đạt k/noise/coverage `sd_1_3+sd_6_3` (3/3/8/2): stable_mc_pm1 = **False** — trùng stable=False của 4 dòng pass cũ.

## 9. Hình

`results/figs/protocol_sensitivity_grid.png` — 224 tổ hợp trên
mặt phẳng (largest_sửa, min_share); vùng đạt bộ lọc sửa là x ≤ 0.85
và y ≥ 0.05; kim cương = 4 tổ hợp pass bộ lọc cũ.

## 10. Kiểm định & giới hạn

- File CSV đầy đủ 224 tổ hợp: `results/protocol_sensitivity.csv`
  (cột `pass` = bộ lọc cũ; `pass_mod_mcs002/005/010` = bộ lọc sửa
  theo ba mcs; `fail_mod_mcs005` = điều kiện bị phạm).
- sha256(`protocol_sensitivity.csv`) = `05cf028ae34d38ca524cad197ade8ef046e712e5cfd27b23b137e2733cec609a`
- sha256(`protocol_sensitivity_grid.png`) = `472f584483a198a1f75aae2cbaba404998618e9b8227b6995c3e2c1082e90027`
- Kiểm định deterministic: chạy `python -E scripts/protocol_sensitivity.py`
  2 lần từ thư mục gốc repo; md/csv/png phải sha256 byte-giống
  (người chạy đối chiếu ngoài script; output cố tình không chứa
  thời gian chạy).
- Giới hạn: phân tích chỉ DÙNG lại đúng dữ liệu train/validation
  của giao thức gốc (≤2022); 2024 không tham gia. Không có kiểm
  định thống kê mới ngoài bộ lọc/điểm đã nêu; không tự nới hoặc
  đổi ngưỡng đóng băng — mọi thay đổi giao thức thuộc quyền GV.
- Hằng số giao thức sao chép nguyên văn từ `predict_sweep.py:48-59`
  và được kiểm chứng bằng đối chiếu 224 dòng ở mục 3.
