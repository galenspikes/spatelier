"""
Tests for database connection management.

This module tests database connection functionality.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import Config
from database.connection import DatabaseConfig, DatabaseManager
from database.models import Base


def test_database_manager_initialization():
    """Test DatabaseManager initialization."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)

    assert db_manager.config == config
    assert db_manager.verbose == False
    assert db_manager.sqlite_engine is None
    assert db_manager.sqlite_session is None
    assert db_manager.mongo_client is None


def test_database_manager_sqlite_connection():
    """Test SQLite connection."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)

    # Test connection
    session = db_manager.connect_sqlite()

    assert session is not None
    assert db_manager.sqlite_engine is not None
    assert db_manager.sqlite_session is not None

    # Test session functionality
    assert hasattr(session, "query")
    assert hasattr(session, "add")
    assert hasattr(session, "commit")

    # Clean up
    db_manager.close_connections()


def test_database_manager_context_manager():
    """Test DatabaseManager as context manager."""
    config = Config()

    with DatabaseManager(config, verbose=False) as db_manager:
        session = db_manager.connect_sqlite()
        assert session is not None
        assert db_manager.sqlite_session is not None

    # Connections should be closed after context exit
    assert db_manager.sqlite_session is None


def test_database_config_initialization():
    """Test DatabaseConfig initialization."""
    config = Config()
    db_config = DatabaseConfig(config)

    assert db_config.config == config
    assert db_config.sqlite_path is not None
    assert db_config.mongo_connection_string == "mongodb://localhost:27017"
    assert db_config.mongo_database == "spatelier"
    assert db_config.enable_analytics == True
    assert db_config.retention_days == 365


def test_database_manager_get_session():
    """Test getting SQLite session."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)

    # Should raise error if not connected
    with pytest.raises(RuntimeError, match="SQLite not connected"):
        db_manager.get_sqlite_session()

    # Connect and get session
    db_manager.connect_sqlite()
    session = db_manager.get_sqlite_session()
    assert session is not None

    # Clean up
    db_manager.close_connections()


def test_database_manager_mongodb_connection():
    """MongoDB connection is optional; skip in SQLite-only mode."""
    pytest.skip("MongoDB optional; SQLite storage is the default")


def test_database_manager_get_mongo_db():
    """MongoDB optional; skip for SQLite-only default."""
    pytest.skip("MongoDB optional; SQLite storage is the default")


def test_database_manager_get_mongo_async_db():
    """MongoDB optional; skip for SQLite-only default."""
    pytest.skip("MongoDB optional; SQLite storage is the default")


def test_database_manager_close_connections():
    """Test closing database connections (SQLite only)."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)

    # Connect to SQLite only
    db_manager.connect_sqlite()

    # Close connections
    db_manager.close_connections()

    # SQLite connections should be None
    assert db_manager.sqlite_session is None
    assert db_manager.sqlite_engine is None
