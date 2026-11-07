"""Chuẩn hóa tỷ lệ hộ nghèo cấp tỉnh từ PX-Web GSO (ma trận V14.47).

Nguồn đã tải về data/raw/gso/ (KHÔNG sửa):
  - pxweb_V14.47_poverty_step2.html — bảng "Tỷ lệ hộ nghèo phân theo địa
    phương" (ma trận V14.47, database "Y tế, văn hóa và MSDC" trên
    pxweb.nso.gov.vn), đơn vị %, cột năm 2006, 2008, 2010, 2012–2016,
    2020–2025 (bảng không có 2017–2019 — KHÔNG nội suy, để trống). Trang HTML
    trả về sau POST form WebForms của PX-Web (xem scripts/gso_pxweb_fetch.py,
    cập nhật lần cuối 21/08/2026, "Bản quyền: Không").
    Chú thích gốc của bảng: "Từ năm 2008 tới nay, số liệu thành phố Hà Nội bao
    gồm cả tỉnh Hà Tây. (*) Chuẩn nghèo của Chính phủ giai đoạn 2011-2015 tính
    theo thu nhập bình quân 1 người 1 tháng ... được cập nhật theo chỉ số giá
    tiêu dùng ..." (chuẩn khác với bảng "chuẩn nghèo đa chiều" trong Niên giám
    2019–2021 cho các năm 2016–2019 — xem PROVENANCE.md data/raw/gso/).

Kết quả (ghi data/processed/, không đụng file nguồn khác):
  - external_poverty_63.csv — province_code, province_ascii, province_vi,
    year, poverty_rate_pct, papi_province_code; 63 tỉnh × 14 năm dạng dài,
    ô thiếu để trống, KHÔNG nội suy.

Đối chiếu (verification, không dùng làm số liệu):
  - Niên giám 2025, bảng chương tr.934–935 (63 tỉnh; cột 2020, 2022*, 2023,
    2024, Sơ bộ 2025) — kỳ vọng trùng khớp pxweb V14.47.
  - Niên giám 2021, bảng "Tỷ lệ hộ nghèo đa chiều phân theo địa phương"
    tr.881–882 (63 tỉnh; cột 2016, 2018, 2019, 2020, 2021) — so cột 2020 và
    2021 (pxweb không có 2016 theo chuẩn đa chiều này, và không có 2018–2019).
  (Bảng phụ lục Niên giám 2025 tr.1494–1495 liệt kê theo 34 tỉnh sau sáp nhập
  2025 — khác địa giới 63 tỉnh nên KHÔNG dùng đối chiếu.)

Chạy từ thư mục gốc repo:  python -E scripts/build_poverty_63.py
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

SRC_HTML = "pxweb_V14.47_poverty_step2.html"

# 6 vùng + cả nước theo bảng pxweb ("TỔNG SỐ"); "hà tây" là dòng cũ (gộp vào
# Hà Nội từ 2008)
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
LEGACY_ASCII = {"ha tay"}


def norm_ascii(name: str) -> str:
    """Chuẩn hóa tên tỉnh về khóa ASCII: NFKC, bỏ 'TP.' đầu, lowercase, gọn khoảng trắng."""
    s = unicodedata.normalize("NFKC", str(name))
    s = s.replace("Ð", "Đ").replace("ð", "đ")
    s = re.sub(r"^\s*tp\.?\s*", "", s, flags=re.I)
    s = re.sub(r"[\s\-–—]+", " ", s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize("NFKC", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def num(cell: str) -> float:
    """'89,53' / '..' -> float / NaN. Giữ 0,0 là 0.0 (giá trị thật)."""
    s = re.sub(r"<[^>]+>", "", str(cell))
    s = s.replace("&nbsp;", " ").replace("\xa0", " ").strip()
    if not s or re.search(r"[a-zA-Z:]", s) or re.fullmatch(r"[\W_]*", s):
        return float("nan")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def html_tables(path: Path) -> list[list[list[str]]]:
    html = path.read_text(encoding="utf-8")
    out = []
    for t in re.findall(r"(?s)<table[^>]*>(.*?)</table>", html):
        rows = []
        for r in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", t):
            cells = re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", r)
            rows.append([re.sub(r"\s+", " ", c).strip() for c in cells])
        out.append(rows)
    return out


def split_label(cell: str) -> str:
    """'Cao Bằng - Cao Bang' -> 'Cao Bằng' (chỉ cắt khi phần sau thuần ASCII)."""
    label = re.sub(r"<[^>]+>", "", cell).replace("&nbsp;", " ").strip()
    label = re.sub(r"\s+", " ", label)
    m = re.search(r"\s+-\s+([A-Za-z][A-Za-z0-9 .,'&()/-]*)$", label)
    if m:
        return label[: m.start()].strip()
    return label


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    cw = pd.read_csv(PKG / "province_crosswalk_63.csv", encoding="utf-8-sig")
    cw["key"] = cw["province_vi"].map(norm_ascii)
    assert cw["key"].is_unique and len(cw) == 63
    key2cw = cw.set_index("key")

    papi = pd.read_csv(OUT / "papi_panel_63_2011_2024.csv")
    papi_map = papi[["province_code", "province_ascii"]].drop_duplicates()
    papi_by_ascii = papi_map.set_index("province_ascii")["province_code"]
    assert papi_by_ascii.index.is_unique

    # ------------------------------------------------------- bảng pxweb V14.47
    tables = html_tables(RAW / SRC_HTML)
    grid = next(t for t in tables if any(re.fullmatch(r"20\d\d", c.strip()) for r in t for c in r) and len(t) > 60)
    header = next(r for r in grid if sum(1 for c in r if re.fullmatch(r"20\d\d", c.strip())) >= 2)
    years = [c.strip() for c in header if re.fullmatch(r"20\d\d", c.strip())]
    print("V14.47 cột năm:", years)
    assert "2017" not in years and "2018" not in years and "2019" not in years

    rows, regions_seen, national = [], [], {}
    for r in grid:
        label = split_label(r[0])
        k = norm_ascii(label)
        if not k or k == "ty le ho ngheo phan theo dia phuong":
            continue
        vals = [num(c) for c in r[1 : 1 + len(years)]]
        if not any(pd.notna(v) for v in vals):
            continue
        if k in ("tong so", "ca nuoc"):
            national = dict(zip(years, vals))
            continue
        if k in REGIONS_ASCII:
            regions_seen.append(label)
            continue
        if k in LEGACY_ASCII:
            filled = [y for y, v in zip(years, vals) if pd.notna(v)]
            print(f"Bỏ dòng cũ {label!r} (chỉ có {filled}; gộp vào Hà Nội từ 2008 theo chú thích bảng)")
            continue
        if k not in key2cw.index:
            raise SystemExit(f"LỖI: tên không khớp crosswalk: {label!r} (key={k!r})")
        rows.append((k, vals))

    assert len(rows) == 63, f"Chỉ khớp {len(rows)}/63 tỉnh"
    assert len(regions_seen) == 6, f"Vùng nhận diện {len(regions_seen)}/6: {regions_seen}"

    long_rows = []
    for k, vals in rows:
        info = key2cw.loc[k]
        for year, v in zip(years, vals):
            long_rows.append({
                "province_code": str(info["province_code"]).strip(),
                "province_ascii": info["province_ascii"],
                "province_vi": info["province_vi"],
                "year": int(year),
                "poverty_rate_pct": v,
            })
    pov = pd.DataFrame(long_rows).sort_values(["province_code", "year"]).reset_index(drop=True)

    # Gán papi_province_code qua province_ascii
    pov["papi_province_code"] = pov["province_ascii"].map(papi_by_ascii)
    if pov["papi_province_code"].isna().any():
        bad = sorted(pov.loc[pov["papi_province_code"].isna(), "province_ascii"].unique())
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {bad}")

    pov.to_csv(OUT / "external_poverty_63.csv", index=False, na_rep="", encoding="utf-8")
    n_missing = int(pov["poverty_rate_pct"].isna().sum())
    print(
        f"Đã ghi external_poverty_63.csv: {pov['province_ascii'].nunique()} tỉnh × "
        f"{pov['year'].nunique()} năm = {len(pov)} dòng; ô thiếu {n_missing} (để trống, không nội suy)"
    )
    print("Giá trị TỔNG SỐ (cả nước) theo bảng, cho đối chiếu nhanh:", national)

    # ---------------------------------------- đối chiếu Niên giám 2025 (verification)
    def yb_table(pdf: str, pages: tuple[int, ...], years_map: dict[int, int]) -> dict[tuple[str, int], float]:
        import pymupdf

        doc = pymupdf.open(str(RAW / pdf))
        out: dict[tuple[str, int], float] = {}
        for p in pages:
            text = doc[p - 1].get_text()
            lines = [line.strip() for line in text.split("\n")]
            for i, line in enumerate(lines):
                k = norm_ascii(split_label(line))
                if k == "hue":  # NH 2025 tách dòng mất 'Thừa Thiên-'
                    k = "thua thien hue"
                if k in key2cw.index:
                    nums = []
                    j = i + 1
                    while j < len(lines) and len(nums) < max(years_map) + 1:
                        t2 = lines[j].strip()
                        k2 = norm_ascii(split_label(t2))
                        if k2 and (k2 in key2cw.index or k2 in REGIONS_ASCII):
                            break  # gặp nhãn hàng kế tiếp — dừng, không nhảy số qua hàng
                        m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})*),(\d+)", t2)
                        if m:
                            nums.append(float((m.group(1).replace(".", "")) + "." + m.group(2)))
                        j += 1
                    if len(nums) == max(years_map) + 1:
                        for pos, yr in years_map.items():
                            out[(k, yr)] = nums[pos]
        doc.close()
        return out

    g = pov.set_index(["province_ascii", "year"])["poverty_rate_pct"]
    checks = [
        (yb_table("nien_giam_2025.pdf", (935, 936), {0: 2020, 1: 2022, 2: 2023, 3: 2024, 4: 2025}),
         "NG2025 chương tr.934-935 (2025 = Sơ bộ)"),
        (yb_table("nien_giam_2021.pdf", (881, 882), {3: 2020, 4: 2021}),
         "NG2021 tr.881-882 cột 2020/2021 (chuẩn đa chiều)"),
    ]
    for yb, name in checks:
        n_ok = n_diff = n_miss = 0
        diff_by_year: dict[int, int] = {}
        for (k, year), v in yb.items():
            key = (cw.set_index("key").loc[k, "province_ascii"], year)
            if key not in g.index or pd.isna(g[key]):
                n_miss += 1
                continue
            if abs(g[key] - v) <= 0.051:
                n_ok += 1
            else:
                n_diff += 1
                diff_by_year[year] = diff_by_year.get(year, 0) + 1
                if n_diff <= 6:
                    print(f"  LỆCH {name}: {key} pxweb={g[key]} vs niên giám={v}")
        print(f"Đối chiếu {name}: trùng {n_ok}, lệch {n_diff}, thiếu {n_miss} / {len(yb)} | lệch theo năm: {diff_by_year}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
