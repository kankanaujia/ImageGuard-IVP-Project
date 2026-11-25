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
// Demo outputs copied from two investigations into figures/demo so the deck rebuilds from the repository alone.
const DEMO = (f) => path.join(__dirname, "figures", "demo", f);

const casia = JSON.parse(fs.readFileSync(path.join(RES, "casia", "metrics.json"), "utf8"));
const jq = JSON.parse(fs.readFileSync(path.join(RES, "casia", "jpeg_quality.json"), "utf8"));
const video = JSON.parse(fs.readFileSync(path.join(RES, "video", "metrics.json"), "utf8"));
const tuning = JSON.parse(fs.readFileSync(path.join(RES, "casia", "copy_move_tuning.json"), "utf8"));
const loc = JSON.parse(fs.readFileSync(path.join(RES, "casia", "localization.json"), "utf8"));
const BEFORE = { repeatPerMinute: 25.2 };   // first version (commit cd4f057), same benchmark
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
const TESTS = { total: 35, api: 21 };   // pytest: tests/ (35 passed; 21 in test_api.py and test_auth.py)
const sideList = (s, rows, x, y0, step, w = 5.1) => rows.forEach(([h, b], i) => {
  const y = y0 + i * step;
  tag(s, x, y, i + 1, { d: 0.42, size: 13 });
  text(s, h, { x: x + 0.6, y: y - 0.02, w, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  text(s, b, { x: x + 0.6, y: y + 0.38, w, h: step - 0.42, fontSize: 13 });
});

// ================================================================== 1. Title slide
pres.addSection({ title: "1. Title" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "1. Title" });
  s.addText("ImageGuard", { placeholder: "title" });
  s.addText("Explainable forensic screening of digital images and videos", { placeholder: "subtitle" });
  text(s, [
    { text: "Elisha Chophla (2025010033)", options: { breakLine: true } },
    { text: "Kanishka Kanaujia (2025010053)", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 8 } },
    { text: "Class: MCA", options: { breakLine: true, color: C.accent6 } },
    { text: "Subject: Image and Video Processing", options: { color: C.accent6 } },
  ], { x: M, y: 4.6, w: 6.5, h: 1.9, fontSize: 16, color: C.background1 });
  const f = path.join(SHOT, "image_analysis.png"), sz = fit(f, 5.0, 4.6);
  picture(s, f, W - M - sz.w, 1.45, sz.w, sz.h, "ImageGuard image forensics page", { shadow: { type: "outer", color: "000000", opacity: 0.45, blur: 12, offset: 4, angle: 90 } });
  s.addNotes("Introduce ImageGuard: a local web app that examines images and videos with classical, explainable image and video processing techniques and reports observations with their limits, never a fake/real verdict.");
}

// ================================================================== 2. Problem statement
pres.addSection({ title: "2. Problem Statement" });
{
  const s = content("2. Problem Statement");
  s.addText("Problem: edited photos and videos are easy to make, hard to question", { placeholder: "title" });
  const items = [
    ["Images", "Regions are copied to hide or duplicate objects, or pasted in from other photos (copy-move and splicing)."],
    ["Videos", "Segments are cut, frozen or inserted, changing what appears to have happened."],
    ["Tools", "Online checkers upload private evidence and return a single score nobody can explain or challenge."],
  ];
  items.forEach(([h, b], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.5, 3.8, 3.3);
    tag(s, x + 0.35, 1.8, i + 1);
    text(s, h, { x: x + 0.35, y: 2.5, w: 3.1, h: 0.5, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    text(s, b, { x: x + 0.35, y: 3.05, w: 3.1, h: 1.7, fontSize: 16 });
  });
  card(s, M, 5.1, W - 2 * M, 1.6, C.text2);
  text(s, [
    { text: "Why it matters  ", options: { bold: true, color: C.accent1 } },
    { text: "Edited media spreads misinformation and is submitted as evidence in insurance claims, complaints and court cases. Investigators need a quick, private first check that shows what was found and where, so a human can decide.", options: { color: C.background1 } },
  ], { x: M + 0.35, y: 5.2, w: W - 2 * M - 0.7, h: 1.4, fontSize: 17, valign: "middle" });
  s.addNotes("What problem we solve and why it is important: privacy (local processing), explainability, evidence integrity.");
}

// ================================================================== 3. Objectives
pres.addSection({ title: "3. Objectives" });
{
  const s = content("3. Objectives");
  s.addText("Objectives", { placeholder: "title" });
  const obj = [
    ["Preserve evidence", "Store every upload unchanged under a random name and fingerprint it with SHA-256."],
    ["Explain images", "ELA heat map, ORB copy-move detection, JPEG ghosts for splicing, compression history and EXIF."],
    ["Explain videos", "Motion-confirmed repeated frames, SSIM continuity, scene cuts and full-video optical flow."],
    ["Show, don't judge", "Visualisations, interpretation notes and limitations for every check, plus a PDF report."],
    ["Keep cases private", "Each analyst signs in and sees only the investigations they ran."],
    ["Measure honestly", "Evaluate on CASIA v2.0 and a synthetic video benchmark, reporting failure modes."],
  ];
  obj.forEach(([h, b], i) => {
    const y = 1.45 + i * 0.88;
    tag(s, M, y + 0.05, i + 1);
    text(s, h, { x: M + 0.8, y, w: 3.3, h: 0.6, fontSize: 20, bold: true, color: C.text2, valign: "middle", fontFace: THEME.headFontFace });
    text(s, b, { x: M + 4.2, y, w: 7.9, h: 0.6, fontSize: 17, valign: "middle" });
  });
}

// ================================================================== 4. Methodology: block diagram + technologies
pres.addSection({ title: "4. Methodology" });
{
  const s = content("4. Methodology");
  s.addText("Methodology: block diagram and technologies", { placeholder: "title" });
  const f = path.join(FIG, "fig_architecture.png"), sz = fit(f, 8.2, 5.3);
  picture(s, f, M, 1.45, sz.w, sz.h, "Block diagram: Next.js front end, FastAPI back end, processing layer and storage");
  const notes = [
    ["Front end", "Next.js 15, React 19, TypeScript, Recharts"],
    ["Back end", "FastAPI, Uvicorn, SQLAlchemy, SQLite"],
    ["Image & video processing", "OpenCV, NumPy, scikit-image, Pillow, ImageHash"],
    ["Reports & evaluation", "ReportLab PDFs; Matplotlib, pytest"],
  ];
  notes.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.3;
    text(s, h, { x: 9.15, y, w: 3.6, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
    text(s, b, { x: 9.15, y: y + 0.42, w: 3.6, h: 0.8, fontSize: 14 });
  });
}

// ================================================================== 5. Methodology: workflow
{
  const s = content("4. Methodology");
  s.addText("Workflow: every upload follows the same evidence-safe path", { placeholder: "title" });
  const steps = [["Sign in", "Session cookie; each analyst sees only their own cases"], ["Upload", "JPG · PNG · TIFF · BMP · WebP\nMP4 · AVI · MOV · MKV"], ["Validate", "Extension, size ≤ 100 MB, real decodable content"],
                 ["Store & hash", "Original kept byte-for-byte; SHA-256 recorded"], ["Analyse", "Independent checks as a background job with progress"], ["Report", "Interactive views and a PDF report"]];
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

// ================================================================== 6. Hardware & software requirements
pres.addSection({ title: "5. Requirements" });
{
  const s = content("5. Requirements");
  s.addText("Hardware and software requirements", { placeholder: "title" });
  card(s, M, 1.45, 5.0, 5.15);
  text(s, "Hardware", { x: M + 0.35, y: 1.65, w: 4.3, h: 0.5, fontSize: 22, bold: true, color: C.accent2, fontFace: THEME.headFontFace });
  text(s, [
    { text: "An ordinary laptop or desktop; CPU only, no GPU needed", options: { bullet: true, breakLine: true } },
    { text: "Input: photos and videos from any camera or phone; no special sensors", options: { bullet: true, breakLine: true } },
    { text: "Runs offline after installation; evidence never leaves the machine", options: { bullet: true } },
  ], { x: M + 0.35, y: 2.3, w: 4.3, h: 4.1, fontSize: 16, paraSpaceAfter: 12 });
  card(s, 5.85, 1.45, W - M - 5.85, 5.15, C.text2);
  text(s, "Software", { x: 6.2, y: 1.65, w: 6.2, h: 0.5, fontSize: 22, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  const rows = [
    ["Platform", "Windows 11 · Python 3.12 · Node.js 26 LTS · a modern browser"],
    ["Vision libraries", "OpenCV 5.1 · NumPy 2.2 · scikit-image 0.26 · Pillow 12 · ImageHash · SciPy"],
    ["Back end", "FastAPI · Uvicorn · SQLAlchemy · SQLite · ReportLab · Matplotlib"],
    ["Front end", "Next.js 15.5 · React 19 · TypeScript · Recharts · Tailwind CSS"],
    ["Testing & data", `pytest · CASIA v2.0 (${casia.n.toLocaleString("en-US")} images) · synthetic video benchmark`],
  ];
  rows.forEach(([h, b], i) => {
    const y = 2.3 + i * 0.84;
    text(s, h, { x: 6.2, y, w: 2.1, h: 0.75, fontSize: 15, bold: true, color: C.accent1 });
    text(s, b, { x: 8.35, y, w: 4.1, h: 0.75, fontSize: 14, color: C.background1 });
  });
}

// ================================================================== 7. Implementation: steps + structure
pres.addSection({ title: "6. Implementation" });
{
  const s = content("6. Implementation");
  s.addText("Implementation: steps followed", { placeholder: "title" });
  const steps = [
    ["Evidence intake", "FastAPI endpoints validate, store and SHA-256 hash every upload."],
    ["Forensic checks", "Each technique is an independent, unit-tested Python function."],
    ["Web interface", "Next.js pages with side-by-side or slider comparisons, timelines and notes."],
    ["Evaluation", "Harnesses run the real pipeline on CASIA v2.0 and on videos with known edits."],
    ["Iterate on results", "Heat maps, motion-confirmed repeats, re-tuned copy-move; JPEG ghosts replaced the noise map; sign-in added."],
  ];
  sideList(s, steps, M, 1.5, 1.03, 6.1);
  card(s, 7.75, 1.45, W - M - 7.75, 5.15, C.text2);
  text(s, "Code structure", { x: 8.05, y: 1.6, w: 4.4, h: 0.45, fontSize: 18, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  text(s, [
    "backend/", "   main.py  (REST API)", "   auth.py  (accounts, sessions)", "   processing/image/  (ELA, ORB, ghost …)", "   processing/video/  (hash, SSIM, flow)",
    "   reports/  (PDF)   database/  (SQLite)", "frontend/src/  (Next.js pages)", "evaluation/  (CASIA, video benchmark)", "tests/  (35 pytest tests)", "requirements.txt · start.ps1",
  ].map((t, i, a) => ({ text: t, options: { breakLine: i < a.length - 1 } })), { x: 8.05, y: 2.15, w: 4.5, h: 4.3, fontSize: 13, fontFace: "Consolas", color: C.background1 });
}

// ================================================================== 8. Image techniques
{
  const s = content("6. Implementation");
  s.addText("Image forensics: five complementary checks", { placeholder: "title" });
  const grid = [[DEMO("gulls_evidence.jpg"), "Evidence (CASIA v2.0 copy-move)"], [DEMO("gulls_ela_map.png"), "ELA heat map"],
                [DEMO("gulls_orb.png"), "Copy-move: duplicated gull matched"], [DEMO("splice_ghost_map.png"), "JPEG ghost on a test splice"]];
  grid.forEach(([f, cap], i) => {
    const sz = fit(f, 2.9, 2.2), x = M + (i % 2) * 3.05, y = 1.45 + Math.floor(i / 2) * 2.62;
    picture(s, f, x, y, sz.w, sz.h, cap);
    text(s, cap, { x, y: y + sz.h + 0.04, w: 2.9, h: 0.32, fontSize: 11, color: C.accent6 });
  });
  sideList(s, [
    ["ELA + heat map", "Re-save at JPEG Q90; each 16 × 16 block is compared with the rest of the image to point at unusual regions."],
    ["Copy-move", "ORB self-matches grouped by repeated RANSAC; flagged at ≥ 5 matches with the copy ≥ 40 px away."],
    ["JPEG ghosts", "Re-save at qualities 50–95; a pasted region matches its earlier quality unusually well (Farid, 2009)."],
    ["Compression", "JPEG quantization tables give the save quality and software vs camera tables."],
    ["EXIF", "Camera, software and date tags."],
  ], 7.0, 1.5, 1.05);
}

// ================================================================== 9. Video techniques
{
  const s = content("6. Implementation");
  s.addText("Video forensics: compare neighbouring frames", { placeholder: "title" });
  const fr = DEMO("video_frame_5s.jpg"), fl = DEMO("video_flow_5s.jpg");
  const sz = fit(fr, 2.9, 1.9);
  picture(s, fr, M, 1.55, sz.w, sz.h, "Sampled frame at the inserted segment");
  picture(s, fl, M + 3.05, 1.55, sz.w, sz.h, "Optical flow into that frame: colour is direction, brightness is speed");
  text(s, "Frame at 5 s (inserted footage)", { x: M, y: 1.6 + sz.h, w: 2.9, h: 0.35, fontSize: 12, color: C.accent6 });
  text(s, "Optical flow into that frame", { x: M + 3.05, y: 1.6 + sz.h, w: 2.9, h: 0.35, fontSize: 12, color: C.accent6 });
  sideList(s, [
    ["Sampling", "1 frame per second, at most 180 frames, keeps analysis fast."],
    ["Repeated frames", "pHash distance ≤ 4 AND optical flow ≤ 1 px: frozen, not just slowly panning."],
    ["Continuity", "SSIM between neighbouring samples; sharp dips mark cuts or fast motion."],
    ["Scene cuts", "8 × 8 × 8 colour histogram, Bhattacharyya distance ≥ 0.55."],
    ["Motion", "Farnebäck dense flow for every pair; spikes above median + 3.5 × MAD are flagged."],
  ], 7.0, 1.5, 1.05);
  card(s, M, 4.25, 5.95, 2.35, C.background2);
  text(s, "Why median and MAD?", { x: M + 0.3, y: 4.45, w: 5.4, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
  text(s, "A robust z-score, (motion − median) / MAD, keeps one large spike from hiding another, so every sudden jump in camera motion is reported, not just the biggest.", { x: M + 0.3, y: 4.9, w: 5.4, h: 1.5, fontSize: 15 });
}

// ================================================================== 10-12. Results: screenshots
pres.addSection({ title: "7. Results" });
{
  const s = content("7. Results");
  s.addText("Results: image forensics page", { placeholder: "title" });
  const f = path.join(SHOT, "image_analysis.png"), sz = fit(f, 8.6, 5.4);
  picture(s, f, M, 1.4, sz.w, sz.h, "Image forensics page: summary metrics and side-by-side ELA comparison");
  const pts = [["Summary metrics", "Indicators, copy-move flag, unusual ELA and JPEG-ghost blocks, JPEG quality"], ["Visual comparison", "Heat maps or matches beside the original, or a wipe slider; click to zoom"],
               ["Method cards", "What each check does, how to read it, and its caveat"]];
  pts.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.55;
    tag(s, 9.55, y, i + 1, { d: 0.42, size: 13 });
    text(s, h, { x: 10.1, y: y - 0.02, w: 2.65, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    text(s, b, { x: 10.1, y: y + 0.4, w: 2.65, h: 1.05, fontSize: 13 });
  });
}
{
  const s = content("7. Results");
  s.addText("Results: JPEG ghost points at a pasted region", { placeholder: "title" });
  const g = path.join(SHOT, "image_ghost.png"), sg = fit(g, 8.4, 4.6);
  picture(s, g, M, 1.45, sg.w, sg.h, "JPEG ghost map: the pasted patch stands out against the rest of the photo");
  text(s, "Test splice: a patch saved at JPEG quality 60, pasted into another photo, saved again at 92. The ghost map lights up the patch (strongest block 15 deviations, ghost at quality ≈ 65).",
    { x: M, y: 1.55 + sg.h, w: sg.w, h: 0.9, fontSize: 14, color: C.text1 });
  const l = path.join(SHOT, "login.png"), sl = fit(l, 3.6, 3.9);
  picture(s, l, W - M - sl.w, 1.45, sl.w, sl.h, "Sign-in page");
  text(s, "Sign-in page: each analyst sees only their own investigations", { x: W - M - 3.6, y: 1.55 + sl.h, w: 3.6, h: 0.7, fontSize: 13, color: C.accent6 });
}
{
  const s = content("7. Results");
  s.addText("Results: video forensics page", { placeholder: "title" });
  const a = path.join(SHOT, "video_analysis.png"), b = path.join(SHOT, "video_frames.png");
  const sa = fit(a, 6.9, 5.3), sb = fit(b, 5.0, 5.3);
  picture(s, a, M, 1.4, sa.w, sa.h, "Video page: summary metrics and synchronised SSIM and motion timelines");
  picture(s, b, W - M - sb.w, 1.4, sb.w, sb.h, "Video page: frame filmstrip, previous/selected/flow comparison and flagged moments");
  text(s, "Synchronised SSIM and motion timelines with scene cuts and motion spikes marked", { x: M, y: 1.45 + sa.h, w: 6.9, h: 0.5, fontSize: 12, color: C.accent6 });
  text(s, "Filmstrip with tags; previous, selected and flow images; flagged moments", { x: W - M - sb.w, y: 1.45 + sb.h, w: sb.w, h: 0.5, fontSize: 12, color: C.accent6 });
}

// ================================================================== 13. Performance: how we tested
{
  const s = content("7. Results");
  s.addText("Performance: how we tested it", { placeholder: "title" });
  const stats = [[casia.n.toLocaleString("en-US"), "CASIA v2.0 images\n7,491 authentic · 5,123 tampered"], [`${casia.seconds.mean.toFixed(2)} s`, "average analysis time per image on a laptop CPU"],
                 [`${video.processing_seconds.mean.toFixed(1)} s`, "per 16–25 s video clip: about 4× faster than real time"], [`${TESTS.total} / ${TESTS.total}`, `automated tests passing (${TESTS.api} end-to-end API tests)`]];
  stats.forEach(([v, l], i) => stat(s, M + i * 3.1, 1.9, 2.8, v, l, [C.accent2, C.accent4, C.accent5, C.accent1][i]));
  card(s, M, 4.6, W - 2 * M, 1.75);
  text(s, [
    { text: "Real pipeline, measured end to end. ", options: { bold: true, color: C.text2 } },
    { text: `The evaluation scripts call the same analysis functions as the app on every image and compute ROC curves, AUC, precision, recall and false-positive rates; heat maps are scored against ${loc.evaluated.toLocaleString("en-US")} ground-truth masks. Rules were tuned on one half of CASIA and reported on the other. 60 synthetic clips with known edits test the video checks.` },
  ], { x: M + 0.35, y: 4.8, w: W - 2 * M - 0.7, h: 1.4, fontSize: 16, valign: "middle" });
}

// ================================================================== 14. Performance: CASIA AUC chart
{
  const s = content("7. Results");
  s.addText("Accuracy: which image scores separate authentic from tampered?", { placeholder: "title" });
  const labels = ["ELA peak", "ORB raw matches", "ORB consistent", "Noise std (removed)", "Noise tile ratio (removed)"];
  const keys = ["ELA peak difference", "ORB raw matches", "ORB consistent matches", "Noise residual std", "Noise tile variance ratio"];
  s.addChart(pres.charts.BAR, [{ name: "AUC", labels, values: keys.map((k) => +casia.scores[k].auc.toFixed(3)) }], {
    x: M, y: 1.4, w: 7.4, h: 5.2, barDir: "bar", catAxisOrientation: "maxMin",
    chartColors: [H.accent2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelFontSize: 14, dataLabelColor: H.dk1,
    valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.25, valAxisLabelFontSize: 12, catAxisLabelFontSize: 13,
    valGridLine: { color: "D9DEE5", size: 0.75 }, catGridLine: { style: "none" }, valAxisLabelColor: H.accent6, catAxisLabelColor: H.dk1,
    showTitle: true, title: "Area under the ROC curve (0.5 = chance, 1.0 = perfect)", titleFontSize: 14, titleColor: H.dk1, showLegend: false, ...chartText,
    objectName: "casia-auc-chart",
  });
  const cmv = casia.by_type["copy-move"], a = casia.app_threshold;
  sideList(s, [
    ["ELA scores highest", `AUC ${casia.scores["ELA peak difference"].auc.toFixed(2)}, but see the next slide for why.`],
    ["Copy-move works for copy-move", `AUC ${cmv.orb_auc.toFixed(2)} on copy-move forgeries, chance (${casia.by_type.splicing.orb_auc.toFixed(2)}) on splicing. Flags ${pct(cmv.recall)} of them, and ${pct(a.fpr, 1)} of authentic images.`],
    ["Noise did not separate", "Near chance, and the noise map did not localise edits, so it was removed and replaced by JPEG ghosts."],
  ], 8.45, 1.55, 1.75, 3.75);
}

// ================================================================== 15. Key finding
{
  const s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "7. Results" });
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
    { text: `ELA keeps its AUC of ${casia.jpeg_only_auc["ELA peak difference"].toFixed(2)} on JPEGs alone, so file format is not the cause: a global ELA peak reflects how a file was last saved. The fix was to compare regions within one image instead. The ELA heat map points at edited pixels with a pixel AUC of ${loc.by_type.all.ela.pixel_auc.toFixed(2)} against the ground-truth masks.`, options: { color: C.background1 } },
  ], { x: M + 0.35, y: 4.45, w: W - 2 * M - 0.7, h: 1.95, fontSize: 17 });
  s.addNotes("This is the most important result: measure quantization tables before trusting compression-based scores on CASIA v2.0.");
}

// ================================================================== 16. Video benchmark
{
  const s = content("7. Results");
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
  text(s, `Scene-cut and motion-spike checks are reliable. Repeats now need near-zero optical-flow motion too: every freeze is still caught, and false repeat alarms on panning clips fell from ${BEFORE.repeatPerMinute} per minute to ${fa.repeat.flags_per_minute.toFixed(1)}.`,
    { x: M, y: 6.15, w: W - 2 * M, h: 0.75, fontSize: 15 });
}

// ================================================================== 17. Challenges & solutions
pres.addSection({ title: "8. Challenges & Solutions" });
{
  const s = content("8. Challenges & Solutions");
  s.addText("Challenges and how we solved them", { placeholder: "title" });
  const p = tuning.test.previous_rule, c = tuning.test.chosen;
  const rows = [
    ["ELA score followed save settings, not edits", "Compare regions within one image: ELA heat map, pixel AUC " + loc.by_type.all.ela.pixel_auc.toFixed(2)],
    ["Panning video looked like repeated frames", `Also require near-zero optical flow: false alarms ${BEFORE.repeatPerMinute} → ${video.false_alarms.repeat.flags_per_minute.toFixed(0)} per minute`],
    ["Copy-move raised too many false alarms", `Re-tuned on held-out data: ${pct(p.fpr, 1)} → ${pct(c.fpr, 1)} of authentic images flagged`],
    ["Noise map did not localise edits", "Removed it (and the histogram); added JPEG ghosts for splicing"],
    ["No labelled tampered-video dataset", "Built a synthetic benchmark of 60 clips with known edit times"],
    ["Several people sharing one install", "Accounts with hashed passwords; each analyst sees only their own cases"],
  ];
  text(s, "Challenge", { x: M, y: 1.4, w: 5.4, h: 0.4, fontSize: 14, bold: true, color: C.accent6 });
  text(s, "Solution", { x: 6.4, y: 1.4, w: 6.3, h: 0.4, fontSize: 14, bold: true, color: C.accent6 });
  rows.forEach(([ch, so], i) => {
    const y = 1.85 + i * 0.8;
    card(s, M, y, 5.5, 0.68);
    text(s, ch, { x: M + 0.2, y, w: 5.1, h: 0.68, fontSize: 15, bold: true, color: C.text2, valign: "middle" });
    s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: 6.15, y: y + 0.24, w: 0.13, h: 0.22, rotate: 90, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: name("arrow") });
    card(s, 6.4, y, W - M - 6.4, 0.68, C.text2);
    text(s, so, { x: 6.6, y, w: W - M - 6.8, h: 0.68, fontSize: 14, color: C.background1, valign: "middle" });
  });
  s.addNotes("Every fix was measured on the same benchmark before and after; rules were chosen on one half of the data and reported on the other.");
}

// ================================================================== 18. Applications
pres.addSection({ title: "9. Applications" });
{
  const s = content("9. Applications");
  s.addText("Applications: where ImageGuard helps", { placeholder: "title" });
  const apps = [
    ["Journalism & fact-checking", "Screen a viral photo or clip before publishing or debunking it."],
    ["Police & cyber cells", "First look at digital evidence, with a SHA-256 record of what was received."],
    ["Insurance claims", "Check damage photos for copied or pasted regions and re-saved files."],
    ["Legal & HR cases", "Attach a PDF report with observations and limits, not a verdict."],
    ["Content moderation", "Triage reported media for repeated frames, cuts and edited regions."],
    ["Teaching", "Show students what ELA, keypoints, SSIM and optical flow reveal."],
  ];
  apps.forEach(([h, b], i) => {
    const x = M + (i % 3) * 4.1, y = 1.5 + Math.floor(i / 3) * 2.6;
    card(s, x, y, 3.85, 2.35, i % 2 ? C.background2 : C.background2);
    tag(s, x + 0.3, y + 0.3, i + 1);
    text(s, h, { x: x + 0.3, y: y + 0.95, w: 3.3, h: 0.5, fontSize: 18, bold: true, color: C.text2 });
    text(s, b, { x: x + 0.3, y: y + 1.45, w: 3.3, h: 0.8, fontSize: 14 });
  });
}

// ================================================================== 19. Conclusion & future scope
pres.addSection({ title: "10. Conclusion" });
{
  const s = content("10. Conclusion");
  s.addText("Conclusion and future scope", { placeholder: "title" });
  card(s, M, 1.45, 5.9, 5.1);
  text(s, "Conclusion", { x: M + 0.35, y: 1.65, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.accent2, fontFace: THEME.headFontFace });
  text(s, [
    { text: "Classical techniques make a practical, private and explainable screening tool on an ordinary laptop", options: { bullet: true, breakLine: true } },
    { text: "Evidence is preserved, verifiable and kept private to each analyst", options: { bullet: true, breakLine: true } },
    { text: "Scene-cut and motion-spike checks reliably locate inserted and deleted video segments", options: { bullet: true, breakLine: true } },
    { text: "Evaluation exposed misleading scores, and measured fixes removed them", options: { bullet: true } },
  ], { x: M + 0.35, y: 2.25, w: 5.2, h: 4.1, fontSize: 16, paraSpaceAfter: 10 });
  card(s, 6.85, 1.45, 5.9, 5.1, C.text2);
  text(s, "Future scope", { x: 7.2, y: 1.65, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  text(s, [
    { text: "Measure JPEG ghosts on CASIA against ground-truth masks", options: { bullet: true, breakLine: true } },
    { text: "SIFT matching to recover small copy-moves (evaluation script ready)", options: { bullet: true, breakLine: true } },
    { text: "Adaptive video sampling around SSIM dips and motion spikes", options: { bullet: true, breakLine: true } },
    { text: "Evaluate on Columbia, CoMoFoD and real tampered videos", options: { bullet: true, breakLine: true } },
    { text: "Optional, clearly labelled deep-learning detectors for comparison", options: { bullet: true } },
  ], { x: 7.2, y: 2.25, w: 5.2, h: 4.1, fontSize: 16, paraSpaceAfter: 10, color: C.background1 });
}

// ================================================================== 20. Thank you
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "10. Conclusion" });
  // Closing slide: only a large, centred "Thank you".
  text(s, "Thank you", { x: 0, y: 0, w: W, h: 7.5, fontSize: 80, bold: true, color: C.background1, fontFace: THEME.headFontFace, align: "center", valign: "middle" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("Wrote " + OUT);
})();
