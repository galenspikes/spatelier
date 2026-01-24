"""
Transcribe video use case.

Orchestrates video transcription, coordinating between
transcription service, media tracking, and analytics.
"""

from pathlib import Path
from typing import Optional

from domain.services.media_file_tracker import MediaFileTracker


class TranscribeVideoUseCase:
    """
    Use case for transcribing a video.

    Orchestrates:
    - Video transcription
    - Subtitle embedding
    - Media file tracking
    - Analytics tracking
    """

    def __init__(
        self,
        transcription_service,
        repositories,
        logger=None,
    ):
        """
        Initialize use case.

        Args:
            transcription_service: Transcription service
            repositories: Repository container
            logger: Optional logger
        """
        self.transcription_service = transcription_service
        self.repos = repositories
        self.logger = logger

        # Initialize domain services
        self.media_tracker = MediaFileTracker(repositories, logger=logger)

    def execute(
        self,
        video_path: Path,
        media_file_id: Optional[int] = None,
        language: Optional[str] = None,
        model_size: Optional[str] = None,
        embed_subtitles: bool = True,
    ) -> bool:
        """
        Execute the transcribe video use case.

        Args:
            video_path: Path to video file
            media_file_id: Optional media file ID
            language: Optional language code
            model_size: Optional model size
            embed_subtitles: Whether to embed subtitles

        Returns:
            True if transcription successful, False otherwise
        """
        video_path = Path(video_path)
        if not video_path.exists():
            if self.logger:
                self.logger.error(f"Video file not found: {video_path}")
            return False

        # Track media file if not provided
        if media_file_id is None:
            media_file_id = self.media_tracker.track_media_file(
                video_path,
                metadata={"source_platform": "local"},
            )

        # Track transcription start
        self._track_analytics_event(
            "transcription_start",
            {
                "video_path": str(video_path),
                "media_file_id": media_file_id,
                "language": language or "auto",
            },
        )

        # Transcribe video
        result = self.transcription_service.transcribe_video(
            video_path,
            media_file_id=media_file_id,
            language=language,
            model_size=model_size,
        )

        if result.get("success", False):
            transcription_id = result.get("transcription_id")
            
            # Track successful transcription
            self._track_analytics_event(
                "transcription_completed",
                {
                    "video_path": str(video_path),
                    "media_file_id": media_file_id,
                    "transcription_id": transcription_id,
                    "segments_count": len(result.get("segments", [])),
                },
            )

            # Embed subtitles if requested
            if embed_subtitles:
                # For embedding, we need to specify output path
                # If same as input, it will overwrite
                embed_result = self.transcription_service.embed_subtitles(
                    video_path,
                    video_path,  # Output to same file
                    media_file_id=media_file_id,
                )
                
                if embed_result.get("success", False):
                    self._track_analytics_event(
                        "subtitle_embedding_completed",
                        {
                            "input_path": str(video_path),
                            "output_path": str(video_path),
                            "media_file_id": media_file_id,
                        },
                    )
                    return True
                else:
                    if self.logger:
                        self.logger.warning(f"Failed to embed subtitles for {video_path}")
                    self._track_analytics_event(
                        "subtitle_embedding_error",
                        {
                            "input_path": str(video_path),
                            "output_path": str(video_path),
                            "media_file_id": media_file_id,
                        },
                    )
                    # Transcription succeeded but embedding failed
                    return False

            return True
        else:
            # Track transcription error
            self._track_analytics_event(
                "transcription_error",
                {
                    "video_path": str(video_path),
                    "media_file_id": media_file_id,
                    "error": result.get("error", "Unknown error"),
                },
            )
            return False

    def _track_analytics_event(self, event_type: str, event_data: dict) -> None:
        """Track analytics event."""
        try:
            self.repos.analytics.track_event(event_type, event_data=event_data)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to track analytics event {event_type}: {e}")
