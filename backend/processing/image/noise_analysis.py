"""Residual and local-variance summaries for image noise inspection."""
from pathlib import Path
import cv2
import numpy as np

def analyze_noise(source: Path, output: Path, grid: int = 8) -> dict:
    image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
    if image is None: raise ValueError("Unsupported or invalid image")
    smooth = cv2.GaussianBlur(image, (3, 3), 0)
    residual = cv2.absdiff(image, smooth)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), residual)
    h, w = image.shape
    stats = []
    for y in range(grid):
        for x in range(grid):
            tile = residual[y*h//grid:(y+1)*h//grid, x*w//grid:(x+1)*w//grid]
            if tile.size: stats.append(float(np.var(tile)))
    return {"residual_mean": float(np.mean(residual)), "residual_std": float(np.std(residual)),
            "tile_variance_min": min(stats, default=0), "tile_variance_max": max(stats, default=0),
            "visualization": output.name, "note": "Content, resizing, denoising, and compression all affect residual statistics."}
