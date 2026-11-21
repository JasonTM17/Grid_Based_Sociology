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
**nguồn bên thứ ba độc lập để chứng minh panel PAPI mà nhóm tự dựng từ 14 Excel
gốc là đúng**:

1. **Đối chiếu chéo số liệu**: panel PAPI 2011–2022 của nhóm (`data/processed/papi_panel_63_2011_2024.csv`)
   so với `Replication_package/data/papi_panel_63_2011_2022.csv` của nhóm tác giả.
   Lệnh: `python scripts/data/crosscheck_mendeley.py` → kết quả **max |diff| = 0.0
   trên 3.522 so sánh** (8 chiều × 63 tỉnh × 12 năm), lưu ở `reports/crosscheck_mendeley.md`.
2. **Chuẩn hóa tên/mã 63 tỉnh**: `province_crosswalk_63.csv` (mã tỉnh ↔ tên Việt/ASCII)
   dùng khi ghép bảng trong `scripts/data/build_panel.py`.
3. **Tọa độ vẽ bản đồ**: `centroids_63_naturalearth.csv` (tâm lat/long từng tỉnh,
   dữ liệu Natural Earth) để vẽ bản đồ kết quả phân cụm.
4. **Kiểm tra hash file gốc**: `SHA256_PAPI_ORIGINALS.txt` là ledger hash của 14
   workbook PAPI gốc theo tên file của tác giả — nhóm đối chiếu để chứng minh
   file trong `data/raw/papi/` khớp bản gốc (2020, 2021, 2023 khớp; xem
   `data/raw/papi/PROVENANCE.md` phần "Chain-of-custody").

## 3. File nào được commit vào repo?

Chỉ **4 file nhỏ dùng trực tiếp** (xem block "Mendeley" trong `.gitignore` —
phần còn lại của gói deliberate giữ NGOÀI repo, tải lại theo DOI khi cần):

| File | Dùng cho |
|---|---|
| `PROVENANCE.md` | Nguồn gốc, giấy phép, hash |
| `Replication_package/data/province_crosswalk_63.csv` | Bảng tra mã/tên 63 tỉnh |
| `Replication_package/data/centroids_63_naturalearth.csv` | Tọa độ tâm tỉnh để vẽ bản đồ |
| `Replication_package/data/papi_panel_63_2011_2022.csv` | Panel PAPI 2011–2022 để đối chiếu chéo |
| `Replication_package/data/SHA256_PAPI_ORIGINALS.txt` | Ledger hash 14 workbook gốc |

Lưu ý: các file CSV khi commit bị chuẩn line-ending LF nên hash bản git khác hash
file gốc trong zip — cả hai hash đều được ghi trong `PROVENANCE.md`.

## 4. Mục lục đầy đủ `Replication_package/data/` (đọc trực tiếp, không cần giải nén lại)

| File | Dung lượng / dòng | Nội dung (đọc từ header) | Dùng cho | Commit? |
|---|---|---|---|---|
| `province_crosswalk_63.csv` | 2,3 KB / 64 dòng | `province_code, province_vi, province_ascii, period` | Chuẩn hóa mã + tên 63 tỉnh | ✅ |
| `centroids_63_naturalearth.csv` | 14 KB / 64 dòng | tâm (latitude, longitude) + iso_3166_2 của 63 tỉnh, nguồn Natural Earth | Vẽ bản đồ | ✅ |
| `papi_panel_63_2011_2022.csv` | 136 KB / 757 dòng (63 tỉnh × 12 năm) | panel PAPI 8 chiều `papi_d1…d8` thang 1–10 | **Đối chiếu chéo panel của nhóm** | ✅ |
| `SHA256_PAPI_ORIGINALS.txt` | 1,6 KB | hash SHA-256 của 14 workbook PAPI gốc theo tên file gốc (vd `161b43ee-PAPI2018_...xlsx`) | Kiểm tra file `data/raw/papi/` có khớp bản gốc | ✅ |
| `contiguity_63_naturalearth.csv` | 1 KB / 136 dòng | danh sách cặp tỉnh kề nhau `id_a,id_b` | Ma trận kề (nếu dùng spatial) | ❌ local |
| `papi_indicators_63_2018_2022.csv` | 78 KB / 316 dòng | các chỉ tiêu CON chi tiết 2018–2022 (vd `papi_d6_3_basic_infrastructure`) | Tham khảo chỉ tiêu con | ❌ local |
| `papi_indicators_63_2018_2024.csv` | 132 KB / 442 dòng | chỉ tiêu con chi tiết 2018–2024 | Tham khảo chỉ tiêu con | ❌ local |
| `papi_indicator_ledger_2018_2022.csv` | 1,8 MB / 3.989 dòng | ledger từng ô: `provenance_id, sheet_cell, row_label, file_sha256, audit_status` | Truy vết từng giá trị về ô Excel gốc | ❌ local |
| `papi_indicator_ledger_2018_2024.csv` | 3,0 MB / 6.868 dòng | như trên nhưng tới 2024 | Truy vết từng giá trị | ❌ local |
| `papi_source_ledger.csv` | 3,0 MB / 5.119 dòng | ledger nguồn đầy đủ: đơn vị gốc, trang tài liệu, ngày công bố/ngày tải | Truy vết nguồn | ❌ local |
| `papi_qa.txt` | — | báo cáo QA: `records: 5118, problems: none`, liệt kê các ô trống **không nội suy** | Tài liệu kiểm chứng (không phải dữ liệu) | ❌ local |
| `papi_indicators_qa_2018_2024.txt` | — | QA vị trí dòng từng biến theo năm trong workbook | Tài liệu kiểm chứng | ❌ local |
| `pci_panel_63x11_SOURCE_EXTRACTED.csv` | 206 KB / 694 dòng | panel PCI 2012–2022 trích từ file gốc VCCI kèm `source_url`, `source_row_locator` | Dự phòng kiểm chứng PCI | ❌ local |
| `gso_population_urban_63x8_SOURCE_EXTRACTED.csv` | 93 KB / 505 dòng | dân số thành thị 63 tỉnh 8 năm từ Niên giám GSO | Dự phòng dữ liệu GSO | ❌ local |
| `gso_waste_wide_from_upload.csv` | 30 KB / 306 dòng | rác thải bình quân đầu người theo tỉnh/năm | Dự phòng dữ liệu GSO | ❌ local |

## 5. Câu hay hỏi

- **"Sao trong repo có cả file Mendeley lẫn file PAPI gốc?"** — Vì hai nguồn độc lập:
  `papi/` là nguồn chính để dựng panel; `mendeley/` là nguồn kiểm chứng chéo chứng
  minh panel dựng ra khớp với một nghiên cứu đã công bố (max |diff| = 0.0).
- **"File nào trong này là dữ liệu, file nào là báo cáo?"** — `.csv` (trừ ledger/qa)
  là dữ liệu; `*_qa.txt`, `SHA256_*.txt` là tài liệu kiểm chứng/hash.
- **"Muốn xem đầy đủ gói replication thì làm sao?"** — Tải lại theo DOI
  10.17632/wbk42j9wc8.1 trên Mendeley Data (CC BY 4.0, ghi nguồn khi dùng).
