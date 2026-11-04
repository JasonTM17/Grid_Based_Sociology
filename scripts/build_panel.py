"""Xây panel PAPI: 63 tỉnh × 2011–2024 từ 14 workbook gốc.

Hai định dạng nguồn:
- 2011–2019 ("PAPI-YYYY-data"): sheet đầu, TỈNH LÀ HÀNG (63 tỉnh + header).
- 2020–2024 ("BangChiTieuCapTinh"): sheet "<YYYY>_VIE_ENG", MA TRẬN CHUYỂN VỊ
  (chỉ tiêu là hàng, tỉnh là cột theo Mã tỉnh; file chứa nhiều sheet năm —
  chỉ lấy sheet năm hiện tại, lấy block "Dimension" ĐẦU TIÊN).

Chạy: python scripts/build_panel.py
Ghi ra: data/processed/papi_panel_63_2011_2024.csv
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "papi"
CROSSWALK = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
OUT = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"

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

# "1: Participation..." (chiều) — không khớp "1.1: ..." vì cần ':' ngay sau số
DIM_RE = re.compile(r"^\s*([1-8])\s*:\s")
SUB_RE = re.compile(r"^\s*([1-8])\.(\d+)\s*:")
DIM_ROW_RE = re.compile(r"^Dimension\s*([1-8])\s*:")

# Viết tắt / biến thể tên tỉnh giữa các năm (khóa & giá trị đều đã chuẩn hóa)
NAME_ALIASES = {
    "tthue": "thuathienhue",  # 2019 viết tắt TT-Hue
}


def norm_name(s) -> str:
    """Chuẩn hóa tên tỉnh: bỏ khoảng trắng/gạch nối, viết thường."""
    return re.sub(r"[\s\-]+", "", str(s).strip().lower())


def to_float(v) -> float:
    if v is None:
        return np.nan
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_crosswalk():
    cw = pd.read_csv(CROSSWALK)
    ascii2code = {}
    code2info = {}
    for code, vi, asc in zip(cw["province_code"], cw["province_vi"], cw["province_ascii"]):
        code = int(code)
        code2info[code] = {"province_vi": str(vi).strip(), "province_ascii": str(asc).strip()}
        ascii2code[norm_name(asc)] = code
    return ascii2code, code2info


def lookup_code(name: str, ascii2code: dict):
    """Tra mã tỉnh theo tên đã chuẩn hóa, có xử lý viết tắt."""
    n = norm_name(name)
    n = NAME_ALIASES.get(n, n)
    return ascii2code.get(n, np.nan)


def parse_old(year: int, fname: str, rows: list):
    wb = openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    header = next(it)
    dim_cols, sub_cols = {}, {}
    for j, h in enumerate(header):
        if h is None:
            continue
        hs = str(h)
        m2 = SUB_RE.match(hs)
        if m2:
            sub_cols[f"sd_{m2.group(1)}_{m2.group(2)}"] = j
            continue
        m = DIM_RE.match(hs)
        if m:
            dim_cols[int(m.group(1))] = j
    n_prov = 0
    for r in it:
        if not r or r[0] is None or not str(r[0]).strip():
            continue
        n_prov += 1
        rec = {"province_ascii": str(r[0]).strip(), "year": year}
        for d, j in dim_cols.items():
            rec[f"d{d}"] = to_float(r[j]) if j < len(r) else np.nan
        for key, j in sub_cols.items():
            rec[key] = to_float(r[j]) if j < len(r) else np.nan
        rows.append(rec)
    wb.close()
    return {"year": year, "format": "old", "provinces": n_prov, "dims": sorted(dim_cols), "subs": len(sub_cols)}


def parse_new(year: int, fname: str, rows: list):
    wb = openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True)
    target = None
    for name in wb.sheetnames:
        ns = name.strip()
        if ns.startswith(str(year)) and "VIE_ENG" in ns:
            target = name
            break
    if target is None:
        raise RuntimeError(f"{fname}: không tìm thấy sheet {year}_VIE_ENG")
    ws = wb[target]
    it = ws.iter_rows(values_only=True)
    row1 = next(it)   # mã tỉnh
    next(it)          # dòng 2: tên tỉnh — bỏ qua, dữ liệu bắt đầu từ dòng 3

    col_code = {}
    for j in range(3, len(row1)):
        v = row1[j]
        if isinstance(v, (int, float)) and float(v).is_integer() and 1 <= int(v) <= 96:
            col_code[j] = int(v)

    dim_data = {n: {} for n in range(1, 9)}
    sub_data: dict[str, dict] = {}
    for r in it:
        if r is None:
            continue
        c0 = str(r[0]).strip() if r[0] is not None else ""
        c1 = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
        m = DIM_ROW_RE.match(c0)
        if m:
            n = int(m.group(1))
            if not dim_data[n]:  # chỉ lấy block đầu tiên
                for j, code in col_code.items():
                    dim_data[n][code] = to_float(r[j]) if j < len(r) else np.nan
            continue
        m2 = SUB_RE.match(c1)
        if m2:
            key = f"sd_{m2.group(1)}_{m2.group(2)}"
            if key not in sub_data:
                sub_data[key] = {
                    code: (to_float(r[j]) if j < len(r) else np.nan)
                    for j, code in col_code.items()
                }

    for code in sorted(set(col_code.values())):
        rec = {"province_code": code, "year": year}
        for n in range(1, 9):
            rec[f"d{n}"] = dim_data[n].get(code, np.nan)
        for key, dd in sub_data.items():
            rec[key] = dd.get(code, np.nan)
        rows.append(rec)
    wb.close()
    return {
        "year": year, "format": "new", "provinces": len(set(col_code.values())),
        "dims": sorted(n for n in dim_data if dim_data[n]), "subs": len(sub_data),
    }


def main() -> int:
    if not CROSSWALK.exists():
        print(f"[FATAL] Thiếu crosswalk: {CROSSWALK}")
        return 2
    ascii2code, code2info = load_crosswalk()

    rows: list[dict] = []
    diagnostics = []
    for year, fname in OLD_FILES.items():
        diagnostics.append(parse_old(year, fname, rows))
    for year, fname in NEW_FILES.items():
        diagnostics.append(parse_new(year, fname, rows))

    df = pd.DataFrame(rows)

    # Gắn mã tỉnh cho các hàng định dạng cũ (map từ tên ASCII qua crosswalk)
    if "province_code" not in df.columns:
        df["province_code"] = np.nan
    df["province_code"] = df["province_code"].astype("float64").fillna(
        df["province_ascii"].map(lambda a: lookup_code(a, ascii2code))
    )
    unmatched = sorted(df.loc[df["province_code"].isna(), "province_ascii"].dropna().unique())
    if unmatched:
        print("[FATAL] Tên tỉnh không map được:", unmatched)
        return 3

    df["province_code"] = df["province_code"].astype(int)
    df["province_vi"] = df["province_code"].map(lambda c: code2info.get(c, {}).get("province_vi", ""))
    df["province_ascii"] = df["province_code"].map(lambda c: code2info.get(c, {}).get("province_ascii", ""))

    # Làm sạch: 0.0 trong cột điểm = "không được xếp hạng" (không phải điểm thật —
    # thang chiều là 1–10, thang tiểu-chiều bắt đầu từ 0.25). Gói Mendeley lưu các ô
    # này là NaN; ta chuyển về NaN để đồng nhất trước khi phân tích.
    score_cols = [c for c in df.columns if re.fullmatch(r"d[1-8]", c) or c.startswith("sd_")]
    n_zero = int((df[score_cols] == 0).sum().sum())
    df[score_cols] = df[score_cols].mask(df[score_cols] == 0)
    if n_zero:
        print(f"[clean] chuyển {n_zero} giá trị 0.0 -> NaN (tỉnh không được xếp hạng năm đó)")

    # Cột chuẩn: id trước, d1..d8, rồi các sub-dim đã sắp xếp
    id_cols = ["province_code", "province_ascii", "province_vi", "year"]
    dim_cols = [f"d{i}" for i in range(1, 9)]
    sub_cols = sorted([c for c in df.columns if c.startswith("sd_")],
                      key=lambda x: (int(x.split("_")[1]), int(x.split("_")[2])))
    df = df[id_cols + dim_cols + sub_cols].sort_values(["province_code", "year"]).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print("=== Layout survey ===")
    for d in diagnostics:
        print(f"  {d['year']}: format={d['format']} provinces={d['provinces']} dims={d['dims']} subs={d['subs']}")
    print()
    print("=== Panel ===")
    print("shape:", df.shape)
    print("provinces:", df["province_code"].nunique(), "| years:", sorted(df["year"].unique()))
    print("rows per year:")
    print(df.groupby("year").size().to_string())
    print("numeric columns:", df.select_dtypes("number").shape[1])
    top_missing = (df.isna().mean() * 100).sort_values(ascending=False).head(10)
    print("top missing %:")
    print(top_missing.round(2).to_string())
    print("saved:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
