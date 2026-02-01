"""
Streaming video processing utilities.

This module provides streaming capabilities for processing large video files
without loading them entirely into memory.
"""

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import ffmpeg

from spatelier.core.logger import get_logger
from spatelier.core.progress import track_progress


class VideoStreamProcessor:
    """Stream-based video processor for large files."""

    def __init__(self, config, verbose: bool = False):
        """
        Initialize streaming video processor.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("VideoStreamProcessor", verbose=verbose)

    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """
        Get video information using ffmpeg-python without loading the entire file.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        try:
            probe = ffmpeg.probe(str(video_path))
            return probe

        except ffmpeg.Error as e:
            self.logger.error(f"FFmpeg probe failed: {e}")
            raise RuntimeError(f"Failed to probe video: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get video info: {e}")
            raise

    def stream_video_segments(
        self, video_path: Path, segment_duration: int = 60
    ) -> Iterator[Path]:
        """
        Stream video in segments for processing.

        Args:
            video_path: Path to video file
            segment_duration: Duration of each segment in seconds

        Yields:
            Path to temporary segment files
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="spatelier_segments_"))

        try:
            # Get video duration
            info = self.get_video_info(video_path)
            duration = float(info["format"]["duration"])

            self.logger.info(
                f"Streaming video: {duration:.1f}s total, {segment_duration}s segments"
            )

            segment_count = int(duration // segment_duration) + 1

            with track_progress(
                f"Creating {segment_count} video segments", total=segment_count
            ) as progress:
                for i in range(segment_count):
                    start_time = i * segment_duration
                    segment_path = temp_dir / f"segment_{i:03d}.mp4"

                    try:
                        # Extract segment using ffmpeg-python
                        (
                            ffmpeg.input(
                                str(video_path), ss=start_time, t=segment_duration
                            )
                            .output(
                                str(segment_path),
                                c="copy",
                                avoid_negative_ts="make_zero",
                            )
                            .overwrite_output()
                            .run(quiet=True)
                        )

                        progress.update(1, f"Created segment {i + 1}/{segment_count}")
                        yield segment_path

                    except ffmpeg.Error as e:
                        self.logger.warning(f"Failed to create segment {i}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            # Cleanup on error
            self._cleanup_temp_dir(temp_dir)
            raise

    def process_video_stream(
        self,
        video_path: Path,
        processor_func: Callable[[Path], Any],
        segment_duration: int = 60,
    ) -> Iterator[Any]:
        """
        Process video in streaming fashion.

        Args:
            video_path: Path to video file
            processor_func: Function to process each segment
            segment_duration: Duration of each segment in seconds

        Yields:
            Results from processing each segment
        """
        try:
            for segment_path in self.stream_video_segments(
                video_path, segment_duration
            ):
                try:
                    result = processor_func(segment_path)
                    yield result
                except Exception as e:
                    self.logger.error(f"Failed to process segment {segment_path}: {e}")
                    yield None
                finally:
                    # Clean up segment file
                    if segment_path.exists():
                        segment_path.unlink()

        except Exception as e:
            self.logger.error(f"Stream processing failed: {e}")
            raise

    def _cleanup_temp_dir(self, temp_dir: Path) -> None:
        """Clean up temporary directory."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")


class AudioStreamProcessor:
    """Stream-based audio processor for large files."""

    def __init__(self, config, verbose: bool = False):
        """
        Initialize streaming audio processor.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("AudioStreamProcessor", verbose=verbose)

    def stream_audio_chunks(
        self, audio_path: Path, chunk_duration: int = 30
    ) -> Iterator[Path]:
        """
        Stream audio in chunks for processing.

        Args:
            audio_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds

        Yields:
            Path to temporary chunk files
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="spatelier_audio_chunks_"))

        try:
            # Get audio duration using ffmpeg-python
            info = ffmpeg.probe(str(audio_path))
            duration = float(info["format"]["duration"])

            self.logger.info(
                f"Streaming audio: {duration:.1f}s total, {chunk_duration}s chunks"
            )

            chunk_count = int(duration // chunk_duration) + 1

            with track_progress(
                f"Creating {chunk_count} audio chunks", total=chunk_count
            ) as progress:
                for i in range(chunk_count):
                    start_time = i * chunk_duration
                    chunk_path = temp_dir / f"chunk_{i:03d}.wav"

                    try:
                        # Extract chunk using ffmpeg-python
                        (
                            ffmpeg.input(
                                str(audio_path), ss=start_time, t=chunk_duration
                            )
                            .output(str(chunk_path), acodec="pcm_s16le")
                            .overwrite_output()
                            .run(quiet=True)
                        )

                        progress.update(1, f"Created chunk {i + 1}/{chunk_count}")
                        yield chunk_path

                    except ffmpeg.Error as e:
                        self.logger.warning(f"Failed to create chunk {i}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Audio streaming failed: {e}")
            # Cleanup on error
            self._cleanup_temp_dir(temp_dir)
            raise

    def _cleanup_temp_dir(self, temp_dir: Path) -> None:
        """Clean up temporary directory."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")


@contextmanager
def stream_video_processing(video_path: Path, segment_duration: int = 60):
    """
    Context manager for streaming video processing.

    Args:
        video_path: Path to video file
        segment_duration: Duration of each segment in seconds

    Usage:
        with stream_video_processing(video_path) as processor:
            for segment in processor.segments:
                # Process segment
                result = process_segment(segment)
    """
    from spatelier.core.config import Config

    config = Config()
    processor = VideoStreamProcessor(config)

    try:
        yield processor
    finally:
        # Cleanup is handled by the processor
        pass


@contextmanager
def stream_audio_processing(audio_path: Path, chunk_duration: int = 30):
    """
    Context manager for streaming audio processing.

    Args:
        audio_path: Path to audio file
        chunk_duration: Duration of each chunk in seconds

    Usage:
        with stream_audio_processing(audio_path) as processor:
            for chunk in processor.chunks:
                # Process chunk
                result = process_chunk(chunk)
    """
    from spatelier.core.config import Config

    config = Config()
    processor = AudioStreamProcessor(config)

    try:
        yield processor
    finally:
        # Cleanup is handled by the processor
        pass
