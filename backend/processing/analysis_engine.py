"""Runs independent forensic checks and records per-algorithm failures explicitly.

Both runners accept an optional progress(fraction, stage) callback used by background jobs.
"""
from pathlib import Path
from time import perf_counter
from typing import Callable
from PIL import Image
from .image.ela import analyze_ela
from .image.copy_move import analyze_copy_move
from .image.compression import analyze_compression
from .image.jpeg_ghost import analyze_ghost
from .image.metadata import extract_metadata
from .video.frame_extraction import extract_frames
from .video.frame_hashing import hash_frames
from .video.ssim_analysis import analyze_ssim
from .video.scene_detection import detect_scenes
from .video.optical_flow import analyze_flow

Progress = Callable[[float, str], None] | None
REPEAT_MAX_MOTION = 1.0   # px: a pHash "repeat" only counts if the scene also did not move between the two samples


def _noop(fraction: float, stage: str) -> None:
    pass


def run_image(source: Path, outputs: Path, progress: Progress = None) -> dict:
    progress = progress or _noop
    started = perf_counter(); outputs.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        original = {"format":image.format,"width":image.width,"height":image.height,"mode":image.mode}
    checks = {
        "ela": ("Error level analysis", lambda: analyze_ela(source, outputs / "ela.png", map_output=outputs / "ela_map.png")),
        "orb": ("Copy-move detection", lambda: analyze_copy_move(source, outputs / "orb.png")),
        "ghost": ("JPEG ghost analysis", lambda: analyze_ghost(source, outputs / "ghost_map.png")),
        "compression": ("Compression history", lambda: analyze_compression(source)),
        "metadata": ("Metadata", lambda: extract_metadata(source)),
    }
    algorithms = {}
    for i, (name, (label, action)) in enumerate(checks.items()):
        progress(0.05 + 0.9 * i / len(checks), label)
        try: algorithms[name] = {"status": "completed", **action()}
        except Exception as exc: algorithms[name] = {"status": "error", "error": str(exc)}
    indicator_count = int(bool(algorithms["orb"].get("flagged")))
    return {"original_image": original, "algorithms": algorithms, "indicator_summary": {"candidate_indicators": indicator_count,
            "statement": "Automated observations require contextual review and do not establish authenticity or manipulation."},
            "limitations": ["ELA is sensitive to recompression and conversion; its global peak mostly reflects how the file was last saved.",
                            "ORB matches can arise from natural repeated texture.",
                            "Heat maps highlight blocks that differ from the rest of the image; edges, texture, saturation and blur also differ.",
                            "JPEG ghosts only appear when pasted content was previously saved at a different JPEG quality.",
                            "Metadata and compression settings can be absent or changed during ordinary workflows."],
            "processing_seconds": round(perf_counter()-started, 3)}


def run_video(source: Path, outputs: Path, progress: Progress = None) -> dict:
    progress = progress or _noop
    started = perf_counter(); frames_dir = outputs / "frames"; outputs.mkdir(parents=True, exist_ok=True)
    progress(0.02, "Sampling frames")
    extraction = extract_frames(source, frames_dir, progress=lambda f: progress(0.02 + 0.28 * f, "Sampling frames"))
    frames = extraction.pop("frames")
    results = {"video": extraction, "frames": frames, "algorithms":{}}
    steps = {
        "frame_hashing": ("Comparing perceptual hashes", 0.32, lambda: hash_frames(frames, frames_dir)),
        "ssim": ("Measuring frame similarity", 0.40, lambda: analyze_ssim(frames, frames_dir, outputs / "ssim.png")),
        "scene_detection": ("Detecting scene changes", 0.50, lambda: detect_scenes(frames, frames_dir)),
    }
    for name, (label, at, action) in steps.items():
        progress(at, label)
        try: results[name] = {"status":"completed", **action()}
        except Exception as exc: results[name] = {"status":"error", "error":str(exc)}
        results["algorithms"][name] = results[name]
    if len(frames) >= 2:
        try: results["optical_flow"] = {"status":"completed", **analyze_flow(frames, frames_dir, outputs/"flow.png",
                                         progress=lambda f: progress(0.55 + 0.4 * f, "Estimating motion (optical flow)"))}
        except Exception as exc: results["optical_flow"] = {"status":"error", "error":str(exc)}
        results["algorithms"]["optical_flow"] = results["optical_flow"]
    confirm_repeats(results)
    results["indicator_summary"] = {"candidate_indicators": len(results.get("scene_detection",{}).get("candidates",[])) + len(results.get("frame_hashing",{}).get("pairs",[])),
         "statement":"Scene changes and repeated frames are observations; ordinary edits and static content can produce them."}
    results["limitations"] = ["Frame sampling may miss short events.", "Scene changes and repeated frames are common in ordinary video editing.",
                              "Optical flow is computed between sampled frames (about one per second), so it reflects motion across each gap, not frame-to-frame motion.",
                              "Repeated frames are confirmed with optical flow; in a genuinely static scene (fixed camera, nothing moving) repeats are expected."]
    results["processing_seconds"] = round(perf_counter()-started, 3)
    return results


def confirm_repeats(results: dict) -> None:
    """Keep a perceptual-hash repeat only if optical flow shows (almost) no motion between the two samples.

    pHash deliberately ignores small shifts, so a slowly panning camera looks "repeated" to it;
    a truly frozen or looped frame also has near-zero motion.
    """
    hashing, flow = results.get("frame_hashing", {}), results.get("optical_flow", {})
    if hashing.get("status") != "completed": return
    candidates = hashing.get("pairs", [])
    if flow.get("status") != "completed" or not flow.get("timestamps"):
        hashing.update(motion_checked=False, hash_only_pairs=len(candidates))
        return
    motion = {round(t, 6): m for t, m in zip(flow["timestamps"], flow["mean_magnitudes"])}
    confirmed = []
    for pair in candidates:
        m = motion.get(round(pair["timestamp"], 6))
        if m is not None and m <= REPEAT_MAX_MOTION:
            confirmed.append({**pair, "mean_motion": round(m, 3)})
    hashing.update(pairs=confirmed, hash_only_pairs=len(candidates), motion_checked=True, max_motion_px=REPEAT_MAX_MOTION,
                   note=f"Repeats require a perceptual-hash distance of 4 or less AND mean motion of at most {REPEAT_MAX_MOTION:g} px between the samples.")
