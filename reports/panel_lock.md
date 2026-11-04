# Panel v1 — khóa mốc (2026-11-04)

- File: `data/processed/papi_panel_v1_LOCKED.csv` — snapshot của panel chính (882×41), tạo theo Phase 4 bước 4.
- SHA-256: `87404305F36BD2609A63A213C41AC365960DD7909D0D122A0909FA9A5D0D9E27`
- Bytes: 485,066
- Pipeline tái tạo từ raw data: `python scripts/build_panel.py` (idempotent); kiểm tra: `python scripts/check_data.py`.
- Không chỉnh tay file; mọi thay đổi phải qua script + changelog + hash mới.
