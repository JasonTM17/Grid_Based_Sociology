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
import time
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
    "data/build_external_master",
    "data/crosscheck_mendeley",
    "data/preprocessing_audit", "data/preprocessing_sensitivity",
    "analysis/first_real_cluster", "common/papi_forecast",
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
    "preprocessing_audit.csv", "preprocessing_audit.md",
    "preprocessing_sensitivity.csv", "preprocessing_sensitivity.md",
    "protocol_sensitivity.csv",
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
SUPPORT = ""
MANIFEST_REL = "results/MANIFEST.json"
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
    "src/preprocessing.py": "Mã nguồn pipeline tiền xử lý dữ liệu PAPI 6 bước",
    "scripts/data/build_panel.py": "Đọc Excel gốc và xây bảng PAPI",
    "scripts/data/build_scale_metadata.py": "Tạo bảng metadata kiểm tra thang đo và cửa sổ khảo sát",
    "scripts/data/check_data.py": "Kiểm tra kích thước bảng PAPI và audit thang đo",
    "scripts/data/preprocessing_audit.py": "Kiểm tra đầy đủ quy trình làm sạch, tích hợp và biến đổi",
    "scripts/data/crosscheck_mendeley.py": "Đối chiếu chéo bảng PAPI với dữ liệu replication Mendeley",
    "scripts/common/papi_pred_common.py": "Đọc bảng, cấu hình chỉ tiêu và lưới STING",
    "scripts/common/fig_style.py": "Định dạng biểu đồ dùng trong notebook",
    "models/predict_config.json": "Cấu hình chỉ tiêu PAPI dùng trong phân cụm",
    "models/sting_predict_scaler.json": "Tham số chuẩn hóa StandardScaler đã khóa trên tập ≤2023",
    "data/processed/papi_panel_63_2011_2024.csv": "Bảng PAPI đã tiền xử lý",
    "data/processed/papi_panel_scale_metadata.csv": "Bảng metadata kiểm tra thang đo và khoảng hợp lệ",
    "data/processed/external_master_63_2011_2024.csv": "Bảng tích hợp 882×59 kiểm chứng khóa nối và mask thiếu",
    "data/raw/mendeley/Replication_package/data/province_crosswalk_63.csv": "Bảng tra mã và tên tỉnh",
    "data/raw/mendeley/Replication_package/data/papi_panel_63_2011_2022.csv": "Bảng PAPI 2011–2022 đối chiếu Mendeley",
    "data/raw/mendeley/Replication_package/data/SHA256_PAPI_ORIGINALS.txt": "Mã băm SHA-256 đối chiếu workbook gốc",
    "data/raw/mendeley/PROVENANCE.md": "Nguồn và giấy phép bảng tra mã tỉnh",
    "data/raw/papi/PROVENANCE.md": "Nguồn và mã kiểm tra dữ liệu PAPI",
    "results/preprocessing_audit.csv": "Bảng kiểm tra quy trình tiền xử lý (CSV)",
    "results/preprocessing_audit.md": "Bảng kiểm tra quy trình tiền xử lý (Markdown)",
    "results/preprocessing_sensitivity.csv": "Bảng đối chiếu độ nhạy tiền xử lý (CSV)",
    "results/preprocessing_sensitivity.md": "Bảng đối chiếu độ nhạy tiền xử lý (Markdown)",
    **{f"data/raw/papi/{name}": "Bảng tính PAPI gốc" for name in (*OLD_FILES.values(), *NEW_FILES.values())},
}
MIDTERM_FILES = {
    "slides/submission.pptx": "Bản trình chiếu",
    f"notebooks/{MIDTERM_NOTEBOOK}": "Notebook đã lưu kết quả",
    "src/sting.py": "Mã nguồn thuật toán STING",
    "scripts/common/midterm_clustering.py": "Tham số, mã phân cụm và biểu đồ dùng trong notebook",
    "scripts/analysis/predict_sweep.py": "Khảo sát chọn cặp chỉ tiêu và cấu hình lưới STING",
    "scripts/analysis/first_real_cluster.py": "Minh họa hai cấu hình lưới STING trên dữ liệu PAPI",
    "scripts/figures/fig_grid_levels_and_elbow.py": "Sinh hình ba mức lưới STING và chọn k cho K-means",
    "requirements.txt": "Thư viện để chạy notebook",
    **PAPI_PREPROCESSING_FILES,
    "results/predict_config_search.csv": "Kết quả khảo sát cấu hình lưới STING",
    "results/per_year.csv": "Kết quả phân cụm STING theo từng năm",
    "results/papi_observed_grid_2024.csv": "Lý do gán cụm trên lưới tham chiếu của 63 tỉnh, thành phố",
    "results/figs/00_synthetic_sting.png": "Kiểm chứng STING trên 240 điểm giả lập hai cụm Gauss",
    "results/figs/papi_zscore_comparison.png": "Đối chiếu STING, K-means và DBSCAN trước và sau z-score",
    "results/figs/predict_2024.png": "Điểm PAPI đã quan sát năm 2024 trên lưới đến 2023",
    "results/figs/sting_first_real.png": "Hai cấu hình lưới STING trên dữ liệu PAPI",
    "results/figs/sting_grid_levels.png": "Ba mức của lưới STING phân cấp trên PAPI",
    "results/figs/kmeans_elbow.png": "WCSS và silhouette của K-means theo số cụm k",
}
FINAL_FILES = {
    "reports/final_report.docx": "Báo cáo cuối kỳ",
    f"notebooks/{FINAL_NOTEBOOK}": "Notebook đã lưu kết quả",
    "slides/final.pptx": "Slide vấn đáp",
    "src/sting.py": "Mã nguồn thuật toán STING",
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
    if relative == "MANIFEST.json":
        return MANIFEST_REL
    return VISIBLE[milestone].get(relative, relative)


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
        raw_references = "\nTài liệu nguồn kèm theo trong data/raw/:\n" + "".join(
            f"  - {relative} — {RAW_REFERENCES[relative]}.\n"
            for relative in source_references
        )
    if milestone == "midterm":
        replay = "python -X utf8 -m nbconvert --to notebook --execute"
        return f"""BÀI NỘP GIỮA KỲ · MÔN HỌC MÁY
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới STING
Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)
Giảng viên hướng dẫn: ThS. Lê Minh Tân

Kính gửi Thầy Lê Minh Tân,

Nhóm 15 trình bày cách ứng dụng STING để quan sát đặc điểm và biến động của
các chỉ số quản trị, hành chính công cấp tỉnh trên bảng PAPI 2011–2024.

1. XEM BÀI NỘP

- {MIDTERM_NAME}.pptx — 10 slide trình bày kể cả bìa, cộng 1 slide cảm ơn.
- {notebook} — Từ ví dụ lưới nhỏ đến phân cụm và so sánh PAPI qua các năm.
- {PREPROCESSING_NOTEBOOK} — Sáu bước xử lý dữ liệu từ 14 bảng tính Excel gốc.

Hai notebook đã lưu sẵn bảng kết quả và biểu đồ. Có thể mở trực tiếp để xem.

2. CHẠY LẠI NOTEBOOK

Giải nén toàn bộ ZIP và mở terminal trong thư mục có requirements.txt.
Dùng môi trường Python 3.14. Có thể tạo môi trường riêng bằng
python -m venv .venv rồi chọn trình thông dịch của môi trường đó.
Các lệnh dưới đây dùng python của môi trường đã chọn.

python --version
python -m pip install -r requirements.txt
{replay} {PREPROCESSING_NOTEBOOK} --output-dir chay_lai --output {Path(PREPROCESSING_NOTEBOOK).stem}
{replay} {notebook} --output-dir chay_lai --output {MIDTERM_NAME}

Kết quả chạy lại nằm trong chay_lai/. Trong Jupyter hoặc VS Code, mở
notebook từ thư mục đã giải nén, chọn kernel Python 3.14 đã cài thư viện,
rồi dùng Restart Kernel → Run All Cells.

3. ĐỐI CHIẾU MÃ NGUỒN VÀ DỮ LIỆU

- src/sting.py — Cài đặt STING. src/preprocessing.py — Quy trình xử lý PAPI.
- scripts/common/midterm_clustering.py — Tham số và hàm dùng trong notebook.
- data/raw/ và data/processed/ — Dữ liệu nguồn và bảng PAPI 882 dòng, 41 cột.
- models/ — Cấu hình lưới và tham số chuẩn hóa đến năm 2023.
- results/papi_observed_grid_2024.csv — Kết quả đối chiếu từng tỉnh với lưới tham chiếu.
- results/MANIFEST.json — Danh mục và mã SHA-256 của các tệp trong gói.
{raw_references}
Để dựng lại bảng PAPI và kiểm tra dữ liệu từ Excel gốc, chạy ở cùng thư mục:

python scripts/data/build_panel.py
python scripts/data/build_scale_metadata.py
python scripts/data/check_data.py
python scripts/data/preprocessing_audit.py
python scripts/data/crosscheck_mendeley.py
"""
    run_preprocessing = (
        f"python -m nbconvert --to notebook --execute {PREPROCESSING_NOTEBOOK} "
        f"--output {Path(PREPROCESSING_NOTEBOOK).stem}_chay_lai"
    )
    return f"""================================================================================
BÁO CÁO CUỐI KỲ MÔN HỌC MÁY
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới (Grid-based Clustering — STING)
Sinh viên thực hiện:
  - Nguyễn Tiến Sơn     (MSSV: 24110054)
  - Trần Thị Ngọc Quyên (MSSV: 24110051)
Giảng viên hướng dẫn: ThS. Lê Minh Tân
================================================================================

Kính gửi Thầy Lê Minh Tân,

Nhóm 15 xin gửi gói bài nộp Cuối kỳ nghiên cứu thuật toán phân cụm dựa trên lưới
STING (Statistical Information Grid) và ứng dụng phân tích, đối chiếu dữ liệu
quản trị hành chính công cấp tỉnh PAPI giai đoạn 2011–2024 (882 quan sát).

1. CẤU TRÚC THƯ MỤC GÓI NỘP
--------------------------------------------------------------------------------
{FINAL_NAME}/
├── {FINAL_NAME}.docx       Báo cáo tổng kết đồ án (Word, 45 trang)
├── {FINAL_NAME}.pptx       Slide bảo vệ cuối kỳ (10 trang đầu kể cả bìa và 1 trang cảm ơn)
├── {notebook}      Notebook phân tích cuối kỳ đã chạy sẵn
├── {PREPROCESSING_NOTEBOOK}  Notebook tiền xử lý PAPI 6 bước
├── HUONG_DAN.txt             Hướng dẫn cấu trúc và cách chạy
├── requirements.txt          Danh mục thư viện Python cố định
├── src/
│   ├── sting.py              Thuật toán STING cài đặt từ đầu
│   └── preprocessing.py      Mô-đun tiền xử lý 6 bước PAPI
├── data/
│   ├── raw/                  14 file Excel PAPI gốc, Mendeley, PCI, GSO, WB
│   └── processed/            Panel PAPI (882×41) & bảng ghép (882×59)
├── scripts/
│   ├── common/               Hàm dùng chung & giao thức dự báo
│   ├── data/                 Script dựng panel & kiểm toán tiền xử lý
│   ├── analysis/             Script phân cụm STING & kiểm chứng ngoài
│   ├── supervised/           Script hồi quy và phân loại bổ trợ
│   └── figures/              Script sinh biểu đồ lưới & dự báo vùng 2024
├── models/
│   ├── sting_predict_model.pkl    Mô hình lưới STING (2011–2023)
│   ├── sting_predict_scaler.json  Tham số StandardScaler (2011–2023)
│   ├── predict_config.json        Cấu hình chỉ tiêu & tham số lưới
│   └── sup_*.joblib               Mô hình học có giám sát đối chiếu
├── results/
    ├── preprocessing_audit.*      Bảng kiểm toán quy trình tiền xử lý
    ├── preprocessing_sensitivity.* Bảng độ nhạy 3 phương án (A/B/C)
    ├── MANIFEST.json              Danh mục tệp & mã kiểm tra SHA-256
    └── figs/                      Bộ biểu đồ thực nghiệm trong báo cáo
└── reports/
    ├── panel_lock.md              Hồ sơ khóa phiên bản bảng PAPI
    ├── crosscheck_mendeley.md     Đối chiếu chéo với gói Mendeley
    └── model_deep_dive.md         Phân tích chuyên sâu các mô hình
{raw_references}
2. HƯỚNG DẪN XEM VÀ CHẠY LẠI NOTEBOOK
--------------------------------------------------------------------------------
Hai notebook ở thư mục gốc đã lưu sẵn kết quả và biểu đồ để xem trực tiếp.
Để chạy lại từ đầu:
- Trong Jupyter / VS Code: giải nén toàn bộ gói, mở {PREPROCESSING_NOTEBOOK}
  hoặc {notebook}, chọn kernel Python 3.14, rồi chọn
  Restart Kernel → Run All Cells.
- Bằng dòng lệnh (mở terminal tại thư mục {FINAL_NAME}/ vừa giải nén):

python -m pip install -r requirements.txt
{run_preprocessing}
python -m nbconvert --to notebook --execute {notebook} --output {FINAL_NAME}_chay_lai

3. TÁI LẬP PANEL & KIỂM TOÁN TIỀN XỬ LÝ TỪ 14 BẢNG TÍNH EXCEL GỐC
--------------------------------------------------------------------------------
Chạy trực tiếp các lệnh sau ngay tại thư mục {FINAL_NAME}/:

python scripts/data/build_panel.py
python scripts/data/build_scale_metadata.py
python scripts/data/check_data.py
python scripts/data/build_external_master.py
python scripts/data/preprocessing_audit.py
python scripts/data/preprocessing_sensitivity.py
python scripts/data/crosscheck_mendeley.py
python scripts/figures/forecast_papi_grid.py

Phụ lục A của báo cáo Word trình bày đầy đủ danh mục các lệnh tái lập.

Trân trọng,
Nhóm 15
"""


def loose_instructions(milestone: str) -> str:
    """Guide for the files visible in a milestone folder in the repo."""
    name, notebook = PACKAGES[milestone]
    if milestone == "midterm":
        title = "GIỮA KỲ"
        presentation = f"- {name}.pptx — 10 slide trình bày kể cả bìa, cộng 1 slide cảm ơn."
    else:
        title = "CUỐI KỲ"
        presentation = f"- {name}.docx — Báo cáo đồ án.\n- {name}.pptx — Slide bảo vệ."
    return f"""BẢN XEM NHANH {title} · NHÓM 15 · MÔN HỌC MÁY

{presentation}
- {notebook} — Notebook phân tích STING đã lưu kết quả.
- {PREPROCESSING_NOTEBOOK} — Notebook tiền xử lý PAPI đã lưu kết quả.
- src/ — Mã nguồn STING và tiền xử lý để đọc cùng notebook.

Để gửi bài hoặc chạy lại notebook độc lập, dùng ../{name}.zip.
Giải nén toàn bộ ZIP rồi mở HUONG_DAN.txt trong gói để cài thư viện và chạy.
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
    expected_catalog = (("Hình", 12), ("Bảng", 13))
    if chapters != set("1234567") or any(
        sum(line.startswith(label + " ") for line in entries["TableofFigures"]) != count
        for label, count in expected_catalog
    ):
        raise ValueError("Mục lục hoặc danh mục Word chưa đầy đủ; chạy update_report_fields.py bằng Word.")


def build_package(root: Path, output: Path, milestone: str, *, report_source: Path | None = None) -> Path:
    name, notebook = PACKAGES[milestone]
    sources = package_files(root, milestone)
    files = {archive_path(p, milestone): role for p, role in sources.items()}
    payload = {archive_path(p, milestone): (root / p).read_bytes() for p in sources}
    now_dt = time.localtime()[:6]
    mtimes = {
        archive_path(p, milestone): time.localtime((root / p).stat().st_mtime)[:6]
        for p in sources
    }
    for filename in (notebook, PREPROCESSING_NOTEBOOK):
        issues = notebook_issues(json.loads(payload[filename]))
        if issues:
            raise ValueError(f"{filename}: " + "; ".join(issues))
    requirements = archive_path("requirements.txt", milestone)
    pins = {line.split("==", 1)[0]: line for line in payload[requirements].decode("utf-8").splitlines()
            if "==" in line}
    needed = MIDTERM_REQUIREMENTS if milestone == "midterm" else FINAL_REQUIREMENTS
    payload[requirements] = ("\n".join(pins[p] for p in needed) + "\n").encode("utf-8")
    mtimes[requirements] = now_dt
    if milestone == "final":
        report = FINAL_VISIBLE["reports/final_report.docx"]
        if report_source is not None:
            payload[report] = report_source.read_bytes()
            mtimes[report] = time.localtime(report_source.stat().st_mtime)[:6]
        verify_report_fields(payload[report])
    payload["HUONG_DAN.txt"] = instructions(
        milestone, source_references=tuple(relative for relative in RAW_REFERENCES if relative in sources),
    ).encode("utf-8")
    files["HUONG_DAN.txt"] = "Hướng dẫn mở và chạy lại bài nộp"
    mtimes["HUONG_DAN.txt"] = now_dt
    manifest = {
        "schema_version": 1, "milestone": milestone, "root": name,
        "files": [{"path": p, "bytes": len(payload[p]), "sha256": sha256(payload[p]),
                   "role": files[p]} for p in sorted(payload)],
    }
    if milestone == "final" and report_source is not None:
        manifest["report_source"] = report_source.name
    manifest_arc = archive_path("MANIFEST.json", milestone)
    payload[manifest_arc] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    mtimes[manifest_arc] = now_dt
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path, data in sorted(payload.items(), key=lambda item: ("/" not in item[0], item[0])):
            info = zipfile.ZipInfo(f"{name}/{path}", date_time=mtimes.get(path, now_dt))
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
            if info.date_time[0] <= 1980:
                raise ValueError(f"Timestamp chưa chuẩn (1980): {info.filename}")
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
        "PYTHONPATH", "PYTHONSTARTUP", "STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH", "MPLBACKEND",
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


def _trimmed_requirements(root: Path, needed: tuple[str, ...]) -> bytes:
    lines = (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
    pins = {line.split("==", 1)[0]: line for line in lines if "==" in line}
    return ("\n".join(pins[pkg] for pkg in needed) + "\n").encode("utf-8")


def preprocessing_instructions() -> str:
    return f"""================================================================================
CHUYÊN ĐỀ TIỀN XỬ LÝ DỮ LIỆU PAPI 2011–2024
Nhóm 15 · Chủ đề 6 · Phân cụm dựa trên lưới (Grid-based Clustering — STING)
Sinh viên thực hiện:
  - Nguyễn Tiến Sơn     (MSSV: 24110054)
  - Trần Thị Ngọc Quyên (MSSV: 24110051)
Giảng viên hướng dẫn: ThS. Lê Minh Tân
================================================================================

Thư mục này đóng gói độc lập toàn bộ mã nguồn, 14 bảng tính Excel PAPI gốc
(2011–2024) và bảng tra mã tỉnh để chạy riêng chuyên đề tiền xử lý dữ liệu.

1. CẤU TRÚC THƯ MỤC
--------------------------------------------------------------------------------
03-tien-xu-ly-papi/
├── {PREPROCESSING_NOTEBOOK}  Notebook tiền xử lý PAPI 6 bước
├── HUONG_DAN.txt             Hướng dẫn cấu trúc và cách chạy
├── requirements.txt          Danh mục thư viện Python cố định
├── src/
│   ├── preprocessing.py      Mô-đun tiền xử lý 6 bước PAPI
│   └── sting.py              Thuật toán STING cài đặt từ đầu
├── data/
│   ├── raw/papi/             14 bảng tính Excel PAPI gốc
│   ├── raw/mendeley/         Bảng mã 63 tỉnh & đối chiếu Mendeley
│   └── processed/            Panel PAPI (882×41) & bảng ghép (882×59)
├── scripts/
│   ├── common/               Hàm đọc dữ liệu & định dạng đồ thị
│   └── data/                 Script dựng panel & kiểm toán tiền xử lý
├── models/
│   ├── predict_config.json   Cấu hình chỉ tiêu & tham số lưới
│   └── sting_predict_scaler.json  Tham số StandardScaler (≤ 2023)
└── results/
    ├── preprocessing_audit.*      Bảng kiểm toán quy trình tiền xử lý
    └── preprocessing_sensitivity.* Bảng độ nhạy 3 phương án (A/B/C)

2. HƯỚNG DẪN XEM VÀ CHẠY TRỰC TIẾP TỪ THƯ MỤC NÀY
--------------------------------------------------------------------------------
1. Trong Jupyter / VS Code: mở {PREPROCESSING_NOTEBOOK} trong thư mục này,
   chọn kernel Python 3.14, sau đó chọn Restart Kernel → Run All Cells.
2. Bằng dòng lệnh (mở terminal tại chính thư mục 03-tien-xu-ly-papi/):

python -m pip install -r requirements.txt
python scripts/data/build_panel.py
python scripts/data/build_scale_metadata.py
python scripts/data/check_data.py
python scripts/data/preprocessing_audit.py
python scripts/data/crosscheck_mendeley.py
python -m nbconvert --to notebook --execute {PREPROCESSING_NOTEBOOK} --output {Path(PREPROCESSING_NOTEBOOK).stem}_chay_lai

Trân trọng,
Nhóm 15
"""


def sync_loose_deliverables(root: Path, output: Path, *, report_source: Path | None = None) -> None:
    """Keep loose milestone folders (01-giua-ky, 02-cuoi-ky, 03-tien-xu-ly-papi) identical to canonical deliverables."""
    dirs = {"midterm": output / "01-giua-ky", "final": output / "02-cuoi-ky"}
    for milestone, target_dir in dirs.items():
        target_dir.mkdir(parents=True, exist_ok=True)
        for stale_top in ("sting.py", "preprocessing.py"):
            (target_dir / stale_top).unlink(missing_ok=True)
        for src_rel, dest_name in VISIBLE[milestone].items():
            src = (
                report_source
                if (milestone == "final" and src_rel == "reports/final_report.docx" and report_source is not None)
                else (root / src_rel)
            )
            shutil.copy2(src, target_dir / dest_name)
        shutil.copy2(root / PREPROCESSING_SOURCE, target_dir / PREPROCESSING_NOTEBOOK)
        src_subdir = target_dir / "src"
        src_subdir.mkdir(parents=True, exist_ok=True)
        for src_rel in ("src/sting.py", "src/preprocessing.py"):
            shutil.copy2(root / src_rel, target_dir / src_rel)
        (target_dir / "HUONG_DAN.txt").write_text(
            loose_instructions(milestone), encoding="utf-8", newline="\n",
        )

    preproc_dir = output / "03-tien-xu-ly-papi"
    preproc_dir.mkdir(parents=True, exist_ok=True)
    for stale_rel in ("scripts/build_panel.py", "scripts/papi_pred_common.py", "sting.py", "preprocessing.py"):
        (preproc_dir / stale_rel).unlink(missing_ok=True)
    shutil.copy2(root / PREPROCESSING_SOURCE, preproc_dir / PREPROCESSING_NOTEBOOK)
    for rel in ("src/sting.py", *(k for k in PAPI_PREPROCESSING_FILES if k != PREPROCESSING_SOURCE)):
        dst = preproc_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    (preproc_dir / "requirements.txt").write_bytes(_trimmed_requirements(root, MIDTERM_REQUIREMENTS))
    (preproc_dir / "HUONG_DAN.txt").write_text(preprocessing_instructions(), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--report-source", type=Path, help="final DOCX copy to package under the graded filename")
    parser.add_argument("--verify", action="store_true", help="verify ZIPs and replay both notebooks in each")
    parser.add_argument("--milestone", choices=PACKAGES, help="with --verify, check one ZIP without replacing the receipt")
    args = parser.parse_args()
    if args.milestone and not args.verify:
        parser.error("--milestone requires --verify")
    args.output_dir = args.output_dir.resolve()
    if args.verify:
        receipts = []
        milestones = (args.milestone,) if args.milestone else PACKAGES
        for milestone in milestones:
            name, _ = PACKAGES[milestone]
            receipt = replay_package(args.output_dir / f"{name}.zip", milestone, args.output_dir)
            receipts.append(receipt)
            print(f"{milestone}: PASS ({receipt['preprocessing_code_cells']} preprocessing, "
                  f"{receipt['code_cells']} analysis code cells, Python {receipt['python']}, {receipt['system']})")
        if not args.milestone:
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
