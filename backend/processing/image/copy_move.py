"""ORB self-match screening for possible copy-move regions."""
from pathlib import Path
import cv2
import numpy as np

def analyze_copy_move(source: Path, output: Path, min_distance: float = 24.0) -> dict:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unsupported or invalid image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=2500)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    matches = []
    filtered_matches = []
    if descriptors is not None and len(descriptors) >= 2:
        # Query one keypoint against every other keypoint in the same image.
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        raw = matcher.knnMatch(descriptors, descriptors, k=min(3, len(descriptors)))
        for pair in raw:
            # Self-match at distance 0 is always first. Compare the best distinct
            # keypoint to the next distinct keypoint, never to the query itself.
            candidates = [match for match in pair if match.queryIdx != match.trainIdx]
            if len(candidates) < 2:
                continue
            candidates.sort(key=lambda match: match.distance)
            first, second = candidates[:2]
            p1, p2 = keypoints[first.queryIdx].pt, keypoints[first.trainIdx].pt
            separation = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5
            if first.queryIdx != first.trainIdx and first.distance < 0.78 * second.distance and separation >= min_distance:
                matches.append(first)
        if len(matches) >= 4:
            points_a = np.float32([keypoints[m.queryIdx].pt for m in matches])
            points_b = np.float32([keypoints[m.trainIdx].pt for m in matches])
            matrix, inliers = cv2.estimateAffinePartial2D(
                points_a, points_b, method=cv2.RANSAC, ransacReprojThreshold=4.0
            )
            if matrix is not None and inliers is not None:
                filtered_matches = [m for m, accepted in zip(matches, inliers.ravel()) if accepted]
        # Without enough matches, retain spatially separated candidates and
        # make the lack of geometric evidence clear in the returned result.
        if not filtered_matches:
            filtered_matches = matches
    vis = cv2.drawMatches(image, keypoints, image, keypoints, filtered_matches[:100], None,
                          flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), vis):
        raise OSError("Could not save ORB visualization")
    return {"keypoints": len(keypoints), "raw_candidate_matches": len(matches),
            "geometrically_consistent_matches": len(filtered_matches), "candidate_matches": len(filtered_matches), "visualization": output.name,
            "interpretation": "Repeated texture can produce matches; these candidates require human review and are not proof of editing."}
