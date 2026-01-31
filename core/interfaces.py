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
    def enrich_media_file(self, media_file, repository=None) -> Dict[str, Any]:
        """
        Enrich media file with additional metadata.
        
        Args:
            media_file: MediaFile instance to enrich
            repository: Optional MediaFileRepository (for use case layer to pass)
        """
        pass

    @abstractmethod
    def prepare_metadata_update(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare metadata update dictionary."""
        pass

    @abstractmethod
    def convert_media_file_to_dict(self, media_file) -> Dict[str, Any]:
        """Convert MediaFile instance to dictionary."""
        pass

    @abstractmethod
    def prepare_search_params(
        self, query: str, media_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare search parameters for media file search."""
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

    @abstractmethod
    def has_transcription(self, media_file) -> bool:
        """Check if a media file has transcription."""
        pass

    @abstractmethod
    def has_whisper_subtitles(self, file_path: Path) -> bool:
        """Check if video file has Whisper subtitles embedded."""
        pass


class IPlaylistService(ABC):
    """Interface for playlist service."""

    @abstractmethod
    def download_playlist(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Download playlist without transcription."""
        pass

    @abstractmethod
    def get_playlist_progress(
        self, playlist_id: str, repositories=None, transcription_service=None
    ) -> Dict[str, int]:
        """
        Get playlist download progress.
        
        Args:
            playlist_id: Playlist ID
            repositories: Optional repository container (for use case layer to pass)
            transcription_service: Optional TranscriptionService (for use case layer to pass)
        """
        pass

    @abstractmethod
    def get_failed_videos(
        self, playlist_id: str, repositories=None, transcription_service=None
    ) -> List[Dict[str, Any]]:
        """
        Get failed videos from playlist.
        
        Args:
            playlist_id: Playlist ID
            repositories: Optional repository container (for use case layer to pass)
            transcription_service: Optional TranscriptionService (for use case layer to pass)
        """
        pass

    @abstractmethod
    def download_playlist_with_transcription(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        continue_download: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Download playlist with transcription support."""
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
