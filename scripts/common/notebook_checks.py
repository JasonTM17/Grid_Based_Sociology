"""Validate saved notebook execution, shared by demo and submission packaging."""

from __future__ import annotations

import re


def notebook_issues(notebook: dict) -> list[str]:
    """Require a complete sequential run with visible outputs and no errors."""
    cells = [c for c in notebook.get("cells", []) if c.get("cell_type") == "code"]
    if not cells:
        return ["không có ô code"]
    issues = []
    counts = [c.get("execution_count") for c in cells]
    if counts != list(range(1, len(cells) + 1)):
        issues.append("execution_count không liên tục từ 1: cần Restart & Run All")
    for number, cell in enumerate(cells, 1):
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        if re.search(r"(?:filterwarnings|simplefilter)\s*\(\s*['\"]ignore['\"]", source):
            issues.append(f"ô {number}: chứa lệnh bỏ qua cảnh báo")
        outputs = cell.get("outputs", [])
        if not outputs:
            issues.append(f"ô {number}: chưa có output")
        for output in outputs:
            if output.get("output_type") == "error":
                issues.append(f"ô {number}: output lỗi")
            if output.get("output_type") == "stream" and output.get("name") == "stderr":
                issues.append(f"ô {number}: stderr")
    return issues
