"""
Video metadata service.

This module provides focused metadata extraction and management functionality.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any

from core.base_service import BaseService
from core.config import Config
from database.metadata import MetadataExtractor, MetadataManager


class MetadataService(BaseService):
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
            if 'youtube.com' in url or 'youtu.be' in url:
                metadata = self.metadata_extractor.extract_youtube_metadata(url)
                self.logger.info(f"Extracted YouTube metadata: {metadata.get('title', 'Unknown')}")
                return metadata
            else:
                self.logger.warning(f"Unsupported URL for metadata extraction: {url}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {url}: {e}")
            return {}
    
    def enrich_media_file(self, media_file_id: int) -> bool:
        """
        Enrich media file with additional metadata.
        
        Args:
            media_file_id: ID of media file to enrich
        
        Returns:
            True if enrichment successful, False otherwise
        """
        try:
            media_file = self.repos.media.get_by_id(media_file_id)
            if not media_file:
                self.logger.error(f"Media file not found: {media_file_id}")
                return False
            
            # Enrich with additional metadata
            self.metadata_manager.enrich_media_file(
                media_file,
                self.repos.media,
                extract_source_metadata=True
            )
            
            self.logger.info(f"Enriched metadata for media file: {media_file_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enrich media file {media_file_id}: {e}")
            return False
    
    def update_media_file_metadata(self, media_file_id: int, metadata: Dict[str, Any]) -> bool:
        """
        Update media file with new metadata.
        
        Args:
            media_file_id: ID of media file to update
            metadata: New metadata to apply
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            media_file = self.repos.media.get_by_id(media_file_id)
            if not media_file:
                self.logger.error(f"Media file not found: {media_file_id}")
                return False
            
            # Update media file with new metadata
            self.repos.media.update(media_file_id, **metadata)
            
            self.logger.info(f"Updated metadata for media file: {media_file_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata for media file {media_file_id}: {e}")
            return False
    
    def get_media_file_metadata(self, media_file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a media file.
        
        Args:
            media_file_id: ID of media file
        
        Returns:
            Dictionary containing media file metadata, or None if not found
        """
        try:
            media_file = self.repos.media.get_by_id(media_file_id)
            if not media_file:
                return None
            
            # Convert SQLAlchemy object to dictionary
            metadata = {
                'id': media_file.id,
                'file_path': media_file.file_path,
                'file_name': media_file.file_name,
                'file_size': media_file.file_size,
                'file_hash': media_file.file_hash,
                'media_type': media_file.media_type,
                'mime_type': media_file.mime_type,
                'source_url': media_file.source_url,
                'source_platform': media_file.source_platform,
                'source_id': media_file.source_id,
                'title': media_file.title,
                'description': media_file.description,
                'uploader': media_file.uploader,
                'uploader_id': media_file.uploader_id,
                'upload_date': media_file.upload_date,
                'view_count': media_file.view_count,
                'like_count': media_file.like_count,
                'duration': media_file.duration,
                'language': media_file.language,
                'created_at': media_file.created_at,
                'updated_at': media_file.updated_at
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for media file {media_file_id}: {e}")
            return None
    
    def search_media_files(self, query: str, media_type: Optional[str] = None) -> list:
        """
        Search media files by metadata.
        
        Args:
            query: Search query
            media_type: Optional media type filter
        
        Returns:
            List of matching media files
        """
        try:
            from database.models import MediaType
            
            media_type_enum = None
            if media_type:
                try:
                    media_type_enum = MediaType(media_type)
                except ValueError:
                    self.logger.warning(f"Invalid media type: {media_type}")
            
            results = self.repos.media.search(query, media_type_enum)
            
            self.logger.info(f"Found {len(results)} media files matching '{query}'")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search media files: {e}")
            return []
