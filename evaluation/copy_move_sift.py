"""Does SIFT recover the small copy-moves that ORB misses? Chosen on one half of CASIA, tested on the other.

Runs the copy-move matching and repeated-RANSAC grouping with SIFT (as in Amerini et al.)
on every authentic and copy-move image, and compares three detectors on the same fixed
halves used by copy_move_tuning.py:
  * ORB    - the current rule (group >= 5 matches, copy >= 40 px away)
  * SIFT   - thresholds chosen on the tuning half: highest recall with FPR <= --max-fpr
  * Either - flag when the ORB rule or the chosen SIFT rule flags
Copy-move images are also split by the size of the copied region (from the ground-truth
masks), so the effect on small copies can be seen directly.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe -m evaluation.copy_move_sift <CASIA2 folder> [--workers 10]
"""
from __future__ import annotations
import argparse, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from .casia_eval import IMAGE_EXTS, OUT, find_split
from .copy_move_tuning import half

SIZES = [4, 5, 6, 8, 10, 12, 15, 20, 25, 30]
SHIFTS = [0, 30, 40, 50, 60, 80, 100]
ORB_RULE = (5, 40.0)
SMALL = 0.02        # a copy covering under 2% of the image counts as small


def best_group(gray, method):
    from backend.processing.image.copy_move import self_matches, consistent_groups
    _, a, b = self_matches(gray, method=method)
    groups = consistent_groups(a, b)
    if not groups: return 0, 0.0
    g = groups[0]
    return int(len(g)), float(np.median(np.linalg.norm(b[g] - a[g], axis=1)))


def features(path_str: str, label: int, mask_str: str | None) -> dict:
    import cv2
    name = Path(path_str).name
    gray = cv2.imread(path_str, cv2.IMREAD_GRAYSCALE)
    if gray is None: return {"file": name, "label": label, "error": True}
    row = {"file": name, "label": label}
    row["orb_size"], row["orb_shift"] = best_group(gray, "orb")
    row["sift_size"], row["sift_shift"] = best_group(gray, "sift")
    if mask_str:
        mask = cv2.imread(mask_str, cv2.IMREAD_GRAYSCALE)
        if mask is not None: row["copy_fraction"] = float((mask > 127).mean())
    return row


def flags(r, method, rule):
    return r[f"{method}_size"] >= rule[0] and r[f"{method}_shift"] >= rule[1]


def rates(rows, flag):
    pos = [r for r in rows if r["label"] == 1]; neg = [r for r in rows if r["label"] == 0]
    tp = sum(1 for r in pos if flag(r)); fp = sum(1 for r in neg if flag(r))
    small = [r for r in pos if r.get("copy_fraction") is not None and r["copy_fraction"] < SMALL]
    return {"recall": tp / max(1, len(pos)), "fpr": fp / max(1, len(neg)), "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall_small_copies": sum(1 for r in small if flag(r)) / max(1, len(small)), "small_copies": len(small), "tp": tp, "fp": fp}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--max-fpr", type=float, default=0.05)
    args = parser.parse_args()
    gt = next((p for p in args.root.rglob("*") if p.is_dir() and "groundtruth" in p.name.lower()), None)
    au = [p for p in find_split(args.root, "Au").iterdir() if p.suffix.lower() in IMAGE_EXTS]
    cm = [p for p in find_split(args.root, "Tp").iterdir() if p.suffix.lower() in IMAGE_EXTS and p.name.lower().startswith("tp_s_")]
    mask = lambda p: str(gt / f"{p.stem}_gt.png") if gt and (gt / f"{p.stem}_gt.png").exists() else None
    jobs = [(str(p), 0, None) for p in au] + [(str(p), 1, mask(p)) for p in cm]
    print(f"{len(au)} authentic + {len(cm)} copy-move images", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = [r for r in pool.map(features, *zip(*jobs), chunksize=16) if not r.get("error")]
    tune = [r for r in rows if half(r["file"]) == "tune"]; test = [r for r in rows if half(r["file"]) == "test"]

    grid = [{"rule": (s, sh), "tune": rates(tune, lambda r, s=s, sh=sh: flags(r, "sift", (s, sh)))} for s in SIZES for sh in SHIFTS]
    ok = [g for g in grid if g["tune"]["fpr"] <= args.max_fpr]
    sift_rule = max(ok, key=lambda g: (g["tune"]["recall"], -g["tune"]["fpr"]))["rule"]
    # For "either", the SIFT threshold is chosen again so that the combination stays within the budget.
    egrid = [{"rule": (s, sh), "tune": rates(tune, lambda r, s=s, sh=sh: flags(r, "orb", ORB_RULE) or flags(r, "sift", (s, sh)))} for s in SIZES for sh in SHIFTS]
    eok = [g for g in egrid if g["tune"]["fpr"] <= args.max_fpr]
    either_rule = max(eok, key=lambda g: (g["tune"]["recall"], -g["tune"]["fpr"]))["rule"] if eok else None

    detectors = {"orb": lambda r: flags(r, "orb", ORB_RULE), "sift": lambda r: flags(r, "sift", sift_rule)}
    if either_rule: detectors["either"] = lambda r: flags(r, "orb", ORB_RULE) or flags(r, "sift", either_rule)
    result = {"n": len(rows), "max_fpr": args.max_fpr, "orb_rule": ORB_RULE, "sift_rule": sift_rule, "either_sift_rule": either_rule,
              "tune": {k: rates(tune, f) for k, f in detectors.items()}, "test": {k: rates(test, f) for k, f in detectors.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "copy_move_sift.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"SIFT rule {sift_rule}; either-rule SIFT part {either_rule}")
    for k, v in result["test"].items():
        print(f"held-out {k:7} recall {v['recall']:.3f}  small-copy recall {v['recall_small_copies']:.3f} (n={v['small_copies']})  FPR {v['fpr']:.3f}  precision {v['precision']:.3f}")


if __name__ == "__main__":
    sys.exit(main())
