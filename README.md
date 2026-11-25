# ImageGuard

ImageGuard is a local web application for explainable image and video forensic screening. It reports observations and limitations; it does not decide whether media is fake.

## Features

- **Images:** error level analysis with a localised block heat map, ORB copy-move detection (repeated RANSAC, rule tuned on held-out CASIA data), JPEG ghost map for spliced regions (Farid 2009), JPEG compression history and EXIF.
- **Videos:** frame sampling, motion-confirmed repeated frames (perceptual hash + optical flow), SSIM continuity, scene-change detection and full-video optical flow with robust motion-spike detection.
- **Evidence handling:** originals stored unchanged under random names, SHA-256 at intake, one-click re-verification, complete deletion.
- **Workflow:** background analysis with live progress, batch upload of many files or a folder, side-by-side or wipe-slider comparison with zoom, case notes, readable PDF reports.

- **Accounts:** each analyst signs in and sees only the investigations they ran. Passwords are salted PBKDF2-SHA256 hashes; sessions are HttpOnly cookies valid for 7 days. The first account created becomes the admin and takes over any investigations made before accounts existed, so Kanishka should create the first account on an existing install.

## Architecture

- `frontend/`: Next.js App Router, React, TypeScript, Tailwind CSS v4 and Lucide icons.
- `backend/`: FastAPI, OpenCV/Pillow/NumPy/scikit-image, SQLAlchemy with SQLite, local evidence and artifact storage, ReportLab PDFs.
- Original uploads use generated opaque names; working visualizations are stored separately. SQLite records the original filename, size, MIME type, SHA-256 and structured results.

## Prerequisites (Windows 11)

- Python 3.11 or newer and Node.js 20 or newer (including npm).
- FFmpeg is optional; OpenCV reads common MP4, AVI, MOV and MKV codecs available in the OpenCV build.
- PowerShell in the project directory.

## Install

```powershell
cd D:\Thapar\MCA\SEM3\IVP\Project
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
cd frontend
npm install
```

If an import fails with "An Application Control policy has blocked this file", Windows Smart App Control rejected a compiled package file. NumPy is pinned below 2.3 for this reason. SQLAlchemy's optional compiled speed-ups were blocked repeatedly, so install its pure-Python build (same version, same behaviour):

```powershell
$env:DISABLE_SQLALCHEMY_CEXT = "1"
backend\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps --no-binary sqlalchemy "SQLAlchemy==2.1.9"
```

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or run `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt` without activation.

## Start (one click)

```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
```

Starts the backend and frontend in the background (output in `logs/`), waits until both answer and opens http://localhost:3000. Stop them with `start.ps1 -Stop`.

## Start backend manually

From project root, in one PowerShell window:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Start frontend manually

In a second PowerShell window:

```powershell
cd D:\Thapar\MCA\SEM3\IVP\Project\frontend
npm run dev
```

App: http://localhost:3000. Set `NEXT_PUBLIC_API_URL` if the backend uses a different address.

## Tests

```powershell
backend\.venv\Scripts\python.exe -m pytest
```

26 tests, including end-to-end API tests that run against a temporary data folder (`IMAGEGUARD_DATA_DIR`), so your own investigations are never touched. Frontend checks: `cd frontend; npm run lint; npm run build`.

## Evaluation

The scripts run the real analysis pipeline and write results to `evaluation/results/`.

```powershell
# CASIA v2.0 image-level evaluation (download from Kaggle; pass the folder that contains Au and Tp)
backend\.venv\Scripts\python.exe -m evaluation.casia_eval "C:\path\to\CASIA2" --workers 10
# JPEG save settings per class (explains the ELA results)
backend\.venv\Scripts\python.exe -m evaluation.casia_jpeg_quality "C:\path\to\CASIA2"
# Pixel-level localisation against the CASIA ground-truth masks
backend\.venv\Scripts\python.exe -m evaluation.casia_localization "C:\path\to\CASIA2" --workers 10
# Copy-move rule: chosen on one half of CASIA, reported on the other
backend\.venv\Scripts\python.exe -m evaluation.copy_move_tuning "C:\path\to\CASIA2" --workers 10
# Synthetic video benchmark (generates clips with known edits)
backend\.venv\Scripts\python.exe -m evaluation.video_benchmark --per-kind 15
```

Add `--per-class 500` to the CASIA run for a quicker random sample.

## Project report

The report in `documentation/` is generated from `documentation/build/` (needs Microsoft Word for the final field refresh and PDF):

```powershell
backend\.venv\Scripts\python.exe documentation\build\diagrams.py
backend\.venv\Scripts\python.exe documentation\build\build_report.py
powershell -ExecutionPolicy Bypass -File documentation\build\render_word.ps1 -Docx documentation\ImageGuard_Project_Report.docx
```

`screenshots.ps1` and `crop_screenshots.py` recapture the app screenshots (both servers must be running).

The presentation (`documentation/ImageGuard_Presentation.pptx`) is built the same way (run `npm install` in `documentation/build` once):

```powershell
cd documentation\build; node build_deck.js
```

## API

- `GET /`, `/api/health`, `/api/system-info` (public; every other endpoint needs a signed-in session and only returns the caller's own investigations)
- `POST /api/auth/register`, `/api/auth/login` (JSON `{"username": "...", "password": "..."}`; sets the session cookie), `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/image/analyze`, `/api/video/analyze` (multipart field `file`; add `?background=true` to get a job id at once)
- `GET /api/jobs/{job_id}`: stage, progress and resulting investigation id of a background analysis
- `GET /api/investigations`, `/api/investigations/{id}`, `/api/investigations/{id}/verify`
- `DELETE /api/investigations/{id}`: removes the record, stored original, outputs and report
- `PUT /api/investigations/{id}/notes` (JSON `{"notes": "..."}`): case notes, included in the PDF
- `GET /api/investigations/{id}/artifacts/{name}`, `/api/investigations/{id}/original`
- `GET /api/reports/{id}`, `/api/reports/{id}/download` (`?inline=true` to view in the browser)

## Interpretation and limits

ELA is sensitive to recompression and format conversion; ORB repeat matches can come from natural textures. JPEG ghosts only appear when the pasted content was saved at a lower quality than the final image, and smooth or saturated areas can also stand out. Video sampling may miss short events, while scene changes and repeated frames are common. The global ELA peak mostly reflects how a file was last saved; the ELA heat map is the better guide to *where* an edit may be. Repeated frames are expected in genuinely static scenes. Review original media and context; no score is presented as a manipulation probability. Uploads are capped at 100 MiB; two analyses run at a time.
