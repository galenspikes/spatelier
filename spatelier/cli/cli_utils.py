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

from spatelier.core.config import Config
from spatelier.core.decorators import handle_errors, time_operation
from spatelier.core.logger import get_logger
from spatelier.utils.helpers import format_file_size, get_file_hash, get_file_size, get_file_type

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

        from spatelier.utils.helpers import find_files

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
    edit: bool = typer.Option(False, "--edit", "-e", help="Open config file in $EDITOR"),
    reset: bool = typer.Option(
        False, "--reset", "-r", help="Reset to default configuration"
    ),
    set_value: Optional[str] = typer.Option(
        None,
        "--set",
        help="Set a config value (e.g. --set video.output_dir=~/Videos)",
        metavar="KEY=VALUE",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Manage configuration settings.

    Examples:
      spatelier utils config --show
      spatelier utils config --set video.output_dir=~/Videos
      spatelier utils config --set video.quality=720p
      spatelier utils config --set audio.bitrate=256
      spatelier utils config --edit
    """
    import os
    import subprocess

    import yaml

    _default_cfg = Config()
    get_logger("utils-config", verbose=verbose)
    config_path = _default_cfg.get_default_config_path()
    cfg = Config.load_from_file(config_path) if config_path.exists() else _default_cfg

    try:
        if set_value:
            if "=" not in set_value:
                console.print(
                    Panel(
                        "[red]✗[/red] Invalid format. Use KEY=VALUE, e.g. --set video.output_dir=~/Videos",
                        title="Invalid Argument",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)

            raw_key, raw_val = set_value.split("=", 1)
            key_parts = raw_key.strip().split(".")

            # Load existing config dict (YAML) or start from defaults
            if config_path.exists():
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
            else:
                data = {}

            # Navigate/create the nested dict and set the leaf value
            node = data
            for part in key_parts[:-1]:
                node = node.setdefault(part, {})

            leaf_key = key_parts[-1]
            # Coerce to int if it looks like one, expand ~ in paths
            value: object
            if raw_val.lstrip("-").isdigit():
                value = int(raw_val)
            elif raw_val.lower() in ("true", "false"):
                value = raw_val.lower() == "true"
            elif raw_val.startswith("~"):
                value = str(Path(raw_val).expanduser())
            elif raw_val.lower() == "null" or raw_val == "":
                value = None
            else:
                value = raw_val
            node[leaf_key] = value

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)

            console.print(
                Panel(
                    f"[green]✓[/green] Set [cyan]{raw_key}[/cyan] = [magenta]{value}[/magenta]\n"
                    f"Config: {config_path}",
                    title="Config Updated",
                    border_style="green",
                )
            )

        elif show:
            table = Table(title="Current Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_column("Env Override", style="yellow", no_wrap=True)

            def env(var: str) -> str:
                v = os.getenv(var)
                return f"{var}={v}" if v else ""

            table.add_row("video.output_dir", str(cfg.video.output_dir), env("SPATELIER_OUTPUT"))
            table.add_row("video.quality", cfg.video.quality, env("SPATELIER_QUALITY"))
            table.add_row("video.default_format", cfg.video.default_format, env("SPATELIER_FORMAT"))
            table.add_row("audio.output_dir", str(cfg.audio.output_dir), env("SPATELIER_OUTPUT"))
            table.add_row("audio.default_format", cfg.audio.default_format, "")
            table.add_row("audio.bitrate", str(cfg.audio.bitrate), env("SPATELIER_BITRATE"))
            table.add_row("log_level", cfg.log_level, env("SPATELIER_LOG_LEVEL"))
            console.print(table)
            console.print(f"\n[dim]Config file: {config_path}[/dim]")

        elif edit:
            cfg.ensure_default_config()
            editor = os.getenv("VISUAL") or os.getenv("EDITOR") or "nano"
            console.print(f"Opening [cyan]{config_path}[/cyan] in [bold]{editor}[/bold]...")
            subprocess.call([editor, str(config_path)])

        elif reset:
            if config_path.exists():
                config_path.unlink()
            cfg.ensure_default_config()
            console.print(
                Panel(
                    f"[green]✓[/green] Configuration reset to defaults\n"
                    f"Config file: {config_path}",
                    title="Reset Complete",
                    border_style="green",
                )
            )

        else:
            console.print("[dim]Use --show, --set KEY=VALUE, --edit, or --reset[/dim]")
            console.print("[dim]Run with --help for examples[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            Panel(
                f"[red]✗[/red] {str(e)}",
                title="Config Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
