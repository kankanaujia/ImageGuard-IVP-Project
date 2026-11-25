"""Pixel-level localisation on CASIA v2.0: do the heat maps point at the edited pixels?

For every tampered image that has a ground-truth mask ("CASIA 2 Groundtruth/<name>_gt.png"):
  * ELA heat map      - robust z of the per-block ELA difference (backend ela_block_z)
  * JPEG ghost map    - robust z of the per-block ghost dip across re-save qualities (backend ghost_block_scores)
  * Copy-move regions - 16 px discs around both ends of the largest consistent ORB group
Measured per image and averaged:
  * pixel AUC         - how well the map ranks edited pixels above unedited ones (0.5 = chance)
  * F1 / IoU          - of the app's own threshold (z >= 3.5; copy-move discs) against the mask
  * baseline F1       - marking the whole image as edited, for comparison
Masks whose size differs from their image are skipped (counted), not stretched.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe -m evaluation.casia_localization <CASIA2 folder> [--workers 10]
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from .casia_eval import IMAGE_EXTS, OUT, find_split, tamper_type

Z = 3.5
DISC = 16


def blocks_to_pixels(z: np.ndarray, shape: tuple[int, int], block: int = 16) -> np.ndarray:
    """Expand a block grid to pixels; the partial blocks at the right/bottom edge copy their neighbours."""
    full = np.kron(z, np.ones((block, block), dtype=np.float32))
    pad_h, pad_w = max(0, shape[0] - full.shape[0]), max(0, shape[1] - full.shape[1])
    return np.pad(full, ((0, pad_h), (0, pad_w)), mode="edge")[: shape[0], : shape[1]]


def pixel_auc(score: np.ndarray, truth: np.ndarray, rng: np.random.Generator, n: int = 40000) -> float | None:
    """Mann-Whitney AUC on a random pixel sample (ties count half)."""
    pos, neg = score[truth], score[~truth]
    if len(pos) == 0 or len(neg) == 0: return None
    pos = rng.choice(pos, min(n, len(pos)), replace=False); neg = rng.choice(neg, min(n, len(neg)), replace=False)
    allv = np.concatenate([pos, neg]); order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv)); ranks[order] = np.arange(1, len(allv) + 1)
    _, inv, counts = np.unique(allv, return_inverse=True, return_counts=True)           # average ranks for ties
    sums = np.bincount(inv, weights=ranks); ranks = (sums / counts)[inv]
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def f1_iou(pred: np.ndarray, truth: np.ndarray) -> tuple[float, float]:
    tp = np.logical_and(pred, truth).sum(); fp = np.logical_and(pred, ~truth).sum(); fn = np.logical_and(~pred, truth).sum()
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    return float(f1), float(iou)


def evaluate_image(image_path: str, mask_path: str) -> dict:
    import cv2
    from PIL import Image
    from backend.processing.image.ela import ela_block_z, ela_difference
    from backend.processing.image.jpeg_ghost import ghost_block_scores
    from backend.processing.image.heatmap import robust_z
    from backend.processing.image.copy_move import self_matches, consistent_groups, FLAG_MIN_GROUP, FLAG_MIN_SHIFT
    name = Path(image_path).name
    row = {"file": name, "type": tamper_type(name)}
    with Image.open(image_path) as im: rgb = im.convert("RGB")
    with Image.open(mask_path) as m: truth = np.asarray(m.convert("L")) > 127
    if truth.shape != (rgb.height, rgb.width):
        return {**row, "skipped": "mask size differs from image"}
    if not truth.any() or truth.all():
        return {**row, "skipped": "empty or full mask"}
    rng = np.random.default_rng(0)
    p = float(truth.mean()); row["tampered_fraction"] = p
    row["baseline_f1"] = 2 * p / (1 + p)
    with tempfile.TemporaryDirectory() as tmp:
        ela = blocks_to_pixels(ela_block_z(ela_difference(rgb, Path(tmp) / "w.jpg", 90)), truth.shape)
    gray = cv2.cvtColor(np.asarray(rgb)[:, :, ::-1], cv2.COLOR_BGR2GRAY)
    ghost = blocks_to_pixels(robust_z(ghost_block_scores(rgb)[0]), truth.shape)
    for key, score in (("ela", ela), ("ghost", ghost)):
        row[f"{key}_auc"] = pixel_auc(score, truth, rng)
        row[f"{key}_f1"], row[f"{key}_iou"] = f1_iou(score >= Z, truth)
    _, a, b = self_matches(gray)
    groups = consistent_groups(a, b)
    mask = np.zeros(truth.shape, np.uint8)
    if groups:
        best = groups[0]
        shift = float(np.median(np.linalg.norm(b[best] - a[best], axis=1)))
        if len(best) >= FLAG_MIN_GROUP and shift >= FLAG_MIN_SHIFT:          # only when the app would flag it
            for pt in np.vstack([a[best], b[best]]):
                cv2.circle(mask, (int(pt[0]), int(pt[1])), DISC, 1, -1)
    row["cm_flagged"] = bool(mask.any())
    row["cm_f1"], row["cm_iou"] = f1_iou(mask.astype(bool), truth)
    return row


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if "skipped" not in r]
    out = {"evaluated": len(ok), "skipped": {}, "by_type": {}}
    for r in rows:
        if "skipped" in r: out["skipped"][r["skipped"]] = out["skipped"].get(r["skipped"], 0) + 1
    for kind in ("all", "copy-move", "splicing"):
        sub = ok if kind == "all" else [r for r in ok if r["type"] == kind]
        if not sub: continue
        mean = lambda k: float(np.mean([r[k] for r in sub if r.get(k) is not None]))
        flagged = [r for r in sub if r["cm_flagged"]]
        out["by_type"][kind] = {
            "images": len(sub), "mean_tampered_fraction": mean("tampered_fraction"), "baseline_f1": mean("baseline_f1"),
            "ela": {"pixel_auc": mean("ela_auc"), "f1": mean("ela_f1"), "iou": mean("ela_iou")},
            "ghost": {"pixel_auc": mean("ghost_auc"), "f1": mean("ghost_f1"), "iou": mean("ghost_iou")},
            "copy_move": {"flagged_share": len(flagged) / len(sub), "f1_all": mean("cm_f1"), "iou_all": mean("cm_iou"),
                          "f1_when_flagged": float(np.mean([r["cm_f1"] for r in flagged])) if flagged else None}}
    return out


def summary_md(s: dict) -> str:
    lines = ["# CASIA v2.0 pixel-level localisation", "", f"Images evaluated: {s['evaluated']}; skipped: {s['skipped']}", "",
             "| Images | Method | Pixel AUC | F1 | IoU |", "|---|---|---|---|---|"]
    for kind, v in s["by_type"].items():
        lines.append(f"| {kind} ({v['images']}) | ELA heat map | {v['ela']['pixel_auc']:.3f} | {v['ela']['f1']:.3f} | {v['ela']['iou']:.3f} |")
        lines.append(f"| {kind} | JPEG ghost map | {v['ghost']['pixel_auc']:.3f} | {v['ghost']['f1']:.3f} | {v['ghost']['iou']:.3f} |")
        cm = v["copy_move"]
        lines.append(f"| {kind} | Copy-move regions (flagged {100 * cm['flagged_share']:.1f}%) | - | {cm['f1_all']:.3f} | {cm['iou_all']:.3f} |")
        lines.append(f"| {kind} | Baseline: whole image | 0.500 | {v['baseline_f1']:.3f} | - |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()
    tp = find_split(args.root, "Tp")
    gt_dir = next(p for p in args.root.rglob("*") if p.is_dir() and "groundtruth" in p.name.lower())
    jobs = []
    for image in sorted(tp.iterdir()):
        if image.suffix.lower() not in IMAGE_EXTS: continue
        mask = gt_dir / f"{image.stem}_gt.png"
        if mask.exists(): jobs.append((str(image), str(mask)))
    print(f"{len(jobs)} tampered images with ground-truth masks", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(evaluate_image, *zip(*jobs), chunksize=16))
    summary = summarise(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "localization.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "localization_summary.md").write_text(summary_md(summary), encoding="utf-8")
    print(summary_md(summary))


if __name__ == "__main__":
    sys.exit(main())
