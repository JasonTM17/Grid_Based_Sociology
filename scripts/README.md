# Hệ thống Mã nguồn Pipeline (`scripts/`)

Tất cả script được chạy từ thư mục gốc dự án (ví dụ: `python scripts/data/check_data.py`).

| Thư mục | Vai trò | Tệp tiêu biểu |
|---|---|---|
| `scripts/data/` | Dựng panel PAPI, metadata thang đo, đối chiếu Mendeley, kiểm tra tiền xử lý & nạp nguồn ngoại lai | `build_panel.py`, `build_scale_metadata.py`, `build_external_master.py`, `check_data.py`, `crosscheck_mendeley.py`, `preprocessing_audit.py`, `preprocessing_sensitivity.py` |
| `scripts/analysis/` | Chạy STING theo cấu hình chốt, quét tham số, kiểm chứng PCI/nghèo, thống kê bàn giao 63 tỉnh, hồi kiểm rà soát, thực nghiệm hướng phát triển, STING đa chiều & suy luận bảng CR1/FDR | `first_real_cluster.py`, `predict_sweep.py`, `predict_demo.py`, `run_analysis.py`, `cluster_profile.py`, `protocol_sensitivity.py`, `external_validation.py`, `poverty_validation.py`, `stakeholder_summary.py`, `client_product.py`, `dashboard_data.py`, `review_shortlist_backtest.py`, `future_work.py`, `high_dim_sting.py`, `panel_inference.py` |
| `scripts/supervised/` | Huấn luyện hồi quy & phân loại đối chứng theo bài giảng (Ridge, RF, Logistic, NB, KNN, SVM, DT) | `predict_supervised.py`, `course_supervised_baselines.py`, `classifier_label_baselines.py`, `supervised_depth.py` |
| `scripts/figures/` | Sinh hình ảnh minh họa chất lượng cao cho báo cáo, dự báo lưới & ảnh bìa repo | `fig_grid_levels_and_elbow.py`, `forecast_papi_grid.py`, `build_banner.py` |
| `scripts/notebooks/` | Tạo bộ đôi notebook nộp bài thống nhất (từ giữa kỳ đến cuối kỳ) | `gen_preprocessing_notebook.py`, `gen_final_analysis.py` |
| `scripts/deliverables/` | Đóng gói báo cáo DOCX, slide PPTX 15 trang, ZIP nộp bài thống nhất, kiểm tra render/nguồn Q&A & smoke test | `build_report.py`, `report_style.py`, `slides_author.py`, `build_slides.py`, `build_slides.mjs`, `slides_chart_workbooks.py`, `slides_portable.py`, `build_submission_packages.py`, `check_qa_sources.py`, `demo_smoke.py`, `render_check.py`, `update_report_fields.py` |
| `scripts/common/` | Module tiện ích dùng chung (style hình, sơ đồ STING/nhiễu 2D, dự báo lưới, kiểm tra notebook) | `fig_style.py`, `midterm_clustering.py`, `papi_pred_common.py`, `papi_forecast.py`, `notebook_checks.py` |
