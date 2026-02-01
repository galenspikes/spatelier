"""
Audio processing test fixtures.

Provides fixtures for audio testing including mock audio files,
conversion scenarios, and audio processing utilities.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import pytest

# from spatelier.modules.audio.converter import AudioConverter  # Module doesn't exist yet


@pytest.fixture
def mock_audio_info():
    """Mock audio information from ffprobe."""
    return {
        "format": {
            "filename": "/test/audio.mp3",
            "format_name": "mp3",
            "format_long_name": "MP2/3 (MPEG audio layer 2/3)",
            "duration": "120.000000",
            "size": "1920000",
            "bit_rate": "128000",
        },
        "streams": [
            {
                "index": 0,
                "codec_name": "mp3",
                "codec_long_name": "MP3 (MPEG audio layer 3)",
                "codec_type": "audio",
                "sample_rate": "44100",
                "channels": 2,
                "bit_rate": "128000",
            }
        ],
    }


@pytest.fixture
def audio_conversion_scenarios():
    """Various audio conversion scenarios for testing."""
    return {
        "mp3_to_wav": {
            "input_format": "mp3",
            "output_format": "wav",
            "input_file": "test.mp3",
            "output_file": "test.wav",
            "expected_quality": "high",
        },
        "wav_to_flac": {
            "input_format": "wav",
            "output_format": "flac",
            "input_file": "test.wav",
            "output_file": "test.flac",
            "expected_quality": "lossless",
        },
        "mp3_to_aac": {
            "input_format": "mp3",
            "output_format": "aac",
            "input_file": "test.mp3",
            "output_file": "test.aac",
            "expected_quality": "high",
        },
        "low_quality_conversion": {
            "input_format": "mp3",
            "output_format": "mp3",
            "input_file": "test.mp3",
            "output_file": "test_low.mp3",
            "expected_quality": "low",
        },
    }


@pytest.fixture
def audio_file_scenarios():
    """Various audio file scenarios for testing."""
    return {
        "short_audio": {
            "duration": 30,
            "size_mb": 1,
            "format": "mp3",
            "bitrate": 128,
            "sample_rate": 44100,
            "channels": 2,
        },
        "long_audio": {
            "duration": 3600,  # 1 hour
            "size_mb": 50,
            "format": "mp3",
            "bitrate": 320,
            "sample_rate": 44100,
            "channels": 2,
        },
        "high_quality_audio": {
            "duration": 180,
            "size_mb": 20,
            "format": "flac",
            "bitrate": 1411,
            "sample_rate": 44100,
            "channels": 2,
        },
        "stereo_audio": {
            "duration": 120,
            "size_mb": 5,
            "format": "wav",
            "bitrate": 1411,
            "sample_rate": 48000,
            "channels": 2,
        },
        "mono_audio": {
            "duration": 90,
            "size_mb": 2,
            "format": "mp3",
            "bitrate": 64,
            "sample_rate": 22050,
            "channels": 1,
        },
        "corrupted_audio": {
            "duration": 0,
            "size_mb": 0,
            "format": "mp3",
            "bitrate": 0,
            "sample_rate": 0,
            "channels": 0,
            "corrupted": True,
        },
    }


@pytest.fixture
def mock_ffmpeg_audio():
    """Mock ffmpeg for audio processing."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg audio processing output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def audio_converter_factory():
    """Factory for creating audio converters with different configurations."""

    def _create_converter(
        input_format: str = "mp3",
        output_format: str = "wav",
        quality: str = "high",
        verbose: bool = False,
    ):
        # Mock converter for now
        return Mock(
            input_format=input_format,
            output_format=output_format,
            quality=quality,
            verbose=verbose,
        )

    return _create_converter


@pytest.fixture
def audio_metadata_scenarios():
    """Various audio metadata scenarios for testing."""
    return {
        "complete_metadata": {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "year": "2024",
            "genre": "Test Genre",
            "track": "1",
            "duration": 180,
        },
        "minimal_metadata": {
            "title": "Unknown",
            "artist": "Unknown",
            "album": "",
            "year": "",
            "genre": "",
            "track": "",
            "duration": 0,
        },
        "partial_metadata": {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "",
            "year": "2024",
            "genre": "",
            "track": "",
            "duration": 120,
        },
    }


@pytest.fixture
def audio_processing_errors():
    """Various audio processing error scenarios."""
    return {
        "file_not_found": {
            "error_type": "FileNotFoundError",
            "message": "Audio file not found",
            "should_raise": True,
        },
        "unsupported_format": {
            "error_type": "ValueError",
            "message": "Unsupported audio format",
            "should_raise": True,
        },
        "corrupted_file": {
            "error_type": "RuntimeError",
            "message": "Corrupted audio file",
            "should_raise": True,
        },
        "permission_denied": {
            "error_type": "PermissionError",
            "message": "Permission denied",
            "should_raise": True,
        },
        "disk_full": {
            "error_type": "OSError",
            "message": "No space left on device",
            "should_raise": True,
        },
    }


@pytest.fixture
def batch_audio_scenarios():
    """Various batch audio processing scenarios."""
    return {
        "small_batch": {
            "file_count": 5,
            "total_size_mb": 25,
            "formats": ["mp3", "wav", "flac"],
            "expected_duration": 300,  # 5 minutes total
        },
        "large_batch": {
            "file_count": 100,
            "total_size_mb": 500,
            "formats": ["mp3", "wav", "flac", "aac"],
            "expected_duration": 6000,  # 100 minutes total
        },
        "mixed_formats": {
            "file_count": 20,
            "total_size_mb": 100,
            "formats": ["mp3", "wav", "flac", "aac", "ogg"],
            "expected_duration": 1200,  # 20 minutes total
        },
        "single_format": {
            "file_count": 50,
            "total_size_mb": 250,
            "formats": ["mp3"],
            "expected_duration": 3000,  # 50 minutes total
        },
    }
