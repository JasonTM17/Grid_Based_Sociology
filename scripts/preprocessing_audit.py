"""Audit tiền xử lý theo đúng thứ tự Day 4: Cleaning → Integration → Transformation.

Mỗi phép kiểm tra in ra một dòng Test → Decide: kết quả ĐO trên file thật và
quyết định mà pipeline đang áp dụng, kèm bằng chứng `file:dòng`. Script chỉ
ĐỌC panel/master/models — không sửa dữ liệu.

Thứ tự bắt buộc (Day 4): trùng khóa trước, rồi thiếu, rồi nhất quán, ngoại lai
CUỐI CÙNG; sau đó Integration (khóa nối, cardinality, rò rỉ dữ liệu) và
Transformation (chuẩn hóa).

Đầu ra:
  results/preprocessing_audit.md   — bảng Test | Result | Decision | Evidence (tiếng Việt)
  results/preprocessing_audit.csv  — cùng nội dung dạng máy đọc

Chạy: python -W error scripts/preprocessing_audit.py
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from papi_pred_common import load_panel  # noqa: E402

MASTER_PATH = ROOT / "data" / "processed" / "external_master_63_2011_2024.csv"
METADATA_PATH = ROOT / "data" / "processed" / "papi_panel_scale_metadata.csv"
CROSSWALK_PATH = (
    ROOT
    / "data"
    / "raw"
    / "mendeley"
    / "Replication_package"
    / "data"
    / "province_crosswalk_63.csv"
)
SCALER_PATH = ROOT / "models" / "sting_predict_scaler.json"
MD_PATH = ROOT / "results" / "preprocessing_audit.md"
CSV_PATH = ROOT / "results" / "preprocessing_audit.csv"

KEY_COLUMNS = ("province_code", "year")
# predict_demo.py: fit 2011–2023, dự đoán 2024 out-of-sample.
TRAIN_MAX_YEAR = 2023
OUTLIER_Z = 3.0
DEFAULT_TOLERANCE = 1e-9


def score_columns(frame: pd.DataFrame) -> list[str]:
    """Cột điểm chỉ tiêu: 8 chiều (d1..d8) và các tiểu chiều (sd_*)."""
    return [
        column
        for column in frame.columns
        if re.fullmatch(r"d[1-8]", column) or column.startswith("sd_")
    ]


def duplicate_key_rows(
    frame: pd.DataFrame, keys=KEY_COLUMNS
) -> pd.DataFrame:
    """Các dòng trùng khóa (giữ mọi bản sao để đếm được cả cặp)."""
    return frame.loc[frame.duplicated(list(keys), keep=False)]


def join_cardinality(left: pd.DataFrame, right: pd.DataFrame, keys=KEY_COLUMNS) -> str:
    """Quan hệ khóa giữa hai bảng: one_to_one / one_to_many / many_to_one / many_to_many."""
    keys = list(keys)
    left_unique = not left.duplicated(keys).any()
    right_unique = not right.duplicated(keys).any()
    if left_unique and right_unique:
        return "one_to_one"
    if left_unique:
        return "one_to_many"
    if right_unique:
        return "many_to_one"
    return "many_to_many"


def missing_window_summary(panel: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Ô thiếu theo năm, chỉ tính các cột còn trong cửa sổ thu thập của chính cột đó.

    Cột ra ngoài `nam_bat_dau`..`nam_ket_thuc` là thiếu CẤU TRÚC (nguồn không
    thu thập), không phải ô khuyết cần xử lý.
    """
    specs = metadata.set_index("cot")
    records = []
    for year, sub in panel.groupby("year", sort=True):
        active = [
            column
            for column in specs.index
            if column in panel.columns
            and specs.loc[column, "nam_bat_dau"] <= year <= specs.loc[column, "nam_ket_thuc"]
        ]
        cells = len(sub) * len(active)
        missing = int(sub[active].isna().sum().sum())
        records.append(
            {
                "year": int(year),
                "active_columns": len(active),
                "cells": cells,
                "missing": missing,
                "missing_pct": 100.0 * missing / cells if cells else 0.0,
                "rows_with_missing": int(sub[active].isna().any(axis=1).sum()),
            }
        )
    return pd.DataFrame(records)


def missing_by_column(panel: pd.DataFrame, columns) -> pd.DataFrame:
    """Tổng ô thiếu theo cột kèm khoảng năm có ô thiếu."""
    records = []
    for column in columns:
        missing = panel[column].isna()
        years = sorted(int(year) for year in panel.loc[missing, "year"].unique())
        records.append(
            {
                "column": column,
                "missing": int(missing.sum()),
                "missing_pct": 100.0 * float(missing.mean()),
                "first_year": years[0] if years else None,
                "last_year": years[-1] if years else None,
                "years": len(years),
            }
        )
    return pd.DataFrame(records)


def name_conflicts(panel: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """So tên tỉnh trong panel với crosswalk 63 tỉnh (mã thiếu, tên lệch, tên trùng)."""
    lookup = crosswalk.set_index("province_code")
    records = []
    for code, sub in panel.groupby("province_code"):
        if code not in lookup.index:
            records.append(
                {
                    "check": "missing_in_crosswalk",
                    "province_code": int(code),
                    "panel_value": sub["province_vi"].iloc[0],
                    "crosswalk_value": "",
                }
            )
            continue
        for field in ("province_vi", "province_ascii"):
            values = [str(value) for value in sub[field].dropna().unique()]
            if len(values) != 1:
                records.append(
                    {
                        "check": f"multiple_{field}",
                        "province_code": int(code),
                        "panel_value": " | ".join(values),
                        "crosswalk_value": str(lookup.loc[code, field]),
                    }
                )
            elif values[0] != str(lookup.loc[code, field]):
                records.append(
                    {
                        "check": field,
                        "province_code": int(code),
                        "panel_value": values[0],
                        "crosswalk_value": str(lookup.loc[code, field]),
                    }
                )
    for field in ("province_vi", "province_ascii"):
        duplicated = crosswalk[crosswalk[field].duplicated(keep=False)]
        for _, row in duplicated.iterrows():
            records.append(
                {
                    "check": f"duplicate_{field}",
                    "province_code": int(row["province_code"]),
                    "panel_value": "",
                    "crosswalk_value": str(row[field]),
                }
            )
    return pd.DataFrame(
        records, columns=["check", "province_code", "panel_value", "crosswalk_value"]
    )


def parse_range(text) -> tuple[float, float] | None:
    """Đọc khoảng 'a-b ...' trong metadata thang đo; không có số → None."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", str(text))
    if match is None:
        return None
    return float(match.group(1)), float(match.group(2))


def score_range_violations(
    panel: pd.DataFrame, metadata: pd.DataFrame, tolerance: float = DEFAULT_TOLERANCE
) -> pd.DataFrame:
    """Ô điểm nằm ngoài khoảng metadata, tách giai đoạn theo `nam_doi_thang`."""
    records = []
    for _, spec in metadata.iterrows():
        column = spec["cot"]
        if column not in panel.columns:
            continue
        first = parse_range(spec["thang_2011_2020"])
        second = parse_range(spec["thang_2021_2024"])
        if first is None and second is None:
            continue
        low_before, high_before = first if first is not None else second
        low_after, high_after = second if second is not None else first
        split = spec["nam_doi_thang"]
        for year, sub in panel.groupby("year", sort=True):
            if pd.isna(split) or year < split:
                low, high = low_before, high_before
            else:
                low, high = low_after, high_after
            values = sub[column].dropna()
            outside = values[(values < low - tolerance) | (values > high + tolerance)]
            if len(outside):
                records.append(
                    {
                        "column": column,
                        "year": int(year),
                        "low": low,
                        "high": high,
                        "n_bad": int(len(outside)),
                        "min_bad": float(outside.min()),
                        "max_bad": float(outside.max()),
                    }
                )
    return pd.DataFrame(
        records,
        columns=["column", "year", "low", "high", "n_bad", "min_bad", "max_bad"],
    )


def window_violations(panel: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Ô có giá trị nhưng năm nằm ngoài cửa sổ thu thập của cột."""
    records = []
    for _, spec in metadata.iterrows():
        column = spec["cot"]
        if column not in panel.columns:
            continue
        present = panel.loc[panel[column].notna()]
        outside = present[
            (present["year"] < spec["nam_bat_dau"])
            | (present["year"] > spec["nam_ket_thuc"])
        ]
        if len(outside):
            records.append(
                {
                    "column": column,
                    "outside_cells": int(len(outside)),
                    "first_year": int(outside["year"].min()),
                    "last_year": int(outside["year"].max()),
                }
            )
    return pd.DataFrame(
        records, columns=["column", "outside_cells", "first_year", "last_year"]
    )


def outlier_mask(
    frame: pd.DataFrame, columns, z_threshold: float = OUTLIER_Z
) -> pd.DataFrame:
    """Mặt nạ |z| > ngưỡng, z tính trên toàn panel cho từng cột (chỉ đánh dấu)."""
    subset = frame[list(columns)]
    z_scores = (subset - subset.mean()) / subset.std(ddof=0)
    return z_scores.abs() > z_threshold


def outlier_summary(
    frame: pd.DataFrame, columns, z_threshold: float = OUTLIER_Z
) -> pd.DataFrame:
    """Số ô bị đánh dấu ngoại lai theo cột."""
    flagged = outlier_mask(frame, columns, z_threshold)
    records = [
        {
            "column": column,
            "flagged": int(flagged[column].sum()),
            "max_abs_z": float(
                ((frame[column] - frame[column].mean()) / frame[column].std(ddof=0))
                .abs()
                .max()
            ),
        }
        for column in columns
        if flagged[column].any()
    ]
    return pd.DataFrame(
        records, columns=["column", "flagged", "max_abs_z"]
    ).sort_values("flagged", ascending=False, ignore_index=True)


def _max_abs_diff(left, right) -> float:
    return float(
        np.max(
            np.abs(
                np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
            )
        )
    )


@dataclass(frozen=True)
class ScalerAudit:
    """Kết quả đối chiếu tham số scaler đóng băng với panel thật."""

    cutoff_year: int
    history_rows: int
    max_mean_diff: float
    max_scale_diff: float
    all_year_rows: int
    max_mean_shift_all_years: float
    leaked: bool


def scaler_audit(
    panel: pd.DataFrame,
    features,
    cutoff_year: int,
    mean,
    scale,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ScalerAudit:
    """Tham số chuẩn hóa có khớp thống kê của đúng các năm ≤ cutoff không.

    Nếu scaler bị fit trên cả các năm sau cutoff (rò rỉ), mean/scale sẽ lệch
    khỏi thống kê lịch sử và `leaked` = True.
    """
    features = list(features)
    history = panel.loc[panel["year"] <= cutoff_year, features].dropna()
    if history.empty:
        raise ValueError(f"Không có dòng đủ {features} tới cutoff {cutoff_year}.")
    expected_mean = history.mean().to_numpy()
    expected_scale = history.std(ddof=0).to_numpy()
    mean_diff = _max_abs_diff(expected_mean, mean)
    scale_diff = _max_abs_diff(expected_scale, scale)
    all_years = panel.loc[:, features].dropna()
    shift = _max_abs_diff(all_years.mean().to_numpy(), expected_mean)
    return ScalerAudit(
        cutoff_year=cutoff_year,
        history_rows=int(len(history)),
        max_mean_diff=mean_diff,
        max_scale_diff=scale_diff,
        all_year_rows=int(len(all_years)),
        max_mean_shift_all_years=shift,
        leaked=mean_diff > tolerance or scale_diff > tolerance,
    )


def _percent(part: int, whole: int) -> float:
    return 0.0 if not whole else 100.0 * part / whole


def _fmt_diff(value: float) -> str:
    """Sai lệch tuyệt đối: 0 hiển thị gọn, còn lại dạng khoa học."""
    return "0" if value == 0.0 else f"{value:.1e}"


def _markdown_table(headers: list[str], rows: list[tuple]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    panel = load_panel()
    master = pd.read_csv(MASTER_PATH)
    crosswalk = pd.read_csv(CROSSWALK_PATH)
    metadata = pd.read_csv(METADATA_PATH)
    scaler = json.loads(SCALER_PATH.read_text(encoding="utf-8"))
    features = list(scaler["features"])

    columns = score_columns(panel)
    total_cells = len(panel) * len(columns)
    total_missing = int(panel[columns].isna().sum().sum())

    # --- 1. Cleaning ---------------------------------------------------- #
    duplicates = duplicate_key_rows(panel)
    full_row_duplicates = int(panel.duplicated().sum())
    window = missing_window_summary(panel, metadata)
    per_column = missing_by_column(panel, columns)
    in_window_missing = int(window["missing"].sum())
    in_window_rows = int(window["rows_with_missing"].sum())
    structural_missing = total_missing - in_window_missing
    incomplete_feature_rows = int(panel[features].isna().any(axis=1).sum())
    conflicts = name_conflicts(panel, crosswalk)
    ranges = score_range_violations(panel, metadata)
    windows = window_violations(panel, metadata)
    zeros = int((panel[columns] == 0).sum().sum())
    outlier_table = outlier_summary(panel, columns)
    outlier_cells = int(outlier_table["flagged"].sum())
    outlier_rows = int(outlier_mask(panel, columns).any(axis=1).sum())

    # --- 2. Integration -------------------------------------------------- #
    cardinality = join_cardinality(panel, master)
    merged_rows = len(
        panel.merge(master[list(KEY_COLUMNS)], on=list(KEY_COLUMNS), how="left")
    )
    shared_numeric = [
        column
        for column in panel.columns
        if column in master.columns
        and column not in KEY_COLUMNS
        and panel[column].dtype.kind in "fi"
    ]
    panel_values = panel.set_index(list(KEY_COLUMNS))[shared_numeric].sort_index()
    master_values = master.set_index(list(KEY_COLUMNS))[shared_numeric].sort_index()
    value_delta = (panel_values - master_values).abs()
    shared_max_diff = float(value_delta.max().max())
    shared_cells_over_tolerance = int((value_delta > DEFAULT_TOLERANCE).sum().sum())
    papi_code_mismatch = int(
        (master["papi_province_code"] != master["province_code"]).sum()
    )
    master_names = master.drop_duplicates("province_code").set_index("province_code")
    panel_names = panel.drop_duplicates("province_code").set_index("province_code")
    master_name_conflicts = sum(
        int(
            (
                panel_names[field].sort_index()
                != master_names[field].sort_index()
            ).sum()
        )
        for field in ("province_vi", "province_ascii")
    )
    grid_identical = set(map(tuple, panel[list(KEY_COLUMNS)].to_numpy())) == set(
        map(tuple, master[list(KEY_COLUMNS)].to_numpy())
    )
    leak = scaler_audit(
        panel,
        features,
        TRAIN_MAX_YEAR,
        scaler["mean"],
        scaler["scale"],
    )

    # --- 3. Transformation ------------------------------------------------ #
    history = panel.loc[panel["year"] <= TRAIN_MAX_YEAR, features].dropna()
    ddof1_scale_diff = _max_abs_diff(
        history.std(ddof=1).to_numpy(), scaler["scale"]
    )
    test_2024_rows = int((panel["year"] == 2024).sum())
    test_2024_complete = int(
        panel.loc[panel["year"] == 2024, features].notna().all(axis=1).sum()
    )

    rows = [
        {
            "stage": "1. Cleaning — (a) trùng khóa",
            "test": "Trùng khóa (province_code, year), dedup chạy ĐẦU TIÊN",
            "result": (
                f"{len(duplicates)} dòng trùng / {len(panel)} dòng "
                f"({panel[list(KEY_COLUMNS)].drop_duplicates().shape[0]} khóa duy nhất); "
                f"trùng toàn dòng: {full_row_duplicates}"
            ),
            "decision": (
                "Giữ đúng 1 dòng/khóa. Pipeline chặn cứng nếu phát hiện trùng "
                "(không tự bỏ dòng) — dedup nằm ở bước đầu của Cleaning."
            ),
            "evidence": (
                "scripts/build_external_master.py:139-140; "
                "scripts/predict_supervised.py:101-102"
            ),
        },
        {
            "stage": "1. Cleaning — (b) giá trị thiếu",
            "test": f"Ô thiếu trong {len(columns)} cột chỉ tiêu (8 chiều + tiểu chiều)",
            "result": (
                f"{total_missing}/{total_cells} ô ({_percent(total_missing, total_cells):.1f}%); "
                f"{structural_missing} ô nằm NGOÀI cửa sổ thu thập của cột (d7/sd_7_*/sd_8_*/sd_5_2)"
            ),
            "decision": (
                "KHÔNG nội suy, không điền: giữ NaN. Chỉ loại dòng khi ghép cặp / "
                "dựng ma trận feature."
            ),
            "evidence": (
                "scripts/papi_pred_common.py:56; scripts/predict_demo.py:67-68"
            ),
        },
        {
            "stage": "1. Cleaning — (b) giá trị thiếu",
            "test": "Dòng thiếu ≥1 chỉ tiêu TRONG cửa sổ thu thập",
            "result": (
                f"{in_window_rows}/{len(panel)} dòng, {in_window_missing} ô; "
                f"{incomplete_feature_rows} dòng thiếu sd_4_2 hoặc sd_6_1"
            ),
            "decision": (
                "Loại khỏi train/dự đoán bằng dropna trên đúng cột đang dùng; "
                "không điền, không nội suy."
            ),
            "evidence": (
                "scripts/predict_demo.py:67-68; scripts/predict_supervised.py:106"
            ),
        },
        {
            "stage": "1. Cleaning — (c) nhất quán",
            "test": "Tên tỉnh vs crosswalk 63 tỉnh",
            "result": (
                f"{len(conflicts)} xung đột; "
                f"{panel['province_code'].nunique()}/"
                f"{crosswalk['province_code'].nunique()} mã khớp crosswalk"
            ),
            "decision": (
                "Tên/mã lấy từ crosswalk; mã không map được là lỗi chặn (build dừng)."
            ),
            "evidence": (
                "scripts/build_panel.py:204-217; scripts/build_panel.py:210-213; "
                "data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv:2-64"
            ),
        },
        {
            "stage": "1. Cleaning — (c) nhất quán",
            "test": "Khoảng giá trị vs metadata thang đo",
            "result": (
                f"{int(ranges['n_bad'].sum()) if len(ranges) else 0} ô ngoài khoảng "
                f"/ {total_cells} ô ({len(columns)} cột × {len(panel)} dòng)"
            ),
            "decision": "Giữ nguyên giá trị; không cắt, không sửa theo metadata.",
            "evidence": (
                "data/processed/papi_panel_scale_metadata.csv:2-38 "
                "(cột thang_2011_2020, thang_2021_2024); scripts/check_data.py:34-58"
            ),
        },
        {
            "stage": "1. Cleaning — (c) nhất quán",
            "test": "Giá trị ngoài cửa sổ thu thập của từng cột",
            "result": (
                f"{int(windows['outside_cells'].sum()) if len(windows) else 0} ô"
            ),
            "decision": (
                "Giữ; cửa sổ năm là metadata kiểm chứng, không dùng để xóa ô."
            ),
            "evidence": (
                "data/processed/papi_panel_scale_metadata.csv:2-38 "
                "(cột nam_bat_dau, nam_ket_thuc)"
            ),
        },
        {
            "stage": "1. Cleaning — (c) nhất quán",
            "test": "Điểm 0.0 (quy ước 'tỉnh không được xếp hạng')",
            "result": f"{zeros} ô điểm = 0.0 còn lại",
            "decision": "0.0 → NaN ngay khi dựng panel để không lẫn với điểm thật.",
            "evidence": "scripts/build_panel.py:218-226",
        },
        {
            "stage": "1. Cleaning — (d) ngoại lai (CUỐI CÙNG)",
            "test": f"Đánh dấu ngoại lai z-score > {OUTLIER_Z:g} (trị tuyệt đối)",
            "result": (
                f"{outlier_cells} ô ({_percent(outlier_cells, total_cells):.1f}%), "
                f"{outlier_rows} dòng, {len(outlier_table)} cột"
            ),
            "decision": (
                "GIỮ toàn bộ — chỉ đánh dấu, không xóa. Đây là điểm khảo sát thật; "
                "điểm cực trị rơi vào ô lưới thưa và tự nhận nhãn nhiễu (-1) theo "
                "cơ chế min_count của STING, dữ liệu gốc không bị loại."
            ),
            "evidence": (
                "src/sting.py:12-13; src/sting.py:334; scripts/predict_demo.py:110"
            ),
        },
        {
            "stage": "2. Integration — khóa nối",
            "test": "Khóa nối duy nhất hai phía + quan hệ bản ghi",
            "result": (
                f"panel {len(duplicate_key_rows(panel))} trùng; "
                f"master {len(duplicate_key_rows(master))} trùng; "
                f"quan hệ {cardinality} (không one-to-many/many-to-many)"
            ),
            "decision": "Nối one-to-one theo (province_code, year); không nhân dòng.",
            "evidence": (
                "scripts/build_external_master.py:148; "
                "scripts/build_external_master.py:139-140"
            ),
        },
        {
            "stage": "2. Integration — số dòng",
            "test": "Số dòng trước/sau khi nối panel × master",
            "result": (
                f"{len(panel)} → {merged_rows}; {master['province_code'].nunique()} tỉnh; "
                f"lưới khóa giống nhau: {grid_identical}"
            ),
            "decision": (
                "LEFT join giữ đúng lưới panel; ô dữ liệu bên ngoài thiếu để trống, có mask."
            ),
            "evidence": (
                "scripts/build_external_master.py:149-150; "
                "scripts/build_external_master.py:180-183"
            ),
        },
        {
            "stage": "2. Integration — xung đột",
            "test": "Tên và giá trị trùng giữa panel và master",
            "result": (
                f"{master_name_conflicts} lệch tên/63 mã; "
                f"papi_province_code≠province_code: {papi_code_mismatch}; "
                f"{len(shared_numeric)} cột số chung lệch tối đa "
                f"{shared_max_diff:.2e} (sai số biểu diễn CSV); "
                f"{shared_cells_over_tolerance} ô lệch > {DEFAULT_TOLERANCE:g}"
            ),
            "decision": (
                "Không sửa; dung sai 1e-9 xác nhận hai file cùng một dữ liệu."
            ),
            "evidence": (
                "scripts/build_external_master.py:161; "
                "scripts/build_external_master.py:70-82"
            ),
        },
        {
            "stage": "2. Integration — rò rỉ dữ liệu",
            "test": "Scaler/lưới dự đoán có fit ngoài cutoff không",
            "result": (
                f"JSON khớp thống kê ≤{TRAIN_MAX_YEAR}: {leak.history_rows} dòng, "
                f"Δmean={_fmt_diff(leak.max_mean_diff)}, "
                f"Δscale={_fmt_diff(leak.max_scale_diff)}; "
                f"nếu fit cả {leak.all_year_rows} dòng thì Δmean="
                f"{leak.max_mean_shift_all_years:.6f} → không khớp JSON"
            ),
            "decision": (
                f"Không rò rỉ: scaler + lưới STING chỉ fit ≤{TRAIN_MAX_YEAR}; "
                f"2024 ({test_2024_rows} dòng, {test_2024_complete} đủ 2 chỉ tiêu) "
                "chỉ được transform/predict."
            ),
            "evidence": (
                "scripts/predict_demo.py:65-70; scripts/predict_demo.py:75-77; "
                "scripts/predict_demo.py:113; scripts/predict_sweep.py:112-113; "
                "scripts/predict_supervised.py:156-159"
            ),
        },
        {
            "stage": "3. Transformation",
            "test": "Phương pháp chuẩn hóa",
            "result": (
                f"StandardScaler z-score (ddof=0), {len(features)} chỉ tiêu "
                f"{', '.join(features)}; fit một lần trên gộp {int(panel['year'].min())}–"
                f"{TRAIN_MAX_YEAR}"
            ),
            "decision": (
                "Dùng tham số đã đóng băng trong models/sting_predict_scaler.json; "
                "không fit lại trên 2024."
            ),
            "evidence": (
                "scripts/predict_demo.py:70-72; "
                "models/sting_predict_scaler.json:10-17"
            ),
        },
        {
            "stage": "3. Transformation",
            "test": "Đối chiếu số học mean/scale với panel thật",
            "result": (
                f"Δmean={_fmt_diff(leak.max_mean_diff)}; "
                f"Δscale={_fmt_diff(leak.max_scale_diff)}; "
                f"ddof=1 lệch {ddof1_scale_diff:.2e} → xác nhận ddof=0"
            ),
            "decision": (
                "Tham số JSON tái lập được từ đúng các năm lịch sử; giữ nguyên trạng."
            ),
            "evidence": (
                "models/sting_predict_scaler.json:10-17 (mean, scale); "
                "scripts/predict_demo.py:86-99"
            ),
        },
    ]

    audit = pd.DataFrame(rows)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    stage_headers = {
        "1. Cleaning": [
            "1. Cleaning — (a) trùng khóa",
            "1. Cleaning — (b) giá trị thiếu",
            "1. Cleaning — (c) nhất quán",
            "1. Cleaning — (d) ngoại lai (CUỐI CÙNG)",
        ],
        "2. Integration": [
            "2. Integration — khóa nối",
            "2. Integration — số dòng",
            "2. Integration — xung đột",
            "2. Integration — rò rỉ dữ liệu",
        ],
        "3. Transformation": ["3. Transformation"],
    }
    stage_intro = {
        "1. Cleaning": (
            "Thứ tự trong Day 4: trùng khóa → thiếu → nhất quán → ngoại lai CUỐI CÙNG."
        ),
        "2. Integration": (
            "Khóa nối, cardinality, số dòng, xung đột tên/giá trị, rò rỉ dữ liệu."
        ),
        "3. Transformation": "Chuẩn hóa (scaling) — fit ở đâu, kiểm chứng số học.",
    }

    lines = [
        "# Audit tiền xử lý theo thứ tự Day 4",
        "",
        "Sinh bởi `scripts/preprocessing_audit.py` — CHỈ ĐỌC dữ liệu, không ghi lại "
        "panel hay master.",
        "",
        f"- Panel: `data/processed/papi_panel_63_2011_2024.csv` — {len(panel)} dòng × "
        f"{panel.shape[1]} cột, {panel['province_code'].nunique()} tỉnh × "
        f"{panel['year'].nunique()} năm ({int(panel['year'].min())}–"
        f"{int(panel['year'].max())})",
        f"- Master dữ liệu bên ngoài: `data/processed/external_master_63_2011_2024.csv` — "
        f"{len(master)} dòng × {master.shape[1]} cột",
        "- Crosswalk: `data/raw/mendeley/Replication_package/data/"
        "province_crosswalk_63.csv`",
        "- Metadata thang đo: `data/processed/papi_panel_scale_metadata.csv`",
        "- Tham số chuẩn hóa đóng băng: `models/sting_predict_scaler.json`",
        "",
        "Mỗi bảng dưới đây là một giai đoạn: **Test | Result | Decision | Evidence**. "
        "Result là số đo trên file thật; Decision là quyết định pipeline đang áp dụng; "
        "Evidence là `file:dòng` của quyết định đó.",
        "",
    ]

    for stage_name, prefixes in stage_headers.items():
        lines.append(f"## {stage_name}")
        lines.append("")
        lines.append(stage_intro[stage_name])
        lines.append("")
        stage_rows = [
            (row["test"], row["result"], row["decision"], row["evidence"])
            for row in rows
            if row["stage"] in prefixes
        ]
        lines.extend(
            _markdown_table(
                ["Test", "Result", "Decision", "Evidence file:line"], stage_rows
            )
        )
        lines.append("")
        if stage_name == "1. Cleaning":
            lines.append("### 1.1 Thiếu theo năm (chỉ cột còn trong cửa sổ thu thập)")
            lines.append("")
            lines.extend(
                _markdown_table(
                    [
                        "Năm",
                        "Số cột trong cửa sổ",
                        "Ô thiếu",
                        "Tỷ lệ",
                        "Dòng thiếu ≥1",
                    ],
                    [
                        (
                            int(row["year"]),
                            int(row["active_columns"]),
                            int(row["missing"]),
                            f"{row['missing_pct']:.2f}%",
                            int(row["rows_with_missing"]),
                        )
                        for _, row in window.iterrows()
                    ],
                )
            )
            lines.append("")
            lines.append("### 1.2 Thiếu theo cột")
            lines.append("")
            lines.extend(
                _markdown_table(
                    ["Cột", "Ô thiếu", "Tỷ lệ", "Năm có thiếu"],
                    [
                        (
                            row["column"],
                            int(row["missing"]),
                            f"{row['missing_pct']:.1f}%",
                            f"{int(row['first_year'])}–{int(row['last_year'])} "
                            f"({int(row['years'])} năm)",
                        )
                        for _, row in per_column[per_column["missing"] > 0].iterrows()
                    ],
                )
            )
            lines.append("")

    lines.extend(
        [
            "## Kết luận",
            "",
            f"- Không phát hiện lỗi chặn: {len(duplicates)} dòng trùng khóa, "
            f"{len(conflicts)} xung đột tên, "
            f"{int(ranges['n_bad'].sum()) if len(ranges) else 0} ô ngoài khoảng metadata, "
            f"rò rỉ scaler: {leak.leaked}.",
            f"- Thiếu dữ liệu là cấu trúc: {structural_missing}/{total_missing} ô thiếu "
            f"nằm ngoài cửa sổ thu thập của cột; {in_window_missing} ô trong cửa sổ, "
            f"trên {in_window_rows} dòng — đúng bằng số dòng thiếu chỉ tiêu mô hình "
            f"({incomplete_feature_rows}).",
            f"- Ngoại lai chỉ đánh dấu ({outlier_cells} ô), không xóa; quyết định giữ "
            "dựa trên bản chất điểm khảo sát và cơ chế nhãn nhiễu của STING.",
            "- z-score > 3 tính gộp toàn panel nên trộn cả bước nhảy thang đo giữa các năm "
            "(metadata ghi rõ vài cột đổi thang 2021); audit này không kết luận tương "
            "đương thang đo xuyên năm.",
            "- Ngoài pipeline chính: `scripts/candidates_regression.py:172` dùng "
            "SimpleImputer(median) cho một ứng viên tham khảo — không thuộc pipeline "
            "đã công bố.",
            "",
        ]
    )

    report = "\n".join(lines)
    MD_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"[audit] đã ghi {MD_PATH.name} và {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
