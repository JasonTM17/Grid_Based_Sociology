# Panel v1 — khóa mốc (2026-11-04)

- File: `data/processed/papi_panel_v1_LOCKED.csv` — snapshot của panel chính (882×41), tạo theo Phase 4 bước 4.
- SHA-256: `35d3476b5ca3c2bb1a6d244933e40b4fa22b176759de6c5a4e28d4329d11f7c2` (bản Git và bản nộp, LF).
- Kích thước bản LF: 484.183 byte. Bản xuất Windows ban đầu có 485.066 byte với
  xuống dòng CRLF và SHA-256 `87404305f36bd2609a63a213c41ac365960dd7909d0d122a0909fa9a5d0d9e27`.
  Hai dạng xuống dòng giữ nguyên nội dung bảng.
- Pipeline tái tạo từ raw data: `python scripts/data/build_panel.py` (idempotent); kiểm tra: `python scripts/data/check_data.py`.
- Không chỉnh tay file; mọi thay đổi phải qua script + changelog + hash mới.
