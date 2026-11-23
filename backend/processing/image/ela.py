"""Error level analysis: global visualisation plus a localised block map.

The global peak describes how the whole file responds to recompression (largely its save
history). The block map compares each 16x16 block with the rest of the same image, so it
points at regions whose compression history differs from their surroundings.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from .heatmap import block_reduce, robust_z, save_overlay

Z_THRESHOLD = 3.5   # blocks this many robust deviations above the image median are "unusual"


def ela_difference(original: Image.Image, working: Path, quality: int) -> Image.Image:
    original.save(working, "JPEG", quality=quality)
    with Image.open(working) as reopened:
        recompressed = reopened.convert("RGB")
    working.unlink(missing_ok=True)
    return ImageChops.difference(original, recompressed)


def ela_block_z(diff: Image.Image) -> np.ndarray:
    """Robust z-score of the mean ELA difference in each block (per-pixel max over RGB)."""
    values = np.asarray(diff, dtype=np.float32).max(axis=2)
    return robust_z(block_reduce(values))


def analyze_ela(source: Path, output: Path, quality: int = 90, map_output: Path | None = None) -> dict:
    if not 1 <= quality <= 100:
        raise ValueError("quality must be between 1 and 100")
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        original = opened.convert("RGB")
    diff = ela_difference(original, output.with_suffix(".recompressed.jpg"), quality)
    extrema = diff.getextrema()
    peak = max(channel[1] for channel in extrema) or 1
    ImageEnhance.Brightness(diff).enhance(255.0 / peak).save(output, "PNG")
    result = {"visualization": output.name, "quality": quality, "difference_peak": peak, "channel_ranges": extrema,
              "note": "Non-JPEG inputs are converted to JPEG for comparison; conversion artifacts affect interpretation."}
    if map_output is not None:
        z = ela_block_z(diff)
        bgr = np.asarray(original)[:, :, ::-1]
        save_overlay(bgr, np.clip(z, 0, None), map_output, vmax=2 * Z_THRESHOLD)
        result.update({"map_visualization": map_output.name, "block_z_max": round(float(z.max()), 2),
                       "unusual_block_share": round(float((z >= Z_THRESHOLD).mean()), 4), "block_size": 16,
                       "map_note": "Bright areas recompress differently from the rest of this image. Edges and fine texture also do, so compare with the photo."})
    return result
