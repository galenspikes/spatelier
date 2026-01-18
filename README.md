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
├── cli/                 # Command-line interface modules
├── core/               # Core functionality and base classes
├── modules/            # Feature modules (video, audio, etc.)
├── database/           # Database models, connections, and repositories
├── analytics/          # Analytics and reporting
├── utils/              # Utility functions and helpers
├── tests/              # Comprehensive test suite
└── bin/                # Executable scripts
```

## Installation

### Global Installation (Recommended)

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

### Troubleshooting

If you're having issues with installation, see [GLOBAL_INSTALL.md](GLOBAL_INSTALL.md) for global installation options.

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
