"""
Core interfaces for dependency injection and service layer.

This module defines abstract interfaces for the service layer,
enabling dependency injection and better testability.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.base import ProcessingResult
from core.config import Config


class IDatabaseService(ABC):
    """Interface for database services."""

    @abstractmethod
    def initialize(self) -> "IRepositoryContainer":
        """Initialize database connections and return repository container."""
        pass

    @abstractmethod
    def close_connections(self):
        """Close all database connections."""
        pass


class IRepositoryContainer(ABC):
    """Interface for repository container."""

    @property
    @abstractmethod
    def media(self):
        """Media file repository."""
        pass

    @property
    @abstractmethod
    def jobs(self):
        """Processing job repository."""
        pass

    @property
    @abstractmethod
    def analytics(self):
        """Analytics repository."""
        pass

    @property
    @abstractmethod
    def playlists(self):
        """Playlist repository."""
        pass

    @property
    @abstractmethod
    def playlist_videos(self):
        """Playlist video repository."""
        pass


class IVideoDownloadService(ABC):
    """Interface for video download service."""

    @abstractmethod
    def download_video(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> ProcessingResult:
        """Download a single video from URL."""
        pass


class IMetadataService(ABC):
    """Interface for metadata service."""

    @abstractmethod
    def extract_video_metadata(self, url: str) -> Dict[str, Any]:
        """Extract metadata from video URL."""
        pass

    @abstractmethod
    def enrich_media_file(self, media_file_id: int) -> bool:
        """Enrich media file with additional metadata."""
        pass

    @abstractmethod
    def get_media_file_metadata(self, media_file_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a media file."""
        pass


class ITranscriptionService(ABC):
    """Interface for transcription service."""

    @abstractmethod
    def transcribe_video(
        self,
        video_path: Union[str, Path],
        media_file_id: Optional[int] = None,
        language: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> bool:
        """Transcribe a video file."""
        pass

    @abstractmethod
    def embed_subtitles(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        media_file_id: Optional[int] = None,
    ) -> bool:
        """Embed subtitles into video file."""
        pass


class IPlaylistService(ABC):
    """Interface for playlist service."""

    @abstractmethod
    def download_playlist(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Download playlist without transcription."""
        pass


class IServiceFactory(ABC):
    """Interface for service factory."""

    @abstractmethod
    def create_database_service(
        self, config: Config, verbose: bool = False
    ) -> IDatabaseService:
        """Create database service."""
        pass

    @abstractmethod
    def create_video_download_service(
        self, config: Config, verbose: bool = False
    ) -> IVideoDownloadService:
        """Create video download service."""
        pass

    @abstractmethod
    def create_metadata_service(
        self, config: Config, verbose: bool = False
    ) -> IMetadataService:
        """Create metadata service."""
        pass

    @abstractmethod
    def create_transcription_service(
        self, config: Config, verbose: bool = False
    ) -> ITranscriptionService:
        """Create transcription service."""
        pass

    @abstractmethod
    def create_playlist_service(
        self, config: Config, verbose: bool = False
    ) -> IPlaylistService:
        """Create playlist service."""
        pass
