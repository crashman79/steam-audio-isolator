#!/bin/bash
# Release script for Steam Audio Isolator
# Usage: ./release.sh <new_version>
# Example: ./release.sh 0.1.5

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if version argument provided
if [ -z "$1" ]; then
    echo "Usage: $0 <new_version>"
    echo "Example: $0 0.1.5"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (X.Y.Z)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Use X.Y.Z (e.g., 0.1.5)"
    exit 1
fi

echo "=== Steam Audio Isolator Release Script ==="
echo "Version: $NEW_VERSION"
echo ""

# Get current version from setup.py
CURRENT_VERSION=$(grep "version=" setup.py | head -1 | sed "s/.*version=['\"]//;s/['\"].*//" | sed 's/^v//')

echo "Current version: $CURRENT_VERSION"
echo "New version: $NEW_VERSION"
echo ""

# Confirm version change
read -p "Continue with release? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled."
    exit 1
fi

echo ""
echo "Updating version in files..."

# Update setup.py
echo "  • Updating setup.py..."
sed -i "s/version='[^']*'/version='$NEW_VERSION'/" setup.py

# Update steam_pipewire/__init__.py
echo "  • Updating steam_pipewire/__init__.py..."
sed -i "s/__version__ = '[^']*'/__version__ = '$NEW_VERSION'/" steam_pipewire/__init__.py

# Update CHANGELOG.md (move [Unreleased] to new version with date)
echo "  • Updating CHANGELOG.md..."
RELEASE_DATE=$(date +%Y-%m-%d)
python3 << PYSCRIPT
import re

NEW_VERSION = "$NEW_VERSION"
RELEASE_DATE = "$RELEASE_DATE"

with open("CHANGELOG.md", "r") as f:
    content = f.read()

# Replace [Unreleased] section with versioned section
old_pattern = r"## \[Unreleased\]"
new_section = f"## [Unreleased]\n\n## [{NEW_VERSION}] - {RELEASE_DATE}"

content = re.sub(old_pattern, new_section, content, count=1)

with open("CHANGELOG.md", "w") as f:
    f.write(content)

print(f"✓ Changelog updated: [Unreleased] → [{NEW_VERSION}]")
PYSCRIPT

echo ""
echo "Committing changes..."

# Stage and commit version updates
git add setup.py steam_pipewire/__init__.py CHANGELOG.md

COMMIT_MSG="chore: bump version to v$NEW_VERSION"
git commit -m "$COMMIT_MSG"

echo "✓ Version files committed"
echo ""
echo "Creating release tag..."

# Create annotated tag
TAG_NAME="v$NEW_VERSION"
TAG_MSG="Release v$NEW_VERSION"

git tag -a "$TAG_NAME" -m "$TAG_MSG"

echo "✓ Tag created: $TAG_NAME"
echo ""
echo "Pushing changes and tag..."

# Push to remote
git push origin main
git push origin "$TAG_NAME"

echo "✓ Pushed to GitHub"
echo ""
echo "=== Release Complete! ==="
echo ""
echo "Tag: $TAG_NAME"
echo "Next steps:"
echo "  1. Run './build_release.sh' to create the standalone release"
echo "  2. Upload the tarball to GitHub Releases"
echo "  3. (Optional) Attach release notes from CHANGELOG.md"
echo ""
