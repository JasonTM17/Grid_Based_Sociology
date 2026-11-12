"""Bổ sung PCI 2011, 2023, 2024 từ pcivietnam.vn vào panel PCI 63 tỉnh.

Nguồn tải ngày 2026-11-07 (file gốc giữ nguyên trong data/raw/pci/, không sửa):
  - Indicator_PCI2011_EN.xls                          — workbook PCI 2011 (xls, sheet 'Summary')
  - Appendix_1_Table_Indicator_PCI2023_EN_web.xlsx    — workbook PCI 2023 (KHÔNG có cột điểm tổng)
  - Appendix_1_Table_Indicator_PCI2023_VN_web.xlsx    — workbook PCI 2023 bản VN (tương tự)
  - Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx   — workbook PCI 2024 (có 'The Weighted PCI Score')
  - Du_lieu_PCI_2025.xlsx                             — PCI 2025 (34 tỉnh sau sáp nhập; KHÔNG dùng,
                                                        ngoài phạm vi 2011-2024, chỉ lưu làm bằng chứng)
  - pci_ranking_page_{2011,2023,2024}.html            — trang /en/pci-ranking?year=<y> (bằng chứng
                                                        + nguồn điểm tổng PCI 2023, vì workbook 2023
                                                        chỉ có 10 sub-index, không có điểm tổng)

Điểm tổng từng năm lấy từ:
  2011: workbook 'Summary', cột 'PCI 2011' (cột 21, Excel 1-based), dòng 2-64 (63 tỉnh).
  2023: trang xếp hạng chính thức /en/pci-ranking?year=2023 (bảng Province | PCI Index | Ranking);
        workbook 2023 không có cột điểm tổng — đã kiểm tra cả bản EN lẫn bản VN.
  2024: workbook 'Summary', cột 'The Weighted PCI Score', dòng 2-64 (63 tỉnh; dòng 66 là dòng
        'Yen Bai' trùng lặp với điểm 0 — artifact, bỏ qua).

Kiểm chứng chéo in ra lúc chạy:
  - workbook 2024 (làm tròn 2 chữ số) so với trang xếp hạng 2024;
  - workbook 2011 so với trang xếp hạng 2011;
  - tập 63 tên tỉnh của từng nguồn phải khớp nhau sau chuẩn hóa.

Đầu ra:
  data/processed/external_pci_63_full.csv — 63 tỉnh × 2011-2024 (882 dòng),
  cột: papi_province_code, province_code, province_ascii, province_vi, year,
       pci_weighted_score, source ('mendeley_extract' | 'pci_vietnam_download_<năm>').
  Dòng nào nguồn không công bố điểm (N/A) thì pci_weighted_score để trống — KHÔNG nội suy.

Script chỉ đọc file gốc và ghi file mới; chạy từ thư mục gốc repo: python -E scripts/build_pci_full.py
"""

from __future__ import annotations

import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import pandas as pd
import xlrd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "pci"
OUT = ROOT / "data" / "processed"
BASE = OUT / "external_pci_63.csv"
PAPI = OUT / "papi_panel_63_2011_2024.csv"
XWALK = (
    ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
)

F_XLS_2011 = "Indicator_PCI2011_EN.xls"
F_XLSX_2023_EN = "Appendix_1_Table_Indicator_PCI2023_EN_web.xlsx"
F_XLSX_2023_VN = "Appendix_1_Table_Indicator_PCI2023_VN_web.xlsx"
F_XLSX_2024 = "Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx"
F_XLSX_2025 = "Du_lieu_PCI_2025.xlsx"


def norm(name: str) -> str:
    """Chuẩn hóa tên tỉnh: bỏ dấu, bỏ ký tự không phải chữ (giống extract của gói replication)."""
    s = unicodedata.normalize("NFD", str(name)).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z]", "", s)


# Bí danh tên hiển thị khác chuẩn (theo extract_indicators.py của gói replication + biến thể
# EN thực tế trong workbook 2024 và trang xếp hạng: BRVT, HCMC, TT-Hue).
ALIASES = {
    "tphochiminh": "79", "hochiminh": "79", "tphcm": "79", "hcmc": "79",
    "thuathienhue": "46", "hue": "46", "tthue": "46",
    "bariavungtau": "77", "brvt": "77",
    "daklak": "66", "daknong": "67", "hoabinh": "17", "thanhhoa": "38", "khanhhoa": "56",
    "baccan": "06",  # 'Bắc Cạn' — chính tả cũ trong workbook 2011
    "tphanoi": "01", "hanoi": "01", "tpdanang": "48", "tphaiphong": "31", "tpcantho": "92",
}


def load_name2code() -> dict[str, str]:
    """Tên đã chuẩn hóa -> province_code (dạng '01'..'92' theo crosswalk)."""
    cw = pd.read_csv(XWALK, dtype=str, encoding="utf-8-sig")
    cw["province_code"] = cw["province_code"].str.strip()
    m: dict[str, str] = {}
    for _, r in cw.iterrows():
        m[norm(r["province_vi"])] = r["province_code"]
        m[norm(r["province_ascii"])] = r["province_code"]
    m.update(ALIASES)
    codes = set(cw["province_code"])
    bad = {v for v in ALIASES.values()} - codes
    if bad:
        raise SystemExit(f"LỖI: bí danh trỏ tới mã không có trong crosswalk: {sorted(bad)}")
    return m


def code_of(name: str, name2code: dict[str, str]) -> str:
    key = norm(name)
    code = name2code.get(key)
    if code is None:
        raise SystemExit(f"LỖI: không suy ra mã tỉnh từ tên nguồn: {name!r} (key={key!r})")
    return code


def as_score(x, where: str) -> float:
    if x is None or (isinstance(x, str) and x.strip() in ("", "N/A", "n/a", "NA")):
        raise SystemExit(f"LỖI: điểm tổng trống tại {where} — cần rà thủ công, không tự điền")
    try:
        v = float(str(x).strip())
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"LỖI: không đọc được số tại {where}: {x!r}") from exc
    if not 0.0 < v <= 100.0:
        raise SystemExit(f"LỖI: điểm ngoài thang (0,100] tại {where}: {v!r}")
    return v


# ---------------------------------------------------------------- 2011 (xls)
def parse_2011() -> tuple[list[tuple[str, float]], str]:
    """Summary 2011 xếp dòng theo rank sub-index đầu tiên; mỗi chỉ số là cặp (tên tỉnh, điểm).

    Cặp 'PCI 2011' (điểm tổng) nằm ở cột 20-21 (Excel 1-based): cột 20 = tên tỉnh đứng đầu
    theo PCI tổng, cột 21 = điểm. Ta lấy đúng cặp này (không lấy cột 2 'Province' vì đó là
    tỉnh theo rank Entry Costs)."""
    ws = xlrd.open_workbook(RAW / F_XLS_2011).sheet_by_name("Summary")
    if ws.cell_value(0, 20) != "PCI 2011":
        raise SystemExit(f"LỖI: cột 21 của {F_XLS_2011}!Summary không phải 'PCI 2011'")
    recs = []
    for i in range(1, 64):  # Excel dòng 2-64 = 63 tỉnh
        name = str(ws.cell_value(i, 19)).strip()
        recs.append((name, as_score(ws.cell_value(i, 20), f"{F_XLS_2011} dòng {i + 1}")))
    if len(recs) != 63:
        raise SystemExit(f"LỖI: 2011 đọc được {len(recs)} dòng thay vì 63")
    note = ("bảng xếp theo rank từng sub-index; điểm tổng lấy từ cặp (tỉnh, điểm) "
            "cột U-V ('PCI 2011'), không phải cột B-C")
    return recs, note


# ------------------------------------------------- trang xếp hạng (2023 + kiểm chứng)
def parse_ranking_html(path: Path, year: str) -> list[tuple[str, float | None, str]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    sel = re.findall(rf'<option value="{year}"\s+selected', raw)
    if not sel:
        raise SystemExit(f"LỖI: {path.name} không phải trang xếp hạng năm {year}")
    body = raw.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    recs: list[tuple[str, float | None, str]] = []
    for tr in body.split("<tr>")[1:]:
        m_name = re.search(r'class="title_province"[^>]*>([^<]+)</a>', tr)
        if not m_name:
            continue
        tds = re.findall(r"<td>(.*?)</td>", tr, flags=re.S)
        if len(tds) < 3:
            raise SystemExit(f"LỖI: dòng bảng không đủ 3 ô trong {path.name}: {tr[:120]!r}")
        name = m_name.group(1).strip()
        val_txt = re.sub(r"<[^>]+>", "", tds[1]).strip()
        rank = re.sub(r"<[^>]+>", "", tds[2]).strip()
        score = None if val_txt in ("", "N/A") else as_score(val_txt, f"{path.name} {name}")
        recs.append((name, score, rank))
    if len(recs) != 63:
        raise SystemExit(f"LỖI: {path.name} đọc được {len(recs)} tỉnh thay vì 63")
    return recs


# ---------------------------------------------------------------- 2024 (xlsx)
def parse_2024() -> tuple[list[tuple[str, float | None]], str]:
    wb = openpyxl.load_workbook(RAW / F_XLSX_2024, read_only=True, data_only=True)
    ws = wb["Summary"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = [str(v) if v is not None else "" for v in rows[0]]
    if "The Weighted PCI Score" not in hdr:
        raise SystemExit(f"LỖI: {F_XLSX_2024}!Summary thiếu cột 'The Weighted PCI Score'")
    i_w = hdr.index("The Weighted PCI Score")
    if rows[1][0] is None or str(rows[1][0]).strip() != "An Giang":
        raise SystemExit(f"LỖI: {F_XLSX_2024} dòng 2 không phải 'An Giang' — cấu trúc khác dự kiến")
    recs = [(str(rows[i][0]).strip(), rows[i][i_w]) for i in range(1, 64)]  # Excel dòng 2-64
    # Dòng 66 là 'Yen Bai' trùng lặp với điểm 0 — artifact phía cuối bảng, bỏ qua nhưng ghi nhận.
    artifact = rows[65]
    note = ""
    if artifact[0] is not None and str(artifact[0]).strip() == "Yen Bai":
        note = f"dòng 66 'Yen Bai' điểm {artifact[1]!r} là dòng trùng lặp cuối bảng — đã bỏ qua"
    return recs, note


def check_code_set(name2code: dict[str, str], label_a: str, names_a: set[str],
                   label_b: str, names_b: set[str]) -> None:
    """So tập MÃ tỉnh suy ra từ tên nguồn (hai nguồn cùng năm phải cho cùng 63 mã)."""
    ca = {code_of(n, name2code) for n in names_a}
    cb = {code_of(n, name2code) for n in names_b}
    if ca != cb:
        raise SystemExit(
            f"LỖI: tập mã tỉnh khác nhau giữa {label_a} và {label_b}: "
            f"{sorted(ca ^ cb)}"
        )


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PROVENANCE_TEXT = """# PROVENANCE — PCI (pcivietnam.vn) — bổ sung năm 2011, 2023, 2024

- **Nguồn:** Chỉ số Năng lực cạnh tranh cấp tỉnh (PCI) — VCCI/USAID, công khai tại
  <https://pcivietnam.vn>. Trang dữ liệu: `/du-lieu-pci` (VN) | `/en/pci-data` (EN);
  trang xếp hạng: `/en/pci-ranking?year=<y>`. Chính sách trích dẫn dữ liệu của trang:
  <https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html> (ghi nguồn
  VCCI — USAID khi sử dụng lại).
- **Ngày tải:** 2026-11-07 (curl, không đăng nhập, không vượt cơ chế bảo vệ nào).
- **Script chuyển đổi:** `scripts/build_pci_full.py` (chạy từ thư mục gốc repo:
  `python -E scripts/build_pci_full.py`; chỉ đọc file gốc trong thư mục này, ghi
  `data/processed/external_pci_63_full.csv`).

## Điểm tổng hợp (weighted score) từng năm lấy từ đâu

| Năm | Nguồn điểm tổng | Ghi chú |
|---|---|---|
| 2011 | `Indicator_PCI2011_EN.xls`, sheet `Summary`, cặp cột U–V ("PCI 2011") | Bảng xếp theo rank từng sub-index; cột B là tỉnh theo rank Entry Costs, KHÔNG phải cặp với điểm tổng |
| 2012–2022 | extract Mendeley (Le et al., DOI 10.17632/wbk42j9wc8.1) — đã có trong `data/processed/external_pci_63.csv` | `source = mendeley_extract` |
| 2023 | Trang xếp hạng chính thức `/en/pci-ranking?year=2023` (file `pci_ranking_page_2023.html`) | Workbook 2023 (cả bản EN lẫn VN) KHÔNG có cột điểm tổng — chỉ 10 sub-index + vùng |
| 2024 | `Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx`, sheet `Summary`, cột "The Weighted PCI Score" | Khớp trang xếp hạng 2024 (chênh lệch ≤ 0,005 = làm tròn 2 chữ số) |

## Phủ dữ liệu và nguyên nhân ô trống (KHÔNG nội suy)

- 2011–2022: đủ 63 tỉnh/năm.
- 2023: chỉ **Top 30** có điểm tổng. Từ PCI 2022, báo cáo PCI đổi cách trình bày
  "từ toàn bộ cả nước sang Top 30" (Báo cáo PCI & PGI 2023, tr. 24 và 43; file
  `VN-Bao-cao-dai-PCI-2023_VN.pdf`). 33 tỉnh còn lại có tính điểm nhưng không được
  công bố trong báo cáo, workbook hay trang xếp hạng — để trống trong CSV.
- 2024: workbook chỉ chứa điểm tổng của **Top 30**, 33 dòng tỉnh để trống trong file
  gốc (Báo cáo PCI 2024 tr. 18: "công bố danh sách 30 tỉnh, thành phố dẫn đầu").
  Khớp đúng 30 giá trị với trang xếp hạng 2024 (chênh ≤ 0,005).

## Kiểm chứng chéo đã chạy (in trong log của script)

1. 2011 workbook vs trang xếp hạng 2011: 61/63 khớp tuyệt đối; 2 lệch là cặp
   **Bắc Giang / Bắc Cạn bị hoán tên trên trang xếp hạng hiện tại**.Workbook:
   Bắc Giang 60,79 (hạng 23), Bắc Cạn 52,71 (hạng 60) — được Báo cáo PCI 2014
   (`Bao_cao_PCI_2014_EN.pdf`, tr. 37–38, hồ sơ "BẮC KẠN 2011 52,71 60" và
   "BẮC GIANG 2011 60,79 23") xác nhận. CSV lấy theo workbook.
2. 2023 trang xếp hạng vs Báo cáo PCI & PGI 2023 (tr. 45–46, Hình 1.4 và đoạn văn):
   khớp từng giá trị (Quảng Ninh 71,25 hạng 1 … Thanh Hóa 66,79 hạng 30).
3. 2024 workbook vs trang xếp hạng 2024: 30/30 cặp khớp (chênh lệch ≤ 0,005).
4. Tập 63 mã tỉnh suy ra từ tên nguồn phải khớp giữa các nguồn cùng năm
   (workbook ↔ trang xếp hạng) sau chuẩn hóa tên (bỏ dấu + bí danh).

## Lỗi dữ liệu đã phát hiện ở nguồn (ghi nhận, không sửa file gốc)

- Workbook 2024, sheet Summary dòng 66: dòng "Yen Bai" trùng lặp với điểm 0
  (artifact cuối bảng) — bỏ qua khi parse.
- Workbook 2023 EN, dòng 66: "Lang Son" trùng lặp; bản VN dòng 66: "Yên Bái"
  trùng lặp; sau đó là Min/Median/Max (VN: "Thấp nhất"/"Trung vị"/"Cao nhất") — bỏ qua.
- Trang xếp hạng 2011: hoán tên Bắc Giang ↔ Bắc Cạn (xem mục kiểm chứng chéo).

## Ghi chú khác

- `Du_lieu_PCI_2025.xlsx` (PCI 2025, công bố 2026) KHÔNG dùng cho panel: cấu trúc mới
  sau sáp nhập 34 tỉnh, 9 chỉ số thành phần, không có cột điểm tổng — chỉ lưu làm bằng chứng.
- pandas/openpyxl có sẵn; `xlrd` 2.0.2 và `pypdf` 6.18.0 được cài vào user site-packages
  để đọc `.xls` (2011) và trích PDF kiểm chứng.
- Console Windows: script ép stdout/stderr UTF-8 để in được chữ Việt.

## Manifest file gốc (tên — bytes — SHA-256)

| File | Bytes | SHA-256 |
|---|---|---|
"""


def write_provenance() -> None:
    lines = [PROVENANCE_TEXT]
    for p in sorted(RAW.iterdir()):
        if p.is_file() and p.name != "PROVENANCE.md":
            lines.append(f"| `{p.name}` | {p.stat().st_size} | `{sha256_of(p)}` |\n")
    (RAW / "PROVENANCE.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    name2code = load_name2code()

    # ---- 2011
    rec_2011, note_2011 = parse_2011()
    names_2011 = {n for n, _ in rec_2011}
    rank_2011 = parse_ranking_html(RAW / "pci_ranking_page_2011.html", "2011")
    names_rank_2011 = {n for n, _, _ in rank_2011}
    check_code_set(name2code, F_XLS_2011, names_2011, "ranking 2011", names_rank_2011)
    # Kiểm chứng chéo điểm 2011: workbook (nguồn chính) vs trang xếp hạng.
    # Đã biết trang xếp hạng hiện tại HOÁN TÊN cặp Bắc Giang/Bắc Cạn (workbook: Bắc Giang
    # 60,79 hạng 23, Bắc Cạn 52,71 hạng 60; Báo cáo PCI 2014 chính thức trang 37-38 xác
    # nhận workbook: 'BẮC KẠN ... 2011 52,71 60', 'BẮC GIANG ... 2011 60,79 23'). Nếu bộ
    # mã lệch khác cặp này thì dừng để rà thủ công.
    rank_map_2011 = {code_of(n, name2code): s for n, s, _ in rank_2011}
    diffs_2011, mismatch_2011 = [], []
    for n, s in rec_2011:
        c = code_of(n, name2code)
        p = rank_map_2011.get(c)
        if p is None:
            continue
        if abs(p - s) <= 0.005:
            diffs_2011.append(abs(p - s))
        else:
            mismatch_2011.append(n)
    expected_swap = {norm("Bắc Giang"), norm("Bắc Cạn")}
    got_swap = {norm(n) for n in mismatch_2011}
    if got_swap != expected_swap:
        raise SystemExit(
            f"LỖI: 2011 lệch workbook vs trang xếp hạng ngoài cặp Bắc Giang/Bắc Cạn đã biết: "
            f"{sorted(mismatch_2011)}"
        )
    print(f"Kiểm chứng 2011 workbook vs trang xếp hạng: {len(diffs_2011)}/63 cặp khớp "
          f"(chênh lệch lớn nhất = {max(diffs_2011):.4f}); 2 lệch đã biết là cặp hoán tên "
          f"Bắc Giang/Bắc Cạn trên trang xếp hạng — lấy theo workbook (khớp Báo cáo PCI 2014)")
    print(f"2011 workbook: {note_2011}")

    # ---- 2023 (điểm tổng từ trang xếp hạng — workbook không có cột điểm tổng)
    rank_2023 = parse_ranking_html(RAW / "pci_ranking_page_2023.html", "2023")
    # Xác nhận workbook 2023 (EN và VN) cùng tập 63 tỉnh, và đúng là không có cột điểm tổng
    for f in (F_XLSX_2023_EN, F_XLSX_2023_VN):
        wb = openpyxl.load_workbook(RAW / f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        hdr = [str(v) if v is not None else "" for v in rows[0]]
        if any("weighted" in h.lower() or "chỉ số pci" in h.lower() for h in hdr):
            raise SystemExit(f"LỖI: {f} lại có cột điểm tổng — cần rà lại cách parse 2023")
        # Excel dòng 2-64 = 63 tỉnh; đuôi bảng (dòng 65+) chứa dòng trống, 1 dòng tỉnh
        # trùng lặp (EN: 'Lang Son', VN: 'Yên Bái') và Min/Median/Max (VN: 'Thấp nhất',
        # 'Trung vị', 'Cao nhất') — bỏ hẳn, không dùng.
        wb_names = {str(rows[i][0]).strip() for i in range(1, 64) if rows[i][0]}
        check_code_set(name2code, f, wb_names, "ranking 2023", {n for n, _, _ in rank_2023})
    scored_2023 = [(n, s) for n, s, _ in rank_2023 if s is not None]
    na_2023 = [n for n, s, _ in rank_2023 if s is None]
    print(f"2023 trang xếp hạng: {len(scored_2023)} tỉnh có điểm tổng (Top 30), "
          f"{len(na_2023)} tỉnh không công bố (từ PCI 2022 báo cáo chỉ công bố Top 30 — "
          f"trang {RAW.name} VN-Bao-cao-dai-PCI-2023_VN.pdf tr.24, 43): {sorted(na_2023)}")

    # ---- 2024
    rec_2024, artifact_note = parse_2024()
    names_2024 = {n for n, _ in rec_2024}
    rank_2024 = parse_ranking_html(RAW / "pci_ranking_page_2024.html", "2024")
    check_code_set(name2code, F_XLSX_2024, names_2024, "ranking 2024", {n for n, _, _ in rank_2024})
    rank_map_2024 = {code_of(n, name2code): s for n, s, _ in rank_2024}
    diffs_2024 = []
    for n, s in rec_2024:
        if s is None:
            continue
        c = code_of(n, name2code)
        if rank_map_2024.get(c) is not None:
            diffs_2024.append(abs(rank_map_2024[c] - float(s)))
    print(f"Kiểm chứng 2024 workbook vs trang xếp hạng: {len(diffs_2024)} cặp, "
          f"chênh lệch lớn nhất = {max(diffs_2024):.4f}")
    blanks_2024 = [n for n, s in rec_2024 if s is None]
    print(f"2024 workbook: {63 - len(blanks_2024)} tỉnh có điểm tổng (Top 30), "
          f"{len(blanks_2024)} tỉnh để trống trong file gốc (báo cáo cũng chỉ công bố Top 30, "
          f"trang {RAW.name} Bao_cao_PCI_2024_VN.pdf tr.18): {sorted(blanks_2024)}")
    if artifact_note:
        print(f"2024 workbook: {artifact_note}")

    # ---- Base (2012-2022 từ extract Mendeley)
    base = pd.read_csv(BASE, dtype={"province_code": str, "papi_province_code": str})
    base["source"] = "mendeley_extract"

    # Khóa hiển thị (code, ascii, vi) lấy ngay từ base để tránh lệch chữ với các file hiện có
    keys = base[["province_code", "province_ascii", "province_vi"]].drop_duplicates()
    if len(keys) != 63:
        raise SystemExit(f"LỖI: base có {len(keys)} bộ khóa tỉnh thay vì 63")
    # crosswalk code '01' -> code dạng base '1' để nối
    disp_of_xw = {str(int(c)): (c, a, v) for c, a, v in
                  zip(keys["province_code"], keys["province_ascii"], keys["province_vi"])}

    def new_year_rows(year: int, scored: list[tuple[str, float | None]], source: str) -> pd.DataFrame:
        by_code: dict[str, float | None] = {}
        for n, s in scored:
            c = str(int(code_of(n, name2code)))  # '01' -> '1' khớp quy ước của base
            if c in by_code:
                raise SystemExit(f"LỖI: năm {year} trùng mã tỉnh {c} sau chuẩn hóa tên")
            by_code[c] = s
        missing = set(disp_of_xw) - set(by_code)
        if missing:
            raise SystemExit(f"LỖI: năm {year} thiếu mã tỉnh {sorted(missing)}")
        rows = []
        for c_str, (_c, ascii_, vi) in disp_of_xw.items():
            rows.append({
                "province_code": c_str, "province_ascii": ascii_, "province_vi": vi,
                "year": year, "pci_weighted_score": by_code[c_str], "source": source,
            })
        return pd.DataFrame(rows)

    extra = pd.concat([
        new_year_rows(2011, rec_2011, "pci_vietnam_download_2011"),
        new_year_rows(2023, [(n, s) for n, s, _ in rank_2023], "pci_vietnam_download_2023"),
        new_year_rows(2024, rec_2024, "pci_vietnam_download_2024"),
    ], ignore_index=True)

    full = pd.concat([base[["province_code", "province_ascii", "province_vi", "year",
                            "pci_weighted_score", "source"]], extra], ignore_index=True)

    # gán papi_province_code qua province_ascii (khóa chính của panel PAPI)
    papi = pd.read_csv(PAPI, dtype={"province_code": str})
    papi_map = papi[["province_code", "province_ascii"]].drop_duplicates()
    if papi_map["province_ascii"].duplicated().any():
        raise SystemExit("LỖI: province_ascii trong panel PAPI không duy nhất")
    full = full.merge(
        papi_map.rename(columns={"province_code": "papi_province_code"}),
        on="province_ascii", how="left", validate="many_to_one",
    )
    unmatched = sorted(full.loc[full["papi_province_code"].isna(), "province_ascii"].unique())
    if unmatched:
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {unmatched}")

    full["year"] = full["year"].astype(int)
    full["pci_weighted_score"] = pd.to_numeric(full["pci_weighted_score"], errors="coerce")
    full = full.sort_values(["province_code", "year"], key=lambda s: pd.to_numeric(s, errors="coerce"))
    full = full[["papi_province_code", "province_code", "province_ascii", "province_vi",
                 "year", "pci_weighted_score", "source"]].reset_index(drop=True)
    full.to_csv(OUT / "external_pci_63_full.csv", index=False)

    # ---- báo cáo phủ
    print(f"\nĐã ghi {OUT / 'external_pci_63_full.csv'}: {len(full)} dòng, "
          f"{full['province_code'].nunique()} tỉnh, năm {full['year'].min()}-{full['year'].max()}")
    per_year = full.groupby("year")["pci_weighted_score"].agg(["count", "size"])
    for y, r in per_year.iterrows():
        miss = int(r["size"] - r["count"])
        print(f"  {y}: {int(r['count'])}/63 tỉnh có điểm" + (f" (thiếu {miss})" if miss else ""))
    total_missing = int(full["pci_weighted_score"].isna().sum())
    print(f"Tổng ô điểm trống: {total_missing} (2023: {len(na_2023)} tỉnh, 2024: "
          f"{len(blanks_2024)} tỉnh — nhà xuất bản chỉ công bố Top 30 từ PCI 2022 trở đi; "
          f"giữ trống, không nội suy)")

    write_provenance()
    return 0


if __name__ == "__main__":
    sys.exit(main())
