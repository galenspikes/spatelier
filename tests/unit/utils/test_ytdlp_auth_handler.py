"""
Tests for YtDlpAuthHandler.

Tests issue #7: Centralize auth error detection + retry for yt-dlp flows.
"""

from unittest.mock import Mock, patch

import pytest

from spatelier.utils.cookie_manager import CookieManager
from spatelier.utils.ytdlp_auth_handler import YtDlpAuthHandler


@pytest.fixture
def mock_cookie_manager():
    """Create a mock CookieManager for testing."""
    manager = Mock(spec=CookieManager)
    manager.get_youtube_cookies.return_value = "/tmp/test_cookies.txt"
    return manager


@pytest.fixture
def auth_handler(mock_cookie_manager):
    """Create an YtDlpAuthHandler instance for testing."""
    return YtDlpAuthHandler(mock_cookie_manager, logger=Mock())


class TestYtDlpAuthHandler:
    """Test YtDlpAuthHandler functionality."""

    def test_initialization(self, auth_handler, mock_cookie_manager):
        """Test that YtDlpAuthHandler initializes correctly."""
        assert auth_handler.cookie_manager == mock_cookie_manager
        assert auth_handler.logger is not None

    def test_is_auth_error_with_sign_in(self, auth_handler):
        """Test is_auth_error detects 'sign in' errors."""
        error = Exception("Please sign in to view this video")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_age(self, auth_handler):
        """Test is_auth_error detects 'age' errors."""
        error = Exception("This video is age-restricted")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_cookies(self, auth_handler):
        """Test is_auth_error detects 'cookies' errors."""
        error = Exception("Cookies required for this video")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_authentication(self, auth_handler):
        """Test is_auth_error detects 'authentication' errors."""
        error = Exception("Authentication required")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_private(self, auth_handler):
        """Test is_auth_error detects 'private' errors."""
        error = Exception("This video is private")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_restricted(self, auth_handler):
        """Test is_auth_error detects 'restricted' errors."""
        error = Exception("This video is restricted")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_login(self, auth_handler):
        """Test is_auth_error detects 'login' errors."""
        error = Exception("Please login to view this video")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_unauthorized(self, auth_handler):
        """Test is_auth_error detects 'unauthorized' errors."""
        error = Exception("Unauthorized access")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_forbidden(self, auth_handler):
        """Test is_auth_error detects 'forbidden' errors."""
        error = Exception("403 Forbidden")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_access_denied(self, auth_handler):
        """Test is_auth_error detects 'access denied' errors."""
        error = Exception("Access denied to this content")
        assert auth_handler.is_auth_error(error) is True

    def test_is_auth_error_with_non_auth_error(self, auth_handler):
        """Test is_auth_error returns False for non-auth errors."""
        error = Exception("Network error occurred")
        assert auth_handler.is_auth_error(error) is False

    def test_update_ydl_opts_with_cookies_success(self, auth_handler, mock_cookie_manager):
        """Test update_ydl_opts_with_cookies updates options correctly."""
        ydl_opts = {"cookies_from_browser": ("chrome", "firefox")}
        
        result = auth_handler.update_ydl_opts_with_cookies(ydl_opts)
        
        assert result == "/tmp/test_cookies.txt"
        assert "cookies" in ydl_opts
        assert ydl_opts["cookies"] == "/tmp/test_cookies.txt"
        assert "cookies_from_browser" not in ydl_opts

    def test_update_ydl_opts_with_cookies_no_cookies(self, auth_handler, mock_cookie_manager):
        """Test update_ydl_opts_with_cookies returns None when no cookies available."""
        mock_cookie_manager.get_youtube_cookies.return_value = None
        ydl_opts = {"cookies_from_browser": ("chrome",)}
        
        result = auth_handler.update_ydl_opts_with_cookies(ydl_opts)
        
        assert result is None
        assert "cookies_from_browser" in ydl_opts  # Should remain unchanged

    def test_retry_with_cookies_success_on_first_attempt(self, auth_handler):
        """Test retry_with_cookies returns result when operation succeeds immediately."""
        def operation():
            return "success"
        
        result = auth_handler.retry_with_cookies(operation, "test operation")
        assert result == "success"

    def test_retry_with_cookies_retries_on_auth_error(self, auth_handler, mock_cookie_manager):
        """Test retry_with_cookies retries with cookies on auth error."""
        call_count = [0]
        
        def operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Please sign in to view this video")
            return "success"
        
        ydl_opts = {"cookies_from_browser": ("chrome",)}
        result = auth_handler.retry_with_cookies(operation, "test operation", ydl_opts)
        
        assert result == "success"
        assert call_count[0] == 2  # Should have been called twice
        assert mock_cookie_manager.get_youtube_cookies.called

    def test_retry_with_cookies_fails_on_non_auth_error(self, auth_handler):
        """Test retry_with_cookies re-raises non-auth errors."""
        def operation():
            raise Exception("Network error")
        
        with pytest.raises(Exception, match="Network error"):
            auth_handler.retry_with_cookies(operation, "test operation")

    def test_retry_with_cookies_fails_when_no_cookies(self, auth_handler, mock_cookie_manager):
        """Test retry_with_cookies returns None when cookies unavailable."""
        mock_cookie_manager.get_youtube_cookies.return_value = None
        
        def operation():
            raise Exception("Please sign in")
        
        result = auth_handler.retry_with_cookies(operation, "test operation")
        assert result is None

    def test_retry_with_cookies_fails_on_retry_error(self, auth_handler, mock_cookie_manager):
        """Test retry_with_cookies returns None when retry also fails."""
        def operation():
            raise Exception("Please sign in")
        
        ydl_opts = {}
        result = auth_handler.retry_with_cookies(operation, "test operation", ydl_opts)
        assert result is None

    def test_execute_with_auth_retry_success(self, auth_handler):
        """Test execute_with_auth_retry returns result when operation succeeds."""
        def operation():
            return "success"
        
        result = auth_handler.execute_with_auth_retry(operation, "test operation")
        assert result == "success"

    def test_execute_with_auth_retry_retries_on_auth_error(self, auth_handler, mock_cookie_manager):
        """Test execute_with_auth_retry retries with cookies on auth error."""
        call_count = [0]
        
        def operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Age-restricted video")
            return "success"
        
        ydl_opts = {}
        result = auth_handler.execute_with_auth_retry(operation, "test operation", ydl_opts)
        
        assert result == "success"
        assert call_count[0] == 2

    def test_execute_with_auth_retry_raises_non_auth_error(self, auth_handler):
        """Test execute_with_auth_retry re-raises non-auth errors."""
        def operation():
            raise ValueError("Invalid URL")
        
        with pytest.raises(ValueError, match="Invalid URL"):
            auth_handler.execute_with_auth_retry(operation, "test operation")

    def test_execute_with_auth_retry_no_ydl_opts(self, auth_handler):
        """Test execute_with_auth_retry handles missing ydl_opts gracefully."""
        def operation():
            raise Exception("Authentication required")
        
        result = auth_handler.execute_with_auth_retry(operation, "test operation", ydl_opts=None)
        assert result is None
