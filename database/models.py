"""
Database models for Spatelier.

This module defines SQLAlchemy models for storing media files, processing history,
and analytics data.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class MediaType(str, Enum):
    """Media type enumeration."""

    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaFile(Base):
    """Media file model."""

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(
        String(1000), nullable=False, index=True
    )  # Remove unique constraint
    file_name = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)

    # OS-level file identification for tracking moved files
    file_device = Column(Integer, nullable=True, index=True)  # st_dev
    file_inode = Column(Integer, nullable=True, index=True)  # st_ino
    file_identifier = Column(
        String(50), nullable=True, unique=True, index=True
    )  # device:inode

    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    duration = Column(Float, nullable=True)  # For video/audio files
    width = Column(Integer, nullable=True)  # For video files
    height = Column(Integer, nullable=True)  # For video files
    bitrate = Column(Integer, nullable=True)  # For audio/video files
    sample_rate = Column(Integer, nullable=True)  # For audio files
    channels = Column(Integer, nullable=True)  # For audio files
    codec = Column(String(50), nullable=True)

    # Video-specific metadata
    title = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    uploader = Column(String(200), nullable=True)
    uploader_id = Column(String(100), nullable=True)
    upload_date = Column(DateTime, nullable=True)
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    dislike_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array of tags
    categories = Column(Text, nullable=True)  # JSON array of categories
    language = Column(String(10), nullable=True)
    age_limit = Column(Integer, nullable=True)

    # Source information
    source_url = Column(String(1000), nullable=True, index=True)
    source_platform = Column(
        String(50), nullable=True, index=True
    )  # youtube, vimeo, etc.
    source_id = Column(String(100), nullable=True, index=True)  # video ID on platform
    source_title = Column(String(1000), nullable=True)
    source_description = Column(Text, nullable=True)

    # Technical metadata
    fps = Column(Float, nullable=True)  # Frames per second
    aspect_ratio = Column(String(20), nullable=True)  # e.g., "16:9"
    color_space = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    video_codec = Column(String(50), nullable=True)

    # Thumbnail and artwork
    thumbnail_url = Column(String(1000), nullable=True)
    thumbnail_path = Column(String(1000), nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="media_file")
    analytics_events = relationship("AnalyticsEvent", back_populates="media_file")
    playlist_videos = relationship("PlaylistVideo", back_populates="media_file")


class ProcessingJob(Base):
    """Processing job model."""

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    job_type = Column(
        String(100), nullable=False, index=True
    )  # download, convert, extract, etc.
    status = Column(SQLEnum(ProcessingStatus), nullable=False, index=True)
    input_path = Column(String(1000), nullable=False)
    output_path = Column(String(1000), nullable=True)
    parameters = Column(Text, nullable=True)  # JSON string of processing parameters
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    media_file = relationship("MediaFile", back_populates="processing_jobs")
    analytics_events = relationship("AnalyticsEvent", back_populates="processing_job")


class AnalyticsEvent(Base):
    """Analytics event model."""

    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id"), nullable=True)
    event_type = Column(
        String(100), nullable=False, index=True
    )  # download, convert, view, etc.
    event_data = Column(Text, nullable=True)  # JSON string of event data
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)

    # Relationships
    media_file = relationship("MediaFile", back_populates="analytics_events")
    processing_job = relationship("ProcessingJob", back_populates="analytics_events")


class DownloadSource(Base):
    """Download source model."""

    __tablename__ = "download_sources"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    domain = Column(String(200), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    duration = Column(Float, nullable=True)
    uploader = Column(String(200), nullable=True)
    upload_date = Column(DateTime, nullable=True)
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    last_downloaded = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserPreference(Base):
    """User preference model."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    preference_key = Column(String(200), nullable=False, index=True)
    preference_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = ({"extend_existing": True},)


class Playlist(Base):
    """Playlist model for organizing videos."""

    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(
        String(100), nullable=False, unique=True, index=True
    )  # YouTube playlist ID
    title = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    uploader = Column(String(200), nullable=True)
    uploader_id = Column(String(100), nullable=True)
    source_url = Column(String(1000), nullable=True, index=True)
    source_platform = Column(String(50), nullable=True, index=True)
    video_count = Column(Integer, nullable=True)
    view_count = Column(Integer, nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    playlist_videos = relationship(
        "PlaylistVideo", back_populates="playlist", cascade="all, delete-orphan"
    )


class PlaylistVideo(Base):
    """Junction table for playlist-video relationships."""

    __tablename__ = "playlist_videos"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(
        Integer, ForeignKey("playlists.id"), nullable=False, index=True
    )
    media_file_id = Column(
        Integer, ForeignKey("media_files.id"), nullable=False, index=True
    )
    position = Column(Integer, nullable=True)  # Order in playlist
    video_title = Column(String(1000), nullable=True)  # Title at time of addition
    added_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    playlist = relationship("Playlist", back_populates="playlist_videos")
    media_file = relationship("MediaFile", back_populates="playlist_videos")

    # Unique constraint to prevent duplicate entries
    __table_args__ = ({"extend_existing": True},)


class Transcription(Base):
    """SQLite transcription storage (JSON + FTS-backed search)."""

    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    media_file_id = Column(
        Integer, ForeignKey("media_files.id"), nullable=False, index=True
    )
    language = Column(String(10), nullable=True)
    duration = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    segments_json = Column(JSON, nullable=False)
    full_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class APIKeys(Base):
    """API keys and credentials storage."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String, nullable=False)  # e.g., 'youtube', 'openai'
    key_value = Column(Text, nullable=False)  # Encrypted API key
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<APIKeys(id={self.id}, service='{self.service_name}')>"
