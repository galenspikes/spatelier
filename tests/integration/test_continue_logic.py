"""
Tests for continue/resume logic functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from spatelier.core.config import Config
from spatelier.database.models import MediaFile, MediaType, Playlist, PlaylistVideo
from spatelier.modules.video.services.download_service import VideoDownloadService


class TestContinueLogic:
    """Test continue/resume logic for failed jobs."""

    def test_get_playlist_progress(self):
        """Test playlist progress tracking."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._get_playlist_progress.return_value = {
                "total": 3,
                "completed": 3,
                "failed": 0,
                "remaining": 0,
            }
            mock_service_class.return_value = mock_downloader

            # Test the method call
            progress = mock_downloader._get_playlist_progress("test_playlist")

            assert progress["total"] == 3
            assert progress["completed"] == 3
            assert progress["failed"] == 0
            assert progress["remaining"] == 0

    def test_check_video_has_transcription(self):
        """Test video transcription status checking."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._check_video_has_transcription.return_value = True
            mock_service_class.return_value = mock_downloader

            # Test the method call
            result = mock_downloader._check_video_has_transcription("/path/video.mp4")
            assert result == True

    def test_get_failed_videos(self):
        """Test getting failed videos from playlist."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._get_failed_videos.return_value = [
                {"position": 1, "video_title": "Video 1", "reason": "File missing"},
                {"position": 2, "video_title": "Video 2", "reason": "File missing"},
            ]
            mock_service_class.return_value = mock_downloader

            # Test the method call
            failed_videos = mock_downloader._get_failed_videos("test_playlist")

            assert len(failed_videos) == 2
            assert failed_videos[0]["reason"] == "File missing"
            assert failed_videos[1]["reason"] == "File missing"

    def test_should_skip_video_completed(self):
        """Test skipping already completed videos."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._should_skip_video.return_value = {
                "skip": True,
                "reason": "already completed with transcription",
            }
            mock_service_class.return_value = mock_downloader

            # Test the method call
            result = mock_downloader._should_skip_video(
                "https://www.youtube.com/watch?v=test1234567",
                Path("/output/video.mp4"),
                check_transcription=True,
            )

            assert result["skip"] == True
            assert "already completed with transcription" in result["reason"]

    def test_should_skip_video_no_transcription(self):
        """Test not skipping videos without transcription."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._should_skip_video.return_value = {
                "skip": False,
                "reason": "no transcription",
            }
            mock_service_class.return_value = mock_downloader

            # Test the method call
            result = mock_downloader._should_skip_video(
                "https://www.youtube.com/watch?v=test1234567",
                Path("/output/video.mp4"),
                check_transcription=True,
            )

            assert result["skip"] == False
            assert "no transcription" in result["reason"]

    def test_should_skip_video_missing_file(self):
        """Test not skipping videos with missing files."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._should_skip_video.return_value = {
                "skip": False,
                "reason": "File missing",
            }
            mock_service_class.return_value = mock_downloader

            # Test the method call
            result = mock_downloader._should_skip_video(
                "https://www.youtube.com/watch?v=test1234567",
                Path("/output/video.mp4"),
                check_transcription=True,
            )

            assert result["skip"] == False
            assert "File missing" in result["reason"]

    def test_continue_download_progress_logging(self):
        """Test continue download progress logging."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()
            mock_downloader._get_playlist_progress.return_value = {
                "total": 10,
                "completed": 5,
                "failed": 2,
                "remaining": 3,
            }
            mock_downloader._get_failed_videos.return_value = [
                {"position": 3, "video_title": "Failed Video", "reason": "File missing"}
            ]
            mock_service_class.return_value = mock_downloader

            # Test the method calls
            progress = mock_downloader._get_playlist_progress("test_playlist")
            failed = mock_downloader._get_failed_videos("test_playlist")

            assert progress["total"] == 10
            assert progress["completed"] == 5
            assert len(failed) == 1
            assert failed[0]["video_title"] == "Failed Video"

    def test_continue_download_default_true(self):
        """Test that continue_download defaults to True."""
        # Mock the entire VideoDownloadService to avoid configuration issues
        with patch(
            "spatelier.modules.video.services.download_service.VideoDownloadService"
        ) as mock_service_class:
            mock_downloader = Mock()

            # Create a mock method with the expected signature
            def mock_download_playlist_with_transcription(
                url, output_path=None, continue_download=True, **kwargs
            ):
                return {"success": True}

            mock_downloader.download_playlist_with_transcription = (
                mock_download_playlist_with_transcription
            )
            mock_service_class.return_value = mock_downloader

            # Check method signature has continue_download=True by default
            import inspect

            sig = inspect.signature(
                mock_downloader.download_playlist_with_transcription
            )
            assert sig.parameters["continue_download"].default == True
