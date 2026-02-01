"""
Video processing CLI commands.

This module provides command-line interfaces for video processing operations.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from spatelier.core.base import ProcessingResult
from spatelier.core.config import Config
from spatelier.core.decorators import handle_errors, time_operation
from spatelier.core.logger import get_logger
from spatelier.core.progress import show_download_progress, track_progress

# Create the video CLI app
app = typer.Typer(
    name="video",
    help="Video processing commands",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
@handle_errors(context="video download", verbose=True)
@time_operation(verbose=True)
def download(
    url: str = typer.Argument(
        ...,
        help="URL to download video from (supports channels, playlists, and single videos)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path or directory"
    ),
    quality: str = typer.Option("best", "--quality", "-q", help="Video quality"),
    format: str = typer.Option("mp4", "--format", "-f", help="Output format"),
    max_videos: int = typer.Option(
        10,
        "--max-videos",
        "-m",
        help="Maximum number of videos to download (for channels/playlists)",
    ),
    transcribe: bool = typer.Option(
        False,
        "--transcribe/--no-transcribe",
        help="Enable automatic transcription (use download-enhanced for transcription by default)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Download video from URL.

    Supports YouTube channels, playlists, single videos, and other popular video platforms.
    Automatically detects channel URLs and converts them to playlist downloads.
    """
    # Lazy import - only import when command is actually called
    from spatelier.core.service_factory import ServiceFactory

    config = Config()
    logger = get_logger("video-download", verbose=verbose)

    # Detect if this is a channel URL and convert to playlist
    processed_url = url
    is_channel = False
    is_playlist = False

    if "youtube.com" in url:
        if "/playlist" in url or "list=" in url:
            is_playlist = True
        if "/@" in url and "/videos" not in url:
            # Strip trailing slashes before appending /videos
            processed_url = f"{url.rstrip('/')}/videos"
            is_channel = True
        elif "/channel/" in url and "/videos" not in url:
            # Strip trailing slashes before appending /videos
            processed_url = f"{url.rstrip('/')}/videos"
            is_channel = True
        elif "/videos" in url:
            is_channel = True

    if is_channel:
        logger.info(f"Detected channel URL, converting to playlist: {processed_url}")
        console.print(
            f"[yellow]📺 Channel detected![/yellow] Converting to playlist download..."
        )

        with ServiceFactory(config, verbose=verbose) as services:
            result = services.download_playlist_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
                max_videos=max_videos,
            )

            if result.is_successful():
                console.print(
                    Panel(
                        f"[green]✓[/green] Channel download successful!\n"
                        f"Output: {result.output_path}\n"
                        f"Videos downloaded: {result.metadata.get('videos_downloaded', 'Unknown')}",
                        title="Success",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[red]✗[/red] Channel download failed: {result.message}",
                        title="Error",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)
    elif is_playlist:
        logger.info(f"Detected playlist URL: {processed_url}")
        console.print(f"[yellow]📼 Playlist detected![/yellow] Downloading playlist...")
        with ServiceFactory(config, verbose=verbose) as services:
            result = services.download_playlist_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
                max_videos=max_videos,
            )

            if result.is_successful():
                transcribed = 0
                embedded = 0
                video_files = []
                if transcribe and result.output_path:
                    playlist_dir = Path(result.output_path)
                    for ext in config.video_extensions:
                        video_files.extend(playlist_dir.rglob(f"*{ext}"))
                    if max_videos and len(video_files) > max_videos:
                        video_files = sorted(
                            video_files,
                            key=lambda path: path.stat().st_mtime,
                            reverse=True,
                        )[:max_videos]
                    for video_file in sorted(video_files):
                        if not video_file.is_file():
                            continue
                        media_record = services.repositories.media.get_by_file_path(
                            str(video_file)
                        )
                        media_file_id = media_record.id if media_record else None
                        transcribe_ok = services.transcribe_video_use_case.execute(
                            video_path=video_file,
                            media_file_id=media_file_id,
                            embed_subtitles=True,
                        )
                        if transcribe_ok:
                            transcribed += 1
                            embedded += 1
                        else:
                            console.print(
                                Panel(
                                    f"[yellow]![/yellow] Transcription failed: {video_file.name}",
                                    title="Warning",
                                    border_style="yellow",
                                )
                            )
                console.print(
                    Panel(
                        f"[green]✓[/green] Playlist download successful!\n"
                        f"Output: {result.output_path}\n"
                        f"Videos downloaded: {result.metadata.get('successful_downloads', 'Unknown')}"
                        + (
                            f"\nTranscribed: {transcribed}/{len(video_files)}"
                            if transcribe
                            else ""
                        )
                        + (
                            f"\nEmbedded: {embedded}/{len(video_files)}"
                            if transcribe
                            else ""
                        ),
                        title="Success",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[red]✗[/red] Playlist download failed: {result.message}",
                        title="Error",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)
    else:
        # Single video download
        with ServiceFactory(config, verbose=verbose) as services:
            result = services.download_video_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
            )

            if result.is_successful():
                if transcribe and result.output_path:
                    media_file_id = (
                        result.metadata.get("media_file_id")
                        if result.metadata
                        else None
                    )
                    transcribe_ok = services.transcribe_video_use_case.execute(
                        video_path=Path(result.output_path),
                        media_file_id=media_file_id,
                        embed_subtitles=True,
                    )
                    if not transcribe_ok:
                        console.print(
                            Panel(
                                "[yellow]![/yellow] Transcription failed. The original file is kept.\n"
                                'Retry: spatelier video embed-subtitles "<path>" --transcription-model small',
                                title="Warning",
                                border_style="yellow",
                            )
                        )
                console.print(
                    Panel(
                        f"[green]✓[/green] Video downloaded successfully!\n"
                        f"Output: {result.output_path}",
                        title="Success",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[red]✗[/red] Download failed: {result.message}",
                        title="Error",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)


@app.command()
@handle_errors(context="enhanced video download", verbose=True)
@time_operation(verbose=True)
def download_enhanced(
    url: str = typer.Argument(..., help="URL to download video from"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    quality: str = typer.Option("best", "--quality", "-q", help="Video quality"),
    format: str = typer.Option("mp4", "--format", "-f", help="Output format"),
    max_videos: int = typer.Option(
        10,
        "--max-videos",
        "-m",
        help="Maximum number of videos to download (for channels/playlists)",
    ),
    transcribe: bool = typer.Option(
        True,
        "--transcribe/--no-transcribe",
        help="Enable/disable automatic transcription",
    ),
    transcription_model: str = typer.Option(
        "small",
        "--transcription-model",
        help="Whisper model size (tiny, base, small, medium, large)",
    ),
    transcription_language: str = typer.Option(
        "en", "--transcription-language", help="Language code for transcription"
    ),
    use_fallback: bool = typer.Option(
        True, "--fallback/--no-fallback", help="Enable/disable fallback URL extraction"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Download video with automatic transcription and fallback support.

    Enhanced download with:
    - Automatic transcription using OpenAI Whisper
    - Fallback URL extraction when yt-dlp fails
    - Analytics and storage in MongoDB

    Supports YouTube, Vimeo, and other popular video platforms.
    """
    # Lazy import - only import when command is actually called
    from spatelier.core.service_factory import ServiceFactory

    config = Config()
    logger = get_logger("video-download-enhanced", verbose=verbose)

    with ServiceFactory(config, verbose=verbose) as services:
        processed_url = url
        is_channel = False
        is_playlist = False

        if "youtube.com" in url:
            if "/playlist" in url or "list=" in url:
                is_playlist = True
            if "/@" in url and "/videos" not in url:
                processed_url = f"{url.rstrip('/')}/videos"
                is_channel = True
            elif "/channel/" in url and "/videos" not in url:
                processed_url = f"{url.rstrip('/')}/videos"
                is_channel = True
            elif "/videos" in url:
                is_channel = True

        if is_channel:
            logger.info(
                f"Detected channel URL, converting to playlist: {processed_url}"
            )
            console.print(
                "[yellow]📺 Channel detected![/yellow] Converting to playlist download..."
            )
            download_result = services.download_playlist_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
                max_videos=max_videos,
            )
        elif is_playlist:
            logger.info(f"Detected playlist URL: {processed_url}")
            console.print(
                "[yellow]📼 Playlist detected![/yellow] Downloading playlist..."
            )
            download_result = services.download_playlist_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
                max_videos=max_videos,
            )
        else:
            # First download the video
            download_result = services.download_video_use_case.execute(
                url=processed_url,
                output_path=output,
                quality=quality,
                format=format,
            )

        if not download_result.is_successful():
            console.print(
                Panel(
                    f"[red]✗[/red] Download failed: {download_result.message}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        if transcribe and download_result.output_path:
            if is_channel or is_playlist:
                playlist_dir = Path(download_result.output_path)
                video_files = [
                    file
                    for ext in config.video_extensions
                    for file in playlist_dir.rglob(f"*{ext}")
                ]
                if max_videos and len(video_files) > max_videos:
                    video_files = sorted(
                        video_files,
                        key=lambda path: path.stat().st_mtime,
                        reverse=True,
                    )[:max_videos]
                transcribed = 0
                embedded = 0
                for video_file in sorted(video_files):
                    if not video_file.is_file():
                        continue
                    media_record = services.repositories.media.get_by_file_path(
                        str(video_file)
                    )
                    media_file_id = media_record.id if media_record else None
                    transcribe_ok = services.transcribe_video_use_case.execute(
                        video_path=video_file,
                        media_file_id=media_file_id,
                        language=transcription_language,
                        model_size=transcription_model,
                        embed_subtitles=True,
                    )
                    if transcribe_ok:
                        transcribed += 1
                        embedded += 1
                    else:
                        console.print(
                            Panel(
                                f"[yellow]![/yellow] Transcription failed: {video_file.name}",
                                title="Warning",
                                border_style="yellow",
                            )
                        )
                result = download_result
                result.message += f" (transcribed {transcribed}/{len(video_files)})"
            else:
                media_file_id = download_result.metadata.get("media_file_id")
                transcribe_result = services.transcribe_video_use_case.execute(
                    video_path=Path(download_result.output_path),
                    media_file_id=media_file_id,
                    language=transcription_language,
                    model_size=transcription_model,
                    embed_subtitles=True,
                )

                if transcribe_result:
                    result = download_result
                    result.message += " (with transcription and subtitles)"
                else:
                    result = download_result
                    result.add_warning(
                        "Transcription completed but subtitle embedding failed"
                    )
        else:
            result = download_result

        if result.success:
            method = (
                result.metadata.get("download_method", "yt-dlp")
                if result.metadata
                else "yt-dlp"
            )
            console.print(
                Panel(
                    f"[green]✓[/green] Video downloaded successfully!\n"
                    f"Output: {result.output_path}\n"
                    f"Method: {method}",
                    title="Success",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] Download failed: {result.message}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)


@app.command()
def download_playlist(
    url: str = typer.Argument(..., help="Playlist URL to download"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory (will create playlist folder)"
    ),
    quality: str = typer.Option("best", "--quality", "-q", help="Video quality"),
    format: str = typer.Option("mp4", "--format", "-f", help="Output format"),
    use_fallback: bool = typer.Option(
        True, "--fallback/--no-fallback", help="Enable/disable fallback URL extraction"
    ),
    continue_download: bool = typer.Option(
        True,
        "--continue/--no-continue",
        help="Continue from failed/incomplete downloads",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Download playlist with fallback support.

    Enhanced playlist download with:
    - Automatic folder creation with playlist name and ID
    - Fallback URL extraction when yt-dlp fails
    - Analytics and storage in MongoDB

    Supports YouTube playlists and other platforms.
    """
    # Lazy import - only import when command is actually called
    from spatelier.core.service_factory import ServiceFactory

    config = Config()

    with ServiceFactory(config, verbose=verbose) as services:
        # First download the playlist
        playlist_result = services.download_playlist_use_case.execute(
            url=url, output_path=output, quality=quality, format=format
        )

        if not playlist_result.is_successful():
            console.print(
                Panel(
                    f"[red]✗[/red] Playlist download failed: {playlist_result.message}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        # Build result message
        metadata = playlist_result.metadata or {}
        message = f"Playlist downloaded successfully: {metadata.get('total_videos', 0)} videos"

        result = ProcessingResult.success_result(
            message=message,
            output_path=playlist_result.output_path,
            metadata=playlist_result.metadata,
        )

        if result.is_successful():
            metadata = result.metadata or {}
            transcription_status = (
                "Enabled" if metadata.get("transcription_enabled") else "Disabled"
            )
            console.print(
                Panel(
                    f"[green]✓[/green] Playlist downloaded successfully!\n"
                    f"Output: {result.output_path}\n"
                    f"Playlist: {metadata.get('playlist_title', 'Unknown')}\n"
                    f"Videos: {metadata.get('successful_downloads', 0)}/{metadata.get('total_videos', 0)}\n"
                    f"Transcription: {transcription_status}",
                    title="Success",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] Playlist download failed: {result.message}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)


@app.command()
def embed_subtitles(
    video_file: Path = typer.Argument(..., help="Video file to embed subtitles into"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output video file (default: adds '_with_subs' to filename)",
    ),
    transcription_model: str = typer.Option(
        "small",
        "--transcription-model",
        help="Whisper model size (tiny, base, small, medium, large)",
    ),
    transcription_language: str = typer.Option(
        "en", "--transcription-language", help="Language code for transcription"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Embed subtitles into an existing video file.

    Transcribes the video using OpenAI Whisper and embeds the subtitles directly
    into the video file. The subtitle track will be named based on the detected language.

    Example:
        spatelier-video embed-subtitles video.mp4
        spatelier-video embed-subtitles video.mp4 --output video_with_subs.mp4
    """
    # Lazy import - only import when command is actually called
    from spatelier.core.service_factory import ServiceFactory

    config = Config()
    logger = get_logger("video-embed-subtitles", verbose=verbose)

    # Check if video file exists
    if not video_file.exists():
        console.print(
            Panel(
                f"[red]✗[/red] Video file not found: {video_file}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Initialize services
    with ServiceFactory(config, verbose=verbose) as services:
        logger.info(f"Transcribing video: {video_file}")

        # Transcribe and embed subtitles using use case
        output_file = output_file or video_file
        success = services.transcribe_video_use_case.execute(
            video_path=video_file,
            language=transcription_language,
            model_size=transcription_model,
            embed_subtitles=True,
        )

        if success:
            console.print(
                Panel(
                    f"[green]✓[/green] Subtitles embedded successfully!\n"
                    f"Input: {video_file}\n"
                    f"Output: {output_file}\n"
                    f"Language: {transcription_language}\n"
                    f"Model: {transcription_model}",
                    title="Success",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] Failed to embed subtitles into video",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)


@app.command()
def extract_audio_from_url(
    url: str = typer.Argument(..., help="YouTube video URL"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory"
    ),
    format: str = typer.Option(
        "mp3", "--format", "-f", help="Audio format (mp3, wav, flac, aac, ogg, m4a)"
    ),
    bitrate: int = typer.Option(320, "--bitrate", "-b", help="Audio bitrate in kbps"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    🎵 Extract audio from YouTube video.

    Downloads only the audio track from a YouTube video and saves it in your preferred format.
    Perfect for getting music, podcasts, or any audio content from videos.
    """
    from spatelier.modules.video.services.audio_extraction_service import AudioExtractionService

    config = Config()
    service = AudioExtractionService(config, verbose=verbose)

    # Set default output directory
    if output_dir is None:
        from spatelier.core.config import get_default_data_dir

        repo_root = get_default_data_dir().parent
        output_dir = repo_root / "audio_extracts"

    try:
        result = service.extract_audio_from_url(
            url=url, output_dir=output_dir, format=format, bitrate=bitrate
        )

        if result.is_successful():
            console.print(
                Panel(
                    f"[green]✓[/green] Audio extracted successfully!\n"
                    f"File: {result.output_path.name}\n"
                    f"Size: {result.metadata.get('file_size_mb', 0):.1f} MB\n"
                    f"Format: {format.upper()}\n"
                    f"Bitrate: {bitrate} kbps",
                    title="Success",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] Audio extraction failed: {result.message}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(
            Panel(
                f"[red]✗[/red] Audio extraction failed: {str(e)}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Input video file"),
    output_file: Path = typer.Argument(..., help="Output video file"),
    quality: str = typer.Option("medium", "--quality", "-q", help="Output quality"),
    codec: str = typer.Option("auto", "--codec", "-c", help="Video codec"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Convert video to different format.

    Supports various input and output formats including MP4, AVI, MOV, etc.
    """
    # Lazy import - only import when command is actually called
    from spatelier.modules.video.converter import VideoConverter

    config = Config()
    logger = get_logger("video-convert", verbose=verbose)

    converter = VideoConverter(config, verbose=verbose)
    result = converter.convert(input_file, output_file, quality=quality, codec=codec)

    if result.success:
        console.print(
            Panel(
                f"[green]✓[/green] Video converted successfully!\n"
                f"Output: {result.output_path}",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗[/red] Conversion failed: {result.message}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def info(
    file_path: Path = typer.Argument(..., help="Video file to analyze"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Display detailed information about a video file.
    """
    config = Config()
    logger = get_logger("video-info", verbose=verbose)

    # This would use a video analyzer module
    # analyzer = VideoAnalyzer(config, verbose=verbose)
    # info = analyzer.analyze(file_path)

    # For now, show basic file info
    if not file_path.exists():
        console.print(
            Panel(
                f"[red]✗[/red] File not found: {file_path}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Create info table
    table = Table(title=f"Video Information: {file_path.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("File Path", str(file_path))
    table.add_row("File Size", f"{file_path.stat().st_size:,} bytes")
    table.add_row("Format", file_path.suffix.upper())

    console.print(table)
