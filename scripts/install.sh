#!/bin/bash
# Install Spatelier in the current environment
# Usage: source venv/bin/activate && bash scripts/install.sh

set -e

echo "📦 Installing Spatelier..."

# Check if we're in a venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment!"
    echo "   Run: source venv/bin/activate"
    echo "   Then run this script again"
    exit 1
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo "✅ Python: $(python --version)"

# Install in development mode
echo "📥 Installing package..."
pip install -e .

# Install build tools if needed
if [ "$1" == "--with-build" ]; then
    echo "📦 Installing build tools..."
    pip install build twine
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Test it:"
echo "  spatelier --version"
echo "  spatelier --help"
