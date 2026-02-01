"""
Pytest configuration and global fixtures.

This module provides global test configuration and fixtures
that are available to all test modules.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test fixtures (lazy import to handle missing optional dependencies)
try:
    from tests.fixtures import *
except ImportError as e:
    # If fixtures can't be imported due to missing dependencies,
    # that's OK - individual test files can define their own fixtures
    import warnings

    warnings.warn(
        f"Could not import all test fixtures: {e}. Some tests may need additional dependencies."
    )


@pytest.fixture(scope="session")
def test_session_id():
    """Generate unique session ID for test isolation."""
    import time

    return f"test_session_{int(time.time())}"


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment."""
    # Set test environment variables
    os.environ["SPATELIER_TEST_MODE"] = "true"
    os.environ["SPATELIER_DEBUG"] = "true"
    os.environ["SPATELIER_VERBOSE"] = "true"

    yield

    # Cleanup environment variables
    os.environ.pop("SPATELIER_TEST_MODE", None)
    os.environ.pop("SPATELIER_DEBUG", None)
    os.environ.pop("SPATELIER_VERBOSE", None)


@pytest.fixture(scope="function")
def test_cleanup():
    """Clean up after each test."""
    yield

    # Clean up any remaining temp files
    temp_dirs = [
        Path(".temp"),
        Path("/tmp/spatelier_test"),
        Path(tempfile.gettempdir()) / "spatelier_test",
    ]

    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def isolated_test_env():
    """Create isolated test environment."""
    # Create isolated temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="spatelier_test_"))

    # Set up isolated environment
    original_cwd = Path.cwd()
    os.chdir(temp_dir)

    yield temp_dir

    # Restore original environment
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_external_services():
    """Mock external services for testing."""
    with pytest.MonkeyPatch() as m:
        # Mock yt-dlp
        m.setattr("yt_dlp.YoutubeDL", Mock())

        # Mock ffmpeg
        m.setattr("subprocess.run", Mock())

        # Mock Whisper
        m.setattr("faster_whisper.WhisperModel", Mock())

        # Mock MongoDB
        m.setattr("pymongo.MongoClient", Mock())

        yield m


@pytest.fixture(scope="function")
def test_logging():
    """Set up test logging."""
    import logging

    # Create test logger
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    yield logger

    # Cleanup
    logger.removeHandler(handler)


@pytest.fixture(scope="function")
def test_metrics():
    """Collect test metrics."""
    metrics = {
        "start_time": None,
        "end_time": None,
        "duration": None,
        "operations": [],
        "errors": [],
        "warnings": [],
    }

    import time

    metrics["start_time"] = time.time()

    yield metrics

    metrics["end_time"] = time.time()
    metrics["duration"] = metrics["end_time"] - metrics["start_time"]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "nas: mark test as NAS test")
    config.addinivalue_line("markers", "slow: mark test as slow test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers based on test location
    for item in items:
        # Mark tests in unit/ directory as unit tests
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark tests in integration/ directory as integration tests
        if "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests in performance/ directory as performance tests
        if "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Mark NAS tests
        if "nas" in str(item.fspath).lower():
            item.add_marker(pytest.mark.nas)

        # Mark slow tests
        if (
            "slow" in str(item.fspath).lower()
            or "performance" in str(item.fspath).lower()
        ):
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """Set up test run."""
    # Skip NAS tests only when no writable root is available (same logic as nas_fixtures: NAS, home, or tmp)
    if item.get_closest_marker("nas"):
        from tests.fixtures.nas_fixtures import get_nas_path_root
        root = get_nas_path_root()
        if not root.exists():
            pytest.skip("NAS not available for testing")


def pytest_runtest_teardown(item):
    """Tear down test run."""
    # Clean up any remaining temp files
    temp_dirs = [
        Path(".temp"),
        Path("/tmp/spatelier_test"),
        Path(tempfile.gettempdir()) / "spatelier_test",
    ]

    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


# Test discovery configuration
def pytest_ignore_collect(collection_path, config):
    """Ignore certain files during test collection."""
    # Ignore __pycache__ directories
    if "__pycache__" in str(collection_path):
        return True

    # Ignore .pyc files
    if str(collection_path).endswith(".pyc"):
        return True

    return False
