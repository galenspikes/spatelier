"""
Tests for smart overwrite logic functionality.

This module tests the smart overwrite logic that determines
when to overwrite existing videos based on subtitle presence
and quality comparison.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from spatelier.core.config import Config
from spatelier.modules.video.services.download_service import VideoDownloadService


class TestSmartOverwrite:
    """Test smart overwrite logic functionality."""

    @pytest.fixture
    def config(self):
        """Create config for testing."""
        return Config()

    @pytest.fixture
    def downloader(self, config):
        """Create video downloader for testing."""
        with patch("spatelier.core.database_service.DatabaseServiceFactory") as mock_db_factory:
            mock_db_service = Mock()
            mock_repos = Mock()
            mock_repos.media = Mock()
            mock_repos.jobs = Mock()
            mock_repos.analytics = Mock()
            mock_db_service.initialize.return_value = mock_repos
            mock_db_service.get_db_manager.return_value = Mock()
            mock_db_factory.return_value = mock_db_service

            return VideoDownloadService(
                config, verbose=False, db_service=mock_db_service
            )

    @pytest.fixture
    def sample_video_file(self):
        """Create a temporary video file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_check_existing_video_file_not_exists(self, downloader):
        """Test checking non-existent video file."""
        non_existent_path = Path("/non/existent/video.mp4")

        result = downloader._check_existing_video(
            non_existent_path, "https://example.com/video"
        )

        assert result["exists"] is False
        assert result["has_subtitles"] is False
        assert result["should_overwrite"] is True
        assert "does not exist" in result["reason"]

    def test_check_existing_video_file_exists_no_subtitles(
        self, downloader, sample_video_file
    ):
        """Test checking existing video file without subtitles."""
        # Mock TranscriptionService.has_whisper_subtitles
        with patch(
            "spatelier.modules.video.services.transcription_service.TranscriptionService"
        ) as mock_transcription_service_class:
            mock_transcription_service = mock_transcription_service_class.return_value
            mock_transcription_service.has_whisper_subtitles.return_value = False

            result = downloader._check_existing_video(
                sample_video_file, "https://example.com/video"
            )

            assert result["exists"] is True
            assert result["has_subtitles"] is False
            assert result["should_overwrite"] is True
            assert "without subtitles" in result["reason"]

    def test_check_existing_video_file_exists_with_subtitles(
        self, downloader, sample_video_file
    ):
        """Test checking existing video file with subtitles."""
        # Mock TranscriptionService.has_whisper_subtitles
        with patch(
            "spatelier.modules.video.services.transcription_service.TranscriptionService"
        ) as mock_transcription_service_class:
            mock_transcription_service = mock_transcription_service_class.return_value
            mock_transcription_service.has_whisper_subtitles.return_value = True

            result = downloader._check_existing_video(
                sample_video_file, "https://example.com/video"
            )

            assert result["exists"] is True
            assert result["has_subtitles"] is True
            assert result["should_overwrite"] is False
            assert "with WhisperAI subtitles" in result["reason"]

    def test_has_whisper_subtitles_success(self, downloader, sample_video_file):
        """Test successful subtitle detection."""
        # Test TranscriptionService.has_whisper_subtitles directly
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        # Mock ffprobe to return subtitle tracks
        mock_ffprobe_output = {
            "streams": [
                {"index": 0, "codec_type": "video"},
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "tags": {"title": "Subtitles (English - WhisperAI)"},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is True

    def test_has_whisper_subtitles_no_subtitles(self, downloader, sample_video_file):
        """Test subtitle detection when no subtitles exist."""
        # Test TranscriptionService.has_whisper_subtitles directly
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        # Mock ffprobe to return no subtitle tracks
        mock_ffprobe_output = {"streams": [{"index": 0, "codec_type": "video"}]}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is False

    def test_has_whisper_subtitles_ffprobe_failure(self, downloader, sample_video_file):
        """Test subtitle detection when ffprobe fails."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "ffprobe error"

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is False

    def test_has_whisper_subtitles_timeout(self, downloader, sample_video_file):
        """Test subtitle detection when ffprobe times out."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutError("ffprobe timeout")

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is False

    def test_has_whisper_subtitles_whisper_in_title(
        self, downloader, sample_video_file
    ):
        """Test subtitle detection with WhisperAI in title."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        mock_ffprobe_output = {
            "streams": [
                {"index": 0, "codec_type": "video"},
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "tags": {"title": "Subtitles (English - WhisperAI)"},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is True

    def test_has_whisper_subtitles_whisperai_in_title(
        self, downloader, sample_video_file
    ):
        """Test subtitle detection with WhisperAI in title (case insensitive)."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        mock_ffprobe_output = {
            "streams": [
                {"index": 0, "codec_type": "video"},
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "tags": {"title": "Subtitles (English - whisperai)"},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is True

    def test_has_whisper_subtitles_other_subtitles(self, downloader, sample_video_file):
        """Test subtitle detection with non-WhisperAI subtitles."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        mock_ffprobe_output = {
            "streams": [
                {"index": 0, "codec_type": "video"},
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "tags": {"title": "English Subtitles"},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            # Should return False because there are no WhisperAI subtitles
            assert result is False

    def test_has_whisper_subtitles_no_title_tag(self, downloader, sample_video_file):
        """Test subtitle detection with subtitles but no title tag."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        mock_ffprobe_output = {
            "streams": [
                {"index": 0, "codec_type": "video"},
                {"index": 1, "codec_type": "subtitle"},
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_ffprobe_output)

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            # Should return False because there are no WhisperAI subtitles (no title tag)
            assert result is False

    def test_has_whisper_subtitles_invalid_json(self, downloader, sample_video_file):
        """Test subtitle detection with invalid JSON from ffprobe."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "invalid json"

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is False

    def test_has_whisper_subtitles_exception_handling(
        self, downloader, sample_video_file
    ):
        """Test subtitle detection with exception handling."""
        from spatelier.modules.video.services.transcription_service import TranscriptionService
        from spatelier.core.config import Config

        config = Config()
        transcription_service = TranscriptionService(config, verbose=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            result = transcription_service.has_whisper_subtitles(sample_video_file)

            assert result is False

    def test_smart_overwrite_integration(self, downloader, sample_video_file):
        """Test smart overwrite logic integration."""
        # Test case 1: File doesn't exist - should overwrite
        non_existent_path = Path("/non/existent/video.mp4")
        result1 = downloader._check_existing_video(
            non_existent_path, "https://example.com/video"
        )
        assert result1["should_overwrite"] is True

        # Test case 2: File exists without subtitles - should overwrite
        with patch(
            "spatelier.modules.video.services.transcription_service.TranscriptionService"
        ) as mock_transcription_service_class:
            mock_transcription_service = mock_transcription_service_class.return_value
            mock_transcription_service.has_whisper_subtitles.return_value = False

            result2 = downloader._check_existing_video(
                sample_video_file, "https://example.com/video"
            )
            assert result2["should_overwrite"] is True

        # Test case 3: File exists with subtitles - should not overwrite
        with patch(
            "spatelier.modules.video.services.transcription_service.TranscriptionService"
        ) as mock_transcription_service_class:
            mock_transcription_service = mock_transcription_service_class.return_value
            mock_transcription_service.has_whisper_subtitles.return_value = True

            result3 = downloader._check_existing_video(
                sample_video_file, "https://example.com/video"
            )
            assert result3["should_overwrite"] is False
