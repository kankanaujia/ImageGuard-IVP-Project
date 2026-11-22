from pathlib import Path
from types import SimpleNamespace
from backend.reports.pdf import generate_report

def test_report_generation(tmp_path: Path):
    record=SimpleNamespace(id="123",original_name="sample.png",media_type="image",size_bytes=12,sha256="abc",created_at="2026-01-01")
    target=tmp_path/"report.pdf"
    generate_report(record,{"indicator_summary":{"statement":"Observation only."},"limitations":["Synthetic input"]},target)
    assert target.exists() and target.stat().st_size > 100
