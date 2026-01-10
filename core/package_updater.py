"""
Unified package updater for automatic dependency updates.

This module provides functionality to check and update critical packages,
supporting both automatic background updates and manual update operations.
"""

import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

from core.logger import get_logger
from core.config import Config


class PackageUpdater:
    """
    Unified package updater supporting both automatic and manual updates.
    
    Consolidates functionality from AutoUpdater and PackageUpdater.
    Supports background automatic updates and manual update checks/operations.
    """
    
    def __init__(
        self,
        config: Config,
        verbose: bool = False,
        auto_update: bool = False,
        check_frequency_hours: int = 24
    ):
        """
        Initialize package updater.
        
        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            auto_update: Enable automatic background updates
            check_frequency_hours: Hours between update checks (default: 24)
        """
        self.config = config
        self.verbose = verbose
        self.auto_update = auto_update
        self.check_frequency_hours = check_frequency_hours
        self.logger = get_logger("PackageUpdater", verbose=verbose)
        
        # Critical packages that should be kept up-to-date
        self.critical_packages = {
            'yt-dlp': {
                'description': 'YouTube downloader',
                'check_command': [sys.executable, '-m', 'yt_dlp', '--version'],
                'update_command': [sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp', '--quiet'],
                'version_file': 'yt-dlp_version.json'
            }
        }
        
        # Lock for thread safety
        self._update_lock = threading.Lock()
        self._last_check_file = Path(config.database.sqlite_path.parent) / 'auto_update_last_check.json'
    
    def should_check_updates(self, package_name: Optional[str] = None) -> bool:
        """
        Check if enough time has passed since last update check.
        
        Args:
            package_name: Optional package name (for per-package checking, kept for compatibility)
            
        Returns:
            True if should check for updates
        """
        if not self._last_check_file.exists():
            return True
        
        try:
            with open(self._last_check_file, 'r') as f:
                data = json.load(f)
            
            last_check = datetime.fromisoformat(data.get('last_check', '1970-01-01'))
            hours_since_check = (datetime.now() - last_check).total_seconds() / 3600
            
            return hours_since_check >= self.check_frequency_hours
            
        except Exception as e:
            self.logger.debug(f"Failed to check last update time: {e}")
            return True
    
    def _save_check_time(self):
        """Save the last check time."""
        try:
            self._last_check_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'last_check': datetime.now().isoformat(),
                'check_frequency_hours': self.check_frequency_hours
            }
            
            with open(self._last_check_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.debug(f"Failed to save check time: {e}")
    
    def _get_current_version(self, package_name: str) -> str:
        """Get current installed version of package."""
        try:
            if package_name == 'yt-dlp':
                result = subprocess.run(
                    [sys.executable, '-m', 'yt_dlp', '--version'],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
                return result.stdout.strip()
            else:
                # Fallback to pip show
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', package_name],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
                return 'unknown'
        except Exception as e:
            self.logger.debug(f"Failed to get current version for {package_name}: {e}")
            return 'unknown'
    
    def _get_latest_version(self, package_name: str) -> str:
        """Get latest available version of package."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'index', 'versions', package_name],
                capture_output=True,
                text=True,
                check=True,
                timeout=15
            )
            # Parse the output to get latest version
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Available versions:' in line:
                    versions = line.split('Available versions:')[1].strip()
                    # Get the first (latest) version)
                    latest = versions.split(',')[0].strip()
                    return latest
            return 'unknown'
        except Exception as e:
            self.logger.debug(f"Failed to get latest version for {package_name}: {e}")
            return 'unknown'
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare version strings to determine if update is needed."""
        if current == 'unknown' or latest == 'unknown':
            return False
        
        # Simple string comparison for now
        # In production, you'd want proper semantic version comparison
        return current != latest
    
    def check_package_updates(self, package_name: str) -> Dict[str, Any]:
        """
        Check if a package has updates available.
        
        Args:
            package_name: Name of package to check
            
        Returns:
            Dictionary with update information
        """
        if package_name not in self.critical_packages:
            return {'error': f'Package {package_name} not in critical packages list'}
        
        package_info = self.critical_packages[package_name]
        
        try:
            # Get current version
            current_version = self._get_current_version(package_name)
            
            # Get latest version
            latest_version = self._get_latest_version(package_name)
            
            # Check if update is needed
            needs_update = self._compare_versions(current_version, latest_version)
            
            return {
                'package': package_name,
                'current_version': current_version,
                'latest_version': latest_version,
                'needs_update': needs_update,
                'last_checked': datetime.now().isoformat(),
                'description': package_info['description']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check updates for {package_name}: {e}")
            return {'error': str(e)}
    
    def update_package(
        self,
        package_name: str,
        auto_confirm: bool = False,
        silent: bool = False
    ) -> Dict[str, Any]:
        """
        Update a package to the latest version.
        
        Args:
            package_name: Name of package to update
            auto_confirm: Whether to update without user confirmation (deprecated, kept for compatibility)
            silent: Whether to run update silently (for background updates)
            
        Returns:
            Dictionary with update result
        """
        if package_name not in self.critical_packages:
            return {'error': f'Package {package_name} not in critical packages list'}
        
        package_info = self.critical_packages[package_name]
        
        try:
            if not silent:
                self.logger.info(f"Updating {package_name}...")
            else:
                self.logger.debug(f"Silently updating {package_name}...")
            
            # Run update command with timeout
            result = subprocess.run(
                package_info['update_command'],
                capture_output=True,
                text=True,
                check=True,
                timeout=60  # 1 minute timeout
            )
            
            # Get new version
            new_version = self._get_current_version(package_name)
            
            # Save update info
            self._save_update_info(package_name, new_version)
            
            if not silent:
                self.logger.info(f"Updated {package_name} to {new_version}")
            else:
                self.logger.info(f"Auto-updated {package_name} to {new_version}")
            
            return {
                'success': True,
                'package': package_name,
                'new_version': new_version,
                'output': result.stdout,
                'updated_at': datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Update timeout for {package_name}"
            self.logger.warning(error_msg)
            return {
                'success': False,
                'package': package_name,
                'error': error_msg
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"Update failed for {package_name}: {e}"
            if not silent:
                self.logger.error(error_msg)
            else:
                self.logger.debug(error_msg)
            return {
                'success': False,
                'package': package_name,
                'error': str(e),
                'output': e.stdout,
                'stderr': e.stderr
            }
        except Exception as e:
            error_msg = f"Unexpected error updating {package_name}: {e}"
            if not silent:
                self.logger.error(error_msg)
            else:
                self.logger.debug(error_msg)
            return {
                'success': False,
                'package': package_name,
                'error': str(e)
            }
    
    def _save_update_info(self, package_name: str, version: str):
        """Save update information to file."""
        try:
            version_file = Path(self.config.database.sqlite_path.parent) / self.critical_packages[package_name]['version_file']
            version_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'package': package_name,
                'version': version,
                'last_checked': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(version_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.debug(f"Failed to save update info: {e}")
    
    def _check_and_update_package(self, package_name: str) -> bool:
        """
        Check if package needs update and update if necessary (for auto-update).
        
        Args:
            package_name: Name of package to check
            
        Returns:
            True if package was updated
        """
        try:
            current_version = self._get_current_version(package_name)
            latest_version = self._get_latest_version(package_name)
            
            if current_version == 'unknown' or latest_version == 'unknown':
                return False
            
            # Simple version comparison
            if current_version != latest_version:
                self.logger.debug(f"Package {package_name} needs update: {current_version} -> {latest_version}")
                result = self.update_package(package_name, silent=True)
                return result.get('success', False)
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking/updating {package_name}: {e}")
            return False
    
    def run_background_update_check(self):
        """
        Run background update check for all critical packages.
        
        This method is designed to be called in a separate thread
        and will not block the main application.
        """
        # Use lock to prevent multiple simultaneous update checks
        if not self._update_lock.acquire(blocking=False):
            self.logger.debug("Update check already in progress, skipping")
            return
        
        try:
            if not self.should_check_updates():
                self.logger.debug("Skipping update check - checked recently")
                return
            
            self.logger.debug("Starting background update check...")
            
            # Check and update each critical package
            updated_packages = []
            for package_name in self.critical_packages:
                if self._check_and_update_package(package_name):
                    updated_packages.append(package_name)
            
            # Save check time
            self._save_check_time()
            
            if updated_packages:
                self.logger.info(f"Auto-updated packages: {', '.join(updated_packages)}")
            else:
                self.logger.debug("All packages up to date")
                
        except Exception as e:
            self.logger.error(f"Error in background update check: {e}")
        finally:
            self._update_lock.release()
    
    def start_background_update(self):
        """
        Start background update check in a separate thread.
        
        This is the main method to call when you want to trigger
        automatic updates without blocking the main thread.
        """
        if not self.auto_update:
            self.logger.debug("Auto-update disabled, skipping background update")
            return
        
        def update_worker():
            try:
                self.run_background_update_check()
            except Exception as e:
                self.logger.error(f"Background update worker error: {e}")
        
        # Start update check in background thread
        update_thread = threading.Thread(
            target=update_worker,
            name="PackageUpdater",
            daemon=True  # Dies when main thread dies
        )
        update_thread.start()
        
        self.logger.debug("Started background update check")
    
    def force_update_check(self):
        """
        Force an immediate update check, bypassing time restrictions.
        
        Useful for testing or when you want to ensure packages are updated.
        """
        self.logger.debug("Forcing immediate update check...")
        
        # Temporarily override the check frequency
        original_frequency = self.check_frequency_hours
        self.check_frequency_hours = 0
        
        try:
            self.run_background_update_check()
        finally:
            self.check_frequency_hours = original_frequency
    
    def check_all_critical_packages(self) -> List[Dict[str, Any]]:
        """
        Check all critical packages for updates.
        
        Returns:
            List of update information for all packages
        """
        results = []
        
        for package_name in self.critical_packages:
            if self.should_check_updates(package_name):
                result = self.check_package_updates(package_name)
                results.append(result)
            else:
                self.logger.debug(f"Skipping {package_name} - checked recently")
        
        return results
    
    def get_update_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all package update statuses.
        
        Returns:
            Dictionary with update summary
        """
        results = self.check_all_critical_packages()
        
        total_packages = len(self.critical_packages)
        packages_needing_update = sum(1 for r in results if r.get('needs_update', False))
        packages_with_errors = sum(1 for r in results if 'error' in r)
        
        return {
            'total_packages': total_packages,
            'packages_needing_update': packages_needing_update,
            'packages_with_errors': packages_with_errors,
            'last_check': datetime.now().isoformat(),
            'results': results
        }
