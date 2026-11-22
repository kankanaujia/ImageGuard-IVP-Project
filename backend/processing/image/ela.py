"""JPEG recompression ELA visualization; output is an indicator, not a verdict."""
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance

def analyze_ela(source: Path, output: Path, quality: int = 90) -> dict:
    if not 1 <= quality <= 100:
        raise ValueError("quality must be between 1 and 100")
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        original = opened.convert("RGB")
        working = output.with_suffix(".recompressed.jpg")
        original.save(working, "JPEG", quality=quality)
        recompressed = Image.open(working).convert("RGB")
        diff = ImageChops.difference(original, recompressed)
        extrema = diff.getextrema()
        peak = max(channel[1] for channel in extrema) or 1
        amplified = ImageEnhance.Brightness(diff).enhance(255.0 / peak)
        amplified.save(output, "PNG")
        mean = sum(sum(channel) / 2 for channel in extrema) / 3
        working.unlink(missing_ok=True)
    return {"visualization": output.name, "quality": quality, "difference_peak": peak,
            "channel_ranges": extrema, "note": "Non-JPEG inputs are converted to JPEG for comparison; conversion artifacts affect interpretation."}
