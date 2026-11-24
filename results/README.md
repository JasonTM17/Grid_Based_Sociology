# Kết quả Thực nghiệm & Hình minh họa (`results/`)

Toàn bộ bảng số liệu và hình ảnh trong báo cáo/slide được sinh tự động từ các script trong `scripts/`.

Mở [Bảng kết quả STING–PAPI trong Excel](KetQua_STING_PAPI.xlsx) để xem 23 bảng CSV đã được trình bày theo cột. Trang **Mục lục** dẫn đến từng bảng và ghi tên tệp nguồn. Bản Excel hiển thị dữ liệu tại thời điểm xuất.

## Nhóm kết quả chính

| Nhóm | Tệp tiêu biểu | Nội dung |
|---|---|---|
| Phân cụm STING & tổng hợp | `metrics.csv`, `per_year.csv`, `cluster_labels.csv`, `cluster_profile.{csv,md}`, `robustness.csv`, `analysis_summary.md` | Nhãn cụm 63 tỉnh (2011–2024), hồ sơ cụm, đối chiếu K-Means/DBSCAN & kiểm tra OFAT |
| Gán cụm & dự báo PAPI 2024 | `predict_config_search.csv`, `predict_all_years.csv`, `predict_summary.md`, `papi_observed_grid_2024.csv`, `papi_forecast_2024.json`, `papi_forecast_cv.csv`, `papi_forecast_provinces_2024.csv` | Tìm cấu hình train-only, gán quan sát 2024 (`48` cụm lớn / `13` ô thưa) và dự báo Ridge/xếp hạng rủi ro |
| Tiền xử lý & độ nhạy | `preprocessing_audit.{csv,md}`, `preprocessing_sensitivity.{csv,md}`, `protocol_sensitivity.{csv,md}` | Kiểm tra tiền xử lý và căn cứ chọn cách xử lý, độ nhạy giữ/loại outlier và cấu hình |
| Mô hình có giám sát | `supervised_metrics.csv`, `supervised_summary.md`, `supervised_depth.{csv,md}`, `course_supervised_baselines.{csv,md}`, `course_supervised_sensitivity.csv`, `classifier_label_baselines.{csv,md}` | Ridge/RF hồi quy `6.1`, Logistic & 6 classifier học phần (NB, KNN, SVM, DT, RF) |
| Kiểm chứng bên ngoài | `external_validation.{csv,md}`, `external_master_summary.md`, `poverty_validation.{csv,md}` | Đối chiếu ANOVA/Kruskal–Wallis cụm STING với PCI, nghèo GSO V14.47, GRDP & y tế |
| Khảo sát ứng viên | `model_improvement_candidates.md`, `candidates_clustering.{csv,md}`, `candidates_regression.{csv,md}`, `candidates_classification.{csv,md}` | Kết quả thử nghiệm tham khảo các ứng viên mở rộng mô hình |

## Biểu đồ đã xuất (`results/figs/`)

Chứa 24 tệp `.png` phục vụ báo cáo Word, slide thuyết trình và dashboard (`00_synthetic_sting.png`, `evolution.png`, `map_2020.png`, `map_2024.png`, `predict_2024.png`, `papi_forecast_*.png`, `external_*.png`, `course_confusion_matrix.png`, `supervised_*.png`, ...).
