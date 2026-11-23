"""Readable, observation-focused PDF investigation reports (ReportLab).

Each check gets a short section: its key measurements in plain words, its visualisation(s)
and how to read it. Results from older versions (with fewer fields) are handled too.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as PDFImage, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK, MUTED, ACCENT, LIGHT = colors.HexColor("#16233A"), colors.HexColor("#5B6B82"), colors.HexColor("#C77D10"), colors.HexColor("#EEF1F5")
_base = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=INK, alignment=0, spaceAfter=2),
    "subtitle": ParagraphStyle("subtitle", parent=_base["Normal"], fontSize=10, textColor=MUTED, spaceAfter=10),
    "h2": ParagraphStyle("h2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=INK, spaceBefore=12, spaceAfter=4),
    "body": ParagraphStyle("body", parent=_base["BodyText"], fontSize=9.5, leading=13),
    "small": ParagraphStyle("small", parent=_base["BodyText"], fontSize=8.5, leading=11, textColor=MUTED),
    "cell": ParagraphStyle("cell", parent=_base["BodyText"], fontSize=8.5, leading=10.5),
    "callout": ParagraphStyle("callout", parent=_base["BodyText"], fontSize=10, leading=14, textColor=INK, backColor=LIGHT, borderPadding=6, spaceBefore=4, spaceAfter=8),
}
WIDTH = A4[0] - 36 * mm

CHECK_TEXT = {
    "ela": ("Error level analysis (ELA)", "Re-saves the image as JPEG (quality 90) and shows the per-pixel difference. The heat map compares each 16x16 block with the rest of the image; bright blocks recompress differently from their surroundings."),
    "orb": ("Copy-move detection (ORB + RANSAC)", "Matches ORB keypoints within the image and keeps groups that agree on one shift/rotation. Lines join matched points (green = source, red = copy)."),
    "noise": ("Noise consistency", "Estimates the local noise level of each block. Bright blocks have a noise level unlike the rest of the image, as pasted content from another source often does."),
    "compression": ("Compression history", "Reads the JPEG quantization tables, which record how the file was last saved."),
    "histogram": ("Colour histogram", "Pixel counts per brightness value; gaps or spikes suggest contrast or levels adjustments."),
    "metadata": ("Metadata (EXIF)", "Camera, software and date tags embedded in the file."),
    "frame_hashing": ("Repeated frames (perceptual hash)", "Neighbouring sampled frames that look nearly identical and show almost no motion between them (frozen or looped footage)."),
    "ssim": ("Frame similarity (SSIM)", "Structural similarity of each sampled frame to the previous one; sharp dips mark cuts or sudden changes."),
    "scene_detection": ("Scene changes (colour histogram)", "Large jumps in the colour distribution between neighbouring samples."),
    "optical_flow": ("Motion (optical flow)", "Dense motion between neighbouring samples; unusually large jumps are flagged as motion spikes."),
}


# The built-in PDF fonts only cover the WinAnsi character set; swap the symbols they lack.
PLAIN = str.maketrans({"≈": "~", "•": "-", "≥": ">=", "≤": "<=", "→": "->", "σ": "sd", "✓": "yes", "✗": "no"})


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text.translate(PLAIN), S[style])


def kv_table(rows: list[tuple[str, str]], first: float = 0.34) -> Table:
    data = [[P(f"<b>{escape(str(k))}</b>", "cell"), P(escape(str(v)), "cell")] for k, v in rows]
    t = Table(data, colWidths=[WIDTH * first, WIDTH * (1 - first)])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D1DC")), ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def grid_table(header: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[P(f"<b>{escape(h)}</b>", "cell") for h in header]] + [[P(escape(str(c)), "cell") for c in r] for r in rows]
    t = Table(data, colWidths=[WIDTH * w for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D1DC")), ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def picture(path: Path | None, max_w: float, max_h: float):
    if not path or not path.is_file(): return None
    try:
        w, h = ImageReader(str(path)).getSize()
    except Exception:
        return None
    scale = min(max_w / w, max_h / h)  # fit inside the box, keeping the aspect ratio
    return PDFImage(str(path), width=w * scale, height=h * scale)


def pictures_row(paths: list[Path | None], captions: list[str], max_h: float = 62 * mm):
    pics = [(picture(p, WIDTH / len(paths) - 4 * mm, max_h), c) for p, c in zip(paths, captions)]
    pics = [(p, c) for p, c in pics if p is not None]
    if not pics: return None
    t = Table([[p for p, _ in pics], [P(escape(c), "small") for _, c in pics]], colWidths=[WIDTH / len(pics)] * len(pics))
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def fmt(v, digits=2):
    return "-" if v is None else (f"{v:.{digits}f}" if isinstance(v, float) else str(v))


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def image_sections(result: dict, artifacts: Path | None, story: list) -> None:
    alg = result.get("algorithms", {})
    art = lambda name: (artifacts / name) if artifacts and name else None
    for key in ("ela", "orb", "noise", "compression", "histogram", "metadata"):
        v = alg.get(key)
        if not v: continue
        title, what = CHECK_TEXT[key]
        block = [P(title, "h2"), P(what)]
        if v.get("status") == "error":
            block.append(P(f"This check could not run: {escape(v.get('error', ''))}", "small")); story.append(KeepTogether(block)); continue
        rows: list[tuple[str, str]] = []
        visuals = None
        if key == "ela":
            rows = [("Recompression quality", fmt(v.get("quality"))), ("Peak difference (whole image)", f"{fmt(v.get('difference_peak'))} / 255")]
            if "block_z_max" in v:
                rows += [("Most unusual block", f"{fmt(v['block_z_max'])} robust deviations above the image median"),
                         ("Share of unusual blocks", f"{100 * v['unusual_block_share']:.1f}%")]
            visuals = pictures_row([art(v.get("visualization")), art(v.get("map_visualization"))], ["ELA difference", "ELA block heat map"])
        elif key == "orb":
            rows = [("Keypoints", fmt(v.get("keypoints"))), ("Raw self-matches", fmt(v.get("raw_candidate_matches"))),
                    ("Largest consistent group", fmt(v.get("geometrically_consistent_matches")))]
            if "copy_shift_px" in v: rows.append(("Distance from source to copy", f"{fmt(v['copy_shift_px'], 0)} px"))
            flagged = v.get("flagged", v.get("candidate_matches", 0) >= 4)
            rows.append(("Result", "Flagged for review: a group of matches consistent with a copied region" if flagged else "Not flagged"))
            visuals = pictures_row([art(v.get("visualization"))], ["Matched keypoints"], max_h=80 * mm)
        elif key == "noise":
            if "block_z_max_abs" in v:
                rows = [("Most unusual block", f"{fmt(v['block_z_max_abs'])} robust deviations from the image median"),
                        ("Share of unusual blocks", f"{100 * v['unusual_block_share']:.1f}%")]
            rows += [("Residual mean / std", f"{fmt(v.get('residual_mean'))} / {fmt(v.get('residual_std'))}")]
            visuals = pictures_row([art(v.get("visualization")), art(v.get("map_visualization"))], ["Noise residual", "Noise consistency heat map"])
        elif key == "compression":
            if v.get("is_jpeg") and "estimated_quality" in v:
                rows = [("Estimated JPEG quality", f"≈ {fmt(v['estimated_quality'], 0)}"), ("Standard IJG tables", "Yes" if v.get("standard_ijg_tables") else "No"),
                        ("Chroma subsampling", fmt(v.get("chroma_subsampling"))), ("Progressive", "Yes" if v.get("progressive") else "No")]
            for o in v.get("observations", []): block.append(P("• " + escape(o), "small"))
        elif key == "histogram":
            rows = [("Grey mean / spread", f"{fmt(v.get('grayscale_mean'), 1)} / {fmt(v.get('grayscale_std'), 1)}")]
            visuals = pictures_row([art(v.get("visualization"))], ["RGB histogram"], max_h=55 * mm)
        elif key == "metadata":
            rows = [("Format / size", f"{v.get('format')} · {v.get('width')} x {v.get('height')} · {v.get('mode')}")]
            exif = v.get("exif") or {}
            rows += [(k, str(val)[:120]) for k, val in list(exif.items())[:14]]
            for o in v.get("observations", []): block.append(P("• " + escape(o), "small"))
        if rows: block.insert(2, kv_table(rows))
        if visuals is not None: block += [Spacer(1, 4), visuals]
        note = v.get("map_note") or v.get("note") or v.get("interpretation")
        if note: block.append(P("How to read it: " + escape(note), "small"))
        story.append(KeepTogether(block))


def video_sections(result: dict, artifacts: Path | None, story: list) -> None:
    video = result.get("video", {})
    story.append(kv_table([("Duration", mmss(video.get("duration", 0))), ("Frame rate", f"{fmt(video.get('fps'))} fps"),
                           ("Resolution", f"{video.get('width')} x {video.get('height')}"), ("Sampled frames", f"{len(result.get('frames', []))} (one every {video.get('sample_interval_seconds', 1)} s)")]))
    events = []
    for c in result.get("scene_detection", {}).get("candidates", []):
        events.append((c["timestamp"], "Scene change", f"histogram distance {c['histogram_distance']:.2f}"))
    for p in result.get("frame_hashing", {}).get("pairs", []):
        extra = f", motion {p['mean_motion']:.2f} px" if "mean_motion" in p else ""
        events.append((p["timestamp"], "Repeated frame", f"matches {mmss(p['previous_timestamp'])}, hash distance {p['hamming_distance']}{extra}"))
    for s in result.get("optical_flow", {}).get("spikes", []) or []:
        events.append((s["timestamp"], "Motion spike", f"mean motion {s['mean_motion']:.1f} px"))
    story.append(P("Flagged moments", "h2"))
    story.append(grid_table(["Time", "Type", "Detail"], [[mmss(t), k, d] for t, k, d in sorted(events)], [0.14, 0.22, 0.64]) if events
                 else P("No scene changes, repeated frames or motion spikes were flagged among the sampled frames."))
    art = lambda name: (artifacts / name) if artifacts and name else None
    for key in ("ssim", "scene_detection", "frame_hashing", "optical_flow"):
        v = result.get(key)
        if not v: continue
        title, what = CHECK_TEXT[key]
        block = [P(title, "h2"), P(what)]
        if v.get("status") == "error":
            block.append(P(f"This check could not run: {escape(v.get('error', ''))}", "small")); story.append(KeepTogether(block)); continue
        rows, visuals = [], None
        if key == "ssim":
            scores = v.get("scores") or []
            if scores: rows = [("Mean / lowest SSIM", f"{sum(scores) / len(scores):.3f} / {min(scores):.3f}")]
            visuals = pictures_row([art(v.get("visualization"))], ["SSIM between neighbouring samples"], max_h=55 * mm)
        elif key == "scene_detection":
            rows = [("Scene-change candidates", str(len(v.get("candidates", []))))]
        elif key == "frame_hashing":
            rows = [("Confirmed repeats", str(len(v.get("pairs", []))))]
            if "hash_only_pairs" in v: rows.append(("Similar by hash only (before motion check)", str(v["hash_only_pairs"])))
        elif key == "optical_flow":
            rows = [("Mean / highest motion", f"{fmt(v.get('mean_motion_magnitude'), 1)} / {fmt(v.get('peak_mean_magnitude', v.get('p95_motion_magnitude')), 1)} px")]
            if v.get("spikes") is not None: rows.append(("Motion spikes", str(len(v["spikes"]))))
            visuals = pictures_row([art(v.get("visualization"))], ["Motion of the highest-motion pair (colour = direction, brightness = speed)"], max_h=55 * mm)
        if rows: block.append(kv_table(rows))
        if visuals is not None: block += [Spacer(1, 4), visuals]
        if v.get("note"): block.append(P("How to read it: " + escape(v["note"]), "small"))
        story.append(KeepTogether(block))


def generate_report(record, result: dict, output: Path, artifact_dir: Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"ImageGuard report - {record.original_name}", author="ImageGuard")
    created = record.created_at.strftime("%d %b %Y, %H:%M UTC") if isinstance(record.created_at, datetime) else str(record.created_at)
    story = [P("ImageGuard forensic observation report", "title"),
             P(f"{escape(record.original_name)} · {record.media_type} · generated {datetime.now().strftime('%d %b %Y %H:%M')}", "subtitle"),
             kv_table([("Investigation ID", record.id), ("Original file", record.original_name), ("Media type", record.media_type),
                       ("File size", f"{record.size_bytes:,} bytes"), ("SHA-256 at intake", record.sha256), ("Analysed", created)])]
    summary = result.get("indicator_summary", {})
    count = summary.get("candidate_indicators")
    story += [Spacer(1, 6), P(f"<b>Candidate indicators: {count if count is not None else '-'}</b>. " + escape(summary.get("statement", "Observations are not conclusions.")), "callout")]
    if record.media_type == "image":
        original = result.get("original_image", {})
        story.append(P(f"Image: {original.get('format')} · {original.get('width')} x {original.get('height')} · {original.get('mode')} · processed in {result.get('processing_seconds')} s", "small"))
        image_sections(result, artifact_dir, story)
    else:
        story.append(P(f"Processed in {result.get('processing_seconds')} s", "small"))
        video_sections(result, artifact_dir, story)
    notes = getattr(record, "notes", "") or ""
    if notes:
        story += [P("Investigator's notes", "h2"), *[P(escape(line) or "&nbsp;") for line in notes.splitlines()]]
    story += [P("Limitations", "h2"), *[P("• " + escape(n)) for n in result.get("limitations", [])],
              Spacer(1, 8), P("This report describes automated observations for human review. It does not determine whether the media is authentic or manipulated.", "small")]

    def footer(canvas, doc_):
        canvas.saveState(); canvas.setFont("Helvetica", 7.5); canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 9 * mm, f"ImageGuard · {record.id}")
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {doc_.page}"); canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
