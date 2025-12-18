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
        
        # Write with header for release notes
        with open("release_changelog.txt", "w") as f:
            f.write("## Installation\n\n")
            f.write("1. Download `steam-audio-isolator-linux-x86_64.tar.gz`\n")
            f.write("2. Extract: `tar -xzf steam-audio-isolator-linux-x86_64.tar.gz`\n")
            f.write("3. Run installer: `./install.sh`\n")
            f.write("4. Launch from application menu or run: `steam-audio-isolator`\n\n")
            f.write("## What's Changed\n\n")
            f.write(changelog)
        print(f"✓ Changelog extracted for v{version}")
    else:
        repo = os.getenv('GITHUB_REPOSITORY', 'crashman79/steam-audio-isolator')
        with open("release_changelog.txt", "w") as f:
            f.write("## Installation\n\n")
            f.write("1. Download `steam-audio-isolator-linux-x86_64.tar.gz`\n")
            f.write("2. Extract: `tar -xzf steam-audio-isolator-linux-x86_64.tar.gz`\n")
            f.write("3. Run installer: `./install.sh`\n")
            f.write("4. Launch from application menu or run: `steam-audio-isolator`\n\n")
            f.write("## What's Changed\n\n")
            f.write(f"See [CHANGELOG.md](https://github.com/{repo}/blob/main/CHANGELOG.md) for details on v{version}")
        print(f"⚠ No changelog found for v{version}")
except Exception as e:
    print(f"Error extracting changelog: {e}")
    sys.exit(1)
