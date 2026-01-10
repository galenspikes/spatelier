"""
Tests for database models.

This module tests all database models and their relationships.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base, MediaFile, ProcessingJob, AnalyticsEvent, DownloadSource, UserPreference,
    MediaType, ProcessingStatus
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_media_file_creation(db_session):
    """Test MediaFile model creation."""
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4",
        duration=120.5,
        width=1920,
        height=1080,
        title="Test Video",
        uploader="Test User",
        source_url="https://youtube.com/watch?v=test",
        source_platform="youtube"
    )
    
    db_session.add(media_file)
    db_session.commit()
    
    assert media_file.id is not None
    assert media_file.file_path == "/test/video.mp4"
    assert media_file.media_type == MediaType.VIDEO
    assert media_file.title == "Test Video"
    assert media_file.source_platform == "youtube"


def test_processing_job_creation(db_session):
    """Test ProcessingJob model creation."""
    # Create a media file first
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    db_session.add(media_file)
    db_session.commit()
    
    # Create processing job
    job = ProcessingJob(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test",
        output_path="/test/video.mp4",
        status=ProcessingStatus.PENDING
    )
    
    db_session.add(job)
    db_session.commit()
    
    assert job.id is not None
    assert job.media_file_id == media_file.id
    assert job.job_type == "download"
    assert job.status == ProcessingStatus.PENDING


def test_analytics_event_creation(db_session):
    """Test AnalyticsEvent model creation."""
    # Create a media file first
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    db_session.add(media_file)
    db_session.commit()
    
    # Create analytics event
    event = AnalyticsEvent(
        media_file_id=media_file.id,
        event_type="download",
        event_data='{"url": "https://youtube.com/watch?v=test"}',
        user_id="user123"
    )
    
    db_session.add(event)
    db_session.commit()
    
    assert event.id is not None
    assert event.media_file_id == media_file.id
    assert event.event_type == "download"
    assert event.user_id == "user123"


def test_download_source_creation(db_session):
    """Test DownloadSource model creation."""
    source = DownloadSource(
        url="https://youtube.com/watch?v=test",
        domain="youtube.com",
        title="Test Video",
        description="A test video",
        duration=120.5,
        uploader="Test User",
        view_count=1000,
        like_count=50
    )
    
    db_session.add(source)
    db_session.commit()
    
    assert source.id is not None
    assert source.url == "https://youtube.com/watch?v=test"
    assert source.domain == "youtube.com"
    assert source.title == "Test Video"


def test_user_preference_creation(db_session):
    """Test UserPreference model creation."""
    preference = UserPreference(
        user_id="user123",
        preference_key="default_quality",
        preference_value="1080p"
    )
    
    db_session.add(preference)
    db_session.commit()
    
    assert preference.id is not None
    assert preference.user_id == "user123"
    assert preference.preference_key == "default_quality"
    assert preference.preference_value == "1080p"


def test_media_file_relationships(db_session):
    """Test MediaFile relationships."""
    # Create media file
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    db_session.add(media_file)
    db_session.commit()
    
    # Create processing job
    job = ProcessingJob(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test",
        status=ProcessingStatus.PENDING
    )
    db_session.add(job)
    db_session.commit()
    
    # Create analytics event
    event = AnalyticsEvent(
        media_file_id=media_file.id,
        event_type="download",
        user_id="user123"
    )
    db_session.add(event)
    db_session.commit()
    
    # Test relationships
    assert len(media_file.processing_jobs) == 1
    assert media_file.processing_jobs[0].id == job.id
    
    assert len(media_file.analytics_events) == 1
    assert media_file.analytics_events[0].id == event.id


def test_processing_job_status_updates(db_session):
    """Test ProcessingJob status updates."""
    # Create media file
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4"
    )
    db_session.add(media_file)
    db_session.commit()
    
    # Create processing job
    job = ProcessingJob(
        media_file_id=media_file.id,
        job_type="download",
        input_path="https://youtube.com/watch?v=test",
        status=ProcessingStatus.PENDING
    )
    db_session.add(job)
    db_session.commit()
    
    # Update status
    job.status = ProcessingStatus.PROCESSING
    job.started_at = datetime.now()
    db_session.commit()
    
    # Update to completed
    job.status = ProcessingStatus.COMPLETED
    job.completed_at = datetime.now()
    job.duration_seconds = 30.5
    db_session.commit()
    
    assert job.status == ProcessingStatus.COMPLETED
    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.duration_seconds == 30.5


def test_media_file_metadata_fields(db_session):
    """Test MediaFile metadata fields."""
    media_file = MediaFile(
        file_path="/test/video.mp4",
        file_name="video.mp4",
        file_size=1024000,
        file_hash="abc123",
        media_type=MediaType.VIDEO,
        mime_type="video/mp4",
        # Video metadata
        title="Amazing Test Video",
        description="This is a test video description",
        uploader="Test Channel",
        uploader_id="testchannel123",
        upload_date=datetime(2023, 1, 1),
        view_count=10000,
        like_count=500,
        dislike_count=10,
        comment_count=100,
        tags='["test", "video", "demo"]',
        categories='["Entertainment", "Education"]',
        language="en",
        age_limit=0,
        # Source information
        source_url="https://youtube.com/watch?v=test123",
        source_platform="youtube",
        source_id="test123",
        source_title="Amazing Test Video",
        source_description="This is a test video description",
        # Technical metadata
        fps=30.0,
        aspect_ratio="16:9",
        color_space="bt709",
        audio_codec="aac",
        video_codec="h264",
        # Thumbnail
        thumbnail_url="https://img.youtube.com/vi/test123/maxresdefault.jpg"
    )
    
    db_session.add(media_file)
    db_session.commit()
    
    # Test all metadata fields
    assert media_file.title == "Amazing Test Video"
    assert media_file.description == "This is a test video description"
    assert media_file.uploader == "Test Channel"
    assert media_file.uploader_id == "testchannel123"
    assert media_file.view_count == 10000
    assert media_file.like_count == 500
    assert media_file.source_platform == "youtube"
    assert media_file.fps == 30.0
    assert media_file.aspect_ratio == "16:9"
    assert media_file.video_codec == "h264"
    assert media_file.audio_codec == "aac"
