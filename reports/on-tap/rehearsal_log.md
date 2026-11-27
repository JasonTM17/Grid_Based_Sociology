# Nhật ký luyện thuyết trình thống nhất (12 slide)

Bộ trình chiếu thống nhất hiện nằm trong `slides/Nhom15_STING_PAPI.pptx` (đồng bộ tại `submissions/Nhom15_STING_PAPI/`). Phân bổ 15 phút ở [kịch bản thuyết trình](presentation_script.md). Bảng dưới dùng để ghi thời gian đo trực tiếp khi nhóm tập vấn đáp cuối kỳ.

## A. Kiểm tra kỹ thuật trước khi luyện thuyết trình

Hai lệnh dưới đây kiểm tra các tệp bàn giao và chạy lại notebook từ gói nộp. Kết quả thực thi được lưu trong `submissions/verification.json` và các lượt chạy GitHub Actions. Thời gian luyện thuyết trình thực tế của nhóm được ghi ở mục B khi nhóm tập.

Kiểm tra toàn bộ tệp nộp, slide, báo cáo và notebook hiện tại chạy bằng `python scripts/deliverables/demo_smoke.py` và `python scripts/deliverables/build_submission_packages.py --verify` từ thư mục dự án.

## B. Ghi khi nhóm tập

| Ngày tập | Người tham gia | Thời gian trình bày | Thời gian hỏi đáp | Phần cần rút gọn hoặc giải thích lại |
|---|---|---|---|---|
| | | | | |
| | | | | |

| Slide hoặc câu hỏi | Người phụ trách | Điều cần sửa | Kết quả sau khi tập lại |
|---|---|---|---|
| | | | |

## C. Tự đối chiếu sau mỗi lượt

- Nhóm giải thích mạch lạc Grid-based clustering, STING (`3×3` & `240` điểm giả lập), tiền xử lý 6 bước PAPI (`882×41`) và ý nghĩa nhãn nhiễu `−1` (slide 2–6).
- Trình bày rõ **thống kê bàn giao 63 tỉnh cho khách hàng** (slide 6–7: 4 nhóm mô tả, 5 tỉnh giữ nhãn 14/14 năm trên cùng lưới và 7 tỉnh rời Cụm 2). Nêu rõ các nhóm là gợi ý rà soát, chưa xác nhận chất lượng hay nguyên nhân.
- Giải thích được dự báo bổ trợ (AUC hồi cứu thăm dò `0,816`, chưa phải xác suất được hiệu chỉnh), đối chiếu với nguồn ngoài (PCI, GRDP, y tế ODM, nghèo GSO) và giới hạn độ bền đa chiều (slide 8–10).
- Thời lượng bài nói 12 slide nằm trong 15 phút, dành 5 phút cho hỏi đáp.
- Mỗi thành viên trả lời được bộ câu hỏi bảo vệ cuối kỳ trong [qa_final.md](qa_final.md), [qa_course_concepts.md](qa_course_concepts.md) và [qa_midterm.md](qa_midterm.md).

Ghi câu hỏi yếu và biên bản luyện tập bảo vệ cuối kỳ vào [mock_defense_log.md](mock_defense_log.md) (ghi nhận phản hồi giữa kỳ đã xử lý lưu đối chiếu tại [midterm_feedback.md](midterm_feedback.md)).
