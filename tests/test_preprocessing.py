"""Kiểm thử toàn diện cho module tiền xử lý src/preprocessing.py."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from preprocessing import (
    ALLOWLIST_FEATURES,
    DEFAULT_CUTOFF_YEAR,
    PREPROCESSING_PIPELINE,
    STING_FEATURES,
    analyze_missingness,
    check_external_integration,
    count_range_violations,
    feature_selection_summary,
    flag_outliers_zscore,
    load_crosswalk,
    lookup_code,
    norm_name,
    run_preprocessing_pipeline,
    run_sting_preprocessing_experiments,
    scale_audit,
    score_columns,
    step_check_consistency,
    step_clean_codes_and_zeros,
    step_deduplicate,
    step_flag_outliers,
    step_integrate_panel,
    step_select_and_scale,
    to_float,
)

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_PATH = (
    ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
)


def _sample_metadata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cot": "sd_4_2",
                "thang_2011_2020": "0.25-2.5 điểm",
                "thang_2021_2024": "0.25-2.5 điểm",
                "nam_doi_thang": np.nan,
                "nam_bat_dau": 2011,
                "nam_ket_thuc": 2024,
            },
            {
                "cot": "sd_6_1",
                "thang_2011_2020": "0.25-2.5 điểm",
                "thang_2021_2024": "0.25-2.5 điểm",
                "nam_doi_thang": np.nan,
                "nam_bat_dau": 2011,
                "nam_ket_thuc": 2024,
            },
            {
                "cot": "d7",
                "thang_2011_2020": "1-10 điểm",
                "thang_2021_2024": "1-10 điểm",
                "nam_doi_thang": np.nan,
                "nam_bat_dau": 2018,
                "nam_ket_thuc": 2024,
            },
        ]
    )


def _sample_ctx(raw_df: pd.DataFrame) -> dict:
    ascii_to_code, code_to_province = load_crosswalk(CROSSWALK_PATH)
    codes = raw_df["province_code"].dropna().astype(int).unique() if "province_code" in raw_df else [1, 2]
    return {
        "root": ROOT,
        "raw": raw_df,
        "crosswalk_maps": (ascii_to_code, code_to_province),
        "crosswalk_codes": codes,
        "metadata": _sample_metadata(),
        "score_cols": score_columns(raw_df),
        "features": list(STING_FEATURES),
        "cutoff_year": 2023,
        "z_threshold": 3.0,
        "log": [],
    }


def test_real_pipeline_matches_locked_panel_and_scaler():
    state = run_preprocessing_pipeline(ROOT)
    assert [name for name, _ in PREPROCESSING_PIPELINE] == [
        "Deduplication",
        "Missing & Zero Convention",
        "Consistency & Scale Audit",
        "Outlier Flagging",
        "Integration & Ordering",
        "Feature Selection & Scaling",
    ]
    assert len(state["log"]) == 6
    ref = pd.read_csv(ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv")
    pd.testing.assert_frame_equal(
        state["panel"],
        ref.sort_values(["province_code", "year"]).reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert state["dedup_stats"] == {"exact_duplicates": 0, "key_duplicates": 0, "rows": 882}
    assert state["missing_summary"]["total_zeros"] == 109
    assert state["missing_summary"]["total_missing"] == 4649
    assert state["missing_summary"]["structural_missing"] == 4284
    assert state["missing_summary"]["in_window_missing"] == 365
    assert state["missing_summary"]["in_window_rows"] == 13
    assert state["consistency_stats"] == {
        "code_mismatch": 0,
        "range_violations": 0,
        "scale_flagged_count": 23,
    }
    assert state["outlier_stats"]["panel_cells"] == 122
    assert state["outlier_stats"]["train_feature_rows"] == 7
    assert state["X_train"].shape == (808, 2)
    assert state["X_holdout"].shape == (61, 2)

    scaler_json = json.loads((ROOT / "models" / "sting_predict_scaler.json").read_text(encoding="utf-8"))
    np.testing.assert_allclose(state["scaler"].mean_, scaler_json["mean"], atol=1e-12)
    np.testing.assert_allclose(state["scaler"].scale_, scaler_json["scale"], atol=1e-12)


def test_helpers_norm_lookup_and_score_columns():
    assert norm_name("Ba Ria - Vung Tau") == "bariavungtau"
    assert np.isnan(to_float("  "))
    assert to_float("1,25") == 125.0
    assert to_float("1.5") == 1.5
    ascii_to_code, _ = load_crosswalk(CROSSWALK_PATH)
    assert lookup_code("TT-Hue", ascii_to_code) == lookup_code("Thua Thien Hue", ascii_to_code)
    assert np.isnan(lookup_code(None, ascii_to_code))
    df = pd.DataFrame(columns=["year", "sd_6_1", "d2", "sd_1_3", "d1"])
    assert score_columns(df) == ["d1", "d2", "sd_1_3", "sd_6_1"]


def test_step_deduplicate_drops_exact_and_rejects_key_collision_or_unknown_province():
    ascii_to_code, _ = load_crosswalk(CROSSWALK_PATH)
    ha_noi_code = ascii_to_code["hanoi"]
    raw_exact = pd.DataFrame(
        [
            {"province_ascii": "Ha Noi", "year": 2022, "sd_4_2": 1.8, "sd_6_1": 1.9},
            {"province_ascii": "Ha Noi", "year": 2022, "sd_4_2": 1.8, "sd_6_1": 1.9},
        ]
    )
    ctx = step_deduplicate(_sample_ctx(raw_exact))
    assert ctx["dedup_stats"]["exact_duplicates"] == 1
    assert len(ctx["clean"]) == 1
    assert int(ctx["clean"].iloc[0]["province_code"]) == ha_noi_code

    raw_conflict = pd.DataFrame(
        [
            {"province_ascii": "Ha Noi", "year": 2022, "sd_4_2": 1.8, "sd_6_1": 1.9},
            {"province_ascii": "Ha Noi", "year": 2022, "sd_4_2": 1.5, "sd_6_1": 1.9},
        ]
    )
    with pytest.raises(ValueError, match="trùng khóa"):
        step_deduplicate(_sample_ctx(raw_conflict))

    raw_unknown = pd.DataFrame(
        [{"province_ascii": "Tinh Khong Ton Tai", "year": 2022, "sd_4_2": 1.8, "sd_6_1": 1.9}]
    )
    with pytest.raises(ValueError, match="map được"):
        step_deduplicate(_sample_ctx(raw_unknown))


def test_step_clean_codes_and_zeros_preserves_nan_and_splits_structural_missing():
    raw = pd.DataFrame(
        [
            {"province_code": 1, "province_ascii": "Ha Noi", "year": 2015, "sd_4_2": 0.0, "sd_6_1": 1.8, "d7": np.nan},
            {"province_code": 2, "province_ascii": "Ha Giang", "year": 2020, "sd_4_2": 1.7, "sd_6_1": np.nan, "d7": 7.1},
        ]
    )
    ctx = step_deduplicate(_sample_ctx(raw))
    ctx = step_clean_codes_and_zeros(ctx)
    assert pd.isna(ctx["clean"].iloc[0]["sd_4_2"])
    assert pd.isna(ctx["clean"].iloc[1]["sd_6_1"])
    miss = ctx["missing_summary"]
    assert miss["total_zeros"] == 1
    assert miss["structural_missing"] == 1  # d7 ở 2015 ngoài cửa sổ 2018–2024
    assert miss["in_window_missing"] == 2  # sd_4_2 ở 2015 và sd_6_1 ở 2020
    assert miss["in_window_rows"] == 2

    empty_df = pd.DataFrame(columns=["province_code", "year", "sd_4_2"])
    assert analyze_missingness(empty_df, _sample_metadata(), ["sd_4_2"])["total_missing"] == 0


def test_step_check_consistency_detects_crosswalk_range_and_scale_audit_violations():
    base = pd.DataFrame(
        [
            {"province_code": 1, "province_ascii": "Ha Noi", "year": 2020, "sd_4_2": 1.8, "sd_6_1": 1.9},
            {"province_code": 2, "province_ascii": "Ha Giang", "year": 2020, "sd_4_2": 1.7, "sd_6_1": 1.8},
        ]
    )
    ctx = step_clean_codes_and_zeros(step_deduplicate(_sample_ctx(base)))
    ctx["crosswalk_codes"] = np.array([1, 999])
    with pytest.raises(ValueError, match="nhất quán"):
        step_check_consistency(ctx)

    bad_range = base.copy()
    bad_range.loc[0, "sd_4_2"] = 9.5  # vượt thang 0.25-2.5
    assert count_range_violations(bad_range, _sample_metadata()) == 1
    ctx_range = step_clean_codes_and_zeros(step_deduplicate(_sample_ctx(bad_range)))
    with pytest.raises(ValueError, match="nhất quán"):
        step_check_consistency(ctx_range)

    jump_rows = [
        {"province_code": 1, "province_ascii": "Ha Noi", "year": yr, "sd_4_2": 1.0 if yr < 2021 else 2.2, "sd_6_1": 1.9}
        for yr in range(2017, 2023)
    ]
    jump_df = pd.DataFrame(jump_rows)
    assert scale_audit(jump_df)[0][0] == "sd_4_2"
    ctx_jump = step_clean_codes_and_zeros(step_deduplicate(_sample_ctx(jump_df)))
    with pytest.raises(ValueError, match="nhảy thang"):
        step_check_consistency(ctx_jump)


def test_step_flag_outliers_preserves_rows_and_handles_constant_columns():
    df = pd.DataFrame({"x": [1.0] * 20 + [100.0], "const": [2.0] * 21})
    mask = flag_outliers_zscore(df, ["x", "const"], z_threshold=3.0)
    assert bool(mask["x"].iloc[-1])
    assert not mask["const"].any()

    rows = [
        {"province_code": i, "province_ascii": "Ha Noi", "year": 2020, "sd_4_2": 1.8 if i < 20 else 2.5, "sd_6_1": 1.9}
        for i in range(1, 21)
    ]
    ctx = _sample_ctx(pd.DataFrame(rows))
    ctx["clean"] = ctx["raw"].copy()
    ctx = step_flag_outliers(ctx)
    assert len(ctx["clean"]) == 20  # không xóa dòng
    assert ctx["outlier_stats"]["train_feature_rows"] == 1


def test_step_select_and_scale_prevents_holdout_leakage_and_handles_empty_holdout():
    rows = []
    for yr in (2021, 2022, 2023, 2024):
        for code in (1, 2, 4):
            rows.append(
                {
                    "province_code": code,
                    "year": yr,
                    "sd_4_2": 1.5 + 0.1 * code + (0.0 if yr <= 2023 else 50.0),
                    "sd_6_1": 1.7 + 0.05 * code,
                }
            )
    ctx_a = _sample_ctx(pd.DataFrame(rows))
    ctx_a["clean"] = ctx_a["raw"].copy()
    ctx_a["code_to_province"] = load_crosswalk(CROSSWALK_PATH)[1]
    ctx_a = step_integrate_panel(ctx_a)
    ctx_a = step_select_and_scale(ctx_a)

    rows_mut = pd.DataFrame(rows)
    rows_mut.loc[rows_mut["year"] == 2024, "sd_4_2"] = 9999.0
    ctx_b = _sample_ctx(rows_mut)
    ctx_b["clean"] = ctx_b["raw"].copy()
    ctx_b["code_to_province"] = load_crosswalk(CROSSWALK_PATH)[1]
    ctx_b = step_integrate_panel(ctx_b)
    ctx_b = step_select_and_scale(ctx_b)

    np.testing.assert_allclose(ctx_a["scaler"].mean_, ctx_b["scaler"].mean_)
    np.testing.assert_allclose(ctx_a["scaler"].scale_, ctx_b["scaler"].scale_)
    np.testing.assert_allclose(ctx_a["X_train"], ctx_b["X_train"])

    ctx_no_holdout = _sample_ctx(pd.DataFrame(rows)[lambda d: d["year"] <= 2023])
    ctx_no_holdout["clean"] = ctx_no_holdout["raw"].copy()
    ctx_no_holdout["code_to_province"] = load_crosswalk(CROSSWALK_PATH)[1]
    ctx_no_holdout = step_integrate_panel(ctx_no_holdout)
    ctx_no_holdout = step_select_and_scale(ctx_no_holdout)
    assert ctx_no_holdout["X_holdout"].shape == (0, 2)


def test_feature_selection_experiments_and_external_integration_on_real_panel():
    panel = pd.read_csv(ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv")
    fs_summary, corr = feature_selection_summary(panel, score_columns(panel), ALLOWLIST_FEATURES, DEFAULT_CUTOFF_YEAR)
    assert len(fs_summary) == 8
    assert not fs_summary["Bị cờ scale_audit"].any()
    assert corr.shape == (8, 8)

    exp_df, arts = run_sting_preprocessing_experiments(panel)
    assert len(exp_df) == 6
    assert int(exp_df.iloc[0]["Số dòng"]) == 808
    assert int(exp_df.iloc[1]["Số dòng"]) == 801
    assert int(exp_df.iloc[2]["Số dòng"]) == 819
    assert set(arts) == {"standard", "trimmed", "imputed", "raw", "minmax", "quantile"}

    ext = check_external_integration(panel, ROOT / "data" / "processed" / "external_master_63_2011_2024.csv")
    assert ext["shape"] == (882, 59)
    assert ext["cardinality"] == "one_to_one"
    assert ext["same_keys"]
    assert ext["cells_over_tolerance"] == 0
