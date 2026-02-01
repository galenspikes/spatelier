# Development Notes

This document tracks issues, features, notes, and takeaways from development work on Spatelier.

## Table of Contents
- [Homebrew Installation Issues & Fixes](#homebrew-installation-issues--fixes)
- [Key Takeaways](#key-takeaways)
- [GitHub Issues](#github-issues)
  - [Prioritized Roadmap](#prioritized-roadmap)
  - [Issue Details](#issue-details)
- [Known Issues](#known-issues)
- [Future Features](#future-features)
- [Architecture Decisions](#architecture-decisions)

---

## Homebrew Installation Issues & Fixes

### Issue: SHA256 Checksum Mismatch (v0.3.3)

**Problem:**
- Homebrew reported different checksum for downloaded tarball than what was in formula
- Local `git archive` produces different tarball than GitHub's release tarball

**Root Cause:**
- `git archive` generates tarball locally with different metadata/timestamps than GitHub
- Homebrew downloads from GitHub, so checksums must match GitHub's tarball

**Solution:**
- Updated release script to download actual GitHub tarball after tag is pushed
- Calculate SHA256 from GitHub-generated tarball, not local `git archive`
- Added retry logic for GitHub tarball availability

**Files Changed:**
- `scripts/release.sh` - Inlined SHA256 calculation with retry logic
- Removed `scripts/update_homebrew.sh` (functionality merged)

---

### Issue: Venv Python Not Found / Pip Missing (v0.3.5)

**Problem:**
- Homebrew installation failed silently during `pip install`
- Logs showed: `Failed to execute: $(brew --prefix)/Cellar/spatelier/0.3.4/libexec/bin/pip` (or `/usr/local/...` on Intel)
- The venv was created with `--without-pip`, so pip wasn't available

**Root Cause:**
- Homebrew's `virtualenv_create` uses `--without-pip` by default
- Attempted to use `venv.pip_install` but pip wasn't installed in venv

**Solution (Attempt 1 - Failed):**
- Changed to `venv.pip_install buildpath` and `bin.install_symlink`
- Still failed because pip wasn't in venv

**Solution (Attempt 2 - Failed):**
- Tried `system python3, "-m", "pip", "install", "--prefix", libexec, "pip", "setuptools", "wheel"`
- Syntax error: `--python` option must be placed before pip subcommand

**Solution (Attempt 3 - Failed):**
- Used `system libexec/"bin/python", "-m", "ensurepip", "--upgrade"`
- `ensurepip` found system pip (due to `--system-site-packages`) and didn't install into venv
- Missing `bin/pip` symlink in venv

**Final Solution (v0.3.8 - Working):**
- Use `get-pip.py` with `--isolated` flag to explicitly install pip into venv
- Ensures pip is properly installed with bin symlinks before package installation

**Files Changed:**
- `Formula/spatelier.rb` - Added `get-pip.py` installation step

---

### Issue: Invalid Pip Option (v0.3.6)

**Problem:**
- Error: `ERROR: The --python option must be placed before the pip subcommand name`

**Root Cause:**
- Incorrect syntax: `python3 -m pip install --python <path> pip setuptools wheel`
- `--python` is not a valid option for `pip install`

**Solution:**
- Changed to `--prefix` approach, but this also had issues
- Ultimately resolved by using `get-pip.py` approach

---

### Issue: ensurepip Finds System Pip (v0.3.7)

**Problem:**
- Installation still failed silently
- Pip log showed: `Requirement already satisfied: pip in $(brew --prefix)/lib/python3.12/site-packages`
- `ensurepip` found system pip and didn't install into venv
- Missing `bin/pip` symlink in venv

**Root Cause:**
- `virtualenv_create` uses `--system-site-packages` flag
- `ensurepip` sees system pip and skips installation into venv

**Solution:**
- Use `get-pip.py` with `--isolated` flag instead
- This explicitly installs pip into the venv, ignoring system packages

---

## Key Takeaways

### 1. SHA256 Checksum Calculation
- **Never use `git archive`** for Homebrew formula checksums
- **Always download from GitHub** after tag is pushed
- GitHub generates tarballs differently than local `git archive`
- Include retry logic for GitHub tarball availability

### 2. Homebrew `virtualenv_create` Behavior
- Uses `--without-pip` by default
- Uses `--system-site-packages` by default
- Pip is NOT automatically available in venv
- Must explicitly install pip before using it

### 3. `ensurepip` Limitation
- With `--system-site-packages`, `ensurepip` finds system pip
- Doesn't install pip into venv if system pip exists
- Use `get-pip.py` with `--isolated` for reliable venv pip installation

### 4. Homebrew Formula Pattern for Python Packages
```ruby
def install
  venv = virtualenv_create(libexec, "python3.12")
  # Install pip using get-pip.py (ensurepip finds system pip with --system-site-packages)
  system "curl", "-sSL", "https://bootstrap.pypa.io/get-pip.py", "-o", "/tmp/get-pip.py"
  system libexec/"bin/python", "/tmp/get-pip.py", "--isolated", "--disable-pip-version-check"
  system libexec/"bin/pip", "install", "-v", buildpath
  bin.install_symlink libexec/"bin/spatelier"
end
```

**Why this works:**
- `get-pip.py` installs pip into venv (not system)
- `--isolated` prevents using system packages
- `pip install buildpath` reads `pyproject.toml` and installs dependencies

### 5. Release Process
1. Tag and push FIRST (so GitHub generates tarball)
2. Wait a few seconds for GitHub to generate tarball
3. Download GitHub tarball and calculate SHA256
4. Update formula with correct SHA256
5. Commit and push formula update

### 6. Testing Homebrew Installations
- Use verbose flags: `HOMEBREW_VERBOSE=1 HOMEBREW_DEBUG=1 HOMEBREW_KEEP_TMP=1 brew install -v spatelier`
- Check logs: `~/Library/Logs/Homebrew/spatelier/`
- Look for silent failures in pip installation logs

### 7. No Workarounds Policy
- Fix root causes, not symptoms
- Understand why something fails before fixing
- Example: Using `get-pip.py` instead of working around `ensurepip` limitations

### 8. Version Consistency
Always update:
- `pyproject.toml` version
- `spatelier/__init__.py` `__version__`
- `CHANGELOG.md` with release notes
- `Formula/spatelier.rb` URL and SHA256

---

## GitHub Issues

**Summary:** 10 total issues as of 2026-01-23
- **✅ Completed:** 2 issues (#6, #10)
- **High Priority:** 4 issues (core functionality fixes)
- **Medium Priority:** 1 issue (configuration & platform support)
- **Low Priority:** 3 issues (enhancements)

### Prioritized Roadmap

#### ✅ Completed Issues
- **#10 - Use platform-appropriate temp directories in config defaults** ✅
  - **Status:** DONE - `get_default_data_dir()` in `core/config.py` uses platform-specific paths
  - **Implementation:** macOS uses `~/Library/Application Support/spatelier`, Linux uses `~/.local/share/spatelier`

- **#6 - Use browser cookies when fetching playlist metadata** ✅
  - **Status:** DONE - `PlaylistService._build_playlist_ydl_opts()` already uses `_get_cookies_from_browser()`
  - **Implementation:** Cookies are automatically used for playlist downloads via `cookies_from_browser` option

#### High Priority (Core Functionality Fixes) ✅ ALL COMPLETED

~~1. **#5 - Fix yt-dlp download file selection in VideoDownloadService** ⚠️~~ ✅ COMPLETED
   - **Why first:** Core download functionality may be broken
   - **Impact:** High - affects primary use case
   - **Complexity:** Medium
   - **Dependencies:** None
   - **Resolution:** Fixed in commit 8b0d383

~~2. **#8 - Fix playlist format selector for non-numeric quality values** ⚠️~~ ✅ COMPLETED
   - **Why second:** Playlist downloads may fail with certain quality settings
   - **Impact:** High - affects playlist functionality
   - **Complexity:** Low-Medium
   - **Dependencies:** None
   - **Resolution:** Fixed in commit 467436d

~~3. **#4 - Refactor cookie handling into shared CookieManager (browser-agnostic)** 🔧~~ ✅ COMPLETED
   - **Why third:** Enables other cookie-related fixes (#7)
   - **Impact:** High - reduces code duplication, enables better error handling
   - **Complexity:** Medium
   - **Dependencies:** None (but enables #7)
   - **Resolution:** Fixed in commit 5ce341f

~~4. **#7 - Centralize auth error detection + retry for yt-dlp flows** 🔧~~ ✅ COMPLETED
   - **Why fourth:** Improves reliability of downloads
   - **Impact:** High - better error handling and retry logic
   - **Complexity:** Medium
   - **Dependencies:** Benefits from #4 (CookieManager)
   - **Resolution:** Fixed in commit 16f2d8b

#### Medium Priority (Configuration & Platform Support)

~~6. **#9 - Decouple Whisper dependency detection for faster-whisper vs openai-whisper** 🔧~~ ✅ CLOSED (Won't Fix)
   - **Why sixth:** Code cleanup, reduces coupling
   - **Impact:** Medium - cleaner architecture
   - **Complexity:** Low-Medium
   - **Dependencies:** None
   - **Resolution:** Not needed - we only use faster-whisper (core dependency)

#### Low Priority (Enhancements - Nice to Have)

~~7. **#2 - Add official Homebrew tap for Spatelier** ✨~~ ✅ COMPLETED
   - **Why eighth:** User experience improvement (easier installation)
   - **Impact:** Low-Medium - convenience feature
   - **Complexity:** Low (formula already exists, just need separate repo)
   - **Dependencies:** None
   - **Resolution:** Tap repository already exists at https://github.com/galenspikes/homebrew-spatelier

~~8. **#1 - Support SQLite JSON/FTS5 as alternative to MongoDB for transcription storage** ✨~~ ✅ COMPLETED
   - **Why eighth:** Alternative database option
   - **Impact:** Medium - adds flexibility
   - **Complexity:** High - significant architecture change
   - **Dependencies:** None
   - **Resolution:** Implemented in v0.2.0. SQLite with JSON and FTS5 is the primary transcription storage implementation.

9. **#3 - Provide official Docker image for Spatelier** ✨
   - **Why ninth:** Containerization support
   - **Impact:** Low-Medium - niche use case
   - **Complexity:** Medium
   - **Dependencies:** None

### Issue Details

#### Enhancement Issues

#### #2 - Add official Homebrew tap for Spatelier
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/2
- **Last Updated:** ~7 days ago
- **Description:** Create an official Homebrew tap repository for easier installation (`brew install spatelier`)
- **Implementation:** Tap repository exists at https://github.com/galenspikes/homebrew-spatelier. Users can install with: `brew tap galenspikes/spatelier && brew install spatelier`

#### #3 - Provide official Docker image for Spatelier
- **Labels:** enhancement
- **Status:** Open
- **URL:** https://github.com/galenspikes/spatelier/issues/3
- **Last Updated:** ~7 days ago
- **Description:** Create and maintain an official Docker image for containerized deployments

#### #1 - Support SQLite JSON/FTS5 as alternative to MongoDB for transcription storage
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/1
- **Last Updated:** ~7 days ago
- **Description:** Add SQLite with JSON/FTS5 support as an alternative to MongoDB for transcription storage
- **Implementation:** SQLite transcription storage with JSON and FTS5 was implemented in v0.2.0. TranscriptionService uses SQLiteTranscriptionStorage exclusively. MongoDB is optional for other features but not used for transcriptions.

#### Bug Fixes / Improvements

#### #10 - Use platform-appropriate temp directories in config defaults ✅
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/10
- **Last Updated:** ~7 days ago
- **Description:** Update config defaults to use platform-appropriate temporary directories
- **Implementation:** `get_default_data_dir()` in `core/config.py` uses platform-specific paths (macOS: `~/Library/Application Support/spatelier`, Linux: `~/.local/share/spatelier`)

#### #9 - Decouple Whisper dependency detection for faster-whisper vs openai-whisper
- **Status:** CLOSED (Won't Fix - 2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/9
- **Last Updated:** ~7 days ago
- **Description:** Separate dependency detection logic for faster-whisper and openai-whisper
- **Resolution:** After analysis, the decoupling abstraction isn't needed since we only use faster-whisper (a core dependency). The current module-level try/except pattern is sufficient for our use case.

#### #8 - Fix playlist format selector for non-numeric quality values
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/8
- **Last Updated:** ~7 days ago
- **Description:** Fix format selector logic to handle non-numeric quality values in playlists
- **Implementation:** Fixed in commit 467436d. PlaylistService._get_format_selector() now correctly handles non-numeric quality values (e.g., '720p', '1080p') and includes robust fallback chains.

#### #7 - Centralize auth error detection + retry for yt-dlp flows
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/7
- **Last Updated:** ~7 days ago
- **Description:** Create centralized authentication error detection and retry logic for yt-dlp operations
- **Implementation:** Fixed in commit 16f2d8b. Created YtDlpAuthHandler class to centralize auth error detection and retry logic, removing duplication from VideoDownloadService and MetadataExtractor.

#### #6 - Use browser cookies when fetching playlist metadata ✅
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/6
- **Last Updated:** ~7 days ago
- **Description:** Implement browser cookie usage for fetching playlist metadata
- **Implementation:** `PlaylistService._build_playlist_ydl_opts()` already uses `_get_cookies_from_browser()` and sets `cookies_from_browser` in ydl_opts

#### #5 - Fix yt-dlp download file selection in VideoDownloadService
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/5
- **Last Updated:** ~7 days ago
- **Description:** Fix file selection logic in VideoDownloadService for yt-dlp downloads
- **Implementation:** Fixed in commit 8b0d383. Improved _resolve_downloaded_path() method with 3-tier fallback mechanism to accurately identify downloaded files, especially after yt-dlp's merging process.

#### #4 - Refactor cookie handling into shared CookieManager (browser-agnostic)
- **Status:** COMPLETED & CLOSED (2026-01-23)
- **URL:** https://github.com/galenspikes/spatelier/issues/4
- **Last Updated:** ~7 days ago
- **Description:** Create a shared CookieManager class that is browser-agnostic for better code reuse
- **Implementation:** Fixed in commit 5ce341f. Created CookieManager class with browser-agnostic cookie extraction, caching with expiration, and automatic cleanup. Eliminated duplication across VideoDownloadService, PlaylistService, and MetadataExtractor.

---

## Known Issues

### Shell Completion Disabled
- **Status:** Known, not critical
- **Location:** `cli/app.py` line 25: `add_completion=False`
- **Impact:** Tab completion doesn't work for `spatelier` commands
- **Fix:** Change to `add_completion=True` and document setup instructions
- **Priority:** Low

---

## Future Features

### Shell Completion
- Enable Typer shell completion
- Add setup instructions for zsh/bash
- Document completion command generation

### Additional Homebrew Improvements
- Create official Homebrew tap (see [GitHub Issue #2](#2---add-official-homebrew-tap-for-spatelier))
- Add formula validation in CI/CD
- Automate formula updates in release workflow

### Docker Support
- Provide official Docker image (see [GitHub Issue #3](#3---provide-official-docker-image-for-spatelier))

### Database Improvements
- Support SQLite JSON/FTS5 as alternative to MongoDB (see [GitHub Issue #1](#1---support-sqlite-jsonfts5-as-alternative-to-mongodb-for-transcription-storage))

---

## Architecture Decisions

### Why `get-pip.py` Instead of `ensurepip`?
- `ensurepip` is unreliable with `--system-site-packages`
- `get-pip.py` explicitly installs into venv
- More predictable and debuggable

### Why Download GitHub Tarball for SHA256?
- Homebrew downloads from GitHub, not local repo
- Must match exact tarball Homebrew will download
- `git archive` produces different checksums

### Why `--isolated` Flag for `get-pip.py`?
- Prevents using system packages
- Ensures pip is installed into venv, not system
- More reliable in Homebrew's sandboxed environment

---

## Release History

### v0.3.8 (2026-01-22)
- Fixed pip installation using `get-pip.py` with `--isolated` flag
- Homebrew installation now working correctly

### v0.3.7 (2026-01-22)
- Attempted fix using `ensurepip` (didn't work with `--system-site-packages`)

### v0.3.6 (2026-01-22)
- Attempted fix using `--prefix` approach (syntax errors)

### v0.3.5 (2026-01-22)
- Attempted fix using `venv.pip_install` (pip not in venv)

### v0.3.4 (2026-01-22)
- Fixed SHA256 calculation to use GitHub tarball
- Simplified release script

### v0.3.3 (2026-01-22)
- Initial Homebrew formula setup
- SHA256 checksum mismatch issues

---

## Notes

- All Homebrew-related fixes were iterative, learning from each failure
- Key insight: `virtualenv_create` doesn't include pip, and `ensurepip` doesn't work with `--system-site-packages`
- Final solution is clean and follows Homebrew best practices
- Release script now handles SHA256 calculation correctly with retry logic
