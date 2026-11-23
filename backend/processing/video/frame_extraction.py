"""Video inspection and interval-based frame extraction."""
from pathlib import Path
from typing import Callable
import cv2

def extract_frames(source: Path, output_dir: Path, interval_seconds: float = 1.0, max_frames: int = 180,
                   progress: Callable[[float], None] | None = None) -> dict:
    if interval_seconds <= 0: raise ValueError("interval_seconds must be positive")
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened(): raise ValueError("Unsupported or invalid video")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = count / fps if fps > 0 else 0
    step = max(1, round((fps or 1) * interval_seconds))
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    planned = max(1, min(max_frames, (count + step - 1) // step))
    for index in range(0, count, step):
        if len(frames) >= max_frames: break
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok: continue
        timestamp = index / fps if fps else 0
        name = f"frame_{index:08d}.jpg"
        cv2.imwrite(str(output_dir / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        frames.append({"file": name, "timestamp": timestamp, "index": index})
        if progress: progress(len(frames) / planned)
    cap.release()
    if not frames: raise ValueError("No frames could be extracted")
    return {"fps": fps, "duration": duration, "frame_count": count, "width": width,
            "height": height, "frames": frames, "sample_interval_seconds": interval_seconds}
