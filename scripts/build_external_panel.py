"""Chuẩn hóa dữ liệu ngoại lai từ gói replication Mendeley thành CSV panel sạch.

Nguồn: Le et al. — "Replication data and code for Digital Governance"
(Mendeley Data, CC BY 4.0, DOI 10.17632/wbk42j9wc8.1). Các file
SOURCE_EXTRACTED đã nằm trong repo tại data/raw/mendeley/Replication_package/.

Nguyên tắc: KHÔNG sửa file gốc; chỉ đọc, chuẩn hóa schema và ghi file mới vào
data/processed/. Nối tỉnh bằng province_crosswalk_63.csv (kèm trong gói), sau đó
gán province_code theo PAPI panel (qua province_ascii) để đồng nhất khóa với
panel chính.

Kết quả:
  data/processed/external_pci_63.csv
  data/processed/external_gso_population_63.csv
  data/processed/external_gso_waste_63.csv
  data/processed/external_63_panel.csv        (bảng nối ngoài theo tỉnh-năm)
  data/processed/external_provenance.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data"
OUT = ROOT / "data" / "processed"

KEEP = ["province_code", "province_ascii", "province_vi", "year"]


def load_crosswalk() -> pd.DataFrame:
    cw = pd.read_csv(PKG / "province_crosswalk_63.csv", encoding="utf-8-sig")
    cw["province_code"] = cw["province_code"].astype(str).str.strip()
    return cw[["province_code", "province_ascii", "province_vi"]]


def attach_keys(df: pd.DataFrame, cw: pd.DataFrame, code_col: str) -> pd.DataFrame:
    df = df.copy()
    df[code_col] = df[code_col].astype(str).str.strip()
    # Bỏ cột tên tỉnh có sẵn trong file gốc — dùng bản chuẩn từ crosswalk (tránh _x/_y).
    for col in ("province_ascii", "province_vi"):
        if col in df.columns:
            df = df.drop(columns=[col])
    merged = df.merge(cw, left_on=code_col, right_on="province_code", how="left", validate="many_to_one")
    if code_col != "province_code":
        # Khóa gốc giữ tên riêng (vd "id"): bỏ cột trùng từ crosswalk, caller sẽ rename sau.
        merged = merged.drop(columns=["province_code"])
    missing = sorted(merged.loc[merged["province_ascii"].isna(), code_col].unique())
    if missing:
        raise SystemExit(f"LỖI: có province_code không nối được crosswalk: {missing}")
    return merged


def pci_panel(cw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(PKG / "pci_panel_63x11_SOURCE_EXTRACTED.csv", encoding="utf-8-sig")
    df = attach_keys(df, cw, "province_code")
    df["year"] = df["year"].astype(int)
    out = df[KEEP + ["pci_weighted_score"]].sort_values(["province_code", "year"])
    return out.reset_index(drop=True)


def gso_population(cw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(PKG / "gso_population_urban_63x8_SOURCE_EXTRACTED.csv", encoding="utf-8-sig")
    df = attach_keys(df, cw, "province_code")
    df["year"] = df["year"].astype(int)
    cols = ["gso_pop_total_thousand", "gso_pop_urban_thousand", "gso_urban_residence_pct_derived"]
    out = df[KEEP + cols].sort_values(["province_code", "year"])
    return out.reset_index(drop=True)


def gso_waste(cw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(PKG / "gso_waste_wide_from_upload.csv", encoding="utf-8-sig")
    df = attach_keys(df, cw, "id").rename(columns={"id": "province_code"})
    df["year"] = df["year"].astype(int)
    out = df[KEEP + ["kg_pc", "kg_urb"]].sort_values(["province_code", "year"])
    return out.reset_index(drop=True)


def coverage(label: str, df: pd.DataFrame, value_col: str) -> str:
    years = sorted(df["year"].unique())
    return (
        f"  {label}: {df['province_code'].nunique()} tỉnh × {len(years)} năm "
        f"({years[0]}–{years[-1]}), {len(df)} dòng, thiếu {int(df[value_col].isna().sum())} ô giá trị"
    )


def main() -> int:
    # Console Windows mặc định cp1252 không mã hóa được chữ Việt trong khối print
    # tổng kết → UnicodeEncodeError khi script đã chạy xong. Ép stdout/stderr sang
    # UTF-8 để phần báo cáo không làm sập script ngay trước khi exit 0.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    cw = load_crosswalk()

    pci = pci_panel(cw)
    pop = gso_population(cw)
    waste = gso_waste(cw)

    # Panel nối ngoài: outer join theo tỉnh-năm để thấy rõ khoảng trống phủ dữ liệu.
    panel = pci.merge(pop, on=KEEP, how="outer").merge(waste, on=KEEP, how="outer")
    panel = panel.sort_values(["province_code", "year"]).reset_index(drop=True)

    # Gán thêm province_code theo PAPI panel (khóa chính của đồ án) qua province_ascii.
    papi = pd.read_csv(OUT / "papi_panel_63_2011_2024.csv")
    papi_map = papi[["province_code", "province_ascii"]].drop_duplicates()
    panel = panel.merge(
        papi_map.rename(columns={"province_code": "papi_province_code"}),
        on="province_ascii",
        how="left",
        validate="many_to_one",
    )
    unmatched = sorted(panel.loc[panel["papi_province_code"].isna(), "province_ascii"].unique())
    if unmatched:
        raise SystemExit(f"LỖI: province_ascii không có trong panel PAPI: {unmatched}")

    OUT.mkdir(parents=True, exist_ok=True)
    pci.to_csv(OUT / "external_pci_63.csv", index=False)
    pop.to_csv(OUT / "external_gso_population_63.csv", index=False)
    waste.to_csv(OUT / "external_gso_waste_63.csv", index=False)
    cols = ["papi_province_code"] + KEEP + [
        "pci_weighted_score",
        "gso_pop_total_thousand",
        "gso_pop_urban_thousand",
        "gso_urban_residence_pct_derived",
        "kg_pc",
        "kg_urb",
    ]
    panel[cols].to_csv(OUT / "external_63_panel.csv", index=False)

    provenance = """# PROVENANCE — Dữ liệu ngoại lai (PCI · GSO · OD Mekong · World Bank WDI)

- **Nền Mendeley:** Le et al. — Replication data and code for "Digital Governance"
  (Mendeley Data V1, **CC BY 4.0**, DOI: 10.17632/wbk42j9wc8.1). File gốc đã nằm
  trong repo tại `data/raw/mendeley/Replication_package/data/` với
  `PROVENANCE.md` riêng.
- **Ngày chuẩn hóa:** 2026-11-07 — script `scripts/build_external_panel.py`
  (chỉ đọc file gốc, ghi file mới; không sửa file gốc).
- **Khóa nối:** `province_crosswalk_63.csv` (kèm trong gói) → `province_ascii`
  → `province_code` của panel PAPI (`data/processed/papi_panel_63_2011_2024.csv`).

## File nền sinh từ gói replication Mendeley (script này)

| File | Nội dung |
|---|---|
| `external_pci_63.csv` | Điểm PCI tổng theo tỉnh-năm (`pci_weighted_score`) |
| `external_gso_population_63.csv` | Dân số, dân số đô thị, % đô thị (GSO, trích Niên giám) |
| `external_gso_waste_63.csv` | Rác thải bình quân đầu người `kg_pc`/`kg_urb` — nhãn đơn vị trong `code/validate_gso.py:11`: "GSO collected kg/person/day" |
| `external_63_panel.csv` | Bảng nối ngoài đầy đủ theo tỉnh-năm (khóa `papi_province_code`) |

## Nguồn gốc từng file gốc (ghi trong chính file SOURCE_EXTRACTED)

- PCI: các workbook "Indicator_PCI<year>_EN.xlsx" từ pcivietnam.vn, sheet `Summary`.
- GSO dân số: Niên giám Thống kê (bản PDF nso.gov.vn), phần dân số theo tỉnh.
- Cần đối chiếu workbook gốc trước khi kết luận về thang đo/gián đoạn chuỗi.

## File mở rộng từ tải trực tiếp 2026-11-07 (script riêng, provenance riêng trong data/raw/*/PROVENANCE.md)

| File | Script sinh | Nguồn gốc | License |
|---|---|---|---|
| `external_pci_63_full.csv` | `scripts/build_pci_full.py` | workbook + trang xếp hạng `data/raw/pci/` (2011, 2023, 2024) + nền Mendeley 2012–2022 | dữ liệu công khai pcivietnam.vn (VCCI–USAID) |
| `external_gso_population_63_full.csv` | `scripts/build_gso_grdp_pop.py` | pxweb V02.01 `data/raw/gso/` + nền Mendeley | NSO công khai ("Bản quyền: Không") |
| `external_gso_grdp_63.csv` | `scripts/build_gso_grdp_pop.py` | pxweb V03.12 `data/raw/gso/` (2018–2024; 2024 = Sơ bộ) | NSO công khai |
| `external_odm_poverty_region_1998_2016.csv` | `scripts/build_odmekong_external.py` | OD Mekong `data/raw/odmekong/` (6 VÙNG, không cấp tỉnh) | CC BY-SA |
| `external_odm_health_63.csv` | `scripts/build_odmekong_external.py` | OD Mekong Health Facilities 2020 + point-in-polygon `data/raw/boundaries/diaphantinh.geojson` | ODbL |
| `external_worldbank_vnm.csv` | `scripts/build_external_worldbank.py` | WDI API v2, quốc gia VNM `data/raw/worldbank/` | CC BY 4.0 |
| `external_master_63_2011_2024.csv` | `scripts/build_external_master.py` | nối panel PAPI + các file trên, mask thiếu tường minh | phái sinh — giữ license nguồn |

Trạng thái từng khoảng trống dữ liệu: `reports/external_data_expansion.md` §4.2.
Đối chiếu chi tiết từng nguồn (độ phủ, vintage, kiểm chứng chéo): file đó.

## Giấy phép

Dữ liệu giữ nguyên **CC BY 4.0** của gói replication — trích dẫn DOI khi dùng lại;
các nguồn tải trực tiếp giữ license riêng ghi trong bảng trên (CC BY 4.0 /
CC BY-SA / ODbL / công khai ghi nguồn).
"""
    (OUT / "external_provenance.md").write_text(provenance, encoding="utf-8")

    print("Đã ghi CSV sạch vào data/processed/:")
    print(coverage("PCI", pci, "pci_weighted_score"))
    print(coverage("GSO dân số", pop, "gso_pop_total_thousand"))
    print(coverage("GSO rác thải", waste, "kg_pc"))
    print(coverage("Panel nối ngoài", panel, "pci_weighted_score"))
    print(f"  Provenance: {OUT / 'external_provenance.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
