"""
Package update management commands.

Provides CLI interface for checking and updating critical packages.
"""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import Config
from core.package_updater import PackageUpdater
from core.progress import track_progress

console = Console()
app = typer.Typer(name="update", help="Package update management")


@app.command()
def check(
    package: Optional[str] = typer.Option(
        None, "--package", "-p", help="Specific package to check"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🔍 Check for package updates.

    Checks if critical packages like yt-dlp have updates available.
    """
    config = Config()
    updater = PackageUpdater(config, verbose=verbose)

    if package:
        # Check specific package
        result = updater.check_package_updates(package)

        if "error" in result:
            console.print(
                Panel(
                    f"[red]✗[/red] Error checking {package}: {result['error']}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        # Display result
        status = "🔄 Update Available" if result["needs_update"] else "✅ Up to Date"
        color = "yellow" if result["needs_update"] else "green"

        console.print(
            Panel(
                f"{status}\n"
                f"Package: {result['package']}\n"
                f"Description: {result['description']}\n"
                f"Current: {result['current_version']}\n"
                f"Latest: {result['latest_version']}\n"
                f"Last Checked: {result['last_checked']}",
                title=f"Package Status: {package}",
                border_style=color,
            )
        )
    else:
        # Check all packages
        with track_progress("Checking for updates...", verbose=verbose) as progress:
            summary = updater.get_update_summary()
            progress.update(1, "Update check completed")

        # Create summary table
        table = Table(title="Package Update Summary")
        table.add_column("Package", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Current", style="green")
        table.add_column("Latest", style="blue")
        table.add_column("Description", style="white")

        for result in summary["results"]:
            if "error" in result:
                table.add_row(
                    result["package"], "[red]Error[/red]", "N/A", "N/A", result["error"]
                )
            else:
                status = (
                    "🔄 Update Available" if result["needs_update"] else "✅ Up to Date"
                )
                table.add_row(
                    result["package"],
                    status,
                    result["current_version"],
                    result["latest_version"],
                    result["description"],
                )

        console.print(table)

        # Summary stats
        console.print(
            Panel(
                f"📊 Summary:\n"
                f"Total Packages: {summary['total_packages']}\n"
                f"Need Updates: {summary['packages_needing_update']}\n"
                f"Errors: {summary['packages_with_errors']}\n"
                f"Last Check: {summary['last_check']}",
                title="Update Summary",
                border_style="blue",
            )
        )


@app.command()
def update(
    package: Optional[str] = typer.Option(
        None, "--package", "-p", help="Specific package to update"
    ),
    auto_confirm: bool = typer.Option(
        False, "--yes", "-y", help="Update without confirmation"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🔄 Update packages to latest versions.

    Updates critical packages like yt-dlp to their latest versions.
    """
    config = Config()
    updater = PackageUpdater(config, verbose=verbose)

    if package:
        # Update specific package
        if not auto_confirm:
            # Check if update is needed first
            result = updater.check_package_updates(package)
            if "error" in result:
                console.print(
                    Panel(
                        f"[red]✗[/red] Error checking {package}: {result['error']}",
                        title="Error",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)

            if not result["needs_update"]:
                console.print(
                    Panel(
                        f"[green]✓[/green] {package} is already up to date!\n"
                        f"Current version: {result['current_version']}",
                        title="No Update Needed",
                        border_style="green",
                    )
                )
                return

            # Ask for confirmation
            if not typer.confirm(
                f"Update {package} from {result['current_version']} to {result['latest_version']}?"
            ):
                console.print("Update cancelled.")
                return

        # Perform update
        with track_progress(f"Updating {package}...", verbose=verbose) as progress:
            result = updater.update_package(package, auto_confirm)
            progress.update(1, f"Update completed")

        if result["success"]:
            console.print(
                Panel(
                    f"[green]✓[/green] Successfully updated {package}!\n"
                    f"New version: {result['new_version']}\n"
                    f"Updated at: {result['updated_at']}",
                    title="Update Successful",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] Failed to update {package}\n"
                    f"Error: {result['error']}\n"
                    f"Output: {result.get('output', 'N/A')}",
                    title="Update Failed",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
    else:
        # Update all packages that need updates
        summary = updater.get_update_summary()

        if summary["packages_needing_update"] == 0:
            console.print(
                Panel(
                    "[green]✓[/green] All packages are up to date!",
                    title="No Updates Needed",
                    border_style="green",
                )
            )
            return

        # Show what will be updated
        packages_to_update = [
            r for r in summary["results"] if r.get("needs_update", False)
        ]

        console.print(
            Panel(
                f"📦 Packages to update:\n"
                + "\n".join(
                    [
                        f"• {p['package']}: {p['current_version']} → {p['latest_version']}"
                        for p in packages_to_update
                    ]
                ),
                title="Update Plan",
                border_style="yellow",
            )
        )

        if not auto_confirm:
            if not typer.confirm(f"Update {len(packages_to_update)} package(s)?"):
                console.print("Update cancelled.")
                return

        # Perform updates
        success_count = 0
        for package_info in packages_to_update:
            package_name = package_info["package"]

            with track_progress(
                f"Updating {package_name}...", verbose=verbose
            ) as progress:
                result = updater.update_package(package_name, auto_confirm=True)
                progress.update(1, f"Update completed")

            if result["success"]:
                success_count += 1
                console.print(
                    f"[green]✓[/green] Updated {package_name} to {result['new_version']}"
                )
            else:
                console.print(
                    f"[red]✗[/red] Failed to update {package_name}: {result['error']}"
                )

        # Final summary
        console.print(
            Panel(
                f"📊 Update Results:\n"
                f"Successful: {success_count}/{len(packages_to_update)}\n"
                f"Failed: {len(packages_to_update) - success_count}",
                title="Update Complete",
                border_style=(
                    "green" if success_count == len(packages_to_update) else "yellow"
                ),
            )
        )


@app.command()
def status(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    📊 Show package update status.

    Displays the current status of all critical packages.
    """
    config = Config()
    updater = PackageUpdater(config, verbose=verbose)

    summary = updater.get_update_summary()

    # Create detailed status table
    table = Table(title="Package Status Overview")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Current Version", style="green")
    table.add_column("Status", style="magenta")
    table.add_column("Last Checked", style="blue")
    table.add_column("Description", style="white")

    for result in summary["results"]:
        if "error" in result:
            table.add_row(
                result["package"],
                "Unknown",
                "[red]Error[/red]",
                "Never",
                result["error"],
            )
        else:
            status = "🔄 Update Available" if result["needs_update"] else "✅ Up to Date"
            table.add_row(
                result["package"],
                result["current_version"],
                status,
                result["last_checked"],
                result["description"],
            )

    console.print(table)

    # Summary stats
    console.print(
        Panel(
            f"📈 Statistics:\n"
            f"Total Packages: {summary['total_packages']}\n"
            f"Need Updates: {summary['packages_needing_update']}\n"
            f"Up to Date: {summary['total_packages'] - summary['packages_needing_update'] - summary['packages_with_errors']}\n"
            f"Errors: {summary['packages_with_errors']}\n"
            f"Last Check: {summary['last_check']}",
            title="Status Summary",
            border_style="blue",
        )
    )
