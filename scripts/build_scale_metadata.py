"""Sinh sidecar metadata thang đo cho panel PAPI.

Output: data/processed/papi_panel_scale_metadata.csv — một dòng cho từng cột
d*/sd_* của panel, mô tả thang đo theo workbook gốc, cửa sổ khả dụng và cờ
heuristic. Được sinh lại bằng script này (không phải ghi tay) để đáp ứng
nguyên tắc provenance: mọi tệp dữ liệu phải có generator tái lập được.

Nguồn chứng minh của các dòng "workbook" (phiên kiểm toán 2026-11-07, xem
plans/model_stability_audit.md):
- data/raw/papi/*.xlsx — sheet 2020/2021/2024_PAPI_VIE_ENG ghi thang từng chỉ
  tiêu: sd_5_1/5_3/5_4 đổi "0.25-2.5" -> "0.33-3.33" từ 2021; sd_5_2 biến mất
  khỏi sheet 2021+; sd_3_2 là "0.33-3.33" ở CẢ hai sheet (giá trị 2013-2015
  đạt 2.66-2.69 > 2.5); sd_6_4 giữ "0.25-2.5" mọi sheet; d1-d8 ghi "1-10 điểm"
  (sheet 2024, cột C); 8 đặc trưng hồi quy (sd_1_3, sd_1_4, sd_4_1..4_4,
  sd_6_1, sd_6_3) cùng "0.25-2.5 điểm/points" ở cả 3 sheet.
- scripts/check_data.py:scale_audit — heuristic cờ bước nhảy mean liên năm
  > 0.25 (CHỈ là cờ, không tự chứng minh đổi thang).
- data/processed/papi_panel_63_2011_2024.csv — cửa sổ khả dụng thực tế.

Nguyên tắc: CHỈ ĐỌC nguồn, ghi tệp mới; không sửa panel (SHA-256 lock).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"
OUT = ROOT / "data" / "processed" / "papi_panel_scale_metadata.csv"
sys.path.insert(0, str(ROOT / "scripts"))
from check_data import scale_audit  # noqa: E402

# Các cột đã đối chiếu workbook (kiểm toán 2026-11-07): thang trước/sau 2021,
# năm đổi thang, năm ngừng thu thập, nguồn chứng minh.
WORKBOOK: dict[str, tuple[str, str, str, str, str]] = {
    "sd_5_1": ("0.25-2.5 điểm", "0.33-3.33 điểm/points", "2021", "", "workbook sheet 2020 vs 2021+"),
    "sd_5_3": ("0.25-2.5 điểm", "0.33-3.33 điểm/points", "2021", "", "workbook sheet 2020 vs 2021+"),
    "sd_5_4": ("0.25-2.5 điểm", "0.33-3.33 điểm/points", "2021", "", "workbook sheet 2020 vs 2021+"),
    "sd_5_2": ("0.25-2.5 điểm", "(không còn)", "", "2021", "workbook: biến mất khỏi sheet 2021+"),
    "sd_3_2": ("0.33-3.33 điểm", "0.33-3.33 điểm", "", "", "workbook 2020 & 2021 giống nhau — jump là biến động thực (giá trị 2013-2015 lên 2.66-2.69 > 2.5)"),
    "sd_6_4": ("0.25-2.5 điểm", "0.25-2.5 điểm", "", "", "workbook 2020-2023 giống nhau — jump là biến động thực"),
}
for d in range(1, 9):
    WORKBOOK[f"d{d}"] = ("1-10 điểm", "1-10 điểm", "", "", "workbook 2024 sheet cột C; chưa chứng minh tương đương cấu trúc xuyên năm")
for sd in ("sd_1_3", "sd_1_4", "sd_4_1", "sd_4_2", "sd_4_3", "sd_4_4", "sd_6_1", "sd_6_3"):
    WORKBOOK[sd] = ("0.25-2.5 điểm/points", "0.25-2.5 điểm/points", "", "", "workbook sheet 2020/2021/2024 giống nhau")


def main() -> int:
    panel = pd.read_csv(PANEL)
    cols = [c for c in panel.columns if c.startswith(("d", "sd_")) and c[1:2].isdigit() or c.startswith("sd_")]
    cols = sorted(set(c for c in cols if c.startswith("d") and len(c) <= 2) | set(c for c in cols if c.startswith("sd_")))
    flags = {c: (abs(j), y) for c, j, y in scale_audit(panel)}
    rows = []
    for col in cols:
        s = panel[col]
        years = panel.loc[s.notna(), "year"]
        if wb := WORKBOOK.get(col):
            thang_truoc, thang_sau, nam_doi, nam_ngung, nguon = wb
        else:
            thang_truoc = thang_sau = nam_doi = nam_ngung = ""
            jump = flags.get(col)
            nguon = (
                f"chưa đối chiếu workbook; bị flag heuristic (|jump| {jump[0]:.3f} tại {jump[1]})"
                if jump
                else "chưa đối chiếu workbook; không bị flag heuristic (không tự chứng minh tương đương)"
            )
        rows.append(
            {
                "cot": col,
                "thang_2011_2020": thang_truoc,
                "thang_2021_2024": thang_sau,
                "nam_doi_thang": nam_doi,
                "nam_ngung_thu_thap": nam_ngung,
                "nam_bat_dau": int(years.min()) if len(years) else "",
                "nam_ket_thuc": int(years.max()) if len(years) else "",
                "so_tinh_nam_dau": int(panel.loc[panel["year"] == years.min(), col].notna().sum()) if len(years) else 0,
                "so_tinh_nam_cuoi": int(panel.loc[panel["year"] == years.max(), col].notna().sum()) if len(years) else 0,
                "nguon_xac_minh": nguon,
            }
        )
    out = pd.DataFrame(rows)
    OUT.write_text(out.to_csv(index=False), encoding="utf-8-sig", newline="\n")
    print(f"Đã ghi {OUT} ({len(out)} cột)")
    changed = [r["cot"] for r in rows if r["nam_doi_thang"] or r["nam_ngung_thu_thap"]]
    print(f"Cột đổi thang/ngừng thu thập theo workbook: {', '.join(changed)}")
    print(f"Cột bị flag heuristic: {len(flags)}/37")
    return 0


if __name__ == "__main__":
    sys.exit(main())
