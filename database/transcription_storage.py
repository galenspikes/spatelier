"""
SQLite-backed transcription storage (JSON + FTS5).

Stores full transcription segments as JSON, with a flattened full_text column
indexed by SQLite FTS5 for search.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.models import Transcription


class SQLiteTranscriptionStorage:
    """SQLite transcription storage adapter."""

    def __init__(self, session: Session):
        """
        Initialize SQLite transcription storage.

        Args:
            session: SQLAlchemy session bound to SQLite
        """
        self.session = session

    def store_transcription(
        self, video_id: Union[str, int], transcription_data: Dict[str, Any]
    ) -> int:
        """
        Store transcription data in SQLite.

        Args:
            video_id: ID of the video file (converted to int)
            transcription_data: Transcription results with segments

        Returns:
            SQLite record ID
        """
        video_id_int = int(video_id) if isinstance(video_id, (str, int)) else video_id
        segments = transcription_data.get("segments", [])
        full_text = " ".join([seg.get("text", "").strip() for seg in segments]).strip()

        record = Transcription(
            media_file_id=video_id_int,
            language=transcription_data.get("language"),
            duration=transcription_data.get("duration"),
            processing_time=transcription_data.get("processing_time"),
            model_used=transcription_data.get("model_used"),
            segments_json=segments,
            full_text=full_text,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record.id

    def get_transcription(self, video_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get transcription for a video.

        Args:
            video_id: Video ID

        Returns:
            Transcription dictionary or None
        """
        video_id_int = int(video_id) if isinstance(video_id, (str, int)) else video_id
        record = (
            self.session.query(Transcription)
            .filter(Transcription.media_file_id == video_id_int)
            .order_by(Transcription.id.desc())
            .first()
        )
        if not record:
            return None

        return {
            "id": record.id,
            "video_id": record.media_file_id,
            "language": record.language,
            "duration": record.duration,
            "processing_time": record.processing_time,
            "model_used": record.model_used,
            "segments": record.segments_json,
            "full_text": record.full_text,
            "created_at": record.created_at,
        }

    def search_transcriptions(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search transcriptions by text content using SQLite FTS5.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching transcription dictionaries
        """
        sql = text(
            """
            SELECT t.id, t.media_file_id, t.language, t.duration, t.processing_time,
                   t.model_used, t.segments_json, t.full_text, t.created_at
            FROM transcriptions t
            JOIN transcriptions_fts fts ON fts.rowid = t.id
            WHERE fts.full_text MATCH :query
            ORDER BY bm25(transcriptions_fts)
            LIMIT :limit
            """
        )
        rows = self.session.execute(sql, {"query": query, "limit": limit}).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            segments = row.segments_json
            if isinstance(segments, str):
                try:
                    segments = json.loads(segments)
                except json.JSONDecodeError:
                    segments = []
            results.append(
                {
                    "id": row.id,
                    "video_id": row.media_file_id,
                    "language": row.language,
                    "duration": row.duration,
                    "processing_time": row.processing_time,
                    "model_used": row.model_used,
                    "segments": segments,
                    "full_text": row.full_text,
                    "created_at": row.created_at,
                }
            )
        return results

    def generate_srt_subtitle(
        self, transcription_data: Dict[str, Any], output_path: Path
    ) -> bool:
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
                return False

            with open(output_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_srt_time(segment.get("start", 0.0))
                    end_time = self._format_srt_time(segment.get("end", 0.0))
                    text_value = segment.get("text", "").strip()

                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text_value}\n\n")

            return True
        except Exception:
            return False

    def generate_vtt_subtitle(
        self, transcription_data: Dict[str, Any], output_path: Path
    ) -> bool:
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
                return False

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                for segment in segments:
                    start_time = self._format_vtt_time(segment.get("start", 0.0))
                    end_time = self._format_vtt_time(segment.get("end", 0.0))
                    text_value = segment.get("text", "").strip()

                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text_value}\n\n")

            return True
        except Exception:
            return False

    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"  # noqa: E231

    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for VTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"  # noqa: E231
