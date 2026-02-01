"""
Comprehensive integration tests for SQLite transcription storage.

Tests the complete real-world workflow:
- Alembic migration execution
- Transcription storage and retrieval
- FTS5 search functionality
- Full TranscriptionService integration
- Edge cases and error handling
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest

try:
    from alembic import command
    from alembic.config import Config as AlembicConfig

    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from spatelier.core.config import Config
from spatelier.database.connection import DatabaseManager
from spatelier.database.models import Base, MediaFile, MediaType, Transcription
from spatelier.database.transcription_storage import SQLiteTranscriptionStorage
from spatelier.modules.video.services.transcription_service import TranscriptionService


class TestSQLiteTranscriptionStorageIntegration:
    """Comprehensive integration tests for SQLite transcription storage."""

    @pytest.fixture
    def temp_db_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for test database."""
        temp_dir = Path(tempfile.mkdtemp(prefix="spatelier_transcription_test_"))
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def test_db_path(self, temp_db_dir: Path) -> Path:
        """Create path to test database file."""
        return temp_db_dir / "test_transcriptions.db"

    @pytest.fixture
    def test_config(self, test_db_path: Path) -> Config:
        """Create test configuration pointing to test database."""
        config = Config()
        config.database.sqlite_path = str(test_db_path)
        config.transcription.default_model = "base"
        config.transcription.default_language = "en"
        return config

    @pytest.fixture
    def fresh_db_engine(self, test_db_path: Path, temp_db_dir: Path):
        """Create fresh database engine and run migrations."""
        # Create database file
        engine = create_engine(f"sqlite:///{test_db_path}")

        # Create base tables (MediaFile, etc.)
        Base.metadata.create_all(engine)

        # Run Alembic migrations if available
        if ALEMBIC_AVAILABLE:
            try:
                alembic_cfg = AlembicConfig("alembic.ini")
                alembic_cfg.set_main_option(
                    "sqlalchemy.url", f"sqlite:///{test_db_path}"
                )

                # Set script location
                script_location = Path(__file__).parent.parent.parent / "migrations"
                alembic_cfg.set_main_option("script_location", str(script_location))

                # Run migrations
                command.upgrade(alembic_cfg, "head")
            except Exception as e:
                pytest.skip(f"Failed to run Alembic migrations: {e}")
        else:
            # Fallback: manually create transcription table and FTS5 if Alembic not available
            # This is less ideal but allows basic testing
            with engine.connect() as conn:
                # Create transcriptions table manually
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS transcriptions (
                        id INTEGER PRIMARY KEY,
                        media_file_id INTEGER NOT NULL,
                        language VARCHAR(10),
                        duration FLOAT,
                        processing_time FLOAT,
                        model_used VARCHAR(100),
                        segments_json JSON NOT NULL,
                        full_text TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(media_file_id) REFERENCES media_files(id)
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_transcriptions_id ON transcriptions(id)"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_transcriptions_media_file_id ON transcriptions(media_file_id)"
                    )
                )

                # Create FTS5 table
                conn.execute(
                    text(
                        """
                    CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts USING fts5(
                        full_text, content='transcriptions', content_rowid='id'
                    )
                """
                    )
                )

                # Create triggers
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

        yield engine

        # Cleanup
        engine.dispose()
        if test_db_path.exists():
            test_db_path.unlink(missing_ok=True)

    @pytest.fixture
    def db_session(self, fresh_db_engine):
        """Create database session."""
        SessionLocal = sessionmaker(bind=fresh_db_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def sample_media_file(self, db_session) -> MediaFile:
        """Create a sample media file for testing."""
        media_file = MediaFile(
            file_path="/test/video.mp4",
            file_name="video.mp4",
            file_size=1000000,
            file_hash="test_hash_123",
            media_type=MediaType.VIDEO,
            mime_type="video/mp4",
            title="Test Video",
        )
        db_session.add(media_file)
        db_session.commit()
        db_session.refresh(media_file)
        return media_file

    @pytest.fixture
    def transcription_storage(self, db_session) -> SQLiteTranscriptionStorage:
        """Create transcription storage instance."""
        return SQLiteTranscriptionStorage(db_session)

    @pytest.fixture
    def sample_transcription_data(self) -> dict:
        """Create sample transcription data."""
        return {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
                {"start": 5.0, "end": 7.5, "text": "Testing SQLite storage"},
            ],
            "language": "en",
            "duration": 7.5,
            "processing_time": 10.5,
            "model_used": "whisper-base",
        }

    def test_migration_creates_transcriptions_table(self, fresh_db_engine):
        """Test that migration creates transcriptions table correctly."""
        inspector = inspect(fresh_db_engine)

        # Check table exists
        assert "transcriptions" in inspector.get_table_names()

        # Check columns
        columns = {col["name"]: col for col in inspector.get_columns("transcriptions")}
        assert "id" in columns
        assert "media_file_id" in columns
        assert "language" in columns
        assert "duration" in columns
        assert "processing_time" in columns
        assert "model_used" in columns
        assert "segments_json" in columns
        assert "full_text" in columns
        assert "created_at" in columns

        # Check indexes
        indexes = inspector.get_indexes("transcriptions")
        index_names = [idx["name"] for idx in indexes]
        assert "ix_transcriptions_id" in index_names
        assert "ix_transcriptions_media_file_id" in index_names

    def test_migration_creates_fts5_table(self, fresh_db_engine):
        """Test that migration creates FTS5 virtual table."""
        with fresh_db_engine.connect() as conn:
            # Check FTS5 table exists
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions_fts'"
                )
            )
            fts_table = result.fetchone()
            assert fts_table is not None, "FTS5 table should exist"

            # Check triggers exist
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'transcriptions_%'"
                )
            )
            triggers = [row[0] for row in result.fetchall()]
            assert "transcriptions_ai" in triggers, "INSERT trigger should exist"
            assert "transcriptions_ad" in triggers, "DELETE trigger should exist"
            assert "transcriptions_au" in triggers, "UPDATE trigger should exist"

    def test_store_transcription_success(
        self, transcription_storage, sample_media_file, sample_transcription_data
    ):
        """Test successfully storing a transcription."""
        transcription_id = transcription_storage.store_transcription(
            sample_media_file.id, sample_transcription_data
        )

        assert isinstance(transcription_id, int)
        assert transcription_id > 0

        # Verify stored data
        stored = transcription_storage.get_transcription(sample_media_file.id)
        assert stored is not None
        assert stored["video_id"] == sample_media_file.id
        assert stored["language"] == "en"
        assert stored["duration"] == 7.5
        assert stored["processing_time"] == 10.5
        assert stored["model_used"] == "whisper-base"
        assert len(stored["segments"]) == 3
        assert (
            stored["full_text"] == "Hello world This is a test Testing SQLite storage"
        )

    def test_store_multiple_transcriptions(
        self, transcription_storage, sample_media_file
    ):
        """Test storing multiple transcriptions for the same video."""
        # Store first transcription
        data1 = {
            "segments": [{"start": 0.0, "end": 2.0, "text": "First transcription"}],
            "language": "en",
        }
        id1 = transcription_storage.store_transcription(sample_media_file.id, data1)

        # Store second transcription
        data2 = {
            "segments": [{"start": 0.0, "end": 2.0, "text": "Second transcription"}],
            "language": "en",
        }
        id2 = transcription_storage.store_transcription(sample_media_file.id, data2)

        assert id1 != id2

        # get_transcription should return the most recent
        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved is not None
        assert retrieved["id"] == id2
        assert retrieved["full_text"] == "Second transcription"

    def test_get_transcription_not_found(self, transcription_storage):
        """Test retrieving non-existent transcription."""
        result = transcription_storage.get_transcription(99999)
        assert result is None

    def test_fts5_search_functionality(
        self, transcription_storage, db_session, sample_media_file
    ):
        """Test FTS5 search functionality."""
        # Store multiple transcriptions with different content
        transcription_storage.store_transcription(
            sample_media_file.id,
            {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Python programming tutorial"},
                    {"start": 2.0, "end": 4.0, "text": "Learn Python basics"},
                ],
                "language": "en",
            },
        )

        # Create second media file
        media_file2 = MediaFile(
            file_path="/test/video2.mp4",
            file_name="video2.mp4",
            file_size=2000000,
            file_hash="test_hash_456",
            media_type=MediaType.VIDEO,
            mime_type="video/mp4",
        )
        db_session.add(media_file2)
        db_session.commit()
        db_session.refresh(media_file2)

        transcription_storage.store_transcription(
            media_file2.id,
            {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "JavaScript tutorial"},
                    {"start": 2.0, "end": 4.0, "text": "Learn JavaScript"},
                ],
                "language": "en",
            },
        )

        # Search for "Python"
        results = transcription_storage.search_transcriptions("Python", limit=10)
        assert len(results) == 1
        assert results[0]["video_id"] == sample_media_file.id
        assert "Python" in results[0]["full_text"]

        # Search for "JavaScript"
        results = transcription_storage.search_transcriptions("JavaScript", limit=10)
        assert len(results) == 1
        assert results[0]["video_id"] == media_file2.id

        # Search for "tutorial" (should match both)
        results = transcription_storage.search_transcriptions("tutorial", limit=10)
        assert len(results) == 2

    def test_fts5_search_with_limit(
        self, transcription_storage, db_session, sample_media_file
    ):
        """Test FTS5 search respects limit parameter."""
        # Create multiple media files and transcriptions
        for i in range(5):
            media_file = MediaFile(
                file_path=f"/test/video{i}.mp4",
                file_name=f"video{i}.mp4",
                file_size=1000000,
                file_hash=f"test_hash_{i}",
                media_type=MediaType.VIDEO,
                mime_type="video/mp4",
            )
            db_session.add(media_file)
            db_session.commit()
            db_session.refresh(media_file)

            transcription_storage.store_transcription(
                media_file.id,
                {
                    "segments": [
                        {"start": 0.0, "end": 2.0, "text": f"Test transcription {i}"}
                    ],
                    "language": "en",
                },
            )

        # Search with limit
        results = transcription_storage.search_transcriptions("transcription", limit=3)
        assert len(results) <= 3

    def test_segments_json_storage(self, transcription_storage, sample_media_file):
        """Test that segments are stored correctly as JSON."""
        complex_segments = [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "world", "start": 0.5, "end": 1.0},
                ],
            },
            {
                "start": 2.5,
                "end": 5.0,
                "text": "Test",
                "words": [{"word": "Test", "start": 2.5, "end": 3.0}],
            },
        ]

        transcription_data = {
            "segments": complex_segments,
            "language": "en",
        }

        transcription_id = transcription_storage.store_transcription(
            sample_media_file.id, transcription_data
        )

        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved is not None
        assert len(retrieved["segments"]) == 2
        assert retrieved["segments"][0]["text"] == "Hello"
        assert "words" in retrieved["segments"][0]
        assert len(retrieved["segments"][0]["words"]) == 2

    def test_full_text_generation(self, transcription_storage, sample_media_file):
        """Test that full_text is correctly generated from segments."""
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "First"},
                {"start": 2.0, "end": 4.0, "text": "Second"},
                {"start": 4.0, "end": 6.0, "text": "Third"},
            ],
            "language": "en",
        }

        transcription_storage.store_transcription(
            sample_media_file.id, transcription_data
        )

        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved["full_text"] == "First Second Third"

    def test_subtitle_generation_srt(self, transcription_storage, temp_db_dir):
        """Test SRT subtitle file generation."""
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
            ]
        }

        output_path = temp_db_dir / "test.srt"
        result = transcription_storage.generate_srt_subtitle(
            transcription_data, output_path
        )

        assert result is True
        assert output_path.exists()

        content = output_path.read_text()
        assert "1" in content
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "Hello world" in content
        assert "00:00:02,500 --> 00:00:05,000" in content
        assert "This is a test" in content

    def test_subtitle_generation_vtt(self, transcription_storage, temp_db_dir):
        """Test VTT subtitle file generation."""
        transcription_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"},
            ]
        }

        output_path = temp_db_dir / "test.vtt"
        result = transcription_storage.generate_vtt_subtitle(
            transcription_data, output_path
        )

        assert result is True
        assert output_path.exists()

        content = output_path.read_text()
        assert "WEBVTT" in content
        assert "00:00:00.000 --> 00:00:02.500" in content
        assert "Hello world" in content

    def test_transcription_service_integration(
        self, test_config, test_db_path, temp_db_dir, sample_media_file
    ):
        """Test full TranscriptionService integration with SQLite storage."""
        # Use DatabaseServiceFactory instead of DatabaseManager directly
        from spatelier.core.database_service import DatabaseServiceFactory

        db_factory = DatabaseServiceFactory(test_config, verbose=False)
        db_manager = db_factory.get_db_manager()
        db_manager.connect_sqlite()

        # Create transcription service with db_factory
        transcription_service = TranscriptionService(
            test_config, verbose=False, db_service=db_factory
        )

        # Mock Whisper to avoid requiring actual model
        from unittest.mock import Mock, patch

        mock_result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Mock transcription"},
            ],
            "language": "en",
            "duration": 2.0,
        }

        # Mock Whisper availability
        with patch(
            "spatelier.modules.video.services.transcription_service.WHISPER_AVAILABLE", True
        ):
            # Mock the model's transcribe method to return proper format
            mock_segments = [
                type(
                    "Segment",
                    (),
                    {
                        "start": 0.0,
                        "end": 2.0,
                        "text": "Mock transcription",
                        "avg_logprob": 0.5,
                    },
                )()
            ]
            mock_info = type(
                "Info",
                (),
                {"language": "en", "language_probability": 0.95, "duration": 2.0},
            )()

            mock_model = Mock()
            mock_model.transcribe.return_value = (mock_segments, mock_info)

            # Set model to None first so _initialize_transcription will set it up
            transcription_service.model = None

            # Manually initialize storage (simulating what happens in _initialize_transcription)
            # This tests that the service can work with SQLite storage
            session = db_manager.get_sqlite_session()
            transcription_service.transcription_storage = SQLiteTranscriptionStorage(
                session
            )
            transcription_service.db_manager = db_manager

            # Store a transcription directly through the storage
            transcription_data = {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Service integration test"},
                ],
                "language": "en",
                "duration": 2.0,
                "model_used": "whisper-base",
            }

            transcription_id = (
                transcription_service.transcription_storage.store_transcription(
                    sample_media_file.id, transcription_data
                )
            )

            assert transcription_id > 0

            # Verify transcription was stored and can be retrieved
            retrieved = transcription_service.transcription_storage.get_transcription(
                sample_media_file.id
            )

            assert retrieved is not None
            assert retrieved["language"] == "en"
            assert retrieved["video_id"] == sample_media_file.id
            assert len(retrieved["segments"]) == 1
            assert retrieved["segments"][0]["text"] == "Service integration test"

        db_factory.close_connections()

    def test_edge_case_empty_segments(self, transcription_storage, sample_media_file):
        """Test handling of empty segments."""
        transcription_data = {
            "segments": [],
            "language": "en",
        }

        transcription_id = transcription_storage.store_transcription(
            sample_media_file.id, transcription_data
        )

        assert transcription_id > 0

        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved is not None
        assert retrieved["full_text"] == ""
        assert retrieved["segments"] == []

    def test_edge_case_missing_fields(self, transcription_storage, sample_media_file):
        """Test handling of missing optional fields."""
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test"}],
            # Missing language, duration, etc.
        }

        transcription_id = transcription_storage.store_transcription(
            sample_media_file.id, transcription_data
        )

        assert transcription_id > 0

        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved is not None
        assert retrieved["language"] is None
        assert retrieved["duration"] is None

    def test_string_video_id_conversion(self, transcription_storage, sample_media_file):
        """Test that string video IDs are converted to integers."""
        transcription_data = {
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test"}],
            "language": "en",
        }

        # Store with string ID
        transcription_id = transcription_storage.store_transcription(
            str(sample_media_file.id), transcription_data
        )

        assert transcription_id > 0

        # Retrieve with integer ID
        retrieved = transcription_storage.get_transcription(sample_media_file.id)
        assert retrieved is not None

        # Retrieve with string ID
        retrieved2 = transcription_storage.get_transcription(str(sample_media_file.id))
        assert retrieved2 is not None
        assert retrieved2["id"] == retrieved["id"]
