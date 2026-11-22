"""RGB and grayscale image histograms."""
from pathlib import Path
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def analyze_histogram(source: Path, output: Path) -> dict:
    image = cv2.imread(str(source))
    if image is None: raise ValueError("Unsupported or invalid image")
    channels = [cv2.calcHist([image], [i], None, [256], [0,256]).flatten() for i in range(3)]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 3.5), facecolor="#101827")
    ax.set_facecolor("#101827")
    for values, color in zip(channels, ("#ef6262", "#6fcf97", "#61a9ff")):
        ax.plot(values, color=color, linewidth=1)
    ax.tick_params(colors="#aab7ca"); ax.spines[:].set_color("#344256")
    fig.tight_layout(); fig.savefig(output, dpi=130, facecolor=fig.get_facecolor()); plt.close(fig)
    return {"rgb_counts": [[int(v) for v in ch] for ch in channels],
            "grayscale_mean": float(gray.mean()), "grayscale_std": float(gray.std()), "visualization": output.name}
