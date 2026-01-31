"""
Tests for PlaylistService format selector.

Tests issue #8: Fix playlist format selector for non-numeric quality values.
"""

import pytest

from core.config import Config
from modules.video.services.playlist_service import PlaylistService


@pytest.fixture
def playlist_service():
    """Create a PlaylistService instance for testing."""
    config = Config()
    return PlaylistService(config, verbose=False)


class TestPlaylistFormatSelector:
    """Test format selector for playlist downloads."""

    def test_format_selector_best_quality(self, playlist_service):
        """Test format selector with 'best' quality."""
        result = playlist_service._get_format_selector("best", "mp4")
        # Should have fallback chain
        assert "best[ext=mp4]" in result
        assert "bestvideo[ext=mp4]+bestaudio" in result
        assert result.endswith("/best")

    def test_format_selector_worst_quality(self, playlist_service):
        """Test format selector with 'worst' quality."""
        result = playlist_service._get_format_selector("worst", "mp4")
        assert result == "worst[ext=mp4]/worst"

    def test_format_selector_720p_quality(self, playlist_service):
        """Test format selector with '720p' quality (non-numeric)."""
        result = playlist_service._get_format_selector("720p", "mp4")
        # Should extract numeric part and use it in height constraint
        assert "height<=720" in result
        assert "height<=720p" not in result  # Should NOT have the 'p'
        assert "[ext=mp4]" in result
        # Should have fallback chain
        assert "bestvideo[height<=720]+bestaudio" in result

    def test_format_selector_1080p_quality(self, playlist_service):
        """Test format selector with '1080p' quality (non-numeric)."""
        result = playlist_service._get_format_selector("1080p", "mp4")
        # Should extract numeric part
        assert "height<=1080" in result
        assert "height<=1080p" not in result  # Should NOT have the 'p'
        assert "[ext=mp4]" in result

    def test_format_selector_480p_quality(self, playlist_service):
        """Test format selector with '480p' quality (non-numeric)."""
        result = playlist_service._get_format_selector("480p", "mkv")
        assert "height<=480" in result
        assert "height<=480p" not in result
        assert "[ext=mkv]" in result

    def test_format_selector_numeric_quality(self, playlist_service):
        """Test format selector with numeric quality (e.g., '720')."""
        result = playlist_service._get_format_selector("720", "mp4")
        # Should handle numeric values
        assert "height<=720" in result
        assert "[ext=mp4]" in result

    def test_format_selector_different_formats(self, playlist_service):
        """Test format selector with different video formats."""
        for fmt in ["mp4", "mkv", "webm"]:
            result = playlist_service._get_format_selector("720p", fmt)
            assert f"[ext={fmt}]" in result
            assert "height<=720" in result

    def test_format_selector_fallback_chain(self, playlist_service):
        """Test that format selector includes proper fallback chain."""
        result = playlist_service._get_format_selector("720p", "mp4")
        # Should have multiple fallback options
        parts = result.split("/")
        assert len(parts) >= 3  # Should have at least 3 fallback options
        # First should be best with height constraint
        assert "best[height<=720][ext=mp4]" in parts[0]
        # Should include bestvideo+bestaudio fallback
        assert any("bestvideo[height<=720]+bestaudio" in part for part in parts)
