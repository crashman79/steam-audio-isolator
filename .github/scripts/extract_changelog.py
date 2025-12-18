#!/usr/bin/env python3
"""Extract changelog section for a specific version"""
import re
import sys
import os

version = os.getenv('VERSION', '')
if not version:
    print("Error: VERSION environment variable not set")
    sys.exit(1)

try:
    with open("CHANGELOG.md", "r") as f:
        content = f.read()
    
    pattern = rf"## \[{re.escape(version)}\].*?(?=## \[|$)"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        changelog = match.group(0).strip()
        changelog = re.sub(r"^## \[.*?\]\s*-\s*.*?\n+", "", changelog)
        with open("release_changelog.txt", "w") as f:
            f.write(changelog)
        print(f"✓ Changelog extracted for v{version}")
    else:
        with open("release_changelog.txt", "w") as f:
            repo = os.getenv('GITHUB_REPOSITORY', 'steam-audio-isolator')
            f.write(f"See [CHANGELOG.md](https://github.com/{repo}/blob/main/CHANGELOG.md) for details on v{version}")
        print(f"⚠ No changelog found for v{version}")
except Exception as e:
    print(f"Error extracting changelog: {e}")
    sys.exit(1)
