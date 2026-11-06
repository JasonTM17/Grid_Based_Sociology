"""Regression checks for time-safe PAPI model labels and feature eligibility."""

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.predict_supervised import (
    CLASSIFICATION_CV_YEARS,
    STING,
    build_regression_pairs,
    build_classification_pairs,
    expanding_origin_folds,
    expanding_majority_f1,
    expanding_year_splits,
    fit_sting_labeler,
    predict_sting_labels_for_origin,
)
from scripts.papi_pred_common import (
    REGRESSION_FEATURES,
    ROOT,
    load_panel,
    select_model_by_cv,
)
from scripts.dashboard_data import (
    DashboardDataError,
    filter_regression_holdout,
    load_dashboard_assets,
    prepare_regression_holdout,
    prepare_sting_view,
    select_regression_model,
)
from scripts.predict_sweep import STABLE_SUBDIMS, candidate_pairs


STING_FEATURES = ["sd_4_2", "sd_6_1"]
STING_PARAMS = {
    "n_levels": 2,
    "factor": 2,
    "min_count": 1,
    "cluster_level": 1,
    "connectivity": 1,
}


def make_panel(years=range(2011, 2019), provinces=8):
    rows = []
    for year in years:
        for province_code in range(1, provinces + 1):
            cluster = province_code % 2
            row = {
                "province_code": province_code,
                "year": year,
                "sd_4_2": 1.0 + 5.0 * cluster + 0.01 * (year - 2011),
                "sd_6_1": 1.5 + 4.0 * cluster + 0.02 * (year - 2011),
            }
            for index, feature in enumerate(REGRESSION_FEATURES):
                row.setdefault(feature, float(index + cluster + year - 2011))
            rows.append(row)
    return pd.DataFrame(rows)


def test_candidate_pairs_exclude_unverified_dimensions_and_train_flags():
    rows = []
    for year in range(2011, 2016):
        for province_code in range(1, 5):
            row = {"year": year, "province_code": province_code}
            for feature in STABLE_SUBDIMS:
                row[feature] = 1.0
            for feature in (f"d{i}" for i in range(1, 7)):
                row[feature] = 5.0
            if year == 2015:
                row["sd_1_3"] = 2.0
            rows.append(row)

    pairs = candidate_pairs(pd.DataFrame(rows))
    used = {feature for pair in pairs for feature in pair}

    assert len(pairs) == 21  # 7 eligible sub-dimensions choose 2
    assert "sd_1_3" not in used
    assert not any(feature in {f"d{i}" for i in range(1, 7)} for feature in used)


def test_labeler_fit_uses_only_rows_at_or_before_origin(monkeypatch):
    panel = make_panel(years=range(2011, 2014))
    fitted_rows = []
    original_fit = STING.fit

    def record_fit(model, values):
        fitted_rows.append(np.asarray(values).copy())
        return original_fit(model, values)

    monkeypatch.setattr(STING, "fit", record_fit)
    fit_sting_labeler(panel, 2011, STING_FEATURES, STING_PARAMS)

    assert fitted_rows[0].shape == (8, len(STING_FEATURES))


def test_labels_for_origin_are_invariant_to_data_after_target_year():
    panel = make_panel(years=range(2011, 2016))
    expected = predict_sting_labels_for_origin(
        panel, 2011, STING_FEATURES, STING_PARAMS
    )
    changed_future = panel.copy()
    future = changed_future.year >= 2013
    changed_future.loc[future, STING_FEATURES] += 1000

    actual = predict_sting_labels_for_origin(
        changed_future, 2011, STING_FEATURES, STING_PARAMS
    )

    assert actual == expected


def test_classification_pairs_build_cutoff_local_labels_without_saved_model(monkeypatch):
    panel = make_panel(years=range(2011, 2016))
    monkeypatch.setattr(
        STING,
        "load",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("saved model used")),
    )

    pairs = build_classification_pairs(panel, STING_FEATURES, STING_PARAMS)

    assert set(pairs.year_t.unique()) == {2011, 2012, 2013, 2014}
    assert set(pairs.y.unique()) <= {0, 1}


def test_expanding_year_splits_never_train_on_validation_or_future_origins():
    years = np.repeat(np.arange(2011, 2023), 2)
    labels = np.tile([0, 1], len(years) // 2)
    splits = expanding_year_splits(years, labels)

    assert len(splits) == len(CLASSIFICATION_CV_YEARS) == 6
    for validation_year, (train_indices, validation_indices) in zip(
        CLASSIFICATION_CV_YEARS, splits
    ):
        assert set(years[validation_indices]) == {validation_year}
        assert years[train_indices].max() < validation_year


def test_expanding_origin_folds_are_nonempty_and_exclude_future_origins():
    years = np.repeat(np.array([2011, 2016, *CLASSIFICATION_CV_YEARS, 2023]), 2)
    splits = expanding_origin_folds(years, first_validation_origin=2017)

    assert len(splits) == len(CLASSIFICATION_CV_YEARS) == 6
    for validation_year, (train_indices, validation_indices) in zip(
        CLASSIFICATION_CV_YEARS, splits
    ):
        assert train_indices.size > 0
        assert validation_indices.size > 0
        assert years[train_indices].max() < years[validation_indices].min()
        assert np.unique(years[validation_indices]).tolist() == [validation_year]
        future_indices = np.flatnonzero(years > validation_year)
        assert np.intersect1d(train_indices, future_indices).size == 0

    later_2017_indices = np.flatnonzero(years == 2022)
    assert later_2017_indices.size > 0
    assert np.intersect1d(splits[0][0], later_2017_indices).size == 0


def test_expanding_origin_folds_cover_production_validation_years():
    pairs = build_regression_pairs(load_panel())
    train = pairs[pairs.year_t < 2023]
    splits = expanding_origin_folds(
        train.year_t.to_numpy(), first_validation_origin=2017
    )

    validation_years = [int(train.year_t.iloc[val_indices[0]]) for _, val_indices in splits]
    assert validation_years == list(CLASSIFICATION_CV_YEARS)


def test_expanding_origin_folds_require_every_validation_year():
    years = np.repeat(
        np.array([2011, 2016, 2017, 2018, 2020, 2021, 2022]), 2
    )

    with pytest.raises(ValueError, match="2019"):
        expanding_origin_folds(years, first_validation_origin=2017)


def test_ridge_pipeline_joblib_roundtrip_and_saved_model_prediction(tmp_path):
    matrix = np.arange(96, dtype=float).reshape(12, 8) / 10
    target = np.linspace(0.2, 0.9, len(matrix))
    probe = np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])
    model = Pipeline(
        [("sc", StandardScaler()), ("m", Ridge(random_state=42))]
    ).fit(matrix, target)
    model_path = tmp_path / "ridge.joblib"
    joblib.dump(model, model_path)
    loaded = joblib.load(model_path)

    np.testing.assert_allclose(loaded.predict(probe), model.predict(probe))

    saved_model = joblib.load(ROOT / "models" / "sup_ridge.joblib")
    prediction = saved_model.predict(probe)
    assert prediction.shape == (1,)
    assert np.isfinite(prediction).all()


def test_expanding_year_splits_require_both_classes_in_training_history():
    years = np.repeat(np.arange(2011, 2023), 2)
    labels = np.zeros(len(years), dtype=int)

    with pytest.raises(ValueError, match="một lớp train"):
        expanding_year_splits(years, labels)


def test_expanding_majority_baseline_uses_each_fold_training_history():
    years = np.repeat(np.arange(2011, 2023), 2)
    labels = np.tile([0, 1], len(years) // 2)
    splits = expanding_year_splits(years, labels)

    assert expanding_majority_f1(labels, splits) == pytest.approx(1 / 3)


def test_model_family_selection_uses_cv_not_holdout_metrics():
    regression = pd.DataFrame(
        [
            {"model": "ridge", "value_cv": 0.451, "holdout_mae": 0.0640},
            {"model": "random forest", "value_cv": 0.432, "holdout_mae": 0.0616},
        ]
    )
    classification = pd.DataFrame(
        [
            {"model": "logistic regression", "value_cv": 0.434, "holdout_macro_f1": 0.541},
            {"model": "random forest", "value_cv": 0.397, "holdout_macro_f1": 0.600},
        ]
    )

    assert select_model_by_cv(regression) == "ridge"
    assert select_model_by_cv(classification) == "logistic regression"

    regression.loc[regression.model == "ridge", "holdout_mae"] = 0.09
    regression.loc[regression.model == "random forest", "holdout_mae"] = 0.01
    classification.loc[classification.model == "logistic regression", "holdout_macro_f1"] = 0.1
    classification.loc[classification.model == "random forest", "holdout_macro_f1"] = 0.99
    assert select_model_by_cv(regression) == "ridge"
    assert select_model_by_cv(classification) == "logistic regression"


def test_pair_builders_reject_duplicate_province_year_rows():
    panel = make_panel(years=range(2011, 2013))
    duplicated = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="trùng"):
        predict_sting_labels_for_origin(
            duplicated, 2011, STING_FEATURES, STING_PARAMS
        )


class DummyRegressor:
    def __init__(self, offset=0.0):
        self.offset = offset

    def predict(self, values):
        return np.asarray(values)[:, 0] + self.offset


def make_holdout_panel():
    rows = []
    for province_code in range(1, 5):
        origin = {"province_code": province_code, "province_vi": f"Tỉnh {province_code}", "year": 2023}
        for index, feature in enumerate(REGRESSION_FEATURES):
            origin[feature] = float(province_code + index)
        if province_code == 3:
            origin[REGRESSION_FEATURES[0]] = np.nan
        target = {
            "province_code": province_code,
            "province_vi": f"Tỉnh {province_code}",
            "year": 2024,
            REGRESSION_FEATURES[6]: float(10 + province_code),
        }
        if province_code == 4:
            target[REGRESSION_FEATURES[6]] = np.nan
        rows.extend([origin, target])
    return pd.DataFrame(rows)


def test_sting_view_joins_by_year_and_province_and_counts_missing_noise():
    panel = pd.DataFrame(
        {
            "province_code": [1, 2, 3, 4],
            "province_vi": ["A", "B", "C", "D"],
            "year": [2024, 2024, 2024, 2024],
            "sd_4_2": [1.0, 1.0, np.nan, 1.0],
            "sd_6_1": [1.0, 1.0, 1.0, 1.0],
        }
    )
    assignments = pd.DataFrame(
        {
            "province_code": [2, 1],
            "year": [2024, 2024],
            "pred_cluster": [-1, 0],
            "split": ["test", "test"],
        }
    )

    visible, counts = prepare_sting_view(
        panel,
        assignments,
        2024,
        province_codes={1, 2, 3, 4},
        cluster_codes={-1},
        required_features=STING_FEATURES,
    )

    assert visible.province_code.tolist() == [2]
    assert visible.cluster_label.tolist() == ["Nhiễu (-1)"]
    assert counts == {
        "source_rows": 4,
        "eligible_assignments": 2,
        "missing_feature_rows": 1,
        "missing_assignment_rows": 2,
        "unassigned_artifact_rows": 1,
        "noise_rows": 1,
        "covered_rows": 1,
        "filtered_rows": 1,
        "filtered_noise_rows": 1,
        "filtered_missing_feature_rows": 0,
        "filtered_unassigned_artifact_rows": 0,
    }


def test_regression_holdout_uses_2023_origin_cluster_and_separates_missing_counts():
    panel = make_holdout_panel().iloc[::-1].reset_index(drop=True)
    assignments = pd.DataFrame(
        {
            "province_code": [1, 2, 1, 2],
            "year": [2023, 2023, 2024, 2024],
            "pred_cluster": [2, 3, 9, 8],
        }
    )

    holdout, counts = prepare_regression_holdout(
        panel, assignments, DummyRegressor(), DummyRegressor(offset=1.0)
    )
    filtered, filter_counts = filter_regression_holdout(
        holdout, province_codes={1, 2}, origin_clusters={2}
    )

    assert holdout.province_code.tolist() == [1, 2]
    assert holdout.actual_2024.tolist() == [11.0, 12.0]
    assert holdout.origin_cluster_2023.tolist()[0] == 2
    assert holdout.origin_cluster_2023.tolist()[1] == 3
    assert counts == {
        "origin_source_rows": 4,
        "missing_origin_feature_rows": 1,
        "origin_feature_rows": 3,
        "missing_target_for_complete_origin": 1,
        "holdout_pairs": 2,
        "missing_origin_cluster": 0,
    }
    assert filtered.province_code.tolist() == [1]
    assert filter_counts["after_origin_cluster_filter"] == 1
    assert filter_counts["missing_origin_cluster_after_province_filter"] == 0


def test_dashboard_selects_regression_family_by_cv_only():
    metrics = pd.DataFrame(
        [
            {"task": "regression", "model": "ridge", "value_cv": 0.451, "holdout_mae": 0.09},
            {"task": "regression", "model": "random forest", "value_cv": 0.432, "holdout_mae": 0.01},
            {"task": "classification", "model": "logistic regression", "value_cv": 0.9, "holdout_mae": np.nan},
        ]
    )

    assert select_regression_model(metrics) == "ridge"


def test_dashboard_missing_artifact_error_has_rebuild_command(tmp_path):
    with pytest.raises(DashboardDataError, match="python scripts/build_panel.py"):
        load_dashboard_assets(tmp_path)
