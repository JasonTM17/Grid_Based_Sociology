"""Gate artifact nộp bài: slide, notebook demo, và provenance PDF PAPI.

Đối chiếu demo tổng hợp và kết quả phân cụm PAPI với artifact. Các hàm
``check_*`` dùng chung cho artifact thật và bản sao đột biến trong RAM.

Chạy: python -m pytest tests/test_submission_artifacts.py -q
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from docx import Document
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]

SUBMISSION_PPTX = ROOT / "slides" / "submission.pptx"
SUBMISSION_NB = ROOT / "notebooks" / "Nhom15_GiuaKy_STING_PAPI.ipynb"
PAPI_LABELS = ROOT / "results" / "predict_all_years.csv"
PROVENANCE = ROOT / "data" / "raw" / "papi" / "PROVENANCE.md"
PAPI_PDF = ROOT / "data" / "raw" / "papi" / "PAPI_2024_REPORT_VIE_final.pdf"
EXPECTED_ARI_STR = "0.950"

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
        "00_synthetic_sting.png", "sting_first_real.png", "predict_2024.png",
        "supervised_regression.png", "course_confusion_matrix.png", "evolution.png",
        "map_2024.png", "external_pci_by_cluster.png", "external_health_density_2020.png",
        "external_grdp_by_cluster.png", "external_wdi_panel.png", "external_poverty_by_cluster.png",
    )
    report = Document(ROOT / "reports" / "final_report.docx")
    assert len(report.inline_shapes) == len(figures)
    for index, (shape, name) in enumerate(zip(report.inline_shapes, figures, strict=True), 1):
        relation = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        embedded = report.part.related_parts[relation].blob
        assert hashlib.sha256(embedded).hexdigest() == _sha256_file(ROOT / "results" / "figs" / name), (
            f"Hình {index} chưa cập nhật từ {name}; cần tạo lại báo cáo."
        )


def check_pptx_submission(prs: Presentation) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ): 1–10 slide, mọi slide có ghi chú."""
    violations: list[str] = []
    count = len(prs.slides)
    if count < 1:
        violations.append("submission.pptx không có slide nào")
    if count > 10:
        violations.append(f"submission.pptx có {count} slide (> 10)")
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
    """Ô code phải có output; không error/stderr; không filterwarnings ignore."""
    violations: list[str] = []
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        violations.append("notebook không có ô code")
        return violations

    for index, cell in enumerate(code_cells):
        source = _cell_source_text(cell)
        for pattern in _IGNORE_PATTERNS:
            if pattern.search(source):
                violations.append(
                    f"ô code #{index}: nguồn chứa lệnh bỏ qua cảnh báo ({pattern.pattern})"
                )

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
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        chunks.append(_cell_source_text(cell))
    return "\n".join(chunks)


def notebook_executed_text(nb: dict) -> str:
    """Ghép mọi stdout / text/plain từ output đã lưu."""
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
    """Output đã lưu không được chứa đường dẫn tuyệt đối máy chủ."""
    blob = notebook_executed_text(nb)
    violations: list[str] = []
    for pattern in _HOST_ABS_PATH_PATTERNS:
        if pattern.search(blob):
            violations.append(
                f"output notebook chứa đường dẫn host khớp {pattern.pattern!r}"
            )
    return violations


def provenance_pdf_sha256(md_text: str) -> str | None:
    match = _PDF_HASH_RE.search(md_text)
    return match.group(1).lower() if match else None


def check_papi_pdf_provenance(
    provenance_path: Path = PROVENANCE,
    pdf_path: Path = PAPI_PDF,
) -> list[str]:
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
        violations.append(
            "PROVENANCE.md không ghi SHA-256 của PAPI_2024_REPORT_VIE_final.pdf"
        )
        return violations

    actual = _sha256_file(pdf_path)
    if listed != actual:
        violations.append(
            f"SHA-256 trong PROVENANCE ({listed}) khác file thực ({actual})"
        )
    return violations


@pytest.fixture(scope="module")
def submission_notebook() -> dict:
    assert SUBMISSION_NB.is_file(), "thiếu notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb"
    return json.loads(SUBMISSION_NB.read_text(encoding="utf-8"))


def test_submission_pptx_exists_and_notes():
    assert SUBMISSION_PPTX.is_file(), "thiếu slides/submission.pptx"
    presentation = Presentation(str(SUBMISSION_PPTX))
    violations = check_pptx_submission(presentation)
    assert not violations, "\n".join(violations)
    titles_and_text = "\n".join(shape.text for slide in presentation.slides
                                for shape in slide.shapes if shape.has_text_frame)
    assert "Đọc cụm từ bảng đếm 3 × 3" in titles_and_text
    assert "Tài liệu tham khảo" not in titles_and_text
    assert "nhóm báo cáo trung thực" not in titles_and_text.lower()
    assert "PHÂN CỤM DỰA TRÊN LƯỚI STING" in titles_and_text
    assert "APPLICATION OF STING GRID-BASED CLUSTERING" in titles_and_text


def test_submission_notebook_cells(submission_notebook: dict):
    violations = check_notebook_cells(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_no_absolute_host_paths(submission_notebook: dict):
    violations = check_notebook_no_absolute_host_paths(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_course_rubric_sections(submission_notebook: dict):
    """Giữa kỳ cần tiền xử lý, demo Grid-based và đánh giá phân cụm."""
    md_text = notebook_markdown_text(submission_notebook)
    code_cells = [
        c for c in submission_notebook.get("cells", []) if c.get("cell_type") == "code"
    ]
    missing: list[str] = []
    if "Tiền xử lý dữ liệu" not in md_text:
        missing.append("thiếu mục Tiền xử lý dữ liệu")
    for section in ("Lý thuyết STING", "Cài đặt từ đầu", "Ứng dụng PAPI"):
        if section not in md_text:
            missing.append(f"thiếu mục {section}")
    if not any("preprocessing_audit.csv" in _cell_source_text(c) for c in code_cells):
        missing.append("không có ô đọc preprocessing_audit.csv")
    if not any("KMeans(" in _cell_source_text(c) and "DBSCAN(" in _cell_source_text(c)
               for c in code_cells):
        missing.append("thiếu ô so sánh K-means và DBSCAN")
    assert not missing, "\n".join(missing)
    assert all(phrase not in md_text for phrase in (
        "Thứ tự giảng dạy", "Test → Decide", "Cách chạy", "Cùng ví dụ với slide",
    ))


def test_submission_notebook_key_numbers(submission_notebook: dict):
    output = notebook_executed_text(submission_notebook)
    labels = pd.read_csv(PAPI_LABELS)
    holdout = labels.loc[labels.year == 2024, "pred_cluster"]
    noise = int(holdout.eq(-1).sum())
    assert "2 cụm, mỗi cụm 7 điểm. 1 điểm nhiễu." in output
    assert f"ARI = {EXPECTED_ARI_STR}" in output
    assert f"{len(labels)}/{len(labels)} nhãn khớp với kết quả đã lưu" in output
    assert f"{len(holdout) - noise} tỉnh được gán cụm, {noise} tỉnh nhận nhãn nhiễu." in output


def test_submission_checks_all_three_sensitivity_rows(submission_notebook: dict, tmp_path):
    source = next(_cell_source_text(c) for c in submission_notebook["cells"]
                  if "def _sensitivity_expectations(" in _cell_source_text(c))
    parser = next(node for node in ast.parse(source).body
                  if isinstance(node, ast.FunctionDef) and node.name == "_sensitivity_expectations")
    scope = {"min_counts": (3, 5, 8)}
    exec(compile(ast.Module(body=[parser], type_ignores=[]), "<notebook>", "exec"), scope)
    parse = scope[parser.name]
    path = tmp_path / "sensitivity.md"
    path.write_text("| min_count  | coverage 2024 | số cụm | ARI |\n"
                    "|---|---|---|---|\n| 3 | 82% | 3 | 0.852 |\n"
                    "| 5 | 79% | 3 | 1.000 |\n| 8 | 70% | 1 | 0.678 |\n", encoding="utf-8")
    assert parse(path) == {3: (0.82, 0.852), 5: (0.79, 1.0), 8: (0.70, 0.678)}
    path.write_text(path.read_text(encoding="utf-8").split("| 8 |")[0], encoding="utf-8")
    with pytest.raises(ValueError, match="3, 5, 8"):
        parse(path)


def test_papi_pdf_provenance_chain():
    violations = check_papi_pdf_provenance()
    assert not violations, "\n".join(violations)


def test_gate_detects_eleventh_slide_in_memory():
    """Đột biến RAM: thêm slide thứ 11 phải làm gate đỏ (không ghi file)."""
    presentation = Presentation(str(SUBMISSION_PPTX))
    layout_index = 6 if len(presentation.slide_layouts) > 6 else 0
    presentation.slides.add_slide(presentation.slide_layouts[layout_index])
    assert len(presentation.slides) == 11
    violations = check_pptx_submission(presentation)
    assert any("> 10" in message for message in violations)


def test_gate_detects_error_output_in_memory(submission_notebook: dict):
    """Đột biến RAM: chèn output error phải làm gate đỏ."""
    mutant = copy.deepcopy(submission_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        cell.setdefault("outputs", []).append(
            {
                "output_type": "error",
                "ename": "SyntheticError",
                "evalue": "cố ý",
                "traceback": ["SyntheticError: cố ý"],
            }
        )
        break
    else:
        pytest.fail("notebook không có ô code để đột biến")

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


def test_optional_final_slides_match_grid_method_and_presentation_scope():
    """Keep the method caveat and teacher-facing results in the oral deck."""
    deck = Presentation(ROOT / "slides/final.pptx")
    text = "\n".join(
        shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame
    )
    assert len(deck.slides) == 16
    assert all(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip()
               for slide in deck.slides)
    assert "STING rút gọn" in text
    assert "Cài đặt dùng ngưỡng số đếm" in text
    assert "STING gốc còn dùng phân phối và kiểm định thống kê" in text
    assert "23/37 cột đổi thang" not in text
    assert "28 unit test" not in text
    assert "Kết quả chính và hướng phát triển" in text
    assert "Cảm ơn thầy và các bạn đã lắng nghe" in text
    closing_text = "\n".join(
        shape.text for shape in deck.slides[-1].shapes if shape.has_text_frame
    ).strip()
    assert closing_text == "Cảm ơn thầy và các bạn đã lắng nghe"
    assert all(phrase not in text.lower() for phrase in (
        "báo cáo trung thực", "slide ghi điểm", "nói rõ trước khi được hỏi",
        "nghi thức phản biện", "bộ nộp cuối kỳ",
    ))
    notes = "\n".join(slide.notes_slide.notes_text_frame.text for slide in deck.slides)
    assert all(name in notes for name in ["final_report.docx", "Nhom15_CuoiKy_STING_PAPI.ipynb", "final.pptx"])
