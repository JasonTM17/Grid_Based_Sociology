"""Kiểm thử mô-đun sản phẩm khách hàng: bản đồ Choropleth 63 tỉnh & Phiếu rà soát tỉnh định dạng in A4."""

from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import pytest

from scripts.analysis.client_product import (
    CUSTOMER_GROUP_LABELS,
    GEOJSON_PROVINCE_ALIAS,
    build_action_choropleth_figure,
    build_province_scorecard_html,
    customer_display_frame,
    load_vietnam_geojson,
    scorecard_filename,
)
from scripts.analysis.stakeholder_summary import build_stakeholder_tables
from scripts.common.papi_pred_common import ROOT


def _iter_rings(geometry: dict):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        yield from coords
    elif gtype == "MultiPolygon":
        for poly in coords:
            yield from poly


def test_load_vietnam_geojson_matches_all_63_provinces_and_closes_rings(tmp_path):
    assert len(GEOJSON_PROVINCE_ALIAS) == 6
    gj = load_vietnam_geojson()
    assert len(gj["features"]) == 63

    summary = pd.read_csv(ROOT / "results" / "stakeholder_province_summary_2024.csv")
    geo_names = {feat["properties"]["province_vi"] for feat in gj["features"]}
    assert geo_names == set(summary["province_vi"])

    for feat in gj["features"]:
        for ring in _iter_rings(feat["geometry"]):
            assert len(ring) >= 4
            assert ring[0] == ring[-1]
            for lon, lat in ring:
                assert round(lon, 3) == lon
                assert round(lat, 3) == lat

    bad_geojson = tmp_path / "bad.geojson"
    bad_geojson.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="63"):
        load_vietnam_geojson(bad_geojson)


def test_build_action_choropleth_figure_covers_63_provinces_offline():
    data = build_stakeholder_tables(ROOT)
    gj = load_vietnam_geojson()

    fig = build_action_choropleth_figure(data["summary"], gj)
    assert isinstance(fig, go.Figure)
    assert fig.layout.geo.visible is False
    total_locs = sum(len(trace.locations) for trace in fig.data)
    assert total_locs == 63

    fig_hi = build_action_choropleth_figure(data["summary"], gj, highlight_codes={1, 79})
    assert isinstance(fig_hi, go.Figure)
    selected_total = sum(len(trace.selectedpoints or []) for trace in fig_hi.data)
    assert selected_total == 2
    assert all(trace.unselected.marker.opacity < 0.5 for trace in fig_hi.data)

    fig_empty_hi = build_action_choropleth_figure(data["summary"], gj, highlight_codes=set())
    assert sum(len(trace.selectedpoints or []) for trace in fig_empty_hi.data) == 0

    bad_gj = {"type": "FeatureCollection", "features": gj["features"][:-1]}
    with pytest.raises(ValueError, match="GeoJSON"):
        build_action_choropleth_figure(data["summary"], bad_gj)


def test_scorecard_filename_ascii_safe():
    assert scorecard_filename("Đà Nẵng") == "phieu_chan_doan_da_nang_2024.html"
    assert scorecard_filename("Bà Rịa - Vũng Tàu") == "phieu_chan_doan_ba_ria_vung_tau_2024.html"
    assert scorecard_filename("TP. Hồ Chí Minh") == "phieu_chan_doan_tp_ho_chi_minh_2024.html"


def test_customer_export_labels_preserve_observations_and_source_data():
    source = build_stakeholder_tables(ROOT)["summary"]
    before = source.copy(deep=True)
    displayed = customer_display_frame(source)
    text_columns = ["action_group", "action_subtier", "transition_2023_2024", "client_recommendation"]
    pd.testing.assert_frame_equal(source, before)
    pd.testing.assert_frame_equal(displayed.drop(columns=text_columns), source.drop(columns=text_columns))
    pd.testing.assert_frame_equal(customer_display_frame(displayed), displayed)
    assert displayed["action_group"].value_counts().to_dict() == {
        CUSTOMER_GROUP_LABELS[name]: count for name, count in source["action_group"].value_counts().items()
    }
    assert not displayed["action_group"].str.contains("vượt chuẩn|ổn định").any()
    assert not displayed["client_recommendation"].str.contains("Nhân rộng thực hành tốt").any()
    # A customer receives the same raw proportions and missing values in CSV.
    exported = pd.read_csv(io.StringIO(displayed.to_csv(index=False)))
    pd.testing.assert_series_equal(exported["risk_outside_scenario_share"], source["risk_outside_scenario_share"])
    assert exported["sd_4_2"].isna().sum() == source["sd_4_2"].isna().sum()


def test_build_province_scorecard_html_covers_groups_missing_and_escaping():
    data = build_stakeholder_tables(ROOT)
    summary = data["summary"]
    all_years = pd.read_csv(ROOT / "results" / "predict_all_years.csv")

    for prov_code, expected_name in ((48, "Đà Nẵng"), (1, "Hà Nội"), (22, "Quảng Ninh")):
        out = build_province_scorecard_html(
            prov_code, summary, all_years, data["bench"], data["benchmarks_14y"]
        )
        assert expected_name in out
        assert "2024" in out
        assert "Kịch bản ngoài vùng 2024" in out
        assert "Hồi kiểm 2023→2024; không phải xác suất" in out
        assert "năm tới" not in out
        assert "Chỉ mô tả bối cảnh kinh tế–xã hội độc lập" in out
        assert "Mốc 6.1 là quy tắc hồi cứu" in out
        assert "chuẩn tham chiếu bền vững" not in out
        assert "vượt chuẩn" not in out
        assert "<script>" not in out
        assert "https://" not in out

    missing_html = build_province_scorecard_html(
        26, summary, all_years, data["bench"], data["benchmarks_14y"]
    )
    assert "Vĩnh Phúc" in missing_html
    assert "—" in missing_html
    assert "NaN" not in missing_html
    assert ">None<" not in missing_html

    tampered = summary.copy()
    tampered.loc[tampered["province_code"].eq(1), "client_recommendation"] = "<script>alert(1)</script>"
    escaped = build_province_scorecard_html(
        1, tampered, all_years, data["bench"], data["benchmarks_14y"]
    )
    assert "<script>alert(1)</script>" not in escaped
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in escaped

    with pytest.raises(ValueError, match="9999"):
        build_province_scorecard_html(
            9999, summary, all_years, data["bench"], data["benchmarks_14y"]
        )
