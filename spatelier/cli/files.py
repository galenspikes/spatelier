"""
File tracking demonstration and CLI commands.

This module demonstrates OS-level file tracking capabilities
and provides CLI commands for file management.
"""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from spatelier.core.config import Config
from spatelier.core.file_tracker import FileIdentifier, FileTracker

console = Console()
app = typer.Typer(name="files", help="File tracking and management")


@app.command()
def track(
    file_path: str = typer.Argument(..., help="Path to file to track"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🔍 Track a file using OS-level identifiers.

    Shows the OS-level file identifier (device:inode) that persists
    even when files are moved or renamed.
    """
    config = Config()
    tracker = FileTracker(verbose=verbose)

    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        console.print(
            Panel(
                f"[red]✗[/red] File not found: {file_path}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Get file identifier
    file_id = tracker.get_file_identifier(file_path_obj)
    metadata = tracker.get_file_metadata(file_path_obj)

    if file_id:
        console.print(
            Panel(
                f"[green]✓[/green] File tracked successfully!\n"
                f"File: {metadata['name']}\n"
                f"Path: {metadata['path']}\n"
                f"Size: {metadata['size']:,} bytes\n"
                f"OS Identifier: {file_id}\n"
                f"Device: {metadata['device']}\n"
                f"Inode: {metadata['inode']}\n"
                f"Modified: {metadata['modified']}",
                title="File Tracking Info",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗[/red] Failed to get file identifier",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def find(
    file_id: str = typer.Argument(..., help="File identifier (device:inode)"),
    search_path: Optional[str] = typer.Option(None, "--path", "-p", help="Search path"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🔍 Find a file by its OS-level identifier.

    Searches for a file using its device:inode identifier,
    useful when files have been moved.
    """
    config = Config()
    tracker = FileTracker(verbose=verbose)

    try:
        device, inode = file_id.split(":")
        file_id_obj = FileIdentifier(device=int(device), inode=int(inode))
    except ValueError:
        console.print(
            Panel(
                f"[red]✗[/red] Invalid file identifier format. Use 'device:inode' (e.g., '16777234:19668159')",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Set search paths
    if search_path:
        search_paths = [Path(search_path)]
    else:
        # Default search paths
        search_paths = [
            Path.home(),
            Path("/tmp"),
            Path("/var/tmp"),
        ]

    # Find the file
    found_path = tracker.find_file_by_identifier(file_id_obj, search_paths)

    if found_path:
        metadata = tracker.get_file_metadata(found_path)
        console.print(
            Panel(
                f"[green]✓[/green] File found!\n"
                f"File: {metadata['name']}\n"
                f"Path: {metadata['path']}\n"
                f"Size: {metadata['size']:,} bytes\n"
                f"Modified: {metadata['modified']}",
                title="File Found",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗[/red] File with identifier {file_id} was not found in search paths",
                title="File Not Found",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def duplicates(
    search_path: str = typer.Argument(..., help="Path to search for duplicates"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🔍 Find duplicate files based on OS-level identifiers.

    Identifies files that have the same device:inode identifier,
    which means they are hard links to the same file.
    """
    config = Config()
    tracker = FileTracker(verbose=verbose)

    search_path_obj = Path(search_path)

    if not search_path_obj.exists():
        console.print(
            Panel(
                f"[red]✗[/red] Search path not found: {search_path}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Find duplicates
    duplicates = tracker.find_duplicate_files([search_path_obj])

    if duplicates:
        table = Table(title="Duplicate Files Found")
        table.add_column("File Identifier", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Paths", style="white")

        for file_id, paths in duplicates.items():
            table.add_row(file_id, str(len(paths)), "\n".join(str(p) for p in paths))

        console.print(table)

        console.print(
            Panel(
                f"Found {len(duplicates)} sets of duplicate files\n"
                f"Total duplicate files: {sum(len(paths) for paths in duplicates.values())}",
                title="Duplicate Summary",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                "[green]✓[/green] No duplicate files found",
                title="No Duplicates",
                border_style="green",
            )
        )


@app.command()
def demo(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🎯 Demonstrate file tracking capabilities.

    Creates test files and demonstrates how OS-level identifiers
    persist through moves but change with copies.
    """
    config = Config()
    tracker = FileTracker(verbose=verbose)

    console.print(
        Panel(
            "[blue]Creating demonstration files...[/blue]",
            title="File Tracking Demo",
            border_style="blue",
        )
    )

    # Create test files
    test_dir = Path("file_tracking_demo")
    test_dir.mkdir(exist_ok=True)

    original_file = test_dir / "original.txt"
    original_file.write_text("This is the original file content.")

    # Get original identifier
    original_id = tracker.get_file_identifier(original_file)
    original_metadata = tracker.get_file_metadata(original_file)

    console.print(f"[green]Original file created:[/green] {original_file}")
    console.print(f"[green]Original identifier:[/green] {original_id}")

    # Copy the file (creates new inode)
    copied_file = test_dir / "copied.txt"
    import shutil

    shutil.copy2(original_file, copied_file)
    copied_id = tracker.get_file_identifier(copied_file)

    console.print(f"[yellow]Copied file created:[/yellow] {copied_file}")
    console.print(f"[yellow]Copied identifier:[/yellow] {copied_id}")
    console.print(f"[yellow]Same identifier?[/yellow] {original_id == copied_id}")

    # Move the original file (preserves inode)
    moved_file = test_dir / "moved.txt"
    shutil.move(str(original_file), str(moved_file))
    moved_id = tracker.get_file_identifier(moved_file)

    console.print(f"[blue]Moved file:[/blue] {moved_file}")
    console.print(f"[blue]Moved identifier:[/blue] {moved_id}")
    console.print(f"[blue]Same as original?[/blue] {original_id == moved_id}")

    # Create summary table
    table = Table(title="File Tracking Demonstration Results")
    table.add_column("Operation", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Identifier", style="magenta")
    table.add_column("Same as Original?", style="yellow")

    table.add_row("Original", str(original_file), str(original_id), "N/A")
    table.add_row(
        "Copy", str(copied_file), str(copied_id), str(original_id == copied_id)
    )
    table.add_row("Move", str(moved_file), str(moved_id), str(original_id == moved_id))

    console.print(table)

    # Cleanup
    console.print(f"[red]Cleaning up demo files...[/red]")
    import shutil

    shutil.rmtree(test_dir)

    console.print(
        Panel(
            "[green]✓[/green] Demonstration completed!\n\n"
            "[bold]Key Insights:[/bold]\n"
            "• Moving files preserves the OS identifier\n"
            "• Copying files creates a new identifier\n"
            "• This allows tracking files even when moved\n"
            "• Database can store device:inode for persistent tracking",
            title="Demo Complete",
            border_style="green",
        )
    )
