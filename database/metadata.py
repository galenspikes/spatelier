"""
Metadata extraction and management.

This module provides functionality for extracting and managing video metadata,
especially from YouTube and other platforms.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import ffmpeg

from core.config import Config
from core.logger import get_logger
from database.models import DownloadSource, MediaFile
from database.repository import MediaFileRepository


class MetadataExtractor:
    """
    Metadata extractor for various media types and platforms.

    Supports YouTube, Vimeo, and other platforms using yt-dlp for metadata extraction.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize metadata extractor.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("MetadataExtractor", verbose=verbose)

    def extract_youtube_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from YouTube URL using yt-dlp.

        Args:
            url: YouTube URL

        Returns:
            Dictionary with extracted metadata
        """
        try:
            self.logger.info(f"Extracting YouTube metadata from: {url}")

            # Use yt-dlp Python package to get metadata without downloading
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_playlist": True,
            }

            # Automatically try to use cookies from browser for age-restricted content
            # Try multiple browsers in order - yt-dlp will use the first available one
            # On macOS, Chrome is more reliable than Safari for cookie extraction
            import platform

            system = platform.system().lower()
            if system == "darwin":  # macOS - prioritize Chrome over Safari
                browsers = ("chrome", "safari", "firefox", "edge")
            else:
                browsers = ("chrome", "firefox", "safari", "edge")
            ydl_opts["cookies_from_browser"] = browsers
            if self.verbose:
                self.logger.info(f"Attempting to use cookies from browsers: {browsers}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                metadata = ydl.extract_info(url, download=False)
                return self._parse_youtube_metadata(metadata)
        except Exception as e:
            error_msg = str(e)
            # Check if this is a cookie/authentication error
            if any(
                keyword in error_msg.lower()
                for keyword in ["sign in", "age", "cookies", "authentication"]
            ):
                self.logger.warning(
                    "Metadata extraction failed due to authentication - attempting to refresh cookies..."
                )
                # Try to refresh cookies and get cookie file
                cookie_file = self._refresh_youtube_cookies()
                if cookie_file:
                    self.logger.info(
                        "Retrying metadata extraction with refreshed cookies..."
                    )
                    # Retry the extraction with cookie file
                    try:
                        # Use the cookie file instead of cookies_from_browser
                        ydl_opts["cookies"] = cookie_file
                        if "cookies_from_browser" in ydl_opts:
                            del ydl_opts["cookies_from_browser"]

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            metadata = ydl.extract_info(url, download=False)

                        # Clean up cookie file
                        import os

                        try:
                            os.unlink(cookie_file)
                        except:
                            pass

                        return self._parse_youtube_metadata(metadata)
                    except Exception as retry_error:
                        # Clean up cookie file
                        import os

                        try:
                            os.unlink(cookie_file)
                        except:
                            pass
                        self.logger.error(
                            f"Metadata extraction failed after cookie refresh: {retry_error}"
                        )
                        return {}
                else:
                    self.logger.error(f"Metadata extraction failed: {e}")
                    return {}
            else:
                self.logger.error(f"Metadata extraction failed: {e}")
                return {}

    def _refresh_youtube_cookies(self) -> Optional[str]:
        """Refresh YouTube cookies by visiting YouTube and extracting fresh cookies.

        Uses Playwright to launch Chrome with the user's profile, visit YouTube,
        extract the cookies, and save them to a temporary file for yt-dlp to use.

        Returns:
            Path to cookie file if successful, None otherwise
        """
        try:
            import os
            import platform
            import tempfile

            from playwright.sync_api import sync_playwright

            system = platform.system().lower()
            if system != "darwin":
                # Only implemented for macOS for now
                return None

            # Get Chrome user data directory
            chrome_user_data = os.path.expanduser(
                "~/Library/Application Support/Google/Chrome"
            )

            if not os.path.exists(chrome_user_data):
                return None

            self.logger.info(
                "Refreshing YouTube cookies by visiting YouTube in Chrome..."
            )

            with sync_playwright() as p:
                # Launch Chrome with user's profile
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=chrome_user_data,
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )

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
                youtube_cookies = [
                    c
                    for c in cookies
                    if "youtube.com" in c.get("domain", "")
                    or ".youtube.com" in c.get("domain", "")
                ]

                if not youtube_cookies:
                    self.logger.warning("No YouTube cookies found after refresh")
                    return None

                # Save cookies to Netscape format file for yt-dlp
                cookie_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                )
                cookie_file.write("# Netscape HTTP Cookie File\n")
                cookie_file.write("# This file was generated by spatelier\n\n")

                for cookie in youtube_cookies:
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
                self.logger.info(
                    f"YouTube cookies refreshed and saved to: {cookie_file.name}"
                )
                return cookie_file.name

        except Exception as e:
            self.logger.warning(f"Failed to refresh cookies automatically: {e}")
            return None

    def extract_file_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract metadata from local media file using ffprobe.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with extracted metadata
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {}

            self.logger.info(f"Extracting file metadata from: {file_path}")

            # Use ffmpeg-python to get technical metadata
            probe_data = ffmpeg.probe(str(file_path))
            return self._parse_ffprobe_metadata(probe_data)

        except ffmpeg.Error as e:
            self.logger.error(f"ffmpeg probe failed: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"File metadata extraction failed: {e}")
            return {}

    def _parse_youtube_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse YouTube metadata from yt-dlp output.

        Args:
            metadata: Raw metadata from yt-dlp

        Returns:
            Parsed metadata dictionary
        """
        parsed = {}

        # Basic information
        parsed["title"] = metadata.get("title", "")
        parsed["description"] = metadata.get("description", "")
        parsed["uploader"] = metadata.get("uploader", "")
        parsed["uploader_id"] = metadata.get("uploader_id", "")
        parsed["source_url"] = metadata.get("webpage_url", "")
        parsed["source_platform"] = "youtube"
        parsed["source_id"] = metadata.get("id", "")

        # Dates
        if metadata.get("upload_date"):
            try:
                upload_date = datetime.strptime(metadata["upload_date"], "%Y%m%d")
                parsed["upload_date"] = upload_date
            except ValueError:
                pass

        # Statistics
        parsed["view_count"] = metadata.get("view_count")
        parsed["like_count"] = metadata.get("like_count")
        parsed["dislike_count"] = metadata.get("dislike_count")
        parsed["comment_count"] = metadata.get("comment_count")

        # Technical information
        parsed["duration"] = metadata.get("duration")
        parsed["age_limit"] = metadata.get("age_limit")
        parsed["language"] = metadata.get("language")

        # Tags and categories
        if metadata.get("tags"):
            parsed["tags"] = json.dumps(metadata["tags"])

        if metadata.get("categories"):
            parsed["categories"] = json.dumps(metadata["categories"])

        # Thumbnails
        if metadata.get("thumbnail"):
            parsed["thumbnail_url"] = metadata["thumbnail"]

        # Video streams information
        if metadata.get("formats"):
            video_streams = [
                f for f in metadata["formats"] if f.get("vcodec") != "none"
            ]
            if video_streams:
                # Get best quality stream info
                best_stream = max(video_streams, key=lambda x: x.get("height", 0) or 0)
                parsed["width"] = best_stream.get("width")
                parsed["height"] = best_stream.get("height")
                parsed["fps"] = best_stream.get("fps")
                parsed["video_codec"] = best_stream.get("vcodec")
                parsed["audio_codec"] = best_stream.get("acodec")
                parsed["bitrate"] = best_stream.get("tbr")

        return parsed

    def _parse_ffprobe_metadata(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse ffprobe metadata from media file.

        Args:
            probe_data: Raw ffprobe output

        Returns:
            Parsed metadata dictionary
        """
        parsed = {}

        # Format information
        format_info = probe_data.get("format", {})
        parsed["duration"] = float(format_info.get("duration", 0))
        parsed["bitrate"] = int(format_info.get("bit_rate", 0))

        # Stream information
        streams = probe_data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        # Video stream info
        if video_streams:
            video_stream = video_streams[0]  # Primary video stream
            parsed["width"] = video_stream.get("width")
            parsed["height"] = video_stream.get("height")
            parsed["fps"] = self._parse_fps(video_stream.get("r_frame_rate", ""))
            parsed["video_codec"] = video_stream.get("codec_name")
            parsed["aspect_ratio"] = video_stream.get("display_aspect_ratio")
            parsed["color_space"] = video_stream.get("color_space")

        # Audio stream info
        if audio_streams:
            audio_stream = audio_streams[0]  # Primary audio stream
            parsed["audio_codec"] = audio_stream.get("codec_name")
            parsed["sample_rate"] = audio_stream.get("sample_rate")
            parsed["channels"] = audio_stream.get("channels")

        return parsed

    def _parse_fps(self, fps_string: str) -> Optional[float]:
        """Parse FPS from fraction string like '30/1'."""
        try:
            if "/" in fps_string:
                numerator, denominator = fps_string.split("/")
                return float(numerator) / float(denominator)
            else:
                return float(fps_string)
        except (ValueError, ZeroDivisionError):
            return None

    def update_media_file_metadata(
        self,
        media_file: MediaFile,
        metadata: Dict[str, Any],
        repository: MediaFileRepository,
    ) -> MediaFile:
        """
        Update media file with extracted metadata.

        Args:
            media_file: MediaFile instance to update
            metadata: Extracted metadata dictionary
            repository: MediaFileRepository instance

        Returns:
            Updated MediaFile instance
        """
        try:
            # Update fields that exist in metadata
            for field, value in metadata.items():
                if hasattr(media_file, field) and value is not None:
                    setattr(media_file, field, value)

            # Commit changes
            repository.session.commit()
            repository.session.refresh(media_file)

            self.logger.info(f"Updated metadata for media file: {media_file.id}")
            return media_file

        except Exception as e:
            self.logger.error(f"Failed to update media file metadata: {e}")
            repository.session.rollback()
            raise


class MetadataManager:
    """
    High-level metadata management.

    Provides convenient methods for metadata extraction and storage.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize metadata manager.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("MetadataManager", verbose=verbose)

        self.extractor = MetadataExtractor(config, verbose=verbose)

    def enrich_media_file(
        self,
        media_file: MediaFile,
        repository: MediaFileRepository,
        extract_source_metadata: bool = True,
    ) -> MediaFile:
        """
        Enrich media file with metadata from various sources.

        Args:
            media_file: MediaFile to enrich
            repository: MediaFileRepository instance
            extract_source_metadata: Whether to extract source metadata (YouTube, etc.)

        Returns:
            Enriched MediaFile instance
        """
        try:
            # Extract file metadata
            file_metadata = self.extractor.extract_file_metadata(media_file.file_path)
            self.extractor.update_media_file_metadata(
                media_file, file_metadata, repository
            )

            # Extract source metadata if available
            if extract_source_metadata and media_file.source_url:
                if (
                    "youtube.com" in media_file.source_url
                    or "youtu.be" in media_file.source_url
                ):
                    youtube_metadata = self.extractor.extract_youtube_metadata(
                        media_file.source_url
                    )
                    self.extractor.update_media_file_metadata(
                        media_file, youtube_metadata, repository
                    )

            self.logger.info(f"Enriched media file {media_file.id} with metadata")
            return media_file

        except Exception as e:
            self.logger.error(f"Failed to enrich media file: {e}")
            return media_file

    def batch_enrich_media_files(
        self,
        repository: MediaFileRepository,
        limit: int = 100,
        media_type: Optional[str] = None,
    ) -> List[MediaFile]:
        """
        Batch enrich multiple media files with metadata.

        Args:
            repository: MediaFileRepository instance
            limit: Maximum number of files to process
            media_type: Filter by media type

        Returns:
            List of enriched MediaFile instances
        """
        try:
            # Get media files to enrich
            query = repository.session.query(MediaFile)
            if media_type:
                query = query.filter(MediaFile.media_type == media_type)

            media_files = query.limit(limit).all()

            enriched_files = []
            for media_file in media_files:
                try:
                    enriched_file = self.enrich_media_file(media_file, repository)
                    enriched_files.append(enriched_file)
                except Exception as e:
                    self.logger.error(f"Failed to enrich file {media_file.id}: {e}")
                    continue

            self.logger.info(f"Batch enriched {len(enriched_files)} media files")
            return enriched_files

        except Exception as e:
            self.logger.error(f"Batch enrichment failed: {e}")
            return []
