"""
Tests for CLI commands.

This module tests all CLI command functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from spatelier.cli.app import app
from spatelier.cli.audio import app as audio_app
from spatelier.cli.cli_analytics import app as analytics_app
from spatelier.cli.cli_utils import app as utils_app
from spatelier.cli.video import app as video_app


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


def test_main_cli_app_help(cli_runner):
    """Test main CLI app help."""
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Personal tool library for video and music file handling" in result.output
    assert "video" in result.output
    assert "audio" in result.output
    assert "utils" in result.output
    assert "analytics" in result.output


def test_main_cli_app_version(cli_runner):
    """Test main CLI app version."""
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Spatelier version" in result.output


@patch("spatelier.core.service_factory.ServiceFactory")
def test_video_download_command(mock_service_factory_class, cli_runner):
    """Test video download command."""
    # Mock service container
    mock_services = Mock()
    mock_use_case = Mock()
    mock_result = Mock()
    mock_result.is_successful.return_value = True
    mock_result.output_path = Path("/test/video.mp4")
    mock_result.message = "Download successful"
    mock_result.metadata = {}
    mock_use_case.execute.return_value = mock_result
    mock_services.download_video_use_case = mock_use_case
    mock_service_factory_class.return_value.__enter__.return_value = mock_services

    result = cli_runner.invoke(
        video_app,
        [
            "download",
            "https://youtube.com/watch?v=test",
            "--output",
            "/test/video.mp4",
            "--quality",
            "best",
        ],
    )

    assert result.exit_code == 0
    assert "Video downloaded successfully!" in result.output
    mock_use_case.execute.assert_called_once()


@patch("spatelier.core.service_factory.ServiceFactory")
def test_video_download_command_failure(mock_service_factory_class, cli_runner):
    """Test video download command failure."""
    # Mock service container with failure
    mock_services = Mock()
    mock_use_case = Mock()
    mock_result = Mock()
    mock_result.is_successful.return_value = False
    mock_result.message = "Download failed"
    mock_use_case.execute.return_value = mock_result
    mock_services.download_video_use_case = mock_use_case
    mock_service_factory_class.return_value.__enter__.return_value = mock_services

    result = cli_runner.invoke(
        video_app, ["download", "https://youtube.com/watch?v=test"]
    )

    # The CLI should show the error message
    assert "Download failed" in result.output
    # Note: Exit code might be 0 due to error handler, but error message should be present


@patch("spatelier.modules.video.converter.VideoConverter")
def test_video_convert_command(mock_converter_class, cli_runner):
    """Test video convert command."""
    # Mock converter
    mock_converter = Mock()
    mock_result = Mock()
    mock_result.success = True
    mock_result.message = "Conversion successful"
    mock_result.output_path = Path("/test/output.mp4")
    mock_result.metadata = {"input_size": 1000000, "output_size": 800000}
    mock_converter.convert.return_value = mock_result
    mock_converter_class.return_value = mock_converter

    result = cli_runner.invoke(
        video_app,
        [
            "convert",
            "/test/input.mp4",
            "/test/output.mp4",
            "--quality",
            "medium",
            "--codec",
            "h264",
        ],
    )

    assert result.exit_code == 0
    assert "Video converted successfully!" in result.output
    mock_converter.convert.assert_called_once()


def test_video_info_command(cli_runner):
    """Test video info command."""
    # Create a temporary test file
    test_file = Path("/tmp/test_video.mp4")
    test_file.touch()

    try:
        result = cli_runner.invoke(video_app, ["info", str(test_file)])

        assert result.exit_code == 0
        assert "Video Information" in result.output
        assert "test_video.mp4" in result.output
    finally:
        if test_file.exists():
            test_file.unlink()


def test_video_info_command_file_not_found(cli_runner):
    """Test video info command with non-existent file."""
    result = cli_runner.invoke(video_app, ["info", "/nonexistent/file.mp4"])

    assert result.exit_code == 1
    assert "File not found" in result.output


@patch("spatelier.modules.audio.converter.AudioConverter.get_audio_info")
def test_audio_info_command(mock_get_audio_info, cli_runner):
    """Test audio info command."""
    # Create a temporary test file
    test_file = Path("/tmp/test_audio.mp3")
    test_file.touch()

    # Mock the audio info response
    mock_get_audio_info.return_value = {
        "format": "mp3",
        "codec": "mp3",
        "duration": 120.5,
        "bitrate": 320000,
        "sample_rate": 44100,
        "channels": 2,
        "channel_layout": "stereo",
    }

    try:
        result = cli_runner.invoke(audio_app, ["info", str(test_file)])

        assert result.exit_code == 0
        assert "Audio Information" in result.output
        assert "test_audio.mp3" in result.output
    finally:
        if test_file.exists():
            test_file.unlink()


def test_utils_hash_command(cli_runner):
    """Test utils hash command."""
    # Create a temporary test file
    test_file = Path("/tmp/test_hash.txt")
    test_file.write_text("Hello, World!")

    try:
        result = cli_runner.invoke(
            utils_app, ["hash", str(test_file), "--algorithm", "sha256"]
        )

        assert result.exit_code == 0
        assert "File Hash" in result.output
        assert "SHA256" in result.output
        assert (
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
            in result.output
        )
    finally:
        if test_file.exists():
            test_file.unlink()


def test_utils_hash_command_file_not_found(cli_runner):
    """Test utils hash command with non-existent file."""
    result = cli_runner.invoke(utils_app, ["hash", "/nonexistent/file.txt"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_utils_info_command(cli_runner):
    """Test utils info command."""
    # Create a temporary test file
    test_file = Path("/tmp/test_info.txt")
    test_file.write_text("Test content")

    try:
        result = cli_runner.invoke(utils_app, ["info", str(test_file)])

        assert result.exit_code == 0
        assert "File Information" in result.output
        assert "test_info.txt" in result.output
        assert "text/plain" in result.output
    finally:
        if test_file.exists():
            test_file.unlink()


def test_utils_find_command(cli_runner):
    """Test utils find command."""
    # Create a temporary test directory with files
    test_dir = Path("/tmp/test_find")
    test_dir.mkdir(exist_ok=True)

    try:
        # Create test files
        (test_dir / "test1.txt").write_text("content1")
        (test_dir / "test2.txt").write_text("content2")
        (test_dir / "test3.log").write_text("log content")

        result = cli_runner.invoke(
            utils_app, ["find", str(test_dir), "--pattern", "*.txt", "--recursive"]
        )

        assert result.exit_code == 0
        assert "Found" in result.output
        assert "test1.txt" in result.output
        assert "test2.txt" in result.output
    finally:
        if test_dir.exists():
            import shutil

            shutil.rmtree(test_dir)


def test_utils_config_show_command(cli_runner):
    """Test utils config show command."""
    result = cli_runner.invoke(utils_app, ["config", "--show"])

    assert result.exit_code == 0
    assert "Current Configuration" in result.output


@patch("spatelier.analytics.reporter.AnalyticsReporter")
def test_analytics_report_command(mock_reporter_class, cli_runner):
    """Test analytics report command."""
    # Mock reporter
    mock_reporter = Mock()
    mock_reporter.generate_media_report.return_value = {
        "total_files": 5,
        "total_size_mb": 100.5,
    }
    mock_reporter.generate_processing_report.return_value = {
        "total_jobs": 3,
        "success_rate": 0.8,
        "avg_processing_time_seconds": 45.2,
    }
    mock_reporter.generate_usage_report.return_value = {"total_events": 10}
    mock_reporter_class.return_value = mock_reporter

    result = cli_runner.invoke(analytics_app, ["report", "--days", "30"])

    assert result.exit_code == 0
    assert "Analytics Summary" in result.output
    mock_reporter.generate_media_report.assert_called_once_with(30)
    mock_reporter.generate_processing_report.assert_called_once_with(30)
    mock_reporter.generate_usage_report.assert_called_once_with(30)


@patch("spatelier.cli.cli_analytics.AnalyticsReporter")
def test_analytics_stats_command(mock_reporter_class, cli_runner):
    """Test analytics stats command."""
    # Mock reporter
    mock_reporter = Mock()
    mock_reporter.generate_media_report.return_value = {
        "total_files": 5,
        "total_size_mb": 100.0,
        "avg_file_size_bytes": 20000000,
        "files_by_type": {"video": 3, "audio": 2},
    }
    mock_reporter.generate_processing_report.return_value = {
        "total_jobs": 3,
        "success_rate": 0.8,
        "avg_processing_time_seconds": 15.5,
    }
    mock_reporter.generate_usage_report.return_value = {
        "total_events": 10,
        "most_active_day": "2023-01-01",
        "trend_analysis": {"trend": "increasing"},
    }
    mock_reporter_class.return_value = mock_reporter

    result = cli_runner.invoke(analytics_app, ["stats", "--days", "30"])

    assert result.exit_code == 0
    assert "Quick Stats" in result.output
    assert "Total Files" in result.output
    assert "Total Jobs" in result.output


@patch("spatelier.cli.cli_analytics.AnalyticsReporter")
def test_analytics_visualize_command(mock_reporter_class, cli_runner):
    """Test analytics visualize command."""
    # Mock reporter
    mock_reporter = Mock()
    mock_reporter.create_visualizations.return_value = [
        Path("/tmp/chart1.png"),
        Path("/tmp/chart2.png"),
    ]
    mock_reporter_class.return_value = mock_reporter

    result = cli_runner.invoke(
        analytics_app, ["visualize", "/tmp/output", "--days", "30"]
    )

    assert result.exit_code == 0
    assert "Visualizations Created" in result.output
    mock_reporter.create_visualizations.assert_called_once_with(Path("/tmp/output"), 30)


@patch("spatelier.cli.cli_analytics.AnalyticsReporter")
def test_analytics_export_command(mock_reporter_class, cli_runner):
    """Test analytics export command."""
    # Mock reporter
    mock_reporter = Mock()
    mock_reporter.export_data.return_value = Path("/tmp/export.json")
    mock_reporter_class.return_value = mock_reporter

    result = cli_runner.invoke(
        analytics_app,
        ["export", "/tmp/export.json", "--format", "json", "--days", "30"],
    )

    assert result.exit_code == 0
    assert "Data exported to" in result.output
    mock_reporter.export_data.assert_called_once_with(Path("/tmp/export.json"), "json")
