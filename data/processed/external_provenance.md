# PROVENANCE — Dữ liệu ngoại lai (PCI · GSO · OD Mekong · World Bank WDI)

- **Nền Mendeley:** Le et al. — Replication data and code for "Digital Governance"
  (Mendeley Data V1, **CC BY 4.0**, DOI: 10.17632/wbk42j9wc8.1). File gốc đã nằm
  trong repo tại `data/raw/mendeley/Replication_package/data/` với
  `PROVENANCE.md` riêng.
- **Ngày chuẩn hóa:** 2026-11-07 — script `scripts/build_external_panel.py`
  (chỉ đọc file gốc, ghi file mới; không sửa file gốc).
- **Khóa nối:** `province_crosswalk_63.csv` (kèm trong gói) → `province_ascii`
  → `province_code` của panel PAPI (`data/processed/papi_panel_63_2011_2024.csv`).

## File nền sinh từ gói replication Mendeley (script này)

| File | Nội dung |
|---|---|
| `external_pci_63.csv` | Điểm PCI tổng theo tỉnh-năm (`pci_weighted_score`) |
| `external_gso_population_63.csv` | Dân số, dân số đô thị, % đô thị (GSO, trích Niên giám) |
| `external_gso_waste_63.csv` | Rác thải bình quân đầu người `kg_pc`/`kg_urb` — nhãn đơn vị trong `code/validate_gso.py:11`: "GSO collected kg/person/day" |
| `external_63_panel.csv` | Bảng nối ngoài đầy đủ theo tỉnh-năm (khóa `papi_province_code`) |

## Nguồn gốc từng file gốc (ghi trong chính file SOURCE_EXTRACTED)

- PCI: các workbook "Indicator_PCI<year>_EN.xlsx" từ pcivietnam.vn, sheet `Summary`.
- GSO dân số: Niên giám Thống kê (bản PDF nso.gov.vn), phần dân số theo tỉnh.
- Cần đối chiếu workbook gốc trước khi kết luận về thang đo/gián đoạn chuỗi.

## File mở rộng từ tải trực tiếp 2026-11-07 (script riêng, provenance riêng trong data/raw/*/PROVENANCE.md)

| File | Script sinh | Nguồn gốc | License |
|---|---|---|---|
| `external_pci_63_full.csv` | `scripts/build_pci_full.py` | workbook + trang xếp hạng `data/raw/pci/` (2011, 2023, 2024) + nền Mendeley 2012–2022 | dữ liệu công khai pcivietnam.vn (VCCI–USAID) |
| `external_gso_population_63_full.csv` | `scripts/build_gso_grdp_pop.py` | pxweb V02.01 `data/raw/gso/` + nền Mendeley | NSO công khai ("Bản quyền: Không") |
| `external_gso_grdp_63.csv` | `scripts/build_gso_grdp_pop.py` | pxweb V03.12 `data/raw/gso/` (2018–2024; 2024 = Sơ bộ) | NSO công khai |
| `external_odm_poverty_region_1998_2016.csv` | `scripts/build_odmekong_external.py` | OD Mekong `data/raw/odmekong/` (6 VÙNG, không cấp tỉnh) | CC BY-SA |
| `external_odm_health_63.csv` | `scripts/build_odmekong_external.py` | OD Mekong Health Facilities 2020 + point-in-polygon `data/raw/boundaries/diaphantinh.geojson` | ODbL |
| `external_worldbank_vnm.csv` | `scripts/build_external_worldbank.py` | WDI API v2, quốc gia VNM `data/raw/worldbank/` | CC BY 4.0 |
| `external_poverty_gap_63.csv` | `scripts/build_poverty_gap.py` | Niên giám Thống kê 2018–2021 (bảng nghèo đa chiều), `data/raw/gso/` — 63 tỉnh × 2017–2019, 189 dòng 0 ô thiếu, vintage mới nhất chứa năm | NSO công khai ("Bản quyền: Không") |
| `external_poverty_63.csv` | `scripts/build_poverty_63.py` | pxweb V14.47 (882 dòng, 2006/2008/2010 + 2012–2025) + `external_poverty_gap_63.csv` điền 2017–2019 (tích hợp 2026-11-08) = 1071 dòng × 17 năm; cột `source` ghi nguồn theo từng dòng | NSO công khai — phái sinh của hai nguồn trên |
| `external_molisa_poverty_63.csv` | `scripts/build_molisa_poverty.py` | Phụ lục I các QĐ 862/2017, 1052/2018, 835/2019 của MOLISA `data/raw/molisa/` — 63 tỉnh × 2017–2019 | văn bản pháp luật công khai |
| `external_master_63_2011_2024.csv` | `scripts/build_external_master.py` | nối panel PAPI + các file trên, mask thiếu tường minh | phái sinh — giữ license nguồn |

**Vai trò MOLISA — kiểm chứng chéo ĐỘC LẬP, KHÔNG gộp vào chuỗi chính:** trên 189 ô
giao (63 tỉnh × 2017–2019), nghèo-only MOLISA (rà soát hành chính theo QĐ
862/1052/835) lệch có hệ thống so với GSO NGTK (khảo sát): 178/189 ô lệch
>0,1 điểm %, mean |Δ| = 2,48 điểm %, max 14,16 điểm % (Gia Lai 2017: GSO 27,5
vs MOLISA 13,34; Lai Châu, Sơn La, Kon Tum cùng pattern) — hai PHÉP ĐO khác
nhau, không phải bản sao; gộp sẽ phá tính thuần nhất của panel kiểm định cụm.
Đo trực tiếp từ 2 CSV trong phiên tích hợp 2026-11-08. WB/UNDP (6 vùng hợp
tỉnh, `data/raw/{worldbank,undp}/`) không có province_code — giữ làm tham
chiếu, không tích hợp.

Trạng thái từng khoảng trống dữ liệu: `reports/external_data_expansion.md` §4.2.
Đối chiếu chi tiết từng nguồn (độ phủ, vintage, kiểm chứng chéo): file đó.

## Giấy phép

Dữ liệu giữ nguyên **CC BY 4.0** của gói replication — trích dẫn DOI khi dùng lại;
các nguồn tải trực tiếp giữ license riêng ghi trong bảng trên (CC BY 4.0 /
CC BY-SA / ODbL / công khai ghi nguồn).
