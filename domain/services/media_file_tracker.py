"""
Media file tracking domain service.

Handles persistence of media files, converting between domain models
and database entities.
"""

from pathlib import Path
from typing import Optional

from domain.models.media_file import MediaFile
from utils.helpers import get_file_hash, get_file_type


class MediaFileTracker:
    """
    Domain service for tracking media files.

    Handles conversion between domain models and database entities,
    keeping persistence logic separate from business logic.
    """

    def __init__(self, repositories, logger=None):
        """
        Initialize media file tracker.

        Args:
            repositories: Repository container
            logger: Optional logger
        """
        self.repos = repositories
        self.logger = logger

    def track_media_file(
        self,
        file_path: Path,
        url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[int]:
        """
        Track a media file in the database.

        Args:
            file_path: Path to media file
            url: Optional source URL
            metadata: Optional metadata dictionary

        Returns:
            Media file ID if successful, None otherwise
        """
        if not file_path.exists():
            if self.logger:
                self.logger.warning(f"Cannot track non-existent file: {file_path}")
            return None

        try:
            from database.models import MediaType

            file_hash = get_file_hash(file_path)
            file_type = get_file_type(file_path)
            metadata = metadata or {}

            # Check if file already exists
            existing = self.repos.media.get_by_file_path(str(file_path))
            if existing:
                if self.logger:
                    self.logger.debug(f"Media file already tracked: {file_path}")
                return existing.id

            # If metadata has file_path that differs, check for existing at that path too
            if metadata and metadata.get("original_path"):
                original_path = Path(metadata["original_path"])
                existing = self.repos.media.get_by_file_path(str(original_path))
                if existing:
                    # Update existing record with new path
                    if self.update_media_file_path(existing.id, file_path):
                        if self.logger:
                            self.logger.info(f"Updated existing media file {existing.id} with new path: {file_path}")
                        return existing.id

            # Create domain model
            media_type_str = "video" if "video" in file_type else "audio"
            domain_media_file = MediaFile(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                media_type=media_type_str,
                file_hash=file_hash,
            )

            # Persist to database (mime_type is NOT NULL in schema; get_file_type returns MIME string)
            db_media_file = self.repos.media.create(
                file_path=str(domain_media_file.file_path),
                file_name=domain_media_file.file_name,
                file_size=domain_media_file.file_size,
                media_type=MediaType.VIDEO if domain_media_file.is_video() else MediaType.AUDIO,
                mime_type=file_type,
                file_hash=domain_media_file.file_hash,
                source_url=url,
                title=metadata.get("title"),
                description=metadata.get("description"),
                uploader=metadata.get("uploader"),
                uploader_id=metadata.get("uploader_id"),
                upload_date=metadata.get("upload_date"),
                view_count=metadata.get("view_count"),
                like_count=metadata.get("like_count"),
                duration=metadata.get("duration"),
                language=metadata.get("language"),
            )

            if self.logger:
                self.logger.info(f"Tracked media file: {file_path} (ID: {db_media_file.id})")

            return db_media_file.id

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to track media file {file_path}: {e}")
            return None

    def update_media_file_path(self, media_file_id: int, new_path: Path) -> bool:
        """
        Update media file path.

        Args:
            media_file_id: Media file ID
            new_path: New file path

        Returns:
            True if successful, False otherwise
        """
        try:
            self.repos.media.update(
                media_file_id,
                file_path=str(new_path),
                file_name=new_path.name,
            )
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to update media file path: {e}")
            return False

    def get_media_file_by_path(self, file_path: Path) -> Optional[dict]:
        """
        Get media file by path.

        Args:
            file_path: File path

        Returns:
            Media file dictionary or None
        """
        try:
            media_file = self.repos.media.get_by_file_path(str(file_path))
            if media_file:
                return {
                    "id": media_file.id,
                    "file_path": media_file.file_path,
                    "file_name": media_file.file_name,
                    "file_size": media_file.file_size,
                    "media_type": media_file.media_type.value if hasattr(media_file.media_type, "value") else str(media_file.media_type),
                }
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get media file by path: {e}")
            return None
