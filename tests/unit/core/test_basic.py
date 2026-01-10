"""
Basic tests for Spatelier.

These tests verify that the basic structure and imports work correctly.
"""

import pytest
from pathlib import Path

from core.config import Config
from core.logger import get_logger
from core.config import VideoConfig, AudioConfig


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
    """Test that the project structure is correct."""
    # Check that main modules exist
    assert Path("__init__.py").exists()
    assert Path("cli/__init__.py").exists()
    assert Path("core/__init__.py").exists()
    assert Path("modules/__init__.py").exists()
    assert Path("utils/__init__.py").exists()
    
    # Check that CLI modules exist
    assert Path("cli/app.py").exists()
    assert Path("cli/video.py").exists()
    assert Path("cli/audio.py").exists()
    assert Path("cli/cli_utils.py").exists()
    
    # Check that core modules exist
    assert Path("core/config.py").exists()
    assert Path("core/logger.py").exists()
    assert Path("core/base.py").exists()
    
    # Check that utility modules exist
    assert Path("utils/helpers.py").exists()


def test_imports():
    """Test that all modules can be imported."""
    # Test main imports
    from core.config import Config
    from core.logger import get_logger
    
    # Test CLI imports
    from cli import app, video, audio, cli_utils
    
    # Test core imports
    from core import config, logger, base
    
    # Test module imports
    from modules.video import VideoDownloadService, VideoConverter
    
    # Test utility imports
    from utils import helpers


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
    from utils.helpers import safe_filename, format_file_size
    
    # Test safe filename
    assert safe_filename("test<file>.mp4") == "test_file_.mp4"
    assert safe_filename("normal_file.mp4") == "normal_file.mp4"
    
    # Test file size formatting
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(0) == "0 B"
