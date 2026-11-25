"""Evaluate ImageGuard's image checks on the CASIA v2.0 tampering dataset.

Runs the real analysis pipeline (backend.processing.analysis_engine.run_image) on authentic
(Au) and tampered (Tp) images and measures how well each check's score separates them.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe -m evaluation.casia_eval <CASIA2 folder> [--per-class N] [--workers 10]

Outputs go to evaluation/results/casia/: per-image CSV, metrics JSON, summary Markdown and plots.
"""
from __future__ import annotations
import argparse, csv, json, os, random, shutil, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png"}
APP_RULE = "copy-move group >= 5 consistent matches and copy >= 40 px from source"  # backend/processing/image/copy_move.py
OUT = Path(__file__).resolve().parent / "results" / "casia"


# ---------------------------------------------------------------- dataset
def find_split(root: Path, name: str) -> Path:
    """Locate the Au / Tp folder anywhere under root (Kaggle zips nest it differently)."""
    for path in [root, *root.rglob("*")]:
        if path.is_dir() and path.name.lower() == name.lower():
            return path
    raise SystemExit(f"Could not find a '{name}' folder under {root}")


def tamper_type(name: str) -> str:
    # CASIA v2 names tampered files Tp_S_... (source = same image: copy-move)
    # or Tp_D_... (source = different image: splicing).
    parts = name.split("_")
    if len(parts) > 1 and parts[0].lower() == "tp":
        return {"s": "copy-move", "d": "splicing"}.get(parts[1].lower(), "unknown")
    return "authentic"


def list_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


# ---------------------------------------------------------------- worker
def analyse(path_str: str, label: int) -> dict:
    from backend.processing.analysis_engine import run_image  # imported in the worker process
    path = Path(path_str)
    work = Path(tempfile.mkdtemp(prefix="ig_eval_"))
    row = {"file": path.name, "label": label, "type": tamper_type(path.name) if label else "authentic",
           "format": path.suffix.lower().lstrip(".").replace("jpeg", "jpg").replace("tiff", "tif")}
    try:
        started = time.perf_counter()
        result = run_image(path, work)
        row["seconds"] = round(time.perf_counter() - started, 4)
        a = result["algorithms"]
        img = result["original_image"]
        row.update(width=img["width"], height=img["height"])
        ok = lambda k: a.get(k, {}).get("status") == "completed"
        row["ela_peak"] = a["ela"]["difference_peak"] if ok("ela") else None
        row["orb_raw"] = a["orb"]["raw_candidate_matches"] if ok("orb") else None
        row["orb_consistent"] = a["orb"]["geometrically_consistent_matches"] if ok("orb") else None
        row["exif_tags"] = len(a["metadata"]["exif"]) if ok("metadata") else None
        row["ela_block_z_max"] = a["ela"].get("block_z_max") if ok("ela") else None
        row["ela_unusual_share"] = a["ela"].get("unusual_block_share") if ok("ela") else None
        row["ghost_block_z_max"] = a["ghost"].get("block_z_max") if ok("ghost") else None
        row["ghost_unusual_share"] = a["ghost"].get("unusual_block_share") if ok("ghost") else None
        row["jpeg_quality"] = a["compression"].get("estimated_quality") if ok("compression") else None
        row["errors"] = ";".join(f"{k}:{v.get('error', '')[:80]}" for k, v in a.items() if v.get("status") == "error")
        row["app_flag"] = int(bool(a["orb"].get("flagged"))) if ok("orb") else 0
    except Exception as exc:  # unreadable file etc.: record and continue
        row["errors"] = f"pipeline:{str(exc)[:120]}"
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return row


# ---------------------------------------------------------------- metrics
def roc(scores: np.ndarray, labels: np.ndarray):
    """ROC curve and AUC (ties handled by grouping equal scores)."""
    order = np.argsort(-scores, kind="mergesort")
    s, y = scores[order], labels[order]
    distinct = np.r_[np.where(np.diff(s))[0], len(s) - 1]
    tps = np.cumsum(y)[distinct]; fps = np.cumsum(1 - y)[distinct]
    tpr = np.r_[0, tps / max(1, y.sum())]; fpr = np.r_[0, fps / max(1, (1 - y).sum())]
    thresholds = np.r_[np.inf, s[distinct]]
    return fpr, tpr, thresholds, float(np.trapezoid(tpr, fpr))


def confusion(pred: np.ndarray, labels: np.ndarray) -> dict:
    tp = int(((pred == 1) & (labels == 1)).sum()); fp = int(((pred == 1) & (labels == 0)).sum())
    fn = int(((pred == 0) & (labels == 1)).sum()); tn = int(((pred == 0) & (labels == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": (tp + tn) / max(1, len(labels)),
            "precision": precision, "recall": recall, "fpr": fp / (fp + tn) if fp + tn else 0.0,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


SCORES = {  # name -> (column, direction: +1 means larger = more suspicious)
    "ORB consistent matches": ("orb_consistent", 1),
    "ORB raw matches": ("orb_raw", 1),
    "ELA peak difference": ("ela_peak", 1),
    "ELA heat map: strongest block": ("ela_block_z_max", 1),
    "ELA heat map: unusual share": ("ela_unusual_share", 1),
    "JPEG ghost: strongest block": ("ghost_block_z_max", 1),
    "JPEG ghost: unusual share": ("ghost_unusual_share", 1),
}


def evaluate(rows: list[dict]) -> dict:
    metrics: dict = {"n": len(rows), "by_class": {}, "scores": {}, "app_threshold": {}, "by_type": {}, "by_format": {}}
    for key in ("authentic", "copy-move", "splicing", "unknown"):
        count = sum(r["type"] == key for r in rows)
        if count: metrics["by_class"][key] = count
    for fmt in sorted({r["format"] for r in rows}):
        metrics["by_format"][fmt] = {"authentic": sum(r["format"] == fmt and r["label"] == 0 for r in rows),
                                     "tampered": sum(r["format"] == fmt and r["label"] == 1 for r in rows)}
    metrics["pipeline_errors"] = sum(bool(r.get("errors")) for r in rows)
    times = [r["seconds"] for r in rows if r.get("seconds")]
    if times:
        metrics["seconds"] = {"mean": float(np.mean(times)), "median": float(np.median(times)), "p95": float(np.percentile(times, 95))}

    for name, (col, sign) in SCORES.items():
        valid = [r for r in rows if r.get(col) is not None]
        if len({r["label"] for r in valid}) < 2: continue
        s = sign * np.array([float(r[col]) for r in valid]); y = np.array([r["label"] for r in valid])
        fpr, tpr, thr, auc = roc(s, y)
        j = int(np.argmax(tpr - fpr))  # Youden's J: best single threshold
        metrics["scores"][name] = {"column": col, "n": len(valid), "auc": auc, "best_threshold": float(sign * thr[j]),
                                   "best_tpr": float(tpr[j]), "best_fpr": float(fpr[j]),
                                   "roc": {"fpr": fpr.tolist()[:: max(1, len(fpr) // 200)], "tpr": tpr.tolist()[:: max(1, len(tpr) // 200)]}}

    # CASIA v2 authentic images are all JPEG while many tampered ones are TIFF, so a score can
    # "detect" the format instead of the tampering. Re-score on JPEG files only to control for it.
    metrics["jpeg_only_auc"] = {}
    jpeg = [r for r in rows if r["format"] == "jpg"]
    for name, (col, sign) in SCORES.items():
        valid = [r for r in jpeg if r.get(col) is not None]
        if len({r["label"] for r in valid}) == 2:
            metrics["jpeg_only_auc"][name] = roc(sign * np.array([float(r[col]) for r in valid]), np.array([r["label"] for r in valid]))[3]

    y = np.array([r["label"] for r in rows if "app_flag" in r]); pred = np.array([r["app_flag"] for r in rows if "app_flag" in r])
    metrics["app_threshold"] = {"rule": APP_RULE, **confusion(pred, y)}
    for kind in ("copy-move", "splicing"):
        subset = [r for r in rows if "app_flag" in r and r["type"] in (kind, "authentic")]
        if any(r["type"] == kind for r in subset):
            yy = np.array([r["label"] for r in subset]); pp = np.array([r["app_flag"] for r in subset])
            entry = confusion(pp, yy)
            col_vals = [r for r in subset if r.get("orb_consistent") is not None]
            entry["orb_auc"] = roc(np.array([float(r["orb_consistent"]) for r in col_vals]), np.array([r["label"] for r in col_vals]))[3]
            ela_vals = [r for r in subset if r.get("ela_peak") is not None]
            entry["ela_auc"] = roc(np.array([float(r["ela_peak"]) for r in ela_vals]), np.array([r["label"] for r in ela_vals]))[3]
            metrics["by_type"][kind] = entry
    return metrics


def plot(rows: list[dict], metrics: dict, out: Path) -> None:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for name, m in metrics["scores"].items():
        ax.plot(m["roc"]["fpr"], m["roc"]["tpr"], label=f"{name} (AUC {m['auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="Chance")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate"); ax.set_title("ROC on CASIA v2.0")
    ax.legend(fontsize=7, loc="lower right"); fig.tight_layout(); fig.savefig(out / "roc.png", dpi=200); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, (col, title, log) in zip(axes, [("orb_consistent", "ORB consistent matches", True), ("ela_peak", "ELA peak difference", False), ("ghost_block_z_max", "JPEG ghost strongest block", False)]):
        for label, colour, name in ((0, "#2b7bb9", "Authentic"), (1, "#d9534f", "Tampered")):
            vals = np.array([r[col] for r in rows if r["label"] == label and r.get(col) is not None], dtype=float)
            if not len(vals): continue
            data = np.log10(vals + 1) if log else vals
            ax.hist(data, bins=40, alpha=0.55, color=colour, label=name, density=True)
        ax.set_title(title, fontsize=10); ax.set_xlabel(f"log10(value + 1)" if log else "value", fontsize=8); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "score_distributions.png", dpi=200); plt.close(fig)


def summary_md(metrics: dict) -> str:
    lines = ["# CASIA v2.0 evaluation", "", f"Images evaluated: {metrics['n']} ({', '.join(f'{k}: {v}' for k, v in metrics['by_class'].items())})",
             f"Pipeline errors: {metrics['pipeline_errors']}", ""]
    if "seconds" in metrics:
        s = metrics["seconds"]; lines += [f"Processing time per image: mean {s['mean']:.3f}s, median {s['median']:.3f}s, p95 {s['p95']:.3f}s", ""]
    lines += ["| Score | AUC (all) | AUC (JPEG only) | Best threshold | TPR | FPR |", "|---|---|---|---|---|---|"]
    for name, m in metrics["scores"].items():
        jo = metrics["jpeg_only_auc"].get(name)
        lines.append(f"| {name} | {m['auc']:.3f} | {'—' if jo is None else f'{jo:.3f}'} | {m['best_threshold']:.3g} | {m['best_tpr']:.3f} | {m['best_fpr']:.3f} |")
    a = metrics["app_threshold"]
    lines += ["", f"App decision rule ({a['rule']}): accuracy {a['accuracy']:.3f}, precision {a['precision']:.3f}, recall {a['recall']:.3f}, FPR {a['fpr']:.3f}, F1 {a['f1']:.3f}",
              f"Confusion: TP {a['tp']}, FP {a['fp']}, FN {a['fn']}, TN {a['tn']}", "", "| Tamper type | Recall | Precision | FPR | ORB AUC | ELA AUC |", "|---|---|---|---|---|---|"]
    for kind, m in metrics["by_type"].items():
        lines.append(f"| {kind} | {m['recall']:.3f} | {m['precision']:.3f} | {m['fpr']:.3f} | {m['orb_auc']:.3f} | {m['ela_auc']:.3f} |")
    lines += ["", "| Format | Authentic | Tampered |", "|---|---|---|"] + [f"| {f} | {v['authentic']} | {v['tampered']} |" for f, v in metrics["by_format"].items()]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="CASIA v2.0 folder (containing Au and Tp)")
    parser.add_argument("--per-class", type=int, default=0, help="random sample size per class (0 = all images)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    au, tp = list_images(find_split(args.root, "Au")), list_images(find_split(args.root, "Tp"))
    if args.per_class:
        rng = random.Random(args.seed)
        au, tp = rng.sample(au, min(args.per_class, len(au))), rng.sample(tp, min(args.per_class, len(tp)))
    jobs = [(str(p), 0) for p in au] + [(str(p), 1) for p in tp]
    print(f"Evaluating {len(au)} authentic + {len(tp)} tampered images with {args.workers} workers", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    rows, started = [], time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(analyse, path, label) for path, label in jobs]
        for done, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if done % 200 == 0 or done == len(futures):
                print(f"  {done}/{len(futures)} ({time.perf_counter() - started:.0f}s)", flush=True)

    rows.sort(key=lambda r: (r["label"], r["file"]))
    fields = ["file", "label", "type", "format", "width", "height", "seconds", "ela_peak", "orb_raw", "orb_consistent",
              "exif_tags", "ela_block_z_max", "ela_unusual_share", "ghost_block_z_max",
              "ghost_unusual_share", "jpeg_quality", "app_flag", "errors"]
    with open(args.out / "per_image.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    metrics = evaluate(rows)
    metrics["config"] = {"per_class": args.per_class, "seed": args.seed, "wall_seconds": round(time.perf_counter() - started, 1)}
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(summary_md(metrics), encoding="utf-8")
    plot(rows, metrics, args.out)
    print(summary_md(metrics))


if __name__ == "__main__":
    sys.exit(main())
