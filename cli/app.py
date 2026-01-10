"""
Main CLI application entry point.

This module provides the main Typer application that orchestrates all CLI commands.
"""

import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import video, audio, cli_utils, cli_analytics, worker, update, files
from core.config import Config
from core.logger import get_logger
from core.interactive_cli import run_interactive_cli
from core.package_updater import PackageUpdater

# Create the main Typer app
app = typer.Typer(
    name="spatelier",
    help="Personal tool library for video and music file handling",
    add_completion=False,
    rich_markup_mode="rich",
)

# Add subcommands
app.add_typer(video.app, name="video", help="Video processing commands")
app.add_typer(audio.app, name="audio", help="Audio processing commands")
app.add_typer(cli_utils.app, name="utils", help="Utility commands")
app.add_typer(cli_analytics.app, name="analytics", help="Analytics and reporting commands")
app.add_typer(worker.app, name="worker", help="Background job worker management")
app.add_typer(update.app, name="update", help="Package update management")
app.add_typer(files.app, name="files", help="File tracking and management")

# Add interactive mode command
@app.command()
def interactive(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    🎮 Launch interactive mode with guided workflows.
    
    Interactive mode provides a user-friendly interface for common operations
    like downloading videos, processing audio, and viewing analytics.
    """
    config = Config()
    run_interactive_cli(config, verbose)

# Global options
def version_callback(value: bool):
    """Show version information."""
    if value:
        version = None
        
        # Strategy 1: Try getting version from installed package metadata (standard way)
        try:
            from importlib.metadata import version
            version = version("spatelier")
        except Exception:
            pass
        
        # Strategy 2: Try importing from root __init__.py (when running from source)
        if version is None:
            try:
                import importlib.util
                from pathlib import Path
                root_init = Path(__file__).parent.parent / "__init__.py"
                if root_init.exists():
                    spec = importlib.util.spec_from_file_location("spatelier_init", root_init)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        version = module.__version__
            except Exception:
                pass
        
        # Strategy 3: Fallback to pyproject.toml version
        if version is None:
            try:
                import tomllib
                from pathlib import Path
                pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
                with open(pyproject_path, "rb") as f:
                    pyproject = tomllib.load(f)
                    version = pyproject["project"]["version"]
            except Exception:
                version = "unknown"
        
        console = Console()
        console.print(f"Spatelier version {version}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version information"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Enable verbose logging"
    ),
    config_file: str = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """
    Spatelier - Personal tool library for video and music file handling.
    
    A modular, extensible tool library built with modern Python architecture.
    """
    # Initialize configuration
    config = Config(config_file=config_file, verbose=verbose)
    
    # Initialize logger
    logger = get_logger(verbose=verbose)
    logger.info("Spatelier CLI started")
    
    # Start automatic background updates (opt-in via auto_update=True)
    # Note: Auto-updates are disabled by default - use explicit update commands
    # To enable: PackageUpdater(config, verbose=verbose, auto_update=True).start_background_update()


# Entry point function for setuptools
def main_entry():
    """Entry point for setuptools console script."""
    app()


if __name__ == "__main__":
    main_entry()
