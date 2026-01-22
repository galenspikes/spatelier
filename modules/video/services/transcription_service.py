"""
Unified transcription service for video files.

This module provides automatic transcription capabilities using OpenAI Whisper,
with database integration, analytics tracking, and subtitle embedding.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from core.base_service import BaseService
from core.config import Config
from database.models import MediaType
from database.transcription_storage import SQLiteTranscriptionStorage
from utils.helpers import get_file_hash, get_file_type

# Global model cache to avoid reloading models
_MODEL_CACHE = {}


class TranscriptionService(BaseService):
    """
    Unified transcription service using faster-whisper.

    Uses faster-whisper (optimized Whisper implementation) for fast transcription.
    Includes database integration, analytics tracking, and subtitle embedding.
    """

    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """
        Initialize the transcription service.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            db_service: Optional database service instance
        """
        super().__init__(config, verbose, db_service)

        # Transcription configuration
        self.model_size = self.config.transcription.default_model
        self.device = self.config.transcription.device
        self.compute_type = self.config.transcription.compute_type

        # Model and storage (lazy-loaded)
        self.model = None
        self.transcription_storage = None

    def _initialize_transcription(self, model_size: Optional[str] = None):
        """Initialize transcription service if not already done.

        Returns:
            True if transcription is available and initialized, False otherwise
        """
        # If model already initialized, return True
        if self.model is not None:
            return True

        if not WHISPER_AVAILABLE:
            self.logger.error(
                "Transcription dependencies not available. This should not happen - faster-whisper is a core dependency."
            )
            return False

        model_size = model_size or self.model_size

        # Load model with caching
        cache_key = f"{model_size}_{self.device}_{self.compute_type}"

        if cache_key in _MODEL_CACHE:
            self.logger.info(f"Using cached Whisper model: {model_size}")
            self.model = _MODEL_CACHE[cache_key]
        else:
            self.logger.info(f"Loading faster-whisper model: {model_size}")
            self.model = WhisperModel(
                model_size, device=self.device, compute_type=self.compute_type
            )
            _MODEL_CACHE[cache_key] = self.model
            self.logger.info("Whisper model loaded and cached successfully")

        # Initialize storage
        if self.transcription_storage is None:
            if self.db_manager is None:
                self.db_manager = self.db_factory.get_db_manager()

            session = self.db_manager.get_sqlite_session()
            self.transcription_storage = SQLiteTranscriptionStorage(session)
            self.logger.info("SQLite transcription storage initialized")

        return True

    def transcribe_video(
        self,
        video_path: Union[str, Path],
        media_file_id: Optional[int] = None,
        language: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> bool:
        """
        Transcribe a video file.

        Args:
            video_path: Path to video file
            media_file_id: Optional media file ID for database tracking
            language: Language code for transcription
            model_size: Whisper model size

        Returns:
            True if transcription successful, False otherwise
        """
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                self.logger.error(f"Video file not found: {video_path}")
                return False

            if media_file_id is None:
                existing_media = self.repos.media.get_by_file_path(str(video_path))
                if existing_media:
                    media_file_id = existing_media.id
                else:
                    created_media = self.repos.media.create(
                        file_path=video_path,
                        file_name=video_path.name,
                        file_size=video_path.stat().st_size,
                        file_hash=get_file_hash(video_path),
                        media_type=MediaType.VIDEO,
                        mime_type=get_file_type(video_path),
                        title=video_path.stem,
                        source_platform="local",
                        source_id=None,
                        source_url=None,
                    )
                    media_file_id = created_media.id

            # Initialize transcription service
            effective_model_size = model_size or self.model_size
            if not self._initialize_transcription(effective_model_size):
                self.logger.error(
                    "Transcription dependencies not available. This should not happen - faster-whisper is a core dependency."
                )
                return False

            # Get language
            language = language or self.config.transcription.default_language

            # Track transcription start
            self.repos.analytics.track_event(
                "transcription_start",
                event_data={
                    "video_path": str(video_path),
                    "media_file_id": media_file_id,
                    "language": language,
                },
            )

            # Transcribe video
            self.logger.info(f"Starting transcription of: {video_path}")
            start_time = time.time()

            result = self._transcribe_with_faster_whisper(video_path, language)

            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["model_used"] = f"whisper-{effective_model_size}"
            result["language"] = language

            self.logger.info(f"Transcription completed in {processing_time:.1f}s")

            if result and "segments" in result:
                # Store transcription in database
                transcription_id = self.transcription_storage.store_transcription(
                    media_file_id, result
                )

                if transcription_id:
                    self.logger.info(
                        f"Transcription stored with ID: {transcription_id}"
                    )

                    # Track successful transcription
                    self.repos.analytics.track_event(
                        "transcription_completed",
                        event_data={
                            "video_path": str(video_path),
                            "media_file_id": media_file_id,
                            "transcription_id": transcription_id,
                            "segments_count": len(result["segments"]),
                        },
                    )

                    return True
                else:
                    self.logger.error("Failed to store transcription in database")
                    return False
            else:
                self.logger.error("Transcription failed - no segments generated")
                return False

        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")

            # Track transcription error
            self.repos.analytics.track_event(
                "transcription_error",
                event_data={
                    "video_path": str(video_path),
                    "media_file_id": media_file_id,
                    "error": str(e),
                },
            )

            return False

    def _transcribe_with_faster_whisper(self, video_path: Path, language: str) -> Dict:
        """Transcribe using faster-whisper (faster, less accurate)."""
        result = self.model.transcribe(
            str(video_path), language=language, word_timestamps=True
        )

        # faster-whisper returns (segments, info) tuple
        segments, info = result

        # Convert segments to our format
        transcription_segments = []
        for segment in segments:
            transcription_segments.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, "avg_logprob", 0.0),
                }
            )

        return {
            "segments": transcription_segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        }

    def embed_subtitles(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        media_file_id: Optional[int] = None,
    ) -> bool:
        """
        Embed subtitles into video file.

        Args:
            video_path: Path to input video file
            output_path: Path for output video with subtitles
            media_file_id: Optional media file ID for database tracking

        Returns:
            True if embedding successful, False otherwise
        """
        try:
            video_path = Path(video_path)
            output_path = Path(output_path)

            if not video_path.exists():
                self.logger.error(f"Video file not found: {video_path}")
                return False

            if media_file_id is None:
                existing_media = self.repos.media.get_by_file_path(str(video_path))
                if existing_media:
                    media_file_id = existing_media.id
                else:
                    created_media = self.repos.media.create(
                        file_path=video_path,
                        file_name=video_path.name,
                        file_size=video_path.stat().st_size,
                        file_hash=get_file_hash(video_path),
                        media_type=MediaType.VIDEO,
                        mime_type=get_file_type(video_path),
                        title=video_path.stem,
                        source_platform="local",
                        source_id=None,
                        source_url=None,
                    )
                    media_file_id = created_media.id

            # Initialize transcription service
            if not self._initialize_transcription():
                self.logger.warning(
                    "Subtitle embedding skipped: transcription dependencies not available. "
                    "This should not happen - faster-whisper is a core dependency."
                )
                return False

            # Get transcription data
            transcription_data = self._get_transcription_data(video_path, media_file_id)

            if not transcription_data or "segments" not in transcription_data:
                self.logger.error("No transcription data available for embedding")
                return False

            # Embed subtitles
            success = self._embed_subtitles_into_video(
                video_path, output_path, transcription_data
            )

            if success:
                self.logger.info(
                    f"Successfully embedded subtitles into video: {output_path}"
                )

                # Track successful embedding
                self.repos.analytics.track_event(
                    "subtitle_embedding_completed",
                    event_data={
                        "input_path": str(video_path),
                        "output_path": str(output_path),
                        "media_file_id": media_file_id,
                    },
                )

                return True
            else:
                self.logger.error("Failed to embed subtitles")
                return False

        except Exception as e:
            self.logger.error(f"Subtitle embedding failed: {e}")

            # Track embedding error
            self.repos.analytics.track_event(
                "subtitle_embedding_error",
                event_data={
                    "input_path": str(video_path),
                    "output_path": str(output_path),
                    "media_file_id": media_file_id,
                    "error": str(e),
                },
            )

            return False

    def _get_transcription_data(
        self, video_path: Path, media_file_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Get transcription data from database or transcribe if not found."""
        # Try to get from database first
        if media_file_id and self.transcription_storage:
            transcription = self.transcription_storage.get_transcription(media_file_id)
            if transcription:
                return {
                    "segments": transcription.get("segments", []),
                    "language": transcription.get("language", "en"),
                    "duration": transcription.get("duration", 0.0),
                }

        # If not in database, transcribe now
        if not WHISPER_AVAILABLE:
            self.logger.error(
                "Cannot transcribe: dependencies not available. "
                "This should not happen - faster-whisper is a core dependency."
            )
            return None

        self.logger.info("Transcription not found in database, transcribing now...")
        language = self.config.transcription.default_language

        result = self._transcribe_with_faster_whisper(video_path, language)
        return result

    def _embed_subtitles_into_video(
        self, video_path: Path, output_path: Path, transcription_data: Dict[str, Any]
    ) -> bool:
        """Embed subtitles into video file."""
        import ffmpeg

        subtitle_file = video_path.parent / f"{video_path.stem}_temp.srt"
        temp_output_path = None
        try:
            # Create subtitle file
            self._create_srt_file(subtitle_file, transcription_data["segments"])

            final_output_path = output_path
            if output_path.resolve() == video_path.resolve():
                temp_output_path = video_path.with_name(
                    f"{video_path.stem}_subs_tmp{video_path.suffix}"
                )
                final_output_path = temp_output_path

            # Embed subtitles using ffmpeg
            video_input = ffmpeg.input(str(video_path))
            subtitle_input = ffmpeg.input(str(subtitle_file))
            (
                ffmpeg.output(
                    video_input,
                    subtitle_input,
                    str(final_output_path),
                    vcodec="copy",
                    acodec="copy",
                    scodec="mov_text",
                    **{"metadata:s:s:0": "language=eng"},
                )
                .overwrite_output()
                .run(quiet=True)
            )

            if temp_output_path:
                temp_output_path.replace(output_path)

            return True
        except Exception as e:
            self.logger.error(f"Failed to embed subtitles: {e}")
            return False
        finally:
            subtitle_file.unlink(missing_ok=True)
            if temp_output_path and temp_output_path.exists():
                temp_output_path.unlink()

    def _create_srt_file(self, subtitle_file: Path, segments: list):
        """Create SRT subtitle file from segments."""
        with open(subtitle_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment["start"])
                end_time = self._format_timestamp(segment["end"])
                text = segment["text"].strip()

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")

    def get_transcription(self, media_file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get transcription data for a media file.

        Args:
            media_file_id: Media file ID

        Returns:
            Transcription data or None if not found
        """
        try:
            if self.transcription_storage is None:
                self._initialize_transcription()

            return self.transcription_storage.get_transcription(media_file_id)

        except Exception as e:
            self.logger.error(
                f"Failed to get transcription for media file {media_file_id}: {e}"
            )
            return None

    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        return ["tiny", "base", "small", "medium", "large"]

    def get_model_info(self) -> Dict:
        """Get information about the current model."""
        return {
            "model_size": self.model_size,
            "library": "faster-whisper",
            "available_models": self.get_available_models(),
        }
