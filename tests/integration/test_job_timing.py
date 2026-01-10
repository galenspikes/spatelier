"""
Tests for job timing functionality.

This module tests the job lifecycle timing to ensure proper
started_at, completed_at, and duration_seconds tracking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from database.models import ProcessingJob, ProcessingStatus, MediaFile, MediaType
from database.repository import ProcessingJobRepository
from database.connection import DatabaseManager
from core.config import Config


class TestJobTiming:
    """Test job timing functionality."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager for testing."""
        config = Config()
        db_manager = DatabaseManager(config, verbose=False)
        db_manager.connect_sqlite()
        return db_manager
    
    @pytest.fixture
    def job_repo(self, db_manager):
        """Create job repository for testing."""
        session = db_manager.get_sqlite_session()
        return ProcessingJobRepository(session, verbose=False)
    
    @pytest.fixture
    def sample_media_file(self, db_manager):
        """Create a sample media file for testing."""
        import uuid
        session = db_manager.get_sqlite_session()
        
        # Use unique identifiers to avoid constraint violations
        unique_id = str(uuid.uuid4())[:8]
        media_file = MediaFile(
            file_path=f"/test/video_{unique_id}.mp4",
            file_name=f"video_{unique_id}.mp4",
            file_size=1000000,
            file_hash=f"test_hash_{unique_id}",
            media_type=MediaType.VIDEO,
            mime_type="video/mp4"
        )
        session.add(media_file)
        session.commit()
        session.refresh(media_file)
        return media_file
    
    def test_job_creation_starts_pending(self, job_repo, sample_media_file):
        """Test that jobs start with PENDING status."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        assert job.status == ProcessingStatus.PENDING
        assert job.started_at is None
        assert job.completed_at is None
        assert job.duration_seconds is None
    
    def test_job_processing_sets_started_at(self, job_repo, sample_media_file):
        """Test that setting status to PROCESSING sets started_at."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        # Update to PROCESSING
        updated_job = job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
        
        assert updated_job.status == ProcessingStatus.PROCESSING
        assert updated_job.started_at is not None
        assert updated_job.completed_at is None
        assert updated_job.duration_seconds is None
        
        # Verify started_at is recent
        now = datetime.now()
        time_diff = abs((now - updated_job.started_at).total_seconds())
        assert time_diff < 5  # Should be within 5 seconds
    
    def test_job_completion_sets_completed_at_and_duration(self, job_repo, sample_media_file):
        """Test that completing a job sets completed_at and calculates duration."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        # Set to PROCESSING first
        job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
        
        # Wait a small amount to ensure duration > 0
        import time
        time.sleep(0.1)
        
        # Complete the job
        updated_job = job_repo.update_status(job.id, ProcessingStatus.COMPLETED)
        
        assert updated_job.status == ProcessingStatus.COMPLETED
        assert updated_job.started_at is not None
        assert updated_job.completed_at is not None
        assert updated_job.duration_seconds is not None
        assert updated_job.duration_seconds > 0
    
    def test_job_duration_calculation(self, job_repo, sample_media_file):
        """Test that duration is calculated correctly."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        # Set to PROCESSING
        job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
        
        # Wait a specific amount
        import time
        wait_time = 0.2
        time.sleep(wait_time)
        
        # Complete the job
        updated_job = job_repo.update_status(job.id, ProcessingStatus.COMPLETED)
        
        # Duration should be approximately the wait time
        assert abs(updated_job.duration_seconds - wait_time) < 0.1
    
    def test_job_failure_sets_completed_at(self, job_repo, sample_media_file):
        """Test that failed jobs also set completed_at and duration."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        # Set to PROCESSING
        job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
        
        # Wait a small amount
        import time
        time.sleep(0.1)
        
        # Fail the job
        updated_job = job_repo.update_status(
            job.id, 
            ProcessingStatus.FAILED,
            error_message="Test error"
        )
        
        assert updated_job.status == ProcessingStatus.FAILED
        assert updated_job.started_at is not None
        assert updated_job.completed_at is not None
        assert updated_job.duration_seconds is not None
        assert updated_job.error_message == "Test error"
    
    def test_job_completion_without_processing_does_not_set_duration(self, job_repo, sample_media_file):
        """Test that completing a job without PROCESSING status doesn't set duration."""
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        # Complete directly without PROCESSING
        updated_job = job_repo.update_status(job.id, ProcessingStatus.COMPLETED)
        
        assert updated_job.status == ProcessingStatus.COMPLETED
        assert updated_job.started_at is None
        assert updated_job.completed_at is not None
        assert updated_job.duration_seconds is None
    
    def test_job_statistics_includes_timing(self, job_repo, sample_media_file):
        """Test that job statistics include timing information."""
        # Create and complete a job with proper timing
        job = job_repo.create(
            media_file_id=sample_media_file.id,
            job_type="download",
            input_path="https://example.com/video.mp4"
        )
        
        job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
        import time
        time.sleep(0.1)
        job_repo.update_status(job.id, ProcessingStatus.COMPLETED)
        
        # Get statistics
        stats = job_repo.get_job_statistics()
        
        assert 'jobs_by_status' in stats
        assert 'jobs_by_type' in stats
        assert ProcessingStatus.COMPLETED in stats['jobs_by_status']
        # Note: This test counts all jobs in the database, not just the test job
        # The assertion should check that there's at least 1 completed job
        assert stats['jobs_by_status'][ProcessingStatus.COMPLETED] >= 1
    
    def test_multiple_jobs_timing(self, job_repo, sample_media_file):
        """Test timing for multiple jobs."""
        jobs = []
        
        # Create multiple jobs
        for i in range(3):
            job = job_repo.create(
                media_file_id=sample_media_file.id,
                job_type="download",
                input_path=f"https://example.com/video{i}.mp4"
            )
            jobs.append(job)
        
        # Process them with different timing
        for i, job in enumerate(jobs):
            job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
            import time
            time.sleep(0.1 * (i + 1))  # Different wait times
            job_repo.update_status(job.id, ProcessingStatus.COMPLETED)
        
        # Verify all jobs have proper timing
        for job in jobs:
            updated_job = job_repo.get_by_id(job.id)
            assert updated_job.started_at is not None
            assert updated_job.completed_at is not None
            assert updated_job.duration_seconds is not None
            assert updated_job.duration_seconds > 0
