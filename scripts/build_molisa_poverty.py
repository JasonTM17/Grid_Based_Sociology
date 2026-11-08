"""Chuẩn hóa số hộ nghèo / tỷ lệ hộ nghèo theo tỉnh từ các Quyết định của MOLISA.

Nguồn đã tải về data/raw/molisa/ (KHÔNG sửa; xem PROVENANCE.md cùng thư mục):
  - QĐ 862/QĐ-LĐTBXH (04/07/2018): kết quả rà soát hộ nghèo, hộ cận nghèo năm 2017
  - QĐ 1052/QĐ-LĐTBXH (29/07/2019): kết quả rà soát năm 2018
  - QĐ 835/QĐ-LĐTBXH (15/07/2020): kết quả rà soát năm 2019
Phụ lục Số 1 của mỗi quyết định là bảng "Tổng hợp số liệu hộ nghèo, hộ cận nghèo
cả nước năm YYYY" theo 63 tỉnh/thành phố (tổng số hộ dân, số hộ nghèo, tỷ lệ %,
số hộ cận nghèo, tỷ lệ %) — chuẩn nghèo tiếp cận đa chiều giai đoạn 2016-2020.

molisa.gov.vn, dolab.gov.vn và vanban.chinhphu.vn KHÔNG truy cập được từ máy này
(TCP timeout — bằng chứng trong PROVENANCE.md); bản PDF chính thức trên
datafiles.chinhphu.vn là bản scan (không có lớp chữ, không OCR theo quy tắc
nhiệm vụ). Nguồn dữ liệu ở đây là TOÀN VĂN HTML (bảng Phụ lục Số 1) do hai cơ
sở dữ liệu pháp luật gõ lại độc lập:
  - năm 2017, 2018: hai bản gõ độc lập (luatvietnam.vn trực tiếp +
    thuvienphapluat.vn qua Wayback Machine) — script so từng ô giữa hai bản,
    lệch ô nào cũng dừng;
  - năm 2019: một bản gõ đầy đủ (thuvienphapluat.vn qua Wayback) — kiểm tra
    tính nhất quán số học từng dòng và tổng 63 tỉnh bằng dòng "Cả nước".

'source=molisa_<năm>' với <năm> là năm số liệu rà soát trong file (2017/2018/2019).

Kiểm tra dữ liệu (đều là điều kiện dừng):
  1. Mỗi bảng: đủ 63 tỉnh, STT 1..63 liên tục, có dòng "Cả nước", 6 dòng vùng.
  2. Số học từng dòng: tỷ lệ % = số hộ / tổng số hộ dân × 100, khớp làm tròn
     2 chữ số thập phân (dung sai 0,0051) — cả hộ nghèo lẫn hộ cận nghèo.
  3. Tổng 63 tỉnh từng cột số đếm = dòng "Cả nước"; tỷ lệ cả nước tính lại từ
     tổng cũng khớp.
  4. Hai bản gõ của cùng một năm: giá trị từng ô trùng khớp 100%.
  5. Tổng cả nước khớp số công bố trong văn bản (1.642.489/6,70% · 2017;
     1.304.001/5,23% · 2018; 984.764/3,75% · 2019).

Kết quả (ghi data/processed/, không đụng file nguồn khác):
  - external_molisa_poverty_63.csv — province_code, province_ascii, province_vi,
    year, poverty_rate_pct, papi_province_code (schema chuẩn như
    external_poverty_63.csv) + các cột bổ sung của nguồn: tong_so_ho_dan,
    so_ho_ngheo, so_ho_can_ngheo, ty_le_can_ngheo_pct, decision_no,
    decision_date, source. Dạng dài 63 tỉnh × 3 năm (2017-2019), KHÔNG nội suy
    năm khác.

Chạy từ thư mục gốc repo:  python -E scripts/build_molisa_poverty.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "molisa"
OUT = ROOT / "data" / "processed"
CROSSWALK = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
PAPI = OUT / "papi_panel_63_2011_2024.csv"

# Năm số liệu -> (file chính, file đối chứng). 2019 chỉ có một bản gõ đầy đủ.
SOURCES: dict[int, list[tuple[str, str]]] = {
    2017: [
        ("QD862_2017_luatvietnam.html", "luatvietnam"),
        ("QD862_2017_thuvienphapluat_wayback20240805133145.html", "thuvienphapluat-wayback"),
    ],
    2018: [
        ("QD1052_2018_luatvietnam.html", "luatvietnam"),
        ("QD1052_2018_thuvienphapluat_wayback20211016091154.html", "thuvienphapluat-wayback"),
    ],
    2019: [
        ("QD835_2019_thuvienphapluat_wayback20211205045134.html", "thuvienphapluat-wayback"),
    ],
}

DECISIONS: dict[int, tuple[str, str]] = {
    2017: ("862/QĐ-LĐTBXH", "2018-07-04"),
    2018: ("1052/QĐ-LĐTBXH", "2019-07-29"),
    2019: ("835/QĐ-LĐTBXH", "2020-07-15"),
}

# Tổng cả nước công bố trong từng quyết định (số hộ nghèo, tỷ lệ %) — kiểm tra chốt.
NATIONAL_EXPECTED: dict[int, tuple[float, float]] = {
    2017: (1642489.0, 6.70),
    2018: (1304001.0, 5.23),
    2019: (984764.0, 3.75),
}

REGION_ASCII = {
    "mien nui dong bac",
    "mien nui tay bac",
    "dong bang song hong",
    "bac trung bo va duyen hai mien trung",
    "tay nguyen",
    "dong nam bo",
    "dong bang song cuu long",
}
REGION_KEYS: set[str] = set()  # điền sau khi desp() được định nghĩa (xem module body cuối)


def norm_ascii(name: str) -> str:
    """Chuẩn hóa tên về khóa ASCII (giống build_poverty_63.py)."""
    s = unicodedata.normalize("NFKC", str(name))
    s = s.replace("Ð", "Đ").replace("ð", "đ")
    s = re.sub(r"^\s*tp\.?\s*", "", s, flags=re.I)
    s = re.sub(r"[\s\-–—]+", " ", s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize("NFKC", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def desp(s: str) -> str:
    """Bỏ toàn bộ khoảng trắng (khớp tên bị gõ lệch khoảng trắng kiểu 'S ơ n')."""
    return re.sub(r"\s+", "", s)


REGION_KEYS = {desp(k) for k in REGION_ASCII}


def cell_text(cell: str) -> str:
    """Ô HTML -> chữ thường đã bỏ thẻ và &nbsp;."""
    s = re.sub(r"<[^>]+>", "", str(cell))
    s = s.replace("&nbsp;", " ").replace("\xa0", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def num(cell: str) -> float:
    """'1.642.489' / '34,18' / '-' -> float / NaN. 0,0 giữ nguyên."""
    s = cell_text(cell)
    if not s or re.search(r"[a-zA-Z:/]", s) or re.fullmatch(r"[\W_]*", s):
        return float("nan")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def html_table_blocks(html: str) -> list[tuple[str, list[list[str]]]]:
    """Tách [(đoạn văn bản nằm TRƯỚC bảng, các <tr> của bảng)]."""
    parts = re.split(r"(?s)(<table[^>]*>.*?</table>)", html)
    out = []
    pending_text = ""
    for part in parts:
        if part.startswith("<table"):
            rows = []
            for r in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", part):
                cells = re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", r)
                rows.append([cell_text(c) for c in cells])
            out.append((pending_text, rows))
            pending_text = ""
        else:
            pending_text = part
    return out


def find_annex1_block(blocks: list[tuple[str, list[list[str]]]], year: int) -> list[list[str]] | None:
    """Đi bộ qua các khối (văn bản, bảng) để tìm bảng Phụ lục Số 1 năm year.

    Nhãn 'PHỤ LỤC SỐ 1' (không phải 1a/1b/2/...) bật cờ; nhãn phụ lục khác tắt
    cờ; bảng cần tìm là bảng đầu tiên mà đoạn văn bản ngay trước nó chứa tiêu đề
    Phụ lục 1 khi cờ còn bật. Một số bản gõ chèn bảng định dạng nhỏ giữa nhãn và
    bảng (QĐ 1052 trên luatvietnam), nên không thể yêu cầu nhãn+tiêu đề trong
    cùng một đoạn.

    So khớp bằng ASCII đã bỏ dấu (norm_ascii) vì các bản gõ đánh vần 'nghèo'
    không thống nhất ('NGHÈO' / 'NGHỀO' — dấu huyền đặt trên e hay ê).
    """
    title = f"tonghopsolieuhongheohocanngheocanuocnam{year}"
    pending = False
    for text_before, rows in blocks:
        seg = desp(norm_ascii(re.sub(r"[.,;:]", "", re.sub(r"<[^>]+>", " ", text_before))))
        pending_at = 0  # vị trí nhãn trong ĐOẠN NÀY (đoạn mới thì tìm từ đầu)
        for m in re.finditer(r"phulucso(\d+)([ab])?", seg):
            if m.group(1) == "1" and not m.group(2):
                pending = True
                pending_at = m.end()
            else:
                pending = False
        if pending and seg.find(title, pending_at) != -1:
            return rows
    return None


def parse_annex1(path: Path, year: int, keys_desp: dict[str, tuple[str, str, str]]) -> dict:
    """Bóc bảng Phụ lục Số 1 của một file HTML -> dict tỉnh + dòng Cả nước."""
    html = path.read_text(encoding="utf-8", errors="strict")
    blocks = html_table_blocks(html)
    grid = find_annex1_block(blocks, year)
    if grid is None:
        raise SystemExit(f"LỖI: {path.name}: không tìm thấy bảng Phụ lục Số 1 năm {year}")

    # kiểm tra tiêu đề bảng (ASCII bỏ dấu — bản gõ có thể lệch dấu thanh)
    header = desp(norm_ascii(" ".join(grid[0])))
    if "tinh/thanhpho" not in header:
        raise SystemExit(f"LỖI: {path.name}: dòng tiêu đề không có 'TỈNH/THÀNH PHỐ': {grid[0]}")

    provinces: dict[int, dict] = {}
    national: dict | None = None
    n_regions = 0
    for r in grid[1:]:
        if len(r) < 5:
            continue
        first = r[0]
        name = r[1] if len(r) > 1 else ""
        k = norm_ascii(name)
        kd = desp(k)
        if re.fullmatch(r"[IVX]+", first) and (kd in REGION_KEYS or first in {"I", "II", "III", "IV", "V", "VI", "VII"}):
            n_regions += 1
            continue
        if kd == "canuoc":
            vals = [num(c) for c in r[2:7]]
            if any(pd.isna(v) for v in vals):
                raise SystemExit(f"LỖI: {path.name}: dòng Cả nước thiếu số: {r}")
            national = dict(zip(("tong_ho", "ho_ngheo", "tl_ngheo", "ho_can", "tl_can"), vals))
            continue
        if re.fullmatch(r"\d{1,2}", first):
            stt = int(first)
            vals = [num(c) for c in r[2:7]]
            if any(pd.isna(v) for v in vals):
                raise SystemExit(f"LỖI: {path.name}: dòng {stt} {name!r} thiếu số: {r}")
            if stt in provinces:
                raise SystemExit(f"LỖI: {path.name}: STT {stt} xuất hiện 2 lần")
            if kd not in keys_desp:
                raise SystemExit(f"LỖI: {path.name}: tên không khớp crosswalk: {name!r} (key={k!r})")
            code, ascii_name, vi_name = keys_desp[kd]
            provinces[stt] = {
                "name_raw": name,
                **dict(zip(("tong_ho", "ho_ngheo", "tl_ngheo", "ho_can", "tl_can"), vals)),
                "code": code,
                "ascii": ascii_name,
                "vi": vi_name,
            }

    if national is None:
        raise SystemExit(f"LỖI: {path.name}: không thấy dòng 'Cả nước'")
    if sorted(provinces) != list(range(1, 64)):
        bad = [i for i in range(1, 64) if i not in provinces]
        raise SystemExit(f"LỖI: {path.name}: STT thiếu/lỗi: {bad} (có {len(provinces)} tỉnh)")
    return {"file": path.name, "provinces": provinces, "national": national, "regions": n_regions}


def check_arithmetic(src: dict, year: int) -> None:
    """Tỷ lệ % trong bảng = số hộ / tổng hộ × 100 (làm tròn 2 chữ số)?"""
    for stt, p in sorted(src["provinces"].items()):
        for cnt, tl, label in (("ho_ngheo", "tl_ngheo", "nghèo"), ("ho_can", "tl_can", "cận nghèo")):
            expect = round(p[cnt] / p["tong_ho"] * 100, 2)
            if abs(expect - p[tl]) > 0.0051:
                raise SystemExit(
                    f"LỖI: {src['file']} năm {year}: STT {stt} {p['name_raw']!r} {label}: "
                    f"bảng ghi {p[tl]} nhưng tính từ {p[cnt]}/{p['tong_ho']} là {expect}"
                )


def check_totals(src: dict, year: int) -> None:
    """Tổng 63 tỉnh từng cột = dòng Cả nước; tỷ lệ cả nước tính lại khớp; khớp số công bố."""
    n = src["national"]
    for col in ("tong_ho", "ho_ngheo", "ho_can"):
        s = sum(p[col] for p in src["provinces"].values())
        if abs(s - n[col]) > 0.5:
            raise SystemExit(f"LỖI: {src['file']} năm {year}: tổng 63 tỉnh cột {col} = {s} ≠ Cả nước {n[col]}")
    for cnt, tl in (("ho_ngheo", "tl_ngheo"), ("ho_can", "tl_can")):
        expect = round(n[cnt] / n["tong_ho"] * 100, 2)
        if abs(expect - n[tl]) > 0.0051:
            raise SystemExit(f"LỖI: {src['file']} năm {year}: tỷ lệ Cả nước {n[tl]} ≠ tính lại {expect}")
    exp_ho, exp_tl = NATIONAL_EXPECTED[year]
    if abs(n["ho_ngheo"] - exp_ho) > 0.5 or abs(n["tl_ngheo"] - exp_tl) > 0.0051:
        raise SystemExit(
            f"LỖI: {src['file']} năm {year}: Cả nước {n['ho_ngheo']}/{n['tl_ngheo']} ≠ "
            f"số công bố {exp_ho}/{exp_tl}"
        )


def fingerprint(src: dict) -> dict[int, tuple]:
    """Dấu vân tay từng STT để so hai bản gõ."""
    return {
        stt: (
            desp(norm_ascii(p["name_raw"])),
            p["tong_ho"],
            p["ho_ngheo"],
            p["tl_ngheo"],
            p["ho_can"],
            p["tl_can"],
        )
        for stt, p in src["provinces"].items()
    }


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    cw = pd.read_csv(CROSSWALK, encoding="utf-8-sig")
    assert cw["province_vi"].map(norm_ascii).is_unique and len(cw) == 63, "crosswalk không phải 63 tỉnh duy nhất"
    keys_desp = {
        desp(norm_ascii(r["province_vi"])): (str(r["province_code"]).strip(), r["province_ascii"], r["province_vi"])
        for _, r in cw.iterrows()
    }
    assert len(keys_desp) == 63, "khóa tên tỉnh de-spaced trùng nhau trong crosswalk"

    papi = pd.read_csv(PAPI)
    papi_by_ascii = papi[["province_ascii", "province_code"]].drop_duplicates().set_index("province_ascii")["province_code"]
    assert papi_by_ascii.index.is_unique

    parsed: dict[int, list[dict]] = {}
    for year, files in SOURCES.items():
        srcs = [parse_annex1(RAW / fname, year, keys_desp) for fname, role in files]
        for src in srcs:
            check_arithmetic(src, year)
            check_totals(src, year)
            print(
                f"OK {src['file']} ({year}): 63 tỉnh, 6 vùng={src['regions']}, "
                f"Cả nước {src['national']['ho_ngheo']:.0f} hộ / {src['national']['tl_ngheo']:.2f}%"
            )
        if len(srcs) >= 2:
            fp0, fp_rest = fingerprint(srcs[0]), [fingerprint(s) for s in srcs[1:]]
            for j, fp in enumerate(fp_rest, start=1):
                diffs = [stt for stt in fp0 if fp0[stt] != fp.get(stt)]
                if diffs:
                    for stt in diffs[:10]:
                        print("  LỆCH:", stt, fp0[stt], "vs", fp.get(stt))
                    raise SystemExit(f"LỖI: hai bản gõ năm {year} lệch nhau ở STT {diffs}")
            print(f"OK năm {year}: {len(srcs)} bản gõ độc lập trùng khớp từng ô")
        parsed[year] = srcs

    rows = []
    for year, srcs in parsed.items():
        src = srcs[0]  # bản chính (các bản đã chứng minh trùng khớp)
        dec_no, dec_date = DECISIONS[year]
        for stt, p in sorted(src["provinces"].items()):
            rows.append({
                "province_code": p["code"],
                "province_ascii": p["ascii"],
                "province_vi": p["vi"],
                "year": year,
                "poverty_rate_pct": p["tl_ngheo"],
                "tong_so_ho_dan": int(p["tong_ho"]),
                "so_ho_ngheo": int(p["ho_ngheo"]),
                "so_ho_can_ngheo": int(p["ho_can"]),
                "ty_le_can_ngheo_pct": p["tl_can"],
                "decision_no": dec_no,
                "decision_date": dec_date,
                "source": f"molisa_{year}",
            })

    df = pd.DataFrame(rows).sort_values(["province_code", "year"]).reset_index(drop=True)

    # papi_province_code qua province_ascii (giống build_poverty_63.py)
    df["papi_province_code"] = df["province_ascii"].map(papi_by_ascii)
    if df["papi_province_code"].isna().any():
        bad = sorted(df.loc[df["papi_province_code"].isna(), "province_ascii"].unique())
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {bad}")

    # 6 cột đầu lặp lại đúng thứ tự schema chuẩn của external_poverty_63.csv
    df = df[
        [
            "province_code", "province_ascii", "province_vi", "year", "poverty_rate_pct",
            "papi_province_code", "tong_so_ho_dan", "so_ho_ngheo", "so_ho_can_ngheo",
            "ty_le_can_ngheo_pct", "decision_no", "decision_date", "source",
        ]
    ]

    assert df["province_ascii"].nunique() == 63
    assert sorted(df["year"].unique()) == [2017, 2018, 2019]
    assert len(df) == 189

    out_path = OUT / "external_molisa_poverty_63.csv"
    df.to_csv(out_path, index=False, na_rep="", encoding="utf-8")
    print(
        f"Đã ghi {out_path.name}: {df['province_ascii'].nunique()} tỉnh × "
        f"{df['year'].nunique()} năm = {len(df)} dòng; nguồn = {sorted(df['source'].unique())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
