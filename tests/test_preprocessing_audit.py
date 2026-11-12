"""Kiểm tra audit tiền xử lý: phát hiện lỗi trên khung nhỏ và smoke trên panel thật."""

import numpy as np
import pandas as pd

from scripts.papi_pred_common import load_panel
from scripts.preprocessing_audit import (
    duplicate_key_rows,
    join_cardinality,
    missing_window_summary,
    name_conflicts,
    outlier_summary,
    scaler_audit,
    score_range_violations,
)


def test_duplicate_key_rows_returns_every_copy():
    frame = pd.DataFrame(
        {
            "province_code": [1, 1, 1, 2],
            "year": [2020, 2020, 2021, 2020],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )

    found = duplicate_key_rows(frame)

    assert len(found) == 2
    assert found["province_code"].tolist() == [1, 1]


def test_join_cardinality_detects_many_to_many():
    many = pd.DataFrame({"province_code": [1, 1], "year": [2020, 2020]})
    unique = pd.DataFrame({"province_code": [1], "year": [2020]})

    assert join_cardinality(many, many) == "many_to_many"
    assert join_cardinality(many, unique) == "many_to_one"
    assert join_cardinality(unique, many) == "one_to_many"
    assert join_cardinality(unique, unique) == "one_to_one"


def test_scaler_audit_flags_scaler_fitted_on_all_years():
    rows = []
    for year in (2011, 2012, 2013, 2014):
        for province_code in range(1, 5):
            # Năm 2014 nằm sau cutoff và lệch hẳn — nếu scaler học cả 2014 thì
            # mean/scale không thể khớp thống kê lịch sử.
            offset = 0.0 if year <= 2013 else 10.0
            rows.append(
                {"province_code": province_code, "year": year, "x": 1.0 + province_code + offset}
            )
    panel = pd.DataFrame(rows)
    train = panel[panel.year <= 2013]

    honest = scaler_audit(
        panel, ["x"], 2013, [train.x.mean()], [train.x.std(ddof=0)]
    )
    leaked = scaler_audit(
        panel, ["x"], 2013, [panel.x.mean()], [panel.x.std(ddof=0)]
    )

    assert not honest.leaked
    assert honest.max_mean_diff == 0.0
    assert leaked.leaked
    assert leaked.max_mean_shift_all_years > 0.5


def test_missing_window_summary_ignores_columns_outside_their_window():
    panel = pd.DataFrame(
        {
            "province_code": [1, 2],
            "year": [2011, 2011],
            "d1": [1.0, np.nan],
            "d7": [np.nan, np.nan],
        }
    )
    metadata = pd.DataFrame(
        {
            "cot": ["d1", "d7"],
            "nam_bat_dau": [2011, 2018],
            "nam_ket_thuc": [2024, 2024],
        }
    )

    summary = missing_window_summary(panel, metadata)

    assert summary.loc[0, "active_columns"] == 1
    assert summary.loc[0, "missing"] == 1
    assert summary.loc[0, "rows_with_missing"] == 1


def test_name_conflicts_reports_bad_name_and_unknown_code():
    panel = pd.DataFrame(
        {
            "province_code": [1, 2, 2],
            "province_vi": ["Hà Nội X", "Hà Giang", "Hà Giang"],
            "province_ascii": ["Ha Noi", "Ha Giang", "Ha Giang"],
        }
    )
    crosswalk = pd.DataFrame(
        {
            "province_code": [1],
            "province_vi": ["Hà Nội"],
            "province_ascii": ["Ha Noi"],
        }
    )

    conflicts = name_conflicts(panel, crosswalk)
    checks = set(conflicts["check"])

    assert "province_vi" in checks
    assert "missing_in_crosswalk" in checks


def test_score_range_violations_flags_value_outside_metadata_scale():
    panel = pd.DataFrame(
        {"province_code": [1, 2], "year": [2020, 2020], "d1": [5.0, 11.0]}
    )
    metadata = pd.DataFrame(
        {
            "cot": ["d1"],
            "thang_2011_2020": ["1-10 điểm"],
            "thang_2021_2024": ["1-10 điểm"],
            "nam_doi_thang": [np.nan],
            "nam_bat_dau": [2011],
            "nam_ket_thuc": [2024],
        }
    )

    violations = score_range_violations(panel, metadata)

    assert len(violations) == 1
    assert int(violations.iloc[0]["n_bad"]) == 1
    assert violations.iloc[0]["max_bad"] == 11.0


def test_outlier_summary_flags_isolated_extreme_value():
    frame = pd.DataFrame({"x": [1.0] * 20 + [50.0]})

    flags = outlier_summary(frame, ["x"])

    assert int(flags["flagged"].sum()) == 1
    assert flags.iloc[0]["column"] == "x"


def test_real_panel_has_unique_keys_and_63_provinces():
    panel = load_panel()

    assert len(duplicate_key_rows(panel)) == 0
    assert panel["province_code"].nunique() == 63
    assert panel["year"].nunique() == 14
