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

from scripts.common.notebook_checks import notebook_issues
from scripts.deliverables.build_submission_packages import (
    MANIFEST_REL, MIDTERM_FILES, PACKAGES, PREPROCESSING_NOTEBOOK, RAW_REFERENCES, ROOT, archive_path,
    build_package, check_member, instructions, package_files, preprocessing_instructions, verify_package,
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
        support_files = files
        assert sum(p.endswith(".xlsx") and p.startswith("data/raw/papi/") for p in files) == 14
        assert preprocessing in files
        assert {
            "src/preprocessing.py", "scripts/data/build_panel.py",
            "scripts/data/build_scale_metadata.py",
            "scripts/data/preprocessing_audit.py", "scripts/data/crosscheck_mendeley.py",
            "scripts/common/papi_pred_common.py", "scripts/common/fig_style.py",
            "data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv",
            "data/raw/mendeley/Replication_package/data/papi_panel_63_2011_2022.csv",
            "data/raw/mendeley/Replication_package/data/SHA256_PAPI_ORIGINALS.txt",
            "data/processed/papi_panel_63_2011_2024.csv",
            "data/processed/papi_panel_scale_metadata.csv",
            "data/processed/external_master_63_2011_2024.csv",
            "models/predict_config.json", "models/sting_predict_scaler.json",
            "results/preprocessing_audit.csv", "results/preprocessing_audit.md",
            "results/preprocessing_sensitivity.csv", "results/preprocessing_sensitivity.md",
        } <= support_files
        with zipfile.ZipFile(path) as archive:
            nb = json.loads(archive.read(f"{name}/{notebook}").decode("utf-8"))
            for info in archive.infolist():
                assert info.date_time[0] >= 2020, f"Timestamp lỗi 1980: {info.filename}"
        nb_src = "\n".join("".join(c["source"]) for c in nb["cells"])
        assert "run_preprocessing_pipeline" in nb_src
        visible = {f"{name}.pptx", notebook, preprocessing, "HUONG_DAN.txt", "requirements.txt"}
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
            assert {
                "src/sting.py", "scripts/common/papi_pred_common.py", "scripts/common/fig_style.py",
                "scripts/common/midterm_clustering.py",
                "scripts/analysis/predict_sweep.py", "scripts/analysis/first_real_cluster.py",
                "scripts/figures/fig_grid_levels_and_elbow.py",
                "results/preprocessing_audit.csv", "results/predict_config_search.csv", "results/per_year.csv",
                "results/figs/00_synthetic_sting.png", "results/figs/papi_zscore_comparison.png",
                "results/figs/sting_first_real.png", "results/figs/sting_grid_levels.png",
                "results/figs/kmeans_elbow.png", "results/figs/predict_2024.png",
                "data/processed/papi_panel_63_2011_2024.csv", "requirements.txt",
            } <= files
            assert not {"results/predict_all_years.csv",
                        "results/metrics.csv", "results/predict_summary.md",
                        "scripts/common/papi_forecast.py"} & support_files
            assert not any(p.endswith((".pkl", ".joblib")) or p.startswith(
                ("tests/", "reports/", "scripts/supervised/")
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
            assert archive.read(f"{name}/src/sting.py") == (ROOT / "src/sting.py").read_bytes()
            assert archive.read(f"{name}/src/preprocessing.py") == (ROOT / "src/preprocessing.py").read_bytes()
            assert b"openpyxl==" in archive.read(f"{name}/requirements.txt")
            assert archive.read(f"{name}/{audit}") == (ROOT / audit).read_bytes()
            for relative in bundled_references:
                assert relative in guide
                assert archive.read(f"{name}/{relative}") == (ROOT / relative).read_bytes()
            if kind == "midterm":
                top = {p.removeprefix(f"{name}/").split("/")[0] for p in archive.namelist()}
                assert top == visible | {"data", "models", "results", "scripts", "src"}
                assert archive.read(f"{name}/{name}.pptx") == (ROOT / "slides/submission.pptx").read_bytes()
            else:
                top = {p.removeprefix(f"{name}/").split("/")[0] for p in archive.namelist()}
                assert top == visible | {"data", "models", "reports", "results", "scripts", "src"}
                assert archive.read(f"{name}/{name}.docx") == (ROOT / "reports/final_report.docx").read_bytes()
                assert archive.read(f"{name}/{name}.pptx") == (ROOT / "slides/final.pptx").read_bytes()
                assert b"tabulate==" in archive.read(f"{name}/requirements.txt")
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
    assert sources.intersection(RAW_REFERENCES) == {present}
    name, _ = PACKAGES["midterm"]
    with zipfile.ZipFile(path) as archive:
        assert archive.read(f"{name}/{present}") == (ROOT / present).read_bytes()
        guide = archive.read(f"{name}/HUONG_DAN.txt").decode("utf-8")
        assert present in guide and "mendeley_replication.zip" not in guide


@pytest.mark.parametrize("milestone", PACKAGES)
def test_delivered_zip_matches_current_sting_source_and_notebooks(milestone):
    name, notebook = PACKAGES[milestone]
    sources = ("src/sting.py", "src/preprocessing.py", f"notebooks/{notebook}", f"notebooks/{PREPROCESSING_NOTEBOOK}")
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
    extra_path = "results/working-notes.log"
    contents = b"temporary notes"
    broken = tmp_path / "extra.zip"
    with zipfile.ZipFile(packages["final"]) as original, zipfile.ZipFile(broken, "w") as archive:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename == f"{name}/{MANIFEST_REL}":
                manifest = json.loads(data)
                manifest["files"].append({
                    "path": extra_path, "bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest(),
                    "role": "unrelated working file",
                })
                data = json.dumps(manifest).encode("utf-8")
            archive.writestr(entry, data)
        extra_info = zipfile.ZipInfo(f"{name}/{extra_path}", date_time=(2026, 11, 21, 12, 0, 0))
        archive.writestr(extra_info, contents)
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
    package = tmp_path / name
    master = package / "data/processed/external_master_63_2011_2024.csv"
    saved_master = master.rename(tmp_path / master.name)
    (package / "results/preprocessing_audit.csv").unlink()
    (package / "results/preprocessing_sensitivity.csv").unlink()
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "MPLBACKEND"}}
    for script in ("build_external_master", "preprocessing_audit", "preprocessing_sensitivity"):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", f"scripts/data/{script}.py"],
            cwd=package, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert result.returncode == 0, result.stderr


    assert master.read_text(encoding="utf-8-sig") == saved_master.read_text(encoding="utf-8-sig")
    assert (package / "results/preprocessing_audit.csv").read_text(encoding="utf-8-sig") == (
        ROOT / "results/preprocessing_audit.csv"
    ).read_text(encoding="utf-8-sig")
    assert (package / "results/preprocessing_sensitivity.csv").read_text(encoding="utf-8-sig") == (
        ROOT / "results/preprocessing_sensitivity.csv"
    ).read_text(encoding="utf-8-sig")


def test_loose_submission_folders_match_canonical_deliverables():
    """Loose copies in submissions/01-giua-ky, 02-cuoi-ky and 03-tien-xu-ly-papi must match canonical files."""
    expected_pairs = [
        ("slides/submission.pptx", "submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.pptx"),
        ("notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb", "submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.ipynb"),
        ("notebooks/Nhom15_TienXuLy_PAPI.ipynb", "submissions/01-giua-ky/Nhom15_TienXuLy_PAPI.ipynb"),
        ("src/sting.py", "submissions/01-giua-ky/src/sting.py"),
        ("src/preprocessing.py", "submissions/01-giua-ky/src/preprocessing.py"),
        ("reports/final_report.docx", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.docx"),
        ("notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.ipynb"),
        ("slides/final.pptx", "submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.pptx"),
        ("notebooks/Nhom15_TienXuLy_PAPI.ipynb", "submissions/02-cuoi-ky/Nhom15_TienXuLy_PAPI.ipynb"),
        ("src/sting.py", "submissions/02-cuoi-ky/src/sting.py"),
        ("src/preprocessing.py", "submissions/02-cuoi-ky/src/preprocessing.py"),
        ("notebooks/Nhom15_TienXuLy_PAPI.ipynb", "submissions/03-tien-xu-ly-papi/Nhom15_TienXuLy_PAPI.ipynb"),
        ("src/sting.py", "submissions/03-tien-xu-ly-papi/src/sting.py"),
        ("src/preprocessing.py", "submissions/03-tien-xu-ly-papi/src/preprocessing.py"),
        ("scripts/data/build_panel.py", "submissions/03-tien-xu-ly-papi/scripts/data/build_panel.py"),
        ("scripts/data/check_data.py", "submissions/03-tien-xu-ly-papi/scripts/data/check_data.py"),
        ("scripts/data/build_scale_metadata.py", "submissions/03-tien-xu-ly-papi/scripts/data/build_scale_metadata.py"),
        ("scripts/data/preprocessing_audit.py", "submissions/03-tien-xu-ly-papi/scripts/data/preprocessing_audit.py"),
        ("scripts/data/crosscheck_mendeley.py", "submissions/03-tien-xu-ly-papi/scripts/data/crosscheck_mendeley.py"),
        ("scripts/common/papi_pred_common.py", "submissions/03-tien-xu-ly-papi/scripts/common/papi_pred_common.py"),
        ("scripts/common/fig_style.py", "submissions/03-tien-xu-ly-papi/scripts/common/fig_style.py"),
        ("data/processed/papi_panel_63_2011_2024.csv", "submissions/03-tien-xu-ly-papi/data/processed/papi_panel_63_2011_2024.csv"),
        ("data/processed/papi_panel_scale_metadata.csv", "submissions/03-tien-xu-ly-papi/data/processed/papi_panel_scale_metadata.csv"),
        ("data/processed/external_master_63_2011_2024.csv", "submissions/03-tien-xu-ly-papi/data/processed/external_master_63_2011_2024.csv"),
        ("models/predict_config.json", "submissions/03-tien-xu-ly-papi/models/predict_config.json"),
        ("models/sting_predict_scaler.json", "submissions/03-tien-xu-ly-papi/models/sting_predict_scaler.json"),
        ("results/preprocessing_audit.csv", "submissions/03-tien-xu-ly-papi/results/preprocessing_audit.csv"),
        ("results/preprocessing_audit.md", "submissions/03-tien-xu-ly-papi/results/preprocessing_audit.md"),
        ("results/preprocessing_sensitivity.csv", "submissions/03-tien-xu-ly-papi/results/preprocessing_sensitivity.csv"),
        ("results/preprocessing_sensitivity.md", "submissions/03-tien-xu-ly-papi/results/preprocessing_sensitivity.md"),
    ]
    for src_rel, dst_rel in expected_pairs:
        src, dst = ROOT / src_rel, ROOT / dst_rel
        assert dst.is_file(), f"Thiếu bản rời {dst_rel}"
        assert src.read_bytes() == dst.read_bytes(), f"{dst_rel} lệch với {src_rel}"
    for stale_rel in (
        "submissions/03-tien-xu-ly-papi/scripts/build_panel.py",
        "submissions/03-tien-xu-ly-papi/scripts/papi_pred_common.py",
        "submissions/01-giua-ky/sting.py",
        "submissions/01-giua-ky/preprocessing.py",
        "submissions/02-cuoi-ky/sting.py",
        "submissions/02-cuoi-ky/preprocessing.py",
        "submissions/03-tien-xu-ly-papi/sting.py",
        "submissions/03-tien-xu-ly-papi/preprocessing.py",
    ):
        assert not (ROOT / stale_rel).exists(), f"Còn tệp cũ hỏng {stale_rel}"
    present_refs = tuple(r for r in RAW_REFERENCES if (ROOT / r).is_file())
    for folder, kind in (("01-giua-ky", "midterm"), ("02-cuoi-ky", "final")):
        guide_file = ROOT / "submissions" / folder / "HUONG_DAN.txt"
        assert guide_file.is_file(), f"Thiếu submissions/{folder}/HUONG_DAN.txt"
        assert guide_file.read_text(encoding="utf-8") == instructions(kind, source_references=present_refs)
    preproc_guide = ROOT / "submissions/03-tien-xu-ly-papi/HUONG_DAN.txt"
    assert preproc_guide.is_file(), "Thiếu submissions/03-tien-xu-ly-papi/HUONG_DAN.txt"
    guide_text = preproc_guide.read_text(encoding="utf-8")
    assert guide_text == preprocessing_instructions()
    assert PREPROCESSING_NOTEBOOK in guide_text
    assert "python scripts/data/check_data.py" in guide_text
    assert "python scripts/data/build_panel.py" in guide_text
    assert "python scripts/data/preprocessing_audit.py" in guide_text
    assert "python scripts/data/crosscheck_mendeley.py" in guide_text


def test_standalone_preprocessing_folder_runs_panel_and_check_data(tmp_path):
    """Copying submissions/03-tien-xu-ly-papi directly must run scripts and notebook cleanly."""
    import nbformat

    src_dir = ROOT / "submissions/03-tien-xu-ly-papi"
    standalone = tmp_path / "03-tien-xu-ly-papi"
    shutil.copytree(src_dir, standalone)
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
            cwd=standalone, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
    assert panel.read_text(encoding="utf-8") == saved_panel

    nb_copy = standalone / PREPROCESSING_NOTEBOOK
    nb = nbformat.read(nb_copy, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    nbformat.write(nb, nb_copy)
    proc = subprocess.run(
        [
            sys.executable, "-X", "utf8", "-m", "nbconvert", "--to", "notebook",
            "--execute", "--inplace", nb_copy.name, "--ExecutePreprocessor.timeout=180",
        ],
        cwd=standalone, env=env, capture_output=True, text=True, encoding="utf-8", timeout=240,
    )
    assert proc.returncode == 0, proc.stderr
    executed = nbformat.read(nb_copy, as_version=4)
    assert sum(c.cell_type == "code" for c in executed.cells) == 9
    assert sum(
        1 for c in executed.cells if c.cell_type == "code"
        for out in c.get("outputs", [])
        if isinstance(out.get("data"), dict) and "image/png" in out["data"]
    ) == 3
    assert not any(
        out.get("output_type") == "error"
        for c in executed.cells if c.cell_type == "code"
        for out in c.get("outputs", [])
    )
    assert notebook_issues(executed) == []
