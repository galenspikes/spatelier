"""
Progress tracking utilities for long-running operations.

This module provides progress bars and progress tracking for video processing,
downloads, and other long-running operations.
"""

import time
from contextlib import contextmanager
from typing import Any, Callable, Optional, ParamSpec, TypeVar

# Type variables for decorators
P = ParamSpec("P")
R = TypeVar("R")

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from spatelier.core.logger import get_logger

console = Console()


class ProgressTracker:
    """Track progress for long-running operations."""

    def __init__(
        self, description: str, total: Optional[int] = None, verbose: bool = False
    ):
        """
        Initialize progress tracker.

        Args:
            description: Description of the operation
            total: Total number of steps (None for indeterminate)
            verbose: Enable verbose logging
        """
        self.description = description
        self.total = total
        self.verbose = verbose
        self.logger = get_logger("ProgressTracker", verbose=verbose)
        self.progress = None
        self.task_id = None

    def __enter__(self):
        """Start progress tracking."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        )

        self.progress.start()

        if self.total:
            self.task_id = self.progress.add_task(self.description, total=self.total)
        else:
            self.task_id = self.progress.add_task(self.description, total=None)

        self.logger.info(f"Started progress tracking: {self.description}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress tracking."""
        if self.progress:
            self.progress.stop()
        self.logger.info(f"Completed progress tracking: {self.description}")

    def update(self, advance: int = 1, description: Optional[str] = None):
        """Update progress."""
        if self.progress and self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=description)
            self.progress.advance(self.task_id, advance)

    def set_total(self, total: int):
        """Set total progress."""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, total=total)


@contextmanager
def track_progress(
    description: str, total: Optional[int] = None, verbose: bool = False
):
    """
    Context manager for progress tracking.

    Args:
        description: Description of the operation
        total: Total number of steps (None for indeterminate)
        verbose: Enable verbose logging

    Usage:
        with track_progress("Downloading video", total=100) as progress:
            for i in range(100):
                # Do work
                progress.update(1)
    """
    tracker = ProgressTracker(description, total, verbose)
    with tracker:
        yield tracker


def progress_decorator(description: str, total_param: Optional[str] = None):
    """
    Decorator to add progress tracking to functions.

    Args:
        description: Description of the operation
        total_param: Parameter name that contains the total count

    Usage:
        @progress_decorator("Processing videos", "video_count")
        def process_videos(self, videos, video_count):
            # Function implementation
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Get total from parameter if specified
            total = None
            if total_param and total_param in kwargs:
                total = kwargs[total_param]
            elif total_param and len(args) > 0:
                # Try to get from first argument if it's a dict or object
                first_arg = args[0]
                if hasattr(first_arg, total_param):
                    total = getattr(first_arg, total_param)
                elif isinstance(first_arg, dict) and total_param in first_arg:
                    total = first_arg[total_param]

            with track_progress(description, total, verbose=True) as progress:
                # Pass progress tracker to the function
                if "progress" not in kwargs:
                    kwargs["progress"] = progress
                return func(*args, **kwargs)

        return wrapper

    return decorator


class DownloadProgress:
    """Progress tracking for video downloads."""

    def __init__(self, total_videos: int, verbose: bool = False):
        """
        Initialize download progress tracker.

        Args:
            total_videos: Total number of videos to download
            verbose: Enable verbose logging
        """
        self.total_videos = total_videos
        self.verbose = verbose
        self.logger = get_logger("DownloadProgress", verbose=verbose)
        self.progress = None
        self.task_id = None
        self.current_video = 0

    def __enter__(self):
        """Start download progress tracking."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        )

        self.progress.start()
        self.task_id = self.progress.add_task(
            f"Downloading {self.total_videos} videos", total=self.total_videos
        )

        self.logger.info(
            f"Started download progress tracking for {self.total_videos} videos"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop download progress tracking."""
        if self.progress:
            self.progress.stop()
        self.logger.info("Completed download progress tracking")

    def update_video(self, video_name: str, status: str = "downloading"):
        """Update progress for current video."""
        self.current_video += 1
        description = (
            f"Downloading video {self.current_video}/{self.total_videos}: {video_name}"
        )

        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=1, description=description)

        self.logger.info(
            f"Video {self.current_video}/{self.total_videos}: {video_name} - {status}"
        )


def show_download_progress(total_videos: int, verbose: bool = False):
    """
    Context manager for download progress tracking.

    Args:
        total_videos: Total number of videos to download
        verbose: Enable verbose logging

    Usage:
        with show_download_progress(10) as progress:
            for video in videos:
                # Download video
                progress.update_video(video.name)
    """
    return DownloadProgress(total_videos, verbose)
