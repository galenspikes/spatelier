"""
Audio processing CLI commands.

This module provides command-line interfaces for audio processing operations.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from spatelier.cli.error_handlers import handle_cli_error, handle_file_not_found
from spatelier.core.config import Config
from spatelier.core.decorators import handle_errors, time_operation
from spatelier.core.logger import get_logger
from spatelier.core.service_factory import ServiceFactory
from spatelier.modules.audio.converter import AudioConverter

# Create the audio CLI app
app = typer.Typer(
    name="audio",
    help="Audio processing commands",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
@handle_errors(context="audio convert", verbose=True)
@time_operation(verbose=True)
def convert(
    input_file: Path = typer.Argument(..., help="Input audio file"),
    output_file: Path = typer.Argument(..., help="Output audio file"),
    bitrate: int = typer.Option(320, "--bitrate", "-b", help="Audio bitrate (kbps)"),
    format: str = typer.Option("mp3", "--format", "-f", help="Output format"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Convert audio to different format.

    Supports various input and output formats including MP3, FLAC, WAV, etc.
    """
    config = Config()
    logger = get_logger("audio-convert", verbose=verbose)

    # Validate input file
    if not input_file.exists():
        handle_file_not_found(input_file, "convert")

    try:
        with ServiceFactory(config, verbose=verbose) as services:
            # Create audio converter
            converter = AudioConverter(config, verbose=verbose)

            # Perform conversion
            result = converter.convert(
                input_file=input_file,
                output_file=output_file,
                format=format,
                bitrate=bitrate,
            )

            # Display success message
            console.print(
                Panel(
                    f"[green]✓[/green] Conversion successful!\n"
                    f"Input: {input_file.name}\n"
                    f"Output: {output_file.name}\n"
                    f"Format: {format.upper()}\n"
                    f"Bitrate: {bitrate}kbps\n"
                    f"Size: {result.metadata.get('input_size', 0):,} -> {result.metadata.get('output_size', 0):,} bytes",
                    title="Conversion Complete",
                    border_style="green",
                )
            )

    except Exception as e:
        handle_cli_error(e, "audio conversion")


@app.command()
@handle_errors(context="audio info", verbose=True)
@time_operation(verbose=True)
def info(
    file_path: Path = typer.Argument(..., help="Audio file to analyze"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Display detailed information about an audio file.
    """
    config = Config()
    logger = get_logger("audio-info", verbose=verbose)

    with ServiceFactory(config, verbose=verbose) as services:
        try:
            if not file_path.exists():
                handle_file_not_found(file_path, "analyze")

            # Create audio converter to get detailed info
            converter = AudioConverter(config, verbose=verbose)
            audio_info = converter.get_audio_info(file_path)

            # Create info table
            table = Table(title=f"Audio Information: {file_path.name}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("File Path", str(file_path))
            table.add_row("File Size", f"{file_path.stat().st_size:,} bytes")
            table.add_row("Format", audio_info.get("format", "unknown"))
            table.add_row("Codec", audio_info.get("codec", "unknown"))
            table.add_row("Duration", f"{audio_info.get('duration', 0):.2f} seconds")
            table.add_row("Bitrate", f"{audio_info.get('bitrate', 0):,} bps")
            table.add_row("Sample Rate", f"{audio_info.get('sample_rate', 0):,} Hz")
            table.add_row("Channels", str(audio_info.get("channels", 0)))
            table.add_row("Channel Layout", audio_info.get("channel_layout", "unknown"))

            console.print(table)

        except Exception as e:
            handle_cli_error(e, "audio analysis")
