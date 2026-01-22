"""
Tests for metadata extraction functionality.

This module tests metadata extraction from various sources.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from core.config import Config
from database.metadata import MetadataExtractor, MetadataManager
from database.models import MediaFile, MediaType
from database.repository import MediaFileRepository


@pytest.fixture
def config():
    """Create test configuration."""
    return Config()


@pytest.fixture
def metadata_extractor(config):
    """Create MetadataExtractor instance."""
    return MetadataExtractor(config, verbose=False)


@pytest.fixture
def metadata_manager(config):
    """Create MetadataManager instance."""
    return MetadataManager(config, verbose=False)


def test_metadata_extractor_initialization(metadata_extractor):
    """Test MetadataExtractor initialization."""
    assert metadata_extractor.config is not None
    assert metadata_extractor.verbose == False
    assert metadata_extractor.logger is not None


def test_metadata_extractor_parse_youtube_metadata(metadata_extractor):
    """Test parsing YouTube metadata."""
    # Sample YouTube metadata from yt-dlp
    youtube_metadata = {
        "title": "Test Video Title",
        "description": "This is a test video description",
        "uploader": "Test Channel",
        "uploader_id": "testchannel123",
        "webpage_url": "https://youtube.com/watch?v=test123",
        "id": "test123",
        "upload_date": "20230101",
        "view_count": 10000,
        "like_count": 500,
        "dislike_count": 10,
        "comment_count": 100,
        "tags": ["test", "video", "demo"],
        "categories": ["Entertainment", "Education"],
        "language": "en",
        "age_limit": 0,
        "duration": 120.5,
        "thumbnail": "https://img.youtube.com/vi/test123/maxresdefault.jpg",
        "formats": [
            {
                "vcodec": "avc1",
                "acodec": "mp4a",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "tbr": 2000,
            }
        ],
    }

    parsed = metadata_extractor._parse_youtube_metadata(youtube_metadata)

    assert parsed["title"] == "Test Video Title"
    assert parsed["description"] == "This is a test video description"
    assert parsed["uploader"] == "Test Channel"
    assert parsed["uploader_id"] == "testchannel123"
    assert parsed["source_url"] == "https://youtube.com/watch?v=test123"
    assert parsed["source_platform"] == "youtube"
    assert parsed["source_id"] == "test123"
    assert parsed["view_count"] == 10000
    assert parsed["like_count"] == 500
    assert parsed["dislike_count"] == 10
    assert parsed["comment_count"] == 100
    assert parsed["language"] == "en"
    assert parsed["age_limit"] == 0
    assert parsed["duration"] == 120.5
    assert (
        parsed["thumbnail_url"]
        == "https://img.youtube.com/vi/test123/maxresdefault.jpg"
    )
    assert parsed["width"] == 1920
    assert parsed["height"] == 1080
    assert parsed["fps"] == 30
    assert parsed["video_codec"] == "avc1"
    assert parsed["audio_codec"] == "mp4a"
    assert parsed["bitrate"] == 2000
    assert json.loads(parsed["tags"]) == ["test", "video", "demo"]
    assert json.loads(parsed["categories"]) == ["Entertainment", "Education"]


def test_metadata_extractor_parse_ffprobe_metadata(metadata_extractor):
    """Test parsing ffprobe metadata."""
    # Sample ffprobe output
    ffprobe_data = {
        "format": {"duration": "120.5", "bit_rate": "2000000"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "display_aspect_ratio": "16:9",
                "color_space": "bt709",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "44100",
                "channels": 2,
            },
        ],
    }

    parsed = metadata_extractor._parse_ffprobe_metadata(ffprobe_data)

    assert parsed["duration"] == 120.5
    assert parsed["bitrate"] == 2000000
    assert parsed["width"] == 1920
    assert parsed["height"] == 1080
    assert parsed["fps"] == 30.0
    assert parsed["video_codec"] == "h264"
    assert parsed["aspect_ratio"] == "16:9"
    assert parsed["color_space"] == "bt709"
    assert parsed["audio_codec"] == "aac"
    assert parsed["sample_rate"] == "44100"
    assert parsed["channels"] == 2


def test_metadata_extractor_parse_fps():
    """Test FPS parsing from fraction strings."""
    extractor = MetadataExtractor(Config(), verbose=False)

    # Test valid fractions
    assert extractor._parse_fps("30/1") == 30.0
    assert extractor._parse_fps("29.97/1") == 29.97
    assert extractor._parse_fps("25/1") == 25.0

    # Test invalid fractions
    assert extractor._parse_fps("invalid") is None
    assert extractor._parse_fps("") is None
    assert extractor._parse_fps("30/0") is None


@patch("yt_dlp.YoutubeDL")
def test_metadata_extractor_extract_youtube_metadata(
    mock_ydl_class, metadata_extractor
):
    """Test YouTube metadata extraction."""
    # Mock successful yt-dlp output
    mock_output = {
        "title": "Test Video",
        "uploader": "Test Channel",
        "view_count": 1000,
        "duration": 120.5,
    }

    # Mock the YoutubeDL instance
    mock_ydl_instance = Mock()
    mock_ydl_instance.extract_info.return_value = mock_output
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance

    result = metadata_extractor.extract_youtube_metadata(
        "https://youtube.com/watch?v=test"
    )

    assert result["title"] == "Test Video"
    assert result["uploader"] == "Test Channel"
    assert result["view_count"] == 1000
    assert result["duration"] == 120.5


@patch("yt_dlp.YoutubeDL")
def test_metadata_extractor_extract_youtube_metadata_failure(
    mock_ydl_class, metadata_extractor
):
    """Test YouTube metadata extraction failure."""
    # Mock failed yt-dlp output
    mock_ydl_instance = Mock()
    mock_ydl_instance.extract_info.side_effect = Exception(
        "ERROR: [youtube] test: Video unavailable"
    )
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance

    result = metadata_extractor.extract_youtube_metadata(
        "https://youtube.com/watch?v=test"
    )

    assert result == {}


@patch("ffmpeg.probe")
@patch("pathlib.Path.exists")
def test_metadata_extractor_extract_file_metadata(
    mock_exists, mock_probe, metadata_extractor
):
    """Test file metadata extraction."""
    # Mock file exists
    mock_exists.return_value = True

    # Mock successful ffprobe output
    mock_output = {
        "format": {"duration": "120.5", "bit_rate": "2000000"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}
        ],
    }

    mock_probe.return_value = mock_output

    result = metadata_extractor.extract_file_metadata("/test/video.mp4")

    assert result["duration"] == 120.5
    assert result["bitrate"] == 2000000
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["video_codec"] == "h264"


def test_metadata_manager_initialization(metadata_manager):
    """Test MetadataManager initialization."""
    assert metadata_manager.config is not None
    assert metadata_manager.verbose == False
    assert metadata_manager.extractor is not None


def test_metadata_manager_enrich_media_file(metadata_manager):
    """Test enriching media file with metadata."""
    # Create a mock media file
    media_file = Mock()
    media_file.file_path = "/test/video.mp4"
    media_file.source_url = "https://youtube.com/watch?v=test"

    # Create a mock repository
    repository = Mock()
    repository.session = Mock()
    repository.session.commit = Mock()
    repository.session.refresh = Mock()

    # Mock metadata extraction
    with (
        patch.object(
            metadata_manager.extractor, "extract_file_metadata"
        ) as mock_file_meta,
        patch.object(
            metadata_manager.extractor, "extract_youtube_metadata"
        ) as mock_youtube_meta,
        patch.object(
            metadata_manager.extractor, "update_media_file_metadata"
        ) as mock_update,
    ):
        mock_file_meta.return_value = {"duration": 120.5, "width": 1920}
        mock_youtube_meta.return_value = {
            "title": "Test Video",
            "uploader": "Test Channel",
        }
        mock_update.return_value = media_file

        result = metadata_manager.enrich_media_file(media_file, repository)

        assert result == media_file
        mock_file_meta.assert_called_once_with("/test/video.mp4")
        mock_youtube_meta.assert_called_once_with("https://youtube.com/watch?v=test")
        assert mock_update.call_count == 2  # Called for file and YouTube metadata


def test_metadata_manager_batch_enrich_media_files(metadata_manager):
    """Test batch enriching multiple media files."""
    # Create mock repository with mock query
    repository = Mock()
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [Mock(), Mock()]
    repository.session.query.return_value = mock_query

    # Mock enrich_media_file method
    with patch.object(metadata_manager, "enrich_media_file") as mock_enrich:
        mock_enrich.return_value = Mock()

        result = metadata_manager.batch_enrich_media_files(repository, limit=10)

        assert len(result) == 2
        assert mock_enrich.call_count == 2


def test_metadata_manager_batch_enrich_with_media_type(metadata_manager):
    """Test batch enriching with media type filter."""
    # Create mock repository
    repository = Mock()
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [Mock()]
    repository.session.query.return_value = mock_query

    # Mock enrich_media_file method
    with patch.object(metadata_manager, "enrich_media_file") as mock_enrich:
        mock_enrich.return_value = Mock()

        result = metadata_manager.batch_enrich_media_files(
            repository, limit=10, media_type="video"
        )

        assert len(result) == 1
        mock_query.filter.assert_called_once()
        mock_enrich.assert_called_once()


def test_metadata_extractor_update_media_file_metadata(metadata_extractor):
    """Test updating media file with metadata."""
    # Create a mock media file
    media_file = Mock()
    media_file.id = 1

    # Create a mock repository
    repository = Mock()
    repository.session = Mock()
    repository.session.commit = Mock()
    repository.session.refresh = Mock()

    # Test metadata update
    metadata = {"title": "Test Video", "duration": 120.5, "width": 1920, "height": 1080}

    result = metadata_extractor.update_media_file_metadata(
        media_file, metadata, repository
    )

    # Check that attributes were set
    assert media_file.title == "Test Video"
    assert media_file.duration == 120.5
    assert media_file.width == 1920
    assert media_file.height == 1080

    # Check that session methods were called
    repository.session.commit.assert_called_once()
    repository.session.refresh.assert_called_once_with(media_file)

    assert result == media_file
