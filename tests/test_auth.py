"""Accounts: registration rules, sign-in and sign-out, and that each analyst sees only their own cases."""
import importlib

import pytest
from fastapi.testclient import TestClient

from tests.test_api import copied_patch_png

PASSWORD = "correct-horse"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGEGUARD_DATA_DIR", str(tmp_path))
    import backend.config, backend.database.session, backend.jobs, backend.auth, backend.main
    for module in (backend.config, backend.database.session, backend.jobs, backend.auth, backend.main):
        importlib.reload(module)
    return backend.main.app


def client(app, username=None, register=True) -> TestClient:
    c = TestClient(app)
    c.__enter__()
    if username:
        path = "/api/auth/register" if register else "/api/auth/login"
        assert c.post(path, json={"username": username, "password": PASSWORD}).status_code in (200, 201)
    return c


def upload(c) -> str:
    r = c.post("/api/image/analyze", files={"file": ("e.png", copied_patch_png(), "image/png")})
    assert r.status_code == 200
    return r.json()["id"]


def test_everything_but_health_needs_sign_in(app):
    c = client(app)
    assert c.get("/api/health").status_code == 200
    for path in ("/api/auth/me", "/api/investigations", "/api/investigations/x", "/api/jobs/x", "/api/reports/x/download",
                 "/api/investigations/x/artifacts/ela.png", "/api/investigations/x/original"):
        assert c.get(path).status_code == 401, path
    assert c.post("/api/image/analyze", files={"file": ("e.png", copied_patch_png(), "image/png")}).status_code == 401


def test_register_login_logout(app):
    c = client(app)
    r = c.post("/api/auth/register", json={"username": "Elisha", "password": PASSWORD})
    assert r.status_code == 201 and r.json() == {"id": 1, "username": "Elisha", "is_admin": True}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert c.get("/api/auth/me").json()["username"] == "Elisha"
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/login", json={"username": "elisha", "password": "wrong-password"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "nobody", "password": PASSWORD}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "elisha", "password": PASSWORD}).status_code == 200   # names are case-insensitive
    assert c.get("/api/auth/me").json()["username"] == "Elisha"


@pytest.mark.parametrize("username,password,status", [
    ("ab", PASSWORD, 422),               # too short
    ("has space", PASSWORD, 422),        # not allowed characters
    ("kanishka", "short", 422),          # password too short
])
def test_register_rejects_bad_credentials(app, username, password, status):
    assert client(app).post("/api/auth/register", json={"username": username, "password": password}).status_code == status


def test_usernames_are_unique_ignoring_case(app):
    client(app, "kanishka")
    assert client(app).post("/api/auth/register", json={"username": "Kanishka", "password": PASSWORD}).status_code == 409


def test_analysts_only_see_their_own_investigations(app):
    alice, bob = client(app, "alice"), client(app, "bob")
    ident = upload(alice)
    assert [i["id"] for i in alice.get("/api/investigations").json()] == [ident]
    assert bob.get("/api/investigations").json() == []
    for path in (f"/api/investigations/{ident}", f"/api/investigations/{ident}/artifacts/ela.png", f"/api/investigations/{ident}/original",
                 f"/api/reports/{ident}/download", f"/api/investigations/{ident}/verify"):
        assert bob.get(path).status_code == 404, path
        assert alice.get(path).status_code == 200, path
    assert bob.put(f"/api/investigations/{ident}/notes", json={"notes": "mine now"}).status_code == 404
    assert bob.delete(f"/api/investigations/{ident}").status_code == 404
    assert alice.get(f"/api/investigations/{ident}").status_code == 200


def test_background_jobs_are_private(app):
    alice, bob = client(app, "alice"), client(app, "bob")
    r = alice.post("/api/image/analyze?background=true", files={"file": ("e.png", copied_patch_png(), "image/png")})
    job = r.json()
    assert r.status_code == 202 and "owner_id" not in job
    assert bob.get(f"/api/jobs/{job['id']}").status_code == 404
    assert alice.get(f"/api/jobs/{job['id']}").status_code == 200


def test_first_account_claims_investigations_made_before_accounts(app):
    from backend.database.session import SessionLocal, init_db
    init_db()
    from backend.database.models import Investigation
    db = SessionLocal()
    db.add(Investigation(id="legacy", media_type="image", original_name="old.png", stored_name="legacy.png", mime_type="image/png",
                         size_bytes=1, sha256="0" * 64, result_json="{}", notes=""))
    db.commit(); db.close()
    first, second = client(app, "first"), client(app, "second")
    assert [i["id"] for i in first.get("/api/investigations").json()] == ["legacy"]
    assert second.get("/api/investigations").json() == []
