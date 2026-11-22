"""SSIM of adjacent sampled frames."""
from pathlib import Path
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from skimage.metrics import structural_similarity

def analyze_ssim(frames: list[dict], frame_dir: Path, output: Path) -> dict:
    scores, times = [], []
    for a,b in zip(frames, frames[1:]):
        left = cv2.imread(str(frame_dir / a["file"]), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(frame_dir / b["file"]), cv2.IMREAD_GRAYSCALE)
        if left is None or right is None: continue
        right = cv2.resize(right, (left.shape[1], left.shape[0]))
        scores.append(float(structural_similarity(left, right, data_range=255)))
        times.append(float(b["timestamp"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,3), facecolor="#101827"); ax.set_facecolor("#101827")
    ax.plot(times, scores, color="#61a9ff", marker="."); ax.set_ylim(-1,1); ax.set_xlabel("Time (s)"); ax.set_ylabel("Adjacent SSIM")
    ax.tick_params(colors="#aab7ca"); ax.spines[:].set_color("#344256"); fig.tight_layout(); fig.savefig(output, dpi=130, facecolor=fig.get_facecolor()); plt.close(fig)
    return {"scores": scores, "timestamps": times, "visualization": output.name, "note": "Abrupt similarity changes often reflect ordinary cuts or motion."}
