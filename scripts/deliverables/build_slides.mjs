/**
 * Editable 15-slide STING–PAPI defense presentation, authored with @oai/artifact-tool.
 * Matches the upgraded 15-slide visual specification implemented in slides_author.py.
 * Evidence comes from build_slides.py --data-only. No source results are changed.
 * The optional Artifact authoring path requires a runtime that provides that
 * package. The Python entry point supports slides_author.py and the portable snapshot.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, i, all) => {
  if (value.startsWith('--')) pairs.push([value.slice(2), all[i + 1]]);
  return pairs;
}, []));
if (!args.data || !args.output) throw new Error('Usage: build_slides.mjs --data evidence.json --output deck.pptx [--render-dir directory]');
const packageRoot = process.env.ARTIFACT_NODE_MODULES || process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
let artifact;
try {
  artifact = packageRoot
    ? await import(pathToFileURL(path.join(packageRoot, '@oai/artifact-tool/dist/artifact_tool.mjs')).href)
    : await import('@oai/artifact-tool');
} catch (error) {
  throw new Error('Artifact authoring requires a runtime with @oai/artifact-tool. Use slides_author.py or the portable Python build.', { cause: error });
}
const { Presentation, PresentationFile } = artifact;
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const d = JSON.parse(await fs.readFile(args.data, 'utf8'));
const ppt = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const FONT = 'Arial';
const C = { navy: '#0F2B46', teal: '#146F78', blue: '#127EA1', orange: '#B9562A', gold: '#B17E20', gray: '#566574', light: '#F3F6F8', line: '#D7E0E7', ink: '#1B2834', white: '#FFFFFF', paleBlue: '#E9F2F8', paleTeal: '#E8F4F2' };
const REPO = 'https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/';
const dec = (v, n = 3) => Number(v).toFixed(n).replace('.', ',').replace('-', '−');
const pct = (v, n = 1) => `${(Number(v) * 100).toFixed(n).replace('.', ',')}%`;
const pStr = (v) => (Number(v) < 1e-4 ? Number(v).toExponential(2).replace('.', ',') : Number(v).toFixed(4).replace('.', ','));
const none = { style: 'solid', fill: 'none', width: 0 };
const axisText = { typeface: FONT, fontSize: '16pt', color: C.gray };
const notes = (slide, prose, files = [], links = []) => {
  slide.speakerNotes.text = `${prose}\n\nNguồn kiểm chứng:\n${files.map(x => REPO + x).concat(links).join('\n')}`;
};
function text(slide, name, value, x, y, w, h, size = 26, color = C.ink, bold = false, align = 'left') {
  const box = slide.shapes.add({ name, geometry: 'textbox', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: none });
  box.text = String(value);
  box.text.style = { typeface: FONT, fontSize: size, color, bold, alignment: align, verticalAlignment: 'top', autoFit: 'none', wrap: 'square', insets: 0 };
  return box;
}
function card(slide, name, x, y, w, h, fill) {
  return slide.shapes.add({ name, geometry: 'rect', position: { left: x, top: y, width: w, height: h }, fill, line: { style: 'solid', fill: C.line, width: 1 } });
}
function picture(slide, relPath, x, y, w, h) {
  return slide.images.add({ path: path.join(ROOT, relPath), left: x, top: y, width: w, height: h });
}
function slide(title, source) {
  const s = ppt.slides.add();
  s.background.fill = C.white;
  const n = ppt.slides.items.length;
  text(s, 'title', title, 60, 44, 1160, 90, 44, C.navy, true);
  text(s, 'source', source, 60, 674, 1090, 27, 16.8, C.gray);
  text(s, 'page', `${String(n).padStart(2, '0')} / ${d.slide_count}`, 1150, 674, 70, 26, 17, C.gray, false, 'right');
  return s;
}
function paragraph(s, name, title, body, x, y, w, h, size = 26) {
  text(s, name + '-title', title, x, y, w, 44, size + 2, C.teal, true);
  text(s, name + '-body', body, x, y + 48, w, h - 48, size);
}
function table(s, name, values, x, y, widths, heights, fontSize = 24) {
  const rows = values.length, columns = widths.length;
  const t = s.tables.add({ rows, columns, left: x, top: y, width: widths.reduce((a, b) => a + b, 0), height: heights.reduce((a, b) => a + b, 0), columnWidths: widths, values: values.map(row => row.map(String)) });
  t.name = name;
  t.borders.assign({ style: 'solid', fill: C.line, width: 1 });
  for (let r = 0; r < rows; r++) {
    t.rows[r].height = heights[r];
    for (let c = 0; c < columns; c++) {
      const cell = t.getCell(r, c);
      cell.fill = r === 0 ? C.teal : r % 2 === 0 ? C.light : C.white;
      cell.text.style = { typeface: FONT, fontSize, color: r === 0 ? C.white : C.ink, bold: r === 0, verticalAlignment: 'middle', alignment: c === 0 ? 'left' : 'center', insets: { left: 14, right: 14, top: 10, bottom: 10 }, autoFit: 'none', wrap: 'square' };
    }
  }
  return t;
}
function chart(s, type, name, config) {
  const c = s.charts.add(type, { chartFill: C.white, chartLine: none, plotAreaFill: C.white, plotAreaLine: none, titlePlacement: 'none', ...config });
  c.name = name;
  c.xAxis.textStyle = axisText;
  c.yAxis.textStyle = axisText;
  return c;
}

// 01. Cover. Keep the authors and supervisor exactly as supplied.
{
  const s = ppt.slides.add(); s.background.fill = C.navy;
  text(s, 'course', 'ĐỒ ÁN MÔN HỌC MÁY', 72, 70, 1100, 45, 26, '#D6B86D', true);
  text(s, 'title', 'Phân cụm dựa trên lưới STING', 72, 148, 1100, 120, 68, C.white, true);
  text(s, 'subtitle', 'Phân tích PAPI 2011–2024\ntrên hai chỉ tiêu quản trị', 72, 282, 1120, 98, 36, '#E0EAF3');
  text(s, 'goals', 'Phân cụm STING · Dựng lưới, nối ô dày và gán nhãn\nBáo cáo kết quả · Thống kê 63 tỉnh và nhận xét từ dữ liệu', 72, 415, 1120, 85, 28, C.white);
  text(s, 'group', 'Nhóm 15   Chủ đề 6', 72, 514, 1080, 42, 28, '#D6B86D', true);
  text(s, 'authors', 'Nguyễn Tiến Sơn (24110054)\nTrần Thị Ngọc Quyên (24110051)', 72, 566, 680, 82, 25, C.white);
  text(s, 'supervisor', 'GVHD\nThS. Lê Minh Tân', 874, 566, 330, 80, 25, C.white);
  text(s, 'page', `01 / ${d.slide_count}`, 1150, 674, 70, 26, 17, '#E0EAF3', false, 'right');
  notes(s, 'Thưa thầy và các bạn, nhóm 15 trình bày cài đặt STING và ứng dụng trên PAPI. Mục tiêu là giải thích cơ chế, kiểm tra kết quả phân cụm và tạo bảng mô tả hỗ trợ rà soát. Phần gán điểm đã quan sát năm 2024 được tách khỏi thí nghiệm dự báo điểm năm 2024.', ['reports/Nhom15_BaoCao_STING_PAPI.docx', 'notebooks/Nhom15_STING_PAPI.ipynb']);
}
// 02. Data, 6-step preprocessing audit & sensitivity.
{
  const s = slide('Dữ liệu PAPI, tiền xử lý 6 bước & kiểm chứng độ nhạy', 'Nguồn: panel 882×41 khóa; preprocessing_audit.csv; preprocessing_sensitivity.csv');
  const pr = d.preprocessing;
  text(s, 'sample', `${d.panel_rows} dòng × ${d.panel_columns} cột · 63 tỉnh × 14 năm. Đủ hai chỉ tiêu: ${d.all_complete_n} dòng; thiếu: 13 dòng (22 ô).`, 60, 138, 1160, 40, 25, C.teal, true);
  text(s, 'feature-heading', 'Hai chỉ tiêu & Tiền xử lý Test → Decide', 60, 194, 540, 38, 27, C.teal, true);
  table(s, 'features', [['Mã', 'Ý nghĩa chỉ tiêu (PAPI 2011–2024)'], ['4.2', 'Kiểm soát tham nhũng trong cung ứng dịch vụ công'], ['6.1', 'Y tế công lập']], 60, 240, [80, 460], [48, 76, 54], 21);
  table(s, 'preproc-audit', [
    ['Bước kiểm định', 'Quyết định bảo toàn dữ liệu'],
    ['Dedup & mã 0', `0/882 trùng · ${pr.zero_to_nan} ô 0→NaN · Giữ ${pr.total_missing} ô thiếu`],
    ['Scale & |z|>3', `${pr.scale_flagged}/37 cờ nhảy · Giữ ${pr.outliers_train2d}/808 |z|>3 (xóa → nhiễu ${pr.drop_outlier_noise})`],
    ['Độ nhạy B/C vs A', `|Δ CV| ≤ ${pr.max_abs_delta} < cv_std(A) ở Ridge, LR, NB`],
  ], 60, 434, [185, 355], [46, 56, 58, 56], 17.5);
  text(s, 'protocol-heading', 'Phân tách chặt theo thời gian', 640, 194, 580, 38, 27, C.teal, true);
  table(s, 'protocol', [['Giai đoạn', 'Vai trò trong pipeline'], ['Đến 2020', 'Sàng lọc đặc trưng, fit cấu hình ứng viên'], ['2021–2022', 'Chọn cấu hình STING & CV hồi quy/phân loại'], ['2011–2023', 'Fit lại lưới 808 dòng (và nhánh 8D ≤ 2023)'], ['2024', 'Giữ scaler & lưới; gán 61 dòng / đánh giá 59 tỉnh']], 640, 240, [172, 408], [54, 72, 68, 66, 76], 22);
  text(s, 'train-only', 'StandardScaler chỉ fit trên tập huấn luyện ở từng bước; hoàn toàn không nội suy ô thiếu.', 640, 594, 580, 62, 21, C.navy, true);
  notes(s, 'Slide 2 hợp nhất dữ liệu PAPI (882×41) với quy trình 6 bước PREPROCESSING_PIPELINE và bằng chứng kiểm định trong preprocessing_audit.csv & preprocessing_sensitivity.csv: 0/882 dòng trùng khóa; 109 ô điểm 0 quy về NaN (giữ nguyên 4.649/32.634 ô thiếu); đối chiếu Mendeley 756 khóa / 5.118 giá trị có max |diff| = 0.0; xóa 7 điểm |z|>3 trên train 2011–2023 làm co biên min/max của lưới đều STING khiến tỷ lệ nhiễu vọt từ 19,6% lên 24,6%, nên quyết định giữ nguyên. Thử nghiệm thay dropna bằng SimpleImputer(median) (biến thể B) hay TrainFoldWinsorizer (C) chỉ tạo |Δ CV| ≤ 0,015 (< cv_std của A là 0,056–0,130).', ['data/processed/papi_panel_v1_LOCKED.csv', 'reports/crosscheck_mendeley.md', 'src/preprocessing.py', 'results/preprocessing_audit.csv', 'results/preprocessing_sensitivity.csv', 'notebooks/Nhom15_TienXuLy_PAPI.ipynb'], ['https://papi.org.vn/', 'https://doi.org/10.17632/wbk42j9wc8.1']);
}
// 03. Mechanism: native table is an editable count grid, not decoration.
{
  const s = slide('Cơ chế gom cụm trên lưới STING', 'Nguồn: src/sting.py; ví dụ 15 điểm; kiểm chứng giả lập trong notebook');
  paragraph(s, 'steps', 'Biến thể STING của đồ án', '1. fit() dựng lưới, lưu thống kê từng ô.\n\n2. cluster() giữ các ô đủ điểm ở tầng đã chọn.\n\n3. DFS nối các ô dày chung cạnh thành cụm.\n\n4. predict() tra ô để gán nhãn hoặc trả −1.', 60, 156, 690, 340, 28);
  text(s, 'toy-title', 'Ví dụ 3 × 3, ngưỡng = 3', 790, 154, 430, 44, 27, C.teal, true);
  const t = table(s, 'toy-grid', [[4, 3, 0], [1, 0, 4], [0, 0, 3]], 790, 215, [125, 125, 125], [82, 82, 82], 36);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const cell = t.getCell(r, c); const a = (r === 0 && c < 2), b = (c === 2 && r > 0);
    cell.fill = a ? C.paleTeal : b ? C.paleBlue : C.light;
    cell.text.style = { typeface: FONT, fontSize: 36, bold: a || b, color: a ? C.teal : b ? C.blue : C.gray, alignment: 'center', verticalAlignment: 'middle', insets: 10 };
  }
  text(s, 'toy-result', '2 cụm × 7 điểm, 1 điểm nhãn −1\nKề góc không nối cụm', 790, 483, 430, 92, 25);
  text(s, 'implementation', 'PAPI · Lưới 16 × 16, ô dày có ít nhất 5 điểm.\nTra từng trục: lấy phần nguyên của\n(điểm − biên dưới) ÷ bề rộng ô.', 60, 505, 690, 105, 25, C.navy);
  text(s, 'synthetic', `Giả lập 240 điểm: ARI = ${dec(d.synthetic_ari)}; ${d.synthetic_clusters} cụm; ${d.synthetic_noise}/240 điểm nhãn −1.`, 60, 618, 1160, 40, 25, C.teal, true);
  notes(s, 'Bảng 3×3 hiển thị số điểm từng ô, tổng 15. Hai ô hàng trên có count 4 và 3 tạo cụm A gồm 7 điểm. Hai ô bên phải có count 4 và 3 tạo cụm B gồm 7 điểm. Một điểm trong ô thưa nhận nhãn -1.', ['src/sting.py', 'scripts/common/midterm_clustering.py', 'notebooks/Nhom15_STING_PAPI.ipynb'], ['https://www.vldb.org/conf/1997/P186.PDF']);
}
// 04. Historical reference distribution.
{
  const s = slide('Một cụm lớn chiếm ưu thế trong dữ liệu lịch sử', 'Nguồn: nhãn lưới cố định 2011–2023, n = 808');
  chart(s, 'bar', 'reference-sizes', {
    position: { left: 60, top: 170, width: 750, height: 380 }, categories: ['Nhãn −1', 'Cụm 0', 'Cụm 1', 'Cụm 2'],
    series: [{ name: 'Số quan sát', values: ['-1', '0', '1', '2'].map(k => d.reference_counts[k]), fill: C.teal, points: [{ idx: 0, fill: C.gray }] }],
    hasLegend: false, barOptions: { direction: 'bar', grouping: 'clustered', gapWidth: 70 },
    xAxis: { visible: true, majorGridlines: null },
    yAxis: { visible: true, min: 0, max: 700, majorUnit: 100, numberFormatCode: '0', majorGridlines: { style: 'solid', fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: 'outEnd', textStyle: { typeface: FONT, fontSize: '20pt', bold: true, color: C.ink } }
  });
  const clustered = d.reference_counts['2'] + d.reference_counts['1'] + d.reference_counts['0'];
  text(s, 'dominance', pct(d.reference_counts['2'] / clustered), 865, 170, 350, 98, 72, C.teal, true);
  text(s, 'dominance-detail', `${d.reference_counts['2']}/${clustered} quan sát\nđã vào cụm thuộc Cụm 2`, 865, 278, 350, 105, 29);
  text(s, 'noise-detail', `${d.reference_counts['-1']}/${d.reference_n} quan sát (${pct(d.reference_counts['-1'] / d.reference_n)})\nnhận nhãn −1`, 865, 433, 350, 103, 27);
  text(s, 'meaning', 'Ba nhãn cụm chưa cho thấy ba nhóm cân bằng hoặc ba cấp chất lượng quản trị.', 60, 593, 1155, 66, 29, C.navy, true);
  notes(s, 'Lưới tham chiếu fit trên 808 quan sát đủ hai chỉ tiêu trong 2011–2023. Cụm 0 có 5, Cụm 1 có 16 và Cụm 2 có 629 quan sát; 158 nhận -1.', ['results/predict_all_years.csv', 'results/predict_summary.md', 'models/predict_config.json']);
}
// 05. Same-sample comparison and affine invariance.
{
  const s = slide('Đối chứng trên cùng tập quan sát', 'Nguồn: STING, K-means và DBSCAN cùng dùng hai đặc trưng đã chuẩn hóa');
  table(s, 'comparison', [['Phương pháp', 'Số cụm', 'Nhãn −1 / 808', 'Silhouette / 631'], ...d.comparison.map(r => [r.method, r.clusters, `${dec(r.noise_pct, 1)}%`, dec(r.silhouette)])], 60, 156, [440, 170, 260, 290], [66, 73, 73, 73], 27);
  text(s, 'shared', `Silhouette chỉ tính trên ${d.shared_n} điểm cùng được STING và DBSCAN gán vào cụm.`, 60, 476, 1160, 66, 27, C.navy, true);
  text(s, 'warning', 'K-means có silhouette cao nhất trên mẫu này. Ý nghĩa quản trị cần kiểm chứng riêng.', 60, 536, 1160, 74, 26);
  text(s, 'affine', `Thí nghiệm toàn kỳ: ${d.same_cells}/869 điểm giữ nguyên ô STING sau z-score.`, 60, 624, 1160, 38, 24, C.teal, true);
  notes(s, `Ba thuật toán fit cùng 808 quan sát chuẩn hóa. Mẫu giao ${d.shared_n} loại những điểm STING hoặc DBSCAN gán -1.`, ['src/sting.py', 'scripts/common/midterm_clustering.py', 'scripts/deliverables/build_slides.py', 'results/metrics.csv']);
}
// 06. Observed 2024 coordinates and the complete descriptive handoff table.
{
  const s = slide('Quan sát 2024 và bảng mô tả 63 tỉnh', 'Nguồn: điểm đã quan sát năm 2024; stakeholder_province_summary_2024.csv');
  text(s, 'observed-count', '48 / 61 tỉnh đủ điểm nằm trong vùng dày. 13 tỉnh ở ô thưa, 2 tỉnh thiếu dữ liệu.', 60, 137, 1160, 55, 28, C.teal, true);
  const members = key => {
    const names = new Set(d.groups.find(group => group.key === key).names);
    return d.stakeholders.filter(row => names.has(row.province_vi));
  };
  const [core, high, low] = ['core', 'high_side', 'low_61'].map(members);
  const series = [[core, 'Trong vùng dày', C.teal, 'circle'], [high, 'Ngoài vùng, điểm cao', C.blue, 'diamond'], [low, 'Ngoài vùng, 6.1 thấp', C.orange, 'square']].map(([rows, name, color, symbol]) => ({ name, xValues: rows.map(r => Number(r.sd_4_2.toFixed(6))), values: rows.map(r => Number(r.sd_6_1.toFixed(6))), xValuesFormatCode: '0.000000', valuesFormatCode: '0.000000', marker: { symbol, size: 7, fill: color, line: { style: 'solid', fill: color, width: 1 } }, line: none }));
  chart(s, 'scatter', 'observed-2024', { position: { left: 45, top: 200, width: 560, height: 369 }, series, scatterOptions: { style: 'marker' }, hasLegend: false, xAxis: { min: 1.75, max: 2.35, majorUnit: 0.1, numberFormatCode: '0.00', title: { text: '4.2  Kiểm soát tham nhũng', textStyle: axisText }, majorGridlines: { style: 'solid', fill: C.line, width: 1 } }, yAxis: { min: 1.6, max: 2.25, majorUnit: 0.1, numberFormatCode: '0.00', title: { text: '6.1  Y tế công lập', textStyle: axisText }, majorGridlines: { style: 'solid', fill: C.line, width: 1 } } });
  const names = { core: '● Trong vùng dày', high_side: '◆ Ngoài vùng dày,\nphía điểm cao', low_61: '■ Ngoài vùng dày,\nđiểm 6.1 thấp', missing: 'Thiếu dữ liệu 2024' };
  const t = table(s, 'groups', [['Nhóm mô tả', 'Tỉnh', 'Trung vị\n4.2', 'Trung vị\n6.1'], ...d.groups.map(g => [names[g.key], g.n, g.median_42 === null ? '—' : dec(g.median_42), g.median_61 === null ? '—' : dec(g.median_61)])], 640, 206, [262, 70, 124, 124], [60, 67, 83, 83, 64], 24);
  for (const [row, color] of [[1, C.teal], [2, C.blue], [3, C.orange], [4, C.gray]]) t.getCell(row, 0).text.style = { typeface: FONT, fontSize: 24, color, bold: true, alignment: 'left', verticalAlignment: 'middle', insets: { left: 14, right: 14, top: 10, bottom: 10 }, autoFit: 'none', wrap: 'square' };
  const fence = dec(d.threshold_61, 4);
  text(s, 'fence', `Ô thưa: nhóm 6.1 thấp có 6.1 < ${fence}. Nhóm phía điểm cao có 6.1 ≥ ${fence} và 4.2 ≥ ${dec(d.core_median_42, 4)}.`, 60, 586, 1160, 39, 23, C.navy, true);
  text(s, 'scope', `Mốc nội bộ tính từ 48 tỉnh trong vùng dày. Trong số đó, ${d.core_lower_n} tỉnh cũng có 6.1 dưới ngưỡng.`, 60, 628, 1160, 37, 23);
  notes(s, 'Đây là gán điểm đã quan sát năm 2024 lên lưới được fit đến hết 2023, không phải dự báo. 48 tỉnh vào Cụm 2, 13 tỉnh ở ô thưa, 2 tỉnh thiếu dữ liệu.', ['results/papi_observed_grid_2024.csv', 'results/stakeholder_province_summary_2024.csv', 'scripts/analysis/stakeholder_summary.py', 'models/sting_predict_scaler.json', 'data/processed/external_gso_grdp_63.csv']);
}
// 07. Transition matrix and one auditable example.
{
  const s = slide('Dịch chuyển 2023–2024 trên cùng lưới', 'Nguồn: 59 tỉnh đủ điểm ở cả hai năm; nhãn do cùng một lưới cố định sinh ra');
  table(s, 'transition', [['2023 / 2024', 'Trong vùng dày', 'Ngoài vùng dày'], ['Trong vùng dày', ...d.transitions[0]], ['Ngoài vùng dày', ...d.transitions[1]]], 60, 165, [224, 190, 190], [65, 82, 82], 25);
  const movedOut = d.stakeholders.filter(row => row.cluster_2023 === 2 && row.cluster === -1);
  const under = movedOut.filter(row => row.sd_6_1 < d.threshold_61).length;
  text(s, 'transition-count', `${movedOut.length} tỉnh rời vùng dày, ${d.transitions[1][0]} tỉnh đi vào`, 60, 421, 604, 52, 30, C.teal, true);
  text(s, 'transition-split', `Trong ${movedOut.length} tỉnh rời vùng, ${movedOut.length - under} tỉnh ở phía điểm cao và ${under} tỉnh có 6.1 dưới mốc nội bộ.`, 60, 474, 604, 76, 25);
  text(s, 'transition-limit', 'Đọc điểm từng trục và ngưỡng số điểm trước khi diễn giải thay đổi nhãn.', 60, 573, 604, 72, 24, C.gray);
  text(s, 'trace-title', 'Truy vết Lạng Sơn', 708, 160, 512, 45, 29, C.teal, true);
  const [earlier, latest] = d.trace;
  table(s, 'trace', [['Năm', 'Điểm 4.2 / 6.1', 'Ô lưới', 'Số điểm\ntham chiếu'], ...d.trace.map(r => [r.year, `${dec(r.x)} / ${dec(r.y)}`, `(${r.cell.join(', ')})`, r.count])], 708, 222, [82, 176, 108, 146], [66, 64, 64], 23);
  const axisExamples = [latest.x, latest.y].map((score, i) => `${['4.2', '6.1'][i]}   ⌊(${dec(score)} − ${dec(d.grid_raw_lo[i])}) / ${dec(d.grid_raw_step[i], 4)}⌋ = ${latest.cell[i]}`);
  text(s, 'trace-example', `Tính ô năm ${latest.year} (số làm tròn)`, 708, 443, 512, 40, 24, C.teal, true);
  text(s, 'trace-calculation', axisExamples.join('\n'), 708, 485, 512, 73, 24);
  const minCount = d.config.sting.min_count;
  text(s, 'trace-rule', `${earlier.count} < ${minCount} → nhãn −1   ·   ${latest.count} ≥ ${minCount} → Cụm ${latest.label}`, 708, 577, 512, 51, 24, C.navy, true);
  notes(s, `Ma trận có tổng ${d.transition_n}: 43 giữ vùng dày, 7 rời vùng dày, 5 từ ngoài vào và 4 vẫn ngoài. Lạng Sơn chuyển từ (13, 9) count=2 lên (12, 10) count=12 năm 2024.`, ['src/sting.py', 'results/predict_all_years.csv', 'results/papi_observed_grid_2024.csv', 'scripts/common/papi_pred_common.py']);
}
// 08. Forecasting + balanced C3/C1 classifiers.
{
  const s = slide('Dự báo điểm cải thiện MAE nhưng bỏ sót vùng rìa', 'Nguồn: papi_forecast_2024.json; supervised_metrics.csv; course_supervised_baselines.csv (n = 59)');
  const score = (target, method) => d.forecast.scores.find(r => r.target === target && r.method === method);
  table(s, 'forecast-scores', [['Chỉ tiêu', 'MAE Ridge', 'MAE giữ 2023', 'RMSE Ridge', 'RMSE giữ 2023'], ...['sd_4_2', 'sd_6_1'].map((f, i) => [i === 0 ? '4.2' : '6.1', dec(score(f, 'forecast').mae, 4), dec(score(f, 'carry').mae, 4), dec(score(f, 'forecast').rmse, 4), dec(score(f, 'carry').rmse, 4)])], 60, 148, [160, 250, 250, 250, 250], [56, 62, 62], 24);
  text(s, 'recall-value', `0 / ${d.forecast.actual_outside}`, 60, 344, 500, 68, 54, C.orange, true);
  text(s, 'recall-label', 'tỉnh ngoài vùng dày được dự báo điểm phát hiện (cả 59 dự báo rơi vào Cụm 2). Balanced accuracy = 0,500.', 60, 418, 520, 88, 23);
  text(s, 'auc-value', `AUC ${dec(d.forecast.scenario_auc)}`, 680, 344, 530, 68, 52, C.teal, true);
  text(s, 'auc-label', `${d.forecast.scenario_count} cặp phần dư tạo kịch bản xếp hạng.\nHồi cứu thăm dò; chưa phải xác suất hiệu chỉnh tiền cứu.`, 680, 418, 530, 88, 23);
  const nb = d.course_baselines.find(row => row.model === 'gaussian naive bayes');
  const sup = d.supervised_summary;
  card(s, 'clf-panel', 60, 520, 1160, 134, C.paleTeal);
  text(s, 'classification-scope', `Phân loại vùng lưới STING (CV expanding 2017–2022, giữ holdout 59 tỉnh không dùng chọn tham số):\n• Baseline học phần (6 model, gồm KNN/SVM/DT): Naive Bayes CV macro-F1 ${dec(nb.value_cv)} (holdout ${dec(nb.holdout_macro_f1)}).\n• Cập nhật cân bằng lớp (thắng 6/6 fold CV): C3 Random Forest (balanced) CV macro-F1 ${dec(sup.rf_bal_cv)} (Acc ${pct(sup.rf_bal_acc)} / F1 ${dec(sup.rf_bal_f1)}); C1 Logistic (balanced) đạt ${pct(sup.lr_bal_acc)} / F1 ${dec(sup.lr_bal_f1)}.`, 80, 532, 1120, 114, 20, C.navy);
  notes(s, 'Nhánh dự báo hai đầu ra cho thấy dự báo điểm co về vùng trung tâm Cụm 2 nên bỏ sót 11/11 ca ngoài vùng dù MAE giảm. Phần phân loại cân bằng C3 Random Forest (balanced) nâng CV macro-F1 lên 0,524 (thắng 6/6 fold trước LR gốc 0,434) cùng C1 Logistic (balanced) đạt holdout Acc 74,6% / Macro-F1 0,595.', ['results/papi_forecast_2024.json', 'results/supervised_metrics.csv', 'results/course_supervised_baselines.csv', 'scripts/supervised/predict_supervised.py']);
}
// 09. Deep Regression (17 Configs), Conformal 90% & E3.
{
  const s = slide('Hồi quy 17 cấu hình 6.1, Conformal 90% & Backtest E3', 'Nguồn: regression_deep_analysis.{csv,md}; regression_conformal_2024.csv; future_work_backtest.csv');
  const reg = d.regression_deep, sp = d.spatial;
  text(s, 'reg-head', 'Đối chiếu 17 cấu hình hồi quy 6.1 (train 740)', 55, 136, 580, 34, 21.5, C.teal, true);
  table(s, 'reg-table', [
    ['Cấu hình / Cơ chế', 'CV R²', 'Holdout MAE (R²)'],
    ['Giữ nguyên năm trước (baseline)', dec(reg.carry_cv_r2, 3), `${dec(reg.carry_ho_mae, 4)} (${dec(reg.carry_ho_r2, 3)})`],
    ['AR(1) OLS (chỉ dùng 6.1 năm t)', dec(reg.ar1_cv_r2, 4), `${dec(reg.ar1_ho_mae, 4)} (${dec(reg.ar1_ho_r2, 3)})`],
    ['Ridge 8 đặc trưng (chính thức)', dec(reg.ridge_cv_r2, 4), `${dec(reg.ridge_ho_mae, 4)} (${dec(reg.ridge_ho_r2, 3)})`],
    ['Sai phân Δ6.1 = y(t+1)−y(t) Ridge α=50', dec(reg.delta_cv_r2, 4), `${dec(reg.delta_ho_mae, 4)} (${dec(reg.delta_ho_r2, 3)})`],
    ['Panel FE (63 tỉnh) / Ablation bỏ 6.1', `${dec(reg.panel_fe_cv_r2, 3)} / ${dec(reg.ablation_cv_r2, 3)}`, `${dec(reg.panel_fe_ho_mae, 4)} (${dec(reg.panel_fe_ho_r2, 3)})`],
  ], 55, 180, [295, 135, 150], [46, 44, 44, 44, 44, 48], 17.5);
  card(s, 'reg-box', 55, 464, 580, 192, C.paleTeal);
  text(s, 'reg-findings', `Phát hiện cơ chế, bất định & không gian:\n• VIF tham nhũng 4.1–4.3 = 3,76–5,00 (κ = 5,09); Ridge vượt carry trên OOF CV (n=366, Wilcoxon p = ${dec(reg.wilcoxon_oof_p, 5)}), holdout p = ${dec(reg.wilcoxon_ho_p, 3)}.\n• Conformal 90% (±${dec(reg.conf90_rad, 4)}): phủ ${pct(reg.conf90_cov)}; cận dưới < 1,7848 báo 28 tỉnh (bắt 4/4 thấp, precision 4/28; phủ ≠ chính xác cảnh báo).\n• Backtest E3 (2019–24): Ridge thắng MAE 4/6 năm; phần dư 2024 chưa phát hiện tự tương quan 5% (I = ${dec(sp.resid_i, 4)}, p = ${dec(sp.resid_p, 4)}).`, 72, 472, 546, 178, 16.8, C.ink);
  picture(s, 'results/figs/regression_diagnostics_deep.png', 648, 138, 578, 520);
  notes(s, 'Slide 9 trình bày kết quả đối chiếu 17 mô hình hồi quy đơn chỉ tiêu 6.1: tín hiệu cốt lõi đến từ quán tính AR(1), sai phân Δ6.1 Ridge α=50 đạt CV R² 0,2732, Conformal 90% phủ 94,9% (precision 4/28, độ phủ ≠ precision) và phần dư Ridge chưa phát hiện tự tương quan 5% (p = 0,7930).', ['scripts/supervised/regression_deep_analysis.py', 'results/regression_deep_analysis.csv', 'results/regression_conformal_2024.csv', 'results/figs/regression_diagnostics_deep.png', 'results/future_work_backtest.csv']);
}
// 10. High-Dim Robustness -> QuantileSTING & Subspace CLIQUE.
{
  const s = slide('Độ bền số chiều: Từ loãng lưới đến STING đa chiều', 'Nguồn: robustness.csv; src/high_dim.py; high_dim_sting.csv/subspaces.csv (train ≤ 2023, holdout 2024)');
  const hd = d.high_dim;
  text(s, 'hd-head', 'Điểm nghẽn lưới đều & Giải pháp Quantile / CLIQUE', 55, 138, 575, 36, 22, C.teal, true);
  table(s, 'robustness', [
    ['Cấu hình đối chiếu', 'k', 'Nhiễu', 'Silh. / Phủ 2024'],
    ['PCA(2) d1–d6 / 8D đều (gốc)', '1 / 3', '6,2 / 60,5%', 'n/a / 0,297'],
    ['8D d1–d8 đều mc=2 (OFAT)', '2', '10,9%', '−0,089 (tách yếu)'],
    ['8D d1–d8 Quantile mc=4 (wy-z)', String(hd.d8q4_k), pct(hd.d8q4_noise), `+${dec(hd.d8q4_sil, 3)} (mc=5: ${pct(hd.d8q5_ho)})`],
    ['8D sàng lọc Quantile mc=7 (≤23)', String(hd.q7_k), pct(hd.q7_noise), `24: ${pct(hd.q7_ho)} (wy-z k=3)`],
    ['CLIQUE 5D đều / 4D Quantile', `${hd.cu5_k} / ${hd.cq4_k}`, `${pct(hd.cu5_noise, 0)} / ${pct(hd.cq4_noise, 0)}`, `${dec(hd.cu5_sil, 3)} / ${dec(hd.cq4_sil, 3)}`],
  ], 55, 180, [255, 76, 108, 141], [46, 46, 46, 46, 46, 46], 17.5);
  card(s, 'hd-box', 55, 468, 580, 188, C.paleBlue);
  text(s, 'hd-takeaway', `Vì sao lưới đều 8D thất bại & vẫn giữ STING 2D (3/4/5/2):\n• Thang thưa 16^d (f=4 lv=2 mc=5): nhiễu nhảy ${pct(hd.d2_f4_noise)} (d=2) → ${pct(hd.d3_f4_noise)} (d=3) → 100% (d=4, 65.536 ô); 0/28 cặp có cụm ≤ 90%.\n• Không thay bản chính 2D: Quantile trên lưới mịn 2D 16×16 cắt nát vùng lõi lên ${pct(hd.q2d_noise)} nhiễu (Silh. ${dec(hd.q2d_sil, 3)}), nên STING 2D 3/4/5/2 vẫn tối ưu cho 4.2 × 6.1.`, 72, 478, 546, 170, 18, C.navy);
  picture(s, 'results/figs/high_dim_sting_analysis.png', 648, 138, 578, 520);
  notes(s, 'Slide 10 đặt cạnh nhau bảng robustness gốc với nghiên cứu STING đa chiều không rò rỉ 2024: QuantileSTING hạ nhiễu 8D còn 44,7% (Silh +0,161), CLIQUE tìm không gian con 5D/4D, nhưng 2D vẫn giữ lưới đều 3/4/5/2.', ['results/robustness.csv', 'src/high_dim.py', 'scripts/analysis/high_dim_sting.py', 'results/high_dim_sting.csv', 'results/high_dim_sting.md']);
}
// 11. External Validation + Year-FE CR1 Comparison.
{
  const s = slide('Đối chiếu nguồn ngoài PAPI & Giới hạn gộp', 'Nguồn: external_validation.{csv,md}; poverty_validation.csv; panel_inference.csv (PCI 2011–2022)');
  const e = d.external_checks, pi = d.panel_inf;
  table(s, 'external', [
    ['Nguồn / giai đoạn', 'n', 'p gộp (Kruskal)', 'p Year-FE CR1 (63 tỉnh)', 'Diễn giải mô tả'],
    ['PCI 2011–2022', e.pci_n, `${pStr(e.pci_p)} (raw)`, `${pStr(pi['2d_pci_cr1'])} (Wald ${dec(pi['2d_pci_waldf'], 2)})`, 'Trung vị Cụm 2: 62,16 vs −1: 59,16\nBiến mất hoàn toàn khi thêm Year-FE'],
    ['GRDP/người 2018–2024', e.grdp_n, pStr(e.grdp_p), `${pStr(pi['2d_grdp_cr1'])} (TWFE ${pStr(pi['2d_grdp_tw'])})`, 'Khác biệt mô tả giữa nhóm,\nchưa đạt ngưỡng 5% dưới CR1'],
    ['Điểm y tế ODM 2020', e.odm_n, pStr(e.odm_p), 'Snapshot 1 năm', `Chưa có bằng chứng khác biệt;\n${e.odm_zero_count} tỉnh không ghi nhận điểm nguồn`],
    ['Nghèo GSO 2012–2024', e.poverty_n, `${dec(e.poverty_raw_p)} (thô)`, `${pStr(pi['2d_pov_cr1'])} (C2 vs −1)`, `Trừ median năm KW p=${dec(e.poverty_demeaned_p, 6)}\nHiệu ứng ANOVA ${e.poverty_eta_note.split(' (')[0].replace('.', ',')}`],
  ], 55, 148, [265, 76, 178, 226, 425], [62, 86, 86, 88, 90], 20.5);
  text(s, 'external-limit', 'Quan sát lặp theo tỉnh & xu hướng năm làm p-value gộp gây nhiễu dương giả trên 2D — chi tiết hiệu chỉnh CR1/TWFE & FDR 383 không gian con ở Slide 12.', 55, 584, 1170, 74, 22, C.navy, true);
  notes(s, 'Cột Year-FE CR1 chứng minh tín hiệu PCI gộp trên 2D biến mất hoàn toàn khi thêm Year-FE (p = 0,7007). Chi tiết ở Slide 12.', ['results/external_validation.csv', 'results/external_validation.md', 'results/poverty_validation.csv', 'results/panel_inference.csv', 'results/panel_inference.md']);
}
// 12. Panel Inference (CR1 / TWFE), Holm/BH/BY FDR & Spatial Moran's I.
{
  const s = slide('Suy luận bảng (CR1 / TWFE), Kiểm soát FDR & Moran\'s I', 'Nguồn: panel_inference.{csv,md}; FWL + Liang–Zeger CR1 (63 tỉnh); B = 1.999 WCR / hoán vị quanh E[I]');
  const pi = d.panel_inf, sp = d.spatial;
  text(s, 'inf-head', 'Year-FE CR1 vs Two-Way FE & Kiểm soát đa kiểm định', 55, 138, 575, 36, 21.5, C.teal, true);
  table(s, 'panel-inf-table', [
    ['Nhánh · Biến ngoài', 'Naive thô', 'Year-FE CR1 (β, p)', 'TWFE · Holm (3 / 6)'],
    ['STING 2D · PCI (n=726)', pStr(pi['2d_pci_raw']), `${dec(pi['2d_pci_b'])} (${pStr(pi['2d_pci_cr1'])})`, `TW ${pStr(pi['2d_pci_tw'])} · Loại`],
    ['8D Quant. mc=7 · PCI (411)', pStr(pi.hd_pci_raw), `${dec(pi.hd_pci_b)} (${pStr(pi.hd_pci_cr1)})`, `${dec(pi.hd_pci_tw)} · ${dec(pi.hd_pci_holm)} / ${dec(pi.hd_pci_holm_g)}`],
    ['8D wy-z mc=7 · PCI (415)', pStr(pi.wy_pci_raw), `${dec(pi.wy_pci_b)} (${pStr(pi.wy_pci_cr1)})`, `TW ${pStr(pi.wy_pci_tw)} (độ nhạy)`],
    ['8D Quant. · GRDP / Nghèo', `${dec(pi.hd_grdp_raw)} / ${pStr(pi.hd_pov_raw)}`, `${pStr(pi.hd_grdp_cr1)} / ${pStr(pi.hd_pov_cr1)}`, 'Holm 0,149 (Loại)'],
    ['Thăm dò 383 KGC PCI (KW)', `${pi.sub_naive} (<0,05)`, `${pi.sub_bh} BH-FDR 5%`, `${pi.sub_by} BY / ${pi.sub_holm} Holm`],
  ], 55, 178, [222, 108, 128, 122], [46, 46, 46, 46, 46, 46], 16);
  card(s, 'inf-box', 55, 464, 580, 192, C.paleTeal);
  text(s, 'inf-notes', `Kết luận suy luận & Chẩn đoán không gian 2024:\n• Kiểm soát 6 phép & TWFE: 8D mc=7 đạt CR1 (p = ${pStr(pi.hd_pci_cr1)}, WCR = ${dec(pi.hd_pci_wcr, 4)}) và Holm nội họ 8D (${dec(pi.hd_pci_holm, 4)}), chưa đạt Holm 6 phép (${dec(pi.hd_pci_holm_g, 4)}); TWFE p = ${dec(pi.hd_pci_tw, 4)} chưa bác bỏ 0.\n• Không gian (Queen 63 tỉnh): sd_6_1 I = +${dec(sp.obs61_i, 4)} (p=${pStr(sp.obs61_p)}); pred_ridge I = +${dec(sp.pred_i, 4)} (p=${pStr(sp.pred_p)}); phần dư Ridge chưa phát hiện tự tương quan 5% (I = ${dec(sp.resid_i, 4)}, p = ${pStr(sp.resid_p)}).`, 72, 472, 546, 178, 16.8, C.ink);
  picture(s, 'results/figs/panel_inference_diagnostics.png', 648, 138, 578, 520);
  notes(s, 'Slide 12 là trụ cột suy luận bảng: FWL + CR1 + WCR Bootstrap (B=1.999) giữ PCI ở 8D Quantile mc=7 (p=0,0156, WCR=0,0185, Holm nhánh 0,0468, Holm 6 phép 0,0937, TWFE p=0,3420 chưa bác bỏ 0), sàng lọc thăm dò 383 KGC giữ 117 BH-FDR 5% và Moran\'s I phần dư Ridge chưa phát hiện tự tương quan 5% (p=0,7930).', ['scripts/analysis/panel_inference.py', 'results/panel_inference.csv', 'results/panel_inference.md', 'results/figs/panel_inference_diagnostics.png', 'tests/test_panel_inference.py']);
}
// 13. Descriptive findings tied back to the clustering output (2024).
{
  const s = slide('Thống kê và nhận xét kết quả 2024', 'Nguồn: điểm PAPI quan sát và nhãn từ lưới STING dựng trên giai đoạn 2011–2023');
  const [core, high, low, missing] = d.groups;
  const names = ['Trong vùng dày (Cụm 2)', 'Ô thưa phía điểm cao', 'Ô thưa có 6.1 dưới mốc', 'Thiếu dữ liệu'];
  table(s, 'reported-groups', [['Nhóm mô tả', 'Số tỉnh', 'Tỉ lệ'], ...d.groups.map((g, i) => [names[i], g.n, pct(g.share)])], 60, 181, [300, 100, 119], [60, 65, 70, 70, 62], 25);
  const total = d.groups.reduce((sum, group) => sum + group.n, 0);
  text(s, 'report-denominator', `Tỉ lệ tính trên ${total} tỉnh.\n${total - missing.n} tỉnh đủ cả hai điểm quan sát.`, 60, 537, 519, 85, 25, C.navy);
  card(s, 'findings-panel', 624, 155, 596, 467, C.paleTeal);
  text(s, 'findings-title', 'Nhận xét', 654, 180, 536, 42, 31, C.teal, true);
  paragraph(s, 'finding-dominance', 'Cụm 2 chiếm ưu thế', `${core.n}/${total - missing.n} tỉnh đủ điểm thuộc Cụm 2.`, 654, 241, 536, 90, 25);
  paragraph(s, 'finding-sparse', 'Các tỉnh cùng nhãn −1 có điểm khác nhau', `Trung vị 4.2 nhóm ${high.n}: ${dec(high.median_42)} · vùng dày: ${dec(core.median_42)}.\nTrung vị 6.1 nhóm ${low.n}: ${dec(low.median_61)} · vùng dày: ${dec(core.median_61)}.`, 654, 348, 536, 124, 23);
  paragraph(s, 'finding-within', 'Vùng dày vẫn có khác biệt về 6.1', `${d.core_lower_n} tỉnh có 6.1 dưới mốc nội bộ ${dec(d.threshold_61, 4)}.`, 654, 490, 536, 99, 24);
  notes(s, 'Thống kê mô tả 63 tỉnh năm 2024: 48 trong vùng dày (76,2%), 8 phía điểm cao (12,7%), 5 ở nhóm 6.1 thấp (7,9%), 2 thiếu dữ liệu (3,2%).', ['results/papi_observed_grid_2024.csv', 'results/stakeholder_province_summary_2024.csv', 'reports/Nhom15_BaoCao_STING_PAPI.docx']);
}
// 14. Integrated Delivery System: Dashboard, Excel, DOCX, Notebooks, Review & CI.
{
  const s = slide('Hệ thống tích hợp: Dashboard, Báo cáo & Phiếu 63 tỉnh', 'Nguồn: app.py; KetQua_STING_PAPI.xlsx; stakeholder_quadrants_2024.png; client_product.py');
  text(s, 'sys-p1-t', 'Dashboard Streamlit 6 Tab (chỉ-đọc, fail-closed)', 55, 138, 575, 34, 23, C.teal, true);
  text(s, 'sys-p1-b', '• Tổng quan & Lưới STING 63 tỉnh (14 năm) + Phân tích Đa chiều Quantile / CLIQUE.\n• Dự báo 6.1 (17 cấu hình, Conformal 90%) + Kiểm chứng ngoài (Year-FE CR1, FDR, Moran\'s I).\n• Kiểm toán thang đo 23/37 cột + Bảng bàn giao 63 tỉnh & In phiếu A4 từng địa phương.', 55, 178, 575, 136, 18.5);
  text(s, 'sys-p2-t', 'Bộ Hồ sơ Thống nhất & Khung Thẩm định Độc lập', 55, 316, 575, 34, 23, C.teal, true);
  text(s, 'sys-p2-b', '• Báo cáo DOCX 7 chương (13 hình, 18 bảng, 86 mục điều hướng Word) & Excel 28 sheet.\n• Bộ đôi Notebook thực thi sạch (22 & 9 code cell) + Bộ Slide bảo vệ 15 trang.\n• Khung thẩm định mù đôi 16 hồ sơ rà soát (cases.csv + external_dossier.csv phi-PAPI).', 55, 356, 575, 128, 18);
  card(s, 'sys-ci-box', 55, 496, 575, 154, C.paleBlue);
  text(s, 'sys-ci-text', 'Kiểm chứng tự động & Đóng gói liên nền tảng (Ubuntu · Windows · macOS):\n• 293 kiểm thử pytest (94% bao phủ src/) · 264 tham chiếu Q&A hợp lệ.\n• Gói ZIP 173 tệp tự chứa, khớp SHA-256 & replay notebook trên cả 3 HĐH.', 72, 508, 542, 132, 17, C.navy, true);
  picture(s, 'results/figs/stakeholder_quadrants_2024.png', 648, 138, 578, 520);
  notes(s, 'Slide 14 minh họa sản phẩm tích hợp sẵn sàng bàn giao: Dashboard Streamlit 6 tab, Excel 28 sheet, DOCX 7 chương, phiếu A4 63 tỉnh, khung thẩm định mù đôi 16 ca phi-PAPI và CI 3 HĐH.', ['app.py', 'scripts/analysis/client_product.py', 'results/KetQua_STING_PAPI.xlsx', 'results/stakeholder_province_summary_2024.csv', 'scripts/deliverables/build_report.py']);
}
// 15. Complete 15-slide Synthesis: Conclusions, Methodological Limits & Next Steps.
{
  const s = slide('Kết luận, giới hạn và hướng phát triển', 'Tài liệu chính: Wang, Yang & Muntz (VLDB 1997); PAPI; Mendeley; PCI, GSO, ODM; CR1/FDR');
  paragraph(s, 'contribution', '1. Kết luận cốt lõi từ toàn bộ nghiên cứu', '• STING 2D (3/4/5/2) minh bạch, truy vết được từng ô (ARI = 0,950 giả lập; bất biến 869/869 z-score; 48 Cụm 2 / 13 ô thưa / 2 thiếu 2024).\n• Hồi quy 17 cấu hình làm rõ động lực AR(1)/Δ6.1 (CV R² 0,2732), Conformal 90% phủ 94,9% (precision 4/28), C3/C1 nâng F1 CV 0,524 và phần dư Ridge chưa phát hiện tự tương quan 5% (p = 0,7930).\n• Mở rộng đa chiều (QuantileSTING / CLIQUE) giảm nhiễu 8D còn 44,7% (Silh. +0,161); Year-FE CR1 giữ PCI ở 8D (p = 0,0156, Holm nhánh 0,0468; Holm 6 phép 0,0937; sàng lọc thăm dò 117/383 BH-FDR).', 60, 142, 1160, 200, 19.8);
  paragraph(s, 'limits', '2. Giới hạn phương pháp luận', '• STING 2D có Cụm 2 chiếm 96,8% điểm vào cụm; chia quantile chỉ hợp lý ở 3D–8D (gây vỡ lõi 2D lên 49,0% nhiễu) nên giữ chuẩn 2D lưới đều.\n• Nhãn phân loại là pseudo-label; chưa bác bỏ TWFE (p = 0,342) hay đạt Holm 6 phép chính (0,0937) và mới hồi kiểm trên một mốc holdout 2024.', 60, 354, 1160, 138, 20);
  paragraph(s, 'future', '3. Bước tiếp theo', '• Tổ chức 2 chuyên viên chấm mù đôi độc lập 16 phiếu địa phương (cases.csv + external_dossier.csv) trước khi dùng nhãn tham chiếu.\n• Kiểm định tiền cứu ngoài mẫu trên dữ liệu PAPI 2025 khi được công bố và hiệu chỉnh xác suất cảnh báo vận hành.', 60, 502, 1160, 116, 20.5);
  text(s, 'thanks', 'Cảm ơn thầy và các bạn. Nhóm xin nhận câu hỏi.', 60, 626, 1160, 36, 26, C.teal, true);
  notes(s, 'Slide 15 kết luận cô đọng 4 trụ cột của đồ án: STING 2D & bàn giao 63 tỉnh, hồi quy 17 cấu hình + Conformal 90% + C3/C1, STING đa chiều QuantileSTING / CLIQUE, và suy luận bảng CR1/TWFE/Holm/FDR/Moran\'s I.', ['results/future_work.md', 'results/high_dim_sting.md', 'results/panel_inference.md', 'results/regression_deep_analysis.md', 'reports/Nhom15_BaoCao_STING_PAPI.docx'], ['https://www.vldb.org/conf/1997/P186.PDF', 'https://papi.org.vn/', 'https://doi.org/10.17632/wbk42j9wc8.1', 'https://otexts.com/fpp3/']);
}
if (ppt.slides.items.length !== d.slide_count) throw new Error('Slide count does not match evidence manifest');
await fs.mkdir(path.dirname(path.resolve(args.output)), { recursive: true });
await (await PresentationFile.exportPptx(ppt)).save(args.output);
if (args['render-dir']) {
  await fs.mkdir(args['render-dir'], { recursive: true });
  for (const [index, s] of ppt.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, '0')}`;
    const png = await ppt.export({ slide: s, format: 'png', scale: 1 });
    await fs.writeFile(path.join(args['render-dir'], `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await s.export({ format: 'layout' });
    await fs.writeFile(path.join(args['render-dir'], `${stem}.layout.json`), await layout.text());
  }
}
console.log(`Saved ${ppt.slides.items.length} slides to ${args.output}`);
