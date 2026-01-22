"""
Analytics CLI commands.

This module provides command-line interfaces for analytics and reporting operations.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from sqlalchemy import func

from analytics.reporter import AnalyticsReporter
from core.config import Config
from core.decorators import handle_errors, time_operation
from core.logger import get_logger
from core.service_factory import ServiceFactory

# Create the analytics CLI app
app = typer.Typer(
    name="analytics",
    help="Analytics and reporting commands",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
@handle_errors(context="analytics report", verbose=True)
@time_operation(verbose=True)
def report(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format (json, csv, excel)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Generate comprehensive analytics report.
    """
    config = Config()
    logger = get_logger("analytics-report", verbose=verbose)

    with ServiceFactory(config, verbose=verbose) as services:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating analytics report...", total=None)

                # Create analytics reporter with database service
                from analytics.reporter import AnalyticsReporter

                reporter = AnalyticsReporter(
                    config, verbose=verbose, db_service=services.database
                )

            # Generate reports
            progress.update(task, description="Generating media report...")
            media_report = reporter.generate_media_report(days)

            progress.update(task, description="Generating processing report...")
            processing_report = reporter.generate_processing_report(days)

            progress.update(task, description="Generating usage report...")
            usage_report = reporter.generate_usage_report(days)

            # Combine reports
            combined_report = {
                "period_days": days,
                "generated_at": reporter.session.query(func.now()).scalar(),
                "media_report": media_report,
                "processing_report": processing_report,
                "usage_report": usage_report,
            }

            # Display summary
            table = Table(title=f"Analytics Summary (Last {days} days)")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Total Files", str(media_report["total_files"]))
            table.add_row("Total Size (MB)", f"{media_report['total_size_mb']:.2f}")
            table.add_row("Total Jobs", str(processing_report["total_jobs"]))
            table.add_row("Success Rate", f"{processing_report['success_rate']:.2%}")
            table.add_row(
                "Avg Processing Time",
                f"{processing_report['avg_processing_time_seconds']:.2f}s",
            )
            table.add_row("Total Events", str(usage_report["total_events"]))

            console.print(table)

            # Save to file if requested
            if output:
                progress.update(task, description="Saving report...")
                reporter.export_data(output, format)
                console.print(
                    Panel(
                        f"[green]✓[/green] Report saved to: {output}",
                        title="Report Saved",
                        border_style="green",
                    )
                )

        except Exception as e:
            logger.error(f"Analytics report failed: {e}")
            console.print(
                Panel(
                    f"[red]✗[/red] Analytics report failed: {str(e)}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)


@app.command()
def visualize(
    output_dir: Path = typer.Argument(..., help="Output directory for visualizations"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Create visualization charts and dashboards.
    """
    config = Config()
    logger = get_logger("analytics-visualize", verbose=verbose)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating visualizations...", total=None)

            reporter = AnalyticsReporter(config, verbose=verbose)

            progress.update(task, description="Generating charts...")
            created_files = reporter.create_visualizations(output_dir, days)

            console.print(
                Panel(
                    f"[green]✓[/green] Created {len(created_files)} visualization files\n"
                    f"Output directory: {output_dir}",
                    title="Visualizations Created",
                    border_style="green",
                )
            )

            # List created files
            if created_files:
                table = Table(title="Created Files")
                table.add_column("File", style="cyan")
                table.add_column("Type", style="magenta")

                for file_path in created_files:
                    file_type = "Chart" if file_path.suffix == ".png" else "Dashboard"
                    table.add_row(str(file_path.name), file_type)

                console.print(table)

    except Exception as e:
        logger.error(f"Visualization creation failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] Visualization creation failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def stats(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Display quick statistics overview.
    """
    config = Config()
    logger = get_logger("analytics-stats", verbose=verbose)

    try:
        reporter = AnalyticsReporter(config, verbose=verbose)

        # Get quick stats
        media_report = reporter.generate_media_report(days)
        processing_report = reporter.generate_processing_report(days)
        usage_report = reporter.generate_usage_report(days)

        # Create stats table
        table = Table(title=f"Quick Stats (Last {days} days)")
        table.add_column("Category", style="cyan")
        table.add_column("Metric", style="yellow")
        table.add_column("Value", style="magenta")

        # Media stats
        table.add_row("Media", "Total Files", str(media_report["total_files"]))
        table.add_row(
            "Media", "Total Size (MB)", f"{media_report['total_size_mb']:.2f}"
        )
        table.add_row(
            "Media",
            "Avg File Size (MB)",
            f"{media_report['avg_file_size_bytes'] / (1024 * 1024):.2f}",
        )

        # Processing stats
        table.add_row("Processing", "Total Jobs", str(processing_report["total_jobs"]))
        table.add_row(
            "Processing", "Success Rate", f"{processing_report['success_rate']:.2%}"
        )
        table.add_row(
            "Processing",
            "Avg Time (s)",
            f"{processing_report['avg_processing_time_seconds']:.2f}",
        )

        # Usage stats
        table.add_row("Usage", "Total Events", str(usage_report["total_events"]))
        table.add_row(
            "Usage", "Most Active Day", usage_report.get("most_active_day", "N/A")
        )
        table.add_row(
            "Usage", "Trend", usage_report.get("trend_analysis", {}).get("trend", "N/A")
        )

        console.print(table)

        # Show files by type
        if media_report["files_by_type"]:
            type_table = Table(title="Files by Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="magenta")

            for file_type, count in media_report["files_by_type"].items():
                type_table.add_row(file_type, str(count))

            console.print(type_table)

    except Exception as e:
        logger.error(f"Stats display failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] Stats display failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def export(
    output_path: Path = typer.Argument(..., help="Output file path"),
    format: str = typer.Option(
        "json", "--format", "-f", help="Export format (json, csv, excel)"
    ),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to export"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Export analytics data to file.
    """
    config = Config()
    logger = get_logger("analytics-export", verbose=verbose)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Exporting analytics data...", total=None)

            reporter = AnalyticsReporter(config, verbose=verbose)

            progress.update(task, description="Generating reports...")
            exported_file = reporter.export_data(output_path, format)

            console.print(
                Panel(
                    f"[green]✓[/green] Data exported to: {exported_file}",
                    title="Export Complete",
                    border_style="green",
                )
            )

    except Exception as e:
        logger.error(f"Data export failed: {e}")
        console.print(
            Panel(
                f"[red]✗[/red] Data export failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
