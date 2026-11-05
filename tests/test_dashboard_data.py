import numpy as np
import pandas as pd
import pytest

from scripts.dashboard_data import (
    DashboardDataError,
    filter_regression_holdout,
    load_dashboard_assets,
    load_regression_models,
    prepare_regression_holdout,
    prepare_sting_view,
    select_classification_model,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, REGRESSION_TARGET


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
