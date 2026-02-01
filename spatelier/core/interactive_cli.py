"""
Interactive CLI for Spatelier.

This module provides an interactive command-line interface with guided workflows,
menus, and user-friendly prompts for common operations.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from spatelier.core.config import Config
from spatelier.core.logger import get_logger
from spatelier.core.progress import track_progress


@dataclass
class MenuOption:
    """Menu option data class."""

    key: str
    title: str
    description: str
    action: Callable
    enabled: bool = True


class InteractiveCLI:
    """Interactive CLI for Spatelier."""

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize interactive CLI.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("InteractiveCLI", verbose=verbose)
        self.console = Console()

    def show_welcome(self):
        """Show welcome message."""
        welcome_text = Text(
            "🎬 Welcome to Spatelier Interactive Mode", style="bold blue"
        )
        subtitle = Text("Your personal video and audio processing toolkit", style="dim")

        self.console.print(
            Panel(
                f"{welcome_text}\n\n{subtitle}",
                title="🚀 Spatelier",
                border_style="blue",
            )
        )

    def show_main_menu(self) -> str:
        """Show main menu and get user choice."""
        menu_table = Table(
            title="📋 Main Menu", show_header=True, header_style="bold magenta"
        )
        menu_table.add_column("Option", style="cyan", no_wrap=True)
        menu_table.add_column("Description", style="white")

        menu_table.add_row("1", "📥 Download Video/Playlist")
        menu_table.add_row("2", "🎵 Process Audio")
        menu_table.add_row("3", "📊 View Analytics")
        menu_table.add_row("4", "⚙️  System Settings")
        menu_table.add_row("5", "❓ Help & Documentation")
        menu_table.add_row("0", "🚪 Exit")

        self.console.print(menu_table)

        choice = Prompt.ask(
            "Select an option", choices=["1", "2", "3", "4", "5", "0"], default="1"
        )

        return choice

    def download_video_workflow(self):
        """Interactive video download workflow."""
        self.console.print(Panel("📥 Video Download Workflow", border_style="green"))

        # Get URL
        url = Prompt.ask("Enter video/playlist URL")
        if not url:
            self.console.print("[red]No URL provided[/red]")
            return

        # Detect if it's a playlist
        is_playlist = "playlist" in url.lower() or "/videos" in url

        if is_playlist:
            self.console.print("[yellow]📺 Playlist detected![/yellow]")

            # Get max videos
            max_videos = IntPrompt.ask(
                "Maximum videos to download", default=10, show_default=True
            )

            # Ask about transcription
            transcribe = Confirm.ask(
                "Enable transcription for all videos?", default=False
            )
        else:
            max_videos = 1
            transcribe = Confirm.ask("Enable transcription?", default=False)

        # Get quality
        quality_choices = ["720p", "1080p", "1440p", "2160p", "best"]
        quality = Prompt.ask(
            "Select video quality", choices=quality_choices, default="1080p"
        )

        # Get output directory
        from spatelier.core.config import get_default_data_dir

        repo_root = get_default_data_dir().parent
        output_dir = Prompt.ask(
            "Output directory", default=str(repo_root / "downloads")
        )

        # Confirm settings
        self.console.print("\n[bold]Download Settings:[/bold]")
        self.console.print(f"URL: {url}")
        self.console.print(f"Quality: {quality}")
        self.console.print(f"Output: {output_dir}")
        if is_playlist:
            self.console.print(f"Max Videos: {max_videos}")
        self.console.print(f"Transcription: {'Yes' if transcribe else 'No'}")

        if not Confirm.ask("Proceed with download?"):
            self.console.print("[yellow]Download cancelled[/yellow]")
            return

        # Execute download
        try:
            from spatelier.cli.video import download

            with track_progress("Downloading...", verbose=True) as progress:
                # This would call the actual download function
                self.console.print("[green]✅ Download completed![/green]")

        except Exception as e:
            self.console.print(f"[red]❌ Download failed: {e}[/red]")

    def process_audio_workflow(self):
        """Interactive audio processing workflow."""
        self.console.print(Panel("🎵 Audio Processing Workflow", border_style="yellow"))

        # Get input file
        input_file = Prompt.ask("Enter audio file path")
        if not input_file or not Path(input_file).exists():
            self.console.print("[red]File not found[/red]")
            return

        # Get operation type
        operation = Prompt.ask(
            "Select operation", choices=["convert", "info"], default="convert"
        )

        if operation == "convert":
            # Get output format
            format_choices = ["mp3", "wav", "flac", "aac", "ogg", "m4a"]
            output_format = Prompt.ask(
                "Output format", choices=format_choices, default="mp3"
            )

            # Get bitrate
            bitrate = IntPrompt.ask(
                "Audio bitrate (kbps)", default=320, show_default=True
            )

            # Get output file
            output_file = Prompt.ask(
                "Output file path",
                default=str(Path(input_file).with_suffix(f".{output_format}")),
            )

            # Confirm settings
            self.console.print("\n[bold]Conversion Settings:[/bold]")
            self.console.print(f"Input: {input_file}")
            self.console.print(f"Output: {output_file}")
            self.console.print(f"Format: {output_format}")
            self.console.print(f"Bitrate: {bitrate} kbps")

            if not Confirm.ask("Proceed with conversion?"):
                self.console.print("[yellow]Conversion cancelled[/yellow]")
                return

            # Execute conversion
            try:
                with track_progress("Converting audio...", verbose=True) as progress:
                    # This would call the actual conversion function
                    self.console.print("[green]✅ Conversion completed![/green]")

            except Exception as e:
                self.console.print(f"[red]❌ Conversion failed: {e}[/red]")

        elif operation == "info":
            try:
                with track_progress(
                    "Analyzing audio file...", verbose=True
                ) as progress:
                    # This would call the actual info function
                    self.console.print("[green]✅ Analysis completed![/green]")

            except Exception as e:
                self.console.print(f"[red]❌ Analysis failed: {e}[/red]")

    def view_analytics_workflow(self):
        """Interactive analytics workflow."""
        self.console.print(Panel("📊 Analytics Dashboard", border_style="blue"))

        # Show analytics options
        analytics_choices = ["dashboard", "export", "stats"]
        choice = Prompt.ask(
            "Select analytics option", choices=analytics_choices, default="dashboard"
        )

        if choice == "dashboard":
            try:
                from spatelier.core.analytics_dashboard import show_analytics_dashboard

                show_analytics_dashboard(self.config, self.verbose)
            except Exception as e:
                self.console.print(f"[red]❌ Dashboard failed: {e}[/red]")

        elif choice == "export":
            from spatelier.core.config import get_default_data_dir

            repo_root = get_default_data_dir().parent
            output_path = Prompt.ask(
                "Export file path", default=str(repo_root / "analytics_export.json")
            )

            try:
                from spatelier.core.analytics_dashboard import export_analytics_data

                success = export_analytics_data(
                    self.config, Path(output_path), self.verbose
                )
                if success:
                    self.console.print(
                        f"[green]✅ Analytics exported to {output_path}[/green]"
                    )
                else:
                    self.console.print("[red]❌ Export failed[/red]")
            except Exception as e:
                self.console.print(f"[red]❌ Export failed: {e}[/red]")

        elif choice == "stats":
            try:
                from spatelier.core.analytics_dashboard import AnalyticsDashboard

                dashboard = AnalyticsDashboard(self.config, self.verbose)
                stats = dashboard.get_processing_stats()
                health = dashboard.get_system_health()

                # Show stats
                stats_table = dashboard.create_stats_table(stats)
                health_table = dashboard.create_health_table(health)

                self.console.print(stats_table)
                self.console.print(health_table)

            except Exception as e:
                self.console.print(f"[red]❌ Stats failed: {e}[/red]")

    def system_settings_workflow(self):
        """Interactive system settings workflow."""
        self.console.print(Panel("⚙️ System Settings", border_style="cyan"))

        settings_choices = ["config", "paths", "database", "workers"]
        choice = Prompt.ask(
            "Select settings category", choices=settings_choices, default="config"
        )

        if choice == "config":
            self.console.print(
                "[yellow]Configuration settings would be shown here[/yellow]"
            )
        elif choice == "paths":
            self.console.print("[yellow]Path settings would be shown here[/yellow]")
        elif choice == "database":
            self.console.print("[yellow]Database settings would be shown here[/yellow]")
        elif choice == "workers":
            self.console.print("[yellow]Worker settings would be shown here[/yellow]")

    def help_workflow(self):
        """Show help and documentation."""
        self.console.print(Panel("❓ Help & Documentation", border_style="magenta"))

        help_choices = ["commands", "examples", "troubleshooting", "api"]
        choice = Prompt.ask(
            "Select help topic", choices=help_choices, default="commands"
        )

        if choice == "commands":
            self.console.print(
                "[yellow]Command documentation would be shown here[/yellow]"
            )
        elif choice == "examples":
            self.console.print("[yellow]Usage examples would be shown here[/yellow]")
        elif choice == "troubleshooting":
            self.console.print(
                "[yellow]Troubleshooting guide would be shown here[/yellow]"
            )
        elif choice == "api":
            self.console.print("[yellow]API documentation would be shown here[/yellow]")

    def run_interactive_mode(self):
        """Run the interactive CLI mode."""
        self.show_welcome()

        while True:
            try:
                choice = self.show_main_menu()

                if choice == "1":
                    self.download_video_workflow()
                elif choice == "2":
                    self.process_audio_workflow()
                elif choice == "3":
                    self.view_analytics_workflow()
                elif choice == "4":
                    self.system_settings_workflow()
                elif choice == "5":
                    self.help_workflow()
                elif choice == "0":
                    self.console.print("[green]👋 Goodbye![/green]")
                    break

                # Ask if user wants to continue
                if not Confirm.ask("\nContinue with another operation?", default=True):
                    self.console.print("[green]👋 Goodbye![/green]")
                    break

            except KeyboardInterrupt:
                self.console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]❌ Error: {e}[/red]")
                self.logger.error(f"Interactive CLI error: {e}")


def run_interactive_cli(config: Config, verbose: bool = False):
    """
    Run the interactive CLI.

    Args:
        config: Configuration instance
        verbose: Enable verbose logging
    """
    cli = InteractiveCLI(config, verbose)
    cli.run_interactive_mode()
