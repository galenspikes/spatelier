"""
Storage adapter interface and implementations.

Provides abstraction for different storage backends, allowing services
to work with storage without knowing implementation details.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


# Probe filename used to check write permission without leaving debris
_WRITE_PROBE_NAME = ".spatelier_write_probe"


class StorageAdapter(ABC):
    """
    Abstract storage adapter interface.

    Provides a unified interface for storage operations regardless of
    the underlying storage backend (local, NAS, cloud, etc.).
    """

    def can_write_to(self, path: Path) -> bool:
        """
        Check if path is writable (e.g. before moving files to NAS).

        Creates path if missing, writes and removes a probe file. Use this
        to fail fast before starting a download when destination is remote.
        """
        try:
            path = path.resolve()
            path.mkdir(parents=True, exist_ok=True)
            probe = path / _WRITE_PROBE_NAME
            probe.write_text("")
            probe.unlink(missing_ok=True)
            return True
        except (OSError, PermissionError):
            return False

    @abstractmethod
    def is_remote(self, path: Path) -> bool:
        """
        Check if path is on remote storage.

        Args:
            path: Path to check

        Returns:
            True if path is on remote storage, False otherwise
        """
        pass

    @abstractmethod
    def get_temp_processing_dir(self, job_id: int) -> Path:
        """
        Get temporary processing directory for a job.

        Args:
            job_id: Job ID

        Returns:
            Path to temporary processing directory
        """
        pass

    @abstractmethod
    def move_file(self, source_file: Path, dest_file: Path) -> bool:
        """
        Move file from source to destination.

        Args:
            source_file: Source file path
            dest_file: Destination file path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def cleanup_temp_dir(self, temp_dir: Path) -> bool:
        """
        Clean up temporary directory.

        Args:
            temp_dir: Temporary directory to clean up

        Returns:
            True if successful, False otherwise
        """
        pass


class LocalStorageAdapter(StorageAdapter):
    """
    Local storage adapter.

    Handles local file system operations.
    """

    def __init__(self, temp_dir: Path, logger=None):
        """
        Initialize local storage adapter.

        Args:
            temp_dir: Base temporary directory
            logger: Optional logger
        """
        self.temp_dir = temp_dir
        self.logger = logger

    def is_remote(self, path: Path) -> bool:
        """Check if path is on remote storage (always False for local)."""
        return False

    def get_temp_processing_dir(self, job_id: int) -> Path:
        """Get temporary processing directory for job."""
        temp_dir = self.temp_dir / str(job_id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def move_file(self, source_file: Path, dest_file: Path) -> bool:
        """Move file from source to destination."""
        try:
            import shutil

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_file), str(dest_file))
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to move file: {e}")
            return False

    def cleanup_temp_dir(self, temp_dir: Path) -> bool:
        """Clean up temporary directory."""
        try:
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
            return False


class NASStorageAdapter(StorageAdapter):
    """
    NAS (Network Attached Storage) adapter.

    Handles NAS-specific operations like detecting NAS paths and
    managing temporary processing directories for remote storage.
    """

    def __init__(self, temp_dir: Path, logger=None):
        """
        Initialize NAS storage adapter.

        Args:
            temp_dir: Base temporary directory for local processing
            logger: Optional logger
        """
        self.temp_dir = temp_dir
        self.logger = logger
        self.nas_indicators = [
            "/volumes/",
            "/mnt/",
            "nas",
            "network",
            "smb://",
            "nfs://",
        ]

    def is_remote(self, path: Path) -> bool:
        """Check if path is on NAS."""
        path_str = str(path)
        return any(nas_indicator in path_str.lower() for nas_indicator in self.nas_indicators)

    def get_temp_processing_dir(self, job_id: int) -> Path:
        """Get temporary processing directory for job (always local for NAS)."""
        temp_dir = self.temp_dir / str(job_id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def move_file(self, source_file: Path, dest_file: Path) -> bool:
        """Move file from local temp to NAS destination."""
        try:
            import shutil

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_file), str(dest_file))
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to move file to NAS: {e}")
            return False

    def cleanup_temp_dir(self, temp_dir: Path) -> bool:
        """Clean up temporary directory."""
        try:
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
            return False
