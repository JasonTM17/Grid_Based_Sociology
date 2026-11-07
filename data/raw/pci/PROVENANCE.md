# PROVENANCE — PCI (pcivietnam.vn) — bổ sung năm 2011, 2023, 2024

- **Nguồn:** Chỉ số Năng lực cạnh tranh cấp tỉnh (PCI) — VCCI/USAID, công khai tại
  <https://pcivietnam.vn>. Trang dữ liệu: `/du-lieu-pci` (VN) | `/en/pci-data` (EN);
  trang xếp hạng: `/en/pci-ranking?year=<y>`. Chính sách trích dẫn dữ liệu của trang:
  <https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html> (ghi nguồn
  VCCI — USAID khi sử dụng lại).
- **Ngày tải:** 2026-11-07 (curl, không đăng nhập, không vượt cơ chế bảo vệ nào).
- **Script chuyển đổi:** `scripts/build_pci_full.py` (chạy từ thư mục gốc repo:
  `python -E scripts/build_pci_full.py`; chỉ đọc file gốc trong thư mục này, ghi
  `data/processed/external_pci_63_full.csv`).

## Điểm tổng hợp (weighted score) từng năm lấy từ đâu

| Năm | Nguồn điểm tổng | Ghi chú |
|---|---|---|
| 2011 | `Indicator_PCI2011_EN.xls`, sheet `Summary`, cặp cột U–V ("PCI 2011") | Bảng xếp theo rank từng sub-index; cột B là tỉnh theo rank Entry Costs, KHÔNG phải cặp với điểm tổng |
| 2012–2022 | extract Mendeley (Le et al., DOI 10.17632/wbk42j9wc8.1) — đã có trong `data/processed/external_pci_63.csv` | `source = mendeley_extract` |
| 2023 | Trang xếp hạng chính thức `/en/pci-ranking?year=2023` (file `pci_ranking_page_2023.html`) | Workbook 2023 (cả bản EN lẫn VN) KHÔNG có cột điểm tổng — chỉ 10 sub-index + vùng |
| 2024 | `Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx`, sheet `Summary`, cột "The Weighted PCI Score" | Khớp trang xếp hạng 2024 (chênh lệch ≤ 0,005 = làm tròn 2 chữ số) |

## Phủ dữ liệu và nguyên nhân ô trống (KHÔNG nội suy)

- 2011–2022: đủ 63 tỉnh/năm.
- 2023: chỉ **Top 30** có điểm tổng. Từ PCI 2022, báo cáo PCI đổi cách trình bày
  "từ toàn bộ cả nước sang Top 30" (Báo cáo PCI & PGI 2023, tr. 24 và 43; file
  `VN-Bao-cao-dai-PCI-2023_VN.pdf`). 33 tỉnh còn lại có tính điểm nhưng không được
  công bố trong báo cáo, workbook hay trang xếp hạng — để trống trong CSV.
- 2024: workbook chỉ chứa điểm tổng của **Top 30**, 33 dòng tỉnh để trống trong file
  gốc (Báo cáo PCI 2024 tr. 18: "công bố danh sách 30 tỉnh, thành phố dẫn đầu").
  Khớp đúng 30 giá trị với trang xếp hạng 2024 (chênh ≤ 0,005).

## Kiểm chứng chéo đã chạy (in trong log của script)

1. 2011 workbook vs trang xếp hạng 2011: 61/63 khớp tuyệt đối; 2 lệch là cặp
   **Bắc Giang / Bắc Cạn bị hoán tên trên trang xếp hạng hiện tại**.Workbook:
   Bắc Giang 60,79 (hạng 23), Bắc Cạn 52,71 (hạng 60) — được Báo cáo PCI 2014
   (`Bao_cao_PCI_2014_EN.pdf`, tr. 37–38, hồ sơ "BẮC KẠN 2011 52,71 60" và
   "BẮC GIANG 2011 60,79 23") xác nhận. CSV lấy theo workbook.
2. 2023 trang xếp hạng vs Báo cáo PCI & PGI 2023 (tr. 45–46, Hình 1.4 và đoạn văn):
   khớp từng giá trị (Quảng Ninh 71,25 hạng 1 … Thanh Hóa 66,79 hạng 30).
3. 2024 workbook vs trang xếp hạng 2024: 30/30 cặp khớp (chênh lệch ≤ 0,005).
4. Tập 63 mã tỉnh suy ra từ tên nguồn phải khớp giữa các nguồn cùng năm
   (workbook ↔ trang xếp hạng) sau chuẩn hóa tên (bỏ dấu + bí danh).

## Lỗi dữ liệu đã phát hiện ở nguồn (ghi nhận, không sửa file gốc)

- Workbook 2024, sheet Summary dòng 66: dòng "Yen Bai" trùng lặp với điểm 0
  (artifact cuối bảng) — bỏ qua khi parse.
- Workbook 2023 EN, dòng 66: "Lang Son" trùng lặp; bản VN dòng 66: "Yên Bái"
  trùng lặp; sau đó là Min/Median/Max (VN: "Thấp nhất"/"Trung vị"/"Cao nhất") — bỏ qua.
- Trang xếp hạng 2011: hoán tên Bắc Giang ↔ Bắc Cạn (xem mục kiểm chứng chéo).

## Ghi chú khác

- `Du_lieu_PCI_2025.xlsx` (PCI 2025, công bố 2026) KHÔNG dùng cho panel: cấu trúc mới
  sau sáp nhập 34 tỉnh, 9 chỉ số thành phần, không có cột điểm tổng — chỉ lưu làm bằng chứng.
- pandas/openpyxl có sẵn; `xlrd` 2.0.2 và `pypdf` 6.18.0 được cài vào user site-packages
  để đọc `.xls` (2011) và trích PDF kiểm chứng.
- Console Windows: script ép stdout/stderr UTF-8 để in được chữ Việt.

## Manifest file gốc (tên — bytes — SHA-256)

| File | Bytes | SHA-256 |
|---|---|---|
| `Appendix_1_Table_Indicator_PCI2023_EN_web.xlsx` | 175730 | `76c98530fb2fecbd3ef27fce1212ad2dc90348ec1a849ff3b87b07977c3f5897` |
| `Appendix_1_Table_Indicator_PCI2023_VN_web.xlsx` | 178259 | `efecb26ea200543d450879cbc2338c02bb3356646426204195910660c5e5d1e8` |
| `Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx` | 178889 | `8997f2712b096198e9867ae9542ab47765021358e03c2f25b789e19b43eb9a15` |
| `Bao_cao_ho_so_tinh_2023.pdf` | 10915572 | `34f97e9548a5aec14f85681155ef16e8ad646223d4c7d2b8acf87a1e142ed1ba` |
| `Bao_cao_PCI_2014_EN.pdf` | 4710505 | `060704adbba8c1083679a96dfd4698c8a24650bed65efdf7fc114973cb7188c1` |
| `Bao_cao_PCI_2024_VN.pdf` | 7551225 | `b9988783b64d19f206904cdd1e333d4ad51323058bfcdd4f8f41f67d7e9f3ee7` |
| `Du_lieu_PCI_2025.xlsx` | 120759 | `e85325c407cf4e3f1579324606967aa362d02c634c9acff1e3111ef1717f6d07` |
| `Indicator_PCI2011_EN.xls` | 274944 | `d438840246b847531d73b3c3545ee8303292b0cb18bcb870df69db778e3bdbea` |
| `pci_ranking_page_2011.html` | 50115 | `6812bd48559c9485b2c5b0745e2cdd77d8ab3fd79a7c089e0372f9ad69745282` |
| `pci_ranking_page_2023.html` | 50082 | `c639da3b619389f58558dc6dcd48c87995fafde957c8bb970238d9877a930748` |
| `pci_ranking_page_2024.html` | 50082 | `cee9ddfcfdf0f6601c0f3a8e3425d3d8b14fec5ef092cd810a1d58d65c6b0529` |
| `VN-Bao-cao-dai-PCI-2023_VN.pdf` | 8671852 | `117de699ccc26e1795e30c51a802f097a25a2290647b4ab3abc7f5a256f517b1` |
