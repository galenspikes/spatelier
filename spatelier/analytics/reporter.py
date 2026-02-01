"""
Analytics reporter for generating insights and reports.

This module provides analytics reporting capabilities using the established data models.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func

from spatelier.core.config import Config
from spatelier.core.database_service import DatabaseServiceFactory
from spatelier.core.logger import get_logger
from spatelier.database.models import (
    AnalyticsEvent,
    MediaFile,
    MediaType,
    ProcessingJob,
    ProcessingStatus,
)


class AnalyticsReporter:
    """
    Analytics reporter for generating insights and reports.

    Uses the established data models and repository patterns.
    """

    def __init__(self, config: Config, verbose: bool = False, db_service=None):
        """
        Initialize analytics reporter.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
            db_service: Optional database service for dependency injection
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("AnalyticsReporter", verbose=verbose)

        # Use provided database service or create one
        if db_service:
            self.db_factory = db_service
            self.repos = self.db_factory.initialize()
        else:
            # Fallback for backward compatibility
            from spatelier.core.database_service import DatabaseServiceFactory

            self.db_factory = DatabaseServiceFactory(config, verbose=verbose)
            self.repos = self.db_factory.initialize()
        self.db_manager = self.db_factory.get_db_manager()
        self.session = self.db_manager.get_sqlite_session()

    def generate_media_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate media files report.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with media statistics
        """
        self.logger.info(f"Generating media report for last {days} days")

        # Get media statistics
        media_stats = self.repos.media.get_statistics()

        # Get recent files
        since = datetime.now() - timedelta(days=days)
        recent_files = (
            self.session.query(MediaFile)
            .filter(MediaFile.created_at >= since)
            .order_by(MediaFile.created_at.desc())
            .all()
        )

        # Calculate additional metrics
        total_size = sum(f.file_size for f in recent_files)
        avg_file_size = total_size / len(recent_files) if recent_files else 0

        report = {
            "period_days": days,
            "total_files": len(recent_files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "avg_file_size_bytes": avg_file_size,
            "files_by_type": media_stats.get("files_by_type", {}),
            "size_by_type": media_stats.get("size_by_type", {}),
            "recent_files": [
                {
                    "id": f.id,
                    "name": f.file_name,
                    "path": f.file_path,
                    "type": f.media_type.value,
                    "size": f.file_size,
                    "created_at": f.created_at.isoformat(),
                }
                for f in recent_files[:10]  # Last 10 files
            ],
        }

        return report

    def generate_processing_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate processing jobs report.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with processing statistics
        """
        self.logger.info(f"Generating processing report for last {days} days")

        # Get job statistics
        job_stats = self.repos.jobs.get_job_statistics()

        # Get recent jobs
        since = datetime.now() - timedelta(days=days)
        recent_jobs = (
            self.session.query(ProcessingJob)
            .filter(ProcessingJob.created_at >= since)
            .order_by(ProcessingJob.created_at.desc())
            .all()
        )

        # Calculate success rate
        completed_jobs = [
            j for j in recent_jobs if j.status == ProcessingStatus.COMPLETED
        ]
        failed_jobs = [j for j in recent_jobs if j.status == ProcessingStatus.FAILED]
        success_rate = len(completed_jobs) / len(recent_jobs) if recent_jobs else 0

        # Calculate average processing time
        completed_with_duration = [
            j for j in completed_jobs if j.duration_seconds is not None
        ]
        avg_processing_time = (
            sum(j.duration_seconds for j in completed_with_duration)
            / len(completed_with_duration)
            if completed_with_duration
            else 0
        )

        report = {
            "period_days": days,
            "total_jobs": len(recent_jobs),
            "completed_jobs": len(completed_jobs),
            "failed_jobs": len(failed_jobs),
            "success_rate": success_rate,
            "avg_processing_time_seconds": avg_processing_time,
            "jobs_by_status": job_stats.get("jobs_by_status", {}),
            "jobs_by_type": job_stats.get("jobs_by_type", {}),
            "recent_jobs": [
                {
                    "id": j.id,
                    "type": j.job_type,
                    "status": j.status.value,
                    "input_path": j.input_path,
                    "output_path": j.output_path,
                    "duration_seconds": j.duration_seconds,
                    "created_at": j.created_at.isoformat(),
                    "completed_at": (
                        j.completed_at.isoformat() if j.completed_at else None
                    ),
                }
                for j in recent_jobs[:10]  # Last 10 jobs
            ],
        }

        return report

    def generate_usage_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate usage analytics report.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with usage statistics
        """
        self.logger.info(f"Generating usage report for last {days} days")

        # Get usage statistics
        usage_stats = self.repos.analytics.get_usage_statistics(days)

        # Get events by type
        event_types = ["download", "convert", "extract", "view", "error"]
        events_by_type = {}

        for event_type in event_types:
            events = self.repos.analytics.get_events_by_type(event_type, days)
            events_by_type[event_type] = len(events)

        report = {
            "period_days": days,
            "total_events": sum(events_by_type.values()),
            "events_by_type": events_by_type,
            "daily_activity": usage_stats.get("daily_activity", []),
            "most_active_day": self._find_most_active_day(
                usage_stats.get("daily_activity", [])
            ),
            "trend_analysis": self._analyze_trends(
                usage_stats.get("daily_activity", [])
            ),
        }

        return report

    def create_visualizations(
        self, output_dir: Union[str, Path], days: int = 30
    ) -> List[Path]:
        """
        Create visualization charts and save them.

        Args:
            output_dir: Directory to save visualizations
            days: Number of days to analyze

        Returns:
            List of created visualization files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creating visualizations in {output_dir}")

        # Lazy import heavy dependencies
        import matplotlib.pyplot as plt
        import seaborn as sns

        created_files = []

        # Set up plotting style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

        # 1. Media files by type
        media_report = self.generate_media_report(days)
        if media_report["files_by_type"]:
            fig, ax = plt.subplots(figsize=(10, 6))
            types = list(media_report["files_by_type"].keys())
            counts = list(media_report["files_by_type"].values())

            ax.pie(counts, labels=types, autopct="%1.1f%%", startangle=90)
            ax.set_title(f"Media Files by Type (Last {days} days)")

            chart_path = output_dir / f"media_files_by_type_{days}d.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            created_files.append(chart_path)

        # 2. Processing jobs over time
        since = datetime.now() - timedelta(days=days)
        daily_jobs = (
            self.session.query(
                func.date(ProcessingJob.created_at).label("date"),
                func.count(ProcessingJob.id).label("count"),
            )
            .filter(ProcessingJob.created_at >= since)
            .group_by(func.date(ProcessingJob.created_at))
            .order_by("date")
            .all()
        )

        if daily_jobs:
            dates = [row.date for row in daily_jobs]
            counts = [row.count for row in daily_jobs]

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(dates, counts, marker="o", linewidth=2, markersize=6)
            ax.set_title(f"Processing Jobs Over Time (Last {days} days)")
            ax.set_xlabel("Date")
            ax.set_ylabel("Number of Jobs")
            ax.tick_params(axis="x", rotation=45)

            chart_path = output_dir / f"processing_jobs_timeline_{days}d.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            created_files.append(chart_path)

        # 3. Interactive Plotly dashboard
        self._create_interactive_dashboard(output_dir, days)

        self.logger.info(f"Created {len(created_files)} visualization files")
        return created_files

    def export_data(self, output_path: Union[str, Path], format: str = "json") -> Path:
        """
        Export analytics data to file.

        Args:
            output_path: Path to save exported data
            format: Export format (json, csv, excel)

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        self.logger.info(f"Exporting analytics data to {output_path}")

        # Gather all data
        media_report = self.generate_media_report(30)
        processing_report = self.generate_processing_report(30)
        usage_report = self.generate_usage_report(30)

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "media_report": media_report,
            "processing_report": processing_report,
            "usage_report": usage_report,
        }

        if format.lower() == "json":
            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

        elif format.lower() == "csv":
            # Create CSV files for each report type
            output_dir = output_path.parent
            base_name = output_path.stem

            # Lazy import pandas
            import pandas as pd

            # Media files CSV
            media_df = pd.DataFrame(media_report["recent_files"])
            media_df.to_csv(output_dir / f"{base_name}_media.csv", index=False)

            # Processing jobs CSV
            jobs_df = pd.DataFrame(processing_report["recent_jobs"])
            jobs_df.to_csv(output_dir / f"{base_name}_jobs.csv", index=False)

        elif format.lower() == "excel":
            # Lazy import pandas
            import pandas as pd

            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                # Media files sheet
                media_df = pd.DataFrame(media_report["recent_files"])
                media_df.to_excel(writer, sheet_name="Media Files", index=False)

                # Processing jobs sheet
                jobs_df = pd.DataFrame(processing_report["recent_jobs"])
                jobs_df.to_excel(writer, sheet_name="Processing Jobs", index=False)

                # Summary sheet
                summary_data = {
                    "Metric": [
                        "Total Files",
                        "Total Jobs",
                        "Success Rate",
                        "Avg Processing Time",
                    ],
                    "Value": [
                        media_report["total_files"],
                        processing_report["total_jobs"],
                        f"{processing_report['success_rate']:.2%}",
                        f"{processing_report['avg_processing_time_seconds']:.2f}s",
                    ],
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name="Summary", index=False)

        self.logger.info(f"Exported data to {output_path}")
        return output_path

    def _find_most_active_day(
        self, daily_activity: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find the most active day from daily activity data."""
        if not daily_activity:
            return None

        max_activity = max(daily_activity, key=lambda x: x["count"])
        return max_activity["date"]

    def _analyze_trends(self, daily_activity: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in daily activity."""
        if len(daily_activity) < 2:
            return {"trend": "insufficient_data"}

        # Simple trend analysis
        counts = [day["count"] for day in daily_activity]
        first_half_avg = sum(counts[: len(counts) // 2]) / (len(counts) // 2)
        second_half_avg = sum(counts[len(counts) // 2 :]) / (
            len(counts) - len(counts) // 2
        )

        if second_half_avg > first_half_avg * 1.1:
            trend = "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "first_half_avg": first_half_avg,
            "second_half_avg": second_half_avg,
            "change_percent": ((second_half_avg - first_half_avg) / first_half_avg)
            * 100,
        }

    def _create_interactive_dashboard(self, output_dir: Path, days: int):
        """Create interactive Plotly dashboard."""
        # Get data
        media_report = self.generate_media_report(days)
        processing_report = self.generate_processing_report(days)

        # Lazy import plotly dependencies
        import plotly.graph_objects as go
        from plotly.offline import plot
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Files by Type",
                "Processing Jobs Status",
                "File Sizes Over Time",
                "Job Types Distribution",
            ),
            specs=[
                [{"type": "pie"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "bar"}],
            ],
        )

        # Files by type pie chart
        if media_report["files_by_type"]:
            fig.add_trace(
                go.Pie(
                    labels=list(media_report["files_by_type"].keys()),
                    values=list(media_report["files_by_type"].values()),
                    name="Files by Type",
                ),
                row=1,
                col=1,
            )

        # Processing jobs status pie chart
        if processing_report["jobs_by_status"]:
            fig.add_trace(
                go.Pie(
                    labels=list(processing_report["jobs_by_status"].keys()),
                    values=list(processing_report["jobs_by_status"].values()),
                    name="Job Status",
                ),
                row=1,
                col=2,
            )

        # File sizes over time (simplified)
        if media_report["recent_files"]:
            file_sizes = [f["size"] for f in media_report["recent_files"]]
            file_names = [
                f["name"][:20] + "..." if len(f["name"]) > 20 else f["name"]
                for f in media_report["recent_files"]
            ]

            fig.add_trace(
                go.Bar(x=file_names, y=file_sizes, name="File Sizes"), row=2, col=1
            )

        # Job types distribution
        if processing_report["jobs_by_type"]:
            fig.add_trace(
                go.Bar(
                    x=list(processing_report["jobs_by_type"].keys()),
                    y=list(processing_report["jobs_by_type"].values()),
                    name="Job Types",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(
            title_text=f"Spatelier Analytics Dashboard (Last {days} days)",
            showlegend=True,
            height=800,
        )

        # Save interactive HTML
        dashboard_path = output_dir / f"analytics_dashboard_{days}d.html"
        plot(fig, filename=str(dashboard_path), auto_open=False)

        return dashboard_path
