# Hệ thống Mã nguồn Pipeline (`scripts/`)

Tất cả script được chạy từ thư mục gốc dự án (ví dụ: `python scripts/data/check_data.py`).

| Thư mục | Vai trò | Tệp tiêu biểu |
|---|---|---|
| `scripts/data/` | Dựng panel PAPI, metadata thang đo, đối chiếu Mendeley, kiểm tra tiền xử lý & nạp nguồn ngoại lai | `build_panel.py`, `build_scale_metadata.py`, `build_external_master.py`, `check_data.py`, `crosscheck_mendeley.py`, `preprocessing_audit.py`, `preprocessing_sensitivity.py` |
| `scripts/analysis/` | Chạy STING theo cấu hình chốt, quét tham số, kiểm chứng PCI/nghèo & chuẩn bị dữ liệu dashboard | `predict_sweep.py`, `predict_demo.py`, `run_analysis.py`, `cluster_profile.py`, `protocol_sensitivity.py`, `external_validation.py`, `poverty_validation.py`, `dashboard_data.py` |
| `scripts/supervised/` | Huấn luyện hồi quy & phân loại đối chứng theo bài giảng (Ridge, RF, Logistic, NB, KNN, SVM, DT) | `predict_supervised.py`, `course_supervised_baselines.py`, `classifier_label_baselines.py`, `supervised_depth.py` |
| `scripts/figures/` | Sinh hình ảnh minh họa chất lượng cao cho báo cáo, dự báo lưới & ảnh bìa repo | `fig_grid_levels_and_elbow.py`, `forecast_papi_grid.py`, `build_banner.py` |
| `scripts/notebooks/` | Sinh lập trình tất cả notebook nộp bài, thử nghiệm và ôn tập Day 6 / Day 9 | `gen_submission_demo.py`, `gen_final_analysis.py`, `gen_study_day6_regressions.py`, `gen_study_day9_kmeans_hc.py`, `gen_synthetic_check.py`, `gen_params_sweep.py`, `gen_midterm_demo.py` |
| `scripts/deliverables/` | Đóng gói báo cáo DOCX, slide PPTX, 2 ZIP nộp bài, kiểm tra nguồn Q&A & smoke test | `build_report.py`, `build_slides_10.py`, `build_slides.py`, `build_submission_packages.py`, `check_qa_sources.py`, `demo_smoke.py`, `render_check.py`, `update_report_fields.py` |
| `scripts/common/` | Module tiện ích dùng chung (style hình, sơ đồ STING/nhiễu 2D, dự báo lưới, kiểm tra notebook) | `fig_style.py`, `midterm_clustering.py`, `papi_pred_common.py`, `papi_forecast.py`, `notebook_checks.py` |
