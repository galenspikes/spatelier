"""
File tracking utilities for persistent file identification.

This module provides OS-level file identification using inode and device numbers
to track files even when they are moved or renamed.
"""

import os
import shutil
import stat
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from core.logger import get_logger


@dataclass
class FileIdentifier:
    """OS-level file identifier."""
    
    device: int
    inode: int
    
    def __str__(self) -> str:
        """String representation as device:inode."""
        return f"{self.device}:{self.inode}"
    
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash((self.device, self.inode))
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, FileIdentifier):
            return False
        return self.device == other.device and self.inode == other.inode


class FileTracker:
    """
    Tracks files using OS-level identifiers.
    
    Provides persistent file identification that survives moves and renames,
    but distinguishes between original files and copies.
    """
    
    def __init__(self, verbose: bool = False):
        """Initialize file tracker."""
        self.verbose = verbose
        self.logger = get_logger("FileTracker", verbose=verbose)
    
    def get_file_identifier(self, file_path: Path) -> Optional[FileIdentifier]:
        """
        Get OS-level identifier for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileIdentifier with device and inode, or None if file doesn't exist
        """
        try:
            if not file_path.exists():
                self.logger.debug(f"File does not exist: {file_path}")
                return None
            
            stat_info = os.stat(file_path)
            return FileIdentifier(
                device=stat_info.st_dev,
                inode=stat_info.st_ino
            )
            
        except (OSError, FileNotFoundError) as e:
            self.logger.debug(f"Failed to get file identifier for {file_path}: {e}")
            return None
    
    def find_file_by_identifier(self, file_id: FileIdentifier, search_paths: list[Path]) -> Optional[Path]:
        """
        Find a file by its OS-level identifier.
        
        Args:
            file_id: FileIdentifier to search for
            search_paths: List of paths to search in
            
        Returns:
            Path to the file if found, None otherwise
        """
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            # Search recursively
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    current_id = self.get_file_identifier(file_path)
                    if current_id == file_id:
                        self.logger.debug(f"Found file by identifier: {file_path}")
                        return file_path
        
        self.logger.debug(f"File with identifier {file_id} not found in search paths")
        return None
    
    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Get comprehensive file metadata including OS identifiers.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            if not file_path.exists():
                return {"error": "File does not exist"}
            
            stat_info = os.stat(file_path)
            file_id = self.get_file_identifier(file_path)
            
            return {
                "path": str(file_path.absolute()),
                "name": file_path.name,
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "created": stat_info.st_ctime,
                "accessed": stat_info.st_atime,
                "permissions": oct(stat_info.st_mode),
                "file_identifier": str(file_id) if file_id else None,
                "device": stat_info.st_dev,
                "inode": stat_info.st_ino,
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
            }
            
        except (OSError, FileNotFoundError) as e:
            return {"error": str(e)}
    
    def track_file_move(self, old_path: Path, new_path: Path) -> bool:
        """
        Track a file move operation.
        
        Args:
            old_path: Original file path
            new_path: New file path
            
        Returns:
            True if the move was tracked successfully
        """
        try:
            old_id = self.get_file_identifier(old_path)
            if not old_id:
                self.logger.warning(f"Cannot track move - old file not found: {old_path}")
                return False
            
            # Perform the move (use shutil.move for cross-device support)
            shutil.move(str(old_path), str(new_path))
            
            # Verify the move
            new_id = self.get_file_identifier(new_path)
            if new_id == old_id:
                self.logger.info(f"Successfully tracked file move: {old_path} -> {new_path}")
                return True
            else:
                self.logger.error(f"File move verification failed - identifiers don't match")
                return False
                
        except (OSError, FileNotFoundError) as e:
            self.logger.error(f"Failed to track file move: {e}")
            return False
    
    def is_same_file(self, path1: Path, path2: Path) -> bool:
        """
        Check if two paths refer to the same file.
        
        Args:
            path1: First file path
            path2: Second file path
            
        Returns:
            True if both paths refer to the same file
        """
        id1 = self.get_file_identifier(path1)
        id2 = self.get_file_identifier(path2)
        
        if not id1 or not id2:
            return False
        
        return id1 == id2
    
    def find_duplicate_files(self, search_paths: list[Path]) -> Dict[str, list[Path]]:
        """
        Find duplicate files based on OS-level identifiers.
        
        Args:
            search_paths: List of paths to search for duplicates
            
        Returns:
            Dictionary mapping file identifiers to lists of duplicate paths
        """
        file_map: Dict[FileIdentifier, list[Path]] = {}
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    file_id = self.get_file_identifier(file_path)
                    if file_id:
                        if file_id not in file_map:
                            file_map[file_id] = []
                        file_map[file_id].append(file_path)
        
        # Return only duplicates (more than one file with same identifier)
        duplicates = {str(file_id): paths for file_id, paths in file_map.items() if len(paths) > 1}
        
        self.logger.info(f"Found {len(duplicates)} sets of duplicate files")
        return duplicates
    
    def validate_file_integrity(self, file_path: Path, expected_id: FileIdentifier) -> bool:
        """
        Validate that a file still has the expected identifier.
        
        Args:
            file_path: Path to check
            expected_id: Expected file identifier
            
        Returns:
            True if file has the expected identifier
        """
        current_id = self.get_file_identifier(file_path)
        if not current_id:
            self.logger.warning(f"File not found: {file_path}")
            return False
        
        if current_id != expected_id:
            self.logger.warning(f"File identifier mismatch for {file_path}: expected {expected_id}, got {current_id}")
            return False
        
        return True
