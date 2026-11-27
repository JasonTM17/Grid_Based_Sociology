"""Embed Excel data for the bar/scatter charts exported by build_slides.mjs.

This postprocessor changes chart data references and package relationships only.
It preserves all slide/layout bytes. Workbook cells must round-trip to the exact
cached decimal values; unsupported charts or incomplete data fail explicitly.
"""
from __future__ import annotations

from io import BytesIO
from decimal import Decimal
from pathlib import Path
import os
import posixpath
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook, load_workbook
from openpyxl.utils.cell import get_column_letter, range_to_tuple

C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
T = "http://schemas.openxmlformats.org/package/2006/content-types"
CHART_TYPE = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SHEET = "Chart Data"
for prefix, uri in [("c", C), ("a", "http://schemas.openxmlformats.org/drawingml/2006/main"), ("r", R)]:
    ET.register_namespace(prefix, uri)


def _xml(root: ET.Element) -> bytes:
    # Office expects unprefixed package metadata with its default namespace.
    for uri in (P, T):
        if root.tag.startswith("{" + uri + "}"):
            ET.register_namespace("", uri)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _chart_parts(parts: dict[str, bytes]) -> list[str]:
    types = ET.fromstring(parts["[Content_Types].xml"])
    return sorted(node.attrib["PartName"].lstrip("/") for node in types
                  if node.get("ContentType") == CHART_TYPE)


def _series(root: ET.Element) -> tuple[str, list[ET.Element], tuple[str, str]]:
    plot = root.find(f"{{{C}}}chart/{{{C}}}plotArea")
    charts = [] if plot is None else [n for n in plot if n.tag.endswith("Chart")]
    if len(charts) != 1 or charts[0].tag not in {f"{{{C}}}barChart", f"{{{C}}}scatterChart"}:
        raise ValueError("Workbook packaging supports one bar or scatter chart per part")
    kind = charts[0].tag.split("}")[-1]
    series = charts[0].findall(f"{{{C}}}ser")
    if not series:
        raise ValueError("Chart contains no series")
    return kind, series, ("cat", "val") if kind == "barChart" else ("xVal", "yVal")


def _values(cache: ET.Element, numeric: bool) -> list[str | Decimal]:
    count = cache.find(f"{{{C}}}ptCount")
    points = cache.findall(f"{{{C}}}pt")
    n = int(count.get("val", "0")) if count is not None else 0
    indices = [int(p.get("idx", "-1")) for p in points]
    if n < 1 or sorted(indices) != list(range(n)):
        raise ValueError("Chart point count/indices are incomplete or duplicated")
    ordered = {int(p.attrib["idx"]): p.findtext(f"{{{C}}}v") for p in points}
    if any(v is None for v in ordered.values()):
        raise ValueError("Chart point is missing its value")
    values = [Decimal(ordered[i]) if numeric else ordered[i] for i in range(n)]
    if numeric and any(not v.is_finite() for v in values):
        raise ValueError("Chart numbers must be finite")
    return values


def _rels_path(chart: str) -> str:
    directory, name = posixpath.split(chart)
    return posixpath.join(directory, "_rels", name + ".rels")


def _validate(parts: dict[str, bytes]) -> list[dict]:
    reports = []
    for chart in _chart_parts(parts):
        root = ET.fromstring(parts[chart])
        kind, series, roles = _series(root)
        external = root.find(f"{{{C}}}externalData")
        if external is None:
            raise ValueError(f"Chart has no embedded workbook: {chart}")
        rid = external.get(f"{{{R}}}id")
        rels = ET.fromstring(parts[_rels_path(chart)])
        matches = [r for r in rels if r.get("Id") == rid]
        if len(matches) != 1 or matches[0].get("Type") != R + "/package" or matches[0].get("TargetMode") == "External":
            raise ValueError(f"Invalid embedded workbook relationship: {chart}")
        workbook = posixpath.normpath(posixpath.join(posixpath.dirname(chart), matches[0].attrib["Target"]))
        wb = load_workbook(BytesIO(parts[workbook]), data_only=False)
        points = numeric_cells = 0
        try:
            for ser in series:
                sizes = []
                for role in roles:
                    data = ser.find(f"{{{C}}}{role}")
                    refs = [] if data is None else list(data)
                    if len(refs) != 1 or refs[0].tag not in {f"{{{C}}}strRef", f"{{{C}}}numRef"}:
                        raise ValueError(f"Chart data must reference its workbook: {chart}/{role}")
                    ref = refs[0]
                    numeric = ref.tag.endswith("numRef")
                    cache = ref.find(f"{{{C}}}{'numCache' if numeric else 'strCache'}")
                    if cache is None:
                        raise ValueError("Chart reference has no cache")
                    values = _values(cache, numeric)
                    sheet, bounds = range_to_tuple(ref.findtext(f"{{{C}}}f", ""))
                    c1, r1, c2, r2 = bounds
                    if c1 != c2 or r2 - r1 + 1 != len(values):
                        raise ValueError("Chart formula range does not match cached points")
                    for row, value in enumerate(values, start=r1):
                        actual = wb[sheet].cell(row, c1).value
                        if numeric:
                            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or Decimal(str(actual)) != value:
                                raise ValueError(f"Workbook/cache numeric mismatch: {chart}, {sheet}, row {row}")
                            numeric_cells += 1
                        elif actual != value:
                            raise ValueError(f"Workbook/cache text mismatch: {chart}, {sheet}, row {row}")
                    sizes.append(len(values))
                if sizes[0] != sizes[1]:
                    raise ValueError("Chart series has different coordinate/value lengths")
                points += sizes[1]
        finally:
            wb.close()
        reports.append({"chart": chart, "type": kind, "series": len(series),
                        "points": points, "numeric_cells": numeric_cells, "workbook": workbook})
    return reports


def validate_chart_workbooks(pptx: Path) -> list[dict]:
    """Check formula ranges and every cached value against the embedded XLSX."""
    with ZipFile(pptx) as package:
        return _validate({name: package.read(name) for name in package.namelist()})


def embed_chart_workbooks(pptx: Path) -> list[dict]:
    """Add missing workbooks atomically; already packaged charts are validated."""
    pptx = Path(pptx)
    with ZipFile(pptx) as package:
        infos, comment = package.infolist(), package.comment
        parts = {info.filename: package.read(info.filename) for info in infos}
    updates: dict[str, bytes] = {}
    types = ET.fromstring(parts["[Content_Types].xml"])
    for index, chart in enumerate(_chart_parts(parts), start=1):
        root = ET.fromstring(parts[chart])
        if root.find(f"{{{C}}}externalData") is not None:
            continue
        _, series, roles = _series(root)
        wb = Workbook()
        sheet = wb.active
        sheet.title = SHEET
        sheet.freeze_panes = "A2"
        column = 1
        for i, ser in enumerate(series, start=1):
            name = ser.findtext(f"{{{C}}}tx/{{{C}}}v", f"Series {i}")
            for role in roles:
                data = ser.find(f"{{{C}}}{role}")
                literals = [] if data is None else list(data)
                if len(literals) != 1 or literals[0].tag not in {f"{{{C}}}strLit", f"{{{C}}}numLit"}:
                    raise ValueError(f"Expected literal chart data: {chart}/{role}")
                cache = literals[0]
                numeric = cache.tag.endswith("numLit")
                values = _values(cache, numeric)
                col = get_column_letter(column)
                sheet.cell(1, column, f"{name}: {role}")
                sheet.column_dimensions[col].width = 28
                fmt = cache.findtext(f"{{{C}}}formatCode", "General")
                for row, value in enumerate(values, start=2):
                    cell = sheet.cell(row, column, float(value) if numeric else value)
                    cell.number_format = fmt if numeric else "@"
                    if not numeric:
                        cell.data_type = "s"
                data.remove(cache)
                ref = ET.SubElement(data, f"{{{C}}}{'numRef' if numeric else 'strRef'}")
                ET.SubElement(ref, f"{{{C}}}f").text = f"'{SHEET}'!${col}$2:${col}${len(values) + 1}"
                cache.tag = f"{{{C}}}{'numCache' if numeric else 'strCache'}"
                ref.append(cache)
                column += 1
        output = BytesIO()
        wb.save(output)
        wb.close()
        workbook = f"ppt/embeddings/sting-chart-data-{index:03d}.xlsx"
        if workbook in parts:
            raise ValueError(f"Refusing to overwrite an unrelated workbook: {workbook}")
        updates[workbook] = output.getvalue()
        relpath = _rels_path(chart)
        rels = ET.fromstring(parts[relpath]) if relpath in parts else ET.Element(f"{{{P}}}Relationships")
        rid = "rIdStingWorkbook"
        while any(r.get("Id") == rid for r in rels):
            rid += "1"
        ET.SubElement(rels, f"{{{P}}}Relationship", Id=rid, Type=R + "/package",
                      Target=posixpath.relpath(workbook, posixpath.dirname(chart)))
        external = ET.Element(f"{{{C}}}externalData", {f"{{{R}}}id": rid})
        ET.SubElement(external, f"{{{C}}}autoUpdate", val="0")
        later = {f"{{{C}}}{tag}" for tag in ("printSettings", "userShapes", "extLst")}
        position = next((i for i, node in enumerate(root) if node.tag in later), len(root))
        root.insert(position, external)
        updates[chart], updates[relpath] = _xml(root), _xml(rels)
        ET.SubElement(types, f"{{{T}}}Override", PartName="/" + workbook, ContentType=XLSX_TYPE)
    if not updates:
        return _validate(parts)
    updates["[Content_Types].xml"] = _xml(types)
    reports = _validate(parts | updates)
    # All data checks complete before replacing the input package.
    handle, temporary = tempfile.mkstemp(prefix=".chart-data-", suffix=".pptx", dir=pptx.parent)
    os.close(handle)
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as package:
            package.comment = comment
            for info in infos:
                package.writestr(info, updates.pop(info.filename, parts[info.filename]))
            for name, payload in updates.items():
                package.writestr(name, payload)
        os.replace(temporary, pptx)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return reports
