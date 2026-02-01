#!/bin/bash
# Development setup script for Spatelier

set -e

echo "🚀 Setting up Spatelier development environment..."

# Check if Python 3.9+ is available
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.9+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
# IMPORTANT: Use Homebrew Python to avoid dependency issues with pyenv Python
# pyenv Python can break when Homebrew is updated/reinstalled because it links
# against Homebrew libraries (like gettext) that may be removed or moved.
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    HOMEBREW_PREFIX="${HOMEBREW_PREFIX:-$(brew --prefix 2>/dev/null)}"
    if [ -n "$HOMEBREW_PREFIX" ] && [ -f "${HOMEBREW_PREFIX}/opt/python@3.12/bin/python3.12" ]; then
        echo "   ✓ Using Homebrew Python 3.12 (recommended - more stable)"
        "${HOMEBREW_PREFIX}/opt/python@3.12/bin/python3.12" -m venv venv
    elif command -v python3.12 &> /dev/null; then
        PYTHON_PATH=$(which python3.12)
        if [[ "$PYTHON_PATH" == *".pyenv"* ]]; then
            echo "   ⚠️  WARNING: Detected pyenv Python. This can break when Homebrew is updated."
            echo "   Consider using Homebrew Python instead: brew install python@3.12"
            read -p "   Continue with pyenv Python? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
        echo "   Using system Python 3.12"
        python3.12 -m venv venv
    else
        echo "   Using system Python 3"
        python3 -m venv venv
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install the package in development mode
echo "📥 Installing Spatelier in development mode..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Run basic tests
echo "🧪 Running basic tests..."
python -m pytest tests/test_basic.py -v

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run tests: make test"
echo "3. Format code: make format"
echo "4. Run linting: make lint"
echo "5. Try the CLI: spatelier --help"
echo ""
echo "Happy coding! 🎵🎬"
