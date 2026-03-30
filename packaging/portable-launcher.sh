#!/usr/bin/env bash
# Run Steam Audio Isolator from a directory that contains steam_pipewire/ and .venv/
set -euo pipefail
_launcher="$(readlink -f "${BASH_SOURCE[0]}")"
_here="$(dirname "${_launcher}")"
cd "${_here}"
export STEAM_AUDIO_ISOLATOR_LAUNCHER="${_launcher}"
_py="${_here}/.venv/bin/python"
if [[ ! -x "${_py}" ]]; then
  echo "steam-audio-isolator: missing ${_py}" >&2
  echo "Create the venv with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
exec "${_py}" -m steam_pipewire.main "$@"
