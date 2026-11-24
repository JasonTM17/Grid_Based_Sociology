"""Temporal boundary, shared observations, and the two forecast endpoints."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from sting import STING
from scripts.common.papi_forecast import TARGETS, forecast_from_history, scenario_auc, score_forecast
from scripts.common.papi_pred_common import describe_grid_assignment, load_config, load_panel


RESULTS = Path(__file__).resolve().parents[1] / "results"


@pytest.fixture(scope="module")
def study():
    panel = load_panel()
    params = load_config()["sting"]
    run = forecast_from_history(panel.loc[panel.year <= 2023], params)
    return panel, params, run


def test_temporal_boundaries_and_same_fold_rows(study):
    _, _, run = study
    cv = run.validation
    assert run.train_pairs == 738
    assert sorted(cv.target_year.unique()) == list(range(2018, 2024))
    assert (cv.last_train_target_year <= cv.origin_year).all()
    assert cv.groupby("origin_year").n_validation.nunique().eq(1).all()
    assert cv.groupby(["origin_year", "target"]).method.nunique().eq(4).all()
    assert run.scenario_count == cv[["origin_year", "n_validation"]].drop_duplicates().n_validation.sum()
    avg = cv.groupby(["target", "method"]).mae.mean()
    assert run.selection == {target: avg[target].idxmin() for target in TARGETS}


def test_history_rejects_target_year_and_duplicate_province_key(study):
    panel, params, _ = study
    with pytest.raises(ValueError, match="mốc xuất phát"):
        forecast_from_history(panel, params)
    history = panel.loc[panel.year <= 2023]
    with pytest.raises(ValueError, match="duy nhất"):
        forecast_from_history(pd.concat([history, history.head(1)]), params)


def test_scoring_uses_keyed_common_sample_and_keeps_predictions(study):
    panel, _, run = study
    observed = panel.loc[panel.year.eq(2024)]
    before_scores = run.predictions.copy()
    rows, baseline_metrics, grid = score_forecast(run, observed.sample(frac=1, random_state=42))
    assert len(rows) == 61 and int(rows.actual_cluster.notna().sum()) == 59
    assert baseline_metrics.n.eq(59).all()
    assert rows.outside_scenario_share.between(0, 1).all()
    assert rows.outside_scenario_share.nunique() > 1
    shift = observed.assign(sd_6_1=observed.sd_6_1 + 0.7)
    rescore, new_metrics, _ = score_forecast(run, shift)
    pd.testing.assert_frame_equal(run.predictions, before_scores)
    pd.testing.assert_frame_equal(rescore[before_scores.columns], before_scores.reset_index(drop=True))
    assert not np.allclose(new_metrics.mae, baseline_metrics.mae)
    with pytest.raises(ValueError, match="duy nhất"):
        score_forecast(run, pd.concat([observed, observed.head(1)]))
    matches = grid.set_index("method")
    assert matches.loc["forecast", "out_correct"] == 0
    assert matches.loc["forecast", "missed_out"] == 11
    assert matches.loc["carry", "out_correct"] == 4
    assert matches.loc["forecast", "exact_label_agreement"] == matches.loc["majority", "exact_label_agreement"]


def test_current_summary_matches_recomputed_results(study):
    panel, _, run = study
    rows, scores, metrics = score_forecast(run, panel.loc[panel.year.eq(2024)])
    summary = json.loads((RESULTS / "papi_forecast_2024.json").read_text(encoding="utf-8"))
    archived_rows = pd.read_csv(RESULTS / "papi_forecast_provinces_2024.csv")
    pd.testing.assert_frame_equal(
        archived_rows, rows.astype({"actual_cluster": "float64"}), check_dtype=False, atol=1e-9, rtol=1e-9,
    )
    assert summary["selected_method"] == run.selection
    pd.testing.assert_frame_equal(pd.DataFrame(summary["scores"]), scores, check_exact=False)
    pd.testing.assert_frame_equal(pd.DataFrame(summary["grid"]), metrics, check_exact=False)
    assert summary["scenario_auc"] == pytest.approx(scenario_auc(rows))
    assert summary["scenario_count"] == run.scenario_count


def test_assignment_reports_all_provinces_and_separates_missing_from_sparse(study):
    panel, _, run = study
    observations = panel.loc[panel.year.eq(2024)]
    audit = describe_grid_assignment(observations, TARGETS, run.scaler, run.grid)
    assert audit.grid_status.value_counts().to_dict() == {
        "in_cluster": 48, "sparse_cell": 13, "missing_score": 2,
    }
    assert audit.province_code.tolist() == observations.province_code.tolist()
    missing = audit.loc[audit.grid_status.eq("missing_score")]
    assert missing[["cluster", "grid_cell", "reference_count"]].isna().all().all()
    sparse = audit.loc[audit.grid_status.eq("sparse_cell")]
    assert sparse.cluster.eq(-1).all() and sparse.reference_count.lt(run.grid.min_count_).all()
    saved = pd.read_csv(RESULTS / "papi_observed_grid_2024.csv", dtype={
        "cluster": "Int64", "grid_cell": "string", "reference_count": "Int64",
    })
    pd.testing.assert_frame_equal(audit, saved)


def test_assignment_distinguishes_out_of_bounds_and_nonfinite(study):
    panel, _, run = study
    target = TARGETS[0]
    rows = panel.loc[panel.year.eq(2024)].dropna(subset=list(TARGETS)).head(2).copy()
    low = run.grid.bounds_min_[0] * run.scaler.scale_[0] + run.scaler.mean_[0]
    rows[target] = [low - 1.0, np.inf]
    audit = describe_grid_assignment(rows, TARGETS, run.scaler, run.grid)
    assert audit.grid_status.tolist() == ["outside_grid", "nonfinite_score"]
    assert audit.cluster.iat[0] == -1 and pd.isna(audit.cluster.iat[1])
    assert audit[["grid_cell", "reference_count"]].isna().all().all()



def test_predict_and_assignment_reject_padded_constant_axis():
    features = list(TARGETS)
    training = pd.DataFrame([[2.0, 1.0], [2.0, 1.1], [2.0, 2.0]], columns=features)
    scaler = StandardScaler().fit(training)
    grid = STING(n_levels=2, factor=2, min_count=1).fit(scaler.transform(training))
    grid.cluster()
    observed = pd.DataFrame({
        "province_code": [1, 2],
        "province_vi": ["A", "B"],
        "year": 2024,
        features[0]: [2.0, 2.1],
        features[1]: [1.1, 1.1],
    })
    points = scaler.transform(observed[features])
    assert points[1, 0] < grid.bounds_max_[0]  # the padded grid still covers the point
    assert grid.predict(points).tolist() == [0, -1]
    assignment = describe_grid_assignment(observed, features, scaler, grid)
    assert assignment.grid_status.tolist() == ["in_cluster", "outside_grid"]
    assert assignment.cluster.tolist() == [0, -1]
    assert assignment.loc[1, ["grid_cell", "reference_count"]].isna().all()
