"""
NAS-specific test fixtures.

Provides fixtures for testing NAS operations including
path detection, file operations, and performance testing.

NAS path is parametrized: default root is /Volumes/Public-01; if that does not
exist, falls back to home dir, then tmp. Test subdir is .spatelier/tests/ and
is created if missing.
"""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import pytest

from core.config import Config
from core.service_factory import ServiceFactory

# Default NAS root; if it doesn't exist, we fall back to home or tmp
NAS_PATH_ROOT_DEFAULT = Path("/Volumes/Public-01")


def _candidate_roots() -> list[Path]:
    """Ordered list of candidate roots: default NAS, then home, then tmp."""
    return [
        NAS_PATH_ROOT_DEFAULT,
        Path.home(),
        Path(tempfile.gettempdir()),
    ]


def get_nas_path_root() -> Path:
    """Return NAS/test root: default /Volumes/Public-01 if it exists, else home, else tmp."""
    for root in _candidate_roots():
        if root.exists():
            return root
    return Path(tempfile.gettempdir())


def get_nas_tests_path() -> Path:
    """Return {nas_path_root}/.spatelier/tests/, creating it if missing. Uses first root where we can create the dir and a subdir (probe)."""
    subdir = Path(".spatelier") / "tests"
    for root in _candidate_roots():
        if not root.exists():
            continue
        path = root / subdir
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Verify we can create a subdir (e.g. NAS may exist but be read-only for new dirs)
            probe = path / ".probe_writable"
            probe.mkdir(parents=False, exist_ok=False)
            probe.rmdir()
            return path
        except (OSError, PermissionError):
            continue
    # Last resort: tmp is always writable
    fallback = Path(tempfile.gettempdir()) / subdir
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


@pytest.fixture
def nas_test_path() -> Path:
    """Get the NAS test path (parametrized root + .spatelier/tests/)."""
    return get_nas_tests_path()


@pytest.fixture
def nas_available() -> bool:
    """True when the test path is under the default NAS root (we are actually using NAS)."""
    try:
        return get_nas_tests_path().resolve().is_relative_to(
            NAS_PATH_ROOT_DEFAULT.resolve()
        )
    except ValueError:
        return False


@pytest.fixture
def nas_test_directory(nas_test_path: Path) -> Generator[Path, None, None]:
    """Create a temporary test directory under nas_test_path (NAS or fallback)."""
    test_dir = nas_test_path / f"test_{int(time.time())}_{id(nas_test_path)}"
    test_dir.mkdir(parents=True, exist_ok=True)

    yield test_dir

    try:
        shutil.rmtree(test_dir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def nas_config(nas_test_path: Path) -> Config:
    """Create configuration pointing to NAS."""
    config = Config()
    config.video.output_dir = nas_test_path / "videos"
    config.audio.output_dir = nas_test_path / "audio"
    # Note: Database configuration is handled separately in the application
    return config


@pytest.fixture
def nas_downloader(nas_config: Config) -> ServiceFactory:
    """Create ServiceFactory configured for NAS testing."""
    return ServiceFactory(nas_config, verbose=False)


@pytest.fixture
def nas_file_scenarios():
    """Various NAS file operation scenarios."""
    return {
        "small_file": {
            "size": 1024,  # 1KB
            "content": "x" * 1024,
            "expected_time": 0.1,
        },
        "medium_file": {
            "size": 1024 * 1024,  # 1MB
            "content": "x" * (1024 * 1024),
            "expected_time": 1.0,
        },
        "large_file": {
            "size": 10 * 1024 * 1024,  # 10MB
            "content": "x" * (10 * 1024 * 1024),
            "expected_time": 5.0,
        },
        "video_file": {
            "size": 50 * 1024 * 1024,  # 50MB
            "content": b"\x00" * (50 * 1024 * 1024),
            "expected_time": 10.0,
        },
    }


@pytest.fixture
def nas_path_scenarios(nas_test_path: Path):
    """Various NAS path scenarios for testing (based on parametrized nas_test_path)."""
    base = str(nas_test_path)
    return {
        "root_path": base,
        "nested_path": f"{base}/videos/2024",
        "deep_path": f"{base}/audio/music/artist/album",
        "special_chars": f"{base}/special chars & symbols",
        "unicode_path": f"{base}/测试/视频",
    }


@pytest.fixture
def nas_permission_scenarios():
    """Various NAS permission scenarios."""
    return {
        "read_write": {"can_read": True, "can_write": True, "can_execute": True},
        "read_only": {"can_read": True, "can_write": False, "can_execute": True},
        "no_access": {"can_read": False, "can_write": False, "can_execute": False},
    }


@pytest.fixture
def nas_network_scenarios():
    """Various NAS network scenarios."""
    return {
        "fast_connection": {
            "latency_ms": 1,
            "bandwidth_mbps": 1000,
            "reliability": 0.99,
        },
        "slow_connection": {
            "latency_ms": 100,
            "bandwidth_mbps": 10,
            "reliability": 0.95,
        },
        "unreliable_connection": {
            "latency_ms": 50,
            "bandwidth_mbps": 100,
            "reliability": 0.80,
        },
    }


@pytest.fixture
def nas_concurrent_scenarios():
    """Various concurrent operation scenarios on NAS."""
    return {
        "single_operation": {"concurrent_ops": 1, "expected_success_rate": 1.0},
        "low_concurrency": {"concurrent_ops": 3, "expected_success_rate": 0.95},
        "medium_concurrency": {"concurrent_ops": 10, "expected_success_rate": 0.90},
        "high_concurrency": {"concurrent_ops": 50, "expected_success_rate": 0.80},
    }


@pytest.fixture
def nas_error_scenarios():
    """Various NAS error scenarios."""
    return {
        "network_timeout": {
            "error_type": "TimeoutError",
            "message": "Network timeout",
            "recoverable": True,
        },
        "permission_denied": {
            "error_type": "PermissionError",
            "message": "Permission denied",
            "recoverable": False,
        },
        "disk_full": {
            "error_type": "OSError",
            "message": "No space left on device",
            "recoverable": False,
        },
        "network_unreachable": {
            "error_type": "ConnectionError",
            "message": "Network unreachable",
            "recoverable": True,
        },
    }


@pytest.fixture
def nas_cleanup_scenarios():
    """Various NAS cleanup scenarios."""
    return {
        "single_file": {"files": ["test1.mp4"], "directories": []},
        "multiple_files": {
            "files": ["test1.mp4", "test2.mp4", "test3.srt"],
            "directories": [],
        },
        "nested_structure": {
            "files": ["video1.mp4", "video2.mp4"],
            "directories": ["subtitles", "thumbnails"],
        },
        "deep_nested": {
            "files": ["video.mp4"],
            "directories": ["2024/01", "2024/02", "subtitles/en", "subtitles/es"],
        },
    }


@pytest.fixture
def nas_performance_benchmarks():
    """NAS performance benchmarks for testing."""
    return {
        "file_operations": {
            "create_file_1kb": {"max_time": 0.1, "max_memory": 1024},
            "create_file_1mb": {"max_time": 1.0, "max_memory": 1024 * 1024},
            "create_file_10mb": {"max_time": 5.0, "max_memory": 10 * 1024 * 1024},
            "read_file_1mb": {"max_time": 0.5, "max_memory": 1024 * 1024},
            "delete_file_1mb": {"max_time": 0.2, "max_memory": 1024},
        },
        "directory_operations": {
            "create_directory": {"max_time": 0.1, "max_memory": 1024},
            "list_directory": {"max_time": 0.5, "max_memory": 1024 * 1024},
            "delete_directory": {"max_time": 1.0, "max_memory": 1024},
        },
        "move_operations": {
            "move_file_1mb": {"max_time": 2.0, "max_memory": 1024 * 1024},
            "move_directory": {"max_time": 5.0, "max_memory": 10 * 1024 * 1024},
        },
    }


@pytest.fixture
def nas_test_data():
    """Test data for NAS operations."""
    return {
        "video_files": [
            {
                "name": "test_video_1.mp4",
                "size": 1024 * 1024,
                "content": b"\x00" * (1024 * 1024),
            },
            {
                "name": "test_video_2.mp4",
                "size": 5 * 1024 * 1024,
                "content": b"\x00" * (5 * 1024 * 1024),
            },
            {
                "name": "test_video_3.mp4",
                "size": 10 * 1024 * 1024,
                "content": b"\x00" * (10 * 1024 * 1024),
            },
        ],
        "audio_files": [
            {
                "name": "test_audio_1.mp3",
                "size": 512 * 1024,
                "content": b"\x00" * (512 * 1024),
            },
            {
                "name": "test_audio_2.wav",
                "size": 2 * 1024 * 1024,
                "content": b"\x00" * (2 * 1024 * 1024),
            },
        ],
        "subtitle_files": [
            {
                "name": "test_subtitles.srt",
                "size": 1024,
                "content": "1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n",
            },
            {
                "name": "test_subtitles.vtt",
                "size": 1024,
                "content": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nTest subtitle\n",
            },
        ],
    }


@pytest.fixture
def nas_monitoring_metrics():
    """NAS monitoring metrics for testing."""
    return {
        "file_operations": {
            "files_created": 0,
            "files_deleted": 0,
            "files_moved": 0,
            "files_copied": 0,
        },
        "directory_operations": {
            "directories_created": 0,
            "directories_deleted": 0,
            "directories_moved": 0,
        },
        "performance_metrics": {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_operation_time": 0.0,
            "total_data_transferred": 0,
        },
    }
