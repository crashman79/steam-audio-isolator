# Steam Audio Isolator

**Record only the audio you choose in Steam Game Recording on Linux.**

By default, Steam Game Recording captures everything that reaches your speakers:
the game, a video in another window, chat notifications, music, and so on. Steam
Audio Isolator creates direct PipeWire links from the audio sources you pick to
Steam's recording input, so the recording gets only those sources.

You still hear the game normally through your speakers. The app does not change
Steam or your game settings, and it does not record anything itself.

> This is an independent, unofficial tool. It only rearranges audio inside your
> local PipeWire session.

<p align="center">
    <img src="screenshots/steam-audio-isolator%20main%20tab.png" alt="Steam Audio Isolator Audio Routing tab" width="800">
    <br><em>The Audio Routing tab, with the Current Routes section below it.</em>
</p>

---

## What it does

```
Default Steam behaviour:
  Game, browser, chat, system sounds → speakers → Steam records all of it

With Steam Audio Isolator:
  Game                 → speakers              (you hear it)
  Game                 → Steam recording input (Steam records it)
  Browser / chat / etc → speakers              (not sent to Steam)
```

**Apply Routing replaces whatever was previously feeding Steam's recording
input.** After it runs, only the sources being routed are connected to Steam. Your
normal speaker output is left alone, so the game stays audible.

All routed sources are mixed into Steam's one recording input. The app cannot put
different sources on separate tracks.

---

## Before you start

You need:

- **Linux with PipeWire.** Steam must also be using PipeWire for Game Recording,
  not plain PulseAudio.
- **Steam running** with **Game Recording enabled** (Steam → Settings → Game
  Recording).
- **The game or app running**, so its audio stream exists and can be detected.

If Steam's recording input cannot be found, the app shows an error instead of
creating routes.

---

## Install

### Flatpak bundle (recommended)

Download `steam-audio-isolator-x86_64.flatpak` from the
[latest release](https://github.com/crashman79/steam-audio-isolator/releases),
then:

```bash
flatpak install --user ./steam-audio-isolator-x86_64.flatpak
flatpak run io.github.crashman79.steam-audio-isolator
```

Flatpak will fetch the Freedesktop runtime if it is not already installed. To
update, install a newer bundle from the releases page.

### Build and install locally

With `flatpak-builder` installed:

```bash
./build.sh
flatpak run io.github.crashman79.steam-audio-isolator
```

`./build.sh --clean` removes the previous build directory first. Local builds use
`pw-cli` and `pw-dump` from your distro's PipeWire package. For Flatpak
permissions and release builds, see [`flatpak/README.md`](flatpak/README.md).

---

## How to use it

1. **Start Steam** and make sure Game Recording is on.
2. **Start your game** (and anything else whose audio you want in the clip).
3. **Open Steam Audio Isolator.** It scans for audio sources immediately and keeps
   checking every few seconds. **Refresh Sources** forces an immediate scan.
4. On the **Audio Routing** tab, look at **Available Audio Sources**. Sources are
   grouped by type.
   - Games are checked automatically.
   - Browsers, chat apps, ordinary applications, and system/output devices are
     not checked automatically.
5. **Choose what to record.**
   - Check any extra source you want in the recording.
   - Uncheck a source to leave it out. Unchecking takes effect immediately: that
     source is disconnected from Steam and marked `excluded (temp)`.
6. **Click Apply Routing** if you changed the selection. With automatic routing on,
   newly detected games are usually connected already.
7. Look at **Current Routes** below the source list. It shows the links that are
   feeding Steam's recording input. It checks automatically and updates when the
   route list changes. **Refresh now** forces a check.
8. **Record in Steam** the way you normally do.
9. When you are done, either:
   - click **Clear All Routes** to disconnect everything and restore the normal
     speaker → Steam routing, or
   - quit the app. If **Restore default sink routing when app closes** is on
     (the default), quitting does the same cleanup.

### Automatic routing is not the same as applying changes

With **Automatically apply routing when new games are detected** on (the
default), the app applies routing by itself in two cases:

- games are already running when the first scan finishes, and
- a new game appears while the app is running.

Automatic routing reacts to **newly detected games**. If you change checkboxes
for a game that is already on screen, click **Apply Routing** to activate the
new selection. Unchecking a source still disconnects it immediately.

If automatic routing is off, newly detected games are still checked in the list,
but the app does not connect them. Click **Apply Routing** to create the routes.

---

## Controls

| Control | What it does |
|---|---|
| **Refresh Sources** | Scans PipeWire again and rebuilds the source list. |
| **Apply Routing** | Clears all existing links into Steam's recording input, then connects the sources chosen for routing. |
| **Clear All Routes** | Disconnects every source from Steam and reconnects a normal output sink, returning to Steam's default behaviour. |
| **Refresh now** | Rechecks the Current Routes table immediately. |
| **Update Info** (System Info tab) | Refreshes the PipeWire and Steam-node details shown on that tab. |
| **Save Settings** | Saves the Settings tab. Theme and behaviour changes take effect after saving. |

---

## Tabs

| Tab | What is there |
|---|---|
| **Audio Routing** | The source list, Apply/Clear buttons, and the **Current Routes** section below them. |
| **System Info** | PipeWire and Steam recording-node details for troubleshooting. |
| **Settings** | Auto-detection, automatic routing, focus mode, close behaviour, tray, theme, and login startup. |
| **Profiles** | Save and reload a set of checked sources. |
| **About** | Built-in quick start, how-it-works summary, version, log location, and update information for packaged builds. |

There is no separate Current Routes tab; it is the lower part of the Audio
Routing tab. Drag the divider between the source list and Current Routes to
resize them. The window size, position, and divider position are remembered.

---

## What gets selected, and what stays out

- **Games are checked automatically** when they appear.
- **Browsers, chat apps, other applications, and output devices are not.** Check
  them yourself if you want them recorded.
- **Speakers and headphones are never checked automatically.** Routing an output
  device into the recording input can create a feedback loop, causing echo or
  distorted capture. Hover over the row (and click **More ▸** if needed) to see
  the warning.
- Long source names are shortened with `…`. Hover over a row to see the full name,
  the application name, and any exclusion status.
- A `(guess: …)` label next to some games is a rough estimate based on the
  stream's buffer size, not a guarantee of what that stream contains.
- Source detection is best-effort. Games from Steam, Proton/Wine, and common game
  audio engines are usually recognised. An unusual launcher or generic process
  name may appear as a plain application. Check it manually if needed.
- A game can expose more than one audio stream. Each stream appears as its own
  row, so check the ones you actually want recorded.

### Temporary and permanent exclusions

- **Unchecking a source** disconnects it from Steam right away and excludes it
  until that source disappears from detection (for example, when the game exits).
  A rediscovered process is selected again (and routed automatically if
  auto-apply is on). Restarting the app also clears these temporary exclusions.
  The row shows `excluded (temp)`.
- **Right-click a source → Exclude permanently** stores the exclusion in your
  settings. It survives restarts and the row shows `excluded`.
- **Re-checking the box**, or **right-click → Include in auto-select**, removes
  the exclusion. A re-checked source is not connected until you click **Apply
  Routing**.

An exclusion only controls automatic selection and automatic routing. It does not
prevent you from manually checking the source later.

### Multiple games and focus mode

In **Settings → When multiple games are selected:**

- **Route all selected games** (default) records every checked game into the same
  mixed Steam input.
- **Route one selected game (focus mode)** keeps one game connected, plus any
  non-game sources you checked. If **Preferred game title** matches one of the
  checked games exactly, that game wins. Otherwise the newest detected game is
  used. The other game stays checked in the list, but is not routed.

### Profiles

A profile stores the names of the sources that were checked when you saved it.
Loading a profile replaces the current selection, clears exclusions for those
sources, and applies routing immediately. Load a profile while its apps or games
are running; a source that is not currently detected cannot be routed.

---

## Settings, in plain terms

| Setting | What it does |
|---|---|
| **Theme** | Light, Dark, or System. Applied when you click Save Settings. |
| **Restore default sink routing when app closes** | On quit, disconnect every source from Steam and reconnect a normal output sink. This returns Steam to recording everything. On by default. |
| **Show confirmation dialog when closing** | Ask before actually quitting. On by default. Hiding to the tray does not show this dialog. |
| **Check for new audio sources every** | How often the app scans for new sources, from 1 to 30 seconds. Default: 3 seconds. |
| **Automatically apply routing when new games are detected** | Route games at startup and when a new game appears, without clicking Apply Routing. On by default. |
| **When multiple games are selected** | Route all checked games, or keep only one game in focus mode. |
| **Preferred game title (optional)** | Exact source name to prefer in focus mode. Leave blank to use the newest detected game. |
| **Minimize to system tray on close** | The window's close button hides the app to the tray instead of quitting. On by default. |
| **Start minimized to tray** | Launch with only the tray icon visible. Off by default. |
| **Start when I log in** | In the Flatpak, changing this and clicking Save opens your desktop's standard background-app permission dialog. Other builds create an autostart entry. |
| **Add to application menu** / **Copy to ~/.local/bin** | Non-Flatpak builds only. The Flatpak is already in your application menu. |

---

## Tray, closing, and quitting

With **Minimize to system tray on close** enabled, clicking the window's close
button hides the window. Routing continues. Open the app again from the tray
icon, or right-click it for:

**Show Window**, **Settings…**, **Apply Routing**, **Clear Routes**,
**Refresh Sources**, and **Quit**.

Use **Quit** to actually exit. If **Restore default sink routing when app closes**
is on, quitting disconnects everything from Steam and reconnects a normal output
sink. If it is off, the direct routes are left in place.

If **Minimize to system tray on close** is off, the close button quits the app
(after the confirmation dialog, if enabled).

**Start minimized to tray** is useful together with **Start when I log in**: the
app starts hidden and shows a tray notification.

---

## Good to know

- **Steam's recorder must exist.** Start Steam and enable Game Recording before
  applying routing. If the app says the Steam recording node was not found, there
  is nowhere to send the audio.
- **Routes are live, not permanent.** Restarting Steam, restarting the game,
  restarting PipeWire/WirePlumber, suspending the computer, or changing audio
  devices can remove the links. Click **Apply Routing** again, or let automatic
  routing catch a newly started game.
- **Applying routing clears old links into Steam.** That includes links created
  automatically by WirePlumber, such as a Bluetooth device. Only the sources being
  routed remain connected after Apply Routing.
- **Do not route speakers or headphones** unless you intentionally want to record
  system output. Feeding an output device back into the recorder can cause echo
  or feedback.
- **One mixed recording input.** There is no per-app track separation.
- **Future recordings only.** The app cannot change a clip that has already been
  recorded.
- **Source names are estimates.** Detection uses process names, Steam/Proton
  paths, and audio metadata. It is usually right, but not guaranteed.

---

## Troubleshooting

**"Steam Not Found" or the recording input is missing**

- Is Steam running?
- Is Game Recording enabled in Steam?
- Is Steam using PipeWire rather than PulseAudio?
- Click **Refresh Sources**, then try **Apply Routing** again.

**A game is not in the list**

- Start the game, then click **Refresh Sources** or wait for the next scan.
- Some unusual launchers are detected as a plain application. Check that row.

**Current Routes is empty after applying**

- Click **Refresh now**.
- Watch the status line for an error.
- Make sure Steam did not restart after you applied routing.

**The recording still contains other audio**

- Check whether you routed a speakers/headphones row. Uncheck it and apply again.
- Click **Clear All Routes**, then apply only the sources you want.
- Confirm Steam is not recording from a different input.

**Echo or distorted audio**

- You probably routed an output device. Uncheck the speakers/headphones row and
  click **Apply Routing**.

**Routes disappeared**

- Reapply routing. This is normal after Steam, PipeWire, the game, or the audio
  device restarts.

The **System Info** tab shows the detected Steam node and PipeWire details. The
log is at:

```
~/.var/app/io.github.crashman79.steam-audio-isolator/cache/steam-audio-isolator/steam-audio-isolator.log
```

(For a non-Flatpak build, use `~/.cache/steam-audio-isolator/steam-audio-isolator.log`.)

---

## Where your settings live

Flatpak:

```
~/.var/app/io.github.crashman79.steam-audio-isolator/config/steam-audio-isolator/
├── settings.json     # preferences, exclusions, window and divider layout
└── profiles/         # saved source selections
```

Non-Flatpak builds use the normal XDG locations under `~/.config/` and
`~/.cache/`.

---

## More screenshots

<p align="center">
    <img src="screenshots/steam-audio-isolator%20settings%20tab.png" alt="Steam Audio Isolator Settings tab" width="800">
    <br><em>The Settings tab in the Flatpak build.</em>
</p>

<details>
<summary>See the routing difference in qpwgraph</summary>

<p align="center">
    <img src="screenshots/before%20routing.png" alt="Before routing" width="800">
    <br><em>Before: every app plays through the speakers, and the speaker monitor feeds Steam's recorder — so everything is captured.</em>
</p>

<p align="center">
    <img src="screenshots/after%20routing.png" alt="After routing" width="800">
    <br><em>After: the checked sources link directly into Steam's recorder and the speaker-monitor link is gone. This older example also had Vivaldi checked.</em>
</p>
</details>

---

## Development note

Some code and documentation were developed with LLM-assisted tooling. The
maintainer reviews, tests, and takes responsibility for every change. AI tools
are not project contributors.

---

## License

MIT. All audio routing happens locally in your PipeWire session.
