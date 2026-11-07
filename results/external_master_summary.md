# Master table ngoại lai 63 tỉnh × 2011–2024 — tóm tắt

Sinh bởi `scripts/build_external_master.py` (gap [1], reports/external_data_expansion.md §4.2). Nối LEFT theo khóa `(province_code, year)` — tức `papi_province_code` của panel PAPI — với validate="one_to_one": **882 dòng × 59 cột**, giữ đúng lưới panel, không nội suy.

## 1) Mask thiếu tường minh từng nguồn

| Nguồn | Cột mask | Ô có giá trị | Tỷ lệ trên 882 | Cửa sổ |
|---|---|---|---|---|
| PCI (VCCI–USAID) | `pci_present` | 816/882 | 92.5% | 2011–2022 đủ 63 tỉnh; 2023–2024 chỉ Top-30 |
| GSO dân số trung bình | `pop_present` | 882/882 | 100.0% | 2011–2024 đủ (trộn 2 vintage, xem §3) |
| GSO GRDP/người | `grdp_present` | 441/882 | 50.0% | 2018–2024 (2024 = Sơ bộ); thiếu 2011–2017 |
| ODM bệnh viện (số điểm) | `odm_present` | 63/882 | 7.1% | snapshot 2020 duy nhất |
| GSO rác thải kg/người | `waste_present` | 305/882 | 34.6% | 2015–2017 + 2019 đủ 63; 2018 trống; 2020 còn 53 |
| Panel PAPI: đủ sd_4_2 & sd_6_1 | `papi_sd46_present` | 869/882 | 98.5% | 13 ô tỉnh-năm thiếu → không có nhãn cụm |

## 2) Ô có giá trị theo năm (mỗi mask, đếm trên 63 tỉnh/năm)

|   year |   n_panel_rows |   pci_present |   pop_present |   grdp_present |   odm_present |   waste_present |   papi_sd46_present |
|-------:|---------------:|--------------:|--------------:|---------------:|--------------:|----------------:|--------------------:|
|   2011 |             63 |            63 |            63 |              0 |             0 |               0 |                  63 |
|   2012 |             63 |            63 |            63 |              0 |             0 |               0 |                  63 |
|   2013 |             63 |            63 |            63 |              0 |             0 |               0 |                  63 |
|   2014 |             63 |            63 |            63 |              0 |             0 |               0 |                  61 |
|   2015 |             63 |            63 |            63 |              0 |             0 |              63 |                  63 |
|   2016 |             63 |            63 |            63 |              0 |             0 |              63 |                  63 |
|   2017 |             63 |            63 |            63 |              0 |             0 |              63 |                  63 |
|   2018 |             63 |            63 |            63 |             63 |             0 |               0 |                  61 |
|   2019 |             63 |            63 |            63 |             63 |             0 |              63 |                  63 |
|   2020 |             63 |            63 |            63 |             63 |            63 |              53 |                  63 |
|   2021 |             63 |            63 |            63 |             63 |             0 |               0 |                  60 |
|   2022 |             63 |            63 |            63 |             63 |             0 |               0 |                  61 |
|   2023 |             63 |            30 |            63 |             63 |             0 |               0 |                  61 |
|   2024 |             63 |            30 |            63 |             63 |             0 |               0 |                  61 |

## 3) Vintage dân số GSO (cột `pop_source` giữ từng dòng)

- `gso_nien_giam_extract`: 504 dòng (năm 2012, 2013, 2014, 2018, 2019, 2020, 2021, 2022)
- `gso_pxweb_V02.01`: 378 dòng (năm 2011, 2015, 2016, 2017, 2023, 2024)
- Lệch vintage đã định lượng trong `data/raw/gso/PROVENANCE.md` (504 tỉnh-năm giao: chênh trung bình 8,49 nghìn người, max 189,63 Hà Nội 2014, 104 dòng >1%) — file master giữ nguyên giá trị từng vintage, không trộn bình quân.

## 4) 13 ô panel thiếu sd_4_2/sd_6_1 (không có nhãn cụm)

- 2014: Bac Giang, Dong Thap
- 2018: Quang Ninh, Dong Thap
- 2021: Quang Ninh, Bac Giang, Bac Ninh
- 2022: Bac Giang, Bac Ninh
- 2023: Quang Ninh, Binh Duong
- 2024: Vinh Phuc, Tien Giang

Các ô này là lý do mask phải xuống cấp **tỉnh-năm** chứ không chỉ theo năm: ví dụ 2018 thiếu Quảng Ninh + Đồng Tháp, 2021 thiếu 3 tỉnh (Quảng Ninh, Bắc Giang, Bắc Ninh).

## 5) Quy tắc dùng

- Mọi phân tích external phải khai báo "chạy trên `mask` = n/882 ô" và KHÔNG nội suy ô False.
- Không tự tính lại PCI weighted score từ sub-index.
- Rác thải đã là kg/người (nhãn replication package `code/validate_gso.py:11`: "kg/person/day") — không chuẩn hóa thêm.
- Provenance đầy đủ: `data/processed/external_provenance.md` và `data/raw/*/PROVENANCE.md`.