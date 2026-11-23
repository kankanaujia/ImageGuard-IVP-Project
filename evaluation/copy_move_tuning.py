"""Choose the copy-move decision rule on half of CASIA v2.0 and test it on the other half.

For every authentic and copy-move image the ORB self-matching and repeated-RANSAC grouping
from backend/processing/image/copy_move.py are run once, and the size, spatial spread, shift
and share of the largest consistent group are recorded. Files are split into fixed halves by
a hash of their name; candidate rules (minimum group size x minimum shift x minimum share of
all matches) are scored on the tuning half only: the chosen rule has the highest recall
among rules whose false-positive rate is at most --max-fpr (default 5%), because a flag is
meant to be worth a reviewer's time. The best-balanced rule by Youden's J (recall - FPR)
is reported alongside, and both are then evaluated on the held-out half.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe -m evaluation.copy_move_tuning <CASIA2 folder> [--workers 10]
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from .casia_eval import IMAGE_EXTS, OUT, find_split

SIZES = [4, 5, 6, 8, 10, 12, 15, 20]
SHIFTS = [0, 30, 40, 50, 60, 80, 100]          # minimum median copy distance, px
SHARES = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7]        # minimum fraction of all matches in the group


def features(path_str: str, label: int) -> dict:
    import cv2
    from backend.processing.image.copy_move import self_matches, consistent_groups, spread
    gray = cv2.imread(path_str, cv2.IMREAD_GRAYSCALE)
    if gray is None: return {"file": Path(path_str).name, "label": label, "error": True}
    _, a, b = self_matches(gray)
    groups = consistent_groups(a, b)
    best = groups[0] if groups else np.array([], dtype=int)
    return {"file": Path(path_str).name, "label": label, "raw": int(len(a)), "size": int(len(best)),
            "spread": spread(a[best]) if len(best) else 0.0,
            "shift": float(np.median(np.linalg.norm(b[best] - a[best], axis=1))) if len(best) else 0.0}


def half(name: str) -> str:
    return "tune" if int(hashlib.sha1(name.encode()).hexdigest(), 16) % 2 == 0 else "test"


def flag_rule(size, shift, share):
    return lambda r: r["size"] >= size and r["shift"] >= shift and r["size"] >= share * r["raw"]


def rates(rows, size, shift=0, share=0.0):
    flag = flag_rule(size, shift, share)
    pos = [r for r in rows if r["label"] == 1]; neg = [r for r in rows if r["label"] == 0]
    tp = sum(map(flag, pos)); fp = sum(map(flag, neg))
    return {"recall": tp / len(pos), "fpr": fp / len(neg), "precision": tp / (tp + fp) if tp + fp else 0.0, "tp": tp, "fp": fp, "pos": len(pos), "neg": len(neg)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--max-fpr", type=float, default=0.05, help="false-positive budget on authentic images")
    args = parser.parse_args()
    au = [p for p in find_split(args.root, "Au").iterdir() if p.suffix.lower() in IMAGE_EXTS]
    cm = [p for p in find_split(args.root, "Tp").iterdir() if p.suffix.lower() in IMAGE_EXTS and p.name.lower().startswith("tp_s_")]
    jobs = [(str(p), 0) for p in au] + [(str(p), 1) for p in cm]
    print(f"{len(au)} authentic + {len(cm)} copy-move images", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = [r for r in pool.map(features, *zip(*jobs), chunksize=32) if not r.get("error")]
    split = {"tune": [r for r in rows if half(r["file"]) == "tune"], "test": [r for r in rows if half(r["file"]) == "test"]}
    grid = []
    for size in SIZES:
        for shift in SHIFTS:
            for share in SHARES:
                t = rates(split["tune"], size, shift, share)
                grid.append({"min_group": size, "min_shift": shift, "min_share": share, "tune": t, "j": t["recall"] - t["fpr"]})
    balanced = max(grid, key=lambda g: g["j"])
    best = max((g for g in grid if g["tune"]["fpr"] <= args.max_fpr), key=lambda g: (g["tune"]["recall"], -g["tune"]["fpr"]))
    rule = (best["min_group"], best["min_shift"], best["min_share"])
    brule = (balanced["min_group"], balanced["min_shift"], balanced["min_share"])
    result = {"n": len(rows), "max_fpr": args.max_fpr, "chosen": {"min_group": rule[0], "min_shift": rule[1], "min_share": rule[2]},
              "best_balanced": {"min_group": brule[0], "min_shift": brule[1], "min_share": brule[2], "test": rates(split["test"], *brule)},
              "previous_rule": {"min_group": 4, "min_shift": 0, "min_share": 0.0},
              "tune": {"chosen": best["tune"], "previous_rule": rates(split["tune"], 4)},
              "test": {"chosen": rates(split["test"], *rule), "previous_rule": rates(split["test"], 4)}, "grid": grid}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "copy_move_tuning.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "copy_move_features.json").write_text(json.dumps(rows), encoding="utf-8")
    c, p = result["test"]["chosen"], result["test"]["previous_rule"]
    print(f"chosen rule: group >= {rule[0]}, shift >= {rule[1]} px, share >= {rule[2]}")
    print(f"held-out half  previous rule: recall {p['recall']:.3f}  FPR {p['fpr']:.3f}  precision {p['precision']:.3f}")
    print(f"held-out half  chosen rule:   recall {c['recall']:.3f}  FPR {c['fpr']:.3f}  precision {c['precision']:.3f}")
    for g in sorted(grid, key=lambda g: -g["j"])[:8]:
        print(f"  size>={g['min_group']:<3} shift>={g['min_shift']:<4} share>={g['min_share']:<4} tune recall {g['tune']['recall']:.3f} fpr {g['tune']['fpr']:.3f} J {g['j']:.3f}")


if __name__ == "__main__":
    sys.exit(main())
