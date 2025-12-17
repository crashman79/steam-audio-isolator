#!/bin/bash
# Steam Audio Isolator - Simple launcher script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Run the app
python -m steam_pipewire.main
