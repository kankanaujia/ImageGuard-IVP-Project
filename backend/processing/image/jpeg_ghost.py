"""JPEG ghost analysis for spliced regions (after H. Farid, "Exposing digital forgeries from
JPEG ghosts", IEEE TIFS 2009).

When part of an image was cut from another JPEG saved at quality q1 and the result was saved
at q2, re-saving the whole image at quality q1 changes that part very little: it leaves a
"ghost", a dip in the recompression difference that the rest of the image does not share.
For every quality in QUALITIES the image is re-saved, the squared difference is averaged per
16x16 block and normalised per block across qualities; a block's score is how far it dips
below the image's typical block at any one quality. Scores become robust z-values across the
image, and the map highlights blocks that "remember" a different compression.
"""
from __future__ import annotations
import io
from pathlib import Path
import numpy as np
from PIL import Image
from .heatmap import block_reduce, robust_z, save_overlay

QUALITIES = list(range(50, 100, 5))
Z_THRESHOLD = 3.5


def ghost_block_scores(rgb: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """Per-block ghost strength and the quality at which it appears."""
    original = np.asarray(rgb, dtype=np.float32)
    diffs = []
    for q in QUALITIES:
        buf = io.BytesIO(); rgb.save(buf, "JPEG", quality=q)
        with Image.open(buf) as resaved:
            again = np.asarray(resaved.convert("RGB"), dtype=np.float32)
        diffs.append(block_reduce(((original - again) ** 2).mean(axis=2)))
    d = np.stack(diffs)                                           # (qualities, rows, cols)
    lo, hi = d.min(axis=0), d.max(axis=0)
    norm = (d - lo) / np.maximum(hi - lo, 1e-6)                    # 0 = this block's best-matching quality
    typical = np.median(norm.reshape(len(QUALITIES), -1), axis=1)[:, None, None]
    dip = typical - norm                                           # how far each block dips below the typical block
    return dip.max(axis=0), np.array(QUALITIES)[dip.argmax(axis=0)]


def analyze_ghost(source: Path, map_output: Path) -> dict:
    with Image.open(source) as opened:
        rgb = opened.convert("RGB")
    strength, quality = ghost_block_scores(rgb)
    z = robust_z(strength)
    save_overlay(np.asarray(rgb)[:, :, ::-1], np.clip(z, 0, None), map_output, vmax=2 * Z_THRESHOLD)
    unusual = z >= Z_THRESHOLD
    ghost_q = int(np.bincount(quality[unusual]).argmax()) if unusual.any() else None
    return {"map_visualization": map_output.name, "block_z_max": round(float(z.max()), 2),
            "unusual_block_share": round(float(unusual.mean()), 4), "ghost_quality": ghost_q, "qualities": [QUALITIES[0], QUALITIES[-1]],
            "note": "Bright blocks match an earlier JPEG compression that the rest of the image does not share, as pasted content often does. "
                    "Smooth or saturated areas can also stand out; compare with the photo."}
