# Flatpak packaging

Primary manifest: [`io.github.crashman79.steam-audio-isolator.yml`](io.github.crashman79.steam-audio-isolator.yml)

- Bundles **PipeWire 1.2.7** (minimal build) so `pw-cli` / `pw-dump` work inside the sandbox.
- Mounts **host** `xdg-run/pipewire-0` so the app talks to your session PipeWire.
- **PyQt5** and other Python deps install via `pip` during the Flatpak build (network enabled for that module only in the manifest).

## GitHub Actions and Releases

| Workflow | When | Output |
|----------|------|--------|
| [`.github/workflows/flatpak.yml`](../.github/workflows/flatpak.yml) | `push` / `pull_request` to `main`, or manual | Workflow artifact **`flatpak-bundle`** (`steam-audio-isolator-x86_64.flatpak`) |
| [`.github/workflows/build-release.yml`](../.github/workflows/build-release.yml) | Version tags `v*` or manual | Same `.flatpak` attached to the **GitHub Release** |

Runners use **Ubuntu 24.04**, **flatpak-builder** ≥ 1.4, and the **appstream** package so AppStream compose matches Freedesktop SDK **24.08**.

## Install from a GitHub Release

1. Download **`steam-audio-isolator-x86_64.flatpak`** from [Releases](https://github.com/crashman79/steam-audio-isolator/releases).
2. Install (user install example):

```bash
flatpak install --user ./steam-audio-isolator-x86_64.flatpak
flatpak run io.github.crashman79.steam-audio-isolator
```

Updates: install a newer `.flatpak` from a newer release, or `flatpak uninstall` then install the new bundle again. There is no in-app update check inside the Flatpak build.

## Migrating from the standalone binary to Flatpak

The old **one-file** build (or portable copy) may have created menu and autostart entries that use the name **`steam-audio-isolator`**. The Flatpak uses the app ID **`io.github.crashman79.steam-audio-isolator`** for its `.desktop` file and **hicolor** icons, so you want the old launchers gone to avoid duplicates and wrong icons.

### 1. Remove the standalone launcher files

If you used **Settings → add to application menu / start at login** in the old app, remove these when the standalone app is **not** running (or use those toggles once more to turn them off, then delete if anything remains):

| Path | Purpose |
|------|---------|
| `~/.local/share/applications/steam-audio-isolator.desktop` | Application menu entry |
| `~/.config/autostart/steam-audio-isolator.desktop` | Login autostart |
| `~/.local/bin/steam-audio-isolator` | Optional copy from “Copy to ~/.local/bin” |

```bash
rm -f ~/.local/share/applications/steam-audio-isolator.desktop
rm -f ~/.config/autostart/steam-audio-isolator.desktop
rm -f ~/.local/bin/steam-audio-isolator
```

### 2. Optional: old icon name under `~/.local/share/icons`

The standalone flow could install PNGs named **`steam-audio-isolator.png`** under `~/.local/share/icons/hicolor/*/apps/`. They are not used by the Flatpak (which ships **`io.github.crashman79.steam-audio-isolator.png`** inside the bundle). You can remove them to avoid confusion:

```bash
find ~/.local/share/icons/hicolor -name 'steam-audio-isolator.png' -print -delete 2>/dev/null
```

### 3. Refresh menus / icon caches

```bash
update-desktop-database ~/.local/share/applications 2>/dev/null || true
gtk-update-icon-cache -f ~/.local/share/icons/hicolor 2>/dev/null || true
```

Log out and back in (or restart the session) if the app menu still shows a stale entry.

### 4. Install the Flatpak bundle

```bash
flatpak install --user ./steam-audio-isolator-x86_64.flatpak
```

After install, the launcher should appear as **Steam Audio Isolator** with **`Exec`** pointing at Flatpak and **`Icon=io.github.crashman79.steam-audio-isolator`**. Icons are provided at standard hicolor sizes inside the app. If the menu icon looks wrong, confirm you removed the old `steam-audio-isolator.desktop` and run the refresh commands above; avoid turning on the in-app **“add to application menu”** for duplicate host-side entries unless you want a second launcher (Flatpak already registers one).

## Local build

From the repository root:

```bash
chmod +x build.sh
./build.sh                    # user install (needs Pillow or python3-pil for icons once)
flatpak run io.github.crashman79.steam-audio-isolator
```

Single-file bundle (no install into your user Flatpak): `./build.sh --bundle` → `steam-audio-isolator-x86_64.flatpak`

Manual equivalent: install Freedesktop 24.08 Platform+Sdk from Flathub, then `flatpak-builder` as in `build.sh`.

## Permissions (`finish-args`)

| Permission | Why |
|------------|-----|
| `session-bus` | Qt platform style / system palette |
| `wayland` / `fallback-x11` | Qt GUI (session picks backend; not X11-only) |
| `talk-name=org.freedesktop.portal.Desktop` | Portal **Settings** (appearance) and **Background** (`RequestBackground`) for login autostart on KDE/GNOME/etc. |
| `talk-name` (Notifications, StatusNotifierWatcher) + StatusNotifierItem own names | Tray icon + desktop notifications |
| `xdg-run/pipewire-0` | Host PipeWire socket |

App data lives under the default Flatpak per-app XDG dirs (`~/.var/app/<app-id>/…`) with no extra host config mounts.

## Optional: other layouts

- **`flatpak/flathub/`** — Alternate KDE BaseApp + pinned-wheel layout (not used by this repo’s CI). Ignore unless you maintain a separate Flathub-style tree.
- Broader publishing options: [Flatpak publishing](https://docs.flatpak.org/en/latest/publishing.html) (self-hosted repo, etc.).

**Qt / X11 / Wayland:** the app does not force `QT_QPA_PLATFORM` under Flatpak (`FLATPAK_ID`); `finish-args` expose Wayland and `fallback-x11` so Qt follows the session.
