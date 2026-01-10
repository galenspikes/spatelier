"""
Tests for database connection management.

This module tests database connection functionality.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import Config
from database.connection import DatabaseManager, DatabaseConfig
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
    assert hasattr(session, 'query')
    assert hasattr(session, 'add')
    assert hasattr(session, 'commit')
    
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
    """Test MongoDB connection."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)
    
    # Test sync connection
    db_manager.connect_mongodb()
    assert db_manager.mongo_client is not None
    assert db_manager.mongo_db is not None
    
    # Test async connection
    db_manager.connect_mongodb(async_mode=True)
    assert db_manager.mongo_async_client is not None
    assert db_manager.mongo_async_db is not None
    
    # Clean up
    db_manager.close_connections()


def test_database_manager_get_mongo_db():
    """Test getting MongoDB database."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)
    
    # Should raise error if not connected
    with pytest.raises(RuntimeError, match="MongoDB not connected"):
        db_manager.get_mongo_db()
    
    # Connect and get database
    db_manager.connect_mongodb()
    db = db_manager.get_mongo_db()
    assert db is not None
    
    # Clean up
    db_manager.close_connections()


def test_database_manager_get_mongo_async_db():
    """Test getting MongoDB async database."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)
    
    # Should raise error if not connected
    with pytest.raises(RuntimeError, match="MongoDB async not connected"):
        db_manager.get_mongo_async_db()
    
    # Connect and get database
    db_manager.connect_mongodb(async_mode=True)
    db = db_manager.get_mongo_async_db()
    assert db is not None
    
    # Clean up
    db_manager.close_connections()


def test_database_manager_close_connections():
    """Test closing database connections."""
    config = Config()
    db_manager = DatabaseManager(config, verbose=False)
    
    # Connect to databases
    db_manager.connect_sqlite()
    db_manager.connect_mongodb()
    
    # Close connections
    db_manager.close_connections()
    
    # All connections should be None
    assert db_manager.sqlite_session is None
    assert db_manager.sqlite_engine is None
    assert db_manager.mongo_client is None
    assert db_manager.mongo_async_client is None
