"""
Playlist domain model.

Represents a playlist as a domain concept.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .video import Video


@dataclass
class Playlist:
    """
    Domain model for a playlist.

    Represents a playlist in the domain, containing videos.
    """

    url: str
    playlist_id: str
    title: Optional[str] = None
    output_path: Optional[Path] = None
    videos: List[Video] = field(default_factory=list)

    def add_video(self, video: Video) -> None:
        """Add a video to the playlist."""
        self.videos.append(video)

    def get_completed_videos(self) -> List[Video]:
        """Get videos that are complete."""
        return [v for v in self.videos if v.is_complete()]

    def get_failed_videos(self) -> List[Video]:
        """Get videos that failed to download."""
        return [v for v in self.videos if not v.exists()]

    def get_progress(self) -> dict:
        """Get playlist download progress."""
        total = len(self.videos)
        completed = len(self.get_completed_videos())
        failed = len(self.get_failed_videos())
        remaining = total - completed - failed

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "remaining": remaining,
        }
