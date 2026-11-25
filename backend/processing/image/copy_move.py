"""ORB self-match screening for possible copy-move regions.

1. Detect ORB keypoints and match the image against itself (ratio test, minimum separation).
2. Orient each pair consistently and remove mirrored duplicates (A->B and B->A).
3. Find groups of matches that agree on one shift/rotation/scale with repeated RANSAC.
4. Flag the image only when the largest group has at least FLAG_MIN_GROUP matches AND the
   copy lies at least FLAG_MIN_SHIFT px from its source. Natural repetition (textures,
   windows, foliage) mostly matches its close neighbours, while copied regions are usually
   moved further away.
The step-4 thresholds were chosen on one half of CASIA v2.0 (highest recall with at most
5% false alarms on authentic images) and checked on the other half: false alarms fell from
10.6% to 4.7% and precision rose from 0.63 to 0.76, at the cost of recall (0.41 -> 0.33).
See evaluation/copy_move_tuning.py.
"""
from pathlib import Path
import cv2
import numpy as np

RATIO = 0.78
MIN_DISTANCE = 24.0       # px between a keypoint and its match
RANSAC_PX = 4.0
MIN_GROUP = 4             # smallest group RANSAC may report
FLAG_MIN_GROUP = 5        # flag only groups at least this large ...
FLAG_MIN_SHIFT = 40.0     # ... whose copy lies at least this far (median px) from its source


SIFT_RATIO = 0.6          # SIFT's float descriptors separate better, so a stricter ratio test is used


def detect(gray: np.ndarray, method: str):
    """Keypoints, descriptors and the matching norm for 'orb' or 'sift'."""
    if method == "sift":
        # A low contrast threshold finds keypoints in flatter regions, where small copies often are.
        kp, desc = cv2.SIFT_create(nfeatures=4000, contrastThreshold=0.02).detectAndCompute(gray, None)
        return kp, desc, cv2.NORM_L2
    kp, desc = cv2.ORB_create(nfeatures=2500).detectAndCompute(gray, None)
    return kp, desc, cv2.NORM_HAMMING


def self_matches(gray: np.ndarray, method: str = "orb", ratio: float | None = None, min_distance: float = MIN_DISTANCE):
    """Keypoints and oriented, de-duplicated self-matches as two (n, 2) point arrays."""
    ratio = ratio if ratio is not None else (SIFT_RATIO if method == "sift" else RATIO)
    keypoints, descriptors, norm = detect(gray, method)
    pairs = set()
    if descriptors is not None and len(descriptors) >= 3:
        raw = cv2.BFMatcher(norm).knnMatch(descriptors, descriptors, k=3)
        for candidates in raw:
            candidates = sorted((m for m in candidates if m.queryIdx != m.trainIdx), key=lambda m: m.distance)
            if len(candidates) < 2: continue
            first, second = candidates[:2]
            if first.distance >= ratio * second.distance: continue
            p, q = keypoints[first.queryIdx].pt, keypoints[first.trainIdx].pt
            if np.hypot(p[0] - q[0], p[1] - q[1]) < min_distance: continue
            # Orient so the pair always points the same way, which merges A->B with B->A.
            pairs.add((p, q) if (p[1], p[0]) <= (q[1], q[0]) else (q, p))
    pts = np.float32([[*p, *q] for p, q in sorted(pairs)]).reshape(-1, 4)
    return keypoints, pts[:, :2], pts[:, 2:]


def consistent_groups(a: np.ndarray, b: np.ndarray, max_groups: int = 3) -> list[np.ndarray]:
    """Repeated RANSAC: index arrays of match groups that share one partial-affine transform."""
    groups, remaining = [], np.arange(len(a))
    while len(remaining) >= MIN_GROUP and len(groups) < max_groups:
        model, inliers = cv2.estimateAffinePartial2D(a[remaining], b[remaining], method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX)
        if model is None or inliers is None: break
        mask = inliers.ravel().astype(bool)
        if mask.sum() < MIN_GROUP: break
        groups.append(remaining[mask]); remaining = remaining[~mask]
    return groups


def spread(points: np.ndarray) -> float:
    """Median distance of points from their centre: small for one compact region."""
    return float(np.median(np.linalg.norm(points - np.median(points, axis=0), axis=1))) if len(points) else 0.0


def analyze_copy_move(source: Path, output: Path, min_distance: float = MIN_DISTANCE) -> dict:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unsupported or invalid image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    keypoints, a, b = self_matches(gray, min_distance=min_distance)
    groups = consistent_groups(a, b)
    best = groups[0] if groups else np.array([], dtype=int)
    group_spread = spread(a[best]) if len(best) else 0.0
    shift = float(np.median(np.linalg.norm(b[best] - a[best], axis=1))) if len(best) else 0.0
    flagged = len(best) >= FLAG_MIN_GROUP and shift >= FLAG_MIN_SHIFT

    vis = image.copy()
    shown = best if len(best) else np.arange(min(len(a), 60))
    for i in shown[:150]:
        p, q = tuple(int(v) for v in a[i]), tuple(int(v) for v in b[i])
        colour = (80, 200, 255) if len(best) else (160, 160, 160)
        cv2.line(vis, p, q, colour, 1, cv2.LINE_AA)
        cv2.circle(vis, p, 3, (60, 220, 60), -1, cv2.LINE_AA); cv2.circle(vis, q, 3, (60, 60, 240), -1, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), vis):
        raise OSError("Could not save ORB visualization")
    return {"keypoints": len(keypoints), "raw_candidate_matches": int(len(a)),
            "geometrically_consistent_matches": int(len(best)), "candidate_matches": int(len(best)) if flagged else 0,
            "consistent_groups": len(groups), "group_spread_px": round(group_spread, 1), "copy_shift_px": round(shift, 1),
            "flagged": bool(flagged), "visualization": output.name,
            "interpretation": "Lines join matched keypoints (green = source, red = copy). Repeated texture can produce matches; these candidates require human review and are not proof of editing."}
