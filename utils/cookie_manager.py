"""
Cookie manager for browser-agnostic cookie handling.

Provides centralized cookie management for yt-dlp operations,
supporting both browser cookie extraction and cookie refresh via Playwright.
Includes cookie caching with expiration and automatic cleanup.
"""

import os
import platform
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Set, Tuple

from core.config import get_default_data_dir


class CookieManager:
    """
    Browser-agnostic cookie manager for yt-dlp operations.
    
    Provides methods for:
    - Getting browser list for yt-dlp's cookies_from_browser option
    - Refreshing YouTube cookies using Playwright
    - Saving cookies to Netscape format file
    - Caching cookies with expiration checking
    - Automatic cleanup of cookie files
    """

    # Cookie expiration buffer: refresh cookies 1 hour before they expire
    COOKIE_EXPIRATION_BUFFER = 3600  # 1 hour in seconds

    def __init__(self, config=None, verbose: bool = False, logger=None):
        """Initialize the cookie manager.
        
        Args:
            config: Optional Config instance
            verbose: Enable verbose logging
            logger: Optional logger instance (if None, uses default)
        """
        self.config = config
        self.verbose = verbose
        self.logger = logger or self._get_default_logger()
        
        # Track cookie files created for automatic cleanup
        self._created_cookie_files: Set[str] = set()
        
        # Get cookies directory for caching
        if config:
            # Use config's data directory if available
            try:
                data_dir = get_default_data_dir()
            except:
                data_dir = Path.home() / ".local" / "share" / "spatelier"
        else:
            data_dir = get_default_data_dir()
        
        self.cookies_dir = data_dir / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        # Cached cookie file path
        self._cached_cookie_file = self.cookies_dir / "youtube_cookies.txt"

    def _get_default_logger(self):
        """Get default logger if none provided."""
        import logging
        return logging.getLogger(__name__)

    def get_browser_list(self) -> Tuple[str, ...]:
        """Get list of browsers to try for cookie extraction.
        
        Returns a tuple of browser names in order of preference.
        yt-dlp will try each browser until one works, or continue
        without cookies if none are available.
        
        Note: On macOS, Chrome is more reliable than Safari for cookie extraction.
        
        Returns:
            Tuple of browser names (e.g., ("chrome", "safari", "firefox", "edge"))
        """
        system = platform.system().lower()

        if system == "darwin":  # macOS - prioritize Chrome over Safari
            browsers = ("chrome", "safari", "firefox", "edge")
        else:  # Linux, Windows, etc.
            browsers = ("chrome", "firefox", "safari", "edge")

        return browsers

    def get_youtube_cookies(self) -> Optional[str]:
        """Get YouTube cookies, using cached cookies if valid, otherwise refreshing.
        
        This is the main method to use - it checks for valid cached cookies first,
        and only refreshes if needed.
        
        Returns:
            Path to cookie file if successful, None otherwise
        """
        # Check if we have valid cached cookies
        cached_file = self._get_cached_cookie_file()
        if cached_file:
            if self.verbose:
                self.logger.info("Using cached YouTube cookies")
            return cached_file
        
        # No valid cached cookies, refresh them
        if self.verbose:
            self.logger.info("No valid cached cookies, refreshing...")
        return self.refresh_youtube_cookies()

    def _get_browser_user_data_dir(self, browser: str) -> Optional[Path]:
        """Get user data directory for a browser on the current platform.
        
        Args:
            browser: Browser name ("chrome", "firefox", "safari", "edge")
            
        Returns:
            Path to browser user data directory, or None if not found
        """
        system = platform.system().lower()
        home = Path.home()
        
        browser_paths = {
            "chrome": {
                "darwin": home / "Library" / "Application Support" / "Google" / "Chrome",
                "linux": home / ".config" / "google-chrome",
                "windows": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
            },
            "firefox": {
                "darwin": home / "Library" / "Application Support" / "Firefox",
                "linux": home / ".mozilla" / "firefox",
                "windows": Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox",
            },
            "edge": {
                "darwin": home / "Library" / "Application Support" / "Microsoft Edge",
                "linux": home / ".config" / "microsoft-edge",
                "windows": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
            },
            "safari": {
                "darwin": home / "Library" / "Safari",
                # Safari is macOS-only
                "linux": None,
                "windows": None,
            },
        }
        
        if browser not in browser_paths:
            return None
        
        browser_config = browser_paths[browser]
        if system not in browser_config:
            return None
        
        path = browser_config[system]
        if path is None:
            return None
        
        # Expand environment variables for Windows paths
        if system == "windows" and isinstance(path, Path):
            try:
                path = Path(str(path).format(**os.environ))
            except:
                pass
        
        if path and path.exists():
            return path
        
        return None

    def _get_playwright_browser_type(self, browser: str):
        """Get Playwright browser type for a browser name.
        
        Args:
            browser: Browser name ("chrome", "firefox", "safari", "edge")
            
        Returns:
            Playwright browser type, or None if not supported
        """
        # No need to import playwright here - just return the mapping
        browser_map = {
            "chrome": "chromium",
            "edge": "chromium",  # Edge uses Chromium engine
            "firefox": "firefox",
            "safari": "webkit",
        }
        
        return browser_map.get(browser.lower())

    def refresh_youtube_cookies(self) -> Optional[str]:
        """Refresh YouTube cookies by visiting YouTube and extracting fresh cookies.

        Uses Playwright to launch browsers with the user's profile, visit YouTube,
        extract the cookies, and save them to a cached file for reuse.

        Tries browsers in order of preference (same as get_browser_list()) until one works.
        Supports Chrome, Firefox, Edge, and Safari on macOS, Linux, and Windows.

        Returns:
            Path to cookie file if successful, None otherwise
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.logger.warning(
                "Playwright not available - cannot refresh cookies automatically"
            )
            return None

        # Get browser list in order of preference
        browsers = self.get_browser_list()
        
        for browser_name in browsers:
            try:
                # Get browser user data directory
                user_data_dir = self._get_browser_user_data_dir(browser_name)
                if not user_data_dir:
                    if self.verbose:
                        self.logger.debug(f"{browser_name.capitalize()} not found, trying next browser...")
                    continue
                
                # Get Playwright browser type
                browser_type = self._get_playwright_browser_type(browser_name)
                if not browser_type:
                    if self.verbose:
                        self.logger.debug(f"{browser_name.capitalize()} not supported by Playwright, trying next browser...")
                    continue
                
                self.logger.info(
                    f"Refreshing YouTube cookies by visiting YouTube in {browser_name.capitalize()}..."
                )
                
                with sync_playwright() as p:
                    # Get the browser launcher based on type
                    if browser_type == "chromium":
                        # Chrome and Edge use Chromium
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=str(user_data_dir),
                            headless=True,
                            args=["--disable-blink-features=AutomationControlled"],
                        )
                    elif browser_type == "firefox":
                        browser = p.firefox.launch_persistent_context(
                            user_data_dir=str(user_data_dir),
                            headless=True,
                        )
                    elif browser_type == "webkit":
                        # Safari uses WebKit
                        browser = p.webkit.launch_persistent_context(
                            user_data_dir=str(user_data_dir),
                            headless=True,
                        )
                    else:
                        continue
                    
                    # Visit YouTube to refresh session
                    page = browser.new_page()
                    page.goto(
                        "https://www.youtube.com", wait_until="networkidle", timeout=15000
                    )
                    # Wait a moment for cookies to be set
                    page.wait_for_timeout(3000)
                    
                    # Extract cookies from the page
                    cookies = browser.cookies()
                    browser.close()
                    
                    # Filter for YouTube cookies only
                    youtube_cookies = self._filter_youtube_cookies(cookies)
                    
                    if not youtube_cookies:
                        if self.verbose:
                            self.logger.warning(f"No YouTube cookies found in {browser_name}, trying next browser...")
                        continue
                    
                    # Save cookies to cached file
                    cookie_file = self.save_cookies_to_netscape_file(
                        youtube_cookies, str(self._cached_cookie_file)
                    )
                    if cookie_file:
                        self.logger.info(
                            f"YouTube cookies refreshed using {browser_name.capitalize()} and saved to: {cookie_file}"
                        )
                        # Track for cleanup (though cached file persists)
                        self._created_cookie_files.add(cookie_file)
                    return cookie_file
                    
            except Exception as e:
                if self.verbose:
                    self.logger.debug(f"Failed to refresh cookies with {browser_name}: {e}, trying next browser...")
                continue
        
        # No browsers worked
        self.logger.warning("Failed to refresh cookies with any available browser")
        return None

    def _get_cached_cookie_file(self) -> Optional[str]:
        """Check if cached cookie file exists and is still valid.
        
        Returns:
            Path to cached cookie file if valid, None otherwise
        """
        if not self._cached_cookie_file.exists():
            return None
        
        # Check if cookies in file are still valid (not expired)
        if self._are_cookies_valid(self._cached_cookie_file):
            return str(self._cached_cookie_file)
        
        # Cookies expired, remove cached file
        try:
            self._cached_cookie_file.unlink()
            if self.verbose:
                self.logger.info("Cached cookies expired, removed cache file")
        except Exception as e:
            self.logger.warning(f"Failed to remove expired cookie cache: {e}")
        
        return None

    def _are_cookies_valid(self, cookie_file_path: Path) -> bool:
        """Check if cookies in Netscape format file are still valid.
        
        A cookie is valid if at least one cookie in the file hasn't expired
        (or expires far enough in the future to be useful).
        
        Args:
            cookie_file_path: Path to Netscape format cookie file
            
        Returns:
            True if cookies are valid, False otherwise
        """
        try:
            current_time = int(time.time())
            max_expiration = current_time + self.COOKIE_EXPIRATION_BUFFER
            
            with open(cookie_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse Netscape format: domain\tflag\tpath\tsecure\texpires\tname\tvalue
                    parts = line.split("\t")
                    if len(parts) >= 5:
                        try:
                            expires = int(parts[4])
                            # Cookie expires at 0 means session cookie (valid)
                            # Otherwise check if expiration is in the future (with buffer)
                            if expires == 0 or expires > max_expiration:
                                return True
                        except (ValueError, IndexError):
                            # Invalid expiration, skip this cookie
                            continue
            
            # No valid cookies found
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking cookie validity: {e}")
            return False

    def _filter_youtube_cookies(self, cookies: List[dict]) -> List[dict]:
        """Filter cookies to only include YouTube cookies.
        
        Args:
            cookies: List of cookie dictionaries from browser
            
        Returns:
            Filtered list containing only YouTube cookies
        """
        return [
            c
            for c in cookies
            if "youtube.com" in c.get("domain", "")
            or ".youtube.com" in c.get("domain", "")
        ]

    def save_cookies_to_netscape_file(
        self, cookies: List[dict], cookie_file_path: Optional[str] = None
    ) -> Optional[str]:
        """Save cookies to a Netscape format file for yt-dlp.
        
        Args:
            cookies: List of cookie dictionaries
            cookie_file_path: Optional path to save cookie file.
                            If None, creates a temporary file.
                            
        Returns:
            Path to the saved cookie file, or None if failed
        """
        try:
            if cookie_file_path:
                cookie_file = open(cookie_file_path, "w")
            else:
                cookie_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                )
                # Track temporary files for cleanup
                self._created_cookie_files.add(cookie_file.name)

            cookie_file.write("# Netscape HTTP Cookie File\n")
            cookie_file.write("# This file was generated by spatelier\n\n")

            for cookie in cookies:
                domain = cookie.get("domain", "")
                domain_flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                expires = str(int(cookie.get("expires", 0)))
                name = cookie.get("name", "")
                value = cookie.get("value", "")

                cookie_file.write(
                    f"{domain}\t{domain_flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                )

            cookie_file.close()
            return cookie_file.name

        except Exception as e:
            self.logger.warning(f"Failed to save cookies to file: {e}")
            return None

    def cleanup_cookie_files(self, keep_cached: bool = True) -> int:
        """Clean up temporary cookie files created by this manager.
        
        Args:
            keep_cached: If True, don't delete the cached cookie file
            
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        files_to_remove = list(self._created_cookie_files)
        
        for file_path in files_to_remove:
            # Skip cached file if requested
            if keep_cached and file_path == str(self._cached_cookie_file):
                continue
            
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    cleaned += 1
                    if self.verbose:
                        self.logger.debug(f"Cleaned up cookie file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up cookie file {file_path}: {e}")
        
        # Clear the tracking set
        self._created_cookie_files.clear()
        
        return cleaned

    def __del__(self):
        """Cleanup on deletion - remove temporary cookie files."""
        try:
            self.cleanup_cookie_files(keep_cached=True)
        except:
            pass  # Ignore errors during cleanup
