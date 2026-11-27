# PROVENANCE — Mendeley replication package (đối chiếu chéo)

- **Nguồn:** Le et al., *"Replication data and code for Digital Governance..."*, Mendeley Data.
  **DOI: 10.17632/wbk42j9wc8.1**
- **Ngày tải:** 2026-11-03. **Giấy phép: CC BY 4.0** theo trang dữ liệu Mendeley (gói tải về
  không kèm file LICENSE riêng) — dùng lại phải ghi nguồn + DOI.
- **Gói gốc:** `mendeley_replication.zip` (711,397 B), SHA-256
  `02d4fce652a62e8ec86d777c64a8f1fde4c386644f2983fc309a9b27e733b04d`.
  Repo lưu nguyên gói này. ZIP có hai mục dưới thư mục
  `Replication data and code for Digital Governance C/`: `README.md` và
  `Replication_package.rar`.

## Bốn tệp đã giải nén dùng trực tiếp

Ngoài gói ZIP gốc và tài liệu nguồn gốc, repo lưu bốn tệp sau để chạy pipeline
không cần công cụ giải nén RAR. Cột dung lượng ghi số byte của tệp gốc;
SHA-256 ghi riêng bản gốc và bản Git chuẩn hóa xuống dòng LF.

| File | Bytes gốc | SHA-256 | Dùng cho |
|---|---|---|---|
| `Replication_package/data/province_crosswalk_63.csv` | 2,296 | gốc `9b9a851bc6c20d916fa8ca0480025fc091160b3ed78e353fd415f8d0965eaa7c`; bản git (LF) `e463049c2ae843cc878b83def3f02b5781523bdae4f4122891fc672826518e8e` | Chuẩn hóa mã + tên tỉnh (panel) |
| `Replication_package/data/centroids_63_naturalearth.csv` | 14,358 | gốc `37de31a904d3924a00b3f492aa39b20ef55c24d56b59c0c6d043e6d1778692db`; bản git (LF) `4232bb3608f89a4f53a2dbf3e1ae896e24417aa3a1ac443d181bd4c699087d31` | Bản đồ (join theo `province_code`) |
| `Replication_package/data/papi_panel_63_2011_2022.csv` | 135,580 | gốc `09100e3280c758ad23f26fc41be05dcb39560c544963e2189d487e7dfbaad2b4`; bản git (LF) `5a90512526b6be1263f4f83e65af0da55fa7f9b6ff9ce6f89274a3f4ee89cea0` | Đối chiếu chéo (max \|diff\| = 0, `reports/crosscheck_mendeley.md`) |
| `Replication_package/data/SHA256_PAPI_ORIGINALS.txt` | 1,609 | `2a5af90b2b511e3d244ef4f34461dc37d888623fb2a2119a88790599ea6a51c1` | Ledger hash 14 workbook gốc |

Phần còn lại (ledger, code, results, …) nằm trong `Replication_package.rar` của
gói ZIP đã lưu, không có bản giải nén riêng trong cây Git. `.gitignore` cho phép
gói ZIP, tài liệu nguồn gốc và bốn tệp trên; có thể tải lại gói từ DOI để đối chiếu.

## Đối chiếu chéo đã chạy

- `python scripts/data/crosscheck_mendeley.py` → max |diff| = 0.0 trên **5.118 cặp
  giá trị hợp lệ**, thuộc 756 hàng có cùng khóa tỉnh–năm (2011–2022), ghi tại
  `reports/crosscheck_mendeley.md`. Số cặp lần lượt ở d1–d8 là
  750, 747, 750, 747, 750, 751, 312 và 311; chỉ đếm khi hai nguồn cùng có dữ liệu.
- Hai panel cùng dựa trên khảo sát PAPI. Kết quả xác nhận số liệu chung khớp nhau,
  không xác lập tính tương đương thang đo hay chất lượng khảo sát xuyên năm.

Ghi chú: 3 file CSV được git lưu với line-ending LF nên hash bản clone khác hash file tải về; cả hai đều được ghi ở trên (`gốc` = bản tải về từ gói replication).

