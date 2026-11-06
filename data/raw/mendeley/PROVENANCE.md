# PROVENANCE — Mendeley replication package (đối chiếu chéo)

- **Nguồn:** Le et al., *"Replication data and code for Digital Governance..."*, Mendeley Data.
  **DOI: 10.17632/wbk42j9wc8.1**
- **Ngày tải:** 2026-11-03. **Giấy phép: CC BY 4.0** theo trang dữ liệu Mendeley (gói tải về
  không kèm file LICENSE riêng) — dùng lại phải ghi nguồn + DOI.
- **Gói gốc:** `mendeley_replication.zip` (711,397 B, sha256 `02d4fce6…33b04d`) chứa README + `Replication_package.rar`.

## File được COMMIT vào repo (4 file nhỏ dùng trực tiếp)

| File | Bytes | SHA-256 | Dùng cho |
|---|---|---|---|
| `Replication_package/data/province_crosswalk_63.csv` | 2,296 | `9b9a851bc6c20d91…65eaa7c` | Chuẩn hóa mã + tên tỉnh (panel) |
| `Replication_package/data/centroids_63_naturalearth.csv` | 14,358 | `37de31a904d3924a…78692db` | Bản đồ (join theo `province_code`) |
| `Replication_package/data/papi_panel_63_2011_2022.csv` | 135,580 | `09100e3280c758ad…fbaad2b4` | Đối chiếu chéo (max \|diff\| = 0, `reports/crosscheck_mendeley.md`) |
| `Replication_package/data/SHA256_PAPI_ORIGINALS.txt` | 1,609 | `2a5af90b2b511e3d…9ea6a51c1` | Ledger hash 14 workbook gốc |

Phần còn lại của gói (ledger 3 MB, code, results, …) **giữ ngoài repo** — tải lại theo DOI khi cần.
Cơ chế: `.gitignore` chỉ mở 4 file trên (xem block "Mendeley" trong `.gitignore`).

## Đối chiếu chéo đã chạy

- `python scripts/crosscheck_mendeley.py` → max |diff| = 0.0 trên 3.522 so sánh (8 chiều × tỉnh × năm),
  ghi tại `reports/crosscheck_mendeley.md`.
