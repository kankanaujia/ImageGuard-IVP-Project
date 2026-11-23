"""End-to-end tests of the REST API, run against a temporary data folder."""
import importlib
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """A fresh app whose database and evidence folders live in tmp_path."""
    monkeypatch.setenv("IMAGEGUARD_DATA_DIR", str(tmp_path))
    import backend.config, backend.database.session, backend.jobs, backend.main
    for module in (backend.config, backend.database.session, backend.jobs, backend.main):
        importlib.reload(module)
    with TestClient(backend.main.app) as client:
        client.data_dir = tmp_path
        client.main = backend.main
        yield client


def copied_patch_png() -> bytes:
    rng = np.random.default_rng(0)
    image = cv2.GaussianBlur((rng.random((240, 320, 3)) * 255).astype(np.uint8), (5, 5), 0)
    image[150:210, 220:290] = image[20:80, 20:90]
    return cv2.imencode(".png", image)[1].tobytes()


def small_avi(path: Path) -> bytes:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 48))
    for i in range(15):
        writer.write(np.full((48, 64, 3), (i * 15) % 255, np.uint8))
    writer.release()
    return path.read_bytes()


def upload_image(api, data=None, name="evidence.png", background=False):
    url = "/api/image/analyze" + ("?background=true" if background else "")
    return api.post(url, files={"file": (name, data if data is not None else copied_patch_png(), "image/png")})


def test_health_and_system_info(api):
    assert api.get("/api/health").json()["status"] == "healthy"
    info = api.get("/api/system-info").json()
    assert ".png" in info["image_formats"] and ".mp4" in info["video_formats"]


def test_image_analysis_end_to_end(api):
    r = upload_image(api)
    assert r.status_code == 200
    body = r.json(); ident = body["id"]
    algorithms = body["result"]["algorithms"]
    assert set(algorithms) == {"ela", "orb", "noise", "compression", "histogram", "metadata"}
    assert all(v["status"] == "completed" for v in algorithms.values())
    assert algorithms["orb"]["flagged"] and body["result"]["indicator_summary"]["candidate_indicators"] == 1
    assert {"map_visualization", "block_z_max"} <= set(algorithms["ela"])
    # Listing, details, artifacts, original, verification and the PDF report
    listed = api.get("/api/investigations").json()
    assert listed[0]["id"] == ident and listed[0]["candidate_indicators"] == 1
    assert api.get(f"/api/investigations/{ident}").json()["sha256"] == body["sha256"]
    for name in ("ela.png", "ela_map.png", "orb.png", "noise.png", "noise_map.png", "histogram.png"):
        assert api.get(f"/api/investigations/{ident}/artifacts/{name}").status_code == 200, name
    assert api.get(f"/api/investigations/{ident}/original").content == copied_patch_png()
    assert api.get(f"/api/investigations/{ident}/verify").json()["integrity_verified"] is True
    pdf = api.get(f"/api/reports/{ident}/download")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_integrity_check_detects_a_changed_original(api):
    ident = upload_image(api).json()["id"]
    stored = next((api.data_dir / "uploads").iterdir())
    stored.write_bytes(stored.read_bytes() + b"tampered")
    assert api.get(f"/api/investigations/{ident}/verify").json()["integrity_verified"] is False


def test_notes_are_saved_and_included(api):
    ident = upload_image(api).json()["id"]
    r = api.put(f"/api/investigations/{ident}/notes", json={"notes": "  Checked with the photographer.  "})
    assert r.status_code == 200 and r.json()["notes"] == "Checked with the photographer."
    assert api.get(f"/api/investigations/{ident}").json()["notes"] == "Checked with the photographer."
    assert api.get("/api/investigations").json()[0]["has_notes"] is True
    assert api.get(f"/api/reports/{ident}/download").content.startswith(b"%PDF")
    assert api.put(f"/api/investigations/{ident}/notes", json={"notes": "x" * 10_001}).status_code == 422


def test_delete_removes_record_and_files(api):
    ident = upload_image(api).json()["id"]
    api.get(f"/api/reports/{ident}/download")
    assert api.delete(f"/api/investigations/{ident}").status_code == 204
    assert api.get(f"/api/investigations/{ident}").status_code == 404
    assert not any((api.data_dir / "uploads").iterdir())
    assert not (api.data_dir / "outputs" / ident).exists() and not any((api.data_dir / "reports").iterdir())
    assert api.delete(f"/api/investigations/{ident}").status_code == 404


def test_background_job_reports_progress_and_result(api):
    r = upload_image(api, background=True)
    assert r.status_code == 202
    job = r.json()
    for _ in range(200):
        job = api.get(f"/api/jobs/{job['id']}").json()
        if job["status"] in ("done", "error"): break
        time.sleep(0.05)
    assert job["status"] == "done" and job["progress"] == 1.0
    assert api.get(f"/api/investigations/{job['investigation_id']}").status_code == 200
    assert api.get("/api/jobs/not-a-job").status_code == 404


def test_video_analysis(api, tmp_path):
    data = small_avi(tmp_path / "clip.avi")
    r = api.post("/api/video/analyze", files={"file": ("clip.avi", data, "video/x-msvideo")})
    assert r.status_code == 200
    result = r.json()["result"]
    assert all(result[k]["status"] == "completed" for k in ("frame_hashing", "ssim", "scene_detection", "optical_flow"))
    assert result["frame_hashing"]["motion_checked"] is True
    first = result["frames"][0]["file"]
    assert api.get(f"/api/investigations/{r.json()['id']}/artifacts/frames/{first}").status_code == 200


@pytest.mark.parametrize("name,data,status", [
    ("fake.jpg", b"not an image", 415),     # wrong content behind an image extension
    ("notes.txt", b"hello", 415),           # unsupported extension
    ("empty.png", b"", 400),                # empty upload
])
def test_rejected_uploads_leave_nothing_behind(api, name, data, status):
    assert upload_image(api, data, name).status_code == status
    assert not any((api.data_dir / "uploads").iterdir())
    assert api.get("/api/investigations").json() == []


def test_upload_size_limit(api, monkeypatch):
    monkeypatch.setattr(api.main, "MAX_BYTES", 1000)
    assert upload_image(api).status_code == 413
    assert not any((api.data_dir / "uploads").iterdir())


def test_artifact_paths_cannot_escape(api):
    ident = upload_image(api).json()["id"]
    assert api.get(f"/api/investigations/{ident}/artifacts/..%2F..%2Fimageguard.db").status_code in (400, 404)
    assert api.get(f"/api/investigations/{ident}/artifacts/missing.png").status_code == 404
    assert api.get("/api/investigations/unknown").status_code == 404
