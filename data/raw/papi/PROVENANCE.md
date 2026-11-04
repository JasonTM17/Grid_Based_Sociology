# PROVENANCE — PAPI Provincial Indicators 2011–2024

- **Nguồn:** PAPI (Vietnam Provincial Governance and Public Administration Performance Index) —
  CECODES, VFF-CRT, RTA & UNDP. Trang dữ liệu: <https://papi.org.vn/du-lieu-papi/>
- **Ngày tải:** 2026-11-03 (người dùng tải trực tiếp từ trang chính thức; file đặt tại `data/raw/papi/`).
- **Giấy phép:** dữ liệu công bố công khai cho mục đích nghiên cứu/học tập theo trang nguồn
  (gói tải về không kèm file LICENSE riêng). Trích dẫn nguồn khi dùng lại.
- **Bất biến:** không chỉnh sửa file gốc; mọi biến đổi thực hiện bằng script trong `scripts/`.

## Manifest 14 file (tên — bytes — SHA-256)

| File | Bytes | SHA-256 |
|---|---|---|
| PAPI-2011-data-1.xlsx | 53,539 | `5975cd6702b253c0b89cb1e5448958320e41974d7b10b5b6ddbbb721d17a415d` |
| PAPI-2012-data-1.xlsx | 53,361 | `ed0364735431fa9ce327dad0de90b984d9efd761a62bf006dfa5d0f350da8e7f` |
| PAPI-2013-data-1.xlsx | 53,382 | `258b0f063635c657afd943d671276d4a5fafa3f80c993a953734bbe45d8431a7` |
| PAPI-2014-data-1.xlsx | 52,912 | `217cca49449794ed9125ab39d6667bf0433bc09dadb966ca009a410be66eebb7` |
| PAPI-2015-data-1.xlsx | 71,413 | `03b46b314a91611db2156ba34c3b592286baa857dcda1675fcfa6c8050747774` |
| PAPI-2016-data-1.xlsx | 71,430 | `6cc8332d3d68c0dd88f28038b3de900bd7d73ff851c4efa88ac1eb26d46713b1` |
| PAPI-2017-data-1.xlsx | 71,296 | `b2ca05435e6047553bd200bf25e333b02ef8de21b0046a76bf4778a81d447922` |
| PAPI-2018-data.xlsx | 94,298 | `6cead4c6ebbbbc77d8ce6af8c05ac857bfbaa03f95517f6b629938d829c8dbff` |
| PAPI2019-data.xlsx | 245,881 | `f749234a8a2213bc2c7485a519db9da96838f59dede732a928e8e44a5e29e9e4` |
| 2020PAPI_ProvincialIndicators_BangChiTieuCapTinh-1.xlsx | 353,826 | `6b38f6dd8da891cc52f5579d1a94b5143363da605b43658379a04f7d04bac020` |
| 1.2021PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx | 482,890 | `f8a3195172c2cad9517e2671f023ed13601896aa545a135571c192bfa76fc54b` |
| 2022PAPI_ProvincialIndicators_BangChiTieuCapTinh-2.xlsx | 878,552 | `b3b50388a0032eb7ebcf52e7b2c9fa56981f3eac1f11b979246e547283de44fb` |
| 2023PAPI_ProvincialIndicators_BangChiTieuCapTinh..xlsx | 1,561,636 | `5f497d0324dc33c20b9cadd0373a0fe91da89e42c551d5186aa7c03f029cbcab` |
| 2024PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx | 1,939,961 | `299b935b5491bde3df995ea3c051692e9ca1e9a3b3600dbda78476abe16c763d` |

## Chain-of-custody

- **2020, 2021, 2023** khớp SHA-256 với ledger của gói nghiên cứu Mendeley
  (`data/raw/mendeley/Replication_package/data/SHA256_PAPI_ORIGINALS.txt`).
- 8 file (2011–2016, 2020, 2021) khớp byte-identical với bản lưu Wayback Machine (snapshot 20240809).
- **File 2024 trong repo là bản 63 tỉnh** (hash `299b935b…`). Tồn tại một bản tái phát hành
  **34 tỉnh hậu sáp nhập** trong ledger Mendeley (hash `d9314e59…`) — KHÁC file này, không dùng lẫn.
- Ghi chú cấu trúc: 2011–2019 sheet đầu tiên chứa điểm (tên sheet khác nhau từng năm);
  2020–2024 ma trận chuyển vị, header 2 dòng (Mã tỉnh dòng 1, tên tỉnh dòng 2). `d7/d8` chỉ có từ 2018.
- **Gãy thang đo:** 23/37 cột chỉ tiêu có bước nhảy trung bình năm > 0.25 điểm
  (vd `sd_5_4` đổi 0.25–2.5 → 0.33–3.33 tại 2021) — audit tự động: `python scripts/check_data.py`.
