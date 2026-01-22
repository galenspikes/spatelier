"""
Tests for MongoDB integration functionality.

This module tests the MongoDB integration for transcription storage
and retrieval, ensuring proper data consistency and operations.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.config import Config
from database.connection import DatabaseManager
from modules.video.transcription_service import TranscriptionStorage


class TestMongoDBIntegration:
    """Test MongoDB integration functionality."""

    @pytest.fixture
    def config(self):
        """Create config for testing."""
        return Config()

    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()

        # Mock the __getitem__ method for MongoDB client and database
        mock_client.__getitem__ = Mock(return_value=mock_db)
        mock_db.__getitem__ = Mock(return_value=mock_collection)

        return mock_client, mock_db, mock_collection

    @pytest.fixture
    def transcription_storage(self, mock_mongo_client):
        """Create transcription storage with mocked MongoDB."""
        mock_client, mock_db, mock_collection = mock_mongo_client
        storage = TranscriptionStorage(mock_db)
        storage.collection = mock_collection
        return storage

    def test_mongodb_connection_initialization(self, config):
        """Test MongoDB connection initialization."""
        with patch("database.connection.MongoClient") as mock_client_class:
            mock_client = Mock()
            mock_db = Mock()
            mock_client.__getitem__ = Mock(return_value=mock_db)
            mock_client_class.return_value = mock_client

            db_manager = DatabaseManager(config, verbose=False)
            db_manager.connect_mongodb()

            assert db_manager.mongo_db is not None

    def test_transcription_storage_initialization(self, transcription_storage):
        """Test transcription storage initialization."""
        assert transcription_storage is not None
        assert transcription_storage.db is not None
        assert transcription_storage.collection is not None

    def test_store_transcription_with_integer_video_id(self, transcription_storage):
        """Test storing transcription with integer video_id."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_123"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = 123
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
            ],
            "language": "en",
            "language_probability": 0.95,
            "duration": 5.0,
            "model_used": "whisper-large",
            "processing_time": 10.5,
        }

        result_id = transcription_storage.store_transcription(
            video_id, transcription_data
        )

        assert result_id == "test_id_123"
        transcription_storage.collection.insert_one.assert_called_once()

        # Verify the document structure
        call_args = transcription_storage.collection.insert_one.call_args[0][0]
        assert call_args["video_id"] == 123
        assert call_args["language"] == "en"
        assert call_args["total_segments"] == 2
        assert call_args["full_text"] == "Hello world This is a test"
        assert call_args["created_at"] is not None

    def test_store_transcription_with_string_video_id(self, transcription_storage):
        """Test storing transcription with string video_id (should convert to int)."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_456"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = "456"  # String ID
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "Test"}],
            "language": "en",
        }

        result_id = transcription_storage.store_transcription(
            video_id, transcription_data
        )

        assert result_id == "test_id_456"

        # Verify video_id was converted to int
        call_args = transcription_storage.collection.insert_one.call_args[0][0]
        assert call_args["video_id"] == 456

    def test_store_transcription_with_non_numeric_string_id(
        self, transcription_storage
    ):
        """Test storing transcription with non-numeric string video_id."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_789"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = "non_numeric_id"
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "Test"}],
            "language": "en",
        }

        # This should raise a ValueError for non-numeric string IDs
        with pytest.raises(ValueError, match="invalid literal for int"):
            transcription_storage.store_transcription(video_id, transcription_data)

    def test_get_transcription_with_integer_video_id(self, transcription_storage):
        """Test getting transcription with integer video_id."""
        mock_transcription = {
            "_id": "test_id_123",
            "video_id": 123,
            "language": "en",
            "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
        }
        transcription_storage.collection.find_one.return_value = mock_transcription

        result = transcription_storage.get_transcription(123)

        assert result is not None
        assert result["video_id"] == 123
        transcription_storage.collection.find_one.assert_called_once_with(
            {"video_id": 123}
        )

    def test_get_transcription_with_string_video_id(self, transcription_storage):
        """Test getting transcription with string video_id (should convert to int)."""
        mock_transcription = {"_id": "test_id_123", "video_id": 123, "language": "en"}
        transcription_storage.collection.find_one.return_value = mock_transcription

        result = transcription_storage.get_transcription("123")

        assert result is not None
        transcription_storage.collection.find_one.assert_called_once_with(
            {"video_id": 123}
        )

    def test_get_transcription_not_found(self, transcription_storage):
        """Test getting transcription when not found."""
        transcription_storage.collection.find_one.return_value = None

        result = transcription_storage.get_transcription(999)

        assert result is None

    def test_search_transcriptions_by_text(self, transcription_storage):
        """Test searching transcriptions by text content."""
        mock_transcriptions = [
            {"video_id": 1, "full_text": "Hello world", "language": "en"},
            {"video_id": 2, "full_text": "Test transcription", "language": "en"},
        ]

        # Mock the MongoDB cursor chain
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_transcriptions
        transcription_storage.collection.find.return_value = mock_cursor

        results = transcription_storage.search_transcriptions("Hello", limit=10)

        assert len(results) == 2
        assert results[0]["video_id"] == 1
        assert results[1]["video_id"] == 2
        transcription_storage.collection.find.assert_called_once()

    def test_search_transcriptions_with_limit(self, transcription_storage):
        """Test searching transcriptions with limit."""
        mock_transcriptions = [
            {"video_id": 1, "full_text": "Test 1"},
            {"video_id": 2, "full_text": "Test 2"},
        ]

        # Mock the MongoDB cursor chain
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_transcriptions
        transcription_storage.collection.find.return_value = mock_cursor

        results = transcription_storage.search_transcriptions("Test", limit=2)

        assert len(results) == 2
        transcription_storage.collection.find.assert_called_once()

    def test_transcription_data_consistency(self, transcription_storage):
        """Test that transcription data is stored consistently."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_123"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = 123
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
            ],
            "language": "en",
            "language_probability": 0.95,
            "duration": 5.0,
            "model_used": "whisper-large",
            "processing_time": 10.5,
        }

        transcription_storage.store_transcription(video_id, transcription_data)

        # Verify all expected fields are present
        call_args = transcription_storage.collection.insert_one.call_args[0][0]
        expected_fields = [
            "video_id",
            "created_at",
            "segments",
            "language",
            "language_probability",
            "duration",
            "model_used",
            "processing_time",
            "total_segments",
            "full_text",
        ]

        for field in expected_fields:
            assert field in call_args

        # Verify specific values
        assert call_args["video_id"] == 123
        assert call_args["language"] == "en"
        assert call_args["total_segments"] == 2
        assert call_args["full_text"] == "Hello world This is a test"
        assert call_args["model_used"] == "whisper-large"
        assert call_args["processing_time"] == 10.5

    def test_transcription_storage_error_handling(self, transcription_storage):
        """Test transcription storage error handling."""
        # Mock insert_one to raise an exception
        transcription_storage.collection.insert_one.side_effect = Exception(
            "MongoDB error"
        )

        video_id = 123
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "Test"}],
            "language": "en",
        }

        # Should not raise exception, but return None or handle gracefully
        with pytest.raises(Exception):
            transcription_storage.store_transcription(video_id, transcription_data)

    def test_transcription_retrieval_error_handling(self, transcription_storage):
        """Test transcription retrieval error handling."""
        # Mock find_one to raise an exception
        transcription_storage.collection.find_one.side_effect = Exception(
            "MongoDB error"
        )

        # Should not raise exception, but return None or handle gracefully
        with pytest.raises(Exception):
            transcription_storage.get_transcription(123)

    def test_transcription_search_error_handling(self, transcription_storage):
        """Test transcription search error handling."""
        # Mock find to raise an exception
        transcription_storage.collection.find.side_effect = Exception("MongoDB error")

        # Should not raise exception, but return empty list or handle gracefully
        with pytest.raises(Exception):
            transcription_storage.search_transcriptions("test")

    def test_mongodb_connection_failure(self, config):
        """Test MongoDB connection failure handling."""
        with patch("database.connection.MongoClient") as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            db_manager = DatabaseManager(config, verbose=False)

            # Should handle connection failure gracefully
            with pytest.raises(Exception):
                db_manager.connect_mongodb()

    def test_transcription_storage_with_missing_segments(self, transcription_storage):
        """Test transcription storage with missing segments."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_123"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = 123
        transcription_data = {
            "language": "en",
            "duration": 5.0,
            "segments": [],  # Empty segments instead of missing
        }

        result_id = transcription_storage.store_transcription(
            video_id, transcription_data
        )

        assert result_id == "test_id_123"

        # Verify default values are set
        call_args = transcription_storage.collection.insert_one.call_args[0][0]
        assert call_args["total_segments"] == 0
        assert call_args["full_text"] == ""

    def test_transcription_storage_with_empty_segments(self, transcription_storage):
        """Test transcription storage with empty segments."""
        mock_result = Mock()
        mock_result.inserted_id = "test_id_123"
        transcription_storage.collection.insert_one.return_value = mock_result

        video_id = 123
        transcription_data = {"segments": [], "language": "en"}

        result_id = transcription_storage.store_transcription(
            video_id, transcription_data
        )

        assert result_id == "test_id_123"

        # Verify empty segments are handled
        call_args = transcription_storage.collection.insert_one.call_args[0][0]
        assert call_args["total_segments"] == 0
        assert call_args["full_text"] == ""
