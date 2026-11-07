# PROVENANCE — Dữ liệu GSO (pxweb.nso.gov.vn + Niên giám Thống kê)

- **Nguồn:** Cục Thống kê Việt Nam (NSO/GSO) — cổng PX-Web `https://pxweb.nso.gov.vn`
  (được nhúng từ `https://www.nso.gov.vn/px-web-2`) và thư viện PDF Niên giám
  Thống kê trên `https://www.nso.gov.vn`.
- **Ngày tải:** 2026-11-07.
- **Giấy phép / điều kiện dùng:** dữ liệu thống kê chính thức công khai của NSO.
  Trang bảng ghi "Bản quyền: Không"; mục "Thông tin: Thống kê chính thức".
  Không qua đăng ký/paywall; tải bằng HTTP thường (curl / urllib), không can
  thiệp cơ chế bảo vệ nào.
- **Cách tải bảng PX-Web:** giao diện PX-Web "cổ" của GSO không mở API v1 cho
  database Tài khoản quốc gia / Dân số (POST `/api/v1/...` trả 404; GET chỉ trả
  metadata). Script `scripts/gso_pxweb_fetch.py` giả lập trình duyệt: GET trang
  chọn biến → POST form ASP.NET (VIEWSTATE/EVENTVALIDATION + danh sách giá trị
  chọn + nút "Tiếp tục") → lưu HTML bảng kết quả vào thư mục này.

## Kết quả đã thử và bằng chứng

| Hướng | Kết quả | Bằng chứng |
|---|---|---|
| `stat.gso.gov.vn` (cổng cũ trong đề bài) | **Không phân giải DNS** | `curl https://stat.gso.gov.vn/` → `curl: (6) Could not resolve host` (cả `www.stat.gso.gov.vn`, `gso.gov.vn`, `opendata.nso.gov.vn`) |
| API PX-Web `/api/v1/vi/` | Chỉ mở 3 database (Công nghiệp, Doanh nghiệp, Dân số và lao động); POST trả 404 | `POST /api/v1/vi/Dân số và lao động/V02.01.px` → IIS 404 |
| Bảng GRDP/bq đầu người (ma trận **V03.12**) | **Đã tải** — 63 tỉnh × 2018–2023 + "Sơ bộ 2024" + "Ước tính 2025", đơn vị **Triệu đồng** | `pxweb_V03.12_grdp_pc_step2.html` (cập nhật lần cuối 15/08/2026) |
| Bảng dân số (ma trận **V02.01**) | **Đã tải** — 63 tỉnh × 2011–2025, "Dân số trung bình (Nghìn người)" | `pxweb_V02.01_pop_step2.html` (2011–2020), `pxweb_V02.01_pop_2021_2025_step2.html` (2021–2023), `pxweb_V02.01_pop_2024_2025_step2.html` (2024–2025) — trình bày PX-Web giới hạn số cột/trang nên phải chia 3 lần chọn năm |
| Tỷ lệ hộ nghèo theo tỉnh (ma trận **V14.47**) | **Đã tải** — 63 tỉnh × 14 năm (2006, 2008, 2010, 2012–2016, 2020–2025), đơn vị **%**, cập nhật lần cuối 21/08/2026, "Bản quyền: Không". **Không có 2017–2019** trên bảng này (đã kiểm tra listbox "Năm" của trang chọn biến — chỉ có đúng 14 giá trị trên) → để trống, không nội suy. Danh mục PX-Web cũng có bảng "Tỷ lệ hộ nghèo phân theo thành thị, nông thôn và theo vùng" (**V14.46**) cùng database | `pxweb_V14.47_poverty_step2.html`; bảng nằm trong database "Y tế, văn hóa và MSDC" — danh sách bảng lấy từ giao diện `?tablelist=true` của PX-Web (API `/api/v1` KHÔNG mở database này) |
| GRDP bình quân đầu người **2011–2017** | **Không có trên các nguồn GSO công khai còn truy cập được** | (1) Niên giám bản in đến bản 2021 **không** có bảng GRDP/tỉnh: quét toàn văn 7 bản PDF 2012–2021 (pymupdf) — 0 trang chứa "GRDP"/"sản phẩm tỉnh"; bảng đầu tiên xuất hiện ở **Niên giám 2022** (bảng 95, tr.260–261, số liệu 2018–2022). (2) `stat.gso.gov.vn` chết DNS. (3) web.archive.org trả 503 "Temporarily Offline" khi thử tra CDX của `gso.gov.vn` (mệnh đề cũ đã stale — kiểm tra lại trong phiên 2026-11-07: CDX API sống và trả snapshot bình thường; 503 là gián đoạn tạm thời lúc tải, không phải chặn truy cập). |
| Tóm tắt Niên giám 2016 | Không có bảng GRDP/tỉnh | `nien_giam_tomtat_2016.pdf`, quét toàn văn |

## File trong thư mục này

| File | Nội dung |
|---|---|
| `pxweb_V03.12_grdp_pc_step2.html` | HTML bảng V03.12 — GRDP bình quân đầu người theo tỉnh, Triệu đồng, 2018–2025 |
| `pxweb_V03.10_grdp_pc_step2.html` | HTML bảng V03.10 — chỉ số phát triển GRDP theo tỉnh (không dùng cho output, lưu làm bằng chứng) |
| `pxweb_V02.01_pop_step2.html` | HTML bảng V02.01 — diện tích/dân số trung bình/mật độ theo tỉnh, 2011–2020 |
| `pxweb_V02.01_pop_2021_2025_step2.html` | như trên, 2021–2023 |
| `pxweb_V02.01_pop_2024_2025_step2.html` | như trên, 2024–2025 |
| `pxweb_V14.47_poverty_step2.html` | HTML bảng V14.47 — "Tỷ lệ hộ nghèo phân theo địa phương", %, 63 tỉnh × 2006–2025 (không có 2017–2019) |
| `nien_giam_2012.pdf` … `nien_giam_2025.pdf` | Niên giám Thống kê các bản 2012, 2014, 2016, 2018, 2019, 2020, 2021, 2022, 2025 (bản "day du"/toàn quốc) — dùng đối chiếu và làm bằng chứng phủ dữ liệu |
| `nien_giam_tomtat_2016.pdf` | Niên giám tóm tắt 2016 — bằng chứng không có bảng GRDP/tỉnh |

URL gốc:

- V03.12: `https://pxweb.nso.gov.vn/pxweb/vi/T%C3%A0i%20kho%E1%BA%A3n%20qu%E1%BB%91c%20gia/T%C3%A0i%20kho%E1%BA%A3n%20qu%E1%BB%91c%20gia/V03.12.px/`
- V02.01: `https://pxweb.nso.gov.vn/pxweb/vi/D%C3%A2n%20s%E1%BB%91%20v%C3%A0%20lao%20%C4%91%E1%BB%99ng/D%C3%A2n%20s%E1%BB%91%20v%C3%A0%20lao%20%C4%91%E1%BB%99ng/V02.01.px/`
- V14.47: `https://pxweb.nso.gov.vn/pxweb/vi/Y%20t%e1%ba%bf,%20v%c4%83n%20h%c3%b3a%20v%c3%a0%20MSDC/Y%20t%e1%ba%bf,%20v%c4%83n%20h%c3%b3a%20v%c3%a0%20MSDC/V14.47.px/`
  (chú thích gốc của bảng, trích: "Từ năm 2008 tới nay, số liệu thành phố Hà
  Nội bao gồm cả tỉnh Hà Tây. (*) Chuẩn nghèo của Chính phủ giai đoạn
  2011-2015 tính theo thu nhập bình quân 1 người 1 tháng của hộ gia đình được
  cập nhật theo chỉ số giá tiêu dùng như sau: Năm 2010 là 400 nghìn đồng đối
  với khu vực nông thôn và 500 nghìn đồng đối với khu vực thành thị; … năm
  2016 là 630 nghìn đồng và 780 nghìn đồng." — tức các cột 2010–2016 của bảng
  pxweb theo **chuẩn nghèo thu nhập của Chính phủ**, KHÁCH với bảng "chuẩn
  nghèo đa chiều" trong Niên giám 2019–2021: cùng năm 2016, pxweb cả nước
  5,8% so với Niên giám 9,2%. Còn Niên giám 2025 ghi chú "(*) Từ năm 2022,
  theo chuẩn nghèo đa chiều của Chính phủ giai đoạn 2022-2025" và giá trị
  2020–2025 của Niên giám 2025 TRÙNG pxweb — đối chiếu bằng script, xem dưới.)
- Niên giám 2012: `https://www.nso.gov.vn/wp-content/uploads/2019/10/Nien-giam-2012-pdf-1.pdf`
- Niên giám 2014: `https://www.nso.gov.vn/wp-content/uploads/2019/10/Nien-giam-2014-pdf.pdf`
- Niên giám 2016: `https://www.nso.gov.vn/wp-content/uploads/2019/10/Nien-giam-Thong-ke-2016.pdf`
- Niên giám 2018: `https://www.nso.gov.vn/wp-content/uploads/2019/10/Nien-giam-2018.pdf`
- Niên giám 2019: `https://www.nso.gov.vn/wp-content/uploads/2020/09/Nien-giam-thong-ke-day-du-2019.pdf`
- Niên giám 2020: `https://www.nso.gov.vn/wp-content/uploads/2021/07/Sach-NGTK-2020Ban-quyen.pdf`
- Niên giám 2021: `https://www.nso.gov.vn/wp-content/uploads/2022/08/Sach-Nien-giam-TK-2021-1.pdf`
- Niên giám 2022: `https://www.nso.gov.vn/wp-content/uploads/2023/06/Sach-Nien-giam-TK-2022-final.pdf`
- Niên giám 2025: `https://www.nso.gov.vn/wp-content/uploads/2026/07/NG-TOAN-QUOC-2025-1.pdf`
- Niên giám tóm tắt 2016: `https://www.nso.gov.vn/wp-content/uploads/2019/03/Ruot-nien-giam-TT-1.pdf`

## Đối chiếu giữa các nguồn (đã chạy trong `scripts/build_gso_grdp_pop.py`)

- GRDP pxweb V03.12 vs **Niên giám 2025** (bảng 86, tr.245–246; 2020/2022/2023/Sơ
  bộ 2024): **248/248 ô trùng khớp** (dung sai 0,051 = sai số làm tròn 1 chữ số).
- GRDP pxweb V03.12 vs **Niên giám 2022** (bảng 95, tr.260–261; 2018–2022):
  259/315 trùng; **56 ô lệch, toàn bộ ở cột "Sơ bộ 2022"** — số liệu 2022 trên
  pxweb đã được sửa lại so với bản Sơ bộ (vd Hà Nội 141,12 so với 141,6). pxweb
  là bản hiệu đính mới hơn (cập nhật 15/08/2026).
- Dân số pxweb V02.01 vs trích Niên giám trong repo (504 tỉnh-năm trùng):
  chênh lệch trung bình 8,49 nghìn người, max 189,63 nghìn, 104 dòng lệch >1% —
  hai "vintage" khác nhau (bản Niên giám in tại thời điểm đó vs bản pxweb sửa
  lại sau Tổng điều tra 2019). Vì vậy file `external_gso_population_63_full.csv`
  giữ nguyên giá trị base cho các năm đã có và chỉ lấp năm thiếu, kèm cột
  `source` ghi rõ từng dòng.

## File sinh ra (data/processed/)

| File | Nội dung |
|---|---|
| `external_gso_grdp_63.csv` | GRDP bình quân đầu người (`grdp_per_capita_million_vnd`, triệu đồng) 63 tỉnh × 2018–2024 (2024 = Sơ bộ), 441 dòng, 0 ô thiếu |
| `external_gso_population_63_full.csv` | Dân số trung bình 63 tỉnh × 2011–2024: năm 2012–2014/2018–2022 giữ trích Niên giám (base), năm 2011/2015–2017/2023–2024 lấy từ pxweb V02.01; cột `source` phân biệt; không có cột đô thị cho năm lấp |
| `external_poverty_63.csv` | Tỷ lệ hộ nghèo (`poverty_rate_pct`, %) 63 tỉnh × 14 năm (2006, 2008, 2010, 2012–2016, 2020–2025) từ pxweb V14.47; 882 dòng, 1 ô thiếu (TP.HCM 2016 — nguồn ghi "..") để trống; KHÔNG có 2017–2019 vì bảng nguồn không có, KHÔNG nội suy |

Đối chiếu poverty V14.47 vs Niên giám (chạy trong `scripts/build_poverty_63.py`,
dung sai 0,051):

- vs **Niên giám 2025** bảng chương tr.934–935 (62 tỉnh × 2020, 2022, 2023,
  2024, Sơ bộ 2025): **310/310 trùng khớp**. Phụ lục tr.1494–1495 của Niên
  giám 2025 liệt kê theo **34 tỉnh sau sáp nhập 2025** (vd "Bắc Ninh" 2020 =
  1,8 là Bắc Ninh + Bắc Giang gộp lại) — khác địa giới nên không dùng đối
  chiếu với chuỗi 63 tỉnh.
- vs **Niên giám 2021** "Tỷ lệ hộ nghèo đa chiều phân theo địa phương"
  tr.881–882 (cột 2020, 2021): **124/124 trùng khớp** (TP.HCM 2020/2021 để
  trống trong Niên giám nên không nằm trong phép so).

Chuẩn hóa: nối tỉnh bằng `province_crosswalk_63.csv` (gói Mendeley) qua khóa
ASCII hóa tên (NFKC, bỏ tiền tố "TP.", gọn dấu "-"), sau đó gán
`papi_province_code` qua `province_ascii` của panel PAPI — **63/63 tỉnh khớp
hết, không có dòng nào bị bỏ/bịa mã**.

## Manifest (tên file — bytes — SHA-256)

| File | Bytes | SHA-256 |
|---|---|---|
| `nien_giam_2012.pdf` | 7,477,030 | `3adaf46126ddd79a99041634fd6c9dd8439472186483d0dd9a53d821d2334fbb` |
| `nien_giam_2014.pdf` | 7,437,182 | `73721c66212b987b3f34f5e521995f870b7a340b69887fe2bf42c9f8319a018c` |
| `nien_giam_2016.pdf` | 5,892,955 | `cf34bc218b70f7822081c2ad8ada7d78f23817c967b43a77e48dd27aadd46bc5` |
| `nien_giam_2018.pdf` | 20,569,187 | `e491e8a47a3119f3ad8d8fca935426aad3767cd1ded5e7ea785930385374d3e1` |
| `nien_giam_2019.pdf` | 16,840,733 | `477f7bf94118645a30d8893d2834d32b3c069f9caf5fd4837592cc793e94f13f` |
| `nien_giam_2020.pdf` | 16,587,405 | `c94c4ed55ebc6d17ab3cd2338a529b1fffd2dc5836ff597f8790e65ff0f1f335` |
| `nien_giam_2021.pdf` | 14,701,017 | `b0a73025ccf63d50b5895fe07f672ab06d3c0386ec69bbb52e29cee1eadf3b0d` |
| `nien_giam_2022.pdf` | 15,673,689 | `5196ff5341607630e3ca5e2b816a89422a573240457d35258701395e92a3bb01` |
| `nien_giam_2025.pdf` | 15,799,990 | `b79ac7e05d2815d30e87985b030f4398b67ff727075cdbe2c908a131c904c67f` |
| `nien_giam_tomtat_2016.pdf` | 1,664,749 | `fdd36d427d10fc34d500421aec94d51257512b7d035c665b78c6b3070cb90912` |
| `pxweb_V02.01_pop_2021_2025_step2.html` | 135,625 | `555c8a79c2d73bf783f56c485364dfb71c131d6c0b6169a501e9fe597e0516a1` |
| `pxweb_V02.01_pop_2024_2025_step2.html` | 120,715 | `3503a1f3834e07fde911098cc03c316ea1ba2404b45cbf0b65010fc702ca5e93` |
| `pxweb_V02.01_pop_step2.html` | 240,164 | `a39a7b0fc7ef8457be1b10e2436736ea6e590827f4295d41ac748eeac61663cc` |
| `pxweb_V03.10_grdp_pc_step2.html` | 118,774 | `bf1b54569d738e53ce02912377437398f75e45f5e19aa13dd25f529e8d244dca` |
| `pxweb_V03.12_grdp_pc_step2.html` | 118,210 | `38238e839d69f75d3ddbc9bede1821594c485889390bb48a33a5b264e98d2951` |
| `pxweb_V14.47_poverty_step2.html` | 146,373 | `3e652b6b1e5be65ebefa718b658dbde3b249fcc148eeb777bd3698d36d7183bd` |
