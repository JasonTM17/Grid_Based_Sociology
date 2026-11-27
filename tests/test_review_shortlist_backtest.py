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


def test_review_dossier_excludes_papi_and_sting_columns_and_evaluator_scores_blind_packets(tmp_path):
    panel = load_panel()
    chosen = pd.DataFrame({
        "case_id": ["R01", "R02", "R03"],
        "province_vi": ["Hà Nội", "Cần Thơ", "Phú Thọ"],
        "year": [2024, 2024, 2024],
    })
    dossier = study.build_external_dossier(chosen, root=study.ROOT)
    assert dossier is not None
    assert len(dossier) == 3
    forbidden = {"sd_4_2", "sd_6_1", "pred_cluster", "cluster", "grid_cell"}
    assert not (set(dossier.columns) & forbidden)
    assert {
        "pci_2022",
        "grdp_2024_mil_vnd",
        "poverty_2024_pct",
        "hospitals_per_100k_pop_2020",
        "gso_urban_pct_2022",
        "waste_kg_urb_2019",
    } <= set(dossier.columns)
    assert dossier[["pci_2022", "grdp_2024_mil_vnd", "poverty_2024_pct", "gso_urban_pct_2022"]].notna().all().all()

    review_dir = tmp_path / "round"
    (review_dir / "for-reviewers").mkdir(parents=True)
    (review_dir / "restricted").mkdir(parents=True)
    pd.DataFrame([
        {"case_id": "R01", "province_code": 1, "selected_health_only": True, "selected_sting_only": True, "selected_combined": True, "audit_sample": False},
        {"case_id": "R02", "province_code": 92, "selected_health_only": True, "selected_sting_only": False, "selected_combined": True, "audit_sample": False},
        {"case_id": "R03", "province_code": 25, "selected_health_only": False, "selected_sting_only": False, "selected_combined": False, "audit_sample": True},
    ]).to_csv(review_dir / "restricted" / "selection_key.csv", index=False)

    blank_cases = chosen.assign(outcome="", evidence_ref="", rationale="")
    blank_cases.to_csv(review_dir / "for-reviewers" / "cases.csv", index=False)
    with pytest.raises(ValueError, match="chưa điền đầy đủ"):
        study.evaluate_review_packet(review_dir)

    r1 = chosen.assign(outcome=["confirmed", "not_confirmed", "insufficient_evidence"], evidence_ref="doc1", rationale="r1")
    r2 = chosen.assign(outcome=["confirmed", "not_confirmed", "insufficient_evidence"], evidence_ref="doc2", rationale="r2")
    p1 = review_dir / "for-reviewers" / "r1.csv"
    p2 = review_dir / "for-reviewers" / "r2.csv"
    r1.to_csv(p1, index=False)
    r2.to_csv(p2, index=False)
    res = study.evaluate_review_packet(review_dir, [p1, p2])
    assert res["status"] == "SCORED"
    assert res["agreement"]["exact_agreement_rate"] == 1.0
    assert res["agreement"]["cohen_kappa"] == pytest.approx(1.0)
    assert res["methods"]["health_only"]["confirmed"] == 1
    assert res["methods"]["health_only"]["not_confirmed"] == 1
    assert res["audit_sample"]["insufficient_evidence"] == 1
    del panel
