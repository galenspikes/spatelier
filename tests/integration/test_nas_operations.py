"""
Integration tests for NAS operations.

Tests actual NAS functionality using the real NAS path
/Volumes/Public-01/spatelier/tests for comprehensive testing.
"""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock, patch

import pytest

from core.config import Config

# Removed imports for deleted modular architecture
from database.connection import DatabaseManager
from database.repository import (
    AnalyticsRepository,
    MediaFileRepository,
    ProcessingJobRepository,
)
from modules.video.services.download_service import VideoDownloadService


class TestNASIntegration:
    """Integration tests for NAS operations."""

    @pytest.fixture
    def nas_test_path(self) -> Path:
        """Get the NAS test path."""
        return Path("/Volumes/Public-01/spatelier/tests")

    @pytest.fixture
    def nas_config(self, nas_test_path: Path) -> Config:
        """Create configuration pointing to NAS."""
        config = Config()
        config.video.output_dir = nas_test_path / "videos"
        config.audio.output_dir = nas_test_path / "audio"
        config.database.sqlite_path = str(nas_test_path / "test.db")
        config.mongodb_database = "test_spatelier_nas"
        return config

    @pytest.fixture
    def nas_test_setup(self, nas_test_path: Path) -> Generator[Path, None, None]:
        """Set up NAS test environment."""
        # Create test directory structure on NAS
        test_dir = nas_test_path / f"test_{int(time.time())}"
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (test_dir / "videos").mkdir(exist_ok=True)
        (test_dir / "audio").mkdir(exist_ok=True)
        (test_dir / "temp").mkdir(exist_ok=True)

        yield test_dir

        # Cleanup
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors on NAS

    def test_nas_path_detection(self, nas_test_path: Path):
        """Test that NAS path is correctly detected."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Test the actual NAS path
        assert downloader._is_nas_path(nas_test_path) == True
        assert downloader._is_nas_path(nas_test_path / "videos") == True
        assert downloader._is_nas_path(nas_test_path / "audio") == True

        # Test non-NAS paths
        assert downloader._is_nas_path(Path("/tmp")) == False
        assert downloader._is_nas_path(Path("/Users/test")) == False

    def test_nas_temp_directory_creation(self, nas_test_path: Path):
        """Test temp directory creation for NAS operations."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        job_id = 12345
        temp_dir = downloader._get_temp_processing_dir(job_id)

        # Should create local temp directory
        assert temp_dir.exists()
        assert temp_dir.name == str(job_id)
        assert temp_dir.parent.name == ".temp"

        # Cleanup
        shutil.rmtree(temp_dir.parent, ignore_errors=True)

    def test_nas_file_move_operation(self, nas_test_path: Path):
        """Test moving files from temp to NAS."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(b"test video content")
            temp_file_path = Path(temp_file.name)

        try:
            # Test move operation
            nas_dest = nas_test_path / "test_video.mp4"
            success = downloader._move_file_to_final_destination(
                temp_file_path, nas_dest
            )

            assert success == True
            assert nas_dest.exists()
            assert not temp_file_path.exists()

            # Cleanup
            nas_dest.unlink(missing_ok=True)

        finally:
            # Cleanup temp file if it still exists
            temp_file_path.unlink(missing_ok=True)

    def test_nas_playlist_directory_move(self, nas_test_path: Path):
        """Test moving entire playlist directory to NAS."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create temp playlist directory
        temp_dir = Path(tempfile.mkdtemp())
        playlist_dir = temp_dir / "Test Playlist [playlist123]"
        playlist_dir.mkdir(exist_ok=True)

        # Add some test files
        (playlist_dir / "video1.mp4").write_text("test video 1")
        (playlist_dir / "video2.mp4").write_text("test video 2")

        try:
            # Test move operation
            nas_dest = nas_test_path / "Test Playlist [playlist123]"
            success = downloader._move_playlist_to_final_destination(
                playlist_dir, nas_dest
            )

            assert success == True
            assert nas_dest.exists()
            assert (nas_dest / "video1.mp4").exists()
            assert (nas_dest / "video2.mp4").exists()
            assert not playlist_dir.exists()

            # Cleanup
            shutil.rmtree(nas_dest, ignore_errors=True)

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_nas_cross_device_move_simulation(self, nas_test_path: Path):
        """Test cross-device move simulation (copy + delete)."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(b"test video content for cross-device move")
            temp_file_path = Path(temp_file.name)

        try:
            # Test move operation (should use copy + delete for cross-device)
            nas_dest = nas_test_path / "cross_device_test.mp4"
            success = downloader._move_file_to_final_destination(
                temp_file_path, nas_dest
            )

            assert success == True
            assert nas_dest.exists()
            assert nas_dest.read_bytes() == b"test video content for cross-device move"
            assert not temp_file_path.exists()

            # Cleanup
            nas_dest.unlink(missing_ok=True)

        finally:
            # Cleanup temp file if it still exists
            temp_file_path.unlink(missing_ok=True)

    def test_nas_processing_workflow(self, nas_test_path: Path):
        """Test complete NAS processing workflow."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create temp processing directory
        job_id = 99999
        temp_dir = downloader._get_temp_processing_dir(job_id)

        try:
            # Simulate downloaded file in temp directory
            temp_video = temp_dir / "Test Video [test123].mp4"
            temp_video.write_bytes(b"simulated video content")

            # Test the complete workflow
            final_dest = nas_test_path / "Test Video [test123].mp4"
            success = downloader._move_file_to_final_destination(temp_video, final_dest)

            assert success == True
            assert final_dest.exists()
            assert final_dest.read_bytes() == b"simulated video content"
            assert not temp_video.exists()

            # Cleanup
            final_dest.unlink(missing_ok=True)

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_nas_permissions_and_access(self, nas_test_path: Path):
        """Test NAS permissions and access."""
        # Test that we can read from NAS
        assert nas_test_path.exists()
        assert nas_test_path.is_dir()

        # Test that we can write to NAS
        test_file = nas_test_path / "permission_test.txt"
        test_file.write_text("NAS permission test")

        try:
            assert test_file.exists()
            assert test_file.read_text() == "NAS permission test"

            # Test that we can create directories
            test_dir = nas_test_path / "permission_test_dir"
            test_dir.mkdir(exist_ok=True)
            assert test_dir.exists()
            assert test_dir.is_dir()

        finally:
            # Cleanup
            test_file.unlink(missing_ok=True)
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_nas_large_file_handling(self, nas_test_path: Path):
        """Test handling large files on NAS."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create a larger test file (10MB)
        large_content = b"0" * (10 * 1024 * 1024)  # 10MB

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(large_content)
            temp_file_path = Path(temp_file.name)

        try:
            # Test move operation with large file
            nas_dest = nas_test_path / "large_file_test.mp4"
            success = downloader._move_file_to_final_destination(
                temp_file_path, nas_dest
            )

            assert success == True
            assert nas_dest.exists()
            assert nas_dest.stat().st_size == len(large_content)

            # Cleanup
            nas_dest.unlink(missing_ok=True)

        finally:
            # Cleanup temp file if it still exists
            temp_file_path.unlink(missing_ok=True)

    def test_nas_concurrent_operations(self, nas_test_path: Path):
        """Test concurrent operations on NAS."""
        import threading
        import time

        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        results = []

        def worker(worker_id: int):
            """Worker function for concurrent testing."""
            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f"_{worker_id}.mp4"
                ) as temp_file:
                    temp_file.write(f"worker {worker_id} content".encode())
                    temp_file_path = Path(temp_file.name)

                # Move to NAS
                nas_dest = nas_test_path / f"concurrent_test_{worker_id}.mp4"
                success = downloader._move_file_to_final_destination(
                    temp_file_path, nas_dest
                )

                results.append((worker_id, success, nas_dest))

            except Exception as e:
                results.append((worker_id, False, str(e)))

        # Start multiple workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(results) == 5
        for worker_id, success, dest in results:
            assert success == True, f"Worker {worker_id} failed: {dest}"
            if isinstance(dest, Path):
                assert dest.exists()
                # Cleanup
                dest.unlink(missing_ok=True)

    def test_nas_error_handling(self, nas_test_path: Path):
        """Test error handling for NAS operations."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Test with non-existent source file
        non_existent_file = Path("/tmp/non_existent_file.mp4")
        nas_dest = nas_test_path / "error_test.mp4"

        success = downloader._move_file_to_final_destination(
            non_existent_file, nas_dest
        )
        assert success == False
        assert not nas_dest.exists()

        # Test with invalid destination (should fail gracefully)
        temp_file = Path(tempfile.mktemp(suffix=".mp4"))
        temp_file.write_bytes(b"test content")

        try:
            invalid_dest = Path("/invalid/path/that/does/not/exist/test.mp4")
            success = downloader._move_file_to_final_destination(
                temp_file, invalid_dest
            )
            assert success == False

        finally:
            temp_file.unlink(missing_ok=True)

    def test_nas_cleanup_operations(self, nas_test_path: Path):
        """Test cleanup operations on NAS."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Create temp directory with files
        job_id = 88888
        temp_dir = downloader._get_temp_processing_dir(job_id)
        (temp_dir / "test_file1.mp4").write_text("test content 1")
        (temp_dir / "test_file2.srt").write_text("test subtitle content")

        # Test cleanup
        downloader._cleanup_temp_directory(temp_dir)

        # Verify cleanup
        assert not temp_dir.exists()
        # Note: Only the specific job directory is cleaned up, not the parent .temp directory

    def test_nas_path_resolution(self, nas_test_path: Path):
        """Test NAS path resolution and handling."""
        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Test various NAS path formats
        nas_paths = [
            nas_test_path,
            nas_test_path / "videos",
            nas_test_path / "audio" / "music",
            nas_test_path / "deep" / "nested" / "path",
        ]

        for path in nas_paths:
            assert downloader._is_nas_path(path) == True
            assert str(path).startswith("/Volumes/")

    def test_nas_performance_characteristics(self, nas_test_path: Path):
        """Test NAS performance characteristics."""
        import time

        config = Mock(spec=Config)
        downloader = VideoDownloadService(config, verbose=False)

        # Test write performance
        test_file = nas_test_path / "performance_test.txt"
        content = "x" * 1024  # 1KB content

        start_time = time.time()
        test_file.write_text(content)
        write_time = time.time() - start_time

        try:
            # Test read performance
            start_time = time.time()
            read_content = test_file.read_text()
            read_time = time.time() - start_time

            assert read_content == content
            assert write_time < 1.0  # Should write in less than 1 second
            assert read_time < 1.0  # Should read in less than 1 second

            # Log performance metrics
            print(f"NAS Write time: {write_time:.3f}s")
            print(f"NAS Read time: {read_time:.3f}s")

        finally:
            test_file.unlink(missing_ok=True)
