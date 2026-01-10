"""
File system test fixtures and utilities.

Provides fixtures for creating temporary files, directories,
and managing file system state during testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, List, Dict, Any
from unittest.mock import Mock

from utils.helpers import get_file_hash, get_file_type, get_file_size


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_video_file(temp_dir: Path) -> Path:
    """Create a temporary video file for testing."""
    video_path = temp_dir / "test_video.mp4"
    # Create a minimal MP4 file (just header)
    video_path.write_bytes(b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom')
    return video_path


@pytest.fixture
def temp_audio_file(temp_dir: Path) -> Path:
    """Create a temporary audio file for testing."""
    audio_path = temp_dir / "test_audio.mp3"
    # Create a minimal MP3 file
    audio_path.write_bytes(b'ID3\x03\x00\x00\x00\x00\x00\x00\x00')
    return audio_path


@pytest.fixture
def temp_srt_file(temp_dir: Path) -> Path:
    """Create a temporary SRT subtitle file for testing."""
    srt_path = temp_dir / "test_subtitles.srt"
    srt_content = """1
00:00:00,000 --> 00:00:02,000
Test subtitle line 1

2
00:00:02,000 --> 00:00:04,000
Test subtitle line 2
"""
    srt_path.write_text(srt_content, encoding='utf-8')
    return srt_path


@pytest.fixture
def temp_video_with_subs(temp_dir: Path) -> Path:
    """Create a temporary video file with embedded subtitles."""
    video_path = temp_dir / "test_video_with_subs.mp4"
    # Create a minimal MP4 file with subtitle track
    video_path.write_bytes(b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom')
    return video_path


@pytest.fixture
def sample_file_paths(temp_dir: Path) -> List[Path]:
    """Create sample file paths for testing."""
    files = [
        temp_dir / "video1.mp4",
        temp_dir / "video2.webm", 
        temp_dir / "audio1.mp3",
        temp_dir / "audio2.wav",
        temp_dir / "document.pdf"
    ]
    
    for file_path in files:
        file_path.write_text("test content")
    
    return files


@pytest.fixture
def mock_file_stats():
    """Mock file statistics for testing."""
    def _mock_stats(file_path: Path) -> Mock:
        mock_stat = Mock()
        mock_stat.st_size = 1024 * 1024  # 1MB
        mock_stat.st_mtime = 1640995200  # 2022-01-01
        return mock_stat
    return _mock_stats


@pytest.fixture
def file_factory():
    """Factory for creating test files with specific properties."""
    def _create_file(
        path: Path,
        content: str = "test content",
        size: int = None,
        mtime: float = None
    ) -> Path:
        path.write_text(content)
        
        if size is not None:
            # Truncate or extend file to desired size
            current_size = path.stat().st_size
            if size > current_size:
                path.write_bytes(path.read_bytes() + b'0' * (size - current_size))
            elif size < current_size:
                path.write_bytes(path.read_bytes()[:size])
        
        if mtime is not None:
            import os
            os.utime(path, (mtime, mtime))
        
        return path
    return _create_file


@pytest.fixture
def directory_tree(temp_dir: Path) -> Dict[str, Path]:
    """Create a sample directory tree for testing."""
    tree = {
        "root": temp_dir,
        "videos": temp_dir / "videos",
        "audio": temp_dir / "audio", 
        "temp": temp_dir / "temp",
        "output": temp_dir / "output"
    }
    
    # Create directories
    for path in tree.values():
        path.mkdir(parents=True, exist_ok=True)
    
    # Add some files
    (tree["videos"] / "video1.mp4").write_text("video content")
    (tree["audio"] / "audio1.mp3").write_text("audio content")
    (tree["temp"] / "temp_file.txt").write_text("temp content")
    
    return tree


@pytest.fixture
def nas_path_simulation(temp_dir: Path) -> Path:
    """Simulate a NAS path for testing."""
    nas_path = temp_dir / "nas" / "media"
    nas_path.mkdir(parents=True, exist_ok=True)
    return nas_path


@pytest.fixture
def large_file_factory():
    """Factory for creating large files for performance testing."""
    def _create_large_file(path: Path, size_mb: int = 10) -> Path:
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(path, 'wb') as f:
            for _ in range(size_mb):
                f.write(b'0' * chunk_size)
        return path
    return _create_large_file
