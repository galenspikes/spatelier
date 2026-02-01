"""
Custom assertion functions for testing.

Provides specialized assertion functions for testing
specific aspects of the spatelier application.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from spatelier.utils.helpers import get_file_hash, get_file_size, get_file_type


def assert_video_file_valid(file_path: Union[str, Path], message: str = None) -> None:
    """Assert that a file is a valid video file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise AssertionError(f"Video file does not exist: {file_path}")

    file_type = get_file_type(file_path)
    if file_type.value not in ["video"]:
        msg = message or f"File is not a video: {file_path} (type: {file_type})"
        raise AssertionError(msg)


def assert_audio_file_valid(file_path: Union[str, Path], message: str = None) -> None:
    """Assert that a file is a valid audio file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise AssertionError(f"Audio file does not exist: {file_path}")

    file_type = get_file_type(file_path)
    if file_type.value not in ["audio"]:
        msg = message or f"File is not an audio file: {file_path} (type: {file_type})"
        raise AssertionError(msg)


def assert_file_hash_matches(
    file_path: Union[str, Path], expected_hash: str, message: str = None
) -> None:
    """Assert that a file has the expected hash."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise AssertionError(f"File does not exist: {file_path}")

    actual_hash = get_file_hash(file_path)
    if actual_hash != expected_hash:
        msg = (
            message
            or f"File hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
        raise AssertionError(msg)


def assert_file_size_within_range(
    file_path: Union[str, Path], min_size: int, max_size: int, message: str = None
) -> None:
    """Assert that a file size is within the specified range."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise AssertionError(f"File does not exist: {file_path}")

    actual_size = get_file_size(file_path)
    if not (min_size <= actual_size <= max_size):
        msg = (
            message or f"File size {actual_size} not in range [{min_size}, {max_size}]"
        )
        raise AssertionError(msg)


def assert_transcription_data_valid(
    transcription_data: Dict[str, Any], message: str = None
) -> None:
    """Assert that transcription data is valid."""
    required_fields = ["language", "duration", "segments", "text"]
    for field in required_fields:
        if field not in transcription_data:
            msg = message or f"Transcription data missing required field: {field}"
            raise AssertionError(msg)

    # Check segments structure
    segments = transcription_data.get("segments", [])
    if not isinstance(segments, list):
        msg = message or "Transcription segments must be a list"
        raise AssertionError(msg)

    for i, segment in enumerate(segments):
        segment_fields = ["id", "start", "end", "text"]
        for field in segment_fields:
            if field not in segment:
                msg = message or f"Segment {i} missing required field: {field}"
                raise AssertionError(msg)


def assert_srt_content_valid(srt_content: str, message: str = None) -> None:
    """Assert that SRT content is valid."""
    lines = srt_content.strip().split("\n")
    if not lines:
        msg = message or "SRT content is empty"
        raise AssertionError(msg)

    # Check for basic SRT structure
    i = 0
    while i < len(lines):
        # Should have sequence number
        if not lines[i].strip().isdigit():
            msg = message or f"Invalid SRT sequence number at line {i+1}: {lines[i]}"
            raise AssertionError(msg)
        i += 1

        # Should have timestamp
        if i >= len(lines) or "-->" not in lines[i]:
            msg = (
                message
                or f"Invalid SRT timestamp at line {i+1}: {lines[i] if i < len(lines) else 'EOF'}"
            )
            raise AssertionError(msg)
        i += 1

        # Should have text (can be empty)
        if i < len(lines):
            i += 1
            # Skip empty lines
            while i < len(lines) and not lines[i].strip():
                i += 1


def assert_vtt_content_valid(vtt_content: str, message: str = None) -> None:
    """Assert that VTT content is valid."""
    if not vtt_content.startswith("WEBVTT"):
        msg = message or "VTT content must start with 'WEBVTT'"
        raise AssertionError(msg)

    if "-->" not in vtt_content:
        msg = message or "VTT content must contain timestamp arrows"
        raise AssertionError(msg)


def assert_database_record_exists(session, model_class, **filters) -> None:
    """Assert that a database record exists."""
    record = session.query(model_class).filter_by(**filters).first()
    if record is None:
        msg = f"Database record not found for {model_class.__name__} with filters: {filters}"
        raise AssertionError(msg)


def assert_database_record_not_exists(session, model_class, **filters) -> None:
    """Assert that a database record does not exist."""
    record = session.query(model_class).filter_by(**filters).first()
    if record is not None:
        msg = f"Database record should not exist for {model_class.__name__} with filters: {filters}"
        raise AssertionError(msg)


def assert_processing_job_status(
    session, job_id: int, expected_status: str, message: str = None
) -> None:
    """Assert that a processing job has the expected status."""
    from spatelier.database.models import ProcessingJob

    job = session.query(ProcessingJob).filter_by(id=job_id).first()
    if job is None:
        msg = message or f"Processing job {job_id} not found"
        raise AssertionError(msg)

    if job.status != expected_status:
        msg = (
            message
            or f"Job {job_id} status mismatch: expected {expected_status}, got {job.status}"
        )
        raise AssertionError(msg)


def assert_media_file_metadata(
    session, media_file_id: int, expected_metadata: Dict[str, Any], message: str = None
) -> None:
    """Assert that a media file has the expected metadata."""
    from spatelier.database.models import MediaFile

    media_file = session.query(MediaFile).filter_by(id=media_file_id).first()
    if media_file is None:
        msg = message or f"Media file {media_file_id} not found"
        raise AssertionError(msg)

    for key, expected_value in expected_metadata.items():
        actual_value = getattr(media_file, key, None)
        if actual_value != expected_value:
            msg = (
                message
                or f"Media file {media_file_id} metadata mismatch for {key}: expected {expected_value}, got {actual_value}"
            )
            raise AssertionError(msg)


def assert_analytics_event_tracked(
    session,
    event_type: str,
    media_file_id: int = None,
    processing_job_id: int = None,
    message: str = None,
) -> None:
    """Assert that an analytics event was tracked."""
    from spatelier.database.models import AnalyticsEvent

    query = session.query(AnalyticsEvent).filter_by(event_type=event_type)
    if media_file_id is not None:
        query = query.filter_by(media_file_id=media_file_id)
    if processing_job_id is not None:
        query = query.filter_by(processing_job_id=processing_job_id)

    event = query.first()
    if event is None:
        msg = message or f"Analytics event {event_type} not tracked"
        raise AssertionError(msg)


def assert_config_valid(config: Dict[str, Any], message: str = None) -> None:
    """Assert that a configuration is valid."""
    required_sections = ["core", "database", "video", "audio", "logging"]
    for section in required_sections:
        if section not in config:
            msg = message or f"Configuration missing section: {section}"
            raise AssertionError(msg)

    # Check database configuration
    if "sqlite_path" not in config["database"]:
        msg = message or "Database configuration missing sqlite_path"
        raise AssertionError(msg)

    # Check video configuration
    if "output_dir" not in config["video"]:
        msg = message or "Video configuration missing output_dir"
        raise AssertionError(msg)


def assert_log_level_valid(level: str, message: str = None) -> None:
    """Assert that a log level is valid."""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        msg = message or f"Invalid log level: {level}. Must be one of {valid_levels}"
        raise AssertionError(msg)


def assert_file_permissions(
    file_path: Union[str, Path], expected_permissions: int, message: str = None
) -> None:
    """Assert that a file has the expected permissions."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise AssertionError(f"File does not exist: {file_path}")

    actual_permissions = file_path.stat().st_mode & 0o777
    if actual_permissions != expected_permissions:
        msg = (
            message
            or f"File permissions mismatch: expected {oct(expected_permissions)}, got {oct(actual_permissions)}"
        )
        raise AssertionError(msg)


def assert_directory_permissions(
    dir_path: Union[str, Path], expected_permissions: int, message: str = None
) -> None:
    """Assert that a directory has the expected permissions."""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        raise AssertionError(f"Directory does not exist: {dir_path}")

    if not dir_path.is_dir():
        raise AssertionError(f"Path is not a directory: {dir_path}")

    actual_permissions = dir_path.stat().st_mode & 0o777
    if actual_permissions != expected_permissions:
        msg = (
            message
            or f"Directory permissions mismatch: expected {oct(expected_permissions)}, got {oct(actual_permissions)}"
        )
        raise AssertionError(msg)


def assert_json_valid(json_string: str, message: str = None) -> None:
    """Assert that a string is valid JSON."""
    try:
        json.loads(json_string)
    except json.JSONDecodeError as e:
        msg = message or f"Invalid JSON: {e}"
        raise AssertionError(msg)


def assert_timestamp_recent(
    timestamp: Union[str, float], max_age_seconds: int = 300, message: str = None
) -> None:
    """Assert that a timestamp is recent."""
    if isinstance(timestamp, str):
        # Parse ISO format timestamp
        from datetime import datetime

        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        timestamp = dt.timestamp()

    current_time = time.time()
    age = current_time - timestamp

    if age > max_age_seconds:
        msg = message or f"Timestamp is too old: {age}s > {max_age_seconds}s"
        raise AssertionError(msg)
