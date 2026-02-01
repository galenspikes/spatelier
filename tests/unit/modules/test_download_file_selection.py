"""
Tests for VideoDownloadService file selection logic.

Tests issue #5: Fix yt-dlp download file selection in VideoDownloadService.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

from spatelier.core.config import Config
from spatelier.modules.video.services.download_service import VideoDownloadService


@pytest.fixture
def download_service():
    """Create a VideoDownloadService instance for testing."""
    config = Config()
    return VideoDownloadService(config, verbose=False)


class TestDownloadFileSelection:
    """Test file selection logic for video downloads."""

    def test_resolve_downloaded_path_with_existing_file(self, download_service):
        """Test that _resolve_downloaded_path returns file when prepare_filename() path exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            test_file = output_dir / "Test Video [abc123].mp4"
            test_file.write_bytes(b"test video content")
            
            # Mock yt-dlp objects
            mock_ydl = Mock()
            mock_ydl.prepare_filename.return_value = str(test_file)
            
            mock_info = {
                "id": "abc123",
                "title": "Test Video",
                "ext": "mp4",
            }
            
            result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
            
            assert result == test_file
            assert result.exists()
            assert result.stat().st_size > 0

    def test_resolve_downloaded_path_with_video_id_fallback(self, download_service):
        """Test that _resolve_downloaded_path falls back to video ID matching when prepare_filename() path doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            # Create file with video ID in name (but different from prepare_filename result)
            actual_file = output_dir / "Different Title [abc123].mp4"
            actual_file.write_bytes(b"test video content")
            
            # Mock yt-dlp - prepare_filename returns path that doesn't exist
            mock_ydl = Mock()
            mock_ydl.prepare_filename.return_value = str(output_dir / "Test Video [abc123].mp4")
            
            mock_info = {
                "id": "abc123",
                "title": "Test Video",
                "ext": "mp4",
            }
            
            result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
            
            # Should find file by video ID pattern
            assert result == actual_file
            assert result.exists()

    def test_resolve_downloaded_path_with_most_recent_fallback(self, download_service):
        """Test that _resolve_downloaded_path falls back to most recent file when video ID matching fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            # Create multiple files
            old_file = output_dir / "Old Video [xyz789].mp4"
            old_file.write_bytes(b"old content")
            
            # Wait a moment and create newer file
            import time
            time.sleep(0.1)
            new_file = output_dir / "New Video [def456].mp4"
            new_file.write_bytes(b"new content")
            
            # Mock yt-dlp - prepare_filename returns path that doesn't exist
            mock_ydl = Mock()
            mock_ydl.prepare_filename.return_value = str(output_dir / "Test Video [abc123].mp4")
            
            mock_info = {
                "id": "abc123",  # Doesn't match any file
                "title": "Test Video",
                "ext": "mp4",
            }
            
            result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
            
            # Should return most recent file (with warning)
            assert result == new_file
            assert result.exists()

    def test_resolve_downloaded_path_with_playlist_entry(self, download_service):
        """Test that _resolve_downloaded_path handles playlist entries correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            test_file = output_dir / "Playlist Video [xyz123].mp4"
            test_file.write_bytes(b"test content")
            
            mock_ydl = Mock()
            mock_ydl.prepare_filename.return_value = str(test_file)
            
            # Simulate playlist info structure
            mock_info = {
                "_type": "playlist",
                "entries": [
                    {
                        "id": "xyz123",
                        "title": "Playlist Video",
                        "ext": "mp4",
                    }
                ],
            }
            
            result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
            
            assert result == test_file
            assert result.exists()

    def test_resolve_downloaded_path_with_empty_info(self, download_service):
        """Test that _resolve_downloaded_path returns None for empty/invalid info."""
        mock_ydl = Mock()
        
        # Test with None
        assert download_service._resolve_downloaded_path(mock_ydl, None) is None
        
        # Test with empty dict
        assert download_service._resolve_downloaded_path(mock_ydl, {}) is None
        
        # Test with non-dict
        assert download_service._resolve_downloaded_path(mock_ydl, "not a dict") is None

    def test_resolve_downloaded_path_validates_file_size(self, download_service):
        """Test that _resolve_downloaded_path only returns files with size > 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            # Create empty file
            empty_file = output_dir / "Empty Video [abc123].mp4"
            empty_file.touch()  # Creates file with 0 bytes
            
            mock_ydl = Mock()
            mock_ydl.prepare_filename.return_value = str(empty_file)
            
            mock_info = {
                "id": "abc123",
                "title": "Empty Video",
                "ext": "mp4",
            }
            
            result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
            
            # Should not return empty file, should try fallback
            # Since no other files exist, should return None
            assert result is None or result != empty_file

    def test_resolve_downloaded_path_handles_exceptions(self, download_service):
        """Test that _resolve_downloaded_path handles exceptions gracefully."""
        mock_ydl = Mock()
        mock_ydl.prepare_filename.side_effect = Exception("Test error")
        
        mock_info = {
            "id": "abc123",
            "title": "Test Video",
            "ext": "mp4",
        }
        
        # Should not raise, should return None
        result = download_service._resolve_downloaded_path(mock_ydl, mock_info)
        assert result is None
