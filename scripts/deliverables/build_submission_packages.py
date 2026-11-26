"""Build dependency-complete unified submission ZIP & folder, and replay both notebooks in isolation.

Run from the project root:
    python scripts/deliverables/build_submission_packages.py
Then replay & verify in complete isolation:
    python scripts/deliverables/build_submission_packages.py --verify
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
import time
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.common.notebook_checks import notebook_issues  # noqa: E402
from scripts.data.build_panel import NEW_FILES, OLD_FILES  # noqa: E402

OUTPUT = ROOT / "submissions"
PACKAGE_NAME = "Nhom15_STING_PAPI"
ANALYSIS_NOTEBOOK = "Nhom15_STING_PAPI.ipynb"
PREPROCESSING_NOTEBOOK = "Nhom15_TienXuLy_PAPI.ipynb"
REPORT_NAME = "Nhom15_BaoCao_STING_PAPI.docx"
SLIDES_NAME = "Nhom15_STING_PAPI.pptx"

PACKAGES = {
    "final": (PACKAGE_NAME, ANALYSIS_NOTEBOOK),
}
PREPROCESSING_SOURCE = f"notebooks/{PREPROCESSING_NOTEBOOK}"
MANIFEST_REL = "results/MANIFEST.json"

VISIBLE = {
    "reports/Nhom15_BaoCao_STING_PAPI.docx": REPORT_NAME,
    f"notebooks/{ANALYSIS_NOTEBOOK}": ANALYSIS_NOTEBOOK,
    f"notebooks/{PREPROCESSING_NOTEBOOK}": PREPROCESSING_NOTEBOOK,
    "slides/Nhom15_STING_PAPI.pptx": SLIDES_NAME,
}

PACKAGE_SCRIPTS = (
    "common/fig_style",
    "common/midterm_clustering",
    "common/papi_forecast",
    "common/papi_pred_common",
    "data/build_external_master",
    "data/build_panel",
    "data/build_scale_metadata",
    "data/check_data",
    "data/crosscheck_mendeley",
    "data/preprocessing_audit",
    "data/preprocessing_sensitivity",
    "analysis/cluster_profile",
    "analysis/client_product",
    "analysis/dashboard_data",
    "analysis/external_validation",
    "analysis/first_real_cluster",
    "analysis/poverty_validation",
    "analysis/predict_demo",
    "analysis/predict_sweep",
    "analysis/protocol_sensitivity",
    "analysis/run_analysis",
    "analysis/stakeholder_summary",
    "supervised/course_supervised_baselines",
    "supervised/predict_supervised",
    "supervised/supervised_depth",
    "figures/fig_grid_levels_and_elbow",
    "figures/forecast_papi_grid",
)

PACKAGE_RESULTS = (
    "KetQua_STING_PAPI.xlsx",
    "analysis_summary.md",
    "cluster_labels.csv",
    "cluster_profile.csv",
    "cluster_profile.md",
    "course_supervised_baselines.csv",
    "course_supervised_baselines.md",
    "course_supervised_sensitivity.csv",
    "external_master_summary.md",
    "external_validation.csv",
    "external_validation.md",
    "metrics.csv",
    "papi_forecast_2024.json",
    "papi_forecast_cv.csv",
    "papi_forecast_provinces_2024.csv",
    "papi_observed_grid_2024.csv",
    "per_year.csv",
    "poverty_validation.csv",
    "poverty_validation.md",
    "predict_all_years.csv",
    "predict_config_search.csv",
    "predict_summary.md",
    "preprocessing_audit.csv",
    "preprocessing_audit.md",
    "preprocessing_sensitivity.csv",
    "preprocessing_sensitivity.md",
    "protocol_sensitivity.csv",
    "protocol_sensitivity.md",
    "robustness.csv",
    "stakeholder_province_summary_2024.csv",
    "stakeholder_summary.md",
    "supervised_depth.csv",
    "supervised_depth.md",
    "supervised_metrics.csv",
    "supervised_summary.md",
)

PACKAGE_FIGURES = (
    "00_synthetic_sting",
    "course_confusion_matrix",
    "deep_cluster_profile",
    "evolution",
    "external_grdp_by_cluster",
    "external_health_density_2020",
    "external_pci_by_cluster",
    "external_poverty_by_cluster",
    "external_wdi_panel",
    "kmeans_elbow",
    "map_2020",
    "map_2024",
    "papi_forecast_grid",
    "papi_forecast_values",
    "papi_zscore_comparison",
    "predict_2024",
    "protocol_sensitivity_grid",
    "stakeholder_quadrants_2024",
    "sting_first_real",
    "sting_grid_levels",
    "supervised_importance",
    "supervised_learning_curve",
)

PACKAGE_FILES_CATALOG = {
    "reports/Nhom15_BaoCao_STING_PAPI.docx": "Báo cáo đồ án thống nhất (Word có mục lục và danh mục tự động)",
    f"notebooks/{ANALYSIS_NOTEBOOK}": "Notebook phân tích STING × PAPI & Thống kê khách hàng đã lưu kết quả",
    f"notebooks/{PREPROCESSING_NOTEBOOK}": "Notebook tiền xử lý PAPI 6 bước từ 14 Excel gốc đã lưu kết quả",
    "slides/Nhom15_STING_PAPI.pptx": "Slide trình bày thống nhất (11 trang 16:9 kèm ghi chú)",
    "app.py": "Ứng dụng dashboard Streamlit tương tác (6 tab, gồm Thống kê khách hàng)",
    "src/sting.py": "Mã nguồn thuật toán STING cài đặt từ đầu",
    "src/preprocessing.py": "Mã nguồn pipeline tiền xử lý dữ liệu PAPI 6 bước",
    "requirements.txt": "Danh mục thư viện Python cố định để chạy lại",
    **{f"scripts/{name}.py": "Mã tái lập dữ liệu, phân tích, hình vẽ và dashboard" for name in PACKAGE_SCRIPTS},
    **{
        f"data/raw/papi/{name}": "Bảng tính PAPI gốc"
        for name in (*OLD_FILES.values(), *NEW_FILES.values())
    },
    "data/raw/papi/PROVENANCE.md": "Nguồn và mã kiểm tra dữ liệu PAPI",
    **{
        f"data/raw/mendeley/Replication_package/data/{name}": "Bảng tra mã tỉnh và dữ liệu đối chiếu Mendeley"
        for name in (
            "centroids_63_naturalearth.csv",
            "papi_panel_63_2011_2022.csv",
            "province_crosswalk_63.csv",
            "SHA256_PAPI_ORIGINALS.txt",
        )
    },
    "data/raw/mendeley/PROVENANCE.md": "Nguồn và giấy phép dữ liệu đối chiếu Mendeley",
    "data/raw/boundaries/diaphantinh.geojson": "Ranh giới hành chính cấp tỉnh Việt Nam",
    **{
        f"data/raw/{source}/PROVENANCE.md": "Nguồn và giấy phép dữ liệu ngoài"
        for source in ("boundaries", "pci", "gso", "odmekong", "worldbank")
    },
    "data/processed/external_provenance.md": "Nguồn và quy trình xử lý dữ liệu đối chiếu",
    **{
        f"data/processed/{name}.csv": "Dữ liệu đã chuẩn hóa để chạy lại"
        for name in (
            "papi_panel_63_2011_2024",
            "papi_panel_scale_metadata",
            "external_master_63_2011_2024",
            "external_poverty_63",
            "external_pci_63_full",
            "external_gso_population_63_full",
            "external_gso_grdp_63",
            "external_gso_waste_63",
            "external_odm_health_63",
            "external_worldbank_vnm",
        )
    },
    **{
        f"models/{name}": "Mô hình, scaler, cấu hình đóng băng và hướng dẫn"
        for name in (
            "predict_config.json",
            "sting_predict_model.pkl",
            "sting_predict_scaler.json",
            "sup_ridge.joblib",
            "sup_rf.joblib",
            "sup_classifier.joblib",
            "README.md",
        )
    },
    **{f"results/{name}": "Bảng kết quả thực nghiệm và thống kê bàn giao" for name in PACKAGE_RESULTS},
    **{f"results/figs/{name}.png": "Hình minh họa trong báo cáo, slide và notebook" for name in PACKAGE_FIGURES},
    "reports/panel_lock.md": "Phiên bản và mã kiểm tra bảng PAPI",
    "reports/crosscheck_mendeley.md": "Kết quả đối chiếu PAPI với Mendeley",
    "reports/model_deep_dive.md": "Minh chứng các phép phân tích bổ sung trong báo cáo",
}

RAW_REFERENCES = {
    "data/raw/papi/PAPI_2024_REPORT_VIE_final.pdf": "Báo cáo PAPI 2024 (bản tiếng Việt)",
    "data/raw/mendeley/mendeley_replication.zip": (
        "Dữ liệu và mã đối chiếu của Le và cộng sự (2026), Mendeley Data, DOI 10.17632/wbk42j9wc8.1, CC BY 4.0"
    ),
}

PACKAGED_REQUIREMENTS = (
    "numpy",
    "pandas",
    "scikit-learn",
    "matplotlib",
    "scipy",
    "joblib",
    "jupyter",
    "nbformat",
    "nbconvert",
    "ipykernel",
    "openpyxl",
    "tabulate",
    "plotly",
    "streamlit",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive_path(relative: str, milestone: str = "final") -> str:
    if relative == "MANIFEST.json":
        return MANIFEST_REL
    return VISIBLE.get(relative, relative)


def package_files(root: Path, milestone: str = "final") -> dict[str, str]:
    """Verify every required source file exists in the repository before packaging."""
    files = PACKAGE_FILES_CATALOG.copy()
    files.update(
        {
            relative: description
            for relative, description in RAW_REFERENCES.items()
            if (root / relative).is_file()
        }
    )
    for relative in files:
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Thiếu dependency: {relative}")
    return files


def instructions(*, source_references: tuple[str, ...] = ()) -> str:
    reference_lines = ""
    if source_references:
        listed = "\n".join(f"├── {relative}  {RAW_REFERENCES[relative]}" for relative in source_references)
        reference_lines = f"\nTài liệu đối chiếu kèm theo:\n{listed}\n"
    return f"""================================================================================
HỒ SƠ ĐỒ ÁN MÔN HỌC MÁY — BẢN THỐNG NHẤT HOÀN CHỈNH
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới (Grid-based Clustering — STING)

Kính gửi Thầy Lê Minh Tân,
Đây là gói bài nộp hoàn chỉnh của Nhóm 15, hợp nhất toàn bộ phần cơ chế STING,
quy trình tiền xử lý 6 bước, phân tích PAPI 2011–2024, thống kê bàn giao 63 tỉnh
cho khách hàng, kiểm chứng ngoại lai và dashboard tương tác.

Sinh viên thực hiện:
  - Nguyễn Tiến Sơn     (MSSV: 24110054)
  - Trần Thị Ngọc Quyên (MSSV: 24110051)
================================================================================

1. CẤU TRÚC THƯ MỤC ({PACKAGE_NAME}/)
--------------------------------------------------------------------------------
{PACKAGE_NAME}/
├── {REPORT_NAME}       Báo cáo đồ án (Word có mục lục và danh mục tự động)
├── {SLIDES_NAME}              Slide thuyết trình 11 trang 16:9 kèm ghi chú
├── {ANALYSIS_NOTEBOOK}             Notebook phân tích STING × PAPI & Thống kê khách hàng
├── {PREPROCESSING_NOTEBOOK}          Notebook tiền xử lý PAPI 6 bước từ 14 Excel gốc
├── app.py                              Dashboard Streamlit (chạy: streamlit run app.py)
├── requirements.txt                    Danh mục thư viện Python cố định
├── HUONG_DAN.txt                       Tệp hướng dẫn này
├── src/                                Mã nguồn lõi STING & tiền xử lý
├── scripts/                            Script tái lập panel, phân tích, dự báo & khách hàng
├── reports/                            Tài liệu phụ (panel_lock, crosscheck_mendeley, model_deep_dive)
├── data/                               14 workbook PAPI gốc, Mendeley & nguồn đối chiếu ngoài
├── models/                             Cấu hình, scaler & model đã khóa
└── results/                            Bảng CSV/MD/Excel (KetQua_STING_PAPI.xlsx) & hình PNG
{reference_lines}
2. CHẠY LẠI ĐỘC LẬP TRÊN MÁY KHÁC
--------------------------------------------------------------------------------
Giải nén toàn bộ ZIP và mở terminal tại thư mục {PACKAGE_NAME}/:

python -m pip install -r requirements.txt
python -m nbconvert --to notebook --execute {PREPROCESSING_NOTEBOOK} --output {Path(PREPROCESSING_NOTEBOOK).stem}_chay_lai
python -m nbconvert --to notebook --execute {ANALYSIS_NOTEBOOK} --output {Path(ANALYSIS_NOTEBOOK).stem}_chay_lai
python -m streamlit run app.py

3. TÁI LẬP SỐ LIỆU & THỐNG KÊ KHÁCH HÀNG TỪ DỮ LIỆU GỐC
--------------------------------------------------------------------------------
python scripts/data/build_panel.py
python scripts/data/build_scale_metadata.py
python scripts/data/check_data.py
python scripts/data/build_external_master.py
python scripts/data/preprocessing_audit.py
python scripts/data/preprocessing_sensitivity.py
python scripts/data/crosscheck_mendeley.py
python -E scripts/analysis/stakeholder_summary.py --with-excel
python scripts/figures/forecast_papi_grid.py

Trân trọng,
Nhóm 15
"""


def verify_report_fields(data: bytes) -> None:
    """Reject a draft DOCX whose Word table-of-contents or caption catalogs are empty."""
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
    expected_catalog = (("Hình", 13), ("Bảng", 15))
    if chapters != set("1234567") or any(
        sum(line.startswith(label + " ") for line in entries["TableofFigures"]) != count
        for label, count in expected_catalog
    ):
        raise ValueError("Mục lục hoặc danh mục Word chưa đầy đủ; chạy update_report_fields.py bằng Word.")


def _trimmed_requirements(root: Path) -> bytes:
    lines = (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
    pins = {line.split("==", 1)[0]: line for line in lines if "==" in line}
    return ("\n".join(pins[pkg] for pkg in PACKAGED_REQUIREMENTS) + "\n").encode("utf-8")


def build_package(root: Path, output: Path, milestone: str = "final", *, report_source: Path | None = None) -> Path:
    sources = package_files(root, milestone)
    files = {archive_path(p, milestone): role for p, role in sources.items()}
    payload = {archive_path(p, milestone): (root / p).read_bytes() for p in sources}
    now_dt = time.localtime()[:6]
    mtimes = {
        archive_path(p, milestone): time.localtime((root / p).stat().st_mtime)[:6]
        for p in sources
    }
    for filename in (ANALYSIS_NOTEBOOK, PREPROCESSING_NOTEBOOK):
        issues = notebook_issues(json.loads(payload[filename]))
        if issues:
            raise ValueError(f"{filename}: " + "; ".join(issues))

    payload["requirements.txt"] = _trimmed_requirements(root)
    mtimes["requirements.txt"] = now_dt
    report = REPORT_NAME
    if report_source is not None:
        payload[report] = report_source.read_bytes()
        mtimes[report] = time.localtime(report_source.stat().st_mtime)[:6]
    verify_report_fields(payload[report])

    refs = tuple(relative for relative in RAW_REFERENCES if relative in sources)
    payload["HUONG_DAN.txt"] = instructions(source_references=refs).encode("utf-8")
    files["HUONG_DAN.txt"] = "Hướng dẫn mở và chạy lại đồ án"
    mtimes["HUONG_DAN.txt"] = now_dt

    manifest = {
        "schema_version": 2,
        "milestone": milestone,
        "root": PACKAGE_NAME,
        "files": [
            {
                "path": p,
                "bytes": len(payload[p]),
                "sha256": sha256(payload[p]),
                "role": files[p],
            }
            for p in sorted(payload)
        ],
    }
    if report_source is not None:
        manifest["report_source"] = report_source.name
    payload[MANIFEST_REL] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    mtimes[MANIFEST_REL] = now_dt

    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path, data in sorted(payload.items(), key=lambda item: ("/" not in item[0], item[0])):
            info = zipfile.ZipInfo(f"{PACKAGE_NAME}/{path}", date_time=mtimes.get(path, now_dt))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, data)
    return archive


def check_member(name: str) -> None:
    parts = PurePosixPath(name).parts
    if (
        not parts
        or PurePosixPath(name).is_absolute()
        or ".." in parts
        or "\\" in name
        or ":" in name
        or name != PurePosixPath(name).as_posix()
    ):
        raise ValueError(f"Đường dẫn ZIP không an toàn: {name}")


def verify_package(archive: Path, milestone: str = "final") -> dict:
    manifest_path = f"{PACKAGE_NAME}/{MANIFEST_REL}"
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len({p.casefold() for p in names}):
            raise ValueError("ZIP có đường dẫn trùng")
        for info in zipped.infolist():
            check_member(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Không chấp nhận symlink trong ZIP")
            if info.date_time[0] <= 1980:
                raise ValueError(f"Timestamp chưa chuẩn (1980): {info.filename}")
        manifest = json.loads(zipped.read(manifest_path))
        if manifest.get("milestone") != milestone or manifest.get("root") != PACKAGE_NAME:
            raise ValueError("Manifest không khớp cấu hình gói nộp")
        rows = manifest["files"]
        expected = {f"{PACKAGE_NAME}/{r['path']}" for r in rows} | {manifest_path}
        if len(expected) != len(rows) + 1 or set(names) != expected:
            raise ValueError("ZIP thiếu/thừa file so với manifest")
        delivery = {f"{PACKAGE_NAME}/{archive_path(p, milestone)}" for p in PACKAGE_FILES_CATALOG}
        delivery.update((manifest_path, f"{PACKAGE_NAME}/HUONG_DAN.txt"))
        raw_references = {f"{PACKAGE_NAME}/{archive_path(p, milestone)}" for p in RAW_REFERENCES}
        if not delivery <= expected <= (delivery | raw_references):
            raise ValueError("ZIP lệch danh mục tệp nộp")
        verify_report_fields(zipped.read(f"{PACKAGE_NAME}/{REPORT_NAME}"))
        for row in rows:
            data = zipped.read(f"{PACKAGE_NAME}/{row['path']}")
            if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
                raise ValueError(f"Checksum sai: {row['path']}")
        for filename in (ANALYSIS_NOTEBOOK, PREPROCESSING_NOTEBOOK):
            issues = notebook_issues(json.loads(zipped.read(f"{PACKAGE_NAME}/{filename}")))
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
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {
            "PYTHONPATH",
            "PYTHONSTARTUP",
            "STING_REPO_ROOT",
            "SUBMISSION_DEMO_NB_PATH",
            "JPY_STARTUP_PATH",
            "MPLBACKEND",
        }
    }
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
            str(replay_input),
            "--output",
            replay_output.name,
            "--ExecutePreprocessor.timeout=300",
        ],
        cwd=path.parent,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    if proc.returncode:
        log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        raise RuntimeError(f"Chạy lại {path.name} thất bại, xem {log.name}")
    executed = nbformat.read(replay_output, as_version=4)
    issues = notebook_issues(executed)
    if issues:
        diagnostics = [f"Chạy lại {path.name}. Danh sách kiểm tra tính cả ô cách ly đầu tiên.", *issues]
        code_cells = (cell for cell in executed.cells if cell.cell_type == "code")
        for number, cell in enumerate(code_cells):
            for output in cell.outputs:
                if output.output_type == "stream" and output.name == "stderr":
                    detail = "".join(output.text).rstrip()
                    position = f"ô code gốc {number}" if number else "ô cách ly"
                    diagnostics.extend((f"stderr ở {position}", detail))
        content = "\n".join(diagnostics) + "\n"
        for home_path in {str(Path.home()), Path.home().as_posix()}:
            content = content.replace(home_path, "<HOME>")
        log.write_text(content, encoding="utf-8")
        raise ValueError(f"Chạy lại {path.name} chưa đạt. Xem {log.name}. " + "; ".join(issues))
    return sum(c.cell_type == "code" for c in executed.cells[1:]), bool(proc.stderr.strip())


def replay_package(archive: Path, output: Path) -> dict:
    """Extract unified ZIP cleanly and replay both notebooks with audit isolation guard."""
    verify_package(archive)
    scratch = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="kiểm tra gói ", dir=scratch) as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path.parent != scratch:
            raise ValueError("Scratch ngoài vùng cho phép")
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(temporary_path)
        package = temporary_path / PACKAGE_NAME
        guard = f'''import os, sys
from pathlib import Path
_allowed = Path({str(package)!r}).resolve()
_blocked = [Path(p).resolve() for p in {list(map(str, [ROOT, Path.home() / "Downloads"]))!r}]
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
            package / PREPROCESSING_NOTEBOOK, guard, output / "replay-preprocessing.log"
        )
        code_cells, messages = replay_notebook(
            package / ANALYSIS_NOTEBOOK, guard, output / "replay-analysis.log"
        )
        return {
            "package": PACKAGE_NAME,
            "status": "PASS",
            "sha256": sha256(archive.read_bytes()),
            "code_cells": code_cells,
            "preprocessing_code_cells": preprocessing_cells,
            "isolation_guard": True,
            "python": sys.version.split()[0],
            "system": platform.system(),
            "launcher_messages": messages or preprocessing_messages,
        }


def sync_loose_deliverable(archive: Path, output: Path) -> Path:
    """Keep submissions/Nhom15_STING_PAPI/ an exact unpacked mirror of the verified ZIP."""
    target_dir = output / PACKAGE_NAME
    if target_dir.exists():
        shutil.rmtree(target_dir)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(output)
    return target_dir


def write_submissions_guide(output: Path) -> None:
    guide = f"""HƯỚNG DẪN BÀI NỘP THỐNG NHẤT — NHÓM 15 (STING × PAPI 2011–2024)

Thư mục này chứa 1 gói hoàn thiện duy nhất (gộp đầy đủ phần giữa kỳ, cuối kỳ,
tiền xử lý 6 bước từ Excel gốc và thống kê bàn giao 63 tỉnh cho khách hàng):

1. {PACKAGE_NAME}.zip
   - Gói nén tự chạy độc lập toàn bộ đồ án (báo cáo Word, slide, 2 notebook,
     dashboard app.py, mã nguồn, 14 workbook PAPI gốc, model & kết quả).
   - Xác thực toàn vẹn qua SHA256SUMS.txt và verification.json.

2. {PACKAGE_NAME}/
   - Bản giải nén đồng nhất 1-1 với {PACKAGE_NAME}.zip để xem hoặc mở trực tiếp:
     + {REPORT_NAME}  (Báo cáo Word đầy đủ có mục lục & danh mục)
     + {SLIDES_NAME}           (Bộ slide bảo vệ 11 trang 16:9)
     + {ANALYSIS_NOTEBOOK}          (Notebook đồ án hoàn chỉnh)
     + {PREPROCESSING_NOTEBOOK}    (Notebook tiền xử lý PAPI 6 bước)
     + app.py                          (Dashboard tương tác Streamlit)
"""
    (output / "HUONG-DAN.txt").write_text(guide, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--report-source", type=Path, help="Báo cáo DOCX tùy chọn đóng gói theo tên chuẩn")
    parser.add_argument("--verify", action="store_true", help="Kiểm tra ZIP và chạy lại cả 2 notebook trong môi trường cách ly")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    archive = args.output_dir / f"{PACKAGE_NAME}.zip"

    if args.verify:
        receipt = replay_package(archive, args.output_dir)
        (args.output_dir / "verification.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"{PACKAGE_NAME}: PASS ({receipt['preprocessing_code_cells']} preprocessing, "
            f"{receipt['code_cells']} analysis code cells, Python {receipt['python']}, {receipt['system']})"
        )
        return 0

    (args.output_dir / "verification.json").unlink(missing_ok=True)
    archive = build_package(ROOT, args.output_dir, "final", report_source=args.report_source)
    manifest = verify_package(archive, "final")
    (args.output_dir / "SHA256SUMS.txt").write_text(
        f"{sha256(archive.read_bytes())}  {archive.name}\n", encoding="utf-8"
    )
    if args.output_dir == OUTPUT.resolve():
        sync_loose_deliverable(archive, args.output_dir)
        write_submissions_guide(args.output_dir)
    print(f"{archive.name}: {len(manifest['files'])} files, {archive.stat().st_size / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
