"""
Analytics dashboard for Spatelier.

This module provides a web-based analytics dashboard for viewing
processing statistics, usage metrics, and system health.
"""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from spatelier.core.config import Config
from spatelier.core.logger import get_logger


@dataclass
class ProcessingStats:
    """Processing statistics data class."""

    total_videos: int = 0
    total_audio: int = 0
    total_playlists: int = 0
    total_duration: float = 0.0
    total_size: int = 0
    success_rate: float = 0.0
    avg_processing_time: float = 0.0
    last_24h_videos: int = 0
    last_24h_audio: int = 0
    last_24h_playlists: int = 0


@dataclass
class SystemHealth:
    """System health metrics."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_jobs: int = 0
    queue_size: int = 0
    last_activity: Optional[datetime] = None
    uptime: float = 0.0


class AnalyticsDashboard:
    """Analytics dashboard for Spatelier."""

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize analytics dashboard.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger("AnalyticsDashboard", verbose=verbose)
        self.console = Console()

    def get_processing_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        try:
            # This would typically query the database
            # For now, return mock data
            return ProcessingStats(
                total_videos=1250,
                total_audio=890,
                total_playlists=45,
                total_duration=125000.0,  # seconds
                total_size=2.5 * 1024**3,  # 2.5 GB
                success_rate=94.5,
                avg_processing_time=45.2,
                last_24h_videos=23,
                last_24h_audio=15,
                last_24h_playlists=3,
            )
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return ProcessingStats()

    def get_system_health(self) -> SystemHealth:
        """Get current system health metrics."""
        try:
            import psutil

            return SystemHealth(
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage("/").percent,
                active_jobs=5,
                queue_size=12,
                last_activity=datetime.now() - timedelta(minutes=5),
                uptime=time.time() - psutil.boot_time(),
            )
        except ImportError:
            self.logger.warning("psutil not available, using mock health data")
            return SystemHealth(
                cpu_usage=25.5,
                memory_usage=68.2,
                disk_usage=45.8,
                active_jobs=3,
                queue_size=8,
                last_activity=datetime.now() - timedelta(minutes=2),
                uptime=86400.0,  # 1 day
            )
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return SystemHealth()

    def create_stats_table(self, stats: ProcessingStats) -> Table:
        """Create processing statistics table."""
        table = Table(
            title="📊 Processing Statistics",
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Last 24h", style="yellow")

        # Format file sizes
        def format_size(size_bytes):
            if size_bytes < 1024**2:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024**3:
                return f"{size_bytes / (1024**2):.1f} MB"
            else:
                return f"{size_bytes / (1024**3):.1f} GB"

        def format_duration(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

        table.add_row(
            "Videos Processed", str(stats.total_videos), str(stats.last_24h_videos)
        )
        table.add_row("Audio Files", str(stats.total_audio), str(stats.last_24h_audio))
        table.add_row(
            "Playlists", str(stats.total_playlists), str(stats.last_24h_playlists)
        )
        table.add_row("Total Duration", format_duration(stats.total_duration), "")
        table.add_row("Total Size", format_size(stats.total_size), "")
        table.add_row("Success Rate", f"{stats.success_rate:.1f}%", "")
        table.add_row("Avg Processing Time", f"{stats.avg_processing_time:.1f}s", "")

        return table

    def create_health_table(self, health: SystemHealth) -> Table:
        """Create system health table."""
        table = Table(
            title="🏥 System Health", show_header=True, header_style="bold red"
        )

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")

        def get_status_color(value, thresholds):
            if value < thresholds[0]:
                return "green"
            elif value < thresholds[1]:
                return "yellow"
            else:
                return "red"

        def get_status_text(value, thresholds, labels):
            if value < thresholds[0]:
                return labels[0]
            elif value < thresholds[1]:
                return labels[1]
            else:
                return labels[2]

        # CPU usage
        cpu_status = get_status_text(
            health.cpu_usage, [50, 80], ["Good", "Warning", "Critical"]
        )
        table.add_row("CPU Usage", f"{health.cpu_usage:.1f}%", cpu_status)

        # Memory usage
        memory_status = get_status_text(
            health.memory_usage, [70, 90], ["Good", "Warning", "Critical"]
        )
        table.add_row("Memory Usage", f"{health.memory_usage:.1f}%", memory_status)

        # Disk usage
        disk_status = get_status_text(
            health.disk_usage, [80, 95], ["Good", "Warning", "Critical"]
        )
        table.add_row("Disk Usage", f"{health.disk_usage:.1f}%", disk_status)

        # Active jobs
        table.add_row(
            "Active Jobs",
            str(health.active_jobs),
            "Running" if health.active_jobs > 0 else "Idle",
        )

        # Queue size
        queue_status = get_status_text(
            health.queue_size, [5, 20], ["Good", "Busy", "Overloaded"]
        )
        table.add_row("Queue Size", str(health.queue_size), queue_status)

        # Last activity
        if health.last_activity:
            time_ago = datetime.now() - health.last_activity
            minutes_ago = int(time_ago.total_seconds() / 60)
            table.add_row(
                "Last Activity",
                f"{minutes_ago}m ago",
                "Active" if minutes_ago < 10 else "Idle",
            )

        # Uptime
        uptime_hours = health.uptime / 3600
        table.add_row(
            "Uptime",
            f"{uptime_hours:.1f}h",
            "Stable" if uptime_hours > 24 else "Recent",
        )

        return table

    def create_dashboard_layout(self) -> Layout:
        """Create the main dashboard layout."""
        layout = Layout()

        # Split into main and sidebar
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Split main into stats and health
        layout["main"].split_row(Layout(name="stats"), Layout(name="health"))

        return layout

    def render_dashboard(self):
        """Render the complete analytics dashboard."""
        stats = self.get_processing_stats()
        health = self.get_system_health()

        layout = self.create_dashboard_layout()

        # Header
        header_text = Text("🚀 Spatelier Analytics Dashboard", style="bold blue")
        layout["header"].update(Panel(header_text, border_style="blue"))

        # Stats section
        stats_table = self.create_stats_table(stats)
        layout["stats"].update(
            Panel(stats_table, title="Processing Overview", border_style="green")
        )

        # Health section
        health_table = self.create_health_table(health)
        layout["health"].update(
            Panel(health_table, title="System Status", border_style="red")
        )

        # Footer
        footer_text = Text(
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim"
        )
        layout["footer"].update(Panel(footer_text, border_style="dim"))

        return layout

    def show_dashboard(self, refresh_interval: int = 5):
        """
        Show live updating dashboard.

        Args:
            refresh_interval: Refresh interval in seconds
        """
        try:
            with Live(
                self.render_dashboard(),
                refresh_per_second=1 / refresh_interval,
                screen=True,
            ) as live:
                while True:
                    time.sleep(refresh_interval)
                    live.update(self.render_dashboard())

        except KeyboardInterrupt:
            self.logger.info("Dashboard closed by user")
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")

    def export_stats(self, output_path: Path) -> bool:
        """
        Export statistics to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            stats = self.get_processing_stats()
            health = self.get_system_health()

            data = {
                "timestamp": datetime.now().isoformat(),
                "processing_stats": asdict(stats),
                "system_health": asdict(health),
            }

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Statistics exported to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export stats: {e}")
            return False


def show_analytics_dashboard(
    config: Config, verbose: bool = False, refresh_interval: int = 5
):
    """
    Show the analytics dashboard.

    Args:
        config: Configuration instance
        verbose: Enable verbose logging
        refresh_interval: Refresh interval in seconds
    """
    dashboard = AnalyticsDashboard(config, verbose)
    dashboard.show_dashboard(refresh_interval)


def export_analytics_data(
    config: Config, output_path: Path, verbose: bool = False
) -> bool:
    """
    Export analytics data to file.

    Args:
        config: Configuration instance
        output_path: Path to output file
        verbose: Enable verbose logging

    Returns:
        True if successful, False otherwise
    """
    dashboard = AnalyticsDashboard(config, verbose)
    return dashboard.export_stats(output_path)
