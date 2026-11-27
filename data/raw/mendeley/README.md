# `data/raw/mendeley/` — Gói replication Mendeley dùng để ĐỐI CHIẾU CHÉO

## 1. Đây là gì?

- **Gói dữ liệu + code tái lập của một nghiên cứu độc lập**: Le et al.,
  *"Replication data and code for Digital Governance..."*, đăng trên **Mendeley Data**,
  **DOI: 10.17632/wbk42j9wc8.1**, giấy phép **CC BY 4.0**, tải ngày 2026-11-03.
- File gốc tải về: `mendeley_replication.zip` (~711 KB, sha256 `02d4fce6…33b04d`)
  chứa README + `Replication_package.rar`. Giải nén ra thư mục `Replication_package/`.
- Nguồn gốc đầy đủ và giấy phép: xem `PROVENANCE.md` trong thư mục này.

## 2. Nhóm dùng Mendeley để làm gì? (trả lời ngắn gọn)

**Không phải là nguồn dữ liệu chính** (PAPI chính nằm ở `data/raw/papi/`), mà là
**gói của nhóm nghiên cứu khác để đối chiếu panel PAPI mà nhóm tự dựng từ 14 Excel
gốc**. Hai panel cùng dựa trên PAPI; khớp số liệu không thay thế việc kiểm tra
thang đo, nội dung chỉ tiêu hay chất lượng khảo sát:

1. **Đối chiếu chéo số liệu**: panel PAPI 2011–2022 của nhóm (`data/processed/papi_panel_63_2011_2024.csv`)
   so với `Replication_package/data/papi_panel_63_2011_2022.csv` của nhóm tác giả.
   Lệnh: `python scripts/data/crosscheck_mendeley.py` → kết quả **max |diff| = 0.0
   trên 5.118 cặp giá trị có dữ liệu ở cả hai panel** thuộc 756 hàng tỉnh–năm
   (2011–2022), lưu ở `reports/crosscheck_mendeley.md`. Đây là tổng số cặp
   hợp lệ trên d1–d8, không phải tích 8 × 63 × 12: d7/d8 chỉ có từ 2018 và
   một số tỉnh–năm thiếu giá trị.
2. **Chuẩn hóa tên/mã 63 tỉnh**: `province_crosswalk_63.csv` (mã tỉnh ↔ tên Việt/ASCII)
   dùng khi ghép bảng trong `scripts/data/build_panel.py`.
3. **Tọa độ vẽ bản đồ**: `centroids_63_naturalearth.csv` (tâm lat/long từng tỉnh,
   dữ liệu Natural Earth) để vẽ bản đồ kết quả phân cụm.
4. **Kiểm tra hash file gốc**: `SHA256_PAPI_ORIGINALS.txt` là ledger hash của 14
   workbook PAPI gốc theo tên file của tác giả — nhóm đối chiếu để chứng minh
   file trong `data/raw/papi/` khớp bản gốc (2020, 2021, 2023 khớp; xem
   `data/raw/papi/PROVENANCE.md` phần "Chain-of-custody").

## 3. File nào được commit vào repo?

Repo lưu **gói nén gốc và bốn tệp đã giải nén dùng trực tiếp**, kèm tài liệu
nguồn gốc. Phần còn lại được giữ trong gói nén; không tạo thêm bản giải nén
trong cây Git (xem block "Mendeley" trong `.gitignore`).

| File | Dùng cho |
|---|---|
| `PROVENANCE.md` | Nguồn gốc, giấy phép, hash |
| `mendeley_replication.zip` | Gói tải gốc chứa README và `Replication_package.rar` |
| `Replication_package/data/province_crosswalk_63.csv` | Bảng tra mã/tên 63 tỉnh |
| `Replication_package/data/centroids_63_naturalearth.csv` | Tọa độ tâm tỉnh để vẽ bản đồ |
| `Replication_package/data/papi_panel_63_2011_2022.csv` | Panel PAPI 2011–2022 để đối chiếu chéo |
| `Replication_package/data/SHA256_PAPI_ORIGINALS.txt` | Ledger hash 14 workbook gốc |

Lưu ý: các file CSV khi commit bị chuẩn line-ending LF nên hash bản git khác hash
file gốc trong zip — cả hai hash đều được ghi trong `PROVENANCE.md`.

## 4. Mục lục tham khảo của `Replication_package/data/` trong gói gốc

Bốn tệp có dấu ✅ mở trực tiếp từ repo. Để xem các tệp còn lại, giải nén ZIP,
sau đó giải nén `Replication_package.rar` bằng công cụ hỗ trợ RAR. Bảng dưới
ghi dung lượng của bản gốc, trước khi chuẩn hóa xuống dòng LF trong Git.

| File | Dung lượng / dòng | Nội dung (đọc từ header) | Dùng cho | Bản giải nén trong repo? |
|---|---|---|---|---|
| `province_crosswalk_63.csv` | 2,3 KB / 64 dòng | `province_code, province_vi, province_ascii, period` | Chuẩn hóa mã + tên 63 tỉnh | ✅ |
| `centroids_63_naturalearth.csv` | 14 KB / 64 dòng | tâm (latitude, longitude) + iso_3166_2 của 63 tỉnh, nguồn Natural Earth | Vẽ bản đồ | ✅ |
| `papi_panel_63_2011_2022.csv` | 136 KB / 757 dòng (63 tỉnh × 12 năm) | panel PAPI 8 chiều `papi_d1…d8` thang 1–10 | **Đối chiếu chéo panel của nhóm** | ✅ |
| `SHA256_PAPI_ORIGINALS.txt` | 1,6 KB | hash SHA-256 của 14 workbook PAPI gốc theo tên file gốc (vd `161b43ee-PAPI2018_...xlsx`) | Kiểm tra file `data/raw/papi/` có khớp bản gốc | ✅ |
| `contiguity_63_naturalearth.csv` | 1 KB / 136 dòng | danh sách cặp tỉnh kề nhau `id_a,id_b` | Ma trận kề (nếu dùng spatial) | Trong gói nén |
| `papi_indicators_63_2018_2022.csv` | 78 KB / 316 dòng | các chỉ tiêu CON chi tiết 2018–2022 (vd `papi_d6_3_basic_infrastructure`) | Tham khảo chỉ tiêu con | Trong gói nén |
| `papi_indicators_63_2018_2024.csv` | 132 KB / 442 dòng | chỉ tiêu con chi tiết 2018–2024 | Tham khảo chỉ tiêu con | Trong gói nén |
| `papi_indicator_ledger_2018_2022.csv` | 1,8 MB / 3.989 dòng | ledger từng ô: `provenance_id, sheet_cell, row_label, file_sha256, audit_status` | Truy vết từng giá trị về ô Excel gốc | Trong gói nén |
| `papi_indicator_ledger_2018_2024.csv` | 3,0 MB / 6.868 dòng | như trên nhưng tới 2024 | Truy vết từng giá trị | Trong gói nén |
| `papi_source_ledger.csv` | 3,0 MB / 5.119 dòng | ledger nguồn đầy đủ: đơn vị gốc, trang tài liệu, ngày công bố/ngày tải | Truy vết nguồn | Trong gói nén |
| `papi_qa.txt` | — | báo cáo QA: `records: 5118, problems: none`, liệt kê các ô trống **không nội suy** | Tài liệu kiểm chứng (không phải dữ liệu) | Trong gói nén |
| `papi_indicators_qa_2018_2024.txt` | — | QA vị trí dòng từng biến theo năm trong workbook | Tài liệu kiểm chứng | Trong gói nén |
| `pci_panel_63x11_SOURCE_EXTRACTED.csv` | 206 KB / 694 dòng | panel PCI 2012–2022 trích từ file gốc VCCI kèm `source_url`, `source_row_locator` | Dự phòng kiểm chứng PCI | Trong gói nén |
| `gso_population_urban_63x8_SOURCE_EXTRACTED.csv` | 93 KB / 505 dòng | dân số thành thị 63 tỉnh 8 năm từ Niên giám GSO | Dự phòng dữ liệu GSO | Trong gói nén |
| `gso_waste_wide_from_upload.csv` | 30 KB / 306 dòng | rác thải bình quân đầu người theo tỉnh/năm | Dự phòng dữ liệu GSO | Trong gói nén |

## 5. Câu hay hỏi

- **"Sao trong repo có cả file Mendeley lẫn file PAPI gốc?"** — `papi/` là nguồn
  chính để dựng panel; `mendeley/` cung cấp panel của nhóm nghiên cứu khác để
  kiểm tra các giá trị chung (max |diff| = 0.0 trên 5.118 cặp giá trị).
- **"File nào trong này là dữ liệu, file nào là báo cáo?"** — `.csv` (trừ ledger/qa)
  là dữ liệu; `*_qa.txt`, `SHA256_*.txt` là tài liệu kiểm chứng/hash.
- **"Muốn xem đầy đủ gói replication thì làm sao?"** — Giải nén
  `mendeley_replication.zip`, rồi giải nén `Replication_package.rar` bên trong.
  Có thể đối chiếu hoặc tải lại theo DOI 10.17632/wbk42j9wc8.1 trên Mendeley Data
  (CC BY 4.0, ghi nguồn khi dùng).
