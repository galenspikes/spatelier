"""
Tests for unified package updater.

Tests all package updater functionality: auto-update, manual updates, version checking, and background updates.
"""

import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from spatelier.core.config import Config
from spatelier.core.package_updater import PackageUpdater


@pytest.fixture
def config():
    """Create test configuration."""
    return Config()


@pytest.fixture
def updater(config):
    """Create test package updater."""
    return PackageUpdater(
        config=config, verbose=True, auto_update=False, check_frequency_hours=24
    )


class TestPackageUpdaterInitialization:
    """Test package updater initialization."""

    def test_updater_init_default(self, config):
        """Test updater initialization with defaults."""
        updater = PackageUpdater(config)
        assert not updater.auto_update
        assert updater.check_frequency_hours == 24
        assert "yt-dlp" in updater.critical_packages

    def test_updater_init_auto_update(self, config):
        """Test updater initialization with auto-update enabled."""
        updater = PackageUpdater(config, auto_update=True)
        assert updater.auto_update is True

    def test_updater_init_custom_frequency(self, config):
        """Test updater initialization with custom frequency."""
        updater = PackageUpdater(config, check_frequency_hours=12)
        assert updater.check_frequency_hours == 12


class TestPackageUpdaterVersionChecking:
    """Test package version checking."""

    def test_get_current_version_yt_dlp(self, updater):
        """Test getting current version of yt-dlp."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="2024.1.1", returncode=0)
            version = updater._get_current_version("yt-dlp")
            assert version == "2024.1.1"

    def test_get_current_version_unknown(self, updater):
        """Test getting current version when package not found."""
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")
        ):
            version = updater._get_current_version("nonexistent")
            assert version == "unknown"

    def test_get_latest_version(self, updater):
        """Test getting latest version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="Available versions: 2024.1.2, 2024.1.1", returncode=0
            )
            version = updater._get_latest_version("yt-dlp")
            assert version == "2024.1.2"

    def test_compare_versions_needs_update(self, updater):
        """Test version comparison when update needed."""
        assert updater._compare_versions("2024.1.1", "2024.1.2") is True

    def test_compare_versions_up_to_date(self, updater):
        """Test version comparison when up to date."""
        assert updater._compare_versions("2024.1.1", "2024.1.1") is False

    def test_compare_versions_unknown(self, updater):
        """Test version comparison with unknown versions."""
        assert updater._compare_versions("unknown", "2024.1.1") is False
        assert updater._compare_versions("2024.1.1", "unknown") is False


class TestPackageUpdaterUpdateChecking:
    """Test package update checking."""

    def test_should_check_updates_first_time(self, updater, tmp_path):
        """Test should check updates when never checked before."""
        # Use temporary path for check file
        updater._last_check_file = tmp_path / "auto_update_last_check.json"

        # File doesn't exist, should check
        assert updater.should_check_updates() is True

    def test_should_check_updates_recent(self, updater, tmp_path):
        """Test should not check updates when checked recently."""
        # Create a recent check file
        updater._last_check_file = tmp_path / "auto_update_last_check.json"
        data = {"last_check": datetime.now().isoformat(), "check_frequency_hours": 24}
        import json

        with open(updater._last_check_file, "w") as f:
            json.dump(data, f)

        assert updater.should_check_updates() is False

    def test_should_check_updates_old(self, updater, tmp_path):
        """Test should check updates when last check is old."""
        # Create an old check file
        updater._last_check_file = tmp_path / "auto_update_last_check.json"
        data = {
            "last_check": (datetime.now() - timedelta(hours=25)).isoformat(),
            "check_frequency_hours": 24,
        }
        import json

        with open(updater._last_check_file, "w") as f:
            json.dump(data, f)

        assert updater.should_check_updates() is True

    def test_check_package_updates(self, updater):
        """Test checking package updates."""
        with patch.object(updater, "_get_current_version", return_value="2024.1.1"):
            with patch.object(updater, "_get_latest_version", return_value="2024.1.2"):
                result = updater.check_package_updates("yt-dlp")

                assert result["package"] == "yt-dlp"
                assert result["current_version"] == "2024.1.1"
                assert result["latest_version"] == "2024.1.2"
                assert result["needs_update"] is True

    def test_check_package_updates_unknown_package(self, updater):
        """Test checking updates for unknown package."""
        result = updater.check_package_updates("nonexistent")
        assert "error" in result


class TestPackageUpdaterManualUpdate:
    """Test manual package updates."""

    def test_update_package_success(self, updater):
        """Test successful package update."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="Success", returncode=0)
            with patch.object(updater, "_get_current_version", return_value="2024.1.2"):
                with patch.object(updater, "_save_update_info"):
                    result = updater.update_package("yt-dlp", silent=False)

                    assert result["success"] is True
                    assert result["package"] == "yt-dlp"
                    assert result["new_version"] == "2024.1.2"

    def test_update_package_failure(self, updater):
        """Test failed package update."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "cmd", "error"),
        ):
            result = updater.update_package("yt-dlp", silent=False)

            assert result["success"] is False
            assert "error" in result

    def test_update_package_timeout(self, updater):
        """Test package update timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            result = updater.update_package("yt-dlp", silent=False)

            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    def test_update_package_silent(self, updater):
        """Test silent package update."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="Success", returncode=0)
            with patch.object(updater, "_get_current_version", return_value="2024.1.2"):
                with patch.object(updater, "_save_update_info"):
                    result = updater.update_package("yt-dlp", silent=True)

                    assert result["success"] is True


class TestPackageUpdaterAutoUpdate:
    """Test automatic background updates."""

    def test_start_background_update_disabled(self, updater):
        """Test starting background update when disabled."""
        updater.auto_update = False
        updater.start_background_update()

        # Should not start thread
        # (hard to test thread creation, but we can verify it doesn't crash)

    def test_start_background_update_enabled(self, config):
        """Test starting background update when enabled."""
        updater = PackageUpdater(config, auto_update=True)

        with patch.object(updater, "run_background_update_check"):
            updater.start_background_update()

            # Give thread time to start
            time.sleep(0.1)

            # Should have started (hard to verify directly, but no exception means success)

    def test_run_background_update_check(self, updater):
        """Test running background update check."""
        with patch.object(updater, "should_check_updates", return_value=True):
            with patch.object(updater, "_check_and_update_package", return_value=False):
                with patch.object(updater, "_save_check_time"):
                    updater.run_background_update_check()

                    # Should complete without error

    def test_run_background_update_check_skips_recent(self, updater):
        """Test background update check skips when checked recently."""
        with patch.object(updater, "should_check_updates", return_value=False):
            with patch.object(updater, "_check_and_update_package") as mock_check:
                updater.run_background_update_check()

                # Should not check packages
                mock_check.assert_not_called()

    def test_check_and_update_package(self, updater):
        """Test checking and updating a package."""
        with patch.object(updater, "_get_current_version", return_value="2024.1.1"):
            with patch.object(updater, "_get_latest_version", return_value="2024.1.2"):
                with patch.object(
                    updater, "update_package", return_value={"success": True}
                ):
                    result = updater._check_and_update_package("yt-dlp")

                    assert result is True

    def test_check_and_update_package_no_update_needed(self, updater):
        """Test checking package when no update needed."""
        with patch.object(updater, "_get_current_version", return_value="2024.1.1"):
            with patch.object(updater, "_get_latest_version", return_value="2024.1.1"):
                result = updater._check_and_update_package("yt-dlp")

                assert result is False


class TestPackageUpdaterSummary:
    """Test package update summary."""

    def test_check_all_critical_packages(self, updater):
        """Test checking all critical packages."""
        with patch.object(updater, "should_check_updates", return_value=True):
            with patch.object(
                updater, "check_package_updates", return_value={"needs_update": False}
            ):
                results = updater.check_all_critical_packages()

                assert len(results) == 1
                assert results[0]["needs_update"] is False

    def test_get_update_summary(self, updater):
        """Test getting update summary."""
        with patch.object(
            updater,
            "check_all_critical_packages",
            return_value=[{"needs_update": True}, {"needs_update": False}],
        ):
            summary = updater.get_update_summary()

            assert summary["total_packages"] == 1
            assert summary["packages_needing_update"] == 1
            assert "results" in summary


class TestPackageUpdaterForceUpdate:
    """Test force update functionality."""

    def test_force_update_check(self, updater):
        """Test forcing immediate update check."""
        original_frequency = updater.check_frequency_hours

        with patch.object(updater, "run_background_update_check"):
            updater.force_update_check()

            # Frequency should be restored
            assert updater.check_frequency_hours == original_frequency
