"""
Audio conversion service.

This module provides audio conversion functionality using FFmpeg.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

import ffmpeg

from spatelier.core.base import ProcessingResult
from spatelier.core.base_service import BaseService
from spatelier.core.config import Config
from spatelier.utils.helpers import safe_filename


class AudioConverter(BaseService):
    """
    Audio conversion service using FFmpeg.

    Handles audio format conversion, quality adjustment, and basic processing.
    """

    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """Initialize the audio converter."""
        super().__init__(config, verbose, db_service)

        # Supported formats
        self.supported_formats = {
            "mp3": {"codec": "libmp3lame", "ext": ".mp3"},
            "wav": {"codec": "pcm_s16le", "ext": ".wav"},
            "flac": {"codec": "flac", "ext": ".flac"},
            "aac": {"codec": "aac", "ext": ".aac"},
            "ogg": {"codec": "libvorbis", "ext": ".ogg"},
            "m4a": {"codec": "aac", "ext": ".m4a"},
        }

    def convert(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        format: str = "mp3",
        bitrate: int = 320,
        **kwargs,
    ) -> ProcessingResult:
        """
        Convert audio file to different format.

        Args:
            input_file: Path to input audio file
            output_file: Path to output audio file
            format: Output format (mp3, wav, flac, aac, ogg, m4a)
            bitrate: Audio bitrate in kbps
            **kwargs: Additional conversion options

        Returns:
            ProcessingResult with conversion details
        """
        input_path = Path(input_file)
        output_path = Path(output_file)

        # Validate input file
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if not input_path.is_file():
            raise ValueError(f"Input path is not a file: {input_path}")

        # Validate format
        if format.lower() not in self.supported_formats:
            raise ValueError(
                f"Unsupported format: {format}. Supported: {list(self.supported_formats.keys())}"
            )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.logger.info(f"Converting {input_path} to {output_path}")

            # Build FFmpeg stream
            stream = ffmpeg.input(str(input_path))

            # Apply audio codec and bitrate
            format_info = self.supported_formats[format.lower()]
            stream = ffmpeg.output(
                stream,
                str(output_path),
                acodec=format_info["codec"],
                audio_bitrate=f"{bitrate}k",
            )

            # Add additional options
            if "start_time" in kwargs:
                stream = stream.overwrite_output()

            if "duration" in kwargs:
                stream = stream.overwrite_output()

            if "sample_rate" in kwargs:
                stream = stream.overwrite_output()

            if "channels" in kwargs:
                stream = stream.overwrite_output()

            # Run conversion
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            # Verify output file was created
            if not output_path.exists():
                raise RuntimeError("Output file was not created")

            # Get file info
            input_size = input_path.stat().st_size
            output_size = output_path.stat().st_size

            self.logger.info(
                f"Conversion successful: {input_size:,} -> {output_size:,} bytes"
            )

            return ProcessingResult(
                success=True,
                message=f"Converted {input_path.name} to {output_path.name}",
                input_file=str(input_path),
                output_file=str(output_path),
                duration_seconds=0,  # Could be calculated from metadata
                metadata={
                    "input_size": input_size,
                    "output_size": output_size,
                    "format": format,
                    "bitrate": bitrate,
                    "compression_ratio": (
                        round(output_size / input_size, 2) if input_size > 0 else 0
                    ),
                },
            )

        except ffmpeg.Error as e:
            # Clean up output file if it exists
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(f"FFmpeg conversion failed: {e}")
        except Exception as e:
            # Clean up output file if it exists
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(f"Audio conversion failed: {e}")

    def get_audio_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get audio file information using FFprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Use ffmpeg-python to probe the file
            probe = ffmpeg.probe(str(file_path))

            # Extract format info
            format_info = probe.get("format", {})

            # Extract audio stream info
            audio_stream = None
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break

            if not audio_stream:
                raise ValueError("No audio stream found in file")

            return {
                "format": format_info.get("format_name", "unknown"),
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "codec": audio_stream.get("codec_name", "unknown"),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "channel_layout": audio_stream.get("channel_layout", "unknown"),
            }

        except ffmpeg.Error as e:
            raise RuntimeError(f"FFprobe failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Audio analysis failed: {e}")
