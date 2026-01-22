"""
Utility CLI commands.

This module provides command-line interfaces for utility operations.
"""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import Config
from core.decorators import handle_errors, time_operation
from core.logger import get_logger
from utils.helpers import format_file_size, get_file_hash, get_file_size, get_file_type

# Create the utils CLI app
app = typer.Typer(
    name="utils",
    help="Utility commands",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def hash(
    file_path: Path = typer.Argument(..., help="File to hash"),
    algorithm: str = typer.Option("sha256", "--algorithm", "-a", help="Hash algorithm"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Calculate hash of a file.
    """
    config = Config()
    logger = get_logger("utils-hash", verbose=verbose)

    try:
        if not file_path.exists():
            console.print(
                Panel(
                    f"[red]✗[/red] File not found: {file_path}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        hash_value = get_file_hash(file_path, algorithm)

        console.print(
            Panel(
                f"File: {file_path}\n"
                f"Algorithm: {algorithm.upper()}\n"
                f"Hash: {hash_value}",
                title="File Hash",
                border_style="green",
            )
        )

    except Exception as e:
        logger.error(f"Hash calculation failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] Hash calculation failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def info(
    file_path: Path = typer.Argument(..., help="File to analyze"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Display detailed information about a file.
    """
    config = Config()
    logger = get_logger("utils-info", verbose=verbose)

    try:
        if not file_path.exists():
            console.print(
                Panel(
                    f"[red]✗[/red] File not found: {file_path}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        # Get file information
        file_size = get_file_size(file_path)
        file_type = get_file_type(file_path)
        file_hash = get_file_hash(file_path)

        # Create info table
        table = Table(title=f"File Information: {file_path.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("File Path", str(file_path))
        table.add_row("File Name", file_path.name)
        table.add_row("File Size", format_file_size(file_size))
        table.add_row("File Type", file_type)
        table.add_row("Extension", file_path.suffix)
        table.add_row("SHA256", file_hash)

        console.print(table)

    except Exception as e:
        logger.error(f"File analysis failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] File analysis failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def find(
    directory: Path = typer.Argument(..., help="Directory to search"),
    pattern: str = typer.Option("*", "--pattern", "-p", help="File pattern to match"),
    file_types: Optional[List[str]] = typer.Option(
        None, "--type", "-t", help="File types to filter by"
    ),
    recursive: bool = typer.Option(
        True, "--recursive", "-r", help="Search recursively"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Find files matching pattern in directory.
    """
    config = Config()
    logger = get_logger("utils-find", verbose=verbose)

    try:
        if not directory.exists():
            console.print(
                Panel(
                    f"[red]✗[/red] Directory not found: {directory}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        from utils.helpers import find_files

        files = find_files(directory, pattern, recursive, file_types)

        if not files:
            console.print(
                Panel(
                    f"[yellow]⚠[/yellow] No files found matching pattern: {pattern}",
                    title="No Files",
                    border_style="yellow",
                )
            )
            return

        # Create results table
        table = Table(title=f"Found {len(files)} files")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="magenta")
        table.add_column("Type", style="green")

        for file_path in files[:50]:  # Limit to first 50 results
            file_size = get_file_size(file_path)
            file_type = get_file_type(file_path)
            table.add_row(
                str(file_path.relative_to(directory)),
                format_file_size(file_size),
                file_type,
            )

        console.print(table)

        if len(files) > 50:
            console.print(f"\n... and {len(files) - 50} more files")

    except Exception as e:
        logger.error(f"File search failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] File search failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit configuration file"),
    reset: bool = typer.Option(
        False, "--reset", "-r", help="Reset to default configuration"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Manage configuration settings.
    """
    config = Config()
    logger = get_logger("utils-config", verbose=verbose)

    try:
        if show:
            # Show current configuration
            table = Table(title="Current Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Video Format", config.video.default_format)
            table.add_row("Video Quality", config.video.quality)
            table.add_row("Video Output Dir", str(config.video.output_dir))
            table.add_row("Audio Format", config.audio.default_format)
            table.add_row("Audio Bitrate", str(config.audio.bitrate))
            table.add_row("Audio Output Dir", str(config.audio.output_dir))
            table.add_row("Log Level", config.log_level)

            console.print(table)

        elif edit:
            # Edit configuration file
            config_path = config.get_default_config_path()
            console.print(
                Panel(
                    f"[yellow]⚠[/yellow] Configuration editing not yet implemented.\n"
                    f"Config file: {config_path}",
                    title="Not Implemented",
                    border_style="yellow",
                )
            )

        elif reset:
            # Reset configuration
            config_path = config.get_default_config_path()
            if config_path.exists():
                config_path.unlink()

            config.ensure_default_config()
            console.print(
                Panel(
                    f"[green]✓[/green] Configuration reset to defaults\n"
                    f"Config file: {config_path}",
                    title="Reset Complete",
                    border_style="green",
                )
            )

    except Exception as e:
        logger.error(f"Configuration management failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] Configuration management failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
