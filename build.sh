#!/usr/bin/env bash
# Build and install Steam Audio Isolator Flatpak (primary local workflow).
#
#   ./build.sh                    # build + install Flatpak
#   ./build.sh --clean            # remove Flatpak build dir first
#   ./build.sh -c                 # same
#
# Optional bundle output (for CI/release/manual sharing):
#   ./build.sh --bundle
#   ./build.sh --bundle --bundle-install
#
# Override default build directory:
#   STEAM_AUDIO_ISOLATOR_FLATPAK_BUILD_DIR=/path/to/build ./build.sh
#
# Optional flatpak-builder flags (e.g. --disable-rofiles-fuse):
#   STEAM_AUDIO_ISOLATOR_FLATPAK_BUILDER_OPTS=--disable-rofiles-fuse ./build.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ROOT="$(pwd)"

APP_ID="io.github.crashman79.steam-audio-isolator"
MANIFEST="$ROOT/flatpak/io.github.crashman79.steam-audio-isolator.yml"
INIT_FILE="$ROOT/steam_pipewire/__init__.py"
BUILD_DIR="${STEAM_AUDIO_ISOLATOR_FLATPAK_BUILD_DIR:-${BUILD_DIR:-$ROOT/../steam-audio-isolator-flatpak-build}}"
REPO_DIR="${STEAM_AUDIO_ISOLATOR_FLATPAK_REPO_DIR:-${REPO_DIR:-$ROOT/repo}}"
BUNDLE_NAME="${STEAM_AUDIO_ISOLATOR_FLATPAK_BUNDLE_NAME:-${BUNDLE_NAME:-steam-audio-isolator-x86_64.flatpak}}"
FB_OPTS="${STEAM_AUDIO_ISOLATOR_FLATPAK_BUILDER_OPTS:-}"

MODE="install"
CLEAN=0
SKIP_RUNTIMES=0
BUNDLE_INSTALL=0
INIT_BACKUP=""

restore_init_file() {
  if [ -n "$INIT_BACKUP" ] && [ -f "$INIT_BACKUP" ]; then
    cp "$INIT_BACKUP" "$INIT_FILE"
    rm -f "$INIT_BACKUP"
  fi
}

usage() {
  echo "Usage: ./build.sh [--clean|-c] [--bundle] [--bundle-install] [--no-runtimes]"
  echo "  default          build + install user Flatpak"
  echo "  --clean, -c      remove Flatpak build dir first"
  echo "  --bundle         build OCI repo + ${BUNDLE_NAME}"
  echo "  --bundle-install install the generated .flatpak bundle (implies --bundle)"
  echo "  --no-runtimes    skip flatpak install for Platform/SDK"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --clean|-c) CLEAN=1; shift ;;
    --bundle) MODE="bundle"; shift ;;
    --bundle-install) MODE="bundle"; BUNDLE_INSTALL=1; shift ;;
    --no-runtimes) SKIP_RUNTIMES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [ ! -f "$MANIFEST" ]; then
  echo "Missing manifest: $MANIFEST" >&2
  exit 1
fi

if [ ! -f "$INIT_FILE" ]; then
  echo "Missing metadata file: $INIT_FILE" >&2
  exit 1
fi

if ! command -v flatpak >/dev/null 2>&1 || ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "Install flatpak and flatpak-builder first (see flatpak/README.md)." >&2
  exit 1
fi

if [ "$CLEAN" -eq 1 ]; then
  echo "Removing Flatpak build dir: $BUILD_DIR"
  rm -rf "$BUILD_DIR"
fi

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
    echo "Error: python3 needed to run generate_icon.py" >&2
    exit 1
  fi
  if ! python3 -c "import PIL" 2>/dev/null; then
    echo "Error: Install Pillow (pip install pillow) or python3-pil, then re-run." >&2
    exit 1
  fi
  python3 generate_icon.py
fi

# Stamp build timestamp for About tab metadata, then restore source after build.
INIT_BACKUP="$(mktemp)"
cp "$INIT_FILE" "$INIT_BACKUP"
trap restore_init_file EXIT
BUILD_TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
if grep -q '^__build_timestamp__ = ' "$INIT_FILE"; then
  sed -i "s/^__build_timestamp__ = .*/__build_timestamp__ = '$BUILD_TIMESTAMP'/" "$INIT_FILE"
else
  printf "\n__build_timestamp__ = '%s'\n" "$BUILD_TIMESTAMP" >> "$INIT_FILE"
fi

if [ "$MODE" = "install" ]; then
  echo "Building and installing (user) from $MANIFEST -> $BUILD_DIR"
  # shellcheck disable=SC2086
  flatpak-builder --user --install --default-branch=stable --force-clean $FB_OPTS "$BUILD_DIR" "$MANIFEST"
  echo "Build/install complete. Run with: flatpak run $APP_ID"
else
  echo "Building bundle from $MANIFEST -> $BUILD_DIR (repo: $REPO_DIR)"
  rm -rf "$REPO_DIR"
  # shellcheck disable=SC2086
  flatpak-builder --user --repo="$REPO_DIR" --default-branch=stable --force-clean $FB_OPTS "$BUILD_DIR" "$MANIFEST"
  flatpak build-bundle "$REPO_DIR" "$BUNDLE_NAME" "$APP_ID" stable
  echo "Bundle built: $ROOT/$BUNDLE_NAME"

  if [ "$BUNDLE_INSTALL" -eq 1 ]; then
    flatpak install --user -y --reinstall "$ROOT/$BUNDLE_NAME"
    echo "Bundle installed. Run with: flatpak run $APP_ID"
  fi
fi
