"""
Generic job queue system with SQLite persistence.

This module provides a flexible job queue system that can handle any type of job,
with configurable throttling, persistent storage, and background processing.
"""

import json
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from spatelier.core.config import Config
from spatelier.core.logger import get_logger


class JobStatus(Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Job type enumeration."""

    DOWNLOAD_VIDEO = "download_video"
    DOWNLOAD_PLAYLIST = "download_playlist"
    TRANSCRIBE_VIDEO = "transcribe_video"
    PROCESS_AUDIO = "process_audio"
    CUSTOM = "custom"


@dataclass
class Job:
    """Generic job definition."""

    id: Optional[int] = None
    job_type: JobType = JobType.CUSTOM
    job_data: Dict[str, Any] = None
    job_path: str = ""
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.job_data is None:
            self.job_data = {}
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def duration(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_finished(self) -> bool:
        """Check if job is in a finished state."""
        return self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "job_data": self.job_data,
            "job_path": self.job_path,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        job = cls()
        job.id = data.get("id")
        job.job_type = JobType(data.get("job_type", "custom"))
        job.job_data = data.get("job_data", {})
        job.job_path = data.get("job_path", "")
        job.status = JobStatus(data.get("status", "pending"))
        job.priority = data.get("priority", 0)
        job.created_at = (
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        )
        job.started_at = (
            datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None
        )
        job.completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )
        job.error_message = data.get("error_message")
        job.retry_count = data.get("retry_count", 0)
        job.max_retries = data.get("max_retries", 3)
        return job


class JobQueue:
    """Generic job queue with SQLite persistence."""

    def __init__(self, config: Config, verbose: bool = False):
        """Initialize job queue."""
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("JobQueue", verbose=verbose)

        # Database connection
        self.db_path = Path(config.database.sqlite_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Threading
        self._lock = threading.Lock()

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize job queue database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    job_data TEXT NOT NULL,
                    job_path TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """
            )

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)"
            )

            conn.commit()

    def add_job(self, job: Job) -> int:
        """Add job to queue."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO jobs (job_type, job_data, job_path, status, priority, created_at, retry_count, max_retries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        job.job_type.value,
                        json.dumps(job.job_data),
                        job.job_path,
                        job.status.value,
                        job.priority,
                        job.created_at.isoformat(),
                        job.retry_count,
                        job.max_retries,
                    ),
                )

                job_id = cursor.lastrowid
                self.logger.info(f"Added job {job_id} to queue: {job.job_type.value}")
                return job_id

    def get_next_job(self) -> Optional[Job]:
        """Get next job to process (highest priority, oldest first)."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """
                )

                row = cursor.fetchone()
                if not row:
                    return None

                # Convert row to job
                job_data = {
                    "id": row[0],
                    "job_type": row[1],
                    "job_data": json.loads(row[2]),
                    "job_path": row[3],
                    "status": row[4],
                    "priority": row[5],
                    "created_at": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                    "error_message": row[9],
                    "retry_count": row[10],
                    "max_retries": row[11],
                }

                return Job.from_dict(job_data)

    def update_job_status(
        self, job_id: int, status: JobStatus, error_message: Optional[str] = None
    ) -> bool:
        """Update job status."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if status == JobStatus.RUNNING:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = ?, started_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (status.value, job_id),
                    )
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                        WHERE id = ?
                    """,
                        (status.value, error_message, job_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = ?
                        WHERE id = ?
                    """,
                        (status.value, job_id),
                    )

                conn.commit()
                return True

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                job_data = {
                    "id": row[0],
                    "job_type": row[1],
                    "job_data": json.loads(row[2]),
                    "job_path": row[3],
                    "status": row[4],
                    "priority": row[5],
                    "created_at": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                    "error_message": row[9],
                    "retry_count": row[10],
                    "max_retries": row[11],
                }

                return Job.from_dict(job_data)

    def get_queue_status(self) -> Dict[str, int]:
        """Get queue status summary."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM jobs
                    GROUP BY status
                """
                )

                status_counts = dict(cursor.fetchall())

                return {
                    "pending": status_counts.get("pending", 0),
                    "running": status_counts.get("running", 0),
                    "completed": status_counts.get("completed", 0),
                    "failed": status_counts.get("failed", 0),
                    "cancelled": status_counts.get("cancelled", 0),
                }

    def get_jobs_by_status(
        self, status: JobStatus, limit: Optional[int] = None
    ) -> List[Job]:
        """Get jobs by status."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC"
                params = [status.value]

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                jobs = []
                for row in rows:
                    job_data = {
                        "id": row[0],
                        "job_type": row[1],
                        "job_data": json.loads(row[2]),
                        "job_path": row[3],
                        "status": row[4],
                        "priority": row[5],
                        "created_at": row[6],
                        "started_at": row[7],
                        "completed_at": row[8],
                        "error_message": row[9],
                        "retry_count": row[10],
                        "max_retries": row[11],
                    }
                    jobs.append(Job.from_dict(job_data))

                return jobs

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs from queue."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
                rows = cursor.fetchall()

                jobs = []
                for row in rows:
                    job_data = {
                        "id": row[0],
                        "job_type": row[1],
                        "job_data": json.loads(row[2]),
                        "job_path": row[3],
                        "status": row[4],
                        "priority": row[5],
                        "created_at": row[6],
                        "started_at": row[7],
                        "completed_at": row[8],
                        "error_message": row[9],
                        "retry_count": row[10],
                        "max_retries": row[11],
                    }
                    jobs.append(Job.from_dict(job_data))

                return jobs

    def cancel_job(self, job_id: int) -> bool:
        """Cancel a job."""
        return self.update_job_status(job_id, JobStatus.CANCELLED)

    def retry_failed_jobs(self) -> int:
        """Retry failed jobs that haven't exceeded max retries."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'pending', retry_count = retry_count + 1
                    WHERE status = 'failed' AND retry_count < max_retries
                """
                )

                retry_count = cursor.rowcount
                conn.commit()

                if retry_count > 0:
                    self.logger.info(f"Retrying {retry_count} failed jobs")

                return retry_count

    def cleanup_old_jobs(self, max_age_days: int = 30) -> int:
        """Clean up old completed jobs."""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM jobs
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    AND completed_at < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old jobs")

                return deleted_count
