# Kiểm định Suy luận Bảng (Year-FE CR1 / TWFE), Kiểm soát Đa kiểm định & Chẩn đoán Không gian

Tài liệu bổ trợ học thuật cho `results/external_validation.md`, `results/high_dim_sting.md` và `results/regression_deep_analysis.md`.
Tái lập: `python -E scripts/analysis/panel_inference.py` (seed=42, B=1.999 Wild Cluster Rademacher / hoán vị không gian).

## 1. So sánh Kiểm định Gộp (Naive MWU) vs Bảng chuẩn hóa Năm + Sai số Gộp theo Tỉnh (CR1) & TWFE

| Nhánh | Biến ngoài | n (G tỉnh) | Naive MWU p | β (Year-FE) | SE (CR1) | Hệ số nở SE | p CR1 | p WCR boot | p TWFE (Tỉnh+Năm) | Holm/BH nhánh | Holm 6 phép | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STING 2D (3/4/5/2) | PCI 2011–2022 | 726 (63) | 8.14e-07 | -0.1737 | 0.4499 | 1.42× | 0.7007 | 0.7075 | 0.3525 | 1.0000 / 0.8888 | 1.0000 | Nhiễu giả theo năm: biến mất hoàn toàn khi thêm Year-FE & CR1 SE (p=0,70) |
| STING 2D (3/4/5/2) | GRDP/người 2018–2024 | 429 (63) | 0.0046 | -21.2309 | 11.3526 | 1.67× | 0.0662 | 0.0830 | 0.0707 | 0.1986 / 0.1986 | 0.3309 | Không đủ bằng chứng dưới Year-FE CR1 (ngưỡng 5%) |
| STING 2D (3/4/5/2) | Hộ nghèo GSO 2012–2024 | 793 (63) | 0.7674 | -0.1294 | 0.9219 | 1.12× | 0.8888 | 0.8890 | 0.5292 | 1.0000 / 0.8888 | 1.0000 | Không đủ bằng chứng dưới Year-FE CR1 (ngưỡng 5%) |
| 8D Quantile mc=7 (≤2023) | PCI 2011–2022 | 411 (63) | 3.96e-34 | +1.5612 | 0.6279 | 1.27× | 0.0156 | 0.0185 | 0.3420 | 0.0468 / 0.0468 | 0.0937 | Year-FE CR1 đạt 5%; Holm nhánh 3 phép 0.0468; Holm 6 phép chính 0.0937 (không đạt 5%); TWFE p=0.3420 không bác bỏ 0 |
| 8D Quantile mc=7 (≤2023) | GRDP/người 2018–2023 | 201 (60) | 0.0430 | -23.2043 | 12.7824 | 1.11× | 0.0746 | 0.0975 | 0.1084 | 0.1491 / 0.1039 | 0.3309 | Bị loại sau Year-FE CR1 & Holm nhánh (naive MWU từng gây nhiễu dương giả) |
| 8D Quantile mc=7 (≤2023) | Hộ nghèo GSO 2012–2023 | 393 (63) | 7.26e-06 | -3.9084 | 2.3682 | 1.92× | 0.1039 | 0.1225 | 0.7249 | 0.1491 / 0.1039 | 0.3309 | Bị loại sau Year-FE CR1 & Holm nhánh (naive MWU từng gây nhiễu dương giả) |
| 8D Quantile wy-z mc=7 | PCI 2011–2022 | 415 (63) | 0.0160 | +1.1990 | 0.5040 | 1.59× | 0.0205 | 0.0200 | 0.8097 | — | — | Độ nhạy, không nằm trong Holm xác nhận: within-year z |
| CLIQUE Quantile 4D (4.1–4.3,6.3) | PCI 2011–2022 | 94 (43) | 2.38e-13 | +5.1508 | 1.1610 | 0.64× | 6.48e-05 | 0.0230 | 0.3015 | — | — | Thăm dò: phân tách giai đoạn, không nằm trong Holm xác nhận |

### Phát hiện suy luận trọng yếu

- **STING 2D chính thức trên PCI 2011–2022 (`2d_pci`)**: kiểm định gộp thô cho `p = 8.14e-07`, nhưng khi đưa Fixed Effects theo năm + CR1 theo 63 tỉnh, chênh lệch Cụm 2 vs Nhiễu chỉ còn `β = -0.174` (SE = 0.450, `p_cr1 = 0.7007`, `p_wcr = 0.7075`; kiểm định đồng thời 4 nhóm Wald `F = 0.1586, p = 0.9237`). Bằng chứng này khẳng định tín hiệu PCI trên STING 2D chủ yếu là **nhiễu trộn theo năm (year composition confounding)**.
- **8D QuantileSTING mc=7 trên PCI (`hd8_q7_pci`)**: sau Year-FE + CR1, vùng cao cao hơn vùng thấp `β = +1.561` điểm PCI (SE = 0.628, `p_cr1 = 0.0156`, `p_wcr = 0.0185`). **Holm nội họ 8D (3 phép) = 0.0468**; **Holm 6 phép chính = 0.0937 (không đạt 5%)**. Chuẩn hóa within-year z là độ nhạy ngoài Holm (`hd8_wy_pci`: `β = +1.199`, `p_cr1 = 0.0205`). TWFE cho `β = +0.391, p = 0.3420` (switchers `n = 49`, `p_t = 0.6086`): **chưa đủ bằng chứng** cho dao động ngắn hạn nội tỉnh; không suy ra đã chứng minh phân tầng cấu trúc.
- **Loại dương giả trên GRDP**: ngay cả trên 8D Quantile mc=7, `naive MWU` từng cho `p_thô = 0.0430` (`p_dm = 0.0249`) trên GRDP 2018–2023, nhưng khi hiệu chỉnh Year-FE CR1 biến mất (`p_cr1 = 0.0746`, Holm = `0.1491`).

## 2. Kiểm soát Đa kiểm định thăm dò (Holm / BH / BY) trên 383 p-value Kruskal–Wallis xếp chồng (`high_dim_sting_subspaces.csv`; 223 bộ đặc trưng PCI)

Đây là sàng lọc thăm dò: p-value KW tính trên dòng tỉnh–năm đã khử trung vị năm, chưa phải sai số gộp theo tỉnh. Không đưa vào Holm xác nhận của 6 phép Year-FE CR1.

| Biến ngoài | Số phép thử (m) | Bộ đặc trưng | Naive p < 0,05 | BH-FDR 5% | BY-FDR 5% | Holm FWER 5% |
|---|---|---|---|---|---|---|
| PCI (khử trung vị năm) | 383 | 223 | 161 (42.0%) | **117** (30.5%) | **68** (17.8%) | **34** (8.9%) |
| GRDP (khử trung vị năm) | 202 | 167 | 56 (27.7%) | **32** | **13** | **10** |

## 3. Chẩn đoán Tự tương quan Không gian Phần dư Holdout 2024 (Moran's I, Queen Contiguity, 1.999 hoán vị)

| Chuỗi không gian (năm 2024) | n tỉnh | Moran's I | z (lý thuyết) | p lý thuyết | p hoán vị (2 phía) | Kết luận |
|---|---|---|---|---|---|---|
| sd_6_1 quan sát 2024 (tất cả 61 tỉnh có điểm) | 61 | +0.1834 | +2.196 | 0.0281 | 0.0235 | Có tự tương quan không gian |
| sd_6_1 quan sát 2024 (59 tỉnh khớp holdout) | 59 | +0.1406 | +1.677 | 0.0936 | 0.0930 | Không rõ / yếu ở ngưỡng 5% |
| Dự báo điểm Ridge 2024 (59 tỉnh holdout) | 59 | +0.3155 | +3.535 | 0.0004 | 0.0010 | Có tự tương quan không gian |
| Phần dư Ridge 2024 (actual - pred_ridge) | 59 | -0.0431 | -0.274 | 0.7838 | 0.7930 | Chưa phát hiện tự tương quan không gian ở ngưỡng 5% |
| Phần dư Quantile q50 2024 | 59 | +0.0598 | +0.818 | 0.4131 | 0.4120 | Chưa phát hiện tự tương quan không gian ở ngưỡng 5% |
| Sai phân Δ6.1 = actual_2024 - sd_6_1_2023 | 59 | +0.0499 | +0.713 | 0.4756 | 0.4690 | Không rõ / yếu ở ngưỡng 5% |

Dự báo điểm `pred_ridge` 2024 mang cấu trúc không gian (`I = +0.3155`, `p_perm = 0.0010` vs quan sát `n=59`: `I = +0.1406`, `p_perm = 0.0930`). Phần dư `residual_ridge` **chưa phát hiện** tự tương quan không gian ở ngưỡng 5% (`I = -0.0431`, `p_perm = 0.7930`) trên 59 tỉnh đối chiếu; hoán vị lấy tâm tại `E[I]=-1/(n-1)`. Không suy ra phần dư là nhiễu trắng mọi khía cạnh.

## Đầu ra kèm theo
- Bảng đầy đủ: `results/panel_inference.csv`
- Biểu đồ 4 khung: `results/figs/panel_inference_diagnostics.png`
- Trang Excel: sheet `Suy luận bảng & FDR` trong `results/KetQua_STING_PAPI.xlsx`
