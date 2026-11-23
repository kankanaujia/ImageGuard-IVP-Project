"""Tests for the compression check, the localised ELA / noise maps and motion-confirmed repeats."""
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from backend.processing.analysis_engine import confirm_repeats
from backend.processing.image.compression import analyze_compression
from backend.processing.image.ela import analyze_ela
from backend.processing.image.noise_analysis import analyze_noise


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


def test_noise_map_points_at_region_with_different_noise(tmp_path: Path):
    rng = np.random.default_rng(2)
    image = np.clip(textured(seed=3).astype(float) + rng.normal(0, 2, (256, 320, 3)), 0, 255)
    image[64:128, 192:272] += rng.normal(0, 18, (64, 80, 3))      # a much noisier pasted region
    path = tmp_path / "noisy.png"; cv2.imwrite(str(path), np.clip(image, 0, 255).astype(np.uint8))
    result = analyze_noise(path, tmp_path / "noise.png", map_output=tmp_path / "noise_map.png")
    assert result["block_z_max_abs"] > 3.5 and 0 < result["unusual_block_share"] < 0.2
    from backend.processing.image.noise_analysis import noise_block_z
    z = np.abs(noise_block_z(cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)))
    y, x = np.unravel_index(np.argmax(z), z.shape)
    assert 64 <= y * 16 + 8 < 128 and 192 <= x * 16 + 8 < 272


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
