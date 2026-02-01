"""
Download playlist use case.

Orchestrates the download of a playlist, coordinating between
playlist service, metadata service, and tracking.
"""

from pathlib import Path
from typing import List, Optional

from spatelier.core.base import ProcessingResult
from spatelier.domain.models.playlist import Playlist
from spatelier.domain.services.job_manager import JobManager
from spatelier.domain.services.media_file_tracker import MediaFileTracker
from spatelier.domain.services.playlist_tracker import PlaylistTracker


class DownloadPlaylistUseCase:
    """
    Use case for downloading a playlist.

    Orchestrates:
    - Playlist downloading
    - Video tracking
    - Playlist tracking
    - Job management
    """

    def __init__(
        self,
        playlist_service,
        metadata_service,
        repositories,
        logger=None,
    ):
        """
        Initialize use case.

        Args:
            playlist_service: Playlist service
            metadata_service: Metadata service
            repositories: Repository container
            logger: Optional logger
        """
        self.playlist_service = playlist_service
        self.metadata_service = metadata_service
        self.repos = repositories
        self.logger = logger

        # Initialize domain services
        self.job_manager = JobManager(repositories, logger=logger)
        self.media_tracker = MediaFileTracker(repositories, logger=logger)
        self.playlist_tracker = PlaylistTracker(repositories, logger=logger)

    def execute(
        self,
        url: str,
        output_path: Optional[Path] = None,
        create_job: bool = True,
        **kwargs,
    ) -> ProcessingResult:
        """
        Execute the download playlist use case.

        Args:
            url: Playlist URL
            output_path: Optional output path
            create_job: Whether to create a processing job (default: True)
            **kwargs: Additional download options

        Returns:
            ProcessingResult with download details
        """
        # Create processing job if requested
        job_id = None
        if create_job:
            job_id = self.job_manager.create_job(
                job_type="download_playlist",
                input_path=url,
                output_path=str(output_path) if output_path else "",
                parameters=kwargs,
            )
            if job_id:
                kwargs["job_id"] = job_id  # Pass job_id to playlist service
                # Mark job as processing
                self.job_manager.update_job_status(job_id, "processing")

        # Download playlist
        result = self.playlist_service.download_playlist(url, output_path, **kwargs)

        if result.success and result.metadata:
            # Get metadata from result
            playlist_metadata = result.metadata
            playlist_id = playlist_metadata.get("playlist_id")
            playlist_title = playlist_metadata.get("playlist_title")
            downloaded_videos = playlist_metadata.get("downloaded_videos", [])

            if playlist_id:
                # Track playlist
                playlist_db_id = self.playlist_tracker.track_playlist(
                    playlist_id=playlist_id,
                    url=url,
                    metadata={
                        "title": playlist_title,
                        "description": playlist_metadata.get("description"),
                        "uploader": playlist_metadata.get("uploader"),
                        "uploader_id": playlist_metadata.get("uploader_id"),
                        "playlist_count": playlist_metadata.get("video_count"),
                        "view_count": playlist_metadata.get("view_count"),
                        "thumbnail": playlist_metadata.get("thumbnail"),
                        "source_platform": "youtube",
                    },
                )

                # Track videos and link to playlist
                if playlist_db_id and downloaded_videos:
                    self._track_playlist_videos(
                        playlist_db_id=playlist_db_id,
                        downloaded_videos=downloaded_videos,
                        playlist_metadata=playlist_metadata,
                    )

                # Update job with playlist ID
                if job_id:
                    self.job_manager.update_job(
                        job_id,
                        output_path=str(result.output_path) if result.output_path else None,
                    )
                    self.job_manager.update_job_status(job_id, "completed")
            else:
                if job_id:
                    self.job_manager.update_job_status(job_id, "completed")
        else:
            # Mark job as failed
            if job_id:
                error_msg = result.message or "Playlist download failed"
                self.job_manager.update_job_status(job_id, "failed", error_message=error_msg)

        return result

    def _track_playlist_videos(
        self,
        playlist_db_id: int,
        downloaded_videos: List[dict],
        playlist_metadata: dict,
    ) -> None:
        """Track videos from playlist and link them to playlist."""
        for position, video_data in enumerate(downloaded_videos, 1):
            try:
                video_path = Path(video_data.get("path", ""))
                if not video_path.exists():
                    continue

                # Track media file
                video_metadata = video_data.get("metadata", {})
                media_file_id = self.media_tracker.track_media_file(
                    video_path,
                    url=video_metadata.get("source_url"),
                    metadata=video_metadata,
                )

                if media_file_id:
                    # Link video to playlist
                    self.playlist_tracker.link_video_to_playlist(
                        playlist_db_id=playlist_db_id,
                        media_file_id=media_file_id,
                        position=position,
                        video_title=video_metadata.get("title"),
                    )

                    # Enrich metadata if needed
                    self._enrich_media_file(media_file_id, video_path, video_metadata.get("source_url"))

            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to track playlist video at position {position}: {e}")

    def _enrich_media_file(self, media_file_id: int, file_path: Path, url: Optional[str]) -> None:
        """Enrich media file with additional metadata."""
        try:
            # Get media file from repository
            media_file = self.repos.media.get_by_id(media_file_id)
            if not media_file:
                return

            # Enrich using metadata manager
            from spatelier.database.metadata import MetadataManager
            # Get config from playlist service or metadata service
            config = getattr(self.playlist_service, 'config', None) or getattr(self.metadata_service, 'config', None)
            if not config:
                if self.logger:
                    self.logger.warning("Cannot enrich media file: no config available")
                return
                
            metadata_manager = MetadataManager(config, verbose=self.logger is not None)
            metadata_manager.enrich_media_file(
                media_file,
                self.repos.media,
                extract_source_metadata=True,
            )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to enrich media file {media_file_id}: {e}")
