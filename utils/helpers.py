"""
General utility functions.

This module contains helper functions used throughout the application.
"""

import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)


def get_file_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use

    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)
    file_path = Path(file_path)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes
    """
    return Path(file_path).stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_file_type(file_path: Union[str, Path]) -> str:
    """
    Get MIME type of a file.

    Args:
        file_path: Path to file

    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def is_video_file(file_path: Union[str, Path]) -> bool:
    """
    Check if file is a video file.

    Args:
        file_path: Path to file

    Returns:
        True if file is a video, False otherwise
    """
    mime_type = get_file_type(file_path)
    return mime_type.startswith("video/")


def is_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Check if file is an audio file.

    Args:
        file_path: Path to file

    Returns:
        True if file is audio, False otherwise
    """
    mime_type = get_file_type(file_path)
    return mime_type.startswith("audio/")


def find_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = True,
    file_types: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find files matching pattern in directory.

    Args:
        directory: Directory to search
        pattern: File pattern to match
        recursive: Whether to search recursively
        file_types: Optional list of file extensions to filter by

    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    files = []

    if recursive:
        files = list(directory.rglob(pattern))
    else:
        files = list(directory.glob(pattern))

    if file_types:
        file_types = [ext.lower().lstrip(".") for ext in file_types]
        files = [f for f in files if f.suffix.lower().lstrip(".") in file_types]

    return files


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename
        max_length: Maximum length of filename

    Returns:
        Safe filename
    """
    # Characters not allowed in filenames
    invalid_chars = '<>:"/\\|?*'

    # Replace invalid characters
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing spaces and dots
    filename = filename.strip(" .")
    # Replace multiple spaces with single space and strip again
    import re

    filename = re.sub(r"\s+", " ", filename).strip()
    # Remove trailing spaces before extension
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        filename = name.strip() + "." + ext

    # Truncate if too long
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        filename = name[:max_name_length] + ("." + ext if ext else "")

    return filename


def copy_file_with_progress(
    src: Union[str, Path], dst: Union[str, Path], description: str = "Copying file"
) -> bool:
    """
    Copy file with progress bar.

    Args:
        src: Source file path
        dst: Destination file path
        description: Description for progress bar

    Returns:
        True if successful, False otherwise
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        return False

    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    file_size = src.stat().st_size

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=Console(),
    ) as progress:
        task = progress.add_task(description, total=file_size)

        with open(src, "rb") as f_src, open(dst, "wb") as f_dst:
            while True:
                chunk = f_src.read(8192)
                if not chunk:
                    break
                f_dst.write(chunk)
                progress.update(task, advance=len(chunk))

    return True


def cleanup_temp_files(temp_dir: Union[str, Path]) -> None:
    """
    Clean up temporary files in directory.

    Args:
        temp_dir: Directory containing temporary files
    """
    temp_path = Path(temp_dir)

    if temp_path.exists():
        try:
            shutil.rmtree(temp_path)
        except Exception:
            pass  # Ignore cleanup errors
