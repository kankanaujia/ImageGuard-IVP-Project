"""Build the ImageGuard project report (Word) in the university template's format.

Run from the project root:
    backend\\.venv\\Scripts\\python.exe documentation\\build\\diagrams.py      # design figures
    backend\\.venv\\Scripts\\python.exe documentation\\build\\build_report.py  # -> documentation/ImageGuard_Project_Report.docx

Evaluation numbers are read from evaluation/results/*/metrics.json, so re-running the
evaluation scripts and this file keeps the report in sync with the code.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from ooxml import Doc, para, run, rich, field, sect_pr, ppr, TEXT_W

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(__file__).resolve().parent
FIG = BUILD / "figures"
SHOTS = BUILD / "screenshots"
RESULTS = ROOT / "evaluation" / "results"
OUT = ROOT / "documentation" / "ImageGuard_Project_Report.docx"

TITLE = "ImageGuard: Explainable Forensic Screening of Digital Images and Videos"
STUDENTS = [("2025010033", "Elisha Chophla"), ("2025010053", "Kanishka Kanaujia")]
MENTOR = "Kamal Kanan"
MONTH_YEAR = "December 2026"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


CASIA = load(RESULTS / "casia" / "metrics.json")
JQ = load(RESULTS / "casia" / "jpeg_quality.json")
VIDEO = load(RESULTS / "video" / "metrics.json")
PENDING = "[pending]"


def cm(*keys, fmt="{:.3f}", default=PENDING):
    """Read a CASIA metric by key path, formatted; '[pending]' until the evaluation has run."""
    node = CASIA
    for k in keys:
        if node is None or k not in node: return default
        node = node[k]
    return fmt.format(node) if isinstance(node, (int, float)) else str(node)


def pct(x): return f"{100 * x:.1f}%"


# ======================================================================= content
# Blocks: ("h1", text) ("h2", text) ("h3", text) ("p", text) ("ul", [..]) ("ol", [..])
#         ("table", key, caption, headers, rows, widths[, align]) ("fig", key, file, width_in, caption) ("pb",)
# Text may reference {fig:key} / {tab:key}; numbers are resolved in a first pass.
B: list[tuple] = []
H1 = lambda t: B.append(("h1", t)); H2 = lambda t: B.append(("h2", t)); H3 = lambda t: B.append(("h3", t))
P = lambda t: B.append(("p", t)); UL = lambda items: B.append(("ul", items)); OL = lambda items: B.append(("ol", items))
TAB = lambda key, cap, head, rows, widths, align=None: B.append(("table", key, cap, head, rows, widths, align))
FIGR = lambda key, file, w, cap: B.append(("fig", key, file, w, cap))

ABSTRACT = [
    "Digital images and videos are routinely used as evidence in journalism, insurance claims, academic integrity cases and legal proceedings, yet free editing tools make convincing manipulation easy. Most people who must judge such media have no practical way to examine it beyond looking at it. This project presents **ImageGuard**, a locally hosted web application that screens images and videos with classical, explainable image and video processing techniques and presents every observation together with its limitations, rather than issuing an opaque \"fake\" or \"real\" verdict.",
    "For images, ImageGuard performs Error Level Analysis (ELA), ORB keypoint self-matching with RANSAC geometric verification for copy-move detection, noise-residual consistency analysis, colour histogram analysis and EXIF metadata extraction. For videos, it samples one frame per second and applies perceptual hashing to find repeated frames, the Structural Similarity Index (SSIM) and colour-histogram distance to find abrupt changes, and Farnebäck dense optical flow across every pair of sampled frames with a robust median/MAD test to flag motion discontinuities. Every upload is stored unmodified under a random name and fingerprinted with SHA-256 so that its integrity can be re-verified at any time, and each investigation produces a PDF report.",
    "The system is built with FastAPI, OpenCV, scikit-image and SQLite on the back end and Next.js with React and TypeScript on the front end. It was evaluated on the public CASIA v2.0 tampering dataset and on a synthetic video benchmark of 60 clips with known edits. "
    + (f"On all {CASIA['n']:,} CASIA v2.0 images, the ELA peak difference separated authentic from tampered images with an AUC of {cm('scores','ELA peak difference','auc')}, but a measurement of the files' JPEG quantization tables showed that much of this comes from the dataset's systematically different save settings rather than from the edits themselves. "
       f"The copy-move score reached an AUC of {cm('scores','ORB consistent matches','auc')}; the app's copy-move rule flagged {pct(CASIA['by_type']['copy-move']['recall'])} of copy-move forgeries at a false-positive rate of {pct(CASIA['app_threshold']['fpr'])}. " if CASIA else "The CASIA v2.0 results are reported in Chapter 5. ")
    + (f"On the video benchmark, inserted footage was flagged in {VIDEO['per_kind']['insertion']['detected_by_any_check']} of {VIDEO['per_kind']['insertion']['clips']} clips and deleted sections in {VIDEO['per_kind']['deletion']['detected_by_any_check']} of {VIDEO['per_kind']['deletion']['clips']}, with no false scene-cut alarms on clean clips; the evaluation also exposed that the repeated-frame check is unreliable on slowly panning footage. " if VIDEO else "")
    + "The results show that explainable, training-free techniques are useful for screening and for directing human attention, while also making their failure modes visible.",
    "**Keywords:** image forensics, video forensics, error level analysis, copy-move detection, ORB, SSIM, optical flow, perceptual hashing, evidence integrity.",
]

ABBREVIATIONS = [
    ("API", "Application Programming Interface"), ("AUC", "Area Under the (ROC) Curve"), ("CASIA", "Chinese Academy of Sciences, Institute of Automation (dataset)"),
    ("CORS", "Cross-Origin Resource Sharing"), ("CPU", "Central Processing Unit"), ("DCT", "Discrete Cosine Transform"), ("ELA", "Error Level Analysis"),
    ("EXIF", "Exchangeable Image File Format"), ("FPR", "False Positive Rate"), ("HSV", "Hue, Saturation, Value"), ("JPEG", "Joint Photographic Experts Group"),
    ("JSON", "JavaScript Object Notation"), ("MAD", "Median Absolute Deviation"), ("ORB", "Oriented FAST and Rotated BRIEF"), ("PDF", "Portable Document Format"),
    ("pHash", "Perceptual Hash"), ("PRNU", "Photo-Response Non-Uniformity"), ("RANSAC", "Random Sample Consensus"), ("REST", "Representational State Transfer"),
    ("ROC", "Receiver Operating Characteristic"), ("SHA-256", "Secure Hash Algorithm, 256-bit"), ("SIFT", "Scale-Invariant Feature Transform"),
    ("SRS", "Software Requirements Specification"), ("SSIM", "Structural Similarity Index Measure"), ("TPR", "True Positive Rate (recall)"),
    ("UI", "User Interface"), ("UUID", "Universally Unique Identifier"), ("WBS", "Work Breakdown Structure"),
]

# ----------------------------------------------------------------------- Chapter 1
H1("CHAPTER 1: INTRODUCTION")
H2("1.1 Project Overview")
P("**Problem statement.** Image and video editing software can now alter photographs and footage in ways that are invisible to a casual viewer: regions are copied to hide or duplicate objects, content from other pictures is spliced in, and video segments are removed, repeated or inserted. People who have to decide whether such media can be trusted (teachers, journalists, claims officers, investigators) rarely have forensic training or tools, and many available online checkers either upload the evidence to a third-party server or return a single score that cannot be explained or challenged.")
P("**Goal.** The goal of this project is to give a non-specialist investigator a private, local tool that examines an image or a video with established image and video processing techniques, shows *what* each technique observed and *where*, states the limits of each observation, and keeps the original evidence verifiably unchanged.")
P("**Solution.** ImageGuard is a web application that runs entirely on the investigator's computer. The user uploads a file in the browser; a FastAPI back end validates it, stores the untouched original under a random name, records its SHA-256 fingerprint and runs a set of independent forensic checks. Images go through error level analysis, copy-move detection, noise-residual analysis, histogram analysis and metadata extraction; videos are sampled and examined for repeated frames, abrupt similarity changes, scene cuts and motion discontinuities. Results are stored in a local SQLite database, displayed as interactive comparisons, charts and frame timelines, and exported as a PDF report. The architecture is shown in {fig:arch}.")

H2("1.2 Need Analysis")
P("Manipulated media is a recognised and growing problem. Farid's survey of image forgery detection [14] and Verdoliva's overview of media forensics [15] both describe how inexpensive tools have made manipulation routine and how detection has become an arms race. The need for this work rests on four observations:")
UL(["**Evidence must stay private.** Images in disciplinary, legal or insurance matters are often sensitive. A tool that runs on the investigator's own machine and never sends the file elsewhere avoids a whole class of privacy and chain-of-custody problems.",
    "**Explanations matter more than scores.** A reviewer must be able to justify a decision. Classical techniques such as ELA [6], keypoint-based copy-move detection [3][5] and SSIM [10] produce visual evidence a person can inspect, unlike most end-to-end deep networks [21][22].",
    "**Integrity must be provable.** Digital-evidence guidelines such as ISO/IEC 27037 [19] stress preserving the original and documenting its state. Hashing the file at intake with SHA-256 [20] lets anyone re-verify that it has not changed.",
    "**Video is under-served.** Most free tools only handle still images, while duplicated or deleted video segments [12] are a common way to misrepresent events."])
P("ImageGuard addresses these needs together in one workflow that a student, teacher or analyst can install and run on an ordinary laptop.")

H2("1.3 Research Gaps")
UL(["**Gap 1: black-box outputs.** State-of-the-art detectors based on deep learning [21][22] produce a mask or a probability but little reasoning a non-expert can check, and their accuracy drops on images unlike their training data [16]. There is a gap for tools that expose interpretable intermediate evidence.",
    "**Gap 2: single-technique tools.** Published methods usually address one manipulation type, for example copy-move [1][3][4] or noise inconsistency [7], while a practical investigation needs several complementary views of the same file, each with stated limitations.",
    "**Gap 3: evaluation hides dataset bias.** Benchmark datasets such as CASIA v2.0 [9] contain file-format and JPEG-compression differences between authentic and tampered images. Simple detectors can score well by recognising how a file was saved rather than the tampering, which is rarely reported. This project measures and reports this effect.",
    "**Gap 4: video tampering on commodity hardware.** Video forensics research [12] often targets specific codecs or needs heavy computation; lightweight, explainable screening for repeated, inserted or deleted segments that runs on a laptop is scarce."])

H2("1.4 Problem Definition and Scope")
P("**Problem definition.** Given a single image (JPEG, PNG, TIFF, BMP or WebP) or video (MP4, AVI, MOV or MKV) of at most 100 MB, produce, within seconds and on a personal computer, a set of forensic observations that (a) localise or time-stamp candidate manipulations where possible, (b) are accompanied by visualisations and plain-language interpretation guidance, (c) never modify the original file, and (d) can be exported as a report.")
P("**In scope:** passive (blind) analysis of a single file; copy-move and recompression cues in images; repeated, inserted and deleted segments and motion discontinuities in video; integrity hashing; investigation history; PDF reports; evaluation on a public image dataset and a synthetic video benchmark.")
P("**Out of scope:** deepfake and face-swap detection, camera identification from sensor noise (PRNU) [8], pixel-level splicing localisation with trained networks, audio forensics, multi-user accounts and cloud deployment. ImageGuard deliberately never claims that a file is authentic or fake.")

H2("1.5 Assumptions and Constraints")
TAB("assume", "Assumptions", ["S. No.", "Assumption"], [
    ["1", "The investigator has a Windows, Linux or macOS computer with Python 3.11+ and Node.js 20+ installed and at least 8 GB of RAM."],
    ["2", "Evidence files are in a common container and codec that Pillow or OpenCV can decode; exotic RAW formats are converted beforehand."],
    ["3", "The investigator reads the interpretation notes; results are used to direct further review, not as a final decision."],
    ["4", "One frame per second is sufficient to observe edits lasting at least about one second in video."],
    ["5", "The machine running ImageGuard is trusted; the application does not defend against an attacker with access to its storage folders."]], [1, 9], ["center", "left"])
TAB("constrain", "Constraints", ["S. No.", "Constraint"], [
    ["1", "Analysis runs synchronously on the CPU, so very long or high-resolution videos take longer; uploads are limited to 100 MB and sampling to 180 frames."],
    ["2", "Classical techniques are sensitive to recompression, resizing and natural repeated textures, which limits accuracy on heavily processed web images."],
    ["3", "No labelled public video-tampering dataset of suitable size is freely available, so video accuracy is measured on synthetic clips."],
    ["4", "On the development machine, Windows Smart App Control intermittently blocked some compiled Python packages; NumPy is pinned below 2.3 for this reason."]], [1, 9], ["center", "left"])

H2("1.6 Standards")
UL(["**ISO/IEC 27037:2012**: guidelines for identification, collection, acquisition and preservation of digital evidence [19]. ImageGuard preserves the original byte-for-byte and records its hash at intake.",
    "**FIPS PUB 180-4 (Secure Hash Standard)**: SHA-256 is used for evidence fingerprints [20].",
    "**ISO/IEC 10918-1 (JPEG)**: ELA relies on the behaviour of JPEG quantisation when an image is recompressed.",
    "**IEEE 830 / ISO/IEC/IEEE 29148**: structure of the software requirements specification in Section 2.2.",
    "**HTTP/1.1, JSON (RFC 8259) and the OpenAPI specification**: the back end exposes a documented REST interface (FastAPI generates the OpenAPI description automatically)."])

H2("1.7 Objectives")
OL(["To design and implement a local web application that accepts image and video evidence, preserves the original and records a SHA-256 fingerprint for later verification.",
    "To implement and integrate explainable image forensic techniques: error level analysis, ORB-based copy-move detection with geometric verification, noise-residual analysis, histogram analysis and metadata extraction.",
    "To implement video forensic techniques covering repeated frames (perceptual hashing), abrupt changes (SSIM and colour-histogram distance) and motion discontinuities (dense optical flow with robust outlier detection).",
    "To present every result with visualisations, interpretation guidance and explicit limitations, and to generate a PDF report per investigation.",
    "To evaluate the techniques quantitatively on the CASIA v2.0 dataset and a synthetic video benchmark, and to report their strengths and failure modes honestly."])

H2("1.8 Methodology Used")
P("The project followed an iterative, prototype-driven methodology. After a literature survey (Chapter 2) the team selected techniques that are well established, explainable and fast on a CPU. Each technique was implemented as an independent Python function with unit tests, integrated behind a common analysis engine that records a status per check, and exposed through REST endpoints. The user interface was then built page by page and checked in the browser against real analyses. Finally, two evaluation harnesses were written: one runs the real pipeline over CASIA v2.0 and computes ROC/AUC, precision, recall and false-positive rates; the other generates videos with known edits and checks whether each edit is flagged at the right moment. Findings from the evaluation fed back into the design (for example, the switch from two-frame to full-video optical flow). Details are given in Chapter 3.")

H2("1.9 Project Outcomes and Deliverables")
UL(["A working application: FastAPI back end (Python) and Next.js front end (TypeScript) with five pages: Overview, New Investigation, Image Forensics, Video Forensics and Reports.",
    "Five image checks and four video checks, each returning metrics, a visualisation and an interpretation caveat.",
    "Evidence integrity: random storage names, SHA-256 at intake and an on-demand verification endpoint.",
    "Automatic PDF reports for every investigation.",
    "An automated test suite (10 tests) and two reproducible evaluation scripts with their results (CASIA v2.0 and the synthetic video benchmark).",
    "This report and the project documentation (README with installation and run instructions)."])

H2("1.10 Novelty of Work")
UL(["**Explanation-first design.** Each check reports what it measured, how to read it and when it misleads, and the interface places the original next to each visualisation so the user can judge for themselves.",
    "**Full-video motion analysis with robust spike detection.** Optical flow is computed for every pair of sampled frames and spikes are detected with a median/MAD rule, so a single busy scene does not hide another.",
    "**Bias-aware evaluation.** The CASIA evaluation reports results on all images and on JPEG-only images and measures the JPEG save settings of each class, exposing how much apparent accuracy comes from how the files were saved rather than from the tampering.",
    "**Fully local and integrity-preserving.** No evidence leaves the machine, and the stored original can be re-hashed at any time."])

# ----------------------------------------------------------------------- Chapter 2
H1("CHAPTER 2: REQUIREMENT ANALYSIS")
H2("2.1 Literature Survey")
H3("2.1.1 Related Work")
P("**Copy-move detection.** Fridrich et al. [1] introduced block matching on quantised DCT coefficients of overlapping blocks; Popescu and Farid [2] reduced block dimensionality with PCA. Block methods are robust to noise but slow and weak against rotation and scaling. Keypoint methods followed: Amerini et al. [3] matched SIFT features within one image and clustered matches to recover the geometric transformation, and Christlein et al. [4] compared fifteen block- and keypoint-based approaches on a common benchmark and found keypoint methods much faster with competitive accuracy. ORB [5] offers binary keypoints that are an order of magnitude faster than SIFT and free of patent restrictions; ImageGuard uses ORB with RANSAC [17] verification.")
P("**Compression and noise cues.** Error level analysis, popularised by Krawetz [6], recompresses an image at a known JPEG quality and visualises the difference, since regions with a different compression history respond differently. Mahdian and Saic [7] segment images by local noise variance estimated from wavelet coefficients and flag regions whose noise differs, and Lukáš et al. [8] showed that the sensor's photo-response non-uniformity (PRNU) identifies cameras and can reveal regions from another source.")
P("**Benchmarks and learned detectors.** Dong et al. [9] released the CASIA tampering databases, which remain among the most widely used. Zampoglou et al. [16] evaluated splicing localisation algorithms on web images at scale and found that most perform poorly outside laboratory conditions. Learned detectors such as MFCN [21] and ManTra-Net [22] localise manipulations at pixel level but require training data and GPUs and are harder to explain.")
P("**Video forensics and similarity measures.** Wang and Farid [12] detected duplicated frames and regions in video through correlation. SSIM [10] compares luminance, contrast and structure and is widely used to measure frame continuity. Farnebäck's polynomial-expansion method [11] estimates dense optical flow between two frames, and perceptual hashing [13] produces compact fingerprints that stay similar for visually similar frames.")

H3("2.1.2 Research Gaps of Existing Literature")
P("The survey shows that (i) most methods target one manipulation type; (ii) learned methods trade explainability and portability for accuracy and generalise poorly [16]; (iii) evaluation on CASIA v2.0 is often reported without controlling for its format and compression imbalance; and (iv) lightweight video-tampering screening on ordinary hardware receives less attention than image forensics. These gaps are listed in Section 1.3, and ImageGuard addresses each of them.")

H3("2.1.3 Detailed Problem Analysis")
P("{tab:lit} summarises the key papers surveyed, the tools or techniques they use and the findings relevant to this project.")
TAB("lit", "Literature survey", ["S. No.", "Paper Title", "Tools / Technology", "Findings", "Citation"], [
    ["1", "Detection of copy-move forgery in digital images", "Overlapping blocks, quantised DCT, lexicographic sort", "Block matching detects duplicated regions but is slow and not rotation invariant", "Fridrich et al. [1]"],
    ["2", "A SIFT-based forensic method for copy-move attack detection and transformation recovery", "SIFT keypoints, g2NN matching, clustering", "Keypoints recover rotation and scaling of copied regions; introduced MICC-F220", "Amerini et al. [3]"],
    ["3", "An evaluation of popular copy-move forgery detection approaches", "15 block and keypoint methods, common benchmark", "Keypoint methods are much faster with competitive accuracy", "Christlein et al. [4]"],
    ["4", "ORB: An efficient alternative to SIFT or SURF", "Oriented FAST, rotated BRIEF, binary descriptors", "Binary keypoints about 10× faster than SIFT; basis of our copy-move check", "Rublee et al. [5]"],
    ["5", "A picture's worth: Digital image analysis and forensics", "Error level analysis (JPEG recompression)", "Regions with a different compression history stand out", "Krawetz [6]"],
    ["6", "Using noise inconsistencies for blind image forensics", "Wavelet noise estimation, segmentation", "Pasted regions often have different noise levels", "Mahdian and Saic [7]"],
    ["7", "CASIA image tampering detection evaluation database", "Dataset: CASIA v1.0 / v2.0", "Standard benchmark of authentic and spliced/copy-move images", "Dong et al. [9]"],
    ["8", "Image quality assessment: From error visibility to structural similarity", "SSIM index", "Structure-based similarity matches perception better than MSE", "Wang et al. [10]"],
    ["9", "Two-frame motion estimation based on polynomial expansion", "Dense optical flow (Farnebäck)", "Accurate dense flow from local polynomial models", "Farnebäck [11]"],
    ["10", "Exposing digital forgeries in video by detecting duplication", "Frame and region correlation", "Duplicated frames and regions reveal video tampering", "Wang and Farid [12]"],
    ["11", "Image forgery detection", "Survey", "Taxonomy of pixel, format, camera, physics and geometry based methods", "Farid [14]"],
    ["12", "Media forensics and deepfakes: An overview", "Survey (classical and deep methods)", "Deep detectors generalise poorly; explainability remains open", "Verdoliva [15]"]],
    [0.55, 2.6, 2.0, 2.7, 1.2], ["center", "left", "left", "left", "left"])

H3("2.1.4 Survey of Tools and Technologies Used")
TAB("tools", "Tools and technologies considered and selected", ["Need", "Selected", "Alternatives considered", "Reason for selection"], [
    ["Image processing", "OpenCV [18], Pillow, scikit-image [23]", "MATLAB, ImageMagick", "Free, fast, complete (ORB, flow, SSIM), Python-native"],
    ["Perceptual hashing", "ImageHash (pHash)", "Custom DCT hash", "Well-tested implementation of [13]"],
    ["Back-end framework", "FastAPI + Uvicorn", "Flask, Django", "Async uploads, validation, automatic OpenAPI docs"],
    ["Database", "SQLite via SQLAlchemy 2", "PostgreSQL, MongoDB", "Zero-configuration local file; ORM keeps it replaceable"],
    ["Reports", "ReportLab", "WeasyPrint, LaTeX", "Pure-Python PDF generation, no system dependencies"],
    ["Front end", "Next.js 15, React 19, TypeScript", "Plain HTML, Streamlit", "Rich interactive UI, typed API models, component reuse"],
    ["Charts", "Recharts", "Chart.js, D3", "Declarative React charts with synchronised tooltips"],
    ["Testing", "pytest", "unittest", "Concise fixtures (tmp_path), widely used"]], [1.4, 2, 1.8, 3])

H3("2.1.5 Summary")
P("ImageGuard builds directly on the surveyed work: ORB matching with RANSAC follows the keypoint line of [3][4][5]; ELA follows [6]; local noise statistics follow the idea of [7]; SSIM [10], Farnebäck flow [11] and perceptual hashing [13] are applied to the duplication and continuity problems studied in [12]. It differs from prior work in combining these into one explainable, local workflow with integrity preservation, in computing motion across the whole video with a robust spike test, and in evaluating on CASIA v2.0 with an explicit control for the dataset's format bias.")

H2("2.2 Software Requirements Specification")
H3("2.2.1 Introduction")
P("**Purpose.** This specification describes the functional and non-functional requirements of ImageGuard version 1.0, a local web application for explainable forensic screening of images and videos.")
P("**Intended audience and reading suggestions.** The document is intended for the project evaluators, the faculty mentor and future developers. Readers interested in what the system does should read Sections 2.2.2 and 2.2.3; developers should also read Chapter 4 (design) and Chapter 5 (implementation).")
P("**Project scope.** ImageGuard accepts a single image or video, runs the analyses listed in Section 1.1, stores the results locally and presents them for human review. It does not decide authenticity, does not detect deepfakes and does not support multiple users.")
H3("2.2.2 Overall Description")
P("**Product perspective.** ImageGuard is a self-contained system made of a browser front end, a REST back end and local storage ({fig:arch}). It depends only on open-source libraries and needs no network access after installation.")
P("**Product features.**")
TAB("features", "Functional requirements", ["ID", "Requirement"], [
    ["FR1", "The system shall accept JPG, JPEG, PNG, TIFF, BMP and WebP images and MP4, AVI, MOV and MKV videos up to 100 MB, rejecting other types (HTTP 415), empty files (400) and larger files (413)."],
    ["FR2", "The system shall verify that file content really is a decodable image or video, not just check the extension."],
    ["FR3", "The system shall store the original unmodified under a random UUID name and record its SHA-256 hash, size, MIME type and original name."],
    ["FR4", "The system shall run ELA, ORB copy-move detection, noise-residual analysis, histogram analysis and EXIF extraction on images."],
    ["FR5", "The system shall sample videos at one frame per second (at most 180 frames) and run perceptual hashing, SSIM, scene-change detection and optical flow."],
    ["FR6", "A failure in one check shall be recorded with its error message without stopping the other checks."],
    ["FR7", "The system shall display each result with metrics, a visualisation, interpretation guidance and limitations."],
    ["FR8", "The system shall let the user re-verify the stored original's hash at any time."],
    ["FR9", "The system shall generate and serve a PDF report for every investigation."],
    ["FR10", "The system shall list past investigations and reopen any of them."]], [1, 9], ["center", "left"])
H3("2.2.3 External Interface Requirements")
P("**User interfaces.** A responsive browser UI with a sidebar (Overview, New Investigation, Image Forensics, Video Forensics, Reports), drag-and-drop upload, side-by-side comparisons, interactive charts and a frame filmstrip (Section 5.3.4).")
P("**Hardware interfaces.** No special hardware. Recommended: a 64-bit multi-core CPU, 8 GB RAM and about 2 GB of free disk space for the software and evidence; no GPU is required.")
P("**Software interfaces.** Windows 10/11, Linux or macOS; Python 3.11+ with the packages in `backend/requirements.txt`; Node.js 20+; a modern browser (Chrome, Edge or Firefox). The front end talks to the back end over HTTP/JSON at `http://127.0.0.1:8000`.")
H3("2.2.4 Other Non-functional Requirements")
P("**Performance requirements.** An image of typical size (under about 2 megapixels) should be analysed in under 3 seconds, and a one-minute video in under 15 seconds, on a laptop CPU. Measured times are reported in Section 5.5.")
P("**Safety requirements.** The original evidence must never be modified; analyses read the stored file and write only to a separate output folder. If anything fails before the record is saved, partial files are deleted.")
P("**Security requirements.** Uploads are stored under generated names, so user-supplied paths are never used on disk; artifact endpoints reject path traversal; the API accepts cross-origin requests only from the local front end; nothing is sent to external services.")

H2("2.3 Cost Analysis")
P("The project had no budget and incurred no cost. All software used (Python, OpenCV, scikit-image, FastAPI, SQLite, Next.js and their libraries) is open source and free of licence fees, the CASIA v2.0 dataset is freely available for research, and development used existing laptops. The application needs no paid services or special hardware to run.")

H2("2.4 Risk Analysis")
TAB("risk", "Risk analysis", ["Risk", "Likelihood", "Impact", "Mitigation"], [
    ["Users treat an indicator as proof of forgery", "Medium", "High", "No verdicts are shown; every result carries caveats and the original is always shown alongside"],
    ["False alarms on natural repeated textures or recompressed images", "High", "Medium", "RANSAC geometric verification; thresholds and limitations documented; evaluation reports FPR"],
    ["Malicious or malformed uploads", "Medium", "Medium", "Extension and content validation, size limit, generated storage names, path-traversal checks"],
    ["Long videos make the UI unresponsive", "Medium", "Low", "Frame sampling with a 180-frame cap; flow computed at 480 px width"],
    ["Library or platform incompatibility (e.g. Smart App Control blocking binaries)", "Medium", "Medium", "Pinned versions, documented workaround in the README"],
    ["Evidence lost or altered on disk", "Low", "High", "Original stored separately; SHA-256 re-verification endpoint"]], [3, 1.1, 1, 4.2], ["left", "center", "center", "left"])

# ----------------------------------------------------------------------- Chapter 3
H1("CHAPTER 3: METHODOLOGY ADOPTED")
H2("3.1 Investigative Techniques")
P("**Investigative technique involved: Descriptive.** ImageGuard is a project that designs a complete new system and records and catalogues observations about the media it examines, which is the defining characteristic of a descriptive investigation. Each check describes a property of the evidence (compression response, repeated keypoint geometry, noise distribution, frame similarity, motion) and the system catalogues these observations per investigation without asserting a cause. The evaluation in Chapter 5 adds a comparative element, because the techniques are compared with each other on the same data, but the core contribution is the design of a new system and the systematic description of observations.")
P("The methodology therefore had three strands. First, the phenomena to be observed were identified from the literature (Chapter 2) and translated into measurable quantities, for example the number of geometrically consistent ORB self-matches or the robust z-score of motion between two samples. Second, each quantity was implemented as an independent, tested function whose output includes the measurement, a visualisation and an interpretation note. Third, the behaviour of each measurement was characterised on labelled data, so that its descriptions can be read with known false-alarm and detection rates.")

H2("3.2 Proposed Solution")
P("The proposed solution is a three-tier local application ({fig:arch}). The **presentation tier** is a Next.js single-page interface. The **application tier** is a FastAPI service that validates uploads, fingerprints and stores evidence, dispatches analysis and persists results. The **processing tier** contains the image and video checks ({fig:imgpipe} and {fig:vidpipe}). Results and artefacts are kept in a **storage tier** consisting of SQLite and three folders (originals, visualisations and reports). The key design decisions were:")
UL(["Each check is independent and wrapped so that an exception becomes a recorded error rather than a failed investigation.",
    "Every numeric output is accompanied by a visualisation that can be compared against the original.",
    "Video analysis works on sampled frames (1 per second) to bound processing time, and optical flow is computed at a reduced width (480 px) with magnitudes converted back to original pixels.",
    "Thresholds are fixed and documented rather than tuned per file, so the same evidence always produces the same report."])

H2("3.3 Work Breakdown Structure")
P("The work was decomposed into five packages: research, back end, front end, evaluation and documentation ({fig:wbs}).")
FIGR("wbs", "fig_wbs.png", 6.4, "Work breakdown structure")

H2("3.4 Tools and Technologies Used")
TAB("stack", "Technology stack", ["Layer", "Technology (version)", "Use in ImageGuard"], [
    ["Language", "Python 3.12, TypeScript 5", "Back-end processing; typed front end"],
    ["Image / video processing", "OpenCV 5.1, Pillow 12, scikit-image 0.26, NumPy 2.2, SciPy", "ORB, RANSAC, optical flow, histograms, SSIM, JPEG recompression"],
    ["Hashing", "ImageHash 4, hashlib", "Perceptual hashes of frames; SHA-256 of evidence"],
    ["Back end", "FastAPI, Uvicorn, python-multipart", "REST API, streaming uploads"],
    ["Persistence", "SQLAlchemy 2, SQLite", "Investigation records"],
    ["Reporting / plots", "ReportLab, Matplotlib", "PDF reports; SSIM and histogram plots"],
    ["Front end", "Next.js 15, React 19, Tailwind CSS 4, Recharts, Lucide icons", "Pages, charts, layout"],
    ["Quality", "pytest, ESLint, TypeScript compiler", "Unit tests, linting, type checking"]], [1.8, 3.4, 3.6])

# ----------------------------------------------------------------------- Chapter 4
H1("CHAPTER 4: DESIGN SPECIFICATIONS")
H2("4.1 System Architecture")
P("{fig:arch} shows the layered architecture. The browser loads the Next.js pages and calls the FastAPI REST API directly. The API validates and fingerprints each upload, after which the analysis engine runs the image or video checks. All results are written to the storage layer: one row per investigation in SQLite, the untouched original in `uploads/`, visualisations in `outputs/<id>/` and the PDF in `reports/`.")
FIGR("arch", "fig_architecture.png", 6.5, "System architecture of ImageGuard")
H2("4.2 Design Level Diagrams")
P("**Use cases.** The single actor, the investigator, can upload evidence, view per-check analyses, compare the original with visualisations, inspect the video timeline, verify integrity, download reports and browse history ({fig:usecase}).")
FIGR("usecase", "fig_use_cases.png", 5.6, "Use case diagram")
P("**Image analysis pipeline.** {fig:imgpipe} shows the five independent image checks and the parameters used. Each produces a status, metrics, a visualisation and a caveat; the indicator summary counts checks that raised a candidate indicator.")
FIGR("imgpipe", "fig_image_pipeline.png", 6.5, "Image analysis pipeline")
P("**Video analysis pipeline.** {fig:vidpipe} shows how sampled frames feed four checks whose flags are merged into a single timeline of flagged moments.")
FIGR("vidpipe", "fig_video_pipeline.png", 6.5, "Video analysis pipeline")
P("**Data model.** All metadata for an investigation lives in one table; large artefacts live in folders named after the investigation's UUID ({fig:data}).")
FIGR("data", "fig_data_model.png", 6.2, "Data model and storage layout")
H2("4.3 User Interface Diagrams")
P("The interface uses a fixed sidebar with five destinations and a content area. The analysis pages share one layout: a list of investigations of that media type on the left, and on the right an evidence header (file facts and SHA-256), a row of summary metrics, a comparison viewer or timeline, and one card per technique explaining what it does and how to read it. Screenshots of the implemented pages are given in Section 5.3.4 ({fig:shot_image} to {fig:shot_reports}).")

# ----------------------------------------------------------------------- Chapter 5
H1("CHAPTER 5: IMPLEMENTATION AND EXPERIMENTAL RESULTS")
H2("5.1 Experimental Setup")
TAB("setup", "Experimental setup", ["Item", "Configuration"], [
    ["Hardware", "Laptop with a 12-thread x86-64 CPU and 16 GB RAM; no GPU used"],
    ["Operating system", "Windows 11"],
    ["Software", "Python 3.12.10, OpenCV 5.1, NumPy 2.2.6, scikit-image 0.26, FastAPI; Node.js 26 LTS, Next.js 15.5"],
    ["Image dataset", "CASIA v2.0 [9]: authentic (Au) and tampered (Tp) images, splicing and copy-move" + (f"; {CASIA['n']} images evaluated" if CASIA else "")],
    ["Video dataset", "Synthetic benchmark: 60 clips (15 clean, 15 insertion, 15 freeze, 15 deletion), 16–25 s, 480×270, 10 fps, random pan speed 4–15 px/s, Gaussian noise σ = 2"],
    ["Execution", "Real analysis pipeline (`run_image`, `run_video`) in 10 parallel worker processes; scripts in `evaluation/`"]], [1.8, 7])

H2("5.2 Experimental Analysis")
H3("5.2.1 Data")
P("**CASIA v2.0.** The dataset [9] contains authentic images and tampered images created by splicing (content from another image, file names beginning `Tp_D`) or copy-move (content from the same image, `Tp_S`). No cleaning or pruning was applied: every readable image in the `Au` and `Tp` folders was analysed. Features are extracted by the application's own checks; the evaluation script records, per image, the ELA peak difference, raw and geometrically consistent ORB matches, noise residual standard deviation, noise tile-variance ratio and EXIF tag count. "
  + (f"The evaluated set contained {', '.join(f'{v} {k}' for k, v in CASIA['by_class'].items())} images." if CASIA else ""))
P("**Format and compression imbalance.** In CASIA v2.0 the authentic images are JPEG (and a few BMP), while most tampered images are stored as uncompressed TIFF. A score that reacts to compression (such as ELA) can therefore separate the classes partly by file format. To control for this, every score is also evaluated on the JPEG files only."
  + (" The per-format counts are listed in {tab:formats}." if CASIA else "")
  + (f" Even among JPEGs, the save settings differ by class: estimating each file's quality from its luminance quantization table shows that {pct(JQ['tampered']['most_common_quality'][0]['share'])} of tampered JPEGs share one setting (quality ≈ {JQ['tampered']['most_common_quality'][0]['quality']:.0f}), whereas authentic JPEGs are mostly saved at quality ≈ {JQ['authentic']['most_common_quality'][0]['quality']:.0f} ({pct(JQ['authentic']['most_common_quality'][0]['share'])}) or ≈ {JQ['authentic']['most_common_quality'][1]['quality']:.0f} ({pct(JQ['authentic']['most_common_quality'][1]['share'])}). This script is `evaluation/casia_jpeg_quality.py`." if JQ else ""))
if CASIA:
    TAB("formats", "CASIA v2.0 images by format and class", ["Format", "Authentic", "Tampered"],
        [[f.upper(), str(v["authentic"]), str(v["tampered"])] for f, v in CASIA["by_format"].items()], [2, 2, 2], ["center"] * 3)
P("**Synthetic video benchmark.** Because no small, freely available, labelled video-tampering dataset exists, 60 clips were generated with a known edit time: *clean* (continuous pan), *insertion* (2–4 s of a different scene spliced in), *freeze* (one frame held for 2–4 s) and *deletion* (2–4 s of camera travel removed). Each scene has its own colour cast, random shapes and texture, and mild sensor noise so that repeated frames are not bit-identical.")
H3("5.2.2 Performance Parameters")
P("For images, each check produces a continuous score. Its ability to separate authentic from tampered images is summarised by the **ROC curve** and its **AUC** (0.5 = chance, 1.0 = perfect). For the application's actual decision rule (copy-move flagged when at least four geometrically consistent ORB matches are found) we report **accuracy**, **precision** = TP/(TP+FP), **recall** (TPR) = TP/(TP+FN), **false-positive rate** = FP/(FP+TN) and **F1**. For video, an edit counts as **detected** if a flag lands within one sample (1 s) of the edit's start or end; **false alarms** are flags on clean clips, reported as clips affected and flags per minute. **Processing time** per file is reported for both.")

H2("5.3 Working of the Project")
H3("5.3.1 Procedural Workflow")
P("{fig:workflow} shows the end-to-end processing of one upload. The browser first checks the extension and size, then posts the file to `/api/image/analyze` or `/api/video/analyze` (the endpoint is chosen from the file type, falling back to the extension because browsers often report no MIME type for MKV and AVI). The back end streams the upload to disk in 1 MB chunks under a UUID name, aborting with HTTP 413 if it exceeds 100 MB. It then confirms that the content is really an image (Pillow) or a readable video (OpenCV), rejecting anything else with HTTP 415, and computes the SHA-256 of the stored file.")
P("The analysis engine runs each check inside its own error handler, so a failure is recorded as `status: error` with the message while the remaining checks continue. The combined result is saved as JSON in the `investigations` table and a PDF report is generated; if PDF generation fails, the download endpoint regenerates it later. If any step fails before the record is saved, the stored file and its output folder are deleted, so no orphaned evidence remains. Finally, the JSON result is returned and the browser navigates to the report view.")
FIGR("workflow", "fig_workflow.png", 5.6, "Procedural workflow for one investigation")

H3("5.3.2 Algorithmic Approaches Used")
P("**(a) Error Level Analysis.** Let *I* be the image converted to RGB and *J* the same image after saving as JPEG at quality *q* = 90. The ELA map is *E* = |*I* − *J*| per channel, scaled by 255/max(*E*) so that the strongest difference is white. Regions that were compressed differently from their surroundings respond differently to recompression.")
OL(["Convert the input to RGB and save a JPEG copy at quality 90.",
    "Compute the absolute per-pixel difference between the original and the copy.",
    "Find the peak difference *p* over all channels and brighten the difference image by 255/*p*.",
    "Return the visualisation, *p* and the per-channel ranges."])
P("**(b) Copy-move detection with ORB and RANSAC.** Up to 2,500 ORB keypoints are detected on the greyscale image. Each descriptor is matched against all descriptors of the same image (Hamming distance, *k* = 3 nearest neighbours). After removing the trivial self-match, a match is kept if it passes Lowe's ratio test (best < 0.78 × second best) and its two keypoints are at least 24 px apart. If four or more matches remain, a partial affine transformation is estimated with RANSAC (reprojection threshold 4 px) and only inliers, matches that agree on one common shift, rotation and scale, are kept. Four or more consistent matches raise a candidate indicator.")
OL(["*kp*, *d* ← ORB(gray, 2500)",
    "for each descriptor *d*ᵢ: find 3 nearest neighbours in *d*; drop the neighbour equal to *i*",
    "keep (*i*, *j*) if dist₁ < 0.78·dist₂ and ‖*kp*ᵢ − *kp*ⱼ‖ ≥ 24",
    "if |matches| ≥ 4: *M*, inliers ← RANSAC-affine(points_i, points_j, 4.0); matches ← inliers",
    "flag ← |matches| ≥ 4; draw matches between the two copies of the image"])
P("**(c) Noise-residual analysis.** The residual *R* = |*I* − *G*₃ₓ₃ ∗ *I*| keeps fine texture and sensor noise. The image is divided into an 8 × 8 grid and the variance of *R* is computed in each tile. The ratio of the largest to the smallest tile variance summarises how uneven the noise is; the residual image itself is shown so the user can see *where* it differs.")
P("**(d) Histogram and metadata.** 256-bin histograms of the three colour channels reveal clipping and the comb-like gaps typical of contrast adjustments; EXIF tags (camera, software, dates) are read with Pillow.")
P("**(e) Repeated-frame detection.** A 64-bit perceptual hash (pHash, based on the low-frequency DCT of a reduced greyscale frame [13]) is computed for each sampled frame. Neighbouring frames whose Hamming distance is at most 4 are reported as exact (distance 0) or near repeats.")
P("**(f) SSIM and scene-change detection.** SSIM [10] between neighbouring greyscale samples gives a continuity score in [−1, 1]. Independently, an 8 × 8 × 8 colour histogram is computed per frame; a Bhattacharyya distance of 0.55 or more to the previous frame marks a scene-change candidate.")
P("**(g) Optical flow with robust spike detection.** For each pair of neighbouring samples, both frames are resized to 480 px width and Farnebäck dense flow [11] is computed (pyramid scale 0.5, 3 levels, window 15, 3 iterations, polynomial neighbourhood 5, σ 1.2). The per-pixel magnitude is divided by the resize factor so it is expressed in original pixels, and the mean and 95th percentile are recorded. With *m*ₖ the mean motion of pair *k*, the median *m̃* and MAD = 1.4826 · median|*m*ₖ − *m̃*| are computed, and pair *k* is a **motion spike** if (*m*ₖ − *m̃*)/MAD ≥ 3.5 and *m*ₖ ≥ 1 px (at least four pairs are required). Using the median and MAD instead of the mean and standard deviation keeps one large spike from masking another. Each pair's flow is rendered in HSV (hue = direction, value = speed, saturating at 8 analysed pixels) so that motion images are comparable.")

H3("5.3.3 Project Deployment")
P("ImageGuard is deployed on a single machine ({fig:deploy}). The back end runs in a Python virtual environment under Uvicorn on `127.0.0.1:8000` and the front end runs under Node.js on port 3000. The browser loads pages from the Next.js server and calls the API directly; CORS permits only the local front-end origin. Installation consists of creating the virtual environment, installing `backend/requirements.txt`, running `npm install` in `frontend/` and starting both servers, as documented in the README.")
FIGR("deploy", "fig_deployment.png", 6.4, "Deployment diagram")

H3("5.3.4 System Screenshots")
for key, file, cap in [("shot_overview", "overview.png", "Overview dashboard"),
                       ("shot_upload", "investigation.png", "New investigation (evidence intake)"),
                       ("shot_image", "image_analysis.png", "Image forensics page: summary metrics and side-by-side ELA comparison"),
                       ("shot_image_cards", "image_cards.png", "Image forensics page: per-technique cards with interpretation guidance"),
                       ("shot_video", "video_analysis.png", "Video forensics page: synchronised SSIM and motion timelines"),
                       ("shot_video_frames", "video_frames.png", "Video forensics page: frame filmstrip, previous/selected/flow comparison and flagged moments"),
                       ("shot_reports", "reports.png", "Reports and investigation history")]:
    FIGR(key, f"../screenshots/{file}", 6.4, cap)

H2("5.4 Testing Process")
H3("5.4.1 Test Plan")
P("Testing was carried out at three levels: automated unit tests for every algorithm and utility, system tests through the REST API with real files, and manual UI tests in the browser. Quantitative evaluation (Section 5.5) complements functional testing by measuring how well the checks perform.")
H3("5.4.2 Features to be Tested")
UL(["Upload validation (type, size, content) and evidence integrity (hashing and verification).",
    "Each image check and each video check, including failure isolation.",
    "Result persistence, PDF generation and artefact serving.",
    "Front-end pages: upload, analysis views, comparisons, charts, frame selection, history and error states."])
H3("5.4.3 Test Strategy")
P("Algorithms were tested in isolation on synthetic inputs whose correct answer is known (a uniform image, a frame sequence shifted by a known number of pixels, an image with a pasted patch). The integrated system was then exercised end to end through the API with generated images and videos, and the UI was checked against those investigations in a browser. Regression tests were added whenever a defect was found.")
H3("5.4.4 Test Techniques")
UL(["**Black-box testing** of API endpoints with valid, invalid and boundary inputs.",
    "**White-box unit testing** of algorithm functions with controlled inputs (pytest).",
    "**Regression testing**: tests added for each defect found (copy-move array types, SHA-256 expected value, optical-flow accuracy and scale).",
    "**Static analysis**: TypeScript type checking and ESLint on the front end."])
H3("5.4.5 Test Cases")
TAB("tests", "Test cases", ["ID", "Test case", "Input", "Expected result", "Result"], [
    ["T1", "SHA-256 of evidence", "File containing the bytes \"imageguard\"", "Digest equals hashlib reference", "Pass"],
    ["T2", "Safe extension handling", "Name `../../photo.JPG`", "Returns `.jpg`, path discarded", "Pass"],
    ["T3", "ELA and metadata", "24×24 PNG", "ELA image written; quality 90; size read", "Pass"],
    ["T4", "Content validation", "Text file named `.jpg`", "Rejected (ValueError → HTTP 415)", "Pass"],
    ["T5", "Copy-move detection", "Image with a duplicated 60×70 patch", "≥ 4 consistent matches", "Pass"],
    ["T6", "Hashing, SSIM, scene cut", "Three identical frames", "2 repeat pairs, SSIM > 0.99, no scene cut", "Pass"],
    ["T7", "Frame extraction", "Synthetic 10-frame AVI", "FPS > 0, frames extracted", "Pass"],
    ["T8", "Optical flow, all pairs", "Texture shifted 1 px/frame with one 12 px jump", "Flow for every pair; spike only at the jump", "Pass"],
    ["T9", "Flow scale correction", "960 px frames shifted 20 px", "Analysed at 480 px; ≈ 20 px reported", "Pass"],
    ["T10", "PDF report", "Minimal investigation record", "Non-empty PDF written", "Pass"],
    ["T11", "API: image end to end", "JPEG with copied region", "200; all 5 checks completed; hash verifies; PDF downloads", "Pass"],
    ["T12", "API: video end to end", "20 s clip with a whip pan and a cut", "200; 19 flow pairs; spikes at 8 s and 15 s", "Pass"],
    ["T13", "API: fake image", "`not an image` named `x.jpg`", "HTTP 415, nothing stored", "Pass"],
    ["T14", "UI: upload with empty MIME type", ".mkv file reported with no type", "Routed to the video endpoint and analysed", "Pass"],
    ["T15", "UI: failed check display", "Investigation with a failed check", "Card shows an error badge and message; others shown", "Pass"]],
    [0.6, 2, 2.4, 3, 0.8], ["center", "left", "left", "left", "center"])
H3("5.4.6 Test Results")
P("All 10 automated tests pass (`pytest`, about 2.5 s) and all manual system and UI tests in {tab:tests} passed. Testing found and fixed four defects before release: the copy-move check always failed because point lists were not passed to OpenCV as NumPy arrays; a dependency (Matplotlib) was missing from the requirements; a test asserted an incorrect SHA-256 value; and the reports page could not be pre-rendered without a React Suspense boundary. A further UI defect (a wide frame filmstrip stretching the page) was found during browser testing and fixed.")

H2("5.5 Results and Discussions")
H3("5.5.1 Image forensics on CASIA v2.0")
if CASIA:
    rows = []
    for name, m in CASIA["scores"].items():
        jo = CASIA.get("jpeg_only_auc", {}).get(name)
        rows.append([name, f"{m['auc']:.3f}", "–" if jo is None else f"{jo:.3f}", f"{m['best_threshold']:.3g}", f"{m['best_tpr']:.3f}", f"{m['best_fpr']:.3f}"])
    P("{tab:auc} lists the area under the ROC curve for each score on all images and on JPEG files only, together with the threshold that maximises Youden's *J* (TPR − FPR). {fig:roc} shows the ROC curves and {fig:dist} the score distributions of authentic and tampered images.")
    TAB("auc", "Separability of each score on CASIA v2.0", ["Score", "AUC (all)", "AUC (JPEG only)", "Best threshold", "TPR", "FPR"], rows,
        [2.6, 1.1, 1.3, 1.3, 0.9, 0.9], ["left"] + ["center"] * 5)
    FIGR("roc", "../../../evaluation/results/casia/roc.png", 4.6, "ROC curves of the image scores on CASIA v2.0")
    FIGR("dist", "../../../evaluation/results/casia/score_distributions.png", 6.5, "Score distributions for authentic and tampered images")
    a = CASIA["app_threshold"]
    P(f"At the application's decision rule ({a['rule']}) ImageGuard flagged {a['tp']} of {a['tp'] + a['fn']} tampered images and {a['fp']} of {a['fp'] + a['tn']} authentic images, giving accuracy {a['accuracy']:.3f}, precision {a['precision']:.3f}, recall {a['recall']:.3f}, false-positive rate {a['fpr']:.3f} and F1 {a['f1']:.3f}. {{tab:bytype}} breaks this down by manipulation type.")
    TAB("bytype", "Detection by manipulation type (app decision rule)", ["Manipulation", "Recall", "Precision", "FPR", "ORB AUC", "ELA AUC"],
        [[k, f"{v['recall']:.3f}", f"{v['precision']:.3f}", f"{v['fpr']:.3f}", f"{v['orb_auc']:.3f}", f"{v['ela_auc']:.3f}"] for k, v in CASIA["by_type"].items()],
        [2, 1, 1, 1, 1, 1], ["left"] + ["center"] * 5)
    if "seconds" in CASIA:
        s = CASIA["seconds"]
        P(f"Processing took {s['mean']:.2f} s per image on average (median {s['median']:.2f} s, 95th percentile {s['p95']:.2f} s) per worker process, including writing all visualisations, which meets the performance requirement of Section 2.2.4.")
    B.append(("casia_discussion",))
else:
    P("*[Pending: the CASIA v2.0 results (ROC curves, AUC per score, confusion statistics at the app's decision rule, breakdown by manipulation type and processing time) are inserted here when the evaluation script has been run on the dataset.]*")

H3("5.5.2 Video forensics on the synthetic benchmark")
if VIDEO:
    pk, fa = VIDEO["per_kind"], VIDEO["false_alarms"]
    P("{tab:video} shows how often each edit was flagged within one second of its true time, by the check designed for it and by any check, and {tab:falsealarm} shows the flags raised on the 15 unedited clips.")
    TAB("video", "Detection of known video edits (15 clips each)", ["Edit", "Expected check", "Detected (expected check)", "Detected (any check)", "Scene · Repeat · Motion"],
        [[k, v["expected_check"], f"{v['detected_by_expected_check']}/{v['clips']}", f"{v['detected_by_any_check']}/{v['clips']}",
          f"{v['by_check']['scene']} · {v['by_check']['repeat']} · {v['by_check']['motion']}"] for k, v in pk.items()],
        [1.4, 1.5, 1.9, 1.7, 2], ["left", "center", "center", "center", "center"])
    TAB("falsealarm", "False alarms on 15 clean clips", ["Check", "Clips with any flag", "Flags per minute"],
        [[k, f"{v['clips_with_any_flag']}/{v['clips']}", f"{v['flags_per_minute']:.2f}" if "flags_per_minute" in v else "–"] for k, v in fa.items()],
        [2, 2, 2], ["left", "center", "center"])
    P(f"Scene-change detection caught {pk['insertion']['detected_by_expected_check']} of 15 insertions with **no** false alarms, and the optical-flow spike test caught {pk['deletion']['detected_by_expected_check']} of 15 deletions at {fa['motion']['flags_per_minute']:.1f} false flags per minute. The repeated-frame check flagged every freeze, but it also raised {fa['repeat']['flags_per_minute']:.1f} flags per minute on clean clips: because pHash is designed to tolerate small shifts, a camera panning a few pixels per second looks like a repeated frame. Its detections are therefore not informative on moving footage, and this is reported in the interface's caveats and in Future Work. Processing averaged {VIDEO['processing_seconds']['mean']:.2f} s per 16–25 s clip.")
P("**Accuracy of the motion estimate.** During development a 20-second test clip with a steady 10 px/s pan measured a median of 9.4 px between samples, but a whip pan of about 75 px between two samples was measured as only 15.5 px. Farnebäck flow underestimates displacements larger than roughly 20 analysed pixels, so with one-second sampling, fast motion is under-reported. It still stood out as the largest spike, which is what the check needs, and the limitation is stated in the results.")

H3("5.5.3 Comparison with related work")
P("Deep-learning detectors such as MFCN [21] and ManTra-Net [22] localise splicing at pixel level after training on large datasets and typically need a GPU, while keypoint copy-move methods [3][4] remain the standard training-free approach. ImageGuard sits with the latter: it needs no training data, runs on a CPU in about a second per image, and explains each observation, at the cost of lower sensitivity to splicing. Unlike most published evaluations, the CASIA results here are also reported on JPEG files alone and set against the measured JPEG save settings of each class, which shows that a compression-based score's apparent accuracy on this benchmark largely reflects how the dataset was built (Section 5.2.1).")

H2("5.6 Inferences Drawn")
B.append(("inferences",))

H2("5.7 Validation of Objectives")
TAB("validate", "Validation of objectives", ["Objective", "Status", "Evidence"], [
    ["1. Local application with integrity preservation", "Met", "UUID storage, SHA-256 at intake, verify endpoint (T1, T2, T11)"],
    ["2. Explainable image checks", "Met", "Five checks implemented and tested (T3–T5, T11); CASIA evaluation"],
    ["3. Video checks", "Met", "Four checks including full-video optical flow (T6–T9, T12); video benchmark"],
    ["4. Visualisation, caveats and PDF reports", "Met", "Analysis pages (Section 5.3.4); PDF per investigation (T10)"],
    ["5. Quantitative, honest evaluation", "Met" if CASIA else "Partly met", "CASIA v2.0 ROC/AUC with JPEG-only and save-setting controls; synthetic video benchmark with false-alarm rates" if CASIA else "Video benchmark complete; CASIA evaluation pending"]],
    [3.2, 1.2, 4.6], ["left", "center", "left"])

# ----------------------------------------------------------------------- Chapter 6
H1("CHAPTER 6: CONCLUSIONS AND FUTURE DIRECTIONS")
H2("6.1 Conclusions")
P("ImageGuard shows that a set of classical image and video processing techniques can be combined into a practical, private and explainable screening tool that runs on an ordinary laptop. The system preserves evidence and makes its integrity verifiable, and it presents every observation with a visualisation and its limitations instead of a verdict. The evaluation showed that ORB copy-move detection responds to its intended manipulation, but at about a 10% false-alarm rate, so its flags need visual confirmation. On the video benchmark, colour-histogram scene detection and robust motion-spike detection located inserted and deleted segments reliably. It also showed that two techniques can look effective while measuring the wrong thing: a global ELA score on a dataset whose classes were saved with different JPEG settings, and pHash repeat detection on panning footage. Making these failure modes visible is itself a central result of the project.")
H2("6.2 Environmental, Economic and Societal Benefits")
UL(["**Societal:** helps teachers, journalists and investigators question manipulated media before acting on it, supporting fairer decisions and reducing the spread of misinformation; local processing protects the privacy of people who appear in evidence.",
    "**Economic:** uses only free, open-source software and ordinary hardware, so schools, newsrooms and small organisations can use it at no licence cost.",
    "**Environmental:** CPU-only, training-free techniques avoid the energy cost of training and running large neural networks and of uploading media to data centres."])
H2("6.3 Reflections")
P("The most valuable lesson was that evaluation must be designed as carefully as the algorithms. Building the evaluation harnesses changed our view of several checks: the repeated-frame detector looked perfect until it was run on clean clips, and ELA's high AUC on CASIA v2.0 turned out to be largely explained by the dataset's JPEG save settings once these were measured. We also learned the practical value of isolating failures (one broken check no longer breaks an investigation), of testing algorithms on inputs with known answers, and of writing interpretation text alongside each feature rather than at the end.")
H2("6.4 Future Work")
UL(["Replace the global ELA peak with a localised measure (ELA or JPEG-ghost statistics per block, compared with the image's own background) so that it responds to edited regions rather than to how the whole file was saved, and evaluate it with JPEG quality controlled.",
    "Make the repeated-frame check motion-aware: report a repeat only when the optical flow between the two samples is also near zero, removing most false alarms on panning footage.",
    "Add region-level localisation of splicing by combining local ELA, noise statistics and JPEG ghost analysis into a heat map.",
    "Sample video adaptively (denser around SSIM dips or motion spikes) and analyse audio continuity.",
    "Process long videos in a background job queue with real upload and analysis progress.",
    "Add camera-model checks based on sensor noise (PRNU) [8] and optional, clearly labelled deep-learning detectors for comparison.",
    "Evaluate on further datasets (Columbia, CoMoFoD, MICC-F220) and on real tampered videos."])

# ----------------------------------------------------------------------- Chapter 7
H1("CHAPTER 7: PROJECT METRICS")
H2("7.1 Challenges Faced")
UL(["**Platform issues:** Windows Smart App Control intermittently blocked compiled Python extension modules (NumPy, SQLAlchemy). This was diagnosed by importing each package in isolation and solved by pinning NumPy to a version the policy accepts.",
    "**Library behaviour:** OpenCV's newer Python bindings reject plain Python lists for point sets, which silently disabled copy-move detection until a regression test exposed it.",
    "**Motion estimation at one sample per second:** large displacements are underestimated by dense flow; the spike test had to rely on relative rather than absolute motion.",
    "**Dataset bias:** CASIA v2.0's authentic and tampered images differ in file format and JPEG save settings, which required JPEG-only and quantization-table analyses to interpret the ELA results fairly.",
    "**No public video ground truth:** a synthetic benchmark with controlled edits had to be designed."])
H2("7.2 Relevant Subjects")
TAB("subjects", "Relevant subjects", ["Subject", "Concepts applied"], [
    ["Image and Video Processing", "JPEG compression, filtering, histograms, feature detection (ORB), geometric transforms (RANSAC), SSIM, optical flow, frame sampling"],
    ["Computer Vision / Pattern Recognition", "Keypoint matching, ratio test, ROC analysis, robust statistics"],
    ["Software Engineering", "Requirements specification, layered architecture, testing, risk analysis"],
    ["Database Management Systems", "Relational schema, ORM, persistence of JSON results"],
    ["Web Technologies", "REST APIs, HTTP, CORS, React components, client-side state"],
    ["Information Security / Cyber Forensics", "Hashing, evidence integrity, input validation, path-traversal prevention"],
    ["Probability and Statistics", "Median and MAD, hypothesis-style thresholds, precision/recall"]], [2.6, 6])
H2("7.3 Interdisciplinary Knowledge Sharing")
P("The project brought together signal processing (compression, frequency-domain hashing, motion estimation), statistics (ROC analysis, robust outlier detection), software engineering (web architecture, testing) and digital forensics practice (evidence handling, chain of custody, interpretation without over-claiming). Explaining technical results to a non-specialist user also drew on technical writing and user-interface design.")
H2("7.4 Work Schedule")
P("{fig:gantt} shows the schedule followed during the semester, from the literature survey through implementation and evaluation to documentation.")
FIGR("gantt", "fig_gantt.png", 6.5, "Work schedule")
H2("7.5 Brief Analytical Assessment")
P("Technically, the project delivered a complete, tested system whose components are each grounded in published methods and whose behaviour has been measured rather than assumed. The strongest components are evidence handling, scene-change detection and full-video motion analysis. Copy-move detection works for its intended manipulation but needs visual confirmation of its flags. The weakest are the whole-image noise statistics and repeated-frame detection on moving footage. Splicing remains hard to detect without learned models, and the global ELA score's benchmark accuracy reflects the dataset's compression settings more than the edits. The evaluation framework is reusable, so improvements such as the motion-aware repeat check proposed in Section 6.4 can be measured on the same data. Overall, the project met its objectives and demonstrates the value of explainability and honest evaluation in forensic tooling.")

REFERENCES = [
    "Fridrich J., Soukal D., Lukáš J. “Detection of copy-move forgery in digital images.” In Proceedings of the Digital Forensic Research Workshop (DFRWS), 2003.",
    "Popescu A. C., Farid H. “Exposing digital forgeries by detecting duplicated image regions.” Technical Report TR2004-515, Department of Computer Science, Dartmouth College, 2004.",
    "Amerini I., Ballan L., Caldelli R., Del Bimbo A., Serra G. “A SIFT-based forensic method for copy-move attack detection and transformation recovery.” IEEE Transactions on Information Forensics and Security, vol. 6(3), pp. 1099–1110, 2011.",
    "Christlein V., Riess C., Jordan J., Riess C., Angelopoulou E. “An evaluation of popular copy-move forgery detection approaches.” IEEE Transactions on Information Forensics and Security, vol. 7(6), pp. 1841–1854, 2012.",
    "Rublee E., Rabaud V., Konolige K., Bradski G. “ORB: An efficient alternative to SIFT or SURF.” In Proceedings of the IEEE International Conference on Computer Vision (ICCV), 2011, pp. 2564–2571.",
    "Krawetz N. “A picture's worth: Digital image analysis and forensics.” Black Hat Briefings, USA, 2007.",
    "Mahdian B., Saic S. “Using noise inconsistencies for blind image forensics.” Image and Vision Computing, vol. 27(10), pp. 1497–1503, 2009.",
    "Lukáš J., Fridrich J., Goljan M. “Digital camera identification from sensor pattern noise.” IEEE Transactions on Information Forensics and Security, vol. 1(2), pp. 205–214, 2006.",
    "Dong J., Wang W., Tan T. “CASIA image tampering detection evaluation database.” In Proceedings of the IEEE China Summit and International Conference on Signal and Information Processing (ChinaSIP), 2013, pp. 422–426.",
    "Wang Z., Bovik A. C., Sheikh H. R., Simoncelli E. P. “Image quality assessment: From error visibility to structural similarity.” IEEE Transactions on Image Processing, vol. 13(4), pp. 600–612, 2004.",
    "Farnebäck G. “Two-frame motion estimation based on polynomial expansion.” In Proceedings of the Scandinavian Conference on Image Analysis (SCIA), LNCS 2749, 2003, pp. 363–370.",
    "Wang W., Farid H. “Exposing digital forgeries in video by detecting duplication.” In Proceedings of the 9th ACM Workshop on Multimedia and Security, 2007, pp. 35–42.",
    "Zauner C. “Implementation and benchmarking of perceptual image hash functions.” Master's thesis, Upper Austria University of Applied Sciences, Hagenberg, 2010.",
    "Farid H. “Image forgery detection.” IEEE Signal Processing Magazine, vol. 26(2), pp. 16–25, 2009.",
    "Verdoliva L. “Media forensics and deepfakes: An overview.” IEEE Journal of Selected Topics in Signal Processing, vol. 14(5), pp. 910–932, 2020.",
    "Zampoglou M., Papadopoulos S., Kompatsiaris Y. “Large-scale evaluation of splicing localization algorithms for web images.” Multimedia Tools and Applications, vol. 76(4), pp. 4801–4834, 2017.",
    "Fischler M. A., Bolles R. C. “Random sample consensus: A paradigm for model fitting with applications to image analysis and automated cartography.” Communications of the ACM, vol. 24(6), pp. 381–395, 1981.",
    "Bradski G. “The OpenCV Library.” Dr. Dobb's Journal of Software Tools, 2000.",
    "ISO/IEC 27037:2012. “Information technology — Security techniques — Guidelines for identification, collection, acquisition and preservation of digital evidence.” International Organization for Standardization, 2012.",
    "National Institute of Standards and Technology. “Secure Hash Standard (SHS).” FIPS PUB 180-4, 2015.",
    "Salloum R., Ren Y., Kuo C.-C. J. “Image splicing localization using a multi-task fully convolutional network (MFCN).” Journal of Visual Communication and Image Representation, vol. 51, pp. 201–209, 2018.",
    "Wu Y., AbdAlmageed W., Natarajan P. “ManTra-Net: Manipulation tracing network for detection and localization of image forgeries with anomalous features.” In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2019, pp. 9543–9552.",
    "van der Walt S., Schönberger J. L., Nunez-Iglesias J., Boulogne F., Warner J. D., Yager N., Gouillart E., Yu T. “scikit-image: Image processing in Python.” PeerJ, vol. 2, e453, 2014.",
]


def casia_discussion() -> list[tuple]:
    """Interpretation paragraphs that depend on the measured CASIA numbers."""
    s, jo = CASIA["scores"], CASIA.get("jpeg_only_auc", {})
    ela, orb = s["ELA peak difference"], s["ORB consistent matches"]
    cmv, spl, a = CASIA["by_type"]["copy-move"], CASIA["by_type"]["splicing"], CASIA["app_threshold"]
    out = [("p", f"**ELA is the strongest single score, for a partly artificial reason.** The ELA peak difference has the highest AUC ({ela['auc']:.3f}) and keeps it on JPEG files alone "
                 f"({jo['ELA peak difference']:.3f}), so the TIFF files are not what drives it. The JPEG save settings are: "
                 + (f"{pct(JQ['tampered']['most_common_quality'][0]['share'])} of tampered JPEGs share one quantization table (quality ≈ {JQ['tampered']['most_common_quality'][0]['quality']:.0f}) and their median ELA peak is "
                    f"{JQ['tampered']['ela_peak_median']:.0f}, against {JQ['authentic']['ela_peak_median']:.0f} for authentic JPEGs saved mostly at quality ≈ {JQ['authentic']['most_common_quality'][0]['quality']:.0f} or ≈ {JQ['authentic']['most_common_quality'][1]['quality']:.0f}. " if JQ else "")
                 + "A global ELA peak therefore largely measures how a file was last compressed, which in CASIA v2.0 differs systematically between the classes. It is useful evidence that a file has been re-saved or processed, but on real evidence it cannot by itself show that, or where, content was altered, which is why ImageGuard presents ELA as a map to inspect rather than as a verdict.")]
    out.append(("p", f"**Copy-move detection works for its intended manipulation, with a real false-alarm cost.** The ORB score's AUC is {cmv['orb_auc']:.3f} on copy-move forgeries but only {spl['orb_auc']:.3f} "
                     f"(chance level) on splicing, as expected for a method that looks for content repeated within one image. At the app's rule ({a['rule']}) it flags {pct(cmv['recall'])} of copy-move forgeries "
                     f"and {pct(a['fpr'])} of authentic images ({a['fp']} of {a['fp'] + a['tn']}). The false alarms come from natural repetition (windows, foliage, textures) that also produces geometrically consistent matches, "
                     "and the misses come from small or low-texture copied regions that yield too few keypoints. Youden's J also picks a threshold of 4 consistent matches, so the app's threshold sits at the best trade-off for this score."))
    out.append(("p", f"**The noise summaries do not separate the classes.** The tile-variance ratio ({s['Noise tile variance ratio']['auc']:.3f}) and residual standard deviation ({s['Noise residual std']['auc']:.3f}) are at or slightly below chance. "
                     "A single number for the whole image is dominated by scene content (sky versus foliage), so these measurements are only informative when the residual map is inspected locally, as the interface does."))
    return out


def inferences() -> list[tuple]:
    items = []
    if CASIA:
        a, cmv = CASIA["app_threshold"], CASIA["by_type"]["copy-move"]
        items.append("A high score on a benchmark can come from how the dataset was built: ELA's AUC on CASIA v2.0 is largely explained by systematic JPEG save-setting differences between classes, so any compression-based detector must be evaluated with format and quality controlled.")
        items.append(f"The copy-move check is specific to its manipulation (AUC {cmv['orb_auc']:.2f} on copy-move, chance on splicing) and flags about one authentic image in {round(1 / a['fpr'])}; its flags must be confirmed by looking at the matched regions, which the interface shows.")
        items.append("Whole-image noise statistics carry little information; local inspection of the residual map is required.")
        items.append("No single check covers all manipulations, and training-free methods detect splicing poorly, which supports presenting several complementary views and explicit limitations instead of a verdict.")
    else:
        items.append("[Image inferences pending the CASIA v2.0 evaluation.]")
    if VIDEO:
        items.append("Colour-histogram scene detection is highly specific (no false alarms on clean clips) and finds inserted footage reliably.")
        items.append("Robust (median/MAD) motion-spike detection over the whole video locates deleted segments that SSIM and histograms miss, with a low false-alarm rate.")
        items.append("Perceptual-hash repeat detection is not specific on moving footage and needs to be combined with motion information before its flags can be trusted.")
    return [("ul", items)]


# ======================================================================= render
def resolve_refs(blocks):
    nums, f, tb = {}, 0, 0
    for b in blocks:
        if b[0] == "fig": f += 1; nums[f"fig:{b[1]}"] = f"Figure {f}"
        elif b[0] == "table": tb += 1; nums[f"tab:{b[1]}"] = f"Table {tb}"
    return nums


def expand(blocks):
    out = []
    for b in blocks:
        if b[0] == "casia_discussion": out += casia_discussion()
        elif b[0] == "inferences": out += inferences()
        else: out.append(b)
    return out


def sub(text, nums):
    def rep(m):
        key = m.group(1)
        if key not in nums: raise KeyError(f"Unknown reference {{{key}}}")
        return nums[key]
    return re.sub(r"\{((?:fig|tab):\w+)\}", rep, text)


def front_matter(d: Doc):
    # Cover page (layout follows the template's specimen).
    d.add(para(run(TITLE, bold=True, size=18), jc="center", before=1100, after=600, line=300))
    d.add(para(run("Image and Video Processing Project Report", bold=True, size=15), jc="center", before=120, after=60))
    d.add(para(run("End-Semester Evaluation", bold=True, size=15), jc="center", before=0, after=900))
    d.add(para(run("Submitted by:", bold=True, size=14), jc="center", before=0, after=240))
    for roll, name in STUDENTS:
        d.add(para(run(f"({roll})  {name.upper()}", bold=True, size=12), jc="center", before=0, after=120))
    d.add(para(run("MCA Second Year", bold=True, size=14), jc="center", before=480, after=900))
    d.add(para(run("Under the Mentorship of", size=14), jc="center", before=0, after=120))
    d.add(para(run(MENTOR, size=14, bold=True), jc="center", before=0, after=700))
    d.image(FIG / "thapar_logo.jpeg", 2.4)
    d.add(para(run("Computer Science and Engineering Department", bold=True, size=14), jc="center", before=360, after=0))
    d.add(para(run("Thapar Institute of Engineering and Technology, Patiala", bold=True, size=14), jc="center", before=0, after=0))
    d.add(para(run(MONTH_YEAR, bold=True, size=14), jc="center", before=0, after=0))
    d.section_break(None, None, None)                       # cover: no page number

    d.heading("ABSTRACT", 1, in_toc=False)
    for text in ABSTRACT: d.p(text)
    d.heading("TABLE OF CONTENTS", 1, page_break=True, in_toc=False)
    d.toc('TOC \\o "1-3" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")
    d.heading("LIST OF TABLES", 1, page_break=True, in_toc=False)
    d.toc('TOC \\h \\z \\c "Table"', "Right-click and choose Update Field to build the list of tables.")
    d.heading("LIST OF FIGURES", 1, page_break=True, in_toc=False)
    d.toc('TOC \\h \\z \\c "Figure"', "Right-click and choose Update Field to build the list of figures.")
    d.heading("LIST OF ABBREVIATIONS", 1, page_break=True, in_toc=False)
    for abbr, full in ABBREVIATIONS:
        d.add(para(run(abbr, bold=True, size=12) + "<w:r><w:tab/></w:r>" + run(full, size=12), tabs=[("left", "none", 2200)], before=0, after=100))
    d.section_break("rId7", "lowerRoman", 1)                # front matter: i, ii, iii …


def build():
    d = Doc(BUILD / "template.docx")
    front_matter(d)
    blocks = expand(B)
    nums = resolve_refs(blocks)
    first_chapter = True
    for b in blocks:
        kind = b[0]
        if kind == "h1":
            d.heading(b[1], 1, page_break=not first_chapter); first_chapter = False
        elif kind == "h2": d.heading(b[1], 2)
        elif kind == "h3": d.heading(b[1], 3)
        elif kind == "p": d.p(sub(b[1], nums))
        elif kind == "ul": d.bullets([sub(x, nums) for x in b[1]])
        elif kind == "ol": d.bullets([sub(x, nums) for x in b[1]], numbered=True)
        elif kind == "table": d.table(sub(b[2], nums), b[3], [[sub(str(c), nums) for c in r] for r in b[4]], b[5], align=b[6])
        elif kind == "fig":
            path = (FIG / b[2]).resolve()
            if path.exists(): d.image(path, b[3], b[4])
            else:
                d.add(para(run(f"[Screenshot pending: {path.name}]", italic=True, size=11), jc="center", before=200, after=0, keep_next=True))
                d.caption("Figure", b[4])
        elif kind == "pb": d.page_break()

    d.heading("APPENDIX A: REFERENCES", 1, page_break=True)
    for i, ref in enumerate(REFERENCES, 1):
        d.add(para(run(f"[{i}]", size=12) + "<w:r><w:tab/></w:r>" + rich(ref, size=12), jc="both", tabs=[("left", "none", 720)],
                   ind_left=720, ind_hanging=720, before=0, after=140, line=300))
    final = sect_pr("rId7", "decimal", 1)                    # main text: 1, 2, 3 …
    d.save(OUT, final, {"title": TITLE, "author": ", ".join(n for _, n in STUDENTS), "date": "2026-12-01T00:00:00Z"})
    print(f"Wrote {OUT} ({d.table_no} tables, {d.figure_no} figures, CASIA {'included' if CASIA else 'pending'})")


if __name__ == "__main__":
    build()
