"""Negative controls for the saved-notebook readiness gate."""

import copy
import json
import re
import runpy
import shutil
import subprocess
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


@pytest.mark.parametrize("failure", ["execution", "publication", "contention"])
def test_midterm_generator_preserves_published_notebook_on_failure(tmp_path, monkeypatch, failure):
    script = tmp_path / "scripts/notebooks/gen_submission_demo.py"
    script.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/notebooks/gen_submission_demo.py", script)
    destination = tmp_path / "notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb"
    destination.parent.mkdir()
    original = (ROOT / "notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb").read_bytes()
    destination.write_bytes(original)
    image = tmp_path / "results/figs/papi_zscore_comparison.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"previous-image")

    def execute(argv, **kwargs):
        if failure == "execution":
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="kernel error")
        Path(argv[-1]).write_bytes(original)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(subprocess, "run", execute)
    namespace = runpy.run_path(str(script))
    if failure == "publication":
        replace_file = Path.replace

        def fail_notebook_replace(source, target):
            if target == destination:
                raise PermissionError("notebook locked")
            return replace_file(source, target)

        monkeypatch.setattr(Path, "replace", fail_notebook_replace)
        with pytest.raises(PermissionError, match="notebook locked"):
            namespace["main"]()
    elif failure == "contention":
        with namespace["_publication_lock"](destination):
            with pytest.raises(RuntimeError, match="khóa cập nhật"):
                namespace["main"]()
    else:
        assert namespace["main"]() == 1
    assert destination.read_bytes() == original
    assert image.read_bytes() == b"previous-image"

    if failure == "contention":
        assert namespace["main"]() == 0
        assert image.read_bytes() == (ROOT / "results/figs/papi_zscore_comparison.png").read_bytes()


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
