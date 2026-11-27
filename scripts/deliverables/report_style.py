"""Apply the measured user reference style without recomputing report content.

The shared formatter is used by build_report.py and can update the existing
DOCX while retaining populated Word fields. Reference measurements are in
reports/report_format_notes.md; the other course's DOCX is not a dependency.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Twips

BLACK = RGBColor(0, 0, 0)
PAGE_WIDTH, PAGE_HEIGHT = 11906, 16838
LEFT_MARGIN, RIGHT_MARGIN = 1417, 1134
TEXT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
ASSETS = Path(__file__).resolve().parents[2] / "assets"
COVER_XML = ASSETS / "report-cover.xml"
COVER_LOGO = ASSETS / "report-cover-logo.png"


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
            widths[index] = max(widths[index], 1021)
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
        for attribute, value in {"val": "single", "sz": "4", "color": "D9D9D9"}.items():
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
            for edge, value in {"top": 65, "bottom": 65, "left": 85, "right": 85}.items():
                item = margins.find(qn(f"w:{edge}"))
                if item is None:
                    item = OxmlElement(f"w:{edge}")
                    margins.append(item)
                item.set(qn("w:w"), str(value))
                item.set(qn("w:type"), "dxa")
            if row_index == 0:
                shade = OxmlElement("w:shd")
                shade.set(qn("w:val"), "clear")
                shade.set(qn("w:fill"), "D9E2F3")
                props.insert_element_before(shade, "w:tcMar", "w:vAlign")
            for paragraph in cell.paragraphs:
                fmt = paragraph.paragraph_format
                fmt.space_before = fmt.space_after = Pt(1)
                fmt.line_spacing = 1.05
                fmt.first_line_indent = Twips(0)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if row_index == 0:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    fmt.keep_with_next = True
                elif len(cell.text) <= 14 and any(c.isdigit() for c in cell.text):
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    _font(run, 11 if len(table.columns) >= 4 else 12)


def _set_page(section, *, cover=False):
    section.page_width, section.page_height = Twips(PAGE_WIDTH), Twips(PAGE_HEIGHT)
    section.left_margin, section.right_margin = Twips(LEFT_MARGIN), Twips(RIGHT_MARGIN)
    section.top_margin = section.bottom_margin = Twips(1134)
    section.header_distance = Twips(720 if cover else 432)
    section.footer_distance = Twips(576)


def replace_cover(document):
    """Insert the actual reference blocks with their report-specific text."""
    cover = parse_xml(COVER_XML.read_bytes())
    border = cover.find(qn("w:pgBorders"))
    blip = cover.find(".//" + qn("a:blip"))
    if border is None or blip is None:
        raise ValueError("Missing page border or logo in the report cover template.")
    marker = next((p for p in document.paragraphs if p._p.pPr is not None
                   and p._p.pPr.find(qn("w:sectPr")) is not None), None)
    if marker is None:
        raise ValueError("Missing cover section boundary; refusing to replace report body.")
    _set_page(document.sections[0], cover=True)
    section_properties = marker._p.pPr.find(qn("w:sectPr"))
    old_border = section_properties.find(qn("w:pgBorders"))
    if old_border is not None:
        section_properties.remove(old_border)
    section_properties.insert_element_before(border, "w:lnNumType", "w:pgNumType", "w:cols")
    relationship, _ = document.part.get_or_add_image(str(COVER_LOGO))
    blip.set(qn("r:embed"), relationship)
    drawing = cover.find(".//" + qn("wp:docPr"))
    drawing.set("id", str(document.part.next_id))
    parent = document._element.body
    while parent[0] is not marker._p:
        parent.remove(parent[0])
    for block in list(cover.findall(qn("w:p"))):
        marker._p.addprevious(block)


def _add_page_number_footer(
    section, placeholder: str, *, fmt: str = "decimal", start: str | None = None
) -> None:
    properties = section._sectPr
    numbering = properties.find(qn("w:pgNumType"))
    if numbering is None:
        numbering = OxmlElement("w:pgNumType")
        properties.insert_element_before(
            numbering,
            "w:cols",
            "w:formProt",
            "w:vAlign",
            "w:noEndnote",
            "w:titlePg",
            "w:textDirection",
            "w:bidi",
            "w:rtlGutter",
            "w:docGrid",
            "w:printerSettings",
            "w:sectPrChange",
        )
    numbering.set(qn("w:fmt"), fmt)
    if start is not None:
        numbering.set(qn("w:start"), start)
    elif qn("w:start") in numbering.attrib:
        del numbering.attrib[qn("w:start")]
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    _font(run, 12)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    result = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = placeholder
    result.append(text)
    field.append(result)
    paragraph._p.append(field)


def apply_reference_style(document):
    """Change layout only; retain all scientific text, tables and field content."""
    for section in document.sections:
        _set_page(section)
    formats = {
        "Normal": (13, False, 1.35, 0, 7),
        "Body Text": (13, False, 1.5, 0, 6),
        "Title": (20, True, 1.15, 0, 12),
        "Heading 1": (16, True, 1.15, 18, 10),
        "Heading 2": (14, True, 1.15, 13, 6),
        "Heading 3": (12, True, 1.15, 10, 5),
        "Caption": (12, True, 1.0, 2, 8),
    }
    for name, (size, bold, leading, before, after) in formats.items():
        style = document.styles[name]
        style.font.name, style.font.size = "Times New Roman", Pt(size)
        style.font.bold, style.font.color.rgb = bold, BLACK
        style.font.italic = name == "Caption"
        fmt = style.paragraph_format
        fmt.line_spacing, fmt.space_before, fmt.space_after = leading, Pt(before), Pt(after)
        fmt.first_line_indent = Twips(720 if name == "Body Text" else 0)
        if name == "Body Text":
            fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if name in ("Title", "Caption"):
            fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if name == "Caption":
            fmt.keep_with_next = False
            fmt.keep_together = True

        properties = style.element.get_or_add_pPr()
        for border in list(properties.findall(qn("w:pBdr"))):
            properties.remove(border)
    for level, (indent, line_spacing, after) in enumerate(((0, 1.15, 2), (260, 1.15, 5), (480, 1.15, 5)), 1):
        name = f"TOC {level}"
        if name not in document.styles:
            document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH, builtin=True)
        style = document.styles[name]
        style.font.name, style.font.size = "Times New Roman", Pt(12)
        style.paragraph_format.left_indent = Twips(indent)
        style.paragraph_format.line_spacing = line_spacing
        style.paragraph_format.space_after = Pt(after)
    for paragraph in document.paragraphs:
        name = paragraph.style.name
        size = formats[name][0] if name in formats and name != "Normal" else None
        if name == "Heading 1" and paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            size = 20
        for run in paragraph.runs:
            if name == "Caption":
                run.bold, run.italic = True, True
            _font(run, size)
    replace_cover(document)
    for table in document.tables:
        _format_table(table)

    sections = list(document.sections)
    for section in sections[1:]:
        section.footer.is_linked_to_previous = False
        section.first_page_footer.is_linked_to_previous = False
    for index, section in enumerate(sections):
        section.different_first_page_header_footer = index == 0
        for footer in (section.footer, section.first_page_footer):
            for paragraph in footer.paragraphs:
                paragraph.clear()
        if 0 < index < len(sections) - 1:
            _add_page_number_footer(
                section, "i", fmt="lowerRoman", start="1" if index == 1 else None
            )
        elif index == len(sections) - 1 and index > 0:
            _add_page_number_footer(section, "1", fmt="decimal", start="1")
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
