"""
Database service factory for centralized database management.

This module provides the database service factory, separated from the main
service factory to avoid circular imports.
"""

from typing import Any, Optional, Type

from sqlalchemy.orm import Session

from spatelier.core.config import Config
from spatelier.core.logger import get_logger
from spatelier.database.connection import DatabaseManager
from spatelier.database.repository import (
    AnalyticsRepository,
    MediaFileRepository,
    PlaylistRepository,
    PlaylistVideoRepository,
    ProcessingJobRepository,
)


class RepositoryContainer:
    """Container for all database repositories."""

    def __init__(self, session: Session, verbose: bool = False):
        """Initialize repository container."""
        self.session = session
        self.verbose = verbose

        # Initialize all repositories
        self.media = MediaFileRepository(session, verbose)
        self.jobs = ProcessingJobRepository(session, verbose)
        self.analytics = AnalyticsRepository(session, verbose)
        self.playlists = PlaylistRepository(session, verbose)
        self.playlist_videos = PlaylistVideoRepository(session, verbose)


class DatabaseServiceFactory:
    """Factory for creating database services and repositories."""

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize database service factory.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("DatabaseServiceFactory", verbose=verbose)

        # Database manager
        self.db_manager = DatabaseManager(config, verbose=verbose)
        self._repositories: Optional[RepositoryContainer] = None

    def initialize(self) -> RepositoryContainer:
        """
        Initialize database connections and return repository container.

        Returns:
            RepositoryContainer with all repositories
        """
        if self._repositories is None:
            # Connect to databases
            self.db_manager.connect_sqlite()
            if self.config.database.enable_mongodb:
                self.db_manager.connect_mongodb()

            # Create repository container
            session = self.db_manager.get_sqlite_session()
            self._repositories = RepositoryContainer(session, self.verbose)

            self.logger.info("Database services initialized")

        return self._repositories

    def get_repositories(self) -> RepositoryContainer:
        """
        Get repository container.

        Returns:
            RepositoryContainer with all repositories

        Raises:
            RuntimeError: If database not initialized
        """
        if self._repositories is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._repositories

    def get_db_manager(self) -> DatabaseManager:
        """
        Get database manager.

        Returns:
            DatabaseManager instance
        """
        return self.db_manager

    def close_connections(self):
        """Close all database connections."""
        if self.db_manager:
            self.db_manager.close_connections()
        self._repositories = None
        self.logger.info("Database connections closed")

    def __enter__(self) -> "RepositoryContainer":
        """Context manager entry."""
        return self.initialize()

    def __exit__(
        self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb: Optional[Any]
    ) -> None:
        """Context manager exit."""
        self.close_connections()
