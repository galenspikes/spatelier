"""
Tests for database repositories.

This module tests all repository classes and their methods.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, MediaFile, ProcessingJob, AnalyticsEvent, MediaType, ProcessingStatus
from database.repository import MediaFileRepository, ProcessingJobRepository, AnalyticsRepository


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def media_repo(db_session):
    """Create MediaFileRepository instance."""
    return MediaFileRepository(db_session, verbose=False)


@pytest.fixture
def job_repo(db_session):
    """Create ProcessingJobRepository instance."""
    return ProcessingJobRepository(db_session, verbose=False)


@pytest.fixture
def analytics_repo(db_session):
    """Create AnalyticsRepository instance."""
    return AnalyticsRepository(db_session, verbose=False)


def test_media_file_repository_create(media_repo):
    """Test MediaFileRepository.create method."""
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    assert media_file.id is not None
    assert media_file.file_path == "/test/video.mp4"
    assert media_file.media_type == MediaType.VIDEO


def test_media_file_repository_get_by_id(media_repo):
    """Test MediaFileRepository.get_by_id method."""
    # Create a media file
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Retrieve by ID
    retrieved = media_repo.get_by_id(media_file.id)
    assert retrieved is not None
    assert retrieved.id == media_file.id
    assert retrieved.file_path == "/test/video.mp4"


def test_media_file_repository_get_by_path(media_repo):
    """Test MediaFileRepository.get_by_path method."""
    # Create a media file
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Retrieve by path
    retrieved = media_repo.get_by_path("/test/video.mp4")
    assert retrieved is not None
    assert retrieved.id == media_file.id


def test_media_file_repository_get_by_hash(media_repo):
    """Test MediaFileRepository.get_by_hash method."""
    # Create a media file
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Retrieve by hash
    retrieved = media_repo.get_by_hash("abc123")
    assert retrieved is not None
    assert retrieved.id == media_file.id


def test_media_file_repository_list_by_type(media_repo):
    """Test MediaFileRepository.list_by_type method."""
    # Create multiple media files
    video_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    audio_file = media_repo.create(
        file_path="/test/audio.mp3",
        file_name="audio.mp3",
        file_size=512000,
        file_hash="def456",
        media_type=MediaType.AUDIO,
        mime_type="audio/mp3"
    )
    
    # List video files
    video_files = media_repo.list_by_type(MediaType.VIDEO)
    assert len(video_files) == 1
    assert video_files[0].id == video_file.id
    
    # List audio files
    audio_files = media_repo.list_by_type(MediaType.AUDIO)
    assert len(audio_files) == 1
    assert audio_files[0].id == audio_file.id


def test_media_file_repository_search(media_repo):
    """Test MediaFileRepository.search method."""
    # Create media files with different names
    media_repo.create(
        file_path="/test/vacation_video.mp4",
        file_name="vacation_video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    media_repo.create(
        file_path="/test/work_audio.mp3",
        file_name="work_audio.mp3",
        file_size=512000,
        file_hash="def456",
        media_type=MediaType.AUDIO,
        mime_type="audio/mp3"
    )
    
    # Search for vacation
    results = media_repo.search("vacation")
    assert len(results) == 1
    assert "vacation" in results[0].file_name
    
    # Search for video files only
    results = media_repo.search("work", MediaType.AUDIO)
    assert len(results) == 1
    assert results[0].media_type == MediaType.AUDIO


def test_media_file_repository_statistics(media_repo):
    """Test MediaFileRepository.get_statistics method."""
    # Create media files
    media_repo.create(
        file_path="/test/video1.mp4",
        file_name="video1.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    media_repo.create(
        file_path="/test/audio1.mp3",
        file_name="audio1.mp3",
        file_size=512000,
        file_hash="def456",
        media_type=MediaType.AUDIO,
        mime_type="audio/mp3"
    )
    
    stats = media_repo.get_statistics()
    
    assert 'files_by_type' in stats
    assert 'size_by_type' in stats
    assert 'recent_files' in stats
    
    assert stats['files_by_type']['video'] == 1
    assert stats['files_by_type']['audio'] == 1


def test_processing_job_repository_create(job_repo, media_repo):
    """Test ProcessingJobRepository.create method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Create processing job
    job = job_repo.create(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test"
    )
    
    assert job.id is not None
    assert job.media_file_id == media_file.id
    assert job.job_type == "download"
    assert job.status == ProcessingStatus.PENDING


def test_processing_job_repository_update_status(job_repo, media_repo):
    """Test ProcessingJobRepository.update_status method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Create processing job
    job = job_repo.create(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test"
    )
    
    # Update status to processing
    updated_job = job_repo.update_status(job.id, ProcessingStatus.PROCESSING)
    assert updated_job.status == ProcessingStatus.PROCESSING
    assert updated_job.started_at is not None
    
    # Update status to completed
    updated_job = job_repo.update_status(
        job.id, 
        ProcessingStatus.COMPLETED,
        output_path="/test/output.mp4"
    )
    assert updated_job.status == ProcessingStatus.COMPLETED
    assert updated_job.output_path == "/test/output.mp4"
    assert updated_job.completed_at is not None
    assert updated_job.duration_seconds is not None


def test_processing_job_repository_get_by_status(job_repo, media_repo):
    """Test ProcessingJobRepository.get_by_status method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Create jobs with different statuses
    pending_job = job_repo.create(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test1"
    )
    
    completed_job = job_repo.create(
        media_file_id=media_file.id,
        job_type="convert",
        input_path="https://youtube.com/watch?v=test2"
    )
    job_repo.update_status(completed_job.id, ProcessingStatus.COMPLETED)
    
    # Get pending jobs
    pending_jobs = job_repo.get_by_status(ProcessingStatus.PENDING)
    assert len(pending_jobs) == 1
    assert pending_jobs[0].id == pending_job.id
    
    # Get completed jobs
    completed_jobs = job_repo.get_by_status(ProcessingStatus.COMPLETED)
    assert len(completed_jobs) == 1
    assert completed_jobs[0].id == completed_job.id


def test_processing_job_repository_statistics(job_repo, media_repo):
    """Test ProcessingJobRepository.get_job_statistics method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Create jobs
    job1 = job_repo.create(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test1"
    )
    job_repo.update_status(job1.id, ProcessingStatus.COMPLETED)
    
    job2 = job_repo.create(
        media_file_id=media_file.id,
        job_type="convert",
        input_path="https://youtube.com/watch?v=test2"
    )
    job_repo.update_status(job2.id, ProcessingStatus.FAILED)
    
    stats = job_repo.get_job_statistics()
    
    assert 'jobs_by_status' in stats
    assert 'jobs_by_type' in stats
    assert 'avg_processing_time' in stats
    
    assert stats['jobs_by_status']['completed'] == 1
    assert stats['jobs_by_status']['failed'] == 1
    assert stats['jobs_by_type']['download'] == 1
    assert stats['jobs_by_type']['convert'] == 1


def test_analytics_repository_track_event(analytics_repo, media_repo):
    """Test AnalyticsRepository.track_event method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Track event
    event = analytics_repo.track_event(
        event_type="download",
        media_file_id=media_file.id,
        event_data={"url": "https://youtube.com/watch?v=test"},
        user_id="user123"
    )
    
    assert event.id is not None
    assert event.event_type == "download"
    assert event.media_file_id == media_file.id
    assert event.user_id == "user123"


def test_analytics_repository_get_events_by_type(analytics_repo, media_repo):
    """Test AnalyticsRepository.get_events_by_type method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Track multiple events
    analytics_repo.track_event("download", media_file_id=media_file.id)
    analytics_repo.track_event("download", media_file_id=media_file.id)
    analytics_repo.track_event("convert", media_file_id=media_file.id)
    
    # Get download events
    download_events = analytics_repo.get_events_by_type("download", days=30)
    assert len(download_events) == 2
    
    # Get convert events
    convert_events = analytics_repo.get_events_by_type("convert", days=30)
    assert len(convert_events) == 1


def test_analytics_repository_usage_statistics(analytics_repo, media_repo):
    """Test AnalyticsRepository.get_usage_statistics method."""
    # Create a media file first
    media_file = media_repo.create(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    
    # Track multiple events
    analytics_repo.track_event("download", media_file_id=media_file.id)
    analytics_repo.track_event("convert", media_file_id=media_file.id)
    analytics_repo.track_event("view", media_file_id=media_file.id)
    
    stats = analytics_repo.get_usage_statistics(days=30)
    
    assert 'events_by_type' in stats
    assert 'daily_activity' in stats
    
    assert stats['events_by_type']['download'] == 1
    assert stats['events_by_type']['convert'] == 1
    assert stats['events_by_type']['view'] == 1
