"""Kiểm thử thống kê bàn giao cho khách hàng (scripts/analysis/stakeholder_summary.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.analysis.stakeholder_summary import (
    OUT_CSV,
    OUT_FIG,
    OUT_MD,
    build_stakeholder_tables,
    compute_core_benchmarks,
)
from scripts.common.papi_pred_common import ROOT


def test_stakeholder_summary_covers_all_63_provinces_and_counts_match():
    data = build_stakeholder_tables(ROOT)
    summary: pd.DataFrame = data["summary"]
    group_stats: pd.DataFrame = data["group_stats"]
    transitions: pd.DataFrame = data["transitions"]
    benchmarks_14y: pd.DataFrame = data["benchmarks_14y"]

    assert len(summary) == 63
    assert summary["province_code"].nunique() == 63
    assert int(group_stats["n_provinces"].sum()) == 63
    assert int(transitions["n_provinces"].sum()) == 63

    counts_by_group = dict(zip(group_stats["action_group"], group_stats["n_provinces"]))
    assert counts_by_group["Vùng lõi ổn định (Cụm 2)"] == 48
    assert counts_by_group["Biên bứt phá vượt chuẩn"] == 8
    assert counts_by_group["Ưu tiên cải thiện Y tế 6.1"] == 5
    assert counts_by_group["Thiếu dữ liệu 2024"] == 2
    assert len(benchmarks_14y) == 5


def test_stakeholder_separates_frontier_from_low_health_without_hardcoding():
    data = build_stakeholder_tables(ROOT)
    summary: pd.DataFrame = data["summary"]
    bench = data["bench"]

    frontier = summary.loc[summary["action_group"].eq("Biên bứt phá vượt chuẩn")]
    priority = summary.loc[summary["action_group"].eq("Ưu tiên cải thiện Y tế 6.1")]

    assert (frontier["grid_status"] == "sparse_cell").all()
    assert (frontier["sd_4_2"] >= bench["med_42"]).all()
    assert (frontier["sd_6_1"] >= bench["lower_61_fence"]).all()

    assert (priority["grid_status"] == "sparse_cell").all()
    assert (priority["sd_6_1"] < bench["lower_61_fence"]).all()


def test_stakeholder_published_artifacts_match_current_data():
    assert OUT_CSV.is_file()
    assert OUT_MD.is_file()
    assert OUT_FIG.is_file() and OUT_FIG.stat().st_size > 20_000

    published = pd.read_csv(OUT_CSV)
    recomputed = build_stakeholder_tables(ROOT)["summary"]
    assert list(published["province_code"]) == list(recomputed["province_code"])
    assert list(published["action_group"]) == list(recomputed["action_group"])
    assert list(published["transition_2023_2024"]) == list(recomputed["transition_2023_2024"])

    md_text = OUT_MD.read_text(encoding="utf-8")
    for required in (
        "Biên bứt phá vượt chuẩn",
        "Ưu tiên cải thiện Y tế 6.1",
        "Vùng lõi ổn định (Cụm 2)",
        "Phú Thọ",
        "Hà Nội",
        "Hà Tĩnh",
        "| Vĩnh Phúc | — | — |",
        "| Tiền Giang | — | — |",
        "rủi ro biến động",
        "Kịch bản ngoài vùng năm 2024",
        "không phải xác suất đã hiệu chỉnh hay dự báo cho năm sau 2024",
    ):
        assert required in md_text
    assert "NaN" not in md_text
    assert "biên động" not in md_text


def test_compute_core_benchmarks_fails_closed_when_no_core_rows():
    empty_core = pd.DataFrame(
        {"grid_status": ["sparse_cell", "missing_score"], "sd_4_2": [2.1, None], "sd_6_1": [1.8, None]}
    )
    with pytest.raises(ValueError, match="in_cluster"):
        compute_core_benchmarks(empty_core)


def test_stakeholder_excel_sheet_and_toc_table_are_consistent():
    import openpyxl

    xlsx_path = ROOT / "results" / "KetQua_STING_PAPI.xlsx"
    wb = openpyxl.load_workbook(xlsx_path)
    assert "Thống kê khách hàng 2024" in wb.sheetnames
    ws = wb["Thống kê khách hàng 2024"]
    assert ws.views.sheetView[0].showGridLines is False
    assert "PapiStakeholder2024" in ws.tables
    assert ws.tables["PapiStakeholder2024"].ref == "A5:P68"

    ws_toc = wb["Mục lục"]
    assert ws_toc.cell(6, 6).value == "stakeholder_province_summary_2024.csv"
    assert "PapiDanhMuc" in ws_toc.tables
    assert ws_toc.tables["PapiDanhMuc"].ref == f"A5:F{ws_toc.max_row}"
