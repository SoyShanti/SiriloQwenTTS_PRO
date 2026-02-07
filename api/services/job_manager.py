"""
Background job tracking with SSE progress streaming.
Uses thread-safe signaling so worker threads can update progress
that the async SSE stream picks up correctly.
"""
import asyncio
import uuid
import threading
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class Job:
    id: str
    status: str = "pending"  # pending | running | completed | failed
    progress: float = 0.0  # 0.0 - 1.0
    message: str = ""
    audio_url: str | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _updated: bool = False


class JobManager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}

    def create_job(self) -> Job:
        job_id = str(uuid.uuid4())[:8]
        job = Job(id=job_id)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def update_progress(self, job_id: str, progress: float, message: str):
        """Thread-safe progress update."""
        job = self.jobs.get(job_id)
        if job:
            with job._lock:
                job.status = "running"
                job.progress = progress
                job.message = message
                job._updated = True

    def complete_job(self, job_id: str, audio_url: str):
        """Thread-safe job completion."""
        job = self.jobs.get(job_id)
        if job:
            with job._lock:
                job.status = "completed"
                job.progress = 1.0
                job.message = "Completado"
                job.audio_url = audio_url
                job._updated = True

    def fail_job(self, job_id: str, error: str):
        """Thread-safe job failure."""
        job = self.jobs.get(job_id)
        if job:
            with job._lock:
                job.status = "failed"
                job.message = error
                job.error = error
                job._updated = True

    def _snapshot(self, job: Job) -> dict:
        with job._lock:
            job._updated = False
            return {
                "status": job.status,
                "progress": job.progress,
                "message": job.message,
                "audio_url": job.audio_url,
                "error": job.error,
            }

    async def stream_progress(self, job_id: str) -> AsyncGenerator[dict, None]:
        """Yields progress dicts until job is completed or failed.
        Polls every 0.5s — simple, thread-safe, no asyncio.Event issues."""
        job = self.jobs.get(job_id)
        if not job:
            yield {"status": "failed", "progress": 0, "message": "Job not found",
                   "error": "Job not found", "audio_url": None}
            return

        # Send current state first
        yield self._snapshot(job)

        while job.status not in ("completed", "failed"):
            await asyncio.sleep(0.5)
            if job._updated or job.status in ("completed", "failed"):
                yield self._snapshot(job)


# Singleton
job_manager = JobManager()
