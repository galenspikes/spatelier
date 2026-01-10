"""
Fallback URL extractor for video downloads.

This module provides fallback functionality when yt-dlp fails to download a video.
It attempts to extract video URLs directly from the webpage source code.
"""

import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from core.config import Config


class FallbackExtractor:
    """
    Fallback video URL extractor.
    
    Extracts video URLs from webpage source when yt-dlp fails.
    Includes safety limits to prevent runaway downloads.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the fallback extractor.
        
        Args:
            config: Main configuration instance
        """
        self.config = config
        
        # Use flattened config properties
        self.max_files = config.fallback_max_files
        self.max_total_size_mb = 1000 * 1024 * 1024  # 1GB default (fallback_max_total_size_mb removed, use constant)
        self.timeout = config.fallback_timeout_seconds
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        
        # Video file extensions to look for
        self.video_extensions = set(config.video_extensions)
        
        # Common video URL patterns
        extensions_pattern = '|'.join(config.video_extensions).replace('.', '')
        self.video_patterns = [
            f'https?://[^"\\s]+\\.(?:{extensions_pattern})(?:\\?[^"\\s]*)?',
            f'https?://[^"\\s]*video[^"\\s]*\\.(?:{extensions_pattern})(?:\\?[^"\\s]*)?',
            f'https?://[^"\\s]*stream[^"\\s]*\\.(?:{extensions_pattern})(?:\\?[^"\\s]*)?',
        ]
    
    def extract_video_urls(self, url: str) -> List[str]:
        """
        Extract potential video URLs from a webpage.
        
        Args:
            url: The webpage URL to analyze
            
        Returns:
            List of potential video URLs
        """
        try:
            logger.info(f"Extracting video URLs from: {url}")
            
            # Get the webpage content
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find video URLs using multiple methods
            video_urls = set()
            
            # Method 1: Look for direct video links in href/src attributes
            for tag in soup.find_all(['a', 'source', 'video']):
                for attr in ['href', 'src', 'data-src']:
                    if tag.get(attr):
                        full_url = urljoin(url, tag[attr])
                        if self._is_video_url(full_url):
                            video_urls.add(full_url)
            
            # Method 2: Search for video URLs in script tags and page content
            page_text = response.text
            for pattern in self.video_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    full_url = urljoin(url, match)
                    if self._is_video_url(full_url):
                        video_urls.add(full_url)
            
            # Method 3: Look for common video hosting patterns
            video_urls.update(self._extract_hosting_urls(soup, url))
            
            logger.info(f"Found {len(video_urls)} potential video URLs")
            return list(video_urls)
            
        except Exception as e:
            logger.error(f"Failed to extract video URLs from {url}: {e}")
            return []
    
    def _is_video_url(self, url: str) -> bool:
        """Check if a URL points to a video file."""
        try:
            parsed = urlparse(url)
            path = Path(parsed.path)
            
            # Check file extension
            if path.suffix.lower() in self.video_extensions:
                return True
            
            # Check for common video hosting domains
            video_domains = {
                'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
                'twitch.tv', 'streamable.com', 'gfycat.com'
            }
            
            if any(domain in parsed.netloc.lower() for domain in video_domains):
                return True
                
            return False
            
        except Exception:
            return False
    
    def _extract_hosting_urls(self, soup: BeautifulSoup, base_url: str) -> set:
        """Extract URLs from common video hosting platforms."""
        urls = set()
        
        # Look for iframe sources (common for embedded videos)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                full_url = urljoin(base_url, src)
                urls.add(full_url)
        
        # Look for video elements
        for video in soup.find_all('video'):
            for source in video.find_all('source'):
                src = source.get('src')
                if src:
                    full_url = urljoin(base_url, src)
                    urls.add(full_url)
        
        return urls
    
    def download_video(self, video_url: str, output_path: Path) -> Tuple[bool, str, int]:
        """
        Download a video from URL with safety checks.
        
        Args:
            video_url: URL of the video to download
            output_path: Path to save the video
            
        Returns:
            Tuple of (success, message, file_size_bytes)
        """
        try:
            logger.info(f"Attempting to download: {video_url}")
            
            # Get file info first (HEAD request)
            head_response = self.session.head(video_url, timeout=self.timeout)
            head_response.raise_for_status()
            
            # Check content type
            content_type = head_response.headers.get('content-type', '').lower()
            if not any(video_type in content_type for video_type in ['video/', 'application/octet-stream']):
                return False, f"URL does not appear to be a video (content-type: {content_type})", 0
            
            # Check file size
            content_length = head_response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                if file_size > self.max_total_size_mb:
                    return False, f"File too large: {file_size / (1024*1024):.1f}MB", file_size
            else:
                # If we can't determine size, we'll check during download
                file_size = 0
            
            # Download the file
            response = self.session.get(video_url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with size checking
            downloaded_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Check size limit during download
                        if downloaded_size > self.max_total_size_mb:
                            output_path.unlink()  # Remove partial file
                            return False, f"Download exceeded size limit: {downloaded_size / (1024*1024):.1f}MB", downloaded_size
            
            logger.info(f"Successfully downloaded: {output_path} ({downloaded_size / (1024*1024):.1f}MB)")
            return True, "Download successful", downloaded_size
            
        except Exception as e:
            logger.error(f"Failed to download {video_url}: {e}")
            return False, str(e), 0
    
    def fallback_download(self, url: str, output_dir: Path) -> List[Dict]:
        """
        Attempt fallback download when yt-dlp fails.
        
        Args:
            url: Original URL that failed
            output_dir: Directory to save downloaded files
            
        Returns:
            List of download results with success status and file paths
        """
        logger.info(f"Starting fallback download for: {url}")
        
        # Extract potential video URLs
        video_urls = self.extract_video_urls(url)
        
        if not video_urls:
            logger.warning("No video URLs found in fallback extraction")
            return [{"success": False, "message": "No video URLs found", "file_path": None}]
        
        # Limit number of URLs to try
        video_urls = video_urls[:self.max_files]
        logger.info(f"Attempting to download {len(video_urls)} potential videos")
        
        results = []
        total_downloaded = 0
        
        for i, video_url in enumerate(video_urls):
            if total_downloaded >= self.max_total_size_mb:
                logger.warning(f"Reached total size limit: {total_downloaded / (1024*1024):.1f}MB")
                break
            
            # Create output filename
            parsed_url = urlparse(video_url)
            filename = Path(parsed_url.path).name
            if not filename or '.' not in filename:
                filename = f"video_{i+1}.mp4"
            
            output_path = output_dir / filename
            
            # Skip if file already exists
            if output_path.exists():
                logger.info(f"File already exists, skipping: {output_path}")
                results.append({
                    "success": True,
                    "message": "File already exists",
                    "file_path": output_path,
                    "size": output_path.stat().st_size
                })
                continue
            
            # Attempt download
            success, message, file_size = self.download_video(video_url, output_path)
            
            results.append({
                "success": success,
                "message": message,
                "file_path": output_path if success else None,
                "size": file_size
            })
            
            if success:
                total_downloaded += file_size
                logger.info(f"Downloaded {i+1}/{len(video_urls)}: {output_path}")
            else:
                logger.warning(f"Failed to download {i+1}/{len(video_urls)}: {message}")
            
            # Small delay between downloads
            time.sleep(1)
        
        successful_downloads = [r for r in results if r["success"]]
        logger.info(f"Fallback download completed: {len(successful_downloads)}/{len(results)} successful")
        
        return results
