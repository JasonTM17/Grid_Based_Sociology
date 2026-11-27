"""Unified submission dependency closure, checksums, and unsafe-archive negative cases."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import nbformat as nbf
import pytest

from scripts.common.notebook_checks import notebook_issues
from scripts.deliverables import build_submission_packages as packaging
from scripts.deliverables.build_submission_packages import (
    ANALYSIS_NOTEBOOK,
    MANIFEST_REL,
    PACKAGE_FILES_CATALOG,
    PACKAGE_NAME,
    PAPI_REFERENCE_PDF,
    PREPROCESSING_NOTEBOOK,
    PREPROCESSING_SOURCE,
    RAW_REFERENCES,
    REPORT_NAME,
    ROOT,
    SLIDES_NAME,
    VISIBLE,
    build_package,
    check_member,
    instructions,
    package_files,
    replay_notebook,
    verify_package,
)


def test_replay_saves_cell_stderr_after_nbconvert_exits_successfully(tmp_path, monkeypatch):
    notebook = tmp_path / "demo.ipynb"
    log = tmp_path / "replay.log"
    cell = nbf.v4.new_code_cell("print('diagnostic')")
    nbf.write(nbf.v4.new_notebook(cells=[cell]), notebook)

    def execute(argv, **kwargs):
        replayed = nbf.read(notebook.with_suffix(".replay-input.ipynb"), as_version=4)
        replayed.cells[0].execution_count = 1
        replayed.cells[0].outputs = [nbf.v4.new_output("stream", name="stdout", text="guard")]
        replayed.cells[1].execution_count = 2
        replayed.cells[1].outputs = [
            nbf.v4.new_output("stream", name="stderr", text="original cell diagnostic\n"),
        ]
        nbf.write(replayed, notebook.with_suffix(".replayed.ipynb"))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="launcher message")

    monkeypatch.setattr(subprocess, "run", execute)
    with pytest.raises(ValueError, match="stderr"):
        replay_notebook(notebook, "print('guard')", log)
    diagnostic = log.read_text(encoding="utf-8")
    assert "original cell diagnostic" in diagnostic
    assert "stderr ở ô code gốc 1" in diagnostic


@pytest.fixture(scope="module")
def unified_package(tmp_path_factory):
    output = tmp_path_factory.mktemp("submissions")
    return build_package(ROOT, output, "final")


def test_unified_archive_includes_all_dependencies_and_excludes_private_material(unified_package):
    manifest = verify_package(unified_package)
    files = {row["path"] for row in manifest["files"]}

    assert sum(p.endswith(".xlsx") and p.startswith("data/raw/papi/") for p in files) == 14
    assert {
        REPORT_NAME,
        SLIDES_NAME,
        ANALYSIS_NOTEBOOK,
        PREPROCESSING_NOTEBOOK,
        "app.py",
        "HUONG_DAN.txt",
        "requirements.txt",
        "src/sting.py",
        "src/preprocessing.py",
        "scripts/common/midterm_clustering.py",
        "scripts/common/papi_pred_common.py",
        "scripts/common/papi_forecast.py",
        "scripts/common/fig_style.py",
        "scripts/common/notebook_checks.py",
        "scripts/deliverables/demo_smoke.py",
        "scripts/analysis/future_work.py",
        "scripts/analysis/stakeholder_summary.py",
        "scripts/analysis/dashboard_data.py",
        "results/stakeholder_province_summary_2024.csv",
        "results/stakeholder_summary.md",
        "results/KetQua_STING_PAPI.xlsx",
        "results/future_work.md",
        "results/future_work_backtest.csv",
        "results/future_work_rank.csv",
        "results/future_work_spatial.csv",
        "results/future_work_trajectory.csv",
        "results/figs/future_work_overview.png",
        "reports/external_data_expansion.md",
        "data/processed/papi_panel_v1_LOCKED.csv",
        "results/figs/stakeholder_quadrants_2024.png",
        "results/figs/00_synthetic_sting.png",
        "results/figs/papi_zscore_comparison.png",
        "results/figs/papi_forecast_grid.png",
        "results/figs/papi_forecast_values.png",
        "results/predict_all_years.csv",
        "results/papi_observed_grid_2024.csv",
        "models/predict_config.json",
        "models/sting_predict_model.pkl",
        "models/sup_ridge.joblib",
        "data/processed/papi_panel_63_2011_2024.csv",
        "data/processed/external_master_63_2011_2024.csv",
    } <= files

    visible = {REPORT_NAME, SLIDES_NAME, ANALYSIS_NOTEBOOK, PREPROCESSING_NOTEBOOK, "app.py", "DEMO.md", "HUONG_DAN.txt", "requirements.txt"}
    assert {p for p in files if "/" not in p} == visible
    assert not any(
        p.startswith((".git", ".codex", ".agentkit", "plans/", "study/", "reports/on-tap/", "data/raw/course/", "tests/", "assets/", "results/candidates_"))
        for p in files
    )
    assert {p for p in files if p.startswith("scripts/deliverables/")} == {
        "scripts/deliverables/demo_smoke.py"
    }
    assert "results/model_improvement_candidates.md" not in files
    assert "pytest.ini" not in files
    assert not any("__pycache__" in p or "probe" in p for p in files)

    bundled_references = {p for p in files if p.endswith((".pdf", ".zip", ".rar"))}
    assert bundled_references == {
        path for path in RAW_REFERENCES if path != PAPI_REFERENCE_PDF and (ROOT / path).is_file()
    }

    with zipfile.ZipFile(unified_package) as archive:
        for info in archive.infolist():
            assert info.date_time[0] >= 2020, f"Timestamp lỗi 1980: {info.filename}"
        guide = archive.read(f"{PACKAGE_NAME}/HUONG_DAN.txt").decode("utf-8")
        assert f"--execute {ANALYSIS_NOTEBOOK}" in guide
        assert f"--execute {PREPROCESSING_NOTEBOOK}" in guide
        assert "Kính gửi Thầy Lê Minh Tân" in guide
        assert "streamlit run app.py" in guide
        assert archive.read(f"{PACKAGE_NAME}/{REPORT_NAME}") == (ROOT / "reports" / REPORT_NAME).read_bytes()
        assert archive.read(f"{PACKAGE_NAME}/{SLIDES_NAME}") == (ROOT / "slides" / SLIDES_NAME).read_bytes()
        assert archive.read(f"{PACKAGE_NAME}/{ANALYSIS_NOTEBOOK}") == (ROOT / "notebooks" / ANALYSIS_NOTEBOOK).read_bytes()
        assert archive.read(f"{PACKAGE_NAME}/{PREPROCESSING_NOTEBOOK}") == (ROOT / PREPROCESSING_SOURCE).read_bytes()
        assert archive.read(f"{PACKAGE_NAME}/app.py") == (ROOT / "app.py").read_bytes()
        assert b"tabulate==" in archive.read(f"{PACKAGE_NAME}/requirements.txt")
        assert b"streamlit==" in archive.read(f"{PACKAGE_NAME}/requirements.txt")


def test_demo_command_runs_from_extracted_zip_and_detects_changed_evidence(unified_package, tmp_path):
    with zipfile.ZipFile(unified_package) as archive:
        archive.extractall(tmp_path)
    package = tmp_path / PACKAGE_NAME
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "MPLBACKEND"}}

    def run_demo():
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "scripts/deliverables/demo_smoke.py"],
            cwd=package, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    result = run_demo()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] checksum goi giai nen" in result.stdout
    assert "[PASS] Nhom15_STING_PAPI.pptx mo duoc 15 trang" in result.stdout
    evidence = package / "results/future_work_rank.csv"
    evidence.write_bytes(evidence.read_bytes() + b"\nchanged evidence\n")
    result = run_demo()
    assert result.returncode == 1, result.stdout + result.stderr
    assert "[FAIL] checksum goi giai nen" in result.stdout
    assert "results/future_work_rank.csv" in result.stdout


def test_failed_reverification_removes_previous_pass_receipt(tmp_path, monkeypatch):
    receipt = tmp_path / "verification.json"
    receipt.write_text('{"status": "PASS", "sha256": "old-archive"}', encoding="utf-8")

    def fail_replay(*args):
        raise RuntimeError("notebook replay failed")

    monkeypatch.setattr(packaging, "replay_package", fail_replay)
    monkeypatch.setattr(sys, "argv", ["build_submission_packages.py", "--verify", "--output-dir", str(tmp_path)])
    with pytest.raises(RuntimeError, match="notebook replay failed"):
        packaging.main()
    assert not receipt.exists()


def test_default_package_omits_reference_pdf_and_keeps_replication_zip(unified_package):
    replication_zip = "data/raw/mendeley/mendeley_replication.zip"
    assert (ROOT / PAPI_REFERENCE_PDF).is_file(), "Canonical reference PDF must remain in the repository"
    sources = package_files(ROOT)
    assert PAPI_REFERENCE_PDF not in sources
    assert replication_zip in sources
    assert PAPI_REFERENCE_PDF in package_files(ROOT, include_reference_pdf=True)
    with zipfile.ZipFile(unified_package) as archive:
        assert f"{PACKAGE_NAME}/{PAPI_REFERENCE_PDF}" not in archive.namelist()
        assert archive.read(f"{PACKAGE_NAME}/{replication_zip}") == (ROOT / replication_zip).read_bytes()
        guide = archive.read(f"{PACKAGE_NAME}/HUONG_DAN.txt").decode("utf-8")
        assert "Gói mặc định không kèm PDF báo cáo PAPI 2024" in guide
        assert "--include-reference-pdf" in guide
        assert f"blob/main/{PAPI_REFERENCE_PDF}" in guide


def test_reference_pdf_can_be_explicitly_included_without_replication_zip(tmp_path):
    present = PAPI_REFERENCE_PDF
    checkout = tmp_path / "checkout"
    for relative in (*PACKAGE_FILES_CATALOG, present):
        destination = checkout / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    path = build_package(checkout, tmp_path / "submissions", "final", include_reference_pdf=True)
    manifest = verify_package(path)
    sources = {row["path"] for row in manifest["files"]}
    assert sources.intersection(RAW_REFERENCES) == {present}
    with zipfile.ZipFile(path) as archive:
        guide = archive.read(f"{PACKAGE_NAME}/HUONG_DAN.txt").decode("utf-8")
        assert present in guide and "mendeley_replication.zip" not in guide
        assert "Gói mặc định không kèm PDF báo cáo PAPI 2024" not in guide


def test_delivered_zip_matches_sources_notebooks_and_loose_mirror():
    delivered_zip = ROOT / "submissions" / f"{PACKAGE_NAME}.zip"
    loose_dir = ROOT / "submissions" / PACKAGE_NAME
    assert delivered_zip.is_file(), "Thiếu submissions/Nhom15_STING_PAPI.zip"
    assert loose_dir.is_dir(), "Thiếu submissions/Nhom15_STING_PAPI/"

    for stale in ("01-giua-ky", "02-cuoi-ky", "03-tien-xu-ly-papi", "Nhom15_GiuaKy_STING_PAPI.zip", "Nhom15_CuoiKy_STING_PAPI.zip"):
        assert not (ROOT / "submissions" / stale).exists(), f"Còn tệp cũ {stale}"
    assert not (ROOT / "study").exists(), "Thư mục study/ chưa được xóa"

    manifest = verify_package(delivered_zip)
    with zipfile.ZipFile(delivered_zip) as archive:
        for src_rel, dest_name in VISIBLE.items():
            assert archive.read(f"{PACKAGE_NAME}/{dest_name}") == (ROOT / src_rel).read_bytes()
            assert (loose_dir / dest_name).read_bytes() == (ROOT / src_rel).read_bytes()
        for src_rel in PACKAGE_FILES_CATALOG:
            if src_rel == "requirements.txt":
                continue
            pkg_rel = VISIBLE.get(src_rel, src_rel)
            assert archive.read(f"{PACKAGE_NAME}/{pkg_rel}") == (ROOT / src_rel).read_bytes(), (
                f"{pkg_rel} trong ZIP lệch bản gốc {src_rel}"
            )
        for row in manifest["files"]:
            p = row["path"]
            assert (loose_dir / p).is_file(), f"Thiếu {p} trong loose mirror"
            assert (loose_dir / p).read_bytes() == archive.read(f"{PACKAGE_NAME}/{p}")
        references = tuple(
            relative for relative in RAW_REFERENCES if f"{PACKAGE_NAME}/{relative}" in archive.namelist()
        )
        guide = archive.read(f"{PACKAGE_NAME}/HUONG_DAN.txt").decode("utf-8")
        assert guide == instructions(source_references=references)


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


def test_removed_dependency_is_rejected(unified_package, tmp_path):
    broken = tmp_path / "missing.zip"
    _rewrite(
        unified_package,
        broken,
        lambda name, data: None if name.endswith("/scripts/supervised/predict_supervised.py") else data,
    )
    with pytest.raises(ValueError, match="manifest"):
        verify_package(broken)


def test_extra_file_is_rejected_even_when_listed_in_manifest(unified_package, tmp_path):
    extra_path = "results/working-notes.log"
    contents = b"temporary notes"
    broken = tmp_path / "extra.zip"
    with zipfile.ZipFile(unified_package) as original, zipfile.ZipFile(broken, "w") as archive:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename == f"{PACKAGE_NAME}/{MANIFEST_REL}":
                manifest = json.loads(data)
                manifest["files"].append(
                    {
                        "path": extra_path,
                        "bytes": len(contents),
                        "sha256": hashlib.sha256(contents).hexdigest(),
                        "role": "unrelated working file",
                    }
                )
                data = json.dumps(manifest).encode("utf-8")
            archive.writestr(entry, data)
        extra_info = zipfile.ZipInfo(f"{PACKAGE_NAME}/{extra_path}", date_time=(2026, 11, 21, 12, 0, 0))
        archive.writestr(extra_info, contents)
    with pytest.raises(ValueError, match="lệch danh mục"):
        verify_package(broken)


def test_corrupted_data_is_rejected(unified_package, tmp_path):
    broken = tmp_path / "corrupt.zip"
    _rewrite(
        unified_package,
        broken,
        lambda name, data: data + b"\nchanged" if name.endswith("/src/sting.py") else data,
    )
    with pytest.raises(ValueError, match="Checksum"):
        verify_package(broken)


def test_missing_input_is_reported_before_build(tmp_path):
    with pytest.raises(FileNotFoundError, match="dependency"):
        package_files(tmp_path)


def test_report_copy_keeps_the_graded_archive_filename(tmp_path):
    replacement = tmp_path / "formatted.docx"
    replacement.write_bytes((ROOT / "reports" / REPORT_NAME).read_bytes())
    with zipfile.ZipFile(replacement, "a") as document:
        document.comment = b"alternate formatted report"
    archive = build_package(ROOT, tmp_path / "output", "final", report_source=replacement)
    manifest = verify_package(archive)
    assert manifest["report_source"] == "formatted.docx"
    with zipfile.ZipFile(archive) as packaged:
        assert packaged.read(f"{PACKAGE_NAME}/{REPORT_NAME}") == replacement.read_bytes()
        assert not any(p.endswith("formatted.docx") for p in packaged.namelist())


def test_reject_report_with_empty_caption_catalogs(tmp_path):
    draft = tmp_path / "empty-catalogs.docx"
    _rewrite(
        ROOT / "reports" / REPORT_NAME,
        draft,
        lambda name, data: data.replace(b'w:val="TableofFigures"', b'w:val="Normal"')
        if name == "word/document.xml"
        else data,
    )
    with pytest.raises(ValueError, match="danh mục Word chưa đầy đủ"):
        build_package(ROOT, tmp_path / "output", "final", report_source=draft)


def test_preprocessing_rebuilds_master_and_audit_from_extracted_package(unified_package, tmp_path):
    with zipfile.ZipFile(unified_package) as archive:
        archive.extractall(tmp_path)
    package = tmp_path / PACKAGE_NAME
    master = package / "data/processed/external_master_63_2011_2024.csv"
    saved_master = master.rename(tmp_path / master.name)
    (package / "results/preprocessing_audit.csv").unlink()
    (package / "results/preprocessing_sensitivity.csv").unlink()
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "MPLBACKEND"}}
    for script in ("build_external_master", "preprocessing_audit", "preprocessing_sensitivity"):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", f"scripts/data/{script}.py"],
            cwd=package,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert result.returncode == 0, result.stderr

    assert master.read_text(encoding="utf-8-sig") == saved_master.read_text(encoding="utf-8-sig")
    assert (package / "results/preprocessing_audit.csv").read_text(encoding="utf-8-sig") == (
        ROOT / "results/preprocessing_audit.csv"
    ).read_text(encoding="utf-8-sig")


def test_standalone_folder_runs_panel_and_preprocessing_notebook(tmp_path):
    standalone = tmp_path / PACKAGE_NAME
    shutil.copytree(ROOT / "submissions" / PACKAGE_NAME, standalone)
    panel = standalone / "data/processed/papi_panel_63_2011_2024.csv"
    saved_panel = panel.read_text(encoding="utf-8")
    panel.unlink()
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "MPLBACKEND"}}
    for cmd in (
        ["scripts/data/build_panel.py"],
        ["scripts/data/check_data.py"],
        ["scripts/data/build_scale_metadata.py"],
        ["scripts/data/preprocessing_audit.py"],
        ["scripts/data/crosscheck_mendeley.py"],
    ):
        proc = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *cmd],
            cwd=standalone,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
    assert panel.read_text(encoding="utf-8") == saved_panel

    nb_copy = standalone / PREPROCESSING_NOTEBOOK
    nb = nbf.read(nb_copy, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    nbf.write(nb, nb_copy)
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--inplace",
            nb_copy.name,
            "--ExecutePreprocessor.timeout=180",
        ],
        cwd=standalone,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    executed = nbf.read(nb_copy, as_version=4)
    assert sum(c.cell_type == "code" for c in executed.cells) == 9
    assert (
        sum(
            1
            for c in executed.cells
            if c.cell_type == "code"
            for out in c.get("outputs", [])
            if isinstance(out.get("data"), dict) and "image/png" in out["data"]
        )
        == 3
    )
    assert notebook_issues(executed) == []
