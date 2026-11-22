from pathlib import Path
import cv2
import numpy as np
from backend.processing.image.copy_move import analyze_copy_move

def test_copy_move_detects_duplicated_patch(tmp_path: Path):
    rng = np.random.default_rng(0)
    image = cv2.GaussianBlur((rng.random((240, 320, 3)) * 255).astype(np.uint8), (5, 5), 0)
    image[150:210, 220:290] = image[20:80, 20:90]
    source = tmp_path / "copied.png"
    cv2.imwrite(str(source), image)
    result = analyze_copy_move(source, tmp_path / "orb.png")
    assert (tmp_path / "orb.png").exists()
    assert result["raw_candidate_matches"] >= 4
    assert result["geometrically_consistent_matches"] >= 4
