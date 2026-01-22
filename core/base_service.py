"""
Base service class for Spatelier services.

This module provides a common base class that eliminates duplication
in service initialization patterns across all service classes.
"""

from abc import ABC
from typing import Any, Optional

from core.config import Config
from core.database_service import DatabaseServiceFactory
from core.logger import get_logger


class BaseService(ABC):
    """
    Base class for all Spatelier services.

    Provides common initialization patterns and database service management
    to eliminate code duplication across service classes.
    """

    def __init__(
        self, config: Config, verbose: bool = False, db_service: Optional[Any] = None
    ):
        """
        Initialize the base service.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            db_service: Optional database service instance
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger(self.__class__.__name__, verbose=verbose)

        # Initialize database service
        self._init_database_service(db_service)

    def _init_database_service(self, db_service: Optional[Any] = None):
        """
        Initialize database service and repositories.

        Args:
            db_service: Optional database service instance
        """
        if db_service:
            self.db_factory = db_service
            self.repos = self.db_factory.initialize()
            self.db_manager = getattr(self.db_factory, "get_db_manager", lambda: None)()
        else:
            # Fallback for backward compatibility
            self.db_factory = DatabaseServiceFactory(self.config, verbose=self.verbose)
            self.repos = self.db_factory.initialize()
            self.db_manager = self.db_factory.get_db_manager()

    def get_database_service(self):
        """Get the database service factory."""
        return self.db_factory

    def get_repositories(self):
        """Get the repository container."""
        return self.repos

    def get_db_manager(self):
        """Get the database manager."""
        return self.db_manager
