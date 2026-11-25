"""ImageGuard FastAPI application."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4
import json, mimetypes, shutil
import cv2
from fastapi import Body, Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from . import jobs
from .config import OUTPUTS, REPORTS, UPLOADS
from .database.session import SessionLocal, init_db
from .database.models import Investigation, User
from .auth import authenticate, create_user, current_user, end_session, get_db, public_user, start_session
from .utils.file_integrity import sha256_file, safe_extension
from .processing.analysis_engine import run_image, run_video
from .processing.image.validation import validate_image
from .reports.pdf import generate_report

MAX_BYTES = 100 * 1024 * 1024
MAX_NOTES = 10_000
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    for directory in (UPLOADS, OUTPUTS, REPORTS): directory.mkdir(parents=True, exist_ok=True)
    init_db(); yield

app = FastAPI(title="ImageGuard API", version="1.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def report_path(ident: str) -> Path:
    """Versioned so reports cached by older releases are regenerated in the current format."""
    return REPORTS/f"{ident}-v2.pdf"

def get_record(db: Session, ident: str, user: User) -> Investigation:
    """The investigation if it belongs to the user; someone else's looks the same as a missing one."""
    record = db.get(Investigation, ident)
    if not record or record.owner_id != user.id: raise HTTPException(404, "Investigation not found")
    return record

def remove_files(ident: str, stored_name: str | None) -> None:
    """Delete everything stored for one investigation (original, outputs, report)."""
    if stored_name: (UPLOADS/stored_name).unlink(missing_ok=True)
    shutil.rmtree(OUTPUTS/ident, ignore_errors=True)
    for old in (REPORTS/f"{ident}.pdf", report_path(ident)): old.unlink(missing_ok=True)

@app.get("/")
def root(): return {"name":"ImageGuard API", "docs":"/docs", "status":"ready"}

@app.get("/api/health")
def health(): return {"status":"healthy", "database": "sqlite", "opencv": cv2.__version__}

@app.get("/api/system-info")
def system_info(): return {"max_upload_bytes":MAX_BYTES, "image_formats":sorted(IMAGE_EXTS), "video_formats":sorted(VIDEO_EXTS)}

# ---------------------------------------------------------------- accounts
def credentials(username: str = Body(..., max_length=64), password: str = Body(..., max_length=256)) -> tuple[str, str]:
    return username, password

@app.post("/api/auth/register", status_code=201)
def register(response: Response, creds: tuple[str, str] = Depends(credentials), db: Session = Depends(get_db)):
    user = create_user(db, *creds)
    start_session(db, user, response)
    return public_user(user)

@app.post("/api/auth/login")
def login(response: Response, creds: tuple[str, str] = Depends(credentials), db: Session = Depends(get_db)):
    user = authenticate(db, *creds)
    start_session(db, user, response)
    return public_user(user)

@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    response = Response(status_code=204)
    end_session(db, request, response)
    return response

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return public_user(user)

# ---------------------------------------------------------------- intake and analysis
async def save_upload(file: UploadFile, media_type: str) -> dict:
    """Stream the upload to disk under a random name, validate its content and hash it."""
    ext = safe_extension(file.filename or "")
    allowed = IMAGE_EXTS if media_type == "image" else VIDEO_EXTS
    if ext not in allowed: raise HTTPException(415, "File extension is not supported")
    ident = str(uuid4()); stored = f"{ident}{ext}"; path = UPLOADS/stored
    size = 0
    try:
        with path.open("wb") as target:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_BYTES: raise HTTPException(413, "Maximum upload size is 100 MB")
                target.write(chunk)
        if size == 0: raise HTTPException(400, "Uploaded file is empty")
        if media_type == "image":
            try: validate_image(path)
            except Exception as exc: raise HTTPException(415, "File content is not a supported image") from exc
        else:
            cap = cv2.VideoCapture(str(path)); valid = cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0; cap.release()
            if not valid: raise HTTPException(415, "File content is not a readable video")
        return {"id": ident, "stored": stored, "path": path, "ext": ext, "size": size, "media_type": media_type,
                "original_name": (file.filename or "evidence")[:255], "sha256": sha256_file(path)}
    except Exception:
        remove_files(ident, stored)
        raise

def analyze_and_record(upload: dict, owner_id: int, progress: Callable[[float, str], None] | None = None) -> tuple[Investigation, dict]:
    """Run the checks on a saved upload, store the record and write the PDF report."""
    ident, out_dir = upload["id"], OUTPUTS/upload["id"]
    db = SessionLocal()
    try:
        runner = run_image if upload["media_type"] == "image" else run_video
        result = runner(upload["path"], out_dir, progress=progress)
        if progress: progress(0.97, "Saving results")
        record = Investigation(id=ident, media_type=upload["media_type"], original_name=upload["original_name"], stored_name=upload["stored"],
            mime_type=mimetypes.guess_type(f"evidence{upload['ext']}")[0] or "application/octet-stream", size_bytes=upload["size"],
            sha256=upload["sha256"], created_at=datetime.now(timezone.utc), result_json=json.dumps(result, default=str), notes="", owner_id=owner_id)
        db.add(record); db.commit()
    except Exception as exc:
        db.rollback(); remove_files(ident, upload["stored"])
        raise HTTPException(500, f"Analysis failed: {exc}") from exc
    finally:
        db.close()
    try:
        if progress: progress(0.98, "Writing PDF report")
        REPORTS.mkdir(parents=True, exist_ok=True); generate_report(record, result, report_path(ident), out_dir)
    except Exception:
        pass  # the findings are saved; the download endpoint regenerates the report
    return record, result

def investigation_json(record: Investigation, result: dict):
    return {"id":record.id, "media_type":record.media_type, "original_file":{"name":record.original_name,"size_bytes":record.size_bytes,"mime_type":record.mime_type},
            "sha256":record.sha256, "created_at":record.created_at.isoformat(), "notes":record.notes or "", "result":result}

async def analyze(file: UploadFile, media_type: str, background: bool, user: User):
    upload = await save_upload(file, media_type)
    if background:
        job = jobs.submit(media_type, upload["original_name"], lambda progress: analyze_and_record(upload, user.id, progress)[0].id, owner_id=user.id)
        job.pop("owner_id", None)
        return JSONResponse(job, status_code=202)
    record, result = analyze_and_record(upload, user.id)
    return investigation_json(record, result)

@app.post("/api/image/analyze")
async def analyze_image(file: UploadFile = File(...), background: bool = Query(False, description="Return a job id at once and analyse in the background"),
                        user: User = Depends(current_user)):
    return await analyze(file, "image", background, user)

@app.post("/api/video/analyze")
async def analyze_video(file: UploadFile = File(...), background: bool = Query(False, description="Return a job id at once and analyse in the background"),
                        user: User = Depends(current_user)):
    return await analyze(file, "video", background, user)

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, user: User = Depends(current_user)):
    job = jobs.snapshot(job_id)
    if not job or job.pop("owner_id", None) != user.id: raise HTTPException(404, "Job not found")
    return job

# ---------------------------------------------------------------- investigations
@app.get("/api/investigations")
def investigations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    records = db.query(Investigation).filter(Investigation.owner_id == user.id).order_by(Investigation.created_at.desc()).limit(500).all()
    def indicators(record: Investigation) -> int:
        try: return int(json.loads(record.result_json).get("indicator_summary", {}).get("candidate_indicators", 0))
        except (ValueError, TypeError, AttributeError): return 0
    return [{"id":r.id,"media_type":r.media_type,"original_name":r.original_name,"size_bytes":r.size_bytes,"sha256":r.sha256,
             "created_at":r.created_at.isoformat(),"candidate_indicators":indicators(r),"has_notes":bool(r.notes)} for r in records]

@app.get("/api/investigations/{ident}")
def investigation(ident: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    return investigation_json(record, json.loads(record.result_json))

@app.delete("/api/investigations/{ident}", status_code=204)
def delete_investigation(ident: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    stored = record.stored_name
    db.delete(record); db.commit()
    remove_files(ident, stored)
    return Response(status_code=204)

@app.put("/api/investigations/{ident}/notes")
def update_notes(ident: str, notes: str = Body(..., embed=True, max_length=MAX_NOTES), db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    record.notes = notes.strip()
    db.commit()
    report_path(ident).unlink(missing_ok=True)  # the next download regenerates the report with the notes
    return {"id": ident, "notes": record.notes}

def serve_artifact(db: Session, user: User, ident: str, name: str, *parts: str) -> FileResponse:
    get_record(db, ident, user)
    if not name or Path(name).name != name: raise HTTPException(400, "Invalid artifact name")
    if not (OUTPUTS/ident).is_dir(): raise HTTPException(404, "Investigation not found")
    path = OUTPUTS.joinpath(ident, *parts, name)
    if not path.is_file(): raise HTTPException(404, "Artifact not found")
    return FileResponse(path, filename=name)

@app.get("/api/investigations/{ident}/artifacts/{name}")
def artifact(ident: str, name: str, db: Session = Depends(get_db), user: User = Depends(current_user)): return serve_artifact(db, user, ident, name)

@app.get("/api/investigations/{ident}/artifacts/frames/{name}")
def frame_artifact(ident: str, name: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return serve_artifact(db, user, ident, name, "frames")

@app.get("/api/investigations/{ident}/original")
def original_file(ident: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    path = UPLOADS / record.stored_name
    if not path.is_file(): raise HTTPException(404,"Original evidence is unavailable")
    return FileResponse(path, media_type=record.mime_type, filename=record.original_name)

@app.get("/api/reports/{ident}")
def report_info(ident: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    get_record(db, ident, user)
    return {"id":ident,"download_url":f"/api/reports/{ident}/download"}

@app.get("/api/reports/{ident}/download")
def download_report(ident: str, inline: bool = Query(False, description="Show in the browser instead of downloading"), db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    path = report_path(ident)
    if not path.exists(): generate_report(record,json.loads(record.result_json),path,OUTPUTS/ident)
    return FileResponse(path, media_type="application/pdf", filename=f"ImageGuard-{ident}.pdf",
                        content_disposition_type="inline" if inline else "attachment")

@app.get("/api/investigations/{ident}/verify")
def verify_integrity(ident: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_record(db, ident, user)
    source = UPLOADS/record.stored_name
    if not source.is_file(): raise HTTPException(404,"Original evidence is unavailable")
    current = sha256_file(source)
    return {"investigation_id":ident,"stored_sha256":record.sha256,"current_sha256":current,"integrity_verified":current == record.sha256}
