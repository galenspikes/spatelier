"""
Database repository for data operations.

This module provides repository classes for database operations on both SQLite and MongoDB.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from core.logger import get_logger
from database.models import (
    AnalyticsEvent,
    DownloadSource,
    MediaFile,
    MediaType,
    Playlist,
    PlaylistVideo,
    ProcessingJob,
    ProcessingStatus,
    UserPreference,
)


class MediaFileRepository:
    """Repository for media file operations."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize media file repository."""
        self.session = session
        self.verbose = verbose
        self.logger = get_logger("MediaFileRepository", verbose=verbose)

    def create(self, file_path: Union[str, Path], **kwargs) -> MediaFile:
        """
        Create a new media file record.

        Args:
            file_path: Path to media file
            **kwargs: Additional media file attributes

        Returns:
            Created MediaFile instance
        """
        file_path = Path(file_path)

        # Extract file_name from kwargs if provided, otherwise use file_path.name
        file_name = kwargs.pop("file_name", file_path.name)

        # Remove file_size from kwargs if it exists to avoid conflicts
        file_size = kwargs.pop(
            "file_size", file_path.stat().st_size if file_path.exists() else 0
        )

        media_file = MediaFile(
            file_path=str(file_path), file_name=file_name, file_size=file_size, **kwargs
        )

        self.session.add(media_file)
        self.session.commit()
        self.session.refresh(media_file)

        self.logger.info(f"Created media file record: {file_path}")
        return media_file

    def get_by_id(self, file_id: int) -> Optional[MediaFile]:
        """Get media file by ID."""
        return self.session.query(MediaFile).filter(MediaFile.id == file_id).first()

    def get_by_path(self, file_path: Union[str, Path]) -> Optional[MediaFile]:
        """Get media file by path."""
        return (
            self.session.query(MediaFile)
            .filter(MediaFile.file_path == str(file_path))
            .first()
        )

    def get_by_hash(self, file_hash: str) -> Optional[MediaFile]:
        """Get media file by hash."""
        return (
            self.session.query(MediaFile)
            .filter(MediaFile.file_hash == file_hash)
            .first()
        )

    def list_by_type(self, media_type: MediaType, limit: int = 100) -> List[MediaFile]:
        """List media files by type."""
        return (
            self.session.query(MediaFile)
            .filter(MediaFile.media_type == media_type)
            .order_by(desc(MediaFile.created_at))
            .limit(limit)
            .all()
        )

    def search(
        self, query: str, media_type: Optional[MediaType] = None
    ) -> List[MediaFile]:
        """Search media files by name or path."""
        filters = [
            or_(
                MediaFile.file_name.ilike(f"%{query}%"),
                MediaFile.file_path.ilike(f"%{query}%"),
            )
        ]

        if media_type:
            filters.append(MediaFile.media_type == media_type)

        return (
            self.session.query(MediaFile)
            .filter(and_(*filters))
            .order_by(desc(MediaFile.created_at))
            .all()
        )

    def get_by_file_path(self, file_path: str) -> Optional[MediaFile]:
        """Get media file by file path."""
        return (
            self.session.query(MediaFile)
            .filter(MediaFile.file_path == file_path)
            .first()
        )

    def delete(self, media_file_id: int) -> bool:
        """Delete media file by ID."""
        media_file = (
            self.session.query(MediaFile).filter(MediaFile.id == media_file_id).first()
        )
        if media_file:
            self.session.delete(media_file)
            self.session.commit()
            self.logger.info(f"Deleted media file {media_file_id}")
            return True
        return False

    def get_by_source_id(self, source_id: str) -> List[MediaFile]:
        """Get media files by source ID (e.g., YouTube video ID)."""
        return (
            self.session.query(MediaFile).filter(MediaFile.source_id == source_id).all()
        )

    def update(self, media_file_id: int, **kwargs) -> MediaFile:
        """Update media file with new data."""
        media_file = self.get_by_id(media_file_id)
        if not media_file:
            raise ValueError(f"Media file with ID {media_file_id} not found")

        # Update fields that exist on the model
        for key, value in kwargs.items():
            if hasattr(media_file, key):
                setattr(media_file, key, value)

        media_file.updated_at = datetime.now()
        self.session.commit()
        return media_file

    def get_statistics(self) -> Dict[str, Any]:
        """Get media file statistics."""
        stats = {}

        # Total files by type
        type_counts = (
            self.session.query(MediaFile.media_type, func.count(MediaFile.id))
            .group_by(MediaFile.media_type)
            .all()
        )
        stats["files_by_type"] = dict(type_counts)

        # Total file size by type
        size_by_type = (
            self.session.query(MediaFile.media_type, func.sum(MediaFile.file_size))
            .group_by(MediaFile.media_type)
            .all()
        )
        stats["size_by_type"] = dict(size_by_type)

        # Recent files (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_count = (
            self.session.query(MediaFile)
            .filter(MediaFile.created_at >= thirty_days_ago)
            .count()
        )
        stats["recent_files"] = recent_count

        return stats


class ProcessingJobRepository:
    """Repository for processing job operations."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize processing job repository."""
        self.session = session
        self.verbose = verbose
        self.logger = get_logger("ProcessingJobRepository", verbose=verbose)

    def create(
        self, media_file_id: int, job_type: str, input_path: str, **kwargs
    ) -> ProcessingJob:
        """
        Create a new processing job.

        Args:
            media_file_id: ID of associated media file
            job_type: Type of processing job
            input_path: Path to input file
            **kwargs: Additional job attributes

        Returns:
            Created ProcessingJob instance
        """
        job = ProcessingJob(
            media_file_id=media_file_id,
            job_type=job_type,
            input_path=input_path,
            status=ProcessingStatus.PENDING,
            **kwargs,
        )

        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)

        self.logger.info(f"Created processing job: {job_type} for {input_path}")
        return job

    def update_status(
        self,
        job_id: int,
        status: ProcessingStatus,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> ProcessingJob:
        """Update processing job status."""
        job = (
            self.session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        )

        if job:
            job.status = status
            if output_path:
                job.output_path = output_path
            if error_message:
                job.error_message = error_message

            if status == ProcessingStatus.PROCESSING:
                # Only set started_at if not already set
                if not job.started_at:
                    job.started_at = datetime.now()
            elif status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                job.completed_at = datetime.now()
                # Calculate duration using started_at if available, otherwise use created_at
                if job.started_at:
                    job.duration_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()
                elif job.created_at:
                    # Fallback to created_at if started_at was never set
                    job.duration_seconds = (
                        job.completed_at - job.created_at
                    ).total_seconds()

            self.session.commit()
            self.logger.info(f"Updated job {job_id} status to {status}")

        return job

    def get_by_id(self, job_id: int) -> Optional[ProcessingJob]:
        """Get processing job by ID."""
        return (
            self.session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        )

    def update(self, job_id: int, **kwargs) -> Optional[ProcessingJob]:
        """Update processing job with given fields."""
        job = (
            self.session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        )

        if job:
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            self.session.commit()
            self.logger.info(f"Updated job {job_id} with fields: {list(kwargs.keys())}")

        return job

    def get_by_status(self, status: ProcessingStatus) -> List[ProcessingJob]:
        """Get jobs by status."""
        return (
            self.session.query(ProcessingJob)
            .filter(ProcessingJob.status == status)
            .order_by(desc(ProcessingJob.created_at))
            .all()
        )

    def get_job_statistics(self) -> Dict[str, Any]:
        """Get processing job statistics."""
        stats = {}

        # Jobs by status
        status_counts = (
            self.session.query(ProcessingJob.status, func.count(ProcessingJob.id))
            .group_by(ProcessingJob.status)
            .all()
        )
        stats["jobs_by_status"] = dict(status_counts)

        # Jobs by type
        type_counts = (
            self.session.query(ProcessingJob.job_type, func.count(ProcessingJob.id))
            .group_by(ProcessingJob.job_type)
            .all()
        )
        stats["jobs_by_type"] = dict(type_counts)

        # Average processing time
        avg_duration = (
            self.session.query(func.avg(ProcessingJob.duration_seconds))
            .filter(ProcessingJob.duration_seconds.isnot(None))
            .scalar()
        )
        stats["avg_processing_time"] = avg_duration

        return stats


class AnalyticsRepository:
    """Repository for analytics operations."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize analytics repository."""
        self.session = session
        self.verbose = verbose
        self.logger = get_logger("AnalyticsRepository", verbose=verbose)

    def track_event(
        self,
        event_type: str,
        media_file_id: Optional[int] = None,
        processing_job_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AnalyticsEvent:
        """
        Track an analytics event.

        Args:
            event_type: Type of event
            media_file_id: Associated media file ID
            processing_job_id: Associated processing job ID
            event_data: Additional event data
            user_id: User ID
            session_id: Session ID

        Returns:
            Created AnalyticsEvent instance
        """
        event = AnalyticsEvent(
            event_type=event_type,
            media_file_id=media_file_id,
            processing_job_id=processing_job_id,
            event_data=json.dumps(event_data) if event_data else None,
            user_id=user_id,
            session_id=session_id,
        )

        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)

        self.logger.debug(f"Tracked event: {event_type}")
        return event

    def get_events_by_type(
        self, event_type: str, days: int = 30
    ) -> List[AnalyticsEvent]:
        """Get events by type within specified days."""
        since = datetime.now() - timedelta(days=days)

        return (
            self.session.query(AnalyticsEvent)
            .filter(
                and_(
                    AnalyticsEvent.event_type == event_type,
                    AnalyticsEvent.timestamp >= since,
                )
            )
            .order_by(desc(AnalyticsEvent.timestamp))
            .all()
        )

    def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for specified days."""
        since = datetime.now() - timedelta(days=days)

        stats = {}

        # Events by type
        event_counts = (
            self.session.query(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .filter(AnalyticsEvent.timestamp >= since)
            .group_by(AnalyticsEvent.event_type)
            .all()
        )
        stats["events_by_type"] = dict(event_counts)

        # Daily activity
        daily_activity = (
            self.session.query(
                func.date(AnalyticsEvent.timestamp).label("date"),
                func.count(AnalyticsEvent.id).label("count"),
            )
            .filter(AnalyticsEvent.timestamp >= since)
            .group_by(func.date(AnalyticsEvent.timestamp))
            .order_by("date")
            .all()
        )
        stats["daily_activity"] = [
            {"date": str(row.date), "count": row.count} for row in daily_activity
        ]

        return stats


class PlaylistRepository:
    """Repository for playlist operations."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize playlist repository."""
        self.session = session
        self.verbose = verbose
        self.logger = get_logger("PlaylistRepository", verbose=verbose)

    def create(self, **kwargs) -> Playlist:
        """Create a new playlist."""
        playlist = Playlist(**kwargs)
        self.session.add(playlist)
        self.session.commit()
        self.session.refresh(playlist)
        self.logger.info(f"Created playlist: {playlist.id}")
        return playlist

    def get_by_id(self, playlist_id: int) -> Optional[Playlist]:
        """Get playlist by ID."""
        return self.session.query(Playlist).filter(Playlist.id == playlist_id).first()

    def get_by_playlist_id(self, playlist_id: str) -> Optional[Playlist]:
        """Get playlist by external playlist ID (e.g., YouTube playlist ID)."""
        return (
            self.session.query(Playlist)
            .filter(Playlist.playlist_id == playlist_id)
            .first()
        )

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Playlist]:
        """Get all playlists with pagination."""
        return (
            self.session.query(Playlist)
            .order_by(desc(Playlist.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update(self, playlist_id: int, **kwargs) -> Optional[Playlist]:
        """Update playlist."""
        playlist = self.get_by_id(playlist_id)
        if not playlist:
            return None

        for key, value in kwargs.items():
            if hasattr(playlist, key):
                setattr(playlist, key, value)

        playlist.updated_at = datetime.now()
        self.session.commit()
        return playlist

    def delete(self, playlist_id: int) -> bool:
        """Delete playlist and all associated playlist_videos."""
        playlist = self.get_by_id(playlist_id)
        if not playlist:
            return False

        self.session.delete(playlist)
        self.session.commit()
        self.logger.info(f"Deleted playlist: {playlist_id}")
        return True


class PlaylistVideoRepository:
    """Repository for playlist-video relationship operations."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize playlist video repository."""
        self.session = session
        self.verbose = verbose
        self.logger = get_logger("PlaylistVideoRepository", verbose=verbose)

    def add_video_to_playlist(
        self,
        playlist_id: int,
        media_file_id: int,
        position: Optional[int] = None,
        video_title: Optional[str] = None,
    ) -> PlaylistVideo:
        """Add video to playlist."""
        playlist_video = PlaylistVideo(
            playlist_id=playlist_id,
            media_file_id=media_file_id,
            position=position,
            video_title=video_title,
        )
        self.session.add(playlist_video)
        self.session.commit()
        self.session.refresh(playlist_video)
        self.logger.info(f"Added video {media_file_id} to playlist {playlist_id}")
        return playlist_video

    def remove_video_from_playlist(self, playlist_id: int, media_file_id: int) -> bool:
        """Remove video from playlist."""
        playlist_video = (
            self.session.query(PlaylistVideo)
            .filter(
                and_(
                    PlaylistVideo.playlist_id == playlist_id,
                    PlaylistVideo.media_file_id == media_file_id,
                )
            )
            .first()
        )

        if not playlist_video:
            return False

        self.session.delete(playlist_video)
        self.session.commit()
        self.logger.info(f"Removed video {media_file_id} from playlist {playlist_id}")
        return True

    def get_playlist_videos(self, playlist_id: int) -> List[PlaylistVideo]:
        """Get all videos in a playlist."""
        return (
            self.session.query(PlaylistVideo)
            .filter(PlaylistVideo.playlist_id == playlist_id)
            .order_by(PlaylistVideo.position, PlaylistVideo.added_at)
            .all()
        )

    def get_by_playlist_id(self, playlist_id: int) -> List[PlaylistVideo]:
        """Get all videos in a playlist by playlist ID."""
        return self.get_playlist_videos(playlist_id)

    def get_video_playlists(self, media_file_id: int) -> List[PlaylistVideo]:
        """Get all playlists containing a video."""
        return (
            self.session.query(PlaylistVideo)
            .filter(PlaylistVideo.media_file_id == media_file_id)
            .all()
        )

    def update_video_position(
        self, playlist_id: int, media_file_id: int, position: int
    ) -> bool:
        """Update video position in playlist."""
        playlist_video = (
            self.session.query(PlaylistVideo)
            .filter(
                and_(
                    PlaylistVideo.playlist_id == playlist_id,
                    PlaylistVideo.media_file_id == media_file_id,
                )
            )
            .first()
        )

        if not playlist_video:
            return False

        playlist_video.position = position
        self.session.commit()
        return True
