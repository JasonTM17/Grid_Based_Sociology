"""Build dependency-complete submission ZIPs and replay them in isolation.

Run from the project: python scripts/build_submission_packages.py
Then: python scripts/build_submission_packages.py --verify
No training/configuration selection or network access is performed by this CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

if __package__:
    from .build_panel import NEW_FILES, OLD_FILES
    from .notebook_checks import notebook_issues
else:
    from build_panel import NEW_FILES, OLD_FILES
    from notebook_checks import notebook_issues

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submissions"
PACKAGES = {
    milestone: (name, f"{name}.ipynb")
    for milestone, name in (
        ("midterm", "Nhom15_GiuaKy_STING_PAPI"),
        ("final", "Nhom15_CuoiKy_STING_PAPI"),
    )
}
SCRIPTS = (
    "build_panel", "build_scale_metadata", "check_data", "crosscheck_mendeley", "first_real_cluster",
    "papi_pred_common", "fig_style", "predict_sweep", "predict_demo",
    "predict_supervised", "run_analysis", "preprocessing_audit",
    "course_supervised_baselines", "classifier_label_baselines",
    "external_validation", "poverty_validation", "cluster_profile",
    "supervised_depth", "preprocessing_sensitivity", "protocol_sensitivity",
    "notebook_checks",
)
MIDTERM_FIGURES = (
    "predict_2024", "00_synthetic_sting", "sting_first_real",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_files(root: Path, milestone: str) -> dict[str, str]:
    """An explicit dependency/role map; no recursive copy of the repository."""
    files = {}

    def add(relative: str, role: str) -> None:
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Thiếu dependency: {relative}")
        files[relative] = role

    for relative in ("LICENSE", "CITATION.cff", "requirements.txt", "pytest.ini", "src/sting.py"):
        add(relative, "environment / algorithm / attribution")
    for name in SCRIPTS:
        add(f"scripts/{name}.py", "analysis and canonical generators")
    for name in ("test_sting", "test_artifact_reproduction", "test_notebook_checks"):
        add(f"tests/{name}.py", "algorithm / frozen-label / execution regressions")
    for name in (*OLD_FILES.values(), *NEW_FILES.values(), "PROVENANCE.md"):
        add(f"data/raw/papi/{name}", "primary source / byte manifest")
    replication = "data/raw/mendeley/Replication_package/data"
    for name in ("province_crosswalk_63.csv", "centroids_63_naturalearth.csv",
                 "papi_panel_63_2011_2022.csv", "SHA256_PAPI_ORIGINALS.txt"):
        add(f"{replication}/{name}", "identity / crosscheck / map coordinates")
    for relative in ("data/raw/mendeley/PROVENANCE.md", "data/raw/boundaries/diaphantinh.geojson",
                     "data/raw/boundaries/PROVENANCE.md", "data/processed/external_provenance.md"):
        add(relative, "source attribution / map rebuild")
    for source in ("pci", "gso", "odmekong", "worldbank"):
        add(f"data/raw/{source}/PROVENANCE.md", "external source attribution; bulky originals kept in repository")
    for name in ("papi_panel_63_2011_2024", "papi_panel_scale_metadata", "external_master_63_2011_2024", "external_poverty_63",
                 "external_pci_63_full", "external_gso_population_63_full", "external_gso_grdp_63",
                 "external_odm_health_63", "external_worldbank_vnm"):
        add(f"data/processed/{name}.csv", "primary data or independent validation input")
    for name in ("predict_config.json", "sting_predict_model.pkl", "sting_predict_scaler.json",
                 "sup_ridge.joblib", "sup_rf.joblib", "sup_classifier.joblib", "README.md"):
        add(f"models/{name}", "frozen fitted models / feature contract")
    # Small scientific tables/notes support the published analyses, not web probes.
    for path in sorted((root / "results").iterdir()):
        if path.is_file() and path.suffix in (".csv", ".md", ".json"):
            add(path.relative_to(root).as_posix(), "published analysis tables / limitations")
    figures = sorted((root / "results/figs").glob("*.png")) if milestone == "final" else [
        root / f"results/figs/{name}.png" for name in MIDTERM_FIGURES
    ]
    for path in figures:
        add(path.relative_to(root).as_posix(), "notebook / report / slide figure")
    add("reports/panel_lock.md", "data provenance and verification")
    _, notebook = PACKAGES[milestone]
    add(f"notebooks/{notebook}", "graded executed notebook")
    if milestone == "midterm":
        for name in ("gen_submission_demo", "build_slides_10"):
            add(f"scripts/{name}.py", "midterm file generator")
        add("slides/submission.pptx", "graded deck, ten slides")
    else:
        for name in ("gen_final_analysis", "build_report", "report_style", "build_slides"):
            add(f"scripts/{name}.py", "final file generator")
        add("assets/report-cover.xml", "report cover template")
        add("reports/final_report.docx", "graded report, current seven-chapter format")
        for name in ("crosscheck_mendeley", "model_deep_dive"):
            add(f"reports/{name}.md", "report generator input")
        add("slides/final.pptx", "optional final oral-defense slides")
    return files


def instructions(milestone: str) -> str:
    _, notebook = PACKAGES[milestone]
    document = "slides/submission.pptx" if milestone == "midterm" else "reports/final_report.docx"
    optional = "\n- Slide vấn đáp tùy chọn  slides/final.pptx" if milestone == "final" else ""
    appendix = (
        "\nCác lệnh tái tạo toàn bộ đồ án ở phụ lục báo cáo chạy từ kho mã đầy đủ.\n"
        if milestone == "final" else ""
    )
    return f"""NHÓM 15 · HỌC MÁY · PHÂN CỤM STING TRÊN PAPI
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)

FILE NỘP
- {document}
- notebooks/{notebook}{optional}

CHẠY LẠI NOTEBOOK
Notebook đã lưu kết quả. Để chạy lại, giải nén toàn bộ ZIP, giữ cấu trúc
thư mục và mở terminal ở thư mục chứa requirements.txt. Dùng Python 3.14.

python -m pip install -r requirements.txt
python -m nbconvert --to notebook --execute --inplace notebooks/{notebook}

KIỂM TRA DỮ LIỆU VÀ THUẬT TOÁN
python scripts/check_data.py
python -m pytest tests/test_sting.py tests/test_artifact_reproduction.py tests/test_notebook_checks.py -q

Panel PAPI 2011–2024 có 882 dòng, 41 cột và 14 workbook gốc đi kèm.
Năm 2024 có 61/63 tỉnh đủ hai chỉ tiêu phân cụm. Có thể dựng lại panel
từ workbook bằng python scripts/build_panel.py.

Thông tin nguồn và giấy phép nằm trong data/raw/*/PROVENANCE.md và
data/processed/external_provenance.md. MANIFEST.json ghi danh mục và mã
SHA-256 các tệp. Địa chỉ kho mã nằm trong CITATION.cff.
{appendix}"""


def build_package(root: Path, output: Path, milestone: str, *, report_source: Path | None = None) -> Path:
    name, notebook = PACKAGES[milestone]
    files = package_files(root, milestone)
    issues = notebook_issues(json.loads((root / "notebooks" / notebook).read_text(encoding="utf-8")))
    if issues:
        raise ValueError(f"{notebook}: " + "; ".join(issues))
    payload = {p: (root / p).read_bytes() for p in files}
    if milestone == "final" and report_source is not None:
        # Preserve the graded filename when Word locks the report being viewed.
        payload["reports/final_report.docx"] = report_source.read_bytes()
    payload["HUONG_DAN.txt"] = instructions(milestone).encode("utf-8")
    files["HUONG_DAN.txt"] = "submitted files and notebook run instructions"
    manifest = {
        "schema_version": 1, "milestone": milestone, "root": name,
        "files": [{"path": p, "bytes": len(payload[p]), "sha256": sha256(payload[p]),
                   "role": files[p]} for p in sorted(payload)],
    }
    if milestone == "final" and report_source is not None:
        manifest["report_source"] = report_source.name
    payload["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path, data in sorted(payload.items()):
            info = zipfile.ZipInfo(f"{name}/{path}")  # fixed timestamp, reproducible bytes
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, data)
    return archive


def check_member(name: str) -> None:
    parts = PurePosixPath(name).parts
    if (not parts or PurePosixPath(name).is_absolute() or ".." in parts
            or "\\" in name or ":" in name or name != PurePosixPath(name).as_posix()):
        raise ValueError(f"Đường dẫn ZIP không an toàn: {name}")


def verify_package(archive: Path, milestone: str) -> dict:
    name, notebook = PACKAGES[milestone]
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(set(p.casefold() for p in names)):
            raise ValueError("ZIP có đường dẫn trùng")
        for info in zipped.infolist():
            check_member(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Không chấp nhận symlink trong ZIP")
        manifest = json.loads(zipped.read(f"{name}/MANIFEST.json"))
        if manifest.get("milestone") != milestone or manifest.get("root") != name:
            raise ValueError("Manifest không khớp mốc nộp")
        rows = manifest["files"]
        expected = {f"{name}/{r['path']}" for r in rows} | {f"{name}/MANIFEST.json"}
        if len(expected) != len(rows) + 1 or set(names) != expected:
            raise ValueError("ZIP thiếu/thừa file so với manifest")
        required = {"src/sting.py", f"notebooks/{notebook}", "requirements.txt",
                    "data/processed/papi_panel_63_2011_2024.csv",
                    "data/processed/external_master_63_2011_2024.csv", "models/predict_config.json"}
        required.add("slides/submission.pptx" if milestone == "midterm" else "reports/final_report.docx")
        if not {f"{name}/{p}" for p in required} <= expected:
            raise ValueError("ZIP thiếu sản phẩm hoặc dependency bắt buộc")
        for row in rows:
            data = zipped.read(f"{name}/{row['path']}")
            if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
                raise ValueError(f"Checksum sai: {row['path']}")
        issues = notebook_issues(json.loads(zipped.read(f"{name}/notebooks/{notebook}")))
        if issues:
            raise ValueError("Notebook trong ZIP chưa hoàn tất: " + "; ".join(issues))
        return manifest


def replay_package(archive: Path, milestone: str, output: Path) -> dict:
    """Run extracted code, blocking reads of the source repo and Downloads."""
    import nbformat

    verify_package(archive, milestone)  # validates every member before extraction
    scratch = ROOT / "plans" / "submission-package-replay"
    scratch.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="kiểm tra gói ", dir=scratch)
    temporary_path = Path(temporary.name).resolve()
    if not temporary_path.is_relative_to(scratch.resolve()):
        raise ValueError("Scratch ngoài vùng cho phép")
    try:
        name, notebook = PACKAGES[milestone]
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(temporary_path)
        package = temporary_path / name
        path = package / "notebooks" / notebook
        nb = nbformat.read(path, as_version=4)
        guard = f'''import os, sys
from pathlib import Path
_allowed = Path({str(package)!r}).resolve()
_blocked = [Path(p).resolve() for p in {list(map(str, [ROOT, Path.home() / 'Downloads']))!r}]
def _isolation_guard(event, args):
    if event not in ("open", "os.listdir", "os.scandir") or not args:
        return
    if not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    try:
        target = Path(os.fsdecode(args[0])).resolve()
    except (OSError, ValueError):
        return
    if target.is_relative_to(_allowed):
        return
    if any(target.is_relative_to(p) for p in _blocked):
        raise PermissionError("Isolated replay attempted to read original workspace/Downloads")
sys.addaudithook(_isolation_guard)
print("Isolation guard enabled")
'''
        nb.cells.insert(0, nbformat.v4.new_code_cell(guard))
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.execution_count = None
                cell.outputs = []
        replay_input = path.with_name("isolated-replay-input.ipynb")
        nbformat.write(nb, replay_input)
        env = {k: v for k, v in os.environ.items() if k not in {
            "PYTHONPATH", "PYTHONSTARTUP", "STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH",
        }}
        proc = subprocess.run([
            sys.executable, "-X", "utf8", "-m", "nbconvert", "--to", "notebook", "--execute",
            str(replay_input), "--output", "isolated-replayed.ipynb",
            "--ExecutePreprocessor.timeout=300",
        ], cwd=package, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
        (output / f"replay-{milestone}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode:
            raise RuntimeError(f"Replay {milestone} thất bại; xem replay-{milestone}.log")
        executed = nbformat.read(path.with_name("isolated-replayed.ipynb"), as_version=4)
        issues = notebook_issues(executed)
        if issues:
            raise ValueError(f"Replay {milestone}: " + "; ".join(issues))
        return {"milestone": milestone, "status": "PASS", "sha256": sha256(archive.read_bytes()),
                "code_cells": sum(c.cell_type == "code" for c in executed.cells),
                "isolation_guard": True, "python": sys.version.split()[0],
                "launcher_messages": bool(proc.stderr.strip())}
    finally:
        # temporary_path was resolved and verified inside the task scratch root.
        temporary.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--report-source", type=Path, help="final DOCX copy to package under reports/final_report.docx")
    parser.add_argument("--verify", action="store_true", help="verify existing ZIPs and replay both notebooks")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    if args.verify:
        receipts = []
        for milestone, (name, _) in PACKAGES.items():
            receipt = replay_package(args.output_dir / f"{name}.zip", milestone, args.output_dir)
            receipts.append(receipt)
            print(f"{milestone}: PASS isolated replay ({receipt['code_cells']} code cells including guard)")
        (args.output_dir / "verification.json").write_text(
            json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        # A successful older replay is no longer evidence for newly built ZIPs.
        (args.output_dir / "verification.json").unlink(missing_ok=True)
        lines = []
        for milestone in PACKAGES:
            path = build_package(ROOT, args.output_dir, milestone, report_source=args.report_source)
            manifest = verify_package(path, milestone)
            lines.append(f"{sha256(path.read_bytes())}  {path.name}\n")
            print(f"{path.name}: {len(manifest['files'])} files, {path.stat().st_size / 1e6:.2f} MB")
        (args.output_dir / "SHA256SUMS.txt").write_text("".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
