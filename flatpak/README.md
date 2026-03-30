# Flatpak packaging

Manifest: `io.github.crashman79.steam-audio-isolator.yml`

- Bundles **PipeWire 1.2.7** (minimal build) so `pw-cli` / `pw-dump` work inside the sandbox.
- Mounts **host** `xdg-run/pipewire-0` so the app talks to your session PipeWire.
- **PyQt5** and other Python deps install via `pip` during the Flatpak build (network enabled for that module only).

## Local build

```bash
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08
# from repository root; generate all hicolor sizes (menu icons need 48×48 etc., not only 256):
test -f steam-audio-isolator-48.png || python3 generate_icon.py
flatpak-builder --user --install --default-branch=stable --force-clean build-dir flatpak/io.github.crashman79.steam-audio-isolator.yml
```

Run: `flatpak run io.github.crashman79.steam-audio-isolator`

Single-file bundle (optional):  
`flatpak build-bundle repo steam-audio-isolator-x86_64.flatpak io.github.crashman79.steam-audio-isolator stable`

## Publishing and automation

Flatpak’s overview of options is in the official docs: [Publishing](https://docs.flatpak.org/en/latest/publishing.html) (Flathub vs self-hosted repo vs [single-file bundles](https://docs.flatpak.org/en/latest/single-file-bundles.html)).

**This repo today**

- **GitHub Actions** (`.github/workflows/flatpak.yml`): builds on `main` / PRs; artifact `steam-audio-isolator-x86_64.flatpak`.
- **Tagged releases** (`.github/workflows/build-release.yml`): same Flatpak build, bumps `<release>` in AppStream for the tag, uploads `steam-audio-isolator-x86_64.flatpak` next to the tarballs.

**Flathub** (best discoverability): follow the official [Submission](https://docs.flathub.org/docs/for-app-authors/submission) guide (build with `org.flatpak.Builder`, run `flatpak-builder-lint`, open a PR against the `new-pr` branch on [flathub/flathub](https://github.com/flathub/flathub)). Replace the inline `pip3 install …` module with [flatpak-builder-tools](https://github.com/flatpak/flatpak-builder-tools) `pip-gen` so wheels are pinned and checksummed. After merge, Flathub hosts the app repo and builds updates; see [GitHub Actions on Flathub](https://docs.flathub.org/docs/for-app-authors/github-actions) for automating those builds.

**Self-hosted OSTree repo** (updates via `flatpak update`): see [Hosting a repository](https://docs.flatpak.org/en/latest/hosting-a-repository.html), including [GitLab / GitHub Pages](https://docs.flatpak.org/en/latest/hosting-a-repository.html#hosting-a-repository-on-gitlab-github-pages). You need a **GPG-signed** repo, `.flatpakrepo` (and often `.flatpakref`) files, and `flatpak build-update-repo` (optionally `--generate-static-deltas` for faster downloads). [Repositories](https://docs.flatpak.org/en/latest/repositories.html) covers `.flatpakref` and publishing updates.

**Qt / X11 / Wayland**: the Flatpak build does **not** set `QT_QPA_PLATFORM` in code (`FLATPAK_ID` skips that logic). `finish-args` expose both **Wayland** and **fallback-x11** so Qt uses whatever the session provides—nothing is forced to X11 only.

## Flathub checklist (when you submit)

- Generated Python/PIP module with hashes (not live `pip install` in CI for the *published* manifest).
- Screenshots and OARS in `metainfo.xml` if reviewers ask.
- Optional: [external data checker](https://github.com/flathub-infra/flatpak-external-data-checker) for PipeWire tarball bumps.

## Permissions (`finish-args`)

| Permission | Why |
|------------|-----|
| `wayland` / `fallback-x11` | Qt GUI (session picks backend; not X11-only) |
| `network` | About tab: GitHub Releases update check |
| `session-bus` | Tray / desktop integration |
| `xdg-run/pipewire-0` | Host PipeWire socket |
| `xdg-config`, `xdg-cache`, `xdg-data` | Profiles, logs, optional Steam path hints under `~/.local/share` |

Tighten further only if you fork the app and accept reduced functionality.
