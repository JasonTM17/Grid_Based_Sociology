"""Build data/processed/external_worldbank_vnm.csv from World Bank WDI API downloads.

Nguồn: World Bank World Development Indicators (WDI) API v2, quốc gia VNM.
Dữ liệu cấp QUỐC GIA (không theo tỉnh) — dùng làm bối cảnh vĩ mô cho báo cáo.
Giấy phép: CC BY 4.0.

URL tải mỗi chỉ số (trả ZIP, trong đó có CSV dữ liệu wide-format):
    https://api.worldbank.org/V2/country/VNM/indicator/<IND>?downloadformat=csv

Lưu ý: dạng inline `format=csv&per_page=2000` bị API trả lỗi XML
"Invalid format - The requested response format was not found" (đã thử 2026-11-07),
nên dùng `downloadformat=csv`.

Chạy từ thư mục gốc repo:
    python -E scripts/build_external_worldbank.py

Script chỉ dùng thư viện chuẩn (csv, hashlib, json, urllib) — không đòi pandas.
Không sửa file gốc trong data/raw/worldbank/; chỉ đọc và tạo lại PROVENANCE.md.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "worldbank"
OUT = ROOT / "data" / "processed" / "external_worldbank_vnm.csv"
PROVENANCE = RAW / "PROVENANCE.md"

DOWNLOAD_URL = "https://api.worldbank.org/V2/country/VNM/indicator/{ind}?downloadformat=csv"
JSON_URL = "https://api.worldbank.org/V2/country/VNM/indicator/{ind}?format=json&per_page=2000"
LICENSE_URL = "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets"
DOWNLOAD_DATE = "2026-11-07"

# Thứ tự yêu cầu trong đề bài: SH.XPD.CHEX.GD.ZS, NY.GDP.PCAP.CD,
# SP.URB.TOTL.IN.ZS, SH.MED.BEDS.ZS.
INDICATORS = [
    "SH.XPD.CHEX.GD.ZS",
    "NY.GDP.PCAP.CD",
    "SP.URB.TOTL.IN.ZS",
    "SH.MED.BEDS.ZS",
]
YEAR_MIN, YEAR_MAX = 2010, 2024
MISSING_MARKERS = {"", "..", "na", "n/a", "nan", "null", "-"}


def is_missing(s: str) -> bool:
    return s.strip().lower() in MISSING_MARKERS


def read_wide_csv(path: Path) -> tuple[str, str, dict[int, str]]:
    """Đọc 1 CSV wide của WDI. Trả về (indicator_code, indicator_name, {năm: giá trị chuỗi gốc})."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if r and any(c.strip() for c in r)]
    hdr_i = next(
        (i for i, r in enumerate(rows) if r[0].strip() == "Country Name"), None
    )
    if hdr_i is None:
        raise SystemExit(f"LOI: khong tim thay dong header trong {path}")
    hdr = [c.strip() for c in rows[hdr_i]]
    data_rows = rows[hdr_i + 1 :]
    if len(data_rows) != 1:
        raise SystemExit(
            f"LOI: {path} ky vong dung 1 dong du lieu (VNM), thay {len(data_rows)}"
        )
    row = data_rows[0]
    idx = {name: hdr.index(name) for name in ("Country Code", "Indicator Name", "Indicator Code")}
    country_code = row[idx["Country Code"]].strip()
    if country_code != "VNM":
        raise SystemExit(f"LOI: {path} khong phai du lieu VNM (thay {country_code})")
    indicator_code = row[idx["Indicator Code"]].strip()
    indicator_name = row[idx["Indicator Name"]].strip()
    values: dict[int, str] = {}
    for j, cell in enumerate(hdr):
        if not cell.isdigit():
            continue
        v = row[j].strip() if j < len(row) else ""
        if not is_missing(v):
            values[int(cell)] = v
    if indicator_code != path.stem:
        raise SystemExit(f"LOI: {path} ma chi so {indicator_code} khac ten file")
    return indicator_code, indicator_name, values


def cross_check_json(indicator_code: str, values: dict[int, str]) -> str:
    """Đối chiếu giá trị đã phân tích với JSON API (nguồn render độc lập cùng API)."""
    url = JSON_URL.format(ind=indicator_code)
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        records = payload[1]
    except Exception as exc:  # noqa: BLE001 — ghi nhận trung thực, không dừng build
        return f"KHONG_KIEM_TRA_DUOC ({type(exc).__name__}: {exc})"
    api = {
        int(r["date"]): r["value"]
        for r in records
        if r.get("countryiso3code") == "VNM" and r.get("value") is not None
    }
    checked, mismatch = 0, []
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        if year not in values and year not in api:
            continue
        if year in values and year in api:
            checked += 1
            if float(values[year]) != float(api[year]):
                mismatch.append(f"{year}: csv={values[year]} json={api[year]}")
        else:
            mismatch.append(
                f"{year}: chi co ben {'csv' if year in values else 'json'}"
            )
    if mismatch:
        return f"LECH ({checked} nam khop so): {'; '.join(mismatch[:8])}"
    return f"KHOP ({checked} nam 2010-2024 giong het JSON API)"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_provenance(
    summary: list[dict], checks: dict[str, str], last_updated: str
) -> None:
    files = sorted(
        p for p in RAW.iterdir() if p.is_file() and p.name != "PROVENANCE.md"
    )
    lines = [
        "# World Bank WDI — Việt Nam (VNM)",
        "",
        "## Nguồn",
        "- World Bank World Development Indicators (WDI), API v2, quốc gia VNM.",
        f"- URL tải mỗi chỉ số (đã dùng, hoạt động): `{DOWNLOAD_URL.replace('{ind}', '<MA_CHI_SO>')}`"
        " — API trả ZIP; CSV dữ liệu bên trong được tách ra cùng thư mục, đổi tên `<MA_CHI_SO>.csv`.",
        "- Lệnh mẫu ban đầu `format=csv&per_page=2000` (inline CSV) bị API từ chối ngày"
        f" {DOWNLOAD_DATE}: trả XML lỗi `Invalid format — The requested response format was not found`;"
        " đã chuyển sang `downloadformat=csv` như trên.",
        "- Các chỉ số tải: "
        + "; ".join(f"`{i['code']}` = {i['name']}" for i in summary)
        + ".",
        "- Phạm vi: cấp QUỐC GIA (VNM), không có chiều tỉnh — dùng làm bối cảnh vĩ mô,"
        " không nối theo tỉnh.",
        f"- Ngày tải: {DOWNLOAD_DATE}. Ngày cập nhật dữ liệu WDI ghi trong file (Last Updated Date): {last_updated}.",
        f"- Giấy phép: CC BY 4.0 — World Bank Terms of Use for Datasets, {LICENSE_URL}.",
        "",
        "## Xử lý",
        "- File `*.zip` là bản tải nguyên trạng; file `<MA_CHI_SO>.csv` là CSV dữ liệu"
        " tách từ ZIP (giữ nguyên nội dung, chỉ đổi tên). Hai file metadata khác trong ZIP"
        " (Metadata_Country, Metadata_Indicator) không tách ra; xem trong ZIP nếu cần.",
        f"- Chuẩn hóa: `data/processed/external_worldbank_vnm.csv` — dạng long"
        f" (indicator_code, indicator_name, year, value), lọc năm {YEAR_MIN}–{YEAR_MAX},"
        " bỏ hàng giá trị trống. Không nội suy, không bịa số liệu.",
        "- Script tạo lại file này mỗi lần chạy: `scripts/build_external_worldbank.py`"
        " (chạy từ thư mục gốc repo bằng `python -E scripts/build_external_worldbank.py`).",
        "",
        "## Kiểm tra chéo với JSON API (cùng nguồn, render khác định dạng)",
        "",
    ]
    for i in summary:
        lines.append(f"- `{i['code']}`: {checks[i['code']]}")
    lines += [
        "",
        "## Manifest (tên file — bytes — SHA-256)",
        "",
        "| Tên file | Bytes | SHA-256 |",
        "|---|---|---|",
    ]
    for p in files:
        lines.append(f"| {p.name} | {p.stat().st_size} | {sha256_of(p)} |")
    lines.append("")
    PROVENANCE.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not RAW.is_dir():
        raise SystemExit(f"LOI: khong ton tai {RAW}")
    out_rows: list[tuple[str, str, int, str]] = []
    summary: list[dict] = []
    checks: dict[str, str] = {}
    last_updated = "khong xac dinh"
    for ind in INDICATORS:
        path = RAW / f"{ind}.csv"
        if not path.is_file():
            raise SystemExit(f"LOI: thieu file {path}")
        # Lấy "Last Updated Date" từ 2 dòng đầu file gốc
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.reader(f):
                if len(r) >= 2 and r[0].strip() == "Last Updated Date":
                    last_updated = r[1].strip()
                    break
        code, name, values = read_wide_csv(path)
        kept = {y: v for y, v in values.items() if YEAR_MIN <= y <= YEAR_MAX}
        missing = [y for y in range(YEAR_MIN, YEAR_MAX + 1) if y not in kept]
        for y in sorted(kept):
            out_rows.append((code, name, y, kept[y]))
        full_years = sorted(values)
        summary.append(
            {
                "code": code,
                "name": name,
                "full_range": f"{full_years[0]}–{full_years[-1]}" if full_years else "trống",
                "n_kept": len(kept),
                "missing": missing,
            }
        )
        checks[code] = cross_check_json(code, values)

    out_rows.sort(key=lambda r: (r[0], r[2]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["indicator_code", "indicator_name", "year", "value"])
        w.writerows(out_rows)

    print(f"Xuat: {OUT} ({len(out_rows)} dong du lieu)")
    for i in summary:
        thieu = ", ".join(str(y) for y in i["missing"]) if i["missing"] else "khong"
        print(
            f"- {i['code']} ({i['name']}): du lieu goc {i['full_range']}; "
            f"{YEAR_MIN}-{YEAR_MAX} co {i['n_kept']} nam co gia tri; thieu nam: {thieu}"
        )
    for code in INDICATORS:
        print(f"- Kiem tra cheo {code}: {checks[code]}")
    write_provenance(summary, checks, last_updated)
    print(f"Da ghi: {PROVENANCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
