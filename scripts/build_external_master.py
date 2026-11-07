"""Dựng MASTER TABLE nối panel PAPI với 5 nguồn dữ liệu ngoại lai.

Gap [1] trong reports/external_data_expansion.md §4.2. Chạy từ thư mục gốc:

    python scripts/build_external_master.py

Nguồn (đều nằm trong data/processed/, mỗi file có provenance riêng trong
external_provenance.md):

  - data/processed/papi_panel_63_2011_2024.csv        (882 dòng — panel chính)
  - data/processed/external_pci_63_full.csv           (882 dòng, PCI điểm tổng)
  - data/processed/external_gso_population_63_full.csv (882 dòng, dân số GSO)
  - data/processed/external_gso_grdp_63.csv           (441 dòng, 2018–2024)
  - data/processed/external_odm_health_63.csv         (63 dòng, snapshot 2020)
  - data/processed/external_gso_waste_63.csv          (305 dòng, rác thải)

Nguyên tắc:
  - Nối LEFT theo khóa (province_code, year) với validate="one_to_one" — giữ
    đúng 882 dòng của panel; dòng thiếu external để TRỐNG (NaN), KHÔNG nội suy.
  - Mỗi nguồn được đánh dấu bằng một cột boolean mask thiếu tường minh
    (`<nguón>_present`) để mọi phân tích sau khai báo rõ "chạy trên bao nhiêu
    ô / tổng bao nhiêu ô". Mask phải xuống cấp tỉnh-năm: kể cả nguồn "đủ năm"
    cũng có thể lỗ cục bộ.
  - Cột `source` của từng nguồn được giữ lại (đổi tên `<nguón>_source`) làm
    flag vintage — riêng dân số GSO phân biệt 504 dòng Niên giám và 378 dòng
    pxweb V02.01.
  - Rác thải không có `papi_province_code`: gán qua `province_ascii` (bắt buộc
    khớp 305/305) rồi kiểm tra bằng với `province_code`.

Đầu ra:
  data/processed/external_master_63_2011_2024.csv — master table 882 dòng
  results/external_master_summary.md              — tóm tắt độ phủ + mask
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
RES = ROOT / "results"

PANEL = OUT / "papi_panel_63_2011_2024.csv"
SOURCES = {
    "pci": OUT / "external_pci_63_full.csv",
    "pop": OUT / "external_gso_population_63_full.csv",
    "grdp": OUT / "external_gso_grdp_63.csv",
    "odm": OUT / "external_odm_health_63.csv",
    "waste": OUT / "external_gso_waste_63.csv",
}
# Cột giá trị giữ lại của từng nguồn (sau khóa nối)
VALUE_COLS = {
    "pci": ["pci_weighted_score"],
    "pop": ["gso_pop_total_thousand", "gso_pop_urban_thousand",
            "gso_urban_residence_pct_derived"],
    "grdp": ["grdp_per_capita_million_vnd"],
    "odm": ["hospital_count_odm2020"],
    "waste": ["kg_pc", "kg_urb"],
}
KEYS = ["province_code", "year"]

# Hai chỉ tiêu đặc trưng dùng khi clustering (models/predict_config.json);
# panel có 13 ô tỉnh-năm thiếu đúng hai cột này nên không có nhãn cụm.
CLUSTER_FEATURES = ["sd_4_2", "sd_6_1"]


def _check_keys_consistent(name: str, df: pd.DataFrame) -> None:
    """Các file external mang cả province_code lẫn papi_province_code: hai cột
    phải trùng nhau từng dòng (cùng một mã hóa PAPI) trước khi nối."""
    if "papi_province_code" in df.columns:
        bad = df[df["papi_province_code"] != df["province_code"]]
        if len(bad):
            raise SystemExit(
                f"LỖI: {name} có {len(bad)} dòng papi_province_code != "
                f"province_code: {bad[KEYS].head().to_dict('records')}"
            )
    if df.duplicated(KEYS).any():
        dup = df.loc[df.duplicated(KEYS, keep=False), KEYS].head().to_dict("records")
        raise SystemExit(f"LỖI: {name} có khóa (province_code, year) trùng: {dup}")


def load_source(name: str, extra_cols: tuple[str, ...] = ()) -> pd.DataFrame:
    """Đọc một nguồn external, giữ khóa + cột giá trị + cột source (nếu có)."""
    df = pd.read_csv(SOURCES[name])
    df["year"] = df["year"].astype(int)
    df["province_code"] = df["province_code"].astype(int)
    _check_keys_consistent(name, df)
    keep = KEYS + VALUE_COLS[name]
    if "source" in df.columns:
        keep = keep + ["source"]
    return df[keep + [c for c in extra_cols if c in df.columns]]


def attach_waste_papi_code(waste: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Rác thải thiếu papi_province_code — gán qua province_ascii, phải khớp 305/305."""
    w = waste.copy()
    if "papi_province_code" in w.columns:
        return w
    w["province_code"] = w["province_code"].astype(int)
    if w.duplicated(["province_ascii", "year"]).any():
        raise SystemExit("LỖI: waste có khóa (province_ascii, year) trùng")
    pmap = panel[["province_ascii", "province_code"]].drop_duplicates()
    pmap = pmap.rename(columns={"province_code": "papi_province_code"})
    w = w.merge(pmap, on="province_ascii", how="left", validate="many_to_one")
    unmatched = sorted(w.loc[w["papi_province_code"].isna(), "province_ascii"].unique())
    if unmatched:
        raise SystemExit(f"LỖI: waste có province_ascii không nối được panel: {unmatched}")
    n = len(w)
    if not (w["papi_province_code"] == w["province_code"]).all():
        raise SystemExit("LỖI: papi_province_code (qua tên) khác province_code trong waste")
    print(f"  waste: gán papi_province_code qua province_ascii — khớp {n}/{n}")
    # Tên tỉnh + mã đối chiếu chỉ dùng để kiểm tra — bỏ trước khi nối để không
    # trùng cột master (master đã có papi_province_code gán từ province_code).
    return w.drop(columns=["province_ascii", "papi_province_code"])


def coverage_by_year(master: pd.DataFrame, masks: list[str]) -> pd.DataFrame:
    """Số ô có giá trị theo năm cho từng mask (bảng năm × nguồn)."""
    rows = []
    for yr, sub in master.groupby("year"):
        row = {"year": int(yr), "n_panel_rows": len(sub)}
        for m in masks:
            row[m] = int(sub[m].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    panel = pd.read_csv(PANEL)
    panel["year"] = panel["year"].astype(int)
    panel["province_code"] = panel["province_code"].astype(int)
    if panel.duplicated(KEYS).any():
        raise SystemExit("LỖI: panel có khóa (province_code, year) trùng")
    n0 = len(panel)
    print(f"Panel chính: {n0} dòng ({panel.year.min()}–{panel.year.max()}), "
          f"{panel.province_code.nunique()} tỉnh")

    master = panel.copy()
    for name in ("pci", "pop", "grdp", "odm"):
        src = load_source(name)
        merged = master.merge(src, on=KEYS, how="left", validate="one_to_one")
        if len(merged) != n0:
            raise SystemExit(f"LỖI: merge {name} làm đổi số dòng: {n0} -> {len(merged)}")
        if "source" in merged.columns:
            merged = merged.rename(columns={"source": f"{name}_source"})
        master = merged
        present = int(master[VALUE_COLS[name][0]].notna().sum())
        print(f"  + {name}: nối xong, mask present = {present}/{n0}")

    waste = load_source("waste", extra_cols=("province_ascii",))
    waste = attach_waste_papi_code(waste, panel)
    # Mọi file external đã kiểm chứng papi_province_code == province_code từng
    # dòng (_check_keys_consistent / attach_waste_papi_code) → gán cho cả 882 dòng.
    master["papi_province_code"] = master["province_code"]
    master = master.merge(waste, on=KEYS, how="left", validate="one_to_one")
    if len(master) != n0:
        raise SystemExit(f"LỖI: merge waste làm đổi số dòng: {n0} -> {len(master)}")
    print(f"  + waste: nối xong, mask present = {int(master['kg_pc'].notna().sum())}/{n0}")

    # ------------------------- mask thiếu tường minh cho từng nguồn --------- #
    master["pci_present"] = master["pci_weighted_score"].notna()
    master["pop_present"] = master["gso_pop_total_thousand"].notna()
    master["grdp_present"] = master["grdp_per_capita_million_vnd"].notna()
    master["odm_present"] = master["hospital_count_odm2020"].notna()
    master["waste_present"] = master["kg_pc"].notna()
    master["papi_sd46_present"] = master[CLUSTER_FEATURES].notna().all(axis=1)

    # Sắp cột: khóa -> panel -> external -> mask -> source flags
    mask_cols = ["pci_present", "pop_present", "grdp_present", "odm_present",
                 "waste_present", "papi_sd46_present"]
    src_cols = ["pci_source", "pop_source", "grdp_source"]
    # province_ascii/province_vi đã có ở head — loại khỏi panel_cols tránh cột trùng tên.
    panel_cols = [c for c in panel.columns if c not in KEYS + ["province_ascii", "province_vi"]]
    ext_cols = [c for k in VALUE_COLS for c in VALUE_COLS[k]]
    head = ["province_code", "papi_province_code", "province_ascii", "province_vi", "year"]
    master = master[head + panel_cols + ext_cols + mask_cols + src_cols]

    out_csv = OUT / "external_master_63_2011_2024.csv"
    master.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Đã ghi {out_csv}: {len(master)} dòng × {len(master.columns)} cột")

    # --------------------------------------- tóm tắt md cho results/ ------- #
    cov = coverage_by_year(master, mask_cols)
    lines = []
    lines.append("# Master table ngoại lai 63 tỉnh × 2011–2024 — tóm tắt\n")
    lines.append(
        "Sinh bởi `scripts/build_external_master.py` (gap [1], "
        "reports/external_data_expansion.md §4.2). Nối LEFT theo khóa "
        "`(province_code, year)` — tức `papi_province_code` của panel PAPI — "
        f"với validate=\"one_to_one\": **{len(master)} dòng × "
        f"{len(master.columns)} cột**, giữ đúng lưới panel, không nội suy.\n"
    )
    lines.append("## 1) Mask thiếu tường minh từng nguồn\n")
    lines.append("| Nguồn | Cột mask | Ô có giá trị | Tỷ lệ trên 882 | Cửa sổ |")
    lines.append("|---|---|---|---|---|")
    windows = {
        "pci_present": ("PCI (VCCI–USAID)", "2011–2022 đủ 63 tỉnh; 2023–2024 chỉ Top-30"),
        "pop_present": ("GSO dân số trung bình", "2011–2024 đủ (trộn 2 vintage, xem §3)"),
        "grdp_present": ("GSO GRDP/người", "2018–2024 (2024 = Sơ bộ); thiếu 2011–2017"),
        "odm_present": ("ODM bệnh viện (số điểm)", "snapshot 2020 duy nhất"),
        "waste_present": ("GSO rác thải kg/người", "2015–2017 + 2019 đủ 63; 2018 trống; 2020 còn 53"),
        "papi_sd46_present": ("Panel PAPI: đủ sd_4_2 & sd_6_1", "13 ô tỉnh-năm thiếu → không có nhãn cụm"),
    }
    for m in mask_cols:
        label, window = windows[m]
        n = int(master[m].sum())
        lines.append(
            f"| {label} | `{m}` | {n}/{len(master)} | {n / len(master):.1%} | {window} |"
        )
    lines.append("")
    lines.append("## 2) Ô có giá trị theo năm (mỗi mask, đếm trên 63 tỉnh/năm)\n")
    lines.append(cov.to_markdown(index=False))
    lines.append("")
    lines.append("## 3) Vintage dân số GSO (cột `pop_source` giữ từng dòng)\n")
    vintage = (
        master[master["pop_present"]]["pop_source"]
        .str.split("(").str[0].str.strip()
        .value_counts()
    )
    for src_name, n in vintage.items():
        yrs = sorted(master.loc[
            master["pop_source"].str.split("(").str[0].str.strip() == src_name, "year"
        ].unique())
        years_txt = ", ".join(str(y) for y in yrs)
        lines.append(f"- `{src_name}`: {n} dòng (năm {years_txt})")
    lines.append(
        "- Lệch vintage đã định lượng trong `data/raw/gso/PROVENANCE.md` "
        "(504 tỉnh-năm giao: chênh trung bình 8,49 nghìn người, max 189,63 "
        "Hà Nội 2014, 104 dòng >1%) — file master giữ nguyên giá trị từng "
        "vintage, không trộn bình quân.\n"
    )
    null46 = master[~master["papi_sd46_present"]]
    lines.append("## 4) 13 ô panel thiếu sd_4_2/sd_6_1 (không có nhãn cụm)\n")
    for yr, sub in null46.groupby("year"):
        lines.append(f"- {int(yr)}: {', '.join(sub['province_ascii'])}")
    lines.append(
        "\nCác ô này là lý do mask phải xuống cấp **tỉnh-năm** chứ không chỉ "
        "theo năm: ví dụ 2018 thiếu Quảng Ninh + Đồng Tháp, 2021 thiếu 3 tỉnh "
        "(Quảng Ninh, Bắc Giang, Bắc Ninh).\n"
    )
    lines.append("## 5) Quy tắc dùng\n")
    lines.append(
        "- Mọi phân tích external phải khai báo \"chạy trên `mask` = n/882 ô\" "
        "và KHÔNG nội suy ô False.\n"
        "- Không tự tính lại PCI weighted score từ sub-index.\n"
        "- Rác thải đã là kg/người (nhãn replication package "
        "`code/validate_gso.py:11`: \"kg/person/day\") — không chuẩn hóa thêm.\n"
        "- Provenance đầy đủ: `data/processed/external_provenance.md` và "
        "`data/raw/*/PROVENANCE.md`."
    )
    out_md = RES / "external_master_summary.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
