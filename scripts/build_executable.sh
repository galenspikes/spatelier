#!/bin/bash
# Build standalone executable using PyInstaller
# Creates a single-file executable that includes Python and all dependencies

set -e

echo "🔨 Building standalone executable..."

# Install PyInstaller if not already installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "📥 Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Build executable
echo "🔨 Building executable..."
pyinstaller \
    --onefile \
    --name spatelier \
    --add-data "cli:cli" \
    --add-data "core:core" \
    --add-data "modules:modules" \
    --add-data "database:database" \
    --add-data "analytics:analytics" \
    --add-data "utils:utils" \
    --hidden-import="cli.app" \
    --hidden-import="typer" \
    --hidden-import="rich" \
    --console \
    cli/app.py

echo "✅ Executable built!"
echo ""
echo "📦 Executable location: dist/spatelier"
echo "   (or dist/spatelier.exe on Windows)"
echo ""
echo "📏 File size:"
ls -lh dist/spatelier* 2>/dev/null || ls -lh dist/spatelier.exe 2>/dev/null || echo "   (check dist/ directory)"
