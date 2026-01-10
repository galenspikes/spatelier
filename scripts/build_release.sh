#!/bin/bash
# Build release packages for Spatelier
# Creates wheel, source distribution, and optionally standalone executables

set -e

echo "🔨 Building Spatelier release packages..."

# Get version from __init__.py
VERSION=$(python -c "from __init__ import __version__; print(__version__)")
echo "📦 Version: $VERSION"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Install build tools
echo "📥 Installing build tools..."
pip install --upgrade build twine

# Build Python packages (wheel + source)
echo "🔨 Building Python packages..."
python -m build

echo "✅ Build complete!"
echo ""
echo "📦 Distribution packages created in dist/:"
ls -lh dist/
echo ""
echo "📤 To upload to PyPI:"
echo "   python -m twine upload dist/*"
echo ""
echo "🧪 To test upload to TestPyPI first:"
echo "   python -m twine upload --repository testpypi dist/*"
