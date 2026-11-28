/**
 * Editable STING–PAPI defense presentation, authored with @oai/artifact-tool.
 * Evidence comes from build_slides.py --data-only. No source results are changed.
 * The optional Artifact authoring path requires a runtime that provides that
 * package. The Python entry point also supports the portable published snapshot.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

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
  throw new Error('Artifact authoring requires a runtime with @oai/artifact-tool. Use the portable Python build for the published snapshot.', { cause: error });
}
const { Presentation, PresentationFile } = artifact;
const d = JSON.parse(await fs.readFile(args.data, 'utf8'));
const ppt = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const FONT = 'Arial';
const C = { navy: '#0F2B46', teal: '#146F78', blue: '#127EA1', orange: '#B9562A', gold: '#B17E20', gray: '#566574', light: '#F3F6F8', line: '#D7E0E7', ink: '#1B2834', white: '#FFFFFF', paleBlue: '#E9F2F8', paleTeal: '#E8F4F2' };
const REPO = 'https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/';
const dec = (v, n = 3) => Number(v).toFixed(n).replace('.', ',');
const pct = (v, n = 1) => `${dec(v * 100, n)}%`;
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
  const t = s.tables.add({ rows, columns, left: x, top: y, width: widths.reduce((a,b) => a+b,0), height: heights.reduce((a,b) => a+b,0), columnWidths: widths, values: values.map(row => row.map(String)) });
  t.name = name;
  t.borders.assign({ style: 'solid', fill: C.line, width: 1 });
  for (let r=0; r<rows; r++) {
    t.rows[r].height = heights[r];
    for (let c=0; c<columns; c++) {
      const cell = t.getCell(r,c);
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
  notes(s, 'Thưa thầy và các bạn, nhóm 15 trình bày cài đặt STING và ứng dụng trên PAPI. Mục tiêu là giải thích cơ chế, kiểm tra kết quả phân cụm và tạo bảng mô tả hỗ trợ rà soát. Phần gán điểm đã quan sát năm 2024 được tách khỏi thí nghiệm dự báo điểm năm 2024. Thời lượng nội dung khoảng 15 phút, sau đó hỏi đáp.', ['reports/Nhom15_BaoCao_STING_PAPI.docx', 'notebooks/Nhom15_STING_PAPI.ipynb']);
}
// 02. Data, cleaning and the chronological evaluation protocol.
{
  const s = slide('Dữ liệu PAPI và quy trình tiền xử lý', 'Nguồn: panel PAPI khóa phiên bản; preprocessing_audit.csv; predict_config.json');
  text(s,'sample',`${d.panel_rows} dòng × ${d.panel_columns} cột; 63 tỉnh × 14 năm. Đủ hai chỉ tiêu: ${d.all_complete_n} dòng, thiếu: 13 dòng.`,60,141,1160,49,27,C.teal,true);
  text(s,'feature-heading','Hai chỉ tiêu quản trị',60,208,520,42,29,C.teal,true);
  table(s,'features',[['Mã','Ý nghĩa'],['4.2','Kiểm soát tham nhũng trong cung ứng dịch vụ công'],['6.1','Y tế công lập']],60,260,[80,440],[58,92,65],24);
  text(s,'cleaning','Hợp nhất 14 bảng theo mã tỉnh và năm.\nKiểm tra khóa, mã tỉnh và miền giá trị.\nChuyển điểm 0 thành giá trị thiếu.\nGắn cờ cực trị và kiểm tra thang đo.',60,500,520,145,25);
  text(s,'protocol-heading','Phân tách theo thời gian',640,208,580,42,29,C.teal,true);
  table(s,'protocol',[['Giai đoạn','Vai trò'],['Đến 2020','Sàng lọc đặc trưng, fit cấu hình ứng viên'],['2021–2022','Chọn cấu hình theo năm kiểm định'],['2011–2023','Fit lại trên 808 dòng lịch sử'],['2024','Giữ scaler và lưới; gán 61 dòng đủ điểm']],640,260,[172,408],[58,75,65,65,75],24);
  text(s,'train-only','StandardScaler chỉ fit trên phần huấn luyện ở mỗi bước.',640,613,580,48,23,C.navy,true);
  notes(s,'PAPI phản ánh trải nghiệm và đánh giá của người dân về quản trị, hành chính công. Một dòng là một tỉnh–năm, không phải một người trả lời khảo sát. Tên và địa giới theo bộ 63 tỉnh lịch sử. Hai trục là điểm thành phần gốc 4.2 và 6.1; lưới này không phải bản đồ địa lý. Panel có 882 dòng và 41 cột. Hai chỉ tiêu có 22 ô thiếu trên 13 dòng, nên mẫu mô tả toàn kỳ còn 869 dòng. Lưới tham chiếu dùng 808 dòng 2011–2023 và gán 61 dòng đủ dữ liệu năm 2024. Vĩnh Phúc và Tiền Giang thiếu dữ liệu năm 2024. Đối chiếu Mendeley có 756 khóa tỉnh–năm giao và 5.118 giá trị dimension hợp lệ, độ lệch tối đa bằng 0; kết quả này kiểm tra tính khớp dữ liệu, không chứng minh mọi thang đo ổn định.\n\nTiền xử lý kiểm tra khóa, mã tỉnh và miền giá trị; quy ước điểm 0 thành thiếu theo cách mã hóa của bộ dữ liệu. Toàn bộ 37 cột có 4.649 ô thiếu, gồm 4.284 ô ngoài cửa sổ thu thập và 365 ô trong cửa sổ. Có 122 ô |z| > 3 ở 29 cột được gắn cờ, không tự xóa; đầu ra phân cụm dùng các dòng đủ đặc trưng. Có 23/37 cột có cờ bước nhảy theo heuristic, cần đối chiếu metadata trước khi kết luận đổi thang. Xóa điểm cực trị có thể đổi min/max và biên ô lưới.\n\nQuy trình dùng thứ tự thời gian: fit và sàng lọc trên dữ liệu đến 2020, chấm cấu hình trên 2021–2022, fit lại lưới trên 2011–2023. StandardScaler chỉ học từ phần train ở mỗi bước; khi gán 2024 giữ nguyên scaler và lưới. Năm 2024 không tham gia lựa chọn cấu hình. Đây vẫn là hồi kiểm được xây dựng sau khi đã có dữ liệu, không tương đương một thử nghiệm tiền cứu đăng ký trước. Bộ lọc tỷ trọng cụm lớn chia cho toàn mẫu nên có thể chấp nhận một cụm áp đảo trong số các điểm đã vào cụm; xem protocol_sensitivity.md và slide 4.', ['data/processed/papi_panel_v1_LOCKED.csv','reports/crosscheck_mendeley.md','src/preprocessing.py','results/preprocessing_audit.csv','scripts/analysis/predict_sweep.py','models/predict_config.json','results/protocol_sensitivity.md','notebooks/Nhom15_TienXuLy_PAPI.ipynb'],['https://papi.org.vn/','https://doi.org/10.17632/wbk42j9wc8.1']);
}
// 03. Mechanism: native table is an editable count grid, not decoration.
{
  const s = slide('Cơ chế gom cụm trên lưới STING', 'Nguồn: src/sting.py; ví dụ 15 điểm; kiểm chứng giả lập trong notebook');
  paragraph(s, 'steps', 'Biến thể STING của đồ án', '1. fit() dựng lưới, lưu thống kê từng ô.\n\n2. cluster() giữ các ô đủ điểm ở tầng đã chọn.\n\n3. DFS nối các ô dày chung cạnh thành cụm.\n\n4. predict() tra ô để gán nhãn hoặc trả −1.', 60, 156, 690, 340, 28);
  text(s, 'toy-title', 'Ví dụ 3 × 3, ngưỡng = 3', 790, 154, 430, 44, 27, C.teal, true);
  const t = table(s, 'toy-grid', [[4,3,0],[1,0,4],[0,0,3]], 790, 215, [125,125,125], [82,82,82], 36);
  for (let r=0;r<3;r++) for(let c=0;c<3;c++) {
    const cell=t.getCell(r,c); const a=(r===0&&c<2), b=(c===2&&r>0);
    cell.fill=a?C.paleTeal:b?C.paleBlue:C.light;
    cell.text.style={typeface:FONT,fontSize:36,bold:a||b,color:a?C.teal:b?C.blue:C.gray,alignment:'center',verticalAlignment:'middle',insets:10};
  }
  text(s, 'toy-result', '2 cụm × 7 điểm, 1 điểm nhãn −1\nKề góc không nối cụm', 790, 483, 430, 92, 25);
  text(s, 'implementation', 'PAPI · Lưới 16 × 16, ô dày có ít nhất 5 điểm.\nTra từng trục: lấy phần nguyên của\n(điểm − biên dưới) ÷ bề rộng ô.', 60, 505, 690, 105, 25, C.navy);
  text(s, 'synthetic', `Giả lập 240 điểm: ARI = ${dec(d.synthetic_ari)}; ${d.synthetic_clusters} cụm; ${d.synthetic_noise}/240 điểm nhãn −1.`, 60, 618, 1160, 40, 25, C.teal, true);
  notes(s, 'Bảng 3×3 hiển thị số điểm từng ô, tổng 15. Hai ô hàng trên có count 4 và 3 tạo cụm A gồm 7 điểm. Hai ô bên phải có count 4 và 3 tạo cụm B gồm 7 điểm. Một điểm trong ô thưa nhận nhãn -1. Đồ án sử dụng biến thể gom ô dày tại một mức, với láng giềng kề cạnh trong 2D. STING gốc của Wang, Yang và Muntz mô tả lưới thống kê phân cấp và xử lý truy vấn vùng theo cách top-down; không nên tuyên bố biến thể count-threshold hiện tại tái hiện toàn bộ thuật toán truy vấn gốc. query_top_down là một chức năng riêng trong mã, không phải đường gán cụm dùng cho các kết quả PAPI. Thí nghiệm 240 điểm sinh từ hai Gaussian với seed 42, ngưỡng 3, kiểm tra bảo toàn count qua mọi tầng. ARI này thuộc dữ liệu giả lập có nhãn tham chiếu, không phải độ chính xác trên PAPI.', ['src/sting.py', 'scripts/common/midterm_clustering.py', 'notebooks/Nhom15_STING_PAPI.ipynb'], ['https://www.vldb.org/conf/1997/P186.PDF']);
}
// 04. Historical reference distribution.
{
  const s = slide('Một cụm lớn chiếm ưu thế trong dữ liệu lịch sử', 'Nguồn: nhãn lưới cố định 2011–2023, n = 808');
  chart(s, 'bar', 'reference-sizes', {
    position:{left:60,top:170,width:750,height:380},categories:['Nhãn −1','Cụm 0','Cụm 1','Cụm 2'],
    series:[{name:'Số quan sát',values:['-1','0','1','2'].map(k=>d.reference_counts[k]),fill:C.teal,points:[{idx:0,fill:C.gray}]}],
    hasLegend:false,barOptions:{direction:'bar',grouping:'clustered',gapWidth:70},
    xAxis:{visible:true,majorGridlines:null},
    yAxis:{visible:true,min:0,max:700,majorUnit:100,numberFormatCode:'0',majorGridlines:{style:'solid',fill:C.line,width:1}},dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:FONT,fontSize:'20pt',bold:true,color:C.ink}}
  });
  const clustered=d.reference_counts['2']+d.reference_counts['1']+d.reference_counts['0'];
  text(s,'dominance',pct(d.reference_counts['2']/clustered),865,170,350,98,72,C.teal,true);
  text(s,'dominance-detail',`${d.reference_counts['2']}/${clustered} quan sát\nđã vào cụm thuộc Cụm 2`,865,278,350,105,29);
  text(s,'noise-detail',`${d.reference_counts['-1']}/${d.reference_n} quan sát (${pct(d.reference_counts['-1']/d.reference_n)})\nnhận nhãn −1`,865,433,350,103,27);
  text(s,'meaning','Ba nhãn cụm chưa cho thấy ba nhóm cân bằng hoặc ba cấp chất lượng quản trị.',60,593,1155,66,29,C.navy,true);
  notes(s,'Lưới tham chiếu fit trên 808 quan sát đủ hai chỉ tiêu trong 2011–2023. Cụm 0 có 5, Cụm 1 có 16 và Cụm 2 có 629 quan sát; 158 nhận -1. Cụm lớn chiếm 96,8% trong 650 quan sát được gán cụm. Hai cụm nhỏ chỉ có quan sát trong giai đoạn 2011–2018 và không nhận điểm 2024. Đây là hạn chế chính của cấu trúc cụm. Giá trị thực tế là nhận diện vùng tập trung và các điểm ngoài vùng cần xem xét, không ép diễn giải ba nhãn thành ba phân khúc chính sách. Kích thước [453,16,5] trong selection_metrics thuộc fit đến 2020, không phải model 808 quan sát.', ['results/predict_all_years.csv','results/predict_summary.md','models/predict_config.json']);
}
// 05. Same-sample comparison and affine invariance.
{
  const s = slide('Đối chứng trên cùng tập quan sát', 'Nguồn: STING, K-means và DBSCAN cùng dùng hai đặc trưng đã chuẩn hóa');
  table(s,'comparison',[['Phương pháp','Số cụm','Nhãn −1 / 808','Silhouette / 631'],...d.comparison.map(r=>[r.method,r.clusters,`${dec(r.noise_pct,1)}%`,dec(r.silhouette)])],60,156,[440,170,260,290],[66,73,73,73],27);
  text(s,'shared',`Silhouette chỉ tính trên ${d.shared_n} điểm cùng được STING và DBSCAN gán vào cụm.`,60,476,1160,66,27,C.navy,true);
  text(s,'warning','K-means có silhouette cao nhất trên mẫu này. Ý nghĩa quản trị cần kiểm chứng riêng.',60,536,1160,74,26);
  text(s,'affine',`Thí nghiệm toàn kỳ: ${d.same_cells}/869 điểm giữ nguyên ô STING sau z-score.`,60,624,1160,38,24,C.teal,true);
  notes(s,`Ba thuật toán fit cùng 808 quan sát chuẩn hóa. Mẫu giao ${d.shared_n} loại những điểm STING hoặc DBSCAN gán -1. Đếm cụm và tỷ lệ nhiễu trong bảng vẫn dùng toàn bộ 808, nên mẫu số được ghi rõ. Không so silhouette tính trên các tập khác nhau để tuyên bố một thuật toán tốt nhất. Với dữ liệu mô tả toàn kỳ 869, giao chung là 680 và silhouette khoảng 0,380 / 0,461 / 0,274. Thí nghiệm bất biến affine dựng lại biên lưới trên cùng 869 điểm: ${d.same_cells}/869 chỉ số ô giữ nguyên khi đổi dữ liệu thô sang z-score, nhãn giữ nguyên=${d.same_labels}. Điều này do lưới đều theo min/max từng trục và biến đổi affine dương, không phải chuẩn hóa luôn vô dụng. Không suy rộng sang PCA, phép biến đổi phi tuyến hoặc thay tập fit. K-means raw và z-score có thể thay nhóm vì khoảng cách đổi trọng số tương đối.`,['src/sting.py','scripts/common/midterm_clustering.py','scripts/deliverables/build_slides.py','results/metrics.csv']);
}
// 06. Observed 2024 coordinates and the complete descriptive handoff table.
{
  const s=slide('Quan sát 2024 và bảng mô tả 63 tỉnh','Nguồn: điểm đã quan sát năm 2024; stakeholder_province_summary_2024.csv');
  text(s,'observed-count','48 / 61 tỉnh đủ điểm nằm trong vùng dày. 13 tỉnh ở ô thưa, 2 tỉnh thiếu dữ liệu.',60,137,1160,55,28,C.teal,true);
  const members = key => {
    const names = new Set(d.groups.find(group => group.key === key).names);
    return d.stakeholders.filter(row => names.has(row.province_vi));
  };
  const [core, high, low] = ['core', 'high_side', 'low_61'].map(members);
  const series=[[core,'Trong vùng dày',C.teal,'circle'],[high,'Ngoài vùng, điểm cao',C.blue,'diamond'],[low,'Ngoài vùng, 6.1 thấp',C.orange,'square']].map(([rows,name,color,symbol])=>({name,xValues:rows.map(r=>Number(r.sd_4_2.toFixed(6))),values:rows.map(r=>Number(r.sd_6_1.toFixed(6))),xValuesFormatCode:'0.000000',valuesFormatCode:'0.000000',marker:{symbol,size:7,fill:color,line:{style:'solid',fill:color,width:1}},line:none}));
  chart(s,'scatter','observed-2024',{position:{left:45,top:200,width:560,height:369},series,scatterOptions:{style:'marker'},hasLegend:false,xAxis:{min:1.75,max:2.35,majorUnit:0.1,numberFormatCode:'0.00',title:{text:'4.2  Kiểm soát tham nhũng',textStyle:axisText},majorGridlines:{style:'solid',fill:C.line,width:1}},yAxis:{min:1.6,max:2.25,majorUnit:0.1,numberFormatCode:'0.00',title:{text:'6.1  Y tế công lập',textStyle:axisText},majorGridlines:{style:'solid',fill:C.line,width:1}}});
  const names={core:'● Trong vùng dày',high_side:'◆ Ngoài vùng dày,\nphía điểm cao',low_61:'■ Ngoài vùng dày,\nđiểm 6.1 thấp',missing:'Thiếu dữ liệu 2024'};
  const t=table(s,'groups',[['Nhóm mô tả','Tỉnh','Trung vị\n4.2','Trung vị\n6.1'],...d.groups.map(g=>[names[g.key],g.n,g.median_42===null?'—':dec(g.median_42),g.median_61===null?'—':dec(g.median_61)])],640,206,[262,70,124,124],[60,67,83,83,64],24);
  for(const [row,color] of [[1,C.teal],[2,C.blue],[3,C.orange],[4,C.gray]])t.getCell(row,0).text.style={typeface:FONT,fontSize:24,color,bold:true,alignment:'left',verticalAlignment:'middle',insets:{left:14,right:14,top:10,bottom:10},autoFit:'none',wrap:'square'};
  const fence = dec(d.threshold_61,4);
  text(s,'fence',`Ô thưa: nhóm 6.1 thấp có 6.1 < ${fence}. Nhóm phía điểm cao có 6.1 ≥ ${fence} và 4.2 ≥ ${dec(d.core_median_42,4)}.`,60,586,1160,39,23,C.navy,true);
  text(s,'scope',`Mốc nội bộ tính từ 48 tỉnh trong vùng dày. Trong số đó, ${d.core_lower_n} tỉnh cũng có 6.1 dưới ngưỡng.`,60,628,1160,37,23);
  notes(s,'Đây là gán điểm đã quan sát năm 2024 lên lưới được fit đến hết 2023, không phải dự báo. Trong 63 tỉnh, 61 tỉnh đủ hai chỉ tiêu: 48 vào Cụm 2 và 13 nằm trong các ô thưa có từ 0 đến 3 điểm lịch sử. Không điểm nào nằm ngoài biên min/max lịch sử. Vĩnh Phúc và Tiền Giang thiếu dữ liệu; hai tỉnh này không bị gán thành nhiễu. Màu và hình marker trên đồ thị tương ứng các nhóm có cùng màu chữ trong bảng.\n\nBốn nhóm là diễn giải sau phân cụm, không phải bốn cụm STING hay chứng nhận chất lượng. Ngưỡng 6.1 = Q25 − 0,5 × IQR = 1,8791 lấy từ 48 tỉnh trong vùng dày năm 2024, nên là quy tắc hậu nghiệm cần xác minh độc lập. Có 7 tỉnh trong vùng dày cũng thấp hơn ngưỡng; không gọi cả cụm là chất lượng tốt hoặc ổn định. Nhóm ngoài vùng phía điểm cao gồm 8 tỉnh; trung vị 4.2 = 2,235 và 6.1 = 1,963. Nhóm 5 tỉnh ngoài vùng có 6.1 thấp gồm Hà Nội (1,686), Cần Thơ (1,698), Gia Lai (1,787), Long An (1,807), Bình Dương (1,808). Không diễn giải nhãn −1 là yếu kém.\n\nGRDP/người trung vị theo thứ tự bốn nhóm trong bảng là 81,0; 87,4; 104,3; 108,9 triệu đồng/người năm 2024. Nhóm 5 tỉnh có GRDP cao hơn nhóm trong vùng và 6.1 thấp là một đối chiếu mô tả, không chứng minh quá tải y tế hay quan hệ nhân quả. Có 5 tỉnh được gán Cụm 2 trong 14/14 năm: Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long; giữ nhãn không có nghĩa điểm số không đổi. Bảng CSV đủ 63 tỉnh cùng cờ thiếu, tọa độ và dữ liệu ngoài là sản phẩm hỗ trợ rà soát.', ['results/papi_observed_grid_2024.csv','results/stakeholder_province_summary_2024.csv','scripts/analysis/stakeholder_summary.py','models/sting_predict_scaler.json','data/processed/external_gso_grdp_63.csv']);
}
// 07. Transition matrix and one auditable example.
{
  const s=slide('Dịch chuyển 2023–2024 trên cùng lưới','Nguồn: 59 tỉnh đủ điểm ở cả hai năm; nhãn do cùng một lưới cố định sinh ra');
  table(s,'transition',[['2023 / 2024','Trong vùng dày','Ngoài vùng dày'],['Trong vùng dày',...d.transitions[0]],['Ngoài vùng dày',...d.transitions[1]]],60,165,[224,190,190],[65,82,82],25);
  const movedOut = d.stakeholders.filter(row => row.cluster_2023 === 2 && row.cluster === -1);
  const under = movedOut.filter(row => row.sd_6_1 < d.threshold_61).length;
  text(s,'transition-count',`${movedOut.length} tỉnh rời vùng dày, ${d.transitions[1][0]} tỉnh đi vào`,60,421,604,52,30,C.teal,true);
  text(s,'transition-split',`Trong ${movedOut.length} tỉnh rời vùng, ${movedOut.length - under} tỉnh ở phía điểm cao và ${under} tỉnh có 6.1 dưới mốc nội bộ.`,60,474,604,76,25);
  text(s,'transition-limit','Đọc điểm từng trục và ngưỡng số điểm trước khi diễn giải thay đổi nhãn.',60,573,604,72,24,C.gray);
  text(s,'trace-title','Truy vết Lạng Sơn',708,160,512,45,29,C.teal,true);
  const [earlier, latest] = d.trace;
  table(s,'trace',[['Năm','Điểm 4.2 / 6.1','Ô lưới','Số điểm\ntham chiếu'],...d.trace.map(r=>[
    r.year,`${dec(r.x)} / ${dec(r.y)}`,`(${r.cell.join(', ')})`,r.count
  ])],708,222,[82,176,108,146],[66,64,64],23);
  const axisExamples = [latest.x, latest.y].map((score, i) =>
    `${['4.2', '6.1'][i]}   ⌊(${dec(score)} − ${dec(d.grid_raw_lo[i])}) / ${dec(d.grid_raw_step[i],4)}⌋ = ${latest.cell[i]}`
  );
  text(s,'trace-example',`Tính ô năm ${latest.year} (số làm tròn)`,708,443,512,40,24,C.teal,true);
  text(s,'trace-calculation',axisExamples.join('\n'),708,485,512,73,24);
  const minCount = d.config.sting.min_count;
  text(s,'trace-rule',`${earlier.count} < ${minCount} → nhãn −1   ·   ${latest.count} ≥ ${minCount} → Cụm ${latest.label}`,708,577,512,51,24,C.navy,true);
  notes(s,`Ma trận có tổng ${d.transition_n}: 43 giữ vùng dày, 7 rời vùng dày, 5 từ ngoài vào và 4 vẫn ngoài. Bốn tỉnh thiếu điểm ở ít nhất một năm nằm ngoài ma trận. Trong 7 tỉnh rời vùng, 5 nằm phía điểm cao và 2 có 6.1 dưới ngưỡng. Có 39/43 tỉnh giữ Cụm 2 vẫn đổi ô.\n\nVới Lạng Sơn, mỗi trục lấy phần nguyên của khoảng cách đến biên dưới chia bề rộng ô. Hai trục đánh số từ 0. Trong mã, điểm và biên đã được chuẩn hóa. Đổi điểm và biên về thang gốc giữ nguyên chỉ số vì z-score là phép biến đổi affine dương. Phép tính với số gốc cho hai thương khoảng 12,164 và 10,757 năm 2024. Với điểm tại biên trên, mã giới hạn chỉ số tối đa là 15. Lạng Sơn năm 2023 thuộc ô (13, 9) có 2 điểm lịch sử nên nhận −1. Năm 2024 thuộc ô (12, 10) có 12 điểm và ô đã nằm trong Cụm 2. Hai số đếm thuộc hai ô khác nhau trên cùng lưới. Đọc điểm từng trục cùng nhãn lưới để hiểu hướng dịch chuyển.`,['src/sting.py','results/predict_all_years.csv','results/papi_observed_grid_2024.csv','scripts/common/papi_pred_common.py']);
}
// 08. Forecasting differs from assignment of observed points.
{
  const s=slide('Dự báo điểm cải thiện MAE nhưng bỏ sót vùng rìa','Nguồn: papi_forecast_2024.json; course_supervised_baselines.csv; hồi kiểm 2024 (n = 59)');
  const score=(target,method)=>d.forecast.scores.find(r=>r.target===target&&r.method===method);
  table(s,'forecast-scores',[['Chỉ tiêu','MAE Ridge','MAE giữ 2023','RMSE Ridge','RMSE giữ 2023'],...['sd_4_2','sd_6_1'].map((f,i)=>[i===0?'4.2':'6.1',dec(score(f,'forecast').mae,4),dec(score(f,'carry').mae,4),dec(score(f,'forecast').rmse,4),dec(score(f,'carry').rmse,4)])],60,153,[160,250,250,250,250],[61,68,68],25);
  text(s,'recall-value',`0 / ${d.forecast.actual_outside}`,60,372,500,72,58,C.orange,true);
  text(s,'recall-label','tỉnh ngoài vùng dày được mô hình dự báo phát hiện. Balanced accuracy = 0,500.',60,451,510,101,26);
  text(s,'auc-value',`AUC ${dec(d.forecast.scenario_auc)}`,680,372,530,72,56,C.teal,true);
  text(s,'auc-label',`${d.forecast.scenario_count} cặp phần dư tạo kịch bản.\nHồi cứu thăm dò; chưa phải xác suất hiệu chỉnh hay kiểm chứng tiền cứu.`,680,451,530,103,25);
  const nb = d.course_baselines.find(row => row.model === 'gaussian naive bayes');
  text(s,'classification-scope',`Khớp nhãn STING với Naive Bayes: macro-F1 ${dec(nb.value_cv)} (CV) và ${dec(nb.holdout_macro_f1)} (kiểm tra 2024).\nĐối chứng gồm KNN, SVM, cây quyết định, Random Forest và Logistic Regression.`,60,576,1160,80,24,C.navy);
  notes(s,'Ridge dự báo hai chỉ tiêu từ 8 tiểu chiều của năm trước, chọn theo MAE qua 6 lượt CV 2018–2023, fit cuối trên 738 cặp. Có 61 dự báo từ dữ liệu năm 2023 và 59 cặp dự báo–quan sát đủ cho đánh giá năm 2024. Đây là nhánh dự báo hai đầu ra, khác thí nghiệm hồi quy một mục tiêu trong các bảng supervised khác. MAE giảm nhẹ trên cả hai trục, nhưng RMSE của 4.2 tăng từ 0,0953 lên 0,0972. Tất cả 59 dự báo điểm ở trong vùng dày, bỏ sót 11 điểm ngoài vùng quan sát; độ đúng thường 48/59 = 81,4% chỉ bằng majority baseline, balanced accuracy 0,500. Kịch bản cộng 364 cặp phần dư CV vào dự báo tạo tỷ lệ ngoài vùng và AUC hồi cứu khoảng 0,816. Phần dư được gom sau bước chọn mô hình và chưa kiểm định tiền cứu độc lập; không gọi tỷ lệ này là xác suất đã hiệu chỉnh. Năm 2024 có 13/61 tỉnh ngoài vùng quan sát, nhưng chỉ 11/59 nằm trong mẫu đánh giá dự báo.\n\nNội dung học có giám sát được triển khai riêng: hồi quy dự báo giá trị liên tục, phân loại dự báo nhãn trong/ngoài vùng dày do STING sinh. Các baseline gồm Gaussian Naive Bayes, KNN, SVM tuyến tính và RBF, cây quyết định, Random Forest và Logistic Regression. Chọn theo macro-F1 qua 6 fold expanding origin 2017–2022, không chọn theo holdout 2024. Naive Bayes có macro-F1 CV 0,514, KNN 0,486; khoảng cách 0,028 nhỏ hơn độ lệch fold của Naive Bayes 0,120 nên không kết luận vượt trội. Nhãn có tính kỹ thuật, chưa phải chất lượng quản trị do chuyên gia xác nhận. Hai fold cuối trùng một phần các năm đã dùng để chọn cấu hình STING, nên CV classifier là thăm dò, chưa độc lập hoàn toàn với quá trình chọn nhãn. Accuracy có thể che mất lớp ít; đọc macro-F1, recall từng lớp và ma trận nhầm lẫn. Phân biệt baseline đa số học từ train với quy tắc luôn đoán lớp đa số của holdout; không dùng nhãn holdout để chọn mô hình.', ['results/papi_forecast_2024.json','scripts/common/papi_forecast.py','results/papi_forecast_provinces_2024.csv','results/course_supervised_baselines.csv','results/course_supervised_baselines.md']);
}
// 09. Independent sources are exploratory checks, not external labels.
{
  const s=slide('Đối chiếu nguồn dữ liệu ngoài PAPI','Nguồn: external_validation.csv/md; poverty_validation.csv; kiểm định gộp mang tính thăm dò');
  const e=d.external_checks;
  const sciP=(value)=>Number(value).toExponential(2).replace('.',',');
  table(s,'external',[['Nguồn / giai đoạn','n','p (Kruskal)','Diễn giải'],['PCI 2011–2022',e.pci_n,sciP(e.pci_p),'Trung vị Cụm 2: 62,16\nNhãn −1: 59,16'],['GRDP/người 2018–2024',e.grdp_n,dec(e.grdp_p,5),'Khác biệt mô tả giữa nhóm,\nkhông suy ra quan hệ nhân quả'],['Điểm cơ sở y tế ODM 2020',e.odm_n,dec(e.odm_p),'Chưa có bằng chứng khác biệt.\n'+e.odm_zero_count+' tỉnh không ghi nhận điểm nguồn'],['Nghèo GSO 2012–2024',e.poverty_n,dec(e.poverty_raw_p)+' (thô)','Trừ trung vị năm: p = '+dec(e.poverty_demeaned_p,6)+'\nHiệu ứng ANOVA '+e.poverty_eta_note.split(' (')[0].replace('.',',')]],60,147,[365,75,215,505],[65,88,88,94,94],24);
  text(s,'external-limit','Quan sát lặp theo tỉnh, khác biệt năm và độ phủ nguồn hạn chế giá trị suy luận của p-value.',60,601,1160,64,25,C.navy,true);
  notes(s,'Nguồn độc lập là phép đối chiếu mô tả, không cung cấp nhãn cụm thật. Không kết luận STING phản ánh đúng chất lượng quản trị chỉ vì p nhỏ. Các phép kiểm định gộp chưa mô hình hóa đầy đủ phụ thuộc giữa nhiều năm của cùng tỉnh; p-value là tham khảo. Bổ sung kiểm định bảng chuẩn hóa năm và sai số chuẩn gộp 63 tỉnh (CR1, B=1.999 Wild Cluster Bootstrap trong results/panel_inference.md) chứng minh: trên STING 2D, tín hiệu PCI gộp thô (8,14e-7) hoàn toàn là nhiễu trộn theo năm và biến mất sau Year-FE CR1 (p = 0,7007; Wald F 4 nhóm p = 0,9237), tương tự GRDP (p CR1 = 0,0662) và Nghèo (p CR1 = 0,8888). Ngược lại, nhánh mở rộng 8D QuantileSTING mc=7 vẫn giữ chênh lệch có ý nghĩa trên PCI (+1,561 điểm, p CR1 = 0,0156, Holm = 0,0468; bền vững sau chuẩn hóa within-year z p = 0,0205) theo cơ chế phân tầng giữa các tỉnh (TWFE p = 0,3420), đồng thời loại được dương giả trên GRDP (p CR1 = 0,0746).\n\nPCI dùng 2011–2022 đầy đủ, không trộn top-30 có chọn lọc ở 2023–2024. GRDP dùng 2018–2024, đơn vị triệu đồng/người. ODM chỉ là số điểm cơ sở xuất hiện trong tập nguồn: 10 tỉnh có count=0 nghĩa là nguồn không ghi nhận cơ sở, không khẳng định tỉnh thực tế không có cơ sở. Mẫu kiểm định ODM vẫn là 63 như pipeline gốc. Nghèo sau trừ trung vị từng năm có p giảm nhưng eta squared từ ANOVA chỉ 0,0124; không suy ra tác động nhân quả và không gọi p=0,198 là chứng minh không có khác biệt.', ['results/external_validation.csv','results/external_validation.md','results/poverty_validation.csv','results/panel_inference.csv','results/panel_inference.md','data/raw/gso/PROVENANCE.md','data/raw/odmekong/PROVENANCE.md']);
}
// 10. Higher-dimensional sensitivity.
{
  const s=slide('Độ bền khi mở rộng số chiều','Nguồn: robustness.csv; các thử nghiệm mô tả gộp theo năm, không dùng để đánh giá dự báo');
  const labels=['PCA 2 thành phần từ d1–d6','8D, cấu hình gốc','8D, đổi factor = 3','8D, đổi min_count = 2','8D, đổi level = 2'];
  table(s,'robustness',[['Thiết lập','n','Số cụm','Nhãn −1','Silhouette'],...d.robustness.map((r,i)=>[labels[i],r.n,r.k,pct(r.noise_ratio),r.silhouette===null?'Không xác định':dec(r.silhouette)])],60,154,[540,90,130,170,230],[65,63,63,63,63,63],25);
  text(s,'base','Cấu hình gốc 8D: factor = 2, min_count = 10, level = 1; mỗi lần chỉ đổi một tham số.',60,568,1160,62,25);
  text(s,'robust-limit','Giảm nhiễu chưa đủ: min_count = 2 cho silhouette âm (−0,089), mức tách cụm yếu.',60,625,1160,35,24,C.orange,true);
  notes(s,'PCA dùng 6 chiều d1–d6 chuẩn hóa trong từng năm rồi giảm còn 2 thành phần, tổng phương sai giải thích 63,2%, kết quả một cụm. Không có silhouette khi dưới hai cụm. Nhánh 8D chỉ dùng 2018–2024 với 430 quan sát đầy đủ. Cấu hình gốc có 60,5% nhiễu; tăng factor lên 3 có 91,9%; tăng level lên 2 có 100%. Hạ min_count xuống 2 giảm nhiễu còn 10,9% và cho 2 cụm, nhưng silhouette âm khoảng -0,089 nên không mô tả như bằng chứng cấu trúc tốt. Nhãn verdict trong CSV là quy tắc lọc k/nhiễu của pipeline; nhận xét trên slide bổ sung giới hạn silhouette. Số chiều tăng làm các ô lưới thưa hơn với cấu hình này; kết quả không chứng minh mọi biểu diễn 8D đều thất bại.\n\nMở rộng đa chiều (src/high_dim.py, chỉ khớp ≤2023 không rò rỉ 2024) giải quyết giới hạn trên qua hai nhánh: (1) Subspace CLIQUE Apriori giữ được cấu trúc đến 5D lưới đều (phủ 41,0%, Silh. 0,433) và 4D Quantile tách [57, 45] (Silh. 0,772, PCI khử năm p=6,99e-6, phủ 12,6% cực trị); (2) QuantileSTING hiệu chuẩn theo n/res^d hạ nhiễu d1–d8 từ 60,5% xuống 44,7% (Silh. +0,161), và trên 8 tiểu chỉ tiêu sàng lọc (n=808, mc=7) tách k=4 [222, 219, 8, 8] (phủ 56,6% train / 60,7% 2024, PCI khử năm p=0,0005, giữ k=3 ngay cả sau chuẩn hóa within-year z). Thang thưa d=2..8 xác nhận lưới mịn 16^d nhảy từ 24,1% lên 93,9% (d=3) và 100% (d=4), còn trên 2D 16×16 thì Quantile làm vỡ lõi (49,0% vs 19,6% đều) nên bản chính 2D 3/4/5/2 tiếp tục giữ lưới đều; p-value không gian con là thăm dò chưa hiệu chỉnh đa kiểm định.', ['results/robustness.csv','scripts/analysis/run_analysis.py','results/analysis_summary.md','src/high_dim.py','scripts/analysis/high_dim_sting.py','results/high_dim_sting.csv','results/high_dim_sting.md']);
}
// 11. Descriptive findings tied back to the clustering output.
{
  const s=slide('Thống kê và nhận xét kết quả 2024','Nguồn: điểm PAPI quan sát và nhãn từ lưới STING dựng trên giai đoạn 2011–2023');
  const [core, high, low, missing] = d.groups;
  const names = ['Trong vùng dày (Cụm 2)', 'Ô thưa phía điểm cao', 'Ô thưa có 6.1 dưới mốc', 'Thiếu dữ liệu'];
  table(s,'reported-groups',[['Nhóm mô tả','Số tỉnh','Tỉ lệ'],...d.groups.map((g,i)=>[
    names[i],g.n,pct(g.share)
  ])],60,181,[300,100,119],[60,65,70,70,62],25);
  const total = d.groups.reduce((sum, group)=>sum+group.n,0);
  text(s,'report-denominator',`Tỉ lệ tính trên ${total} tỉnh.\n${total-missing.n} tỉnh đủ cả hai điểm quan sát.`,60,537,519,85,25,C.navy);

  s.shapes.add({name:'findings-panel',geometry:'rect',position:{left:624,top:155,width:596,height:467},fill:C.paleTeal,line:{style:'solid',fill:C.line,width:1}});
  text(s,'findings-title','Nhận xét',654,180,536,42,31,C.teal,true);
  paragraph(s,'finding-dominance','Cụm 2 chiếm ưu thế',`${core.n}/${total-missing.n} tỉnh đủ điểm thuộc Cụm 2.`,654,241,536,90,25);
  paragraph(s,'finding-sparse','Các tỉnh cùng nhãn −1 có điểm khác nhau',
    `Trung vị 4.2 nhóm ${high.n}: ${dec(high.median_42)} · vùng dày: ${dec(core.median_42)}.\nTrung vị 6.1 nhóm ${low.n}: ${dec(low.median_61)} · vùng dày: ${dec(core.median_61)}.`,654,348,536,124,23);
  paragraph(s,'finding-within','Vùng dày vẫn có khác biệt về 6.1',
    `${d.core_lower_n} tỉnh có 6.1 dưới mốc nội bộ ${dec(d.threshold_61,4)}.`,654,490,536,99,24);
  notes(s,'Kết quả STING năm 2024 có 48 tỉnh vào Cụm 2 và 13 tỉnh ở ô thưa với nhãn −1. Báo cáo dùng điểm PAPI để tách 13 tỉnh này thành hai nhóm mô tả. Mẫu số của bảng là 63 và gồm cả 2 tỉnh thiếu dữ liệu; 48/61 trả lời câu hỏi bao nhiêu tỉnh có điểm được vào Cụm 2.\n\nSo sánh trung vị trong cùng năm. Nhóm 8 tỉnh phía điểm cao có trung vị 4.2 là 2,235 so với 2,032 trong vùng dày. Nhóm 5 tỉnh dưới mốc 6.1 có trung vị là 1,787 so với 1,963 trong vùng dày. Trong vùng dày, 7 tỉnh vẫn dưới mốc 6.1 = 1,8791. Các quan sát này mô tả phân bố điểm trên hai chỉ tiêu và cần thêm dữ liệu để diễn giải chất lượng quản trị. Ví dụ để trả lời khi được hỏi: Hà Nội có 6.1 = 1,686, ô (10, 5) có 3 điểm tham chiếu nên nhận −1. Tọa độ ô, số đếm và lịch sử 14 năm có trong phiếu rà soát theo tỉnh.', ['results/papi_observed_grid_2024.csv','results/stakeholder_province_summary_2024.csv','reports/Nhom15_BaoCao_STING_PAPI.docx']);
}
// 12. Conclusion and limits.
{
  const s=slide('Kết luận và hướng phát triển','Tài liệu chính: Wang, Yang & Muntz (VLDB 1997); PAPI; Mendeley; nguồn PCI, GSO, ODM');
  paragraph(s,'contribution','Kết luận từ kết quả','STING nối các ô dày và cho phép truy vết từng nhãn theo số điểm trong ô.\nCụm 2 chiếm ưu thế. Các tỉnh ở ô thưa có thể nằm phía điểm cao hoặc thấp.',60,155,1160,120,29);
  paragraph(s,'limits','Giới hạn','Phân cụm dùng hai chỉ tiêu và kết quả nhạy với tham số lưới.\nCác ngưỡng mô tả và kết quả dự báo cần được kiểm tra trên dữ liệu mới.',60,327,1160,127,29);
  paragraph(s,'future','Bước tiếp theo','Đánh giá cuốn chiếu, kiểm định ngưỡng trên dữ liệu độc lập.\nHiệu chỉnh kịch bản và thẩm định với người dùng địa phương.',60,484,1160,116,28);
  text(s,'thanks','Cảm ơn thầy và các bạn. Nhóm xin nhận câu hỏi.',60,625,1160,38,26,C.teal,true);
  notes(s,'Đóng góp của đồ án nằm ở khả năng giải thích, kiểm chứng và tái lập quy trình. Không đặt mục tiêu chứng minh STING luôn tốt hơn các thuật toán khác. Kết quả chính cần nhớ: 808 quan sát lịch sử, 61 tỉnh đủ điểm năm 2024, trong đó 48 trong vùng dày và 13 ô thưa. Bốn nhóm mô tả bao quát 63 tỉnh. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng trong tập đánh giá 59 tỉnh. Các phân tích mở rộng — gồm QuantileSTING và Subspace CLIQUE đa chiều (results/high_dim_sting.md: 8D d1–d8 giảm nhiễu còn 44,7% với Silh. +0,161; 8D sàng lọc tách k=4 phủ 56,6%/60,7% năm 2024; giữ chuẩn 2D lưới đều 3/4/5/2), lớp suy luận bảng Year-FE CR1 / TWFE & FDR đa kiểm định (results/panel_inference.md: 8D Quantile mc=7 sống sót Year-FE CR1 + Holm 5% trên PCI p = 0,0156 với cơ chế between-province; 117/383 không gian con đạt BH-FDR 5%; phần dư Ridge 2024 trắng về không gian Moran\'s I = -0,0431, p = 0,6600), đối chiếu 17 cấu hình hồi quy và khoảng Conformal 90% (results/regression_deep_analysis.md), cùng hồi kiểm cuốn chiếu, Moran’s I và cân bằng lớp (results/future_work.md) — là thăm dò bổ sung, không thay protocol chốt hay chứng minh tổng quát hóa. Cần đánh giá ngoại mẫu mới, kiểm soát phụ thuộc theo tỉnh và hiệu chỉnh xác suất trước ứng dụng cảnh báo.\n\nTài liệu tham khảo: Wang W., Yang J., Muntz R. (1997), STING: A Statistical Information Grid Approach to Spatial Data Mining, VLDB, pp.186–195. CECODES, VFF-CRT, RTA và UNDP: dữ liệu PAPI 2011–2024. Mendeley Data, DOI 10.17632/wbk42j9wc8.1. VCCI: PCI. GSO PX-Web: GRDP/dân số/nghèo. Open Development Mekong: cơ sở y tế. Hyndman & Athanasopoulos (2021), Forecasting: Principles and Practice, 3rd ed.', ['results/future_work.md','results/high_dim_sting.md','results/panel_inference.md','results/regression_deep_analysis.md','reports/external_data_expansion.md','reports/Nhom15_BaoCao_STING_PAPI.docx'], ['https://www.vldb.org/conf/1997/P186.PDF','https://papi.org.vn/','https://doi.org/10.17632/wbk42j9wc8.1','https://otexts.com/fpp3/']);
}
if(ppt.slides.items.length!==d.slide_count) throw new Error('Slide count does not match evidence manifest');
await fs.mkdir(path.dirname(path.resolve(args.output)),{recursive:true});
await (await PresentationFile.exportPptx(ppt)).save(args.output);
if(args['render-dir']) {
  await fs.mkdir(args['render-dir'],{recursive:true});
  for(const [index,s] of ppt.slides.items.entries()) {
    const stem=`slide-${String(index+1).padStart(2,'0')}`;
    const png=await ppt.export({slide:s,format:'png',scale:1});
    await fs.writeFile(path.join(args['render-dir'],`${stem}.png`),new Uint8Array(await png.arrayBuffer()));
    const layout=await s.export({format:'layout'});
    await fs.writeFile(path.join(args['render-dir'],`${stem}.layout.json`),await layout.text());
  }
}
console.log(`Saved ${ppt.slides.items.length} slides to ${args.output}`);
