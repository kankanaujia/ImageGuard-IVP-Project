"""Tests for the compression check, the ELA heat map, JPEG ghosts and motion-confirmed repeats."""
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from backend.processing.analysis_engine import confirm_repeats
from backend.processing.image.compression import analyze_compression
from backend.processing.image.ela import analyze_ela
from backend.processing.image.jpeg_ghost import analyze_ghost, ghost_block_scores


def textured(h=256, w=320, seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return cv2.GaussianBlur((rng.random((h, w, 3)) * 255).astype(np.uint8), (5, 5), 0)


def test_compression_reads_jpeg_quality_and_ijg_tables(tmp_path: Path):
    for quality in (60, 75, 92):
        path = tmp_path / f"q{quality}.jpg"
        Image.fromarray(textured()).save(path, "JPEG", quality=quality)
        result = analyze_compression(path)
        assert result["is_jpeg"] and result["estimated_quality"] == quality and result["standard_ijg_tables"]
    png = tmp_path / "x.png"; Image.fromarray(textured()).save(png)
    assert analyze_compression(png)["is_jpeg"] is False


def test_ela_map_points_at_region_with_different_compression(tmp_path: Path):
    base = textured(seed=1)
    def jpeg(img, q):
        buf = io.BytesIO(); Image.fromarray(img).save(buf, "JPEG", quality=q); return np.array(Image.open(buf).convert("RGB"))
    composite = jpeg(base, 70)                                # whole image compressed at 70 ...
    composite[96:160, 160:240] = base[96:160, 160:240]        # ... except a pasted, never-compressed patch
    path = tmp_path / "composite.png"; Image.fromarray(composite).save(path)
    result = analyze_ela(path, tmp_path / "ela.png", map_output=tmp_path / "ela_map.png")
    assert (tmp_path / "ela_map.png").exists() and result["block_z_max"] > 3.5
    from backend.processing.image.ela import ela_block_z, ela_difference
    z = ela_block_z(ela_difference(Image.fromarray(composite), tmp_path / "w.jpg", 90))
    y, x = np.unravel_index(np.argmax(z), z.shape)
    assert 96 <= y * 16 + 8 < 160 and 160 <= x * 16 + 8 < 240   # strongest block lies inside the patch


def test_jpeg_ghost_finds_region_saved_at_another_quality(tmp_path: Path):
    def jpeg(img, q):
        buf = io.BytesIO(); Image.fromarray(img).save(buf, "JPEG", quality=q); return np.array(Image.open(buf).convert("RGB"))
    host, donor = textured(seed=1), jpeg(textured(seed=2), 60)     # the donor was saved at quality 60
    composite = host.copy(); composite[96:176, 160:256] = donor[96:176, 160:256]
    final = jpeg(composite, 92)                                     # the composite is saved at 92
    path = tmp_path / "composite.png"; Image.fromarray(final).save(path)
    result = analyze_ghost(path, tmp_path / "ghost_map.png")
    assert (tmp_path / "ghost_map.png").exists() and result["block_z_max"] > 3.5 and result["ghost_quality"] == 60
    from backend.processing.image.heatmap import robust_z
    z = robust_z(ghost_block_scores(Image.fromarray(final))[0])
    y, x = np.unravel_index(np.argmax(z), z.shape)
    assert 96 <= y * 16 + 8 < 176 and 160 <= x * 16 + 8 < 256       # strongest block lies inside the pasted region


def test_repeats_need_both_similar_hash_and_no_motion():
    results = {"frame_hashing": {"status": "completed", "pairs": [
                   {"previous_timestamp": 0.0, "timestamp": 1.0, "hamming_distance": 2, "kind": "near_duplicate"},
                   {"previous_timestamp": 1.0, "timestamp": 2.0, "hamming_distance": 0, "kind": "exact"}]},
               "optical_flow": {"status": "completed", "timestamps": [1.0, 2.0], "mean_magnitudes": [6.5, 0.2]}}
    confirm_repeats(results)
    pairs = results["frame_hashing"]["pairs"]
    assert [p["timestamp"] for p in pairs] == [2.0]             # the panning pair (6.5 px) is dropped
    assert results["frame_hashing"]["hash_only_pairs"] == 2 and results["frame_hashing"]["motion_checked"]
    no_flow = {"frame_hashing": {"status": "completed", "pairs": [{"timestamp": 1.0}]}, "optical_flow": {"status": "error"}}
    confirm_repeats(no_flow)
    assert len(no_flow["frame_hashing"]["pairs"]) == 1 and no_flow["frame_hashing"]["motion_checked"] is False
