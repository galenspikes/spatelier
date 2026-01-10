"""
Test helper functions and utilities.

Provides common helper functions used across test modules
for setup, teardown, and test data management.
"""

import os
import tempfile
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest


def create_temp_file(
    content: str = "test content",
    suffix: str = ".txt",
    directory: Optional[Path] = None
) -> Path:
    """Create a temporary file with specified content."""
    if directory is None:
        directory = Path(tempfile.gettempdir())
    
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix=suffix,
        dir=directory,
        delete=False
    )
    temp_file.write(content)
    temp_file.close()
    
    return Path(temp_file.name)


def create_temp_directory(prefix: str = "test_") -> Path:
    """Create a temporary directory."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def cleanup_path(path: Union[str, Path]) -> None:
    """Safely clean up a file or directory."""
    path = Path(path)
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except (OSError, PermissionError):
        pass  # Ignore cleanup errors


@contextmanager
def temp_environment(**env_vars):
    """Temporarily set environment variables."""
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = str(value)
    
    try:
        yield
    finally:
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


@contextmanager
def temp_working_directory(path: Path):
    """Temporarily change working directory."""
    original_cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_cwd)


def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met"
) -> bool:
    """Wait for a condition to be true within timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    raise AssertionError(f"{message} (timeout: {timeout}s)")


def assert_file_exists(path: Union[str, Path], message: str = None) -> None:
    """Assert that a file exists."""
    path = Path(path)
    if not path.exists():
        msg = message or f"File does not exist: {path}"
        raise AssertionError(msg)


def assert_file_not_exists(path: Union[str, Path], message: str = None) -> None:
    """Assert that a file does not exist."""
    path = Path(path)
    if path.exists():
        msg = message or f"File should not exist: {path}"
        raise AssertionError(msg)


def assert_directory_exists(path: Union[str, Path], message: str = None) -> None:
    """Assert that a directory exists."""
    path = Path(path)
    if not path.is_dir():
        msg = message or f"Directory does not exist: {path}"
        raise AssertionError(msg)


def assert_file_size(path: Union[str, Path], expected_size: int, tolerance: int = 0) -> None:
    """Assert that a file has the expected size within tolerance."""
    path = Path(path)
    if not path.exists():
        raise AssertionError(f"File does not exist: {path}")
    
    actual_size = path.stat().st_size
    if abs(actual_size - expected_size) > tolerance:
        raise AssertionError(
            f"File size mismatch: expected {expected_size}±{tolerance}, got {actual_size}"
        )


def assert_file_content(path: Union[str, Path], expected_content: str) -> None:
    """Assert that a file contains expected content."""
    path = Path(path)
    if not path.exists():
        raise AssertionError(f"File does not exist: {path}")
    
    actual_content = path.read_text()
    if actual_content != expected_content:
        raise AssertionError(
            f"File content mismatch:\nExpected: {expected_content}\nActual: {actual_content}"
        )


def create_mock_file(
    path: Union[str, Path],
    size: int = 1024,
    content: str = None
) -> Path:
    """Create a mock file with specified size and content."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if content is not None:
        path.write_text(content)
    else:
        # Create file with specified size
        with open(path, 'wb') as f:
            f.write(b'0' * size)
    
    return path


def create_mock_directory_structure(
    base_path: Union[str, Path],
    structure: Dict[str, Any]
) -> Path:
    """Create a mock directory structure."""
    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    for name, content in structure.items():
        item_path = base_path / name
        if isinstance(content, dict):
            # It's a directory
            item_path.mkdir(exist_ok=True)
            create_mock_directory_structure(item_path, content)
        else:
            # It's a file
            item_path.write_text(str(content))
    
    return base_path


def mock_database_operations():
    """Mock database operations for testing."""
    return patch.multiple(
        'database.connection.DatabaseManager',
        connect_sqlite=Mock(),
        connect_mongodb=Mock(),
        get_sqlite_session=Mock(),
        get_mongodb_client=Mock(),
        close_connections=Mock()
    )


def mock_file_operations():
    """Mock file operations for testing."""
    return patch.multiple(
        'pathlib.Path',
        exists=Mock(return_value=True),
        is_file=Mock(return_value=True),
        is_dir=Mock(return_value=False),
        stat=Mock(return_value=Mock(st_size=1024, st_mtime=time.time())),
        unlink=Mock(),
        mkdir=Mock()
    )


def mock_network_operations():
    """Mock network operations for testing."""
    return patch.multiple(
        'requests.get',
        return_value=Mock(
            status_code=200,
            json=Mock(return_value={}),
            content=b'test content'
        )
    )


def create_test_config(
    **overrides
) -> Dict[str, Any]:
    """Create a test configuration dictionary."""
    config = {
        "debug": True,
        "verbose": True,
        "database": {
            "sqlite_path": "/tmp/test.db",
            "mongodb_database": "test_db"
        },
        "video": {
            "output_dir": "/tmp/test_videos",
            "transcribe": True,
            "transcription_model": "base"
        },
        "audio": {
            "output_dir": "/tmp/test_audio",
            "format": "mp3",
            "quality": "high"
        },
        "logging": {
            "level": "DEBUG"
        }
    }
    
    # Apply overrides
    for key, value in overrides.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    return config


def assert_logs_contain(logs: List[str], expected_messages: List[str]) -> None:
    """Assert that logs contain expected messages."""
    for expected in expected_messages:
        if not any(expected in log for log in logs):
            raise AssertionError(f"Expected log message not found: {expected}")


def assert_logs_not_contain(logs: List[str], unexpected_messages: List[str]) -> None:
    """Assert that logs do not contain unexpected messages."""
    for unexpected in unexpected_messages:
        if any(unexpected in log for log in logs):
            raise AssertionError(f"Unexpected log message found: {unexpected}")


def create_mock_transcription_data(
    text: str = "Test transcription",
    duration: float = 10.0,
    language: str = "en"
) -> Dict[str, Any]:
    """Create mock transcription data for testing."""
    return {
        "language": language,
        "language_name": "English",
        "duration": duration,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": duration,
                "text": text,
                "words": [
                    {"word": word, "start": i * 0.5, "end": (i + 1) * 0.5}
                    for i, word in enumerate(text.split())
                ]
            }
        ],
        "text": text,
        "processing_time": 5.0,
        "model_used": "whisper-base"
    }


def create_mock_video_info(
    video_id: str = "test123",
    title: str = "Test Video",
    duration: int = 120
) -> Dict[str, Any]:
    """Create mock video information for testing."""
    return {
        "id": video_id,
        "title": title,
        "description": "Test video description",
        "uploader": "Test Uploader",
        "upload_date": "20240101",
        "duration": duration,
        "thumbnail": f"https://example.com/thumb_{video_id}.jpg",
        "extractor_key": "youtube",
        "webpage_url": f"https://youtube.com/watch?v={video_id}"
    }
