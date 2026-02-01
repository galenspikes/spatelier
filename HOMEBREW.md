# Homebrew Installation Guide

## Quick Start

### Option 1: Install Directly from Formula (No Separate Repo Needed!)

Users can install directly from your repo:

```bash
brew install --build-from-source https://raw.githubusercontent.com/galenspikes/spatelier/main/Formula/spatelier.rb
```

Or if they have the repo cloned:
```bash
brew install --build-from-source Formula/spatelier.rb
```

### Option 2: Create a Tap (Optional - For Easier Distribution)

If you want users to just run `brew install spatelier`, create a tap repo:

```bash
brew tap galenspikes/spatelier
brew install spatelier
```

Then just use:
```bash
spatelier --version
spatelier video download <url>
```

**No pip, no venv, no Python management - Homebrew handles everything internally.**

## How It Works

1. **Homebrew installs dependencies:**
   - Python 3.12 (via `depends_on "python@3.12"`)
   - ffmpeg (via `depends_on "ffmpeg"`)

2. **Homebrew creates internal virtualenv:**
   - You never see it
   - It's managed by Homebrew
   - No activation needed

3. **Homebrew installs your package:**
   - Runs `pip install` internally
   - Installs all dependencies from `pyproject.toml`
   - You never run pip yourself

4. **Homebrew installs the command:**
   - `spatelier` goes to `$(brew --prefix)/bin/spatelier` (e.g. `/opt/homebrew/bin` on Apple Silicon, `/usr/local/bin` on Intel)
   - Available system-wide
   - No PATH configuration needed

## Setup Steps

### Option A: Direct Installation (Simplest - No Separate Repo!)

1. **Create a GitHub release tag** (e.g., `v0.1.0`)
2. **Update the formula** with the release URL and SHA256
3. **Users install directly:**
   ```bash
   brew install --build-from-source https://raw.githubusercontent.com/galenspikes/spatelier/main/Formula/spatelier.rb
   ```

### Option B: Create a Tap (For `brew install spatelier`)

1. **Create a GitHub repository:** `homebrew-spatelier`
2. **Copy the formula** to that repo:
   ```
   homebrew-spatelier/
   └── Formula/
       └── spatelier.rb
   ```
3. **Create a release** in your main repo (e.g., `v0.1.0`)
4. **Update the formula** with the release URL and SHA256:
   ```ruby
   url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.1.0.tar.gz"
   sha256 "..." # Get from: shasum -a 256 <tarball>
   ```
5. **Users install:**
   ```bash
   brew tap galenspikes/spatelier
   brew install spatelier
   ```

## Testing Locally

```bash
# Test the formula locally (before creating tap)
brew install --build-from-source Formula/spatelier.rb

# Or test with HEAD (development version)
brew install --HEAD Formula/spatelier.rb
```

## Updating

When you release a new version:
1. Update the formula's `url` and `sha256`
2. Users run: `brew upgrade spatelier`

## Why ffmpeg?

`ffmpeg-python` is just a Python wrapper - it requires the actual `ffmpeg` binary to be installed. Your code uses:
- `ffmpeg.probe()` - for video metadata
- `ffmpeg.input()` / `ffmpeg.output()` - for video/audio conversion
- `ffmpeg.run()` - for subtitle embedding

So `ffmpeg` is a required system dependency, not optional.

## Advantages

✅ **No pip/venv management** - Homebrew handles it all
✅ **System-wide installation** - Works from anywhere
✅ **Easy updates** - `brew upgrade spatelier`
✅ **Clean uninstall** - `brew uninstall spatelier`
✅ **Dependency management** - Homebrew tracks all deps (Python, ffmpeg, etc.)

## Alternative: Standalone Executable

If you prefer a completely standalone binary (no Python needed):

1. Build with PyInstaller: `make build-executable`
2. Create a Homebrew formula that installs the binary
3. Users get a single executable file

This is more complex but gives you a true standalone tool.
