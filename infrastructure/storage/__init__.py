"""
Storage abstractions for Spatelier.

Provides storage adapters for different storage backends (local, NAS, cloud).
"""

from .storage_adapter import StorageAdapter, LocalStorageAdapter, NASStorageAdapter

__all__ = ["StorageAdapter", "LocalStorageAdapter", "NASStorageAdapter"]
