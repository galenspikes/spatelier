"""
Database test fixtures and factories.

Provides reusable fixtures for database testing including
test data creation, cleanup, and database state management.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from spatelier.core.config import Config
from spatelier.database.connection import DatabaseManager
from spatelier.database.models import (
    AnalyticsEvent,
    Base,
    MediaFile,
    Playlist,
    PlaylistVideo,
    ProcessingJob,
)
from spatelier.database.repository import (
    AnalyticsRepository,
    MediaFileRepository,
    PlaylistRepository,
    PlaylistVideoRepository,
    ProcessingJobRepository,
)


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database file for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_file.close()
    return Path(temp_file.name)


@pytest.fixture
def test_config(temp_db_path: Path) -> Config:
    """Create test configuration with temporary database."""
    config = Config()
    config.database.sqlite_path = str(temp_db_path)
    config.mongodb_database = "test_spatelier"
    return config


@pytest.fixture
def test_db_engine(temp_db_path: Path):
    """Create test database engine."""
    engine = create_engine(f"sqlite:///{temp_db_path}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    temp_db_path.unlink(missing_ok=True)


@pytest.fixture
def test_db_session(test_db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_db_manager(test_config: Config) -> Generator[DatabaseManager, None, None]:
    """Create test database manager."""
    db_manager = DatabaseManager(test_config)
    db_manager.connect_sqlite()
    yield db_manager
    db_manager.close_connections()


@pytest.fixture
def media_file_factory():
    """Factory for creating test media files."""

    def _create_media_file(**kwargs) -> Dict[str, Any]:
        defaults = {
            "file_path": "/test/path/video.mp4",
            "file_name": "test_video.mp4",
            "file_size": 1024 * 1024,  # 1MB
            "file_hash": "test_hash_123",
            "media_type": "video",
            "source_url": "https://example.com/video",
            "source_id": "test_id_123",
            "title": "Test Video",
            "description": "Test video description",
            "uploader": "Test Uploader",
            "upload_date": "2024-01-01",
            "duration": 120,
            "thumbnail_url": "https://example.com/thumb.jpg",
            "source_platform": "youtube",
        }
        defaults.update(kwargs)
        return defaults

    return _create_media_file


@pytest.fixture
def processing_job_factory():
    """Factory for creating test processing jobs."""

    def _create_processing_job(**kwargs) -> Dict[str, Any]:
        defaults = {
            "media_file_id": 1,
            "job_type": "download",
            "input_path": "https://example.com/video",
            "output_path": "/test/output/video.mp4",
            "parameters": "{}",
            "status": "pending",
        }
        defaults.update(kwargs)
        return defaults

    return _create_processing_job


@pytest.fixture
def analytics_event_factory():
    """Factory for creating test analytics events."""

    def _create_analytics_event(**kwargs) -> Dict[str, Any]:
        defaults = {
            "event_type": "download_completed",
            "media_file_id": 1,
            "processing_job_id": 1,
            "event_data": {"test": "data"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        defaults.update(kwargs)
        return defaults

    return _create_analytics_event


@pytest.fixture
def playlist_factory():
    """Factory for creating test playlists."""

    def _create_playlist(**kwargs) -> Dict[str, Any]:
        defaults = {
            "title": "Test Playlist",
            "description": "Test playlist description",
            "source_url": "https://example.com/playlist",
            "source_id": "playlist_123",
            "uploader": "Test Uploader",
            "video_count": 5,
            "thumbnail_url": "https://example.com/playlist_thumb.jpg",
        }
        defaults.update(kwargs)
        return defaults

    return _create_playlist


@pytest.fixture
def sample_media_files(media_file_factory) -> List[Dict[str, Any]]:
    """Create sample media files for testing."""
    return [
        media_file_factory(
            id=1, file_path="/test/video1.mp4", title="Video 1", source_id="video_1"
        ),
        media_file_factory(
            id=2, file_path="/test/video2.mp4", title="Video 2", source_id="video_2"
        ),
        media_file_factory(
            id=3,
            file_path="/test/audio1.mp3",
            title="Audio 1",
            media_type="audio",
            source_id="audio_1",
        ),
    ]


@pytest.fixture
def sample_processing_jobs(processing_job_factory) -> List[Dict[str, Any]]:
    """Create sample processing jobs for testing."""
    return [
        processing_job_factory(
            id=1, media_file_id=1, job_type="download", status="completed"
        ),
        processing_job_factory(
            id=2, media_file_id=2, job_type="transcribe", status="processing"
        ),
        processing_job_factory(
            id=3, media_file_id=3, job_type="convert", status="failed"
        ),
    ]


@pytest.fixture
def populated_test_db(test_db_session, sample_media_files, sample_processing_jobs):
    """Create a test database with sample data."""
    # Add media files
    for media_data in sample_media_files:
        media_file = MediaFile(**media_data)
        test_db_session.add(media_file)

    # Add processing jobs
    for job_data in sample_processing_jobs:
        processing_job = ProcessingJob(**job_data)
        test_db_session.add(processing_job)

    test_db_session.commit()
    return test_db_session
