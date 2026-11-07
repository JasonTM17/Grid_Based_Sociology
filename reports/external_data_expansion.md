# Mở rộng dữ liệu ngoài cho panel 63 tỉnh — PCI · GSO · OD Mekong · World Bank

Ngày lập: **2026-11-07** (phiên bản 2 — cập nhật theo góp ý của người đọc độc lập cùng ngày).
Lưới chuẩn của dự án: **63 tỉnh × 14 năm (2011–2024) = 882 ô tỉnh-năm**.
Tài liệu dành cho sinh viên học Học máy đang làm đồ án: giải thích **từng nguồn dữ liệu ngoài** (tải thế nào, schema gì, phủ đâu, thiếu gì), **giấy phép** để trích dẫn đúng khi demo/thi, và **giá trị cho bài toán cụm STING + hồi quy**.

> **Quy ước đọc nhanh:** *panel* = bảng dữ liệu dạng tỉnh×năm (mỗi dòng một tỉnh trong một năm).
> *Ô tỉnh-năm* = một cặp (tỉnh, năm) trên lưới 882 ô. *Không nội suy* = ô thiếu giữ nguyên trống,
> không tự điền số (điền số bịa là lỗi phương pháp phổ biến nhất khi xử lý panel).
> *STING* (Statistical Information Grid) — thuật toán clustering dạng lưới: chia không gian đặc
> trưng thành ô lưới thống kê nhiều tầng rồi gom các ô đủ dày đặc thành cụm; dự án cài đặt tự
> viết tại `src/sting.py` (README: "Thư viện STING (tự viết từ đầu)").

---

## 1. Mục tiêu & tóm tắt

### 1.1 Vì sao cần dữ liệu ngoài

Dự án hiện có đúng **một** nguồn chính: panel PAPI 2011–2024 (`data/processed/papi_panel_63_2011_2024.csv` — đếm trực tiếp trong phiên tài liệu: **882 dòng × 41 cột** = **4 cột khóa** (`province_code`, `province_ascii`, `province_vi`, `year` — `province_code` của panel chính là `papi_province_code` dùng trong các file external) + 37 cột chỉ số = 8 dimension `d1–d8` + 29 sub-indicator `sd_1_1`–`sd_8_3`). Vấn đề của đồ án khi chỉ có một nguồn:

1. **Clustering là học không giám sát** (unsupervised): STING gom nhóm tỉnh mà không có "đáp án đúng", nên cần một biến **nằm ngoài khung đo PAPI** để kiểm tra các cụm có nghĩa xã hội hay chỉ là artifact của thang đo (xem §5.1).
2. **Nghi vấn "nhảy thang đo" PAPI xuyên năm**: `scripts/check_data.py` flag cột có bước nhảy mean năm > 0,25; workbook PAPI ghi rõ có nội dung thay đổi năm 2021 và thang dimension 1–10 chưa được chứng minh tương đương xuyên năm (README.md, mục "Lưu ý thang đo" — `README.md:131`–`140`). Cần một mỏ neo ngoài để phân biệt "thang đo đổi" với "cấu trúc thật đổi" (§5.2).
3. **Phần hồi quy** (dự báo Y tế công lập t+1, `scripts/predict_supervised.py`) chưa có biến kiểm soát kinh tế cấp tỉnh nào (README.md:79–87).

### 1.2 Đã có thêm gì trong đợt mở rộng này

Bốn nguồn mới, toàn bộ tải **ngày 2026-11-07** bằng HTTP thường, không đăng nhập, không có cơ chế chặn nào cần vượt (cơ sở pháp lý phương pháp: xem §3.2 robots.txt và §3.4; từng nguồn có `PROVENANCE.md` riêng):

| # | Nguồn | File chính (`data/processed/`) | Đã đạt gì |
|---|---|---|---|
| 1 | **PCI** (VCCI–USAID, pcivietnam.vn) | `external_pci_63_full.csv` | 882 dòng; điểm có giá trị: **756** (đủ 63 tỉnh × 2011–2022) + **60** (Top-30 × 2023–2024); **66 ô trống** (33+33) — xem §3.1 |
| 2 | **GSO/NSO** (pxweb.nso.gov.vn + Niên giám) | `external_gso_grdp_63.csv`, `external_gso_population_63_full.csv` | GRDP/người 2018–2024 (441 dòng); dân số **đủ 2011–2024** (882 dòng) |
| 3 | **OD Mekong** (datahub mở) | `external_odm_poverty_region_1998_2016.csv`, `external_odm_health_63.csv` | Nghèo **6 vùng × 12 năm rải rác** trong 1998–2016 (không cấp tỉnh); bệnh viện 63 tỉnh × 2020 |
| 4 | **World Bank WDI** (API v2, quốc gia VNM) | `external_worldbank_vnm.csv` | 4 chỉ số vĩ mô × 2010–2024 (52 dòng giá trị) |

Ngoài ra các file "base" trích từ gói replication Mendeley (có sẵn từ Phase 2, không phải sản phẩm của đợt này) vẫn là nền: `external_pci_63.csv`, `external_gso_population_63.csv`, `external_gso_waste_63.csv`, `external_63_panel.csv` — chi tiết ở §3.5.

### 1.3 Dùng được ngay / dùng có điều kiện / không dùng được

- **Dùng được ngay:** PCI 2011–2022 (756 ô đủ 63 tỉnh × 12 năm), dân số 882/882 ô, GRDP 441/441 ô (2018–2024), WDI **cấp quốc gia**.
- **Dùng có điều kiện:** PCI 2023–2024 (chỉ Top-30 → chỉ kiểm tra phụ, cảnh báo chọn mẫu), rác thải (chuỗi ngắn, 2018 trống hoàn toàn, 2020 thiếu 10 tỉnh), bệnh viện 2020 (snapshot một năm, 10 tỉnh count=0 cần làm rõ), nghèo 6 vùng (không đưa vào feature cấp tỉnh).
- **Không dùng được — và vì sao:** GRDP **2011–2017** — GSO không công bố ở nguồn nào còn truy cập được (chi tiết §3.2); **nghèo cấp tỉnh trên ODM** — dataset `poverty-rate` đã bị gỡ (HTTP 404, `data/raw/odmekong/PROVENANCE.md` dòng 14–25); **WDI ở cấp tỉnh** — biến quốc gia không tồn tại chiều tỉnh (chính chuỗi cấp quốc gia dùng được ngay, đã liệt kê ở trên).

### 1.4 Phạm vi xác minh của tài liệu này (trung thực về điều gì đã chạy, điều gì chưa)

Đã **chạy trong phiên tài liệu** (2026-11-07, hai lượt: lần đầu lập tài liệu và lần này sửa theo góp ý):

1. **Đếm CSV bằng `python -I` (chỉ stdlib `csv`)** — phạm vi chính xác: *đếm chi tiết* (tổng dòng, số tỉnh/năm, ô giá trị trống, nhãn `source`) **7 file external mới**: `external_pci_63_full.csv`, `external_gso_population_63_full.csv`, `external_gso_grdp_63.csv`, `external_gso_waste_63.csv`, `external_odm_health_63.csv`, `external_odm_poverty_region_1998_2016.csv`, `external_worldbank_vnm.csv`; *kiểm tra header + tổng dòng* thêm **`external_63_panel.csv`** (tổng cộng 8 file). Kết quả khớp toàn bộ tuyên bố của phiên tải (PCI 882 dòng / 30 điểm 2023 / 30 điểm 2024; dân số 882 dòng = 504 Niên giám + 378 pxweb, cột đô thị trống đúng 378 dòng; GRDP 441 dòng 2018–2024, 0 trống; rác thải 305 dòng; bệnh viện 63 dòng, tổng 423; nghèo 72 dòng; WDI 52 dòng = 15+15+14+8).
2. **Liệt kê chi tiết:** 10 tỉnh thiếu rác thải 2020, 10 tỉnh có hospital_count = 0, tập Top-30 2023 vs 2024 (28 tỉnh chung; chỉ 2023 có Dak Nong, Tien Giang; chỉ 2024 có Ha Nam, Thai Binh — đếm lại trong phiên này), và **min PCI 2022 = 59,58 (Cao Bang)** trên 63 dòng 2022 của `external_pci_63.csv` (khớp giá trị "tỉnh đứng cuối PCI 2022" mà Báo cáo PCI 2023 tr.42 nêu — theo tuyên bố phiên nguồn).
3. **Parse trực tiếp 3 file HTML pxweb V02.01** (`python -I`): phủ đủ **2011–2025**, mỗi năm **70 dòng giá trị** (63 tỉnh + 6 vùng + CẢ NƯỚC); riêng `pxweb_V02.01_pop_step2.html` chứa **2011–2020** — bác bỏ nhận định "file chỉ chứa 2011–2018" của phiên QA trước.
4. **Tính lại độ lệch vintage dân số** (join 3 HTML với `external_gso_population_63.csv` qua tên tỉnh chuẩn hóa): giao **504 tỉnh-năm** (8 năm 2012–2014, 2018–2022 × 63), chênh trung bình **8,49 nghìn người**, max **189,63** (Hà Nội 2014), **104 dòng >1%** — khớp **4/4 con số** với `data/raw/gso/PROVENANCE.md` dòng 63–64 (tuy nhiên phiên QA trước đã báo các số này "không tái lập được" — kết luận của QA sai do đọc nhầm phạm vi năm của file HTML, xem §3.2).
5. **Đọc `license_id` từ file package_show đã lưu:** `_pkg_poor_households.json` và `_pkg_covid_hosp.json` đều `cc-by-sa` — giấy phép CC BY-SA của dataset nghèo 6 vùng là **đã xác minh từ API lưu**, không phải suy từ quy ước chung.
6. **`curl https://pxweb.nso.gov.vn/robots.txt`** (ngày 2026-11-07): chỉ có `User-agent: *` + dòng Sitemap, **không có dòng Disallow nào** → tải tự động trang công khai không bị cấm. **`curl https://papi.org.vn/robots.txt`**: trả về trang thách thức Cloudflare ("Just a moment...", kiểu challenge *managed*) — không đọc được robots.txt bằng curl, **không cố vượt**; điều khoản của papi.org.vn vì vậy chưa kiểm được online.
7. **`git status --short`** (2026-11-07): `M README.md` + các file untracked mới (data/raw/pci, gso, odmekong, worldbank; data/processed/external_*; 7 script; reports/external_data_expansion.md).
8. **Đọc:** `README.md`, `data/raw/{pci,gso,odmekong,worldbank,boundaries,papi}/PROVENANCE.md`, `data/processed/external_provenance.md`, docstring 7 script liên quan; kiểm tra dependency `python -E -c "import shapely, xlrd, pypdf, pandas"` → `shapely 2.1.2 | xlrd 2.0.2 | pypdf 6.18.0 | pandas 2.3.3`.

**Chưa chạy lại** (ghi nhận theo tuyên bố của phiên tải + phiên QA): curl 200 OK các file dữ liệu PCI/GSO/ODM/WDI, manifest SHA-256, đối chiếu CSV↔JSON của WDI, và quét toàn văn PDF Niên giám (phiên nguồn quét 8 file — chi tiết §3.2; phiên QA quét lại 2/8 là bản 2012 và 2021, cùng kết quả 0 hit).

**Kết luận QA hiện tại:** pci, odmekong, worldbank = đã xác nhận (theo phiên QA; odmekong có 2 lỗi nhỏ về nhãn file bằng chứng, không sai dữ liệu); gso = **đã xác nhận trọn vẹn sau khi kiểm tra trực tiếp** ở mục 3–4 (hai "lỗi" của phiên QA trước đều bị bác bỏ; output CSV khớp raw 100% theo QA gốc).

---

## 2. Bảng nguồn: nguồn · giấy phép · file CSV · độ phủ

| Nguồn | Giấy phép / điều kiện dùng | File CSV (data/processed/) | Độ phủ |
|---|---|---|---|
| **PCI** — VCCI/USAID, <https://pcivietnam.vn> | Dữ liệu công khai; **phải ghi nguồn VCCI–USAID** khi tái sử dụng ([chính sách trích dẫn](https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html)) | `external_pci_63_full.csv` | 63 tỉnh × 2011–2024; điểm tổng đủ 2011–2022 (756 ô) + Top-30 2023–2024 (60 ô) = **816/882 ô**; 66 ô trống (không nội suy) |
| **GSO/NSO** — <https://pxweb.nso.gov.vn> + Niên giám Thống kê <https://www.nso.gov.vn> | Thống kê chính thức công khai; trang bảng ghi **"Bản quyền: Không"**; PDF Niên giám công bố tự do (điều khoản riêng cho PDF: chưa kiểm tra — NOT_RUN); ghi nguồn NSO khi dùng lại | `external_gso_grdp_63.csv` | GRDP/người (Triệu đồng): 63 tỉnh × **2018–2024** = 441/441 ô (2024 = "Sơ bộ"); **thiếu 2011–2017** |
| | | `external_gso_population_63_full.csv` | Dân số trung bình (Nghìn người): 63 tỉnh × **2011–2024 đầy đủ** = 882/882 ô; cột đô thị chỉ có 504 ô (2012–2014 + 2018–2022) |
| **OD Mekong** — <https://data.vietnam.opendevelopmentmekong.net> | Nghèo + COVID: **CC BY-SA** (`license_id = cc-by-sa` đọc từ package_show đã lưu — xác minh trực tiếp); *Health Facilities in Mekong Countries 2020*: **ODbL** | `external_odm_poverty_region_1998_2016.csv` | **6 vùng** × 12 năm rải rác (1998, 2002, 2004, 2006, 2008, 2010–2016) = 72/72 ô — **KHÔNG cấp tỉnh** |
| | | `external_odm_health_63.csv` | 63 tỉnh × **2020** (snapshot 1 năm): tổng 423 điểm bệnh viện |
| **World Bank WDI** — API v2, quốc gia VNM | **CC BY 4.0** ([Terms of Use for Datasets](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets)) | `external_worldbank_vnm.csv` | Quốc gia × 2010–2024 × 4 chỉ số: GDP/người 15/15 năm, % đô thị 15/15, chi y tế/GDP 14/15 (thiếu 2024), giường bệnh 8/15 (2010–2017) |
| *(Nền)* **Extract Mendeley** — Le et al., DOI 10.17632/wbk42j9wc8.1 | **CC BY 4.0** | `external_pci_63.csv`, `external_gso_population_63.csv`, `external_gso_waste_63.csv`, `external_63_panel.csv` | PCI 2012–2022 (693 dòng); dân số + % đô thị **63 tỉnh × 8 năm trong 2012–2022** (2012–2014, 2018–2022 — thiếu hẳn 2015–2017; 504 dòng); rác thải 305 dòng (2015–2017, 2019 đủ 63; 2018 trống; 2020 còn 53); panel nối 693 dòng |

Giấy phép nêu rõ cho người học: **CC BY 4.0** = được dùng lại/vanç thể nếu **ghi công**; **CC BY-SA** = ghi công + mọi bản phái sinh phải phát hành dưới **cùng** giấy phép (share-alike); **ODbL** = giấy phép mở của Open Data Commons cho database, cũng có điều khoản share-alike cho database phái sinh. Khi demo/thi, nêu tên nguồn + license là đủ điều kiện của cả ba loại trên.

---

## 3. Chi tiết từng nguồn

### 3.1 PCI — Chỉ số Năng lực cạnh tranh cấp tỉnh (VCCI–USAID)

- **Nguồn gốc + URL:** PCI là bộ chỉ số khảo sát doanh nghiệp về môi trường kinh doanh cấp tỉnh, do VCCI và USAID thực hiện từ 2005. Công khai tại <https://pcivietnam.vn> — trang dữ liệu `/du-lieu-pci` (VN) | `/en/pci-data` (EN); trang xếp hạng `/en/pci-ranking?year=<năm>`; chính sách trích dẫn: <https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html> (theo `data/raw/pci/PROVENANCE.md` dòng 3–7).
- **Cách tải:** curl trực tiếp **server sống** ngày 2026-11-07 (HTTP 200, không đăng nhập). Sitemap cũ `/pci-data` đã 404, URL mới tìm qua Google redirect; Wayback CDX chỉ dùng để **dò URL**, mọi file đều từ server sống (theo tuyên bố phiên tải). File raw: `data/raw/pci/` — workbook 2011 (`.xls`), 2023 (EN+VN `.xlsx`), 2024 (EN `.xlsx`), 3 trang xếp hạng HTML 2011/2023/2024, 5 báo cáo PDF, và `Du_lieu_PCI_2025.xlsx`.
- **Nguồn điểm tổng (`pci_weighted_score`) theo từng năm** (tổng hợp từ `data/raw/pci/PROVENANCE.md` dòng 13–20):

| Năm | Điểm tổng trong CSV lấy từ đâu | Ghi chú |
|---|---|---|
| 2011 | Workbook `Indicator_PCI2011_EN.xls`, sheet Summary, cặp cột U–V ("PCI 2011") | Bảng xếp theo rank từng sub-index nên điểm tổng KHÔNG nằm ở cột B–C; đối chiếu trang xếp hạng: 61/63 khớp tuyệt đối, 2 lệch là lỗi hoán tên của site (dưới đây) |
| 2012–2022 | Extract Mendeley (`source = mendeley_extract`, 693 dòng) | 2022 có **đủ 63 giá trị** từ nguồn thứ cấp — giải thích câu chuyện Top-30 ngay dưới |
| 2023 | Trang xếp hạng chính thức `/en/pci-ranking?year=2023` (đã lưu `pci_ranking_page_2023.html`) | Workbook 2023 (cả EN lẫn VN) **không có cột điểm tổng**; khớp từng giá trị với Báo cáo PCI & PGI 2023 (Quảng Ninh 71,25 hạng 1 … Thanh Hóa 66,79 hạng 30) |
| 2024 | Workbook `Appendix_1_Table_Indicator_PCI_2024_EN_web.xlsx`, cột "The Weighted PCI Score" — **30 giá trị, 33 ô trống sẵn trong file gốc** | Khớp 30/30 với trang xếp hạng 2024 (chênh ≤ 0,005 = làm tròn 2 chữ số) |

- **Giải thích apparent contradiction "2022 vừa đủ 63 vừa chỉ Top 30":** hai kênh khác nhau. (a) Kênh **chính thức hiện tại** — Báo cáo PCI 2023 tr. 24, 43 nói cách trình bày đã đổi "từ toàn bộ cả nước sang Top 30" (từ kỳ PCI 2022 trở đi), nên workbook/trang xếp hạng ngày nay không công bố điểm 2023–2024 ngoài Top 30. (b) Kênh **nguồn thứ cấp** — extract Mendeley (Le et al.) ghi nhận đủ 63 giá trị của 2022; bằng chứng chéo: min 2022 của extract = **59,58 (Cao Bang)** — đếm lại trực tiếp trong phiên tài liệu — trùng đúng giá trị "tỉnh đứng cuối PCI 2022" mà Báo cáo 2023 tr.42 nêu (theo tuyên bố phiên nguồn), tức số liệu đủ-63 của 2022 có thật và được trích từ một bản dữ liệu/ấn phẩm đủ 63 tỉnh. **Tài liệu không có bằng chứng trực tiếp cho thấy extract lấy bản đủ-63 của 2022 từ đâu cụ thể** (ghi nhận trung thực). Hệ quả thực hành: khi trích dẫn điểm PCI 2022, ghi nguồn là **extract Mendeley (DOI)**, không phải pcivietnam.vn trực tiếp.
- **Schema cột** (đã đọc header trong phiên này): `papi_province_code, province_code, province_ascii, province_vi, year, pci_weighted_score, source`. `pci_weighted_score` thang 0–100. `source` (đếm trong phiên này): `mendeley_extract` 693 dòng (2012–2022), `pci_vietnam_download_2011` / `_2023` / `_2024` mỗi năm 63 dòng.
- **Độ phủ tỉnh×năm:** 882 dòng, đủ 63 tỉnh mỗi năm; **ô có giá trị: 816/882** — đủ 63 tỉnh × 2011–2022 (756 ô) + 30 tỉnh × 2023 + 30 tỉnh × 2024; **66 ô trống** (33 + 33), không nội suy.
- **Hạn chế & cạm bẫy dữ liệu đã ghi nhận:**
  1. **33 tỉnh/năm 2023 và 33 tỉnh/năm 2024 không có điểm công bố** → CSV để trống. **Tuyệt đối không tự tính weighted score từ sub-index** dù trọng số có công bố — đó là số phái sinh, không phải điểm chính thức.
  2. **Tập Top-30 hai năm không cùng tập** (đếm lại trong phiên này): 28 tỉnh chung; chỉ 2023 có Dak Nong, Tien Giang; chỉ 2024 có Ha Nam, Thai Binh — chọn mẫu thiên về tỉnh tốt.
  3. **Lỗi nguồn ở trang xếp hạng 2011:** site **hoán tên Bắc Giang ↔ Bắc Cạn**; Báo cáo PCI 2014 (tr. 37–38) xác nhận workbook đúng (Bắc Cạn 2011 = 52,71 hạng 60; Bắc Giang 2011 = 60,79 hạng 23) → CSV lấy theo workbook; 61/63 tỉnh còn lại khớp tuyệt đối giữa hai nguồn (`data/raw/pci/PROVENANCE.md` dòng 35–39).
  4. Workbook 2024 có dòng "Yen Bai" trùng lặp với điểm 0 ở dòng 66 (artifact cuối bảng); workbook 2023 có dòng trùng tương tự — đã bỏ qua khi parse.
  5. `Du_lieu_PCI_2025.xlsx` **không dùng**: cấu trúc mới 34 tỉnh sau sáp nhập, 9 chỉ số thành phần, ngoài phạm vi 2011–2024; chỉ lưu làm bằng chứng (hệ quả cho tương lai: §4.3).
- **Provenance:** `data/raw/pci/PROVENANCE.md` — bảng "điểm tổng từng năm lấy từ đâu", mục phủ dữ liệu + nguyên nhân ô trống, kiểm chứng chéo đã chạy, manifest tên file — bytes — SHA-256 (tính bằng `hashlib`, đối chiếu `sha256sum` độc lập — theo tuyên bố phiên tải).
- **Nối tỉnh:** chuẩn hóa tên bỏ dấu + bí danh (`brvt`, `hcmc`, `tthue`, `baccan` cho chính tả cũ "Bắc Cạn" trong file 2011) → `province_code` theo `province_crosswalk_63.csv` (gói Mendeley) → `papi_province_code` qua `province_ascii` của panel PAPI: 63/63 mã mỗi năm mới, không tỉnh nào không khớp.

### 3.2 GSO — Cục Thống kê (PX-Web + Niên giám Thống kê)

- **Nguồn gốc + URL:** cổng PX-Web của NSO thực tế nằm tại **<https://pxweb.nso.gov.vn>** (được nhúng từ `nso.gov.vn/px-web-2`); Niên giám Thống kê dạng PDF tại `nso.gov.vn`. **Cổng cũ `stat.gso.gov.vn` trong đề bài đã chết DNS** (`curl: Could not resolve host` — theo tuyên bố phiên tải, `data/raw/gso/PROVENANCE.md` dòng 21). Hai bảng dùng: **V03.12** "Tổng sản phẩm trên địa bàn bình quân đầu người phân theo địa phương" và **V02.01** "Diện tích, dân số và mật độ dân số phân theo địa phương".
- **Cơ sở phương pháp tải (đã kiểm tra trực tiếp ngày 2026-11-07):** `curl https://pxweb.nso.gov.vn/robots.txt` trả về đúng 2 dòng — `User-agent: *` và `Sitemap: …` — **không có dòng `Disallow` nào**, tức cổng không cấm tải tự động trang công khai. API v1 của PX-Web GSO chỉ mở 3 database và từ chối POST (thông báo 404 của **IIS** — *Internet Information Services*, web server của Microsoft) → `scripts/gso_pxweb_fetch.py` dùng đúng luồng bình thường của trang: GET trang chọn biến → POST form (**VIEWSTATE/EVENTVALIDATION** là hai trường ẩn của web form *ASP.NET* phải gửi lại để server xác thực trạng thái trang; script tự khai báo User-Agent "…research-download"). Không đăng nhập, không CAPTCHA, không rate-limit cần né — đây là cách dùng tiêu chuẩn của một trang công khai, không phải đi vòng lọc bot.
- **File raw:** `data/raw/gso/` — 5 HTML pxweb (V03.12, V03.10, 3 file V02.01) + 10 PDF = 9 bản Niên giám (2012, 2014, 2016, 2018, 2019, 2020, 2021, 2022, 2025) + 1 bản tóm tắt 2016.
- **Schema cột (output):**
  - `external_gso_grdp_63.csv` (441 dòng, đọc trong phiên này): `province_code, province_ascii, province_vi, year, grdp_per_capita_million_vnd, source, papi_province_code`. Đơn vị **Triệu đồng**; `source = gso_pxweb_V03.12`; 0 ô trống.
  - `external_gso_population_63_full.csv` (882 dòng): `papi_province_code, province_code, province_ascii, province_vi, year, gso_pop_total_thousand, gso_pop_urban_thousand, gso_urban_residence_pct_derived, source`. Đơn vị **Nghìn người** (dân số trung bình). `source` đếm trong phiên này: `gso_nien_giam_extract` 504 dòng (2012–2014, 2018–2022), `gso_pxweb_V02.01` 378 dòng (2011, 2015–2017, 2023–2024 — *6 năm × 63 tỉnh*); **cột đô thị trống đúng 378 dòng pxweb** (V02.01 không có phân tổ đô thị theo tỉnh).
- **Độ phủ tỉnh×năm:** GRDP **2018–2024** (2024 = "Sơ bộ", tức số chưa chính thức) — **thiếu hẳn 2011–2017**; dân số **đầy đủ 2011–2024**.
- **Đối chiếu GRDP — có mẫu số rõ (theo `data/raw/gso/PROVENANCE.md` dòng 57–62, chạy trong `scripts/build_gso_grdp_pop.py`):**
  - pxweb V03.12 vs **Niên giám 2025** (bảng 86, tr.245–246; các cột năm 2020, 2022, 2023, Sơ bộ 2024): **248/248 ô trùng khớp** (dung sai 0,051 = sai số làm tròn). Mẫu số tối đa theo cấu trúc là 63 × 4 = 252; con số 248 là số ô thực sự so sánh, 4 ô chênh lệch không được giải thích trong PROVENANCE.md — ghi nhận trung thực.
  - pxweb V03.12 vs **Niên giám 2022** (bảng 95, tr.260–261; 5 năm 2018–2022 × 63 tỉnh = **315 ô so sánh**): 259 trùng, **56 lệch — toàn bộ ở cột "Sơ bộ 2022"** (56/63 ô của cột đó; số 2022 trên pxweb là bản hiệu đính mới hơn, cập nhật 15/08/2026).
- **Độ lệch vintage dân số — đã định lượng VÀ tái lập trong phiên tài liệu:** *vintage* = phiên bản số liệu của cùng chỉ số tại thời điểm công bố khác nhau (bản Niên giám in tại thời điểm đó vs bản pxweb sửa lại sau Tổng điều tra Dân số 2019). Trên **504 tỉnh-năm giao** (8 năm 2012–2014, 2018–2022 — hai nguồn cùng có giá trị): chênh trung bình **8,49 nghìn người**, max **189,63** (Hà Nội 2014), **104 dòng >1%** — khớp 4/4 với `data/raw/gso/PROVENANCE.md` dòng 63–64. Lưu ý tránh nhầm hai con số 378: **378 dòng pxweb trong file output** (6 năm thiếu lấp mới: 2011, 2015–2017, 2023–2024) ≠ 504 tỉnh-năm giao dùng đối chiếu vintage. File giữ nguyên giá trị từng vintage và **cột `source` ghi rõ từng dòng**; không trộn bừa.
- **Về hai "lỗi" phiên QA trước (đã giải quyết):** phiên QA khi kiểm tra báo (a) số 504/8,49/104 "không tái lập được" (tính lại được 378/≈11,32/92) và (b) `pxweb_V02.01_pop_step2.html` "chỉ chứa 2011–2018, không phải 2011–2020 như PROVENANCE.md dòng 24 ghi". **Kiểm tra trực tiếp trong phiên tài liệu bác bỏ cả hai**: parse HTML cho thấy pop_step2 chứa đủ **2011–2020** (mỗi năm 70 dòng giá trị; 70 = 63 tỉnh + 6 vùng + CẢ NƯỚC), bộ 3 file phủ **2011–2025 đầy đủ**, và tính lại trên đúng phạm vi cho **504 / 8,49 / 189,63 / 104 — khớp PROVENANCE.md**. Con số 378 của phiên QA sinh ra từ premise sai "không có 2019–2020" (và trùng số 378 của output một cách ngẫu nhiên). Kết luận: **PROVENANCE.md GSO đúng, không cần sửa**; mọi sự chênh lệch giữa hai nguồn đã được định lượng và ghi nguồn bằng cột `source`.
- **Hạn chế còn lại:**
  1. **GRDP 2011–2017 không có nguồn công khai còn truy cập được.** Bằng chứng: quét toàn văn **8 file PDF** (7 bản Niên giám 2012–2021 — phủ số liệu 2011–2020 — cộng bản tóm tắt 2016) bằng pymupdf: 0 trang chứa "GRDP"/"sản phẩm tỉnh" (phiên nguồn; phiên QA quét lại 2/8 — bản 2012 và 2021 — cùng kết quả); bảng GRDP/tỉnh đầu tiên xuất hiện ở **Niên giám 2022** (bảng 95, số liệu 2018+) và Niên giám 2025 — 2 bản này được tải để đối chiếu chứ không phải "bằng chứng không có bảng"; `stat.gso.gov.vn` chết DNS; Wayback trả 503 lúc tra. → **KHÔNG nội suy**.
  2. **Lệch vintage dân số có hệ thống** (mục trên) → chạy sensitivity trước khi kết luận (gap [5]).
  3. **Điều kiện dùng PDF Niên giám chưa kiểm tra riêng** (trang điều khoản của nso.gov.vn — NOT_RUN trong phiên này); mức trích dẫn an toàn: "Nguồn: Niên giám Thống kê, Cục Thống kê Việt Nam (nso.gov.vn)".
- **Provenance:** `data/raw/gso/PROVENANCE.md` — bảng "kết quả đã thử và bằng chứng", URL gốc từng bảng/PDF, đối chiếu giữa các nguồn, manifest SHA-256 15 file.
- **Nối tỉnh:** 63/63 tỉnh khớp crosswalk và 63/63 `province_ascii` khớp panel PAPI; không có dòng nào bị bỏ hay bịa mã.

### 3.3 OD Mekong — Open Development Vietnam / Mekong Datahub

- **Nguồn gốc + URL:** datahub mở vận hành bởi **CKAN** (*phần mềm mã nguồn mở quản lý catalog dữ liệu mở*; truy vấn qua API `/api/3/action/package_show`, `package_search`) + curl tải resource trực tiếp; không cần đăng ký (theo `data/raw/odmekong/PROVENANCE.md` dòng 5).
- **Giấy phép (đã xác minh từ file package_show đã lưu, đọc `license_id` trong phiên này):**
  - Dataset nghèo 6 vùng: **`cc-by-sa`** (`_pkg_poor_households.json`, license_title "Creative Commons Attribution Share-Alike") — không còn là suy từ quy ước chung.
  - Dataset COVID: **`cc-by-sa`** (`_pkg_covid_hosp.json`).
  - Dataset *Health Facilities in Mekong Countries 2020*: **ODbL** (`license_id = 'odc-odbl'` — xác minh live bởi phiên QA, resource `ad45d153…` trùng URL dump trong PROVENANCE.md).
  - Quy ước chung của hub: CC BY-SA 4.0 — <https://vietnam.opendevelopmentmekong.net/terms-of-use/>.
- **Hai file COVID là "tàn dư phiên tải" — nói rõ:** `poverty_covid/rate_poor_dataset_en.csv` (rate_poor chỉ Urban/Rural) và `health_covid/quarantine_en.csv` được tải làm **bằng chứng rà catalog** khi tìm thay thế cho dataset poverty theo tỉnh; chúng **không sinh file processed nào và không được dùng trong phân tích**. Được giữ trong raw + manifest để tái lập quá trình tìm kiếm.
- **Mục tiêu chính KHÔNG đạt cấp tỉnh — trung thực báo "partial":**
  - Dataset `poverty-rate` theo tỉnh (URL cũ trong nhiệm vụ) trả **HTTP 404** cả web lẫn CKAN API (`package_show` → "Not Found Error") trên cả hai hostname.
  - Rà catalog (kết quả lưu trong `_search_*.json`): `q=poverty` 439 kết quả; `title:poverty` 81; `"poverty rate"` 10; `"tỷ lệ nghèo"` 3. Phát biểu chính xác theo bằng chứng: **trong các truy vấn đã lưu bằng chứng, không thấy dataset poverty VN cấp tỉnh dạng bảng nào khác**; dataset dạng bảng tốt nhất còn lại là "Proportion of poor households by region in Vietnam from 1998 to 2016" — cấp **6 vùng**. Lưu ý trung thực: một file bằng chứng (`_search_poverty_vn.json`) chứa một truy vấn có **61 kết quả chưa được liệt kê chi tiết** trong ghi chú nguồn — chưa rà từng kết quả, vì vậy không khẳng định tuyệt đối "duy nhất trên toàn catalog" (việc rà bổ sung: gap [7]).
  - Wayback Machine tạm offline lúc tải nên không khôi phục trang cũ được.
  - Hệ quả: **không** đặt tên `external_odm_poverty_63.csv` (sẽ giả 63 tỉnh), mà là `external_odm_poverty_region_1998_2016.csv`.
- **Mục tiêu phụ ĐẠT — bệnh viện 2020:** dump datastore của dataset *Health Facilities in Mekong Countries 2020* gồm **2.169 điểm** bệnh viện toàn khu vực Mekong (423 VN + 1.746 nước Mekong khác — điểm không dùng), encode **EWKB** (*Extended Well-Known Binary* — định dạng nhị phân của hình học không gian; WKT/"Well-Known Text" là bản văn bản của cùng định dạng; cả hai do **PostGIS** — phần mở rộng không gian của PostgreSQL — sử dụng), hệ tọa độ **SRID 4326** = mã của hệ kinh độ–vĩ độ **WGS84** (cùng hệ GPS). Dump **không có cột tỉnh/quốc gia** → script decode tọa độ rồi chạy **point-in-polygon** (*kiểm tra mỗi điểm nằm trong đa giác ranh giới tỉnh nào*) với GeoJSON **`data/raw/boundaries/diaphantinh.geojson`** — provenance của file này (đọc `data/raw/boundaries/PROVENANCE.md`): nguồn Open Development Vietnam (OD Mekong), tải **2026-11-03**, **CC-BY-SA 4.0**, 4.343.853 bytes, SHA-256 `95475ee5…ca6be9`, 63 features với thuộc tính `gid`/`code`/`ten_tinh`; **lưu ý join:** `code` là hằng số 'AD01' (không dùng được), `ten_tinh` lệch 6 tỉnh so với tên chuẩn (cùng bộ alias đã map trong script ODM). Kết quả: **423 điểm thuộc Việt Nam** (sum count = 423 — đếm lại trong phiên này).
- **Schema cột:**
  - `external_odm_poverty_region_1998_2016.csv` (72 dòng): `region_en, region_vi, year, poverty_rate_pct`. 6 vùng × 12 năm (1998, 2002, 2004, 2006, 2008, 2010–2016). Lưu ý đặc thù nguồn: **cột 1998 trùng đúng giá trị cột 2002 ở cả 6 vùng** (file nguồn phân tách bằng TAB dù đuôi `.csv`).
  - `external_odm_health_63.csv` (63 dòng): `province_code, province_ascii, province_vi, year=2020, hospital_count_odm2020, papi_province_code`. `hospital_count_odm2020` = số điểm bệnh viện đếm được trong ranh giới tỉnh.
- **Hạn chế:**
  1. Nghèo chỉ cấp vùng × giai đoạn cũ (1998–2016) → **chỉ dùng diễn giải bối cảnh, tuyệt đối không đưa vào feature cấp tỉnh** (kết cấp vùng với panel tỉnh là lỗi "mismatch aggregation" — gán một giá trị vùng cho mọi tỉnh trong vùng làm cụm/hồi quy bị nhiễu cấu trúc vùng).
  2. Bệnh viện là **snapshot 1 năm (2020)** và đếm **số điểm**, không phải số giường/bệnh nhân; 10 tỉnh có `count = 0` (liệt kê §4 ghi chú 6) — phương pháp làm rõ: gap [8].
  3. QA ghi 2 lỗi nhỏ về **nhãn file bằng chứng** (không sai dữ liệu, các con số 439/81/10/3 đều đúng và đã tái tạo live): `_search_poverty_title.json` thực tế chứa truy vấn "tỷ lệ nghèo" (count=3); `_search_poverty_vn.json` chứa một truy vấn count=61 không được nhắc trong ghi chú.
  4. 3 tên tỉnh lỗi chính tả trong nguồn (`Bà Rịa -Vũng Tàu`, `Cần Thơn`, `Quản Bình`) và 3 tên không dấu (`Kien Giang`, `Đăk Lăk`, `Đăk Nông`) được map tường minh qua bí danh trong `scripts/build_odmekong_external.py` — 63/63 tỉnh khớp crosswalk và khớp `papi_province_code` với panel, không bịa mã.
- **Provenance:** `data/raw/odmekong/PROVENANCE.md` — giấy phép từng dataset (kèm file package_show), bằng chứng 404 + rà catalog, manifest SHA-256 toàn bộ raw files, bảng URL gốc từng resource.

### 3.4 World Bank WDI — chỉ số phát triển thế giới, quốc gia VNM

- **Nguồn gốc + URL:** World Development Indicators (WDI), API v2, quốc gia `VNM`:
  `https://api.worldbank.org/V2/country/VNM/indicator/<MÃ>?downloadformat=csv` (4 chỉ số: `NY.GDP.PCAP.CD` GDP/người USD hiện hành; `SP.URB.TOTL.IN.ZS` % dân số đô thị; `SH.XPD.CHEX.GD.ZS` chi y tế hiện hành % GDP; `SH.MED.BEDS.ZS` giường bệnh trên 1.000 dân).
- **Giấy phép:** **CC BY 4.0** — World Bank Terms of Use for Datasets, <https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets>.
- **Cách tải:** dạng inline `format=csv&per_page=2000` bị API trả XML lỗi *"Invalid format"* (đã thử 2026-11-07) → dùng `downloadformat=csv`, API trả **ZIP**; CSV dữ liệu tách ra `data/raw/worldbank/<MÃ>.csv`, 4 ZIP giữ nguyên trạng thái; xác minh CSV tách ra **byte-identical** với ZIP bằng `sha256sum` 4/4 (theo tuyên bố phiên tải). **Kiểm tra chéo tự động** với JSON API (cùng nguồn, render khác) trong `scripts/build_external_worldbank.py`: **4/4 chỉ số khớp trên 52/52 giá trị** (15+15+14+8 giá trị-năm trong 2010–2024).
- **Schema cột:** long format (*mỗi dòng một giá trị*) — `indicator_code, indicator_name, year, value`; lọc 2010–2024, bỏ hàng trống: **52 dòng** (15 + 15 + 14 + 8 — đếm trong phiên này; dải năm từng chỉ số liệt kê ở §2).
- **Độ phủ:** cấp **quốc gia** × 2010–2024. `NY.GDP.PCAP.CD` và `SP.URB.TOTL.IN.ZS` đủ 15/15 năm; `SH.XPD.CHEX.GD.ZS` 14/15 (**thiếu 2024** — WDI last-updated 2026-10-08 chỉ có tới 2023, giá trị 2024 = null cả trong JSON); `SH.MED.BEDS.ZS` 8/15 (**chỉ 2010–2017** — WDI ngừng cập nhật chuỗi này). Năm 2025 có trong file gốc nhưng ngoài cửa sổ đã chọn → lọc bỏ.
- **Hạn chế:** không có chiều tỉnh (schema tỉnh bỏ qua theo yêu cầu — dùng làm bối cảnh vĩ mô, không nối theo tỉnh); các chuỗi bị cắt **là phía nguồn, không phải lỗi tải** → hiển thị trống trong bảng, **không nội suy**.
- **Provenance:** `data/raw/worldbank/PROVENANCE.md` — URL tải, lỗi format đã gặp, kiểm tra chéo JSON, manifest SHA-256 8 file (4 ZIP + 4 CSV).

### 3.5 Nền tảng: các file "base" trích từ gói replication Mendeley

Các file này có sẵn từ Phase 2 (không phải sản phẩm mới của đợt mở rộng, nhưng là nguồn nền của PCI 2012–2022 và rác thải):

- **Nguồn gốc:** Le et al. — *Replication data and code for "Digital Governance"*, Mendeley Data V1, **CC BY 4.0**, DOI: `10.17632/wbk42j9wc8.1`; file gốc trong `data/raw/mendeley/Replication_package/data/` (theo `data/processed/external_provenance.md` dòng 3–10).
- **File & schema:**
  - `external_pci_63.csv` — 693 dòng (63 tỉnh × 2012–2022), `pci_weighted_score`; 2022 có đủ 63 giá trị (xem §3.1 về câu chuyện Top-30).
  - `external_gso_population_63.csv` — **504 dòng = 63 tỉnh × 8 năm có số liệu trong 2012–2022** (2012–2014, 2018–2022; **thiếu hẳn 2015–2017**): dân số, dân số đô thị, % đô thị (trích Niên giám). Đây là nguồn của 504 dòng `gso_nien_giam_extract` trong file `_full`.
  - `external_gso_waste_63.csv` — **305 dòng**: `province_code, province_ascii, province_vi, year, kg_pc, kg_urb` (rác thải bình quân **đầu người** / khu vực đô thị; đơn vị gốc ghi trong `external_provenance.md` là "kg/người" — xét độ lớn ~0,75 kg ở Hà Nội 2015, chuỗi nhiều khả năng tính **theo ngày**, cần đối chiếu codebook gói Mendeley trước khi phát biểu trong báo cáo — đã đưa vào gap [6]). Độ phủ thật (đếm trong phiên này): **2015, 2016, 2017, 2019 đủ 63 tỉnh; 2018 trống hoàn toàn; 2020 còn 53/63** (thiếu Ben Tre, Binh Thuan, Cao Bang, Da Nang, Ha Nam, Ho Chi Minh City, Kien Giang, Quang Binh, Quang Nam, Son La). Log chuẩn hóa cũ viết "5 năm 2015–2020, thiếu 0 ô giá trị" chỉ đúng nghĩa "không có ô rỗng trong các dòng hiện có", còn **lưới có lỗ**. Lưu ý: file này **không có cột `papi_province_code`** — nối qua `province_ascii` khớp 305/305, cần bổ sung code khi dựng master table (gap [1]).
  - `external_63_panel.csv` — bảng nối ngoài 693 dòng (2012–2022): `papi_province_code, province_code, province_ascii, province_vi, year, pci_weighted_score, gso_pop_total_thousand, gso_pop_urban_thousand, gso_urban_residence_pct_derived, kg_pc, kg_urb` (đọc header trong phiên này).
- **Hạn chế:** các file này được `external_pci_63_full.csv` và `external_gso_population_63_full.csv` thay thế (thêm năm 2011/2023/2024 và cột `source`); `external_gso_waste_63.csv` **chưa có** bản "full" hơn.
- **Provenance:** `data/processed/external_provenance.md`.

---

## 4. Ma trận độ phủ và khoảng trống còn lại

### 4.1 Ma trận độ phủ — nguồn ngoài × panel PAPI (63 tỉnh × 2011–2024 = 882 ô tỉnh-năm)

Kiểm chứng: các con số ô/dòng dưới đây được **đếm lại trực tiếp** trong phiên tài liệu từ **8 file CSV** (7 file external mới đếm chi tiết + `external_63_panel.csv` kiểm header/tổng dòng — danh sách chính xác ở §1.4 mục 1); các chi tiết tỉnh được liệt kê lại từng tên (Top-30 hai tập, 10 tỉnh thiếu, 10 tỉnh count=0). Các tuyên bố mạng của phiên tải (curl 200 OK pcivietnam.vn, DNS chết `stat.gso.gov.vn`, Wayback 503, manifest SHA-256, đối chiếu CSV↔JSON của WDI, sửa hoán tên Bắc Giang/Bắc Cạn 2011) **không chạy lại** — ghi nhận theo tuyên bố nguồn; riêng robots.txt pxweb/papi và độ lệch vintage GSO đã kiểm/tính lại trực tiếp (§1.4 mục 3–6).

Ký hiệu: ✓ = lấp đủ 63/63 tỉnh · ◐ = một phần · ✗ = trống hoàn toàn · CS = chỉ số.

**Bảng 1 — Ma trận chính: nguồn × giai đoạn (ô = số tỉnh có giá trị / 63)**

| Nguồn (file trong data/processed/) | Đơn vị | 2011 | 2012–2014 | 2015–2017 | 2018–2020 | 2021–2022 | 2023 | 2024 | Khớp nối vào panel PAPI |
|---|---|---|---|---|---|---|---|---|---|
| **Panel PAPI (mỏ neo)** `papi_panel_63_2011_2024.csv` | 63 tỉnh × 37 cột chỉ số (8 dimension + 29 sub-indicator) | 63/63 ✓ | 63/63 ✓¹ | 63/63 ✓ | 63/63 ✓¹ | 63/63 ✓¹ | 63/63 ✓¹ | 63/63 ✓¹ | — (chính nó) |
| **PCI** `external_pci_63_full.csv` | 63 tỉnh | 63/63 ✓ | 63/63 ✓ | 63/63 ✓ | 63/63 ✓ | 63/63 ✓ | 30/63 ◐² | 30/63 ◐² | 882/882 cặp (cả code lẫn ascii) |
| **GSO dân số** `external_gso_population_63_full.csv` | 63 tỉnh | 63/63 ✓³ | 63/63 ✓ | 63/63 ✓³ | 63/63 ✓ | 63/63 ✓ | 63/63 ✓³ | 63/63 ✓³ | 882/882 cặp |
| **GSO GRDP/người** `external_gso_grdp_63.csv` | 63 tỉnh | ✗ 0/63 | ✗ 0/63 | ✗ 0/63 | 63/63 ✓ | 63/63 ✓ | 63/63 ✓ | 63/63 ✓ (Sơ bộ) | 441/441 cặp |
| **GSO rác thải** `external_gso_waste_63.csv` | 63 tỉnh | ✗ | ✗ | 63/63 ✓ | 2018 ✗ · 2019 63/63 ✓ · 2020 53/63 ◐⁴ | ✗ | ✗ | ✗ | 305/305 (qua province_ascii)⁵ |
| **ODM bệnh viện** `external_odm_health_63.csv` | 63 tỉnh | ✗ | ✗ | ✗ | 2018 ✗ · 2019 ✗ · 2020 63/63 ◐⁶ | ✗ | ✗ | ✗ | 63/63 cặp |
| **ODM nghèo — 6 vùng, KHÔNG cấp tỉnh** `external_odm_poverty_region_1998_2016.csv` | 6 vùng | 6/6 vùng⁷ | 6/6 vùng⁷ (2002–2014) | 2015–16: 6/6 vùng⁷ · 2017 ✗ | ✗ | ✗ | ✗ | ✗ | n/a — không nối theo tỉnh |
| **WDI — quốc gia VNM, KHÔNG cấp tỉnh** `external_worldbank_vnm.csv` | quốc gia | 4/4 CS⁸ | 4/4 CS⁸ | 4/4 CS⁸ | 3/4 CS⁸ | 3/4 CS⁸ | 3/4 CS⁸ | 2/4 CS⁸ | n/a — cấp quốc gia |

**Bảng 2 — Chi tiết theo từng năm (các nguồn cấp tỉnh; số tỉnh có giá trị; «—» = không có trong nguồn)**

| Nguồn cấp tỉnh | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PCI (có điểm) | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 30 | 30 |
| Dân số (tổng) | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| GRDP/người | — | — | — | — | — | — | — | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| Rác thải kg_pc | — | — | — | — | 63 | 63 | 63 | — | 63 | 53 | — | — | — | — |
| Bệnh viện (count) | — | — | — | — | — | — | — | — | — | 63 | — | — | — | — |

**Tổng hợp ô external cấp tỉnh có giá trị trên 882 ô của panel:** PCI 816/882 (92,5%) · dân số tổng 882/882 (100%) · dân số đô thị/% đô thị 504/882 (57,1%) · GRDP 441/882 (50,0%) · rác thải 305/882 (34,6%) · bệnh viện 63/882 (7,1%).

**Ghi chú (các mục đánh dấu ✓ đã đếm lại trực tiếp trong phiên tài liệu):**

1. **PAPI nội bộ không đầy 100%** *(theo phiên ma trận — không tái đếm trong phiên tài liệu):* d7, d8, sd_2_4, sd_7_1–3, sd_8_1–2 chỉ có giá trị từ 2018 (sd_8_3 từ 2019; sd_5_2 dừng ở 2020); các chỉ số còn lại thiếu rải rác: 2014 chỉ 61 tỉnh có giá trị, 2021 chỉ 60, 2022: 61–62, 2023–2024: 61.
2. **PCI 2023 & 2024 ✓:** đủ 63 dòng/năm nhưng 33 ô điểm trống mỗi năm (tổng 66); không nội suy, không tự tính weighted score từ sub-index. Tập Top-30 hai năm **không cùng tập** ✓: 28 tỉnh chung; chỉ 2023 có Dak Nong, Tien Giang; chỉ 2024 có Ha Nam, Thai Binh. Vì sao 2022 vẫn đủ 63 điểm: §3.1 (kênh extract Mendeley vs kênh chính thức Top-30).
3. **Vintage dân số ✓:** 2011, 2015–2017, 2023–2024 lấp từ pxweb V02.01 (378 dòng = 6 năm × 63, `source = gso_pxweb_V02.01`, urban/% đô thị trống đúng 378 dòng này); 504 dòng 2012–2014 + 2018–2022 từ Niên giám (`gso_nien_giam_extract`). Lệch vintage đã định lượng và tái lập ✓: trên 504 tỉnh-năm giao, chênh trung bình 8,49 nghìn người, max 189,63 (Hà Nội 2014), 104 dòng >1% — khớp PROVENANCE.md (hai "lỗi" phiên QA trước bị bác bỏ — §3.2).
4. **Rác thải ✓:** lưới thật là 2015–2017 + 2019 (đủ 63 tỉnh) + 2020 còn 53/63 (thiếu 10 tỉnh liệt kê ở §3.5); **2018 trống hoàn toàn**.
5. File rác thải không mang cột `papi_province_code` — nối qua `province_ascii` khớp 305/305; cần thêm code khi dựng master table.
6. **hospital_count_odm2020 ✓:** tổng 423 điểm khớp tuyên bố; 10 tỉnh count = 0 (Bac Kan, Tuyen Quang, Dien Bien, Lai Chau, Son La, Bac Giang, Quang Tri, Ninh Thuan, Binh Phuoc, Ben Tre) — phương pháp phân biệt 0-thật vs lỗi map: gap [8].
7. **ODM nghèo KHÔNG đạt cấp tỉnh:** dataset `poverty-rate` theo tỉnh đã 404 trên ODM; chỉ còn 6 vùng × 12 năm rải rác (72/72 ô đầy) ✓; cột 1998 trùng giá trị 2002 (đặc thù file nguồn).
8. **WDI ✓:** NY.GDP.PCAP.CD và SP.URB.TOTL.IN.ZS đủ 15/15 năm 2010–2024; SH.XPD.CHEX.GD.ZS 14/15 (thiếu 2024); SH.MED.BEDS.ZS 8/15 (2010–2017) — đếm trực tiếp từ CSV.

### 4.2 Khoảng trống còn lại và việc cần làm (thứ tự theo giá trị/công sức)

> **Trạng thái cập nhật 2026-11-07 (phiên dựng master table + external validation):**
> [1] [2] [8] [9] **ĐÃ ĐÓNG** · [3] **ĐÓNG dạng quyết định thiết kế** · [6] **ĐÓNG**
> (kèm lưu ý tài liệu ngoài) · nhận định gốc của [5] **VÔ HIỆU** · [7] [10] **MỞ,
> cần tải thêm / quyết định nhóm**. Bằng chứng của từng trạng thái ghi ngay trong
> mục; số liệu chi tiết xem `results/external_master_summary.md` và
> `results/external_validation.md`.

1. **[1] ĐÃ ĐÓNG — master table phân tích:** `scripts/build_external_master.py`
   nối `papi_panel_63_2011_2024.csv` + `external_pci_63_full.csv` +
   `external_gso_population_63_full.csv` + `external_gso_grdp_63.csv` +
   `external_gso_waste_63.csv` + `external_odm_health_63.csv` theo khóa
   `(province_code, year)` (= `papi_province_code`) với `validate="one_to_one"`
   — giữ đúng **882 dòng × 59 cột**, kèm **mask thiếu tường minh từng nguồn**
   (`pci_present` 816, `pop_present` 882, `grdp_present` 441, `odm_present` 63,
   `waste_present` 305) và mask `papi_sd46_present` 869 (13 ô tỉnh-năm thiếu
   sd_4_2/sd_6_1 — ví dụ 2018 thiếu Quảng Ninh + Đồng Tháp, 2021 thiếu 3 tỉnh:
   mask phải xuống cấp tỉnh-năm). Cột `source` giữ lại làm flag vintage dân số
   (504 Niên giám / 378 pxweb V02.01). `papi_province_code` đã gán cho
   `external_gso_waste_63.csv` qua `province_ascii` — **khớp 305/305, bằng với
   `province_code`** (kiểm chứng trong script). Output:
   `data/processed/external_master_63_2011_2024.csv` +
   `results/external_master_summary.md`.
2. **[2] ĐÃ ĐÓNG — giao thức external validation:** `scripts/external_validation.py`
   (output `results/external_validation.md` + `.csv` + 4 hình
   `results/figs/external_*`). Validation CHÍNH trên lưới đầy 2011–2022
   (**756 ô** — bản nháp ma trận trước đây ghi 753 là lỗi cộng): PCI theo nhãn
   cụm của model đóng băng (`results/predict_all_years.csv`), join được **747
   điểm** (9 ô thiếu nhãn), ANOVA F(3,743) = 9,04 (p ≈ 6,9e-06) + Kruskal–Wallis
   H ≈ 31,78 (p ≈ 5,8e-07) — khác biệt có ý nghĩa; Top-30 2023–2024 chỉ là
   kiểm tra phụ với cảnh báo chọn mẫu. Không nội suy 66 ô trống, không tự tính
   weighted score từ sub-index.
3. **[3] ĐÓNG dạng quyết định thiết kế — GRDP 2011–2017:** vòng tìm cuối đã
   chạy ở phiên trước (7 Niên giám 2012–2021: 0 trang có bảng GRDP tỉnh;
   bảng đầu tiên ở Niên giám 2022, tr.260–261, chỉ từ 2018 — §3.2) → chốt:
   **GRDP chỉ dùng cửa sổ 2018–2024, dân số là normalizer chính xuyên panel,
   không nội suy 441 ô 2011–2017**. Đã thực thi trong
   `scripts/external_validation.py` §4 (hình GRDP theo cụm, mask tường minh 11
   ô thiếu nhãn trong cửa sổ; ghi chú 2024 = Sơ bộ).
4. **[4] Cửa sổ khả dụng của chính panel PAPI:** chọn feature cho STING theo cửa sổ khả dụng — hai cấu hình: lõi 8 dimension xuyên 2011–2024 và **mở rộng 37 cột cho 2018–2024 nhưng với mask thiếu tường minh** (sd_5_2 chỉ tới 2020, sd_8_3 chỉ từ 2019 — các ô này để trống/không dùng trong khoảng tương ứng), thay vì giả định lưới đầy đủ.
5. **[5] VÔ HIỆU — nhận định gốc của phiên QA sai phạm vi:** tuyên bố
   "PROVENANCE.md GSO thật ra ghi sai / file HTML chỉ chứa 2011–2018" và bộ số
   378/11,32/92 chỉ tái lập được khi **sai phạm vi năm** của file HTML. Kiểm
   chứng độc lập (tái lập trực tiếp trong phiên 2026-11-07 bằng hàm parse của
   `scripts/build_gso_grdp_pop.py`): `pxweb_V02.01_pop_step2.html` chứa dữ liệu
   thật 2019–2020 (Hà Nội 8.093,90 / 8.246,54 nghìn người), bộ 3 file phủ
   2011–2025; trên đúng phạm vi giao 504 tỉnh-năm: chênh trung bình **8,49**,
   max **189,63** (Hà Nội 2014), **104** dòng >1% — khớp **4/4** với
   `data/raw/gso/PROVENANCE.md` dòng 63–64. **PROVENANCE.md GSO đúng — không
   sửa số vintage.** Việc còn lại (thuộc phiên model, không phải phiên dữ liệu):
   chạy STING trên chuỗi dân số chỉ-Niên-giám (504 dòng) vs hỗn-hợp-vintage
   (882 dòng) nếu muốn chứng minh cụm không phải artifact của lệch vintage.
6. **[6] ĐÓNG — rác thải:** (a) **lỗ 2018/2020 là phía nguồn, không phải extract
   bỏ sót** — kiểm chứng trực tiếp trong phiên 2026-11-07: file gốc
   `data/raw/mendeley/Replication_package/data/gso_waste_wide_from_upload.csv`
   đúng 305 dòng (2015/2016/2017/2019 = 63 dòng/năm; 2020 = 53; **2018 không có
   dòng nào**) — byte-cùng cấu trúc với `external_gso_waste_63.csv` → chấp nhận
   lỗ, định vị rác thải là external check (chuỗi ngắn, 34,6% panel), không đưa
   vào feature chính; (b) **đơn vị `kg_pc`/`kg_urb`**: nhãn trong chính gói
   replication `code/validate_gso.py:11` — "GSO collected **kg/person/day**"
   (và "kg/urban resident/day") → phát biểu "kg/người/ngày" dựa trên nhãn
   code của gói; văn bản GSO gốc (Supplementary S5) là tài liệu ngoài — cần tải
   thêm nếu muốn chốt văn bản thay vì nhãn code.
7. **[7] MỞ — nghèo cấp tỉnh thay cho 6 vùng ODM (needs-new-download):** nếu muốn đưa nghèo vào feature/validation — (a) rà nốt **61 kết quả** của truy vấn chưa liệt kê trong `_search_poverty_vn.json` để đóng cửa khả năng bỏ sót (file hiện **chỉ lưu 30/61 items** — đếm lại trong phiên 2026-11-07; tùy chọn fetch `rows=61` để đóng kho lưu trữ); (b) thử lại **Wayback Machine** cho trang `poverty-rate` đã 404 (một lần, rẻ; nếu vẫn offline/chết nội dung → chốt bỏ đường này); (c) chuyển hẳn sang nguồn cấp tỉnh khác: số hộ nghèo MOLISA theo tỉnh, bảng nghèo World Bank Vietnam.
8. **[8] ĐÃ ĐÓNG — ODM health 10 tỉnh count=0:** kết luận "0-thật (nguồn điểm
   không phủ)" — dump 2.169 điểm đã point-in-polygon với bộ alias tên tỉnh đã
   kiểm tra (script ODM map 6 tên lệch của geojson), 10 tỉnh giữ 0. Đã thực
   thi: `scripts/external_validation.py` §3 — mật độ/1.000 dân theo cụm 2020
   (ODM + dân số GSO) với **ghi chú bắt buộc "10 tỉnh count=0 là 0-thật"**
   ngay trên hình `results/figs/external_health_density_2020.png` và trong
   `results/external_validation.md`. Cân nhắc dump ODM các năm khác để có panel
   hạ tầng thay vì 1 snapshot 2020 — vẫn là tùy chọn tương lai.
9. **[9] ĐÃ ĐÓNG — WDI (chỉ tài liệu):** không có việc tải thêm vì truncate là
   phía nguồn. Đã thực thi: `scripts/external_validation.py` §5 — panel 2×2
   2010–2024 với ghi chú tường minh trên hình (giường bệnh dừng 2017, chi y tế
   thiếu 2024 — giữ ô trống, không nội suy) và bảng trạng thái chuỗi trong
   `results/external_validation.md` §5.
10. **[10] Phụ thuộc tái lập:** bổ sung `shapely`, `xlrd`, `pypdf` (và `scipy` — dùng cho kiểm định, đã có sẵn trong user site-packages máy lập) vào `requirements.txt` (hoặc requirements-dev) ở phiên kế tiếp — hiện thiếu, tái lập trên máy khác sẽ hỏng ngay bước ODM, PCI 2011 và kiểm định thống kê (chi tiết §6.3). *Quyết định của nhóm — tài liệu không tự sửa `requirements.txt` vì ngoài phạm vi.*

**Phân công đề xuất** (nhóm 2 sinh viên chủ nhiệm chốt, theo README): [1]+[2] một phiên duy nhất (master table + giao thức validation) trước khi chạy lại phân tích; [10] 5 phút sửa file khi chạm pipeline; [5]–[8] xếp sau [1]; [3], [7], [9] làm song song, không chặn báo cáo.

### 4.3 Câu hỏi dự kiến khi demo/thi (chuẩn bị trước)

- **"Dữ liệu sau sáp nhập 34 tỉnh thì sao?"** PCI 2025 là cấu trúc mới 34 tỉnh sau sáp nhập với 9 chỉ số thành phần (§3.1), nên panel 63 tỉnh 2011–2024 kết thúc tại 2024. Nối tiếp kỳ sau là quyết định thiết kế riêng (crosswalk 34 tỉnh mới, panel riêng) — ngoài phạm vi tài liệu này, nhưng cần một câu trả lời chuẩn bị sẵn.
- **"Vì sao không có nghèo cấp tỉnh?"** — trả lời bằng §3.3 (404 + rà catalog) và kế hoạch [7].
- **"10 tỉnh không có bệnh viện là lỗi không?"** — trả lời bằng gap [8] (quy trình 3 bước).

---

## 5. Giá trị cho đồ án học máy

### 5.1 External validation của cụm STING là gì?

STING là **học không giám sát**: không có nhãn "đúng" để tính accuracy. Nếu chỉ đo bằng chính PAPI (ví dụ inertia trên grid), ta chỉ chứng minh thuật toán tự nhất quán, không chứng minh các cụm **có nghĩa ngoài đó**. **External validation** (kiểm định ngoài) = lấy một biến **chưa từng dùng khi clustering**, đến từ khung đo **độc lập** về mặt tổ chức và phương pháp luận, rồi kiểm tra các cụm có phân biệt được nó hay không:

- Gán mỗi tỉnh-năm một nhãn cụm STING, rồi so sánh phân phối `pci_weighted_score` giữa các cụm: **ANOVA** (kiểm định F — so sánh **trung bình** giữa các nhóm) và/hoặc **Kruskal–Wallis** (phi tham số — so sánh **phân phối/hạng** giữa các nhóm, thường diễn giải qua trung vị); dùng cả hai để không phụ thuộc giả định phân phối chuẩn.
- **Vì sao PCI là external validation mạnh nhất hiện có:** PCI thang 0–100, do VCCI–USAID soạn bằng **khảo sát doanh nghiệp** — hoàn toàn tách khỏi PAPI (khảo sát hộ dân, CECODES/UNDP). Hai nguồn không dùng chung bảng hỏi, đơn vị khảo sát hay cách tính điểm, nên tương quan cụm–PCI không thể là "rò rỉ thang đo" (data leakage giữa feature và validation).
- **Lưới chạy:** chính là lưới đầy 2011–2022 (756 ô đủ 63 tỉnh). **60 ô Top-30 của 2023–2024 chỉ dùng làm kiểm tra phụ** — vì nhà xuất bản chỉ công bố tỉnh tốt (chọn mẫu — *selection bias*: trung bình mẫu bị kéo lên so với tổng thể), nên so sánh Top-30 với panel đủ 63 tỉnh sẽ lệch.

### 5.2 PCI là mỏ neo xuyên năm để đối chiếu "nhảy thang đo" PAPI

- **Vấn đề:** README (mục "Lưu ý thang đo", `README.md:131`–`140`) ghi rõ: `check_data.py` flag cột có bước nhảy mean năm > 0,25 (heuristic); `sd_5_4` có thay đổi khoảng điểm ghi trong workbook; thang dimension 1–10 "không tự chứng minh tính tương đương xuyên năm"; PAPI có nội dung thay đổi năm 2021. Khi một năm PAPI nhảy, ta **không biết** đó là tỉnh thay đổi thật hay PAPI đổi thang.
- **Mỏ neo (anchor)** = một chuỗi tham chiếu ổn định, đo cùng khái niệm, do tổ chức khác công bố. PCI 2011–2022 đủ **12 năm liên tục, cùng một cách tính điểm tổng, cùng một đơn vị thực hiện** — đủ dài để đặt cạnh từng năm của PAPI.
- **Cách dùng (giải thích cho người học):** nếu cụm STING sắp xếp lại đúng lúc PAPI nhảy thang nhưng **PCI cùng năm không phản ánh sự sắp xếp lại đó** → nghi vấn về thang đo PAPI tăng; nếu **cả PCI lẫn PAPI** cùng phản ánh một thay đổi → khả năng cao là thay đổi cấu trúc thật của tỉnh. Đây là **chẩn đoán chéo, không phải chứng minh tuyệt đối** — PCI đo khái niệm khác (môi trường kinh doanh theo doanh nghiệp) nên phản ứng trễ/nhẹ hơn là bình thường; trình bày như bằng chứng phụ, đừng viết như phép thử quyết định.
- Lưu ý thực thi: chỉ dùng đoạn PCI có điểm đủ (2011–2022); phần 2023–2024 thiếu 33 tỉnh không thể làm anchor cho toàn 63 tỉnh.

### 5.3 Dân số & GRDP: normalizer và biến kiểm soát cho hồi quy

- **Dân số** (`gso_pop_total_thousand`, đủ 882/882 ô, có cột `source` phân biệt vintage) là **normalizer** (biến chuẩn hóa quy mô): biến đếm thô như `hospital_count_odm2020` cần đổi thành **mật độ trên 1.000 dân** trước khi so tỉnh, vì tỉnh to đương nhiên nhiều bệnh viện hơn — so sánh count thô là sai logic quy mô. Dân số cũng để kiểm tra cụm STING có bám gradient quy mô–đô thị hóa hay không (cụm chỉ chia tỉnh to/nhỏ thì ít giá trị xã hội).
- **GRDP/người** (`grdp_per_capita_million_vnd`) là **biến kiểm soát kinh tế cấp tỉnh duy nhất** trong bộ dữ liệu cho phần hồi quy (hiện hồi quy chỉ có 8 dimension `d1–d8` của PAPI làm biến giải thích — README gọi nhóm này là "sub-dimension", cùng một nhóm biến, đừng nhầm với 29 sub-indicator `sd_*` — `README.md:79`–`87`). Vì chỉ phủ 2018–2024, mọi phân tích dùng GRDP phải **tách cửa sổ 2018–2024**; phần còn lại của panel dùng dân số làm mỏ neo xuyên năm.
- **WDI quốc gia** dùng được trong hồi quy dưới dạng **year effects** (dummy cho từng năm — giá trị giống nhau cho mọi tỉnh trong cùng một năm, hấp thụ sốc chung toàn quốc như COVID 2020–2021). Vì vậy WDI không phải "feature cấp tỉnh" — quy tắc ở §5.5 mục 3 nói về feature cấp tỉnh, hai điều này nhất quán (nói rõ ở đó).
- **Cảnh báo phương pháp cho cả hai:** GRDP 2024 là số "Sơ bộ" (có thể bị sửa sau); dân số trộn hai vintage — chạy sensitivity (gap [5]) trước khi kết luận.

### 5.4 WDI và ODM: vai trò bối cảnh

- **WDI (quốc gia):** đặt kết quả cụm/hồi quy vào bối cảnh vĩ mô trong báo cáo (tăng trưởng GDP/người, đô thị hóa, chi y tế công) và làm year effects (§5.3). Không thể làm feature cấp tỉnh — **nghĩa là gì**: mọi tỉnh trong cùng một năm có cùng giá trị, nên biến này không phân biệt được tỉnh nào với tỉnh nào; nó chỉ giải thích biến động **theo năm**.
- **ODM nghèo (6 vùng):** chỉ dùng cho **diễn giải bối cảnh** trong phần thảo luận (vd so sánh gradient cụm với bản đồ nghèo vùng 2010–2016). Không đưa vào feature cấp tỉnh (mismatch aggregation, §3.3).
- **ODM bệnh viện (2020):** dùng một lần như external check cho gradient hạ tầng: cụm STING có tách được tỉnh giàu/nghèo hạ tầng y tế không — sau khi đổi thành mật độ/1.000 dân và làm rõ 10 tỉnh count = 0.

### 5.5 Những gì tuyệt đối không làm (danh sách ngắn cho phòng thi)

1. **Không nội suy** ô thiếu (66 ô PCI, 441 ô GRDP 2011–2017, 2018 rác thải, WDI thiếu) — để trống + mask thiếu tường minh.
2. **Không tự tính PCI weighted score từ sub-index** cho 33 tỉnh thiếu 2023–2024 — số phái sinh ≠ điểm chính thức.
3. **Không đưa biến cấp vùng/quốc gia vào feature cấp tỉnh** (nghèo 6 vùng, WDI). Ngoại lệ có kiểm soát: WDI vào **hồi quy** dạng year effects — đó không phải feature cấp tỉnh vì giá trị giống nhau cho mọi tỉnh trong năm (xem §5.3); hai quy tắc này không mâu thuẫn.
4. **Không so biến đếm thô giữa các tỉnh** (bệnh viện `hospital_count`) — chuẩn hóa thành mật độ/1.000 dân trước. Riêng rác thải **đã là chỉ tiêu bình quân đầu người** (`kg_pc`, `kg_urb`) nên không cần chuẩn hóa thêm; việc cần chốt là **đơn vị** (ngày hay năm — gap [6]).
5. **Không trộn Top-30 2023–2024 với panel đủ 63 tỉnh** trong cùng một thống kê so sánh.

---

## 6. Cách tái lập

### 6.1 Bản đồ script → file

| Script | Input | Output |
|---|---|---|
| `scripts/build_external_panel.py` | extract SOURCE_EXTRACTED trong `data/raw/mendeley/Replication_package/data/` + `province_crosswalk_63.csv` | `external_pci_63.csv`, `external_gso_population_63.csv`, `external_gso_waste_63.csv`, `external_63_panel.csv`, `external_provenance.md` |
| `scripts/build_pci_full.py` | `data/raw/pci/` (workbook 2011/2023/2024, trang xếp hạng HTML 3 năm) + `external_pci_63.csv` (base 2012–2022) | `external_pci_63_full.csv` |
| `scripts/gso_pxweb_probe.py` | mạng: `pxweb.nso.gov.vn/api/v1` (thăm dò, chỉ in stdout) | không ghi file dữ liệu |
| `scripts/gso_pxweb_fetch.py` | mạng: POST form WebForms pxweb (robots.txt không cấm — §3.2) | HTML thô vào `data/raw/gso/pxweb_*.html` (5 file) |
| `scripts/build_gso_grdp_pop.py` | `data/raw/gso/` (5 HTML pxweb + Niên giám PDF để đối chiếu) + extract Mendeley (base dân số) | `external_gso_grdp_63.csv`, `external_gso_population_63_full.csv` |
| `scripts/build_odmekong_external.py` | `data/raw/odmekong/` (CSV nghèo 6 vùng, dump bệnh viện EWKB) + `data/raw/boundaries/diaphantinh.geojson` (OD Mekong, 2026-11-03, CC-BY-SA 4.0 — `data/raw/boundaries/PROVENANCE.md`) | `external_odm_poverty_region_1998_2016.csv`, `external_odm_health_63.csv` |
| `scripts/build_external_worldbank.py` | `data/raw/worldbank/<MÃ>.csv` (tách từ ZIP) + JSON API (kiểm tra chéo — cần mạng) | `external_worldbank_vnm.csv` (+ tạo lại `data/raw/worldbank/PROVENANCE.md`) |

### 6.2 Thứ tự lệnh (chạy từ thư mục gốc repo)

```powershell
# (1) Tải dữ liệu thô một lần (đã làm ngày 2026-11-07; file raw đã nằm trong data/raw/)
#     PCI: curl workbook + trang xếp hạng từ pcivietnam.vn
#     GSO: python -E scripts/gso_pxweb_probe.py tree ...   (thăm dò)
#          python -E scripts/gso_pxweb_fetch.py <table_url> <out_html> [giữ_cột2.txt]
#     OD Mekong / World Bank: CKAN API + curl / API WDI downloadformat=csv

# (2) Chuẩn hóa base từ gói Mendeley (đã chạy, sinh 4 file external_* + provenance)
python -E scripts/build_external_panel.py

# (3) Bổ sung PCI 2011/2023/2024 -> external_pci_63_full.csv
python -E scripts/build_pci_full.py

# (4) Chuẩn hóa GSO -> external_gso_grdp_63.csv + external_gso_population_63_full.csv
python -E scripts/build_gso_grdp_pop.py

# (5) Chuẩn hóa OD Mekong -> poverty 6 vùng + bệnh viện 63 tỉnh (point-in-polygon)
python -E scripts/build_odmekong_external.py

# (6) Chuẩn hóa WDI -> external_worldbank_vnm.csv (bước này gọi JSON API để kiểm tra chéo -> cần mạng)
python -E scripts/build_external_worldbank.py
```

Cờ `-E` bảo Python bỏ qua biến môi trường `PYTHONPATH`/`PYTHONHOME` — chạy đúng như các PROVENANCE.md đã ghi (`python -E scripts/<script>.py`). **Đừng** thay bằng `-I` cho các script cần `pandas`/`shapely`/`xlrd`: `-I` loại cả user site-packages, nơi các thư viện bổ sung này đang cài (đã kiểm tra: `python -I -c "import shapely"` lỗi `ModuleNotFoundError`, còn `python -E ...` thấy `shapely 2.1.2, xlrd 2.0.2, pypdf 6.18.0, pandas 2.3.3`). *(Các lệnh `python -I` chỉ dùng khi kiểm tra số liệu bằng stdlib như trong §1.4.)*

### 6.3 Môi trường, dependency và trạng thái repo

- Trong `requirements.txt` (pandas 2.3.3, numpy, openpyxl, …) **chưa có** `shapely` (point-in-polygon của ODM), `xlrd` (đọc `.xls` PCI 2011) và `pypdf` (trích PDF kiểm chứng PCI) — ba gói đang nằm trong **user site-packages** của máy lập (`pip install --user shapely xlrd pypdf` nếu tái lập trên máy khác). Cho đến khi gap [10] được chốt (bổ sung vào requirements), tái lập trên máy mới sẽ hỏng ở bước ODM và PCI 2011 nếu chỉ `pip install -r requirements.txt`.
- Các script chuẩn hóa **chỉ đọc file raw và ghi file mới** vào `data/processed/` — không sửa file gốc trong `data/raw/`, không đụng panel PAPI hay file nguồn khác.
- **Trạng thái repo hiện tại** (`git status --short`, 2026-11-07): 1 file modified — `README.md` (do phiên tài liệu sửa mục cấu trúc + nguồn dữ liệu) — cộng các file **untracked** mới: `data/raw/{pci,gso,odmekong,worldbank}/`, `data/processed/external_*.csv` + `external_provenance.md`, 7 script dữ liệu, `reports/external_data_expansion.md`. Các phiên **dữ liệu** (chạy build script) khi đó chưa sửa file có sẵn nào; việc sửa README thuộc **phiên tài liệu**, không thuộc phiên dữ liệu.
- Manifest SHA-256 nằm trong từng `data/raw/*/PROVENANCE.md` — dùng `sha256sum` (Git Bash) để đối chiếu khi tái lập.

### 6.4 Trích dẫn nhanh khi demo/thi (mỗi nguồn một dòng)

- **PAPI:** CECODES / VFF-CRT / RTA / UNDP — <https://papi.org.vn/du-lieu-papi/>. Giấy phép: **không có file LICENSE kèm gói tải về**; `data/raw/papi/PROVENANCE.md` ghi "dữ liệu công bố công khai cho mục đích nghiên cứu/học tập theo trang nguồn… trích dẫn nguồn khi dùng lại". Kiểm tra mạng 2026-11-07: GET `robots.txt` của papi.org.vn bị trả trang thách thức Cloudflare (không đọc được — không cố vượt), nên điều khoản chi tiết của trang **chưa kiểm được online**; mức an toàn khi thi: trích nguồn + URL + cụm "dữ liệu công khai theo papi.org.vn".
- **PCI:** VCCI – USAID, pcivietnam.vn — "Nguồn: PCI Việt Nam (VCCI – USAID)" theo [chính sách trích dẫn](https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html).
- **GSO/NSO:** "Nguồn: Cục Thống kê Việt Nam (pxweb.nso.gov.vn / Niên giám Thống kê, nso.gov.vn)" — dữ liệu thống kê chính thức, trang bảng ghi "Bản quyền: Không"; điều khoản riêng cho PDF Niên giám chưa kiểm tra (NOT_RUN).
- **OD Mekong:** "Nguồn: Open Development Vietnam / OD Mekong" — nghèo 6 vùng + COVID: **CC BY-SA** (license_id xác minh từ package_show); riêng *Health Facilities in Mekong Countries 2020*: **ODbL**; nếu sản xuất bản phái sinh thì giữ điều khoản share-alike. GeoJSON ranh giới 63 tỉnh (OD Vietnam): **CC-BY-SA 4.0** — `data/raw/boundaries/PROVENANCE.md`.
- **World Bank:** "Nguồn: World Development Indicators, The World Bank (CC BY 4.0)".
- **Gói replication Mendeley:** Le et al., CC BY 4.0, DOI 10.17632/wbk42j9wc8.1.
- Bằng chứng nguồn gốc chi tiết (URL, ngày tải, hash): các `PROVENANCE.md` trong `data/raw/*/` và `data/processed/external_provenance.md`.
