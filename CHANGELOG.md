# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-01-22

### Fixed
- Job duration calculation: now returns `None` when job completes without PROCESSING status (was incorrectly using `created_at` fallback)
- Version consistency: `spatelier/__init__.py` now matches `pyproject.toml` version

### Changed
- Black target-version updated from `py39` to `py310` to match `requires-python >=3.10`
- Code formatting: all files reformatted with Black (py310 target)

### Removed
- Removed unused `bin/` directory and convenience scripts (entry point is in `pyproject.toml`)
- Removed broken `spt` symlink
- Removed `.venv` directory (using `venv/` instead)

## [0.3.0] - 2026-01-22

### Added
- Job duration tracking: jobs now properly track `started_at` and calculate `duration_seconds`
- Transcription dependencies moved to core: `faster-whisper` and `openai-whisper` are now always installed

### Changed
- Default transcription model changed from `large` to `small` for faster performance
- Video download command: transcription now defaults to `False` (use `download-enhanced` for transcription by default)
- Pre-commit hooks simplified to only black, isort, and mypy (removed flake8 and other checks)

### Fixed
- Job duration tracking: `started_at` is now set when jobs transition to PROCESSING status
- Duration calculation: improved to use `created_at` as fallback if `started_at` is not set
- Job tracking fixed in both `download_service` and `playlist_service`

## [0.2.1] - 2026-01-22

### Fixed
- Fixed `get_default_data_dir()` to work when installed via Homebrew or other package managers
- Now uses `~/Library/Application Support/spatelier` on macOS when not in development mode
- Previously required running from repository root, now works from any location

## [0.2.0] - 2026-01-21

### Added
- SQLite transcription storage with FTS5 full-text search
- Homebrew installation support (Formula/spatelier.rb)
- Automated release script with logging (scripts/release.sh)
- Homebrew formula update script (scripts/update_homebrew.sh)
- Release automation in Makefile (make release, make update-homebrew)
- Comprehensive integration tests for SQLite transcription storage

### Changed
- All file system operations now relative to repo directory (no home directory usage)
- Database storage location fixed to `.data/` in repo root
- Improved flake8 configuration to work with black formatter
- Updated cursor rules with release process documentation
- Enhanced README with Homebrew installation instructions

## [0.1.0] - TBD

### Added
- Initial release
- Core video and audio processing
- CLI interface
- Database support
- Analytics features

[Unreleased]: https://github.com/galenspikes/spatelier/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/galenspikes/spatelier/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/galenspikes/spatelier/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/galenspikes/spatelier/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/galenspikes/spatelier/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/galenspikes/spatelier/releases/tag/v0.1.0
