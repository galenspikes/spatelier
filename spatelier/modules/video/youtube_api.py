"""
YouTube Data API v3 integration for real video search and recommendations.

This module provides YouTube API integration for:
- Video search with real metadata
- Related video recommendations
- Channel information
- Rate limiting and error handling
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import pickle

    import google.auth
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

from spatelier.core.logger import get_logger

# VideoMetadata removed with SSD library


class YouTubeAPIService:
    """YouTube Data API v3 service for video search and recommendations."""

    def __init__(
        self, api_key: str = None, oauth_credentials: str = None, verbose: bool = False
    ):
        """Initialize YouTube API service with API key or OAuth."""
        self.api_key = api_key
        self.oauth_credentials = oauth_credentials
        self.verbose = verbose
        self.logger = get_logger("YouTubeAPI", verbose=verbose)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

        # Initialize API client
        self.youtube = None
        self.credentials = None

        if YOUTUBE_API_AVAILABLE:
            if oauth_credentials:
                self._initialize_oauth()
            elif api_key:
                self._initialize_api_key()
            else:
                self.logger.warning("No authentication method provided")
        else:
            self.logger.warning("YouTube API not available")

    def _initialize_oauth(self):
        """Initialize OAuth authentication."""
        try:
            # OAuth 2.0 scopes for YouTube
            SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

            # Load credentials from file
            creds = None
            token_file = "config/youtube_token.pickle"

            # Load existing token
            if os.path.exists(token_file):
                with open(token_file, "rb") as token:
                    creds = pickle.load(token)

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Load OAuth client credentials
                    if os.path.exists(self.oauth_credentials):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.oauth_credentials, SCOPES
                        )
                        creds = flow.run_local_server(port=0)
                    else:
                        self.logger.error(
                            f"OAuth credentials file not found: {self.oauth_credentials}"
                        )
                        return

                # Save credentials for next run
                with open(token_file, "wb") as token:
                    pickle.dump(creds, token)

            self.credentials = creds
            self.youtube = build("youtube", "v3", credentials=creds)
            self.logger.info("YouTube API client initialized with OAuth")

        except Exception as e:
            self.logger.error(f"Failed to initialize OAuth: {e}")
            self.youtube = None

    def _initialize_api_key(self):
        """Initialize API key authentication."""
        try:
            self.youtube = build("youtube", "v3", developerKey=self.api_key)
            self.logger.info("YouTube API client initialized with API key")
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube API: {e}")
            self.youtube = None

    def _rate_limit(self):
        """Apply rate limiting to API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get detailed video information for multiple videos."""
        if not self.youtube or not video_ids:
            return {}

        try:
            self._rate_limit()

            # Batch request for video details
            details_response = (
                self.youtube.videos()
                .list(part="statistics,contentDetails,snippet", id=",".join(video_ids))
                .execute()
            )

            details_dict = {}
            for item in details_response.get("items", []):
                video_id = item["id"]
                details_dict[video_id] = item

            return details_dict

        except HttpError as e:
            self.logger.error(f"Video details API error: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Video details error: {e}")
            return {}

    def _parse_duration(self, duration_iso: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re

        # Parse PT1H2M3S format
        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_iso)

        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS."""
        if not seconds:
            return "0:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    def _calculate_age(self, upload_date: datetime) -> str:
        """Calculate human-readable age from upload date."""
        now = datetime.now(upload_date.tzinfo) if upload_date.tzinfo else datetime.now()
        delta = now - upload_date

        if delta.days > 365:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        else:
            return "Today"

    def _get_category_name(self, category_id: str) -> str:
        """Get category name from ID."""
        categories = {
            "1": "Film & Animation",
            "2": "Autos & Vehicles",
            "10": "Music",
            "15": "Pets & Animals",
            "17": "Sports",
            "19": "Travel & Events",
            "20": "Gaming",
            "22": "People & Blogs",
            "23": "Comedy",
            "24": "Entertainment",
            "25": "News & Politics",
            "26": "Howto & Style",
            "27": "Education",
            "28": "Science & Technology",
        }
        return categories.get(category_id, "Unknown")


def get_youtube_api_key() -> Optional[str]:
    """Get YouTube API key from environment, database, config, or user input."""
    # Try environment variable first
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        return api_key

    # Try database
    api_key = _get_api_key_from_db("youtube")
    if api_key:
        return api_key

    # Try config file
    try:
        from spatelier.core.config import Config

        config = Config()
        # Add YouTube API key to config if needed
        config_key = getattr(config, "youtube_api_key", None)
        if config_key:
            return config_key
    except:
        pass

    # Prompt user for API key
    try:
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()
        console.print("\n[bold blue]YouTube API Integration[/bold blue]")
        console.print(
            "For real video search results, you can provide a YouTube Data API v3 key."
        )
        console.print(
            "Without an API key, the system will use mock data for development."
        )

        choice = Prompt.ask(
            "Do you want to enter an API key?", choices=["Y", "N"], default="N"
        )

        if choice.upper() == "Y":
            api_key = Prompt.ask("Enter your YouTube Data API v3 key", password=True)
            if api_key and api_key.strip():
                # Save to database
                _save_api_key_to_db("youtube", api_key.strip())
                # Also save to environment for this session
                os.environ["YOUTUBE_API_KEY"] = api_key.strip()
                console.print("[green]✓ API key saved to database and session[/green]")
                return api_key.strip()
            else:
                console.print("[yellow]No API key provided, using mock data[/yellow]")
        else:
            console.print("[yellow]Using mock data for development[/yellow]")

    except (EOFError, KeyboardInterrupt):
        # Handle non-interactive environments
        pass
    except Exception as e:
        # Handle any other errors gracefully
        pass

    return None


def _save_api_key_to_db(service_name: str, api_key: str) -> bool:
    """Save API key to database."""
    try:
        from sqlalchemy.sql import func

        from spatelier.core.config import Config
        from spatelier.database.connection import DatabaseManager
        from spatelier.database.models import APIKeys

        config = Config()
        db_manager = DatabaseManager(config)
        db_manager.connect_sqlite()

        with db_manager.get_session() as session:
            # Check if key already exists
            existing_key = (
                session.query(APIKeys)
                .filter(APIKeys.service_name == service_name, APIKeys.is_active == True)
                .first()
            )

            if existing_key:
                # Update existing key
                existing_key.key_value = api_key
                existing_key.updated_at = func.now()
            else:
                # Create new key
                new_key = APIKeys(
                    service_name=service_name, key_value=api_key, is_active=True
                )
                session.add(new_key)

            session.commit()
            return True

    except Exception as e:
        # Log error but don't fail the whole process
        import logging

        logging.error(f"Failed to save API key to database: {e}")
        return False


def _get_api_key_from_db(service_name: str) -> Optional[str]:
    """Get API key from spatelier.database."""
    try:
        from sqlalchemy.sql import func

        from spatelier.core.config import Config
        from spatelier.database.connection import DatabaseManager
        from spatelier.database.models import APIKeys

        config = Config()
        db_manager = DatabaseManager(config)
        db_manager.connect_sqlite()

        with db_manager.get_session() as session:
            api_key = (
                session.query(APIKeys)
                .filter(APIKeys.service_name == service_name, APIKeys.is_active == True)
                .first()
            )

            if api_key:
                return api_key.key_value

    except Exception as e:
        # Log error but don't fail the whole process
        import logging

        logging.error(f"Failed to get API key from database: {e}")

    return None


def create_youtube_service(
    verbose: bool = False, oauth_credentials: str = None
) -> Optional[YouTubeAPIService]:
    """Create YouTube API service with proper configuration."""
    logger = get_logger("YouTubeAPI", verbose=verbose)

    # Debug logging
    logger.info(
        f"create_youtube_service called with oauth_credentials: {oauth_credentials}"
    )
    logger.info(
        f"oauth_credentials exists: {oauth_credentials and os.path.exists(oauth_credentials) if oauth_credentials else False}"
    )

    # Try OAuth first if credentials provided
    if oauth_credentials and os.path.exists(oauth_credentials):
        logger.info("Using OAuth credentials for YouTube API")
        return YouTubeAPIService(oauth_credentials=oauth_credentials, verbose=verbose)

    # Fallback to API key
    logger.info("Falling back to API key authentication")
    api_key = get_youtube_api_key()

    if not api_key:
        logger.warning(
            "No YouTube API key found. Set YOUTUBE_API_KEY environment variable."
        )
        return None

    logger.info("Using API key for YouTube API")
    return YouTubeAPIService(api_key=api_key, verbose=verbose)
