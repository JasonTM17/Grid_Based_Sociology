import numpy as np
import pandas as pd

from scripts.dashboard_data import prepare_sting_view, select_classification_model


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
