"""Provenance + trích xuất cho truy tìm nghèo cấp tỉnh VN (World Bank / UNDP).

Chốt câu hỏi: "World Bank / UNDP có công bố nghèo cấp tỉnh Việt Nam dạng open
data không?" — ngày truy tìm 2026-11-08.

Kết quả truy tìm (bằng chứng gốc lưu trong data/raw/, KHÔNG TIN CẬY cho tới khi
được kiểm chứng ở giai đoạn tích hợp):

1. World Bank API v2: nghèo cho VNM chỉ cấp QUỐC GIA; dimension "country"
   không có admin1 (VNM-HAN -> lỗi 120 "Invalid value"); nguồn 38 "Subnational
   Poverty" không có thực thể admin1 nào của VN (chỉ 18 dòng quốc gia null).
2. PIP API: reporting_level="national"; các tham số coverage_area=urban/rural
   trả về payload national giống hệt.
3. World Bank Data Catalog — SPID (dataset 0064796, CC BY 4.0): TẢI ĐƯỢC,
   admin1 của VN = 6 vùng hợp tỉnh (GAULx_1..6), KHÔNG phải 63 tỉnh.
4. UNDP: báo cáo nghèo đa chiều cấp tỉnh của UNDP VN chỉ có PDF (curl bị 403);
   UNDP/OPHI Global MPI subnational (HDX, CC0): 6 vùng MICS 2020-2021.

Script làm: (a) trích xuất các dòng VN thành CSV nhỏ kèm provenance;
(b) sinh bảng manifest tên—bytes—SHA-256 (hashlib); (c) viết PROVENANCE.md cho
data/raw/worldbank/provincial_poverty_probe/ và data/raw/undp/.

Chạy từ thư mục gốc repo:
    python -E scripts/wb_undp_poverty_probe.py

Không merge vào data/processed ở giai đoạn truy tìm.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WB_DIR = ROOT / "data" / "raw" / "worldbank" / "provincial_poverty_probe"
UNDP_DIR = ROOT / "data" / "raw" / "undp"

SPID_XLSX = WB_DIR / "AM26-SPID_data.xlsx"
MPM_XLSX = WB_DIR / "AM26-Subnational_MPM.xlsx"
HDX_XLSX = UNDP_DIR / "ophi_hdx_subnational-results-mpi.xlsx"

WB_PROVENANCE = WB_DIR / "PROVENANCE.md"
UNDP_PROVENANCE = UNDP_DIR / "PROVENANCE.md"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_table(dir_path: Path) -> str:
    """Bảng manifest tên—bytes—SHA-256 cho mọi file trừ PROVENANCE.md."""
    rows = []
    for path in sorted(dir_path.iterdir()):
        if path.is_file() and path.name != "PROVENANCE.md":
            rows.append(
                f"| {path.name} | {path.stat().st_size} | {sha256_of(path)} |"
            )
    header = "| Tên file | Bytes | SHA-256 |\n|---|---|---|"
    return header + "\n" + "\n".join(rows)


def extract_spid_monetary() -> Path:
    """6 vùng GAULx của VN, nhóm ALL, nghèo $3/$4.20/$8.30 + Gini + Theil."""
    df = pd.read_excel(SPID_XLSX, sheet_name="Data")
    vnm = df[(df["code"] == "VNM") & (df["data"] == "ALL")]
    cols = ["year", "geo_code", "sample", "mean2021", "poor300", "poor420",
            "poor830", "gini", "theil"]
    out = vnm[cols].sort_values(["year", "geo_code"])
    out_path = WB_DIR / "spid_vnm6_admin1_monetary_extract.csv"
    out.to_csv(out_path, index=False, float_format="%.6f", encoding="utf-8")
    return out_path


def extract_spid_mpm() -> Path:
    """6 vùng GAULx của VN, nghèo đa chiều MPM 2010-2022."""
    df = pd.read_excel(MPM_XLSX, sheet_name="Data")
    vnm = df[df["code"] == "VNM"]
    keep = ["year", "geo_code"] + [
        c for c in vnm.columns if c.startswith("dep_") or c == "mdpoor_i1"
    ]
    out = vnm[keep].sort_values(["year", "geo_code"])
    out_path = WB_DIR / "spid_vnm6_admin1_mpm_extract.csv"
    out.to_csv(out_path, index=False, float_format="%.6f", encoding="utf-8")
    return out_path


def extract_hdx_mpi() -> Path:
    """6 vùng MPI của VN từ bảng 5.1 (HDX/OPHI global MPI 2025, MICS 2020-21)."""
    df = pd.read_excel(HDX_XLSX, sheet_name="5.1 MPI Region", header=None)
    vnm = df[df[2].astype(str).str.contains("Viet Nam", case=False, na=False)]
    out = vnm[[4, 5, 6, 8, 9, 10, 11, 12]].copy()
    out.columns = [
        "survey", "survey_year", "region_name", "mpi", "headcount_h_pct",
        "intensity_a_pct", "vulnerable_to_poverty_pct", "severe_poverty_pct",
    ]
    out = out.sort_values("region_name")
    out_path = UNDP_DIR / "ophi_vnm6_mpi_extract.csv"
    out.to_csv(out_path, index=False, float_format="%.6f", encoding="utf-8")
    return out_path


WB_PROVENANCE_TEXT = """# World Bank — Truy tìm nghèo cấp tỉnh Việt Nam (provincial_poverty_probe)

## Mục đích
Chốt câu hỏi: World Bank có công bố nghèo cấp tỉnh (admin1/63 tỉnh) VN dạng
open data không? Ngày truy tìm: 2026-11-08. Mọi file ở đây là dữ liệu NGUỒN
KHÔNG TIN CẬY cho tới khi được kiểm chứng ở giai đoạn tích hợp.

## Bằng chứng KHÔNG có 63 tỉnh (đã truy vấn, lưu response nguyên trạng)
1. API v2 chỉ cấp quốc gia:
   - `https://api.worldbank.org/v2/country/VNM/indicator/SI.POV.DDAY?format=json&per_page=100`
     -> `api_v2_VNM_SI.POV.DDAY_national.json` (HTTP 200; mọi dòng country.iso3Code=VNM).
   - `SI.POV.NAHC` tương tự -> `api_v2_VNM_SI.POV.NAHC_national.json`.
2. Dimension "country" của API không có admin1:
   - `https://api.worldbank.org/v2/country/VNM-HAN/indicator/SI.POV.DDAY?format=json`
     -> `api_v2_NEGATIVE_admin1code_VNM-HAN.json`:
     `[{{"message":[{{"id":"120","key":"Invalid value","value":"The provided parameter value is not valid"}}]}}]`.
3. Nguồn API số 38 "Subnational Poverty" — KHÔNG có VN admin1:
   - Danh mục nguồn `https://api.worldbank.org/v2/sources?format=json&per_page=300`
     -> `api_v2_sources_list.json` (71 nguồn; id 5 Subnational Malnutrition,
     38 Subnational Poverty, 50 Subnational Population).
   - Source 38 chỉ có 3 chỉ số (SI.POV.NAHC/RUHC/URHC)
     -> `api_v2_source38_indicators.json` (total=3).
   - Dump toàn quốc gia source 38 SI.POV.NAHC
     -> `api_v2_source38_allcountries_SI.POV.NAHC.json` (15.516 dòng, 111 thực
     thể; admin1 của Bangladesh/Bhutan/Belarus... có mặt) — nhưng VN chỉ có 18
     dòng cấp QUỐC GIA 1996-2013 giá trị null, KHÔNG có thực thể admin1 nào.
   - Truy vấn riêng VN:
     `https://api.worldbank.org/v2/country/VNM/indicator/SI.POV.NAHC?source=38&format=json`
     -> `api_v2_VNM_source38_SI.POV.NAHC.json` (total=0).
4. PIP API (Poverty and Inequality Platform):
   - `https://api.worldbank.org/pip/v1/pip?country=VNM&year=2022&format=json`
     -> `pip_v1_VNM_2022.json`: reporting_level="national", survey VHLSS.
   - Thử `reporting_level=all`, `coverage_area=urban`, `coverage_area=rural`
     -> trả về payload national giống hệt (3 file bytes như nhau).
   - `https://api.worldbank.org/pip/v1/_swagger.json` -> 404
     (`pip_v1_swagger.json`).
5. MapVietnam `https://www.worldbank.org/mapvietnam/`: trình xem bản đồ tương
   tác; curl bị vòng lặp redirect www -> www5 (curl exit 47 MAXREDIRS sau 50
   lần, 2026-11-08) — không phải kênh tải open data dạng file.

## Bằng chứng CÓ — subnational 6 vùng (không phải 63 tỉnh), tải được, CC BY 4.0
- Bộ dữ liệu: Subnational Poverty and Inequality Database (SPID), Data Catalog
  dataset 0064796, admin level 1, 141+ nền kinh tế, 1999-2022, License:
  Creative Commons Attribution 4.0. Trang:
  `https://datacatalog.worldbank.org/search/dataset/0064796/subnational-poverty-and-inequality-database-spid`
- File tải nguyên trạng (HTTP 200, 2026-11-08):
  - `https://datacatalogfiles.worldbank.org/ddh-published/0064796/DR0092191/AM26%20-%20SPID%20data.xlsx`
    -> `AM26-SPID_data.xlsx` (18.419.638 B).
  - `https://datacatalogfiles.worldbank.org/ddh-published/0064796/DR0092190/AM26%20-%20Subnational%20MPM.xlsx`
    -> `AM26-Subnational_MPM.xlsx` (1.224.391 B).
- VN trong SPID: `code=VNM`, `lvlvar=subnatid1`, `geo_code=VNM_2015_GAULx_1..6`
  — đúng 6 vùng hợp tỉnh; danh sách tỉnh thành viên nằm trong cột `sample`
  (ví dụ GAULx_1 = "Bac Ninh & Ha Nam & Ha Noi City & ... & Vinh Phuc").
  KHÔNG có mức 63 tỉnh trong file.
- Phủ VN: monetary (sheet Data, nhóm ALL) 2002-2022 cách năm (VHLSS) x 6 vùng;
  MPM nghèo đa chiều 2010-2022 x 6 vùng.

## Tệp xuất từ SPID (script tạo; vẫn là dữ liệu nguồn chưa kiểm chứng)
- `spid_vnm6_admin1_monetary_extract.csv` — 66 dòng (11 năm x 6 vùng, nhóm
  ALL): year, geo_code, sample, mean2021, poor300, poor420, poor830, gini, theil.
- `spid_vnm6_admin1_mpm_extract.csv` — 42 dòng (7 năm x 6 vùng).
- Script: `scripts/wb_undp_poverty_probe.py`, chạy từ thư mục gốc repo
  `python -E scripts/wb_undp_poverty_probe.py`. KHÔNG merge vào
  data/processed ở giai đoạn truy tìm.

## Giấy phép
CC BY 4.0 — World Bank Terms of Use for Datasets,
https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets

## Manifest (tên file — bytes — SHA-256)

{manifest}
"""

UNDP_PROVENANCE_TEXT = """# UNDP — Truy tìm nghèo đa chiều cấp tỉnh Việt Nam

## Mục đích
Chốt câu hỏi: UNDP (vn.undp.org) có file số liệu nghèo đa chiều cấp tỉnh tải
được không? Ngày truy tìm: 2026-11-08. Mọi file ở đây là dữ liệu NGUỒN KHÔNG
TIN CẬY cho tới khi được kiểm chứng ở giai đoạn tích hợp.

## Bằng chứng: báo cáo UNDP Việt Nam = PDF, KHÔNG có file số liệu
- undp.org chặn curl (HTTP 403 "Access Denied" — bot protection, 2026-11-08);
  response 403 lưu nguyên trạng: `undp_vn_page_mpi_report_2021.html`,
  `undp_vn_page_mpi_report_2018.html`.
- Qua WebFetch (render như trình duyệt), hai trang báo cáo nghèo đa chiều chính
  của UNDP Việt Nam chỉ có link PDF:
  - "Viet Nam Multi-dimensional Poverty Report 2021"
    (https://www.undp.org/vietnam/publications/viet-nam-multi-dimensional-poverty-report-2021):
    MDP_full-E-7-2022.pdf, MDP_full-V-7-2022.pdf, MDP_SummaryE+V-7-2022.pdf.
  - "Multidimensional Poverty in Viet Nam" (2018)
    (https://www.undp.org/vietnam/publications/multidimensional-poverty-viet-nam):
    MDP-full-E.pdf, Bao-cao.pdf, Summary-report-MDP-final-EN.pdf,
    Summary-report-MDP-final-VN.pdf.
  - Không có bất kỳ xlsx/csv nào trên cả hai trang.

## Bằng chứng: UNDP/OPHI Global MPI subnational — 6 vùng, tải được (HDX, CC0)
- CKAN API của HDX: `https://data.humdata.org/api/3/action/package_show?id=global-mpi`
  -> `hdx_ckan_global_mpi.json` (dataset "Global Multidimensional Poverty
  Index", license "Public Domain / No restrictions (CC0)").
- File subnational tải được (HTTP 200 qua redirect 302):
  `https://data.humdata.org/dataset/42b16840-3a56-4a20-9314-7aa171f1136c/resource/45b18fbb-ab0d-4f54-ae23-c078f1eccf25/download/subnational-results-mpi.xlsx`
  -> `ophi_hdx_subnational-results-mpi.xlsx` (1.935.836 B).
- VN trong bảng "5.1 MPI Region": đúng 6 vùng (Central Highlands, Mekong River
  Delta, North Central & Central Coast, Northern Uplands, Red River Delta,
  Southeast), nguồn MICS 2020-2021 — KHÔNG có 63 tỉnh.
- Nguồn gốc: OPHI (University of Oxford) cho UNDP HDR; trích dẫn trong file:
  Alkire, S., Mishra, R., Selden, L. and Suppa, N. (2025), "The global
  Multidimensional Poverty Index (MPI) 2025: Disaggregation results and
  methodological note", OPHI MPI Methodological Note 62.

## Tệp xuất (script tạo; vẫn là dữ liệu nguồn chưa kiểm chứng)
- `ophi_vnm6_mpi_extract.csv` — 6 dòng (6 vùng, MICS 2020-2021): survey,
  survey_year, region_name, mpi, headcount_h_pct, intensity_a_pct,
  vulnerable_to_poverty_pct, severe_poverty_pct.
- Script: `scripts/wb_undp_poverty_probe.py`, chạy từ thư mục gốc repo
  `python -E scripts/wb_undp_poverty_probe.py`. KHÔNG merge vào
  data/processed ở giai đoạn truy tìm.

## Kết luận
UNDP không công bố nghèo (đa chiều) cấp 63 tỉnh dạng file số liệu; mức nhỏ nhất
của UNDP/OPHI là 6 vùng. Báo cáo cấp tỉnh của UNDP Việt Nam chỉ có PDF.

## Giấy phép
- HDX global MPI: CC0 (Public Domain / No restrictions).
- Nội dung undp.org: (c) UNDP — trang báo cáo không phải open data file.

## Manifest (tên file — bytes — SHA-256)

{manifest}
"""


def main() -> None:
    WB_DIR.mkdir(parents=True, exist_ok=True)
    UNDP_DIR.mkdir(parents=True, exist_ok=True)
    monetary = extract_spid_monetary()
    mpm = extract_spid_mpm()
    mpi = extract_hdx_mpi()
    print("extract:", monetary.name, mpm.name, mpi.name, sep="\n  ")
    WB_PROVENANCE.write_text(
        WB_PROVENANCE_TEXT.format(manifest=manifest_table(WB_DIR)),
        encoding="utf-8",
    )
    UNDP_PROVENANCE.write_text(
        UNDP_PROVENANCE_TEXT.format(manifest=manifest_table(UNDP_DIR)),
        encoding="utf-8",
    )
    print("provenance:", WB_PROVENANCE.name, UNDP_PROVENANCE.name, sep="\n  ")


if __name__ == "__main__":
    main()
