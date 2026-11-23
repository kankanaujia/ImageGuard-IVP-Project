"""In-process background analysis jobs with progress reporting.

Uploads are saved and validated in the request; the slow analysis then runs in a small
thread pool so the browser can poll real progress instead of waiting on one long request.
Job state lives in memory: it is only needed while an analysis is running (finished
results are in the database), so a restart simply forgets old job ids.
"""
from __future__ import annotations
import threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

MAX_WORKERS = 2          # analyses run concurrently; more mostly competes for CPU
KEEP_SECONDS = 3600      # finished jobs are forgotten after an hour

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="analysis")
_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _prune() -> None:
    cutoff = time.time() - KEEP_SECONDS
    for job_id in [j for j, v in _jobs.items() if v["finished_at"] and v["finished_at"] < cutoff]:
        _jobs.pop(job_id, None)


def submit(kind: str, original_name: str, work: Callable[[Callable[[float, str], None]], str]) -> dict:
    """Queue `work(progress)`; it must return the new investigation id."""
    job_id = str(uuid.uuid4())
    job = {"id": job_id, "kind": kind, "original_name": original_name, "status": "queued", "stage": "Waiting to start",
           "progress": 0.0, "investigation_id": None, "error": None, "created_at": time.time(), "finished_at": None}
    with _lock:
        _prune()
        _jobs[job_id] = job

    def progress(fraction: float, stage: str) -> None:
        with _lock:
            job.update(status="running", stage=stage, progress=round(max(job["progress"], min(fraction, 0.99)) * 100) / 100)

    def run() -> None:
        try:
            progress(0.0, "Starting analysis")
            investigation_id = work(progress)
            with _lock:
                job.update(status="done", stage="Complete", progress=1.0, investigation_id=investigation_id, finished_at=time.time())
        except Exception as exc:  # recorded for the client; the worker cleans up its own files
            with _lock:
                job.update(status="error", stage="Failed", error=str(getattr(exc, "detail", exc)), finished_at=time.time())

    _executor.submit(run)
    return snapshot(job_id)


def snapshot(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
