"""
Tests for unified worker.

Tests all worker functionality: throttling, stuck job detection, PID tracking, retry logic, and statistics.
"""

import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from spatelier.core.config import Config
from spatelier.core.job_queue import Job, JobStatus, JobType
from spatelier.core.worker import (
    Worker,
    WorkerMode,
    create_download_processor,
    create_playlist_processor,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return Config()


@pytest.fixture
def worker(config):
    """Create test worker in thread mode."""
    return Worker(
        config=config,
        mode=WorkerMode.THREAD,
        verbose=True,
        min_time_between_jobs=1,  # Short for testing
        poll_interval=1,
        stuck_job_timeout=5,  # Short for testing
    )


@pytest.fixture
def mock_job():
    """Create mock job."""
    return Job(
        id=1,
        job_type=JobType.DOWNLOAD_VIDEO,
        job_data={"url": "https://example.com/video", "quality": "1080p"},
        job_path="/tmp/test_output",
        status=JobStatus.PENDING,
    )


class TestWorkerInitialization:
    """Test worker initialization."""

    def test_worker_init_thread_mode(self, config):
        """Test worker initialization in thread mode."""
        worker = Worker(config, mode=WorkerMode.THREAD)
        assert worker.mode == WorkerMode.THREAD
        assert not worker.running
        assert worker.min_time_between_jobs == 60  # Default

    def test_worker_init_daemon_mode(self, config):
        """Test worker initialization in daemon mode."""
        worker = Worker(config, mode=WorkerMode.DAEMON)
        assert worker.mode == WorkerMode.DAEMON
        assert worker.pid_file is not None
        assert worker.lock_file is not None

    def test_worker_init_auto_mode(self, config):
        """Test worker initialization in auto mode."""
        worker = Worker(config, mode=WorkerMode.AUTO)
        assert worker.mode == WorkerMode.AUTO

    def test_worker_custom_throttling(self, config):
        """Test worker with custom throttling."""
        worker = Worker(config, min_time_between_jobs=30, additional_sleep_time=10)
        assert worker.min_time_between_jobs == 30
        assert worker.additional_sleep_time == 10


class TestWorkerThrottling:
    """Test worker throttling functionality."""

    def test_should_throttle_when_recent_job(self, worker):
        """Test throttling when job was processed recently."""
        worker.last_job_time = datetime.now() - timedelta(seconds=30)
        worker.min_time_between_jobs = 60

        assert worker._should_throttle() is True

    def test_should_not_throttle_when_no_recent_job(self, worker):
        """Test no throttling when no recent job."""
        worker.last_job_time = datetime.now() - timedelta(seconds=120)
        worker.min_time_between_jobs = 60

        assert worker._should_throttle() is False

    def test_should_not_throttle_when_no_last_job_time(self, worker):
        """Test no throttling when no last job time."""
        worker.last_job_time = None

        assert worker._should_throttle() is False

    def test_set_throttling(self, worker):
        """Test setting throttling configuration."""
        worker.set_throttling(30, 10)

        assert worker.min_time_between_jobs == 30
        assert worker.additional_sleep_time == 10


class TestWorkerJobProcessing:
    """Test worker job processing."""

    def test_register_processor(self, worker):
        """Test registering a job processor."""

        def mock_processor(job):
            return True

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        assert JobType.DOWNLOAD_VIDEO in worker.job_processors
        assert worker.job_processors[JobType.DOWNLOAD_VIDEO] == mock_processor

    def test_process_job_success(self, worker, mock_job):
        """Test processing a job successfully."""

        def mock_processor(job):
            return True

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        with patch.object(worker.job_queue, "update_job_status") as mock_update:
            worker._process_job(mock_job)

            # Should update to running, then completed
            assert mock_update.call_count >= 2
            assert worker.stats["jobs_processed"] == 1
            assert worker.stats["jobs_failed"] == 0

    def test_process_job_failure(self, worker, mock_job):
        """Test processing a job that fails."""

        def mock_processor(job):
            return False

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        with patch.object(worker.job_queue, "update_job_status") as mock_update:
            worker._process_job(mock_job)

            # Should update to running, then failed
            assert mock_update.call_count >= 2
            assert worker.stats["jobs_processed"] == 0
            assert worker.stats["jobs_failed"] == 1

    def test_process_job_exception(self, worker, mock_job):
        """Test processing a job that raises exception."""

        def mock_processor(job):
            raise ValueError("Test error")

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        with patch.object(worker.job_queue, "update_job_status") as mock_update:
            worker._process_job(mock_job)

            # Should update to running, then failed
            assert mock_update.call_count >= 2
            assert worker.stats["jobs_failed"] == 1

    def test_process_job_no_processor(self, worker, mock_job):
        """Test processing a job with no registered processor."""
        with patch.object(worker.job_queue, "update_job_status") as mock_update:
            worker._process_job(mock_job)

            # Should fail due to no processor
            assert worker.stats["jobs_failed"] == 1


class TestWorkerPIDTracking:
    """Test worker PID tracking."""

    def test_pid_tracking_on_job_start(self, worker, mock_job):
        """Test PID tracking when job starts."""

        def mock_processor(job):
            return True

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        with patch.object(worker.job_queue, "update_job_status"):
            worker._process_job(mock_job)

            # PID should be tracked during processing
            # But cleaned up after
            assert mock_job.id not in worker.active_jobs

    def test_is_process_running(self, worker):
        """Test checking if process is running."""
        current_pid = os.getpid()

        assert worker._is_process_running(current_pid) is True
        assert worker._is_process_running(999999) is False  # Non-existent PID


class TestWorkerStuckJobDetection:
    """Test worker stuck job detection."""

    def test_get_stuck_jobs_none(self, worker):
        """Test getting stuck jobs when none exist."""
        with patch.object(worker.job_queue, "get_jobs_by_status", return_value=[]):
            stuck_jobs = worker._get_stuck_jobs()
            assert len(stuck_jobs) == 0

    def test_get_stuck_jobs_recent(self, worker):
        """Test getting stuck jobs when jobs are recent."""
        recent_job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_VIDEO,
            status=JobStatus.RUNNING,
            started_at=datetime.now()
            - timedelta(seconds=10),  # Recent (less than timeout)
        )

        # Add PID tracking to make it clear it's not stuck
        worker.active_jobs[1] = {
            "pid": os.getpid(),
            "started_at": recent_job.started_at,
            "job_type": "download_video",
        }

        with patch.object(
            worker.job_queue, "get_jobs_by_status", return_value=[recent_job]
        ):
            with patch.object(worker, "_is_process_running", return_value=True):
                with patch.object(worker, "_is_job_making_progress", return_value=True):
                    stuck_jobs = worker._get_stuck_jobs()
                    assert len(stuck_jobs) == 0

    def test_get_stuck_jobs_old(self, worker):
        """Test getting stuck jobs when jobs are old."""
        old_job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_VIDEO,
            status=JobStatus.RUNNING,
            started_at=datetime.now() - timedelta(seconds=2000),  # Old
        )

        with patch.object(
            worker.job_queue, "get_jobs_by_status", return_value=[old_job]
        ):
            with patch.object(worker, "_is_process_running", return_value=False):
                with patch.object(
                    worker, "_is_job_making_progress", return_value=False
                ):
                    stuck_jobs = worker._get_stuck_jobs()
                    assert len(stuck_jobs) == 1

    def test_is_job_making_progress_with_files(self, worker, tmp_path):
        """Test checking job progress when files exist."""
        job = Job(id=1, job_type=JobType.DOWNLOAD_VIDEO, job_path=str(tmp_path))

        # Create a recent file
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test")
        test_file.touch()  # Update mtime

        job_info = {"pid": os.getpid(), "started_at": datetime.now()}

        assert worker._is_job_making_progress(job, job_info) is True

    def test_is_job_making_progress_no_files(self, worker, tmp_path):
        """Test checking job progress when no files exist."""
        job = Job(id=1, job_type=JobType.DOWNLOAD_VIDEO, job_path=str(tmp_path))

        job_info = {"pid": os.getpid(), "started_at": datetime.now()}

        # Should return True by default (can't determine otherwise)
        assert worker._is_job_making_progress(job, job_info) is True

    def test_handle_stuck_jobs(self, worker):
        """Test handling stuck jobs."""
        stuck_job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_VIDEO,
            status=JobStatus.RUNNING,
            started_at=datetime.now() - timedelta(seconds=2000),
        )

        with patch.object(worker, "_check_job_output_success", return_value=False):
            with patch.object(worker.job_queue, "update_job_status") as mock_update:
                worker._handle_stuck_jobs([stuck_job])

                # Should update job status
                assert mock_update.called
                assert worker.stats["jobs_stuck_detected"] == 1

    def test_check_job_output_success_with_video(self, worker, tmp_path):
        """Test checking job output success when video files exist."""
        job = Job(id=1, job_type=JobType.DOWNLOAD_VIDEO, job_path=str(tmp_path))

        # Create video file
        video_file = tmp_path / "test.mp4"
        video_file.write_text("test")

        assert worker._check_job_output_success(job) is True

    def test_check_job_output_success_no_video(self, worker, tmp_path):
        """Test checking job output success when no video files exist."""
        job = Job(id=1, job_type=JobType.DOWNLOAD_VIDEO, job_path=str(tmp_path))

        assert worker._check_job_output_success(job) is False


class TestWorkerRetryLogic:
    """Test worker retry logic."""

    def test_get_retryable_failed_jobs(self, worker):
        """Test getting retryable failed jobs."""
        retryable_job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_VIDEO,
            status=JobStatus.FAILED,
            retry_count=5,
            max_retries=10,
        )

        non_retryable_job = Job(
            id=2,
            job_type=JobType.DOWNLOAD_VIDEO,
            status=JobStatus.FAILED,
            retry_count=10,
            max_retries=10,
        )

        with patch.object(
            worker.job_queue,
            "get_jobs_by_status",
            return_value=[retryable_job, non_retryable_job],
        ):
            retryable = worker._get_retryable_failed_jobs()

            assert len(retryable) == 1
            assert retryable[0].id == 1

    def test_retry_count_increments(self, worker, mock_job):
        """Test that retry count increments on retry."""
        mock_job.status = JobStatus.FAILED
        mock_job.retry_count = 5

        def mock_processor(job):
            return True

        worker.register_processor(JobType.DOWNLOAD_VIDEO, mock_processor)

        with patch.object(worker.job_queue, "update_job_status"):
            worker._process_job(mock_job)

            assert worker.stats["jobs_retried"] == 1


class TestWorkerStatistics:
    """Test worker statistics."""

    def test_get_stats(self, worker):
        """Test getting worker statistics."""
        worker.running = True
        worker.stats["jobs_processed"] = 10
        worker.stats["jobs_failed"] = 2

        with patch.object(
            worker.job_queue, "get_queue_status", return_value={"pending": 5}
        ):
            stats = worker.get_stats()

            assert stats["worker_running"] is True
            assert stats["mode"] == "thread"
            assert stats["worker_stats"]["jobs_processed"] == 10
            assert stats["worker_stats"]["jobs_failed"] == 2
            assert "throttling" in stats
            assert "queue_status" in stats


class TestWorkerLifecycle:
    """Test worker lifecycle (start/stop)."""

    def test_start_stop_thread_mode(self, worker):
        """Test starting and stopping worker in thread mode."""
        assert not worker.running

        worker.start()

        # Give it a moment to start
        time.sleep(0.1)

        assert worker.running

        worker.stop()

        # Give it a moment to stop
        time.sleep(0.1)

        assert not worker.running

    def test_start_already_running(self, worker):
        """Test starting worker when already running."""
        worker.start()
        time.sleep(0.1)

        # Should not raise error
        worker.start()

        worker.stop()


class TestWorkerHelperFunctions:
    """Test helper functions for creating processors."""

    def test_create_download_processor(self, tmp_path):
        """Test creating download processor."""
        mock_services = Mock()
        mock_use_case = Mock()
        mock_result = Mock()
        mock_result.is_successful.return_value = True
        mock_use_case.execute.return_value = mock_result
        mock_services.download_video_use_case = mock_use_case

        processor = create_download_processor(mock_services)

        job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_VIDEO,
            job_data={"url": "https://example.com/video", "quality": "1080p"},
            job_path=str(tmp_path),
        )

        result = processor(job)

        assert result is True
        mock_use_case.execute.assert_called_once()

    def test_create_playlist_processor(self, tmp_path):
        """Test creating playlist processor."""
        mock_services = Mock()
        mock_use_case = Mock()
        mock_result = Mock()
        mock_result.is_successful.return_value = True
        mock_use_case.execute.return_value = mock_result
        mock_services.download_playlist_use_case = mock_use_case

        processor = create_playlist_processor(mock_services)

        job = Job(
            id=1,
            job_type=JobType.DOWNLOAD_PLAYLIST,
            job_data={"url": "https://example.com/playlist", "quality": "1080p"},
            job_path=str(tmp_path),
        )

        result = processor(job)

        assert result is True
        mock_use_case.execute.assert_called_once()
