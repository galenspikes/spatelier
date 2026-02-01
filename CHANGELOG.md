# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.2] - 2026-02-01

### Added
- **Docker:** Official image on Docker Hub (`galenspikes/spatelier`). Multi-platform (linux/amd64 and linux/arm64) for QNAP, Apple Silicon, and x86. Includes ffmpeg and Chromium for YouTube cookie refresh. See README for pull and run with volume mounts.
- **Version tracking:** Single source of truth in `pyproject.toml`. `make sync-version` (or `scripts/sync_version.sh`) syncs `__version__` to `spatelier/__init__.py` and `__init__.py`. Release script verifies version is synced before tagging; prints Docker buildx command to push versioned and latest tags.

### Changed
- **Single-package layout:** All application code now lives under `spatelier/` (cli, core, database, domain, infrastructure, modules, analytics, utils). One installable package; setuptools `include = ["spatelier*"]` only. Eliminates risk of missing packages in the installed manifest; faster startup (no alias imports at load).
- **Alembic migrations:** Idempotent for SQLite. Initial migration uses `batch_alter_table` and conditional index drop/create so it runs after `Base.metadata.create_all()`. File-tracking and transcription migrations only add/create when columns/tables don't exist. SQLite transcription integration tests no longer skipped.
- **NAS integration tests:** Skip only when no writable root exists (same logic as `get_nas_path_root`: /Volumes/NAS, home, or tmp). Tests run on typical dev machines without a NAS volume.

### Fixed
- (None; 0.4.2 is primarily layout, Docker, and tooling.)

## [0.4.1] - (release date TBD)

### Fixed
- Installed package: include `domain*` and `infrastructure*` in setuptools `packages.find.include` so the installed CLI (e.g. Homebrew) no longer raises `ModuleNotFoundError: No module named 'domain'`.

### Added
- Release hygiene: test that every top-level Python package is listed in `pyproject.toml` setuptools include, to prevent this regression.

### Changed
- Docs and scripts: replaced repo-specific paths with generics (e.g. `/path/to/spatelier`, `$(brew --prefix)`, `/Volumes/NAS`, `~/Library/Logs/Homebrew/`).

## [0.4.0] - 2026-01-31

### Added
- NAS support: `StorageAdapter.can_write_to(path)` to verify write access before download; download/playlist flows check remote paths and return a clear error if not writable.
- Parametrized NAS test path: tests use `.spatelier/tests/` under a configurable root (default `/Volumes/NAS`, fallback home/tmp); `nas_available` only true when root is actual NAS.
- tests/unit/test_release_hygiene.py: Tests that release script uses absolute log path, pytest config is single-source, and Alembic warning filter is present.

### Fixed
- Release script: Use absolute path for log file (`REPO_ROOT`) so tap-repo subshell can write to it; fixes `tee: .data/logs/... No such file or directory` and false "Could not update tap repository" warning.
- Pytest config: Removed duplicate `[tool.pytest.ini_options]` from pyproject.toml so pytest no longer warns "ignoring pytest config in pyproject.toml".
- NAS tests: use real `Config()` (or `nas_config` fixture) instead of `Mock(spec=Config)` so `database.sqlite_path`, `video.temp_dir`, etc. are set; fixes `AttributeError` in metadata and DB paths.
- VideoDownloadService: added delegation methods `_is_nas_path`, `_get_temp_processing_dir`, `_move_file_to_final_destination`, `_cleanup_temp_directory`, `_move_playlist_to_final_destination` for NAS/StorageAdapter; tests updated to use `download_video`, `PlaylistService`, `TranscriptionService` (or use cases).
- Media file tracker: always check for existing media by path; pass `mime_type` into `repos.media.create()` to fix `NOT NULL constraint failed: media_files.mime_type`.
- Playlist/job: convert `output_path` to string before `job_manager.update_job()` and coerce in job_manager to fix PosixPath/serialization issues.
- NAS performance tests: use `write_bytes`/`read_bytes` for byte content and `write_text`/`read_text` for str to fix `TypeError: data must be str, not bytes`.

### Changed
- pytest.ini: Added filter for harmless Alembic "autoincrement only make sense for MySQL" warning (we use SQLite).
- docs/release-errors-and-warnings.md: Document release script errors/warnings and fixes.
- Integration NAS tests: `test_nas_dir_is_writable` and `test_nas_permissions_and_access` use `can_write_to()`; skip with a clear message when path is not writable (e.g. NFS/SMB permission issues on macOS).

## [0.3.9] - 2026-01-23

### Fixed
- Download service: Fixed glob iterator check in `_resolve_downloaded_path()`. `Path.glob()` returns an iterator that is always truthy; converting to list ensures we only process when files are actually found.

### Changed
- Code quality improvements: Simplified truthiness checks, list comprehensions, extracted constants, removed unused variables, improved type hints, simplified dict.get() usage, optimized .lower() calls. (12 files)

## [0.3.8] - 2026-01-22

### Fixed
- Homebrew installation: Fixed pip installation by using `get-pip.py` with `--isolated` flag instead of `ensurepip`, which was finding system pip (due to `--system-site-packages`) and not installing into venv. This ensures pip is properly installed with bin symlinks in the virtual environment before package installation.

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
