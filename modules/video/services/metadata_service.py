"""
Video metadata service.

This module provides focused metadata extraction and management functionality.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from core.base_service import BaseService
from core.config import Config
from core.interfaces import IMetadataService
from database.metadata import MetadataExtractor, MetadataManager

if TYPE_CHECKING:
    from database.models import MediaFile
    from database.repository import MediaFileRepository


class MetadataService(BaseService, IMetadataService):
    """
    Focused metadata service.

    Handles metadata extraction, enrichment, and management for video files.
    """

    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """Initialize the metadata service."""
        # Initialize base service
        super().__init__(config, verbose, db_service)

        # Initialize metadata management
        self.metadata_extractor = MetadataExtractor(config, verbose=verbose)
        self.metadata_manager = MetadataManager(config, verbose=verbose)

    def extract_video_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from video URL.

        Args:
            url: Video URL to extract metadata from

        Returns:
            Dictionary containing extracted metadata
        """
        try:
            if "youtube.com" in url or "youtu.be" in url:
                metadata = self.metadata_extractor.extract_youtube_metadata(url)
                self.logger.info(
                    f"Extracted YouTube metadata: {metadata.get('title', 'Unknown')}"
                )
                return metadata
            else:
                self.logger.warning(f"Unsupported URL for metadata extraction: {url}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {url}: {e}")
            return {}

    def enrich_media_file(
        self,
        media_file: "MediaFile",
        repository: Optional["MediaFileRepository"] = None,
    ) -> Dict[str, Any]:
        """
        Enrich media file with additional metadata.

        Args:
            media_file: MediaFile instance to enrich
            repository: Optional MediaFileRepository (for use case layer to pass)

        Returns:
            Dictionary with enriched metadata, or empty dict if enrichment failed
        """
        try:
            # Enrich with additional metadata (returns enriched media_file)
            # Repository is passed from use case layer, not accessed via self.repos
            enriched_file = self.metadata_manager.enrich_media_file(
                media_file, repository, extract_source_metadata=True
            )

            # Convert to dictionary for use case layer
            metadata = {
                "id": enriched_file.id,
                "file_path": enriched_file.file_path,
                "file_name": enriched_file.file_name,
                "file_size": enriched_file.file_size,
                "file_hash": enriched_file.file_hash,
                "media_type": enriched_file.media_type,
                "mime_type": enriched_file.mime_type,
                "source_url": enriched_file.source_url,
                "source_platform": enriched_file.source_platform,
                "source_id": enriched_file.source_id,
                "title": enriched_file.title,
                "description": enriched_file.description,
                "uploader": enriched_file.uploader,
                "uploader_id": enriched_file.uploader_id,
                "upload_date": enriched_file.upload_date,
                "view_count": enriched_file.view_count,
                "like_count": enriched_file.like_count,
                "duration": enriched_file.duration,
                "language": enriched_file.language,
            }

            self.logger.info(f"Enriched metadata for media file: {media_file.id}")
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to enrich media file {media_file.id}: {e}")
            return {}

    def prepare_metadata_update(
        self, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare metadata update dictionary.

        Args:
            metadata: New metadata to apply

        Returns:
            Dictionary with prepared metadata for use case layer to apply
        """
        # Validate and prepare metadata
        prepared = {}
        for key, value in metadata.items():
            if value is not None:
                prepared[key] = value

        self.logger.debug(f"Prepared metadata update with {len(prepared)} fields")
        return prepared

    def convert_media_file_to_dict(self, media_file: "MediaFile") -> Dict[str, Any]:
        """
        Convert MediaFile instance to dictionary.

        Args:
            media_file: MediaFile instance

        Returns:
            Dictionary containing media file metadata
        """
        try:
            # Convert SQLAlchemy object to dictionary
            metadata = {
                "id": media_file.id,
                "file_path": media_file.file_path,
                "file_name": media_file.file_name,
                "file_size": media_file.file_size,
                "file_hash": media_file.file_hash,
                "media_type": media_file.media_type,
                "mime_type": media_file.mime_type,
                "source_url": media_file.source_url,
                "source_platform": media_file.source_platform,
                "source_id": media_file.source_id,
                "title": media_file.title,
                "description": media_file.description,
                "uploader": media_file.uploader,
                "uploader_id": media_file.uploader_id,
                "upload_date": media_file.upload_date,
                "view_count": media_file.view_count,
                "like_count": media_file.like_count,
                "duration": media_file.duration,
                "language": media_file.language,
                "created_at": media_file.created_at,
                "updated_at": media_file.updated_at,
            }

            return metadata

        except Exception as e:
            self.logger.error(
                f"Failed to convert media file to dict: {e}"
            )
            return {}

    def prepare_search_params(
        self, query: str, media_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare search parameters for media file search.

        Args:
            query: Search query
            media_type: Optional media type filter

        Returns:
            Dictionary with search parameters for use case layer
        """
        try:
            from database.models import MediaType

            params = {"query": query}
            
            if media_type:
                try:
                    params["media_type"] = MediaType(media_type)
                except ValueError:
                    self.logger.warning(f"Invalid media type: {media_type}")
                    params["media_type"] = None
            else:
                params["media_type"] = None

            return params

        except Exception as e:
            self.logger.error(f"Failed to prepare search params: {e}")
            return {"query": query, "media_type": None}
