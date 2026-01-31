"""
Video download service.

This module provides focused video downloading functionality,
separated from transcription and metadata concerns.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.base import ProcessingResult
from core.base_service import BaseService
from core.config import Config
from core.interfaces import IVideoDownloadService
from database.metadata import MetadataExtractor, MetadataManager
from infrastructure.storage import NASStorageAdapter, StorageAdapter
from modules.video.fallback_extractor import FallbackExtractor
from utils.cookie_manager import CookieManager
from utils.helpers import (
    MIN_VALID_FILE_SIZE,
    YOUTUBE_VIDEO_ID_PATTERN,
    get_file_hash,
    get_file_type,
    safe_filename,
)
from utils.ytdlp_auth_handler import YtDlpAuthHandler


class VideoDownloadService(BaseService, IVideoDownloadService):
    """
    Focused video download service.

    Handles only video downloading, without transcription or complex metadata processing.
    """

    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """Initialize the video download service."""
        # Initialize base service
        super().__init__(config, verbose, db_service)

        # Service-specific initialization
        self.supported_sites = [
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "dailymotion.com",
            "twitch.tv",
            "twitter.com",
            "instagram.com",
            "tiktok.com",
        ]

        # Initialize metadata management
        self.metadata_extractor = MetadataExtractor(config, verbose=verbose)
        self.metadata_manager = MetadataManager(config, verbose=verbose)

        # Initialize fallback extractor
        try:
            self.fallback_extractor = FallbackExtractor(config)
        except RuntimeError as exc:
            self.fallback_extractor = None
            self.logger.info(f"Fallback extractor disabled: {exc}")

        # Initialize cookie manager
        self.cookie_manager = CookieManager(config, verbose=verbose, logger=self.logger)
        # Initialize auth error handler
        self.auth_handler = YtDlpAuthHandler(self.cookie_manager, logger=self.logger)

        # Initialize storage adapter
        self.storage_adapter: StorageAdapter = NASStorageAdapter(
            config.video.temp_dir, logger=self.logger
        )

    def download_video(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> ProcessingResult:
        """
        Download a single video from URL.

        Args:
            url: URL to download from
            output_path: Optional output path
            **kwargs: Additional download options

        Returns:
            ProcessingResult with download details
        """
        # Analytics tracking will be handled by decorator/middleware

        # Extract metadata before download
        source_metadata = {}
        if "youtube.com" in url or "youtu.be" in url:
            source_metadata = self.metadata_extractor.extract_youtube_metadata(url)
            self.logger.info(
                f"Extracted YouTube metadata: {source_metadata.get('title', 'Unknown')}"
            )

        try:
            # Determine output path
            output_file = None
            if output_path is None:
                from core.config import get_default_data_dir

                repo_root = get_default_data_dir().parent
                output_dir = self.config.video.output_dir or (repo_root / "downloads")
            else:
                output_path = Path(output_path)
                if output_path.suffix:
                    output_file = output_path
                    output_dir = output_path.parent
                else:
                    output_dir = output_path

            output_dir.mkdir(parents=True, exist_ok=True)

            # Get job_id if provided (from use case layer) - for logging only
            job_id = kwargs.get("job_id")

            # Check if output is on remote storage and set up temp processing if needed
            is_remote = self.storage_adapter.is_remote(output_dir)

            temp_dir = None
            processing_path = output_dir

            if is_remote and job_id:
                # Create job-specific temp processing directory
                temp_dir = self.storage_adapter.get_temp_processing_dir(job_id)
                processing_path = temp_dir
                self.logger.info(f"Remote storage detected, using temp processing: {temp_dir}")
                self.logger.info(f"Video will be processed in: {processing_path}")

            # Download using yt-dlp
            downloaded_file = self._download_with_ytdlp(url, processing_path, **kwargs)

            if downloaded_file and downloaded_file.exists() and downloaded_file.stat().st_size >= MIN_VALID_FILE_SIZE:
                # Extract video metadata
                video_id = self._extract_video_id_from_url(url)

                # Prepare metadata for use case layer to handle persistence
                file_metadata = {
                    "file_path": str(downloaded_file),
                    "file_name": downloaded_file.name,
                    "file_size": downloaded_file.stat().st_size,
                    "file_hash": get_file_hash(downloaded_file),
                    "mime_type": get_file_type(downloaded_file),
                    "source_url": url,
                    "source_platform": (
                        "youtube"
                        if "youtube.com" in url or "youtu.be" in url
                        else "unknown"
                    ),
                    "source_id": video_id,
                    "title": source_metadata.get("title", downloaded_file.stem),
                    "description": source_metadata.get("description"),
                    "uploader": source_metadata.get("uploader"),
                    "uploader_id": source_metadata.get("uploader_id"),
                    "upload_date": source_metadata.get("upload_date"),
                    "view_count": source_metadata.get("view_count"),
                    "like_count": source_metadata.get("like_count"),
                    "duration": source_metadata.get("duration"),
                    "language": source_metadata.get("language"),
                }

                # If we used temp processing, move file to final destination
                if is_remote and temp_dir:
                    self.logger.info("Moving video to remote storage destination...")
                    final_file_path = output_file or (output_dir / downloaded_file.name)

                    if self.storage_adapter.move_file(downloaded_file, final_file_path):
                        self.logger.info(
                            f"Successfully moved video to NAS: {final_file_path}"
                        )

                        # Clean up temp directory
                        self.storage_adapter.cleanup_temp_dir(temp_dir)
                        self.logger.info(f"Cleaned up temp directory: {temp_dir}")

                        # Update metadata with final path
                        file_metadata["file_path"] = str(final_file_path)
                        file_metadata["file_name"] = final_file_path.name
                        file_metadata["nas_processing"] = True
                        file_metadata["original_path"] = str(downloaded_file)

                        metadata = {
                            **file_metadata,
                            "nas_processing": True,
                            "original_path": str(downloaded_file),
                        }
                        if job_id:
                            metadata["job_id"] = job_id

                        return ProcessingResult(
                            success=True,
                            message="Video downloaded and moved to remote storage successfully",
                            output_path=str(final_file_path),
                            metadata=metadata,
                        )
                    else:
                        self.logger.error("Failed to move video to remote storage")
                        metadata = {
                            **file_metadata,
                            "nas_processing": True,
                            "error": "Failed to move to remote storage",
                        }
                        if job_id:
                            metadata["job_id"] = job_id
                        return ProcessingResult(
                            success=False,
                            message="Video downloaded but failed to move to NAS",
                            errors=["Failed to move file to final destination"],
                            metadata=metadata,
                        )
                else:
                    # For local downloads
                    final_file_path = downloaded_file
                    if output_file and final_file_path.exists():
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        if final_file_path.resolve() != output_file.resolve():
                            final_file_path.replace(output_file)
                        # Update metadata with final path
                        file_metadata["file_path"] = str(output_file)
                        file_metadata["file_name"] = output_file.name
                        final_file_path = output_file

                    metadata = {
                        **file_metadata,
                        "nas_processing": False,
                    }
                    if job_id:
                        metadata["job_id"] = job_id
                    return ProcessingResult(
                        success=True,
                        message=f"Video downloaded successfully: {final_file_path.name}",
                        output_path=str(final_file_path),
                        metadata=metadata,
                    )
            else:
                metadata = {"error": "Download failed", "source_url": url}
                if job_id:
                    metadata["job_id"] = job_id
                return ProcessingResult(
                    success=False,
                    message="Video download failed",
                    errors=["No video file found after download"],
                    metadata=metadata,
                )

        except Exception as e:
            self.logger.error(f"Video download failed: {e}")
            return ProcessingResult(
                success=False, message=f"Video download failed: {e}", errors=[str(e)]
            )

    def _download_with_ytdlp(
        self, url: str, output_path: Path, **kwargs
    ) -> Optional[Path]:
        """Download video using yt-dlp.

        Automatically refreshes cookies and retries if download fails due to
        authentication issues with age-restricted content.
        """
        # Build yt-dlp options
        ydl_opts = self._build_ydl_opts(output_path, **kwargs)
        output_path.mkdir(parents=True, exist_ok=True)

        import yt_dlp

        def download_operation() -> Optional[Path]:
            """
            Inner function for download operation that can be retried.
            
            Returns:
                Path to downloaded file if successful, None otherwise.
            """
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = self._resolve_downloaded_path(ydl, info)
                if (
                    downloaded_file
                    and downloaded_file.exists()
                    and downloaded_file.stat().st_size >= MIN_VALID_FILE_SIZE
                ):
                    return downloaded_file

            # Only fallback to finding latest if we can't resolve the path
            # But validate it matches the expected video ID to avoid picking up old files
            return self._validate_fallback_file(output_path, url)

        try:
            # Try download with automatic auth retry
            result = self.auth_handler.execute_with_auth_retry(
                download_operation,
                operation_name="video download",
                ydl_opts=ydl_opts,
            )
            return result
        except Exception as e:
            self.logger.error(f"yt-dlp download failed: {e}")
            return self._validate_fallback_file(output_path, url)


    def _resolve_downloaded_path(
        self, ydl: Any, info: Optional[Dict[str, Any]]
    ) -> Optional[Path]:
        """Resolve downloaded file path from yt-dlp info.
        
        Handles cases where prepare_filename() might not return the correct path,
        such as when video and audio are merged, or when the file path doesn't exist yet.
        """
        if not info:
            return None

        if isinstance(info, dict) and info.get("_type") == "playlist":
            entries = [entry for entry in info.get("entries", []) if entry]
            if not entries:
                return None
            info = entries[0]

        if not isinstance(info, dict):
            return None

        try:
            # Try to get the filename from yt-dlp
            prepared_path = ydl.prepare_filename(info)
            file_path = Path(prepared_path)
            
            # Check if the file exists and is valid
            if file_path.exists() and file_path.stat().st_size >= MIN_VALID_FILE_SIZE:
                return file_path
            
            # If prepare_filename() path doesn't exist, try to find the actual downloaded file
            # This handles cases where video+audio are merged or file is in a different location
            output_dir = file_path.parent
            if output_dir.exists():
                # Look for files matching the expected pattern (title + video ID)
                video_id = info.get("id")
                
                if video_id:
                    # Try to find file with video ID in name
                    for ext in self.config.video_extensions:
                        pattern = f"*{video_id}*{ext}"
                        matches = list(output_dir.glob(pattern))
                        if matches:
                            # Return the most recently modified matching file
                            valid_files = [
                                f
                                for f in matches
                                if f.is_file() and f.stat().st_size >= MIN_VALID_FILE_SIZE
                            ]
                            if valid_files:
                                return max(valid_files, key=lambda p: p.stat().st_mtime)
                
                # Fallback: find most recently modified video file in output directory
                # This is a last resort if we can't match by video ID
                candidates = [
                    file
                    for ext in self.config.video_extensions
                    for file in output_dir.glob(f"*{ext}")
                ]
                
                valid_candidates = [
                    f
                    for f in candidates
                    if f.is_file() and f.stat().st_size >= MIN_VALID_FILE_SIZE
                ]
                if valid_candidates:
                    # Return most recent file, but log a warning
                    latest = max(valid_candidates, key=lambda p: p.stat().st_mtime)
                    self.logger.warning(
                        f"Could not resolve exact file path, using most recent file: {latest.name}"
                    )
                    return latest
            
        except Exception as e:
            self.logger.warning(f"Error resolving downloaded path: {e}")
            return None
        
        return None

    def _find_latest_download(self, output_path: Path) -> Optional[Path]:
        """Find the most recently modified downloaded video file."""
        candidates: List[Path] = []
        for ext in self.config.video_extensions:
            candidates.extend(output_path.glob(f"*{ext}"))

        candidates = [path for path in candidates if path.is_file()]
        if not candidates:
            return None

        return max(candidates, key=lambda path: path.stat().st_mtime)

    def _validate_fallback_file(self, output_path: Path, url: str) -> Optional[Path]:
        """Find latest download and validate it matches the expected video ID."""
        fallback_file = self._find_latest_download(output_path)
        if not fallback_file:
            return None

        # Extract video ID from URL to validate
        import re

        video_id_match = re.search(YOUTUBE_VIDEO_ID_PATTERN, url)
        if video_id_match:
            expected_id = video_id_match.group(1)
            # Check if the filename contains the expected video ID
            if expected_id in fallback_file.name:
                return fallback_file
            else:
                self.logger.warning(
                    f"Found file {fallback_file.name} but it doesn't match expected video ID {expected_id}. "
                    "Download may have failed."
                )
                return None
        # If we can't extract video ID, return the file anyway (for non-YouTube URLs)
        return fallback_file


    def _build_ydl_opts(self, output_path: Path, **kwargs) -> Dict[str, Any]:
        """Build yt-dlp options."""
        # Output template
        output_template = str(output_path / "%(title)s [%(id)s].%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "format": self._get_format_selector(
                kwargs.get("quality", self.config.video.quality),
                kwargs.get("format", self.config.video.default_format),
            ),
            "writeinfojson": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "no_warnings": not self.verbose,
            "quiet": not self.verbose,
            # Add fallback formats for YouTube SABR streaming issues
            "format_sort": ["res", "ext", "codec", "br", "asr"],
            # Try to use available formats even if preferred format fails
            "ignoreerrors": False,
        }

        # Automatically try to use cookies from browser for age-restricted content
        cookies_browser = self.cookie_manager.get_browser_list()
        if cookies_browser:
            ydl_opts["cookies_from_browser"] = cookies_browser
            if self.verbose:
                self.logger.info(
                    f"Attempting to use cookies from browsers: {cookies_browser}"
                )

        if self.verbose:
            ydl_opts["verbose"] = True

        return ydl_opts

    def _get_format_selector(self, quality: str, format: str) -> str:
        """Get format selector for yt-dlp with fallbacks for YouTube issues."""
        from utils.format_selector import get_format_selector

        return get_format_selector(quality, format)


    def _extract_video_id_from_url(self, url: str) -> str:
        """
        Extract video ID from URL.
        
        Uses regex pattern for consistent extraction across all YouTube URL formats.
        """
        import re
        
        video_id_match = re.search(YOUTUBE_VIDEO_ID_PATTERN, url)
        if video_id_match:
            return video_id_match.group(1)
        return "unknown"


    def _check_existing_video(self, file_path: Path, url: str) -> Dict[str, Any]:
        """Check if video file exists and has subtitles."""
        result = {
            "exists": False,
            "has_subtitles": False,
            "should_overwrite": True,
            "reason": "",
        }

        if not file_path.exists():
            result["reason"] = f"File {file_path} does not exist"
            return result

        result["exists"] = True

        # Check for subtitles using TranscriptionService
        from modules.video.services.transcription_service import TranscriptionService

        transcription_service = TranscriptionService(
            self.config, verbose=self.verbose, db_service=self.db_factory
        )
        has_subtitles = transcription_service.has_whisper_subtitles(file_path)
        result["has_subtitles"] = has_subtitles

        if has_subtitles:
            result["should_overwrite"] = False
            result["reason"] = f"File {file_path} exists with WhisperAI subtitles"
        else:
            result["should_overwrite"] = True
            result["reason"] = f"File {file_path} exists without subtitles"

        return result

