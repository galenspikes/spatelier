"""
Playlist service.

This module provides focused playlist management functionality.
"""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.base import ProcessingResult
from core.base_service import BaseService
from core.config import Config
from core.interfaces import IPlaylistService
from infrastructure.storage import NASStorageAdapter, StorageAdapter
from utils.cookie_manager import CookieManager
from utils.helpers import YOUTUBE_VIDEO_ID_FILENAME_PATTERN


class PlaylistService(BaseService, IPlaylistService):
    """
    Focused playlist service.

    Handles playlist downloading and management without transcription concerns.
    """

    def __init__(
        self,
        config: Config,
        verbose: bool = False,
        db_service=None,
        metadata_extractor=None,
        metadata_manager=None,
    ):
        """
        Initialize the playlist service.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            db_service: Optional database service instance
            metadata_extractor: Optional MetadataExtractor (injected dependency)
            metadata_manager: Optional MetadataManager (injected dependency)
        """
        # Initialize base service
        super().__init__(config, verbose, db_service)

        # Initialize cookie manager
        self.cookie_manager = CookieManager(config, verbose=verbose, logger=self.logger)

        # Use injected dependencies or create if not provided
        if metadata_extractor is None or metadata_manager is None:
            from database.metadata import MetadataExtractor, MetadataManager

            self.metadata_extractor = (
                metadata_extractor
                if metadata_extractor
                else MetadataExtractor(config, verbose=verbose)
            )
            self.metadata_manager = (
                metadata_manager
                if metadata_manager
                else MetadataManager(config, verbose=verbose)
            )
        else:
            self.metadata_extractor = metadata_extractor
            self.metadata_manager = metadata_manager

        # Initialize storage adapter
        self.storage_adapter: StorageAdapter = NASStorageAdapter(
            config.video.temp_dir, logger=self.logger
        )

    def download_playlist(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> ProcessingResult:
        """
        Download playlist without transcription.

        Args:
            url: Playlist URL to download
            output_path: Optional output directory (will create playlist folder)
            **kwargs: Additional download options

        Returns:
            Dictionary with download results
        """
        try:
            # Get playlist metadata first
            playlist_info = self._get_playlist_info(url)
            if not playlist_info:
                return ProcessingResult(
                    success=False,
                    message="Failed to get playlist information",
                    errors=["Could not extract playlist metadata"],
                )

            # Create playlist folder
            playlist_name = self._sanitize_filename(
                playlist_info.get("title", "Unknown Playlist")
            )
            playlist_id = playlist_info.get("id", "unknown")
            folder_name = f"{playlist_name} [{playlist_id}]"

            if output_path:
                playlist_dir = Path(output_path) / folder_name
            else:
                from core.config import get_default_data_dir

                repo_root = get_default_data_dir().parent
                playlist_dir = repo_root / "downloads" / folder_name

            # Check if output is on remote storage and set up temp processing if needed
            is_remote = self.storage_adapter.is_remote(playlist_dir)

            if is_remote and not self.storage_adapter.can_write_to(playlist_dir):
                self.logger.warning(
                    f"Remote path not writable: {playlist_dir}. "
                    "Check NAS mount and permissions (NFS/SMB from Mac can have permission issues)."
                )
                return ProcessingResult(
                    success=False,
                    message="Remote storage path is not writable",
                    errors=["Cannot write to remote destination; check mount and permissions"],
                    metadata={"output_path": str(playlist_dir), "url": url},
                )

            # Get job_id if provided (from use case layer) - for temp directory creation
            job_id = kwargs.get("job_id")

            temp_dir = None
            processing_dir = playlist_dir

            if is_remote and job_id:
                # Create job-specific temp processing directory with playlist folder
                temp_dir = self.storage_adapter.get_temp_processing_dir(job_id)
                processing_dir = temp_dir / folder_name
                self.logger.info(
                    f"Remote storage detected for playlist, using temp processing: {temp_dir}"
                )
                self.logger.info(f"Playlist will be processed in: {processing_dir}")

            processing_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Downloading playlist to: {playlist_dir}")

            # Download playlist using yt-dlp Python package
            self.logger.info(f"Downloading playlist from: {url}")

            # Build yt-dlp options
            ydl_opts = self._build_playlist_ydl_opts(processing_dir, **kwargs)

            # Execute download
            import yt_dlp

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Check if download was successful by looking for files
            downloaded_videos = self._find_playlist_videos(processing_dir)
            max_videos = kwargs.get("max_videos")
            if (
                isinstance(max_videos, int)
                and max_videos > 0
                and len(downloaded_videos) > max_videos
            ):
                downloaded_videos = sorted(
                    downloaded_videos,
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )[:max_videos]
                self.logger.info(
                    f"Limiting processed videos to most recent {max_videos}"
                )

            if downloaded_videos:
                self.logger.info(
                    f"Processing {len(downloaded_videos)} downloaded videos from playlist"
                )

                # Process each video (extract metadata for use case layer)
                successful_downloads = []
                failed_downloads = []

                for position, video_path in enumerate(downloaded_videos, 1):
                    try:
                        # Extract video metadata
                        video_id = self._extract_video_id_from_path(video_path)

                        # Get source metadata for this video
                        source_metadata = (
                            self.metadata_extractor.extract_youtube_metadata(
                                f"https://www.youtube.com/watch?v={video_id}"
                            )
                        )

                        # Prepare metadata for use case layer to handle persistence
                        from utils.helpers import get_file_hash, get_file_type

                        video_metadata = {
                            "file_path": str(video_path),
                            "file_name": video_path.name,
                            "file_size": video_path.stat().st_size,
                            "file_hash": get_file_hash(video_path),
                            "mime_type": get_file_type(video_path),
                            "source_url": f"https://www.youtube.com/watch?v={video_id}",
                            "source_platform": "youtube",
                            "source_id": video_id,
                            "title": source_metadata.get("title", video_path.stem),
                            "description": source_metadata.get("description"),
                            "uploader": source_metadata.get("uploader"),
                            "uploader_id": source_metadata.get("uploader_id"),
                            "upload_date": source_metadata.get("upload_date"),
                            "view_count": source_metadata.get("view_count"),
                            "like_count": source_metadata.get("like_count"),
                            "duration": source_metadata.get("duration"),
                            "language": source_metadata.get("language"),
                            "position": position,
                        }

                        successful_downloads.append({
                            "path": str(video_path),
                            "metadata": video_metadata,
                        })

                    except Exception as e:
                        self.logger.error(f"Failed to process {video_path.name}: {e}")
                        failed_downloads.append(str(video_path))

                # If we used temp processing, move entire playlist directory to final destination
                if is_remote and temp_dir:
                    self.logger.info("Moving playlist directory to NAS destination...")

                    # Move the entire playlist directory from temp to final destination
                    if self.storage_adapter.move_file(processing_dir, playlist_dir):
                        self.logger.info(
                            f"Successfully moved playlist directory to NAS: {playlist_dir}"
                        )

                        # Clean up temp directory after successful move
                        self.storage_adapter.cleanup_temp_dir(temp_dir)
                        self.logger.info(f"Cleaned up temp directory: {temp_dir}")
                    else:
                        self.logger.error("Failed to move playlist directory to NAS")
                        metadata = {
                            "playlist_title": playlist_name,
                            "playlist_id": playlist_id,
                            "error": "Failed to move playlist to NAS",
                        }
                        if job_id:
                            metadata["job_id"] = job_id
                        return ProcessingResult.error_result(
                            message="Playlist downloaded but failed to move to NAS",
                            errors=["Failed to move playlist directory to final destination"],
                            metadata=metadata,
                        )

                # Prepare metadata for use case layer
                metadata = {
                    "playlist_title": playlist_name,
                    "playlist_id": playlist_id,
                    "description": playlist_info.get("description"),
                    "uploader": playlist_info.get("uploader"),
                    "uploader_id": playlist_info.get("uploader_id"),
                    "playlist_count": playlist_info.get("playlist_count"),
                    "view_count": playlist_info.get("view_count"),
                    "thumbnail": playlist_info.get("thumbnail"),
                    "total_videos": len(downloaded_videos),
                    "successful_downloads": len(successful_downloads),
                    "failed_downloads": len(failed_downloads),
                    "downloaded_videos": successful_downloads,
                    "nas_processing": is_remote,
                    "video_count": len(successful_downloads),
                }
                if job_id:
                    metadata["job_id"] = job_id

                return ProcessingResult.success_result(
                    message=f"Playlist downloaded successfully: {len(successful_downloads)} videos",
                    output_path=str(playlist_dir),
                    metadata=metadata,
                )
            else:
                return ProcessingResult.error_result(
                    message="Playlist download completed but no videos found",
                    errors=["No video files found in download directory"],
                )

        except Exception as e:
            self.logger.error(f"Playlist download failed: {e}")
            return ProcessingResult.error_result(
                message=f"Playlist download failed: {e}", errors=[str(e)]
            )

    def _get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get playlist information."""
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info

        except Exception as e:
            self.logger.error(f"Failed to get playlist info: {e}")
            return None


    def _build_playlist_ydl_opts(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Build yt-dlp options for playlist download."""
        # Output template for playlist
        output_template = str(output_dir / "%(title)s [%(id)s].%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "format": self._get_format_selector(
                kwargs.get("quality", self.config.video.quality),
                kwargs.get("format", self.config.video.default_format),
            ),
            "writeinfojson": False,  # Don't write info files
            "writesubtitles": False,  # We handle subtitles separately
            "writeautomaticsub": False,
            "ignoreerrors": True,  # Continue on individual video errors
            "no_warnings": not self.verbose,
            "quiet": not self.verbose,
            "extract_flat": False,  # We want to download, not just extract info
        }

        max_videos = kwargs.get("max_videos")
        if isinstance(max_videos, int) and max_videos > 0:
            ydl_opts["playlistend"] = max_videos

        # Automatically try to use cookies from browser for age-restricted content
        cookies_browser = self.cookie_manager.get_browser_list()
        if cookies_browser:
            ydl_opts["cookies_from_browser"] = cookies_browser

        # Additional options
        if self.verbose:
            ydl_opts["verbose"] = True

        return ydl_opts

    def _get_format_selector(self, quality: str, format: str) -> str:
        """Get format selector for yt-dlp with fallbacks for YouTube issues."""
        from utils.format_selector import get_format_selector

        return get_format_selector(quality, format)

    def _find_playlist_videos(self, directory: Path) -> List[Path]:
        """Find downloaded video files in playlist directory."""
        return [
            file
            for ext in self.config.video_extensions
            for file in directory.rglob(f"*{ext}")
        ]

    def _extract_video_id_from_path(self, video_path: Path) -> str:
        """Extract video ID from file path."""
        # Look for [video_id] pattern in filename
        match = re.search(YOUTUBE_VIDEO_ID_FILENAME_PATTERN, video_path.name)
        if match:
            return match.group(1)
        return "unknown"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Limit length
        max_length = self.config.max_filename_length
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename


    def get_playlist_progress(
        self, playlist_id: str, repositories=None, transcription_service=None
    ) -> Dict[str, int]:
        """
        Get playlist download progress.

        Args:
            playlist_id: Playlist ID
            repositories: Optional repository container (for use case layer to pass)
            transcription_service: Optional TranscriptionService (for use case layer to pass)

        Returns:
            Dictionary with progress information (total, completed, failed, remaining)
        """
        try:
            # Repositories passed from use case layer, not accessed via self.repos
            if not repositories:
                self.logger.warning("No repositories provided to get_playlist_progress")
                return {"total": 0, "completed": 0, "failed": 0, "remaining": 0}

            # Get playlist from database
            playlist = repositories.playlists.get_by_playlist_id(playlist_id)
            if not playlist:
                return {"total": 0, "completed": 0, "failed": 0, "remaining": 0}

            # Get playlist videos
            playlist_videos = repositories.playlist_videos.get_by_playlist_id(playlist.id)
            total = len(playlist_videos)

            completed = 0
            failed = 0

            # TranscriptionService passed from use case layer
            if not transcription_service:
                # Import here to avoid circular dependency
                from modules.video.services.transcription_service import TranscriptionService

                transcription_service = TranscriptionService(
                    self.config, verbose=self.verbose, db_service=self.db_factory
                )

            for pv in playlist_videos:
                media_file = repositories.media.get_by_id(pv.media_file_id)
                if media_file and media_file.file_path:
                    file_path = Path(media_file.file_path)
                    if file_path.exists():
                        # Check if has transcription using TranscriptionService
                        if transcription_service.has_transcription(media_file):
                            completed += 1
                        else:
                            failed += 1
                    else:
                        failed += 1
                else:
                    failed += 1

            remaining = total - completed - failed

            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "remaining": remaining,
            }

        except Exception as e:
            self.logger.error(f"Failed to get playlist progress: {e}")
            return {"total": 0, "completed": 0, "failed": 0, "remaining": 0}

    def get_failed_videos(
        self, playlist_id: str, repositories=None, transcription_service=None
    ) -> List[Dict[str, Any]]:
        """
        Get failed videos from playlist.

        Args:
            playlist_id: Playlist ID
            repositories: Optional repository container (for use case layer to pass)
            transcription_service: Optional TranscriptionService (for use case layer to pass)

        Returns:
            List of failed videos with position, title, and reason
        """
        try:
            # Repositories passed from use case layer, not accessed via self.repos
            if not repositories:
                self.logger.warning("No repositories provided to get_failed_videos")
                return []

            # Get playlist from database
            playlist = repositories.playlists.get_by_playlist_id(playlist_id)
            if not playlist:
                return []

            # Get playlist videos
            playlist_videos = repositories.playlist_videos.get_by_playlist_id(playlist.id)
            failed_videos = []

            # TranscriptionService passed from use case layer
            if not transcription_service:
                # Import here to avoid circular dependency
                from modules.video.services.transcription_service import TranscriptionService

                transcription_service = TranscriptionService(
                    self.config, verbose=self.verbose, db_service=self.db_factory
                )

            for pv in playlist_videos:
                media_file = repositories.media.get_by_id(pv.media_file_id)
                if media_file and media_file.file_path:
                    file_path = Path(media_file.file_path)
                    if not file_path.exists():
                        failed_videos.append(
                            {
                                "position": pv.position,
                                "video_title": pv.video_title or "Unknown",
                                "reason": "File missing",
                            }
                        )
                    elif not transcription_service.has_transcription(media_file):
                        failed_videos.append(
                            {
                                "position": pv.position,
                                "video_title": pv.video_title or "Unknown",
                                "reason": "No transcription",
                            }
                        )
                else:
                    failed_videos.append(
                        {
                            "position": pv.position,
                            "video_title": pv.video_title or "Unknown",
                            "reason": "Media file not found",
                        }
                    )

            return failed_videos

        except Exception as e:
            self.logger.error(f"Failed to get failed videos: {e}")
            return []

    def download_playlist_with_transcription(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        continue_download: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Download playlist with transcription support.

        Args:
            url: Playlist URL
            output_path: Optional output directory
            continue_download: Whether to continue from previous downloads
            **kwargs: Additional download options

        Returns:
            Dictionary with download results
        """
        try:
            # Download playlist first
            result = self.download_playlist(url, output_path, **kwargs)

            # Note: Transcription for playlists is handled at the use case level
            # (DownloadPlaylistUseCase) rather than in the service layer.
            # This method exists to satisfy the interface contract.
            return result

        except Exception as e:
            self.logger.error(f"Playlist download with transcription failed: {e}")
            return {
                "success": False,
                "message": f"Playlist download failed: {e}",
                "errors": [str(e)],
            }
