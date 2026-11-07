"""Chuẩn hóa dữ liệu GSO tải từ pxweb.nso.gov.vn và Niên giám Thống kê.

Nguồn đã tải về data/raw/gso/ (KHÔNG sửa):
  - pxweb_V03.12_grdp_pc_step2.html  — bảng "Tổng sản phẩm trên địa bàn bình
    quân đầu người phân theo địa phương" (ma trận V03.12), 63 tỉnh, đơn vị
    Triệu đồng, cột 2018..2023, Sơ bộ 2024, Ước tính 2025. Trang HTML trả về
    sau khi POST form WebForms của PX-Web (xem scripts/gso_pxweb_fetch.py).
  - pxweb_V02.01_pop_step2.html      — bảng "Diện tích, dân số và mật độ dân
    số phân theo địa phương" (ma trận V02.01), 63 tỉnh, Dân số trung bình
    (Nghìn người), 2011..2025.
  - nien_giam_2022.pdf / nien_giam_2025.pdf — Niên giám Thống kê, bảng GRDP
    bình quân đầu người (Triệu đồng), dùng ĐỐI CHIẾU (không dùng làm số liệu).

Kết quả (ghi data/processed/, không đụng file nguồn khác):
  - external_gso_grdp_63.csv         — GRDP bình quân đầu người (triệu đồng)
    theo tỉnh-năm, 2018–2024 (2024 = Sơ bộ).
  - external_gso_population_63_full.csv — dân số trung bình đầy đủ 2011–2024:
    năm cũ giữ giá trị trích Niên giám (file base), năm thiếu lấy từ pxweb
    V02.01, cột `source` ghi rõ từng dòng.

Chạy từ thư mục gốc repo:  python -E scripts/build_gso_grdp_pop.py
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
    "ca nuoc",
    "dong bang song hong",
    "trung du va mien nui phia bac",
    "bac trung bo va duyen hai mien trung",
    "tay nguyen",
    "dong nam bo",
    "dong bang song cuu long",
}


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
    """'89,53' / '6.825,82' / '1.234.567,8' -> float; rỗng/'...' -> NaN."""
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
    """'Đồng bằng sông Hồng - Red River Delta' -> 'Đồng bằng sông Hồng'.

    Chỉ cắt khi phần sau dấu ' - ' là thuần ASCII (tên tiếng Anh); giữ nguyên
    'Bà Rịa - Vũng Tàu' vì 'Vũng Tàu' có dấu tiếng Việt.
    """
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

    # ------------------------------------------------------------------ GRDP
    tables = html_tables(RAW / "pxweb_V03.12_grdp_pc_step2.html")
    grid = next(t for t in tables if any("2018" in c for r in t for c in r) and len(t) > 60)
    header = next(r for r in grid if any(re.fullmatch(r"20\d\d", c.strip()) for c in r))
    year_cols = [c.strip() for c in header if re.search(r"20\d\d", c)]
    print("V03.12 cột năm:", year_cols)

    rows, regions_seen = [], []
    for r in grid:
        label = split_label(r[0])
        k = norm_ascii(label)
        if not k or k in ("tổng sản phẩm trên địa bàn bình quân đầu người",):
            continue
        vals = [num(c) for c in r[1 : 1 + len(year_cols)]]
        if not any(pd.notna(v) for v in vals):
            continue
        if k in REGIONS_ASCII:
            regions_seen.append(label)
            continue
        if k not in key2cw.index:
            raise SystemExit(f"LỖI: tên không khớp crosswalk: {label!r} (key={k!r})")
        rows.append((k, vals))

    assert len(rows) == 63, f"Chỉ khớp {len(rows)}/63 tỉnh"
    assert len(regions_seen) >= 5, f"Vùng nhận diện thiếu: {regions_seen}"

    grdp = []
    for k, vals in rows:
        info = key2cw.loc[k]
        for yc, v in zip(year_cols, vals):
            if yc.startswith("Ước tính"):
                continue  # ngoài phạm vi 2011-2024
            year = int(re.search(r"20\d\d", yc).group(0))
            src = "gso_pxweb_V03.12"
            if yc.startswith("Sơ bộ"):
                src += " (Sơ bộ/preliminary)"
            grdp.append({
                "province_code": str(info["province_code"]).strip(),
                "province_ascii": info["province_ascii"],
                "province_vi": info["province_vi"],
                "year": year,
                "grdp_per_capita_million_vnd": v,
                "source": src,
            })
    grdp = pd.DataFrame(grdp).sort_values(["province_code", "year"]).reset_index(drop=True)

    # Gán papi_province_code qua province_ascii
    grdp["papi_province_code"] = grdp["province_ascii"].map(papi_by_ascii)
    if grdp["papi_province_code"].isna().any():
        bad = sorted(grdp.loc[grdp["papi_province_code"].isna(), "province_ascii"].unique())
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {bad}")

    # -------------------------------------------------- đối chiếu Niên giám
    def yb_table(pdf: str, pages: tuple[int, ...], years: dict[int, int]) -> dict[tuple[str, int], float]:
        import pymupdf

        doc = pymupdf.open(str(RAW / pdf))
        out = {}
        for p in pages:
            text = doc[p - 1].get_text()
            lines = [line.strip() for line in text.split("\n")]
            for i, line in enumerate(lines):
                k = norm_ascii(split_label(line))
                if k in key2cw.index:
                    nums = []
                    j = i + 1
                    while j < len(lines) and len(nums) < len(years):
                        t2 = lines[j].strip()
                        m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})*),(\d+)", t2)
                        if m:
                            nums.append(float((m.group(1).replace(".", "")) + "." + m.group(2)))
                        j += 1
                    if len(nums) == len(years):
                        for pos, yr in years.items():
                            out[(k, yr)] = nums[pos]
        doc.close()
        return out

    yb22 = yb_table("nien_giam_2022.pdf", (260, 261), {0: 2018, 1: 2019, 2: 2020, 3: 2021, 4: 2022})
    yb25 = yb_table("nien_giam_2025.pdf", (245, 246), {0: 2020, 1: 2022, 2: 2023, 3: 2024})

    g = grdp.set_index(["province_ascii", "year"])["grdp_per_capita_million_vnd"]
    checks = [(yb22, "YB2022 (2022 là cột Sơ bộ)"), (yb25, "YB2025 (2024 là cột Sơ bộ)")]
    for yb, name in checks:
        n_ok = n_diff = n_miss = 0
        diff_by_year: dict[int, int] = {}
        for (k, year), v in yb.items():
            key = (cw.set_index("key").loc[k, "province_ascii"], year)
            if key not in g.index or pd.isna(g[key]):
                n_miss += 1
                continue
            if abs(g[key] - v) <= 0.051:  # YB in 1 chữ số thập phân, pxweb 2 chữ số
                n_ok += 1
            else:
                n_diff += 1
                diff_by_year[year] = diff_by_year.get(year, 0) + 1
                if n_diff <= 6:
                    print(f"  LỆCH {name}: {key} pxweb={g[key]} vs {v}")
        print(f"Đối chiếu {name}: trùng {n_ok}, lệch {n_diff}, thiếu {n_miss} / {len(yb)} | lệch theo năm: {diff_by_year}")

    # ------------------------------------------------------------- dân số
    pop_rows = []
    for fname in (
        "pxweb_V02.01_pop_step2.html",
        "pxweb_V02.01_pop_2021_2025_step2.html",
        "pxweb_V02.01_pop_2024_2025_step2.html",
    ):
        tables = html_tables(RAW / fname)
        grid = next(t for t in tables if any(re.fullmatch(r"20\d\d", c.strip()) for r in t for c in r) and len(t) > 60)
        header = next(r for r in grid if sum(1 for c in r if re.search(r"20\d\d", c)) >= 2)
        years = [c.strip() for c in header if re.search(r"20\d\d", c) and len(c.strip()) <= 16]
        # mỗi năm 3 ô dữ liệu: Diện tích, Dân số trung bình, Mật độ — dân số là ô 3*i+1
        pop_cols = {yr: 3 * i + 1 for i, yr in enumerate(years)}
        print(f"{fname}: năm {years[0]}..{years[-1]} ({len(years)} năm, 3 chỉ tiêu/năm)")

        for r in grid:
            label = split_label(r[0])
            k = norm_ascii(label)
            if not k:
                continue
            cells = [num(c) for c in r[1:]]
            if sum(pd.notna(c) for c in cells) < 4:
                continue  # dòng tiêu đề/caption không có số liệu
            if k in REGIONS_ASCII:
                continue
            if k not in key2cw.index:
                raise SystemExit(f"LỖI: tên dân số không khớp crosswalk: {label!r} (key={k!r})")
            info = key2cw.loc[k]
            for yr, ci in pop_cols.items():
                if int(yr) > 2024:
                    continue
                v = cells[ci] if ci < len(cells) else float("nan")
                pop_rows.append({
                    "province_code": str(info["province_code"]).strip(),
                    "province_ascii": info["province_ascii"],
                    "province_vi": info["province_vi"],
                    "year": int(yr),
                    "gso_pop_total_thousand": v,
                    "source": "gso_pxweb_V02.01 (dân số trung bình)",
                })
    pop = pd.DataFrame(pop_rows)
    assert pop["province_code"].nunique() == 63
    # mỗi tỉnh-năm phải có duy nhất 1 dòng
    dup = pop[pop.duplicated(["province_code", "year"], keep=False)]
    assert dup.empty, f"Trùng tỉnh-năm trong dữ liệu pxweb: {dup.head()}"

    # ------------------------------------------------- gộp file dân số đầy đủ
    base = pd.read_csv(OUT / "external_gso_population_63.csv")
    base["province_code"] = base["province_code"].astype(str)
    base["source"] = "gso_nien_giam_extract (Mendeley replication package)"
    missing_years = sorted(set(range(2011, 2025)) - set(base["year"].unique()))
    print("Năm thiếu trong base:", missing_years)
    fill = pop[pop["year"].isin(missing_years)].copy()
    for col in ("gso_pop_urban_thousand", "gso_urban_residence_pct_derived"):
        fill[col] = float("nan")
    full = pd.concat([base, fill], ignore_index=True)
    full["papi_province_code"] = full["province_ascii"].map(papi_by_ascii)
    if full["papi_province_code"].isna().any():
        bad = sorted(full.loc[full["papi_province_code"].isna(), "province_ascii"].unique())
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {bad}")
    full = full.sort_values(["province_code", "year"]).reset_index(drop=True)
    cols = ["papi_province_code", "province_code", "province_ascii", "province_vi", "year",
            "gso_pop_total_thousand", "gso_pop_urban_thousand",
            "gso_urban_residence_pct_derived", "source"]
    full = full[cols]

    # so sánh vintage: năm trùng nhau giữa base và pxweb
    chk = base.merge(pop, on=["province_code", "year"], suffixes=("_base", "_px"))
    chk["diff"] = (chk["gso_pop_total_thousand_base"] - chk["gso_pop_total_thousand_px"]).abs()
    print(f"So sánh vintage (base Niên giám vs pxweb V02.01) trên {len(chk)} tỉnh-năm trùng:")
    print("  chênh lệch trung bình:", round(chk["diff"].mean(), 2), "nghìn người; max:",
          round(chk["diff"].max(), 2), "| dòng lệch >1%:", int((chk["diff"] / chk["gso_pop_total_thousand_base"] > 0.01).sum()))

    # --------------------------------------------------------------- ghi file
    OUT.mkdir(parents=True, exist_ok=True)
    grdp.to_csv(OUT / "external_gso_grdp_63.csv", index=False)
    full.to_csv(OUT / "external_gso_population_63_full.csv", index=False)

    years_g = sorted(grdp["year"].unique())
    print(f"\nĐã ghi {OUT / 'external_gso_grdp_63.csv'}: {grdp['province_code'].nunique()} tỉnh × "
          f"{len(years_g)} năm ({years_g[0]}–{years_g[-1]}), {len(grdp)} dòng, "
          f"thiếu {int(grdp['grdp_per_capita_million_vnd'].isna().sum())} ô giá trị")
    print(f"Đã ghi {OUT / 'external_gso_population_63_full.csv'}: {full['province_code'].nunique()} tỉnh × "
          f"{full['year'].nunique()} năm ({full['year'].min()}–{full['year'].max()}), {len(full)} dòng")
    return 0


if __name__ == "__main__":
    sys.exit(main())
