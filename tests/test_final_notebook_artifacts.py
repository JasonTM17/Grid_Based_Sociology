"""Gate artifact notebook nộp cuối kỳ: ``notebooks/final_analysis.ipynb``.

Notebook đã execute phải có output ở mọi ô code, không lỗi, không stderr, không dòng
cảnh báo trong output và không lệnh bỏ qua cảnh báo. Các hàm ``check_*`` tách riêng
để test artifact thật và bản sao đột biến trong RAM — không sửa file tracked.

Chạy: python -m pytest tests/test_final_notebook_artifacts.py -q
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FINAL_NOTEBOOK = ROOT / "notebooks" / "final_analysis.ipynb"

_IGNORE_PATTERNS = (
    re.compile(r"""filterwarnings\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
    re.compile(r"""simplefilter\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
)
_WARNING_LINE_RE = re.compile(
    r"(?m)^.*\b(?:UserWarning|DeprecationWarning|FutureWarning|RuntimeWarning|"
    r"ResourceWarning|SyntaxWarning|PendingDeprecationWarning)\b.*$"
)


def _cell_source_text(cell: dict) -> str:
    raw = cell.get("source", "")
    if isinstance(raw, list):
        return "".join(raw)
    return str(raw)


def _output_text(output: dict) -> str:
    """Gộp text của một output (stream/list hoặc text/plain)."""
    if output.get("output_type") == "stream":
        text = output.get("text", "")
    else:
        data = output.get("data") or {}
        text = data.get("text/plain", "")
    if isinstance(text, list):
        return "".join(text)
    return str(text)


def notebook_output_text(nb: dict) -> str:
    """Ghép mọi stdout / text/plain đã lưu (bỏ qua output ảnh)."""
    chunks = [
        _output_text(output)
        for cell in nb.get("cells", [])
        if cell.get("cell_type") == "code"
        for output in cell.get("outputs") or []
    ]
    return "\n".join(chunk for chunk in chunks if chunk)


def check_executed_notebook(nb: dict) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ)."""
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

    warning_lines = _WARNING_LINE_RE.findall(notebook_output_text(nb))
    for line in warning_lines:
        violations.append(f"output chứa dòng cảnh báo: {line.strip()[:120]}")
    return violations


@pytest.fixture(scope="module")
def final_notebook() -> dict:
    assert FINAL_NOTEBOOK.is_file(), "thiếu notebooks/final_analysis.ipynb"
    return json.loads(FINAL_NOTEBOOK.read_text(encoding="utf-8"))


def test_final_notebook_executed(final_notebook: dict):
    violations = check_executed_notebook(final_notebook)
    assert not violations, "\n".join(violations)


def test_final_notebook_has_code_cells(final_notebook: dict):
    code_cells = [
        cell for cell in final_notebook.get("cells", []) if cell.get("cell_type") == "code"
    ]
    assert len(code_cells) >= 10, f"chỉ có {len(code_cells)} ô code"


def test_gate_detects_stderr_in_memory(final_notebook: dict):
    """Đột biến RAM: thêm stderr stream phải làm gate đỏ."""
    mutant = copy.deepcopy(final_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell.setdefault("outputs", []).append(
                {"output_type": "stream", "name": "stderr", "text": ["cố ý"]}
            )
            break
    else:
        pytest.fail("notebook không có ô code để đột biến")

    violations = check_executed_notebook(mutant)
    assert any("stderr" in message for message in violations)


def test_gate_detects_warning_text_in_memory(final_notebook: dict):
    """Đột biến RAM: dòng 'UserWarning' trong stdout phải làm gate đỏ."""
    mutant = copy.deepcopy(final_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell.setdefault("outputs", []).append(
                {
                    "output_type": "stream",
                    "name": "stdout",
                    "text": ["cố ý\nUserWarning: cảnh báo giả lập\n"],
                }
            )
            break
    else:
        pytest.fail("notebook không có ô code để đột biến")

    violations = check_executed_notebook(mutant)
    assert any("dòng cảnh báo" in message for message in violations)


def test_gate_detects_filterwarnings_in_memory(final_notebook: dict):
    mutant = copy.deepcopy(final_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["source"] = [
                'import warnings\nwarnings.filterwarnings("ignore")\n'
            ] + list(cell.get("source", []))
            cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": "ok\n"}]
            break
    else:
        pytest.fail("notebook không có ô code để đột biến")

    violations = check_executed_notebook(mutant)
    assert any("bỏ qua cảnh báo" in message for message in violations)


def test_gate_detects_missing_output_in_memory(final_notebook: dict):
    mutant = copy.deepcopy(final_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            break
    violations = check_executed_notebook(mutant)
    assert any("không có output" in message for message in violations)


def test_gate_detects_error_output_in_memory(final_notebook: dict):
    mutant = copy.deepcopy(final_notebook)
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

    violations = check_executed_notebook(mutant)
    assert any("output_type=error" in message for message in violations)
