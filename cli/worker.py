"""
Job worker CLI commands.

This module provides CLI commands for managing the background job worker daemon,
including starting, stopping, and monitoring the worker process.
"""

import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import Config
from core.decorators import handle_errors, time_operation
from core.logger import get_logger
from core.worker import Worker, WorkerMode

# Create the worker CLI app
app = typer.Typer(
    name="worker",
    help="Background job worker daemon management",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
@handle_errors(context="start worker daemon", verbose=True)
@time_operation(verbose=True)
def start(
    max_retries: int = typer.Option(
        10, "--max-retries", "-r", help="Maximum retries for failed jobs"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Start the background job worker daemon.

    The worker will run in the background and automatically process jobs from the queue.
    Only one worker daemon can run at a time.
    """
    logger = get_logger("worker-start", verbose=verbose)
    config = Config()

    # Initialize worker in daemon mode
    worker = Worker(
        config=config, mode=WorkerMode.DAEMON, verbose=verbose, max_retries=max_retries
    )

    # Check if already running
    if worker.is_running():
        console.print(
            Panel(
                "⚠️  Worker daemon is already running\n"
                "Use 'spt worker status' to check status\n"
                "Use 'spt worker stop' to stop the current daemon",
                title="Already Running",
                border_style="yellow",
            )
        )
        return

    # Start daemon
    try:
        worker.start()
        console.print(
            Panel(
                "🚀 Worker daemon started successfully\n"
                "The worker is now running in the background\n"
                "Use 'spt worker status' to check status\n"
                "Use 'spt worker stop' to stop the daemon",
                title="Daemon Started",
                border_style="green",
            )
        )
    except Exception as e:
        logger.error(f"Failed to start worker daemon: {e}")
        console.print(
            Panel(
                f"❌ Failed to start worker daemon: {e}\n"
                "Check logs for more information",
                title="Start Failed",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
@handle_errors(context="stop worker daemon", verbose=True)
@time_operation(verbose=True)
def stop(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Stop the background job worker daemon.

    This will gracefully stop the worker daemon if it's running.
    """
    logger = get_logger("worker-stop", verbose=verbose)
    config = Config()

    # Initialize worker in daemon mode
    worker = Worker(config=config, mode=WorkerMode.DAEMON, verbose=verbose)

    # Check if running
    if not worker.is_running():
        console.print(
            Panel(
                "ℹ️  Worker daemon is not running",
                title="Not Running",
                border_style="blue",
            )
        )
        return

    # Stop daemon
    if worker.stop_daemon():
        console.print(
            Panel(
                "🛑 Worker daemon stopped successfully",
                title="Daemon Stopped",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                "❌ Failed to stop worker daemon\n"
                "You may need to force kill the process",
                title="Stop Failed",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
@handle_errors(context="check worker status", verbose=True)
@time_operation(verbose=True)
def status(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Check the status of the background job worker daemon.

    Shows whether the daemon is running, its PID, uptime, and resource usage.
    """
    logger = get_logger("worker-status", verbose=verbose)
    config = Config()

    # Initialize worker in daemon mode
    worker = Worker(config=config, mode=WorkerMode.DAEMON, verbose=verbose)

    # Get status
    is_running = worker.is_running()
    stats = worker.get_stats() if is_running else {}

    # Create status table
    table = Table(title="Worker Daemon Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    if is_running:
        # Try to get PID and process info
        try:
            import psutil

            if worker.pid_file and worker.pid_file.exists():
                pid = int(worker.pid_file.read_text().strip())
                process = psutil.Process(pid)

                table.add_row("Status", "🟢 Running")
                table.add_row("PID", str(pid))
                uptime_hours = (time.time() - process.create_time()) / 3600
                table.add_row("Uptime", f"{uptime_hours:.1f} hours")
                memory_mb = process.memory_info().rss / 1024 / 1024
                table.add_row("Memory", f"{memory_mb:.1f} MB")
                table.add_row("CPU", f"{process.cpu_percent():.1f}%")
            else:
                table.add_row("Status", "🟢 Running")
                table.add_row("PID", "N/A")
        except Exception as e:
            logger.debug(f"Failed to get process info: {e}")
            table.add_row("Status", "🟢 Running")
            table.add_row("PID", "N/A")

        # Add worker stats
        if stats:
            worker_stats = stats.get("worker_stats", {})
            table.add_row("Jobs Processed", str(worker_stats.get("jobs_processed", 0)))
            table.add_row("Jobs Failed", str(worker_stats.get("jobs_failed", 0)))
            table.add_row(
                "Stuck Jobs Detected", str(stats.get("stuck_jobs_detected", 0))
            )
    else:
        table.add_row("Status", "🔴 Not Running")
        table.add_row("PID", "N/A")
        table.add_row("Uptime", "N/A")
        table.add_row("Memory", "N/A")
        table.add_row("CPU", "N/A")

    console.print(table)


@app.command()
@handle_errors(context="restart worker daemon", verbose=True)
@time_operation(verbose=True)
def restart(
    max_retries: int = typer.Option(
        10, "--max-retries", "-r", help="Maximum retries for failed jobs"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Restart the background job worker daemon.

    This will stop the current daemon (if running) and start a new one.
    """
    logger = get_logger("worker-restart", verbose=verbose)
    config = Config()

    # Initialize worker in daemon mode
    worker = Worker(
        config=config, mode=WorkerMode.DAEMON, verbose=verbose, max_retries=max_retries
    )

    # Stop if running
    if worker.is_running():
        console.print("Stopping current daemon...")
        worker.stop_daemon()
        time.sleep(2)  # Give it time to stop

    # Start new daemon
    console.print("Starting new daemon...")
    try:
        worker.start()
        console.print(
            Panel(
                "🔄 Worker daemon restarted successfully",
                title="Daemon Restarted",
                border_style="green",
            )
        )
    except Exception as e:
        logger.error(f"Failed to restart worker daemon: {e}")
        console.print(
            Panel(
                f"❌ Failed to restart worker daemon: {e}",
                title="Restart Failed",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
@handle_errors(context="list jobs", verbose=True)
@time_operation(verbose=True)
def list_jobs(
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, table, summary"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    List all jobs in the queue.

    Shows pending, running, completed, and failed jobs.
    """
    logger = get_logger("worker-list-jobs", verbose=verbose)

    try:
        from core.config import Config
        from core.job_queue import JobQueue

        # Initialize job queue
        config = Config()
        job_queue = JobQueue(config, verbose=verbose)

        # Get all jobs
        jobs = job_queue.get_all_jobs()

        if not jobs:
            if format == "json":
                console.print('{"jobs": [], "total": 0, "summary": {}}')
            else:
                console.print(
                    Panel(
                        "📭 No jobs found in queue",
                        title="Empty Queue",
                        border_style="blue",
                    )
                )
            return

        # Count jobs by status
        status_counts = {}
        for job in jobs:
            status_value = (
                job.status.value if hasattr(job.status, "value") else str(job.status)
            )
            status_counts[status_value] = status_counts.get(status_value, 0) + 1

        # Handle JSON format
        if format == "json":
            import json

            # Prepare job data for JSON
            job_data = []
            for job in jobs:
                job_info = {
                    "id": job.id,
                    "type": job.job_type.value,
                    "status": (
                        job.status.value
                        if hasattr(job.status, "value")
                        else str(job.status)
                    ),
                    "path": job.job_path,
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else None
                    ),
                    "error_message": job.error_message,
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                }
                job_data.append(job_info)

            # Create JSON response
            response = {"total": len(jobs), "summary": status_counts, "jobs": job_data}

            console.print(json.dumps(response, indent=2))
            return

        # Show summary for table/summary formats
        summary_parts = []
        for status, count in status_counts.items():
            emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
            }.get(status.lower(), "❓")
            summary_parts.append(f"{emoji} {count} {status.title()}")

        if format == "summary":
            console.print(
                Panel(
                    f"📊 Total Jobs: {len(jobs)} | " + " | ".join(summary_parts),
                    title="Job Queue Summary",
                    border_style="green",
                )
            )
            return

        # Show summary for table format
        summary_text = f"📊 Total Jobs: {len(jobs)} | {' | '.join(summary_parts)}"
        console.print(
            Panel(
                summary_text,
                title="Job Queue Summary",
                border_style="green",
            )
        )

        # Create a very simple table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("ID", style="cyan", width=3)
        table.add_column("Status", style="bold", width=8)
        table.add_column("Type", style="green", width=12)
        table.add_column("Path", style="blue", width=20)
        table.add_column("Time", style="magenta", width=6)
        table.add_column("Error", style="red", width=15)

        for job in jobs:
            # Simple status with emoji
            status_value = (
                job.status.value if hasattr(job.status, "value") else str(job.status)
            )
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
            }.get(status_value.lower(), "❓")

            # Simple job type
            job_type = "Video" if "video" in job.job_type.value else "Playlist"

            # Simple path - just show the last part
            path = job.job_path.split("/")[-1] if "/" in job.job_path else job.job_path
            if len(path) > 15:
                path = "..." + path[-12:]

            # Simple time
            time_str = job.created_at.strftime("%H:%M") if job.created_at else "N/A"

            # Simple error - only show if there is one
            error = (
                job.error_message[:12] + "..."
                if job.error_message and len(job.error_message) > 15
                else (job.error_message or "")
            )

            table.add_row(
                str(job.id),
                f"{status_emoji} {status_value.upper()[:4]}",
                job_type,
                path,
                time_str,
                error,
            )

        console.print(table)

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        console.print(
            Panel(f"❌ Failed to list jobs: {e}", title="Error", border_style="red")
        )
        raise typer.Exit(1)


@app.command()
@handle_errors(context="check stuck jobs", verbose=True)
@time_operation(verbose=True)
def check_stuck(
    timeout: int = typer.Option(
        1800,
        "--timeout",
        "-t",
        help="Timeout in seconds for stuck jobs (default: 1800 = 30 minutes)",
    ),
    reset: bool = typer.Option(
        False, "--reset", "-r", help="Reset stuck jobs to pending status"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Check for stuck jobs in the queue.

    Jobs stuck in 'running' state for longer than the timeout are considered stuck.
    Use --reset to automatically reset stuck jobs to pending status.
    """
    logger = get_logger("worker-check-stuck", verbose=verbose)

    try:
        from datetime import datetime, timedelta

        from core.job_queue import JobQueue, JobStatus

        # Initialize job queue
        config = Config()
        job_queue = JobQueue(config, verbose=verbose)

        # Get running jobs
        running_jobs = job_queue.get_jobs_by_status(JobStatus.RUNNING, limit=50)

        if not running_jobs:
            console.print(
                Panel(
                    "✅ No running jobs found",
                    title="No Stuck Jobs",
                    border_style="green",
                )
            )
            return

        # Check for stuck jobs
        stuck_jobs = []
        cutoff_time = datetime.now() - timedelta(seconds=timeout)

        for job in running_jobs:
            # Check if job has been running too long
            if job.started_at and job.started_at < cutoff_time:
                stuck_jobs.append(job)
            # Also check jobs without started_at that are old
            elif job.created_at and job.created_at < cutoff_time:
                stuck_jobs.append(job)

        if not stuck_jobs:
            console.print(
                Panel(
                    f"✅ No stuck jobs found (timeout: {timeout}s)",
                    title="No Stuck Jobs",
                    border_style="green",
                )
            )
            return

        # Show stuck jobs
        console.print(
            Panel(
                f"⚠️  Found {len(stuck_jobs)} stuck jobs (timeout: {timeout}s)",
                title="Stuck Jobs Detected",
                border_style="yellow",
            )
        )

        # Create table for stuck jobs
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=3)
        table.add_column("Type", style="green", width=12)
        table.add_column("Path", style="blue", width=20)
        table.add_column("Running Since", style="magenta", width=12)
        table.add_column("Duration", style="red", width=10)

        for job in stuck_jobs:
            # Calculate duration
            start_time = job.started_at or job.created_at
            if start_time:
                duration = datetime.now() - start_time
                duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
                running_since = start_time.strftime("%H:%M:%S")
            else:
                duration_str = "Unknown"
                running_since = "Unknown"

            # Truncate path
            path = job.job_path.split("/")[-1] if "/" in job.job_path else job.job_path
            if len(path) > 15:
                path = "..." + path[-12:]

            # Check if job has output files (intelligent assessment)
            has_output = False
            try:
                from pathlib import Path

                output_path = Path(job.job_path)
                if output_path.exists():
                    video_extensions = ["*.mp4", "*.mkv", "*.avi"]
                    video_files = [
                        file
                        for ext in video_extensions
                        for file in output_path.rglob(ext)
                    ]
                    has_output = bool(video_files)
            except Exception:
                # Silently ignore errors when checking for output files
                # This is a best-effort check and shouldn't fail the stuck job check
                pass

            # Add output status to duration
            if has_output:
                duration_str += " ✅"
            else:
                duration_str += " ❌"

            table.add_row(
                str(job.id),
                job.job_type.value.replace("download_", "").title(),
                path,
                running_since,
                duration_str,
            )

        console.print(table)

        # Reset stuck jobs if requested
        if reset:
            console.print("\n🔄 Resetting stuck jobs to pending...")
            reset_count = 0
            for job in stuck_jobs:
                try:
                    job_queue.update_job_status(
                        job.id,
                        JobStatus.PENDING,
                        error_message=f"Job was stuck in running state for {timeout}s, reset to pending",
                    )
                    reset_count += 1
                except Exception as e:
                    logger.error(f"Failed to reset job {job.id}: {e}")

            console.print(
                Panel(
                    f"✅ Reset {reset_count} stuck jobs to pending status",
                    title="Jobs Reset",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    "💡 Use --reset to automatically reset stuck jobs to pending status",
                    title="Reset Available",
                    border_style="blue",
                )
            )

    except Exception as e:
        logger.error(f"Failed to check stuck jobs: {e}")
        console.print(
            Panel(
                f"❌ Failed to check stuck jobs: {e}", title="Error", border_style="red"
            )
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
