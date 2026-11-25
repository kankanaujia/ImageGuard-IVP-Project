"""Draw the report's design diagrams with matplotlib (no external diagram tools needed).

Run from the project root:  backend\\.venv\\Scripts\\python.exe documentation\\build\\diagrams.py
Writes PNGs to documentation/build/figures/.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "DejaVu Sans"
C = {"ui": "#dbeafe", "api": "#e0e7ff", "proc": "#dcfce7", "img": "#fef9c3", "vid": "#fde2e4", "store": "#ede9fe", "grey": "#f1f5f9", "edge": "#334155"}


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10); ax.set_ylim(0, h * 10); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, colour="grey", size=9, bold=False, style="round,pad=0.4,rounding_size=1.2"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=C.get(colour, colour), ec=C["edge"], lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, family=FONT, weight="bold" if bold else "normal", wrap=True)
    return (x, y, w, h)


def arrow(ax, a, b, text="", both=False, rad=0.0, size=7.5):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>", mutation_scale=11, lw=1, color=C["edge"],
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 1.2, text, ha="center", va="bottom", fontsize=size, family=FONT, color="#475569",
                bbox=dict(fc="white", ec="none", pad=0.6))


def group(ax, x, y, w, h, title, colour="#f8fafc", where="top-left"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.5", fc=colour, ec="#94a3b8", lw=0.9, ls="--"))
    tx = x + w - 1.5 if where.endswith("right") else x + 1.5
    ty, va = (y + h - 1.2, "top") if where.startswith("top") else (y + 0.8, "bottom")
    ax.text(tx, ty, title, ha="right" if where.endswith("right") else "left", va=va, fontsize=8.5, family=FONT, weight="bold", color="#475569")


def save(fig, name):
    fig.tight_layout(pad=0.2); fig.savefig(OUT / f"{name}.png", dpi=200); plt.close(fig)


def mid(b, side):
    x, y, w, h = b
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]


# ------------------------------------------------------------------ architecture
def architecture():
    fig, ax = canvas(10, 6.4)
    group(ax, 1, 46, 98, 16, "Presentation layer (Next.js / React, browser)")
    pages = ["Sign in /\ncreate account", "Overview\ndashboard", "New\ninvestigation", "Image\nforensics", "Video\nforensics", "Reports &\nhistory"]
    pb = [box(ax, 3 + i * 16, 48, 14, 9, p, "ui", 8) for i, p in enumerate(pages)]
    group(ax, 1, 26, 98, 17, "Application layer (FastAPI, Python)", where="top-right")
    api = box(ax, 4, 28, 26, 9.5, "REST API + accounts\n/api/auth · /api/*/analyze\nsession cookie, own cases only", "api", 8)
    val = box(ax, 35, 28, 26, 9.5, "Validation & integrity\nextension · size · content\nSHA-256 at intake", "api", 8)
    eng = box(ax, 66, 28, 30, 9.5, "Background analysis jobs\nchecks run independently,\nprogress reported per stage", "proc", 8)
    group(ax, 1, 3, 62, 20, "Processing layer (OpenCV, scikit-image, Pillow, ImageHash)", where="bottom-left")
    box(ax, 4, 8, 27, 12, "Image checks\nELA + heat map · ORB copy-move\nJPEG ghost map · compression\nhistory · EXIF", "img", 8)
    box(ax, 34, 8, 27, 12, "Video checks\nframe sampling · pHash + motion\nSSIM · scene histogram\nFarnebäck optical flow", "vid", 8)
    group(ax, 66, 3, 33, 20, "Storage layer", where="bottom-right")
    box(ax, 68, 14, 14, 6.5, "SQLite: users,\nsessions, cases", "store", 7.5)
    box(ax, 84, 14, 13, 6.5, "uploads/\n(originals)", "store", 7.5)
    box(ax, 68, 6.5, 14, 6.5, "outputs/\nvisualizations", "store", 7.5)
    box(ax, 84, 6.5, 13, 6.5, "reports/\nPDF (ReportLab)", "store", 7.5)
    arrow(ax, (17, 47.5), (17, 37.9), "HTTP / JSON", both=True)
    arrow(ax, mid(api, "r"), mid(val, "l")); arrow(ax, mid(val, "r"), mid(eng, "l"))
    arrow(ax, (72, 28), (18, 20.4)); arrow(ax, (76, 28), (48, 20.4))
    arrow(ax, (88, 28), (85, 21), "results, files")
    save(fig, "fig_architecture")


# ------------------------------------------------------------------ workflow
def workflow():
    fig, ax = canvas(10, 10)
    steps = [
        ("Investigator signs in, then selects an image or video", "ui"),
        ("Client check: extension and 100 MB limit", "ui"),
        ("POST multipart upload to /api/{image|video}/analyze", "api"),
        ("Stream to disk under a random name (UUID); enforce size", "api"),
        ("Validate content (Pillow decode / OpenCV open)", "api"),
        ("Compute SHA-256 of the stored original", "api"),
        ("Background job runs the checks; progress reported per stage", "proc"),
        ("Save result JSON in SQLite under the investigator's account", "store"),
        ("Generate PDF report (retried on download if it fails)", "store"),
        ("UI polls the job, then shows metrics, maps, charts and notes", "ui"),
    ]
    y = 92; boxes = []
    for i, (t, c) in enumerate(steps):
        boxes.append(box(ax, 12, y, 60, 6.2, f"{i + 1}. {t}", c, 8.5)); y -= 9
    for a, b in zip(boxes, boxes[1:]): arrow(ax, mid(a, "b"), mid(b, "t"))
    for i, reason in ((1, "unsupported type / too large"), (3, "> 100 MB → 413"), (4, "not a real image/video → 415")):
        bx = boxes[i]; ax.text(76, bx[1] + 3.1, f"✗ {reason}", fontsize=7.5, family=FONT, color="#b91c1c", va="center")
        arrow(ax, mid(bx, "r"), (75.5, bx[1] + 3.1))
    ax.text(76, 12, "On any rejection the stored\nfile and outputs are deleted", fontsize=7.5, family=FONT, color="#b91c1c")
    save(fig, "fig_workflow")


# ------------------------------------------------------------------ image + video pipelines
def pipelines():
    fig, ax = canvas(10, 5.2)
    src = box(ax, 2, 22, 13, 9, "Image\n(JPG, PNG,\nTIFF, BMP, WebP)", "ui", 8)
    checks = [("ELA at JPEG Q90 + block heat map\n(robust z of 16×16 block means)", "img"),
              ("ORB self-match, oriented + de-duplicated,\nrepeated RANSAC; flag: ≥5 matches, ≥40 px", "img"),
              ("JPEG ghosts: re-save at Q50–95, per-block\ndip below typical block, robust z", "img"),
              ("Compression: quantization tables →\nquality, IJG vs custom tables", "img"),
              ("EXIF tags (Pillow)", "img")]
    cb = [box(ax, 24, 43 - i * 9.4, 44, 7.2, t, c, 7.4) for i, (t, c) in enumerate(checks)]
    out = box(ax, 76, 20, 22, 13, "Per-check result\n(status, metrics,\nvisualization, caveat)\n+ indicator summary", "proc", 7.5)
    for b in cb:
        arrow(ax, mid(src, "r"), mid(b, "l")); arrow(ax, mid(b, "r"), mid(out, "l"))
    save(fig, "fig_image_pipeline")

    fig, ax = canvas(10, 5.2)
    src = box(ax, 1, 22, 11, 9, "Video\n(MP4, AVI,\nMOV, MKV)", "ui", 8)
    smp = box(ax, 15, 21, 15, 11, "Frame sampling\n1 frame / s\n(max 180 frames)", "vid", 8)
    checks = ["pHash distance ≤ 4 AND optical-flow\nmotion ≤ 1 px → repeat",
              "SSIM between neighbours\n(scikit-image)",
              "8×8×8 colour histogram,\nBhattacharyya ≥ 0.55 → scene cut",
              "Farnebäck dense flow per pair\n(480 px), spikes: median + 3.5·MAD"]
    cb = [box(ax, 35, 41 - i * 11, 36, 8.6, t, "vid", 7.5) for i, t in enumerate(checks)]
    out = box(ax, 77, 19, 21, 15, "Flagged moments\n(time, type, detail)\nSSIM & motion timelines\nper-pair flow images", "proc", 7.5)
    arrow(ax, mid(src, "r"), mid(smp, "l"))
    for b in cb:
        arrow(ax, mid(smp, "r"), mid(b, "l")); arrow(ax, mid(b, "r"), mid(out, "l"))
    save(fig, "fig_video_pipeline")


# ------------------------------------------------------------------ deployment
def deployment():
    fig, ax = canvas(10, 5)
    group(ax, 1, 2, 98, 46, "Investigator's computer (Windows 11, single machine, no internet needed after install)", "#f8fafc")
    br = box(ax, 4, 26, 22, 14, "Web browser\nhttp://localhost:3000", "ui", 8.5)
    group(ax, 30, 22, 26, 22, "Node.js 20+", "#eff6ff")
    nx = box(ax, 33, 26, 20, 12, "Next.js server\n(port 3000)\npages, scripts", "ui", 8)
    group(ax, 60, 6, 37, 38, "Python 3.11+ virtual environment", "#f0fdf4")
    uv = box(ax, 63, 27, 31, 11, "Uvicorn + FastAPI\n(127.0.0.1:8000)\nbackend.main:app", "api", 8)
    db = box(ax, 63, 10, 14, 11, "imageguard\n.db (SQLite)", "store", 7.5)
    fs = box(ax, 79, 10, 15, 11, "uploads/ outputs/\nreports/", "store", 7.5)
    arrow(ax, mid(br, "r"), mid(nx, "l"), "page load")
    arrow(ax, (15, 26), (70, 27), rad=0.18)
    ax.text(42, 17.5, "REST calls from the browser (CORS allows localhost:3000)", ha="center", fontsize=7.5, family=FONT, color="#475569")
    arrow(ax, (70, 27), (70, 21)); arrow(ax, (86, 27), (86, 21))
    save(fig, "fig_deployment")


# ------------------------------------------------------------------ use cases
def use_cases():
    fig, ax = canvas(9, 6)
    ax.add_patch(FancyBboxPatch((24, 2), 62, 55, boxstyle="round,pad=0.3,rounding_size=2", fc="#f8fafc", ec="#94a3b8"))
    ax.text(55, 55, "ImageGuard", ha="center", fontsize=10, family=FONT, weight="bold")
    # stick figure
    ax.add_patch(Ellipse((10, 36), 4, 4, fc="white", ec=C["edge"]))
    ax.plot([10, 10], [34, 25], color=C["edge"]); ax.plot([5, 15], [31, 31], color=C["edge"])
    ax.plot([10, 6], [25, 18], color=C["edge"]); ax.plot([10, 14], [25, 18], color=C["edge"])
    ax.text(10, 14, "Investigator", ha="center", fontsize=9, family=FONT)
    cases = ["Sign in / create an account", "Upload image / video evidence", "View per-check analysis", "Compare original with visualizations",
             "Inspect video timeline & frames", "Verify evidence integrity (SHA-256)", "Download PDF report", "Browse investigation history"]
    for i, c in enumerate(cases):
        y = 49 - i * 5.9
        ax.add_patch(Ellipse((58, y), 46, 4.9, fc=C["ui"], ec=C["edge"]))
        ax.text(58, y, c, ha="center", va="center", fontsize=8.2, family=FONT)
        ax.plot([16, 35], [28, y], color="#64748b", lw=0.8)
    save(fig, "fig_use_cases")


# ------------------------------------------------------------------ data model
def data_model():
    fig, ax = canvas(9, 4.6)
    fields = ["id : UUID (PK)", "media_type : image | video", "original_name : text", "stored_name : UUID + extension",
              "mime_type : text", "size_bytes : integer", "sha256 : 64 hex chars", "created_at : UTC timestamp", "result_json : full analysis (JSON)", "notes : investigator's notes", "owner_id : FK → User"]
    box(ax, 4, 41, 34, 4.5, "Investigation (SQLite table)", "api", 9, True, "square,pad=0.2")
    for i, f in enumerate(fields):
        box(ax, 4, 37 - i * 3.3, 34, 3.3, f, "white", 7.4, style="square,pad=0.2")
    notes = [("uploads/{stored_name}", "original evidence, never modified"), ("outputs/{id}/", "ela.png, ela_map.png, orb.png, ghost_map.png,\nssim.png, flow.png, frames/frame_*.jpg, frames/flow_*.jpg"),
             ("reports/{id}-v2.pdf", "generated PDF report")]
    for i, (k, v) in enumerate(notes):
        b = box(ax, 45, 22.5 - i * 9.2, 43, 7.2, f"{k}\n{v}", "store", 7.0)
        arrow(ax, (38.4, 22 - i * 6), mid(b, "l"))
    box(ax, 45, 41, 20, 4.5, "User", "api", 8.5, True, "square,pad=0.2")
    box(ax, 45, 33, 20, 8, "id (PK) · username\npassword_hash (PBKDF2)\nis_admin · created_at", "white", 7.0, style="square,pad=0.2")
    box(ax, 68, 41, 20, 4.5, "Session", "api", 8.5, True, "square,pad=0.2")
    box(ax, 68, 33, 20, 8, "token_hash (PK, SHA-256)\nuser_id → User\nexpires_at (7 days)", "white", 7.0, style="square,pad=0.2")
    save(fig, "fig_data_model")


# ------------------------------------------------------------------ WBS
def wbs():
    fig, ax = canvas(10, 5.4)
    root = box(ax, 38, 44, 24, 7, "ImageGuard", "api", 10, True)
    branches = [("1 Research", ["1.1 Literature survey", "1.2 Technique selection", "1.3 Dataset selection"]),
                ("2 Backend", ["2.1 API, validation, accounts", "2.2 Image checks", "2.3 Video checks", "2.4 Storage & PDF"]),
                ("3 Frontend", ["3.1 Upload flow", "3.2 Analysis pages", "3.3 Reports & history"]),
                ("4 Evaluation", ["4.1 Unit tests", "4.2 CASIA v2.0 run", "4.3 Video benchmark"]),
                ("5 Documentation", ["5.1 Report", "5.2 Presentation"])]
    for i, (name, kids) in enumerate(branches):
        x = 1 + i * 20
        b = box(ax, x, 32, 18, 6, name, "proc", 8.5, True)
        arrow(ax, mid(root, "b"), mid(b, "t"))
        for j, k in enumerate(kids):
            kb = box(ax, x + 1.5, 24 - j * 6.4, 16, 4.8, k, "white", 7.5)
            ax.plot([x + 0.8, x + 0.8, x + 1.5], [32, kb[1] + 2.4, kb[1] + 2.4], color="#64748b", lw=0.8)
    save(fig, "fig_wbs")


# ------------------------------------------------------------------ Gantt
def gantt():
    import datetime as dt
    tasks = [("Problem study & literature survey", "2026-08-03", "2026-08-30", "1"),
             ("Requirements & design", "2026-08-24", "2026-09-13", "1"),
             ("Backend: API, storage, integrity", "2026-09-07", "2026-10-04", "2"),
             ("Image forensic checks", "2026-09-21", "2026-10-18", "2"),
             ("Video forensic checks", "2026-10-05", "2026-11-01", "2"),
             ("Frontend pages", "2026-10-12", "2026-11-15", "3"),
             ("Testing & evaluation (CASIA, video)", "2026-11-02", "2026-11-25", "4"),
             ("Report & presentation", "2026-11-16", "2026-11-29", "5")]
    colours = {"1": "#93c5fd", "2": "#86efac", "3": "#fcd34d", "4": "#fca5a5", "5": "#c4b5fd"}
    fig, ax = plt.subplots(figsize=(10, 3.8))
    d = lambda s: dt.date.fromisoformat(s)
    for i, (name, a, b, g) in enumerate(reversed(tasks)):
        ax.barh(i, (d(b) - d(a)).days, left=d(a), color=colours[g], edgecolor="#334155", lw=0.6, height=0.6)
    ax.set_yticks(range(len(tasks))); ax.set_yticklabels([t[0] for t in reversed(tasks)], fontsize=8.5, family=FONT)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=0)); ax.grid(axis="x", which="both", color="#e2e8f0", lw=0.6)
    ax.set_axisbelow(True); ax.tick_params(axis="x", labelsize=8.5)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT / "fig_gantt.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    for f in (architecture, workflow, pipelines, deployment, use_cases, data_model, wbs, gantt):
        f()
    print("\n".join(sorted(p.name for p in OUT.glob("*.png"))))
