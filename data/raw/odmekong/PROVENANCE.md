# PROVENANCE — Open Development Vietnam / OD Mekong Datahub

- **Nguồn:** Open Development Vietnam (ODM), `vietnam.opendevelopmentmekong.net` / datahub `data.opendevelopmentmekong.net`
- **Ngày tải:** 2026-11-07
- **Phương thức:** CKAN API (`/api/3/action/package_show`, `package_search`) + tải resource trực tiếp bằng curl; không cần đăng ký, không bị chặn.

## Giấy phép

- Dataset "Proportion of poor households by region in Vietnam from 1998 to 2016": **Creative Commons Attribution Share-Alike (CC BY-SA)** — http://www.opendefinition.org/licenses/cc-by-sa
- Dataset "COVID-19 quarantine areas and treatment hospitals in Vietnam": **CC BY-SA** (license_title = "Creative Commons Attribution Share-Alike")
- Dataset "Health Facilities in Mekong Countries 2020": **ODbL** (Open Data Commons Open Database License) — khác CC BY-SA, ghi theo đúng license_title của dataset.
- Quy ước chung của OD Mekong: CC BY-SA 4.0 (https://vietnam.opendevelopmentmekong.net/terms-of-use/).

## Dataset "Poverty rate" theo tỉnh — KHÔNG TÌM THẤY (đã bị gỡ)

- Trang dataset id `poverty-rate` (URL cũ trong nhiệm vụ: `vietnam.opendevelopmentmekong.net/dataset/?id=poverty-rate`, redirect 302 → `https://data.vietnam.opendevelopmentmekong.net//dataset/poverty-rate`) trả **HTTP 404** cả trên trang web lẫn API:
  - `GET /api/3/action/package_show?id=poverty-rate` → `{"success": false, "error": {"message": "Not found", "__type__": "Not Found Error"}}`
  - Cũng 404 trên datahub chính `data.opendevelopmentmekong.net`.
- Rà soát catalog thay thế (kết quả lưu trong các file `_search_*.json`):
  - `package_search?q=poverty` → 439 kết quả; `title:poverty` → 81; `"poverty rate"` → 10; `"tỷ lệ nghèo"` → 3. Toàn bộ dataset poverty của VN còn lại:
    1. `proportion-of-poor-households-by-region-in-vietnam` — poverty rate theo **6 VÙNG** (không phải 63 tỉnh), 1998–2016, CC BY-SA;
    2. `61-poorest-districts-in-vietnam` — cấp huyện, chỉ KML;
    3. `covid-19-impacts-on-society-in-vietnam` — rate_poor chỉ Urban/Rural.
- Wayback Machine tạm offline lúc tải ("Internet Archive: Temporarily Offline") nên không kiểm chứng được bản lưu cũ của trang `poverty-rate`.
- Kết luận: **không còn dataset poverty theo tỉnh trên nguồn này**; lấy bản 6 vùng làm thay thế tốt nhất có được, xuất ra `data/processed/external_odm_poverty_region_1998_2016.csv` (KHÔNG đặt tên `external_odm_poverty_63.csv` vì dữ liệu không phải cấp tỉnh).

## Manifest — tên file — bytes — SHA-256

### Dữ liệu tải về

```
poverty/poverty_rate_1998_2016.csv — 717 — f63d4be9353f737254476bbc6839d315d2f1986ab498a42f8c55fb04258f7385
poverty_covid/rate_poor_dataset_en.csv — 1172 — e972684d186024860e53c2c557b40d188591a9f62ebcb77aa471a5f0a859446b
health/mekong_countries_hospitals_dump.csv — 261244 — 7dca3ff594ee9d3b3c3e7375a7701619791a8cc29702db00e70f3aeecd6ad386
health_covid/quarantine_en.csv — 9992 — e423c56869d70802c37e3e2bcde55c7c7481244e0e4717aa1087245e3a2f2f65
```

### Bằng chứng tra cứu metadata (CKAN API responses)

```
_search_poverty_api.json — 183984 — 14e10f4d58042ed95022ca61b88902710c676ccdb8765957cbeea8eddf8dfc2d
_search_poverty_vn.json — 362098 — 844e9c250bc070d96b02666aad8d04367511b9310b2809635b7ad639cf54e7ec
_search_poverty_title.json — 49499 — 9ccb533427e88fb64f8627748b4cf0866f8507810d79d54d704bd5614f71fa16
_search_poverty_all.json — 5933113 — 50ab6aec298085345e8d55ffb313337e38ad4a6f4e0c5d7d03d94184ae39d306
_all_0.json — 6250774 — c34b4600d2e3726a4a8e6db343531be5b4e1f825d9fe723fb8161a210824da42
_all_500.json — 6143298 — 8bd9c7fa78d2cf9a28fd87aa0afc7f41c2a6c2f0998f71f8af612514ace89d28
_all_1000.json — 7812315 — 1a1c3e36cfca37f7bdecc385641759e3c320b976f48f4aded707a2768f423957
_all_1500.json — 7823562 — 3c840972c47c5e8257447f576496f05e87143b9c92d7b707891747ccfa6b298c
_pkg_poor_households.json — 15433 — a16cd952bc2de0dd52320c9e960d617a433bf2608d1de7079cbc0c4a14c3fc4f
_pkg_lowermekong.json — 6813 — b2b68f0972b003e553a56c6e2f5ef819e35989a04f454c3f20c2209c966b2df8
_pkg_hdi_vn.json — 28395 — d670bb74411eac32ceefaaa3f739fb9c8af6c183f99b46f7b3aa1284aee24458
_pkg_health.json — 16611 — c5aba5b03465fdb9b618a751f60db2a92b4b930bdee47387db6218b792106e69
_pkg_covid_hosp.json — 8280 — e1b1397d29f0e51f636ab783aee73ee690d2d0b275fd63d8233a77802b9bcb4a
```

## URL gốc của từng resource

| File | Dataset | Resource URL |
|---|---|---|
| `poverty/poverty_rate_1998_2016.csv` | [proportion-of-poor-households-by-region-in-vietnam](https://data.vietnam.opendevelopmentmekong.net/dataset/proportion-of-poor-households-by-region-in-vietnam) | https://data.opendevelopmentmekong.net/dataset/c476e859-7294-4dd0-a4ba-dcf7af43d350/resource/5e5feb6d-aab0-48b5-96f8-a0d22c3e3796/download/poverty_rate_1998_2016.csv |
| `poverty_covid/rate_poor_dataset_en.csv` | [covid-19-impacts-on-society-in-vietnam](https://data.vietnam.opendevelopmentmekong.net/dataset/covid-19-impacts-on-society-in-vietnam) | https://data.opendevelopmentmekong.net/dataset/587c70ae-d529-43eb-a6eb-c86d0909f0df/resource/06f0696b-5fa7-4112-a91c-85562a5bd585/download/rate_poor_dataset_en.csv |
| `health/mekong_countries_hospitals_dump.csv` | [health-facilities-in-mekong-countries-2020](https://data.vietnam.opendevelopmentmekong.net/dataset/health-facilities-in-mekong-countries-2020) | https://data.vietnam.opendevelopmentmekong.net/datastore/dump/ad45d153-d682-48e0-8d92-de3bfe6bf8ac |
| `health_covid/quarantine_en.csv` | [covid-19-quarantine-areas-and-treatment-hospitals-in-vietnam](https://data.vietnam.opendevelopmentmekong.net/dataset/covid-19-quarantine-areas-and-treatment-hospitals-in-vietnam) | https://data.opendevelopmentmekong.net/dataset/b7b95a98-4b2e-44ae-9aaa-69d199f24091/resource/5dd53360-f6b0-4729-a986-21eee2add660/download/quarantine_en.csv |

## Ghi chú xử lý

- File `poverty_rate_1998_2016.csv` phân tách bằng **TAB** dù đuôi `.csv`; cột `1998` trùng đúng giá trị cột `2002` ở cả 6 vùng (đặc thù file nguồn, giữ nguyên).
- `health/mekong_countries_hospitals_dump.csv`: dump datastore 2.169 điểm `fclass=hospital` toàn Mekong (SRID 4326, EWKB), không có cột tỉnh/quốc gia. Chuyển tỉnh bằng point-in-polygon với `data/raw/boundaries/diaphantinh.geojson` (63 tỉnh): 423 điểm nằm trong VN. Có 3 ten_tinh lỗi chính tả trong nguồn được map tường minh trong `scripts/build_odmekong_external.py` (`Bà Rịa -Vũng Tàu`, `Cần Thơn`, `Quản Bình`); 3 tên không dấu được fold về dạng chuẩn (`Kien Giang`, `Đăk Lăk`, `Đăk Nông`). 1.746 điểm còn lại thuộc nước Mekong khác — không dùng.
- Số liệu nguồn KHÔNG sửa; mọi biến đổi chỉ đọc file raw và ghi file mới vào `data/processed/`.
