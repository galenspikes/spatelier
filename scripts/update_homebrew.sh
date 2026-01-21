#!/bin/bash
# Update Homebrew formula with new release SHA256

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ -z "$1" ]; then
    echo -e "${RED}Error: Tag required${NC}"
    echo "Usage: $0 <tag>"
    echo "Example: $0 v0.1.0"
    exit 1
fi

TAG="$1"
VERSION="${TAG#v}"  # Remove 'v' prefix
URL="https://github.com/galenspikes/spatelier/archive/refs/tags/${TAG}.tar.gz"
FORMULA_FILE="Formula/spatelier.rb"

echo -e "${GREEN}🔍 Getting SHA256 for ${TAG}...${NC}"

# Download tarball and calculate SHA256
TEMP_FILE=$(mktemp)
curl -L -s -o "$TEMP_FILE" "$URL"
SHA256=$(shasum -a 256 "$TEMP_FILE" | awk '{print $1}')
rm "$TEMP_FILE"

if [ -z "$SHA256" ]; then
    echo -e "${RED}Error: Could not calculate SHA256${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SHA256: ${SHA256}${NC}"
echo ""

# Update formula file
if [ ! -f "$FORMULA_FILE" ]; then
    echo -e "${RED}Error: Formula file not found at ${FORMULA_FILE}${NC}"
    exit 1
fi

# Backup original
cp "$FORMULA_FILE" "${FORMULA_FILE}.bak"

# Update URL and SHA256
sed -i '' "s|url \".*\"|url \"${URL}\"|" "$FORMULA_FILE"
sed -i '' "s|sha256 \".*\"|sha256 \"${SHA256}\"|" "$FORMULA_FILE"

echo -e "${GREEN}✅ Updated ${FORMULA_FILE}${NC}"
echo ""
echo "Changes:"
echo "  URL: ${URL}"
echo "  SHA256: ${SHA256}"
echo ""
echo "Review the changes, then commit:"
echo -e "  ${GREEN}git add ${FORMULA_FILE}${NC}"
echo -e "  ${GREEN}git commit -m \"Update Homebrew formula for ${TAG}\"${NC}"
echo -e "  ${GREEN}git push${NC}"
