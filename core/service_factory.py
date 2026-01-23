"""
Consolidated service factory for dependency injection.

This module provides a single factory for creating and managing all services,
eliminating duplication and ensuring consistent service lifecycle management.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from core.config import Config
from core.database_service import DatabaseServiceFactory, RepositoryContainer
from core.interfaces import (
    IDatabaseService,
    IMetadataService,
    IPlaylistService,
    IRepositoryContainer,
    IServiceFactory,
    ITranscriptionService,
    IVideoDownloadService,
)
from core.logger import get_logger

if TYPE_CHECKING:
    from core.job_queue import JobQueue


class ServiceFactory(IServiceFactory):
    """
    Consolidated factory for creating and managing all services.

    Supports context manager usage and lazy-loaded service properties.
    Replaces ServiceContainer with a cleaner, more direct approach.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize service factory.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("ServiceFactory", verbose=verbose)

        # Services will be created lazily
        self._database_service: Optional[IDatabaseService] = None
        self._repositories: Optional[IRepositoryContainer] = None
        self._video_download_service: Optional[IVideoDownloadService] = None
        self._metadata_service: Optional[IMetadataService] = None
        self._transcription_service: Optional[ITranscriptionService] = None
        self._playlist_service: Optional[IPlaylistService] = None
        self._job_queue: Optional["JobQueue"] = None

    def create_database_service(
        self, config: Optional[Config] = None, verbose: Optional[bool] = None
    ) -> IDatabaseService:
        """
        Create database service.

        Args:
            config: Optional config override (defaults to instance config)
            verbose: Optional verbose override (defaults to instance verbose)
        """
        if self._database_service is None:
            use_config = config if config is not None else self.config
            use_verbose = verbose if verbose is not None else self.verbose
            self._database_service = DatabaseServiceFactory(
                use_config, verbose=use_verbose
            )
        return self._database_service

    def create_video_download_service(
        self, config: Optional[Config] = None, verbose: Optional[bool] = None
    ) -> IVideoDownloadService:
        """
        Create video download service.

        Args:
            config: Optional config override (defaults to instance config)
            verbose: Optional verbose override (defaults to instance verbose)
        """
        if self._video_download_service is None:
            use_config = config if config is not None else self.config
            use_verbose = verbose if verbose is not None else self.verbose
            # Get database service for dependency injection
            db_service = self.create_database_service(use_config, use_verbose)
            # Import here to avoid circular imports
            from modules.video.services import VideoDownloadService

            self._video_download_service = VideoDownloadService(
                use_config, verbose=use_verbose, db_service=db_service
            )
        return self._video_download_service

    def create_metadata_service(
        self, config: Optional[Config] = None, verbose: Optional[bool] = None
    ) -> IMetadataService:
        """
        Create metadata service.

        Args:
            config: Optional config override (defaults to instance config)
            verbose: Optional verbose override (defaults to instance verbose)
        """
        if self._metadata_service is None:
            use_config = config if config is not None else self.config
            use_verbose = verbose if verbose is not None else self.verbose
            # Get database service for dependency injection
            db_service = self.create_database_service(use_config, use_verbose)
            # Import here to avoid circular imports
            from modules.video.services import MetadataService

            self._metadata_service = MetadataService(
                use_config, verbose=use_verbose, db_service=db_service
            )
        return self._metadata_service

    def create_transcription_service(
        self, config: Optional[Config] = None, verbose: Optional[bool] = None
    ) -> ITranscriptionService:
        """
        Create transcription service.

        Args:
            config: Optional config override (defaults to instance config)
            verbose: Optional verbose override (defaults to instance verbose)
        """
        if self._transcription_service is None:
            use_config = config if config is not None else self.config
            use_verbose = verbose if verbose is not None else self.verbose
            # Get database service for dependency injection
            db_service = self.create_database_service(use_config, use_verbose)
            # Import here to avoid circular imports
            from modules.video.services.transcription_service import (
                TranscriptionService,
            )

            self._transcription_service = TranscriptionService(
                use_config, verbose=use_verbose, db_service=db_service
            )
        return self._transcription_service

    def create_playlist_service(
        self, config: Optional[Config] = None, verbose: Optional[bool] = None
    ) -> IPlaylistService:
        """
        Create playlist service.

        Args:
            config: Optional config override (defaults to instance config)
            verbose: Optional verbose override (defaults to instance verbose)
        """
        if self._playlist_service is None:
            use_config = config if config is not None else self.config
            use_verbose = verbose if verbose is not None else self.verbose
            # Get database service for dependency injection
            db_service = self.create_database_service(use_config, use_verbose)
            # Import here to avoid circular imports
            from modules.video.services import PlaylistService

            self._playlist_service = PlaylistService(
                use_config, verbose=use_verbose, db_service=db_service
            )
        return self._playlist_service

    # Property-based access for convenience (replaces ServiceContainer properties)
    @property
    def database(self) -> IDatabaseService:
        """Get database service (lazy-loaded)."""
        return self.create_database_service()

    @property
    def repositories(self) -> IRepositoryContainer:
        """Get repository container (lazy-loaded, initializes database)."""
        if self._repositories is None:
            self._repositories = self.database.initialize()
        return self._repositories

    @property
    def video_download(self) -> IVideoDownloadService:
        """Get video download service (lazy-loaded)."""
        return self.create_video_download_service()

    @property
    def metadata(self) -> IMetadataService:
        """Get metadata service (lazy-loaded)."""
        return self.create_metadata_service()

    @property
    def transcription(self) -> ITranscriptionService:
        """Get transcription service (lazy-loaded)."""
        return self.create_transcription_service()

    @property
    def playlist(self) -> IPlaylistService:
        """Get playlist service (lazy-loaded)."""
        return self.create_playlist_service()

    @property
    def job_queue(self) -> "JobQueue":
        """Get job queue (lazy-loaded)."""
        if self._job_queue is None:
            from core.job_queue import JobQueue

            self._job_queue = JobQueue(self.config, self.verbose)
        return self._job_queue

    def initialize_database(self) -> IRepositoryContainer:
        """
        Initialize database and return repositories.

        Returns:
            RepositoryContainer with all repositories
        """
        return self.repositories

    def close_all_services(self):
        """Close all services and connections."""
        if self._database_service:
            self._database_service.close_connections()

        # Reset all services
        self._database_service = None
        self._repositories = None
        self._video_download_service = None
        self._metadata_service = None
        self._transcription_service = None
        self._playlist_service = None
        self._job_queue = None

    def get_database_service(self) -> Optional[IDatabaseService]:
        """Get existing database service."""
        return self._database_service

    def get_video_download_service(self) -> Optional[IVideoDownloadService]:
        """Get existing video download service."""
        return self._video_download_service

    def get_metadata_service(self) -> Optional[IMetadataService]:
        """Get existing metadata service."""
        return self._metadata_service

    def get_transcription_service(self) -> Optional[ITranscriptionService]:
        """Get existing transcription service."""
        return self._transcription_service

    def get_playlist_service(self) -> Optional[IPlaylistService]:
        """Get existing playlist service."""
        return self._playlist_service

    def reset_services(self):
        """Reset all services (useful for testing)."""
        self.close_all_services()

    # Context manager support
    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all_services()


