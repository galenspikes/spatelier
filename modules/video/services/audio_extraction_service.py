"""
Audio extraction service for YouTube videos.

This service provides clean, object-oriented audio extraction from YouTube videos
with proper separation of concerns and error handling.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.base import ProcessingResult
from core.base_service import BaseService
from core.progress import track_progress
from modules.audio.converter import AudioConverter
from modules.video.services.download_service import VideoDownloadService


class AudioExtractionService(BaseService):
    """
    Service for extracting audio from YouTube videos.

    Provides clean, object-oriented audio extraction with proper error handling,
    progress tracking, and resource management.
    """

    def __init__(
        self,
        config,
        verbose: bool = False,
        db_service=None,
        audio_converter: Optional[AudioConverter] = None,
        download_service: Optional[VideoDownloadService] = None,
    ):
        """
        Initialize audio extraction service.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            db_service: Optional database service instance
            audio_converter: Optional AudioConverter (injected dependency)
            download_service: Optional VideoDownloadService (injected dependency)
        """
        super().__init__(config, verbose, db_service)
        self.logger = self.logger.bind(service="AudioExtractionService")

        # Use injected dependencies or create lazily if not provided
        self._audio_converter = audio_converter
        self._download_service = download_service

    @property
    def audio_converter(self) -> AudioConverter:
        """Get audio converter service (lazy initialization if not injected)."""
        if self._audio_converter is None:
            self._audio_converter = AudioConverter(
                self.config, verbose=self.verbose, db_service=self.db_factory
            )
        return self._audio_converter

    @property
    def download_service(self) -> VideoDownloadService:
        """Get video download service (lazy initialization if not injected)."""
        if self._download_service is None:
            self._download_service = VideoDownloadService(
                self.config, verbose=self.verbose, db_service=self.db_factory
            )
        return self._download_service

    def extract_audio_from_url(
        self, url: str, output_dir: Path, format: str = "mp3", bitrate: int = 320
    ) -> ProcessingResult:
        """
        Extract audio from YouTube URL.

        Args:
            url: YouTube video URL
            output_dir: Output directory for audio file
            format: Audio format (mp3, wav, flac, aac, ogg, m4a)
            bitrate: Audio bitrate in kbps

        Returns:
            ProcessingResult with extraction details
        """
        self.logger.info(f"Starting audio extraction from URL: {url}")

        # Validate inputs
        validation_result = self._validate_inputs(url, output_dir, format, bitrate)
        if not validation_result.is_successful():
            return validation_result

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = None
        try:
            with track_progress(
                "Extracting audio from video...", verbose=self.verbose
            ) as progress:
                # Step 1: Download video to temporary location
                temp_dir = self._create_temp_directory()
                download_result = self._download_video(url, temp_dir)

                if not download_result.is_successful():
                    return ProcessingResult.fail(
                        f"Failed to download video: {download_result.message}",
                        errors=download_result.errors,
                    )

                progress.update(0.3, "Video downloaded, extracting audio...")

                # Step 2: Find downloaded file
                input_file = self._find_downloaded_file(temp_dir)
                if not input_file:
                    return ProcessingResult.fail("No audio file found after download")

                progress.update(0.2, "Converting audio format...")

                # Step 3: Convert to desired format
                output_file = self._generate_output_path(input_file, output_dir, format)
                conversion_result = self._convert_audio(
                    input_file, output_file, format, bitrate
                )

                if not conversion_result.is_successful():
                    return ProcessingResult.fail(
                        f"Audio conversion failed: {conversion_result.message}",
                        errors=conversion_result.errors,
                    )

                progress.update(0.5, "Audio extraction completed!")

                # Step 4: Prepare success result
                return self._create_success_result(output_file, format, bitrate)

        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            return ProcessingResult.fail(f"Audio extraction failed: {e}")

        finally:
            # Clean up temporary directory
            if temp_dir and temp_dir.exists():
                self._cleanup_temp_directory(temp_dir)

    def _validate_inputs(
        self, url: str, output_dir: Path, format: str, bitrate: int
    ) -> ProcessingResult:
        """Validate input parameters."""
        errors = []

        if not url or not url.strip():
            errors.append("URL cannot be empty")

        if not url.startswith(("http://", "https://")):
            errors.append("URL must start with http:// or https://")

        format_lower = format.lower()
        if format_lower not in ["mp3", "wav", "flac", "aac", "ogg", "m4a"]:
            errors.append(f"Unsupported format: {format}")

        if bitrate < 64 or bitrate > 512:
            errors.append("Bitrate must be between 64 and 512 kbps")

        if errors:
            return ProcessingResult.fail("Input validation failed", errors=errors)

        return ProcessingResult.success("Input validation passed")

    def _create_temp_directory(self) -> Path:
        """Create temporary directory for processing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="spatelier_audio_"))
        self.logger.debug(f"Created temp directory: {temp_dir}")
        return temp_dir

    def _download_video(self, url: str, temp_dir: Path) -> ProcessingResult:
        """Download video to temporary directory."""
        try:
            self.logger.info(f"Downloading video to: {temp_dir}")

            result = self.download_service.download_video(
                url=url,
                output_path=temp_dir,
                quality="bestaudio",  # Get best audio quality
                format="bestaudio/best",  # Prefer audio-only formats
            )

            return result

        except Exception as e:
            self.logger.error(f"Video download failed: {e}")
            return ProcessingResult.fail(f"Video download failed: {e}")

    def _find_downloaded_file(self, temp_dir: Path) -> Optional[Path]:
        """Find the downloaded audio/video file."""
        # Look for common audio/video extensions
        extensions = [".mp4", ".webm", ".mkv", ".avi", ".mov", ".m4a", ".mp3", ".wav"]

        for ext in extensions:
            files = list(temp_dir.glob(f"*{ext}"))
            if files:
                file_path = files[0]
                self.logger.info(f"Found downloaded file: {file_path}")
                return file_path

        self.logger.warning("No audio/video file found after download")
        return None

    def _generate_output_path(
        self, input_file: Path, output_dir: Path, format: str
    ) -> Path:
        """Generate output file path."""
        output_filename = f"{input_file.stem}.{format}"
        return output_dir / output_filename

    def _convert_audio(
        self, input_file: Path, output_file: Path, format: str, bitrate: int
    ) -> ProcessingResult:
        """Convert audio to desired format."""
        try:
            self.logger.info(f"Converting audio: {input_file} -> {output_file}")

            result = self.audio_converter.convert(
                input_path=input_file,
                output_path=output_file,
                bitrate=bitrate,
                format=format,
            )

            return result

        except Exception as e:
            self.logger.error(f"Audio conversion failed: {e}")
            return ProcessingResult.fail(f"Audio conversion failed: {e}")

    def _create_success_result(
        self, output_file: Path, format: str, bitrate: int
    ) -> ProcessingResult:
        """Create success result with metadata."""
        try:
            file_size = output_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            metadata = {
                "file_size": file_size,
                "file_size_mb": file_size_mb,
                "format": format,
                "bitrate": bitrate,
                "output_path": str(output_file),
            }

            return ProcessingResult.success(
                message=f"Audio extracted successfully: {output_file.name}",
                output_path=output_file,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Failed to create success result: {e}")
            return ProcessingResult.fail(f"Failed to create success result: {e}")

    def _cleanup_temp_directory(self, temp_dir: Path) -> None:
        """Clean up temporary directory."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                self.logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats."""
        return ["mp3", "wav", "flac", "aac", "ogg", "m4a"]

    def get_supported_bitrates(self) -> Dict[str, Any]:
        """Get supported bitrate ranges by format."""
        return {
            "mp3": {"min": 64, "max": 320, "default": 320},
            "wav": {"min": 128, "max": 1536, "default": 1411},
            "flac": {"min": 128, "max": 1536, "default": 1411},
            "aac": {"min": 64, "max": 320, "default": 256},
            "ogg": {"min": 64, "max": 320, "default": 192},
            "m4a": {"min": 64, "max": 320, "default": 256},
        }
