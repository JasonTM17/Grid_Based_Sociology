"""Probe 2: liệt kê mã tiểu-chiều (sub-dim) có mặt ở từng năm (cả 2 định dạng).

Chạy: python scripts/_layout_probe2.py
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
    2011: "PAPI-2011-data-1.xlsx", 2012: "PAPI-2012-data-1.xlsx", 2013: "PAPI-2013-data-1.xlsx",
    2014: "PAPI-2014-data-1.xlsx", 2015: "PAPI-2015-data-1.xlsx", 2016: "PAPI-2016-data-1.xlsx",
    2017: "PAPI-2017-data-1.xlsx", 2018: "PAPI-2018-data.xlsx", 2019: "PAPI2019-data.xlsx",
}
NEW_FILES = {
    2020: "2020PAPI_ProvincialIndicators_BangChiTieuCapTinh-1.xlsx",
    2021: "1.2021PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
    2022: "2022PAPI_ProvincialIndicators_BangChiTieuCapTinh-2.xlsx",
    2023: "2023PAPI_ProvincialIndicators_BangChiTieuCapTinh..xlsx",
    2024: "2024PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
}

SUB_RE = re.compile(r"^\s*([1-8])\.(\d+)\s*:")

def collect_old(year, fname):
    wb = openpyxl.load_workbook(BASE / fname, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    subs = set()
    for h in header:
        if h is None:
            continue
        m = SUB_RE.match(str(h))
        if m:
            subs.add(f"{m.group(1)}.{m.group(2)}")
    wb.close()
    return subs

def collect_new(year, fname):
    wb = openpyxl.load_workbook(BASE / fname, read_only=True, data_only=True)
    target = None
    for name in wb.sheetnames:
        if str(year) in name and "VIE_ENG" in name and name.strip().startswith(str(year)):
            target = name
            break
    ws = wb[target]
    subs = set()
    for row in ws.iter_rows(min_row=4, values_only=True):
        c0 = str(row[0]) if row and row[0] is not None else ""
        c1 = str(row[1]) if len(row) > 1 and row[1] is not None else ""
        for cell in (c0, c1):
            m = SUB_RE.match(cell)
            if m and not c0.startswith("Dimension"):
                subs.add(f"{m.group(1)}.{m.group(2)}")
    wb.close()
    return subs

all_sets = {}
for y, f in OLD_FILES.items():
    all_sets[y] = collect_old(y, f)
for y, f in NEW_FILES.items():
    all_sets[y] = collect_new(y, f)

for y in sorted(all_sets):
    s = sorted(all_sets[y], key=lambda x: (int(x.split(".")[0]), int(x.split(".")[1])))
    print(f"{y}: ({len(s)}) {s}")

common = None
for y, s in all_sets.items():
    common = s if common is None else (common & s)
print()
print("Common across ALL years:", sorted(common, key=lambda x: (int(x.split(".")[0]), int(x.split(".")[1]))))

from collections import Counter
cnt = Counter()
for s in all_sets.values():
    cnt.update(s)
print()
print("Present in >= 12 of 14 years:", sorted([k for k, v in cnt.items() if v >= 12], key=lambda x: (int(x.split(".")[0]), int(x.split(".")[1]))))
print("Present in all 14:", len([k for k, v in cnt.items() if v == 14]))
