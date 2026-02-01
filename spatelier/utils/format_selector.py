"""
Format selector utility for yt-dlp.

Provides shared format selector logic for video downloads and playlists.
"""


def get_format_selector(quality: str, format: str) -> str:
    """
    Get format selector for yt-dlp with fallbacks for YouTube issues.
    
    Args:
        quality: Video quality (e.g., "best", "worst", "720p", "1080p")
        format: Video format (e.g., "mp4", "mkv", "webm")
    
    Returns:
        Format selector string for yt-dlp
    """
    if quality == "best":
        # Add fallback chain: preferred format -> any format -> best available
        return f"best[ext={format}]/bestvideo[ext={format}]+bestaudio/best[ext={format}]/best"
    elif quality == "worst":
        return f"worst[ext={format}]/worst"
    else:
        # Extract numeric part from quality (e.g., "1080p" -> "1080")
        try:
            height = quality.replace("p", "")
            # Add fallback chain with height constraint
            return f"best[height<={height}][ext={format}]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        except (AttributeError, ValueError):
            # Fallback to simpler selector if parsing fails
            return f"best[ext={format}]/bestvideo+bestaudio/best"
