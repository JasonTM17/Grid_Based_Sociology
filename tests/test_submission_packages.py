"""Submission dependency closure, checksums, and unsafe-archive negative cases."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from scripts.deliverables.build_submission_packages import (
    MIDTERM_FILES, PACKAGES, PREPROCESSING_NOTEBOOK, RAW_REFERENCES, ROOT, SUPPORT, archive_path,
    build_package, check_member, package_files, verify_package,
)


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    output = tmp_path_factory.mktemp("submissions")
    return {kind: build_package(ROOT, output, kind) for kind in PACKAGES}


def test_archives_include_consumed_dependencies_and_exclude_private_material(packages):
    preprocessing = "Nhom15_TienXuLy_PAPI.ipynb"
    for kind, path in packages.items():
        manifest = verify_package(path, kind)
        files = {row["path"] for row in manifest["files"]}
        name, notebook = PACKAGES[kind]
        prefix = f"{SUPPORT}/"
        support_files = {p.removeprefix(prefix) for p in files}
        assert sum(p.endswith(".xlsx") and p.startswith(f"{prefix}data/raw/papi/") for p in files) == 14
        assert preprocessing in files
        assert {
            "scripts/data/build_panel.py", "scripts/common/papi_pred_common.py",
            "data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv",
            "data/processed/papi_panel_63_2011_2024.csv", "models/predict_config.json",
        } <= support_files
        visible = {f"{name}.pptx", notebook, preprocessing, "HUONG_DAN.txt"}
        audit = "results/papi_observed_grid_2024.csv"
        assert audit in support_files
        if kind == "final":
            assert {
                "scripts/supervised/predict_supervised.py", "scripts/common/papi_pred_common.py", "scripts/common/fig_style.py",
                "models/sup_ridge.joblib", "models/sting_predict_model.pkl",
                "results/supervised_metrics.csv", "results/predict_all_years.csv",
                "data/processed/papi_panel_scale_metadata.csv",
                "data/processed/external_master_63_2011_2024.csv",
                "data/processed/external_gso_waste_63.csv", "scripts/data/build_external_master.py",
                "scripts/common/papi_forecast.py", "results/papi_forecast_provinces_2024.csv",
                "results/figs/papi_forecast_grid.png", "results/figs/papi_forecast_values.png",
            } <= support_files
            visible.add(f"{name}.docx")
            assert not any(p.startswith(("tests/", "scripts/deliverables/", "assets/", "results/candidates_"))
                           for p in support_files)
            assert not {"scripts/common/notebook_checks.py", "results/model_improvement_candidates.md",
                        "results/figs/00_synthetic_sting.png", "results/figs/supervised_regression.png"} & support_files
            assert "pytest.ini" not in support_files
        else:
            assert {f"{prefix}{p}" for p in (
                "src/sting.py", "scripts/common/papi_pred_common.py", "scripts/common/fig_style.py",
                "scripts/common/midterm_clustering.py", "results/preprocessing_audit.csv",
                "results/figs/predict_2024.png",
                "data/processed/papi_panel_63_2011_2024.csv", "requirements.txt",
            )} <= files
            assert not {"results/predict_all_years.csv",
                        "results/metrics.csv", "results/predict_summary.md",
                        "scripts/common/papi_forecast.py"} & support_files
            assert not any(p.endswith((".pkl", ".joblib")) or p.startswith(
                (f"{prefix}tests/", f"{prefix}reports/", f"{prefix}scripts/supervised/")
            ) for p in files)
        assert {p for p in files if "/" not in p} == visible
        assert not any(p.startswith((".git", ".codex", ".agentkit", "plans/", "study/", "reports/on-tap/", "data/raw/course/")) for p in support_files)
        assert not {
            "reports/course_requirements.md", "reports/report_format_notes.md",
            "reports/on-tap/qa_course_concepts.md", "reports/on-tap/presentation_script.md",
        } & support_files
        assert not any("__pycache__" in p or "probe" in p for p in files)
        bundled_references = {p for p in support_files if p.endswith((".pdf", ".zip", ".rar"))}
        assert bundled_references == {path for path in RAW_REFERENCES if (ROOT / path).is_file()}
        with zipfile.ZipFile(path) as archive:
            guide = archive.read(f"{name}/HUONG_DAN.txt").decode("utf-8")
            assert f"--execute {notebook}" in guide
            assert f"--execute {preprocessing}" in guide
            assert "Kính gửi Thầy Lê Minh Tân" in guide
            assert archive.read(f"{name}/{notebook}") == (ROOT / "notebooks" / notebook).read_bytes()
            assert archive.read(f"{name}/{preprocessing}") == (ROOT / "notebooks" / preprocessing).read_bytes()
            assert b"openpyxl==" in archive.read(f"{name}/{prefix}requirements.txt")
            assert archive.read(f"{name}/{prefix}{audit}") == (ROOT / audit).read_bytes()
            for relative in bundled_references:
                assert f"{prefix}{relative}" in guide
                assert archive.read(f"{name}/{prefix}{relative}") == (ROOT / relative).read_bytes()
            if kind == "midterm":
                top = {p.removeprefix(f"{name}/").split("/")[0] for p in archive.namelist()}
                assert top == visible | {SUPPORT}
                assert archive.read(f"{name}/{name}.pptx") == (ROOT / "slides/submission.pptx").read_bytes()
            else:
                assert archive.read(f"{name}/{name}.docx") == (ROOT / "reports/final_report.docx").read_bytes()
                assert archive.read(f"{name}/{name}.pptx") == (ROOT / "slides/final.pptx").read_bytes()
                assert b"tabulate==" in archive.read(f"{name}/{prefix}requirements.txt")
                assert "python scripts/data/build_external_master.py" in guide
        assert all(phrase not in guide for phrase in ("luyện trình bày", "deadline", "nộp lên LMS"))


def test_package_keeps_available_papi_pdf_when_replication_zip_is_absent(tmp_path):
    present = "data/raw/papi/PAPI_2024_REPORT_VIE_final.pdf"
    checkout = tmp_path / "checkout"
    for relative in (*MIDTERM_FILES, present):
        destination = checkout / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    path = build_package(checkout, tmp_path / "submissions", "midterm")
    manifest = verify_package(path, "midterm")
    sources = {row["path"] for row in manifest["files"]}
    present_path = f"{SUPPORT}/{present}"
    assert sources.intersection(f"{SUPPORT}/{ref}" for ref in RAW_REFERENCES) == {present_path}
    name, _ = PACKAGES["midterm"]
    with zipfile.ZipFile(path) as archive:
        assert archive.read(f"{name}/{present_path}") == (ROOT / present).read_bytes()
        guide = archive.read(f"{name}/HUONG_DAN.txt").decode("utf-8")
        assert present_path in guide and "mendeley_replication.zip" not in guide


@pytest.mark.parametrize("milestone", PACKAGES)
def test_delivered_zip_matches_current_sting_source_and_notebooks(milestone):
    name, notebook = PACKAGES[milestone]
    sources = ("src/sting.py", f"notebooks/{notebook}", f"notebooks/{PREPROCESSING_NOTEBOOK}")
    with zipfile.ZipFile(ROOT / "submissions" / f"{name}.zip") as archive:
        for relative in sources:
            member = f"{name}/{archive_path(relative, milestone)}"
            assert archive.read(member) == (ROOT / relative).read_bytes(), member


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
             lambda name, data: None if name.endswith("/scripts/supervised/predict_supervised.py") else data)
    with pytest.raises(ValueError, match="manifest"):
        verify_package(broken, "final")


def test_extra_file_is_rejected_even_when_listed_in_manifest(packages, tmp_path):
    name, _ = PACKAGES["final"]
    extra_path = f"{SUPPORT}/results/working-notes.log"
    contents = b"temporary notes"
    broken = tmp_path / "extra.zip"
    with zipfile.ZipFile(packages["final"]) as original, zipfile.ZipFile(broken, "w") as archive:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename == f"{name}/{SUPPORT}/MANIFEST.json":
                manifest = json.loads(data)
                manifest["files"].append({
                    "path": extra_path, "bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest(),
                    "role": "unrelated working file",
                })
                data = json.dumps(manifest).encode("utf-8")
            archive.writestr(entry, data)
        archive.writestr(f"{name}/{extra_path}", contents)
    with pytest.raises(ValueError, match="lệch danh mục"):
        verify_package(broken, "final")


def test_corrupted_data_is_rejected(packages, tmp_path):
    broken = tmp_path / "corrupt.zip"
    _rewrite(packages["midterm"], broken,
             lambda name, data: data + b"\nchanged" if name.endswith("/src/sting.py") else data)
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
        assert packaged.read(f"{name}/{name}.docx") == replacement.read_bytes()
        assert not any(p.endswith("formatted.docx") for p in packaged.namelist())


def test_reject_report_with_empty_caption_catalogs(tmp_path):
    draft = tmp_path / "empty-catalogs.docx"
    _rewrite(ROOT / "reports/final_report.docx", draft,
             lambda name, data: data.replace(b'w:val="TableofFigures"', b'w:val="Normal"')
             if name == "word/document.xml" else data)
    with pytest.raises(ValueError, match="danh mục Word chưa đầy đủ"):
        build_package(ROOT, tmp_path / "output", "final", report_source=draft)


def test_preprocessing_rebuilds_master_and_audit_from_extracted_package(packages, tmp_path):
    """Recreate the audit input from the bundled components before running the audit."""
    name, _ = PACKAGES["final"]
    with zipfile.ZipFile(packages["final"]) as archive:
        archive.extractall(tmp_path)
    package = tmp_path / name / SUPPORT
    master = package / "data/processed/external_master_63_2011_2024.csv"
    saved_master = master.rename(tmp_path / master.name)
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    for script in ("build_external_master", "preprocessing_audit"):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", f"scripts/data/{script}.py"],
            cwd=package, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert result.returncode == 0, result.stderr


    assert master.read_text(encoding="utf-8-sig") == saved_master.read_text(encoding="utf-8-sig")
    assert (package / "results/preprocessing_audit.csv").read_text(encoding="utf-8-sig") == (
        ROOT / "results/preprocessing_audit.csv"
    ).read_text(encoding="utf-8-sig")


def test_loose_submission_folders_match_canonical_deliverables():
    """Loose copies in submissions/01-giua-ky and 02-cuoi-ky must match canonical files."""
    expected_pairs = [
        ("slides/submission.pptx", "submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.pptx"),
        ("notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb", "submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.ipynb"),
        ("reports/final_report.docx", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.docx"),
        ("notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.ipynb"),
        ("slides/final.pptx", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.pptx"),
    ]
    for src_rel, dst_rel in expected_pairs:
        src, dst = ROOT / src_rel, ROOT / dst_rel
        assert dst.is_file(), f"Thiếu bản rời {dst_rel}"
        assert src.read_bytes() == dst.read_bytes(), f"{dst_rel} lệch với {src_rel}"
