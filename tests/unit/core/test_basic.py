"""
Basic tests for Spatelier.

These tests verify that the basic structure and imports work correctly.
"""

from pathlib import Path

import pytest

from spatelier.core.config import AudioConfig, Config, VideoConfig
from spatelier.core.logger import get_logger


def test_config_creation():
    """Test that configuration can be created."""
    config = Config()
    assert isinstance(config.video, VideoConfig)
    assert isinstance(config.audio, AudioConfig)
    assert isinstance(config.log_level, str)


def test_config_defaults():
    """Test that configuration has sensible defaults."""
    config = Config()

    # Video config defaults
    assert config.video.default_format == "mp4"
    assert config.video.quality == "best"

    # Audio config defaults
    assert config.audio.default_format == "mp3"
    assert config.audio.bitrate == 320

    # Logging config defaults
    assert config.log_level == "INFO"


def test_logger_creation():
    """Test that logger can be created."""
    logger = get_logger("test", verbose=False)
    assert logger is not None


def test_project_structure():
    """Test that the project structure is correct (single package under spatelier/)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    # Single installable package
    assert (root / "spatelier/__init__.py").exists()
    assert (root / "spatelier/cli/__init__.py").exists()
    assert (root / "spatelier/core/__init__.py").exists()
    assert (root / "spatelier/modules/__init__.py").exists()
    assert (root / "spatelier/utils/__init__.py").exists()

    assert (root / "spatelier/cli/app.py").exists()
    assert (root / "spatelier/cli/video.py").exists()
    assert (root / "spatelier/cli/audio.py").exists()
    assert (root / "spatelier/cli/cli_utils.py").exists()

    assert (root / "spatelier/core/config.py").exists()
    assert (root / "spatelier/core/logger.py").exists()
    assert (root / "spatelier/core/base.py").exists()

    assert (root / "spatelier/utils/helpers.py").exists()


def test_imports():
    """Test that all modules can be imported."""
    from spatelier.cli import app, audio, cli_utils, video
    from spatelier.core import base, config, logger
    from spatelier.core.config import Config
    from spatelier.core.logger import get_logger
    from spatelier.modules.video import VideoConverter, VideoDownloadService
    from spatelier.utils import helpers


def test_config_validation():
    """Test that configuration validation works."""
    config = Config()

    # Test that temp directories are created (they should be created by the validator)
    assert config.video.temp_dir.exists()
    assert config.audio.temp_dir.exists()

    # Test that output directories are None by default (they're optional)
    assert config.video.output_dir is None
    assert config.audio.output_dir is None


def test_helpers():
    """Test utility helper functions."""
    from spatelier.utils.helpers import format_file_size, safe_filename

    # Test safe filename
    assert safe_filename("test<file>.mp4") == "test_file_.mp4"
    assert safe_filename("normal_file.mp4") == "normal_file.mp4"

    # Test file size formatting
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(0) == "0 B"
