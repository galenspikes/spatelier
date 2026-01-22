#!/bin/bash
# Release script for Spatelier
# Automates the release process including Homebrew formula updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from pyproject.toml
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
TAG="v${VERSION}"

if [ -z "$VERSION" ]; then
    echo -e "${RED}Error: Could not find version in pyproject.toml${NC}"
    exit 1
fi

# Setup logging
LOG_DIR=".data/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/release_${TAG}_${TIMESTAMP}.log"

# Function to log and echo (supports -e flag for colors)
log_and_echo() {
    if [ "$1" = "-e" ]; then
        shift
        echo -e "$@" | tee -a "$LOG_FILE"
    else
        echo "$@" | tee -a "$LOG_FILE"
    fi
}

# Function to log without colors (for file)
log_plain() {
    echo "$1" >> "$LOG_FILE"
}

# Start logging
log_plain "=========================================="
log_plain "Release Process Started: $(date)"
log_plain "Version: ${TAG}"
log_plain "Branch: $(git branch --show-current)"
log_plain "Commit: $(git rev-parse HEAD)"
log_plain "=========================================="
log_and_echo ""
log_and_echo -e "${GREEN}🚀 Starting release process for ${TAG}${NC}"
log_and_echo -e "${GREEN}📝 Logging to: ${LOG_FILE}${NC}"
log_and_echo ""

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    log_and_echo -e "${RED}Error: Tag ${TAG} already exists${NC}"
    log_plain "ERROR: Tag already exists"
    exit 1
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    log_and_echo -e "${RED}Error: Must be on main branch to release (currently on ${CURRENT_BRANCH})${NC}"
    log_plain "ERROR: Not on main branch"
    log_and_echo ""
    log_and_echo "Release workflow:"
    log_and_echo "  1. Merge your feature branch to main"
    log_and_echo "  2. Switch to main: git checkout main"
    log_and_echo "  3. Pull latest: git pull"
    log_and_echo "  4. Run release script: make release"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    log_and_echo -e "${RED}Error: You have uncommitted changes. Commit or stash them first.${NC}"
    log_plain "ERROR: Uncommitted changes detected"
    git status --short >> "$LOG_FILE"
    exit 1
fi

# Verify CHANGELOG has been updated
if ! grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    log_and_echo -e "${YELLOW}Warning: CHANGELOG.md doesn't appear to have entry for ${VERSION}${NC}"
    log_plain "WARNING: CHANGELOG not updated"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    log_plain "User response: $REPLY"
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
log_and_echo -e "${GREEN}🧪 Running tests...${NC}"
log_plain "Running pytest..."

# Try to use venv pytest first, then fall back to system pytest
PYTEST_CMD=""
if [ -f "venv/bin/pytest" ]; then
    PYTEST_CMD="venv/bin/pytest"
    log_plain "Using venv pytest: $PYTEST_CMD"
elif [ -n "$VIRTUAL_ENV" ] && command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
    log_plain "Using pytest from active venv: $VIRTUAL_ENV"
elif command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
    log_plain "Using system pytest (WARNING: may not have all dependencies)"
else
    log_and_echo -e "${YELLOW}Warning: pytest not found. Skipping tests.${NC}"
    log_plain "WARNING: pytest not found"
    log_and_echo "   Make sure tests pass before releasing!"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    log_plain "User response: $REPLY"
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if [ -n "$PYTEST_CMD" ]; then
    $PYTEST_CMD 2>&1 | tee -a "$LOG_FILE"
    TEST_EXIT_CODE=${PIPESTATUS[0]}
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        log_and_echo -e "${RED}Error: Tests failed. Fix tests before releasing.${NC}"
        log_plain "ERROR: Tests failed with exit code $TEST_EXIT_CODE"
        exit 1
    fi
    log_and_echo -e "${GREEN}✅ All tests passed${NC}"
    log_plain "SUCCESS: All tests passed"
fi

log_and_echo ""
log_and_echo -e "${GREEN}✅ Pre-release checks passed${NC}"
log_plain "SUCCESS: Pre-release checks passed"
log_and_echo ""
# Update Homebrew formula first
# Note: We calculate SHA256 from HEAD (current commit). After committing the formula update,
# we'll tag the commit BEFORE the formula update, so the SHA256 matches.
log_and_echo -e "${GREEN}🍺 Updating Homebrew formula...${NC}"
log_plain "Updating Homebrew formula"
if [ -f "scripts/update_homebrew.sh" ]; then
    # Calculate SHA256 from current HEAD (this commit will be tagged, before formula update)
    ./scripts/update_homebrew.sh "$TAG" 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_and_echo -e "${GREEN}✅ Homebrew formula updated${NC}"
        log_plain "SUCCESS: Homebrew formula updated"
        
        # Stage and commit the formula update
        if git diff --quiet Formula/spatelier.rb; then
            log_and_echo -e "${YELLOW}No changes to Formula/spatelier.rb${NC}"
        else
            log_and_echo -e "${GREEN}📝 Committing formula update...${NC}"
            log_plain "Committing formula update"
            git add Formula/spatelier.rb 2>&1 | tee -a "$LOG_FILE"
            git commit -m "Update Homebrew formula for ${TAG}" 2>&1 | tee -a "$LOG_FILE"
            log_and_echo -e "${GREEN}✅ Formula update committed${NC}"
            log_plain "SUCCESS: Formula update committed"
            
            # Update tap repository if it exists (before tagging)
            TAP_REPO="../homebrew-spatelier"
            if [ -d "$TAP_REPO" ] && [ -d "$TAP_REPO/.git" ]; then
                log_and_echo -e "${GREEN}🍺 Updating Homebrew tap repository...${NC}"
                log_plain "Updating tap repository at $TAP_REPO"
                (
                    cd "$TAP_REPO" || exit 1
                    git pull 2>&1 | tee -a "$LOG_FILE"
                    cp "../spatelier/Formula/spatelier.rb" "Formula/spatelier.rb" 2>&1 | tee -a "$LOG_FILE"
                    if ! git diff --quiet Formula/spatelier.rb; then
                        git add Formula/spatelier.rb 2>&1 | tee -a "$LOG_FILE"
                        git commit -m "Update to ${TAG}" 2>&1 | tee -a "$LOG_FILE"
                        git push 2>&1 | tee -a "$LOG_FILE"
                        log_and_echo -e "${GREEN}✅ Tap repository updated${NC}"
                        log_plain "SUCCESS: Tap repository updated"
                    else
                        log_and_echo -e "${YELLOW}No changes needed in tap repository${NC}"
                    fi
                ) || log_and_echo -e "${YELLOW}Warning: Could not update tap repository${NC}"
            else
                log_and_echo -e "${YELLOW}Tap repository not found at ${TAP_REPO}, skipping${NC}"
                log_plain "INFO: Tap repository not found"
            fi
        fi
    else
        log_and_echo -e "${YELLOW}Warning: Homebrew formula update failed, but continuing...${NC}"
        log_plain "WARNING: Homebrew formula update failed"
    fi
else
    log_and_echo -e "${YELLOW}Warning: update_homebrew.sh not found, skipping formula update${NC}"
    log_plain "WARNING: update_homebrew.sh not found"
fi

log_and_echo ""
# Create tag pointing to the commit BEFORE formula update (so SHA256 matches)
# The formula update is a separate commit that comes after the tag
if git diff --quiet HEAD~1 HEAD -- Formula/spatelier.rb 2>/dev/null; then
    # No formula update was committed, tag current HEAD
    log_and_echo -e "${GREEN}📝 Creating tag ${TAG}...${NC}"
    log_plain "Creating git tag: ${TAG}"
    git tag -a "$TAG" -m "Release ${TAG}" 2>&1 | tee -a "$LOG_FILE"
    log_and_echo -e "${GREEN}✅ Tag created${NC}"
    log_plain "SUCCESS: Tag created"
else
    # Formula update was committed, tag the commit before it (so SHA256 matches)
    log_and_echo -e "${GREEN}📝 Creating tag ${TAG} (pointing to commit before formula update)...${NC}"
    log_plain "Creating git tag: ${TAG} at HEAD~1"
    git tag -a "$TAG" -m "Release ${TAG}" HEAD~1 2>&1 | tee -a "$LOG_FILE"
    log_and_echo -e "${GREEN}✅ Tag created at commit before formula update${NC}"
    log_plain "SUCCESS: Tag created"
fi

log_and_echo ""
# Push tag and commits to origin
log_and_echo -e "${GREEN}📤 Pushing tag and commits to origin...${NC}"
log_plain "Pushing tag and commits to origin"
git push origin "$TAG" 2>&1 | tee -a "$LOG_FILE"
git push 2>&1 | tee -a "$LOG_FILE"

log_and_echo ""
log_and_echo -e "${GREEN}✅ Tag ${TAG} pushed successfully!${NC}"
log_plain "SUCCESS: Tag pushed successfully"

log_and_echo ""
log_and_echo -e "${YELLOW}⏳ Waiting for GitHub Actions to create release...${NC}"
log_and_echo "   Check progress at: https://github.com/galenspikes/spatelier/actions"

# Final log entry
log_plain "=========================================="
log_plain "Release Process Completed: $(date)"
log_plain "Tag: ${TAG}"
log_plain "Log file: ${LOG_FILE}"
log_plain "=========================================="
log_and_echo ""
log_and_echo -e "${GREEN}📝 Full log saved to: ${LOG_FILE}${NC}"
