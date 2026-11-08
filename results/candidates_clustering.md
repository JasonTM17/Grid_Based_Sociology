# Ứng viên thuật toán phân cụm thay thế — cửa sổ 747 tỉnh-năm ≤2022, z-score trong từng năm

**[THAM KHẢO — CHƯA DUYỆT GV]** — lane phân tích MỚI, sinh bởi `scripts/candidates_clustering.py`; CHỈ thêm 2 tệp này (`results/candidates_clustering.{csv,md}`), không đụng artifact đóng băng (`models/predict_config.json`, `results/predict_all_years.csv` — chỉ đọc), không thay model production, không đổi số đã công bố (Ridge 0.265, carry 0.145, LR 0.434, k=3). Holdout 2023→2024 không fit/chấm/nhìn; cửa sổ loại cả 61 dòng năm 2023 (origin holdout).

## Thiết kế chốt trước khi chạy (pre-registered trong ask của lane)

- **Dữ liệu**: `results/predict_all_years.csv` (artifact đóng băng, đọc thôi) — 2D sd_4_2 × sd_6_1, nhãn STING đóng băng = cột `pred_cluster` (model fit 2011–2023, lưới toàn cục — `scripts/predict_demo.py`).
- **Cửa sổ**: year ≤ 2022 → 747 dòng (869 tổng − 61 dòng 2023 − 61 dòng 2024; script fail-closed kiểm đúng phân bố nhãn −1: 149, 0: 5, 1: 16, 2: 577 — khớp join PCI 747, `results/cluster_profile.md:34`).
- **Chuẩn hóa**: z-score TRONG TỪNG NĂM (ddof=0) trên 2 cột — cùng mẫu `scripts/run_analysis.py:256`; mỗi năm dùng mean/sd của chính năm đó. *Ghi chú trung thực*: đề bài nói 'mỗi năm 63 điểm' nhưng thực tế 4 năm trong cửa sổ không đủ 63 dòng ({2014: 61, 2018: 61, 2021: 60, 2022: 61}) — phương pháp không đổi: từng năm vẫn chuẩn hóa bằng mean/sd của chính năm đó.
- **Ứng viên**: DBSCAN min_samples ∈ {5, 10} × eps tại phân vị {50, 60, 70, 80, 90}% của phân phối k-distance (10 combo suy từ dữ liệu, không tune tay); KMeans(k=3, random_state=11, n_init=10); Ward(k=3, linkage=ward).
- **Metrics**: ARI vs nhãn đóng băng 2 cách (đầy đủ / chỉ non-noise của nhãn đóng băng); ARI 2 cách vs refit (đọc deconfound); silhouette euclidean (DBSCAN/STING chỉ tính trên non-noise của nhãn đó, <2 cụm non-noise → n/a); noise rate; sizes_top5 (quy ước `models/predict_config.json:21` — non-noise, giảm dần); cờ noise ≤ 0.25 (mô tả theo bộ lọc cũ, KHÔNG phải bộ lọc ứng viên).
- **Ngưỡng thắng (chốt trước)**: ứng viên thắng mốc CHỈ khi vượt 'STING đóng băng tính lại trên cùng 747 dòng' trên CẢ 3 chỉ số ARI đầy đủ, ARI non-noise, silhouette (đọc chặt nhất của '3 chỉ số' trong đề bài; noise rate chỉ mô tả). Exploratory — không tuyên bố p-value, không hiệu chỉnh đa so sánh; cấm trích 1 combo đẹp lẻ tẻ.

## Bảng so sánh đầy đủ (14 dòng: mốc + deconfound + 12 ứng viên)

| phương pháp | min_samples | eps | phân vị k-dist (%) | k (non-noise) | noise | noise≤0.25 | sizes_top5 | ARI đầy đủ | ARI non-noise | silhouette | n_sil | ARI đầy đủ vs refit | ARI non-noise vs refit | ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STING đóng băng — nhãn gốc CSV (mốc) | – | – | – | 3 | 0.1995 | có | [577, 16, 5] | 1.0000 | 1.0000 | -0.0651 | 598 | 0.2927 | 0.0672 | mốc công bằng: nhãn pred_cluster của predict_all_years.csv trên đúng 747 dòng + z-trong-năm; ARI vs chính nó = 1 |
| STING refit z-trong-năm (cfg đóng băng) | – | – | – | 2 | 0.158 | có | [624, 5] | 0.2927 | 0.0060 | 0.3586 | 629 | 1.0000 | 1.0000 | deconfound: refit cfg đóng băng (L=3, f=4, mc=5, lv=2, conn=1) trên cùng z-trong-năm — tách hiệu ứng chuẩn hóa |
| DBSCAN ms=5 eps=0.1407 (k-dist p50) | 5 | 0.1407 | 50 | 18 | 0.3708 | không | [350, 15, 11, 10, 9] | 0.1260 | 0.0340 | -0.0611 | 470 | 0.1073 | 0.0063 |  |
| DBSCAN ms=5 eps=0.1579 (k-dist p60) | 5 | 0.1579 | 60 | 17 | 0.2664 | không | [419, 16, 15, 12, 11] | 0.2095 | 0.0034 | -0.1696 | 548 | 0.2510 | 0.0194 |  |
| DBSCAN ms=5 eps=0.1860 (k-dist p70) | 5 | 0.1860 | 70 | 8 | 0.2129 | có | [540, 11, 9, 7, 6] | 0.3099 | 0.0295 | -0.2173 | 588 | 0.5494 | 0.0758 |  |
| DBSCAN ms=5 eps=0.2267 (k-dist p80) | 5 | 0.2267 | 80 | 8 | 0.1178 | có | [609, 12, 10, 8, 6] | 0.3372 | 0.0742 | -0.0633 | 659 | 0.6813 | 0.2043 |  |
| DBSCAN ms=5 eps=0.2989 (k-dist p90) | 5 | 0.2989 | 90 | 2 | 0.0549 | có | [702, 4] | 0.1912 | 0.0372 | 0.2180 | 706 | 0.4262 | 0.0000 |  |
| DBSCAN ms=10 eps=0.2134 (k-dist p50) | 10 | 0.2134 | 50 | 3 | 0.3467 | không | [470, 11, 7] | 0.2544 | 0.0562 | 0.0256 | 488 | 0.3156 | 0.0305 |  |
| DBSCAN ms=10 eps=0.2446 (k-dist p60) | 10 | 0.2446 | 60 | 3 | 0.2517 | không | [536, 13, 10] | 0.3390 | 0.0506 | 0.1838 | 559 | 0.5017 | 0.0682 |  |
| DBSCAN ms=10 eps=0.2786 (k-dist p70) | 10 | 0.2786 | 70 | 1 | 0.1968 | có | [600] | 0.3125 | 0.0371 | n/a | 600 | 0.6861 | 0.1840 | <2 cụm non-noise → silhouette n/a |
| DBSCAN ms=10 eps=0.3273 (k-dist p80) | 10 | 0.3273 | 80 | 1 | 0.1111 | có | [664] | 0.2586 | 0.0003 | n/a | 664 | 0.6190 | 0.5432 | <2 cụm non-noise → silhouette n/a |
| DBSCAN ms=10 eps=0.4193 (k-dist p90) | 10 | 0.4193 | 90 | 1 | 0.0375 | có | [719] | 0.1252 | 0.0524 | n/a | 719 | 0.2787 | 0.0000 | <2 cụm non-noise → silhouette n/a |
| KMeans k=3 (seed 11, n_init=10) | – | – | – | 3 | 0.0 | có | [307, 234, 206] | 0.0557 | 0.0272 | 0.3360 | 747 | 0.0155 | 0.0011 | tất cả điểm được gán cụm |
| Ward k=3 (linkage=ward) | – | – | – | 3 | 0.0 | có | [413, 191, 143] | 0.1462 | 0.0679 | 0.3336 | 747 | 0.0726 | 0.0142 | tất cả điểm được gán cụm |

Đọc bảng: 'ARI đầy đủ'/'ARI non-noise' so với nhãn STING đóng băng (cột `pred_cluster`); 'vs refit' so với STING refit trên cùng z-trong-năm. silhouette của DBSCAN/STING tính trên điểm non-noise của chính nhãn đó (n_sil); KMeans/Ward tính trên cả 747 điểm.

## Lưới eps suy từ k-distance (không tune tay)

Quy ước: k-distance = khoảng cách tới hàng xóm thứ-k với k = min_samples, tính bởi `NearestNeighbors` — hàng xóm đầu tiên là chính điểm đó (khoảng cách 0), nên cột cuối là khoảng cách tới (min_samples − 1) điểm KHÁC gần nhất; với eps bằng giá trị đó, điểm vừa đủ core point (|N_eps| ≥ min_samples kể cả tự thân).

| min_samples | phân vị (%) | eps |
|---|---|---|
| 5 | 50 | 0.1407 |
| 5 | 60 | 0.1579 |
| 5 | 70 | 0.1860 |
| 5 | 80 | 0.2267 |
| 5 | 90 | 0.2989 |
| 10 | 50 | 0.2134 |
| 10 | 60 | 0.2446 |
| 10 | 70 | 0.2786 |
| 10 | 80 | 0.3273 |
| 10 | 90 | 0.4193 |

Phân phối k-distance theo min_samples:

| min_samples | min | trung vị | max |
|---|---|---|---|
| 5 | 0.0460 | 0.1407 | 1.5974 |
| 10 | 0.1104 | 0.2134 | 2.0563 |

## Deconfound: tách hiệu ứng chuẩn hóa khỏi hiệu ứng thuật toán

- STING refit đúng cfg đóng băng (L=3, f=4, mc=5, level=2, connectivity=1) trên cùng z-trong-năm: k=2, noise=0.1580, sizes=[624, 5], silhouette=0.3586 (n=629).
- ARI(refit, nhãn đóng băng gốc): đầy đủ 0.2927, non-noise 0.0060 — đây là mức ARI 'trần' chỉ do ĐỔI CHUẨN HÓA (scaler pooled cửa sổ-dài fit ≤2023 của model đóng băng vs z-trong-năm) khi thuật toán giữ nguyên. STING bất biến affine từng chiều (`src/sting.py:263-271`) nên refit không thêm scaler — khác biệt chỉ đến từ việc z-trong-năm xáo trộn vị trí tương đối GIỮA các năm (scaler đóng băng dùng 1 hệ trục chung cho cả cửa sổ), làm đổi ô lưới của từng điểm.
- Đọc: ARI(refit, gốc) đầy đủ 0.2927, non-noise 0.0060 — gần như 0 trên dòng non-noise — nhãn đóng băng trên z-trong-năm khác xa nhãn gốc; so sánh ứng viên phải đọc CẢ hai cột ARI (vs gốc và vs refit) mới tách được hiệu ứng chuẩn hóa khỏi hiệu ứng thuật toán.
- Mốc công bằng trên cửa sổ này: silhouette nhãn đóng băng (non-noise) = -0.0651 (n=598), noise=0.1995, sizes=[577, 16, 5] — *khác* silhouette 0.3611 đã công bố vì 0.3611 tính trên cửa sổ khác (fit 2011–2023, scaler pooled; `results/cluster_profile.md:97`); không so chéo số giữa hai cửa sổ.

## Nhận xét trung thực

- **KMeans sanity khớp phiên thiết kế**: sizes [307, 234, 206] (đa tập khớp [206, 234, 307]: CÓ), ARI đầy đủ 0.0557 vs 0.0557 trong phiên thiết kế (CÓ) — xác nhận kỳ vọng: ARI tuyệt đối thấp vì cấu trúc '1 cụm lớn + nhiễu' của STING không thể được k-means (3 cụm cân) tái lập.
- **DBSCAN cho ra gì ở eps nào** (đọc thẳng từ bảng, không tune tay):
  - ms=5: p50: k=18, noise=0.37, sil=-0.0611; p60: k=17, noise=0.27, sil=-0.1696; p70: k=8, noise=0.21, sil=-0.2173; p80: k=8, noise=0.12, sil=-0.0633; p90: k=2, noise=0.05, sil=0.2180.
  - ms=10: p50: k=3, noise=0.35, sil=0.0256; p60: k=3, noise=0.25, sil=0.1838; p70: k=1, noise=0.20, sil=n/a; p80: k=1, noise=0.11, sil=n/a; p90: k=1, noise=0.04, sil=n/a.
- **Hình thức vs thành phần**: 2/10 combo DBSCAN cho k=3 (DBSCAN ms=10 eps=0.2134 (k-dist p50) sizes=[470, 11, 7], ARI non-noise 0.0562; DBSCAN ms=10 eps=0.2446 (k-dist p60) sizes=[536, 13, 10], ARI non-noise 0.0506) — cùng HÌNH THỨC '1 cụm lớn + 2 cụm li ti' như đóng băng [577, 16, 5] nhưng thành phần khác hẳn (ARI non-noise ≈ 0); cụm li ti của ứng viên có trùng cụm 0/1 đóng băng hay không xem đếm chéo bên dưới.
- **Có cụm nào tương đương STING không** — đếm chéo trên 747 dòng:

| STING đóng băng | KMeans cụm 0 | KMeans cụm 1 | KMeans cụm 2 |
|---|---|---|---|
| cụm 0 | 4 | 0 | 1 |
| cụm 1 | 0 | 0 | 16 |
| cụm 2 | 178 | 274 | 125 |
| nhiễu (−1) | 52 | 33 | 64 |
| STING đóng băng | Ward cụm 0 | Ward cụm 1 | Ward cụm 2 |
|---|---|---|---|
| cụm 0 | 0 | 0 | 5 |
| cụm 1 | 0 | 16 | 0 |
| cụm 2 | 370 | 116 | 91 |
| nhiễu (−1) | 43 | 59 | 47 |
| STING đóng băng | DBSCAN best cụm 0 | DBSCAN best cụm 1 | DBSCAN best cụm 2 | DBSCAN best cụm 3 | DBSCAN best cụm 4 | DBSCAN best cụm 5 | DBSCAN best cụm 6 | DBSCAN best cụm 7 | DBSCAN best nhiễu (−1) |
|---|---|---|---|---|---|---|---|---|---|
| cụm 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cụm 1 | 11 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 |
| cụm 2 | 524 | 2 | 3 | 3 | 6 | 4 | 3 | 3 | 29 |
| nhiễu (−1) | 69 | 8 | 2 | 2 | 5 | 3 | 2 | 0 | 58 |

- KMeans: cụm 0 (5 dòng) → cụm 0: 4/5 (80%); cụm 1 (16 dòng) → cụm 2: 16/16 (100%); cụm 2 (577 dòng) → cụm 1: 274/577 (47%).
- Ward: cụm 0 (5 dòng) → cụm 2: 5/5 (100%); cụm 1 (16 dòng) → cụm 1: 16/16 (100%); cụm 2 (577 dòng) → cụm 0: 370/577 (64%).
- DBSCAN best (DBSCAN ms=5 eps=0.2267 (k-dist p80)): cụm 0 (5 dòng) → cụm 0: 5/5 (100%); cụm 1 (16 dòng) → cụm 0: 11/16 (69%); cụm 2 (577 dòng) → cụm 0: 524/577 (91%).

- **Verdict ngưỡng thắng (chốt trước)**: KHÔNG ứng viên nào vượt mốc trên cả 3 chỉ số — đọc trung thực: không có cơ sở từ lane này để thay STING đóng băng; khuyến nghị mặc định giữ nguyên cấu hình cho tới khi GV quyết định.
- **Đọc theo thành phần** (verdict giữ nguyên, không đổi metric sau khi thấy số):
  - silhouette: 7/12 ứng viên vượt mốc -0.0651 (top: KMeans k=3 (seed 11, n_init=10) 0.3360; Ward k=3 (linkage=ward) 0.3336; DBSCAN ms=5 eps=0.2989 (k-dist p90) 0.2180) — NHƯNG mốc là silhouette của CHÍNH phân hoạch công bố trên z-trong-năm và nó ÂM (dưới chuẩn hóa này phân hoạch công bố không tách biệt hình học), và silhouette của DBSCAN/STING tính trên non-noise nên n_sil khác nhau giữa các dòng — không so tuyệt đối.
  - tái lập cấu trúc: KHÔNG ứng viên nào tái lập phân hoạch đóng băng — ARI non-noise tối đa 0.0742, ARI đầy đủ tối đa 0.3390 (≈ 0). Ghi chú về ngưỡng chốt trước: mốc ARI của 'STING đóng băng tính lại' là ARI của mốc với chính nó (= 1.0), nên tiêu chí 'ARI > mốc' đọc nghĩa đen là không thể đạt bởi ứng viên nào; nội dung ràng buộc có ý nghĩa của tiêu chí là 'tái lập cấu trúc đóng băng' — và KHÔNG ứng viên nào đạt.
  - deconfound (quyết định cách hiểu ARI): chính STING refit trên z-trong-năm cũng chỉ đạt ARI non-noise 0.0060 với nhãn gốc của nó — phần lớn khoảng cách ARI giữa ứng viên và nhãn gốc là HIỆU ỨNG CHUẨN HÓA, không phải hiệu ứng thuật toán. Trên cùng chuẩn hóa (cột 'vs refit'), ứng viên đồng thuận nhất là DBSCAN ms=10 eps=0.3273 (k-dist p80) (k=1, ARI non-noise 0.5432, đầy đủ 0.6190) — k=1 nên sự đồng thuận này chủ yếu là 'cùng mô tả một khối/cấu trúc lớn', KHÔNG phải cùng phân hoạch nhiều cụm.
  - kết luận chung: không có cơ sở từ lane này để thay STING đóng băng; dưới z-trong-năm, dữ liệu 2D đọc là 'một khối + ngoại vi' ở mọi thuật toán, còn phân hoạch 3 cụm cân của KMeans/Ward có silhouette cao hơn nhưng KHÔNG liên kết với cấu trúc đã công bố (ARI ≈ 0) — việc 'thắng silhouette' của chúng là đổi câu hỏi, không phải tái lập cấu trúc; quyền kết luận thuộc GV.

## Hạn chế & phạm vi

- Exploratory: 12 combo ứng viên × 1 cửa sổ; KHÔNG hiệu chỉnh đa so sánh, KHÔNG tuyên bố p-value — guard chống fishing là ngưỡng thắng chốt trước + duyệt đọc trung thực; adoption cần GV (reports/model_deep_dive.md:293-299, nhóm (b)).
- Tiêu chí 'nhất quán ≥4/6 fold' của đề bài áp dụng cho hồi quy/phân loại (có 6 fold expanding origin 2017–2022); clustering KHÔNG có fold nên tiêu chí này KHÔNG áp dụng được ở lane này — chỉ so ngang chỉ số trên cùng cửa sổ như pre-registered.
- 4 năm cửa sổ không đủ 63 dòng ({2014: 61, 2018: 61, 2021: 60, 2022: 61}) — z-trong-năm vẫn dùng mean/sd của chính năm đó; số 'mỗi năm 63 điểm' trong đề bài là gần đúng, không ảnh hưởng phương pháp.
- ARI đo sự TÁI LẬP cấu trúc nhãn đóng băng (pseudo-label), không phải chất lượng phân cụm tuyệt đối; nhãn cụm 0/1 của STING là cụm li ti (5/16 dòng chỉ ở 2011–2018) — mọi kết luận vững chỉ nên dựa trên tương phản nhiễu vs cụm 2 (results/cluster_profile.md:127).
- Silhouette KMeans/Ward tính trên CẢ 747 điểm gồm cả 149 điểm mà STING gọi là nhiễu — so với silhouette non-noise của STING là khác tập điểm; cột n_sil ghi rõ tập điểm mỗi dòng.
- NOT_RUN: không có mục NOT_RUN — script tính được toàn bộ metrics yêu cầu trong ask; các kiểm định phiên (2 lần chạy sha256 byte-giống, ruff, pytest) do lane báo cáo kèm, nằm ngoài tệp này.

## Tái lập

```powershell
python -E scripts/candidates_clustering.py
python -m ruff check .
```

- Đầu vào (chỉ đọc): `results/predict_all_years.csv`, `models/predict_config.json`.
- Đầu ra MỚI: file này + `results/candidates_clustering.csv`.
- Tất định: seed 11 (KMeans); DBSCAN/Ward/STING tất định; không có thời gian hệ thống trong đầu ra → chạy 2 lần cho md/csv sha256 byte-giống.
- Script fail-closed: cửa sổ ≠ 747 dòng, phân bố nhãn lệch, hoặc số dòng bị loại ≠ 122 đều DỪNG với lỗi rõ ràng (artifact đóng băng đã đổi).
