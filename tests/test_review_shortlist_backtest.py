import pandas as pd
import pytest

from scripts.analysis import review_shortlist_backtest as study
from scripts.common.papi_pred_common import load_config, load_panel


def test_backtest_has_no_future_fit_and_reproduces_2024_grid(monkeypatch):
    monkeypatch.setattr(study, "YEARS", (2024,))
    panel = load_panel()
    seen = []
    fit = study.fit_grid

    def record_fit(history, params):
        seen.append((int(history.year.max()), len(history)))
        return fit(history, params)

    monkeypatch.setattr(study, "fit_grid", record_fit)
    audit, summary = study.analyze(panel, load_config()["sting"])
    assert seen == [(2023, 808)]
    assert summary["annual"][0]["status_counts"] == {"in_cluster": 48, "sparse_cell": 13}
    assert len(audit) == audit.province_code.nunique() == 61
    for rule in study.RULES:
        assert sorted(audit[f"rank_{rule}"]) == list(range(1, 62))
    assert (audit.rank_health_only.le(5) & audit.rank_combined.le(5)).sum() == 3
    with pytest.raises(ValueError, match="Duplicate province-year"):
        study.analyze(pd.concat([panel, panel.iloc[:1]]), load_config()["sting"])


def test_review_packet_separates_methods_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "REVIEW_BUDGET", 2)
    frame = pd.DataFrame({
        "province_code": range(1, 7), "province_vi": list("ABCDEF"), "year": [2024] * 6,
        "rank_health_only": [1, 2, 3, 4, 5, 6], "rank_sting_only": [1, 3, 2, 4, 5, 6],
        "rank_combined": [3, 1, 2, 4, 5, 6],
    })
    path = tmp_path / "review"
    study.prepare_review(frame, path)
    sheet = pd.read_csv(path / "for-reviewers" / "cases.csv")
    key = pd.read_csv(path / "restricted" / "selection_key.csv")
    assert list(sheet) == ["case_id", "province_vi", "year", "outcome", "evidence_ref", "rationale"]
    assert sheet.case_id.is_unique and list(sheet.case_id) == list(key.case_id)
    assert len(sheet) == 5 and sheet.outcome.isna().all()
    flags = [f"selected_{rule}" for rule in study.RULES]
    assert key[flags].sum().tolist() == [2, 2, 2]
    assert key.audit_sample.sum() == 2
    assert not key.loc[key.audit_sample, flags].any().any()
    with pytest.raises(FileExistsError):
        study.prepare_review(frame, path)
