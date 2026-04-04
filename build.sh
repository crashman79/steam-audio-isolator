#!/usr/bin/env bash
# Build Steam Audio Isolator as a Flatpak (only supported distribution path).
# See flatpak/README.md for permissions and CI notes.
#
# Usage:
#   ./build.sh                  # install into user Flatpak (flatpak-builder --install)
#   ./build.sh --bundle         # build repo + steam-audio-isolator-x86_64.flatpak (CI / sharing)
#   ./build.sh --no-runtimes    # skip flatpak install Platform/SDK (already installed)
#   BUILD_DIR=build-flatpak ./build.sh --bundle   # custom build dir (e.g. CI)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_ID="io.github.crashman79.steam-audio-isolator"
MANIFEST="flatpak/io.github.crashman79.steam-audio-isolator.yml"
BUILD_DIR="${BUILD_DIR:-build-dir}"
REPO_DIR="${REPO_DIR:-repo}"
BUNDLE_NAME="${BUNDLE_NAME:-steam-audio-isolator-x86_64.flatpak}"
MODE="install"
SKIP_RUNTIMES=0

usage() {
  echo "Usage: ./build.sh [--bundle] [--no-runtimes] [-h|--help]"
  echo "  default     flatpak-builder --user --install (local dev)"
  echo "  --bundle    build OCI repo + ${BUNDLE_NAME}"
  echo "  --no-runtimes  do not run flatpak install for Platform/SDK"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --bundle) MODE="bundle"; shift ;;
    --no-runtimes) SKIP_RUNTIMES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

command -v flatpak-builder >/dev/null 2>&1 || {
  echo "Error: flatpak-builder not found. Install flatpak-builder (e.g. apt install flatpak-builder)."
  exit 1
}

if [ "$SKIP_RUNTIMES" -eq 0 ]; then
  flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  FP_INSTALL=(flatpak install -y)
  if [ -n "${GITHUB_ACTIONS:-}" ]; then
    FP_INSTALL+=(--noninteractive)
  fi
  "${FP_INSTALL[@]}" flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08
fi

if [ ! -f steam-audio-isolator-48.png ] || [ ! -f steam-audio-isolator-256.png ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 needed to run generate_icon.py"
    exit 1
  fi
  if ! python3 -c "import PIL" 2>/dev/null; then
    echo "Error: Install Pillow (pip install pillow) or python3-pil, then re-run."
    exit 1
  fi
  python3 generate_icon.py
fi

if [ "$MODE" = "install" ]; then
  echo "=== Flatpak: user install ==="
  flatpak-builder --user --install --default-branch=stable --force-clean "$BUILD_DIR" "$MANIFEST"
  echo "Run: flatpak run $APP_ID"
else
  echo "=== Flatpak: OCI repo + bundle ==="
  rm -rf "$REPO_DIR"
  flatpak-builder --user --repo="$REPO_DIR" --default-branch=stable --force-clean "$BUILD_DIR" "$MANIFEST"
  flatpak build-bundle "$REPO_DIR" "$BUNDLE_NAME" "$APP_ID" stable
  echo "Bundle: $(pwd)/$BUNDLE_NAME"
fi
