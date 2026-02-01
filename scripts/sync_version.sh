#!/bin/bash
# Sync __version__ in spatelier/__init__.py and __init__.py from pyproject.toml.
# Single source of truth: pyproject.toml. Run this after bumping version there.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ -z "$VERSION" ]; then
    echo "Error: Could not find version in pyproject.toml"
    exit 1
fi

for file in spatelier/__init__.py __init__.py; do
    if [ -f "$file" ]; then
        if sed -i.bak "s/^__version__ = .*/__version__ = \"${VERSION}\"/" "$file" 2>/dev/null || \
           sed -i '' "s/^__version__ = .*/__version__ = \"${VERSION}\"/" "$file"; then
            rm -f "${file}.bak" 2>/dev/null || true
            echo "Updated $file -> __version__ = \"${VERSION}\""
        fi
    fi
done

echo "Version ${VERSION} synced. Commit and run release when ready."
