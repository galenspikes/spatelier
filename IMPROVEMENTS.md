# Spatelier Improvements & Recommendations

## Executive Summary

Spatelier is a well-architected project with clear separation of concerns (DDD, clean architecture). However, it has inherited the complexity of youtube-dl while attempting to simplify the UX. There are three critical areas to address:

1. **Default output location is unintuitive** — saves to `~/.local/share/spatelier/downloads` by default, not the current directory
2. **CLI has too many options** — trying to be a Swiss Army knife rather than a focused tool
3. **Configuration is cumbersome** — changes require YAML files; per-session options scattered across commands

---

## 1. Default Output Location: The Core Problem

### Current Behavior

When running `spatelier video download <url>` without `--output`:
- Files are saved to either:
  - Config: `config.video.output_dir` (if set)
  - Default: `~/.local/share/spatelier/downloads` (installed) or `./.data/downloads` (dev)

### Why This Is Bad

1. **Breaks user expectations** — most CLI tools save to current directory (like `curl`, `wget`, `ffmpeg`)
2. **Requires repeated `--output` flags** — `spatelier video download <url> --output ./videos` every time
3. **Hidden outputs** — users don't know where files went
4. **Violates principle of least surprise** — goes against Unix conventions

### The Fix: Smart Output Defaults

**Priority:** HIGH — implement for v0.5.0

```python
# spatelier/core/config.py
def get_output_dir_smart(explicit_path: Optional[Path], config: Config) -> Path:
    """
    Determine output directory with sensible defaults.
    
    Priority (highest to lowest):
    1. Explicit --output flag (user intent)
    2. SPATELIER_OUTPUT env var (session override)
    3. Current working directory (default, follows Unix conventions)
    4. Config file setting (persistent override)
    """
    if explicit_path:
        return explicit_path
    
    if env_output := os.getenv("SPATELIER_OUTPUT"):
        return Path(env_output)
    
    # Default: current directory (THE FIX)
    # Remove fallback to ~/.local/share/spatelier/downloads
    return Path.cwd()
```

**Implementation steps:**

1. Update `VideoDownloadService.download_video()`:
```python
# Before
output_dir = self.config.video.output_dir or (repo_root / "downloads")

# After
output_dir = self.config.video.output_dir or Path.cwd()
```

2. Update `AudioConverter.convert()` similarly

3. Update CLI help text to be explicit:
```python
@app.command()
def download(
    url: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory or file (default: current directory)"
    ),
```

4. Add environment variable support documentation:
```bash
# Instead of changing config file, users can do:
export SPATELIER_OUTPUT=~/Videos
spatelier video download <url>
```

5. Show where file was saved in output:
```python
# Print message like:
# ✓ Downloaded to: /home/user/Downloads/video.mp4
# (or relative path if in cwd)
```

### Migration Path

- Add deprecation warning in v0.4.3: "Default output location will change to current directory in v0.5.0"
- In v0.5.0: Change default to `Path.cwd()`
- Keep config file setting as explicit override for power users

---

## 2. CLI Option Bloat: Too Many Flags

### Current State

The CLI has grown to resemble youtube-dl with scattered options:

```bash
spatelier video download <url>
  --output <path>
  --quality <quality>
  --format <format>
  --max-videos <int>
  --transcribe/--no-transcribe
  --verbose
```

Plus many more in other commands. This is the exact problem you were trying to solve!

### The Problem

1. **Options paralysis** — users don't know which flags they need
2. **Not discoverable** — `--help` is huge, hard to find what's relevant
3. **Duplicates interactive mode** — why have both CLI and `interactive` mode?
4. **Poor defaults** — forcing users to know about `--max-videos`, quality names, etc.

### The Solution: Workflow-Driven CLI

**Priority:** HIGH (long-term)

**Principle:** Make the common case trivial, advanced options discoverable.

#### Option 1: Subcommand Reorganization (Recommended)

```bash
# Simple commands (for 90% of users)
spatelier download <url>              # downloads video, saves to cwd
spatelier download-audio <url>        # extracts audio, saves to cwd
spatelier transcribe <video>          # transcribes video, embeds subs

# Batch operations
spatelier batch download <file>       # reads URLs from file
spatelier batch process <file>        # batch download + transcribe

# Power user mode (grouped options)
spatelier download <url> \
  --advanced \                        # flag to show all options
  --quality 1080p \
  --format webm
```

**Benefits:**
- Simple commands have no options (just arguments)
- Advanced options gated behind `--advanced` flag
- Organized by workflow, not by feature

#### Option 2: Profile System

```bash
# Create profiles for different use cases
spatelier profile create podcast \
  --transcribe \
  --quality 360p \
  --format mp4 \
  --output ~/podcasts

# Use profile
spatelier download <url> --profile podcast

# Or switch profiles
export SPATELIER_PROFILE=podcast
spatelier download <url>
```

#### Option 3: Config-First Approach

```bash
# Instead of CLI flags, users set config once:
spatelier config set video.quality 720p
spatelier config set video.transcribe-by-default true
spatelier config set output ~/Videos

# Then simple commands work as expected
spatelier download <url>
```

### Immediate Quick Wins

1. **Reduce default options** — remove `--quality`, `--format`, `--max-videos` from top-level commands; move to `--advanced`

2. **Add sensible defaults**:
   - Quality: "best" ✓ (already done)
   - Format: inferred from source or "mp4"
   - Transcribe: false (let users opt-in)

3. **Create focused commands**:
```bash
# Instead of: spatelier video download-enhanced <url> --transcribe
# New: spatelier download-transcribe <url>

# Instead of: spatelier video download-playlist <url> --max-videos 100
# New: spatelier download-playlist <url> --limit 100
```

---

## 3. Configuration Management: Too Much Manual Work

### Current Complexity

Users need to:
1. Find config file: `~/.local/share/spatelier/config.yaml`
2. Edit YAML by hand
3. Restart sessions for changes to take effect

### Improvements

#### A. Config GUI (Medium-term)

```bash
spatelier config edit              # Opens interactive editor
spatelier config show              # Displays current config
spatelier config reset             # Resets to defaults
```

#### B. Environment Variables (Quick Win)

```bash
# Support more env vars for per-session overrides
export SPATELIER_OUTPUT=~/Videos
export SPATELIER_QUALITY=720p
export SPATELIER_TRANSCRIBE=true
export SPATELIER_FORMAT=mkv

spatelier download <url>
```

#### C. Per-Command Config Files (Low Priority)

```bash
# Create .spatelier in project root for directory-specific settings
# ~~/Videos/.spatelier (YAML):
# output_dir: .
# transcribe: true
# quality: 720p

# This way, cd ~/Videos && spatelier download <url> uses those settings
```

---

## 4. Architecture & Code Quality Improvements

### 4.1 Remove Redundant CLI Subcommands

**Current:**
```
video/
  ├── download
  ├── download-enhanced (same as download + --transcribe)
  ├── download-playlist
  ├── embed-subtitles
  ├── convert
  ├── info
```

**Proposed:**
```
video/
  ├── download <url>             # single, works for all types
  ├── transcribe <video>         # embeds subtitles
  ├── convert <input> <output>   # optional --format
  ├── info <video>
```

**Reasoning:**
- `download` already detects channels, playlists, etc.
- Transcription can be an option: `--transcribe` or separate `transcribe` command
- Fewer commands = easier to learn

### 4.2 Simplify ServiceFactory

The service factory is powerful but has grown complex:

```python
# Current: 
with ServiceFactory(config, verbose=verbose) as services:
    services.download_video_use_case.execute(url, output_path, ...)

# Proposed simplified interface:
with Spatelier(config) as app:
    app.download_video(url, output)
```

This is a facade that reduces cognitive load.

### 4.3 Decouple CLI from Business Logic

Move validation and path handling out of CLI commands:

```python
# BAD (current):
@app.command()
def download(
    url: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(...),
    quality: str = typer.Option(...),
    ...
):
    # Too much responsibility
    config = Config()
    validate_url(url)
    resolve_output_path(output)
    ...
    services.execute()

# GOOD (proposed):
@app.command()
def download(
    url: str = typer.Argument(...),
    output: Optional[Path] = typer.Option(None, help="Output directory"),
):
    result = app_service.download(url, output)
    display_result(result)
```

### 4.4 Better Error Messages

Current: Generic error messages don't help users

```python
# Current:
"Download failed"

# Proposed:
"Download failed: YouTube video is unavailable (403 Forbidden)
 
 Possible solutions:
 1. Video may be geo-restricted — try a VPN
 2. Video may be age-restricted — log in with --auth-user
 3. Video may be private — check link
 
 Debug: Run with --verbose for details"
```

---

## 5. Interactive Mode Needs Rethink

### Current State
- Interactive mode exists but isn't discoverable
- Most users use CLI commands instead
- Duplicates logic between interactive and command modes

### Proposal: TUI-First Approach

Create a proper TUI (Text User Interface) with menus:

```bash
spatelier             # Launches TUI (instead of --help)
spatelier --cli      # Force CLI mode
```

TUI Features:
- Menu-driven workflow
- Show what you're about to do
- Cancel/confirm before executing
- Real-time progress with rich output

---

## 6. Database & Analytics: Clarify Purpose

### Issues

1. **SQLite** — good for metadata, but why separate from file system?
2. **Analytics** — optional but doesn't add much value for most users
3. **MongoDB** — confusing optional dependency

### Recommendations

1. **SQLite:** Keep it, but make it optional
   - Primary use: tracking downloads (avoid re-downloading duplicates)
   - Secondary: generating reports

2. **Analytics:** 
   - Consider moving to separate tool (`spatelier analytics`)
   - Or remove if not heavily used

3. **MongoDB:**
   - Remove or create separate project (`spatelier-mongo`)
   - SQLite is simpler default

---

## 7. Transcription Workflow Issues

### Current Problem

```bash
# To get transcription, users must:
spatelier video download-enhanced <url>

# Or:
spatelier video download <url> --transcribe
spatelier transcribe <file>
spatelier embed-subtitles <file> <subs>
```

This is confusing and multi-step.

### Proposed Solution

```bash
# Simple: download video
spatelier download <url>

# Simple: transcribe (auto-embed)
spatelier transcribe <video>

# Power user: transcribe with options
spatelier transcribe <video> --model large --language es --format srt
```

**Key:** Transcription should be a separate step, not bundled into download.

---

## 8. Package Distribution & Installation

### Current Issue

Users must install via Homebrew, pipx, or PyPI. Unclear which method to use.

### Recommendation

**Simplify:** Official distribution should be:
1. **Homebrew** (macOS/Linux) — zero Python knowledge
2. **PyPI** with pipx — Linux/cross-platform

Remove:
- Docker (unless specifically requested)
- Standalone executables (too many release assets)

Focus on **Homebrew** as primary macOS/Linux distribution.

---

## 9. Documentation Improvements

### Add

1. **Troubleshooting Guide**
   - "Download is slow" → check quality, use `--quality 360p`
   - "Auth required" → use `--auth-user` or follow cookie setup
   - "File not found" → explain where files are saved

2. **Configuration Examples**
   ```yaml
   # Setup once, forget about it
   video:
     output_dir: ~/Downloads/Videos
     quality: 720p
     format: mp4
   
   audio:
     output_dir: ~/Music
     format: mp3
     bitrate: 320
   ```

3. **Quick Start Guide**
   - "Download a video in 10 seconds"
   - "Extract audio from YouTube in one command"

---

## 10. Testing & Quality

### Current Status
Good: Comprehensive test suite exists

### Improvements

1. **Add end-to-end tests** with real YouTube URLs (gated, optional)
2. **Performance benchmarks** — track download speeds
3. **CLI integration tests** — test actual commands
4. **User flow testing** — simulate real workflows

---

## Confirmed Bugs from Smoke Testing

The following bugs were confirmed by actually running the app. See [SMOKE_TEST.md](SMOKE_TEST.md) for full details.

| # | Bug | File | Effort |
|---|-----|------|--------|
| 1 | INFO logs printed to stderr on every command (no `--verbose` needed) | `core/logger.py:36` | 1 line |
| 2 | `worker list-jobs` defaults to JSON output, not table | `cli/worker.py:274` | 1 line |
| 3 | YouTube metadata fetched twice per download (double network call) | `download_video_use_case.py:78` + `download_service.py:94` | 30 min |
| 4 | Download error message is generic (`"Video download failed"`) with no actionable info | `download_service.py` | ~10 lines |
| 5 | `storage_adapter.move_file()` creates directories unconditionally before checking source exists | `storage/storage_adapter.py:192` | 5 lines |
| 6 | `pytest` binary fails with import error; only `python -m pytest` works | `pytest.ini` | 1 line |

---

## Implementation Roadmap

### v0.4.3 (Quick Bugs, ~1-2 days)
- [ ] Fix INFO log bleeding (Bug 1) — `core/logger.py:36`
- [ ] Fix `worker list-jobs` default format (Bug 2) — `cli/worker.py:274`
- [ ] Fix `storage_adapter.move_file()` directory creation (Bug 5) — `storage/storage_adapter.py`
- [ ] Fix `pytest` path resolution (Bug 6) — `pytest.ini`

### v0.5.0 (High Impact UX, ~1-2 weeks)
- [ ] Fix default output location → current directory (`download_service.py:106`)
- [ ] Fix generic error messages (Bug 4) — surface yt-dlp errors to user
- [ ] Fix double metadata extraction (Bug 3)
- [ ] Add environment variable support (`SPATELIER_OUTPUT`, `SPATELIER_QUALITY`)

### v0.6.0 (Medium Impact, ~4-6 weeks)
- [ ] Remove redundant download commands (`download-enhanced`, `download-playlist`)
- [ ] Config editing UI (`spatelier config set`)
- [ ] Profile system
- [ ] Simplify ServiceFactory
- [ ] Better transcription workflow (separate step, not bundled into download)

### v0.7.0+ (Future)
- [ ] TUI mode
- [ ] Better analytics
- [ ] Plugin system (if needed)

---

## Summary Table

| Issue | Severity | Fix | Effort | Impact |
|-------|----------|-----|--------|--------|
| Default output not in cwd | 🔴 HIGH | Change default to `Path.cwd()` | 1 day | Critical UX improvement |
| INFO logs on every command | 🔴 HIGH | Default logger to WARNING | 1 line | Every user sees this |
| Generic download errors | 🔴 HIGH | Surface yt-dlp error to user | 10 lines | Usability |
| Too many CLI options | 🟠 MEDIUM | Reorganize commands, gate advanced options | 1 week | Cleaner interface |
| Config is hard to change | 🟠 MEDIUM | Add `spatelier config set` command | 2 days | Better UX |
| Redundant commands | 🟠 MEDIUM | Merge `download-*` into single `download` | 1 day | Less confusion |
| Double metadata fetch | 🟠 MEDIUM | Pass metadata through, don't re-fetch | 30 min | 2x faster startup |
| move_file creates dirs blindly | 🟠 MEDIUM | Check source exists first | 5 lines | Correctness |
| ServiceFactory complex | 🟡 LOW | Create `Spatelier` facade | 2-3 days | Cleaner code |
| pytest binary broken | 🟡 LOW | Add `pythonpath = .` to pytest.ini | 1 line | Dev ergonomics |

---

## Key Takeaway

**Spatelier has excellent architecture but tries to do too much.** Focus on:

1. **Respecting Unix conventions** (output to cwd)
2. **Sensible defaults** (transcription is opt-in, not default)
3. **Simple workflows** (one command per task)
4. **Clear configuration** (ENV vars + config file, not scattered options)

These changes will make Spatelier **actually simpler than youtube-dl**, not just a prettier version of it.
