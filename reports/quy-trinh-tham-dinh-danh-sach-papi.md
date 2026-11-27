# Thẩm định độc lập danh sách rà soát PAPI

Đây là hướng dẫn sử dụng phiếu trống, chưa có đánh giá của chuyên viên. Không dùng điểm PAPI 6.1, nhãn STING hoặc vị trí trong danh sách để tự xác nhận nhu cầu rà soát.

Lượt mẫu 2024 đã chuẩn bị sẵn phiếu trống tại `plans/papi-review-round-1/for-reviewers/cases.csv`: 16 ca gồm 11 ca thuộc ít nhất một phương pháp và 5 ca ngoài hợp danh sách. Chưa có chuyên viên chấm. Nếu tạo lại, dùng thư mục mới để không ghi đè lượt cũ.

1. Điều phối viên tạo phiếu bằng `python -X utf8 -m scripts.analysis.review_shortlist_backtest --review-dir plans/papi-review-round-2`. Không chạy lệnh nếu chỉ đang sử dụng lượt mẫu đã có. Chỉ gửi `for-reviewers/cases.csv` cho người rà; giữ `restricted/selection_key.csv` và các bảng xếp hạng nội bộ. Mỗi dòng phiếu là một tỉnh–năm, tỉnh có thể thuộc nhiều danh sách; chỉ rà một lần mỗi người.
2. Hai chuyên viên đọc độc lập theo cùng thời lượng và cùng nguồn tại địa phương. Không gửi họ phiếu STING, điểm/xếp hạng PAPI hoặc khóa tuyển mẫu cho lượt chấm này. Đối chiếu bằng chứng cùng thời kỳ: chẳng hạn phản hồi dịch vụ hoặc chỉ tiêu vận hành có nguồn, mốc thời gian và phạm vi rõ. Ghi mã tham chiếu tài liệu, không đưa dữ liệu cá nhân vào phiếu.
3. Điền `outcome`: `confirmed` nếu bằng chứng độc lập đủ để mở đầu việc rà soát 6.1 cụ thể; `not_confirmed` nếu nguồn đủ để xem xét nhưng không ủng hộ việc mở đầu việc; `insufficient_evidence` nếu thiếu nguồn hoặc nguồn không so sánh được. Điền `evidence_ref` và `rationale` cùng với kết luận. Lưu cả hai bản riêng trước khi giải quyết bất đồng; chưa mở khóa danh sách.
4. Sau khi chốt nhận định, điều phối viên ghép `case_id` với khóa nội bộ. Với mỗi phương pháp, báo số xác nhận, không xác nhận và thiếu bằng chứng trên đúng 5 ca đã chọn; không bỏ ca thiếu để làm đẹp mẫu số. Báo mức đồng thuận hai chuyên viên trước khi hòa giải. Phần lấy mẫu ngoài hợp ba danh sách chỉ dùng để phát hiện ví dụ bỏ sót, không ước lượng recall cho cả 61 tỉnh. Nếu thấy khác biệt, mô tả số ca và độ phủ hồ sơ trước khi diễn giải lợi thế.

Lưu bộ phiếu đã điền tại nơi kiểm soát quyền truy cập, không đưa vào Git hoặc ZIP học phần. Hai nhóm vai trò có thể đối chiếu [quy trình ứng dụng](ung-dung-va-phat-trien-sting-papi.md) sau khi khóa kết luận.
