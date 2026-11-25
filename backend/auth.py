"""Accounts and sign-in sessions.

Passwords are stored as salted PBKDF2-SHA256 hashes (Python's hashlib; no extra
dependency). Signing in creates a random session token: the browser keeps it in an
HttpOnly cookie, and the database keeps only its SHA-256, so a leaked database does
not reveal usable sessions.
"""
from __future__ import annotations
import hashlib, hmac, re, secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .database.models import Investigation, User, UserSession
from .database.session import SessionLocal

COOKIE = "imageguard_session"
SESSION_DAYS = 7
ITERATIONS = 240_000
USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD, MAX_PASSWORD = 8, 128


def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != "pbkdf2_sha256": return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, TypeError):
        return False


# A hash to check against when the username does not exist, so both cases take the same time.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_credentials(username: str, password: str) -> str:
    username = username.strip()
    if not USERNAME.match(username):
        raise HTTPException(422, "Username must be 3-32 letters, digits, '.', '_' or '-'")
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise HTTPException(422, f"Password must be {MIN_PASSWORD} to {MAX_PASSWORD} characters")
    return username


def create_user(db: Session, username: str, password: str) -> User:
    username = validate_credentials(username, password)
    if db.query(User).filter(User.username_key == username.lower()).first():
        raise HTTPException(409, "That username is taken")
    first = db.query(User).count() == 0
    user = User(username=username, username_key=username.lower(), password_hash=hash_password(password), is_admin=first)
    db.add(user); db.flush()
    if first:  # the first account takes over investigations made before accounts existed
        db.query(Investigation).filter(Investigation.owner_id.is_(None)).update({Investigation.owner_id: user.id})
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username_key == username.strip().lower()).first()
    if not verify_password(password, user.password_hash if user else _DUMMY_HASH) or not user:
        raise HTTPException(401, "Wrong username or password")
    return user


def start_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(UserSession.expires_at < now).delete()   # tidy expired sessions
    db.add(UserSession(token_hash=_token_hash(token), user_id=user.id, created_at=now, expires_at=now + timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", path="/")


def end_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        db.query(UserSession).filter(UserSession.token_hash == _token_hash(token)).delete(); db.commit()
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency for every protected endpoint: the signed-in user, or 401."""
    token = request.cookies.get(COOKIE)
    if token:
        session = db.get(UserSession, _token_hash(token))
        if session:
            expires = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
            if expires > datetime.now(timezone.utc):
                user = db.get(User, session.user_id)
                if user: return user
    raise HTTPException(401, "Please sign in")


def public_user(user: User) -> dict:
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}
