"""Pipeline tiền xử lý dữ liệu PAPI 2011–2024 cho phân cụm STING và học có giám sát.

Thiết kế theo quy trình ba giai đoạn:
  1. Làm sạch (Cleaning — đúng thứ tự):
     - Khử trùng lặp toàn dòng và khóa (province_code, year) đầu tiên
     - Quy ước 0.0 -> NaN và phân tách thiếu cấu trúc vs trong giai đoạn (giữ NaN, không nội suy)
     - Kiểm tra tính nhất quán mã tỉnh crosswalk, miền giá trị metadata & scale_audit
     - Đánh dấu ngoại lai |z| > 3 ở cuối Cleaning (chỉ đánh dấu, giữ nguyên để bảo toàn biên lưới STING)
  2. Tích hợp (Integration):
     - Ghép bảng tên tỉnh chuẩn (many_to_one, validate không nhân dòng) & sắp xếp khóa
     - Kiểm chứng ghép bảng ngoại lai one_to_one (khi có external_master_63_2011_2024.csv)
     - Tách ranh giới huấn luyện <= cutoff_year với holdout > cutoff_year để chống rò rỉ
  3. Biến đổi & Thử nghiệm (Transformation & Feature Selection):
     - Sàng lọc đặc trưng (phương sai, tương quan Pearson, cờ scale_audit)
     - Chuẩn hóa StandardScaler (ddof=0) fit chỉ trên tập <= cutoff_year
     - Thử nghiệm định lượng Cleaning/Scaling/Discretization trực tiếp trên lưới STING
"""
from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler, QuantileTransformer, StandardScaler

try:
    from sting import STING
except ImportError:  # pragma: no cover - hỗ trợ import dưới dạng src.preprocessing
    from src.sting import STING

__all__ = [
    "ALLOWLIST_FEATURES",
    "DEFAULT_CUTOFF_YEAR",
    "DEFAULT_STING_CONFIG",
    "FEATURE_LABELS",
    "KEY_COLUMNS",
    "NAME_ALIASES",
    "NEW_FILES",
    "OLD_FILES",
    "OUTLIER_Z_THRESHOLD",
    "PREPROCESSING_PIPELINE",
    "SCALE_JUMP_THRESHOLD",
    "STING_FEATURES",
    "analyze_missingness",
    "check_external_integration",
    "count_range_violations",
    "feature_selection_summary",
    "flag_outliers_zscore",
    "load_crosswalk",
    "load_raw_papi",
    "lookup_code",
    "norm_name",
    "parse_new",
    "parse_old",
    "resolve_project_root",
    "run_preprocessing_pipeline",
    "run_sting_preprocessing_experiments",
    "scale_audit",
    "score_columns",
    "step_check_consistency",
    "step_clean_codes_and_zeros",
    "step_deduplicate",
    "step_flag_outliers",
    "step_integrate_panel",
    "step_select_and_scale",
    "to_float",
]

OLD_FILES: dict[int, str] = {
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
NEW_FILES: dict[int, str] = {
    2020: "2020PAPI_ProvincialIndicators_BangChiTieuCapTinh-1.xlsx",
    2021: "1.2021PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
    2022: "2022PAPI_ProvincialIndicators_BangChiTieuCapTinh-2.xlsx",
    2023: "2023PAPI_ProvincialIndicators_BangChiTieuCapTinh..xlsx",
    2024: "2024PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx",
}

KEY_COLUMNS: tuple[str, str] = ("province_code", "year")
DEFAULT_CUTOFF_YEAR = 2023
OUTLIER_Z_THRESHOLD = 3.0
SCALE_JUMP_THRESHOLD = 0.25

ALLOWLIST_FEATURES: tuple[str, ...] = (
    "sd_1_3",
    "sd_1_4",
    "sd_4_1",
    "sd_4_2",
    "sd_4_3",
    "sd_4_4",
    "sd_6_1",
    "sd_6_3",
)
STING_FEATURES: tuple[str, str] = ("sd_4_2", "sd_6_1")
DEFAULT_STING_CONFIG: dict[str, int] = {
    "n_levels": 3,
    "factor": 4,
    "min_count": 5,
    "cluster_level": 2,
    "connectivity": 1,
}

FEATURE_LABELS: dict[str, str] = {
    "sd_1_3": "1.3 Chất lượng bầu cử",
    "sd_1_4": "1.4 Đóng góp tự nguyện",
    "sd_4_1": "4.1 Kiểm soát tham nhũng trong chính quyền địa phương",
    "sd_4_2": "4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công",
    "sd_4_3": "4.3 Công bằng trong tuyển dụng vào khu vực công",
    "sd_4_4": "4.4 Quyết tâm chống tham nhũng của chính quyền địa phương",
    "sd_6_1": "6.1 Y tế công lập",
    "sd_6_3": "6.3 Cơ sở hạ tầng căn bản",
    "d1": "Chiều 1 – Tham gia ở cấp cơ sở",
    "d2": "Chiều 2 – Minh bạch",
    "d3": "Chiều 3 – Trách nhiệm giải trình",
    "d4": "Chiều 4 – Kiểm soát tham nhũng",
    "d5": "Chiều 5 – Thủ tục hành chính công",
    "d6": "Chiều 6 – Cung ứng dịch vụ công",
    "d7": "Chiều 7 – Quản trị môi trường",
    "d8": "Chiều 8 – Quản trị điện tử",
}

NAME_ALIASES: dict[str, str] = {"tthue": "thuathienhue"}

_DIM_RE = re.compile(r"^\s*([1-8])\s*:\s")
_SUB_RE = re.compile(r"^\s*([1-8])\.(\d+)\s*:")
_DIM_ROW_RE = re.compile(r"^Dimension\s*([1-8])\s*:")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")


def resolve_project_root(start: Path | None = None) -> Path:
    """Tìm thư mục gốc dự án hoặc thư mục ``tai_lieu_kem`` chứa dữ liệu tiền xử lý."""
    seed = (start or Path.cwd()).resolve()
    marker = Path("data") / "raw" / "papi"
    for candidate_parent in (seed, *seed.parents):
        for cand in (candidate_parent / "tai_lieu_kem", candidate_parent):
            if (cand / "src" / "sting.py").is_file() and (cand / marker).is_dir():
                return cand
    raise FileNotFoundError(
        "Không tìm thấy thư mục dự án hoặc tai_lieu_kem chứa src/sting.py và data/raw/papi."
    )


def norm_name(value: object) -> str:
    """Chuẩn hóa tên tỉnh: bỏ khoảng trắng/gạch nối, viết thường."""
    return re.sub(r"[\s\-]+", "", str(value).strip().lower())


def to_float(value: object) -> float:
    """Chuyển giá trị ô Excel thành float; ô rỗng/không hợp lệ trả về NaN."""
    if value is None:
        return float(np.nan)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return float(np.nan)
    try:
        return float(text)
    except ValueError:
        return float(np.nan)


def load_crosswalk(crosswalk_path: Path) -> tuple[dict[str, int], dict[int, dict[str, str]]]:
    """Đọc bảng tra 63 tỉnh thành mapping tên chuẩn hóa -> mã tỉnh và mã -> nhãn."""
    if not crosswalk_path.is_file():
        raise FileNotFoundError(f"Thiếu file crosswalk: {crosswalk_path}")
    cw = pd.read_csv(crosswalk_path)
    ascii2code: dict[str, int] = {}
    code2info: dict[int, dict[str, str]] = {}
    for code, vi, asc in zip(
        cw["province_code"], cw["province_vi"], cw["province_ascii"], strict=True
    ):
        icode = int(code)
        code2info[icode] = {
            "province_vi": str(vi).strip(),
            "province_ascii": str(asc).strip(),
        }
        ascii2code[norm_name(asc)] = icode
    return ascii2code, code2info


def lookup_code(name: object, ascii2code: dict[str, int]) -> float | int:
    """Tra mã tỉnh theo tên đã chuẩn hóa (hỗ trợ viết tắt trong NAME_ALIASES)."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return float(np.nan)
    normalized = norm_name(name)
    normalized = NAME_ALIASES.get(normalized, normalized)
    return ascii2code.get(normalized, float(np.nan))


def parse_old(year: int, filepath: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Đọc workbook PAPI giai đoạn 2011–2019 (mỗi hàng là một tỉnh)."""
    if not filepath.is_file():
        raise FileNotFoundError(f"Thiếu workbook PAPI {year}: {filepath}")
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        it = ws.iter_rows(values_only=True)
        header = next(it)
        dim_cols: dict[int, int] = {}
        sub_cols: dict[str, int] = {}
        for j, col_name in enumerate(header):
            if col_name is None:
                continue
            hs = str(col_name)
            m_sub = _SUB_RE.match(hs)
            if m_sub:
                sub_cols[f"sd_{m_sub.group(1)}_{m_sub.group(2)}"] = j
                continue
            m_dim = _DIM_RE.match(hs)
            if m_dim:
                dim_cols[int(m_dim.group(1))] = j

        n_prov = 0
        for row in it:
            if not row or row[0] is None or not str(row[0]).strip():
                continue
            n_prov += 1
            rec: dict[str, Any] = {"province_ascii": str(row[0]).strip(), "year": year}
            for d, j in dim_cols.items():
                rec[f"d{d}"] = to_float(row[j]) if j < len(row) else np.nan
            for key, j in sub_cols.items():
                rec[key] = to_float(row[j]) if j < len(row) else np.nan
            rows.append(rec)
    finally:
        wb.close()

    return {
        "year": year,
        "format": "2011–2019 (tỉnh là hàng)",
        "provinces": n_prov,
        "dims": len(dim_cols),
        "subs": len(sub_cols),
    }


def parse_new(year: int, filepath: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Đọc workbook PAPI giai đoạn 2020–2024 (ma trận chuyển vị trên sheet <năm>…VIE_ENG)."""
    if not filepath.is_file():
        raise FileNotFoundError(f"Thiếu workbook PAPI {year}: {filepath}")
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    try:
        target = next(
            (
                name
                for name in wb.sheetnames
                if name.strip().startswith(str(year)) and "VIE_ENG" in name.strip()
            ),
            None,
        )
        if target is None:
            raise RuntimeError(f"{filepath.name}: không tìm thấy sheet {year}_VIE_ENG")

        ws = wb[target]
        it = ws.iter_rows(values_only=True)
        row1 = next(it)
        next(it)  # bỏ qua dòng tên tỉnh

        col_code: dict[int, int] = {}
        for j in range(3, len(row1)):
            v = row1[j]
            if isinstance(v, (int, float)) and float(v).is_integer() and 1 <= int(v) <= 96:
                col_code[j] = int(v)

        dim_data: dict[int, dict[int, float]] = {n: {} for n in range(1, 9)}
        sub_data: dict[str, dict[int, float]] = {}
        for row in it:
            if row is None:
                continue
            c0 = str(row[0]).strip() if row[0] is not None else ""
            c1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            m_dim = _DIM_ROW_RE.match(c0)
            if m_dim:
                n = int(m_dim.group(1))
                if not dim_data[n]:
                    for j, code in col_code.items():
                        dim_data[n][code] = to_float(row[j]) if j < len(row) else np.nan
                continue
            m_sub = _SUB_RE.match(c1)
            if m_sub:
                key = f"sd_{m_sub.group(1)}_{m_sub.group(2)}"
                if key not in sub_data:
                    sub_data[key] = {
                        code: (to_float(row[j]) if j < len(row) else np.nan)
                        for j, code in col_code.items()
                    }

        for code in sorted(set(col_code.values())):
            rec: dict[str, Any] = {"province_code": code, "year": year}
            for n in range(1, 9):
                rec[f"d{n}"] = dim_data[n].get(code, np.nan)
            for key, dd in sub_data.items():
                rec[key] = dd.get(code, np.nan)
            rows.append(rec)
    finally:
        wb.close()

    return {
        "year": year,
        "format": "2020–2024 (chuyển vị)",
        "provinces": len(set(col_code.values())),
        "dims": sum(1 for n in dim_data if dim_data[n]),
        "subs": len(sub_data),
    }


def load_raw_papi(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đọc đủ 14 workbook PAPI gốc (2011–2024) và trả về (raw_df, diagnostics_df)."""
    records: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for files, reader in ((OLD_FILES, parse_old), (NEW_FILES, parse_new)):
        for year, filename in files.items():
            diagnostics.append(reader(year, raw_dir / filename, records))
    return pd.DataFrame(records), pd.DataFrame(diagnostics)


def score_columns(df: pd.DataFrame) -> list[str]:
    """Liệt kê cột điểm PAPI (d1..d8 rồi sd_*) theo thứ tự tự nhiên."""
    cols = [c for c in df.columns if re.fullmatch(r"d[1-8]", c) or c.startswith("sd_")]
    return sorted(
        cols,
        key=lambda c: (0, int(c[1:]), 0)
        if c.startswith("d")
        else (1, int(c.split("_")[1]), int(c.split("_")[2])),
    )


def analyze_missingness(
    df: pd.DataFrame,
    metadata: pd.DataFrame | None = None,
    cols: Sequence[str] | None = None,
    *,
    zeros_before: pd.Series | None = None,
    missing_before: pd.Series | None = None,
) -> dict[str, Any]:
    """Thống kê ô thiếu theo cột và theo năm, phân tách thiếu cấu trúc vs trong giai đoạn."""
    target_cols = list(cols) if cols is not None else score_columns(df)
    missing_after = df[target_cols].isna().sum()
    zeros_ser = zeros_before if zeros_before is not None else df[target_cols].eq(0).sum()
    before_ser = missing_before if missing_before is not None else missing_after

    per_column = pd.DataFrame(
        {
            "Ô bằng 0 trước xử lý": zeros_ser,
            "Ô thiếu trước xử lý": before_ser,
            "Ô thiếu sau xử lý": missing_after,
            "Tỷ lệ thiếu (%)": (100.0 * missing_after / max(1, len(df))).round(2),
        }
    )
    per_column.loc["Toàn bộ 37 cột chỉ tiêu"] = {
        "Ô bằng 0 trước xử lý": int(zeros_ser.sum()),
        "Ô thiếu trước xử lý": int(before_ser.sum()),
        "Ô thiếu sau xử lý": int(missing_after.sum()),
        "Tỷ lệ thiếu (%)": round(
            100.0 * float(missing_after.sum()) / max(1, len(df) * len(target_cols)), 2
        ),
    }

    total_missing = int(missing_after.sum())
    by_year_rows: list[dict[str, Any]] = []
    in_window_missing = 0
    in_window_rows = 0

    if metadata is not None and not metadata.empty and "year" in df.columns:
        specs = metadata.set_index("cot")
        for yr, sub in df.groupby("year", sort=True):
            active = [
                c
                for c in target_cols
                if c in specs.index
                and specs.loc[c, "nam_bat_dau"] <= yr <= specs.loc[c, "nam_ket_thuc"]
            ]
            yr_total = int(sub[target_cols].isna().sum().sum())
            yr_in_win = int(sub[active].isna().sum().sum()) if active else 0
            yr_in_win_rows = int(sub[active].isna().any(axis=1).sum()) if active else 0
            in_window_missing += yr_in_win
            in_window_rows += yr_in_win_rows
            by_year_rows.append(
                {
                    "Năm": int(yr),
                    "Cột trong cửa sổ": len(active),
                    "Thiếu cấu trúc (ngoài cửa sổ)": yr_total - yr_in_win,
                    "Thiếu trong cửa sổ": yr_in_win,
                    "Dòng thiếu trong cửa sổ": yr_in_win_rows,
                }
            )
    else:
        in_window_missing = total_missing

    structural_missing = total_missing - in_window_missing
    return {
        "per_column": per_column,
        "by_year": pd.DataFrame(by_year_rows),
        "total_zeros": int(zeros_ser.sum()),
        "total_missing": total_missing,
        "total_cells": int(len(df) * len(target_cols)),
        "structural_missing": int(structural_missing),
        "in_window_missing": int(in_window_missing),
        "in_window_rows": int(in_window_rows),
    }


def count_range_violations(
    df: pd.DataFrame, metadata: pd.DataFrame, tolerance: float = 1e-9
) -> int:
    """Đếm số ô vượt khoảng giá trị hợp lệ theo metadata từng giai đoạn."""
    if df.empty or metadata.empty:
        return 0
    bad = 0
    for _, spec in metadata.iterrows():
        col = spec["cot"]
        if col not in df.columns:
            continue
        m1 = _RANGE_RE.search(str(spec["thang_2011_2020"]))
        m2 = _RANGE_RE.search(str(spec["thang_2021_2024"]))
        if not m1 and not m2:
            continue
        r1 = (
            (float(m1.group(1)), float(m1.group(2)))
            if m1
            else (float(m2.group(1)), float(m2.group(2)))
        )
        r2 = (float(m2.group(1)), float(m2.group(2))) if m2 else r1
        split_yr = spec["nam_doi_thang"]
        for yr, sub in df.groupby("year"):
            lo, hi = r1 if (pd.isna(split_yr) or yr < split_yr) else r2
            vals = sub[col].dropna()
            bad += int(((vals < lo - tolerance) | (vals > hi + tolerance)).sum())
    return bad


def scale_audit(
    df: pd.DataFrame,
    threshold: float = SCALE_JUMP_THRESHOLD,
    *,
    min_years: int = 5,
) -> list[tuple[str, float, int]]:
    """Heuristic đánh dấu cột có bước nhảy |Δmean| giữa hai năm liên tiếp > threshold."""
    cols = [
        c
        for c in df.columns
        if (re.fullmatch(r"d[1-8]", c) or c.startswith("sd_")) and df[c].dtype.kind in "fi"
    ]
    if "year" not in df.columns or not cols:
        return []
    means = df.groupby("year")[cols].mean()
    flags: list[tuple[str, float, int]] = []
    for c in cols:
        m = means[c].dropna()
        if len(m) < min_years:
            continue
        jumps = m.diff().abs()
        j = float(jumps.max())
        if j > threshold:
            flags.append((c, round(j, 3), int(jumps.idxmax())))
    flags.sort(key=lambda t: -t[1])
    return flags


def flag_outliers_zscore(
    df: pd.DataFrame, cols: Sequence[str], z_threshold: float = OUTLIER_Z_THRESHOLD
) -> pd.DataFrame:
    """Đánh dấu ô có |z| > z_threshold (ddof=0); cột hằng số không phát sinh cờ NaN."""
    target = list(cols)
    if df.empty or not target:
        return pd.DataFrame(False, index=df.index, columns=target)
    sub = df[target].astype(float)
    stds = sub.std(ddof=0).replace(0.0, np.nan)
    z = (sub - sub.mean()) / stds
    return z.abs().gt(z_threshold).fillna(False)


def step_deduplicate(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 1 (Cleaning — đầu tiên): khử trùng toàn dòng & kiểm tra khóa (province_code, year)."""
    raw_df = ctx["raw"]
    if raw_df.empty:
        raise ValueError("Bảng dữ liệu thô rỗng.")
    n_exact = int(raw_df.duplicated().sum())
    df = raw_df.drop_duplicates().copy()
    ascii_to_code, code_to_province = ctx["crosswalk_maps"]
    if "province_code" not in df.columns:
        df["province_code"] = np.nan
    if "province_ascii" in df.columns:
        old_codes = df["province_ascii"].map(lambda name: lookup_code(name, ascii_to_code))
        df["province_code"] = df["province_code"].astype("float64").fillna(old_codes)
    if df["province_code"].isna().any():
        raise ValueError("Còn tên tỉnh chưa map được sang mã tỉnh.")
    df["province_code"] = df["province_code"].astype(int)
    n_key = int(df.duplicated(list(KEY_COLUMNS), keep=False).sum())
    if n_key:
        raise ValueError(f"Phát hiện {n_key} dòng trùng khóa {KEY_COLUMNS}.")
    ctx["clean"] = df
    ctx["code_to_province"] = code_to_province
    ctx["dedup_stats"] = {"exact_duplicates": n_exact, "key_duplicates": n_key, "rows": len(df)}
    ctx["log"].append(
        (
            "1. Cleaning — Deduplicate (đầu tiên)",
            f"{len(df)} dòng (trùng toàn dòng: {n_exact}; trùng khóa tỉnh–năm: {n_key})",
        )
    )
    return ctx


def step_clean_codes_and_zeros(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 2 (Cleaning): quy 0.0 -> NaN và giữ giá trị thiếu (không nội suy)."""
    df = ctx["clean"].copy()
    cols = ctx["score_cols"]
    missing_before = df[cols].isna().sum()
    zeros = df[cols].eq(0)
    n_zero = int(zeros.sum().sum())
    df[cols] = df[cols].mask(zeros)
    summary = analyze_missingness(
        df,
        ctx.get("metadata"),
        cols,
        zeros_before=zeros.sum(),
        missing_before=missing_before,
    )
    ctx["clean"] = df
    ctx["missing_summary"] = summary
    ctx["log"].append(
        (
            "2. Cleaning — Missing & 0.0→NaN",
            f"{n_zero} ô 0.0 → NaN; tổng {summary['total_missing']} ô NaN "
            f"({summary['structural_missing']} ngoài cửa sổ + "
            f"{summary['in_window_missing']} trong cửa sổ/{summary['in_window_rows']} dòng), giữ nguyên",
        )
    )
    return ctx


def step_check_consistency(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 3 (Cleaning): kiểm tra mã tỉnh crosswalk, miền metadata và scale_audit."""
    df = ctx["clean"]
    crosswalk_codes = ctx.get("crosswalk_codes")
    n_code_mismatch = (
        len(set(df["province_code"].unique()) ^ set(crosswalk_codes))
        if crosswalk_codes is not None
        else 0
    )
    metadata = ctx.get("metadata")
    n_range_bad = count_range_violations(df, metadata) if metadata is not None else 0
    if n_code_mismatch or n_range_bad:
        raise ValueError(
            f"Phát hiện lỗi nhất quán: code_mismatch={n_code_mismatch}, range_bad={n_range_bad}"
        )
    flags = scale_audit(df)
    flagged = {c for c, _, _ in flags}
    bad_selected = [c for c in ctx["features"] if c in flagged]
    if bad_selected:
        raise ValueError(f"Đặc trưng chọn bị cờ nhảy thang: {bad_selected}")
    ctx["scale_flags"] = flags
    ctx["flagged_names"] = flagged
    ctx["consistency_stats"] = {
        "code_mismatch": n_code_mismatch,
        "range_violations": n_range_bad,
        "scale_flagged_count": len(flags),
    }
    ctx["log"].append(
        (
            "3. Cleaning — Consistency & Scale Audit",
            f"{n_code_mismatch} xung đột mã; {n_range_bad} vi phạm miền; "
            f"{len(flags)}/{len(ctx['score_cols'])} cột bị cờ >0.25 (không chọn)",
        )
    )
    return ctx


def step_flag_outliers(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 4 (Cleaning — cuối cùng): đánh dấu ngoại lai |z| > ngưỡng và giữ nguyên toàn bộ."""
    df = ctx["clean"]
    cols = ctx["score_cols"]
    z_thr = float(ctx.get("z_threshold", OUTLIER_Z_THRESHOLD))
    panel_mask = flag_outliers_zscore(df, cols, z_thr)
    n_panel_cells = int(panel_mask.sum().sum())
    n_panel_rows = int(panel_mask.any(axis=1).sum())
    n_panel_cols = int(panel_mask.any(axis=0).sum())

    feats = list(ctx["features"])
    sub = df.loc[df["year"] <= ctx["cutoff_year"], feats].dropna()
    train_mask = (
        flag_outliers_zscore(sub, feats, z_thr).any(axis=1)
        if not sub.empty
        else pd.Series(dtype=bool)
    )

    ctx["panel_outlier_mask"] = panel_mask
    ctx["train_outlier_mask"] = train_mask
    ctx["outlier_stats"] = {
        "panel_cells": n_panel_cells,
        "panel_rows": n_panel_rows,
        "panel_cols": n_panel_cols,
        "train_feature_rows": int(train_mask.sum()) if len(train_mask) else 0,
        "train_total_rows": len(sub),
    }
    ctx["log"].append(
        (
            "4. Cleaning — Flag outliers (cuối Cleaning)",
            f"toàn panel: {n_panel_cells} ô/{n_panel_rows} dòng/{n_panel_cols} cột; "
            f"train {len(feats)} biến: {ctx['outlier_stats']['train_feature_rows']}/{len(sub)} dòng |z|>{z_thr:g} (giữ)",
        )
    )
    return ctx


def step_integrate_panel(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 5 (Integration): nối thông tin tỉnh many_to_one và sắp xếp theo (province_code, year)."""
    provinces = (
        pd.DataFrame.from_dict(ctx["code_to_province"], orient="index")
        .rename_axis("province_code")
        .reset_index()
    )
    base = ctx["clean"].drop(columns=["province_ascii", "province_vi"], errors="ignore")
    df = base.merge(provinces, on="province_code", how="left", validate="many_to_one")
    if df[["province_ascii", "province_vi"]].isna().any().any():
        raise ValueError("Còn mã tỉnh chưa nối được với bảng tên chuẩn.")

    column_order = ctx.get("column_order")
    if column_order is None:
        id_cols = ["province_code", "province_ascii", "province_vi", "year"]
        dim_cols = [f"d{i}" for i in range(1, 9) if f"d{i}" in df.columns]
        sub_cols = [c for c in score_columns(df) if c.startswith("sd_")]
        column_order = id_cols + dim_cols + sub_cols

    df = df[list(column_order)].sort_values(list(KEY_COLUMNS)).reset_index(drop=True)
    ctx["panel"] = df
    ctx["log"].append(
        (
            "5. Integration — Merge & Sort",
            f"{df.shape[0]} dòng × {df.shape[1]} cột, {df['province_code'].nunique()} tỉnh, 0 xung đột khóa",
        )
    )
    return ctx


def step_select_and_scale(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bước 6 (Transformation): dropna theo cặp đặc trưng & StandardScaler fit chỉ trên <= cutoff_year."""
    df = ctx["panel"]
    feats = list(ctx["features"])
    cutoff = int(ctx["cutoff_year"])
    complete = df.dropna(subset=feats).copy()
    tr = complete.loc[complete["year"] <= cutoff, feats]
    te = complete.loc[complete["year"] > cutoff, feats]
    if tr.empty:
        raise ValueError(f"Không có quan sát nào đủ {feats} ở giai đoạn <= {cutoff}.")
    sc = StandardScaler().fit(tr)
    X_train = sc.transform(tr)
    X_holdout = sc.transform(te) if not te.empty else np.empty((0, len(feats)), dtype=float)

    ctx["complete_df"] = complete
    ctx["train_df"] = complete.loc[complete["year"] <= cutoff].copy()
    ctx["holdout_df"] = complete.loc[complete["year"] > cutoff].copy()
    ctx["X_train"] = X_train
    ctx["X_holdout"] = X_holdout
    ctx["scaler"] = sc
    ctx["log"].append(
        (
            f"6. Transformation — StandardScaler (≤{cutoff})",
            f"train={X_train.shape}, holdout={X_holdout.shape} (fit chỉ trên ≤{cutoff})",
        )
    )
    return ctx


PREPROCESSING_PIPELINE: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = [
    ("Deduplication", step_deduplicate),
    ("Missing & Zero Convention", step_clean_codes_and_zeros),
    ("Consistency & Scale Audit", step_check_consistency),
    ("Outlier Flagging", step_flag_outliers),
    ("Integration & Ordering", step_integrate_panel),
    ("Feature Selection & Scaling", step_select_and_scale),
]


def run_preprocessing_pipeline(
    root: Path,
    *,
    features: Sequence[str] = STING_FEATURES,
    cutoff_year: int = DEFAULT_CUTOFF_YEAR,
    z_threshold: float = OUTLIER_Z_THRESHOLD,
) -> dict[str, Any]:
    """Chạy trọn bộ 6 bước tiền xử lý từ 14 workbook PAPI gốc trong thư mục ``root``."""
    raw_dir = root / "data" / "raw" / "papi"
    crosswalk_path = (
        root / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
    )
    metadata_path = root / "data" / "processed" / "papi_panel_scale_metadata.csv"

    raw_df, diagnostics_df = load_raw_papi(raw_dir)
    ascii_to_code, code_to_province = load_crosswalk(crosswalk_path)
    crosswalk_df = pd.read_csv(crosswalk_path)
    crosswalk_codes = crosswalk_df["province_code"].astype(int).unique()
    metadata = pd.read_csv(metadata_path) if metadata_path.is_file() else None
    s_cols = score_columns(raw_df)

    state: dict[str, Any] = {
        "root": root,
        "raw": raw_df,
        "diagnostics": diagnostics_df,
        "crosswalk_maps": (ascii_to_code, code_to_province),
        "crosswalk_codes": crosswalk_codes,
        "metadata": metadata,
        "score_cols": s_cols,
        "features": list(features),
        "cutoff_year": int(cutoff_year),
        "z_threshold": float(z_threshold),
        "log": [],
    }
    for _name, step_fn in PREPROCESSING_PIPELINE:
        state = step_fn(state)
    return state


def feature_selection_summary(
    panel: pd.DataFrame,
    score_cols: Sequence[str],
    candidate_features: Sequence[str] = ALLOWLIST_FEATURES,
    cutoff_year: int = DEFAULT_CUTOFF_YEAR,
    flagged_names: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đánh giá phương sai, tương quan Pearson và cờ audit của các đặc trưng sạch <= cutoff."""
    feats = list(candidate_features)
    train_subset = panel.loc[panel["year"] <= cutoff_year, feats].dropna()
    variances = train_subset.var(ddof=0)
    corr = train_subset.corr()
    corr_other = corr.abs().mask(np.eye(len(feats), dtype=bool))
    max_abs_r = corr_other.max()
    flagged = flagged_names if flagged_names is not None else {c for c, _, _ in scale_audit(panel)}

    summary = pd.DataFrame(
        {
            "Tên chỉ tiêu": [FEATURE_LABELS.get(c, c) for c in feats],
            "Min (≤cutoff)": train_subset.min(),
            "Max (≤cutoff)": train_subset.max(),
            "Phương sai (ddof=0)": variances,
            "|r| max với biến khác": max_abs_r,
            "Bị cờ scale_audit": [c in flagged for c in feats],
            "Loại khỏi 37 cột": len(score_cols) - len(feats),
        }
    )
    return summary, corr


def run_sting_preprocessing_experiments(
    panel: pd.DataFrame,
    sting_cfg: dict[str, int] | None = None,
    features: Sequence[str] = STING_FEATURES,
    cutoff_year: int = DEFAULT_CUTOFF_YEAR,
    z_threshold: float = OUTLIER_Z_THRESHOLD,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Thử nghiệm Cleaning & Transformation trên lưới STING tập huấn luyện <= cutoff."""
    sp = dict(sting_cfg or DEFAULT_STING_CONFIG)
    feats = list(features)
    train_raw_all = panel.loc[panel["year"] <= cutoff_year, feats]
    train_df = train_raw_all.dropna().copy()

    scaler_std = StandardScaler().fit(train_df)
    X_std = scaler_std.transform(train_df)
    extreme_mask = (np.abs(X_std) > z_threshold).any(axis=1)

    X_raw = train_df.to_numpy(dtype=float)
    X_trim = X_std[~extreme_mask]
    if len(X_trim) == 0:
        raise ValueError("Mọi quan sát huấn luyện đều vượt ngưỡng ngoại lai.")
    X_imputed = StandardScaler().fit_transform(
        SimpleImputer(strategy="median").fit_transform(train_raw_all)
    )
    X_minmax = MinMaxScaler().fit_transform(train_df)
    X_quant = QuantileTransformer(
        n_quantiles=max(2, min(200, len(train_df))),
        output_distribution="uniform",
        random_state=42,
    ).fit_transform(train_df)

    def _probe(X_arr: np.ndarray, ref_cells: np.ndarray | None = None):
        model = STING(
            n_levels=sp["n_levels"],
            factor=sp["factor"],
            min_count=sp["min_count"],
        ).fit(X_arr)
        labels = model.cluster(level=sp["cluster_level"], connectivity=sp["connectivity"])
        cells = model.point_cell_index(sp["cluster_level"])
        same = (
            int((cells == ref_cells).all(axis=1).sum())
            if (ref_cells is not None and len(cells) == len(ref_cells))
            else None
        )
        row = {
            "Số dòng": int(len(X_arr)),
            "Số cụm": int(model.n_clusters_),
            "Số ô dày": int(len(model.label_of_)),
            "Điểm nhiễu (−1)": int((labels == -1).sum()),
            "Tỷ lệ nhiễu": f"{(labels == -1).mean():.1%}",
            "Giữ nguyên ô vs z-score": (
                f"{same}/{len(cells)}" if same is not None else "n/a (đổi mẫu)"
            ),
        }
        return row, cells, {"X": X_arr, "model": model, "labels": labels}

    row_std, ref_cells, art_std = _probe(X_std)
    row_std["Giữ nguyên ô vs z-score"] = f"{len(X_std)}/{len(X_std)} (chuẩn)"
    row_trim, _, art_trim = _probe(X_trim)
    row_imp, _, art_imp = _probe(X_imputed)
    row_raw, _, art_raw = _probe(X_raw, ref_cells)
    row_minmax, _, art_minmax = _probe(X_minmax, ref_cells)
    row_quant, _, art_quant = _probe(X_quant, ref_cells)

    variants = {
        "1. Pipeline chọn (dropna + giữ |z|>3 + StandardScaler)": row_std,
        f"2. Cleaning: Xóa {int(extreme_mask.sum())} điểm |z|>3 (co biên lưới)": row_trim,
        f"3. Cleaning: Điền SimpleImputer(median) cho {int(train_raw_all.isna().any(axis=1).sum())} dòng thiếu": row_imp,
        "4. Transform: Điểm gốc (không scale)": row_raw,
        "5. Transform: MinMaxScaler [0, 1] (affine)": row_minmax,
        "6. Transform: QuantileTransformer (phi tuyến)": row_quant,
    }
    artifacts = {
        "standard": art_std,
        "trimmed": art_trim,
        "imputed": art_imp,
        "raw": art_raw,
        "minmax": art_minmax,
        "quantile": art_quant,
    }
    return pd.DataFrame.from_dict(variants, orient="index"), artifacts


def check_external_integration(
    panel: pd.DataFrame, master_path: Path, tolerance: float = 1e-9
) -> dict[str, Any]:
    """Kiểm chứng quan hệ one_to_one, nhất quán giá trị và độ phủ mask của bảng master ngoại lai."""
    master = pd.read_csv(master_path)
    keys = list(KEY_COLUMNS)
    panel_unique = not panel.duplicated(keys).any()
    master_unique = not master.duplicated(keys).any()
    if panel_unique and master_unique:
        cardinality = "one_to_one"
    elif panel_unique:
        cardinality = "one_to_many"
    elif master_unique:
        cardinality = "many_to_one"
    else:
        cardinality = "many_to_many"

    shared_numeric = [
        c
        for c in panel.columns
        if c in master.columns and c not in keys and panel[c].dtype.kind in "fi"
    ]
    if shared_numeric:
        p_vals = panel.set_index(keys)[shared_numeric].sort_index()
        m_vals = master.set_index(keys)[shared_numeric].sort_index()
        diff = (p_vals - m_vals).abs()
        max_diff = float(diff.max().max())
        over_tol = int((diff > tolerance).sum().sum())
    else:
        max_diff = 0.0
        over_tol = 0
    mask_cols = [c for c in master.columns if c.endswith("_present")]
    masks = pd.DataFrame(
        [
            {
                "Cột mask": m,
                "Ô có dữ liệu": int(master[m].sum()),
                "Tổng dòng": len(master),
                "Độ phủ (%)": round(100.0 * float(master[m].mean()), 1),
            }
            for m in mask_cols
        ]
    )
    return {
        "shape": master.shape,
        "cardinality": cardinality,
        "same_keys": panel[keys].sort_values(keys).reset_index(drop=True).equals(
            master[keys].sort_values(keys).reset_index(drop=True)
        ),
        "max_shared_diff": max_diff,
        "cells_over_tolerance": over_tol,
        "masks": masks,
    }
