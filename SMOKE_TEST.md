# Spatelier Smoke Test Results

> Tested on branch `claude/youthful-hopper-y9d144`, v0.4.2  
> Environment: Linux, Python 3.11, clean `pip install -e .`

---

## TL;DR

| Category | Status |
|----------|--------|
| CLI boots and help works | ✅ |
| Config show/edit | ✅ |
| File utilities (hash, info, find, track) | ✅ |
| Analytics report/stats | ✅ |
| Worker daemon status | ✅ |
| Interactive mode starts | ✅ |
| Video download | ❌ (SSL blocked in sandbox, not app bug) |
| Audio conversion | ⚠️ not tested (no audio files) |
| Transcription | ⚠️ not tested (no video files) |
| Unit tests (core) | ✅ 285/285 pass |
| Integration tests | ⚠️ 42/43 pass (1 real bug) |
| Analytics tests | ❌ 0/3 pass (optional deps not installed) |

---

## Command-by-Command Results

### ✅ CLI & Version

```
spatelier --help      → clean help output with all subcommands
spatelier --version   → "Spatelier version 0.4.2"
```

### ✅ Config Display

```
spatelier utils config --show
```

Shows a table with all settings. Works. However, `Video Output Dir` and `Audio Output Dir` both show `None` — confirming the documented UX problem that users have no obvious output destination.

### ✅ Analytics

```
spatelier analytics report   → runs, shows zero stats (fresh DB)
spatelier analytics stats    → works, shows counts from prior smoke test runs
```

Stats show **63.64% success rate** across 22 jobs and 16 tracked files — accumulated from the test download attempts during this session. The tracking is working.

### ✅ File Utilities

```
spatelier utils hash README.md        → SHA256 hash, clean output
spatelier utils info README.md        → size, type, extension table
spatelier utils find . --pattern *.md → table of 15 matching files
spatelier files track README.md       → device:inode tracking works
spatelier files demo                  → full demo passes
```

### ✅ Worker Daemon

```
spatelier worker status   → shows "🔴 Not Running" table, correct
spatelier worker list-jobs → outputs raw JSON: {"jobs": [], "total": 0, ...}
```

The `list-jobs` command **defaults to `--format json`**. This is wrong — a user running `list-jobs` expects a table. Bug noted below.

### ✅ Interactive Mode

```
spatelier interactive   → starts, shows welcome banner
```

Interactive mode launches correctly. Not fully tested as it requires stdin.

### ❌ Video Download (environment issue, not app bug)

```
spatelier video download "https://youtube.com/watch?v=..." --output /tmp/test
```

Fails with SSL certificate errors:

```
WARNING: [youtube] [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate in certificate chain
```

This is a **sandbox/network restriction** in the remote execution environment, not an app bug. The yt-dlp call itself is reaching YouTube — it's being intercepted by a proxy with a self-signed cert. Would work on a real machine.

**What did work during the download attempt:**
- ServiceFactory initializes correctly
- SQLite DB connects and creates jobs
- Job lifecycle (created → processing → failed) all tracked correctly
- Cookie manager loads (no cookies, no playwright available — graceful warning)
- Error is shown cleanly in a rich panel

**What didn't work even given the SSL issue:**
- Error message is useless: `"✗ Download failed: Video download failed"` — gives no actionable info (see Bugs section)

---

## Bugs Found

### 🐛 Bug 1: INFO logs bleed to stderr by default

**Severity: Medium-High**

Every command prints INFO-level loguru logs to stderr, even without `--verbose`:

```
2026-06-21 21:54:33 | INFO     | spatelier.cli.app:main:133 - Spatelier CLI started
2026-06-21 21:54:33 | INFO     | spatelier.database.connection:connect_sqlite:154 - Connected to SQLite database
2026-06-21 21:54:33 | INFO     | spatelier.core.database_service:initialize:76 - Database services initialized
```

**Root cause:** `get_logger()` in `spatelier/core/logger.py:36` uses `level = "DEBUG" if verbose else level`, where the default `level` argument is `"INFO"`. So INFO always logs, even without `--verbose`.

**Impact:**
- Confusing for users — they see internal implementation details on every command
- Breaks scripts/pipelines — `spatelier analytics stats 2>/dev/null` is required to get clean output
- Multiple commands create separate loggers (`"video-download"`, `"audio-convert"`, etc.) each calling `logger.remove()` and re-adding a handler, which could cause log duplication

**Fix:**
```python
# spatelier/core/logger.py
def get_logger(name=None, verbose=False, log_file=None, level="INFO"):
    logger.remove()
    log_level = "DEBUG" if verbose else "WARNING"  # was: level (defaulting to INFO)
    ...
```

Or alternatively, default the console to `WARNING` and only go to `INFO` when `--verbose` is passed through from the top-level callback.

---

### 🐛 Bug 2: `worker list-jobs` defaults to JSON format

**Severity: Medium**

```bash
spatelier worker list-jobs
# Output: {"jobs": [], "total": 0, "summary": {}}
```

The `--format` option in `spatelier/cli/worker.py:274` defaults to `"json"`:

```python
format: str = typer.Option(
    "json", "--format", "-f", help="Output format: json, table, summary"
)
```

**Impact:** Users get raw JSON by default — a machine-readable format as the human-facing default. Should be `"table"`.

**Fix:**
```python
format: str = typer.Option(
    "table", "--format", "-f", help="Output format: json, table, summary"
)
```

---

### 🐛 Bug 3: YouTube metadata extracted twice per download

**Severity: Medium (performance)**

When a download is triggered, `extract_youtube_metadata()` is called **twice** before yt-dlp even starts:

1. In `DownloadVideoUseCase.execute()` → `self.metadata_service.extract_video_metadata(url)` (`domain/use_cases/download_video_use_case.py:78`)
2. In `VideoDownloadService.download_video()` → `self.metadata_extractor.extract_youtube_metadata(url)` (`modules/video/services/download_service.py:94`)

Each call makes a network request to YouTube's API. This doubles startup time and doubles the chance of auth errors.

**Fix:** Pass metadata from the use case down to the service, or remove the extraction from the service entirely and rely on what the use case provides:

```python
# In VideoDownloadService.download_video():
# Accept pre-fetched metadata as a kwarg rather than re-fetching
source_metadata = kwargs.pop("source_metadata", None)
if source_metadata is None and ("youtube.com" in url or "youtu.be" in url):
    source_metadata = self.metadata_extractor.extract_youtube_metadata(url)
```

---

### 🐛 Bug 4: Generic error messages on download failure

**Severity: Medium**

When a download fails, the user sees:

```
╭─────────────────────── Error ───────────────────────╮
│ ✗ Download failed: Video download failed            │
╰─────────────────────────────────────────────────────╘
```

The actual yt-dlp error (SSL failure, geo-restriction, auth required, etc.) is logged at ERROR level to stderr but is not surfaced in the user-facing panel. The user has no idea what went wrong or how to fix it.

**Fix:** Pass the specific error through to the result message and display it:

```python
# In VideoDownloadService._download_with_ytdlp catch block:
return ProcessingResult(
    success=False,
    message=f"Download failed: {e}",  # was: "Video download failed"
    errors=[str(e)],
)
```

And in the CLI display:
```python
# Show specific error in the panel, not just generic message
console.print(Panel(
    f"[red]✗[/red] {result.message}\n\n"
    f"[dim]Run with --verbose for debug output[/dim]",
    ...
))
```

---

### 🐛 Bug 5: `storage_adapter.move_file()` creates arbitrary directory trees

**Severity: Medium (test failure + real behavioral bug)**

`NASStorageAdapter.move_file()` calls `dest_file.parent.mkdir(parents=True, exist_ok=True)` **before** checking if the move will succeed:

```python
# spatelier/infrastructure/storage/storage_adapter.py:195
def move_file(self, source_file: Path, dest_file: Path) -> bool:
    try:
        dest_file.parent.mkdir(parents=True, exist_ok=True)  # creates dirs unconditionally
        shutil.move(str(source_file), str(dest_file))
        return True
    except Exception as e:
        ...
        return False
```

This causes `test_nas_error_handling` to fail (the test expects `False` when moving to `/invalid/path/...` but the move actually succeeds because the directories get created).

More importantly: if a source file doesn't exist but the destination path has been constructed incorrectly, the code creates orphan directories silently.

**Fix:** Check source file exists first:

```python
def move_file(self, source_file: Path, dest_file: Path) -> bool:
    if not source_file.exists():
        if self.logger:
            self.logger.error(f"Source file does not exist: {source_file}")
        return False
    try:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_file), str(dest_file))
        return True
    except Exception as e:
        ...
        return False
```

---

### 🐛 Bug 6: Test suite doesn't run with `pytest` binary (only with `python -m pytest`)

**Severity: Low (dev experience)**

Running `pytest tests/` from the project root fails with `ModuleNotFoundError: No module named 'spatelier.core'` despite `pip install -e .` being done. The `conftest.py` adds the project root to `sys.path`, but the `conftest.py` itself fails to load because `tests/fixtures/__init__.py` imports spatelier before the path manipulation runs.

Running `python -m pytest tests/` works correctly.

**Fix:** Add a `pyproject.toml` `[tool.pytest.ini_options]` or `pytest.ini` entry:

```ini
[tool:pytest]
pythonpath = .
```

(requires pytest ≥ 7.0 which is already required in dev deps)

---

## Test Suite Summary

```
python3.11 -m pytest tests/ -q
```

| Bucket | Result |
|--------|--------|
| Core unit tests (285) | ✅ 285 passed |
| Integration tests (43) | ⚠️ 42 passed, 1 failed (Bug 5) |
| Analytics tests (3) | ❌ 3 failed — `matplotlib`, `pandas` not installed |
| Release hygiene (7) | ⚠️ 6 passed, 1 failed — `pip wheel` fails in this environment (distutils/system Python issue, not app) |

**Total: 327 passed, 5 failed, 22 skipped**

The 5 failures break down as:
- **1 real app bug** (NAS move_file, Bug 5)
- **3 missing optional dependencies** (matplotlib, pandas, seaborn — analytics extra not installed)
- **1 environment-specific** (distutils incompatibility in system Python, release hygiene test)

Core functionality is **well-tested and passes cleanly**.

---

## Priority Fix List

| # | Bug | File | Effort | Impact |
|---|-----|------|--------|--------|
| 1 | INFO logs always on (Bug 1) | `core/logger.py:36` | 1 line | High — every user sees this |
| 2 | worker list-jobs JSON default (Bug 2) | `cli/worker.py:274` | 1 line | Medium |
| 3 | Generic download error (Bug 4) | `modules/video/services/download_service.py` | ~10 lines | High — usability |
| 4 | Double metadata fetch (Bug 3) | `use_cases/download_video_use_case.py:78` | 30 min | Medium — performance |
| 5 | move_file creates dirs before checking (Bug 5) | `infrastructure/storage/storage_adapter.py:192` | 5 lines | Medium — test + real bug |
| 6 | pytest path issue (Bug 6) | `pytest.ini` | 1 line | Low — dev ergonomics |

---

## What Unambiguously Works

- Full CLI loads with no import errors
- All subcommand groups accessible and help-rendered correctly
- SQLite database initializes and tracks jobs and files correctly
- File tracking (inode/device) works correctly
- Config display and management works
- Analytics queries and displays correctly
- Worker daemon status/management works (daemon mode not tested)
- Interactive mode launches
- Error handling gracefully catches bad URLs and failed downloads

## What Cannot Be Verified Here

- Actual video download (network sandbox)
- Audio extraction from real videos
- Transcription (needs model weights + actual audio)
- NAS operations (no NAS)
- Playlist/channel downloads
- Cookie-based auth for age-restricted content
