"""Dense optical flow across every pair of adjacent sampled frames."""
from pathlib import Path
import cv2
import numpy as np

ANALYSIS_WIDTH = 480      # frames are downscaled to this width before computing flow
SATURATION_PX = 8.0       # motion (in analysed pixels) shown at full brightness in visualizations
SPIKE_MAD_FACTOR = 3.5    # robust z-score above which a pair counts as a motion spike
SPIKE_MIN_PX = 1.0        # ignore "spikes" in near-static footage below this mean motion (original pixels)


def _load_gray(path: Path, size: tuple[int, int] | None):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Unable to read frame {path.name}")
    if size is None:
        return image
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)


def _render(flow: np.ndarray) -> np.ndarray:
    """Hue = direction, brightness = speed on a fixed scale so pairs are comparable."""
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    hsv = np.zeros((*flow.shape[:2], 3), dtype=np.uint8)
    hsv[..., 0] = (angle * 180 / np.pi / 2).astype(np.uint8)
    hsv[..., 1] = 255
    hsv[..., 2] = np.clip(magnitude / SATURATION_PX * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def flow_file(frame: dict) -> str:
    """Name of the flow image showing motion from the previous sampled frame into this one."""
    return f"flow_{frame['index']:08d}.jpg"


def analyze_flow(frames: list[dict], frame_dir: Path, output: Path) -> dict:
    """Compute Farneback flow for each adjacent pair of sampled frames.

    Magnitudes are reported in original-resolution pixels. A per-pair flow image is
    written next to the frames, and the pair with the most motion is copied to `output`.
    """
    if len(frames) < 2:
        raise ValueError("At least two sampled frames are needed for optical flow")
    first = _load_gray(frame_dir / frames[0]["file"], None)
    height, width = first.shape
    scale = min(1.0, ANALYSIS_WIDTH / width)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))

    timestamps, means, p95s = [], [], []
    peak_index, peak_mean = None, -1.0
    previous = cv2.resize(first, size, interpolation=cv2.INTER_AREA)
    for frame in frames[1:]:
        current = _load_gray(frame_dir / frame["file"], size)
        flow = cv2.calcOpticalFlowFarneback(previous, current, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude = np.hypot(flow[..., 0], flow[..., 1]) / scale
        mean, p95 = float(magnitude.mean()), float(np.percentile(magnitude, 95))
        cv2.imwrite(str(frame_dir / flow_file(frame)), _render(flow), [cv2.IMWRITE_JPEG_QUALITY, 85])
        timestamps.append(float(frame["timestamp"])); means.append(mean); p95s.append(p95)
        if mean > peak_mean:
            peak_index, peak_mean = len(timestamps) - 1, mean
        previous = current

    peak_frame = frames[peak_index + 1]
    output.parent.mkdir(parents=True, exist_ok=True)
    peak_image = cv2.imread(str(frame_dir / flow_file(peak_frame)))
    if peak_image is None or not cv2.imwrite(str(output), peak_image):
        raise OSError("Could not save optical flow visualization")

    # Robust outlier test (median / MAD) so a few busy pairs do not hide each other.
    values = np.array(means)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) * 1.4826
    spikes = []
    if len(values) >= 4:
        for t, m in zip(timestamps, means):
            score = (m - median) / mad if mad > 1e-9 else (float("inf") if m - median > SPIKE_MIN_PX else 0.0)
            if m >= SPIKE_MIN_PX and score >= SPIKE_MAD_FACTOR:
                spikes.append({"timestamp": t, "mean_motion": m, "robust_z": None if score == float("inf") else round(score, 2)})

    return {
        "timestamps": timestamps,
        "mean_magnitudes": means,
        "p95_magnitudes": p95s,
        "mean_motion_magnitude": float(values.mean()),
        "p95_motion_magnitude": float(np.max(p95s)),
        "median_motion_magnitude": median,
        "peak_timestamp": timestamps[peak_index],
        "peak_mean_magnitude": peak_mean,
        "spikes": spikes,
        "analysed_width": size[0],
        "saturation_px": SATURATION_PX / scale,
        "visualization": output.name,
        "note": "Motion spikes often come from camera moves, cuts or fast action; they mark moments to review, not edits. "
                "Very large motion between samples (beyond roughly 20 analysed pixels) is underestimated, and across a cut the flow is meaningless.",
    }
