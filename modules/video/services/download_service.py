"""
Video download service.

This module provides focused video downloading functionality,
separated from transcription and metadata concerns.
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

from core.base import BaseDownloader, ProcessingResult
from core.base_service import BaseService
from core.config import Config
from utils.helpers import safe_filename, get_file_hash, get_file_type
from database.models import MediaType, ProcessingStatus
from database.metadata import MetadataExtractor, MetadataManager
from modules.video.fallback_extractor import FallbackExtractor


class VideoDownloadService(BaseService):
    """
    Focused video download service.
    
    Handles only video downloading, without transcription or complex metadata processing.
    """
    
    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """Initialize the video download service."""
        # Initialize base service
        super().__init__(config, verbose, db_service)
        
        # Service-specific initialization
        self.supported_sites = [
            "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
            "twitch.tv", "twitter.com", "instagram.com", "tiktok.com"
        ]
        
        # Initialize metadata management
        self.metadata_extractor = MetadataExtractor(config, verbose=verbose)
        self.metadata_manager = MetadataManager(config, verbose=verbose)
        
        # Initialize fallback extractor
        self.fallback_extractor = FallbackExtractor(config)
    
    def download_video(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Download a single video from URL.
        
        Args:
            url: URL to download from
            output_path: Optional output path
            **kwargs: Additional download options
        
        Returns:
            ProcessingResult with download details
        """
        # Track download start
        self.repos.analytics.track_event("download_start", event_data={"url": url})
        
        # Extract metadata before download
        source_metadata = {}
        if 'youtube.com' in url or 'youtu.be' in url:
            source_metadata = self.metadata_extractor.extract_youtube_metadata(url)
            self.logger.info(f"Extracted YouTube metadata: {source_metadata.get('title', 'Unknown')}")
        
        try:
            # Create processing job
            job = self.repos.jobs.create(
                media_file_id=None,  # Will be updated after processing
                job_type="download_video",
                input_path=url,
                output_path=str(output_path) if output_path else None,
                parameters=str(kwargs)
            )
            self.logger.info(f"Created video processing job: {job.id}")
            
            # Determine output path
            if output_path is None:
                output_path = self.config.video.output_dir or Path.cwd()
            else:
                output_path = Path(output_path)
            
            # Check if output is on NAS and set up temp processing if needed
            is_nas = self._is_nas_path(output_path)
            
            temp_dir = None
            processing_path = output_path
            
            if is_nas:
                # Create job-specific temp processing directory
                temp_dir = self._get_temp_processing_dir(job.id)
                processing_path = temp_dir
                self.logger.info(f"NAS detected, using temp processing: {temp_dir}")
                self.logger.info(f"Video will be processed in: {processing_path}")
            
            # Download using yt-dlp
            downloaded_file = self._download_with_ytdlp(url, processing_path, **kwargs)
            
            if downloaded_file and downloaded_file.exists():
                # Extract video metadata
                video_id = self._extract_video_id_from_url(url)
                
                # Create media file record
                media_file = self.repos.media.create(
                    file_path=str(downloaded_file),
                    file_name=downloaded_file.name,
                    file_size=downloaded_file.stat().st_size,
                    file_hash=get_file_hash(downloaded_file),
                    media_type=MediaType.VIDEO,
                    mime_type=get_file_type(downloaded_file),
                    source_url=url,
                    source_platform="youtube" if 'youtube.com' in url or 'youtu.be' in url else "unknown",
                    source_id=video_id,
                    title=source_metadata.get('title', downloaded_file.stem),
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
                
                # Update job with media file ID
                self.repos.jobs.update(job.id, media_file_id=media_file.id, output_path=str(downloaded_file))
                
                # If we used temp processing, move file to final destination
                if is_nas and temp_dir:
                    self.logger.info("Moving video to NAS destination...")
                    final_file_path = output_path / downloaded_file.name
                    
                    if self._move_file_to_nas(downloaded_file, final_file_path):
                        self.logger.info(f"Successfully moved video to NAS: {final_file_path}")
                        
                        # Check if a media file with this path already exists
                        existing_media = self.repos.media.get_by_file_path(str(final_file_path))
                        if existing_media:
                            # Delete the old record and update the current one
                            self.logger.info(f"Found existing media file {existing_media.id} with same path, updating it")
                            self.repos.media.delete(existing_media.id)
                        
                        # Update media file record with final path
                        self.repos.media.update(media_file.id, file_path=str(final_file_path))
                        
                        # Update job status
                        self.repos.jobs.update_status(job.id, ProcessingStatus.COMPLETED)
                        
                        # Clean up temp directory
                        self._cleanup_temp_directory(temp_dir)
                        self.logger.info(f"Cleaned up temp directory: {temp_dir}")
                        
                        return ProcessingResult(
                            success=True,
                            message="Video downloaded and moved to NAS successfully",
                            output_path=str(final_file_path),
                            metadata={
                                "media_file_id": media_file.id,
                                "job_id": job.id,
                                "nas_processing": True
                            }
                        )
                    else:
                        self.logger.error("Failed to move video to NAS")
                        self.repos.jobs.update_status(job.id, ProcessingStatus.FAILED, error_message="Failed to move to NAS")
                        return ProcessingResult(
                            success=False,
                            message="Video downloaded but failed to move to NAS",
                            errors=["Failed to move file to final destination"]
                        )
                else:
                    # For local downloads, update job status
                    self.repos.jobs.update_status(job.id, ProcessingStatus.COMPLETED)
                    
                    return ProcessingResult(
                        success=True,
                        message="Video downloaded successfully",
                        output_path=str(downloaded_file),
                        metadata={
                            "media_file_id": media_file.id,
                            "job_id": job.id,
                            "nas_processing": False
                        }
                    )
            else:
                self.repos.jobs.update_status(job.id, ProcessingStatus.FAILED, error_message="Download failed")
                return ProcessingResult(
                    success=False,
                    message="Video download failed",
                    errors=["No video file found after download"]
                )
                
        except Exception as e:
            self.logger.error(f"Video download failed: {e}")
            return ProcessingResult(
                success=False,
                message=f"Video download failed: {e}",
                errors=[str(e)]
            )
    
    def _download_with_ytdlp(self, url: str, output_path: Path, **kwargs) -> Optional[Path]:
        """Download video using yt-dlp.
        
        Automatically refreshes cookies and retries if download fails due to
        authentication issues with age-restricted content.
        """
        try:
            # Build yt-dlp options
            ydl_opts = self._build_ydl_opts(output_path, **kwargs)
            
            # Execute download
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the downloaded file
            downloaded_files = list(output_path.glob("*"))
            if downloaded_files:
                return downloaded_files[0]  # Return first file found
            
            return None
            
        except Exception as e:
            error_msg = str(e)
            # Check if this is a cookie/authentication error
            if any(keyword in error_msg.lower() for keyword in ['sign in', 'age', 'cookies', 'authentication']):
                self.logger.warning("Download failed due to authentication - attempting to refresh cookies...")
                # Try to refresh cookies and get cookie file
                cookie_file = self._refresh_youtube_cookies()
                if cookie_file:
                    self.logger.info("Retrying download with refreshed cookies...")
                    # Retry the download with cookie file
                    try:
                        ydl_opts = self._build_ydl_opts(output_path, **kwargs)
                        # Use the cookie file instead of cookies_from_browser
                        ydl_opts['cookies'] = cookie_file
                        if 'cookies_from_browser' in ydl_opts:
                            del ydl_opts['cookies_from_browser']
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        
                        # Clean up cookie file
                        import os
                        try:
                            os.unlink(cookie_file)
                        except:
                            pass
                        
                        # Find the downloaded file
                        downloaded_files = list(output_path.glob("*"))
                        if downloaded_files:
                            return downloaded_files[0]
                    except Exception as retry_error:
                        # Clean up cookie file
                        import os
                        try:
                            os.unlink(cookie_file)
                        except:
                            pass
                        self.logger.error(f"Download failed after cookie refresh: {retry_error}")
                        return None
                else:
                    self.logger.error(f"yt-dlp download failed: {e}")
                    return None
            else:
                self.logger.error(f"yt-dlp download failed: {e}")
                return None
    
    def _refresh_youtube_cookies(self) -> Optional[str]:
        """Refresh YouTube cookies by visiting YouTube and extracting fresh cookies.
        
        Uses Playwright to launch Chrome with the user's profile, visit YouTube,
        extract the cookies, and save them to a temporary file for yt-dlp to use.
        
        Returns:
            Path to cookie file if successful, None otherwise
        """
        try:
            from playwright.sync_api import sync_playwright
            import platform
            import os
            import tempfile
            
            system = platform.system().lower()
            if system != 'darwin':
                # Only implemented for macOS for now
                return None
            
            # Get Chrome user data directory
            chrome_user_data = os.path.expanduser(
                '~/Library/Application Support/Google/Chrome'
            )
            
            if not os.path.exists(chrome_user_data):
                return None
            
            self.logger.info("Refreshing YouTube cookies by visiting YouTube in Chrome...")
            
            with sync_playwright() as p:
                # Launch Chrome with user's profile
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=chrome_user_data,
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # Visit YouTube to refresh session
                page = browser.new_page()
                page.goto('https://www.youtube.com', wait_until='networkidle', timeout=15000)
                # Wait a moment for cookies to be set
                page.wait_for_timeout(3000)
                
                # Extract cookies from the page
                cookies = browser.cookies()
                browser.close()
                
                # Filter for YouTube cookies only
                youtube_cookies = [c for c in cookies if 'youtube.com' in c.get('domain', '') or '.youtube.com' in c.get('domain', '')]
                
                if not youtube_cookies:
                    self.logger.warning("No YouTube cookies found after refresh")
                    return None
                
                # Save cookies to Netscape format file for yt-dlp
                cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                cookie_file.write("# Netscape HTTP Cookie File\n")
                cookie_file.write("# This file was generated by spatelier\n\n")
                
                for cookie in youtube_cookies:
                    domain = cookie.get('domain', '')
                    domain_flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie.get('path', '/')
                    secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                    expires = str(int(cookie.get('expires', 0)))
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    
                    cookie_file.write(f"{domain}\t{domain_flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
                
                cookie_file.close()
                self.logger.info(f"YouTube cookies refreshed and saved to: {cookie_file.name}")
                return cookie_file.name
            
        except Exception as e:
            self.logger.warning(f"Failed to refresh cookies automatically: {e}")
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
    
    def _build_ydl_opts(self, output_path: Path, **kwargs) -> Dict:
        """Build yt-dlp options."""
        # Output template
        output_template = str(output_path / "%(title)s [%(id)s].%(ext)s")
        
        ydl_opts = {
            'outtmpl': output_template,
            'format': self._get_format_selector(
                kwargs.get('quality', self.config.video.quality),
                kwargs.get('format', self.config.video.default_format)
            ),
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'no_warnings': not self.verbose,
            'quiet': not self.verbose,
        }
        
        # Automatically try to use cookies from browser for age-restricted content
        cookies_browser = self._get_cookies_from_browser()
        if cookies_browser:
            ydl_opts['cookies_from_browser'] = cookies_browser
            if self.verbose:
                self.logger.info(f"Attempting to use cookies from browsers: {cookies_browser}")
        
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
            # Extract numeric part from quality (e.g., "1080p" -> "1080")
            try:
                height = quality.replace('p', '')
                return f"best[height<={height}][ext={format}]/best"
            except:
                return f"best[ext={format}]/best"
    
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
    
    def _move_file_to_nas(self, source_file: Path, dest_file: Path) -> bool:
        """Move file to NAS destination."""
        try:
            import shutil
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_file), str(dest_file))
            return True
        except Exception as e:
            self.logger.error(f"Failed to move file to NAS: {e}")
            return False
    
    def _cleanup_temp_directory(self, temp_dir: Path):
        """Clean up temporary directory."""
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def _extract_video_id_from_url(self, url: str) -> str:
        """Extract video ID from URL."""
        if 'youtube.com' in url or 'youtu.be' in url:
            if 'v=' in url:
                return url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                return url.split('youtu.be/')[1].split('?')[0]
        return "unknown"
    
    def _get_playlist_progress(self, playlist_id: str) -> Dict[str, int]:
        """Get playlist download progress."""
        try:
            # Get playlist from database
            playlist = self.repos.playlists.get_by_playlist_id(playlist_id)
            if not playlist:
                return {'total': 0, 'completed': 0, 'failed': 0, 'remaining': 0}
            
            # Get playlist videos
            playlist_videos = self.repos.playlist_videos.get_by_playlist_id(playlist.id)
            total = len(playlist_videos)
            
            completed = 0
            failed = 0
            
            for pv in playlist_videos:
                media_file = self.repos.media.get_by_id(pv.media_file_id)
                if media_file and media_file.file_path:
                    file_path = Path(media_file.file_path)
                    if file_path.exists():
                        # Check if has transcription
                        if self._check_video_has_transcription(media_file):
                            completed += 1
                        else:
                            failed += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            
            remaining = total - completed - failed
            
            return {
                'total': total,
                'completed': completed,
                'failed': failed,
                'remaining': remaining
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get playlist progress: {e}")
            return {'total': 0, 'completed': 0, 'failed': 0, 'remaining': 0}
    
    def _get_failed_videos(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get failed videos from playlist."""
        try:
            # Get playlist from database
            playlist = self.repos.playlists.get_by_playlist_id(playlist_id)
            if not playlist:
                return []
            
            # Get playlist videos
            playlist_videos = self.repos.playlist_videos.get_by_playlist_id(playlist.id)
            failed_videos = []
            
            for pv in playlist_videos:
                media_file = self.repos.media.get_by_id(pv.media_file_id)
                if media_file and media_file.file_path:
                    file_path = Path(media_file.file_path)
                    if not file_path.exists():
                        failed_videos.append({
                            'position': pv.position,
                            'video_title': pv.video_title or 'Unknown',
                            'reason': 'File missing'
                        })
                    elif not self._check_video_has_transcription(media_file):
                        failed_videos.append({
                            'position': pv.position,
                            'video_title': pv.video_title or 'Unknown',
                            'reason': 'No transcription'
                        })
                else:
                    failed_videos.append({
                        'position': pv.position,
                        'video_title': pv.video_title or 'Unknown',
                        'reason': 'Media file not found'
                    })
            
            return failed_videos
            
        except Exception as e:
            self.logger.error(f"Failed to get failed videos: {e}")
            return []
    
    def _check_video_has_transcription(self, media_file) -> bool:
        """Check if video has transcription."""
        try:
            if not media_file or not media_file.file_path:
                return False
            
            file_path = Path(media_file.file_path)
            if not file_path.exists():
                return False
            
            # Check for transcription files
            base_name = file_path.stem
            transcription_files = [
                file_path.parent / f"{base_name}.srt",
                file_path.parent / f"{base_name}.vtt",
                file_path.parent / f"{base_name}.json"
            ]
            
            return any(f.exists() for f in transcription_files)
            
        except Exception as e:
            self.logger.error(f"Failed to check transcription: {e}")
            return False
    
    def download_playlist_with_transcription(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        continue_download: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Download playlist with transcription support."""
        try:
            # This method would integrate with PlaylistService
            # For now, return a placeholder implementation
            from modules.video.services.playlist_service import PlaylistService
            
            playlist_service = PlaylistService(self.config, verbose=self.verbose, db_service=self.db_factory)
            result = playlist_service.download_playlist(url, output_path, **kwargs)
            
            # Add transcription logic here if needed
            return result
            
        except Exception as e:
            self.logger.error(f"Playlist download with transcription failed: {e}")
            return {
                "success": False,
                "message": f"Playlist download failed: {e}",
                "errors": [str(e)]
            }
    
    def _check_existing_video(self, file_path: Path, url: str) -> Dict[str, Any]:
        """Check if video file exists and has subtitles."""
        result = {
            'exists': False,
            'has_subtitles': False,
            'should_overwrite': True,
            'reason': ''
        }
        
        if not file_path.exists():
            result['reason'] = f'File {file_path} does not exist'
            return result
        
        result['exists'] = True
        
        # Check for subtitles
        has_subtitles = self._has_whisper_subtitles(file_path)
        result['has_subtitles'] = has_subtitles
        
        if has_subtitles:
            result['should_overwrite'] = False
            result['reason'] = f'File {file_path} exists with WhisperAI subtitles'
        else:
            result['should_overwrite'] = True
            result['reason'] = f'File {file_path} exists without subtitles'
        
        return result
    
    def _has_whisper_subtitles(self, file_path: Path) -> bool:
        """Check if video file has Whisper subtitles."""
        try:
            # Use ffprobe to check for subtitle tracks
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            import json
            data = json.loads(result.stdout)
            
            # Check for subtitle streams
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    # Check if it's a Whisper subtitle
                    title = stream.get('tags', {}).get('title', '')
                    if 'whisper' in title.lower() or 'whisperai' in title.lower():
                        return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking subtitles for {file_path}: {e}")
            return False