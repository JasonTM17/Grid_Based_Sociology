"""Negative controls for the saved-notebook readiness gate."""

import copy
import json
import re
from pathlib import Path

import pytest

from scripts.common.notebook_checks import notebook_issues

ROOT = Path(__file__).resolve().parents[1]
_HOST_PATH_RE = re.compile(r"(?:D:\\|C:\\Users|c:/msys64)", re.IGNORECASE)


def executed_notebook():
    return {"cells": [{
        "cell_type": "code", "source": "print('ok')", "execution_count": 1,
        "outputs": [{"output_type": "stream", "name": "stdout", "text": "ok\n"}],
    }]}


def test_complete_run_passes():
    assert not notebook_issues(executed_notebook())


@pytest.mark.parametrize("count", [None, 0, 7])
def test_outputs_without_a_complete_run_are_rejected(count):
    notebook = executed_notebook()
    notebook["cells"][0]["execution_count"] = count

    assert all(o["output_type"] != "error" for o in notebook["cells"][0]["outputs"])
    assert notebook_issues(notebook)


def test_out_of_order_run_is_rejected():
    notebook = executed_notebook()
    notebook["cells"].append(copy.deepcopy(notebook["cells"][0]))
    assert notebook_issues(notebook)


@pytest.mark.parametrize("outputs", [
    [],
    [{"output_type": "error", "ename": "ValueError"}],
    [{"output_type": "stream", "name": "stderr", "text": "warning"}],
])
def test_missing_or_failed_outputs_are_rejected(outputs):
    notebook = executed_notebook()
    notebook["cells"][0]["outputs"] = outputs
    assert notebook_issues(notebook)


def test_empty_notebook_is_rejected():
    assert notebook_issues({"cells": []})


def test_warning_suppression_is_rejected():
    notebook = executed_notebook()
    notebook["cells"][0]["source"] = 'warnings.filterwarnings("ignore")'
    assert notebook_issues(notebook)


def test_repo_and_study_notebooks_are_clean_and_portable():
    """All tracked notebooks in notebooks/ and study/ must be cleanly executed without host paths."""
    paths = [
        p
        for folder in ("notebooks", "study")
        for p in sorted((ROOT / folder).rglob("*.ipynb"))
        if ".ipynb_checkpoints" not in p.parts
    ]
    assert paths
    for path in paths:
        raw = path.read_text(encoding="utf-8")
        assert not _HOST_PATH_RE.search(raw), f"{path.relative_to(ROOT)} chứa đường dẫn host"
        issues = notebook_issues(json.loads(raw))
        assert not issues, f"{path.relative_to(ROOT)}: {issues}"
