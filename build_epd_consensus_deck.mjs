import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { Presentation, PresentationFile } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = process.env.EPD_WORKSPACE_ROOT
  ? path.resolve(process.env.EPD_WORKSPACE_ROOT)
  : __dirname;

const OUTPUT_DIR = path.join(workspaceRoot, "outputs", "epd-consensus-key-slides");
const PPTX_PATH = path.join(workspaceRoot, "outputs", "epd-consensus-key-slides-formal.pptx");
const PAGE = { left: 56, top: 72, width: 1168, height: 592 };

const COLORS = {
  bg: "#F4F7FB",
  white: "#FFFFFF",
  navy: "#102554",
  blue: "#2365D1",
  sky: "#E7F0FF",
  accent: "#F47C4D",
  accentLight: "#FFF1EA",
  slate900: "#14213D",
  slate700: "#3B4A67",
  slate500: "#65748B",
  slate300: "#D7E0EC",
  line: "#DCE5F0",
};

const FONT = "Microsoft YaHei";

const SLIDES = [
  {
    kind: "content",
    id: "spectrum_overview",
    mmss: "00:59",
    title: "疾病谱总览：先建立 EPD 全局认识",
    rawTitle: "EPD 临床表现谱系庞大，正确识别是后续精准诊断的前提",
    image: "video_sprites/selected/slide_crop/spectrum_overview-0059s.jpg",
    summary:
      "这一页承担开场总览功能，提醒我们 EPD 不是单一病名，而是一组临床表现、病理基础和影像特征各不相同的相关疾病。",
    bullets: [
      "学习重点是先把“嗜酸粒细胞增多”和“肺部受累”放到同一诊断框架中。",
      "同一类患者可能呈现气道、肺实质或系统性受累，不能只盯单一器官表现。",
      "把这页放在前面，有助于后续理解为什么需要流程化鉴别。",
    ],
    takeaway: "适合作为病例汇报导入页，用来建立问题意识。",
  },
  {
    kind: "content",
    id: "recognition_principles",
    mmss: "05:59",
    title: "诊断标准页：先抓住判定门槛",
    rawTitle: "明确嗜酸粒细胞增多相关性肺疾病（EPD）诊断标准",
    image: "video_sprites/selected/slide_crop/recognition_principles-0359s.jpg",
    summary:
      "这页把 EPD 识别时最核心的判定门槛集中展示出来，是整段视频里最适合反复回看的基础页之一。",
    bullets: [
      "不要把诊断简化成单一数值阈值，更重要的是临床情境和证据组合。",
      "外周血、组织学和影像学线索需要彼此印证，才能支持疾病归类。",
      "若后续要做正式汇报，可围绕这页再补充对应文献和原共识条目。",
    ],
    takeaway: "建议与原共识原文对照，做成自己的判定清单。",
  },
  {
    kind: "content",
    id: "diagnostic_checklist",
    mmss: "08:59",
    title: "共识提示页：疑似 EPD 的分层评估",
    rawTitle: "2022 年中国 EPD 共识以临床问题为先导，细化评估与诊断次序",
    image: "video_sprites/selected/slide_crop/diagnostic_checklist-0539s.jpg",
    summary:
      "视频在这里把中国共识的诊疗思路拆解成可执行的评估问题，适合转译成门诊或会诊前的核对表。",
    bullets: [
      "先确认是否存在真实嗜酸粒细胞增多，再看是否伴有肺部受累证据。",
      "再往下要追问病因、受累器官、危险信号和是否需要多学科协作。",
      "这类页面很适合转成临床路径表单，而不是只停留在阅读层面。",
    ],
    takeaway: "若用于教学，可把左右两栏改写成“首诊问题单”。",
  },
  {
    kind: "content",
    id: "differential_pathway",
    mmss: "12:59",
    title: "诊断路径页：从发现嗜酸到收敛病因",
    rawTitle: "EPD 评估和诊断程序",
    image: "video_sprites/selected/slide_crop/differential_pathway-0779s.jpg",
    summary:
      "这是整场讲座最关键的流程图页面，适合直接作为病例讨论或院内汇报的底图来使用。",
    bullets: [
      "可以按“发现嗜酸粒细胞异常 -> 证实肺受累 -> 排除继发原因 -> 收敛具体病种”来理解。",
      "流程图的价值在于减少漏诊，也减少把不同病因混为一谈的风险。",
      "实际应用时，最好把实验室、影像和系统症状并列放进流程节点。",
    ],
    takeaway: "正式汇报时最值得单独放大讲解的一页。",
  },
  {
    kind: "content",
    id: "disease_spectrum",
    mmss: "17:59",
    title: "相关疾病页：常见病因与疾病谱提示",
    rawTitle: "寄生虫感染仍然为多见的嗜酸相关 EPD",
    image: "video_sprites/selected/slide_crop/disease_spectrum-1079s.jpg",
    summary:
      "这一页把感染性和非感染性病因同时放进同一张图里，提醒鉴别诊断不能只从免疫炎症角度出发。",
    bullets: [
      "寄生虫感染等常见原因仍需优先考虑，尤其在流行病学背景支持时更不能跳过。",
      "免疫相关疾病、药物因素和系统性疾病需要与感染性原因同步排查。",
      "病例讨论时可据此先搭建“病因树”，再逐层排除。",
    ],
    takeaway: "适合作为病因学鉴别页插入到病例汇报中段。",
  },
  {
    kind: "content",
    id: "abpa_focus",
    mmss: "21:59",
    title: "ABPA 专题页：IgE、EOS 与影像并看",
    rawTitle: "所有伴外周血 EOS 和总 IgE 升高的哮喘患者都需关注 ABPA 可能",
    image: "video_sprites/selected/slide_crop/abpa_focus-1319s.jpg",
    summary:
      "这页把 ABPA 的识别线索收得很集中，适合在支气管哮喘、反复肺部阴影和支扩场景中重点回看。",
    bullets: [
      "关键不是某一项指标单独升高，而是病史、实验室和影像共同指向同一问题。",
      "总 IgE、EOS 水平与肺部影像特征要结合既往哮喘或过敏背景来理解。",
      "如果做专题课，这页可以拆成“提示线索”和“进一步证据”两部分。",
    ],
    takeaway: "适合放进哮喘合并肺部影像异常的鉴别章节。",
  },
  {
    kind: "content",
    id: "egpa_focus",
    mmss: "24:59",
    title: "EGPA 专题页：系统性受累是识别关键",
    rawTitle: "EGPA 是一种以嗜酸粒细胞增多为主要特征并可累及多个器官系统的疾病",
    image: "video_sprites/selected/slide_crop/egpa_focus-1499s.jpg",
    summary:
      "这一页强调 EGPA 绝不只是肺部疾病，真正的识别关键在于多系统表现是否被同时看见。",
    bullets: [
      "除呼吸系统外，皮肤、神经、心血管等受累提示都应纳入病史和查体清单。",
      "当患者已经存在哮喘背景时，更要留意是否出现系统性扩展信号。",
      "会诊汇报时可把“器官受累谱”独立成一栏，提升判断效率。",
    ],
    takeaway: "适合和 ANCA、系统症状一起做专题延展。",
  },
  {
    kind: "content",
    id: "mechanism_pathology",
    mmss: "27:59",
    title: "少见疾病页：KD / EMS / EF 的鉴别提醒",
    rawTitle: "KD、EMS、EF 的诊断可参考以下标准，需注意排除其他疾病",
    image: "video_sprites/selected/slide_crop/mechanism_pathology-1679s.jpg",
    summary:
      "讲者在这里把相对少见但临床上容易忽略的疾病并列展示，帮助把鉴别诊断从常见病再往外扩一层。",
    bullets: [
      "疑难病例里不能把所有嗜酸粒细胞增多都默认归入常见过敏或哮喘相关疾病。",
      "这类页面的价值在于补齐“少见但关键”的排查清单，降低误归类风险。",
      "如果后续继续深加工，可把这页整理成单独的鉴别速查表。",
    ],
    takeaway: "适合作为疑难病例讨论时的补充页。",
  },
  {
    kind: "content",
    id: "hes_management",
    mmss: "31:59",
    title: "共识汇总页：11 条推荐意见总览",
    rawTitle: "EPD 诊疗中国专家共识：共提出 11 条推荐意见汇总",
    image: "video_sprites/selected/slide_crop/hes_management-1919s.jpg",
    summary:
      "这是整场视频里最适合做复盘锚点的一页，几乎可以直接作为后续正式汇报的大纲起点。",
    bullets: [
      "如果要把讲座整理成院内分享，建议直接以这 11 条推荐意见作为一级标题展开。",
      "本次成品保留了原页截图，方便你后续逐条校对、二次补充证据和改写话术。",
      "从效率上看，这一页最值得单独截图打印或放进病例讨论资料包。",
    ],
    takeaway: "后续若需要扩展全文版 PPT，可从这一页继续拆分。",
  },
];

function resolveAsset(relativePath) {
  return path.join(workspaceRoot, relativePath);
}

async function writeBlob(targetPath, blob) {
  await fs.writeFile(targetPath, new Uint8Array(await blob.arrayBuffer()));
}

async function loadImage(relativePath) {
  return fs.readFile(resolveAsset(relativePath));
}

function addRect(slide, position, fill, extra = {}) {
  return slide.shapes.add({
    geometry: "roundRect",
    position,
    fill,
    line: { style: "solid", fill: extra.lineFill ?? fill, width: extra.lineWidth ?? 0 },
    borderRadius: extra.borderRadius ?? "rounded-xl",
    shadow: extra.shadow,
  });
}

function addText(slide, { left, top, width, height, text, style, fill = "none", lineFill = "none" }) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    wrap: "square",
    autoFit: "shrinkText",
    ...style,
  };
  return shape;
}

function addBulletList(slide, { left, top, width, height, items, fontSize = 21, color = COLORS.slate700 }) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = items.map((item) => ({
    bulletCharacter: "•",
    marginLeft: 28,
    indent: -16,
    spaceAfter: 10,
    runs: [item],
  }));
  shape.text.style = {
    typeface: FONT,
    fontSize,
    color,
    lineSpacing: 1.18,
    wrap: "square",
    autoFit: "shrinkText",
  };
  return shape;
}

function addFooter(slide, slideNumber, totalSlides) {
  addText(slide, {
    left: 64,
    top: 682,
    width: 540,
    height: 20,
    text: "张清玲教授讲座关键页整理 | B站视频 BV13k4y1Q7UR",
    style: { fontSize: 12, color: COLORS.slate500 },
  });
  addText(slide, {
    left: 1120,
    top: 680,
    width: 92,
    height: 20,
    text: `${slideNumber}/${totalSlides}`,
    style: { fontSize: 12, color: COLORS.slate500, alignment: "right" },
  });
}

function addChrome(slide, section, pageTitle, timeLabel, slideNumber, totalSlides) {
  slide.background.fill = COLORS.bg;

  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1280, height: 82 },
    fill: COLORS.navy,
    line: { style: "solid", fill: COLORS.navy, width: 0 },
  });

  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 82, width: 1280, height: 5 },
    fill: COLORS.accent,
    line: { style: "solid", fill: COLORS.accent, width: 0 },
  });

  slide.shapes.add({
    geometry: "ellipse",
    position: { left: 1032, top: -58, width: 256, height: 256 },
    fill: COLORS.blue,
    transparency: 84,
    line: { style: "solid", fill: COLORS.blue, width: 0 },
  });

  addText(slide, {
    left: 62,
    top: 22,
    width: 180,
    height: 20,
    text: section,
    style: { fontSize: 13, bold: true, color: "#C8D6FF" },
  });

  addText(slide, {
    left: 62,
    top: 40,
    width: 760,
    height: 28,
    text: pageTitle,
    style: { fontSize: 28, bold: true, color: COLORS.white },
  });

  addRect(
    slide,
    { left: 1088, top: 22, width: 128, height: 36 },
    COLORS.accent,
    { borderRadius: "rounded-full" },
  );
  addText(slide, {
    left: 1100,
    top: 29,
    width: 104,
    height: 18,
    text: `视频 ${timeLabel}`,
    style: { fontSize: 14, bold: true, color: COLORS.white, alignment: "center" },
  });

  addFooter(slide, slideNumber, totalSlides);
}

async function buildCoverSlide(presentation, totalSlides) {
  const slide = presentation.slides.add();
  slide.background.fill = "#081A4A";

  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1280, height: 720 },
    fill: "#0A1C4E",
    line: { style: "solid", fill: "#0A1C4E", width: 0 },
  });

  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 440, height: 720 },
    fill: "#0D2668",
    transparency: 18,
    line: { style: "solid", fill: "#0D2668", width: 0 },
  });

  slide.shapes.add({
    geometry: "ellipse",
    position: { left: 874, top: -84, width: 460, height: 460 },
    fill: "#2365D1",
    transparency: 64,
    line: { style: "solid", fill: "#2365D1", width: 0 },
  });

  addRect(
    slide,
    { left: 80, top: 88, width: 156, height: 36 },
    COLORS.accent,
    { borderRadius: "rounded-full" },
  );
  addText(slide, {
    left: 98,
    top: 96,
    width: 120,
    height: 20,
    text: "学习整理版",
    style: { fontSize: 15, bold: true, color: COLORS.white, alignment: "center" },
  });

  addText(slide, {
    left: 80,
    top: 150,
    width: 560,
    height: 150,
    text: "识别嗜酸，精准诊断",
    style: { fontSize: 44, bold: true, color: COLORS.white, lineSpacing: 1.08 },
  });

  addText(slide, {
    left: 80,
    top: 300,
    width: 580,
    height: 80,
    text: "《嗜酸粒细胞增多相关性肺疾病诊疗中国专家共识》2023 解读关键页提炼",
    style: { fontSize: 24, color: "#DDE8FF", lineSpacing: 1.18 },
  });

  addText(slide, {
    left: 80,
    top: 418,
    width: 360,
    height: 62,
    text: "张清玲 教授\n广州医科大学附属第一医院 呼吸科",
    style: { fontSize: 20, color: COLORS.white, lineSpacing: 1.22 },
  });

  addText(slide, {
    left: 80,
    top: 550,
    width: 420,
    height: 46,
    text: "来源：B站视频 BV13k4y1Q7UR\n整理日期：2026-06-28",
    style: { fontSize: 15, color: "#C6D5FF", lineSpacing: 1.24 },
  });

  addRect(
    slide,
    { left: 706, top: 92, width: 486, height: 474 },
    "#14347F",
    { lineFill: "#5D89F5", lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-lg" },
  );

  const coverImage = await loadImage("video_sprites/selected/full/cover-0000s.jpg");
  slide.images.add({
    blob: coverImage,
    contentType: "image/jpeg",
    alt: "讲座封面截图",
    fit: "contain",
    position: { left: 736, top: 122, width: 426, height: 414 },
    geometry: "roundRect",
    borderRadius: "rounded-2xl",
  });

  addRect(
    slide,
    { left: 706, top: 590, width: 486, height: 48 },
    "#0C245D",
    { lineFill: "#0C245D", borderRadius: "rounded-xl" },
  );
  addText(slide, {
    left: 726,
    top: 603,
    width: 446,
    height: 18,
    text: "基于公开视频关键帧提取，并按复盘逻辑重排为正式汇报版式",
    style: { fontSize: 14, color: "#DDE8FF", alignment: "center" },
  });

  addFooter(slide, 1, totalSlides);
}

function buildOverviewSlide(presentation, totalSlides) {
  const slide = presentation.slides.add();
  addChrome(slide, "SOURCE", "视频来源与整理说明", "00:00", 2, totalSlides);

  addRect(
    slide,
    { left: 64, top: 122, width: 534, height: 468 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );
  addRect(
    slide,
    { left: 626, top: 122, width: 590, height: 468 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );

  addText(slide, {
    left: 96,
    top: 154,
    width: 180,
    height: 24,
    text: "来源与方法",
    style: { fontSize: 24, bold: true, color: COLORS.slate900 },
  });
  addBulletList(slide, {
    left: 96,
    top: 204,
    width: 458,
    height: 232,
    fontSize: 20,
    items: [
      "视频来源：B站 BV13k4y1Q7UR，《嗜酸粒细胞增多相关性肺疾病诊疗专家共识解读 张清玲教授》。",
      "发布时间：2024-01-13；全长约 36 分钟。",
      "整理方式：从公开视频关键帧中提取 11 张代表性页面，再按学习复盘逻辑重组。",
      "当前版本保留截图证据页，便于后续继续 OCR、补全文字和院内二次改写。",
    ],
  });

  addRect(
    slide,
    { left: 96, top: 464, width: 466, height: 84 },
    COLORS.accentLight,
    { lineFill: "#FFD9C8", lineWidth: 1, borderRadius: "rounded-2xl" },
  );
  addText(slide, {
    left: 116,
    top: 485,
    width: 426,
    height: 40,
    text: "说明：截图来自讲解视频画面，不等同于原始 PPT 文件；本成品更适合作为学习整理版和二次编辑底稿。",
    style: { fontSize: 17, color: "#92400E", lineSpacing: 1.2 },
  });

  addText(slide, {
    left: 660,
    top: 154,
    width: 180,
    height: 24,
    text: "本版结构",
    style: { fontSize: 24, bold: true, color: COLORS.slate900 },
  });

  const agendaItems = [
    "疾病谱总览",
    "诊断标准与判定门槛",
    "分层评估与诊断流程",
    "病因学与常见相关疾病",
    "ABPA / EGPA 专题页",
    "少见疾病鉴别提醒",
    "11 条推荐意见总览",
  ];

  agendaItems.forEach((item, index) => {
    const top = 206 + index * 42;
    addRect(
      slide,
      { left: 664, top, width: 44, height: 28 },
      index < 3 ? COLORS.blue : COLORS.accent,
      { borderRadius: "rounded-full" },
    );
    addText(slide, {
      left: 676,
      top: top + 7,
      width: 20,
      height: 14,
      text: String(index + 1).padStart(2, "0"),
      style: { fontSize: 12, bold: true, color: COLORS.white, alignment: "center" },
    });
    addText(slide, {
      left: 726,
      top: top + 3,
      width: 420,
      height: 22,
      text: item,
      style: { fontSize: 20, color: COLORS.slate700 },
    });
  });

  addText(slide, {
    left: 664,
    top: 528,
    width: 500,
    height: 22,
    text: "关键时间点：00:59 / 05:59 / 08:59 / 12:59 / 17:59 / 21:59 / 24:59 / 27:59 / 31:59",
    style: { fontSize: 16, color: COLORS.slate500, lineSpacing: 1.15 },
  });
}

async function buildContentSlide(presentation, slideInfo, slideNumber, totalSlides) {
  const slide = presentation.slides.add();
  addChrome(slide, "KEY PAGE", slideInfo.title, slideInfo.mmss, slideNumber, totalSlides);

  addRect(
    slide,
    { left: 64, top: 122, width: 544, height: 470 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );
  addRect(
    slide,
    { left: 632, top: 122, width: 584, height: 470 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );

  addRect(
    slide,
    { left: 90, top: 148, width: 492, height: 338 },
    "#EAF1FB",
    { lineFill: "#CCDAEE", lineWidth: 1, borderRadius: "rounded-2xl" },
  );

  const imageBytes = await loadImage(slideInfo.image);
  slide.images.add({
    blob: imageBytes,
    contentType: "image/jpeg",
    alt: `${slideInfo.id} 页面截图`,
    fit: "contain",
    position: { left: 104, top: 162, width: 464, height: 310 },
    geometry: "roundRect",
    borderRadius: "rounded-xl",
  });

  addRect(
    slide,
    { left: 90, top: 504, width: 492, height: 56 },
    COLORS.sky,
    { lineFill: "#C9DAFD", lineWidth: 1, borderRadius: "rounded-2xl" },
  );
  addText(slide, {
    left: 112,
    top: 518,
    width: 448,
    height: 26,
    text: `原页标题（按截图辨识整理）：${slideInfo.rawTitle}`,
    style: { fontSize: 16, color: COLORS.slate700, lineSpacing: 1.15 },
  });

  addRect(
    slide,
    { left: 664, top: 152, width: 132, height: 30 },
    COLORS.accentLight,
    { lineFill: "#FFD9C8", lineWidth: 1, borderRadius: "rounded-full" },
  );
  addText(slide, {
    left: 678,
    top: 159,
    width: 104,
    height: 16,
    text: "页面主题",
    style: { fontSize: 13, bold: true, color: "#B45309", alignment: "center" },
  });
  addText(slide, {
    left: 664,
    top: 198,
    width: 520,
    height: 96,
    text: slideInfo.summary,
    style: { fontSize: 24, bold: true, color: COLORS.slate900, lineSpacing: 1.18 },
  });

  addText(slide, {
    left: 664,
    top: 310,
    width: 180,
    height: 24,
    text: "提炼重点",
    style: { fontSize: 22, bold: true, color: COLORS.slate900 },
  });
  addBulletList(slide, {
    left: 664,
    top: 346,
    width: 512,
    height: 170,
    fontSize: 20,
    items: slideInfo.bullets,
  });

  addRect(
    slide,
    { left: 664, top: 526, width: 520, height: 42 },
    "#EEF4FF",
    { lineFill: "#D7E5FF", lineWidth: 1, borderRadius: "rounded-xl" },
  );
  addText(slide, {
    left: 682,
    top: 538,
    width: 484,
    height: 16,
    text: `使用建议：${slideInfo.takeaway}`,
    style: { fontSize: 16, color: COLORS.blue, bold: true },
  });
}

async function buildClosingSlide(presentation, totalSlides) {
  const slide = presentation.slides.add();
  addChrome(slide, "WRAP-UP", "复盘建议：把关键页继续变成可讲可用的汇报", "35:59", totalSlides, totalSlides);

  addRect(
    slide,
    { left: 64, top: 122, width: 544, height: 470 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );
  addRect(
    slide,
    { left: 632, top: 122, width: 584, height: 470 },
    COLORS.white,
    { lineFill: COLORS.line, lineWidth: 1, borderRadius: "rounded-3xl", shadow: "shadow-sm" },
  );

  addRect(
    slide,
    { left: 92, top: 150, width: 488, height: 340 },
    "#EAF1FB",
    { lineFill: "#CCDAEE", lineWidth: 1, borderRadius: "rounded-2xl" },
  );

  const closingImage = await loadImage("video_sprites/selected/full/closing_summary-2159s.jpg");
  slide.images.add({
    blob: closingImage,
    contentType: "image/jpeg",
    alt: "视频结束页截图",
    fit: "contain",
    position: { left: 106, top: 164, width: 460, height: 312 },
    geometry: "roundRect",
    borderRadius: "rounded-xl",
  });

  addText(slide, {
    left: 94,
    top: 510,
    width: 484,
    height: 40,
    text: "结束页保留在这里，方便后续继续回看原视频并补充完整文本、讲者旁白和指南条目。",
    style: { fontSize: 18, color: COLORS.slate700, lineSpacing: 1.18 },
  });

  addText(slide, {
    left: 664,
    top: 158,
    width: 420,
    height: 34,
    text: "建议的二次使用方式",
    style: { fontSize: 28, bold: true, color: COLORS.slate900 },
  });
  addBulletList(slide, {
    left: 664,
    top: 222,
    width: 500,
    height: 206,
    fontSize: 21,
    items: [
      "把 31:59 的“11 条推荐意见汇总页”扩成正式汇报目录，用作主线结构。",
      "把 12:59 的诊断流程页单独放大，作为病例讨论中的流程底图。",
      "把 ABPA、EGPA 和 KD/EMS/EF 三页拆成专题补充材料，形成鉴别诊断附录。",
      "若需要发布到院内教学，可继续补做全文 OCR、文献出处和病例示意图。",
    ],
  });

  addRect(
    slide,
    { left: 664, top: 468, width: 488, height: 86 },
    COLORS.accentLight,
    { lineFill: "#FFD9C8", lineWidth: 1, borderRadius: "rounded-2xl" },
  );
  addText(slide, {
    left: 688,
    top: 489,
    width: 442,
    height: 42,
    text: "当前成品定位：正式学习整理版 PPT。\n优点是可直接汇报，缺点是文字仍以截图证据页为主，尚未完全替换成全文可编辑内容。",
    style: { fontSize: 18, color: "#9A3412", lineSpacing: 1.22 },
  });
}

async function exportDeck() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });

  const totalSlides = 12;
  await buildCoverSlide(presentation, totalSlides);
  buildOverviewSlide(presentation, totalSlides);

  for (const [index, slideInfo] of SLIDES.entries()) {
    await buildContentSlide(presentation, slideInfo, index + 3, totalSlides);
  }

  await buildClosingSlide(presentation, totalSlides);

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await writeBlob(path.join(OUTPUT_DIR, `${stem}.png`), png);
  }

  const montage = await presentation.export({
    format: "webp",
    montage: true,
    scale: 1,
  });
  await writeBlob(path.join(OUTPUT_DIR, "deck-montage.webp"), montage);

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(PPTX_PATH);

  const manifest = {
    generatedAt: "2026-06-28",
    slideCount: totalSlides,
    pptx: PPTX_PATH,
    previewDir: OUTPUT_DIR,
  };
  await fs.writeFile(path.join(OUTPUT_DIR, "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");

  console.log(JSON.stringify(manifest, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  exportDeck().catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exitCode = 1;
  });
}
