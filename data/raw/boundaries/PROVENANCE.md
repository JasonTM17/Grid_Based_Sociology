# PROVENANCE — GeoJSON ranh giới 63 tỉnh

- **Nguồn:** Open Development Vietnam (OD Mekong) — dataset ranh giới hành chính cấp tỉnh.
  Trang dữ liệu: <https://data.opendevelopmentmekong.net/> (tỉnh Việt Nam).
- **Ngày tải:** 2026-11-03. **Giấy phép: CC-BY-SA 4.0** theo trang dữ liệu (file không nhúng
  metadata giấy phép). Dùng lại phải ghi nguồn + giữ cùng giấy phép.
- **File:** `diaphantinh.geojson` — 4,343,853 B, SHA-256 `95475ee5e8abe71485d9564ea11e990c8dae7da34a6fc7cb6a62c2b260ca6be9`;
  63 features; thuộc tính `gid` (1–63), `code`, `ten_tinh`.

## Lưu ý join bản đồ (quan trọng)

- **`code` KHÔNG phải mã tỉnh PAPI** — là hằng số `'AD01'` cho mọi feature ⇒ không dùng để join.
- **`ten_tinh` lệch 6 tỉnh** so với tên chuẩn PAPI:
  `'Bà Rịa -Vũng Tàu'`, `'Cần Thơn'`, `'Kien Giang'`, `'Quản Bình'`, `'Đăk Lăk'`, `'Đăk Nông'`.
- **Cách join chuẩn:** dùng `data/raw/mendeley/Replication_package/data/centroids_63_naturalearth.csv`
  (join theo `province_code`) hoặc chuẩn hóa tên + bảng alias 6 tên trên → mục tiêu 63/63 tỉnh khớp.
