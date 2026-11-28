# Kiểm định Suy luận Bảng (Year-FE CR1 / TWFE), Kiểm soát Đa kiểm định & Chẩn đoán Không gian

Tài liệu bổ trợ học thuật cho `results/external_validation.md`, `results/high_dim_sting.md` và `results/regression_deep_analysis.md`.
Tái lập: `python -E scripts/analysis/panel_inference.py` (seed=42, B=1.999 Wild Cluster Rademacher / hoán vị không gian).

## 1. So sánh Kiểm định Gộp (Naive MWU) vs Bảng chuẩn hóa Năm + Sai số Gộp theo Tỉnh (CR1) & TWFE

| Nhánh | Biến ngoài | n (G tỉnh) | Naive MWU p | β (Year-FE) | SE (CR1) | Hệ số nở SE | p CR1 | p WCR boot | p TWFE (Tỉnh+Năm) | Holm / BH (nhánh) | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|---|
| STING 2D (3/4/5/2) | PCI 2011–2022 | 726 (63) | 8.14e-07 | -0.1737 | 0.4499 | 1.42× | 0.7007 | 0.7045 | 0.3525 | 1.0000 / 0.8888 | Nhiễu giả theo năm: biến mất hoàn toàn khi thêm Year-FE & CR1 SE (p=0,70) |
| STING 2D (3/4/5/2) | GRDP/người 2018–2024 | 429 (63) | 0.0046 | -21.2309 | 11.3526 | 1.67× | 0.0662 | 0.0770 | 0.0707 | 0.1986 / 0.1986 | Không đủ bằng chứng dưới Year-FE CR1 (ngưỡng 5%) |
| STING 2D (3/4/5/2) | Hộ nghèo GSO 2012–2024 | 793 (63) | 0.7674 | -0.1294 | 0.9219 | 1.12× | 0.8888 | 0.8895 | 0.5292 | 1.0000 / 0.8888 | Không đủ bằng chứng dưới Year-FE CR1 (ngưỡng 5%) |
| 8D Quantile mc=7 (≤2023) | PCI 2011–2022 | 411 (63) | 3.96e-34 | +1.5612 | 0.6279 | 1.27× | 0.0156 | 0.0150 | 0.3420 | 0.0468 / 0.0468 | Sống sót Year-FE CR1, WCR & Holm/BH 5% (between-province, TWFE p=0,34) |
| 8D Quantile mc=7 (≤2023) | GRDP/người 2018–2023 | 201 (60) | 0.0430 | -23.2043 | 12.7824 | 1.11× | 0.0746 | 0.0955 | 0.1084 | 0.1491 / 0.1039 | Bị loại sau Year-FE CR1 & Holm/BH (naive MWU từng gây nhiễu dương giả) |
| 8D Quantile mc=7 (≤2023) | Hộ nghèo GSO 2012–2023 | 393 (63) | 7.26e-06 | -3.9084 | 2.3682 | 1.92× | 0.1039 | 0.0990 | 0.7249 | 0.1491 / 0.1039 | Bị loại sau Year-FE CR1 & Holm/BH (naive MWU từng gây nhiễu dương giả) |
| 8D Quantile wy-z mc=7 | PCI 2011–2022 | 415 (63) | 0.0160 | +1.1990 | 0.5040 | 1.59× | 0.0205 | 0.0190 | 0.8097 | — | Bền vững ngay cả sau chuẩn hóa within-year z (khử xu hướng năm) |
| CLIQUE Quantile 4D (4.1–4.3,6.3) | PCI 2011–2022 | 94 (43) | 2.38e-13 | +5.1508 | 1.1610 | 0.64× | 6.48e-05 | 0.0115 | 0.3015 | — | Cực trị phân tách giai đoạn: C0 2011–17 vs C1 2018–22 (ít năm giao, cần thận trọng) |

### Phát hiện suy luận trọng yếu

- **STING 2D chính thức trên PCI 2011–2022 (`2d_pci`)**: kiểm định gộp thô cho `p = 8.14e-07`, nhưng khi đưa Fixed Effects theo năm + CR1 theo 63 tỉnh, chênh lệch Cụm 2 vs Nhiễu chỉ còn `β = -0.174` (SE = 0.450, `p_cr1 = 0.7007`, `p_wcr = 0.7045`; kiểm định đồng thời 4 nhóm Wald `F = 0.1586, p = 0.9237`). Bằng chứng này khẳng định tín hiệu PCI trên STING 2D chủ yếu là **nhiễu trộn theo năm (year composition confounding)**.
- **8D QuantileSTING mc=7 trên PCI (`hd8_q7_pci`)**: **sống sót toàn bộ bộ lọc suy luận chặt** — sau Year-FE + CR1 (hệ số phình SE = 1.27×), nhóm Vùng cao đa chiều vẫn cao hơn Vùng thấp `β = +1.561` điểm PCI (SE = 0.628, `p_cr1 = 0.0156`, `p_wcr = 0.0150`, **Holm = 0.0468 < 0,05**), và vẫn giữ ý nghĩa khi chuẩn hóa within-year z (`hd8_wy_pci`: `β = +1.199`, `p_cr1 = 0.0205`). Ngược lại, TWFE (Tỉnh + Năm) cho `β = +0.391, p = 0.3420` (switchers `n = 49`, `p_t = 0.6086`): cơ chế là **phân tầng cấu trúc giữa các tỉnh (between-province structural stratification)** chứ không phải dao động ngắn hạn nội tỉnh.
- **Loại dương giả trên GRDP**: ngay cả trên 8D Quantile mc=7, `naive MWU` từng cho `p_thô = 0.0430` (`p_dm = 0.0249`) trên GRDP 2018–2023, nhưng khi hiệu chỉnh Year-FE CR1 biến mất (`p_cr1 = 0.0746`, Holm = `0.1491`).

## 2. Kiểm soát Đa kiểm định (Holm / BH / BY FDR) trên 383 Không gian con (`high_dim_sting_subspaces.csv`)

| Biến ngoài | Số phép thử (m) | Naive p < 0,05 | Sống sót BH-FDR 5% | Sống sót BY-FDR 5% | Sống sót Holm FWER 5% |
|---|---|---|---|---|---|
| PCI (khử trung vị năm) | 383 | 161 (42.0%) | **117** (30.5%) | **68** (17.8%) | **34** (8.9%) |
| GRDP (khử trung vị năm) | 202 | 56 (27.7%) | **32** | **13** | **10** |

## 3. Chẩn đoán Tự tương quan Không gian Phần dư Holdout 2024 (Moran's I, Queen Contiguity, 1.999 hoán vị)

| Chuỗi không gian (năm 2024) | n tỉnh | Moran's I | z (lý thuyết) | p lý thuyết | p hoán vị (2 phía) | Kết luận |
|---|---|---|---|---|---|---|
| sd_6_1 quan sát 2024 (tất cả 61 tỉnh có điểm) | 61 | +0.1834 | +2.196 | 0.0281 | 0.0395 | Có tự tương quan không gian |
| sd_6_1 quan sát 2024 (59 tỉnh khớp holdout) | 59 | +0.1406 | +1.677 | 0.0936 | 0.1370 | Không rõ / yếu ở ngưỡng 5% |
| Dự báo điểm Ridge 2024 (59 tỉnh holdout) | 59 | +0.3155 | +3.535 | 0.0004 | 0.0015 | Có tự tương quan không gian |
| Phần dư Ridge 2024 (actual - pred_ridge) | 59 | -0.0431 | -0.274 | 0.7838 | 0.6600 | Hấp thụ sạch (white noise) |
| Phần dư Quantile q50 2024 | 59 | +0.0598 | +0.818 | 0.4131 | 0.5265 | Hấp thụ sạch (white noise) |
| Sai phân Δ6.1 = actual_2024 - sd_6_1_2023 | 59 | +0.0499 | +0.713 | 0.4756 | 0.6025 | Không rõ / yếu ở ngưỡng 5% |

Dự báo điểm `pred_ridge` 2024 mang cấu trúc không gian rõ rệt (`I = +0.3155`, `p_perm = 0.0015` vs quan sát `n=59`: `I = +0.1406`, `p_perm = 0.1370`), giúp **phần dư `residual_ridge` trở nên trắng về mặt không gian** (`I = -0.0431`, `p_perm = 0.6600`) — chứng tỏ tập 8 đặc trưng trễ đã hấp thụ tự tương quan không gian địa lý mà chưa cần biến trễ không gian riêng.

## Đầu ra kèm theo
- Bảng đầy đủ: `results/panel_inference.csv`
- Biểu đồ 4 khung: `results/figs/panel_inference_diagnostics.png`
- Trang Excel: sheet `Suy luận bảng & FDR` trong `results/KetQua_STING_PAPI.xlsx`
