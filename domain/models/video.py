"""
Video domain model.

Represents a video as a domain concept, independent of storage or infrastructure.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
        """Extract video ID from URL."""
        if "youtube.com" in self.url or "youtu.be" in self.url:
            if "v=" in self.url:
                return self.url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in self.url:
                return self.url.split("youtu.be/")[1].split("?")[0]
        return None

    def exists(self) -> bool:
        """Check if video file exists."""
        return self.file_path is not None and self.file_path.exists()

    def is_complete(self) -> bool:
        """Check if video download is complete."""
        if not self.exists():
            return False
        # Could add more checks here (file size validation, etc.)
        return True
