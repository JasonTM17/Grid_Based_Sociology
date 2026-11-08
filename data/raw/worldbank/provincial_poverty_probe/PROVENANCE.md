# World Bank — Truy tìm nghèo cấp tỉnh Việt Nam (provincial_poverty_probe)

## Mục đích
Chốt câu hỏi: World Bank có công bố nghèo cấp tỉnh (admin1/63 tỉnh) VN dạng
open data không? Ngày truy tìm: 2026-11-08. Mọi file ở đây là dữ liệu NGUỒN
KHÔNG TIN CẬY cho tới khi được kiểm chứng ở giai đoạn tích hợp.

## Bằng chứng KHÔNG có 63 tỉnh (đã truy vấn, lưu response nguyên trạng)
1. API v2 chỉ cấp quốc gia:
   - `https://api.worldbank.org/v2/country/VNM/indicator/SI.POV.DDAY?format=json&per_page=100`
     -> `api_v2_VNM_SI.POV.DDAY_national.json` (HTTP 200; mọi dòng country.iso3Code=VNM).
   - `SI.POV.NAHC` tương tự -> `api_v2_VNM_SI.POV.NAHC_national.json`.
2. Dimension "country" của API không có admin1:
   - `https://api.worldbank.org/v2/country/VNM-HAN/indicator/SI.POV.DDAY?format=json`
     -> `api_v2_NEGATIVE_admin1code_VNM-HAN.json`:
     `[{"message":[{"id":"120","key":"Invalid value","value":"The provided parameter value is not valid"}]}]`.
3. Nguồn API số 38 "Subnational Poverty" — KHÔNG có VN admin1:
   - Danh mục nguồn `https://api.worldbank.org/v2/sources?format=json&per_page=300`
     -> `api_v2_sources_list.json` (71 nguồn; id 5 Subnational Malnutrition,
     38 Subnational Poverty, 50 Subnational Population).
   - Source 38 chỉ có 3 chỉ số (SI.POV.NAHC/RUHC/URHC)
     -> `api_v2_source38_indicators.json` (total=3).
   - Dump toàn quốc gia source 38 SI.POV.NAHC
     -> `api_v2_source38_allcountries_SI.POV.NAHC.json` (15.516 dòng, 111 thực
     thể; admin1 của Bangladesh/Bhutan/Belarus... có mặt) — nhưng VN chỉ có 18
     dòng cấp QUỐC GIA 1996-2013 giá trị null, KHÔNG có thực thể admin1 nào.
   - Truy vấn riêng VN:
     `https://api.worldbank.org/v2/country/VNM/indicator/SI.POV.NAHC?source=38&format=json`
     -> `api_v2_VNM_source38_SI.POV.NAHC.json` (total=0).
4. PIP API (Poverty and Inequality Platform):
   - `https://api.worldbank.org/pip/v1/pip?country=VNM&year=2022&format=json`
     -> `pip_v1_VNM_2022.json`: reporting_level="national", survey VHLSS.
   - Thử `reporting_level=all`, `coverage_area=urban`, `coverage_area=rural`
     -> trả về payload national giống hệt (3 file bytes như nhau).
   - `https://api.worldbank.org/pip/v1/_swagger.json` -> 404
     (`pip_v1_swagger.json`).
5. MapVietnam `https://www.worldbank.org/mapvietnam/`: trình xem bản đồ tương
   tác; curl bị vòng lặp redirect www -> www5 (curl exit 47 MAXREDIRS sau 50
   lần, 2026-11-08) — không phải kênh tải open data dạng file.

## Bằng chứng CÓ — subnational 6 vùng (không phải 63 tỉnh), tải được, CC BY 4.0
- Bộ dữ liệu: Subnational Poverty and Inequality Database (SPID), Data Catalog
  dataset 0064796, admin level 1, 141+ nền kinh tế, 1999-2022, License:
  Creative Commons Attribution 4.0. Trang:
  `https://datacatalog.worldbank.org/search/dataset/0064796/subnational-poverty-and-inequality-database-spid`
- File tải nguyên trạng (HTTP 200, 2026-11-08):
  - `https://datacatalogfiles.worldbank.org/ddh-published/0064796/DR0092191/AM26%20-%20SPID%20data.xlsx`
    -> `AM26-SPID_data.xlsx` (18.419.638 B).
  - `https://datacatalogfiles.worldbank.org/ddh-published/0064796/DR0092190/AM26%20-%20Subnational%20MPM.xlsx`
    -> `AM26-Subnational_MPM.xlsx` (1.224.391 B).
- VN trong SPID: `code=VNM`, `lvlvar=subnatid1`, `geo_code=VNM_2015_GAULx_1..6`
  — đúng 6 vùng hợp tỉnh; danh sách tỉnh thành viên nằm trong cột `sample`
  (ví dụ GAULx_1 = "Bac Ninh & Ha Nam & Ha Noi City & ... & Vinh Phuc").
  KHÔNG có mức 63 tỉnh trong file.
- Phủ VN: monetary (sheet Data, nhóm ALL) 2002-2022 cách năm (VHLSS) x 6 vùng;
  MPM nghèo đa chiều 2010-2022 x 6 vùng.

## Tệp xuất từ SPID (script tạo; vẫn là dữ liệu nguồn chưa kiểm chứng)
- `spid_vnm6_admin1_monetary_extract.csv` — 66 dòng (11 năm x 6 vùng, nhóm
  ALL): year, geo_code, sample, mean2021, poor300, poor420, poor830, gini, theil.
- `spid_vnm6_admin1_mpm_extract.csv` — 42 dòng (7 năm x 6 vùng).
- Script: `scripts/wb_undp_poverty_probe.py`, chạy từ thư mục gốc repo
  `python -E scripts/wb_undp_poverty_probe.py`. KHÔNG merge vào
  data/processed ở giai đoạn truy tìm.

## Giấy phép
CC BY 4.0 — World Bank Terms of Use for Datasets,
https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets

## Manifest (tên file — bytes — SHA-256)

| Tên file | Bytes | SHA-256 |
|---|---|---|
| AM26-SPID_data.xlsx | 18419638 | 4a63361863218b1a58be1b116ba0425c52e5fcd2d5acc4d524da57b38f206a51 |
| AM26-Subnational_MPM.xlsx | 1224391 | 422e8e0e3d9c8257da7a63c17ef1d31c751fd26845c15fe5db27d443d017e48a |
| api_v2_country_VNM.json | 458 | 7ddd064eb77613024ad050f7b885a61c239c01692ec59ef4b352ed100f2b7525 |
| api_v2_NEGATIVE_admin1code_VNM-HAN.json | 102 | f230e5b6d8f652aa544aec29624faa117c27571ce309a7a474584e1cfeb45c1b |
| api_v2_source38_allcountries_SI.POV.NAHC.json | 480057 | 6875061f58d17dbe250768cb282610cc2c54efe42d71c3e21311291f4f649c37 |
| api_v2_source38_indicators.json | 2187 | a3f1706da96e6e233fd793120e2c191438a996cdabb9ac26ad8b391ead140c80 |
| api_v2_sources_list.json | 13048 | bc128731b210cfdba0121abce50aa63b6b42ba39de25e2c0911c4ca163a88347 |
| api_v2_VNM_SI.POV.DDAY_national.json | 16123 | f4e99c906091c1ac3bb9075f49c18fc6b87be06badb060233639492a29808d4d |
| api_v2_VNM_SI.POV.NAHC_national.json | 16121 | 7be81dcb58736d36ebe0a4edd4ab5c07fd373ef45bbe70c594852b5bcd7388ea |
| api_v2_VNM_source38_SI.POV.NAHC.json | 85 | 244e629ceec4b53324246967388d17b706efe2207744b8148d60ea52dbccd264 |
| pip_v1_swagger.json | 54 | 3494d22a0b9ae1678a72df5841b7a6ec60e75499b91341f9763a556d6b8cb1f9 |
| pip_v1_VNM_2022.json | 906 | 0e3a15634841d9a3c431710e984f3dacd5d6aff7ed0b41fc6ba7cb9f7c780cb5 |
| pip_v1_VNM_2022_coverage_rural.json | 906 | 0e3a15634841d9a3c431710e984f3dacd5d6aff7ed0b41fc6ba7cb9f7c780cb5 |
| pip_v1_VNM_2022_coverage_urban.json | 906 | 0e3a15634841d9a3c431710e984f3dacd5d6aff7ed0b41fc6ba7cb9f7c780cb5 |
| pip_v1_VNM_2022_reporting_all.json | 906 | 0e3a15634841d9a3c431710e984f3dacd5d6aff7ed0b41fc6ba7cb9f7c780cb5 |
| spid_vnm6_admin1_monetary_extract.csv | 13441 | f19bd030df0455183152b3e203b5d36f9b24c2f59ce5daff99ed22b82ffb4dfa |
| spid_vnm6_admin1_mpm_extract.csv | 3718 | fd7527dce314ca866999e29dab46718424a3e9c71cc555c1fcee2514f310090d |
