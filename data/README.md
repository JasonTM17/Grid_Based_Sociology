# Dữ liệu gốc & Dữ liệu đã xử lý (`data/`)

Toàn bộ dữ liệu được tách rõ thành hai tầng bất biến (`raw/`) và dẫn xuất (`processed/`).
Để biết nhanh trong `raw/` file nào là dữ liệu, nguồn nào dùng làm gì (đặc biệt gói
đối chiếu Mendeley), xem **[`raw/README.md`](raw/README.md)** và **[`raw/mendeley/README.md`](raw/mendeley/README.md)**.

## `data/raw/` — Dữ liệu nguồn gốc (không chỉnh tay)

| Thư mục | Nội dung | Hồ sơ nguồn |
|---|---|---|
| `papi/` | 14 bảng tính Excel PAPI 2011–2024 & báo cáo PAPI 2024 | `data/raw/papi/PROVENANCE.md` |
| `mendeley/` | Gói đối chiếu Le et al. (CC BY 4.0) & bảng crosswalk 63 tỉnh | `data/raw/mendeley/PROVENANCE.md` |
| `boundaries/` | Ranh giới hành chính 63 tỉnh `diaphantinh.geojson` | `data/raw/boundaries/PROVENANCE.md` |
| `pci/` | Chỉ số năng lực cạnh tranh cấp tỉnh PCI (VCCI–USAID) | `data/raw/pci/PROVENANCE.md` |
| `gso/` | Niên giám Thống kê & bảng PX-Web GSO (dân số, GRDP, nghèo V14.47) | `data/raw/gso/PROVENANCE.md` |
| `molisa/` | Phụ lục chuẩn nghèo đa chiều 2017–2019 (MOLISA) | `data/raw/molisa/PROVENANCE.md` |
| `odmekong/` | Dữ liệu nghèo theo vùng & mật độ cơ sở y tế 2020 (OD Mekong) | `data/raw/odmekong/PROVENANCE.md` |
| `worldbank/`, `undp/` | Chỉ số vĩ mô WDI & kết quả rà soát nghèo cấp tỉnh | `PROVENANCE.md` trong từng thư mục |
| `course/` | Tài liệu bài giảng tham khảo về học máy, tiền xử lý, hồi quy và phân cụm, lưu cục bộ | `data/raw/course/SHA256SUMS.txt` |

## `data/processed/` — Dữ liệu đã chuẩn hóa & ghép bảng

| Tệp | Mô tả | Script tái tạo |
|---|---|---|
| `papi_panel_63_2011_2024.csv` | Panel PAPI chính (882 dòng × 41 cột = 63 tỉnh × 14 năm) | `python scripts/data/build_panel.py` |
| `papi_panel_v1_LOCKED.csv` | Bản snapshot khóa hash đối chiếu với `reports/panel_lock.md` | Khóa tham chiếu |
| `papi_panel_scale_metadata.csv` | Metadata thang đo & cảnh báo đổi thang/ngừng thu thập từng cột | `python scripts/data/build_scale_metadata.py` |
| `external_master_63_2011_2024.csv` | Bảng tổng hợp 882 × 59 ghép PAPI với PCI, GRDP, dân số, rác thải | `python scripts/data/build_external_master.py` |
| `external_poverty_63.csv` | Chuỗi tỷ lệ hộ nghèo cấp tỉnh (GSO V14.47 + Niên giám) | `python scripts/data/build_poverty_63.py` |
| `external_provenance.md` | Bản ghi nguồn gốc, schema và quy trình ghép dữ liệu ngoại lai | `python scripts/data/build_external_panel.py` |
