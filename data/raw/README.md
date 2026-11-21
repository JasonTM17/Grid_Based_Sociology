# `data/raw/` — Dữ liệu gốc (bất biến, không chỉnh tay)

Thư mục này lưu **nguồn dữ liệu thô** của toàn bộ đồ án. Quy tắc bất biến:

- **Không bao giờ sửa tay** bất kỳ file nào ở đây. Mọi xử lý (làm sạch, ghép bảng,
  chuẩn hóa) đều thực hiện bằng script trong `scripts/` và kết quả chỉ được ghi
  sang `data/processed/`.
- Mỗi thư mục con đều có **`PROVENANCE.md`** ghi rõ: nguồn gốc (URL), ngày tải,
  giấy phép sử dụng, và **SHA-256 của từng file** để kiểm chứng file không bị
  thay đổi. Nếu cần kiểm tra: `sha256sum -c` bên trong từng thư mục hoặc đối chiếu
  với bảng trong `PROVENANCE.md`.
- `data/raw/**` được đánh dấu `-text` trong `.gitattributes` (giữ nguyên byte,
  không chuẩn hóa line-ending) để hash trong PROVENANCE luôn khớp với bản trên git.

## File nào là dữ liệu, file nào là tài liệu?

| Loại | Đuôi file | Ví dụ | Vai trò |
|---|---|---|---|
| **Dữ liệu thật** | `.xlsx`, `.xls`, `.csv`, `.json`, `.geojson`, `.html`, `.pdf` | `PAPI-2011-data-1.xlsx`, `diaphantinh.geojson`, `pxweb_*.html` | Đầu vào cho các script dựng panel / kiểm chứng |
| **Tài liệu kiểm chứng / metadata** | `PROVENANCE.md`, `SHA256SUMS.txt`, `SHA256_*.txt`, `*_qa.txt` | `papi/PROVENANCE.md`, `mendeley/.../papi_qa.txt` | Ghi nguồn gốc, hash, báo cáo QA — **không phải dữ liệu**, chỉ dùng để đối chiếu |

## Bản đồ thư mục nguồn (ai dùng làm gì trong đồ án)

| Thư mục | Nguồn | Dùng làm gì trong đồ án |
|---|---|---|
| `papi/` | PAPI 2011–2024 (CECODES/VFF-CRT/RTA/UNDP, papi.org.vn) — 14 workbook Excel + báo cáo PAPI 2024 PDF | **Nguồn dữ liệu CHÍNH** của đồ án → `scripts/data/build_panel.py` dựng panel 882×41 |
| `mendeley/` | Gói replication Le et al., Mendeley Data, DOI 10.17632/wbk42j9wc8.1 (CC BY 4.0) | **Nguồn độc lập để đối chiếu chéo** panel PAPI của nhóm (xem chi tiết `mendeley/README.md`) + bảng tra mã tỉnh + tọa độ vẽ bản đồ |
| `boundaries/` | Ranh giới hành chính 63 tỉnh (diaphantinh.geojson, OD Mekong) | Vẽ bản đồ kết quả phân cụm theo tỉnh |
| `pci/` | Chỉ số PCI của VCCI–USAID (2011–2025) | Kiểm chứng NGOÀI: cụm STING có khác biệt PCI không (ANOVA/Kruskal–Wallis) |
| `gso/` | Niên giám Thống kê + các bảng PX-Web GSO (dân số, GRDP, nghèo V14.47, y tế) | Nguồn chính thức để kiểm chứng ngoài (GRDP, nghèo, mật độ y tế) |
| `molisa/` | Quyết định chuẩn nghèo đa chiều 2017–2019 (QĐ862/QĐ835/QĐ1052) | Bù dữ liệu nghèo 2017–2019 mà PX-Web không công bố |
| `odmekong/` | Dữ liệu nghèo theo vùng 1998–2016 + cơ sở y tế 2020 (OD Mekong) | Kiểm chứng thêm (mật độ y tế, nghèo vùng) |
| `worldbank/` | WDI + kho nghèo cấp tỉnh (poverty data portal, incl. `provincial_poverty_probe/`) | Kiểm chứng nghèo cấp tỉnh độc lập với GSO |
| `undp/` | MPI cấp tỉnh (UNDP/HDI) | Nguồn nghèo đa chiều thứ ba |
| `course/` | Bài giảng của giảng viên (PDF) — **chỉ lưu local, KHÔNG commit** (bị `.gitignore`) | Tài liệu học, không phải dữ liệu đồ án |

## Đọc tiếp

- Tổng quan hai tầng raw/processed: `data/README.md`
- Chi tiết gói đối chiếu Mendeley (file nào làm gì): `data/raw/mendeley/README.md`
- Bằng chứng đối chiếu đã chạy: `reports/crosscheck_mendeley.md` (lệnh: `python scripts/data/crosscheck_mendeley.py`)
