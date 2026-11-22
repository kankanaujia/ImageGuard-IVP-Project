# ImageGuard

ImageGuard is a local web application for explainable image and video forensic screening. It reports observations and limitations; it does not decide whether media is fake.

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

## Start backend

From project root, in one PowerShell window:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Start frontend

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

Run the current tests after installing prerequisites. Frontend production build: `cd frontend; npm run build`.

## Evaluation

Both scripts run the real analysis pipeline and write results to `evaluation/results/`.

```powershell
# CASIA v2.0 (download from Kaggle; pass the folder that contains Au and Tp)
backend\.venv\Scripts\python.exe -m evaluation.casia_eval "C:\path\to\CASIA2" --workers 10
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

- `GET /`, `/api/health`, `/api/system-info`
- `POST /api/image/analyze`, `/api/video/analyze` (multipart field `file`)
- `GET /api/investigations`, `/api/investigations/{id}`, `/api/investigations/{id}/verify`
- `GET /api/investigations/{id}/artifacts/{name}`
- `GET /api/reports/{id}`, `/api/reports/{id}/download`

## Interpretation and limits

ELA is sensitive to recompression and format conversion; ORB repeat matches can come from natural textures. Noise measurements vary with image content and processing. Video sampling may miss short events, while scene changes and repeated frames are common. Review original media and context; no score is presented as a manipulation probability. Current uploads are capped at 100 MiB and processing is synchronous.
