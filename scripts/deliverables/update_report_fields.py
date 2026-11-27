"""Populate the report TOC, figure/table catalogs and page-number caches.

Windows uses Microsoft Word through pywin32. Linux/macOS can use LibreOffice
and PyMuPDF to measure pagination and fill the caches of the same Word fields.
The DOCX remains editable: Word can update its TOC/SEQ/PAGE fields with F9.

    python scripts/deliverables/build_report.py
    python scripts/deliverables/update_report_fields.py
    python scripts/deliverables/update_report_fields.py --engine libreoffice

The LibreOffice route never executes document macros or changes the user's
Office profile. It writes the original only after page numbers converge.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "reports" / "Nhom15_BaoCao_STING_PAPI.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
INDEXES = (
    ("MỤC LỤC", 'TOC \\o "1-3" \\h \\z \\u', "heading"),
    ("DANH MỤC HÌNH ẢNH", 'TOC \\h \\z \\c "Hình"', "figure"),
    ("DANH MỤC BẢNG", 'TOC \\h \\z \\c "Bảng"', "table"),
)


def _tag(name):
    return f"{{{W}}}{name}"


def _element(tag_name, **attrs):
    return etree.Element(_tag(tag_name), {_tag(k): str(v) for k, v in attrs.items()})


def _text(element):
    return "".join(element.xpath(".//w:t/text()", namespaces=NS))


def _normalize(text):
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    return re.sub(r"\s+", "", text)


def _style_id(paragraph):
    styles = paragraph.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return styles[0] if styles else "Normal"


def _run(text=None):
    run = _element("r")
    if text is not None:
        value = _element("t")
        value.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        value.text = text
        run.append(value)
    return run


def _field_marker(kind):
    run = _run()
    run.append(_element("fldChar", fldCharType=kind))
    return run


def _collect_records(document):
    body = document.find("w:body", NS)
    records = []
    for paragraph in body.findall("w:p", NS):
        style = _style_id(paragraph)
        text = _text(paragraph).strip()
        if style.startswith("Heading") and style[-1:] in "123":
            kind, level = "heading", int(style[-1])
        elif style == "Caption" and re.match(r"Hình \d+\.", text):
            kind, level = "figure", 1
        elif style == "Caption" and re.match(r"Bảng \d+\.", text):
            kind, level = "table", 1
        else:
            continue
        bookmark = f"ReportIndex{len(records) + 1:03d}"
        # Remove only bookmarks created by this helper on a previous run.
        own_ids = {node.get(_tag("id")) for node in paragraph.findall("w:bookmarkStart", NS)
                   if node.get(_tag("name"), "").startswith("ReportIndex")}
        for old in paragraph.xpath("./w:bookmarkStart|./w:bookmarkEnd", namespaces=NS):
            if old.get(_tag("id")) in own_ids:
                paragraph.remove(old)
        identity = str(10000 + len(records))
        start = _element("bookmarkStart", id=identity, name=bookmark)
        paragraph.insert(1 if paragraph.find("w:pPr", NS) is not None else 0, start)
        paragraph.append(_element("bookmarkEnd", id=identity))
        records.append({"text": text, "kind": kind, "level": level, "bookmark": bookmark})
    chapters = {m.group(1) for r in records if (m := re.match(r"CHƯƠNG (\d+)\.", r["text"]))}
    if chapters != set("1234567"):
        raise ValueError("Expected all seven report chapters before updating fields.")
    return records


def _ensure_index_styles(styles):
    for name, display, level in (("TOC1", "TOC 1", 1), ("TOC2", "TOC 2", 2),
                                 ("TOC3", "TOC 3", 3), ("TableofFigures", "Table of Figures", 1)):
        existing = styles.xpath(f'./w:style[@w:styleId="{name}"]', namespaces=NS)
        style = existing[0] if existing else _element("style", type="paragraph", styleId=name)
        if not existing:
            styles.append(style)
        for child in list(style):
            style.remove(child)
        style.append(_element("name", val=display))
        style.append(_element("basedOn", val="Normal"))
        properties = _element("pPr")
        properties.append(_element("spacing", before=0, after=45, line=264, lineRule="auto"))
        properties.append(_element("ind", left=260 * (level - 1), firstLine=0))
        properties.append(_element("jc", val="left"))
        properties.append(_element("keepLines"))
        tabs = _element("tabs")
        tabs.append(_element("tab", val="right", leader="dot", pos=9355))
        properties.append(tabs)
        style.append(properties)
        run_properties = _element("rPr")
        run_properties.append(_element("rFonts", ascii="Times New Roman", hAnsi="Times New Roman", eastAsia="Times New Roman", cs="Times New Roman"))
        run_properties.append(_element("sz", val=24))
        run_properties.append(_element("color", val="000000"))
        style.append(run_properties)


def _populate_indexes(document, records, pages):
    body = document.find("w:body", NS)
    for title, instruction, kind in INDEXES:
        heading = next((p for p in body.findall("w:p", NS) if _text(p).strip() == title), None)
        if heading is None:
            raise ValueError(f"Missing index heading: {title}")
        index = body.index(heading) + 1
        while index < len(body):
            child = body[index]
            if child.tag == _tag("sectPr"):
                break
            if child.tag == _tag("p") and (
                _style_id(child) in {"Title", "Heading1"}
                or child.find("w:pPr/w:sectPr", NS) is not None
            ):
                break
            body.remove(child)
        selected = [r for r in records if r["kind"] == kind]
        for offset, record in enumerate(selected):
            paragraph = _element("p")
            properties = _element("pPr")
            properties.append(_element("pStyle", val=f"TOC{record['level']}" if kind == "heading" else "TableofFigures"))
            paragraph.append(properties)
            if offset == 0:
                paragraph.append(_field_marker("begin"))
                run = _run()
                instr = _element("instrText")
                instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                instr.text = f" {instruction} "
                run.append(instr)
                paragraph.append(run)
                paragraph.append(_field_marker("separate"))
            hyperlink = _element("hyperlink", anchor=record["bookmark"], history="1")
            hyperlink.append(_run(record["text"]))
            run = _run()
            run.append(_element("tab"))
            hyperlink.append(run)
            hyperlink.append(_run(str(pages.get(record["bookmark"], 1))))
            paragraph.append(hyperlink)
            if offset == len(selected) - 1:
                paragraph.append(_field_marker("end"))
            body.insert(index + offset, paragraph)


def _write_archive(source, destination, document, styles):
    replacement = {
        "word/document.xml": etree.tostring(document, encoding="UTF-8", xml_declaration=True, standalone=True),
        "word/styles.xml": etree.tostring(styles, encoding="UTF-8", xml_declaration=True, standalone=True),
    }
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output:
        for entry in archive.infolist():
            output.writestr(entry, replacement.get(entry.filename, archive.read(entry.filename)))


def _resolve_soffice(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise FileNotFoundError(f"LibreOffice executable not found: {explicit}")
    runtime = os.environ.get("CODEX_PRIMARY_RUNTIME_ROOT")
    candidates = [Path(runtime) / "dependencies/bin/override/soffice"] if runtime else []
    candidates += [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable:
        return executable
    raise FileNotFoundError("Install LibreOffice or supply --soffice /path/to/soffice.")


def _measure_pages(soffice, path, directory, records):
    import fitz

    pdf = directory / f"{path.stem}.pdf"
    pdf.unlink(missing_ok=True)
    process = subprocess.run(
        [soffice, f"-env:UserInstallation={(directory / 'profile').as_uri()}",
         "--headless", "--norestore", "--convert-to", "pdf", "--outdir", str(directory), str(path)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if process.returncode or not pdf.is_file() or not pdf.stat().st_size:
        raise RuntimeError(f"LibreOffice PDF export failed:\n{process.stdout}\n{process.stderr}")
    with fitz.open(pdf) as rendered:
        # Contents pages contain the same titles. Only the final body occurrence
        # of Chapter 1 starts decimal report pagination. Crop away footers.
        text = [_normalize(page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, page.rect.height - 45))) for page in rendered]
    chapter_one = _normalize(next(r["text"] for r in records if r["text"].startswith("CHƯƠNG 1.")))
    occurrences = [i for i, value in enumerate(text) if chapter_one in value]
    if not occurrences:
        raise ValueError("Could not locate Chapter 1 in the rendered report.")
    start = occurrences[-1]
    pages = {}
    for record in records:
        needle = _normalize(record["text"])
        matches = [i for i in range(start, len(text)) if needle in text[i]]
        if len(matches) != 1:
            raise ValueError(f"Expected one body location, got {len(matches)}: {record['text']}")
        pages[record["bookmark"]] = matches[0] - start + 1
    return pages, len(text)


def update_libreoffice(path, soffice):
    with zipfile.ZipFile(path) as archive:
        document = etree.fromstring(archive.read("word/document.xml"))
        styles = etree.fromstring(archive.read("word/styles.xml"))
    records = _collect_records(document)
    _ensure_index_styles(styles)
    pages = {}
    with tempfile.TemporaryDirectory(prefix="report_fields_") as temporary:
        directory = Path(temporary)
        working = directory / path.name
        for attempt in range(1, 6):
            _populate_indexes(document, records, pages)
            _write_archive(path, working, document, styles)
            measured, total = _measure_pages(soffice, working, directory, records)
            if measured == pages:
                # Preserve pictures and native field definitions instead of
                # round-tripping a DOCX through another editor's exporter.
                shutil.copy2(working, path)
                print(f"Updated {len(records)} index entries; pagination stable after {attempt} passes ({total} pages, LibreOffice).")
                return
            pages = measured
        raise RuntimeError("Index page numbers did not converge; the original DOCX was not changed.")


def update_word(path):
    import win32com.client as win32

    word = None
    try:
        word = win32.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(str(path), ReadOnly=False)
        document.Fields.Update()
        for collection in (document.TablesOfContents, document.TablesOfFigures):
            for index in range(1, collection.Count + 1):
                collection(index).Update()
        document.Repaginate()
        for collection in (document.TablesOfContents, document.TablesOfFigures):
            for index in range(1, collection.Count + 1):
                collection(index).UpdatePageNumbers()
        document.Save()
        document.Close(False)
        print(f"Updated report fields with Microsoft Word: {path.name}")
    finally:
        if word is not None:
            word.Quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DOCX)
    parser.add_argument("--engine", choices=("auto", "word", "libreoffice"), default="auto")
    parser.add_argument("--soffice", help="LibreOffice executable, when not on PATH")
    args = parser.parse_args()
    path = args.path.resolve()
    if not path.is_file():
        parser.error(f"Report not found: {path}; run build_report.py first.")
    engine = "word" if args.engine == "auto" and sys.platform == "win32" else args.engine
    try:
        if engine == "word":
            update_word(path)
        else:
            update_libreoffice(path, _resolve_soffice(args.soffice))
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Report field update failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
