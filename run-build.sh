#!/bin/sh
# Backwards-compatible alias: clean Flatpak build dirs, rebuild, run.
cd "$(dirname "$0")"
exec ./build-and-run.sh -c "$@"
