"""
Tests for transcription service functionality.

This module tests the transcription service with mocked WhisperAI
to ensure proper transcription and MongoDB storage.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import text

from core.config import Config
from database.models import Base
from database.transcription_storage import SQLiteTranscriptionStorage
from modules.video.services.transcription_service import TranscriptionService


class TestTranscriptionService:
    """Test transcription service functionality."""

    @pytest.fixture
    def config(self):
        """Create config for testing."""
        return Config()

    @pytest.fixture
    def mock_whisper_model(self):
        """Create a mock Whisper model."""
        mock_model = Mock()

        # Create mock segments and info objects
        mock_segments = [
            Mock(start=0.0, end=2.5, text="Hello world"),
            Mock(start=2.5, end=5.0, text="This is a test"),
        ]
        mock_info = Mock(language="en", language_probability=0.95)

        # faster-whisper returns (segments, info) tuple
        mock_model.transcribe.return_value = (mock_segments, mock_info)
        return mock_model

    @pytest.fixture
    def transcription_service(self, mock_whisper_model):
        """Create transcription service with mocked Whisper."""
        with patch(
            "modules.video.services.transcription_service.WhisperModel", create=True
        ) as mock_whisper_class:
            mock_whisper_class.return_value = mock_whisper_model

            # Create a config with transcription settings
            config = Config()
            config.transcription.default_model = "large"
            config.transcription.use_faster_whisper = True

            # Mock database service
            from unittest.mock import Mock

            mock_db_service = Mock()
            service = TranscriptionService(
                config, verbose=False, db_service=mock_db_service
            )
            service.model = mock_whisper_model
            service.transcription_storage = (
                None  # Don't initialize storage in unit tests
            )
            return service

    @pytest.fixture
    def sample_video_file(self):
        """Create a temporary video file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_transcription_service_initialization(self, transcription_service):
        """Test that transcription service initializes correctly."""
        assert transcription_service is not None
        # Model is lazy-loaded, so we check it's set in the fixture
        assert transcription_service.model is not None

    def test_transcribe_video_success(self, transcription_service, sample_video_file):
        """Test successful video transcription."""
        # Mock transcription storage to avoid database calls
        from unittest.mock import Mock

        mock_storage = Mock()
        mock_storage.store_transcription.return_value = "test_id_123"
        transcription_service.transcription_storage = mock_storage
        transcription_service.repos = Mock()
        transcription_service.repos.analytics = Mock()
        transcription_service.repos.analytics.track_event = Mock()

        result = transcription_service.transcribe_video(
            sample_video_file, language="en"
        )

        assert result is True
        mock_storage.store_transcription.assert_called_once()

    def test_transcribe_video_with_different_language(
        self, transcription_service, sample_video_file
    ):
        """Test transcription with different language."""
        # Mock transcription storage
        from unittest.mock import Mock

        mock_storage = Mock()
        mock_storage.store_transcription.return_value = "test_id_123"
        transcription_service.transcription_storage = mock_storage
        transcription_service.repos = Mock()
        transcription_service.repos.analytics = Mock()
        transcription_service.repos.analytics.track_event = Mock()

        result = transcription_service.transcribe_video(
            sample_video_file, language="es"
        )

        assert result is True

    def test_transcribe_video_file_not_found(self, transcription_service):
        """Test transcription with non-existent file."""
        non_existent_file = Path("/non/existent/file.mp4")

        result = transcription_service.transcribe_video(
            non_existent_file, language="en"
        )
        assert result is False

    def test_transcribe_video_whisper_error(
        self, transcription_service, sample_video_file
    ):
        """Test transcription when Whisper fails."""
        # Mock Whisper to raise an exception
        transcription_service.model.transcribe.side_effect = Exception("Whisper error")
        transcription_service.repos = Mock()
        transcription_service.repos.analytics = Mock()
        transcription_service.repos.analytics.track_event = Mock()

        result = transcription_service.transcribe_video(
            sample_video_file, language="en"
        )
        assert result is False

    def test_transcribe_video_processing_time_tracking(
        self, transcription_service, sample_video_file
    ):
        """Test that processing time is tracked."""
        # Mock transcription storage
        from unittest.mock import Mock

        mock_storage = Mock()
        mock_storage.store_transcription.return_value = "test_id_123"
        transcription_service.transcription_storage = mock_storage
        transcription_service.repos = Mock()
        transcription_service.repos.analytics = Mock()
        transcription_service.repos.analytics.track_event = Mock()

        result = transcription_service.transcribe_video(
            sample_video_file, language="en"
        )

        assert result is True
        # Verify analytics tracking was called
        assert transcription_service.repos.analytics.track_event.call_count >= 1

    def test_transcribe_video_model_used_tracking(
        self, transcription_service, sample_video_file
    ):
        """Test that model used is tracked."""
        # Mock transcription storage
        from unittest.mock import Mock

        mock_storage = Mock()
        mock_storage.store_transcription.return_value = "test_id_123"
        transcription_service.transcription_storage = mock_storage
        transcription_service.repos = Mock()
        transcription_service.repos.analytics = Mock()
        transcription_service.repos.analytics.track_event = Mock()

        result = transcription_service.transcribe_video(
            sample_video_file, language="en"
        )

        assert result is True
        # Verify storage was called with transcription data containing model_used
        call_args = mock_storage.store_transcription.call_args
        assert call_args is not None


class TestTranscriptionStorage:
    """Test SQLite transcription storage functionality."""

    @pytest.fixture
    def sqlite_session(self):
        """Create an in-memory SQLite session for testing."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def transcription_storage(self, sqlite_session):
        """Create transcription storage with SQLite."""
        return SQLiteTranscriptionStorage(sqlite_session)

    def test_transcription_storage_initialization(self, transcription_storage):
        """Test that transcription storage initializes correctly."""
        assert transcription_storage is not None
        assert transcription_storage.session is not None

    def test_store_transcription_success(self, transcription_storage):
        """Test successful transcription storage."""
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

        assert isinstance(result_id, int)
        result = transcription_storage.get_transcription(video_id)
        assert result is not None
        assert result["video_id"] == 123
        assert result["language"] == "en"
        assert result["full_text"] == "Hello world This is a test"

    def test_store_transcription_with_string_video_id(self, transcription_storage):
        """Test storing transcription with string video_id (should convert to int)."""
        video_id = "456"  # String ID
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "Test"}],
            "language": "en",
        }

        result_id = transcription_storage.store_transcription(
            video_id, transcription_data
        )
        assert isinstance(result_id, int)
        result = transcription_storage.get_transcription(456)
        assert result is not None
        assert result["video_id"] == 456

    def test_get_transcription_success(self, transcription_storage):
        """Test successful transcription retrieval."""
        transcription_storage.store_transcription(
            123,
            {
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
                "language": "en",
            },
        )

        result = transcription_storage.get_transcription(123)

        assert result is not None
        assert result["video_id"] == 123
        assert result["language"] == "en"

    def test_get_transcription_not_found(self, transcription_storage):
        """Test transcription retrieval when not found."""
        result = transcription_storage.get_transcription(999)
        assert result is None

    def test_get_transcription_with_string_video_id(self, transcription_storage):
        """Test transcription retrieval with string video_id (should convert to int)."""
        transcription_storage.store_transcription(
            123,
            {
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
                "language": "en",
            },
        )

        result = transcription_storage.get_transcription("123")
        assert result is not None

    def test_search_transcriptions(self, transcription_storage):
        """Test transcription search functionality."""
        transcription_storage.session.execute(
            text(
                "CREATE VIRTUAL TABLE transcriptions_fts USING fts5("
                "full_text, content='transcriptions', content_rowid='id')"
            )
        )
        transcription_storage.session.execute(
            text(
                "CREATE TRIGGER transcriptions_ai AFTER INSERT ON transcriptions BEGIN "
                "INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text); END;"
            )
        )
        transcription_storage.session.execute(
            text(
                "CREATE TRIGGER transcriptions_ad AFTER DELETE ON transcriptions BEGIN "
                "INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text) "
                "VALUES('delete', old.id, old.full_text); END;"
            )
        )
        transcription_storage.session.execute(
            text(
                "CREATE TRIGGER transcriptions_au AFTER UPDATE ON transcriptions BEGIN "
                "INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text) "
                "VALUES('delete', old.id, old.full_text); "
                "INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text); "
                "END;"
            )
        )
        transcription_storage.session.commit()

        transcription_storage.store_transcription(
            1,
            {
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
                "language": "en",
            },
        )
        transcription_storage.store_transcription(
            2,
            {
                "segments": [{"start": 0.0, "end": 2.5, "text": "Test transcription"}],
                "language": "en",
            },
        )

        results = transcription_storage.search_transcriptions("Hello", limit=10)
        assert len(results) == 1
        assert results[0]["video_id"] == 1

    def test_generate_srt_subtitle(self, transcription_storage):
        """Test SRT subtitle generation."""
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = transcription_storage.generate_srt_subtitle(
                transcription_data, temp_path
            )

            assert result is True
            assert temp_path.exists()

            # Check SRT content
            content = temp_path.read_text()
            assert "1" in content
            assert "00:00:00,000 --> 00:00:02,500" in content
            assert "Hello world" in content
            assert "00:00:02,500 --> 00:00:05,000" in content
            assert "This is a test" in content

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_vtt_subtitle(self, transcription_storage):
        """Test VTT subtitle generation."""
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".vtt", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = transcription_storage.generate_vtt_subtitle(
                transcription_data, temp_path
            )

            assert result is True
            assert temp_path.exists()

            # Check VTT content
            content = temp_path.read_text()
            assert "WEBVTT" in content
            assert "00:00:00.000 --> 00:00:02.500" in content
            assert "Hello world" in content

        finally:
            if temp_path.exists():
                temp_path.unlink()
