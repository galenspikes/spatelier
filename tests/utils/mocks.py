"""
Mock utilities for testing.

Provides mock objects and utilities for testing
various components of the spatelier application.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch


def create_mock_database_manager():
    """Create a mock database manager."""
    mock_manager = Mock()
    mock_manager.connect_sqlite = Mock()
    mock_manager.connect_mongodb = Mock()
    mock_manager.get_sqlite_session = Mock()
    mock_manager.get_mongodb_client = Mock()
    mock_manager.close_connections = Mock()
    return mock_manager


def create_mock_media_file_repository():
    """Create a mock media file repository."""
    mock_repo = Mock()
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.get_by_path = Mock()
    mock_repo.get_by_hash = Mock()
    mock_repo.update = Mock()
    mock_repo.delete = Mock()
    mock_repo.list_by_type = Mock()
    mock_repo.search = Mock()
    mock_repo.statistics = Mock()
    return mock_repo


def create_mock_processing_job_repository():
    """Create a mock processing job repository."""
    mock_repo = Mock()
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.update = Mock()
    mock_repo.update_status = Mock()
    mock_repo.get_by_status = Mock()
    mock_repo.statistics = Mock()
    return mock_repo


def create_mock_analytics_repository():
    """Create a mock analytics repository."""
    mock_repo = Mock()
    mock_repo.track_event = Mock()
    mock_repo.get_events_by_type = Mock()
    mock_repo.usage_statistics = Mock()
    return mock_repo


def create_mock_transcription_service():
    """Create a mock transcription service."""
    mock_service = Mock()
    mock_service.transcribe_video = Mock()
    mock_service.get_model_info = Mock()
    return mock_service


def create_mock_transcription_storage():
    """Create a mock transcription storage."""
    mock_storage = Mock()
    mock_storage.store_transcription = Mock()
    mock_storage.get_transcription = Mock()
    mock_storage.search_transcriptions = Mock()
    mock_storage.generate_srt_subtitle = Mock()
    mock_storage.generate_vtt_subtitle = Mock()
    return mock_storage


def create_mock_video_downloader():
    """Create a mock video downloader."""
    mock_downloader = Mock()
    mock_downloader.download = Mock()
    mock_downloader.download_playlist_with_transcription = Mock()
    mock_downloader._transcribe_video = Mock()
    mock_downloader._embed_subtitles_into_video = Mock()
    return mock_downloader


def create_mock_yt_dlp():
    """Create a mock yt-dlp instance."""
    mock_ydl = Mock()
    mock_ydl.extract_info = Mock()
    mock_ydl.download = Mock()
    return mock_ydl


def create_mock_ffmpeg():
    """Create a mock ffmpeg subprocess."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "ffmpeg output"
    mock_result.stderr = ""
    return mock_result


def create_mock_whisper_model():
    """Create a mock Whisper model."""
    mock_model = Mock()
    mock_model.transcribe = Mock()
    return mock_model


def create_mock_file_system():
    """Create a mock file system."""
    mock_fs = Mock()
    mock_fs.exists = Mock(return_value=True)
    mock_fs.is_file = Mock(return_value=True)
    mock_fs.is_dir = Mock(return_value=False)
    mock_fs.stat = Mock()
    mock_fs.unlink = Mock()
    mock_fs.mkdir = Mock()
    return mock_fs


def create_mock_network():
    """Create a mock network interface."""
    mock_network = Mock()
    mock_network.get = Mock()
    mock_network.post = Mock()
    mock_network.put = Mock()
    mock_network.delete = Mock()
    return mock_network


def create_mock_config():
    """Create a mock configuration."""
    mock_config = Mock()
    mock_config.core.debug = True
    mock_config.verbose = True
    mock_config.video.output_dir = Path("/tmp/test_videos")
    mock_config.transcription.default_model = "base"
    mock_config.transcription.default_language = "en"
    mock_config.audio.output_dir = Path("/tmp/test_audio")
    mock_config.database.sqlite_path = Path("/tmp/test.db")
    mock_config.database.mongodb_database = "test_db"
    mock_config.log_level = "DEBUG"
    return mock_config


def create_mock_logger():
    """Create a mock logger."""
    mock_logger = Mock()
    mock_logger.debug = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.critical = Mock()
    return mock_logger


def create_mock_job_context():
    """Create a mock job context."""
    mock_context = Mock()
    mock_context.job_id = 12345
    mock_context.source_url = "https://example.com/video"
    mock_context.final_destination = Path("/tmp/test_output.mp4")
    mock_context.is_nas_destination = False
    mock_context.temp_dir = None
    mock_context.current_file_path = None
    mock_context.media_file_id = None
    mock_context.source_metadata = {}
    mock_context.processing_metadata = {}
    mock_context.step_results = {}
    return mock_context


def create_mock_step_result():
    """Create a mock step result."""
    mock_result = Mock()
    mock_result.step_name = "TestStep"
    mock_result.status = "completed"
    mock_result.success = True
    mock_result.message = "Test step completed"
    mock_result.output_path = Path("/tmp/test_output.mp4")
    mock_result.metadata = {}
    mock_result.errors = []
    return mock_result


def create_mock_processing_result():
    """Create a mock processing result."""
    mock_result = Mock()
    mock_result.success = True
    mock_result.message = "Processing completed"
    mock_result.output_path = Path("/tmp/test_output.mp4")
    mock_result.metadata = {}
    mock_result.errors = []
    return mock_result


def create_mock_media_file():
    """Create a mock media file."""
    mock_file = Mock()
    mock_file.id = 1
    mock_file.file_path = "/tmp/test_video.mp4"
    mock_file.file_name = "test_video.mp4"
    mock_file.file_size = 1024 * 1024
    mock_file.file_hash = "test_hash_123"
    mock_file.media_type = "video"
    mock_file.source_url = "https://example.com/video"
    mock_file.source_id = "test_id_123"
    mock_file.title = "Test Video"
    mock_file.description = "Test video description"
    mock_file.uploader = "Test Uploader"
    mock_file.upload_date = "2024-01-01"
    mock_file.duration = 120
    mock_file.thumbnail_url = "https://example.com/thumb.jpg"
    mock_file.source_platform = "youtube"
    return mock_file


def create_mock_processing_job():
    """Create a mock processing job."""
    mock_job = Mock()
    mock_job.id = 1
    mock_job.media_file_id = 1
    mock_job.job_type = "download"
    mock_job.input_path = "https://example.com/video"
    mock_job.output_path = "/tmp/test_output.mp4"
    mock_job.parameters = "{}"
    mock_job.status = "completed"
    mock_job.created_at = "2024-01-01T00:00:00Z"
    mock_job.started_at = "2024-01-01T00:01:00Z"
    mock_job.completed_at = "2024-01-01T00:02:00Z"
    mock_job.duration_seconds = 60
    mock_job.error_message = None
    return mock_job


def create_mock_analytics_event():
    """Create a mock analytics event."""
    mock_event = Mock()
    mock_event.id = 1
    mock_event.event_type = "download_completed"
    mock_event.media_file_id = 1
    mock_event.processing_job_id = 1
    mock_event.event_data = {"test": "data"}
    mock_event.timestamp = "2024-01-01T00:00:00Z"
    return mock_event


def create_mock_playlist():
    """Create a mock playlist."""
    mock_playlist = Mock()
    mock_playlist.id = 1
    mock_playlist.title = "Test Playlist"
    mock_playlist.description = "Test playlist description"
    mock_playlist.source_url = "https://example.com/playlist"
    mock_playlist.source_id = "playlist_123"
    mock_playlist.uploader = "Test Uploader"
    mock_playlist.video_count = 5
    mock_playlist.thumbnail_url = "https://example.com/playlist_thumb.jpg"
    return mock_playlist


def create_mock_playlist_video():
    """Create a mock playlist video."""
    mock_playlist_video = Mock()
    mock_playlist_video.id = 1
    mock_playlist_video.playlist_id = 1
    mock_playlist_video.media_file_id = 1
    mock_playlist_video.position = 1
    mock_playlist_video.video_title = "Test Video"
    return mock_playlist_video


def create_mock_transcription_data():
    """Create mock transcription data."""
    return {
        "language": "en",
        "language_name": "English",
        "duration": 120.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.0,
                "text": "Hello, this is a test transcription.",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "this", "start": 0.5, "end": 1.0},
                    {"word": "is", "start": 1.0, "end": 1.5},
                    {"word": "a", "start": 1.5, "end": 2.0},
                    {"word": "test", "start": 2.0, "end": 2.5},
                    {"word": "transcription", "start": 2.5, "end": 3.0},
                ],
            }
        ],
        "text": "Hello, this is a test transcription.",
        "processing_time": 10.0,
        "model_used": "whisper-base",
    }


def create_mock_video_info():
    """Create mock video information."""
    return {
        "id": "test_video_123",
        "title": "Test Video",
        "description": "Test video description",
        "uploader": "Test Uploader",
        "upload_date": "20240101",
        "duration": 120,
        "thumbnail": "https://example.com/thumb.jpg",
        "extractor_key": "youtube",
        "webpage_url": "https://youtube.com/watch?v=test_video_123",
    }


def create_mock_playlist_info():
    """Create mock playlist information."""
    return {
        "id": "playlist_123",
        "title": "Test Playlist",
        "uploader": "Test Uploader",
        "entries": [
            {
                "id": "video1",
                "title": "Video 1",
                "duration": 60,
                "uploader": "Test Uploader",
            },
            {
                "id": "video2",
                "title": "Video 2",
                "duration": 90,
                "uploader": "Test Uploader",
            },
        ],
    }


def create_mock_srt_content():
    """Create mock SRT content."""
    return """1
00:00:00,000 --> 00:00:05,000
Hello, this is a test transcription.

2
00:00:05,000 --> 00:00:10,000
This is the second segment.
"""


def create_mock_vtt_content():
    """Create mock VTT content."""
    return """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello, this is a test transcription.

00:00:05.000 --> 00:00:10.000
This is the second segment.
"""


def create_mock_file_stat():
    """Create mock file statistics."""
    mock_stat = Mock()
    mock_stat.st_size = 1024 * 1024  # 1MB
    mock_stat.st_mtime = 1640995200  # 2022-01-01
    mock_stat.st_mode = 0o644
    return mock_stat


def create_mock_directory_stat():
    """Create mock directory statistics."""
    mock_stat = Mock()
    mock_stat.st_size = 4096  # 4KB
    mock_stat.st_mtime = 1640995200  # 2022-01-01
    mock_stat.st_mode = 0o755
    return mock_stat


def create_mock_subprocess_result():
    """Create mock subprocess result."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Command output"
    mock_result.stderr = ""
    return mock_result


def create_mock_exception(exception_type: type, message: str = "Test exception"):
    """Create a mock exception."""
    return exception_type(message)


def create_mock_patch_decorator():
    """Create a mock patch decorator."""
    return patch


def create_mock_temp_file():
    """Create a mock temporary file."""
    mock_file = Mock()
    mock_file.name = "/tmp/temp_file_123.txt"
    mock_file.write = Mock()
    mock_file.read = Mock(return_value="test content")
    mock_file.close = Mock()
    return mock_file


def create_mock_temp_directory():
    """Create a mock temporary directory."""
    mock_dir = Mock()
    mock_dir.name = "/tmp/temp_dir_123"
    mock_dir.mkdir = Mock()
    mock_dir.rmdir = Mock()
    mock_dir.exists = Mock(return_value=True)
    mock_dir.is_dir = Mock(return_value=True)
    return mock_dir
