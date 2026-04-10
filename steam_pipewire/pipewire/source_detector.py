#!/usr/bin/env python3
"""Detect and enumerate audio sources from PipeWire"""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)


class SourceDetector:
    """Detect audio sources available in PipeWire"""

    _steam_appname_cache: Dict[str, str] = {}
    _steam_library_cache: List[Path] = []
    _steam_cache_time: float = 0.0
    _steam_cache_ttl: float = 300.0

    def __init__(self):
        self.sources = []
        self.node_map = {}  # Cache for node ID to info mapping
        self._cache = None  # pw-dump cache
        self._cache_time = 0  # Timestamp of last cache
        self._cache_duration = 2  # Cache for 2 seconds
        self._pw_dump_proc = None  # active pw-dump; kill from UI thread on watchdog (never QThread.terminate)

    def abort_active_dump(self):
        """Kill a stuck pw-dump subprocess (safe from GUI thread). Avoids QThread.terminate crashes."""
        p = self._pw_dump_proc
        if p is None or p.poll() is not None:
            return
        try:
            p.kill()
            p.wait(timeout=3)
        except Exception:
            try:
                p.wait(timeout=1)
            except Exception:
                pass

    def get_audio_sources(self) -> List[Dict]:
        """Get all audio output sources using pw-dump with caching"""
        try:
            import time
            logger.debug("=== SOURCE DETECTION START ===")
            
            # Check cache first
            current_time = time.time()
            if self._cache is not None and (current_time - self._cache_time) < self._cache_duration:
                logger.debug(f"Using cached sources (age: {current_time - self._cache_time:.1f}s)")
                logger.debug(f"Found {len(self._cache)} audio sources (from cache)")
                for src in self._cache:
                    logger.debug(f"  Source: id={src['id']}, name={src['name']}, type={src['type']}")
                logger.debug("=== SOURCE DETECTION END ===")
                return self._cache
            
            logger.debug("Getting audio sources via pw-dump (not cached)...")
            start_time = time.time()

            stdout = ""
            returncode = -1
            try:
                self._pw_dump_proc = subprocess.Popen(
                    ['pw-dump'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                )
                try:
                    stdout, _stderr = self._pw_dump_proc.communicate(timeout=2)
                    returncode = self._pw_dump_proc.returncode
                except subprocess.TimeoutExpired:
                    logger.error("pw-dump timeout!")
                    self.abort_active_dump()
                    logger.debug("=== SOURCE DETECTION END ===")
                    return []
            finally:
                self._pw_dump_proc = None

            elapsed = time.time() - start_time
            logger.debug(f"pw-dump completed in {elapsed:.2f}s, code: {returncode}")

            if returncode != 0:
                logger.error(f"pw-dump failed with code {returncode}")
                logger.debug("=== SOURCE DETECTION END ===")
                return []

            try:
                data = json.loads(stdout)
                logger.debug(f"Parsed JSON with {len(data)} objects")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                logger.debug("=== SOURCE DETECTION END ===")
                return []
            
            # Cache nodes for future reference
            self.node_map = {node.get('id'): node for node in data 
                           if node.get('type') == 'PipeWire:Interface:Node'}
            logger.debug(f"Cached {len(self.node_map)} nodes")
            
            sources = self._parse_nodes(data)
            logger.info(f"Found {len(sources)} audio sources")
            for src in sources:
                logger.debug(f"  Source: id={src['id']}, name={src['name']}, type={src['type']}")
            
            # Cache the results
            self._cache = sources
            self._cache_time = time.time()
            
            logger.debug("=== SOURCE DETECTION END ===")
            return sources

        except Exception as e:
            logger.error(f"Error detecting sources: {e}", exc_info=True)
            logger.debug("=== SOURCE DETECTION END ===")
            return []

    def get_steam_recording_node(self) -> Optional[Dict]:
        """Find Steam's recording input node"""
        try:
            for node_id, node in self.node_map.items():
                props = node.get('info', {}).get('props', {})
                an = (props.get('application.name') or '').strip().lower()
                if an in ('steam', 'steam client'):
                    return {
                        'id': node_id,
                        'name': props.get('node.name', 'Steam'),
                        'description': props.get('node.description', 'Steam Recording'),
                        'props': props
                    }
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error finding Steam node: {e}")
        return None

    @staticmethod
    def _game_label_from_process_binary(
        props: Dict, app_name: str, node_description: str, node_name: str
    ) -> str:
        """Prefer real executable name when middleware (FMOD/Wwise) hides the game title."""
        raw = (props.get('application.process.binary') or '').strip()
        if raw:
            base = Path(raw).name
            generic = {
                'run.sh', 'start.sh', 'launch.sh', 'steam.sh', 'bash', 'sh',
                'steam', 'xdg-open', 'python', 'python3',
            }
            bl = base.lower()
            if bl not in generic and 'fmod' not in bl and 'wwise' not in bl:
                stem = base
                for suf in ('.x86_64', '.x86', '.bin'):
                    if stem.endswith(suf):
                        stem = stem[:-len(suf)]
                        break
                return stem
        return node_description or app_name or node_name

    @staticmethod
    def _sanitize_game_candidate(value: str) -> str:
        """Return a cleaned game title candidate, or empty if it is generic/middleware noise."""
        candidate = (value or '').strip().strip('"').strip("'")
        if not candidate:
            return ''

        lower = candidate.lower()
        generic_exact = {
            'audio stream',
            'stream output audio',
            'stream input audio',
            'wine',
            'wine64',
            'wine-preloader',
            'wine64-preloader',
            'proton',
            'steam',
            'steam client',
            'pipewire',
            'wireplumber',
            'fmod ex app',
            'wwise',
            'webrtc voiceengine',
        }
        if lower in generic_exact:
            return ''
        if re.fullmatch(r'audio\s+stream\s*#\d+', lower):
            return ''
        if re.fullmatch(r'stream\s*#\d+', lower):
            return ''

        return candidate

    @staticmethod
    def _extract_steam_appid(text: str) -> Optional[str]:
        """Extract Steam AppID from an arbitrary string."""
        if not text:
            return None
        m = re.search(r'(?:SteamAppId|AppId|appid|steam_appid)\s*[=:]\s*(\d{3,8})', text, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'/compatdata/(\d{3,8})/', text)
        if m:
            return m.group(1)
        return None

    def _read_proc_text(self, pid: Optional[int], filename: str) -> str:
        """Read procfs text blobs safely (cmdline/environ)."""
        if not pid or pid <= 0:
            return ''
        try:
            raw = Path(f'/proc/{pid}/{filename}').read_bytes()
            # proc cmdline/environ are NUL-separated
            return raw.replace(b'\x00', b' ').decode('utf-8', errors='replace')
        except Exception:
            return ''

    @classmethod
    def _steam_libraries(cls) -> List[Path]:
        """Resolve known Steam library roots and cache them for a short window."""
        now = time.time()
        if cls._steam_library_cache and (now - cls._steam_cache_time) < cls._steam_cache_ttl:
            return cls._steam_library_cache

        home = Path.home()
        roots = [
            home / '.local/share/Steam',
            home / '.steam/steam',
            home / '.var/app/com.valvesoftware.Steam/.local/share/Steam',
        ]

        libraries = []
        seen = set()

        def _add_library(root_path: Path):
            rp = root_path.expanduser()
            if not rp.exists():
                return
            key = str(rp.resolve())
            if key in seen:
                return
            seen.add(key)
            libraries.append(rp)

        for root in roots:
            _add_library(root)
            vdf = root / 'steamapps/libraryfolders.vdf'
            if not vdf.exists():
                continue
            try:
                text = vdf.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for m in re.finditer(r'"path"\s*"([^"]+)"', text):
                path_text = m.group(1).replace('\\\\', '/')
                lib_root = Path(path_text)
                # libraryfolders.vdf path points to the library root that contains steamapps
                if (lib_root / 'steamapps').exists():
                    _add_library(lib_root)

        cls._steam_library_cache = libraries
        cls._steam_cache_time = now
        return libraries

    @classmethod
    def _steam_name_for_appid(cls, appid: str) -> Optional[str]:
        """Resolve Steam game name for an AppID from appmanifest files."""
        if not appid:
            return None
        if appid in cls._steam_appname_cache:
            return cls._steam_appname_cache[appid]

        for library_root in cls._steam_libraries():
            manifest = library_root / 'steamapps' / f'appmanifest_{appid}.acf'
            if not manifest.exists():
                continue
            try:
                text = manifest.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            m = re.search(r'"name"\s*"([^"]+)"', text)
            if m:
                name = m.group(1).strip()
                if name:
                    cls._steam_appname_cache[appid] = name
                    return name
        return None

    def _game_name_from_process(self, props: Dict) -> str:
        """Best-effort game title extraction for Steam/Proton/Wine streams."""
        app_binary = (props.get('application.process.binary') or '').strip()
        app_name = (props.get('application.name') or '').strip()
        node_desc = (props.get('node.description') or '').strip()

        # Prefer already-useful labels before expensive procfs/manifest checks.
        for candidate in (app_name, node_desc):
            cleaned = self._sanitize_game_candidate(candidate)
            if cleaned:
                return cleaned

        pid_raw = props.get('application.process.id')
        try:
            pid = int(pid_raw)
        except Exception:
            pid = None

        cmdline_text = self._read_proc_text(pid, 'cmdline')
        environ_text = self._read_proc_text(pid, 'environ')

        # Resolve Steam AppID first where possible; this is the most stable name source.
        for text in (app_binary, cmdline_text, environ_text):
            appid = self._extract_steam_appid(text)
            if not appid:
                continue
            steam_name = self._steam_name_for_appid(appid)
            if steam_name:
                return steam_name

        # Next best: pull executable/path hints from process command line.
        args = [a for a in cmdline_text.split(' ') if a]
        for arg in reversed(args):
            low = arg.lower()
            if '/steamapps/common/' in low:
                m = re.search(r'/steamapps/common/([^/]+)', arg, re.IGNORECASE)
                if m:
                    cleaned = self._sanitize_game_candidate(m.group(1).replace('_', ' '))
                    if cleaned:
                        return cleaned
            if low.endswith('.exe'):
                stem = Path(arg).name
                stem = stem[:-4] if stem.lower().endswith('.exe') else stem
                cleaned = self._sanitize_game_candidate(stem.replace('_', ' '))
                if cleaned:
                    return cleaned
            if low.endswith(('.x86_64', '.x86', '.bin')):
                stem = Path(arg).name
                for suf in ('.x86_64', '.x86', '.bin'):
                    if stem.endswith(suf):
                        stem = stem[:-len(suf)]
                        break
                cleaned = self._sanitize_game_candidate(stem.replace('_', ' '))
                if cleaned:
                    return cleaned

        # Last fallback: process binary label, then old behavior.
        binary_guess = self._game_label_from_process_binary(
            props,
            app_name,
            node_desc,
            (props.get('node.name') or '').strip(),
        )
        cleaned = self._sanitize_game_candidate(binary_guess)
        if cleaned:
            return cleaned

        return node_desc or app_name or (props.get('node.name') or '')

    def _parse_nodes(self, data: List[Dict]) -> List[Dict]:
        """Parse PipeWire nodes to extract audio sources"""
        sources = []

        for node in data:
            if node.get('type') == 'PipeWire:Interface:Node':
                info = node.get('info', {})
                props = info.get('props', {})
                media_class = props.get('media.class', '')

                # Look for stream outputs (like games, applications) and audio sinks
                # Include: Stream/Output/Audio (apps), Audio/Source (mics), Audio/Sink (speakers/headphones)
                # Also include Stream/Input/Audio for Communication apps (Discord, Zoom, etc.)
                if not any(cls in media_class for cls in 
                          ['Stream/Output/Audio', 'Stream/Input/Audio', 'Audio/Source', 'Audio/Sink']):
                    continue
                
                # Skip internal/monitoring streams explicitly
                if 'Internal' in media_class:
                    continue
                
                # For Stream/Input/Audio, only allow Communication apps (Discord mic, etc.)
                if 'Stream/Input/Audio' in media_class:
                    # Quick pre-check: is this a communication app?
                    app_binary = props.get('application.process.binary', '').lower()
                    if not any(x in app_binary for x in 
                             ['discord', 'slack', 'zoom', 'telegram', 'teams', 'skype', 
                              'mumble', 'teamspeak', 'element', 'signal', 'whatsapp']):
                        # Not a communication app, skip this input stream
                        continue
                
                # Skip system echo-cancel, dummy, and internal nodes
                node_name = props.get('node.name', '').lower()
                node_description = props.get('node.description', '').lower()
                
                # Skip monitor nodes (passive observers of audio streams)
                if 'monitor' in node_name or 'monitor' in node_description:
                    logger.debug(f"Skipping monitor node: {node_name} / {node_description}")
                    continue
                
                # Skip other internal nodes
                if any(x in node_name for x in ['echo-cancel', 'dummy', 'freewheel', 'loopback']):
                    continue
                
                # Skip ALSA input devices (microphones already covered by Audio/Source)
                if 'alsa_input' in node_name:
                    continue
                
                # Skip Steam's own recording node (match client variants)
                app_name_skip = (props.get('application.name', '') or '').strip().lower()
                if app_name_skip in ('steam', 'steam client'):
                    continue

                source_type = self._determine_source_type(props)
                
                # Build a clear description.
                # For games we use Steam/Proton-aware name resolution to avoid generic labels like
                # "Audio Stream #1" when compatibility layers hide the title.
                app_binary = props.get('application.process.binary', '')
                app_name = props.get('application.name', '')
                media_name = props.get('media.name', '')
                
                # Start with best available name
                # System sources (audio devices) should always use descriptive name
                if source_type == 'System':
                    description = props.get('node.description') or app_name or node_name
                elif source_type == 'Game':
                    description = self._game_name_from_process(props)
                # For Communication apps, use binary name for clarity (Discord not WEBRTC VoiceEngine)
                elif source_type == 'Communication' and app_binary and app_binary not in ['', 'pipewire', 'wireplumber']:
                    # Use binary name and capitalize it nicely
                    description = app_binary.split('/')[-1]  # Get filename only
                    description = description.replace('-', ' ').replace('_', ' ').title()
                else:
                    # For Application and other types, use original descriptive names
                    description = props.get('node.description') or app_name or node_name
                
                # Add stream direction for communication apps (Input = Microphone, Output = Speakers)
                if source_type == 'Communication':
                    if 'Stream/Input/Audio' in media_class:
                        description += " (Microphone)"
                    elif 'Stream/Output/Audio' in media_class:
                        description += " (Voice Chat)"
                
                # Enhance description for System devices (output devices) to show function
                if source_type == 'System' and 'Audio/Sink' in media_class:
                    # This is an output device (speakers, headphones)
                    if 'bluez' in node_name or 'bluetooth' in node_name.lower():
                        # Bluetooth device - differentiate profiles by checking node name patterns
                        # HSP/HFP = Headset profile (mono, voice quality, bidirectional)
                        # A2DP = Advanced Audio Distribution Profile (stereo, high quality, output only)
                        if 'headset_head_unit' in node_name.lower() or 'hsp' in node_name.lower() or 'hfp' in node_name.lower():
                            description += " [Headset Profile - Mono/Voice]"
                        elif 'a2dp' in node_name.lower() or 'a2dp_sink' in node_name.lower():
                            description += " [A2DP - Stereo Audio]"
                        else:
                            description += " [Bluetooth Audio]"
                    elif 'hdmi' in node_name.lower():
                        description += " [HDMI Output]"
                    elif 'analog' in node_name.lower():
                        description += " [Speakers]"
                    else:
                        description += " [Output Device]"
                
                # Include media.name to distinguish multiple streams from same app
                # (but skip for Communication apps since we already labeled them)
                stream_purpose = ''
                if media_name:
                    # Guess the purpose of this stream based on its properties
                    stream_purpose = self._guess_stream_purpose(props, 0)
                    # Only append media_name if we haven't already added a clarifying label
                    if not (source_type == 'System' and 'Audio/Sink' in media_class) and source_type != 'Communication':
                        description = f"{description} ({media_name})"
                
                source = {
                    'id': node.get('id'),
                    'name': description,
                    'type': source_type,
                    'app_name': app_name,
                    'media_class': media_class,
                    'node_name': node_name,
                    'media_name': media_name,
                    'stream_purpose': stream_purpose,
                    'props': props
                }
                sources.append(source)

        return sources

    def _determine_source_type(self, props: Dict) -> str:
        """Determine the type of audio source based on application"""
        app_name = props.get('application.name', '').lower()
        app_binary = props.get('application.process.binary', '').lower()
        node_name = props.get('node.name', '').lower()
        media_class = props.get('media.class', '')
        app_id = props.get('application.process.id', '')
        
        # Check if this is an Audio/Sink (output device like speakers, headphones)
        # These are categorized as System since they're infrastructure, not app sources
        if 'Audio/Sink' in media_class:
            return 'System'

        media_name_l = (props.get('media.name') or '').lower()
        node_desc_l = (props.get('node.description') or '').lower()
        combo_mw = f"{app_name} {node_desc_l} {media_name_l}"
        # Common game audio middleware registers a generic app name (e.g. "FMOD Ex App")
        if 'fmod' in combo_mw or 'wwise' in combo_mw:
            return 'Game'
        
        # Check for Steam game indicators (expanded detection)
        # 1. Wine/Proton executables
        if any(x in app_binary for x in ['wine', 'proton', '.exe']):
            return 'Game'
        
        # 2. Steam runtime containers and launchers
        if any(x in app_binary for x in 
               ['pressure-vessel', 'steam-runtime', 'steamwebhelper', 
                'gameoverlayui', 'reaper', 'fossilize']):
            # Skip Steam's own processes (web helper, overlay)
            if 'steamwebhelper' in app_binary or 'gameoverlayui' in app_binary:
                return 'System'
            return 'Game'
        
        # 3. Games running under Steam runtime (check parent process)
        if 'steam' in app_binary.lower() and 'game' not in app_binary.lower():
            # This is likely Steam itself, not a game
            pass
        
        # 4. Application name hints
        if any(x in app_name for x in ['game', 'proton', 'wine']):
            return 'Game'
        
        # 5. Check for common Linux game binaries
        if app_binary.endswith(('.x86_64', '.x86', '.bin', '.sh')) and app_binary:
            # Many native Linux games end with these
            # But exclude known applications
            if not any(x in app_name for x in 
                      ['firefox', 'chrome', 'code', 'electron', 'discord', 
                       'slack', 'spotify', 'vlc', 'mpv']):
                # Could be a game, check if it's from a game-like path
                if any(x in app_binary for x in 
                      ['/steam/', '/steamapps/', '/games/', '/.steam/', 
                       '/compatdata/', '/shadercache/', '/.var/app/com.valvesoftware.steam',
                       'flatpak/com.valvesoftware.steam']):
                    return 'Game'

        # 5b. Native Linux under steamapps/common/ often has no .x86_64 suffix on the binary
        if '/steamapps/common/' in app_binary:
            if 'steamwebhelper' not in app_binary and 'gameoverlayui' not in app_binary:
                return 'Game'
        
        # 6. Check media.role property (some games set this)
        media_role = props.get('media.role', '').lower()
        if media_role in ['game', 'production']:
            return 'Game'
        
        # Check for communication tools FIRST (before browsers)
        # Many use Electron/Chromium but binary name reveals true identity
        if any(x in app_binary for x in 
               ['discord', 'slack', 'zoom', 'telegram', 'teams', 'skype', 
                'mumble', 'teamspeak', 'element', 'signal', 'whatsapp']):
            return 'Communication'
        
        # Check app name for communication (fallback)
        if any(x in app_name for x in 
               ['discord', 'slack', 'zoom', 'telegram', 'teams', 'skype', 
                'mumble', 'teamspeak', 'webrtc', 'element', 'signal']):
            return 'Communication'
        
        # Check for browser (after communication to avoid Electron false positives)
        if any(x in app_binary for x in 
               ['firefox', 'chrome', 'chromium', 'opera', 'brave', 'edge', 
                'vivaldi', 'safari', 'epiphany', 'falkon', 'midori', 'qutebrowser']):
            return 'Browser'
        
        # Check app name for browser (fallback)
        if any(x in app_name for x in 
               ['firefox', 'chrome', 'chromium', 'opera', 'brave', 'edge', 
                'vivaldi', 'safari', 'epiphany']):
            return 'Browser'
        
        # ALSA/system audio devices and Bluetooth devices
        if any(x in node_name for x in ['alsa', 'jack', 'pulse', 'bluez', 'bluetooth', 'hci']):
            return 'System'
        
        # Check for Bluetooth in device/driver properties
        device_name = props.get('device.name', '').lower()
        if any(x in device_name for x in ['bluez', 'bluetooth', 'hci']):
            return 'System'
        
        # Default to Application
        return 'Application'

    def _guess_stream_purpose(self, props: Dict, stream_index: int) -> str:
        """Guess the purpose of an audio stream based on its properties"""
        # Extract relevant properties
        max_length = props.get('pulse.attr.maxlength', 0)
        try:
            max_length = int(max_length) if isinstance(max_length, str) else max_length
        except:
            max_length = 0
        
        # Stream numbering hint (later streams often are ancillary)
        media_name = props.get('media.name', '')
        
        # Try to extract stream number
        stream_num = 0
        if 'audio stream #' in media_name.lower():
            try:
                stream_num = int(media_name.split('#')[1].split()[0])
            except:
                pass
        
        # Heuristic scoring based on properties
        # Larger buffers (>25KB) suggest continuous audio: music, main gameplay
        # Smaller buffers (<15KB) suggest discrete sounds: UI, effects, dialogue
        # Very large buffers (>31KB) suggest background/music
        
        if max_length > 31000:
            return "music/ambient"
        elif max_length > 25000:
            return "main audio/gameplay"
        elif max_length < 12000:
            return "UI/effects/voice/chat"
        elif max_length > 20000:
            return "speech/voice"
        else:
            # If buffer size is inconclusive, use stream order
            if stream_num == 1:
                return "main audio"
            elif stream_num == 2:
                return "UI/menu"
            elif stream_num == 3:
                return "voice/dialogue/chat"
            elif stream_num >= 4:
                return "music/ambient"
        
        return "audio stream"

    def _fallback_sources(self) -> List[Dict]:
        """Fallback source detection using pw-cli"""
        sources = []
        try:
            result = subprocess.run(
                ['pw-cli', 'list-objects', 'Node'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse pw-cli output format
                current_node = {}
                for line in result.stdout.split('\n'):
                    id_match = re.match(r'\s*id\s+(\d+)', line)
                    if id_match:
                        current_node = {'id': int(id_match.group(1)), 'name': '', 'type': 'Application'}
                        sources.append(current_node)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Fallback detection failed: {e}")

        return sources
