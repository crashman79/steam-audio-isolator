#!/usr/bin/env python3
"""Detect and enumerate audio sources from PipeWire"""

import subprocess
import json
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SourceDetector:
    """Detect audio sources available in PipeWire"""

    def __init__(self):
        self.sources = []
        self.node_map = {}  # Cache for node ID to info mapping
        self._cache = None  # pw-dump cache
        self._cache_time = 0  # Timestamp of last cache
        self._cache_duration = 2  # Cache for 2 seconds

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
            
            # Use pw-dump with strict timeout
            result = subprocess.run(
                ['pw-dump'],
                capture_output=True,
                text=True,
                timeout=2  # Subprocess timeout
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"pw-dump completed in {elapsed:.2f}s, code: {result.returncode}")

            if result.returncode != 0:
                logger.error(f"pw-dump failed with code {result.returncode}")
                logger.debug("=== SOURCE DETECTION END ===")
                return []

            try:
                data = json.loads(result.stdout)
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
            
        except subprocess.TimeoutExpired:
            logger.error("pw-dump timeout!")
            logger.debug("=== SOURCE DETECTION END ===")
            return []
        except Exception as e:
            logger.error(f"Error detecting sources: {e}", exc_info=True)
            logger.debug("=== SOURCE DETECTION END ===")
            return []

    def get_steam_recording_node(self) -> Optional[Dict]:
        """Find Steam's recording input node"""
        try:
            for node_id, node in self.node_map.items():
                props = node.get('info', {}).get('props', {})
                if props.get('application.name') == 'Steam':
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

    def _parse_nodes(self, data: List[Dict]) -> List[Dict]:
        """Parse PipeWire nodes to extract audio sources"""
        sources = []

        for node in data:
            if node.get('type') == 'PipeWire:Interface:Node':
                info = node.get('info', {})
                props = info.get('props', {})
                media_class = props.get('media.class', '')

                # Look for stream outputs (like games, applications) that produce audio
                # Skip inputs, sinks, system nodes, and Steam's own node
                if not any(cls in media_class for cls in 
                          ['Stream/Output/Audio', 'Audio/Source']):
                    continue
                
                # Skip system echo-cancel and internal nodes
                node_name = props.get('node.name', '').lower()
                if any(x in node_name for x in ['echo-cancel', 'dummy', 'freewheel']):
                    continue
                
                # Skip Steam's own recording node
                app_name = props.get('application.name', '')
                if app_name == 'Steam':
                    continue

                source_type = self._determine_source_type(props)
                description = props.get('node.description') or props.get('application.name') or node_name
                
                # Include media.name to distinguish multiple streams from same app
                media_name = props.get('media.name', '')
                stream_purpose = ''
                if media_name:
                    # Guess the purpose of this stream based on its properties
                    stream_purpose = self._guess_stream_purpose(props, 0)
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
        app_id = props.get('application.process.id', '')
        
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
                       '/compatdata/', '/shadercache/']):
                    return 'Game'
        
        # 6. Check media.role property (some games set this)
        media_role = props.get('media.role', '').lower()
        if media_role in ['game', 'production']:
            return 'Game'
        
        # Check for browser
        if any(x in app_name for x in ['firefox', 'chromium', 'chrome', 'opera', 'brave', 'edge']):
            return 'Browser'
        
        # Check for communication tools
        if any(x in app_name for x in ['discord', 'slack', 'zoom', 'telegram', 'teams', 'skype', 'mumble', 'teamspeak']):
            return 'Communication'
        
        # ALSA/system audio devices
        if any(x in node_name for x in ['alsa', 'jack', 'pulse']):
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
