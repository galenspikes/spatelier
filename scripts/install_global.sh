#!/bin/bash
# Install Spatelier globally using pipx
# This makes the 'spatelier' command available from anywhere

set -e

echo "🌍 Installing Spatelier globally with pipx..."

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "❌ pipx is not installed"
    echo ""
    echo "Install it with:"
    echo "  brew install pipx"
    echo "  pipx ensurepath"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Get the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "✅ Found project at: $PROJECT_ROOT"
echo "📦 Installing with pipx..."

# Install with pipx
pipx install -e "$PROJECT_ROOT"

echo ""
echo "✅ Installation complete!"
echo ""
echo "You can now use 'spatelier' from anywhere:"
echo "  spatelier --version"
echo "  spatelier --help"
echo ""
echo "To update in the future:"
echo "  pipx upgrade spatelier"
