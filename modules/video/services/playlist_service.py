"""
Playlist service.

This module provides focused playlist management functionality.
"""

import shutil
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

from core.base_service import BaseService
from core.base import ProcessingResult
from core.config import Config
from database.models import MediaType, ProcessingStatus


class PlaylistService(BaseService):
    """
    Focused playlist service.
    
    Handles playlist downloading and management without transcription concerns.
    """
    
    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """Initialize the playlist service."""
        # Initialize base service
        super().__init__(config, verbose, db_service)
        
        # Initialize metadata management
        from database.metadata import MetadataExtractor, MetadataManager
        self.metadata_extractor = MetadataExtractor(config, verbose=verbose)
        self.metadata_manager = MetadataManager(config, verbose=verbose)
    
    def download_playlist(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Download playlist without transcription.
        
        Args:
            url: Playlist URL to download
            output_path: Optional output directory (will create playlist folder)
            **kwargs: Additional download options
        
        Returns:
            Dictionary with download results
        """
        try:
            # Get playlist metadata first
            playlist_info = self._get_playlist_info(url)
            if not playlist_info:
                return ProcessingResult(
                    success=False,
                    message="Failed to get playlist information",
                    errors=["Could not extract playlist metadata"]
                )
            
            # Create playlist folder
            playlist_name = self._sanitize_filename(playlist_info.get('title', 'Unknown Playlist'))
            playlist_id = playlist_info.get('id', 'unknown')
            folder_name = f"{playlist_name} [{playlist_id}]"
            
            if output_path:
                playlist_dir = Path(output_path) / folder_name
            else:
                playlist_dir = Path.cwd() / folder_name
            
            # Check if output is on NAS and set up temp processing if needed
            is_nas = self._is_nas_path(playlist_dir)
            
            # Create processing job
            job = self.repos.jobs.create(
                media_file_id=None,  # Will be updated after processing
                job_type="download_playlist",
                input_path=url,
                output_path=str(playlist_dir),
                parameters=str(kwargs)
            )
            self.logger.info(f"Created playlist processing job: {job.id}")
            
            temp_dir = None
            processing_dir = playlist_dir
            
            if is_nas:
                # Create job-specific temp processing directory with playlist folder
                temp_dir = self._get_temp_processing_dir(job.id)
                processing_dir = temp_dir / folder_name
                self.logger.info(f"NAS detected for playlist, using temp processing: {temp_dir}")
                self.logger.info(f"Playlist will be processed in: {processing_dir}")
            
            processing_dir.mkdir(parents=True, exist_ok=True)
            
            # Create or update playlist record in database
            existing_playlist = self.repos.playlists.get_by_playlist_id(playlist_id)
            if existing_playlist:
                # Update existing playlist
                existing_playlist.title = playlist_name
                existing_playlist.description = playlist_info.get('description')
                existing_playlist.uploader = playlist_info.get('uploader')
                existing_playlist.uploader_id = playlist_info.get('uploader_id')
                existing_playlist.source_url = url
                existing_playlist.source_platform = 'youtube'
                existing_playlist.video_count = playlist_info.get('playlist_count')
                existing_playlist.view_count = playlist_info.get('view_count')
                existing_playlist.thumbnail_url = playlist_info.get('thumbnail')
                playlist_record = existing_playlist
            else:
                playlist_record = self.repos.playlists.create(
                    playlist_id=playlist_id,
                    title=playlist_name,
                    description=playlist_info.get('description'),
                    uploader=playlist_info.get('uploader'),
                    uploader_id=playlist_info.get('uploader_id'),
                    source_url=url,
                    source_platform='youtube',
                    video_count=playlist_info.get('playlist_count'),
                    view_count=playlist_info.get('view_count'),
                    thumbnail_url=playlist_info.get('thumbnail')
                )
            
            self.logger.info(f"Downloading playlist to: {playlist_dir}")
            self.logger.info(f"Playlist record: {playlist_record.id}")
            
            # Download playlist using yt-dlp Python package
            self.logger.info(f"Downloading playlist from: {url}")
            
            # Build yt-dlp options
            ydl_opts = self._build_playlist_ydl_opts(processing_dir, **kwargs)
            
            # Execute download
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Check if download was successful by looking for files
            downloaded_videos = self._find_playlist_videos(processing_dir)
            
            if downloaded_videos:
                self.logger.info(f"Downloaded {len(downloaded_videos)} videos from playlist")
                
                # Process each video (metadata only, no transcription)
                successful_downloads = []
                failed_downloads = []
                
                for position, video_path in enumerate(downloaded_videos, 1):
                    try:
                        # Extract video metadata and create/update media file record
                        video_id = self._extract_video_id_from_path(video_path)
                        
                        # Get source metadata for this video
                        source_metadata = self.metadata_extractor.extract_youtube_metadata(f"https://www.youtube.com/watch?v={video_id}")
                        
                        # Create media file record
                        from utils.helpers import get_file_hash, get_file_type
                        media_file = self.repos.media.create(
                            file_path=str(video_path),
                            file_name=video_path.name,
                            file_size=video_path.stat().st_size,
                            file_hash=get_file_hash(video_path),
                            media_type=MediaType.VIDEO,
                            mime_type=get_file_type(video_path),
                            source_url=f"https://www.youtube.com/watch?v={video_id}",
                            source_platform="youtube",
                            source_id=video_id,
                            title=source_metadata.get('title', video_path.stem),
                            description=source_metadata.get('description'),
                            uploader=source_metadata.get('uploader'),
                            uploader_id=source_metadata.get('uploader_id'),
                            upload_date=source_metadata.get('upload_date'),
                            view_count=source_metadata.get('view_count'),
                            like_count=source_metadata.get('like_count'),
                            duration=source_metadata.get('duration'),
                            language=source_metadata.get('language')
                        )
                        
                        # Enrich with additional metadata
                        self.metadata_manager.enrich_media_file(
                            media_file,
                            self.repos.media,
                            extract_source_metadata=True
                        )
                        
                        # Link video to playlist
                        self.repos.playlist_videos.add_video_to_playlist(
                            playlist_id=playlist_record.id,
                            media_file_id=media_file.id,
                            position=position,
                            video_title=media_file.title
                        )
                        
                        successful_downloads.append(str(video_path))
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process {video_path.name}: {e}")
                        failed_downloads.append(str(video_path))
                
                # If we used temp processing, move entire playlist directory to final destination
                if is_nas and temp_dir:
                    self.logger.info("Moving playlist directory to NAS destination...")
                    
                    # Move the entire playlist directory from temp to final destination
                    if self._move_playlist_to_final_destination(processing_dir, playlist_dir):
                        self.logger.info(f"Successfully moved playlist directory to NAS: {playlist_dir}")
                        
                        # Update job status to completed
                        self.repos.jobs.update_status(job.id, ProcessingStatus.COMPLETED)
                        
                        # Clean up temp directory after successful move
                        self._cleanup_temp_directory(temp_dir)
                        self.logger.info(f"Cleaned up temp directory: {temp_dir}")
                    else:
                        self.logger.error("Failed to move playlist directory to NAS")
                        self.repos.jobs.update_status(job.id, ProcessingStatus.FAILED, error_message="Failed to move playlist to NAS")
                        return ProcessingResult.error_result(
                            message="Playlist downloaded but failed to move to NAS",
                            errors=["Failed to move playlist directory to final destination"]
                        )
                else:
                    # For local downloads, update job status
                    self.repos.jobs.update_status(job.id, ProcessingStatus.COMPLETED)
                
                return ProcessingResult.success_result(
                    message=f"Playlist downloaded successfully: {len(successful_downloads)} videos",
                    output_path=playlist_dir,
                    metadata={
                        "playlist_title": playlist_name,
                        "playlist_id": playlist_id,
                        "total_videos": len(downloaded_videos),
                        "successful_downloads": len(successful_downloads),
                        "failed_downloads": len(failed_downloads),
                        "nas_processing": is_nas,
                        "videos_downloaded": len(successful_downloads)
                    }
                )
            else:
                return ProcessingResult.error_result(
                    message="Playlist download completed but no videos found",
                    errors=["No video files found in download directory"]
                )
                
        except Exception as e:
            self.logger.error(f"Playlist download failed: {e}")
            return ProcessingResult.error_result(
                message=f"Playlist download failed: {e}",
                errors=[str(e)]
            )
    
    def _get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get playlist information."""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
                
        except Exception as e:
            self.logger.error(f"Failed to get playlist info: {e}")
            return None
    
    def _get_cookies_from_browser(self) -> Optional[tuple]:
        """Try to get cookies from common browsers automatically.
        
        Returns a tuple of browsers to try in order. yt-dlp will try each browser
        until one works, or continue without cookies if none are available.
        
        Note: On macOS, Chrome is more reliable than Safari for cookie extraction.
        """
        # Try browsers in order of preference
        # On macOS, Chrome is more reliable than Safari (Safari cookies are harder to access)
        # yt-dlp will try each browser until one works
        import platform
        system = platform.system().lower()
        
        if system == 'darwin':  # macOS - prioritize Chrome over Safari
            browsers = ('chrome', 'safari', 'firefox', 'edge')
        else:  # Linux, Windows, etc.
            browsers = ('chrome', 'firefox', 'safari', 'edge')
        
        return browsers
    
    def _build_playlist_ydl_opts(self, output_dir: Path, **kwargs) -> Dict:
        """Build yt-dlp options for playlist download."""
        # Output template for playlist
        output_template = str(output_dir / "%(title)s [%(id)s].%(ext)s")
        
        ydl_opts = {
            'outtmpl': output_template,
            'format': self._get_format_selector(
                kwargs.get('quality', self.config.video.quality),
                kwargs.get('format', self.config.video.default_format)
            ),
            'writeinfojson': False,  # Don't write info files
            'writesubtitles': False,  # We handle subtitles separately
            'writeautomaticsub': False,
            'ignoreerrors': True,  # Continue on individual video errors
            'no_warnings': not self.verbose,
            'quiet': not self.verbose,
            'extract_flat': False,  # We want to download, not just extract info
        }
        
        # Automatically try to use cookies from browser for age-restricted content
        cookies_browser = self._get_cookies_from_browser()
        if cookies_browser:
            ydl_opts['cookies_from_browser'] = cookies_browser
        
        # Additional options
        if self.verbose:
            ydl_opts['verbose'] = True
        
        return ydl_opts
    
    def _get_format_selector(self, quality: str, format: str) -> str:
        """Get format selector for yt-dlp."""
        if quality == "best":
            return f"best[ext={format}]/best"
        elif quality == "worst":
            return f"worst[ext={format}]/worst"
        else:
            return f"best[height<={quality}][ext={format}]/best"
    
    def _find_playlist_videos(self, directory: Path) -> List[Path]:
        """Find downloaded video files in playlist directory."""
        video_extensions = self.config.video_extensions
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(directory.rglob(f"*{ext}"))
        
        return video_files
    
    def _extract_video_id_from_path(self, video_path: Path) -> str:
        """Extract video ID from file path."""
        # Look for [video_id] pattern in filename
        import re
        match = re.search(r'\[([a-zA-Z0-9_-]{11})\]', video_path.name)
        if match:
            return match.group(1)
        return "unknown"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        import re
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        max_length = self.config.max_filename_length
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename
    
    def _is_nas_path(self, path: Union[str, Path]) -> bool:
        """Check if path is on NAS."""
        path_str = str(path)
        return any(nas_indicator in path_str.lower() for nas_indicator in [
            '/volumes/', '/mnt/', 'nas', 'network', 'smb://', 'nfs://'
        ])
    
    def _get_temp_processing_dir(self, job_id: int) -> Path:
        """Get temporary processing directory for job."""
        temp_dir = self.config.video.temp_dir / str(job_id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def _move_playlist_to_final_destination(self, source_dir: Path, dest_dir: Path) -> bool:
        """Move playlist directory to final destination."""
        try:
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_dir), str(dest_dir))
            return True
        except Exception as e:
            self.logger.error(f"Failed to move playlist directory: {e}")
            return False
    
    def _cleanup_temp_directory(self, temp_dir: Path):
        """Clean up temporary directory."""
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
