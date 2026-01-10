"""
Transcription service for video files.

This module provides automatic transcription capabilities using OpenAI Whisper.
Supports multiple models for speed vs accuracy tradeoffs.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple

import whisper
from faster_whisper import WhisperModel
from loguru import logger

# Global model cache to avoid reloading models
_MODEL_CACHE = {}

from core.config import Config, TranscriptionConfig


class TranscriptionService:
    """
    Video transcription service using OpenAI Whisper.
    
    Supports both openai-whisper and faster-whisper for different speed/accuracy needs.
    """
    
    def __init__(self, config: Config, transcription_config: Optional[TranscriptionConfig] = None):
        """
        Initialize the transcription service.
        
        Args:
            config: Main configuration instance
            transcription_config: Transcription-specific configuration (optional)
        """
        self.config = config
        self.transcription_config = transcription_config or config.transcription
        
        self.model_size = self.transcription_config.default_model
        self.use_faster_whisper = self.transcription_config.use_faster_whisper
        self.device = self.transcription_config.device
        self.compute_type = self.transcription_config.compute_type
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model with caching."""
        try:
            # Create cache key based on model configuration
            cache_key = f"{self.model_size}_{self.device}_{self.compute_type}_{self.use_faster_whisper}"
            
            # Check if model is already cached
            if cache_key in _MODEL_CACHE:
                logger.info(f"Using cached Whisper model: {self.model_size}")
                self.model = _MODEL_CACHE[cache_key]
                return
            
            # Load new model
            if self.use_faster_whisper:
                logger.info(f"Loading faster-whisper model: {self.model_size}")
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            else:
                logger.info(f"Loading openai-whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
            
            # Cache the model
            _MODEL_CACHE[cache_key] = self.model
            logger.info("Whisper model loaded and cached successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_video(self, video_path: Path, language: str = "en") -> Dict:
        """
        Transcribe a video file.
        
        Args:
            video_path: Path to the video file
            language: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            Dictionary with transcription results
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Starting transcription of: {video_path}")
        start_time = time.time()
        
        try:
            if self.use_faster_whisper:
                result = self._transcribe_with_faster_whisper(video_path, language)
            else:
                result = self._transcribe_with_openai_whisper(video_path, language)
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["model_used"] = f"whisper-{self.model_size}"
            result["language"] = language
            
            logger.info(f"Transcription completed in {processing_time:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
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
                "confidence": getattr(segment, 'avg_logprob', 0.0)  # Convert logprob to confidence
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


class TranscriptionStorage:
    """
    Handles storage and retrieval of transcriptions in MongoDB.
    """
    
    def __init__(self, mongo_db):
        """
        Initialize transcription storage.
        
        Args:
            mongo_db: MongoDB database instance
        """
        self.db = mongo_db
        self.collection = self.db.transcriptions
    
    def store_transcription(self, video_id: Union[str, int], transcription_data: Dict) -> str:
        """
        Store transcription data in MongoDB.
        
        Args:
            video_id: ID of the video file (will be converted to int for consistency)
            transcription_data: Transcription results from Whisper
            
        Returns:
            MongoDB document ID
        """
        # Ensure video_id is always stored as an integer for consistency
        video_id_int = int(video_id) if isinstance(video_id, (str, int)) else video_id
        
        document = {
            "video_id": video_id_int,
            "created_at": time.time(),
            "segments": transcription_data["segments"],
            "language": transcription_data["language"],
            "language_probability": transcription_data.get("language_probability", 1.0),
            "duration": transcription_data.get("duration", 0.0),
            "model_used": transcription_data.get("model_used", "unknown"),
            "processing_time": transcription_data.get("processing_time", 0.0),
            "total_segments": len(transcription_data["segments"]),
            "full_text": " ".join([seg["text"] for seg in transcription_data["segments"]])
        }
        
        result = self.collection.insert_one(document)
        logger.info(f"Stored transcription for video {video_id}: {result.inserted_id}")
        return str(result.inserted_id)
    
    def get_transcription(self, video_id: Union[str, int]) -> Optional[Dict]:
        """Get transcription for a video."""
        # Ensure consistent integer lookup
        video_id_int = int(video_id) if isinstance(video_id, (str, int)) else video_id
        return self.collection.find_one({"video_id": video_id_int})
    
    def search_transcriptions(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search transcriptions by text content.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching transcriptions
        """
        # Create text index if it doesn't exist
        try:
            self.collection.create_index([("full_text", "text")])
        except Exception:
            pass  # Index might already exist
        
        # Search using MongoDB text search
        results = self.collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort("score", -1).limit(limit)
        
        return list(results)
    
    def generate_srt_subtitle(self, transcription_data: Dict, output_path: Path) -> bool:
        """
        Generate SRT subtitle file from transcription data.
        
        Args:
            transcription_data: Transcription data with segments
            output_path: Path to save SRT file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            segments = transcription_data.get("segments", [])
            if not segments:
                logger.warning("No segments found in transcription data")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_srt_time(segment["start"])
                    end_time = self._format_srt_time(segment["end"])
                    text = segment["text"].strip()
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            
            logger.info(f"Generated SRT subtitle file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate SRT subtitle: {e}")
            return False
    
    def generate_vtt_subtitle(self, transcription_data: Dict, output_path: Path) -> bool:
        """
        Generate VTT subtitle file from transcription data.
        
        Args:
            transcription_data: Transcription data with segments
            output_path: Path to save VTT file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            segments = transcription_data.get("segments", [])
            if not segments:
                logger.warning("No segments found in transcription data")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for segment in segments:
                    start_time = self._format_vtt_time(segment["start"])
                    end_time = self._format_vtt_time(segment["end"])
                    text = segment["text"].strip()
                    
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            
            logger.info(f"Generated VTT subtitle file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate VTT subtitle: {e}")
            return False
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for VTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"
    
    def get_analytics(self) -> Dict:
        """Get analytics about stored transcriptions."""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_transcriptions": {"$sum": 1},
                    "total_duration": {"$sum": "$duration"},
                    "avg_processing_time": {"$avg": "$processing_time"},
                    "languages": {"$addToSet": "$language"},
                    "models_used": {"$addToSet": "$model_used"}
                }
            }
        ]
        
        result = list(self.collection.aggregate(pipeline))
        if result:
            return result[0]
        return {}
