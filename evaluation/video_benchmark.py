"""Synthetic video tampering benchmark for ImageGuard's video checks.

There is no small, standard public dataset for video tampering, so this script generates
clips with known edits and checks whether the real pipeline (run_video) flags them:

  clean      continuous camera pan (measures false alarms)
  insertion  footage from a different scene spliced in for a few seconds
  freeze     one frame repeated for a few seconds (frozen / looped footage)
  deletion   several seconds of the pan removed (a jump in continuity)

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe -m evaluation.video_benchmark [--per-kind 15] [--workers 8]
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "results" / "video"
FPS, W, H = 10, 480, 270
KINDS = ("clean", "insertion", "freeze", "deletion")
TOLERANCE = 1.01  # a flag counts if it lands within one sample (1 s) of the edit


def make_scene(rng: np.random.Generator, length: int):
    import cv2
    base = cv2.GaussianBlur((rng.random((H, length, 3)) * 255).astype(np.uint8), (9, 9), 0)
    base = cv2.normalize(base, None, 0, 255, cv2.NORM_MINMAX)
    tint = rng.uniform(0.45, 1.0, 3)                      # each scene gets its own colour cast
    base = (base * tint).astype(np.uint8)
    for _ in range(length // 40):
        x, y = int(rng.integers(0, length - 90)), int(rng.integers(0, H - 60))
        colour = [int(c) for c in rng.integers(0, 255, 3)]
        if rng.random() < 0.5: cv2.rectangle(base, (x, y), (x + int(rng.integers(20, 90)), y + int(rng.integers(20, 60))), colour, -1)
        else: cv2.circle(base, (x, y), int(rng.integers(8, 35)), colour, -1)
    return base


def make_clip(kind: str, seed: int, path: Path) -> dict:
    """Write one clip and return its ground truth (edit time in seconds, or None)."""
    import cv2
    rng = np.random.default_rng(seed)
    seconds = int(rng.integers(16, 26)); n = seconds * FPS
    speed = float(rng.uniform(4, 15))                     # pan speed, px per second
    scene = make_scene(rng, W + int(speed * (seconds + 10)) + 200)
    other = make_scene(rng, W + int(speed * 10) + 200)
    t_edit = int(rng.integers(5, seconds - 6))            # edit starts here (whole seconds)
    span = int(rng.integers(2, 5))                        # edit duration, seconds
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    x = 0.0                                               # camera position in the main scene
    for i in range(n):
        t = i / FPS
        inside = t_edit <= t < t_edit + span
        if kind == "deletion" and i == t_edit * FPS:
            x += speed * span                             # skip `span` seconds of camera travel
        if kind == "insertion" and inside:
            offset = int((t - t_edit) * speed)
            frame = other[:, offset: offset + W]
        else:
            frame = scene[:, int(x): int(x) + W]          # during a freeze x stops, so the frame repeats
        noise = rng.normal(0, 2.0, frame.shape)           # mild sensor noise so repeats are not bit-identical
        writer.write(np.clip(frame + noise, 0, 255).astype(np.uint8))
        if not (kind == "freeze" and inside):
            x += speed / FPS
    writer.release()
    truth = None if kind == "clean" else float(t_edit)
    end = None if kind in ("clean", "deletion") else float(t_edit + span)
    return {"kind": kind, "seed": seed, "seconds": seconds, "speed": speed, "edit_start": truth, "edit_end": end, "span": span}


def run_one(kind: str, seed: int) -> dict:
    from backend.processing.analysis_engine import run_video
    work = Path(tempfile.mkdtemp(prefix="ig_vbench_"))
    try:
        truth = make_clip(kind, seed, work / "clip.mp4")
        result = run_video(work / "clip.mp4", work / "out")
        flags = {
            "scene": [c["timestamp"] for c in result.get("scene_detection", {}).get("candidates", [])],
            "repeat": [p["timestamp"] for p in result.get("frame_hashing", {}).get("pairs", [])],
            "motion": [s["timestamp"] for s in result.get("optical_flow", {}).get("spikes", [])],
        }
        ssim = result.get("ssim", {})
        return {**truth, "flags": flags, "processing_seconds": result["processing_seconds"],
                "min_ssim": min(ssim.get("scores") or [1.0]),
                "errors": [k for k, v in result["algorithms"].items() if v.get("status") == "error"]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def near(times: list[float], targets: list[float]) -> bool:
    return any(abs(t - g) <= TOLERANCE for t in times for g in targets)


def score(rows: list[dict]) -> dict:
    # Which check is expected to catch which edit, and where the flag should land.
    expected = {"insertion": "scene", "freeze": "repeat", "deletion": "motion"}
    out: dict = {"per_kind": {}, "false_alarms": {}}
    clean = [r for r in rows if r["kind"] == "clean"]
    for check in ("scene", "repeat", "motion"):
        out["false_alarms"][check] = {"clips_with_any_flag": sum(bool(r["flags"][check]) for r in clean), "clips": len(clean),
                                      "flags_per_minute": 60 * sum(len(r["flags"][check]) for r in clean) / max(1, sum(r["seconds"] for r in clean))}
    out["false_alarms"]["any"] = {"clips_with_any_flag": sum(any(r["flags"].values()) for r in clean), "clips": len(clean)}
    for kind, check in expected.items():
        clips = [r for r in rows if r["kind"] == kind]
        targets = lambda r: [t for t in (r["edit_start"], r["edit_end"]) if t is not None]
        out["per_kind"][kind] = {
            "clips": len(clips), "expected_check": check,
            "detected_by_expected_check": sum(near(r["flags"][check], targets(r)) for r in clips),
            "detected_by_any_check": sum(any(near(v, targets(r)) for v in r["flags"].values()) for r in clips),
            "by_check": {c: sum(near(r["flags"][c], targets(r)) for r in clips) for c in ("scene", "repeat", "motion")},
        }
    times = [r["processing_seconds"] for r in rows]
    out["processing_seconds"] = {"mean": float(np.mean(times)), "max": float(np.max(times))}
    out["errors"] = sum(bool(r["errors"]) for r in rows)
    return out


def summary_md(m: dict) -> str:
    lines = ["# Synthetic video benchmark", "", "| Edit | Clips | Expected check | Detected (expected check) | Detected (any check) | scene · repeat · motion |", "|---|---|---|---|---|---|"]
    for kind, v in m["per_kind"].items():
        b = v["by_check"]
        lines.append(f"| {kind} | {v['clips']} | {v['expected_check']} | {v['detected_by_expected_check']}/{v['clips']} | {v['detected_by_any_check']}/{v['clips']} | {b['scene']} · {b['repeat']} · {b['motion']} |")
    lines += ["", "False alarms on clean clips:", "", "| Check | Clips with any flag | Flags per minute |", "|---|---|---|"]
    for check, v in m["false_alarms"].items():
        rate = f"{v['flags_per_minute']:.2f}" if "flags_per_minute" in v else "—"
        lines.append(f"| {check} | {v['clips_with_any_flag']}/{v['clips']} | {rate} |")
    lines += ["", f"Processing time per clip: mean {m['processing_seconds']['mean']:.2f}s, max {m['processing_seconds']['max']:.2f}s; clips with errors: {m['errors']}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-kind", type=int, default=15)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    jobs = [(kind, 1000 * k + i) for k, kind in enumerate(KINDS) for i in range(args.per_kind)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run_one, *zip(*jobs)))
    metrics = score(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "clips.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(summary_md(metrics), encoding="utf-8")
    print(summary_md(metrics))


if __name__ == "__main__":
    sys.exit(main())
