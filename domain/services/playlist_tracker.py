"""
Playlist tracking domain service.

Handles persistence of playlists and playlist-video relationships,
converting between domain models and database entities.
"""

from pathlib import Path
from typing import Dict, List, Optional


class PlaylistTracker:
    """
    Domain service for tracking playlists.

    Handles conversion between domain models and database entities,
    keeping persistence logic separate from business logic.
    """

    def __init__(self, repositories, logger=None):
        """
        Initialize playlist tracker.

        Args:
            repositories: Repository container
            logger: Optional logger
        """
        self.repos = repositories
        self.logger = logger

    def track_playlist(
        self,
        playlist_id: str,
        url: str,
        metadata: Optional[dict] = None,
    ) -> Optional[int]:
        """
        Track a playlist in the database.

        Args:
            playlist_id: Playlist ID
            url: Playlist URL
            metadata: Optional metadata dictionary

        Returns:
            Playlist database ID if successful, None otherwise
        """
        try:
            metadata = metadata or {}

            # Check if playlist already exists
            existing_playlist = self.repos.playlists.get_by_playlist_id(playlist_id)
            if existing_playlist:
                # Update existing playlist
                if metadata.get("title"):
                    existing_playlist.title = metadata.get("title")
                if metadata.get("description") is not None:
                    existing_playlist.description = metadata.get("description")
                if metadata.get("uploader"):
                    existing_playlist.uploader = metadata.get("uploader")
                if metadata.get("uploader_id"):
                    existing_playlist.uploader_id = metadata.get("uploader_id")
                existing_playlist.source_url = url
                existing_playlist.source_platform = metadata.get("source_platform", "youtube")
                if metadata.get("playlist_count") is not None:
                    existing_playlist.video_count = metadata.get("playlist_count")
                if metadata.get("view_count") is not None:
                    existing_playlist.view_count = metadata.get("view_count")
                if metadata.get("thumbnail"):
                    existing_playlist.thumbnail_url = metadata.get("thumbnail")
                
                self.repos.playlists.session.commit()
                self.repos.playlists.session.refresh(existing_playlist)
                
                if self.logger:
                    self.logger.debug(f"Updated existing playlist: {playlist_id} (ID: {existing_playlist.id})")
                return existing_playlist.id
            else:
                # Create new playlist
                playlist_record = self.repos.playlists.create(
                    playlist_id=playlist_id,
                    title=metadata.get("title", "Unknown Playlist"),
                    description=metadata.get("description"),
                    uploader=metadata.get("uploader"),
                    uploader_id=metadata.get("uploader_id"),
                    source_url=url,
                    source_platform=metadata.get("source_platform", "youtube"),
                    video_count=metadata.get("playlist_count"),
                    view_count=metadata.get("view_count"),
                    thumbnail_url=metadata.get("thumbnail"),
                )

                if self.logger:
                    self.logger.info(f"Tracked playlist: {playlist_id} (ID: {playlist_record.id})")

                return playlist_record.id

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to track playlist {playlist_id}: {e}")
            return None

    def link_video_to_playlist(
        self,
        playlist_db_id: int,
        media_file_id: int,
        position: int,
        video_title: Optional[str] = None,
    ) -> bool:
        """
        Link a video to a playlist.

        Args:
            playlist_db_id: Playlist database ID
            media_file_id: Media file ID
            position: Position in playlist
            video_title: Optional video title

        Returns:
            True if successful, False otherwise
        """
        try:
            self.repos.playlist_videos.add_video_to_playlist(
                playlist_id=playlist_db_id,
                media_file_id=media_file_id,
                position=position,
                video_title=video_title,
            )
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to link video to playlist: {e}")
            return False

    def get_playlist_by_id(self, playlist_id: str) -> Optional[dict]:
        """
        Get playlist by playlist ID.

        Args:
            playlist_id: Playlist ID

        Returns:
            Playlist dictionary or None
        """
        try:
            playlist = self.repos.playlists.get_by_playlist_id(playlist_id)
            if playlist:
                return {
                    "id": playlist.id,
                    "playlist_id": playlist.playlist_id,
                    "title": playlist.title,
                    "video_count": playlist.video_count,
                }
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get playlist by ID: {e}")
            return None
