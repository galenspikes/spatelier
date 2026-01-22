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

echo -e "${GREEN}🔍 Calculating SHA256 for ${TAG} from current commit...${NC}"

# Check if tag exists locally
if git rev-parse "$TAG" >/dev/null 2>&1; then
    # Tag exists locally, use it
    REF="$TAG"
    echo -e "${YELLOW}Note: Using existing local tag ${TAG}${NC}"
else
    # Tag doesn't exist yet, use HEAD (will be tagged in release script)
    REF="HEAD"
    echo -e "${YELLOW}Note: Tag ${TAG} doesn't exist yet, using HEAD (will be tagged next)${NC}"
fi

# Create local tarball matching GitHub's format
# GitHub uses: git archive --format=tar.gz --prefix=<repo-name>-<version>/ <ref>
TEMP_FILE=$(mktemp)
REPO_NAME="spatelier"
PREFIX="${REPO_NAME}-${VERSION}/"

echo -e "${GREEN}Creating tarball from ${REF} with prefix ${PREFIX}...${NC}"
git archive --format=tar.gz --prefix="$PREFIX" "$REF" > "$TEMP_FILE"

# Calculate SHA256 from local tarball
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

# No backup needed - git tracks changes

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
