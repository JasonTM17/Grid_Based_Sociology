# Nhật ký Rehearsal giữa kỳ — Topic 6 · STING × PAPI

_Cập nhật: 2026-11-04 · Owner rehearsal: A + B · Freeze gói nộp: 2026-11-20 (≥3 ngày trước 24/11)._

## A. Dry-run thời gian (AI/từng cá nhân tự chạy — đã đo)

- Notebook demo `notebooks/midterm_demo.ipynb`: **execute sạch ~18 giây** (đo bằng `nbconvert --execute`), yêu cầu ≤ 5' ⇒ dòng thông qua.
- Slide `slides/midterm.pptx`: 15 trang; kịch bản thời gian (tổng ≈ 14–15'):

| # | Slide | Phút | Người nói |
|---|---|---|---|
| 1 | Bìa — thesis | 0:45 | B |
| 2 | Vì sao grid-based? | 1:00 | A |
| 3 | STING trong 3 bước | 1:30 | A |
| 4 | Dữ liệu PAPI & audit thang đo | 1:30 | B |
| 5 | Demo synthetic (ARI 0.95) | 1:00 | A |
| 6 | Kết quả thật: đồng nhất | 1:30 | A |
| 7 | Pipeline dự đoán (2 model) | 1:30 | A |
| 8 | Kết quả 2024 (48 cụm lớn / 13 nhiễu) | 1:30 | A |
| 9 | Ridge vs carry-forward | 1:15 | A |
| 10 | So sánh baselines | 1:15 | A |
| 11 | Bản đồ 63 tỉnh | 1:00 | B |
| 12 | Hạn chế trung thực | 1:00 | B |
| 13 | Lộ trình cuối kỳ | 0:45 | B |
| 14 | Nguồn dữ liệu | 0:30 | B |
| 15 | Q&A | — | Cả hai |
| Tổng | | **≈ 14–15'** | |

- Q&A: 12 câu chuẩn bị (`reports/qa_midterm.md`) — mỗi thành viên phải trả lời được cả 12.

## B. Chưa làm (cần nhóm — không thể thay thế)

- [ ] **Rehearsal live**: 2 người đứng bấm giờ 15' + phản biện 5' (đề xuất 2 buổi: 07/11 và 14/11); ghi mốc thời gian thực tế vào bảng A.
- [ ] **Phản biện bất ngờ**: một người đóng vai "GV khó tính" với 3 câu ngoài bộ chuẩn bị.
- [ ] **Feedback**: sau khi đã trình bày (24/11–01/12) → `reports/midterm_feedback.md` (Phase 4 bước 1).
- [ ] **Freeze 20/11**: tag commit `v0.1-midterm` (chờ rehearsal đạt).

## C. Tiêu chí freeze đạt

- Notebook execute sạch trên kernel mới ✓ (18s).
- Slides ≤ 15 trang, tiếng Việt, đủ mục ✓ (15 trang; nội dung theo outline `phase-03`).
- `qa_midterm.md` ≥ 10 câu ✓ (12 câu).
- Live rehearsal ≤ 15' + Q&A ≤ 5' ⏳ — **bằng chứng duy nhất còn thiếu** (cần 2 người).

## Bộ 10 slide nộp bài — thời gian đề xuất (chưa rehearsal)

Bảng trên là kế hoạch rehearsal cho deck mở rộng `slides/final.pptx` (16 slide, phụ lục). Deck nộp bài là `slides/submission.pptx` (10 slide); phân bổ phút dưới đây chỉ là đề xuất, người nói chưa được phân công.

| # | Slide | Phút | Người nói |
|---|---|---|---|
| 1 | Bìa — thesis | 0:30 | chưa phân công |
| 2 | Bài toán & dữ liệu | 1:30 | chưa phân công |
| 3 | Lý thuyết STING (1/2): lưới phân cấp | 1:30 | chưa phân công |
| 4 | Lý thuyết STING (2/2): gom cụm, độ phức tạp | 1:30 | chưa phân công |
| 5 | Ví dụ minh họa (synthetic, ARI 0.95) | 2:00 | chưa phân công |
| 6 | Ứng dụng PAPI | 2:30 | chưa phân công |
| 7 | Đánh giá | 2:00 | chưa phân công |
| 8 | Kiểm chứng ngoài và hạn chế | 1:30 | chưa phân công |
| 9 | Kết luận | 1:00 | chưa phân công |
| 10 | TLTK / Q&A | 1:00 | chưa phân công |
| Tổng | | **≈ 15'** | |
