"""Gate artifact nộp bài thống nhất: báo cáo DOCX, slide 15 trang, notebook và provenance PAPI."""

from __future__ import annotations

import copy
from base64 import b64decode
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pytest
from docx import Document
from docx.oxml.ns import qn
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]

REPORT_DOCX = ROOT / "reports" / "Nhom15_BaoCao_STING_PAPI.docx"
SUBMISSION_PPTX = ROOT / "slides" / "Nhom15_STING_PAPI.pptx"
SUBMISSION_NB = ROOT / "notebooks" / "Nhom15_STING_PAPI.ipynb"
PROVENANCE = ROOT / "data" / "raw" / "papi" / "PROVENANCE.md"
PAPI_PDF = ROOT / "data" / "raw" / "papi" / "PAPI_2024_REPORT_VIE_final.pdf"
EXPECTED_ARI_STR = "0.950"
SLIDE_COUNT = 15
THANK_YOU = "Cảm ơn thầy và các bạn."

_IGNORE_PATTERNS = (
    re.compile(r"""filterwarnings\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
    re.compile(r"""simplefilter\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
)
_PDF_HASH_RE = re.compile(
    r"PAPI_2024_REPORT_VIE_final\.pdf.*?SHA-256\s+`([a-f0-9]{64})`",
    re.IGNORECASE | re.DOTALL,
)
_HOST_ABS_PATH_PATTERNS = (
    re.compile(r"D:\\"),
    re.compile(r"C:\\Users"),
    re.compile(r"/Users/"),
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_report_embeds_current_canonical_figures():
    figures = (
        "00_synthetic_sting.png",
        "sting_first_real.png",
        "papi_forecast_values.png",
        "papi_forecast_grid.png",
        "course_confusion_matrix.png",
        "evolution.png",
        "map_2024.png",
        "stakeholder_quadrants_2024.png",
        "external_pci_by_cluster.png",
        "external_health_density_2020.png",
        "external_grdp_by_cluster.png",
        "external_wdi_panel.png",
        "external_poverty_by_cluster.png",
    )
    report = Document(REPORT_DOCX)
    shapes = list(report.inline_shapes)
    assert len(shapes) == len(figures) + 1
    for shape, path in zip(
        shapes,
        (
            ROOT / "assets/report-cover-logo.png",
            *(ROOT / "results" / "figs" / name for name in figures),
        ),
        strict=True,
    ):
        relation = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        embedded = report.part.related_parts[relation].blob
        assert hashlib.sha256(embedded).hexdigest() == _sha256_file(path), (
            f"Hình chưa cập nhật từ {path.name}; cần tạo lại báo cáo."
        )


def test_report_uses_the_user_final_template_geometry():
    report = Document(REPORT_DOCX)
    cover, front, body = report.sections
    assert (cover.left_margin.twips, cover.right_margin.twips) == (1699, 1138)
    assert (cover.page_width.twips, cover.page_height.twips) == (11906, 16838)
    border = cover._sectPr.find(qn("w:pgBorders"))
    assert border.get(qn("w:display")) == "firstPage"
    assert [edge.get(qn("w:val")) for edge in border] == ["single"] * 4
    assert (body.left_margin.twips, body.right_margin.twips) == (1417, 1134)
    assert front._sectPr.find(qn("w:pgBorders")) is None
    assert body._sectPr.find(qn("w:pgNumType")).get(qn("w:start")) == "1"
    assert report.styles["Body Text"].paragraph_format.line_spacing == 1.5
    cover_lines = [paragraph.text for paragraph in report.paragraphs[:16]]
    assert cover_lines.index("ThS. Lê Minh Tân") < cover_lines.index("KHÓA 2024–2028")
    assert cover_lines.index("KHÓA 2024–2028") < cover_lines.index("NHÓM 15 · MÃ HỌC PHẦN MALE431984")


def check_pptx_submission(prs: Presentation) -> list[str]:
    """Kiểm tra 15 slide, kết luận gộp cảm ơn và ghi chú ở mọi trang."""
    violations: list[str] = []
    count = len(prs.slides)
    if count != SLIDE_COUNT:
        violations.append(f"Nhom15_STING_PAPI.pptx có {count} slide, cần đúng {SLIDE_COUNT}")
    else:
        closing_text = "\n".join(
            shape.text.strip() for shape in prs.slides[-1].shapes if shape.has_text_frame and shape.text.strip()
        )
        if THANK_YOU not in closing_text:
            violations.append("slide kết luận thiếu lời cảm ơn")
        if "kết luận" not in closing_text.lower():
            violations.append("slide cuối thiếu phần kết luận")
    for index, slide in enumerate(prs.slides, start=1):
        notes = ""
        if slide.has_notes_slide:
            frame = slide.notes_slide.notes_text_frame
            notes = (frame.text if frame is not None else "").strip()
        if not notes:
            violations.append(f"slide {index}: ghi chú trống")
    return violations


def _cell_source_text(cell: dict) -> str:
    raw = cell.get("source", "")
    if isinstance(raw, list):
        return "".join(raw)
    return str(raw)


def check_notebook_cells(nb: dict) -> list[str]:
    violations: list[str] = []
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        violations.append("notebook không có ô code")
        return violations

    for index, cell in enumerate(code_cells):
        source = _cell_source_text(cell)
        for pattern in _IGNORE_PATTERNS:
            if pattern.search(source):
                violations.append(f"ô code #{index}: nguồn chứa lệnh bỏ qua cảnh báo ({pattern.pattern})")

        outputs = cell.get("outputs")
        if not outputs:
            violations.append(f"ô code #{index}: không có output đã lưu")
            continue

        for output in outputs:
            if output.get("output_type") == "error":
                violations.append(f"ô code #{index}: output_type=error")
            if output.get("output_type") == "stream" and output.get("name") == "stderr":
                violations.append(f"ô code #{index}: có stderr stream")

    return violations


def notebook_markdown_text(nb: dict) -> str:
    return "\n".join(
        _cell_source_text(cell) for cell in nb.get("cells", []) if cell.get("cell_type") == "markdown"
    )


def notebook_executed_text(nb: dict) -> str:
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs") or []:
            kind = output.get("output_type")
            if kind == "stream":
                text = output.get("text", "")
                chunks.append("".join(text) if isinstance(text, list) else str(text))
            elif kind in ("execute_result", "display_data"):
                data = output.get("data") or {}
                plain = data.get("text/plain")
                if plain is not None:
                    chunks.append("".join(plain) if isinstance(plain, list) else str(plain))
    return "\n".join(chunks)


def check_notebook_no_absolute_host_paths(nb: dict) -> list[str]:
    blob = notebook_executed_text(nb)
    return [
        f"output notebook chứa đường dẫn host khớp {pattern.pattern!r}"
        for pattern in _HOST_ABS_PATH_PATTERNS
        if pattern.search(blob)
    ]


def provenance_pdf_sha256(md_text: str) -> str | None:
    match = _PDF_HASH_RE.search(md_text)
    return match.group(1).lower() if match else None


def check_papi_pdf_provenance(provenance_path: Path = PROVENANCE, pdf_path: Path = PAPI_PDF) -> list[str]:
    violations: list[str] = []
    if not provenance_path.is_file():
        violations.append(f"thiếu {provenance_path.relative_to(ROOT)}")
        return violations
    if not pdf_path.is_file():
        violations.append(f"thiếu {pdf_path.relative_to(ROOT)}")
        return violations

    text = provenance_path.read_text(encoding="utf-8")
    if "PAPI_2024_REPORT_VIE_final.pdf" not in text:
        violations.append("PROVENANCE.md không liệt kê PAPI_2024_REPORT_VIE_final.pdf")

    listed = provenance_pdf_sha256(text)
    if listed is None:
        violations.append("PROVENANCE.md không ghi SHA-256 của PAPI_2024_REPORT_VIE_final.pdf")
        return violations

    actual = _sha256_file(pdf_path)
    if listed != actual:
        violations.append(f"SHA-256 trong PROVENANCE ({listed}) khác file thực ({actual})")
    return violations


@pytest.fixture(scope="module")
def submission_notebook() -> dict:
    assert SUBMISSION_NB.is_file(), "thiếu notebooks/Nhom15_STING_PAPI.ipynb"
    return json.loads(SUBMISSION_NB.read_text(encoding="utf-8"))


def test_unified_pptx_exists_notes_and_content():
    assert SUBMISSION_PPTX.is_file(), "thiếu slides/Nhom15_STING_PAPI.pptx"
    presentation = Presentation(str(SUBMISSION_PPTX))
    violations = check_pptx_submission(presentation)
    assert not violations, "\n".join(violations)

    def slide_text(slide):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text)
            if shape.has_table:
                parts.extend(cell.text for row in shape.table.rows for cell in row.cells)
        return "\n".join(parts).strip()

    visible = [slide_text(slide) for slide in presentation.slides]
    # Line breaks inside editable cells are layout choices, not missing evidence.
    full_text = " ".join("\n".join(visible).split())
    for required in (
        "Phân cụm dựa trên lưới STING",
        "ARI = 0,950",
        "869/869 điểm giữ nguyên ô STING",
        "631 điểm",
        "48 / 61",
        "bảng mô tả 63 tỉnh",
        "Ngoài vùng dày, phía điểm cao",
        "Ngoài vùng dày, điểm 6.1 thấp",
        "Thiếu dữ liệu 2024",
        "1,787",
        "1,8791",
        "Lạng Sơn",
        "(13, 9)",
        "(12, 10)",
        "0,0736",
        "0,0641",
        "0 / 11",
        "AUC 0,816",
        "Hồi cứu thăm dò",
        "Wang, Yang & Muntz (VLDB 1997)",
    ):
        assert required in full_text, f"Thiếu nội dung slide: {required}"
    assert "Nhiễu¹" not in full_text
    assert "(kèm Bạc Liêu, Huế" not in full_text
    assert "bứt phá vượt chuẩn" not in full_text.lower()
    for required in ("Nhận xét", "76,2%", "12,7%", "7,9%", "3,2%", "2,235", "1,787"):
        assert required in visible[12], f"Slide 13 thiếu thống kê hoặc nhận xét: {required}"
    assert all(term in visible[1] for term in ("109 ô 0→NaN", "0,015"))
    assert all(term in visible[6] for term in ("0,0738", "0,0488", "12 ≥ 5"))
    assert all(term in visible[7] for term in ("0,524", "74,6%"))
    assert all(term in visible[8] for term in ("0,2732", "Conformal 90%", "94,9%", "4/28"))
    assert all(term in visible[9] for term in ("Quantile", "CLIQUE", "49,0%"))
    assert all(term in visible[10] for term in ("Year-FE CR1", "0,7007"))
    assert all(term in visible[11] for term in ("0,0156", "0,047", "0,094", "117 BH-FDR", "0,7930"))
    assert all(term in visible[13] for term in ("293 kiểm thử", "Streamlit 6 Tab", "28 sheet", "16 hồ sơ"))
    assert "khách hàng" not in full_text.lower()
    assert THANK_YOU in visible[-1]
    assert "kết luận" in visible[-1].lower()

    # Core evidence must remain editable, with data embedded in both charts.
    tables = [shape.table for slide in presentation.slides for shape in slide.shapes if shape.has_table]
    charts = [shape.chart for slide in presentation.slides for shape in slide.shapes if shape.has_chart]
    assert len(tables) >= 12, "Các bảng bằng chứng phải là bảng PowerPoint có thể chỉnh sửa"
    assert len(charts) == 2
    assert all(chart.part.chart_workbook.xlsx_part is not None for chart in charts)

    notes = "\n".join(slide.notes_slide.notes_text_frame.text for slide in presentation.slides)
    assert "khách hàng" not in notes.lower()
    for name in ("Nhom15_BaoCao_STING_PAPI.docx", "Nhom15_STING_PAPI.ipynb", "Nhom15_TienXuLy_PAPI.ipynb"):
        assert name in notes


def test_unified_notebook_root_skips_incomplete_loose_folder(submission_notebook, tmp_path, monkeypatch):
    root = tmp_path / "Đồ án PAPI"
    loose = root / "submissions/Nhom15_STING_PAPI"
    for relative in (
        "src/sting.py",
        "src/preprocessing.py",
        "scripts/common/midterm_clustering.py",
        "data/processed/papi_panel_63_2011_2024.csv",
        "models/predict_config.json",
        "submissions/Nhom15_STING_PAPI/src/sting.py",
    ):
        marker = root / relative
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

    monkeypatch.chdir(loose)
    for env_key in ("STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH"):
        monkeypatch.delenv(env_key, raising=False)
    setup = next(cell for cell in submission_notebook["cells"] if cell["cell_type"] == "code")
    finder = _cell_source_text(setup).split("ROOT = _find_project_root()", 1)[0]
    namespace = {}
    exec(finder, namespace)
    assert namespace["_find_project_root"]() == root


def test_submission_notebook_cells(submission_notebook: dict):
    violations = check_notebook_cells(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_no_absolute_host_paths(submission_notebook: dict):
    violations = check_notebook_no_absolute_host_paths(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_sections_and_key_numbers(submission_notebook: dict):
    md_text = notebook_markdown_text(submission_notebook)
    code_cells = [c for c in submission_notebook.get("cells", []) if c.get("cell_type") == "code"]
    for section in (
        "Phần 1. Lý thuyết STING",
        "Phần 2. Dữ liệu PAPI",
        "Phần 3. Phân cụm STING trên PAPI",
        "Phần 4. STING theo từng năm",
        "Phần 5. Thống kê bàn giao cho khách hàng",
        "Phần 6. Thí nghiệm dự báo 2024",
        "Phần 7. Kết luận tổng hợp",
        "Phụ lục A.",
        "Phụ lục B.",
        "Phụ lục C.",
        "Phụ lục D.",
        "Phụ lục E.",
        "Phụ lục F.",
    ):
        assert section in md_text, f"Thiếu mục {section}"
    for calculation in ("KMeans(", "DBSCAN(", "build_stakeholder_tables", "PREPROCESSING_PIPELINE"):
        assert any(calculation in _cell_source_text(c) for c in code_cells)

    output = notebook_executed_text(submission_notebook)
    for expected in (
        "2 cụm, mỗi cụm 7 điểm. 1 điểm nhiễu.",
        f"ARI = {EXPECTED_ARI_STR}",
        "869 quan sát đủ hai chỉ tiêu",
        "56 ô dày tạo thành 3 vùng liên thông.",
        "Nhiễu: 171/869 quan sát (19.7%).",
        "STING: 869/869 điểm cùng chỉ số ô, 869/869 nhãn trùng.",
        "K-means k=2: 68/869 điểm đổi nhóm sau ghép tên cụm.",
        "Ngoài vùng dày, phía điểm cao",
        "Ngoài vùng dày, điểm 6.1 thấp",
        "Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long",
    ):
        assert expected in output


def test_unified_notebook_contains_zscore_and_stakeholder_figures(submission_notebook):
    cells = submission_notebook["cells"]
    z_cell = next(c for c in cells if "papi-zscore-comparison" in c.get("metadata", {}).get("tags", []))
    png_z = next(out["data"]["image/png"] for out in z_cell["outputs"] if "image/png" in out.get("data", {}))
    assert b64decode("".join(png_z)) == (ROOT / "results/figs/papi_zscore_comparison.png").read_bytes()

    stake_cell = next(c for c in cells if "results/figs/stakeholder_quadrants_2024.png" in _cell_source_text(c))
    png_s = next(out["data"]["image/png"] for out in stake_cell["outputs"] if "image/png" in out.get("data", {}))
    assert b64decode("".join(png_s)) == (ROOT / "results/figs/stakeholder_quadrants_2024.png").read_bytes()


def test_unified_slide_rejects_changed_panel_without_overwriting_reviewed_output(tmp_path):
    panel_path = Path("data/processed/papi_panel_63_2011_2024.csv")
    slide_builder = Path("scripts/deliverables/build_slides.py")
    copy_dirs = (
        "src", "scripts/common", "scripts/analysis", "scripts/supervised",
        "scripts/deliverables", "data/processed", "models", "results",
        "reports", "assets",
    )
    for rel_dir in copy_dirs:
        shutil.copytree(ROOT / rel_dir, tmp_path / rel_dir)
    shutil.copy2(ROOT / "app.py", tmp_path / "app.py")
    panel = pd.read_csv(tmp_path / panel_path)
    year = panel.year.eq(2024)
    features = ["sd_4_2", "sd_6_1"]
    panel.loc[year & panel.province_vi.eq("Quảng Ninh"), features] = (
        panel.loc[year & panel.province_vi.eq("Lạng Sơn"), features].to_numpy()
    )
    panel.to_csv(tmp_path / panel_path, index=False)
    reviewed = tmp_path / "slides/Nhom15_STING_PAPI.pptx"
    reviewed.parent.mkdir()
    reviewed.write_bytes(b"previous reviewed presentation")
    completed = subprocess.run(
        [sys.executable, str(slide_builder)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert completed.returncode != 0
    assert "Dữ liệu slide đã thay đổi" in completed.stderr
    assert reviewed.read_bytes() == b"previous reviewed presentation"


def test_papi_pdf_provenance_chain():
    violations = check_papi_pdf_provenance()
    assert not violations, "\n".join(violations)


def test_gate_detects_extra_slide_in_memory():
    presentation = Presentation(str(SUBMISSION_PPTX))
    layout_index = 6 if len(presentation.slide_layouts) > 6 else 0
    presentation.slides.add_slide(presentation.slide_layouts[layout_index])
    assert len(presentation.slides) == SLIDE_COUNT + 1
    violations = check_pptx_submission(presentation)
    assert any(f"cần đúng {SLIDE_COUNT}" in message for message in violations)


def test_gate_rejects_missing_thanks_on_conclusion_slide():
    presentation = Presentation(str(SUBMISSION_PPTX))
    text_box = next(
        shape for shape in presentation.slides[-1].shapes
        if shape.has_text_frame and THANK_YOU in shape.text
    )
    text_box.text = text_box.text.replace(THANK_YOU, "")
    assert "slide kết luận thiếu lời cảm ơn" in check_pptx_submission(presentation)


def test_gate_detects_error_output_in_memory(submission_notebook: dict):
    mutant = copy.deepcopy(submission_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell.setdefault("outputs", []).append(
                {
                    "output_type": "error",
                    "ename": "SyntheticError",
                    "evalue": "cố ý",
                    "traceback": ["SyntheticError: cố ý"],
                }
            )
            break
    violations = check_notebook_cells(mutant)
    assert any("output_type=error" in message for message in violations)


def test_gate_detects_missing_output_in_memory(submission_notebook: dict):
    mutant = copy.deepcopy(submission_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            break
    violations = check_notebook_cells(mutant)
    assert any("không có output" in message for message in violations)
