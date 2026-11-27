"""Data-editing contract for the optional Artifact presentation build."""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
import importlib.util
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import load_workbook
import pytest

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "slides/Nhom15_STING_PAPI.pptx"
SPEC = importlib.util.spec_from_file_location(
    "slides_chart_workbooks", ROOT / "scripts/deliverables/slides_chart_workbooks.py")
PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK)
C = PACK.C


def _read(path):
    with ZipFile(path) as package:
        return {name: package.read(name) for name in package.namelist()}


def _write(path, parts):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as package:
        for name, data in parts.items():
            package.writestr(name, data)


def _literal_copy(path):
    """Use the real chart data, with the same literal format as Artifact export."""
    parts = _read(DECK)
    for name in list(parts):
        if name.endswith(".xlsx") or "/charts/_rels/" in name:
            del parts[name]
        elif "/charts/chart" in name and name.endswith(".xml"):
            root = ET.fromstring(parts[name])
            root.remove(root.find(f"{{{C}}}externalData"))
            for series in root.iter(f"{{{C}}}ser"):
                for role in ("cat", "val", "xVal", "yVal"):
                    data = series.find(f"{{{C}}}{role}")
                    if data is None:
                        continue
                    ref = data[0]
                    numeric = ref.tag.endswith("numRef")
                    cache = ref.find(f"{{{C}}}{'numCache' if numeric else 'strCache'}")
                    ref.remove(cache)
                    data.remove(ref)
                    cache.tag = f"{{{C}}}{'numLit' if numeric else 'strLit'}"
                    data.append(cache)
            parts[name] = ET.tostring(root)
    types = ET.fromstring(parts["[Content_Types].xml"])
    for node in list(types):
        if node.get("Extension") == "xlsx" or node.get("PartName", "").endswith(".xlsx"):
            types.remove(node)
    parts["[Content_Types].xml"] = ET.tostring(types)
    _write(path, parts)
    return parts


def test_packages_all_real_chart_values_and_preserves_slide_bytes(tmp_path):
    path = tmp_path / "slides.pptx"
    before = _literal_copy(path)
    reports = PACK.embed_chart_workbooks(path)
    assert [(r["series"], r["points"], r["numeric_cells"]) for r in reports] == [(1, 4, 4), (3, 61, 122)]
    after = _read(path)
    assert b'<Types xmlns="' in after["[Content_Types].xml"]
    assert b'<Override ' in after["[Content_Types].xml"]
    assert all(b'<Relationships xmlns="' in data
               for name, data in after.items() if "/charts/_rels/" in name)
    changed = {name for name in before if before[name] != after[name]}
    assert changed == {"[Content_Types].xml", *(r["chart"] for r in reports)}
    # Independently compare workbook numbers with the input chart's literals.
    for report in reports:
        root = ET.fromstring(before[report["chart"]])
        expected = [Decimal(p.findtext(f"{{{C}}}v"))
                    for cache in root.iter(f"{{{C}}}numLit")
                    for p in cache.findall(f"{{{C}}}pt")]
        wb = load_workbook(BytesIO(after[report["workbook"]]), data_only=False)
        actual = [Decimal(str(cell.value)) for column in wb.active.iter_cols(min_row=2)
                  for cell in column if isinstance(cell.value, (int, float))]
        wb.close()
        assert actual == expected
    assert PACK.validate_chart_workbooks(path) == reports


def test_already_packaged_canonical_deck_is_byte_identical(tmp_path):
    path = tmp_path / "slides.pptx"
    shutil.copyfile(DECK, path)
    original = path.read_bytes()
    assert len(PACK.embed_chart_workbooks(path)) == 2
    assert path.read_bytes() == original


def test_tampered_workbook_is_rejected_without_rewriting(tmp_path):
    path = tmp_path / "slides.pptx"
    shutil.copyfile(DECK, path)
    report = PACK.validate_chart_workbooks(path)[0]
    parts = _read(path)
    wb = load_workbook(BytesIO(parts[report["workbook"]]))
    wb.active["B2"] = 999
    output = BytesIO()
    wb.save(output)
    wb.close()
    parts[report["workbook"]] = output.getvalue()
    _write(path, parts)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="numeric mismatch"):
        PACK.embed_chart_workbooks(path)
    assert path.read_bytes() == original


def test_unrepresentable_decimal_is_rejected_without_rewriting(tmp_path):
    path = tmp_path / "slides.pptx"
    parts = _literal_copy(path)
    name = "ppt/slides/charts/chart1.xml"
    chart = ET.fromstring(parts[name])
    chart.find(f".//{{{C}}}numLit/{{{C}}}pt/{{{C}}}v").text = "0.1234567890123456789"
    parts[name] = ET.tostring(chart)
    _write(path, parts)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="numeric mismatch"):
        PACK.embed_chart_workbooks(path)
    assert path.read_bytes() == original
