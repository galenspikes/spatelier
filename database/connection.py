"""
Database connection management.

This module provides database connection management for both SQLite and MongoDB.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional, Type, Union

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:  # pragma: no cover - optional dependency
    AsyncIOMotorClient = None

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover - optional dependency
    MongoClient = None
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import Config, get_default_data_dir
from core.logger import get_logger
from database.models import Base


class DatabaseManager:
    """Database connection manager for both SQLite and MongoDB."""

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize database manager.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("DatabaseManager", verbose=verbose)

        # SQLite connection
        self.sqlite_engine = None
        self.sqlite_session = None

        # MongoDB connections
        self.mongo_client = None
        self.mongo_async_client = None
        self.mongo_db = None
        self.mongo_async_db = None

    def connect_sqlite(
        self, database_path: Optional[Union[str, Path]] = None
    ) -> Session:
        """
        Connect to SQLite database.

        Args:
            database_path: Path to SQLite database file

        Returns:
            SQLAlchemy session
        """
        if database_path is None:
            database_path = self.config.database.sqlite_path

        database_path = Path(database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLite engine
        self.sqlite_engine = create_engine(
            f"sqlite:///{database_path}", echo=self.verbose, pool_pre_ping=True
        )

        # Create session factory
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.sqlite_engine
        )
        self.sqlite_session = SessionLocal()

        # Create tables
        Base.metadata.create_all(bind=self.sqlite_engine)

        # Create FTS5 virtual table and triggers for transcriptions (if not exists)
        from sqlalchemy import text

        with self.sqlite_engine.connect() as conn:
            # Drop existing FTS5 table and triggers if they exist (to allow overwrite)
            conn.execute(text("DROP TABLE IF EXISTS transcriptions_fts"))
            conn.execute(text("DROP TRIGGER IF EXISTS transcriptions_ai"))
            conn.execute(text("DROP TRIGGER IF EXISTS transcriptions_ad"))
            conn.execute(text("DROP TRIGGER IF EXISTS transcriptions_au"))
            conn.commit()

            # Create FTS5 virtual table
            conn.execute(
                text(
                    """
                CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts USING fts5(
                    full_text, content='transcriptions', content_rowid='id'
                )
            """
                )
            )

            # Create triggers for automatic FTS5 updates
            conn.execute(
                text(
                    """
                CREATE TRIGGER IF NOT EXISTS transcriptions_ai AFTER INSERT ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text);
                END
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE TRIGGER IF NOT EXISTS transcriptions_ad AFTER DELETE ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text)
                    VALUES('delete', old.id, old.full_text);
                END
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE TRIGGER IF NOT EXISTS transcriptions_au AFTER UPDATE ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text)
                    VALUES('delete', old.id, old.full_text);
                    INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text);
                END
            """
                )
            )

            conn.commit()

            # Populate FTS5 table with existing transcriptions
            conn.execute(
                text(
                    """
                INSERT OR IGNORE INTO transcriptions_fts(rowid, full_text)
                SELECT id, full_text FROM transcriptions
            """
                )
            )
            conn.commit()

        self.logger.info(f"Connected to SQLite database: {database_path}")
        return self.sqlite_session

    def get_session(self):
        """Get SQLite session for database operations."""
        if not self.sqlite_session:
            self.connect_sqlite()
        return self.sqlite_session

    def connect_mongodb(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
        async_mode: bool = False,
    ):
        """
        Connect to MongoDB.

        Args:
            connection_string: MongoDB connection string (optional, uses config default)
            database_name: Database name (optional, uses config default)
            async_mode: Whether to use async client
        """
        if connection_string is None:
            connection_string = self.config.database.mongodb_url
        if database_name is None:
            database_name = self.config.database.mongodb_database
        if async_mode:
            if AsyncIOMotorClient is None:
                raise RuntimeError(
                    "MongoDB async client is unavailable. Install the 'mongodb' extra to enable it."
                )
            # Async MongoDB client
            self.mongo_async_client = AsyncIOMotorClient(connection_string)
            self.mongo_async_db = self.mongo_async_client[database_name]
            self.logger.info(f"Connected to MongoDB (async): {database_name}")
        else:
            if MongoClient is None:
                raise RuntimeError(
                    "MongoDB client is unavailable. Install the 'mongodb' extra to enable it."
                )
            # Sync MongoDB client
            self.mongo_client = MongoClient(connection_string)
            self.mongo_db = self.mongo_client[database_name]
            self.logger.info(f"Connected to MongoDB (sync): {database_name}")

    def get_sqlite_session(self) -> Session:
        """Get SQLite session."""
        if self.sqlite_session is None:
            raise RuntimeError("SQLite not connected. Call connect_sqlite() first.")
        return self.sqlite_session

    def get_mongo_db(self):
        """Get MongoDB database (sync)."""
        if self.mongo_db is None:
            raise RuntimeError("MongoDB not connected. Call connect_mongodb() first.")
        return self.mongo_db

    def get_mongo_async_db(self):
        """Get MongoDB database (async)."""
        if self.mongo_async_db is None:
            raise RuntimeError(
                "MongoDB async not connected. Call connect_mongodb(async_mode=True) first."
            )
        return self.mongo_async_db

    def close_connections(self):
        """Close all database connections."""
        if self.sqlite_session:
            self.sqlite_session.close()
            self.sqlite_session = None
            self.logger.info("SQLite session closed")

        if self.sqlite_engine:
            self.sqlite_engine.dispose()
            self.sqlite_engine = None
            self.logger.info("SQLite engine disposed")

        if self.mongo_client:
            self.mongo_client.close()
            self.mongo_client = None
            self.logger.info("MongoDB client closed")

        if self.mongo_async_client:
            # Note: Motor clients don't need explicit closing in async context
            self.logger.info("MongoDB async client closed")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(
        self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb: Optional[Any]
    ) -> None:
        """Context manager exit."""
        self.close_connections()
        # Ensure session is properly closed
        if hasattr(self, "sqlite_session") and self.sqlite_session:
            self.sqlite_session.close()
            self.sqlite_session = None


class DatabaseConfig:
    """Database configuration class."""

    def __init__(self, config: Config):
        """Initialize database configuration."""
        self.config = config
        self.sqlite_path = get_default_data_dir() / "spatelier.db"
        self.mongo_connection_string = "mongodb://localhost:27017"
        self.mongo_database = "spatelier"
        self.enable_mongodb = False
        self.enable_analytics = True
        self.retention_days = 365  # Keep analytics data for 1 year
