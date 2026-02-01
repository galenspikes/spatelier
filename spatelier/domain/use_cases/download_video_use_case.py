"""
Download video use case.

Orchestrates the download of a video, coordinating between
download service, metadata service, and tracking.
"""

from pathlib import Path
from typing import Optional

from spatelier.core.base import ProcessingResult
from spatelier.domain.models.media_file import MediaFile
from spatelier.domain.models.video import Video
from spatelier.domain.services.job_manager import JobManager
from spatelier.domain.services.media_file_tracker import MediaFileTracker


class DownloadVideoUseCase:
    """
    Use case for downloading a video.

    Orchestrates:
    - Video downloading
    - Metadata extraction
    - File tracking
    - Analytics (via decorator)
    """

    def __init__(
        self,
        download_service,
        metadata_service,
        repositories,
        logger=None,
    ):
        """
        Initialize use case.

        Args:
            download_service: Video download service
            metadata_service: Metadata service
            repositories: Repository container
            logger: Optional logger
        """
        self.download_service = download_service
        self.metadata_service = metadata_service
        self.repos = repositories
        self.logger = logger

        # Initialize domain services
        self.job_manager = JobManager(repositories, logger=logger)
        self.media_tracker = MediaFileTracker(repositories, logger=logger)

    def execute(
        self,
        url: str,
        output_path: Optional[Path] = None,
        create_job: bool = True,
        **kwargs,
    ) -> ProcessingResult:
        """
        Execute the download video use case.

        Args:
            url: Video URL
            output_path: Optional output path
            create_job: Whether to create a processing job (default: True)
            **kwargs: Additional download options

        Returns:
            ProcessingResult with download details
        """
        # Create domain model
        video = Video(url=url)

        # Extract metadata
        if self.metadata_service:
            metadata = self.metadata_service.extract_video_metadata(url)
            video.title = metadata.get("title")
            video.duration_seconds = metadata.get("duration")

        # Create processing job if requested
        job_id = None
        if create_job:
            job_id = self.job_manager.create_job(
                job_type="download_video",
                input_path=url,
                output_path=str(output_path) if output_path else "",
                parameters=kwargs,
            )
            if job_id:
                kwargs["job_id"] = job_id  # Pass job_id to download service
                # Mark job as processing
                self.job_manager.update_job_status(job_id, "processing")

        # Download video
        result = self.download_service.download_video(url, output_path, **kwargs)

        if result.success and result.output_path:
            video.file_path = Path(result.output_path)
            video.file_size = video.file_path.stat().st_size if video.file_path.exists() else None

            # Get metadata from result
            file_metadata = result.metadata or {}
            
            # Track media file (handles path changes internally via original_path in metadata)
            media_file_id = self.media_tracker.track_media_file(
                video.file_path,
                url=url,
                metadata=file_metadata,
            )

            # Enrich metadata if media file was created
            if media_file_id:
                self._enrich_media_file(media_file_id, video.file_path, url)

            # Update result metadata
            if media_file_id:
                if result.metadata:
                    result.metadata["media_file_id"] = media_file_id
                else:
                    result.metadata = {"media_file_id": media_file_id}

            # Update job with media file ID and mark as completed
            if job_id:
                self.job_manager.update_job(
                    job_id,
                    media_file_id=media_file_id,
                    output_path=str(video.file_path),
                )
                self.job_manager.update_job_status(job_id, "completed")
        else:
            # Mark job as failed
            if job_id:
                error_msg = result.message or "Download failed"
                self.job_manager.update_job_status(job_id, "failed", error_message=error_msg)

        return result

    def _enrich_media_file(self, media_file_id: int, file_path: Path, url: str) -> None:
        """Enrich media file with additional metadata."""
        try:
            # Get media file from repository
            media_file = self.repos.media.get_by_id(media_file_id)
            if not media_file:
                return

            # Enrich using metadata manager
            from spatelier.database.metadata import MetadataManager
            # Get config from download service or metadata service
            config = getattr(self.download_service, 'config', None) or getattr(self.metadata_service, 'config', None)
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
