"""Submission dependency closure, checksums, and unsafe-archive negative cases."""

from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from scripts.build_submission_packages import (
    PACKAGES, ROOT, build_package, check_member, package_files, verify_package,
)


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    output = tmp_path_factory.mktemp("submissions")
    return {kind: build_package(ROOT, output, kind) for kind in PACKAGES}


def test_archives_include_consumed_dependencies_and_exclude_private_material(packages):
    for kind, path in packages.items():
        manifest = verify_package(path, kind)
        files = {row["path"] for row in manifest["files"]}
        assert {
            "scripts/predict_supervised.py", "scripts/papi_pred_common.py", "scripts/fig_style.py",
            "models/sup_ridge.joblib", "models/sting_predict_model.pkl",
            "results/supervised_metrics.csv", "results/predict_all_years.csv",
            "data/processed/papi_panel_scale_metadata.csv",
            "data/processed/external_master_63_2011_2024.csv",
        } <= files
        assert sum(p.endswith(".xlsx") and p.startswith("data/raw/papi/") for p in files) == 14
        if kind == "final":
            assert {"slides/final.pptx", "scripts/build_slides.py"} <= files
        assert not any(p.startswith((".git", ".codex", ".agentkit", "plans/", "data/raw/course/")) for p in files)
        assert not any("__pycache__" in p or "probe" in p or p.endswith(".pdf") for p in files)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "root/../escape", "C:/escape", "root\\escape", "root//duplicate"])
def test_unsafe_member_paths_are_rejected(name):
    with pytest.raises(ValueError):
        check_member(name)


def _rewrite(source: Path, target: Path, transform):
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
        for entry in old.infolist():
            data = transform(entry.filename, old.read(entry))
            if data is not None:
                new.writestr(entry, data)


def test_removed_dependency_is_rejected(packages, tmp_path):
    broken = tmp_path / "missing.zip"
    _rewrite(packages["final"], broken,
             lambda name, data: None if name.endswith("/scripts/predict_supervised.py") else data)
    with pytest.raises(ValueError, match="manifest"):
        verify_package(broken, "final")


def test_corrupted_data_is_rejected(packages, tmp_path):
    broken = tmp_path / "corrupt.zip"
    _rewrite(packages["midterm"], broken,
             lambda name, data: data + b"\nchanged" if name.endswith("/models/predict_config.json") else data)
    with pytest.raises(ValueError, match="Checksum"):
        verify_package(broken, "midterm")


def test_missing_input_is_reported_before_build(tmp_path):
    with pytest.raises(FileNotFoundError, match="dependency"):
        package_files(tmp_path, "midterm")


def test_report_copy_keeps_the_graded_archive_filename(tmp_path):
    replacement = tmp_path / "formatted.docx"
    replacement.write_bytes((ROOT / "reports/final_report.docx").read_bytes())
    with zipfile.ZipFile(replacement, "a") as document:
        document.comment = b"alternate formatted report"
    archive = build_package(ROOT, tmp_path / "output", "final", report_source=replacement)
    manifest = verify_package(archive, "final")
    assert manifest["report_source"] == "formatted.docx"
    name = PACKAGES["final"][0]
    with zipfile.ZipFile(archive) as packaged:
        assert packaged.read(f"{name}/reports/final_report.docx") == replacement.read_bytes()
        assert not any(p.endswith("formatted.docx") for p in packaged.namelist())


def test_preprocessing_reproduces_from_extracted_package(packages, tmp_path):
    """A saved audit CSV must not conceal a missing audit-input dataset."""
    name, _ = PACKAGES["final"]
    with zipfile.ZipFile(packages["final"]) as archive:
        archive.extractall(tmp_path)
    package = tmp_path / name
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(package / "scripts/preprocessing_audit.py")],
        cwd=package, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, result.stderr
    # Git normalizes CSV to LF; pandas on Windows writes CRLF. Keep every
    # logical character/cell identical while accepting the platform newline.
    assert (package / "results/preprocessing_audit.csv").read_text(encoding="utf-8-sig") == (
        ROOT / "results/preprocessing_audit.csv"
    ).read_text(encoding="utf-8-sig")
