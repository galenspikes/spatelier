"""
Video processing test fixtures.

Provides fixtures for video testing including mock video files,
transcription data, and video processing scenarios.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import pytest

try:
    from modules.video.transcription_service import (
        TranscriptionService,
        TranscriptionStorage,
    )
except ImportError:
    # Optional dependency - tests that need this will import it directly
    TranscriptionService = None
    TranscriptionStorage = None


@pytest.fixture
def mock_video_info():
    """Mock video information from yt-dlp."""
    return {
        "id": "test_video_123",
        "title": "Test Video Title",
        "description": "Test video description",
        "uploader": "Test Uploader",
        "upload_date": "20240101",
        "duration": 120,
        "thumbnail": "https://example.com/thumb.jpg",
        "extractor_key": "youtube",
        "webpage_url": "https://youtube.com/watch?v=test_video_123",
    }


@pytest.fixture
def mock_transcription_data():
    """Mock transcription data from Whisper."""
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
                    {"word": "this", "start": 0.5, "end": 0.8},
                    {"word": "is", "start": 0.8, "end": 1.0},
                    {"word": "a", "start": 1.0, "end": 1.1},
                    {"word": "test", "start": 1.1, "end": 1.5},
                    {"word": "transcription", "start": 1.5, "end": 2.0},
                ],
            },
            {
                "id": 1,
                "start": 5.0,
                "end": 10.0,
                "text": "This is the second segment of the transcription.",
                "words": [
                    {"word": "This", "start": 5.0, "end": 5.3},
                    {"word": "is", "start": 5.3, "end": 5.5},
                    {"word": "the", "start": 5.5, "end": 5.7},
                    {"word": "second", "start": 5.7, "end": 6.2},
                    {"word": "segment", "start": 6.2, "end": 6.8},
                    {"word": "of", "start": 6.8, "end": 7.0},
                    {"word": "the", "start": 7.0, "end": 7.2},
                    {"word": "transcription", "start": 7.2, "end": 8.0},
                ],
            },
        ],
        "text": "Hello, this is a test transcription. This is the second segment of the transcription.",
        "processing_time": 15.5,
        "model_used": "whisper-base",
    }


@pytest.fixture
def mock_srt_content():
    """Mock SRT subtitle content."""
    return """1
00:00:00,000 --> 00:00:05,000
Hello, this is a test transcription.

2
00:00:05,000 --> 00:00:10,000
This is the second segment of the transcription.
"""


@pytest.fixture
def mock_vtt_content():
    """Mock VTT subtitle content."""
    return """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello, this is a test transcription.

00:00:05.000 --> 00:00:10.000
This is the second segment of the transcription.
"""


@pytest.fixture
def video_processing_scenarios():
    """Various video processing scenarios for testing."""
    return {
        "short_video": {
            "duration": 30,
            "size_mb": 5,
            "format": "mp4",
            "has_audio": True,
            "has_subtitles": False,
        },
        "long_video": {
            "duration": 3600,  # 1 hour
            "size_mb": 500,
            "format": "mp4",
            "has_audio": True,
            "has_subtitles": False,
        },
        "video_with_subs": {
            "duration": 120,
            "size_mb": 50,
            "format": "mp4",
            "has_audio": True,
            "has_subtitles": True,
            "subtitle_tracks": 2,
        },
        "audio_only": {
            "duration": 180,
            "size_mb": 10,
            "format": "mp4",
            "has_audio": True,
            "has_video": False,
            "has_subtitles": False,
        },
        "corrupted_video": {
            "duration": 0,
            "size_mb": 0,
            "format": "mp4",
            "has_audio": False,
            "has_subtitles": False,
            "corrupted": True,
        },
    }


@pytest.fixture
def mock_yt_dlp():
    """Mock yt-dlp for testing."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        # Mock extract_info
        mock_instance.extract_info.return_value = {
            "id": "test_video_123",
            "title": "Test Video",
            "duration": 120,
            "uploader": "Test Uploader",
        }

        # Mock download
        mock_instance.download.return_value = None

        yield mock_instance


@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for testing."""
    with patch("faster_whisper.WhisperModel") as mock_model_class:
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Mock transcribe method
        mock_model.transcribe.return_value = (
            [{"start": 0.0, "end": 5.0, "text": "Hello, this is a test."}],
            {"language": "en", "language_probability": 0.99, "duration": 5.0},
        )

        yield mock_model


@pytest.fixture
def mock_ffmpeg():
    """Mock ffmpeg for testing."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def transcription_service_factory():
    """Factory for creating transcription services with different configurations."""

    def _create_service(
        model_size: str = "base", use_faster_whisper: bool = True, verbose: bool = False
    ) -> TranscriptionService:
        return TranscriptionService(
            model_size=model_size,
            use_faster_whisper=use_faster_whisper,
            verbose=verbose,
        )

    return _create_service


@pytest.fixture
def transcription_storage_factory():
    """Factory for creating transcription storage with different configurations."""

    def _create_storage(
        mongodb_client=None, database_name: str = "test_db", verbose: bool = False
    ) -> TranscriptionStorage:
        return TranscriptionStorage(
            mongodb_client=mongodb_client, database_name=database_name, verbose=verbose
        )

    return _create_storage


@pytest.fixture
def video_download_scenarios():
    """Various video download scenarios for testing."""
    return {
        "successful_download": {
            "url": "https://youtube.com/watch?v=test123",
            "expected_file": "Test Video [test123].mp4",
            "expected_size": 1024 * 1024,  # 1MB
            "should_succeed": True,
        },
        "invalid_url": {
            "url": "https://invalid-url.com/video",
            "expected_file": None,
            "expected_size": 0,
            "should_succeed": False,
        },
        "private_video": {
            "url": "https://youtube.com/watch?v=private123",
            "expected_file": None,
            "expected_size": 0,
            "should_succeed": False,
            "error": "Video is private",
        },
        "age_restricted": {
            "url": "https://youtube.com/watch?v=age_restricted123",
            "expected_file": None,
            "expected_size": 0,
            "should_succeed": False,
            "error": "Video is age restricted",
        },
    }


@pytest.fixture
def playlist_scenarios():
    """Various playlist scenarios for testing."""
    return {
        "simple_playlist": {
            "url": "https://youtube.com/playlist?list=test123",
            "title": "Test Playlist",
            "video_count": 5,
            "videos": [
                {"id": "video1", "title": "Video 1"},
                {"id": "video2", "title": "Video 2"},
                {"id": "video3", "title": "Video 3"},
                {"id": "video4", "title": "Video 4"},
                {"id": "video5", "title": "Video 5"},
            ],
        },
        "empty_playlist": {
            "url": "https://youtube.com/playlist?list=empty123",
            "title": "Empty Playlist",
            "video_count": 0,
            "videos": [],
        },
        "large_playlist": {
            "url": "https://youtube.com/playlist?list=large123",
            "title": "Large Playlist",
            "video_count": 100,
            "videos": [{"id": f"video{i}", "title": f"Video {i}"} for i in range(100)],
        },
    }
