"""
Tests for core functionality.

This module tests core components like configuration, logging, and base classes.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.base import BaseConverter, BaseDownloader, BaseProcessor, ProcessingResult
from core.config import (
    AudioConfig,
    Config,
    DatabaseConfig,
    TranscriptionConfig,
    VideoConfig,
)
from core.logger import get_logger, setup_logging
from utils.helpers import (
    find_files,
    format_file_size,
    get_file_hash,
    get_file_size,
    get_file_type,
    is_audio_file,
    is_video_file,
    safe_filename,
)


def test_config_initialization():
    """Test Config initialization."""
    config = Config()

    assert isinstance(config.video, VideoConfig)
    assert isinstance(config.audio, AudioConfig)
    assert isinstance(config.database, DatabaseConfig)
    assert isinstance(config.transcription, TranscriptionConfig)
    assert isinstance(config.log_level, str)
    assert isinstance(config.video_extensions, list)
    assert config.verbose == False
    assert config.debug == False


def test_video_config_defaults():
    """Test VideoConfig defaults."""
    config = VideoConfig()

    assert config.default_format == "mp4"
    assert config.quality == "best"
    assert config.output_dir is None  # Should not create default directory
    assert config.temp_dir.name == "video"


def test_audio_config_defaults():
    """Test AudioConfig defaults."""
    config = AudioConfig()

    assert config.default_format == "mp3"
    assert config.bitrate == 320
    assert config.output_dir is None  # output_dir is None by default
    assert config.temp_dir.name == "audio"


def test_database_config_defaults():
    """Test DatabaseConfig defaults."""
    config = DatabaseConfig()

    assert "spatelier.db" in str(config.sqlite_path)
    assert config.mongodb_url == "mongodb://localhost:27017"
    assert config.mongodb_database == "spatelier"
    assert config.retention_days == 365
    assert config.enable_analytics == True


def test_transcription_config_defaults():
    """Test TranscriptionConfig defaults."""
    config = TranscriptionConfig()

    assert config.default_model == "small"
    assert config.default_language == "en"
    assert config.device == "auto"
    assert config.compute_type == "auto"


def test_config_flattened_settings():
    """Test flattened config settings."""
    config = Config()

    assert config.log_level == "INFO"
    assert ".mp4" in config.video_extensions
    assert ".mp3" in config.audio_extensions
    assert config.max_filename_length == 255
    assert config.fallback_max_files == 10
    assert config.fallback_timeout_seconds == 30


def test_config_load_from_file():
    """Test loading configuration from file."""
    import yaml

    # Create temporary config file
    config_data = {
        "video": {
            "default_format": "mkv",
            "quality": "1080p",  # Use valid quality value
        },
        "audio": {
            "default_format": "flac",
            "bitrate": 320,  # Use valid bitrate value (max 320)
        },
        "verbose": True,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name

    try:
        config = Config.load_from_file(config_file)

        assert config.video.default_format == "mkv"
        assert config.video.quality == "1080p"
        assert config.audio.default_format == "flac"
        assert config.audio.bitrate == 320
        assert config.verbose == True
    finally:
        Path(config_file).unlink()


def test_config_load_from_env():
    """Test loading configuration from environment variables."""
    with patch.dict(
        "os.environ", {"SPATELIER_VERBOSE": "true", "SPATELIER_DEBUG": "true"}
    ):
        config = Config.load_from_env()

        assert config.verbose == True
        assert config.debug == True


def test_config_save_to_file():
    """Test saving configuration to file."""
    config = Config()
    config.video.default_format = "mkv"
    config.verbose = True

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        config_file = f.name

    try:
        config.save_to_file(config_file)

        # Load and verify
        loaded_config = Config.load_from_file(config_file)
        assert loaded_config.video.default_format == "mkv"
        assert loaded_config.verbose == True
    finally:
        Path(config_file).unlink()


def test_config_get_default_config_path():
    """Test getting default configuration path."""
    config = Config()
    default_path = config.get_default_config_path()

    assert default_path.name == "config.yaml"
    assert "spatelier" in str(default_path)


def test_config_ensure_default_config():
    """Test ensuring default configuration exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.object(Config, "get_default_config_path") as mock_path:
            mock_path.return_value = Path(temp_dir) / "config.yaml"

            config = Config()
            config.ensure_default_config()

            assert Path(temp_dir) / "config.yaml" in mock_path.return_value.parent.glob(
                "*.yaml"
            )


def test_logger_creation():
    """Test logger creation."""
    logger = get_logger("test_logger", verbose=False)
    assert logger is not None
    assert logger.name == "test_logger"


def test_logger_creation_verbose():
    """Test logger creation with verbose mode."""
    logger = get_logger("test_logger", verbose=True)
    assert logger is not None


def test_setup_logging():
    """Test setting up global logging."""
    setup_logging(verbose=True, level="DEBUG")
    # This should not raise an exception


def test_processing_result_creation():
    """Test ProcessingResult creation."""
    result = ProcessingResult(
        success=True,
        message="Test successful",
        output_path=Path("/test/output.mp4"),
        metadata={"file_size": 1000000},
        errors=[],
    )

    assert result.success == True
    assert result.message == "Test successful"
    assert result.output_path == Path("/test/output.mp4")
    assert result.metadata["file_size"] == 1000000
    assert result.errors == []


def test_processing_result_factory_methods():
    """Test ProcessingResult factory methods."""
    # Test success_result
    success_result = ProcessingResult.success_result(
        message="Operation successful",
        output_path="/test/output.mp4",
        metadata={"file_size": 1000000},
        warnings=["Minor warning"],
    )

    assert success_result.success == True
    assert success_result.message == "Operation successful"
    assert success_result.output_path == Path("/test/output.mp4")
    assert success_result.metadata["file_size"] == 1000000
    assert success_result.warnings == ["Minor warning"]

    # Test error_result
    error_result = ProcessingResult.error_result(
        message="Operation failed",
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"],
    )

    assert error_result.success == False
    assert error_result.message == "Operation failed"
    assert error_result.errors == ["Error 1", "Error 2"]
    assert error_result.warnings == ["Warning 1"]

    # Test warning_result
    warning_result = ProcessingResult.warning_result(
        message="Operation completed with warnings",
        warnings=["Warning 1", "Warning 2"],
        output_path="/test/output.mp4",
    )

    assert warning_result.success == True
    assert warning_result.message == "Operation completed with warnings"
    assert warning_result.warnings == ["Warning 1", "Warning 2"]
    assert warning_result.output_path == Path("/test/output.mp4")


def test_processing_result_methods():
    """Test ProcessingResult methods."""
    result = ProcessingResult(success=True, message="Test")

    # Test add_error
    result.add_error("Test error")
    assert result.has_errors() == True
    assert result.is_successful() == False
    assert result.success == False

    # Test add_warning
    result.add_warning("Test warning")
    assert result.has_warnings() == True

    # Test add_metadata
    result.add_metadata("test_key", "test_value")
    assert result.metadata["test_key"] == "test_value"

    # Test get_summary
    summary = result.get_summary()
    assert "Success: False" in summary
    assert "Errors: 1" in summary
    assert "Warnings: 1" in summary


def test_base_processor_initialization():
    """Test BaseProcessor initialization."""
    config = Config()

    class TestProcessor(BaseProcessor):
        def process(self, input_path, **kwargs):
            return ProcessingResult(success=True, message="Test")

    processor = TestProcessor(config, verbose=False)

    assert processor.config == config
    assert processor.verbose == False
    assert processor.logger is not None


def test_base_processor_validate_input():
    """Test BaseProcessor input validation."""
    config = Config()

    class TestProcessor(BaseProcessor):
        def process(self, input_path, **kwargs):
            return ProcessingResult(success=True, message="Test")

    processor = TestProcessor(config, verbose=False)

    # Test with non-existent file
    assert processor.validate_input("/nonexistent/file.mp4") == False

    # Test with existing file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_file = f.name

    try:
        assert processor.validate_input(temp_file) == True
    finally:
        Path(temp_file).unlink()


def test_base_processor_ensure_output_dir():
    """Test BaseProcessor output directory creation."""
    config = Config()

    class TestProcessor(BaseProcessor):
        def process(self, input_path, **kwargs):
            return ProcessingResult(success=True, message="Test")

    processor = TestProcessor(config, verbose=False)

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "subdir" / "output.mp4"
        assert processor.ensure_output_dir(output_path) == True
        assert output_path.parent.exists()


def test_base_downloader_initialization():
    """Test BaseDownloader initialization."""
    config = Config()

    class TestDownloader(BaseDownloader):
        def download(self, url, output_path=None, **kwargs):
            return ProcessingResult(success=True, message="Test")

    downloader = TestDownloader(config, verbose=False)

    assert downloader.supported_sites == []
    assert downloader.is_supported("https://example.com") == False


def test_base_converter_initialization():
    """Test BaseConverter initialization."""
    config = Config()

    class TestConverter(BaseConverter):
        def convert(self, input_path, output_path, **kwargs):
            return ProcessingResult(success=True, message="Test")

    converter = TestConverter(config, verbose=False)

    assert converter.supported_input_formats == []
    assert converter.supported_output_formats == []
    assert converter.is_supported_format("test.mp4", is_input=True) == False


def test_helpers_get_file_hash():
    """Test file hash calculation."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Hello, World!")
        temp_file = f.name

    try:
        hash_value = get_file_hash(temp_file)
        assert len(hash_value) == 64  # SHA256 hash length
        assert hash_value.isalnum()
    finally:
        Path(temp_file).unlink()


def test_helpers_get_file_size():
    """Test file size calculation."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Hello, World!")
        temp_file = f.name

    try:
        size = get_file_size(temp_file)
        assert size == 13  # Length of "Hello, World!"
    finally:
        Path(temp_file).unlink()


def test_helpers_format_file_size():
    """Test file size formatting."""
    assert format_file_size(0) == "0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(1073741824) == "1.0 GB"


def test_helpers_get_file_type():
    """Test file type detection."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        temp_file = f.name

    try:
        mime_type = get_file_type(temp_file)
        assert mime_type.startswith("video/")
    finally:
        Path(temp_file).unlink()


def test_helpers_is_video_file():
    """Test video file detection."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        temp_file = f.name

    try:
        assert is_video_file(temp_file) == True
    finally:
        Path(temp_file).unlink()


def test_helpers_is_audio_file():
    """Test audio file detection."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_file = f.name

    try:
        assert is_audio_file(temp_file) == True
    finally:
        Path(temp_file).unlink()


def test_helpers_find_files():
    """Test file finding functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "test1.txt").write_text("content1")
        (temp_path / "test2.txt").write_text("content2")
        (temp_path / "test3.log").write_text("log content")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "test4.txt").write_text("content4")

        # Find all txt files
        txt_files = find_files(temp_path, "*.txt", recursive=True)
        assert len(txt_files) == 3

        # Find txt files in root only
        txt_files_root = find_files(temp_path, "*.txt", recursive=False)
        assert len(txt_files_root) == 2

        # Find files by type
        txt_files_by_type = find_files(temp_path, "*", file_types=["txt"])
        assert len(txt_files_by_type) == 3


def test_helpers_safe_filename():
    """Test safe filename creation."""
    assert safe_filename("normal_file.mp4") == "normal_file.mp4"
    assert safe_filename("file<with>invalid:chars.mp4") == "file_with_invalid_chars.mp4"
    assert safe_filename("  file with spaces  .mp4") == "file with spaces.mp4"
    assert safe_filename("very_long_filename_" + "x" * 300 + ".mp4").endswith(".mp4")
