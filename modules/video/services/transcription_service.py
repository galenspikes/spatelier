"""
Unified transcription service for video files.

This module provides automatic transcription capabilities using OpenAI Whisper,
with database integration, analytics tracking, and subtitle embedding.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

try:
    import whisper
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from core.base_service import BaseService
from core.config import Config
# Import TranscriptionStorage from the original module (kept for backward compatibility)
try:
    from modules.video.transcription_service import TranscriptionStorage
except ImportError:
    # Fallback: TranscriptionStorage might be in a different location
    TranscriptionStorage = None

# Global model cache to avoid reloading models
_MODEL_CACHE = {}


class TranscriptionService(BaseService):
    """
    Unified transcription service using OpenAI Whisper.
    
    Supports both openai-whisper and faster-whisper for different speed/accuracy needs.
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
        self.use_faster_whisper = self.config.transcription.use_faster_whisper
        self.device = self.config.transcription.device
        self.compute_type = self.config.transcription.compute_type
        
        # Model and storage (lazy-loaded)
        self.model = None
        self.transcription_storage = None
    
    def _initialize_transcription(self, model_size: Optional[str] = None):
        """Initialize transcription service if not already done."""
        if self.model is None:
            if not WHISPER_AVAILABLE:
                raise ImportError("Whisper dependencies not available. Install with: pip install spatelier[transcription]")
            
            model_size = model_size or self.model_size
            
            # Load model with caching
            cache_key = f"{model_size}_{self.device}_{self.compute_type}_{self.use_faster_whisper}"
            
            if cache_key in _MODEL_CACHE:
                self.logger.info(f"Using cached Whisper model: {model_size}")
                self.model = _MODEL_CACHE[cache_key]
            else:
                if self.use_faster_whisper:
                    self.logger.info(f"Loading faster-whisper model: {model_size}")
                    self.model = WhisperModel(model_size, device=self.device, compute_type=self.compute_type)
                else:
                    self.logger.info(f"Loading openai-whisper model: {model_size}")
                    self.model = whisper.load_model(model_size)
                
                _MODEL_CACHE[cache_key] = self.model
                self.logger.info("Whisper model loaded and cached successfully")
            
            # Initialize storage
            if self.transcription_storage is None:
                if self.db_manager is None:
                    self.db_manager = self.db_factory.get_db_manager()
                
                # Connect to MongoDB if not already connected
                if not hasattr(self.db_manager, 'mongo_db') or self.db_manager.mongo_db is None:
                    self.db_manager.connect_mongodb()
                
                self.transcription_storage = TranscriptionStorage(self.db_manager.mongo_db)
                self.logger.info("Transcription storage initialized")
    
    def transcribe_video(
        self,
        video_path: Union[str, Path],
        media_file_id: Optional[int] = None,
        language: Optional[str] = None,
        model_size: Optional[str] = None
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
            
            # Initialize transcription service
            self._initialize_transcription(model_size)
            
            # Get language
            language = language or self.config.transcription.default_language
            
            # Track transcription start
            self.repos.analytics.track_event("transcription_start", event_data={
                "video_path": str(video_path),
                "media_file_id": media_file_id,
                "language": language
            })
            
            # Transcribe video
            self.logger.info(f"Starting transcription of: {video_path}")
            start_time = time.time()
            
            if self.use_faster_whisper:
                result = self._transcribe_with_faster_whisper(video_path, language)
            else:
                result = self._transcribe_with_openai_whisper(video_path, language)
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["model_used"] = f"whisper-{self.model_size}"
            result["language"] = language
            
            self.logger.info(f"Transcription completed in {processing_time:.1f}s")
            
            if result and 'segments' in result:
                # Store transcription in database
                transcription_id = self.transcription_storage.store_transcription(
                    media_file_id, result
                )
                
                if transcription_id:
                    self.logger.info(f"Transcription stored with ID: {transcription_id}")
                    
                    # Track successful transcription
                    self.repos.analytics.track_event("transcription_completed", event_data={
                        "video_path": str(video_path),
                        "media_file_id": media_file_id,
                        "transcription_id": transcription_id,
                        "segments_count": len(result['segments'])
                    })
                    
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
            self.repos.analytics.track_event("transcription_error", event_data={
                "video_path": str(video_path),
                "media_file_id": media_file_id,
                "error": str(e)
            })
            
            return False
    
    def _transcribe_with_faster_whisper(self, video_path: Path, language: str) -> Dict:
        """Transcribe using faster-whisper (faster, less accurate)."""
        result = self.model.transcribe(
            str(video_path),
            language=language,
            word_timestamps=True
        )
        
        # faster-whisper returns (segments, info) tuple
        segments, info = result
        
        # Convert segments to our format
        transcription_segments = []
        for segment in segments:
            transcription_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": getattr(segment, 'avg_logprob', 0.0)
            })
        
        return {
            "segments": transcription_segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration
        }
    
    def _transcribe_with_openai_whisper(self, video_path: Path, language: str) -> Dict:
        """Transcribe using openai-whisper (more accurate, slower)."""
        result = self.model.transcribe(
            str(video_path),
            language=language,
            word_timestamps=True
        )
        
        # Convert to our format
        transcription_segments = []
        for segment in result["segments"]:
            transcription_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": segment.get("avg_logprob", 0.0)
            })
        
        return {
            "segments": transcription_segments,
            "language": result.get("language", language),
            "language_probability": 1.0,  # openai-whisper doesn't provide this
            "duration": result.get("duration", 0.0)
        }
    
    def embed_subtitles(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        media_file_id: Optional[int] = None
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
            
            # Initialize transcription service
            self._initialize_transcription()
            
            # Get transcription data
            transcription_data = self._get_transcription_data(video_path, media_file_id)
            
            if not transcription_data or 'segments' not in transcription_data:
                self.logger.error("No transcription data available for embedding")
                return False
            
            # Embed subtitles
            success = self._embed_subtitles_into_video(video_path, output_path, transcription_data)
            
            if success:
                self.logger.info(f"Successfully embedded subtitles into video: {output_path}")
                
                # Track successful embedding
                self.repos.analytics.track_event("subtitle_embedding_completed", event_data={
                    "input_path": str(video_path),
                    "output_path": str(output_path),
                    "media_file_id": media_file_id
                })
                
                return True
            else:
                self.logger.error("Failed to embed subtitles")
                return False
                
        except Exception as e:
            self.logger.error(f"Subtitle embedding failed: {e}")
            
            # Track embedding error
            self.repos.analytics.track_event("subtitle_embedding_error", event_data={
                "input_path": str(video_path),
                "output_path": str(output_path),
                "media_file_id": media_file_id,
                "error": str(e)
            })
            
            return False
    
    def _get_transcription_data(self, video_path: Path, media_file_id: Optional[int] = None) -> Optional[Dict]:
        """Get transcription data from database or transcribe if not found."""
        # Try to get from database first
        if media_file_id and self.transcription_storage:
            transcription = self.transcription_storage.get_transcription(media_file_id)
            if transcription:
                return {
                    "segments": transcription.get("segments", []),
                    "language": transcription.get("language", "en"),
                    "duration": transcription.get("duration", 0.0)
                }
        
        # If not in database, transcribe now
        self.logger.info("Transcription not found in database, transcribing now...")
        language = self.config.transcription.default_language
        
        if self.use_faster_whisper:
            result = self._transcribe_with_faster_whisper(video_path, language)
        else:
            result = self._transcribe_with_openai_whisper(video_path, language)
        
        return result
    
    def _embed_subtitles_into_video(
        self,
        video_path: Path,
        output_path: Path,
        transcription_data: Dict[str, Any]
    ) -> bool:
        """Embed subtitles into video file."""
        try:
            import ffmpeg
            
            # Create subtitle file
            subtitle_file = video_path.parent / f"{video_path.stem}_temp.srt"
            self._create_srt_file(subtitle_file, transcription_data['segments'])
            
            # Embed subtitles using ffmpeg
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(output_path),
                    vcodec='copy',
                    acodec='copy',
                    scodec='mov_text',
                    **{'metadata:s:s:0': 'language=eng'}
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Clean up temporary subtitle file
            subtitle_file.unlink(missing_ok=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to embed subtitles: {e}")
            return False
    
    def _create_srt_file(self, subtitle_file: Path, segments: list):
        """Create SRT subtitle file from segments."""
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment['start'])
                end_time = self._format_timestamp(segment['end'])
                text = segment['text'].strip()
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
    
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
            self.logger.error(f"Failed to get transcription for media file {media_file_id}: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        return ["tiny", "base", "small", "medium", "large"]
    
    def get_model_info(self) -> Dict:
        """Get information about the current model."""
        return {
            "model_size": self.model_size,
            "use_faster_whisper": self.use_faster_whisper,
            "available_models": self.get_available_models()
        }
