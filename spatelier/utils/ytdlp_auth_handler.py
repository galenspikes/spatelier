"""
Centralized authentication error detection and retry handler for yt-dlp operations.

Provides unified error detection and retry logic for yt-dlp operations that fail
due to authentication issues (age-restricted content, private videos, etc.).
"""

from typing import Any, Callable, Dict, Optional, TypeVar

from spatelier.utils.cookie_manager import CookieManager

T = TypeVar("T")


class YtDlpAuthHandler:
    """
    Centralized handler for yt-dlp authentication errors and retries.
    
    Detects authentication errors and automatically retries operations
    with cookies when available.
    """

    # Keywords that indicate authentication errors
    AUTH_ERROR_KEYWORDS = [
        "sign in",
        "login",
        "age",
        "cookies",
        "authentication",
        "private",
        "restricted",
        "unauthorized",
        "forbidden",
        "access denied",
    ]

    def __init__(self, cookie_manager: CookieManager, logger=None):
        """Initialize the auth error handler.
        
        Args:
            cookie_manager: CookieManager instance for getting cookies
            logger: Optional logger instance
        """
        self.cookie_manager = cookie_manager
        self.logger = logger or self._get_default_logger()

    def _get_default_logger(self):
        """Get default logger if none provided."""
        import logging
        return logging.getLogger(__name__)

    def is_auth_error(self, error: Exception) -> bool:
        """Check if an exception indicates an authentication error.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error appears to be authentication-related, False otherwise
        """
        error_msg = str(error).lower()
        return any(keyword in error_msg for keyword in self.AUTH_ERROR_KEYWORDS)

    def update_ydl_opts_with_cookies(self, ydl_opts: Dict[str, Any]) -> Optional[str]:
        """Update yt-dlp options to use cookie file instead of cookies_from_browser.
        
        Args:
            ydl_opts: yt-dlp options dictionary to update
            
        Returns:
            Path to cookie file if successful, None otherwise
        """
        cookie_file = self.cookie_manager.get_youtube_cookies()
        if cookie_file:
            # Use the cookie file instead of cookies_from_browser
            ydl_opts["cookies"] = cookie_file
            if "cookies_from_browser" in ydl_opts:
                del ydl_opts["cookies_from_browser"]
            return cookie_file
        return None

    def retry_with_cookies(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation",
        ydl_opts: Optional[Dict[str, Any]] = None,
    ) -> Optional[T]:
        """Retry a yt-dlp operation with cookies if it fails due to authentication.
        
        This method:
        1. Attempts the operation
        2. If it fails with an auth error, gets cookies and retries
        3. Returns the result or None if retry also fails
        
        Args:
            operation: Callable that performs the yt-dlp operation
            operation_name: Name of the operation (for logging)
            ydl_opts: Optional yt-dlp options dict to update with cookies
            
        Returns:
            Result of the operation if successful, None otherwise
        """
        try:
            # Try the operation first
            return operation()
        except Exception as e:
            # Check if this is an authentication error
            if not self.is_auth_error(e):
                # Not an auth error, re-raise
                raise

            self.logger.warning(
                f"{operation_name} failed due to authentication - attempting to get cookies..."
            )

            # Try to get cookies and update options if provided
            cookie_file = None
            if ydl_opts is not None:
                cookie_file = self.update_ydl_opts_with_cookies(ydl_opts)

            if cookie_file:
                self.logger.info(f"Retrying {operation_name} with cookies...")
                try:
                    # Retry the operation
                    return operation()
                except Exception as retry_error:
                    self.logger.error(
                        f"{operation_name} failed after cookie refresh: {retry_error}"
                    )
                    return None
            else:
                self.logger.error(f"Could not get cookies for {operation_name}")
                return None

    def execute_with_auth_retry(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation",
        ydl_opts: Optional[Dict[str, Any]] = None,
    ) -> Optional[T]:
        """Execute an operation with automatic auth error detection and retry.
        
        This is a convenience method that wraps retry_with_cookies but handles
        both auth and non-auth errors more gracefully.
        
        Args:
            operation: Callable that performs the yt-dlp operation
            operation_name: Name of the operation (for logging)
            ydl_opts: Optional yt-dlp options dict to update with cookies
            
        Returns:
            Result of the operation if successful, None otherwise
        """
        try:
            return operation()
        except Exception as e:
            if self.is_auth_error(e):
                # Auth error - try with cookies
                if ydl_opts is not None:
                    cookie_file = self.update_ydl_opts_with_cookies(ydl_opts)
                    if cookie_file:
                        self.logger.info(f"Retrying {operation_name} with cookies...")
                        try:
                            return operation()
                        except Exception as retry_error:
                            self.logger.error(
                                f"{operation_name} failed after cookie refresh: {retry_error}"
                            )
                            return None
                else:
                    self.logger.warning(
                        f"{operation_name} failed with auth error but no ydl_opts provided for retry"
                    )
                    return None
            else:
                # Not an auth error, re-raise
                raise
