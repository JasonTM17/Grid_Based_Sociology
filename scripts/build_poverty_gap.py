"""Điền lỗ hổng 2017–2019 của tỷ lệ hộ nghèo cấp tỉnh từ Niên giám Thống kê (GSO).

Bối cảnh: bảng PX-Web V14.47 ("Tỷ lệ hộ nghèo phân theo địa phương",
pxweb.nso.gov.vn) KHÔNG có cột 2017, 2018, 2019 (đã kiểm tra listbox "Năm"
của trang chọn biến — 2026-11-08, lưu data/raw/gso/pxweb_V14.46_step1_*.html,
pxweb_PL.V14.24_step1_*.html và 2 tablelist làm bằng chứng). Quét tablelist
cả 28 database cổng PX-Web: chỉ có 4 bảng "nghèo" (V14.46, V14.47, PL.V14.23,
PL.V14.24) và không bảng nào phủ 2017–2019 ở cấp tỉnh.

Nguồn dùng để điền (đều là ấn phẩm chính thức của Tổng cục/Cục Thống kê,
đã tải sẵn data/raw/gso/nien_giam_*.pdf, manifest trong PROVENANCE.md):
  - Niên giám 2018, tr.854–856: "Tỷ lệ hộ nghèo phân theo địa phương", 6 cột
    [2010, 2015, 2016 thu nhập, 2016 đa chiều, 2017, Sơ bộ 2018] — dùng cột
    đa chiều.
  - Niên giám 2019, tr.864–865 (Biểu 365): "Tỷ lệ hộ nghèo phân theo địa
    phương(*)" — 2016, 2017, 2018, Sơ bộ 2019. Chú thích (*): "Tỷ lệ hộ nghèo
    được tính theo chuẩn nghèo tiếp cận đa chiều".
  - Niên giám 2020, tr.879–880: như trên — 2016, 2017, 2018, 2019, Sơ bộ 2020.
  - Niên giám 2021, tr.881–882: "Tỷ lệ hộ nghèo đa chiều phân theo địa
    phương(*)" — 2016, 2018, 2019, 2020, Sơ bộ 2021.

Chọn số liệu theo vintage mới nhất chứa năm đó (cùng quy ước
external_gso_population_63_full.csv):
  2017 ← Niên giám 2020;  2018, 2019 ← Niên giám 2021.
Các vintage khác chỉ dùng đối chiếu chéo (in lệch nếu > 0,051 = sai số làm
tròn 1 chữ số thập phân), không dùng làm số liệu. KHÔNG nội suy.

Kiểm tra liên tục (sanity, không phải nguồn số liệu): cột 2020/2021 của
Niên giám 2021 phải trùng data/processed/external_poverty_63.csv (pxweb
V14.47 đã đối chiếu 124/124 trong scripts/build_poverty_63.py).

Kết quả: data/processed/external_poverty_gap_63.csv — 63 tỉnh × 2017–2019
(189 dòng), cột province_code, province_ascii, province_vi, year,
poverty_rate_pct, papi_province_code, source. KHÔNG đụng
external_poverty_63.csv (file đó chỉ được merge ở giai đoạn tích hợp).

Chạy từ thư mục gốc repo:  python -E scripts/build_poverty_gap.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "gso"
OUT = ROOT / "data" / "processed"
PKG = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data"

REGIONS_ASCII = {
    "tong so",
    "ca nuoc",
    "dong bang song hong",
    "trung du va mien nui phia bac",
    "bac trung bo va duyen hai mien trung",
    "tay nguyen",
    "dong nam bo",
    "dong bang song cuu long",
}

# (file, các trang pdf, số cột bảng, {vị trí cột: năm}, nhãn source)
YEARBOOKS: list[tuple[str, tuple[int, ...], int, dict[int, int], str]] = [
    ("nien_giam_2018.pdf", (854, 855, 856), 6, {3: 2016, 4: 2017, 5: 2018},
     "GSO NGTK 2018 tr.854-856 (đa chiều; 2018=Sơ bộ)"),
    ("nien_giam_2019.pdf", (864, 865), 4, {0: 2016, 1: 2017, 2: 2018, 3: 2019},
     "GSO NGTK 2019 tr.864-865 (đa chiều; 2019=Sơ bộ)"),
    ("nien_giam_2020.pdf", (879, 880), 5, {0: 2016, 1: 2017, 2: 2018, 3: 2019, 4: 2020},
     "GSO NGTK 2020 tr.879-880 (đa chiều; 2020=Sơ bộ)"),
    ("nien_giam_2021.pdf", (881, 882), 5, {0: 2016, 1: 2018, 2: 2019, 3: 2020, 4: 2021},
     "GSO NGTK 2021 tr.881-882 (đa chiều; 2021=Sơ bộ)"),
]

# Năm kết quả -> (chỉ số trong YEARBOOKS, vị trí cột): vintage mới nhất chứa năm
PRIMARY = {2017: (2, 1), 2018: (3, 1), 2019: (3, 2)}

NUM_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*),(\d+)")


def norm_ascii(name: str) -> str:
    """Chuẩn hóa tên tỉnh về khóa ASCII (giống hệt scripts/build_poverty_63.py)."""
    s = unicodedata.normalize("NFKC", str(name))
    s = s.replace("Ð", "Đ").replace("ð", "đ")
    s = re.sub(r"^\s*tp\.?\s*", "", s, flags=re.I)
    s = re.sub(r"[\s\-–—]+", " ", s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize("NFKC", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def split_label(cell: str) -> str:
    """'CẢ NƯỚC - WHOLE COUNTRY' -> 'CẢ NƯỚC' (chỉ cắt khi phần sau thuần ASCII)."""
    label = re.sub(r"<[^>]+>", "", cell).replace("&nbsp;", " ").strip()
    label = re.sub(r"\s+", " ", label)
    m = re.search(r"\s+-\s+([A-Za-z][A-Za-z0-9 .,'&()/-]*)$", label)
    if m:
        return label[: m.start()].strip()
    return label


def parse_cells(lines: list[str], i: int, ncols: int) -> list[float]:
    """Thu các ô của hàng bắt đầu tại lines[i] (nhãn tỉnh): số / '' / '..' =
    ô giá trị hoặc ô trống; gặp nhãn/footnote (text khác) thì dừng."""
    cells: list[float] = []
    j = i + 1
    while j < len(lines) and len(cells) < ncols:
        t = lines[j].strip()
        m = NUM_RE.fullmatch(t)
        if m:
            cells.append(float(m.group(1).replace(".", "") + "." + m.group(2)))
        elif t in ("", "..", "…", "-"):
            cells.append(float("nan"))
        else:
            break
        j += 1
    return cells


def parse_yearbook(pdf: str, pages: tuple[int, ...], ncols: int,
                   key2cw_index: pd.Index) -> tuple[dict[tuple[str, int], float],
                                                    dict[int, float], dict[str, int]]:
    """Trích {(key tỉnh, năm): giá trị} + {năm: giá trị CẢ NƯỚC} từ 1 Niên giám."""
    import pymupdf

    doc = pymupdf.open(str(RAW / pdf))
    vals: dict[tuple[str, int], float] = {}
    national: dict[int, float] = {}
    provinces_seen: set[str] = set()
    for p in pages:
        lines = [ln.strip() for ln in doc[p - 1].get_text().split("\n")]
        for i, line in enumerate(lines):
            k = norm_ascii(split_label(line))
            if k not in key2cw_index and k not in ("ca nuoc",):
                continue
            cells = parse_cells(lines, i, ncols)
            if len(cells) < ncols:
                continue  # tiêu đề trùng chữ (vd 'Hà Nội' trong mục lục) — không phải hàng số liệu
            for pos, year in sorted(POSITIONS[pdf].items()):
                if pos < len(cells) and pd.notna(cells[pos]):
                    if k == "ca nuoc":
                        national[year] = cells[pos]
                    elif k in key2cw_index:
                        vals[(k, year)] = cells[pos]
            if k in key2cw_index:
                provinces_seen.add(k)
    doc.close()
    return vals, national, provinces_seen


POSITIONS: dict[str, dict[int, int]] = {}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    global POSITIONS
    for pdf, _pages, _ncols, colmap, _label in YEARBOOKS:
        POSITIONS[pdf] = {pos: year for pos, year in colmap.items()}

    cw = pd.read_csv(PKG / "province_crosswalk_63.csv", encoding="utf-8-sig")
    cw["key"] = cw["province_vi"].map(norm_ascii)
    assert cw["key"].is_unique and len(cw) == 63
    key2cw = cw.set_index("key")

    papi = pd.read_csv(OUT / "papi_panel_63_2011_2024.csv")
    papi_map = papi[["province_code", "province_ascii"]].drop_duplicates()
    papi_by_ascii = papi_map.set_index("province_ascii")["province_code"]
    assert papi_by_ascii.index.is_unique

    # -------------------------------------------------- trích 4 bảng Niên giám
    extracted: dict[str, dict[tuple[str, int], float]] = {}
    nationals: dict[str, dict[int, float]] = {}
    for pdf, pages, ncols, colmap, label in YEARBOOKS:
        vals, national, seen = parse_yearbook(pdf, pages, ncols, key2cw.index)
        want_years = sorted(set(colmap.values()))
        got_prov = {y: sum(1 for k, yy in vals if yy == y) for y in want_years}
        print(f"{label}: tỉnh/năm = {got_prov}; cả nước = {national}")
        assert len(seen) == 63, f"{pdf}: chỉ nhận diện {len(seen)}/63 tỉnh"
        # TP.HCM để trống 2020/2021 trong NGTK 2021 (đã ghi trong PROVENANCE.md
        # cũ: "TP.HCM 2020/2021 để trống trong Niên giám") — 62/63 là duy nhất
        # 2 cột đó; mọi cột khác phải đủ 63.
        for y in want_years:
            n = got_prov[y]
            if pdf == "nien_giam_2021.pdf" and y in (2020, 2021):
                assert n == 62, f"{pdf}: cột {y} có {n}/63 tỉnh (kỳ vọng 62 — chỉ TP.HCM trống)"
            else:
                assert n == 63, f"{pdf}: cột {y} chỉ có {n}/63 tỉnh"
        extracted[pdf] = vals
        nationals[pdf] = national

    # --------------------------------------------- đối chiếu chéo giữa các vintage
    all_years = sorted({y for _p, _pg, _n, cm, _l in YEARBOOKS for y in cm.values()})
    print("\nĐối chiếu chéo các vintage (dung sai 0,051):")
    vintage_conflict = False
    for y in all_years:
        holders = [(pdf, pos) for pdf, _pg, _n, cm, _l in YEARBOOKS
                   for pos, yy in cm.items() if yy == y]
        if len(holders) < 2:
            continue
        base_pdf, base_pos = holders[0]
        n_diff = 0
        for (k, yy), v0 in extracted[base_pdf].items():
            if yy != y:
                continue
            for pdf2, pos2 in holders[1:]:
                v2 = extracted[pdf2].get((k, y))
                if v2 is not None and abs(v0 - v2) > 0.051:
                    n_diff += 1
                    if n_diff <= 8:
                        print(f"  LỆCH năm {y} {k}: {Path(base_pdf).stem}={v0} vs {Path(pdf2).stem}={v2}")
        if n_diff:
            vintage_conflict = True
        print(f"  năm {y}: {len(holders)} nguồn {[(Path(p).stem, q) for p, q in holders]} — {n_diff} ô lệch")

    # --------------- sanity: cột 2020/2021 NGTK 2021 phải trùng external_poverty_63.csv
    existing = pd.read_csv(OUT / "external_poverty_63.csv")
    g2020 = existing.set_index(["province_ascii", "year"])["poverty_rate_pct"]
    n_ok = n_diff = n_skip = 0
    ng21 = extracted["nien_giam_2021.pdf"]
    ascii_by_key = key2cw["province_ascii"]
    for (k, year), v in ng21.items():
        if year not in (2020, 2021) or pd.isna(v):
            continue
        key2 = (ascii_by_key[k], year)
        if key2 not in g2020.index or pd.isna(g2020[key2]):
            n_skip += 1
            continue
        if abs(g2020[key2] - v) <= 0.051:
            n_ok += 1
        else:
            n_diff += 1
            print(f"  NGTK2021 {year} {k}={v} KHÁC pxweb V14.47={g2020[key2]}")
    print(f"Sanity NGTK 2021 (2020/2021) vs external_poverty_63.csv: trùng {n_ok}, "
          f"lệch {n_diff}, bỏ qua {n_skip} (TP.HCM trống trong Niên giám)")
    assert n_diff == 0, "NGTK 2021 cột 2020/2021 lệch pxweb — kiểm tra parser"

    # --------------------------------------------- dựng bảng chỉ 2017–2019
    rows = []
    for year, (yi, pos) in PRIMARY.items():
        pdf = YEARBOOKS[yi][0]
        label = YEARBOOKS[yi][4]
        vals = extracted[pdf]
        for k in key2cw.index:
            v = vals.get((k, year))
            assert v is not None and pd.notna(v), f"Thiếu {year} {k} trong {pdf} — KHÔNG nội suy"
            info = key2cw.loc[k]
            rows.append({
                "province_code": str(info["province_code"]).strip(),
                "province_ascii": info["province_ascii"],
                "province_vi": info["province_vi"],
                "year": year,
                "poverty_rate_pct": v,
                "source": label,
            })
    gap = pd.DataFrame(rows).sort_values(["province_code", "year"]).reset_index(drop=True)
    assert len(gap) == 189 and gap["poverty_rate_pct"].notna().all()
    assert set(gap["year"]) == {2017, 2018, 2019}

    gap["papi_province_code"] = gap["province_ascii"].map(papi_by_ascii)
    if gap["papi_province_code"].isna().any():
        bad = sorted(gap.loc[gap["papi_province_code"].isna(), "province_ascii"].unique())
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {bad}")

    out_path = OUT / "external_poverty_gap_63.csv"
    gap.to_csv(out_path, index=False, na_rep="", encoding="utf-8")
    print(f"\nĐã ghi {out_path.relative_to(ROOT)}: {len(gap)} dòng "
          f"({gap['province_ascii'].nunique()} tỉnh × {gap['year'].nunique()} năm), 0 ô thiếu")

    print("CẢ NƯỚC theo vintage chính (đối chiếu nhanh):")
    for year, (yi, pos) in PRIMARY.items():
        print(f"  {year}: {nationals[YEARBOOKS[yi][0]].get(year)}")

    if vintage_conflict:
        print("\nLƯU Ý: có ô lệch giữa các vintage — đã in ở trên; số liệu dùng "
              "vintage mới nhất (xem PROVENANCE.md data/raw/gso/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
