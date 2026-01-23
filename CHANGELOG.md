# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.7] - 2026-01-22

### Fixed
- Homebrew installation: Fixed pip installation by using `ensurepip` (bundled with Python) instead of invalid `--python` option, ensuring pip, setuptools, and wheel are properly installed in venv before package installation

## [0.3.6] - 2026-01-22

### Fixed
- Homebrew installation: Fixed formula to explicitly install pip, setuptools, and wheel before installing package, ensuring dependencies from pyproject.toml are properly installed

## [0.3.5] - 2026-01-22

### Fixed
- Homebrew installation: Fixed formula to use `venv.pip_install` instead of calling pip directly, ensuring pip is properly installed in the virtualenv

## [0.3.4] - 2026-01-22

### Fixed
- Homebrew installation checksum error: Fixed SHA256 calculation in release script to download actual GitHub tarball after tag is pushed, ensuring Homebrew formula checksums match GitHub-generated tarballs
- Simplified release script by removing separate `update_homebrew.sh` script and inlining SHA256 calculation with retry logic

## [0.3.3] - 2026-01-22

### Fixed
- Homebrew installation checksum error: Fixed SHA256 calculation in release script to use `git archive` instead of downloading from GitHub before tag exists
- Release script now correctly calculates SHA256 from the commit that will be tagged, ensuring Homebrew formula checksums match GitHub-generated tarballs

## [0.3.2] - 2026-01-22

### Changed
- faster-whisper is now a core dependency (always installed by default)
- Transcription is available by default without optional extras

### Removed
- Removed openai-whisper support completely (unsupported)
- Removed `use_faster_whisper` config option (always uses faster-whisper)
- Removed `[transcription]` optional extra (faster-whisper is in core dependencies)
- Removed old `modules/video/transcription_service.py` file (replaced by `services/transcription_service.py`)
- Removed MongoDB integration test (MongoDB not used)

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
