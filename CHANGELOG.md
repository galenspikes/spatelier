# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/galenspikes/spatelier/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/galenspikes/spatelier/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/galenspikes/spatelier/releases/tag/v0.1.0
