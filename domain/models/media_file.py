"""
Media file domain model.

Represents a media file as a domain concept.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class MediaFile:
    """
    Domain model for a media file.

    Represents a media file in the domain, independent of database storage.
    """

    file_path: Path
    file_name: str
    file_size: int
    media_type: str  # "video" or "audio"
    file_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    has_transcription: bool = False
    has_subtitles: bool = False

    def exists(self) -> bool:
        """Check if media file exists on disk."""
        return self.file_path.exists()

    def is_video(self) -> bool:
        """Check if this is a video file."""
        return self.media_type == "video"

    def is_audio(self) -> bool:
        """Check if this is an audio file."""
        return self.media_type == "audio"
