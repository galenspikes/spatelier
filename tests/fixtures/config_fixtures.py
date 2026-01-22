"""
Configuration test fixtures.

Provides fixtures for creating test configurations,
environment variables, and configuration validation.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import patch

import pytest

from core.config import AudioConfig, Config, VideoConfig


@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """Create a temporary configuration file."""
    config_content = """
[core]
debug = true
verbose = true

[video]
output_dir = "/tmp/test_videos"
transcribe = true
transcription_model = "base"
transcription_language = "en"
use_fallback = true

[audio]
output_dir = "/tmp/test_audio"
format = "mp3"
quality = "high"

[database]
sqlite_path = "/tmp/test.db"
mongodb_url = "mongodb://localhost:27017"
mongodb_database = "test_spatelier"

[logging]
level = "DEBUG"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    config = Config()
    config.debug = True
    config.verbose = True
    config.video.output_dir = Path("/tmp/test_videos")
    config.transcription.default_model = "base"
    config.transcription.default_language = "en"
    config.audio.output_dir = Path("/tmp/test_audio")
    config.database.sqlite_path = Path("/tmp/test.db")
    config.database.mongodb_database = "test_spatelier"
    config.log_level = "DEBUG"
    return config


@pytest.fixture
def minimal_config() -> Config:
    """Create a minimal test configuration."""
    config = Config()
    config.database.sqlite_path = "/tmp/minimal_test.db"
    return config


@pytest.fixture
def production_config() -> Config:
    """Create a production-like configuration."""
    config = Config()
    config.debug = False
    config.verbose = False
    config.transcription.default_model = "large"
    config.transcription.default_language = "en"
    config.audio.default_format = "mp3"
    config.database.sqlite_path = Path("/var/lib/spatelier/spatelier.db")
    config.database.mongodb_database = "spatelier_prod"
    config.log_level = "INFO"
    return config


@pytest.fixture
def env_vars():
    """Set up environment variables for testing."""
    env = {
        "SPATELIER_DEBUG": "true",
        "SPATELIER_VERBOSE": "true",
        "SPATELIER_VIDEO_TRANSCRIBE": "true",
        "SPATELIER_VIDEO_MODEL": "base",
        "SPATELIER_DATABASE_PATH": "/tmp/env_test.db",
        "SPATELIER_MONGODB_DATABASE": "test_env",
    }

    with patch.dict(os.environ, env):
        yield env


@pytest.fixture
def config_factory():
    """Factory for creating custom configurations."""

    def _create_config(**kwargs) -> Config:
        config = Config()

        # Apply core settings
        if "debug" in kwargs:
            config.debug = kwargs["debug"]
        if "verbose" in kwargs:
            config.verbose = kwargs["verbose"]

        # Apply video settings
        if "video_output" in kwargs:
            config.video.output_dir = Path(kwargs["video_output"])
        if "model" in kwargs:
            config.transcription.default_model = kwargs["model"]
        if "language" in kwargs:
            config.transcription.default_language = kwargs["language"]

        # Apply audio settings
        if "audio_output" in kwargs:
            config.audio.output_dir = Path(kwargs["audio_output"])
        if "audio_format" in kwargs:
            config.audio.default_format = kwargs["audio_format"]

        # Apply database settings
        if "db_path" in kwargs:
            config.database.sqlite_path = Path(kwargs["db_path"])
        if "mongodb_db" in kwargs:
            config.database.mongodb_database = kwargs["mongodb_db"]

        # Apply logging settings
        if "log_level" in kwargs:
            config.log_level = kwargs["log_level"]

        return config

    return _create_config


@pytest.fixture
def invalid_config():
    """Create an invalid configuration for testing validation."""
    config = Config()
    config.video.output_dir = Path("/nonexistent/path")
    config.database.sqlite_path = Path("")
    config.log_level = "INVALID_LEVEL"
    return config


@pytest.fixture
def config_with_nas_paths():
    """Create configuration with NAS paths for testing."""
    config = Config()
    config.video.output_dir = Path("/Volumes/NAS/Media/Videos")
    config.audio.output_dir = Path("/Volumes/NAS/Media/Audio")
    config.database.sqlite_path = Path("/Volumes/NAS/Data/spatelier.db")
    return config


@pytest.fixture
def config_validation_fixtures():
    """Provide various configuration validation test cases."""
    return {
        "valid_paths": ["/tmp/test", "/home/user/videos", "/var/lib/spatelier"],
        "invalid_paths": ["", "/nonexistent/path", None],
        "valid_languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
        "invalid_languages": ["invalid", "xx", "123", ""],
        "valid_models": ["tiny", "base", "small", "medium", "large"],
        "invalid_models": ["invalid", "huge", "micro", ""],
        "valid_formats": ["mp3", "wav", "flac", "aac", "ogg"],
        "invalid_formats": ["invalid", "mp4", "avi", ""],
    }
