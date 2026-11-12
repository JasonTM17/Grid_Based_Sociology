# Câu hỏi mở với giảng viên (theo plan.md §8)

_Cập nhật: 2026-11-12 · Địa chỉ hỏi: GV phụ trách môn (LMS/email lớp) · Hạn chốt logistics: chờ GV (xem câu 5–7)_

| # | Câu hỏi | Mặc định đang áp dụng | Trả lời | Ngày trả lời |
|---|---|---|---|---|
| 1 | Ngày giữa kỳ & cuối kỳ chính xác (LMS)? | Giữa kỳ 24/11–01/12; cuối kỳ ~01/2027; **freeze gói giữa kỳ 20/11** | ✅ user giữ mặc định (24/11–01/12) | 2026-11-04 |
| 2 | Nộp bằng Jupyter hay Zeppelin? | Jupyter (`python -m nbconvert` để execute) | ⏳ chưa | — |
| 3 | Có template báo cáo `.docx` của môn không? | Môn chưa có template riêng → tự soạn theo ghi chú định dạng đã chắt lọc từ tài liệu mẫu của nhóm (`report_format_notes.md`) | ✅ user gợi ý lấy mẫu trong OneDrive; đã khảo sát xong | 2026-11-04 |
| 4 | Nhóm 1 hay 2 người? | **2 người** — Nguyễn Tiến Sơn (24110054), Trần Thị Ngọc Quyên (24110051); **Nhóm 15**; kế hoạch đầy đủ, không cut-lines | ✅ user xác nhận | 2026-11-04 |
| 5 | Định dạng nộp: tên file, cấu trúc thư mục/zip, nơi nộp? | Đề xuất: `Nhom<mã>_HocMay_Topic6_STING_GiuaKy/` gồm slides + notebook; chốt khi GV/LMS phản hồi | ⏳ chưa | — |
| 6 | Trọng số rubric **cuối kỳ** (preprocessing, model learning, evaluation, code, report, oral)? | Text trích PDF bài giảng bị garbled — **chỉ liệt kê được tên hạng mục**, không đọc được điểm; xem `reports/course_requirements.md` | ⏳ chưa — cần xác nhận trực quan slide/PDF hoặc GV | — |
| 7 | Báo cáo cuối: bắt buộc **3 chương** (mẫu `Report-proj.docx`) hay chấp nhận **7 chương** hiện tại (`reports/final_report.docx`)? | Giữ 7 chương + bìa/Lời cảm ơn theo mẫu quan sát; skeleton 3 chương ghi trong `course_requirements.md` | ⏳ chưa | — |

**Ghi chú:** câu 2, 5–7 chờ GV; khi hết hạn tự đặt vẫn áp dụng mặc định ở cột giữa và ghi ngày quyết định.

---

## CẬP NHẬT 2026-11-07 (vòng hoàn thiện cuối)

Bảng câu hỏi logistics ở trên **giữ nguyên, không xóa** (câu 2 và câu 5 vẫn ⏳ chờ GV). Riêng các câu hỏi/khoảng trống **kỹ thuật** đã được giải quyết trong các phiên hoàn thiện ngày 2026-11-07 — không có số kết quả đã công bố nào bị đổi; gate chạy lại trong phiên cập nhật này: `python -E -m pytest tests -q` → **67 passed** (exit 0), `python -m ruff check .` → **All checks passed!**.

| Câu hỏi / khoảng trống | Kết quả | Bằng chứng |
|---|---|---|
| Cụm STING có nghĩa ngoài thang đo PAPI không? (external validation) | Đã giải quyết — kiểm định chính: PCI (VCCI–USAID) theo nhãn cụm của model đóng băng trên lưới đầy 2011–2022 (756 ô có điểm, join được 747 điểm, 9 ô có PCI nhưng panel thiếu sd_4_2/sd_6_1 nên không có nhãn): One-way ANOVA F(3,743) = 9.04 (p = 6.9e-06), Kruskal–Wallis H = 31.78 (p = 5.8e-07), eta² = 0.0352 | `results/external_validation.md`; `data/processed/external_master_63_2011_2024.csv`; `reports/external_data_expansion.md` §4.2 mục [2] |
| B2 — baseline hồi quy có chạy cùng giao thức CV không? (audit model stability) | Đã áp — `value_cv` thật cho 2 baseline trên cùng fold expanding 2017–2022: carry-forward **0.145**, trung bình train **−0.77**, cạnh ridge **0.265** (kết luận chọn ridge không đổi) | `results/supervised_metrics.csv` (cột `value_cv`); `plans/model_stability_audit.md` mục 6 (B2) |
| B3 — độ nhạy min_count đo ở mức nhãn chứ không chỉ coverage? | Đã áp — bảng min_count {3, 5, 8} thêm **ARI vs cấu hình chốt (2024)** (0.852 / 1.000 / 0.678) và **số tỉnh đổi cụm↔nhiễu** (2 / 0 / 5); kèm lưu ý hoán vị nhãn (exact agreement mc=3 vs mc=5 chỉ 18%) | `results/predict_summary.md` mục "Độ nhạy coverage theo min_count" |
| B4 — nhánh robustness 8 chiều confounded (đổi 3 tham số cùng lúc)? | Đã áp — OFAT đổi một tham số mỗi lần từ cấu hình gốc (L=3 f=2 mc=10 lv=1): f=3 → k=1/nhiễu 91.9%; lv=2 → k=0/100% nhiễu; mc=2 → k=2/nhiễu 10.9% nhưng silhouette −0.089 (âm — tách yếu) | `results/robustness.csv` (các dòng OFAT) |
| Provenance GSO/ODM đã đủ chưa? | Đã cập nhật — **GSO:** thêm bảng pxweb **V14.47** "Tỷ lệ hộ nghèo phân theo địa phương" (146.373 bytes, SHA-256 `3e652b6b…7183bd` — đã tính lại độc lập trong phiên này) + URL gốc + trích nguyên văn chú thích + manifest; **ODM:** `_search_poverty_vn.json` tải lại đủ **61/61** kết quả (`rows=61`, SHA-256 `1d824ad8…960f2d`) — không có dataset poverty cấp tỉnh nào mới, kết luận cũ không đổi | `data/raw/gso/PROVENANCE.md`; `data/raw/odmekong/PROVENANCE.md` |
| "Vì sao không có nghèo cấp tỉnh?" (gap [7] của `reports/external_data_expansion.md`) | Đã giải quyết qua nguồn khác ODM — tìm thấy trên **pxweb GSO** (đúng cơ chế tải của repo): ma trận V14.47 → `data/processed/external_poverty_63.csv`: 63 tỉnh × 14 năm (2006, 2008, 2010, 2012–2016, 2020–2025), **881/882 ô có số** (thiếu duy nhất TP.HCM 2016 — nguồn ghi ".."); 2017–2019 bảng nguồn không có → để trống, **KHÔNG nội suy**; đối chiếu trong script (dung sai 0,051): Niên giám 2025 **315/315** trùng, Niên giám 2021 **124/124** trùng | `data/processed/external_poverty_63.csv`; `scripts/build_poverty_63.py`; `data/raw/gso/pxweb_V14.47_poverty_step2.html`; `reports/external_data_expansion.md` §3.6 |
| Dashboard có hiển thị kiểm chứng ngoại lai không? | Có — tab mới **"Kiểm chứng ngoại lai"**: 4 metric lưới PCI (756 / 747 / 9 / 4), box plot PCI theo cụm, ANOVA/Kruskal/eta² tính lại bằng scipy trên chính dữ liệu hiển thị rồi tự đối chiếu `results/external_validation.csv` (lệch quá sai số làm tròn → tab dừng, không hiện số khác số đã công bố); kèm kiểm tra phụ Top-30 2023–2024, mật độ y tế 2020, GRDP 2018–2024 | `app.py:193` (đăng ký tab), `app.py:448` (nội dung), `scripts/dashboard_data.py:525` (khâu tự đối chiếu); `tests/test_dashboard_data.py` |

Còn mở sau vòng này: câu 2 và câu 5 của bảng logistics (chờ GV); **B5** (`predict_sweep`) chờ người hướng dẫn duyệt — ngoài phạm vi vòng này; `external_poverty_63.csv` **chưa nối** vào `external_master` (ngoài phạm vi yêu cầu) — dùng làm feature/validation hay chỉ bối cảnh là quyết định của nhóm.

---

## CẬP NHẬT 2026-11-08 (nghèo cấp tỉnh đã vào đầy đủ asset)

Không có câu hỏi logistics mới; bảng ở trên **giữ nguyên** (câu 2 và câu 5 vẫn ⏳ chờ GV). Mục này chốt trạng thái tích hợp của **nghèo cấp tỉnh GSO V14.47** (kiểm chứng bổ trợ thứ hai sau PCI): đã vào **đầy đủ asset** — script kiểm định, results (md + csv + hình), dashboard, tests, báo cáo, notebook, tài liệu nguồn. **Không có số kết quả đã công bố nào bị đổi** (PCI F = 9.04 / H = 31.78, ridge 0.265, carry 0.145 — giữ nguyên; poverty là bổ sung). Gate chạy trong phiên này (từ thư mục gốc repo): `python -E -m pytest tests -q` → **101 passed** (exit 0), `python -m ruff check .` → **All checks passed!**; rebuild `python -E scripts/poverty_validation.py` → `results/poverty_validation.md`/`.csv`/hình **byte-giống** trước–sau (sha256, diff rỗng).

| Asset | Trạng thái | Bằng chứng |
|---|---|---|
| Script kiểm định | Có — tái dùng helper `external_validation.py`, hình dùng `scripts/fig_style.py`, cửa sổ giao 2012–2016 & 2020–2024 assert khớp thiết kế | `scripts/poverty_validation.py:63-83` |
| Results (md + csv) | Có — mọi số tự tính từ CSV provenance, không hardcode, không nội suy (TP.HCM 2016 thiếu phía nguồn); determinstic — rebuild 2026-11-08 byte-giống | `results/poverty_validation.md`; stdout phiên chạy: 630 ô cửa sổ / 629 có giá trị / 618 vào kiểm định / 11 ô không nhãn |
| Hình | Có — `results/figs/external_poverty_by_cluster.png` (boxplot gộp + median theo năm, 400 dpi) | `scripts/poverty_validation.py:80`, `:536` |
| Dashboard | Có — tab "Kiểm chứng ngoại lai", mục "Nghèo cấp tỉnh (GSO V14.47)": metrics cửa sổ, box plot, hai kiểm định tính live, cảnh báo "đọc CÙNG nhau" | `app.py:728`–`860`; `scripts/dashboard_data.py:674` (`load_poverty_assets`), `:700` (`prepare_poverty_cluster_view`) |
| Tests | Có — loader/schema, cửa sổ giao, bảng kiểm định hiển thị; test pin protocol trên artifact thật đối chiếu `results/poverty_validation.csv` đã công bố | `tests/test_dashboard_data.py` (ví dụ `test_poverty_protocol_recomputed_on_real_artifacts`); `tests/test_app_ui.py:185`–`436` |
| Báo cáo + notebook | Có — đọc cùng `results/poverty_validation.csv` (không hardcode số) | `scripts/build_report.py:74`–`82`; `scripts/gen_final_analysis.py:165`–`193` |
| Tài liệu nguồn | Có — `reports/external_data_expansion.md` §3.6 (nguồn + provenance) + mục mới §3.7 "Nghèo cấp tỉnh đã tích hợp" | `reports/external_data_expansion.md` |

Còn mở như cũ: câu 2 và câu 5 logistics (chờ GV); **B5** (`predict_sweep`) chờ người hướng dẫn duyệt; `external_poverty_63.csv` **vẫn chưa nối** vào `external_master` — dùng làm feature/validation hay chỉ bối cảnh là quyết định của nhóm.

---

## CẬP NHẬT 2026-11-12 (đối chiếu khóa học + README/DEMO)

Bảng logistics ở trên **giữ nguyên**; câu 2, 5, 6, 7 vẫn ⏳ chờ GV. Các mục kỹ thuật sau **đã đạt** (ngày 2026-11-12, worktree `docs/readme-and-requirements-course-alignment`):

| Mục | Trạng thái | Bằng chứng |
|---|---|---|
| Bìa `final_report.docx` (họ tên/MSSV) | Đã điền | `reports/submission_checklist.md` (mục deliverable + con người) |
| Audit tiền xử lý Day 4 | Có artifact + gate notebook | `results/preprocessing_audit.{md,csv}`; `scripts/preprocessing_audit.py`; `tests/test_preprocessing_audit.py`; `tests/test_submission_artifacts.py` |
| Classifier học phần + confusion | Có artifact + test | `results/course_supervised_baselines.{csv,md}`; `results/figs/course_confusion_matrix.png`; `tests/test_course_supervised_baselines.py` |
| Notebook gates (submission + final) | Pass | `tests/test_submission_artifacts.py`; `tests/test_final_notebook_artifacts.py` |
| Tài liệu README/DEMO/requirements | Cập nhật đối chiếu Day 1–4 | `README.md` (mục Đối chiếu); `DEMO.md`; `reports/course_requirements.md` |

Gate chạy cuối phiên (cwd repo): `python -m ruff check .`; `python -m pytest tests -q`; `python scripts/demo_smoke.py` — xem exit code trong summary worker.

Vẫn **chỉ con người:** rehearsal/mock defense; nộp LMS/zip; chốt deadline & format (câu 5); trọng số rubric cuối kỳ (câu 6); skeleton 3 vs 7 chương (câu 7).

---

## CẬP NHẬT 2026-11-08 (ma trận ứng viên cải thiện model)

**CẬP NHẬT 2026-11-08** — ma trận ứng viên cải thiện model đã chạy, verdict trong `results/model_improvement_candidates.md` (exploratory, adoption cần GV). Kết luận highlights đã chốt thành câu trả lời Q&A số 31 "Còn gì cải thiện được cho model?" trong `reports/qa_final.md`. Đợt này chỉ sửa 2 tệp tài liệu (`reports/open-questions.md`, `reports/qa_final.md`) — không đụng script/artifact, không đổi số đã công bố (Ridge 0.265, carry 0.145, LR 0.434, k=3 — giữ nguyên); ba ứng viên vượt ngưỡng (C3, C1, R1) đều còn nhãn [THAM KHẢO — CHƯA DUYỆT GV]. Gate trong phiên này (từ thư mục gốc repo): `python -E -m ruff check .` → **All checks passed!**; `git diff --name-only` trước khi ghi → rỗng, sau khi ghi → đúng 2 tệp reports/.
