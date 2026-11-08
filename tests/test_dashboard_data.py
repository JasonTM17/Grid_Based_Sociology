import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from scripts.dashboard_data import (
    POVERTY_OVERLAP_YEARS,
    DashboardDataError,
    ensure_external_pci_consistency,
    external_pci_group_stats,
    external_pci_tests,
    external_section_frame,
    filter_regression_holdout,
    format_p_value,
    format_poverty_window,
    load_dashboard_assets,
    load_external_validation_assets,
    load_poverty_assets,
    load_regression_models,
    prepare_external_pci_view,
    prepare_poverty_cluster_view,
    prepare_regression_holdout,
    prepare_sting_view,
    poverty_cluster_tests,
    poverty_noise_vs_c2,
    published_external_pci_tests,
    select_classification_model,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, REGRESSION_TARGET, ROOT


class DummyRegressor:
    def predict(self, values):
        return np.zeros(len(values), dtype=float)


def _make_regression_panel(provinces=(1, 2)):
    rows = []
    for code in provinces:
        origin = {
            "province_code": code,
            "province_vi": f"Province {code}",
            "year": 2023,
            **{f: 1.0 for f in REGRESSION_FEATURES},
        }
        target = {
            "province_code": code,
            "province_vi": f"Province {code}",
            "year": 2024,
            **{f: 2.0 for f in REGRESSION_FEATURES},
            REGRESSION_TARGET: 2.0,
        }
        rows.extend([origin, target])
    return pd.DataFrame(rows)


def test_sting_filtered_missing_counts_follow_visible_provinces():
    panel = pd.DataFrame(
        {
            "province_code": [1, 2, 3],
            "province_vi": ["A", "B", "C"],
            "year": [2024, 2024, 2024],
            "sd_4_2": [1.0, np.nan, 1.0],
            "sd_6_1": [1.0, 1.0, 1.0],
        }
    )
    assignments = pd.DataFrame(
        {
            "province_code": [1],
            "year": [2024],
            "pred_cluster": [0],
            "split": ["test"],
        }
    )

    missing_view, missing_counts = prepare_sting_view(
        panel, assignments, 2024, province_codes={2}, required_features=["sd_4_2", "sd_6_1"]
    )
    artifact_gap_view, artifact_gap_counts = prepare_sting_view(
        panel, assignments, 2024, province_codes={3}, required_features=["sd_4_2", "sd_6_1"]
    )

    assert missing_view.assignment_state.tolist() == ["Thiếu feature — chưa gán"]
    assert missing_view.cluster_label.tolist() == ["Thiếu feature — chưa gán"]
    assert missing_counts["filtered_rows"] == 1
    assert missing_counts["filtered_missing_feature_rows"] == 1
    assert missing_counts["filtered_unassigned_artifact_rows"] == 0
    assert artifact_gap_view.assignment_state.tolist() == ["Không có assignment trong artifact"]
    assert artifact_gap_view.cluster_label.tolist() == ["Không có assignment trong artifact"]
    assert artifact_gap_counts["filtered_rows"] == 1
    assert artifact_gap_counts["filtered_missing_feature_rows"] == 0
    assert artifact_gap_counts["filtered_unassigned_artifact_rows"] == 1


def test_classifier_selection_excludes_majority_baseline():
    metrics = pd.DataFrame(
        [
            {"task": "classification", "model": "majority (lớp đa số)", "value_cv": 0.99},
            {"task": "classification", "model": "logistic regression", "value_cv": 0.45},
            {"task": "classification", "model": "random forest", "value_cv": 0.40},
        ]
    )

    assert select_classification_model(metrics) == "logistic regression"


def test_sting_view_empty_and_nonmatching_filters():
    panel = pd.DataFrame(
        {
            "province_code": [1, 2],
            "province_vi": ["A", "B"],
            "year": [2024, 2024],
            "sd_4_2": [1.0, 2.0],
            "sd_6_1": [1.0, 2.0],
        }
    )
    assignments = pd.DataFrame(
        {
            "province_code": [1, 2],
            "year": [2024, 2024],
            "pred_cluster": [0, -1],
            "split": ["test", "test"],
        }
    )
    required_features = ["sd_4_2", "sd_6_1"]

    # Baseline: no filter (None)
    vis_all, counts_all = prepare_sting_view(
        panel, assignments, 2024, required_features, province_codes=None, cluster_codes=None
    )
    assert len(vis_all) == 2
    assert counts_all["filtered_rows"] == 2
    assert counts_all["source_rows"] == 2
    assert counts_all["noise_rows"] == 1
    assert counts_all["filtered_noise_rows"] == 1

    # Empty province filter: set()
    vis_empty_p, counts_empty_p = prepare_sting_view(
        panel, assignments, 2024, required_features, province_codes=set()
    )
    assert vis_empty_p.empty
    assert counts_empty_p["filtered_rows"] == 0
    assert counts_empty_p["filtered_noise_rows"] == 0
    assert counts_empty_p["filtered_missing_feature_rows"] == 0
    assert counts_empty_p["filtered_unassigned_artifact_rows"] == 0
    # Unfiltered aggregate counts remain based on the joined year frame
    assert counts_empty_p["source_rows"] == 2
    assert counts_empty_p["eligible_assignments"] == 2
    assert counts_empty_p["noise_rows"] == 1

    # Non-matching province filter: {999}
    vis_nomatch_p, counts_nomatch_p = prepare_sting_view(
        panel, assignments, 2024, required_features, province_codes={999}
    )
    assert vis_nomatch_p.empty
    assert counts_nomatch_p["filtered_rows"] == 0
    assert counts_nomatch_p["filtered_noise_rows"] == 0
    assert counts_nomatch_p["source_rows"] == 2

    # Empty cluster filter: set()
    vis_empty_c, counts_empty_c = prepare_sting_view(
        panel, assignments, 2024, required_features, cluster_codes=set()
    )
    assert vis_empty_c.empty
    assert counts_empty_c["filtered_rows"] == 0
    assert counts_empty_c["filtered_noise_rows"] == 0
    assert counts_empty_c["source_rows"] == 2
    assert counts_empty_c["noise_rows"] == 1

    # Non-matching cluster filter: {999}
    vis_nomatch_c, counts_nomatch_c = prepare_sting_view(
        panel, assignments, 2024, required_features, cluster_codes={999}
    )
    assert vis_nomatch_c.empty
    assert counts_nomatch_c["filtered_rows"] == 0
    assert counts_nomatch_c["filtered_noise_rows"] == 0
    assert counts_nomatch_c["source_rows"] == 2


def test_regression_holdout_empty_and_nonmatching_filters():
    panel = _make_regression_panel(provinces=(1, 2))
    assignments = pd.DataFrame(
        {
            "province_code": [1, 2],
            "year": [2023, 2023],
            "pred_cluster": [0, 1],
            "split": ["test", "test"],
        }
    )
    holdout, counts = prepare_regression_holdout(panel, assignments)
    assert counts["holdout_pairs"] == 2

    # Baseline: no filter
    vis_all, f_counts_all = filter_regression_holdout(
        holdout, province_codes=None, origin_clusters=None
    )
    assert len(vis_all) == 2
    assert f_counts_all["after_province_filter"] == 2
    assert f_counts_all["after_origin_cluster_filter"] == 2

    # Empty province filter set()
    vis_empty_p, f_counts_empty_p = filter_regression_holdout(holdout, province_codes=set())
    assert vis_empty_p.empty
    assert f_counts_empty_p["after_province_filter"] == 0
    assert f_counts_empty_p["after_origin_cluster_filter"] == 0
    assert f_counts_empty_p["holdout_pairs"] == 2

    # Non-matching province filter {999}
    vis_nomatch_p, f_counts_nomatch_p = filter_regression_holdout(holdout, province_codes={999})
    assert vis_nomatch_p.empty
    assert f_counts_nomatch_p["after_province_filter"] == 0
    assert f_counts_nomatch_p["after_origin_cluster_filter"] == 0

    # Empty cluster filter set()
    vis_empty_c, f_counts_empty_c = filter_regression_holdout(holdout, origin_clusters=set())
    assert vis_empty_c.empty
    assert f_counts_empty_c["after_province_filter"] == 2
    assert f_counts_empty_c["after_origin_cluster_filter"] == 0

    # Non-matching cluster filter {999}
    vis_nomatch_c, f_counts_nomatch_c = filter_regression_holdout(holdout, origin_clusters={999})
    assert vis_nomatch_c.empty
    assert f_counts_nomatch_c["after_province_filter"] == 2
    assert f_counts_nomatch_c["after_origin_cluster_filter"] == 0


def test_regression_holdout_noise_cluster_labeled_and_filtered():
    panel = _make_regression_panel(provinces=(1, 2))
    assignments = pd.DataFrame(
        {
            "province_code": [1, 2],
            "year": [2023, 2023],
            "pred_cluster": [-1, 0],
            "split": ["test", "test"],
        }
    )
    holdout, _ = prepare_regression_holdout(panel, assignments)
    row_noise = holdout.loc[holdout.province_code == 1].iloc[0]
    row_clean = holdout.loc[holdout.province_code == 2].iloc[0]

    assert row_noise.origin_cluster_2023 == -1
    assert row_noise.origin_cluster_label == "Nhiễu (-1)"
    assert row_clean.origin_cluster_label == "Cụm 0"

    # Filter with origin_clusters={-1} keeps only the noise row
    filtered_noise, f_counts_noise = filter_regression_holdout(holdout, origin_clusters={-1})
    assert len(filtered_noise) == 1
    assert filtered_noise.iloc[0].province_code == 1
    assert f_counts_noise["after_origin_cluster_filter"] == 1

    # Filter with origin_clusters={0} excludes the noise row
    filtered_clean, f_counts_clean = filter_regression_holdout(holdout, origin_clusters={0})
    assert len(filtered_clean) == 1
    assert filtered_clean.iloc[0].province_code == 2
    assert f_counts_clean["after_origin_cluster_filter"] == 1


def test_regression_holdout_asymmetric_models_raise_dashboard_error():
    panel = _make_regression_panel(provinces=(1,))
    assignments = pd.DataFrame(
        {
            "province_code": [1],
            "year": [2023],
            "pred_cluster": [0],
            "split": ["test"],
        }
    )
    expected_msg = "Cần truyền đồng thời cả hai model hồi quy hoặc không truyền model nào."

    with pytest.raises(DashboardDataError, match=expected_msg):
        prepare_regression_holdout(
            panel, assignments, ridge_model=DummyRegressor(), random_forest_model=None
        )

    with pytest.raises(DashboardDataError, match=expected_msg):
        prepare_regression_holdout(
            panel, assignments, ridge_model=None, random_forest_model=DummyRegressor()
        )


def test_missing_artifact_errors_contain_rebuild_commands(tmp_path):
    # 1. Missing panel -> python scripts/build_panel.py
    with pytest.raises(DashboardDataError, match=r"python scripts/build_panel\.py"):
        load_dashboard_assets(tmp_path)

    panel_file = tmp_path / "data" / "processed" / "papi_panel_63_2011_2024.csv"
    panel_file.parent.mkdir(parents=True, exist_ok=True)
    panel_file.write_text("province_code,year\n1,2024\n", encoding="utf-8")

    # 2. Missing config -> python scripts/predict_sweep.py
    with pytest.raises(DashboardDataError, match=r"python scripts/predict_sweep\.py"):
        load_dashboard_assets(tmp_path)

    config_file = tmp_path / "models" / "predict_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text('{"features": []}', encoding="utf-8")

    # 3. Missing assignments -> python scripts/predict_demo.py
    with pytest.raises(DashboardDataError, match=r"python scripts/predict_demo\.py"):
        load_dashboard_assets(tmp_path)

    assignments_file = tmp_path / "results" / "predict_all_years.csv"
    assignments_file.parent.mkdir(parents=True, exist_ok=True)
    assignments_file.write_text("province_code,year\n1,2024\n", encoding="utf-8")

    # 4. Missing metrics -> python scripts/predict_supervised.py
    with pytest.raises(DashboardDataError, match=r"python scripts/predict_supervised\.py"):
        load_dashboard_assets(tmp_path)

    # 5. Missing ridge model in load_regression_models -> python scripts/predict_supervised.py
    with pytest.raises(DashboardDataError, match=r"python scripts/predict_supervised\.py"):
        load_regression_models(tmp_path)

    # 6. Missing random forest model in load_regression_models -> python scripts/predict_supervised.py
    ridge_file = tmp_path / "models" / "sup_ridge.joblib"
    ridge_file.write_text("dummy", encoding="utf-8")
    with pytest.raises(DashboardDataError, match=r"python scripts/predict_supervised\.py"):
        load_regression_models(tmp_path)


def test_sting_view_ignores_phantom_provinces_in_assignments():
    panel = pd.DataFrame(
        {
            "province_code": [1],
            "province_vi": ["Tỉnh 1"],
            "year": [2024],
            "sd_4_2": [1.0],
            "sd_6_1": [2.0],
        }
    )
    # Province 999 exists only in assignments, not in panel
    assignments = pd.DataFrame(
        {
            "province_code": [1, 999],
            "year": [2024, 2024],
            "pred_cluster": [0, 1],
            "split": ["test", "test"],
        }
    )

    visible, counts = prepare_sting_view(
        panel, assignments, 2024, required_features=["sd_4_2", "sd_6_1"]
    )

    assert visible.province_code.tolist() == [1]
    assert 999 not in visible.province_code.values
    assert len(visible) == 1
    assert counts["source_rows"] == 1
    assert counts["filtered_rows"] == 1
    assert counts["eligible_assignments"] == 1


def test_regression_holdout_unassigned_origin_province():
    panel = _make_regression_panel(provinces=(1, 2))
    # Province 1 is assigned in 2023, Province 2 has no assignment row in 2023
    assignments = pd.DataFrame(
        {
            "province_code": [1],
            "year": [2023],
            "pred_cluster": [0],
            "split": ["test"],
        }
    )

    holdout, counts = prepare_regression_holdout(panel, assignments)

    assert counts["holdout_pairs"] == 2
    assert counts["missing_origin_cluster"] == 1

    row1 = holdout.loc[holdout.province_code == 1].iloc[0]
    row2 = holdout.loc[holdout.province_code == 2].iloc[0]

    assert row1.origin_cluster_2023 == 0
    assert row1.origin_cluster_label == "Cụm 0"

    assert pd.isna(row2.origin_cluster_2023)
    assert row2.origin_cluster_label == "Không có assignment trong artifact"


# --------------------------------------------------------------------- #
# Kiểm chứng ngoại lai — PCI · y tế 2020 · GRDP 2018–2024
# --------------------------------------------------------------------- #


def _make_pci_frame():
    # 2011–2022 đủ ô; (2022, tỉnh 4) thiếu điểm; 2023–2024 kiểu Top-30.
    return pd.DataFrame({
        "papi_province_code": [1, 2, 3, 4, 5, 6],
        "province_code": [1, 2, 3, 4, 5, 6],
        "province_ascii": ["A", "B", "C", "D", "E", "F"],
        "province_vi": ["Tỉnh A", "Tỉnh B", "Tỉnh C", "Tỉnh D", "Tỉnh E", "Tỉnh F"],
        "year": [2011, 2011, 2022, 2022, 2023, 2024],
        "pci_weighted_score": [50.0, 60.0, 55.0, np.nan, 70.0, 71.0],
        "source": ["pci"] * 6,
    })


def _make_external_assignments():
    # Tỉnh 999 chỉ tồn tại trong assignments (phantom) — phải bị bỏ qua.
    return pd.DataFrame({
        "province_code": [1, 2, 3, 5, 999],
        "year": [2011, 2011, 2022, 2023, 2011],
        "pred_cluster": [-1, 2, 2, -1, 0],
        "split": ["test"] * 5,
    })


def _validation_row(section, group, n="", note="", **cells):
    row = {
        "section": section, "group": group, "year": "", "n": n,
        "mean": "", "median": "", "std": "", "min": "", "max": "", "note": note,
    }
    row.update(cells)
    return row


def test_load_external_validation_assets_missing_files_point_to_rebuild(tmp_path):
    with pytest.raises(DashboardDataError, match=r"python scripts/external_validation\.py"):
        load_external_validation_assets(tmp_path)

    pci_file = tmp_path / "data" / "processed" / "external_pci_63_full.csv"
    pci_file.parent.mkdir(parents=True, exist_ok=True)
    _make_pci_frame().to_csv(pci_file, index=False, encoding="utf-8")

    with pytest.raises(DashboardDataError, match=r"python scripts/external_validation\.py"):
        load_external_validation_assets(tmp_path)


def _write_validation_csv(tmp_path):
    validation = pd.DataFrame([
        _validation_row("pci_2011_2022", "nhiễu (–1)", n=149, mean=59.798),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 9.0426; p = 6.93e-06"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", n=747, note="H = 31.7751; p = 5.84e-07"),
        _validation_row("pci_2011_2022", "eta squared", n=747, note="eta² = 0.0352 (SS giữa / SS tổng)"),
        _validation_row("pci_top30_2023_2024", "ANOVA F(1,56)", n=58, note="F = 0.8880; p = 0.35"),
        _validation_row("odm_health_2020", "nhiễu (–1)", n=6, year=2020, mean=0.00174),
        _validation_row("grdp_2018_2024", "cụm 2", n=58, year=2018, mean=60.36),
    ])
    path = tmp_path / "results" / "external_validation.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(path, index=False, encoding="utf-8")
    return validation


def test_load_external_validation_assets_validates_schema(tmp_path):
    pci_file = tmp_path / "data" / "processed" / "external_pci_63_full.csv"
    validation_file = tmp_path / "results" / "external_validation.csv"
    pci_file.parent.mkdir(parents=True, exist_ok=True)

    _make_pci_frame().drop(columns=["province_vi"]).to_csv(
        pci_file, index=False, encoding="utf-8"
    )
    _write_validation_csv(tmp_path)
    with pytest.raises(DashboardDataError, match="external_pci_63_full.csv thiếu cột"):
        load_external_validation_assets(tmp_path)

    _make_pci_frame().to_csv(pci_file, index=False, encoding="utf-8")
    ok = load_external_validation_assets(tmp_path)
    assert set(ok) == {"pci", "validation"}
    assert ok["pci"].province_vi.tolist() == _make_pci_frame().province_vi.tolist()

    _write_validation_csv(tmp_path).drop(columns=["note"]).to_csv(
        validation_file, index=False, encoding="utf-8"
    )
    with pytest.raises(DashboardDataError, match="external_validation.csv thiếu cột"):
        load_external_validation_assets(tmp_path)

    validation = _write_validation_csv(tmp_path)
    validation.loc[validation.section.ne("grdp_2018_2024")].to_csv(
        validation_file, index=False, encoding="utf-8"
    )
    with pytest.raises(DashboardDataError, match="external_validation.csv thiếu section"):
        load_external_validation_assets(tmp_path)

    pd.concat([_make_pci_frame(), _make_pci_frame().iloc[[0]]]).to_csv(
        pci_file, index=False, encoding="utf-8"
    )
    _write_validation_csv(tmp_path)
    with pytest.raises(DashboardDataError, match="PCI external có khóa trùng"):
        load_external_validation_assets(tmp_path)


def test_prepare_external_pci_view_counts_and_labels():
    pci = _make_pci_frame()
    assignments = _make_external_assignments()

    view, counts = prepare_external_pci_view(pci, assignments)
    assert counts["year_min"] == 2011
    assert counts["year_max"] == 2022
    assert counts["window_cells"] == 3  # 2011×2 + 2022×1; ô (2022, 4) thiếu điểm
    assert counts["missing_label_cells"] == 0
    assert counts["tested_points"] == 3
    assert counts["clusters"] == [-1, 2]
    assert counts["n_by_cluster"] == {-1: 1, 2: 2}
    assert view[["year", "province_code"]].values.tolist() == [
        [2011, 1], [2011, 2], [2022, 3],
    ]
    assert view.cluster_label.tolist() == ["Nhiễu (-1)", "Cụm 2", "Cụm 2"]
    assert view.pci_weighted_score.tolist() == [50.0, 60.0, 55.0]
    # Tỉnh 999 chỉ có trong assignments — không được lọt vào view
    assert 999 not in view.province_code.values

    top_view, top_counts = prepare_external_pci_view(pci, assignments, 2023, 2024)
    assert top_counts["window_cells"] == 2
    assert top_counts["missing_label_cells"] == 1  # tỉnh 6 năm 2024 không có nhãn
    assert top_counts["tested_points"] == 1
    assert top_counts["n_by_cluster"] == {-1: 1}
    assert top_view.cluster_label.tolist() == ["Nhiễu (-1)"]


def test_prepare_external_pci_view_rejects_bad_inputs():
    pci = _make_pci_frame()
    assignments = _make_external_assignments()

    duplicated_pci = pd.concat([pci, pci.iloc[[0]]])
    with pytest.raises(DashboardDataError, match="PCI external có khóa trùng"):
        prepare_external_pci_view(duplicated_pci, assignments)

    duplicated_assignments = pd.concat([assignments, assignments.iloc[[0]]])
    with pytest.raises(DashboardDataError, match="STING assignments có khóa trùng"):
        prepare_external_pci_view(pci, duplicated_assignments)

    with pytest.raises(DashboardDataError, match="thiếu cột pred_cluster"):
        prepare_external_pci_view(pci, assignments.drop(columns=["pred_cluster"]))

    with pytest.raises(DashboardDataError, match="thiếu cột bắt buộc"):
        prepare_external_pci_view(pci.drop(columns=["province_vi"]), assignments)


def test_external_pci_tests_hand_computed_values():
    # Ba nhóm [1,2,3], [4,5,6], [7,8,9]: F = MS giữa / MS trong = 54/2 / 1 = 27;
    # Kruskal không tie: H = 12/90 × (6²+15²+24²)/3 − 30 = 7.2; eta² = 54/60 = 0.9.
    view = pd.DataFrame({
        "pred_cluster": [0] * 3 + [1] * 3 + [2] * 3,
        "pci_weighted_score": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
    })

    tests = external_pci_tests(view)

    assert tests["f"] == pytest.approx(27.0)
    assert tests["h"] == pytest.approx(7.2)
    assert tests["df1"] == 2
    assert tests["df2"] == 6
    assert tests["eta_sq"] == pytest.approx(0.9)
    assert tests["n"] == 9
    assert tests["p_anova"] == pytest.approx(scipy_stats.f.sf(27.0, 2, 6))
    assert tests["p_kw"] == pytest.approx(scipy_stats.chi2.sf(7.2, 2))


def test_external_pci_tests_rejects_incomplete_input():
    one_group = pd.DataFrame({
        "pred_cluster": [0, 0, 0],
        "pci_weighted_score": [1.0, 2.0, 3.0],
    })
    with pytest.raises(DashboardDataError, match="ít nhất 2 nhóm"):
        external_pci_tests(one_group)

    with_nan = pd.DataFrame({
        "pred_cluster": [0, 1],
        "pci_weighted_score": [1.0, np.nan],
    })
    with pytest.raises(DashboardDataError, match="thiếu điểm"):
        external_pci_tests(with_nan)


def test_format_p_value_matches_artifact_style():
    assert format_p_value(1e-13) == "p < 1e-12"
    assert format_p_value(1e-12) == "p = 1e-12"
    assert format_p_value(6.93e-06) == "p = 6.93e-06"
    assert format_p_value(0.35) == "p = 0.35"


def test_published_external_pci_tests_parses_published_rows():
    validation = pd.DataFrame([
        _validation_row("pci_2011_2022", "nhiễu (–1)", n=149, mean=59.798),
        _validation_row("pci_2011_2022", "cụm 0", n=5, mean=58.996),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 9.0426; p = 6.93e-06"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", n=747, note="H = 31.7751; p = 5.84e-07"),
        _validation_row("pci_2011_2022", "eta squared", n=747, note="eta² = 0.0352 (SS giữa / SS tổng)"),
    ])

    tests = published_external_pci_tests(validation, "pci_2011_2022")

    assert tests == {
        "df1": 3,
        "df2": 743,
        "f": 9.0426,
        "p_anova": 6.93e-06,
        "p_anova_is_bound": False,
        "h": 31.7751,
        "p_kw": 5.84e-07,
        "p_kw_is_bound": False,
        "eta_sq": 0.0352,
        "n": 747,
    }


def test_published_external_pci_tests_parses_bound_p_note():
    """Note dạng chặn trên 'p < 1e-12' (format_p_value cho p cực nhỏ, cùng quy
    ước fmt_p của scripts/external_validation.py) phải đọc được — trước fix
    parser raise 'không đọc được định dạng' dù artifact nhất quán."""
    validation = pd.DataFrame([
        _validation_row("pci_2011_2022", "nhiễu (–1)", n=149, mean=59.798),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 9.0426; p < 1e-12"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", n=747, note="H = 31.7751; p < 1e-12"),
        _validation_row("pci_2011_2022", "eta squared", n=747, note="eta² = 0.0352 (SS giữa / SS tổng)"),
    ])

    tests = published_external_pci_tests(validation, "pci_2011_2022")

    assert tests["f"] == 9.0426
    assert tests["p_anova"] == 1e-12
    assert tests["p_anova_is_bound"] is True
    assert tests["h"] == 31.7751
    assert tests["p_kw"] == 1e-12
    assert tests["p_kw_is_bound"] is True
    assert tests["n"] == 747


def test_published_external_pci_tests_rejects_malformed_rows():
    base = [
        _validation_row("pci_2011_2022", "nhiễu (–1)", n=149, mean=59.798),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 9.0426; p = 6.93e-06"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", n=747, note="H = 31.7751; p = 5.84e-07"),
        _validation_row("pci_2011_2022", "eta squared", n=747, note="eta² = 0.0352 (SS giữa / SS tổng)"),
    ]

    with pytest.raises(DashboardDataError, match="không có section"):
        published_external_pci_tests(pd.DataFrame(base), "pci_2020")

    duplicated_anova = pd.DataFrame(
        base + [_validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 1.0; p = 0.5")]
    )
    with pytest.raises(DashboardDataError, match="cần đúng 1 dòng"):
        published_external_pci_tests(duplicated_anova, "pci_2011_2022")

    broken_note = pd.DataFrame([
        _validation_row("pci_2011_2022", "nhiễu (–1)", n=149),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F-đọc-không-ra"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", n=747, note="H = 31.7751; p = 5.84e-07"),
        _validation_row("pci_2011_2022", "eta squared", n=747, note="eta² = 0.0352"),
    ])
    with pytest.raises(DashboardDataError, match="không đọc được định dạng"):
        published_external_pci_tests(broken_note, "pci_2011_2022")

    missing_n = pd.DataFrame([
        _validation_row("pci_2011_2022", "nhiễu (–1)", mean=59.798),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", note="F = 9.0426; p = 6.93e-06"),
        _validation_row("pci_2011_2022", "Kruskal–Wallis", note="H = 31.7751; p = 5.84e-07"),
        _validation_row("pci_2011_2022", "eta squared", note="eta² = 0.0352"),
    ])
    with pytest.raises(DashboardDataError, match="thiếu n"):
        published_external_pci_tests(missing_n, "pci_2011_2022")


def _published_rows_for(view, section):
    """Artifact giả lập đúng định dạng results/external_validation.csv."""
    tests = external_pci_tests(view)
    rows = []
    for code, sub in view.groupby("pred_cluster"):
        values = sub.pci_weighted_score
        group = "nhiễu (–1)" if int(code) == -1 else f"cụm {int(code)}"
        rows.append(_validation_row(
            section, group, n=len(sub),
            mean=round(float(values.mean()), 3),
            median=round(float(values.median()), 3),
            std=round(float(values.std(ddof=1)), 3) if len(sub) > 1 else "",
            min=round(float(values.min()), 3),
            max=round(float(values.max()), 3),
        ))
    rows.append(_validation_row(
        section, f"ANOVA F({tests['df1']},{tests['df2']})", n=tests["n"],
        note=f"F = {tests['f']:.4f}; {format_p_value(tests['p_anova'])}",
    ))
    rows.append(_validation_row(
        section, "Kruskal–Wallis", n=tests["n"],
        note=f"H = {tests['h']:.4f}; {format_p_value(tests['p_kw'])}",
    ))
    rows.append(_validation_row(
        section, "eta squared", n=tests["n"],
        note=f"eta² = {tests['eta_sq']:.4f} (SS giữa / SS tổng)",
    ))
    return pd.DataFrame(rows)


def test_ensure_external_pci_consistency_passes_then_flags_drift():
    # Nhóm -1 chỉ 1 điểm: std trống hai phía phải được chấp nhận.
    view = pd.DataFrame({
        "pred_cluster": [-1, 0, 0, 0, 2, 2, 2],
        "pci_weighted_score": [60.0, 1.0, 2.0, 3.0, 7.0, 8.0, 9.0],
    })
    validation = _published_rows_for(view, "pci_main")

    result = ensure_external_pci_consistency(view, validation, section="pci_main")
    assert result["f"] == pytest.approx(external_pci_tests(view)["f"])
    assert result["n"] == 7

    drifted_f = validation.copy()
    drifted_f.loc[drifted_f.group.str.startswith("ANOVA"), "note"] = "F = 99.0000; p = 0.001"
    with pytest.raises(DashboardDataError, match="KHÔNG khớp artifact"):
        ensure_external_pci_consistency(view, drifted_f, section="pci_main")

    drifted_n = validation.copy()
    drifted_n.loc[drifted_n.group.eq("cụm 0"), "n"] = 99
    with pytest.raises(DashboardDataError, match="n nhóm 'cụm 0'"):
        ensure_external_pci_consistency(view, drifted_n, section="pci_main")

    drifted_mean = validation.copy()
    drifted_mean.loc[drifted_mean.group.eq("cụm 2"), "mean"] = 42.0
    with pytest.raises(DashboardDataError, match="mean nhóm 'cụm 2'"):
        ensure_external_pci_consistency(view, drifted_mean, section="pci_main")


def _tiny_p_view() -> pd.DataFrame:
    """ANOVA p ≈ 2.7e-16 (< 1e-12 → note dạng 'p < 1e-12'), Kruskal p ≈ 0.0495
    (note dạng 'p = …') — một view phủ cả hai quy ước của format_p_value."""
    return pd.DataFrame({
        "pred_cluster": [0, 0, 0, 1, 1, 1],
        "pci_weighted_score": [1.0, 2.0, 3.0, 10001.0, 10002.0, 10003.0],
    })


def test_ensure_external_pci_consistency_accepts_bound_p_note():
    """p cực nhỏ: generator phát hành note 'p < 1e-12' (format_p_value /
    fmt_p) — gate phải đọc được và chấp nhận khi p tính lại cũng dưới chặn
    trên. Trước fix parser đây là DashboardDataError 'không đọc được định
    dạng' dù dữ liệu nhất quán và rebuild không chữa được."""
    view = _tiny_p_view()
    recomputed = external_pci_tests(view)
    assert recomputed["p_anova"] < 1e-12  # note ANOVA chắc chắn ở dạng chặn trên

    validation = _published_rows_for(view, "pci_main")
    anova_note = validation.loc[
        validation.group.str.startswith("ANOVA"), "note"
    ].iloc[0]
    assert "p < 1e-12" in anova_note  # format_p_value đã phát hành dạng chặn trên

    result = ensure_external_pci_consistency(view, validation, section="pci_main")
    assert result["p_anova"] == pytest.approx(external_pci_tests(view)["p_anova"])
    # Cờ bound nằm ở phía artifact đã parse, không phải dict số tính lại.
    published = published_external_pci_tests(validation, "pci_main")
    assert published["p_anova_is_bound"] is True
    assert published["p_kw_is_bound"] is False


def test_ensure_external_pci_consistency_rejects_unsatisfied_bound():
    """p tính lại KHÔNG thỏa chặn trên của artifact → từ chối, không hiển thị
    số khác một cách âm thầm."""
    view = _tiny_p_view()
    validation = _published_rows_for(view, "pci_main")
    validation.loc[validation.group.str.startswith("ANOVA"), "note"] = (
        f"F = {external_pci_tests(view)['f']:.4f}; p < 1e-40"
    )

    with pytest.raises(DashboardDataError, match="KHÔNG khớp artifact"):
        ensure_external_pci_consistency(view, validation, section="pci_main")


def test_external_pci_group_stats_summary_and_labels():
    view = pd.DataFrame({
        "pred_cluster": [-1, 0, 0, 0],
        "pci_weighted_score": [60.0, 10.0, 20.0, 30.0],
    })

    stats_frame = external_pci_group_stats(view)

    assert stats_frame.pred_cluster.tolist() == [-1, 0]
    assert stats_frame.cluster_label.tolist() == ["Nhiễu (-1)", "Cụm 0"]
    noise = stats_frame.iloc[0]
    assert noise["n"] == 1
    assert pd.isna(noise["std"])
    cluster = stats_frame.iloc[1]
    assert cluster["n"] == 3
    assert cluster["mean"] == pytest.approx(20.0)
    assert cluster["median"] == pytest.approx(20.0)
    assert cluster["std"] == pytest.approx(10.0)
    assert cluster["min"] == pytest.approx(10.0)
    assert cluster["max"] == pytest.approx(30.0)


def test_external_section_frame_maps_labels_and_sorts():
    validation = pd.DataFrame([
        _validation_row("odm_health_2020", "cụm 2", n=57, year=2020, mean=0.003924),
        _validation_row("odm_health_2020", "nhiễu (–1)", n=6, year=2020, mean=0.00174),
        _validation_row("grdp_2018_2024", "cụm 2", n=58, year=2018, mean=60.36),
        _validation_row("grdp_2018_2024", "cụm 2", n=56, year=2019, mean=67.21),
        _validation_row("grdp_2018_2024", "nhiễu (–1)", n=2, year=2018, mean=61.08),
    ])

    health = external_section_frame(validation, "odm_health_2020")
    assert health.cluster_label.tolist() == ["Nhiễu (-1)", "Cụm 2"]
    assert health.n.tolist() == [6, 57]
    assert [int(y) for y in health.year] == [2020, 2020]

    grdp = external_section_frame(validation, "grdp_2018_2024")
    assert [[int(c), int(y)] for c, y in grdp[["pred_cluster", "year"]].values] == [
        [-1, 2018], [2, 2018], [2, 2019],
    ]

    with pytest.raises(DashboardDataError, match="không có section"):
        external_section_frame(validation, "missing")

    unknown_group = pd.DataFrame([_validation_row("khác", "???", n=1)])
    with pytest.raises(DashboardDataError, match="Không hiểu tên nhóm"):
        external_section_frame(unknown_group, "khác")

    pci_like = pd.DataFrame([
        _validation_row("pci_2011_2022", "cụm 2", n=577),
        _validation_row("pci_2011_2022", "ANOVA F(3,743)", n=747, note="F = 9.0426; p = 6.93e-06"),
    ])
    with pytest.raises(DashboardDataError, match="Không hiểu tên nhóm"):
        external_section_frame(pci_like, "pci_2011_2022")


# --------------------------------------------------------------------- #
# Kiểm chứng bổ trợ — nghèo cấp tỉnh GSO V14.47 theo nhãn cụm
# --------------------------------------------------------------------- #


def _make_poverty_frame() -> pd.DataFrame:
    """4 tỉnh thay cho 63: đủ 13 năm cửa sổ giao + 1 năm poverty-only.
    (2013, tỉnh 3) thiếu giá trị phía nguồn (pattern TP. Hồ Chí Minh 2016);
    giá trị là số nguyên dương nên so sánh float chính xác."""
    rows = []
    for year in POVERTY_OVERLAP_YEARS:
        for code in (1, 2, 3):
            value = float(10 + code + (year - 2012))
            if year == 2013 and code == 3:
                value = np.nan  # nguồn ghi ".." — KHÔNG nội suy
            rows.append({
                "province_code": code,
                "province_ascii": f"P{code}",
                "province_vi": f"Tỉnh {code}",
                "year": int(year),
                "poverty_rate_pct": value,
                "papi_province_code": code,
            })
    # Năm poverty-only: có poverty nhưng predict_all_years không phủ (pattern 2006/2008/2010/2025).
    rows.append({
        "province_code": 4,
        "province_ascii": "P4",
        "province_vi": "Tỉnh 4",
        "year": 2006,
        "poverty_rate_pct": 20.0,
        "papi_province_code": 4,
    })
    return pd.DataFrame(rows)


def _make_poverty_assignments() -> pd.DataFrame:
    """Nhãn cho tỉnh 1 (nhiễu) và 2 (cụm 2) mọi năm giao; tỉnh 3 chỉ có nhãn
    trừ năm 2014 (pattern ô không nhãn); cộng 1 năm label-only 2011."""
    rows = []
    for year in POVERTY_OVERLAP_YEARS:
        rows.append({"province_code": 1, "year": int(year), "pred_cluster": -1, "split": "test"})
        rows.append({"province_code": 2, "year": int(year), "pred_cluster": 2, "split": "test"})
        if year != 2014:
            rows.append({"province_code": 3, "year": int(year), "pred_cluster": 0, "split": "test"})
    rows.append({"province_code": 1, "year": 2011, "pred_cluster": 1, "split": "train"})
    return pd.DataFrame(rows)


def test_load_poverty_assets_missing_file_points_to_rebuild(tmp_path):
    with pytest.raises(DashboardDataError, match=r"python scripts/build_poverty_63\.py"):
        load_poverty_assets(tmp_path)


def test_load_poverty_assets_validates_schema(tmp_path):
    poverty_file = tmp_path / "data" / "processed" / "external_poverty_63.csv"
    poverty_file.parent.mkdir(parents=True, exist_ok=True)

    _make_poverty_frame().drop(columns=["papi_province_code"]).to_csv(
        poverty_file, index=False, encoding="utf-8"
    )
    with pytest.raises(DashboardDataError, match="external_poverty_63.csv thiếu cột"):
        load_poverty_assets(tmp_path)

    misaligned = _make_poverty_frame()
    misaligned.loc[0, "papi_province_code"] = 99
    misaligned.to_csv(poverty_file, index=False, encoding="utf-8")
    with pytest.raises(DashboardDataError, match="papi_province_code lệch province_code"):
        load_poverty_assets(tmp_path)

    frame = _make_poverty_frame()
    pd.concat([frame, frame.iloc[[0]]]).to_csv(poverty_file, index=False, encoding="utf-8")
    with pytest.raises(DashboardDataError, match="Poverty GSO có khóa trùng"):
        load_poverty_assets(tmp_path)

    _make_poverty_frame().to_csv(poverty_file, index=False, encoding="utf-8")
    loaded = load_poverty_assets(tmp_path)
    assert set(loaded) == {"poverty"}
    assert int(loaded["poverty"].year.nunique()) == len(POVERTY_OVERLAP_YEARS) + 1


def test_prepare_poverty_cluster_view_counts_and_masks():
    view, counts = prepare_poverty_cluster_view(_make_poverty_frame(), _make_poverty_assignments())

    assert counts["overlap_years"] == list(POVERTY_OVERLAP_YEARS)
    assert counts["pov_only_years"] == [2006]
    assert counts["label_only_years"] == [2011]
    assert counts["window_cells"] == 39  # 3 tỉnh × 13 năm giao
    assert counts["valid_cells"] == 38  # (2013, 3) thiếu phía nguồn
    assert [
        (int(cell["year"]), int(cell["province_code"]), cell["province_vi"])
        for cell in counts["missing_source_cells"]
    ] == [(2013, 3, "Tỉnh 3")]
    # Ô (2014, 3) có poverty nhưng không có nhãn — mask tường minh, không vào view
    assert [
        (int(cell["year"]), int(cell["province_code"]), cell["province_vi"])
        for cell in counts["no_label_cells"]
    ] == [(2014, 3, "Tỉnh 3")]
    assert counts["panel_rows"] == 37  # 38 ô hợp lệ − 1 ô không nhãn
    assert counts["clusters"] == [-1, 0, 2]
    assert counts["n_by_cluster"] == {-1: 13, 0: 11, 2: 13}
    assert counts["noise_by_year"] == {int(year): 1 for year in POVERTY_OVERLAP_YEARS}

    noise_row = view.loc[(view.year == 2012) & (view.province_code == 1)].iloc[0]
    assert noise_row.poverty_rate_pct == pytest.approx(11.0)
    assert noise_row.pov_dm == pytest.approx(-1.0)  # median năm 2012 = 12
    assert noise_row.cluster_label == "Nhiễu (-1)"
    # Năm chỉ còn 2 ô: median là trung bình 2 giá trị (12, 13) → dm = ±0.5
    half_row = view.loc[(view.year == 2013) & (view.province_code == 1)].iloc[0]
    assert half_row.pov_dm == pytest.approx(-0.5)
    assert (view.year == 2006).sum() == 0  # năm poverty-only bị loại khỏi view


def test_prepare_poverty_cluster_view_rejects_protocol_drift_and_bad_inputs():
    poverty = _make_poverty_frame()
    assignments = _make_poverty_assignments()

    # Mất 1 năm phía poverty → cửa sổ giao tự tính lệch protocol → từ chối.
    truncated = poverty.loc[poverty.year.ne(2020)]
    with pytest.raises(DashboardDataError, match="lệch protocol"):
        prepare_poverty_cluster_view(truncated, assignments)

    duplicated_poverty = pd.concat([poverty, poverty.iloc[[0]]])
    with pytest.raises(DashboardDataError, match="Poverty GSO có khóa trùng"):
        prepare_poverty_cluster_view(duplicated_poverty, assignments)

    duplicated_assignments = pd.concat([assignments, assignments.iloc[[0]]])
    with pytest.raises(DashboardDataError, match="STING assignments có khóa trùng"):
        prepare_poverty_cluster_view(poverty, duplicated_assignments)

    with pytest.raises(DashboardDataError, match="thiếu cột pred_cluster"):
        prepare_poverty_cluster_view(poverty, assignments.drop(columns=["pred_cluster"]))

    with pytest.raises(DashboardDataError, match="thiếu cột bắt buộc"):
        prepare_poverty_cluster_view(poverty.drop(columns=["province_vi"]), assignments)


def test_poverty_demean_preserves_within_year_comparison():
    """Trừ median trong năm là HẰNG SỐ trong năm: pov_dm + median năm = giá trị
    thô và KW từng năm KHÔNG đổi (thứ hạng trong năm giữ nguyên) — demean chỉ
    tái trọng số giữa các năm khi gộp, đúng ý nghĩa test đã-điều-chỉnh-năm."""
    view, _ = prepare_poverty_cluster_view(_make_poverty_frame(), _make_poverty_assignments())

    medians = view.groupby("year").poverty_rate_pct.transform("median")
    assert np.allclose(view.pov_dm + medians, view.poverty_rate_pct)
    for _, sub in view.groupby("year"):
        raw = scipy_stats.kruskal(*[g.poverty_rate_pct.to_numpy() for _, g in sub.groupby("pred_cluster")])
        demeaned = scipy_stats.kruskal(*[g.pov_dm.to_numpy() for _, g in sub.groupby("pred_cluster")])
        assert raw.statistic == pytest.approx(demeaned.statistic)


def test_poverty_cluster_tests_hand_computed_values():
    # Ba nhóm [1,2,3], [4,5,6], [7,8,9]: F = MS giữa / MS trong = 54/2 / 1 = 27;
    # Kruskal không tie: H = 12/90 × (6²+15²+24²)/3 − 30 = 7.2; eta² = 54/60 = 0.9.
    view = pd.DataFrame({
        "pred_cluster": [0] * 3 + [1] * 3 + [2] * 3,
        "poverty_rate_pct": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
    })

    tests = poverty_cluster_tests(view)

    assert tests["f"] == pytest.approx(27.0)
    assert tests["h"] == pytest.approx(7.2)
    assert tests["df1"] == 2
    assert tests["df2"] == 6
    assert tests["eta_sq"] == pytest.approx(0.9)
    assert tests["n"] == 9
    assert tests["p_anova"] == pytest.approx(scipy_stats.f.sf(27.0, 2, 6))
    assert tests["p_kw"] == pytest.approx(scipy_stats.chi2.sf(7.2, 2))


def test_poverty_cluster_tests_separates_year_effect_from_cluster_effect():
    """Cơ chế của quy tắc 'hai kết quả báo cáo CÙNG nhau': khi baseline nghèo
    giảm mạnh xuyên năm mà khoảng cách cụm nhỏ, KW gộp thô không phân biệt được
    (nhiễu năm át hiệu ứng cụm) còn đã-trừ-median-năm thì có."""
    rows = []
    for year, base in ((2012, 10.0), (2016, 4.0), (2024, 1.0)):
        # Nhiễu cao hơn cụm 2 đúng 0.5 điểm ở MỌI năm, baseline năm trôi 10→1.
        rows += [
            {"pred_cluster": -1, "poverty_rate_pct": base, "year": year},
            {"pred_cluster": -1, "poverty_rate_pct": base + 0.1, "year": year},
            {"pred_cluster": 2, "poverty_rate_pct": base + 0.5, "year": year},
            {"pred_cluster": 2, "poverty_rate_pct": base + 0.6, "year": year},
        ]
    view = pd.DataFrame(rows)
    # pov_dm đúng cách prepare_poverty_cluster_view sinh ra (trừ median trong năm).
    view["pov_dm"] = view.poverty_rate_pct - view.groupby("year").poverty_rate_pct.transform("median")

    raw = poverty_cluster_tests(view)
    demeaned = poverty_cluster_tests(view, "pov_dm")

    assert raw["p_kw"] > 0.05  # gộp thô: không đáng kể
    assert raw["p_anova"] > 0.05
    assert demeaned["p_kw"] < 0.05  # đã trừ median năm: đáng kể
    assert demeaned["p_anova"] < 0.05
    assert demeaned["h"] > raw["h"]


def test_poverty_cluster_tests_rejects_incomplete_input():
    one_group = pd.DataFrame({
        "pred_cluster": [0, 0, 0],
        "poverty_rate_pct": [1.0, 2.0, 3.0],
    })
    with pytest.raises(DashboardDataError, match="ít nhất 2 nhóm"):
        poverty_cluster_tests(one_group)

    with_nan = pd.DataFrame({
        "pred_cluster": [0, 1],
        "poverty_rate_pct": [1.0, np.nan],
    })
    with pytest.raises(DashboardDataError, match="thiếu giá trị"):
        poverty_cluster_tests(with_nan)


def test_poverty_noise_vs_c2_hand_computed():
    view = pd.DataFrame({
        "pred_cluster": [-1] * 3 + [2] * 3,
        "poverty_rate_pct": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    })

    mw = poverty_noise_vs_c2(view)

    assert mw["u"] == pytest.approx(0.0)  # nhiễu thấp hơn cụm 2 toàn bộ → U = 0
    assert mw["n"] == 6
    assert mw["p"] == pytest.approx(
        scipy_stats.mannwhitneyu([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]).pvalue
    )


def test_poverty_noise_vs_c2_requires_both_groups():
    only_noise = pd.DataFrame({
        "pred_cluster": [-1, -1],
        "poverty_rate_pct": [1.0, 2.0],
    })
    with pytest.raises(DashboardDataError, match="Thiếu nhóm nhiễu hoặc cụm 2"):
        poverty_noise_vs_c2(only_noise)


def test_format_poverty_window_runs_and_singles():
    assert format_poverty_window(
        [2012, 2013, 2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024]
    ) == "2012–2016 & 2020–2024"
    assert format_poverty_window([2006, 2008, 2010]) == "2006, 2008, 2010"
    assert format_poverty_window([2020]) == "2020"

    with pytest.raises(DashboardDataError, match="rỗng"):
        format_poverty_window([])


def test_poverty_protocol_recomputed_on_real_artifacts():
    """Pin protocol trên artifact thật — các số protocol ghi nhận (TP.HCM 2016
    code 79 thiếu nguồn; 13 ô không nhãn; panel 805 ô, {-1:144, 0:2, 1:10, 2:649};
    KW thô p≈0.198 KHÔNG đáng kể, KW đã-trừ-median-năm p≈1.3e-04 đáng kể, khớp
    results/poverty_validation.csv đã công bố). Artifact hoặc hàm đổi → test
    lộ ra thay vì dashboard hiển thị lệch im lặng. Pin cập nhật 2026-11-08 khi
    2017–2019 được điền từ NGTK 2020/2021 (cửa sổ 10 → 13 năm, panel 618 → 805)."""
    poverty = load_poverty_assets()["poverty"]
    assignments = pd.read_csv(ROOT / "results" / "predict_all_years.csv")

    view, counts = prepare_poverty_cluster_view(poverty, assignments)

    assert counts["overlap_years"] == list(POVERTY_OVERLAP_YEARS)
    assert counts["pov_only_years"] == [2006, 2008, 2010, 2025]
    assert counts["label_only_years"] == [2011]
    assert [
        (int(cell["year"]), int(cell["province_code"]), cell["province_vi"])
        for cell in counts["missing_source_cells"]
    ] == [(2016, 79, "TP. Hồ Chí Minh")]
    assert [
        (int(cell["year"]), int(cell["province_code"])) for cell in counts["no_label_cells"]
    ] == [
        (2014, 24), (2014, 87), (2018, 22), (2018, 87), (2021, 22), (2021, 24),
        (2021, 27), (2022, 24), (2022, 27), (2023, 22), (2023, 74), (2024, 26),
        (2024, 82),
    ]
    assert counts["panel_rows"] == 805
    assert counts["n_by_cluster"] == {-1: 144, 0: 2, 1: 10, 2: 649}

    raw = poverty_cluster_tests(view)
    demeaned = poverty_cluster_tests(view, "pov_dm")
    assert raw["h"] == pytest.approx(4.6670, abs=5e-4)
    assert raw["p_kw"] == pytest.approx(0.1979, abs=5e-4)  # KHÔNG đáng kể
    assert demeaned["h"] == pytest.approx(20.6285, abs=5e-4)
    assert demeaned["p_kw"] == pytest.approx(1.257e-04, rel=0.05)  # đáng kể
    assert raw["n"] == demeaned["n"] == 805

    mw_raw = poverty_noise_vs_c2(view)
    mw_dm = poverty_noise_vs_c2(view, "pov_dm")
    assert mw_raw["n"] == mw_dm["n"] == 793  # 144 nhiễu + 649 cụm 2
    assert mw_raw["p"] > 0.05  # thô: không khác biệt
    assert mw_dm["p"] > 0.10  # đã trừ median năm: không khác biệt
    # (trước khi điền 2017–2019, mw_dm p = 0.0836 — biên; thêm 3 năm làm mất
    # tín hiệu biên đó — phải báo cáo thẳng, không giữ claim cũ)
