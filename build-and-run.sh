#!/bin/sh
# Build Flatpak (user install) and run the app. Primary local dev entrypoint.
#
#   ./build-and-run.sh              # build + flatpak run
#   ./build-and-run.sh --clean      # rm build-dir/repo, then build + run (-c)
#   ./build-and-run.sh -- --help    # extra args go to flatpak run
#
# Bundle only (no run):  ./build.sh --bundle
# Run from source (no Flatpak):     python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#                                    .venv/bin/python -m steam_pipewire.main

set -e
cd "$(dirname "$0")"

APP_ID="io.github.crashman79.steam-audio-isolator"

clean=0
while [ $# -gt 0 ]; do
	case "$1" in
		--clean|-c) clean=1; shift ;;
		--) shift; break ;;
		*) break ;;
	esac
done

if [ "$clean" -eq 1 ]; then
	echo "Removing Flatpak build artifacts (build-dir, build-flatpak, repo)..."
	rm -rf build-dir build-flatpak repo
fi

./build.sh
exec flatpak run "$APP_ID" "$@"
