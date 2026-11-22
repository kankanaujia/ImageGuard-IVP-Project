"""Histogram distance based scene transition candidates."""
from pathlib import Path
import cv2

def detect_scenes(frames: list[dict], frame_dir: Path, threshold: float = 0.55) -> dict:
    scenes = []
    previous = None
    for frame in frames:
        image = cv2.imread(str(frame_dir / frame["file"]))
        if image is None: continue
        hist = cv2.calcHist([image], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        cv2.normalize(hist, hist)
        if previous is not None:
            distance = cv2.compareHist(previous, hist, cv2.HISTCMP_BHATTACHARYYA)
            if distance >= threshold: scenes.append({"timestamp": frame["timestamp"], "histogram_distance": float(distance)})
        previous = hist
    return {"candidates": scenes, "note": "Histogram cuts are scene transition candidates; ordinary editing and camera changes are expected."}
