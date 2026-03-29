#!/bin/bash
# Clean, rebuild onefile binary, then run it.
set -e
cd "$(dirname "$0")"
rm -rf build dist
bash build.sh
exec ./dist/steam-audio-isolator "$@"
