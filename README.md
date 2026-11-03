# Đồ án Học máy — Phân cụm 63 tỉnh Việt Nam bằng STING (PAPI 2011–2024)

Đồ án môn Học máy · Chủ đề 6: **Grid-based (clustering)** · Domain: Sociology / History.

## Cấu trúc dự án

| Thư mục | Nội dung |
|---|---|
| `plans/` | Kế hoạch triển khai (không commit theo quy định công cụ) |
| `data/raw/papi/` | 14 workbook PAPI 2011–2024 (nguồn: papi.org.vn, dữ liệu công khai) |
| `data/raw/mendeley/` | Gói replication CC BY 4.0 (panel đối chiếu, crosswalk, centroid) |
| `data/raw/boundaries/` | GeoJSON 63 tỉnh (Open Development Vietnam, CC-BY-SA 4.0) |
| `data/processed/` | Panel sạch (kết quả Phase 2) |
| `src/` | Thư viện STING (tự viết từ đầu) |
| `scripts/` | Script dữ liệu & phân tích |
| `notebooks/` | Notebook nộp bài (Jupyter) |
| `tests/` | Unit test |
| `results/figs/` | Hình kết quả |
| `reports/` | Báo cáo, ghi chú |
| `slides/` | Slide trình bày |

## Nguồn dữ liệu & giấy phép

- **PAPI 2011–2024** — CECODES / VFF-CRT / RTA / UNDP. Tải từ <https://papi.org.vn/du-lieu-papi/>.
- **Gói replication** — Le et al., Mendeley Data, CC BY 4.0. DOI: 10.17632/wbk42j9wc8.1.
- **GeoJSON tỉnh** — Open Development Vietnam (OD Mekong), CC-BY-SA 4.0.

## Chạy nhanh

```powershell
# Kiểm tra môi trường
python -c "import pandas, openpyxl, plotly, sklearn; print('ok')"

# Unit test STING
python -m pytest tests -q

# Kiểm tra dữ liệu (sau khi panel được tạo ở Phase 2)
python scripts/check_data.py
```

Ghi chú: `jupyter` CLI chưa vào PATH — dùng `python -m jupyter` / `python -m nbconvert`.
