# Bàn giao phân tích STING × PAPI 2024

**Dành cho:** đơn vị quản lý hoặc tư vấn cải cách hành chính công.  
**Mục đích:** chọn địa phương để đối sánh, rà soát sâu hoặc bổ sung dữ liệu; không xếp hạng chất lượng chính quyền hay y tế.

Cách cài đặt, lọc tỉnh, xuất CSV/phiếu và ý nghĩa từng cột được trình bày trong [Hướng dẫn sử dụng](customer_guide.md).

## 1. Kết quả để lựa chọn ca rà soát

Bảng phân tích gồm 882 dòng tỉnh–năm, 41 cột, giai đoạn 2011–2024. Báo cáo dùng 63 đơn vị cấp tỉnh theo phạm vi dữ liệu lịch sử. Năm 2024, 61/63 tỉnh có đủ hai chỉ tiêu: **4.2 — Kiểm soát tham nhũng trong cung ứng dịch vụ công** và **6.1 — Y tế công lập**. Đặt điểm đã quan sát năm 2024 lên lưới STING dựng đến năm 2023 cho kết quả 48/61 tỉnh trong vùng dày (78,7%) và 13/61 tỉnh trong ô thưa (21,3%).

| Nhóm mô tả và gợi ý rà soát | Số tỉnh (% trên 63) | Trung vị 4.2 | Trung vị 6.1 | Việc đề xuất |
|---|---:|---:|---:|---|
| Trong vùng dày (Cụm 2) | 48 (76,2%) | 2,032 | 1,963 | Duy trì theo dõi; chọn tỉnh tham chiếu có bối cảnh tương đồng. |
| Ngoài vùng dày phía điểm cao | 8 (12,7%) | 2,235 | 1,963 | Chọn ca đối sánh theo chỉ tiêu 4.2; kiểm tra tính phù hợp trước khi đề xuất áp dụng kinh nghiệm. |
| Ngoài vùng dày và 6.1 thấp theo quy tắc rà soát | 5 (7,9%) | 2,050 | 1,787 | Rà soát từng thành phần của chỉ tiêu 6.1 bằng dữ liệu và phản hồi tại địa phương. |
| Thiếu dữ liệu 2024 | 2 (3,2%) | — | — | Xác minh dữ liệu nguồn; chưa xếp nhóm theo kết quả quan sát. |

Các CSV nguồn giữ tên nhóm lịch sử ở cột `action_group` để tái lập. Sheet Excel **Thống kê khách hàng 2024**, dashboard, CSV tải từ dashboard và phiếu HTML dùng tên mô tả như bảng trên. Các tên hiển thị dẫn về cùng nhãn lưới và số liệu theo tỉnh.

Mốc đối sánh là trung vị của 48 tỉnh vùng lõi; ngưỡng rà soát 6.1 là **1,8791** (`Q25 − 0,5 × IQR` của vùng lõi). Đây là quy tắc mô tả nội bộ, không phải chuẩn quốc gia hoặc ngưỡng có ý nghĩa thống kê. Nhãn kỹ thuật `−1` chỉ ô thưa: 8 tỉnh ngoài vùng dày phía điểm cao và 5 tỉnh có 6.1 thấp đều nhận nhãn này, nhưng cần các hành động khác nhau.

## 2. Những trường hợp cần rà soát

- **Rà soát 6.1 trước:** Hà Nội (1,686), Cần Thơ (1,698), Gia Lai (1,787), Long An (1,807) và Bình Dương (1,808). Trung vị GRDP/người 2024 của nhóm là 104,26 triệu đồng so với 80,97 triệu đồng ở vùng lõi; đây là so sánh mô tả, không chứng minh quá tải hay quan hệ nhân quả.
- **Theo dõi trong vùng lõi:** có thêm 7 tỉnh thuộc Cụm 2 dưới ngưỡng 6.1. Đây là danh sách theo dõi, khác với 5 tỉnh ưu tiên ở ô thưa. Xem danh sách và tọa độ ô trong [bảng phân tích chi tiết](../results/stakeholder_summary.md).
- **Chọn điểm tham chiếu:** Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận và Vĩnh Long đều có đủ 14 năm và nằm trong Cụm 2 ở cả 14 năm trên cùng lưới dựng từ 2011–2023. Đây là mô tả hồi cứu của nhãn, chưa xác nhận ổn định điểm số hay chất lượng dịch vụ.
- **Đối soát dữ liệu thiếu:** Vĩnh Phúc và Tiền Giang không có đủ hai chỉ tiêu quan sát cho năm 2024. Không dùng giá trị dự báo để thay vào bảng phân nhóm quan sát.
- **Theo dõi dịch chuyển 2023→2024:** 43 tỉnh giữ Cụm 2, 5 tỉnh vào Cụm 2 và 7 tỉnh rời Cụm 2. Trong 7 tỉnh rời cụm, 5 chuyển ra nhóm ngoài vùng dày phía điểm cao, 2 chuyển xuống rìa ưu tiên 6.1. Rời cụm không mặc nhiên là suy giảm.

**Ví dụ Hà Nội.** Ô `(10, 5)` có 3 điểm tham chiếu, dưới ngưỡng 5 của STING nên nhận nhãn `−1`. Điểm 6.1 là 1,686, dưới mốc rà soát nội bộ 1,8791. Người nhận có thể dùng phiếu để đối chiếu các thành phần của 6.1 với dữ liệu địa phương.

## 3. Giới hạn của thí nghiệm dự báo

Thí nghiệm dùng dữ liệu đến 2023 để dự báo **năm 2024**, không dự báo sau năm 2024. Có 61 dự báo, trong đó 59 tỉnh đối chiếu được với quan sát thực tế.

| Điểm dự báo (59 tỉnh đối chiếu) | MAE Ridge | MAE giữ nguyên điểm 2023 | RMSE Ridge | RMSE giữ nguyên điểm 2023 |
|---|---:|---:|---:|---:|
| 4.2 | 0,0736 | 0,0763 | 0,0972 | 0,0953 |
| 6.1 | 0,0641 | 0,0683 | 0,0770 | 0,0875 |

Dự báo điểm nhận ra **0/11** tỉnh thực tế ngoài vùng dày trong 59 tỉnh đối chiếu. Tỉ lệ kịch bản ngoài vùng dùng 364 cặp phần dư lịch sử, đạt **AUC thăm dò 0,816** trên một kỳ hồi kiểm. Dùng chỉ số này để đọc thứ hạng trong thí nghiệm, **không** đọc như xác suất đã hiệu chỉnh, cảnh báo hiện tại hay căn cứ tự động cho phân bổ nguồn lực. Tương tự, các bộ phân loại học phần đo độ khớp với nhãn do STING sinh, không đo độ đúng của một phân loại xã hội độc lập.

## 4. Tệp nhận bàn giao và cách kiểm tra

| Việc cần làm | Tệp hoặc công cụ |
|---|---|
| Lọc 63 tỉnh và chọn nhóm mô tả | [CSV cấp tỉnh](../results/stakeholder_province_summary_2024.csv) hoặc sheet **Thống kê khách hàng 2024** trong [Excel](../results/KetQua_STING_PAPI.xlsx). |
| Xem mốc đối sánh, dịch chuyển, danh sách chi tiết và hình | [Bảng phân tích](../results/stakeholder_summary.md), [biểu đồ](../results/figs/stakeholder_quadrants_2024.png), [dự báo theo tỉnh](../results/papi_forecast_provinces_2024.csv). |
| Xuất Phiếu rà soát tỉnh | Vào tab **Thống kê khách hàng**, tải phiếu HTML và in một trang A4. [Hướng dẫn sử dụng](customer_guide.md) |
| Xem phương pháp, báo cáo và cách chạy lại | Mở `Nhom15_BaoCao_STING_PAPI.docx`, `Nhom15_STING_PAPI.pptx` và `HUONG_DAN.txt` ở cấp đầu gói ZIP. Trong kho mã nguồn, xem bảng đường dẫn tương ứng tại [hướng dẫn sử dụng](customer_guide.md). |

## 5. Nghiệm thu trước khi gửi

| Người kiểm tra | Tiêu chí | Bằng chứng cần giữ |
|---|---|---|
| Đầu mối dữ liệu | CSV và Excel đủ 63 mã tỉnh không trùng; hai tỉnh thiếu quan sát vẫn có dòng và không dùng dự báo để điền. | Phiên bản CSV/XLSX và kết quả đếm theo mã tỉnh. |
| Đầu mối phân tích | Tên nhóm và số lượng khớp bảng trên; mở thử phiếu một tỉnh ưu tiên và một tỉnh thiếu dữ liệu; kiểm tra thời điểm của chỉ số kịch bản trên bảng, bản đồ và phiếu. | Biên bản đối chiếu, hai phiếu mẫu và danh sách sai lệch cần khắc phục (nếu có). |
| Chủ hồ sơ bàn giao | Phân biệt bộ gửi khách hàng với gói học phần; chỉ gửi tệp cần thiết sau khi có quyền chia sẻ dữ liệu, tài liệu nguồn và thông tin định danh. | Danh mục tệp và phiên bản, ghi nhận quyền chia sẻ và biên bản nghiệm thu. |

Chưa gửi khách hàng, chưa nộp LMS và chưa có xác nhận nghiệm thu từ bên nhận.
