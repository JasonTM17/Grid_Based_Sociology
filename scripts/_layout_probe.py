"""Khảo sát layout 14 file PAPI (dùng một lần để viết parser chính xác).

Chạy: python scripts/_layout_probe.py
"""
import re
import sys
from pathlib import Path

import openpyxl

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent.parent / "data" / "raw" / "papi"

OLD_FILES = {
    2011: "PAPI-2011-data-1.xlsx",
    2012: "PAPI-2012-data-1.xlsx",
    2013: "PAPI-2013-data-1.xlsx",
    2014: "PAPI-2014-data-1.xlsx",
    2015: "PAPI-2015-data-1.xlsx",
    2016: "PAPI-2016-data-1.xlsx",
    2017: "PAPI-2017-data-1.xlsx",
    2018: "PAPI-2018-data.xlsx",
    2019: "PAPI2019-data.xlsx",
}
NEW_FILES = {
    2020: "2020PAPI_ProvincialIndicators_BangChiTieuCapTinh-1.xlsx",
    2021: "1.2021PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
    2022: "2022PAPI_ProvincialIndicators_BangChiTieuCapTinh-2.xlsx",
    2023: "2023PAPI_ProvincialIndicators_BangChiTieuCapTinh..xlsx",
    2024: "2024PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
}

DIM_RE = re.compile(r"^\s*([1-8])\s*:")

print("#" * 78)
print("# OLD FORMAT (2011-2019): provinces as rows")
print("#" * 78)
prov_names_2011 = []
for year, fname in OLD_FILES.items():
    wb = openpyxl.load_workbook(BASE / fname, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    dims = []
    for j, h in enumerate(header):
        if h is None:
            continue
        m = DIM_RE.match(str(h))
        if m and "." not in str(h)[:6]:
            dims.append((j, int(m.group(1)), str(h).strip()[:50]))
    names = [str(r[0]).strip() for r in rows[1:] if r and r[0]]
    print(f"{year}: sheet='{ws.title}' | {len(rows)} rows x {len(header)} cols | dims={[(d, n) for _, d, n in dims][:10]}")
    print(f"   provinces count={len(names)} | first={names[:3]} | last={names[-3:]}")
    if year == 2011:
        prov_names_2011 = names
    wb.close()

print()
print("Full province list (2011 file):")
for n in prov_names_2011:
    print("  ", n)

print()
print("#" * 78)
print("# NEW FORMAT (2020-2024): provinces as columns, transposed")
print("#" * 78)
for year, fname in NEW_FILES.items():
    wb = openpyxl.load_workbook(BASE / fname, read_only=True, data_only=True)
    # find the main VIE_ENG sheet for this year
    target = None
    for name in wb.sheetnames:
        if str(year) in name and ("VIE_ENG" in name):
            if name.strip().lower().startswith(str(year)):
                target = name
                break
    if target is None:
        target = wb.sheetnames[0]
    ws = wb[target]
    rows = list(ws.iter_rows(min_row=1, max_row=3, values_only=True))
    r1, r2 = rows[0], rows[1]
    codes = [v for v in r1[3:] if v is not None]
    names = [v for v in r2[3:] if v is not None]
    # count rows with 'Dimension' label and total rows
    dim_rows = []
    total = 0
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        total = i
        c0 = str(row[0]) if row and row[0] is not None else ""
        if c0.startswith("Dimension"):
            dim_rows.append((i, c0.strip()[:55]))
    print(f"{year}: sheet='{target}' | {total} rows x {ws.max_column} cols")
    print(f"   codes={len(codes)} sample={codes[:6]} | names={len(names)} sample={names[:4]}")
    print(f"   dimension rows={[(i, c[:45]) for i, c in dim_rows]}")
    wb.close()
