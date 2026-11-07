# World Bank WDI — Việt Nam (VNM)

## Nguồn
- World Bank World Development Indicators (WDI), API v2, quốc gia VNM.
- URL tải mỗi chỉ số (đã dùng, hoạt động): `https://api.worldbank.org/V2/country/VNM/indicator/<MA_CHI_SO>?downloadformat=csv` — API trả ZIP; CSV dữ liệu bên trong được tách ra cùng thư mục, đổi tên `<MA_CHI_SO>.csv`.
- Lệnh mẫu ban đầu `format=csv&per_page=2000` (inline CSV) bị API từ chối ngày 2026-11-07: trả XML lỗi `Invalid format — The requested response format was not found`; đã chuyển sang `downloadformat=csv` như trên.
- Các chỉ số tải: `SH.XPD.CHEX.GD.ZS` = Current health expenditure (% of GDP); `NY.GDP.PCAP.CD` = GDP per capita (current US$); `SP.URB.TOTL.IN.ZS` = Urban population (% of total population); `SH.MED.BEDS.ZS` = Hospital beds (per 1,000 people).
- Phạm vi: cấp QUỐC GIA (VNM), không có chiều tỉnh — dùng làm bối cảnh vĩ mô, không nối theo tỉnh.
- Ngày tải: 2026-11-07. Ngày cập nhật dữ liệu WDI ghi trong file (Last Updated Date): 2026-10-08.
- Giấy phép: CC BY 4.0 — World Bank Terms of Use for Datasets, https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets.

## Xử lý
- File `*.zip` là bản tải nguyên trạng; file `<MA_CHI_SO>.csv` là CSV dữ liệu tách từ ZIP (giữ nguyên nội dung, chỉ đổi tên). Hai file metadata khác trong ZIP (Metadata_Country, Metadata_Indicator) không tách ra; xem trong ZIP nếu cần.
- Chuẩn hóa: `data/processed/external_worldbank_vnm.csv` — dạng long (indicator_code, indicator_name, year, value), lọc năm 2010–2024, bỏ hàng giá trị trống. Không nội suy, không bịa số liệu.
- Script tạo lại file này mỗi lần chạy: `scripts/build_external_worldbank.py` (chạy từ thư mục gốc repo bằng `python -E scripts/build_external_worldbank.py`).

## Kiểm tra chéo với JSON API (cùng nguồn, render khác định dạng)

- `SH.XPD.CHEX.GD.ZS`: KHOP (14 nam 2010-2024 giong het JSON API)
- `NY.GDP.PCAP.CD`: KHOP (15 nam 2010-2024 giong het JSON API)
- `SP.URB.TOTL.IN.ZS`: KHOP (15 nam 2010-2024 giong het JSON API)
- `SH.MED.BEDS.ZS`: KHOP (8 nam 2010-2024 giong het JSON API)

## Manifest (tên file — bytes — SHA-256)

| Tên file | Bytes | SHA-256 |
|---|---|---|
| NY.GDP.PCAP.CD.csv | 1535 | 6cca544643a610bb2dab20b373f1c3b41bb91abb58a39096ff3005927809d990 |
| NY.GDP.PCAP.CD.zip | 2012 | c53c6b47f1280be76a30039bffbc14e04ee6011e4aa63b38e01c5aced45f940b |
| SH.MED.BEDS.ZS.csv | 1027 | 06a8cae9f3a6e97a50b5ea8ba666d773d117b5644c741072ae40fd9220acce70 |
| SH.MED.BEDS.ZS.zip | 1479 | 0435dc048ae6df5ab27df32317252b3c2ad8a9eda7bee009df9b92ca10a94c2f |
| SH.XPD.CHEX.GD.ZS.csv | 1134 | 3e25b40470a8636c0f9066db5438fced9878d3d9ad2b0d1d32b639dbf650e6ba |
| SH.XPD.CHEX.GD.ZS.zip | 1654 | 9394b8e2c532ac42608a7dadf6274938f0793e6c7aaa441efaafedf420f0202f |
| SP.URB.TOTL.IN.ZS.csv | 1948 | 7aa87c67df20bf83b30b01ceb5e60dc8e8a39ad18116735537cef50c2b271483 |
| SP.URB.TOTL.IN.ZS.zip | 2031 | a93abc1f2369da2bd56446038bc1a1f563c6e067a9f5c7eed568c846ae8103a3 |
