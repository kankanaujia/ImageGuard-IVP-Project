"""Perceptual hashing for sampled video frames."""
from pathlib import Path
import imagehash
from PIL import Image

def hash_frames(frames: list[dict], frame_dir: Path, near_threshold: int = 4) -> dict:
    hashes = []
    for frame in frames:
        with Image.open(frame_dir / frame["file"]) as img:
            hashes.append((frame, imagehash.phash(img)))
    pairs = []
    for i in range(1, len(hashes)):
        distance = hashes[i-1][1] - hashes[i][1]
        if distance <= near_threshold:
            pairs.append({"previous_timestamp": hashes[i-1][0]["timestamp"], "timestamp": hashes[i][0]["timestamp"],
                          "hamming_distance": distance, "kind": "exact" if distance == 0 else "near_duplicate"})
    return {"pairs": pairs, "sampled_frames": len(hashes), "note": "Low perceptual hash distance indicates visual similarity, not necessarily repeated or manipulated footage."}
