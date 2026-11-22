from pathlib import Path
import cv2
import numpy as np
import pytest
from backend.processing.video.optical_flow import analyze_flow, flow_file


def _write_shifted_frames(tmp_path: Path, shifts: list[int], width: int = 480, height: int = 270) -> list[dict]:
    """Frames cut from one wide texture, each window moved `shift` px from the previous."""
    rng = np.random.default_rng(1)
    texture = cv2.GaussianBlur((rng.random((height, width + 200)) * 255).astype(np.uint8), (7, 7), 0)
    texture = cv2.normalize(texture, None, 0, 255, cv2.NORM_MINMAX)  # realistic contrast
    frames, offset = [], 0
    for index, shift in enumerate([0] + shifts):
        offset += shift
        image = cv2.cvtColor(np.ascontiguousarray(texture[:, offset:offset + width]), cv2.COLOR_GRAY2BGR)
        name = f"frame_{index:08d}.jpg"
        cv2.imwrite(str(tmp_path / name), image)
        frames.append({"file": name, "timestamp": float(index), "index": index})
    return frames


def test_flow_covers_every_pair_and_flags_jump(tmp_path: Path):
    shifts = [1, 1, 1, 1, 12, 1, 1, 1]          # one sudden jump between t=4 and t=5
    frames = _write_shifted_frames(tmp_path, shifts)
    result = analyze_flow(frames, tmp_path, tmp_path / "flow.png")
    assert result["timestamps"] == [float(i) for i in range(1, len(frames))]
    assert len(result["mean_magnitudes"]) == len(shifts)
    assert all((tmp_path / flow_file(f)).exists() for f in frames[1:])
    assert (tmp_path / "flow.png").exists()
    assert result["peak_timestamp"] == 5.0
    assert [s["timestamp"] for s in result["spikes"]] == [5.0]
    # Measured motion should be close to the true shift.
    assert result["mean_magnitudes"][4] == pytest.approx(12, rel=0.35)


def test_flow_reports_original_pixels_when_downscaled(tmp_path: Path):
    frames = _write_shifted_frames(tmp_path, [20, 20], width=960, height=540)   # analysed at half size
    result = analyze_flow(frames, tmp_path, tmp_path / "flow.png")
    assert result["analysed_width"] == 480
    assert result["mean_magnitudes"][0] == pytest.approx(20, rel=0.35)
    assert result["spikes"] == []


def test_flow_needs_two_frames(tmp_path: Path):
    frames = _write_shifted_frames(tmp_path, [])
    with pytest.raises(ValueError):
        analyze_flow(frames, tmp_path, tmp_path / "flow.png")
