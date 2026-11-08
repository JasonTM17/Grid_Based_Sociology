# PROVENANCE — data/raw/molisa/

Nguồn dữ liệu: Bộ Lao động - Thương binh và Xã hội (MOLISA) — các Quyết định
"công bố kết quả rà soát hộ nghèo, hộ cận nghèo năm YYYY theo chuẩn nghèo tiếp
cận đa chiều áp dụng cho giai đoạn 2016–2020". Phụ lục số 1 của mỗi quyết định
là bảng "Tổng hợp số liệu hộ nghèo, hộ cận nghèo cả nước năm YYYY" theo 63
tỉnh/thành phố: Tổng số hộ dân, Số hộ nghèo, Tỷ lệ %, Số hộ cận nghèo, Tỷ lệ %.

Ngày tải: **2026-11-08**. Mọi tệp trong thư mục này là **dữ liệu KHÔNG TIN CẬY**
(chỉ đọc; script chuyển đổi nằm ở `scripts/build_molisa_poverty.py` và chạy từ
thư mục gốc repo).

## Văn bản gốc (bản phát hành chính thức của MOLISA)

| Quyết định | Ngày ban hành | Số liệu năm | Số hộ nghèo cả nước | Tỷ lệ hộ nghèo |
|---|---|---|---|---|
| 862/QĐ-LĐTBXH | 04/07/2018 | 2017 | 1.642.489 | 6,70% |
| 1052/QĐ-LĐTBXH | 29/07/2019 | 2018 | 1.304.001 | 5,23% |
| 835/QĐ-LĐTBXH | 15/07/2020 | 2019 | 984.764 | 3,75% |

## Vì sao dùng bản sao (đường đi truy tìm, 2026-11-08)

1. `https://molisa.gov.vn/` — DNS phân giải (103.194.188.21) nhưng TCP 80/443
   **timeout** từ máy này (curl exit 28, "Connection timed out"); WebFetch cũng
   timeout. Cả `http://` lẫn `https://` đều không kết nối được.
2. `https://dolab.gov.vn/` — DNS phân giải (123.30.7.46), TCP 80/443 **timeout**
   tương tự.
3. `https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=200645` (trang
   chính thức của Quyết định 835) — **timeout** từ máy này.
4. `https://chinhphu.vn/default.aspx?pageid=27160&docid=194287` (Quyết định 862)
   và `docid=200645` (Quyết định 835) — **tải được** (HTTP 200). Trang chỉ có
   tiêu đề + liên kết PDF đính kèm trên `datafiles.chinhphu.vn`, **không có bảng
   số liệu dạng HTML**. Hai PDF đính kèm chính thức đã tải về:
   - `https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/07/862-ldtbxh.signed.pdf`
   - `https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/08/835-bldtbxh.signed.pdf`
   → **Cả hai là PDF bản scan** (mỗi trang 1 ảnh, không có lớp chữ — kiểm tra
   bằng pymupdf: text_len=0 trên mọi trang trừ trang chữ ký số của Cổng TTĐT
   Chính phủ). Không OCR được theo quy tắc nhiệm vụ → KHÔNG dùng để bóc số.
5. `https://thuvienphapluat.vn/`, `https://vbpl.vn/`, `https://moj.gov.vn/` —
   HTTP 403 (chặn bot) khi truy cập trực tiếp.
6. `https://luatvietnam.vn/` — truy cập được (HTTP 200), có **toàn văn dạng
   HTML** (kèm bảng Phụ lục) cho QĐ 862 và QĐ 1052; phần tìm kiếm trả 403.
7. `https://web.archive.org/` — truy cập được; API tìm kiếm CDX trả 503
   "Internet Archive: Temporarily Offline" trong suốt phiên, nhưng API
   `archive.org/wayback/available` và replay `web.archive.org/web/<ts>/<url>`
   hoạt động. Đã tải bản lưu trữ (Wayback) của các trang thuvienphapluat.vn
   chứa toàn văn ba quyết định.

## Tệp đã tải

| Tệp | Nguồn URL gốc | Bản sao qua |
|---|---|---|
| `QD862_2017_luatvietnam.html` | https://luatvietnam.vn/chinh-sach/quyet-dinhh-862-qd-ldtbxh-2018-ket-qua-ra-soat-ho-ngheo-can-ngheo-nam-2017-168879-d1.html | tải trực tiếp 2026-11-08 |
| `QD862_2017_thuvienphapluat_wayback20240805133145.html` | https://thuvienphapluat.vn/van-ban/Van-hoa-Xa-hoi/Quyet-dinh-862-QD-LDTBXH-2018-cong-bo-ket-qua-ra-soat-ho-ngheo-ho-can-ngheo-2017-387930.aspx | web.archive.org/web/20240805133145/… |
| `QD1052_2018_luatvietnam.html` | https://luatvietnam.vn/chinh-sach/quyet-dinh-1052-qd-ldtbxh-2019-cong-bo-ket-qua-ra-soat-ho-ngheo-nam-2018-175726-d1.html | tải trực tiếp 2026-11-08 |
| `QD1052_2018_thuvienphapluat_wayback20211016091154.html` | https://thuvienphapluat.vn/van-ban/Van-hoa-Xa-hoi/Quyet-dinh-1052-QD-LDTBXH-2019-ket-qua-ho-ngheo-ho-can-ngheo-chuan-ngheo-tiep-can-da-chieu-420130.aspx | web.archive.org/web/20211016091154/… |
| `QD835_2019_thuvienphapluat_wayback20211205045134.html` | https://thuvienphapluat.vn/van-ban/Van-hoa-Xa-hoi/Quyet-dinh-835-QD-LDTBXH-2020-cong-bo-ket-qua-ra-soat-ho-ngheo-ho-can-ngheo-nam-2019-448889.aspx | web.archive.org/web/20211205045134/… |
| `QD862_official_chinhphu_signed_scan.pdf` | https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/07/862-ldtbxh.signed.pdf | tải trực tiếp 2026-11-08 (PDF scan, tham chiếu) |
| `QD835_official_chinhphu_signed_scan.pdf` | https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/08/835-bldtbxh.signed.pdf | tải trực tiếp 2026-11-08 (PDF scan, tham chiếu) |

Quyết định 1052 không tìm được bản PDF chính thức trên `datafiles.chinhphu.vn`
(trang `chinhphu.vn` cho QĐ 1052 chưa xác định docid; `vanban.chinhphu.vn` bị
timeout); bản QĐ 835 chính thức đã tải về nhưng là scan (tham chiếu).

## Bản chất bản sao

- Toàn văn HTML trên luatvietnam.vn / thuvienphapluat.vn là **bản gõ lại (typed
  copy) văn bản gốc** do hai cơ sở dữ liệu pháp luật tư nhân thực hiện, KHÔNG
  phải tệp gốc của Bộ. Đây là điểm yếu chính về chuỗi cung chứng.
- Đã giảm rủi ro bằng: (a) với năm 2017 và 2018 có **hai bản gõ độc lập**
  (luatvietnam và thuvienphapluat-via-Wayback) — script chuyển đổi so từng ô
  của bảng Phụ lục 1 giữa hai bản, lệch nào cũng dừng; (b) năm 2019 chỉ có một
  bản gõ đầy đủ (thuvienphapluat-via-Wayback) — script kiểm tra tính nhất quán
  số học từng dòng (tỷ lệ % = số hộ nghèo / tổng số hộ dân × 100, làm tròn 2
  chữ số thập phân) và tổng 63 tỉnh bằng dòng "Cả nước"; (c) tổng cả nước của
  cả ba năm khớp với phần thuyết minh trong văn bản và các trích dẫn thứ cấp.

## Giấy phép

- Văn bản pháp luật Việt Nam là **thông tin công khai** (Luật Tiếp cận thông tin
  2016; văn bản QPPL được đăng tải đầy đủ trên Cổng/số công báo) — số liệu trong
  Phụ lục là kết quả công bố chính thức của MOLISA, tái sử dụng không hạn chế.
- Bản sao luatvietnam/thuvienphapluat giữ bố cục trình bày của từng trang; sử
  dụng ở đây chỉ là **vận chuyển nội dung văn bản gốc**, không dùng lại hình
  thức/bố cục trang. URL gốc ghi ở bảng trên.
- Bản PDF có chữ ký số của Cổng Thông tin điện tử Chính phủ (Văn phòng Chính
  phủ) — lưu giữ nguyên trạng, không chỉnh sửa.

## Manifest (tên — bytes — SHA-256, tính bằng python hashlib 2026-11-08)

| Tệp | Bytes | SHA-256 |
|---|---|---|
| QD1052_2018_luatvietnam.html | 1957026 | de497762113b9dc517e3a0016565d6abbf9500c0490ac2ed64d28c664ed9a88b |
| QD1052_2018_thuvienphapluat_wayback20211016091154.html | 2461238 | 73fb3601f0fba1f3dc19d72bce02d5dabdece0cf3a9b886a4d57ed745ef7fe24 |
| QD835_2019_thuvienphapluat_wayback20211205045134.html | 1033846 | bdb4caf724777000f95fc043165143d297c0a9e47bc206e5652f5f6cd99b802b |
| QD835_official_chinhphu_signed_scan.pdf | 2034630 | c65824ba7f48109c10fd221569bf45d4a591db6127184ac58e1d4cb9d63f0886 |
| QD862_2017_luatvietnam.html | 2187505 | abbc79aa39699883643954f83d04dd37e75f611076c3d803cf4f57c8eadb9d0c |
| QD862_2017_thuvienphapluat_wayback20240805133145.html | 1045320 | 17364deff85222557f3ba3169d5d9cd84ee79c9c93d8fbd7ce0f023365606b81 |
| QD862_official_chinhphu_signed_scan.pdf | 1419508 | 050c4b5f28d922ec81b6d8a2d0f0ec11654bbfde50fd88feac1492564ec83008 |

## Giới hạn đã biết

- Chỉ có 3 năm số liệu (2017, 2018, 2019) theo chuẩn nghèo đa chiều 2016–2020
  của chính sách giảm nghèo (khác chuẩn của bảng GSO V14.47 — xem
  `data/raw/gso/PROVENANCE.md`); KHÔNG nội suy các năm khác.
- Chuẩn nghèo hộ (MOLISA rà soát hàng năm) ≠ chuẩn nghèo đa chiều điều tra của
  GSO; hai nguồn cùng tên "hộ nghèo" nhưng khác phương pháp và khác con số
  (ví dụ 2019: MOLISA 3,75% hộ — GSO pxweb V14.47 không có 2019).
- Năm 2019 chỉ có một bản gõ đầy đủ; đã đối chiếu tổng cả nước (984.764 hộ /
  3,75%) với phần thuyết minh quyết định và các trích dẫn công khai khác.
