# Hướng dẫn sử dụng bộ phân tích STING và PAPI

Tài liệu dành cho người nhận bộ phân tích, cần mở dữ liệu, chọn tỉnh để rà soát và xuất kết quả. Phạm vi là 63 đơn vị cấp tỉnh trong dữ liệu PAPI 2011–2024. Các nhóm do mô hình tạo hỗ trợ mô tả hai chỉ tiêu; chưa phải xếp hạng chất lượng chính quyền hay y tế.

Kết quả và các trường hợp cần đối chiếu được trình bày trong [Bàn giao phân tích năm 2024](ban-giao-khach-hang-2024.md). Hướng dẫn này tập trung vào thao tác sử dụng.

## 1. Chọn cách mở phù hợp

| Nhu cầu | Cách thực hiện |
|---|---|
| Chỉ đọc kết quả | Mở báo cáo Word, PowerPoint hoặc `results/KetQua_STING_PAPI.xlsx`; không cần cài Python. |
| Lọc tỉnh, xem bản đồ và tải phiếu | Chạy ứng dụng Streamlit theo mục 2. |
| Kiểm tra tệp nhận được | Chạy `scripts/deliverables/demo_smoke.py`; trong gói giải nén, lệnh đối chiếu thêm mã kiểm tra của các tệp. |
| Thực thi lại phân tích | Chạy hai notebook theo mục 6; cần môi trường Python đã cài đủ thư viện. |

Giữ nguyên cấu trúc thư mục sau khi giải nén `Nhom15_STING_PAPI.zip`. Không chỉ sao chép riêng `app.py`: ứng dụng cần các thư mục `data/`, `models/`, `results/`, `src/` và `scripts/` đi kèm.

| Tài liệu | Trong kho mã nguồn | Trong gói ZIP giải nén |
|---|---|---|
| Báo cáo | `reports/Nhom15_BaoCao_STING_PAPI.docx` | `Nhom15_BaoCao_STING_PAPI.docx` |
| Trình chiếu | `slides/Nhom15_STING_PAPI.pptx` | `Nhom15_STING_PAPI.pptx` |
| Notebook tiền xử lý | `notebooks/Nhom15_TienXuLy_PAPI.ipynb` | `Nhom15_TienXuLy_PAPI.ipynb` |
| Notebook phân tích | `notebooks/Nhom15_STING_PAPI.ipynb` | `Nhom15_STING_PAPI.ipynb` |
| Ứng dụng và dữ liệu | `app.py`, `data/`, `results/`, `models/` | Cùng đường dẫn tương đối |

## 2. Khởi động ứng dụng

Mở terminal tại thư mục chứa `app.py` và `requirements.txt`. Dự án dùng **Python 3.14**; `python --version` cần trả về phiên bản 3.14.x. Cài các phiên bản thư viện đã khóa trong tệp yêu cầu của chính bộ nhận được.

**Windows PowerShell**

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/deliverables/demo_smoke.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**Linux hoặc macOS**

```sh
python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python scripts/deliverables/demo_smoke.py
./.venv/bin/python -m streamlit run app.py
```

Mở địa chỉ `Local URL` do Streamlit in trong terminal, thường là `http://localhost:8501`. Giữ terminal đang chạy; nhấn `Ctrl+C` để dừng. Cần mạng để cài thư viện lần đầu. Sau khi cài xong, dữ liệu, mô hình và bản đồ ranh giới dùng trong ứng dụng nằm trong gói.

## 3. Đọc và xuất một trường hợp địa phương

1. Mở tab **Thống kê khách hàng**. Bốn thẻ và bảng tổng hợp phản ánh toàn bộ 63 tỉnh năm 2024, gồm 48 tỉnh trong vùng dày, 8 tỉnh ngoài vùng dày phía điểm cao, 5 tỉnh ngoài vùng dày có 6.1 thấp và 2 tỉnh thiếu dữ liệu.
2. Chọn tỉnh ở thanh bên hoặc chọn **Lọc theo nhóm mô tả** trong tab. Để trống bộ lọc để xem tất cả. Bộ lọc tỉnh và nhóm được kết hợp: nếu không có tỉnh khớp, ứng dụng báo danh sách rỗng và không xuất phiếu của tỉnh khác.
3. Xem bản đồ hoặc chuyển sang biểu đồ hai trục. Các đường phân vị là mốc đối sánh nội bộ. Các tỉnh thiếu điểm vẫn nằm trong danh sách và bản đồ hành chính; không đặt vào biểu đồ hai trục khi thiếu tọa độ.
4. Chuyển bảng chi tiết giữa **Phân nhóm & chỉ số chính**, **Khuyến nghị & dịch chuyển** và **Đầy đủ 10 cột**. Đối chiếu gợi ý rà soát với thông tin địa phương trước khi đề xuất can thiệp.
5. Chọn **Tải CSV bàn giao** để tải đúng các tỉnh đang lọc. CSV dùng UTF-8 có BOM để Excel đọc được tiếng Việt. Giá trị thiếu là ô trống; các cột số giữ giá trị để tiếp tục phân tích.
6. Chọn tỉnh ở mục **Phiếu rà soát tỉnh** và tải HTML. Phiếu ghi ô lưới, số điểm tham chiếu và lịch sử 14 năm. Mở bằng trình duyệt, chọn In, khổ A4 và lưu thành PDF. Bố cục in trình bày dữ liệu trên một trang A4.

Thẻ và bảng tổng hợp ở đầu tab luôn phản ánh 63 tỉnh. Bản đồ giữ đủ ranh giới để nhìn bối cảnh, làm mờ các tỉnh ngoài bộ lọc. Bảng chi tiết, CSV và danh sách chọn phiếu đi theo bộ lọc.

**Phạm vi bộ lọc:** năm và cụm ở thanh bên áp dụng cho **Tổng quan** và **STING theo năm**. Tab khách hàng luôn là năm 2024; chỉ nhận bộ lọc tỉnh từ thanh bên. Hồi quy giữ kỳ đối chiếu 2023→2024. Các bảng nguồn ngoài dùng cửa sổ thời gian ghi ngay tại từng phần.

## 4. Hiểu đúng nhóm và chỉ số

“Vùng dày” là các ô trên mặt phẳng hai chỉ tiêu có đủ quan sát tham chiếu, không phải vùng địa lý. Lưới chính dựng từ 808 quan sát trong 2011–2023, có 16×16 ô và ngưỡng 5 quan sát mỗi ô. Điểm thực đo năm 2024 được gán lên lưới này. Nhãn `−1` có thể gồm điểm cao hoặc thấp; không có nghĩa địa phương quản trị yếu kém.

| Trường CSV | Ý nghĩa và cách đọc |
|---|---|
| `province_code`, `province_vi` | Mã và tên tỉnh trong dữ liệu lịch sử; dùng mã để ghép dữ liệu. |
| `action_group`, `action_subtier` | Nhóm mô tả và phân nhóm chi tiết; không phải nhãn xã hội do chuyên gia xác nhận. |
| `sd_4_2`, `sd_6_1` | Hai điểm PAPI quan sát năm 2024: kiểm soát tham nhũng trong cung ứng dịch vụ công và y tế công lập. |
| `grid_cell`, `reference_count` | Tọa độ ô và số quan sát tham chiếu trong ô; số đếm không phải dân số tỉnh. |
| `years_cluster2_2011_2024` | Số năm được gán Cụm 2 trên cùng lưới tham chiếu; giữ nhãn chưa chứng minh điểm số hoặc chất lượng ổn định. |
| `years_noise_2011_2024` | Số năm nhận nhãn `−1`; không phải số năm tỉnh hoạt động kém. |
| `transition_2023_2024` | Dịch chuyển nhãn giữa hai năm có điểm quan sát. Rời Cụm 2 không mặc nhiên là suy giảm. |
| `risk_outside_scenario_share` | Tỉ lệ kịch bản sai số lịch sử đưa dự báo 2024 ra ngoài vùng dày, lưu theo thang 0–1; nhân 100 để biểu diễn phần trăm. Đây là thứ hạng thăm dò hồi cứu, chưa phải xác suất cảnh báo. |
| `grdp_2024_mil_vnd` | GRDP/người 2024, triệu đồng/người, số sơ bộ. |
| `pci_2022` | Điểm PCI năm 2022; không đọc như điểm của năm 2024. |
| `poverty_2024_pct` | Tỷ lệ hộ nghèo GSO 2024 theo phần trăm; không nhân 100 thêm lần nữa. |
| `client_recommendation` | Gợi ý đối chiếu hoặc rà soát, cần được xác minh bằng dữ liệu địa phương. |

Mốc rà soát `6.1 = 1,8791` tính từ `Q25 − 0,5×IQR` của 48 tỉnh trong vùng dày năm 2024. Mốc này được chọn hồi cứu, không phải chuẩn chất lượng quốc gia hay ngưỡng đã được kiểm chứng trước năm 2024. Năm tỉnh giữ nhãn Cụm 2 cả 14 năm là các ca tham chiếu để nghiên cứu thêm.

Giao diện, CSV tải từ giao diện, phiếu và sheet Excel **Thống kê khách hàng 2024** dùng tên mô tả. CSV nguồn giữ tên lịch sử để đối chiếu với mã nguồn.

| Tên trong tệp nguồn | Tên hiển thị cho người nhận |
|---|---|
| Biên bứt phá vượt chuẩn | Ngoài vùng dày phía điểm cao |
| Vùng lõi ổn định (Cụm 2) | Trong vùng dày (Cụm 2) |
| Ưu tiên cải thiện Y tế 6.1 | Ngoài vùng dày, 6.1 thấp |
| Thiếu dữ liệu 2024 | Thiếu dữ liệu 2024 |

Tên lưu trữ không xác nhận một chuẩn chất lượng hay hiệu quả quản lý. Các phép chuyển tên chỉ thay cách diễn đạt; số liệu, mã tỉnh, nhãn mô hình và cấu hình thực nghiệm được giữ nguyên.

## 5. Phân biệt các kết quả dự báo

Thí nghiệm dự báo hai chỉ tiêu chọn Ridge theo MAE ở các lượt kiểm định theo thời gian. Trên 59 tỉnh đối chiếu được năm 2024, MAE của Ridge thấp hơn cách giữ nguyên điểm 2023 ở cả hai chỉ tiêu, nhưng khi gán dự báo vào lưới, mô hình bỏ sót 11/11 tỉnh có quan sát ngoài vùng dày. AUC 0,816 của kịch bản sai số là kết quả thăm dò trên cùng kỳ hồi kiểm, chưa đánh giá khả năng cảnh báo cho một năm tương lai.

Tab **Hồi quy 2023 → 2024** trình bày nhánh chẩn đoán hồi quy chỉ tiêu 6.1 từ `results/supervised_metrics.csv`, chọn mô hình theo R² kiểm định. Nhánh này khác thí nghiệm dự báo hai chỉ tiêu trong `results/papi_forecast_2024.json`: khác cách chọn mô hình, tham số và điều kiện đủ dữ liệu. Vì vậy cần đọc tên bảng, chỉ tiêu, mẫu số và tiêu chí lựa chọn trước khi so sánh các con số. Các bộ phân loại trong phần học phần đo mức khớp với nhãn STING, không đo độ đúng của một nhãn xã hội độc lập.

## 6. Kiểm tra và chạy lại khi nhận bàn giao

`demo_smoke.py` kiểm tra tệp, cấu trúc và kết quả notebook đã lưu. Lệnh này không thực thi lại các ô mã. Để chạy lại, dùng môi trường đã cài ở mục 2, thay `python` dưới đây bằng đường dẫn Python trong `.venv` nếu chưa kích hoạt môi trường.

Từ thư mục gốc của gói ZIP giải nén:

```sh
python -m nbconvert --to notebook --execute Nhom15_TienXuLy_PAPI.ipynb --output TienXuLy_chay_lai
python -m nbconvert --to notebook --execute Nhom15_STING_PAPI.ipynb --output STING_PAPI_chay_lai
```

Trong kho mã nguồn đầy đủ, thêm `notebooks/` trước tên notebook đầu vào. Trong Jupyter hoặc VS Code, chọn kernel của cùng môi trường và dùng **Restart Kernel → Run All**. Tệp nguồn gồm 14 workbook PAPI gốc; dữ liệu thiếu không được điền bằng dự báo.

Khi nghiệm thu, thử lọc một tỉnh có điểm, một tỉnh thiếu dữ liệu và một bộ lọc không có kết quả. Đối chiếu điểm trên giao diện, CSV và phiếu HTML của cùng tỉnh. Kiểm tra 63 mã tỉnh không trùng; không tự đánh dấu đã nghiệm thu chỉ vì chương trình chạy được.

## 7. Xử lý tình huống thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Thiếu mô-đun hoặc API Streamlit | Kiểm tra Python 3.14 và cài lại đúng `requirements.txt` bằng Python trong `.venv`; khởi động Streamlit bằng cùng trình thông dịch. |
| Báo thiếu dữ liệu hoặc mô hình | Kiểm tra đang đứng tại thư mục chứa `app.py`, đã giải nén toàn bộ gói và giữ nguyên cấu trúc. |
| Cổng 8501 đang dùng | Dừng phiên cũ hoặc thêm `--server.port 8502` vào lệnh chạy Streamlit. |
| Số tỉnh ít hơn 63 | Xem bộ lọc tỉnh và nhóm; bảng tổng hợp toàn bộ vẫn giữ 63 tỉnh. |
| Điểm hiện “—” | Giá trị thiếu phía nguồn hoặc không đủ điều kiện ghép, không phải điểm 0; xem trạng thái dữ liệu. |
| Bản đồ không mở | Dùng chế độ biểu đồ hai trục; giữ tệp `data/raw/boundaries/diaphantinh.geojson` trong gói để dùng bản đồ. |
| CSV bị lỗi dấu khi mở Excel | Nhập tệp dạng UTF-8, dùng mã hóa 65001 nếu Excel hỏi; không đổi dấu phân cách thập phân trước khi nhập. |
| Mã kiểm tra trong ZIP không khớp | Giải nén lại bộ nhận ban đầu. Nếu đã tái tạo dữ liệu, giữ bản tái tạo riêng để đối chiếu, không coi nó còn trùng gói gốc. |
| PDF phiếu bị xuống trang | Chọn A4, tắt đầu/chân trang tự thêm của trình duyệt và xem trước khi lưu; có thể điều chỉnh tỉ lệ in. |

Nguồn đối chiếu: [bảng 63 tỉnh](../results/stakeholder_province_summary_2024.csv), [kết quả phân nhóm](../results/stakeholder_summary.md), [dự báo hai chỉ tiêu](../results/papi_forecast_2024.json), [nhánh hồi quy học phần](../results/supervised_metrics.csv) và [hồ sơ nguồn](../data/raw/papi/PROVENANCE.md).
