"""Build dependency-complete submission ZIPs and replay them in isolation.

Run from the project: python scripts/deliverables/build_submission_packages.py
Then: python scripts/deliverables/build_submission_packages.py --verify
No training/configuration selection or network access is performed by this CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.common.notebook_checks import notebook_issues  # noqa: E402
from scripts.data.build_panel import NEW_FILES, OLD_FILES  # noqa: E402

OUTPUT = ROOT / "submissions"
PACKAGES = {
    milestone: (name, f"{name}.ipynb")
    for milestone, name in (
        ("midterm", "Nhom15_GiuaKy_STING_PAPI"),
        ("final", "Nhom15_CuoiKy_STING_PAPI"),
    )
}
FINAL_SCRIPTS = (
    "data/build_scale_metadata", "data/build_external_master",
    "data/check_data", "data/crosscheck_mendeley", "data/preprocessing_audit",
    "analysis/first_real_cluster", "common/fig_style", "common/papi_forecast",
    "analysis/predict_sweep", "analysis/predict_demo", "analysis/run_analysis",
    "analysis/external_validation", "analysis/poverty_validation", "analysis/cluster_profile",
    "analysis/protocol_sensitivity", "supervised/predict_supervised",
    "supervised/course_supervised_baselines", "supervised/supervised_depth",
    "figures/fig_grid_levels_and_elbow", "figures/forecast_papi_grid",
)
FINAL_RESULTS = (
    "analysis_summary.md", "cluster_labels.csv", "cluster_profile.csv", "cluster_profile.md",
    "course_supervised_baselines.csv", "course_supervised_baselines.md", "course_supervised_sensitivity.csv",
    "external_master_summary.md", "external_validation.csv", "external_validation.md",
    "metrics.csv", "papi_forecast_2024.json", "papi_forecast_cv.csv", "papi_forecast_provinces_2024.csv",
    "papi_observed_grid_2024.csv",
    "per_year.csv", "poverty_validation.csv", "poverty_validation.md",
    "predict_all_years.csv", "predict_config_search.csv", "predict_summary.md",
    "preprocessing_audit.csv", "preprocessing_audit.md", "protocol_sensitivity.csv",
    "protocol_sensitivity.md", "robustness.csv", "supervised_depth.csv",
    "supervised_depth.md", "supervised_metrics.csv", "supervised_summary.md",
)
FINAL_FIGURES = (
    "course_confusion_matrix", "deep_cluster_profile", "evolution", "external_grdp_by_cluster",
    "external_health_density_2020", "external_pci_by_cluster", "external_poverty_by_cluster",
    "external_wdi_panel", "kmeans_elbow", "map_2020", "map_2024", "papi_forecast_grid", "papi_forecast_values",
    "predict_2024",
    "protocol_sensitivity_grid", "sting_grid_levels", "supervised_importance",
    "supervised_learning_curve",
)
SUPPORT = "tai_lieu_kem"
MIDTERM_NAME, MIDTERM_NOTEBOOK = PACKAGES["midterm"]
FINAL_NAME, FINAL_NOTEBOOK = PACKAGES["final"]
PREPROCESSING_NOTEBOOK = "Nhom15_TienXuLy_PAPI.ipynb"
PREPROCESSING_SOURCE = f"notebooks/{PREPROCESSING_NOTEBOOK}"
MIDTERM_VISIBLE = {
    "slides/submission.pptx": f"{MIDTERM_NAME}.pptx",
    f"notebooks/{MIDTERM_NOTEBOOK}": MIDTERM_NOTEBOOK,
}
FINAL_VISIBLE = {
    "reports/final_report.docx": f"{FINAL_NAME}.docx",
    f"notebooks/{FINAL_NOTEBOOK}": FINAL_NOTEBOOK,
    "slides/final.pptx": f"{FINAL_NAME}.pptx",
}
VISIBLE = {"midterm": MIDTERM_VISIBLE, "final": FINAL_VISIBLE}
PAPI_PREPROCESSING_FILES = {
    PREPROCESSING_SOURCE: "Notebook tiền xử lý PAPI đã lưu kết quả",
    "scripts/data/build_panel.py": "Đọc Excel gốc và xây bảng PAPI",
    "scripts/common/papi_pred_common.py": "Đọc bảng, cấu hình chỉ tiêu và lưới STING",
    "models/predict_config.json": "Cấu hình chỉ tiêu PAPI dùng trong phân cụm",
    "data/processed/papi_panel_63_2011_2024.csv": "Bảng PAPI đã tiền xử lý",
    "data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv": "Bảng tra mã và tên tỉnh",
    "data/raw/mendeley/PROVENANCE.md": "Nguồn và giấy phép bảng tra mã tỉnh",
    "data/raw/papi/PROVENANCE.md": "Nguồn và mã kiểm tra dữ liệu PAPI",
    **{f"data/raw/papi/{name}": "Bảng tính PAPI gốc" for name in (*OLD_FILES.values(), *NEW_FILES.values())},
}
MIDTERM_FILES = {
    "slides/submission.pptx": "Bản trình chiếu",
    f"notebooks/{MIDTERM_NOTEBOOK}": "Notebook đã lưu kết quả",
    "src/sting.py": "Mã nguồn thuật toán STING",
    "scripts/common/fig_style.py": "Định dạng biểu đồ trong notebook",
    "scripts/common/midterm_clustering.py": "Tham số, mã phân cụm và biểu đồ dùng trong notebook",
    "LICENSE": "Giấy phép mã nguồn",
    "requirements.txt": "Thư viện để chạy notebook",
    **PAPI_PREPROCESSING_FILES,
    "results/preprocessing_audit.csv": "Kết quả kiểm tra tiền xử lý",
    "results/papi_observed_grid_2024.csv": "Lý do gán cụm trên lưới tham chiếu của 63 tỉnh, thành phố",
    "results/figs/predict_2024.png": "Điểm PAPI đã quan sát năm 2024 trên lưới đến 2023",
}
FINAL_FILES = {
    "reports/final_report.docx": "Báo cáo cuối kỳ",
    f"notebooks/{FINAL_NOTEBOOK}": "Notebook đã lưu kết quả",
    "slides/final.pptx": "Slide vấn đáp",
    "src/sting.py": "Mã nguồn thuật toán STING",
    "LICENSE": "Giấy phép mã nguồn",
    "CITATION.cff": "Thông tin trích dẫn dự án",
    "requirements.txt": "Thư viện để tái lập",
    **PAPI_PREPROCESSING_FILES,
    **{f"scripts/{name}.py": "Mã tái lập dữ liệu và thí nghiệm" for name in FINAL_SCRIPTS},
    **{f"data/raw/mendeley/Replication_package/data/{name}": "Đối chiếu PAPI và tọa độ bản đồ"
       for name in ("centroids_63_naturalearth.csv",
                    "papi_panel_63_2011_2022.csv", "SHA256_PAPI_ORIGINALS.txt")},
    "data/raw/boundaries/diaphantinh.geojson": "Ranh giới hành chính dùng trong bản đồ",
    **{f"data/raw/{source}/PROVENANCE.md": "Nguồn và giấy phép dữ liệu"
       for source in ("boundaries", "pci", "gso", "odmekong", "worldbank")},
    "data/processed/external_provenance.md": "Nguồn và quy trình xử lý dữ liệu đối chiếu",
    **{f"data/processed/{name}.csv": "Dữ liệu đã xử lý để chạy lại"
       for name in ("papi_panel_scale_metadata",
                    "external_master_63_2011_2024", "external_poverty_63", "external_pci_63_full",
                    "external_gso_population_63_full", "external_gso_grdp_63", "external_gso_waste_63",
                    "external_odm_health_63", "external_worldbank_vnm")},
    **{f"models/{name}": "Mô hình, cấu hình và hướng dẫn sử dụng"
       for name in ("sting_predict_model.pkl", "sting_predict_scaler.json",
                    "sup_ridge.joblib", "sup_rf.joblib", "sup_classifier.joblib", "README.md")},
    **{f"results/{name}": "Bảng đối chiếu kết quả thực nghiệm" for name in FINAL_RESULTS},
    **{f"results/figs/{name}.png": "Hình dùng trong notebook hoặc tài liệu đối chiếu" for name in FINAL_FIGURES},
    "reports/panel_lock.md": "Phiên bản và mã kiểm tra bảng PAPI",
    "reports/crosscheck_mendeley.md": "Kết quả đối chiếu PAPI với Mendeley",
    "reports/model_deep_dive.md": "Minh chứng các phép phân tích bổ sung trong báo cáo",
}
PACKAGE_FILES = {"midterm": MIDTERM_FILES, "final": FINAL_FILES}
RAW_REFERENCES = {
    "data/raw/papi/PAPI_2024_REPORT_VIE_final.pdf": "Báo cáo PAPI 2024 (bản tiếng Việt)",
    "data/raw/mendeley/mendeley_replication.zip":
        "Dữ liệu và mã đối chiếu của Le và cộng sự (2026), Mendeley Data, DOI 10.17632/wbk42j9wc8.1, CC BY 4.0",
}
MIDTERM_REQUIREMENTS = (
    "numpy", "pandas", "scikit-learn", "matplotlib", "scipy", "joblib",
    "jupyter", "nbformat", "nbconvert", "ipykernel", "openpyxl",
)
FINAL_REQUIREMENTS = (*MIDTERM_REQUIREMENTS, "tabulate")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive_path(relative: str, milestone: str) -> str:
    if relative == PREPROCESSING_SOURCE:
        return PREPROCESSING_NOTEBOOK
    return VISIBLE[milestone].get(relative, f"{SUPPORT}/{relative}")


def package_files(root: Path, milestone: str) -> dict[str, str]:
    """Check the source files from the fixed catalog for each submission."""
    files = PACKAGE_FILES[milestone].copy()
    files.update({
        relative: description for relative, description in RAW_REFERENCES.items()
        if (root / relative).is_file()
    })
    for relative in files:
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Thiếu dependency: {relative}")
    return files


def instructions(milestone: str, *, source_references: tuple[str, ...] = ()) -> str:
    _, notebook = PACKAGES[milestone]
    raw_references = ""
    if source_references:
        raw_references = "\nTài liệu nguồn kèm theo\n\n" + "".join(
            f"- {SUPPORT}/{relative} — {RAW_REFERENCES[relative]}.\n"
            for relative in source_references
        )
    preprocessing_item = (
        f"- {PREPROCESSING_NOTEBOOK} — Notebook đọc 14 tệp Excel gốc, làm sạch,\n"
        "  ghép mã tỉnh, đối chiếu bảng PAPI và chuẩn hóa hai chỉ tiêu.\n"
    )
    run_preprocessing = (
        f"python -m nbconvert --to notebook --execute {PREPROCESSING_NOTEBOOK} "
        f"--output {Path(PREPROCESSING_NOTEBOOK).stem}_chay_lai"
    )
    if milestone == "midterm":
        return f"""BÁO CÁO GIỮA KỲ MÔN HỌC MÁY
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới (Grid-based clustering)
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)

Kính gửi Thầy Lê Minh Tân,

Nhóm 15 xin gửi bài báo cáo giữa kỳ về thuật toán phân cụm dựa trên lưới STING
và phân tích mô tả 869 quan sát đủ hai chỉ tiêu PAPI giai đoạn 2011–2024.
Bài nộp gồm ba tệp chính.

- {MIDTERM_NAME}.pptx — Bản trình chiếu.
- {notebook} — Notebook Jupyter có mã phân cụm, đối chiếu z-score và phần
  gán điểm PAPI đã quan sát năm 2024 lên lưới STING dựng từ 2011–2023.
{preprocessing_item}
Thư mục {SUPPORT}/ chứa mã tiền xử lý, mã STING, bảng PAPI đã xử lý
(882 quan sát tỉnh–năm, 41 cột), 14 tệp Excel gốc và thông tin nguồn dữ liệu.
{raw_references}
Xem và chạy lại notebook

Thầy có thể mở hai notebook để xem kết quả đã lưu. Để chạy lại, vui lòng giải
nén toàn bộ gói và mở các notebook cạnh thư mục {SUPPORT}/. Trong Jupyter,
chọn Restart Kernel rồi Run All Cells cho từng notebook.

Nếu chạy bằng dòng lệnh, mở terminal tại thư mục vừa giải nén. Môi trường
đã kiểm tra dùng Python 3.14.

python -m pip install -r {SUPPORT}/requirements.txt
{run_preprocessing}
python -m nbconvert --to notebook --execute {notebook} --output {MIDTERM_NAME}_chay_lai

Trân trọng,
Nhóm 15
"""
    return f"""BÁO CÁO CUỐI KỲ MÔN HỌC MÁY
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới (Grid-based clustering)
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)

Kính gửi Thầy Lê Minh Tân,

Nhóm 15 xin gửi bài báo cáo cuối kỳ về phương pháp STING và ứng dụng
trên dữ liệu PAPI giai đoạn 2011–2024. Gói bài nộp gồm các tệp sau.

- {FINAL_NAME}.docx — Báo cáo nghiên cứu.
- {notebook} — Notebook Jupyter có mã và kết quả thực nghiệm đã lưu.
- {FINAL_NAME}.pptx — Slide dùng khi vấn đáp.
{preprocessing_item}
Trong báo cáo, Chương 3 trình bày dữ liệu và tiền xử lý. Chương 4 trình bày
cấu hình STING và quy trình đánh giá. Chương 5 trình bày kết quả phân cụm,
dự báo hai chỉ tiêu từ dữ liệu đến 2023 và đối chiếu trên cùng lưới với
điểm quan sát năm 2024.

Thư mục {SUPPORT}/ chứa mã nguồn STING, bảng PAPI đã tiền xử lý
(882 quan sát tỉnh–năm, 41 cột), 14 bảng tính gốc, mô hình và kết quả
đối chiếu. Hồ sơ nguồn dữ liệu nằm trong data/raw/ và mã SHA-256 của
từng tệp nằm trong MANIFEST.json của thư mục này.
{raw_references}
Xem và chạy lại notebook

Thầy có thể mở hai notebook để xem kết quả đã lưu. Để chạy lại, giải nén toàn
bộ gói và mở các notebook cạnh thư mục {SUPPORT}/. Trong Jupyter, chọn
Restart Kernel rồi Run All Cells cho từng notebook.

Nếu dùng dòng lệnh, mở terminal tại thư mục vừa giải nén. Môi trường
đã kiểm tra dùng Python 3.14.

python -m pip install -r {SUPPORT}/requirements.txt
{run_preprocessing}
python -m nbconvert --to notebook --execute {notebook} --output {FINAL_NAME}_chay_lai

Dựng lại panel từ 14 bảng tính PAPI gốc

Sau khi cài thư viện, chạy các lệnh sau từ thư mục vừa giải nén.

cd {SUPPORT}
python scripts/data/build_panel.py
python scripts/data/build_scale_metadata.py
python scripts/data/check_data.py

Các lệnh trên tạo bảng PAPI 882 × 41 và bảng mô tả thang đo. Cũng tại
thư mục {SUPPORT}/, thầy có thể dựng bảng ghép 882 × 59 và chạy kiểm tra
tiền xử lý, đối chiếu dữ liệu bằng các lệnh sau.

python scripts/data/build_external_master.py
python scripts/data/preprocessing_audit.py
python scripts/data/crosscheck_mendeley.py
python scripts/figures/forecast_papi_grid.py

Phụ lục A trình bày thêm các lệnh tái lập từ kho mã đầy đủ của dự án.

Trân trọng,
Nhóm 15
"""


def verify_report_fields(data: bytes) -> None:
    """Reject a draft DOCX whose Word table-of-contents fields are still empty."""
    word = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as docx:
        document = ElementTree.fromstring(docx.read("word/document.xml"))
    entries = {"TOC1": [], "TableofFigures": []}
    for paragraph in document.findall(".//w:p", word):
        style = paragraph.find("w:pPr/w:pStyle", word)
        name = style.get(f"{{{word['w']}}}val") if style is not None else None
        if name in entries:
            content = "".join(t.text or "" for t in paragraph.findall(".//w:t", word))
            entries[name].append(content)
    chapters = {m.group(1) for line in entries["TOC1"] if (m := re.match(r"CHƯƠNG (\d+)\.", line))}
    if chapters != set("1234567") or any(
        sum(line.startswith(label + " ") for line in entries["TableofFigures"]) != 12
        for label in ("Hình", "Bảng")
    ):
        raise ValueError("Mục lục hoặc danh mục Word chưa đầy đủ; chạy update_report_fields.py bằng Word.")


def build_package(root: Path, output: Path, milestone: str, *, report_source: Path | None = None) -> Path:
    name, notebook = PACKAGES[milestone]
    sources = package_files(root, milestone)
    files = {archive_path(p, milestone): role for p, role in sources.items()}
    payload = {archive_path(p, milestone): (root / p).read_bytes() for p in sources}
    for filename in (notebook, PREPROCESSING_NOTEBOOK):
        issues = notebook_issues(json.loads(payload[filename]))
        if issues:
            raise ValueError(f"{filename}: " + "; ".join(issues))
    requirements = archive_path("requirements.txt", milestone)
    pins = {line.split("==", 1)[0]: line for line in payload[requirements].decode("utf-8").splitlines()
            if "==" in line}
    needed = MIDTERM_REQUIREMENTS if milestone == "midterm" else FINAL_REQUIREMENTS
    payload[requirements] = ("\n".join(pins[p] for p in needed) + "\n").encode("utf-8")
    if milestone == "final":
        report = FINAL_VISIBLE["reports/final_report.docx"]
        if report_source is not None:

            payload[report] = report_source.read_bytes()
        verify_report_fields(payload[report])
    payload["HUONG_DAN.txt"] = instructions(
        milestone, source_references=tuple(relative for relative in RAW_REFERENCES if relative in sources),
    ).encode("utf-8")
    files["HUONG_DAN.txt"] = "Hướng dẫn mở và chạy lại bài nộp"
    manifest = {
        "schema_version": 1, "milestone": milestone, "root": name,
        "files": [{"path": p, "bytes": len(payload[p]), "sha256": sha256(payload[p]),
                   "role": files[p]} for p in sorted(payload)],
    }
    if milestone == "final" and report_source is not None:
        manifest["report_source"] = report_source.name
    payload[archive_path("MANIFEST.json", milestone)] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path, data in sorted(payload.items()):
            info = zipfile.ZipInfo(f"{name}/{path}")
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
    manifest_path = f"{name}/{archive_path('MANIFEST.json', milestone)}"
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(set(p.casefold() for p in names)):
            raise ValueError("ZIP có đường dẫn trùng")
        for info in zipped.infolist():
            check_member(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Không chấp nhận symlink trong ZIP")
        manifest = json.loads(zipped.read(manifest_path))
        if manifest.get("milestone") != milestone or manifest.get("root") != name:
            raise ValueError("Manifest không khớp mốc nộp")
        rows = manifest["files"]
        expected = {f"{name}/{r['path']}" for r in rows} | {manifest_path}
        if len(expected) != len(rows) + 1 or set(names) != expected:
            raise ValueError("ZIP thiếu/thừa file so với manifest")
        delivery = {f"{name}/{archive_path(p, milestone)}" for p in PACKAGE_FILES[milestone]}
        delivery.update((manifest_path, f"{name}/HUONG_DAN.txt"))
        raw_references = {f"{name}/{archive_path(p, milestone)}" for p in RAW_REFERENCES}
        if not delivery <= expected <= (delivery | raw_references):
            raise ValueError("ZIP lệch danh mục tệp nộp")
        if milestone == "final":
            verify_report_fields(zipped.read(f"{name}/{FINAL_VISIBLE['reports/final_report.docx']}"))
        for row in rows:
            data = zipped.read(f"{name}/{row['path']}")
            if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
                raise ValueError(f"Checksum sai: {row['path']}")
        for filename in (notebook, PREPROCESSING_NOTEBOOK):
            issues = notebook_issues(json.loads(zipped.read(f"{name}/{filename}")))
            if issues:
                raise ValueError(f"{filename} trong ZIP chưa hoàn tất: " + "; ".join(issues))
        return manifest


def replay_notebook(path: Path, guard: str, log: Path) -> tuple[int, bool]:
    import nbformat

    nb = nbformat.read(path, as_version=4)
    nb.cells.insert(0, nbformat.v4.new_code_cell(guard))
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    replay_input = path.with_suffix(".replay-input.ipynb")
    replay_output = path.with_suffix(".replayed.ipynb")
    nbformat.write(nb, replay_input)
    env = {k: v for k, v in os.environ.items() if k not in {
        "PYTHONPATH", "PYTHONSTARTUP", "STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH",
    }}
    proc = subprocess.run([
        sys.executable, "-X", "utf8", "-m", "nbconvert", "--to", "notebook", "--execute",
        str(replay_input), "--output", replay_output.name,
        "--ExecutePreprocessor.timeout=300",
    ], cwd=path.parent, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
    if proc.returncode:
        log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        raise RuntimeError(f"Chạy lại {path.name} thất bại, xem {log.name}")
    executed = nbformat.read(replay_output, as_version=4)
    issues = notebook_issues(executed)
    if issues:
        raise ValueError(f"Chạy lại {path.name}: " + "; ".join(issues))
    return sum(c.cell_type == "code" for c in executed.cells[1:]), bool(proc.stderr.strip())


def replay_package(archive: Path, milestone: str, output: Path) -> dict:
    """Run both extracted notebooks, blocking reads of the source repo and Downloads."""
    verify_package(archive, milestone)
    scratch = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="kiểm tra gói ", dir=scratch) as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path.parent != scratch:
            raise ValueError("Scratch ngoài vùng cho phép")
        name, notebook = PACKAGES[milestone]
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(temporary_path)
        package = temporary_path / name
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
        preprocessing_cells, preprocessing_messages = replay_notebook(
            package / PREPROCESSING_NOTEBOOK, guard, output / f"replay-{milestone}-preprocessing.log",
        )
        code_cells, messages = replay_notebook(
            package / notebook, guard, output / f"replay-{milestone}.log",
        )
        return {"milestone": milestone, "status": "PASS", "sha256": sha256(archive.read_bytes()),
                "code_cells": code_cells, "preprocessing_code_cells": preprocessing_cells,
                "isolation_guard": True, "python": sys.version.split()[0],
                "system": platform.system(), "launcher_messages": messages or preprocessing_messages}


def sync_loose_deliverables(root: Path, output: Path, *, report_source: Path | None = None) -> None:
    """Keep loose milestone folders (01-giua-ky, 02-cuoi-ky) identical to canonical deliverables."""
    dirs = {"midterm": output / "01-giua-ky", "final": output / "02-cuoi-ky"}
    for milestone, target_dir in dirs.items():
        target_dir.mkdir(parents=True, exist_ok=True)
        for src_rel, dest_name in VISIBLE[milestone].items():
            src = (
                report_source
                if (milestone == "final" and src_rel == "reports/final_report.docx" and report_source is not None)
                else (root / src_rel)
            )
            shutil.copy2(src, target_dir / dest_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--report-source", type=Path, help="final DOCX copy to package under the graded filename")
    parser.add_argument("--verify", action="store_true", help="verify ZIPs and replay both notebooks in each")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    if args.verify:
        receipts = []
        for milestone, (name, _) in PACKAGES.items():
            receipt = replay_package(args.output_dir / f"{name}.zip", milestone, args.output_dir)
            receipts.append(receipt)
            print(f"{milestone}: PASS ({receipt['preprocessing_code_cells']} preprocessing, "
                  f"{receipt['code_cells']} analysis code cells)")
        (args.output_dir / "verification.json").write_text(
            json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:

        (args.output_dir / "verification.json").unlink(missing_ok=True)
        lines = []
        for milestone in PACKAGES:
            path = build_package(ROOT, args.output_dir, milestone, report_source=args.report_source)
            manifest = verify_package(path, milestone)
            lines.append(f"{sha256(path.read_bytes())}  {path.name}\n")
            print(f"{path.name}: {len(manifest['files'])} files, {path.stat().st_size / 1e6:.2f} MB")
        (args.output_dir / "SHA256SUMS.txt").write_text("".join(lines), encoding="utf-8")
        if args.output_dir == OUTPUT.resolve():
            sync_loose_deliverables(ROOT, args.output_dir, report_source=args.report_source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
