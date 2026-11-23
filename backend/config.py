"""Where ImageGuard keeps its database and evidence files.

Set IMAGEGUARD_DATA_DIR to keep data elsewhere (the API tests use a temporary folder).
By default everything lives inside the backend folder, as before.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("IMAGEGUARD_DATA_DIR", BACKEND_DIR))
UPLOADS = DATA_DIR / "uploads"      # original evidence, stored unchanged
OUTPUTS = DATA_DIR / "outputs"      # visualisations and sampled frames, one folder per investigation
REPORTS = DATA_DIR / "reports"      # generated PDF reports
DB_PATH = DATA_DIR / "imageguard.db"
