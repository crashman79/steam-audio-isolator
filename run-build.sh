#!/bin/sh
# Backwards-compatible alias: clean Flatpak build, install, run.
cd "$(dirname "$0")"
./build.sh --clean "$@"
exec flatpak run io.github.crashman79.steam-audio-isolator
