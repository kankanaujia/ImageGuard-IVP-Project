"""ImageGuard FastAPI application."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json, mimetypes
import cv2
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .database.session import SessionLocal, init_db
from .database.models import Investigation
from .utils.file_integrity import sha256_file, safe_extension
from .processing.analysis_engine import run_image, run_video
from .processing.image.validation import validate_image
from .reports.pdf import generate_report

ROOT = Path(__file__).resolve().parent
UPLOADS, OUTPUTS, REPORTS = ROOT/"uploads", ROOT/"outputs", ROOT/"reports"
MAX_BYTES = 100 * 1024 * 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    for directory in (UPLOADS, OUTPUTS, REPORTS): directory.mkdir(parents=True, exist_ok=True)
    init_db(); yield

app = FastAPI(title="ImageGuard API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/")
def root(): return {"name":"ImageGuard API", "docs":"/docs", "status":"ready"}

@app.get("/api/health")
def health(): return {"status":"healthy", "database": "sqlite", "opencv": cv2.__version__}

@app.get("/api/system-info")
def system_info(): return {"max_upload_bytes":MAX_BYTES, "image_formats":sorted(IMAGE_EXTS), "video_formats":sorted(VIDEO_EXTS)}

async def save_and_analyze(file: UploadFile, media_type: str, db: Session):
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
            try:
                validate_image(path)
            except Exception as exc: raise HTTPException(415, "File content is not a supported image") from exc
        else:
            cap = cv2.VideoCapture(str(path)); valid = cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0; cap.release()
            if not valid: raise HTTPException(415, "File content is not a readable video")
        digest = sha256_file(path)
        out_dir = OUTPUTS/ident
        result = run_image(path, out_dir) if media_type == "image" else run_video(path, out_dir)
        actual_mime = mimetypes.guess_type(f"evidence{ext}")[0] or "application/octet-stream"
        record = Investigation(id=ident, media_type=media_type, original_name=(file.filename or "evidence")[:255], stored_name=stored,
            mime_type=actual_mime, size_bytes=size,
            sha256=digest, created_at=datetime.now(timezone.utc), result_json=json.dumps(result, default=str))
        db.add(record); db.commit()
        try:
            REPORTS.mkdir(parents=True, exist_ok=True); generate_report(record, result, REPORTS/f"{ident}.pdf", out_dir)
        except Exception:
            # The finding remains available; the download endpoint can retry generation.
            pass
        return investigation_json(record, result)
    except HTTPException:
        if not db.get(Investigation, ident):
            path.unlink(missing_ok=True)
            import shutil
            shutil.rmtree(OUTPUTS/ident, ignore_errors=True)
        raise
    except Exception as exc:
        if not db.get(Investigation, ident):
            path.unlink(missing_ok=True)
            import shutil
            shutil.rmtree(OUTPUTS/ident, ignore_errors=True)
        raise HTTPException(500, f"Analysis failed: {str(exc)}") from exc

def investigation_json(record: Investigation, result: dict):
    return {"id":record.id, "media_type":record.media_type, "original_file":{"name":record.original_name,"size_bytes":record.size_bytes,"mime_type":record.mime_type},
            "sha256":record.sha256, "created_at":record.created_at.isoformat(), "result":result}

@app.post("/api/image/analyze")
async def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await save_and_analyze(file,"image",db)

@app.post("/api/video/analyze")
async def analyze_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await save_and_analyze(file,"video",db)

@app.get("/api/investigations")
def investigations(db: Session = Depends(get_db)):
    records = db.query(Investigation).order_by(Investigation.created_at.desc()).limit(100).all()
    def indicators(record: Investigation) -> int:
        try: return int(json.loads(record.result_json).get("indicator_summary", {}).get("candidate_indicators", 0))
        except (ValueError, TypeError, AttributeError): return 0
    return [{"id":r.id,"media_type":r.media_type,"original_name":r.original_name,"size_bytes":r.size_bytes,"sha256":r.sha256,
             "created_at":r.created_at.isoformat(),"candidate_indicators":indicators(r)} for r in records]

@app.get("/api/investigations/{ident}")
def investigation(ident: str, db: Session = Depends(get_db)):
    record = db.get(Investigation, ident)
    if not record: raise HTTPException(404,"Investigation not found")
    return investigation_json(record,json.loads(record.result_json))

@app.get("/api/investigations/{ident}/artifacts/{name}")
def artifact(ident: str, name: str):
    if not name or Path(name).name != name: raise HTTPException(400,"Invalid artifact name")
    if not (OUTPUTS/ident).is_dir(): raise HTTPException(404,"Investigation not found")
    path = OUTPUTS/ident/name
    if not path.is_file(): raise HTTPException(404,"Artifact not found")
    return FileResponse(path, filename=name)

@app.get("/api/investigations/{ident}/artifacts/frames/{name}")
def frame_artifact(ident: str, name: str):
    if not name or Path(name).name != name: raise HTTPException(400,"Invalid frame name")
    if not (OUTPUTS/ident).is_dir(): raise HTTPException(404,"Investigation not found")
    path = OUTPUTS/ident/"frames"/name
    if not path.is_file(): raise HTTPException(404,"Artifact not found")
    return FileResponse(path, filename=name)

@app.get("/api/investigations/{ident}/original")
def original_file(ident: str, db: Session = Depends(get_db)):
    record = db.get(Investigation, ident)
    if not record: raise HTTPException(404,"Investigation not found")
    path = UPLOADS / record.stored_name
    if not path.is_file(): raise HTTPException(404,"Original evidence is unavailable")
    return FileResponse(path, media_type=record.mime_type, filename=record.original_name)

@app.get("/api/reports/{ident}")
def report_info(ident: str, db: Session = Depends(get_db)):
    record = db.get(Investigation,ident)
    if not record: raise HTTPException(404,"Investigation not found")
    return {"id":ident,"download_url":f"/api/reports/{ident}/download"}

@app.get("/api/reports/{ident}/download")
def download_report(ident: str, db: Session = Depends(get_db)):
    record = db.get(Investigation,ident)
    if not record: raise HTTPException(404,"Investigation not found")
    path = REPORTS/f"{ident}.pdf"
    if not path.exists(): generate_report(record,json.loads(record.result_json),path,OUTPUTS/ident)
    return FileResponse(path, media_type="application/pdf", filename=f"ImageGuard-{ident}.pdf")

@app.get("/api/investigations/{ident}/verify")
def verify_integrity(ident: str, db: Session = Depends(get_db)):
    record = db.get(Investigation,ident)
    if not record: raise HTTPException(404,"Investigation not found")
    source = UPLOADS/record.stored_name
    if not source.is_file(): raise HTTPException(404,"Original evidence is unavailable")
    current = sha256_file(source)
    return {"investigation_id":ident,"stored_sha256":record.sha256,"current_sha256":current,"integrity_verified":current == record.sha256}
