# UNDP — Truy tìm nghèo đa chiều cấp tỉnh Việt Nam

## Mục đích
Chốt câu hỏi: UNDP (vn.undp.org) có file số liệu nghèo đa chiều cấp tỉnh tải
được không? Ngày truy tìm: 2026-11-08. Mọi file ở đây là dữ liệu NGUỒN KHÔNG
TIN CẬY cho tới khi được kiểm chứng ở giai đoạn tích hợp.

## Bằng chứng: báo cáo UNDP Việt Nam = PDF, KHÔNG có file số liệu
- undp.org chặn curl (HTTP 403 "Access Denied" — bot protection, 2026-11-08);
  response 403 lưu nguyên trạng: `undp_vn_page_mpi_report_2021.html`,
  `undp_vn_page_mpi_report_2018.html`.
- Qua WebFetch (render như trình duyệt), hai trang báo cáo nghèo đa chiều chính
  của UNDP Việt Nam chỉ có link PDF:
  - "Viet Nam Multi-dimensional Poverty Report 2021"
    (https://www.undp.org/vietnam/publications/viet-nam-multi-dimensional-poverty-report-2021):
    MDP_full-E-7-2022.pdf, MDP_full-V-7-2022.pdf, MDP_SummaryE+V-7-2022.pdf.
  - "Multidimensional Poverty in Viet Nam" (2018)
    (https://www.undp.org/vietnam/publications/multidimensional-poverty-viet-nam):
    MDP-full-E.pdf, Bao-cao.pdf, Summary-report-MDP-final-EN.pdf,
    Summary-report-MDP-final-VN.pdf.
  - Không có bất kỳ xlsx/csv nào trên cả hai trang.

## Bằng chứng: UNDP/OPHI Global MPI subnational — 6 vùng, tải được (HDX, CC0)
- CKAN API của HDX: `https://data.humdata.org/api/3/action/package_show?id=global-mpi`
  -> `hdx_ckan_global_mpi.json` (dataset "Global Multidimensional Poverty
  Index", license "Public Domain / No restrictions (CC0)").
- File subnational tải được (HTTP 200 qua redirect 302):
  `https://data.humdata.org/dataset/42b16840-3a56-4a20-9314-7aa171f1136c/resource/45b18fbb-ab0d-4f54-ae23-c078f1eccf25/download/subnational-results-mpi.xlsx`
  -> `ophi_hdx_subnational-results-mpi.xlsx` (1.935.836 B).
- VN trong bảng "5.1 MPI Region": đúng 6 vùng (Central Highlands, Mekong River
  Delta, North Central & Central Coast, Northern Uplands, Red River Delta,
  Southeast), nguồn MICS 2020-2021 — KHÔNG có 63 tỉnh.
- Nguồn gốc: OPHI (University of Oxford) cho UNDP HDR; trích dẫn trong file:
  Alkire, S., Mishra, R., Selden, L. and Suppa, N. (2025), "The global
  Multidimensional Poverty Index (MPI) 2025: Disaggregation results and
  methodological note", OPHI MPI Methodological Note 62.

## Tệp xuất (script tạo; vẫn là dữ liệu nguồn chưa kiểm chứng)
- `ophi_vnm6_mpi_extract.csv` — 6 dòng (6 vùng, MICS 2020-2021): survey,
  survey_year, region_name, mpi, headcount_h_pct, intensity_a_pct,
  vulnerable_to_poverty_pct, severe_poverty_pct.
- Script: `scripts/wb_undp_poverty_probe.py`, chạy từ thư mục gốc repo
  `python -E scripts/wb_undp_poverty_probe.py`. KHÔNG merge vào
  data/processed ở giai đoạn truy tìm.

## Kết luận
UNDP không công bố nghèo (đa chiều) cấp 63 tỉnh dạng file số liệu; mức nhỏ nhất
của UNDP/OPHI là 6 vùng. Báo cáo cấp tỉnh của UNDP Việt Nam chỉ có PDF.

## Giấy phép
- HDX global MPI: CC0 (Public Domain / No restrictions).
- Nội dung undp.org: (c) UNDP — trang báo cáo không phải open data file.

## Manifest (tên file — bytes — SHA-256)

| Tên file | Bytes | SHA-256 |
|---|---|---|
| hdx_ckan_global_mpi.json | 93035 | 821fca425d15b4065e441a0771e5b9e0028155ffaaba9c6246200db4642adde0 |
| ophi_hdx_subnational-results-mpi.xlsx | 1935836 | 80da87a9e96fb848fc256de04cebdcdf2198ca60deef329d06f300ec3abb0d4d |
| ophi_vnm6_mpi_extract.csv | 821 | c80fef180471d873c1e9b9b80f47251dabeceb82d1a8bfea6f097cd7b3a160a5 |
| undp_vn_page_mpi_report_2018.html | 438 | 56acf38d1453ec910cd9c3931b8219f26ead3a05063f6eeb64bd99c67cfe5716 |
| undp_vn_page_mpi_report_2021.html | 463 | c2d85863f4904ea27be4405732cba676e4e70c20dadf1884e34f0c1c91f38bd6 |
