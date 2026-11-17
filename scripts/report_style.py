"""Apply the measured user reference style without recomputing report content.

The shared formatter is used by build_report.py and can update the existing
DOCX while retaining populated Word fields. Reference measurements are in
reports/report_format_notes.md; the other course's DOCX is not a dependency.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Twips

BLACK = RGBColor(0, 0, 0)
PAGE_WIDTH, PAGE_HEIGHT = 11909, 16834
TEXT_WIDTH = PAGE_WIDTH - 2 * 1080
COVER_XML = Path(__file__).resolve().parents[1] / "assets/report-cover.xml"


def _font(run, size=None):
    run.font.name = "Times New Roman"
    run.font.color.rgb = BLACK
    if size is not None:
        run.font.size = Pt(size)
    fonts = run._r.get_or_add_rPr().rFonts
    for name in list(fonts.attrib):
        if name.endswith("Theme"):
            del fonts.attrib[name]
    for family in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn(f"w:{family}"), "Times New Roman")


def _format_table(table):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [column.width.twips for column in table.columns]
    for index, cell in enumerate(table.rows[0].cells):
        if cell.text == "value_cv":
            widths[index] = max(widths[index], 1021)  # keep the short CV key on one line
    if sum(widths) > TEXT_WIDTH:
        widths = [int(width * TEXT_WIDTH / sum(widths)) for width in widths]
    for column, width in zip(table.columns, widths):
        column.width = Twips(width)
    properties = table._tbl.tblPr
    total_width = properties.find(qn("w:tblW"))
    total_width.set(qn("w:type"), "dxa")
    total_width.set(qn("w:w"), str(sum(widths)))
    borders = properties.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = borders.find(qn(f"w:{edge}"))
        if item is None:
            item = OxmlElement(f"w:{edge}")
            borders.append(item)
        for attribute, value in {"val": "single", "sz": "4", "color": "000000"}.items():
            item.set(qn(f"w:{attribute}"), value)
    for row_index, row in enumerate(table.rows):
        row.height = None
        props = row._tr.get_or_add_trPr()
        if props.find(qn("w:cantSplit")) is None:
            props.append(OxmlElement("w:cantSplit"))
        if row_index == 0:
            if props.find(qn("w:tblHeader")) is None:
                props.append(OxmlElement("w:tblHeader"))
        for column_index, cell in enumerate(row.cells):
            cell.width = Twips(widths[column_index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            for shading in list(props.findall(qn("w:shd"))):
                props.remove(shading)
            margins = props.find(qn("w:tcMar"))
            if margins is None:
                margins = OxmlElement("w:tcMar")
                props.append(margins)
            for edge, value in {"top": 30, "bottom": 30, "left": 60, "right": 60}.items():
                item = margins.find(qn(f"w:{edge}"))
                if item is None:
                    item = OxmlElement(f"w:{edge}")
                    margins.append(item)
                item.set(qn("w:w"), str(value))
                item.set(qn("w:type"), "dxa")
            for paragraph in cell.paragraphs:
                fmt = paragraph.paragraph_format
                fmt.space_before = fmt.space_after = Pt(1)
                fmt.line_spacing = 1.05
                if row_index == 0:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    fmt.keep_with_next = True
                for run in paragraph.runs:
                    _font(run, 12)


def replace_cover(document):
    """Insert the actual reference blocks with their report-specific text."""
    cover = parse_xml(COVER_XML.read_bytes())
    table = cover.find(qn("w:tbl"))
    if table is None:
        raise ValueError("Missing table in the report cover template.")
    marker = next((p for p in document.paragraphs if p._p.pPr is not None
                   and p._p.pPr.find(qn("w:sectPr")) is not None), None)
    if marker is None:
        raise ValueError("Missing cover section boundary; refusing to replace report body.")
    parent = document._element.body
    while parent[0] is not marker._p:
        parent.remove(parent[0])
    for block in list(cover):
        marker._p.addprevious(block)
    return table


def apply_reference_style(document):
    """Change layout only; retain all scientific text, tables and field content."""
    for section in document.sections:
        section.page_width, section.page_height = Twips(PAGE_WIDTH), Twips(PAGE_HEIGHT)
        section.left_margin = section.right_margin = Twips(1080)
        section.top_margin = section.bottom_margin = Twips(1008)
        section.header_distance, section.footer_distance = Twips(720), Twips(454)
    for name, size, bold, before in (
        ("Normal", 12, False, 0), ("Title", 20, True, 6),
        ("Heading 1", 14, True, 24), ("Heading 2", 12, True, 10),
        ("Heading 3", 12, True, 10),
    ):
        style = document.styles[name]
        style.font.name, style.font.size = "Times New Roman", Pt(size)
        style.font.bold, style.font.color.rgb = bold, BLACK
        fmt = style.paragraph_format
        fmt.line_spacing, fmt.space_before, fmt.space_after = 1.1, Pt(before), Pt(6)
        fmt.first_line_indent = Twips(0)
        # The old Word Title style contains a theme-colored bottom rule.
        properties = style.element.get_or_add_pPr()
        for border in list(properties.findall(qn("w:pBdr"))):
            properties.remove(border)
    for paragraph in document.paragraphs:
        fmt = paragraph.paragraph_format
        fmt.line_spacing = 1.1
        heading = paragraph.style.name.startswith("Heading ")
        if heading:
            fmt.space_before = Pt(24 if paragraph.style.name == "Heading 1" else 10)
        if paragraph.style.name == "Title" and paragraph._p.pPr is not None:
            for border in list(paragraph._p.pPr.findall(qn("w:pBdr"))):
                paragraph._p.pPr.remove(border)
        for run in paragraph.runs:
            _font(run, 14 if paragraph.style.name == "Heading 1" else 12 if heading else None)
    cover_table = replace_cover(document)
    for table in document.tables:
        if table._tbl is not cover_table:
            _format_table(table)
    # The previous document had empty footer parts. Create PAGE fields explicitly;
    # unlink first so clearing the cover cannot clear later sections' page numbers.
    for section in list(document.sections)[1:]:
        section.footer.is_linked_to_previous = False
        section.first_page_footer.is_linked_to_previous = False
    for index, section in enumerate(document.sections):
        section.different_first_page_header_footer = index == 0
        for footer in (section.footer, section.first_page_footer):
            for paragraph in footer.paragraphs:
                paragraph.clear()
        if index:
            paragraph = section.footer.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            _font(run, 12)
            field = OxmlElement("w:fldSimple")
            field.set(qn("w:instr"), "PAGE")
            result = OxmlElement("w:r")
            text = OxmlElement("w:t")
            text.text = "1"
            result.append(text)
            field.append(result)
            paragraph._p.append(field)
    settings = document.settings.element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, help="Write a separate copy when the source is open in Word.")
    parser.add_argument("--cover-only", action="store_true", help="Keep the existing body and replace only the cover.")
    args = parser.parse_args()
    document = Document(args.path)
    if args.cover_only:
        replace_cover(document)
    else:
        apply_reference_style(document)
    target = args.output or args.path
    document.save(target)
    print(f"Applied reference formatting: {target.name}")


if __name__ == "__main__":
    main()
