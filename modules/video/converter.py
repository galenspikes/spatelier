"""
Video converter module.

This module provides video format conversion functionality using FFmpeg.
"""

import subprocess
from pathlib import Path
from typing import Union

from core.base import BaseConverter, ProcessingResult
from core.config import Config
from core.logger import get_logger


class VideoConverter(BaseConverter):
    """
    Video converter using FFmpeg.

    Supports various input and output formats.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """Initialize the video converter."""
        super().__init__(config, verbose)
        self.supported_input_formats = [
            "mp4",
            "avi",
            "mkv",
            "mov",
            "wmv",
            "flv",
            "webm",
            "m4v",
            "3gp",
        ]
        self.supported_output_formats = [
            "mp4",
            "avi",
            "mkv",
            "mov",
            "wmv",
            "flv",
            "webm",
            "m4v",
            "3gp",
        ]
        self.logger = get_logger("VideoConverter", verbose=verbose)

    def convert(
        self, input_path: Union[str, Path], output_path: Union[str, Path], **kwargs
    ) -> ProcessingResult:
        """
        Convert video from one format to another.

        Args:
            input_path: Path to input file
            output_path: Path to output file
            **kwargs: Additional conversion options

        Returns:
            ProcessingResult with conversion details
        """
        try:
            input_path = Path(input_path).expanduser().resolve()
            output_path = Path(output_path).expanduser().resolve()

            # Validate input
            if not self.validate_input(input_path):
                return ProcessingResult(
                    success=False,
                    message=f"Invalid input file: {input_path}",
                    errors=[f"Input file not found or invalid: {input_path}"],
                )

            # Validate formats
            if not self.is_supported_format(input_path, is_input=True):
                return ProcessingResult(
                    success=False,
                    message=f"Unsupported input format: {input_path.suffix}",
                    errors=[f"Unsupported input format: {input_path.suffix}"],
                )

            if not self.is_supported_format(output_path, is_input=False):
                return ProcessingResult(
                    success=False,
                    message=f"Unsupported output format: {output_path.suffix}",
                    errors=[f"Unsupported output format: {output_path.suffix}"],
                )

            # Ensure output directory exists
            if not self.ensure_output_dir(output_path):
                return ProcessingResult(
                    success=False,
                    message=f"Failed to create output directory: {output_path.parent}",
                    errors=[f"Cannot create output directory: {output_path.parent}"],
                )

            # Build FFmpeg command
            cmd = self._build_command(input_path, output_path, **kwargs)

            self.logger.info(f"Converting video: {input_path} -> {output_path}")
            self.logger.debug(f"Command: {' '.join(cmd)}")

            # Execute conversion
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and output_path.exists():
                return ProcessingResult(
                    success=True,
                    message=f"Video converted successfully: {output_path}",
                    output_path=output_path,
                    metadata={
                        "input_file": str(input_path),
                        "output_file": str(output_path),
                        "input_size": input_path.stat().st_size,
                        "output_size": output_path.stat().st_size,
                        "command": " ".join(cmd),
                    },
                )
            else:
                return ProcessingResult(
                    success=False,
                    message=f"Conversion failed: {result.stderr}",
                    errors=[result.stderr],
                )

        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            return ProcessingResult(
                success=False, message=f"Conversion failed: {str(e)}", errors=[str(e)]
            )

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "medium",
        codec: str = "auto",
        **kwargs,
    ) -> list:
        """
        Build FFmpeg command.

        Args:
            input_path: Input file path
            output_path: Output file path
            quality: Output quality
            codec: Video codec
            **kwargs: Additional options

        Returns:
            Command list for subprocess
        """
        cmd = ["ffmpeg", "-i", str(input_path)]

        # Video codec
        if codec == "auto":
            if output_path.suffix.lower() == ".mp4":
                cmd.extend(["-c:v", "libx264"])
            elif output_path.suffix.lower() == ".webm":
                cmd.extend(["-c:v", "libvpx-vp9"])
            else:
                cmd.extend(["-c:v", "libx264"])
        else:
            cmd.extend(["-c:v", codec])

        # Quality settings
        if quality == "high":
            cmd.extend(["-crf", "18", "-preset", "slow"])
        elif quality == "medium":
            cmd.extend(["-crf", "23", "-preset", "medium"])
        elif quality == "low":
            cmd.extend(["-crf", "28", "-preset", "fast"])
        else:
            cmd.extend(["-crf", "23", "-preset", "medium"])

        # Audio codec
        cmd.extend(["-c:a", "aac"])

        # Additional options
        if self.verbose:
            cmd.append("-v")
            cmd.append("info")
        else:
            cmd.extend(["-v", "quiet"])

        # Output file
        cmd.append(str(output_path))

        return cmd
