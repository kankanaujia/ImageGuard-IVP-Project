"""Runs independent forensic checks and records per-algorithm failures explicitly."""
from pathlib import Path
from time import perf_counter
from PIL import Image
from .image.ela import analyze_ela
from .image.copy_move import analyze_copy_move
from .image.metadata import extract_metadata
from .image.noise_analysis import analyze_noise
from .image.histogram import analyze_histogram
from .video.frame_extraction import extract_frames
from .video.frame_hashing import hash_frames
from .video.ssim_analysis import analyze_ssim
from .video.scene_detection import detect_scenes
from .video.optical_flow import analyze_flow

def run_image(source: Path, outputs: Path) -> dict:
    started = perf_counter(); outputs.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        original = {"format":image.format,"width":image.width,"height":image.height,"mode":image.mode}
    algorithms = {}
    for name, action in {
        "ela": lambda: analyze_ela(source, outputs / "ela.png"),
        "orb": lambda: analyze_copy_move(source, outputs / "orb.png"),
        "noise": lambda: analyze_noise(source, outputs / "noise.png"),
        "histogram": lambda: analyze_histogram(source, outputs / "histogram.png"),
        "metadata": lambda: extract_metadata(source),
    }.items():
        try: algorithms[name] = {"status": "completed", **action()}
        except Exception as exc: algorithms[name] = {"status": "error", "error": str(exc)}
    indicator_count = sum(1 for v in algorithms.values() if v.get("candidate_matches", 0) >= 4)
    return {"original_image": original, "algorithms": algorithms, "indicator_summary": {"candidate_indicators": indicator_count,
            "statement": "Automated observations require contextual review and do not establish authenticity or manipulation."},
            "limitations": ["ELA is sensitive to recompression and conversion.", "ORB matches can arise from natural repeated texture.", "Metadata can be absent or changed during ordinary workflows."],
            "processing_seconds": round(perf_counter()-started, 3)}

def run_video(source: Path, outputs: Path) -> dict:
    started = perf_counter(); frames_dir = outputs / "frames"; outputs.mkdir(parents=True, exist_ok=True)
    extraction = extract_frames(source, frames_dir)
    frames = extraction.pop("frames")
    results = {"video": extraction, "frames": frames, "algorithms":{}}
    for name, action in {
        "frame_hashing": lambda: hash_frames(frames, frames_dir),
        "ssim": lambda: analyze_ssim(frames, frames_dir, outputs / "ssim.png"),
        "scene_detection": lambda: detect_scenes(frames, frames_dir),
    }.items():
        try: results[name] = {"status":"completed", **action()}
        except Exception as exc: results[name] = {"status":"error", "error":str(exc)}
        results["algorithms"][name] = results[name]
    if len(frames) >= 2:
        try: results["optical_flow"] = {"status":"completed", **analyze_flow(frames, frames_dir, outputs/"flow.png")}
        except Exception as exc: results["optical_flow"] = {"status":"error", "error":str(exc)}
        results["algorithms"]["optical_flow"] = results["optical_flow"]
    results["indicator_summary"] = {"candidate_indicators": len(results.get("scene_detection",{}).get("candidates",[])) + len(results.get("frame_hashing",{}).get("pairs",[])),
         "statement":"Scene changes and repeated-looking frames are observations; ordinary edits and static content can produce them."}
    results["limitations"] = ["Frame sampling may miss short events.", "Scene changes and repeated frames are common in ordinary video editing.",
                              "Optical flow is computed between sampled frames (about one per second), so it reflects motion across each gap, not frame-to-frame motion."]
    results["processing_seconds"] = round(perf_counter()-started, 3)
    return results
