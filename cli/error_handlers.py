"""
Common error handlers for CLI commands.

This module provides standardized error handling patterns
for all CLI commands to ensure consistency.
"""

from pathlib import Path
from typing import Any, Optional
import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def handle_cli_error(
    error: Exception,
    context: str = "",
    show_traceback: bool = False
) -> None:
    """
    Standardized error handler for CLI commands.
    
    Args:
        error: The exception that occurred
        context: Additional context about the operation
        show_traceback: Whether to show full traceback
    """
    error_msg = str(error)
    
    # Create standardized error message
    if context:
        title = f"Error in {context}"
    else:
        title = "Error"
    
    # Format error message
    if show_traceback:
        console.print(Panel(
            f"[red]✗[/red] {error_msg}\n\nTraceback:\n{error.__traceback__}",
            title=title,
            border_style="red"
        ))
    else:
        console.print(Panel(
            f"[red]✗[/red] {error_msg}",
            title=title,
            border_style="red"
        ))
    
    # Exit with error code
    raise typer.Exit(1)


def handle_file_not_found(file_path: Path, operation: str = "access") -> None:
    """
    Handle file not found errors with consistent messaging.
    
    Args:
        file_path: The file that was not found
        operation: The operation being performed (access, read, write, etc.)
    """
    handle_cli_error(
        FileNotFoundError(f"File not found: {file_path}"),
        context=f"File {operation}"
    )


def handle_directory_not_found(dir_path: Path, operation: str = "access") -> None:
    """
    Handle directory not found errors with consistent messaging.
    
    Args:
        dir_path: The directory that was not found
        operation: The operation being performed (access, read, write, etc.)
    """
    handle_cli_error(
        FileNotFoundError(f"Directory not found: {dir_path}"),
        context=f"Directory {operation}"
    )


def handle_permission_error(file_path: Path, operation: str = "access") -> None:
    """
    Handle permission errors with consistent messaging.
    
    Args:
        file_path: The file/directory with permission issues
        operation: The operation being performed
    """
    handle_cli_error(
        PermissionError(f"Permission denied: {file_path}"),
        context=f"File {operation}"
    )


def handle_validation_error(message: str, field: str = "") -> None:
    """
    Handle validation errors with consistent messaging.
    
    Args:
        message: The validation error message
        field: The field that failed validation
    """
    context = f"Validation error for {field}" if field else "Validation error"
    handle_cli_error(
        ValueError(message),
        context=context
    )


def handle_not_implemented(feature: str) -> None:
    """
    Handle not implemented features with consistent messaging.
    
    Args:
        feature: The feature that is not implemented
    """
    console.print(Panel(
        f"[yellow]⚠[/yellow] {feature} is not yet implemented.\n"
        f"This feature is planned for a future release.",
        title="Not Implemented",
        border_style="yellow"
    ))
    raise typer.Exit(0)  # Exit with success since this is expected
