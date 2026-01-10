# Global Installation - Use Spatelier From Anywhere

You're absolutely right! The point is to install it once and use it from anywhere. Here are your options:

## Option 1: pipx (Recommended) ⭐

**pipx** installs Python CLI tools in isolated environments but makes them globally available. Perfect for this!

### Install pipx (one-time setup)
```bash
brew install pipx
pipx ensurepath  # Adds pipx to your PATH
```

### Install Spatelier globally
```bash
cd /Users/galenspikes/repos/spatelier
pipx install -e .
```

Now `spatelier` works from anywhere! 🎉

### Update Spatelier
```bash
pipx upgrade spatelier
```

## Option 2: Standalone Executable

Build a single executable file that works without Python:

### Build it
```bash
cd /Users/galenspikes/repos/spatelier
source venv/bin/activate  # Only needed for building
pip install pyinstaller
make build-executable
```

### Install globally
```bash
# Copy to a directory in your PATH
cp dist/spatelier ~/.local/bin/
# Or
sudo cp dist/spatelier /usr/local/bin/
```

Now `spatelier` works from anywhere!

## Option 3: User Installation (if pipx doesn't work)

```bash
cd /Users/galenspikes/repos/spatelier
python3 -m pip install --user -e .
```

This installs to `~/.local/bin/` - make sure that's in your PATH.

## Option 4: Publish to PyPI (Best for Distribution)

Once published, anyone can:
```bash
pip install spatelier
```

And it works globally!

## Recommendation

**Use pipx** - it's designed exactly for this use case:
- ✅ Isolated environment (no conflicts)
- ✅ Global command availability
- ✅ Easy updates
- ✅ No venv management needed

## Quick Setup with pipx

```bash
# 1. Install pipx (one time)
brew install pipx
pipx ensurepath

# 2. Install Spatelier
cd /Users/galenspikes/repos/spatelier
pipx install -e .

# 3. Use it anywhere!
spatelier --version
```

That's it! No more venv activation needed.
