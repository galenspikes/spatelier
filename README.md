# Spatelier

A personal tool library for video and music file handling, built with modern Python architecture and inspired by excellent projects like yt-dlp.

## Features

- **Video Processing**: Download, transcribe, and process videos with automatic subtitle embedding
- **Audio Processing**: Extract, convert, and normalize audio from videos
- **Analytics**: Track usage and generate insights from your media library
- **Database Management**: SQLite + MongoDB for structured and unstructured data
- **Batch Operations**: Process multiple files with intelligent resume logic
- **NAS Support**: Smart handling of Network Attached Storage with local processing
- **Comprehensive Testing**: Full test suite with unit, integration, and performance tests
- **Modern CLI**: Beautiful, type-safe command-line interface with Rich output

## Architecture

```
spatelier/
├── cli/                 # Command-line interface (presentation layer)
├── domain/              # Domain layer (business logic)
│   ├── models/         # Domain models (Video, Playlist, MediaFile)
│   ├── services/       # Domain services (MediaFileTracker, JobManager, PlaylistTracker)
│   └── use_cases/      # Use cases (DownloadVideoUseCase, TranscribeVideoUseCase, etc.)
├── infrastructure/     # Infrastructure layer
│   └── storage/        # Storage adapters (LocalStorageAdapter, NASStorageAdapter)
├── core/               # Core functionality and base classes
│   ├── service_factory.py  # Dependency injection container
│   └── interfaces.py       # Service interfaces
├── modules/            # Feature modules (video, audio, etc.)
│   └── video/
│       └── services/   # Pure executor services (VideoDownloadService, etc.)
├── database/           # Database models, connections, and repositories
├── analytics/          # Analytics and reporting
├── utils/              # Utility functions and helpers
└── tests/              # Comprehensive test suite
```

### Architecture Layers

- **CLI Layer**: User-facing commands, delegates to use cases
- **Use Case Layer**: Orchestrates business logic, coordinates services and domain services
- **Domain Layer**: Business entities and domain services for persistence logic
- **Service Layer**: Pure executors (no repository access), focused on single responsibilities
- **Infrastructure Layer**: Storage adapters, external system integrations
- **Repository Layer**: Data access abstraction
```

## Installation

### Homebrew (Recommended - No pip/venv needed!)

**Install with Homebrew - handles everything automatically:**

```bash
brew install --build-from-source https://raw.githubusercontent.com/galenspikes/spatelier/main/Formula/spatelier.rb
```

That's it! `spatelier` is now available system-wide. No pip, no venv, no Python management.

**Update:**
```bash
brew upgrade spatelier
```

### Global Installation with pipx

**Want to use `spatelier` from anywhere? Use pipx:**

```bash
# Install pipx (one-time setup)
brew install pipx
pipx ensurepath

# Install Spatelier globally
pipx install -e /path/to/spatelier

# Or from PyPI (once published)
pipx install spatelier
```

Now `spatelier` works from any directory! No venv activation needed.

**See [GLOBAL_INSTALL.md](GLOBAL_INSTALL.md) for all global installation options.**

### From PyPI

```bash
# Basic installation
pip install spatelier

# With optional features
pip install spatelier[transcription,analytics]
pip install spatelier[all]  # All optional features
```

### From Source (Development)

For development, you'll need to activate the virtual environment:

```bash
# 1. Clone the repository
git clone https://github.com/galenspikes/spatelier
cd spatelier

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install
```


### Standalone Executable

Download the latest release from [GitHub Releases](https://github.com/galenspikes/spatelier/releases) and run directly (no Python installation required).

### Docker

Run spatelier in a container (no local Python or ffmpeg required). The image includes ffmpeg and Chromium for YouTube cookie refresh. Supports linux/amd64 (e.g. QNAP, x86 PCs) and linux/arm64 (e.g. Apple Silicon, ARM NAS).

```bash
# Pull from Docker Hub (no build required). Use :latest or a specific version (e.g. :0.4.1)
docker pull galenspikes/spatelier:latest

# Or build from source
docker build -t spatelier .

# Run (version check)
docker run --rm galenspikes/spatelier:latest --version

# Run with volume mounts for config and downloads
docker run --rm -it \
  -v "$HOME/.config/spatelier:/home/app/.config/spatelier" \
  -v "/path/to/downloads:/home/app/downloads" \
  galenspikes/spatelier:latest video download "https://youtube.com/watch?v=..."
```

Mount your config dir so the database and settings persist. Mount a host directory as the download output (e.g. `-v /path/to/downloads:/home/app/downloads` and set output path via config or CLI). On QNAP Container Station, create a container from the image and add the same volume mounts in the UI.

### Troubleshooting

If you're having issues with installation, see [GLOBAL_INSTALL.md](GLOBAL_INSTALL.md) for global installation options.

**Homebrew:** When installing or upgrading with `brew install` or `brew upgrade spatelier`, you may see a warning about "Failed to fix install linkage" or "Updated load commands do not fit in the header" for the `av` library. This is a known issue with pre-built dylibs in that dependency; the install is still valid and spatelier works normally. You can ignore the warning.

## Usage

```bash
# List available commands
spatelier --help

# Video processing
spatelier video download <url>                    # Download video
spatelier video download-enhanced <url>           # Download with transcription
spatelier video download-playlist <url>          # Download entire playlist (no transcription)
spatelier video embed-subtitles <video>          # Embed subtitles
spatelier video convert <input> <output>         # Convert format
spatelier video info <video>                      # Show video info

# Audio processing
spatelier audio convert <input> <output>          # Convert audio format
spatelier audio info <audio>                      # Show audio info

# Batch operations

# Analytics
spatelier analytics report                        # Generate usage reports

```

## Development

```bash
# Run tests
pytest                                    # Run all tests
pytest -m unit                          # Run unit tests only
pytest -m integration                   # Run integration tests only
pytest -m nas                           # Run NAS tests (requires NAS)

# Format code
black .
isort .

# Type checking
mypy .

# Linting
flake8 .

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each version.

## Security

For security concerns, please see [SECURITY.md](SECURITY.md).

## License

MIT License - see [LICENSE](LICENSE) file for details.
