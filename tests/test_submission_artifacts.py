"""Gate artifact nộp bài: slide, notebook demo, và provenance PDF PAPI.

Đọc số từ ``results/supervised_metrics.csv`` (không hard-code MAE Ridge). Các
hàm ``check_*`` tách riêng để test artifact thật và bản sao đột biến trong RAM —
không sửa file tracked.

Chạy: python -m pytest tests/test_submission_artifacts.py -q
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]

SUBMISSION_PPTX = ROOT / "slides" / "submission.pptx"
SUBMISSION_NB = ROOT / "notebooks" / "submission_demo.ipynb"
SUPERVISED_METRICS = ROOT / "results" / "supervised_metrics.csv"
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ridge_holdout_mae_from_csv(metrics_path: Path = SUPERVISED_METRICS) -> float:
    """MAE holdout Ridge đọc từ artifact CSV."""
    frame = pd.read_csv(metrics_path)
    rows = frame[(frame["task"] == "regression") & (frame["model"] == "ridge")]
    if len(rows) != 1:
        raise AssertionError(
            f"{metrics_path}: cần đúng 1 dòng ridge, có {len(rows)}"
        )
    return float(rows.iloc[0]["holdout_mae"])


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


def check_notebook_key_numbers(nb: dict, ridge_mae: float) -> list[str]:
    """Output đã chạy phải chứa ARI 0.950 và MAE holdout Ridge từ CSV."""
    violations: list[str] = []
    blob = notebook_executed_text(nb)

    if EXPECTED_ARI_STR not in blob:
        violations.append("output notebook thiếu ARI 0.950")

    mae_formats = {f"{ridge_mae:.4f}", f"{ridge_mae:.3f}", repr(ridge_mae)}
    if not any(token in blob for token in mae_formats):
        violations.append(
            f"output notebook thiếu MAE holdout Ridge ({ridge_mae}) từ supervised_metrics.csv"
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
    assert SUBMISSION_NB.is_file(), "thiếu notebooks/submission_demo.ipynb"
    return json.loads(SUBMISSION_NB.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ridge_holdout_mae() -> float:
    assert SUPERVISED_METRICS.is_file(), "thiếu results/supervised_metrics.csv"
    return ridge_holdout_mae_from_csv()


def test_submission_pptx_exists_and_notes():
    assert SUBMISSION_PPTX.is_file(), "thiếu slides/submission.pptx"
    presentation = Presentation(str(SUBMISSION_PPTX))
    violations = check_pptx_submission(presentation)
    assert not violations, "\n".join(violations)


def test_submission_notebook_cells(submission_notebook: dict):
    violations = check_notebook_cells(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_course_rubric_sections(submission_notebook: dict):
    """Notebook nộp bài phải hiện thứ tự Day 4 và baseline classifier học phần."""
    md_text = notebook_markdown_text(submission_notebook)
    code_cells = [
        c for c in submission_notebook.get("cells", []) if c.get("cell_type") == "code"
    ]
    missing: list[str] = []
    if "Tiền xử lý theo Day 4" not in md_text:
        missing.append("thiếu mục Tiền xử lý theo Day 4")
    if "Bộ phân loại trong môn học" not in md_text:
        missing.append("thiếu mục Bộ phân loại trong môn học")
    if not any("preprocessing_audit.csv" in _cell_source_text(c) for c in code_cells):
        missing.append("không có ô đọc preprocessing_audit.csv")
    if not any("course_supervised_baselines.csv" in _cell_source_text(c) for c in code_cells):
        missing.append("không có ô đọc course_supervised_baselines.csv")
    if not any("course_confusion_matrix.png" in _cell_source_text(c) for c in code_cells):
        missing.append("không có ô hiển thị course_confusion_matrix.png")
    assert not missing, "\n".join(missing)


def test_submission_notebook_key_numbers(
    submission_notebook: dict, ridge_holdout_mae: float
):
    violations = check_notebook_key_numbers(submission_notebook, ridge_holdout_mae)
    assert not violations, "\n".join(violations)


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
