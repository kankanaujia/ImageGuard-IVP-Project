"""Noise residual summaries plus a localised noise-consistency map.

Local noise is estimated per 16x16 block with the robust wavelet estimator
sigma = median(|HH|) / 0.6745, where HH is the finest diagonal Haar detail band.
A pasted region from another camera or processing chain often has a noise level
that differs from the rest of the image, in either direction.
"""
from pathlib import Path
import cv2
import numpy as np
from .heatmap import block_reduce, robust_z, save_overlay

Z_THRESHOLD = 3.5


def haar_hh(gray: np.ndarray) -> np.ndarray:
    """Finest diagonal detail coefficients at half resolution."""
    g = gray[: gray.shape[0] // 2 * 2, : gray.shape[1] // 2 * 2].astype(np.float32)
    a, b, c, d = g[0::2, 0::2], g[0::2, 1::2], g[1::2, 0::2], g[1::2, 1::2]
    return (a - b - c + d) / 2


def noise_block_z(gray: np.ndarray) -> np.ndarray:
    """Robust z of log local noise level per 16x16 image block (8x8 in the half-resolution HH band)."""
    hh = np.abs(haar_hh(gray))
    sigma = block_reduce(hh, block=8, reducer=np.median) / 0.6745
    return robust_z(np.log(sigma + 0.05))


def analyze_noise(source: Path, output: Path, grid: int = 8, map_output: Path | None = None) -> dict:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None: raise ValueError("Unsupported or invalid image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = cv2.absdiff(gray, smooth)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), residual)
    h, w = gray.shape
    stats = []
    for y in range(grid):
        for x in range(grid):
            tile = residual[y*h//grid:(y+1)*h//grid, x*w//grid:(x+1)*w//grid]
            if tile.size: stats.append(float(np.var(tile)))
    result = {"residual_mean": float(np.mean(residual)), "residual_std": float(np.std(residual)),
              "tile_variance_min": min(stats, default=0), "tile_variance_max": max(stats, default=0),
              "visualization": output.name, "note": "Content, resizing, denoising, and compression all affect residual statistics."}
    if map_output is not None:
        z = noise_block_z(gray)
        save_overlay(image, np.abs(z), map_output, vmax=2 * Z_THRESHOLD)
        result.update({"map_visualization": map_output.name, "block_z_max_abs": round(float(np.abs(z).max()), 2),
                       "unusual_block_share": round(float((np.abs(z) >= Z_THRESHOLD).mean()), 4), "block_size": 16,
                       "map_note": "Bright areas have a noise level unlike the rest of the image (either much smoother or much noisier). Saturated or blurred areas also stand out."})
    return result
