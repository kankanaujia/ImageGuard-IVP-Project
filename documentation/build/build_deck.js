// Build the ImageGuard presentation (structured deck: theme, layouts, sections).
//   cd documentation\build ; node build_deck.js   ->  documentation/ImageGuard_Presentation.pptx
// Numbers come from evaluation/results/*/metrics.json, like the report.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "documentation", "ImageGuard_Presentation.pptx");
const RES = path.join(ROOT, "evaluation", "results");
const FIG = path.join(__dirname, "figures");
const SHOT = path.join(__dirname, "screenshots");
const IMG_ID = "90be9285-7978-4118-be69-36f30cb9d1ef";   // gulls (CASIA copy-move) demo investigation
const VID_ID = "7cb63a45-6b04-49a3-a923-07b74c9ecd59";   // synthetic pan with inserted footage
const ART = (id, f) => path.join(ROOT, "backend", "outputs", id, f);

const casia = JSON.parse(fs.readFileSync(path.join(RES, "casia", "metrics.json"), "utf8"));
const jq = JSON.parse(fs.readFileSync(path.join(RES, "casia", "jpeg_quality.json"), "utf8"));
const video = JSON.parse(fs.readFileSync(path.join(RES, "video", "metrics.json"), "utf8"));
const pct = (x, d = 0) => `${(100 * x).toFixed(d)}%`;

// ------------------------------------------------------------------ theme
const THEME = {
  name: "ImageGuard Evidence",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "141A24", lt1: "FFFFFF", dk2: "16233A", lt2: "EEF1F5",
    accent1: "F2A541",  // amber: evidence tags, highlights
    accent2: "2E86AB",  // steel blue
    accent3: "E4572E",  // signal red (tampered / false alarms)
    accent4: "3BB273",  // green (authentic / detected)
    accent5: "7768AE",  // violet
    accent6: "8D99AE",  // slate
    hlink: "2E86AB", folHlink: "7768AE",
  },
};
const H = THEME.colors; // hex values, only for hex-only chart options

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "ImageGuard: Explainable Forensic Screening of Digital Images and Videos";
pres.author = "Elisha Chophla, Kanishka Kanaujia";
pres.subject = "Image and Video Processing project, end-semester evaluation";
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
const W = 13.333, M = 0.6;
const footer = (dark) => [
  { text: { text: "ImageGuard  ·  Image and Video Processing Project", options: { x: M, y: 7.0, w: 7, h: 0.3, fontSize: 10, color: dark ? C.accent6 : C.accent6, margin: 0 } } },
];
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.7, w: 7.2, h: 1.6, fontSize: 48, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: M, y: 3.45, w: 7.0, h: 1.0, fontSize: 20, color: C.accent1, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 0.9, fontSize: 32, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
    ...footer(false),
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "SECTION_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 0.9, fontSize: 32, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    ...footer(true),
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});

// ------------------------------------------------------------------ helpers
let objId = 0;
const name = (n) => `${n}-${++objId}`;
function tag(slide, x, y, label, opts = {}) {
  // Motif: amber evidence-tag circle with a number or short label.
  const d = opts.d || 0.5;
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: opts.fill || C.accent1 }, line: { color: opts.fill || C.accent1 }, objectName: name("tag") });
  slide.addText(String(label), { x, y, w: d, h: d, fontSize: opts.size || 16, bold: true, color: opts.color || C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: name("tag-label") });
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2 }, objectName: name("card") });
}
function text(slide, str, o) {
  slide.addText(str, { margin: 0, isTextBox: true, valign: "top", color: C.text1, fontSize: 16, objectName: name("text"), ...o });
}
function stat(slide, x, y, w, value, label, colour) {
  text(slide, value, { x, y, w, h: 0.95, fontSize: 48, bold: true, color: colour || C.accent2, fontFace: THEME.headFontFace, valign: "bottom" });
  text(slide, label, { x, y: y + 1.0, w, h: 0.75, fontSize: 14, color: C.text1 });
}
function picture(slide, file, x, y, w, h, alt, opts = {}) {
  slide.addImage({ path: file, x, y, w, h, altText: alt, objectName: name("picture"), ...opts });
}
function imgSize(file) { // read PNG/JPEG pixel size without extra dependencies
  const b = fs.readFileSync(file);
  if (b[0] === 0x89) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  let i = 2;
  while (i < b.length) {
    const marker = b[i + 1], len = b.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xc3) return { w: b.readUInt16BE(i + 7), h: b.readUInt16BE(i + 5) };
    i += 2 + len;
  }
  throw new Error("size? " + file);
}
function fit(file, maxW, maxH) { const s = imgSize(file); const r = Math.min(maxW / s.w, maxH / s.h); return { w: s.w * r, h: s.h * r }; }
const content = (section) => pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt", legendFontFace: "+mn-lt" };

// ================================================================== 1. Title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Introduction" });
  s.addText("ImageGuard", { placeholder: "title" });
  s.addText("Explainable forensic screening of digital images and videos", { placeholder: "subtitle" });
  text(s, [
    { text: "Elisha Chophla (2025010033)", options: { breakLine: true } },
    { text: "Kanishka Kanaujia (2025010053)" },
  ], { x: M, y: 4.7, w: 6.5, h: 0.8, fontSize: 16, color: C.background1 });
  const f = path.join(SHOT, "image_analysis.png"), sz = fit(f, 5.0, 4.6);
  picture(s, f, W - M - sz.w, 1.45, sz.w, sz.h, "ImageGuard image forensics page", { shadow: { type: "outer", color: "000000", opacity: 0.45, blur: 12, offset: 4, angle: 90 } });
  s.addNotes("Introduce ImageGuard: a local web app that examines images and videos with classical, explainable image and video processing techniques and reports observations with their limits, never a fake/real verdict.");
}

// ================================================================== 2. Problem
{
  const s = content("Introduction");
  s.addText("Manipulated media is easy to make and hard to question", { placeholder: "title" });
  const items = [
    ["Images", "Regions are copied to hide or duplicate objects, or pasted in from other photos (copy-move and splicing)."],
    ["Videos", "Segments are cut, frozen or inserted, changing what appears to have happened."],
    ["Tools", "Online checkers upload private evidence and return a single score nobody can explain or challenge."],
  ];
  items.forEach(([h, b], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.6, 3.8, 3.4);
    tag(s, x + 0.35, 1.9, i + 1);
    text(s, h, { x: x + 0.35, y: 2.6, w: 3.1, h: 0.5, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    text(s, b, { x: x + 0.35, y: 3.15, w: 3.1, h: 1.7, fontSize: 16 });
  });
  card(s, M, 5.35, W - 2 * M, 1.2, C.text2);
  text(s, [
    { text: "Goal  ", options: { bold: true, color: C.accent1 } },
    { text: "Give a non-specialist a private, local tool that shows what each forensic technique observed and where, states its limits, and keeps the original evidence verifiably unchanged.", options: { color: C.background1 } },
  ], { x: M + 0.35, y: 5.45, w: W - 2 * M - 0.7, h: 1.0, fontSize: 17, valign: "middle" });
  s.addNotes("Problem and goal. Emphasise privacy (local processing), explainability, and evidence integrity.");
}

// ================================================================== 3. Objectives
{
  const s = content("Introduction");
  s.addText("Objectives", { placeholder: "title" });
  const obj = [
    ["Preserve evidence", "Store every upload unchanged under a random name and fingerprint it with SHA-256."],
    ["Explain images", "Error level analysis, ORB copy-move detection, noise residuals, histograms and EXIF."],
    ["Explain videos", "Repeated frames, SSIM continuity, scene cuts and full-video optical flow."],
    ["Show, don't judge", "Visualisations, interpretation notes and limitations for every check, plus a PDF report."],
    ["Measure honestly", "Evaluate on CASIA v2.0 and a synthetic video benchmark, reporting failure modes."],
  ];
  obj.forEach(([h, b], i) => {
    const y = 1.55 + i * 1.0;
    tag(s, M, y + 0.05, i + 1);
    text(s, h, { x: M + 0.8, y, w: 3.3, h: 0.6, fontSize: 20, bold: true, color: C.text2, valign: "middle", fontFace: THEME.headFontFace });
    text(s, b, { x: M + 4.2, y, w: 7.9, h: 0.6, fontSize: 17, valign: "middle" });
  });
}

// ================================================================== 4. Architecture
pres.addSection({ title: "System" });
{
  const s = content("System");
  s.addText("A three-tier application that runs entirely on one laptop", { placeholder: "title" });
  const f = path.join(FIG, "fig_architecture.png"), sz = fit(f, 8.2, 5.3);
  picture(s, f, M, 1.45, sz.w, sz.h, "Layered architecture: Next.js front end, FastAPI back end, processing layer and storage");
  const notes = [
    ["Next.js + React", "Five pages: overview, intake, image and video forensics, reports"],
    ["FastAPI", "Validates uploads, hashes evidence, runs checks, serves results"],
    ["OpenCV · scikit-image", "Each check isolated: one failure never stops the others"],
    ["SQLite + folders", "Originals, visualisations and PDF reports kept separately"],
  ];
  notes.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.3;
    text(s, h, { x: 9.15, y, w: 3.6, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
    text(s, b, { x: 9.15, y: y + 0.42, w: 3.6, h: 0.8, fontSize: 14 });
  });
}

// ================================================================== 5. Evidence workflow
{
  const s = content("System");
  s.addText("Every upload follows the same evidence-safe workflow", { placeholder: "title" });
  const steps = [["Upload", "JPG · PNG · TIFF · BMP · WebP\nMP4 · AVI · MOV · MKV"], ["Validate", "Extension, size ≤ 100 MB, real decodable content"], ["Store", "Original kept byte-for-byte under a random UUID name"],
                 ["Fingerprint", "SHA-256 recorded; re-verify at any time"], ["Analyse", "Independent checks, errors recorded per check"], ["Report", "Interactive views and a PDF report"]];
  const w = 1.85, gap = 0.17;
  steps.forEach(([h, b], i) => {
    const x = M + i * (w + gap);
    card(s, x, 1.9, w, 3.0, i === 3 ? C.text2 : C.background2);
    tag(s, x + w / 2 - 0.25, 2.15, i + 1);
    text(s, h, { x: x + 0.15, y: 2.85, w: w - 0.3, h: 0.5, fontSize: 18, bold: true, align: "center", color: i === 3 ? C.accent1 : C.text2 });
    text(s, b, { x: x + 0.15, y: 3.4, w: w - 0.3, h: 1.4, fontSize: 13, align: "center", color: i === 3 ? C.background1 : C.text1 });
    if (i < steps.length - 1) s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: x + w + 0.02, y: 3.3, w: 0.13, h: 0.22, rotate: 90, fill: { color: C.accent6 }, line: { color: C.accent6 }, objectName: name("arrow") });
  });
  text(s, "If anything fails before the record is saved, the stored file and its outputs are deleted, so no orphaned evidence is left behind.", { x: M, y: 5.4, w: W - 2 * M, h: 0.6, fontSize: 16, color: C.accent6, italic: true });
}

// ================================================================== 6. Image techniques
pres.addSection({ title: "Techniques" });
{
  const s = content("Techniques");
  s.addText("Image forensics: five complementary views of one photo", { placeholder: "title" });
  const pics = [[ART(IMG_ID, "ela.png"), "Error level analysis"], [ART(IMG_ID, "orb.png"), "ORB copy-move matches"]];
  const orig = path.join(process.env.USERPROFILE, "Downloads", "CASIA2", "Tp", "Tp_S_NNN_S_N_ani10172_ani10172_12451.jpg");
  const left = fs.existsSync(orig) ? [[orig, "Evidence (CASIA v2.0 copy-move)"], ...pics.slice(0, 1)] : pics.slice(0, 1);
  left.forEach(([f, cap], i) => {
    const sz = fit(f, 2.9, 2.3);
    picture(s, f, M + i * 3.05, 1.5, sz.w, sz.h, cap);
    text(s, cap, { x: M + i * 3.05, y: 1.55 + sz.h, w: 2.9, h: 0.35, fontSize: 12, color: C.accent6 });
  });
  const orb = ART(IMG_ID, "orb.png"), osz = fit(orb, 5.95, 2.2);
  picture(s, orb, M, 4.35, osz.w, osz.h, "ORB copy-move matches linking the original and duplicated gull");
  text(s, "ORB matches link the duplicated gull to its source", { x: M, y: 4.4 + osz.h, w: 6, h: 0.35, fontSize: 12, color: C.accent6 });
  const rows = [
    ["ELA", "Re-save at JPEG Q90 and amplify |original − copy|; regions with a different compression history stand out."],
    ["Copy-move", "2,500 ORB keypoints self-matched (ratio 0.78, ≥ 24 px apart), confirmed by a RANSAC affine fit."],
    ["Noise", "Residual |I − Gaussian(I)| and its variance over an 8 × 8 grid."],
    ["Histogram", "RGB distributions reveal clipping and contrast edits."],
    ["Metadata", "EXIF camera, software and dates."],
  ];
  rows.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.05;
    tag(s, 7.0, y, i + 1, { d: 0.42, size: 13 });
    text(s, h, { x: 7.6, y: y - 0.02, w: 5.1, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
    text(s, b, { x: 7.6, y: y + 0.38, w: 5.1, h: 0.62, fontSize: 13 });
  });
}

// ================================================================== 7. Video techniques
{
  const s = content("Techniques");
  s.addText("Video forensics: compare neighbouring frames", { placeholder: "title" });
  const fr = ART(VID_ID, "frames/frame_00000050.jpg"), fl = ART(VID_ID, "frames/flow_00000050.jpg");
  const sz = fit(fr, 2.9, 1.9);
  picture(s, fr, M, 1.55, sz.w, sz.h, "Sampled frame at the inserted segment");
  picture(s, fl, M + 3.05, 1.55, sz.w, sz.h, "Optical flow into that frame: colour is direction, brightness is speed");
  text(s, "Frame at 5 s (inserted footage)", { x: M, y: 1.6 + sz.h, w: 2.9, h: 0.35, fontSize: 12, color: C.accent6 });
  text(s, "Optical flow into that frame", { x: M + 3.05, y: 1.6 + sz.h, w: 2.9, h: 0.35, fontSize: 12, color: C.accent6 });
  const rows = [
    ["Sampling", "1 frame per second, at most 180 frames, keeps analysis fast."],
    ["Repeated frames", "Perceptual hash (pHash) of neighbours; distance ≤ 4 means near-identical."],
    ["Continuity", "SSIM between neighbouring samples; sharp dips mark cuts or fast motion."],
    ["Scene cuts", "8 × 8 × 8 colour histogram, Bhattacharyya distance ≥ 0.55."],
    ["Motion", "Farnebäck dense flow for every pair; spikes above median + 3.5 × MAD are flagged."],
  ];
  rows.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.05;
    tag(s, 7.0, y, i + 1, { d: 0.42, size: 13 });
    text(s, h, { x: 7.6, y: y - 0.02, w: 5.1, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
    text(s, b, { x: 7.6, y: y + 0.38, w: 5.1, h: 0.62, fontSize: 13 });
  });
  card(s, M, 4.25, 5.95, 2.35, C.background2);
  text(s, "Why median and MAD?", { x: M + 0.3, y: 4.45, w: 5.4, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
  text(s, "A robust z-score, (motion − median) / MAD, keeps one large spike from hiding another, so every sudden jump in camera motion is reported, not just the biggest.", { x: M + 0.3, y: 4.9, w: 5.4, h: 1.5, fontSize: 15 });
}

// ================================================================== 8-9. Demo screenshots
pres.addSection({ title: "Demo" });
{
  const s = content("Demo");
  s.addText("Image forensics page", { placeholder: "title" });
  const f = path.join(SHOT, "image_analysis.png"), sz = fit(f, 8.6, 5.4);
  picture(s, f, M, 1.4, sz.w, sz.h, "Image forensics page: summary metrics and side-by-side ELA comparison");
  const pts = [["Summary metrics", "Candidate indicators, copy-move matches, ELA peak, noise ratio, EXIF count"], ["Visual comparison", "Original beside ELA, noise residual or copy-move matches"],
               ["Method cards", "What each check does, how to read it, and its caveat"]];
  pts.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.55;
    tag(s, 9.55, y, i + 1, { d: 0.42, size: 13 });
    text(s, h, { x: 10.1, y: y - 0.02, w: 2.65, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    text(s, b, { x: 10.1, y: y + 0.4, w: 2.65, h: 1.05, fontSize: 13 });
  });
}
{
  const s = content("Demo");
  s.addText("Video forensics page", { placeholder: "title" });
  const a = path.join(SHOT, "video_analysis.png"), b = path.join(SHOT, "video_frames.png");
  const sa = fit(a, 6.9, 5.3), sb = fit(b, 5.0, 5.3);
  picture(s, a, M, 1.4, sa.w, sa.h, "Video page: summary metrics and synchronised SSIM and motion timelines");
  picture(s, b, W - M - sb.w, 1.4, sb.w, sb.h, "Video page: frame filmstrip, previous/selected/flow comparison and flagged moments");
  text(s, "Synchronised SSIM and motion timelines with scene cuts and motion spikes marked", { x: M, y: 1.45 + sa.h, w: 6.9, h: 0.5, fontSize: 12, color: C.accent6 });
  text(s, "Filmstrip with tags; previous, selected and flow images; flagged moments", { x: W - M - sb.w, y: 1.45 + sb.h, w: sb.w, h: 0.5, fontSize: 12, color: C.accent6 });
}

// ================================================================== 10. Evaluation setup
pres.addSection({ title: "Results" });
{
  const s = content("Results");
  s.addText("How we tested it", { placeholder: "title" });
  const stats = [[casia.n.toLocaleString("en-US"), "CASIA v2.0 images\n7,491 authentic · 5,123 tampered"], ["60", "synthetic video clips with known edits (insertion, freeze, deletion, clean)"],
                 [`${casia.seconds.mean.toFixed(2)} s`, "average analysis time per image on a laptop CPU"], ["10 / 10", "automated tests passing, plus 15 system and UI test cases"]];
  stats.forEach(([v, l], i) => stat(s, M + i * 3.1, 1.9, 2.8, v, l, [C.accent2, C.accent5, C.accent4, C.accent1][i]));
  card(s, M, 4.6, W - 2 * M, 1.75);
  text(s, [
    { text: "Real pipeline, measured end to end. ", options: { bold: true, color: C.text2 } },
    { text: "The evaluation scripts call the same analysis functions as the app on every image (10 parallel workers) and compute ROC curves, AUC, precision, recall and false-positive rates. Video edits count as detected when a flag lands within one second of the true edit." },
  ], { x: M + 0.35, y: 4.8, w: W - 2 * M - 0.7, h: 1.4, fontSize: 16, valign: "middle" });
}

// ================================================================== 11. CASIA AUC chart
{
  const s = content("Results");
  s.addText("Which image scores separate authentic from tampered?", { placeholder: "title" });
  const labels = ["ELA peak", "ORB raw matches", "ORB consistent", "Noise std", "Noise tile ratio"];
  const keys = ["ELA peak difference", "ORB raw matches", "ORB consistent matches", "Noise residual std", "Noise tile variance ratio"];
  s.addChart(pres.charts.BAR, [{ name: "AUC", labels, values: keys.map((k) => +casia.scores[k].auc.toFixed(3)) }], {
    x: M, y: 1.4, w: 7.4, h: 5.2, barDir: "bar", catAxisOrientation: "maxMin",
    chartColors: [H.accent2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelFontSize: 14, dataLabelColor: H.dk1,
    valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.25, valAxisLabelFontSize: 12, catAxisLabelFontSize: 14,
    valGridLine: { color: "D9DEE5", size: 0.75 }, catGridLine: { style: "none" }, valAxisLabelColor: H.accent6, catAxisLabelColor: H.dk1,
    showTitle: true, title: "Area under the ROC curve (0.5 = chance, 1.0 = perfect)", titleFontSize: 14, titleColor: H.dk1, showLegend: false, ...chartText,
    objectName: "casia-auc-chart",
  });
  const cmv = casia.by_type["copy-move"], a = casia.app_threshold;
  const pts = [
    ["ELA scores highest", `AUC ${casia.scores["ELA peak difference"].auc.toFixed(2)}, but see the next slide for why.`],
    ["Copy-move works for copy-move", `AUC ${cmv.orb_auc.toFixed(2)} on copy-move forgeries, chance (${casia.by_type.splicing.orb_auc.toFixed(2)}) on splicing. Flags ${pct(cmv.recall)} of them, and ${pct(a.fpr, 1)} of authentic images.`],
    ["Whole-image noise numbers fail", "AUC below 0.5: scene content dominates; the residual map must be read locally."],
  ];
  pts.forEach(([h, b], i) => {
    const y = 1.55 + i * 1.75;
    tag(s, 8.45, y, i + 1, { d: 0.42, size: 13 });
    text(s, h, { x: 9.0, y: y - 0.02, w: 3.75, h: 0.45, fontSize: 17, bold: true, color: C.text2 });
    text(s, b, { x: 9.0, y: y + 0.45, w: 3.75, h: 1.2, fontSize: 14 });
  });
}

// ================================================================== 12. Key finding: ELA and save settings
{
  const s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "Results" });
  s.addText("Key finding: ELA measured how files were saved", { placeholder: "title" });
  const t = jq.tampered.most_common_quality[0], a1 = jq.authentic.most_common_quality[0], a2 = jq.authentic.most_common_quality[1];
  const stats = [[pct(t.share), `of tampered JPEGs share one save setting (quality ≈ ${t.quality})`],
                 [`≈ ${a1.quality} / ${a2.quality}`, `quality of most authentic JPEGs (${pct(a1.share)} and ${pct(a2.share)})`],
                 [`${jq.authentic.ela_peak_median} → ${jq.tampered.ela_peak_median}`, "median ELA peak, authentic → tampered"]];
  stats.forEach(([v, l], i) => {
    text(s, v, { x: M + i * 4.1, y: 1.7, w: 3.8, h: 1.1, fontSize: 54, bold: true, color: C.accent1, fontFace: THEME.headFontFace, valign: "bottom" });
    text(s, l, { x: M + i * 4.1, y: 2.9, w: 3.6, h: 0.9, fontSize: 16, color: C.background1 });
  });
  card(s, M, 4.3, W - 2 * M, 2.2, "1F3150");
  text(s, [
    { text: "What it means", options: { bold: true, color: C.accent1, breakLine: true } },
    { text: `ELA keeps its AUC of ${casia.jpeg_only_auc["ELA peak difference"].toFixed(2)} on JPEGs alone, so file format is not the cause. A global ELA peak largely reflects how a file was last compressed, and CASIA's classes were saved differently. ELA is good evidence of re-saving, not proof of where (or whether) content was edited, so ImageGuard shows it as a map to inspect, never as a verdict.`, options: { color: C.background1 } },
  ], { x: M + 0.35, y: 4.45, w: W - 2 * M - 0.7, h: 1.95, fontSize: 17 });
  s.addNotes("This is the most important result: measure quantization tables before trusting compression-based scores on CASIA v2.0.");
}

// ================================================================== 13. Video benchmark
{
  const s = content("Results");
  s.addText("Video benchmark: edits found, and the cost in false alarms", { placeholder: "title" });
  const pk = video.per_kind, fa = video.false_alarms;
  s.addChart(pres.charts.BAR, [{ name: "Detected (of 15)", labels: ["Inserted footage\n(scene cut)", "Frozen frames\n(repeat)", "Deleted section\n(motion spike)"],
    values: [pk.insertion.detected_by_expected_check, pk.freeze.detected_by_expected_check, pk.deletion.detected_by_expected_check] }], {
    x: M, y: 1.4, w: 5.9, h: 4.6, barDir: "col", chartColors: [H.accent4], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 14, dataLabelColor: H.dk1,
    valAxisMinVal: 0, valAxisMaxVal: 18, valAxisMajorUnit: 5, valAxisLabelFontSize: 12, catAxisLabelFontSize: 13,
    valGridLine: { color: "D9DEE5", size: 0.75 }, catGridLine: { style: "none" }, valAxisLabelColor: H.accent6, catAxisLabelColor: H.dk1,
    showTitle: true, title: "Edits detected by the intended check (out of 15)", titleFontSize: 14, titleColor: H.dk1, showLegend: false, ...chartText, objectName: "video-detected-chart",
  });
  s.addChart(pres.charts.BAR, [{ name: "False flags per minute", labels: ["Scene cut", "Motion spike", "Repeated frame"],
    values: [+fa.scene.flags_per_minute.toFixed(1), +fa.motion.flags_per_minute.toFixed(1), +fa.repeat.flags_per_minute.toFixed(1)] }], {
    x: 6.85, y: 1.4, w: 5.9, h: 4.6, barDir: "col", chartColors: [H.accent3], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelFontSize: 14, dataLabelColor: H.dk1,
    valAxisMinVal: 0, valAxisLabelFontSize: 12, catAxisLabelFontSize: 13,
    valGridLine: { color: "D9DEE5", size: 0.75 }, catGridLine: { style: "none" }, valAxisLabelColor: H.accent6, catAxisLabelColor: H.dk1,
    showTitle: true, title: "False flags per minute on 15 unedited clips", titleFontSize: 14, titleColor: H.dk1, showLegend: false, ...chartText, objectName: "video-falsealarm-chart",
  });
  text(s, "Scene-cut and motion-spike checks are reliable. The repeat check catches every freeze but also fires on slow camera pans, because pHash is built to ignore small shifts, so its flags are not yet trustworthy on moving footage.",
    { x: M, y: 6.15, w: W - 2 * M, h: 0.75, fontSize: 15 });
}

// ================================================================== 14. Testing
{
  const s = content("Results");
  s.addText("Testing found and fixed real defects", { placeholder: "title" });
  [["10", "automated unit tests (pytest), all passing"], ["15", "system and UI test cases, all passing"], ["4", "defects found by testing and fixed"]]
    .forEach(([v, l], i) => stat(s, M + i * 2.4, 1.7, 2.2, v, l, [C.accent4, C.accent2, C.accent3][i]));
  const fixes = [
    ["Copy-move never ran", "OpenCV needed NumPy arrays, not lists; caught by a regression test."],
    ["Missing dependency", "Matplotlib was not in the requirements; charts could not load."],
    ["Wrong test value", "A test expected an incorrect SHA-256; the code itself was right."],
    ["Front-end build failed", "A page needed a React Suspense boundary to pre-render."],
  ];
  fixes.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.3;
    card(s, 7.95, y, 4.8, 1.12);
    text(s, h, { x: 8.2, y: y + 0.12, w: 4.4, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    text(s, b, { x: 8.2, y: y + 0.52, w: 4.4, h: 0.55, fontSize: 13 });
  });
  text(s, "Each algorithm was tested on inputs with a known answer, such as an image with a pasted patch or frames shifted by an exact number of pixels.", { x: M, y: 4.35, w: 6.9, h: 1.0, fontSize: 15, color: C.accent6, italic: true });
}

// ================================================================== 15. Conclusions
pres.addSection({ title: "Conclusion" });
{
  const s = content("Conclusion");
  s.addText("Conclusions and future work", { placeholder: "title" });
  card(s, M, 1.45, 5.9, 5.1);
  text(s, "What we showed", { x: M + 0.35, y: 1.65, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.accent2, fontFace: THEME.headFontFace });
  text(s, [
    { text: "Classical techniques make a practical, private and explainable screening tool on an ordinary laptop", options: { bullet: true, breakLine: true } },
    { text: "Evidence is preserved and its integrity is verifiable at any time", options: { bullet: true, breakLine: true } },
    { text: "Scene-cut and motion-spike checks reliably locate inserted and deleted video segments", options: { bullet: true, breakLine: true } },
    { text: "Honest evaluation exposed misleading scores: ELA on CASIA, pHash on panning video", options: { bullet: true } },
  ], { x: M + 0.35, y: 2.25, w: 5.2, h: 4.1, fontSize: 16, paraSpaceAfter: 10 });
  card(s, 6.85, 1.45, 5.9, 5.1, C.text2);
  text(s, "Next steps", { x: 7.2, y: 1.65, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  text(s, [
    { text: "Local, block-wise ELA and JPEG-ghost maps instead of a global peak", options: { bullet: true, breakLine: true } },
    { text: "Motion-aware repeat detection: a repeat only when optical flow is near zero", options: { bullet: true, breakLine: true } },
    { text: "Splicing heat maps combining compression and noise cues", options: { bullet: true, breakLine: true } },
    { text: "Background jobs with real progress for long videos", options: { bullet: true, breakLine: true } },
    { text: "Evaluate on Columbia, CoMoFoD and real tampered videos", options: { bullet: true } },
  ], { x: 7.2, y: 2.25, w: 5.2, h: 4.1, fontSize: 16, paraSpaceAfter: 10, color: C.background1 });
}

// ================================================================== 16. Thank you
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Conclusion" });
  // Closing slide: only a large, centred "Thank you" (the video screenshot already appears on slide 9).
  text(s, "Thank you", { x: 0, y: 0, w: W, h: 7.5, fontSize: 80, bold: true, color: C.background1, fontFace: THEME.headFontFace, align: "center", valign: "middle" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("Wrote " + OUT);
})();
