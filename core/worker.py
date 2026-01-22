"""
Unified worker for background job processing.

This module provides a single, configurable worker that consolidates all worker
functionality: throttling, stuck job detection, PID tracking, retry logic, and statistics.
"""

import os
import signal
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.config import Config
from core.job_queue import Job, JobQueue, JobStatus, JobType
from core.logger import get_logger


class WorkerMode(str, Enum):
    """Worker execution mode."""

    THREAD = "thread"  # In-process thread worker
    DAEMON = "daemon"  # System daemon worker
    AUTO = "auto"  # Auto-start/stop worker


class Worker:
    """
    Unified worker for background job processing.

    Consolidates functionality from JobWorker, AutoWorker, DaemonWorker, and WorkerManager.
    Supports multiple execution modes and includes throttling, stuck job detection,
    PID tracking, retry logic, and comprehensive statistics.
    """

    def __init__(
        self,
        config: Config,
        mode: WorkerMode = WorkerMode.THREAD,
        verbose: bool = False,
        max_retries: int = 10,
        min_time_between_jobs: int = 60,
        additional_sleep_time: int = 0,
        poll_interval: int = 30,
        stuck_job_timeout: int = 1800,  # 30 minutes
        services: Optional[Any] = None,
    ):
        """
        Initialize unified worker.

        Args:
            config: Configuration instance
            mode: Worker execution mode (thread, daemon, or auto)
            verbose: Enable verbose logging
            max_retries: Maximum retries for failed jobs
            min_time_between_jobs: Minimum seconds between jobs (throttling)
            additional_sleep_time: Additional sleep time after throttling
            poll_interval: Seconds between queue polls
            stuck_job_timeout: Seconds before a job is considered stuck
            services: Optional service container for job processors
        """
        self.config = config
        self.mode = mode
        self.verbose = verbose
        self.max_retries = max_retries
        self.min_time_between_jobs = min_time_between_jobs
        self.additional_sleep_time = additional_sleep_time
        self.poll_interval = poll_interval
        self.stuck_job_timeout = stuck_job_timeout
        self.services = services

        self.logger = get_logger("Worker", verbose=verbose)

        # Job queue
        self.job_queue = JobQueue(config, verbose=verbose)

        # Worker state
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.last_job_time: Optional[datetime] = None

        # Job processors
        self.job_processors: Dict[JobType, Callable[[Job], bool]] = {}

        # PID tracking for active jobs
        self.active_jobs: Dict[
            int, Dict[str, Any]
        ] = {}  # job_id -> {"pid": int, "started_at": datetime, "job_type": str}

        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_retried": 0,
            "jobs_stuck_detected": 0,
            "jobs_stuck_reset": 0,
            "total_runtime": 0,
            "start_time": None,
        }

        # Daemon management (for daemon mode)
        self.pid_file: Optional[Path] = None
        self.lock_file: Optional[Path] = None

        # Setup signal handlers for daemon mode
        if mode == WorkerMode.DAEMON:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            from core.config import get_default_data_dir

            data_dir = get_default_data_dir()
            self.pid_file = data_dir / "worker.pid"
            self.lock_file = data_dir / "worker.lock"

    def set_throttling(
        self, min_time_seconds: int, additional_sleep_seconds: int = 0
    ) -> None:
        """Set throttling configuration."""
        self.min_time_between_jobs = min_time_seconds
        self.additional_sleep_time = additional_sleep_seconds
        self.logger.info(
            f"Throttling set: min {min_time_seconds}s, additional {additional_sleep_seconds}s"
        )

    def register_processor(
        self, job_type: JobType, processor: Callable[[Job], bool]
    ) -> None:
        """Register a job processor for a specific job type."""
        self.job_processors[job_type] = processor
        self.logger.info(f"Registered processor for {job_type.value}")

    def start(self) -> None:
        """Start the worker."""
        if self.running:
            self.logger.warning("Worker is already running")
            return

        if self.mode == WorkerMode.DAEMON:
            self._start_daemon()
        elif self.mode == WorkerMode.AUTO:
            self._start_auto()
        else:  # THREAD mode
            self._start_thread()

    def stop(self) -> None:
        """Stop the worker."""
        if not self.running:
            self.logger.warning("Worker is not running")
            return

        self.running = False
        self.stop_event.set()

        if self.worker_thread:
            self.worker_thread.join(timeout=10)

        if self.stats["start_time"]:
            self.stats["total_runtime"] = (
                datetime.now() - self.stats["start_time"]
            ).total_seconds()

        # Clean up PID tracking
        self.active_jobs.clear()

        # Clean up daemon files
        if self.mode == WorkerMode.DAEMON:
            self._cleanup_daemon_files()

        self.logger.info("Worker stopped")

    def _start_thread(self) -> None:
        """Start worker in thread mode."""
        self.running = True
        self.stop_event.clear()
        self.stats["start_time"] = datetime.now()

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self.logger.info("Worker started in thread mode")

    def _start_auto(self) -> None:
        """Start worker in auto mode (thread with auto-management)."""
        self._start_thread()
        self.logger.info("Worker started in auto mode")

    def _start_daemon(self) -> None:
        """Start worker in daemon mode (system daemon)."""
        try:
            import psutil
        except ImportError:
            self.logger.error("psutil not available, cannot start daemon mode")
            raise RuntimeError("psutil required for daemon mode")

        # Check if already running
        if self.pid_file and self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                if psutil.pid_exists(pid):
                    self.logger.warning("Worker daemon is already running")
                    return
            except (ValueError, FileNotFoundError):
                pass

        # Create lock file
        if self.lock_file:
            if self.lock_file.exists():
                self.logger.warning("Lock file exists, worker may be starting")
                return
            self.lock_file.touch()

        # Fork to background
        pid = os.fork()

        if pid == 0:
            # Child process - start worker daemon
            os.setsid()  # Create new session

            # Redirect stdio
            devnull = os.open(os.devnull, os.O_RDWR)
            os.dup2(devnull, 0)  # stdin
            os.dup2(devnull, 1)  # stdout
            os.dup2(devnull, 2)  # stderr

            # Start worker loop
            self.running = True
            self.stop_event.clear()
            self.stats["start_time"] = datetime.now()

            # Write PID file
            if self.pid_file:
                self.pid_file.write_text(str(os.getpid()))

            # Remove lock file
            if self.lock_file:
                self.lock_file.unlink(missing_ok=True)

            self.logger.info("Worker daemon started")
            self._worker_loop()
            os._exit(0)
        else:
            # Parent process
            self.logger.info(f"Started worker daemon with PID {pid}")

            # Write PID file
            if self.pid_file:
                self.pid_file.write_text(str(pid))

            # Remove lock file
            if self.lock_file:
                self.lock_file.unlink(missing_ok=True)

    def _worker_loop(self) -> None:
        """Main worker loop."""
        self.logger.info("Worker loop started")

        while self.running and not self.stop_event.is_set():
            try:
                # Check for stuck jobs first
                stuck_jobs = self._get_stuck_jobs()
                if stuck_jobs:
                    self.logger.warning(f"Found {len(stuck_jobs)} stuck jobs")
                    self._handle_stuck_jobs(stuck_jobs)

                # Check for pending jobs
                jobs = self.job_queue.get_jobs_by_status(JobStatus.PENDING, limit=5)

                # Also retry failed jobs that haven't exceeded max retries
                failed_jobs = self._get_retryable_failed_jobs()
                if failed_jobs:
                    self.logger.info(f"Found {len(failed_jobs)} retryable failed jobs")
                    jobs.extend(failed_jobs)

                if jobs:
                    # Process jobs with throttling
                    for job in jobs:
                        if not self.running:
                            break

                        # Check throttling
                        if self._should_throttle():
                            self.logger.debug("Throttling job processing")
                            break

                        # Process job
                        self._process_job(job)
                        self.last_job_time = datetime.now()
                else:
                    self.logger.debug("No jobs found to process")

                # Sleep before next poll
                self.stop_event.wait(self.poll_interval)

            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                self.stop_event.wait(self.poll_interval)

        self.logger.info("Worker loop ended")

    def _should_throttle(self) -> bool:
        """Check if we should throttle based on timing."""
        if not self.last_job_time:
            return False

        time_since_last = (datetime.now() - self.last_job_time).total_seconds()
        return time_since_last < self.min_time_between_jobs

    def _get_retryable_failed_jobs(self) -> list:
        """Get failed jobs that can be retried."""
        try:
            failed_jobs = self.job_queue.get_jobs_by_status(JobStatus.FAILED, limit=5)

            # Filter for retryable jobs (retry_count < max_retries)
            retryable_jobs = []
            for job in failed_jobs:
                if job.retry_count < self.max_retries:
                    retryable_jobs.append(job)

            return retryable_jobs

        except Exception as e:
            self.logger.error(f"Failed to get retryable failed jobs: {e}")
            return []

    def _get_stuck_jobs(self) -> list:
        """Get jobs that are actually stuck (not just running long)."""
        try:
            running_jobs = self.job_queue.get_jobs_by_status(
                JobStatus.RUNNING, limit=10
            )

            stuck_jobs = []
            cutoff_time = datetime.now() - timedelta(seconds=self.stuck_job_timeout)

            for job in running_jobs:
                # Check if job has been running too long
                job_start_time = job.started_at or job.created_at
                if not job_start_time or job_start_time > cutoff_time:
                    continue  # Job is not old enough to be considered stuck

                # Check if we have PID tracking for this job
                if job.id in self.active_jobs:
                    job_info = self.active_jobs[job.id]
                    pid = job_info.get("pid")

                    if pid and self._is_process_running(pid):
                        # Process is still running, check if it's making progress
                        if self._is_job_making_progress(job, job_info):
                            self.logger.debug(
                                f"Job {job.id} is still running and making progress"
                            )
                            continue
                        else:
                            self.logger.warning(
                                f"Job {job.id} process {pid} is running but not making progress"
                            )
                            stuck_jobs.append(job)
                    else:
                        # Process is not running - job failed silently
                        self.logger.warning(
                            f"Job {job.id} process {pid} is not running - failed silently"
                        )
                        stuck_jobs.append(job)
                else:
                    # No PID tracking - job might be stuck without a process
                    self.logger.warning(
                        f"Job {job.id} has no PID tracking - might be stuck"
                    )
                    stuck_jobs.append(job)

            return stuck_jobs

        except Exception as e:
            self.logger.error(f"Failed to get stuck jobs: {e}")
            return []

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is still running."""
        try:
            os.kill(pid, 0)  # Signal 0 does nothing, but checks if PID exists
            return True
        except (OSError, ProcessLookupError):
            return False

    def _is_job_making_progress(self, job: Job, job_info: Dict[str, Any]) -> bool:
        """Check if a job is making progress (files being created, etc.)."""
        try:
            # For download jobs, check if output files are being created/modified
            if job.job_type.value in ["download_video", "download_playlist"]:
                output_path = Path(job.job_path)

                # Check if any files in the output directory have been modified recently
                if output_path.exists():
                    recent_files = []
                    for file_path in output_path.rglob("*"):
                        if file_path.is_file():
                            # Check if file was modified in the last 5 minutes
                            if time.time() - file_path.stat().st_mtime < 300:
                                recent_files.append(file_path)

                    if recent_files:
                        self.logger.debug(
                            f"Job {job.id} has {len(recent_files)} recently modified files"
                        )
                        return True

                # Check if temp files are being created
                from core.config import get_default_data_dir

                temp_path = get_default_data_dir() / "tmp" / "video" / str(job.id)
                if temp_path.exists():
                    temp_files = list(temp_path.rglob("*"))
                    if temp_files:
                        # Check if any temp files were modified recently
                        recent_temp_files = [
                            f
                            for f in temp_files
                            if time.time() - f.stat().st_mtime < 300
                        ]
                        if recent_temp_files:
                            self.logger.debug(
                                f"Job {job.id} has {len(recent_temp_files)} recently modified temp files"
                            )
                            return True

            # For other job types, assume it's making progress if we can't determine otherwise
            return True

        except Exception as e:
            self.logger.error(f"Failed to check job progress: {e}")
            return False

    def _handle_stuck_jobs(self, stuck_jobs: list) -> None:
        """Handle stuck jobs intelligently based on their actual status."""
        try:
            for job in stuck_jobs:
                self.logger.warning(f"Analyzing stuck job {job.id}")
                self.stats["jobs_stuck_detected"] += 1

                # Check if we have PID tracking for this job
                if job.id in self.active_jobs:
                    job_info = self.active_jobs[job.id]
                    pid = job_info.get("pid")

                    if pid and self._is_process_running(pid):
                        # Process is still running but not making progress
                        self.logger.warning(
                            f"Job {job.id} process {pid} is running but stuck"
                        )

                        # Check if we got any output files
                        if self._check_job_output_success(job):
                            self.logger.info(
                                f"Job {job.id} actually completed successfully, marking as completed"
                            )
                            self.job_queue.update_job_status(
                                job.id, JobStatus.COMPLETED
                            )
                        else:
                            self.logger.warning(
                                f"Job {job.id} is stuck with no output, resetting to pending"
                            )
                            self.job_queue.update_job_status(
                                job.id,
                                JobStatus.PENDING,
                                error_message=f"Job was stuck in running state for {self.stuck_job_timeout}s, reset to pending",
                            )
                            self.stats["jobs_stuck_reset"] += 1
                    else:
                        # Process is not running - job failed silently
                        self.logger.warning(
                            f"Job {job.id} process {pid} is not running - failed silently"
                        )

                        # Check if we got any output files despite the failure
                        if self._check_job_output_success(job):
                            self.logger.info(
                                f"Job {job.id} completed successfully despite process failure, marking as completed"
                            )
                            self.job_queue.update_job_status(
                                job.id, JobStatus.COMPLETED
                            )
                        else:
                            self.logger.warning(
                                f"Job {job.id} failed silently with no output, marking as failed"
                            )
                            self.job_queue.update_job_status(
                                job.id,
                                JobStatus.FAILED,
                                error_message=f"Job failed silently - process not running after {self.stuck_job_timeout}s",
                            )
                else:
                    # No PID tracking - job might be stuck without a process
                    self.logger.warning(
                        f"Job {job.id} has no PID tracking - might be stuck"
                    )

                    # Check if we got any output files
                    if self._check_job_output_success(job):
                        self.logger.info(
                            f"Job {job.id} actually completed successfully, marking as completed"
                        )
                        self.job_queue.update_job_status(job.id, JobStatus.COMPLETED)
                    else:
                        self.logger.warning(
                            f"Job {job.id} is stuck with no output, resetting to pending"
                        )
                        self.job_queue.update_job_status(
                            job.id,
                            JobStatus.PENDING,
                            error_message=f"Job was stuck in running state for {self.stuck_job_timeout}s, reset to pending",
                        )
                        self.stats["jobs_stuck_reset"] += 1

        except Exception as e:
            self.logger.error(f"Failed to handle stuck jobs: {e}")

    def _check_job_output_success(self, job: Job) -> bool:
        """Check if a job actually succeeded by looking for output files."""
        try:
            # For download jobs, check if output files exist
            if job.job_type.value in ["download_video", "download_playlist"]:
                output_path = Path(job.job_path)

                if output_path.exists():
                    # Check if there are any video files in the output directory
                    video_files = (
                        list(output_path.rglob("*.mp4"))
                        + list(output_path.rglob("*.mkv"))
                        + list(output_path.rglob("*.avi"))
                    )
                    if video_files:
                        self.logger.info(
                            f"Job {job.id} has {len(video_files)} video files in output directory"
                        )
                        return True

                    # Check if there are any files at all
                    all_files = list(output_path.rglob("*"))
                    if all_files:
                        self.logger.info(
                            f"Job {job.id} has {len(all_files)} files in output directory"
                        )
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to check job output success: {e}")
            return False

    def _process_job(self, job: Job) -> None:
        """Process a single job."""
        self.logger.info(f"Processing job {job.id}: {job.job_type.value}")

        # Update job status to running
        self.job_queue.update_job_status(job.id, JobStatus.RUNNING)

        # Track this job's PID
        self.active_jobs[job.id] = {
            "pid": os.getpid(),  # Current process PID
            "started_at": datetime.now(),
            "job_type": job.job_type.value,
        }

        try:
            # If this is a retry, increment retry count
            if job.status == JobStatus.FAILED:
                job.retry_count += 1
                self.stats["jobs_retried"] += 1

            # Get processor for job type
            processor = self.job_processors.get(job.job_type)
            if not processor:
                raise ValueError(
                    f"No processor registered for job type: {job.job_type.value}"
                )

            # Process job
            success = processor(job)

            if success:
                self.job_queue.update_job_status(job.id, JobStatus.COMPLETED)
                self.stats["jobs_processed"] += 1
                self.logger.info(f"Job {job.id} completed successfully")
            else:
                self.job_queue.update_job_status(
                    job.id, JobStatus.FAILED, "Processor returned False"
                )
                self.stats["jobs_failed"] += 1
                self.logger.error(f"Job {job.id} failed: Processor returned False")

        except Exception as e:
            error_msg = str(e)
            self.job_queue.update_job_status(job.id, JobStatus.FAILED, error_msg)
            self.stats["jobs_failed"] += 1
            self.logger.error(f"Job {job.id} failed: {error_msg}")

        finally:
            # Clean up PID tracking
            if job.id in self.active_jobs:
                del self.active_jobs[job.id]

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        queue_status = self.job_queue.get_queue_status()

        return {
            "worker_running": self.running,
            "mode": self.mode.value,
            "throttling": {
                "min_time_between_jobs": self.min_time_between_jobs,
                "additional_sleep_time": self.additional_sleep_time,
                "last_job_time": (
                    self.last_job_time.isoformat() if self.last_job_time else None
                ),
            },
            "queue_status": queue_status,
            "worker_stats": self.stats,
            "registered_processors": [jt.value for jt in self.job_processors.keys()],
            "active_jobs": len(self.active_jobs),
            "stuck_jobs_detected": self.stats["jobs_stuck_detected"],
            "stuck_jobs_reset": self.stats["jobs_stuck_reset"],
        }

    def is_running(self) -> bool:
        """Check if worker is running (for daemon mode)."""
        if self.mode != WorkerMode.DAEMON:
            return self.running

        if not self.pid_file or not self.pid_file.exists():
            return False

        try:
            import psutil

            pid = int(self.pid_file.read_text().strip())

            if not psutil.pid_exists(pid):
                self._cleanup_daemon_files()
                return False

            # Check if it's actually our worker process
            try:
                process = psutil.Process(pid)
                if "python" in process.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return False

        except (ValueError, FileNotFoundError, ImportError):
            return False

    def stop_daemon(self) -> bool:
        """Stop daemon worker (for daemon mode)."""
        if self.mode != WorkerMode.DAEMON:
            return False

        if not self.is_running():
            return True

        try:
            import psutil

            pid = int(self.pid_file.read_text().strip())

            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)

            # Wait for process to stop
            for _ in range(10):
                if not psutil.pid_exists(pid):
                    break
                time.sleep(1)

            # Force kill if still running
            if psutil.pid_exists(pid):
                self.logger.warning(f"Force killing worker PID {pid}")
                os.kill(pid, signal.SIGKILL)

            self._cleanup_daemon_files()
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop daemon: {e}")
            return False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _cleanup_daemon_files(self):
        """Clean up daemon files."""
        if self.pid_file and self.pid_file.exists():
            self.pid_file.unlink(missing_ok=True)
        if self.lock_file and self.lock_file.exists():
            self.lock_file.unlink(missing_ok=True)


# Helper functions for creating job processors
def create_download_processor(services) -> Callable[[Job], bool]:
    """Create a download job processor."""

    def process_download_job(job: Job) -> bool:
        """Process a download job."""
        try:
            # Extract job data
            job_data = job.job_data
            video_url = job_data.get("url")
            output_path = Path(job.job_path)

            if not video_url:
                raise ValueError("No URL in job data")

            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Download video using existing service
            result = services.video_download.download_video(
                video_url, output_path, quality=job_data.get("quality", "1080p")
            )

            return result.is_successful()

        except Exception as e:
            raise Exception(f"Download failed: {e}")

    return process_download_job


def create_playlist_processor(services) -> Callable[[Job], bool]:
    """Create a playlist download processor."""

    def process_playlist_job(job: Job) -> bool:
        """Process a playlist download job."""
        try:
            # Extract job data
            job_data = job.job_data
            playlist_url = job_data.get("url")
            output_path = Path(job.job_path)

            if not playlist_url:
                raise ValueError("No URL in job data")

            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Download playlist using existing service
            result = services.playlist.download_playlist(
                playlist_url, output_path, quality=job_data.get("quality", "1080p")
            )

            return result.is_successful()

        except Exception as e:
            raise Exception(f"Playlist download failed: {e}")

    return process_playlist_job
