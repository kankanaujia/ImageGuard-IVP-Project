"""Create a compact, observation-focused PDF investigation report."""
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage
from reportlab.lib.utils import ImageReader

def generate_report(record, result: dict, output: Path, artifact_dir: Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=letter)
    styles = getSampleStyleSheet(); story = [Paragraph("ImageGuard | Forensic Observation Report", styles["Title"]), Spacer(1,12)]
    fields = [("Investigation ID", record.id), ("Original file", record.original_name), ("Media type", record.media_type),
              ("File size", f"{record.size_bytes:,} bytes"), ("SHA-256", record.sha256), ("Created", str(record.created_at))]
    for label,value in fields: story.append(Paragraph(f"<b>{label}:</b> {value}", styles["BodyText"]))
    story += [Spacer(1,12), Paragraph("Findings", styles["Heading2"])]
    story.append(Paragraph(result.get("indicator_summary",{}).get("statement", "Observations are not conclusions."), styles["BodyText"]))
    for name, value in result.get("algorithms", result).items():
        story.append(Spacer(1,6)); story.append(Paragraph(f"<b>{name.replace('_',' ').title()}</b>", styles["Heading3"]))
        body = json.dumps(value, ensure_ascii=False, default=str)
        story.append(Paragraph(body.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"), styles["BodyText"]))
        visual = value.get("visualization") if isinstance(value, dict) else None
        visual_path = artifact_dir / visual if artifact_dir and visual else None
        if visual_path and visual_path.is_file():
            try:
                reader = ImageReader(str(visual_path)); width, height = reader.getSize()
                scale = min(480 / width, 260 / height, 1)
                story += [Spacer(1,4), PDFImage(str(visual_path), width=width*scale, height=height*scale)]
            except Exception:
                pass
    story += [Spacer(1,12), Paragraph("Limitations", styles["Heading2"])]
    for note in result.get("limitations", []): story.append(Paragraph("• " + note, styles["BodyText"]))
    story.append(Spacer(1,10)); story.append(Paragraph("This report describes automated observations. It does not conclusively determine whether media is authentic or manipulated.", styles["Italic"]))
    doc.build(story)
