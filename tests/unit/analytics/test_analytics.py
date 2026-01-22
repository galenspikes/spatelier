"""
Tests for analytics and reporting functionality.

This module tests analytics reporting and data visualization.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from analytics.reporter import AnalyticsReporter
from core.config import Config
from database.models import (
    AnalyticsEvent,
    MediaFile,
    MediaType,
    ProcessingJob,
    ProcessingStatus,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return Config()


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def mock_repositories(mock_session):
    """Create mock repositories."""
    media_repo = Mock()
    job_repo = Mock()
    analytics_repo = Mock()

    return media_repo, job_repo, analytics_repo


@pytest.fixture
def analytics_reporter(config, mock_session, mock_repositories):
    """Create AnalyticsReporter with mocked dependencies."""
    media_repo, job_repo, analytics_repo = mock_repositories

    # Create mock database service
    mock_db_service = Mock()
    mock_repos = Mock()
    mock_repos.media = media_repo
    mock_repos.jobs = job_repo
    mock_repos.analytics = analytics_repo
    mock_db_service.initialize.return_value = mock_repos
    mock_db_service.get_db_manager.return_value = Mock()

    # Create reporter with mocked database service
    reporter = AnalyticsReporter(config, verbose=False, db_service=mock_db_service)
    reporter.session = mock_session
    reporter.media_repo = media_repo
    reporter.job_repo = job_repo
    reporter.analytics_repo = analytics_repo

    return reporter


def test_analytics_reporter_initialization(analytics_reporter):
    """Test AnalyticsReporter initialization."""
    assert analytics_reporter.config is not None
    assert analytics_reporter.verbose == False
    assert analytics_reporter.logger is not None
    assert analytics_reporter.session is not None
    assert analytics_reporter.media_repo is not None
    assert analytics_reporter.job_repo is not None
    assert analytics_reporter.analytics_repo is not None


def test_generate_media_report(analytics_reporter):
    """Test generating media report."""
    # Mock media statistics
    mock_stats = {
        "files_by_type": {"video": 5, "audio": 3},
        "size_by_type": {"video": 1000000, "audio": 500000},
        "recent_files": 8,
    }
    analytics_reporter.repos.media.get_statistics.return_value = mock_stats

    # Mock recent files query
    mock_files = [
        Mock(
            id=1,
            file_name="video1.mp4",
            file_path="/test/video1.mp4",
            media_type=MediaType.VIDEO,
            file_size=200000,
            created_at=datetime.now(),
        ),
        Mock(
            id=2,
            file_name="audio1.mp3",
            file_path="/test/audio1.mp3",
            media_type=MediaType.AUDIO,
            file_size=100000,
            created_at=datetime.now(),
        ),
    ]

    # Ensure file_size is an integer, not a Mock
    for mock_file in mock_files:
        mock_file.file_size = int(mock_file.file_size)

    # Mock the session query for create_visualizations
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = mock_files
    analytics_reporter.session.query.return_value = mock_query

    # Generate report
    report = analytics_reporter.generate_media_report(days=30)

    assert report["period_days"] == 30
    assert report["total_files"] == 2
    assert report["total_size_bytes"] == 300000
    assert report["total_size_mb"] == 300000 / (1024 * 1024)
    assert report["files_by_type"] == {"video": 5, "audio": 3}
    assert len(report["recent_files"]) == 2


def test_generate_processing_report(analytics_reporter):
    """Test generating processing report."""
    # Mock job statistics
    mock_stats = {
        "jobs_by_status": {"completed": 10, "failed": 2},
        "jobs_by_type": {"download": 8, "convert": 4},
        "avg_processing_time": 15.5,
    }
    analytics_reporter.repos.jobs.get_job_statistics.return_value = mock_stats

    # Mock recent jobs query
    mock_jobs = [
        Mock(
            id=1,
            job_type="download",
            status=ProcessingStatus.COMPLETED,
            input_path="https://youtube.com/watch?v=test1",
            output_path="/test/video1.mp4",
            duration_seconds=20.0,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        ),
        Mock(
            id=2,
            job_type="convert",
            status=ProcessingStatus.FAILED,
            input_path="/test/video1.mp4",
            output_path=None,
            duration_seconds=None,
            created_at=datetime.now(),
            completed_at=None,
        ),
    ]

    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = mock_jobs
    analytics_reporter.session.query.return_value = mock_query

    # Generate report
    report = analytics_reporter.generate_processing_report(days=30)

    assert report["period_days"] == 30
    assert report["total_jobs"] == 2
    assert report["completed_jobs"] == 1
    assert report["failed_jobs"] == 1
    assert report["success_rate"] == 0.5
    assert report["avg_processing_time_seconds"] == 20.0
    assert report["jobs_by_status"] == {"completed": 10, "failed": 2}
    assert report["jobs_by_type"] == {"download": 8, "convert": 4}


def test_generate_usage_report(analytics_reporter):
    """Test generating usage report."""
    # Mock usage statistics
    mock_stats = {
        "events_by_type": {"download": 5, "convert": 3, "view": 10},
        "daily_activity": [
            {"date": "2023-01-01", "count": 5},
            {"date": "2023-01-02", "count": 8},
        ],
    }
    analytics_reporter.repos.analytics.get_usage_statistics.return_value = mock_stats

    # Mock the events by type query
    mock_events = {
        "download": [Mock() for _ in range(5)],
        "convert": [Mock() for _ in range(3)],
        "view": [Mock() for _ in range(10)],
    }

    def mock_get_events_by_type(event_type, days):
        return mock_events.get(event_type, [])

    analytics_reporter.repos.analytics.get_events_by_type.side_effect = (
        mock_get_events_by_type
    )

    # Generate report
    report = analytics_reporter.generate_usage_report(days=30)

    assert report["period_days"] == 30
    assert report["total_events"] == 18  # 5 + 3 + 10
    assert report["events_by_type"]["download"] == 5
    assert report["events_by_type"]["convert"] == 3
    assert report["events_by_type"]["view"] == 10
    assert report["daily_activity"] == mock_stats["daily_activity"]


def test_find_most_active_day(analytics_reporter):
    """Test finding most active day."""
    daily_activity = [
        {"date": "2023-01-01", "count": 5},
        {"date": "2023-01-02", "count": 8},
        {"date": "2023-01-03", "count": 3},
    ]

    most_active = analytics_reporter._find_most_active_day(daily_activity)
    assert most_active == "2023-01-02"

    # Test empty list
    most_active = analytics_reporter._find_most_active_day([])
    assert most_active is None


def test_analyze_trends(analytics_reporter):
    """Test trend analysis."""
    # Increasing trend
    daily_activity = [
        {"date": "2023-01-01", "count": 5},
        {"date": "2023-01-02", "count": 6},
        {"date": "2023-01-03", "count": 7},
        {"date": "2023-01-04", "count": 8},
    ]

    trend = analytics_reporter._analyze_trends(daily_activity)
    assert trend["trend"] == "increasing"
    assert trend["change_percent"] > 0

    # Decreasing trend
    daily_activity = [
        {"date": "2023-01-01", "count": 8},
        {"date": "2023-01-02", "count": 7},
        {"date": "2023-01-03", "count": 6},
        {"date": "2023-01-04", "count": 5},
    ]

    trend = analytics_reporter._analyze_trends(daily_activity)
    assert trend["trend"] == "decreasing"
    assert trend["change_percent"] < 0

    # Stable trend
    daily_activity = [
        {"date": "2023-01-01", "count": 5},
        {"date": "2023-01-02", "count": 5},
        {"date": "2023-01-03", "count": 5},
        {"date": "2023-01-04", "count": 5},
    ]

    trend = analytics_reporter._analyze_trends(daily_activity)
    assert trend["trend"] == "stable"


@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
@patch("matplotlib.pyplot.subplots")
def test_create_visualizations(
    mock_subplots, mock_close, mock_savefig, analytics_reporter
):
    """Test creating visualizations."""
    # Mock matplotlib
    mock_fig = Mock()
    mock_ax = Mock()
    mock_subplots.return_value = (mock_fig, mock_ax)

    # Mock media report data
    analytics_reporter.media_repo.get_statistics.return_value = {
        "files_by_type": {"video": 5, "audio": 3}
    }

    # Mock processing report
    analytics_reporter.job_repo.get_job_statistics.return_value = {
        "jobs_by_status": {"completed": 10, "failed": 2},
        "jobs_by_type": {"download": 8, "convert": 4},
    }

    # Mock recent files
    mock_files = [Mock(file_name="test.mp4", file_size=100000)]
    # Ensure file_size is an integer, not a Mock
    for mock_file in mock_files:
        mock_file.file_size = int(mock_file.file_size)

    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = mock_files
    analytics_reporter.session.query.return_value = mock_query

    # Mock daily jobs query
    mock_daily_jobs = [Mock(date=datetime.now().date(), count=5)]
    mock_daily_query = Mock()
    mock_daily_query.filter.return_value = mock_daily_query
    mock_daily_query.group_by.return_value = mock_daily_query
    mock_daily_query.order_by.return_value = mock_daily_query
    mock_daily_query.all.return_value = mock_daily_jobs

    # Set up session.query to return different mocks based on the query
    def mock_query_side_effect(*args, **kwargs):
        if args and hasattr(args[0], "__name__") and args[0].__name__ == "MediaFile":
            return mock_query
        else:
            return mock_daily_query

    analytics_reporter.session.query.side_effect = mock_query_side_effect

    # Create visualizations
    output_dir = Path("/tmp/test_visualizations")
    created_files = analytics_reporter.create_visualizations(output_dir, days=30)

    # Check that files were created
    assert len(created_files) > 0
    mock_savefig.assert_called()
    mock_close.assert_called()


@patch("json.dump")
@patch("builtins.open", create=True)
def test_export_data_json(mock_open, mock_json_dump, analytics_reporter):
    """Test exporting data as JSON."""
    # Mock report generation
    analytics_reporter.generate_media_report = Mock(return_value={"total_files": 5})
    analytics_reporter.generate_processing_report = Mock(return_value={"total_jobs": 3})
    analytics_reporter.generate_usage_report = Mock(return_value={"total_events": 10})

    # Export data
    output_path = Path("/tmp/test_export.json")
    result = analytics_reporter.export_data(output_path, format="json")

    assert result == output_path
    mock_open.assert_called()
    mock_json_dump.assert_called()


@patch("pandas.DataFrame.to_csv")
@patch("builtins.open", create=True)
def test_export_data_csv(mock_open, mock_to_csv, analytics_reporter):
    """Test exporting data as CSV."""
    # Mock report generation
    analytics_reporter.generate_media_report = Mock(
        return_value={"recent_files": [{"id": 1, "name": "test.mp4", "size": 100000}]}
    )
    analytics_reporter.generate_processing_report = Mock(
        return_value={
            "recent_jobs": [{"id": 1, "type": "download", "status": "completed"}]
        }
    )
    analytics_reporter.generate_usage_report = Mock(return_value={"total_events": 10})

    # Export data
    output_path = Path("/tmp/test_export.csv")
    result = analytics_reporter.export_data(output_path, format="csv")

    assert result == output_path
    mock_to_csv.assert_called()


@patch("pandas.ExcelWriter")
def test_export_data_excel(mock_excel_writer, analytics_reporter):
    """Test exporting data as Excel."""
    # Mock report generation
    analytics_reporter.generate_media_report = Mock(
        return_value={
            "recent_files": [{"id": 1, "name": "test.mp4", "size": 100000}],
            "total_files": 5,
        }
    )
    analytics_reporter.generate_processing_report = Mock(
        return_value={
            "recent_jobs": [{"id": 1, "type": "download", "status": "completed"}],
            "total_jobs": 3,
            "success_rate": 0.8,
            "avg_processing_time_seconds": 15.5,
        }
    )
    analytics_reporter.generate_usage_report = Mock(return_value={"total_events": 10})

    # Mock Excel writer
    mock_writer = Mock()
    mock_excel_writer.return_value.__enter__.return_value = mock_writer

    # Mock pandas DataFrame to avoid Excel writing issues
    with patch("pandas.DataFrame") as mock_df:
        mock_df_instance = Mock()
        mock_df_instance.to_excel.return_value = None
        mock_df.return_value = mock_df_instance

        # Export data
        output_path = Path("/tmp/test_export.xlsx")
        result = analytics_reporter.export_data(output_path, format="excel")

        assert result == output_path
        mock_excel_writer.assert_called_with(output_path, engine="openpyxl")
