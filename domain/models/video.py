"""
Video domain model.

Represents a video as a domain concept, independent of storage or infrastructure.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.helpers import YOUTUBE_VIDEO_ID_PATTERN


@dataclass
class Video:
    """
    Domain model for a video.

    Represents a video in the domain, independent of how it's stored
    or what infrastructure is used to download it.
    """

    url: str
    title: Optional[str] = None
    video_id: Optional[str] = None
    file_path: Optional[Path] = None
    duration_seconds: Optional[float] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    quality: Optional[str] = None

    def __post_init__(self):
        """Extract video ID from URL if not provided."""
        if self.video_id is None and self.url:
            self.video_id = self._extract_video_id()

    def _extract_video_id(self) -> Optional[str]:
        """
        Extract video ID from URL.
        
        Uses regex pattern for consistent extraction across all YouTube URL formats.
        """
        import re
        
        video_id_match = re.search(YOUTUBE_VIDEO_ID_PATTERN, self.url)
        if video_id_match:
            return video_id_match.group(1)
        return None

    def exists(self) -> bool:
        """Check if video file exists."""
        return self.file_path is not None and self.file_path.exists()

    def is_complete(self) -> bool:
        """
        Check if video download is complete.
        
        Returns:
            True if file exists and could be validated further (file size, etc.)
        """
        return self.exists()  # Could add more checks here (file size validation, etc.)
