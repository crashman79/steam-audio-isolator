#!/usr/bin/env python3
"""PipeWire control interface using pw-cli"""

import subprocess
import json
import re
import logging
import os
import signal
import threading
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_available_ports(node_id: int, direction: str = "out") -> List[int]:
    """Get available ports for a node with specified direction
    
    Args:
        node_id: The node ID
        direction: "in" or "out"
    
    Returns:
        List of port IDs
    """
    try:
        result = subprocess.run(
            ['pw-dump'],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            ports = []
            for item in data:
                if item.get('type') == 'PipeWire:Interface:Port':
                    props = item.get('info', {}).get('props', {})
                    port_node_id = props.get('node.id')
                    port_direction = props.get('port.direction')
                    
                    # node.id is a string in props
                    try:
                        if int(port_node_id) == node_id and port_direction == direction:
                            ports.append(item.get('id'))
                    except (ValueError, TypeError):
                        pass
            
            logger.debug(f"  Found {len(ports)} {direction} ports for node {node_id}: {ports}")
            return ports
    except Exception as e:
        logger.debug(f"  Error getting ports: {e}")
    
    return []


def _run_pw_cli_safe(*args, timeout=5):
    """Run pw-cli command with timeout and error handling
    
    Returns:
        CompletedProcess or None if timeout/error
    """
    try:
        logger.debug(f"  Running: pw-cli {' '.join(str(a) for a in args)}")
        
        result = subprocess.run(
            ['pw-cli'] + [str(a) for a in args],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        logger.debug(f"    Returned: code={result.returncode}")
        if result.stdout.strip():
            logger.debug(f"    Stdout: {result.stdout.strip()[:100]}...")
        if result.stderr.strip():
            logger.debug(f"    Stderr: {result.stderr.strip()[:100]}...")
        
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"  TIMEOUT (>{timeout}s) running: pw-cli {' '.join(str(a) for a in args)}")
        return None
    except FileNotFoundError:
        logger.error("pw-cli not found! Is PipeWire installed?")
        return None
    except Exception as e:
        logger.error(f"  Exception running pw-cli: {e}", exc_info=True)
        return None


class PipeWireController:
    """Control PipeWire audio routing"""

    def __init__(self):
        self.steam_node_id = None
        self._update_steam_node()

    def _update_steam_node(self):
        """Find and cache Steam's recording node ID"""
        try:
            result = subprocess.run(
                ['pw-dump'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for node in data:
                    if node.get('type') == 'PipeWire:Interface:Node':
                        props = node.get('info', {}).get('props', {})
                        if props.get('application.name') == 'Steam':
                            self.steam_node_id = node.get('id')
                            logger.debug(f"Found Steam recording node: {self.steam_node_id}")
                            return
                logger.warning("Steam node not found - is Steam running?")
        except subprocess.TimeoutExpired:
            logger.error("Timeout finding Steam node")
        except Exception as e:
            logger.error(f"Error updating Steam node: {e}", exc_info=True)

    def get_recording_devices(self) -> List[Dict]:
        """Get Steam's recording node (the target for game audio)"""
        devices = []
        try:
            self._update_steam_node()
            if self.steam_node_id:
                result = subprocess.run(
                    ['pw-cli', 'info', str(self.steam_node_id)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    devices.append({
                        'id': self.steam_node_id,
                        'name': 'Steam Recording Input',
                        'description': 'Steam Game Recording'
                    })
        except Exception as e:
            logger.debug(f"Error getting recording devices: {e}")

        return devices

    def get_current_routes(self) -> List[Dict]:
        """Get all current audio routes to Steam"""
        routes = []
        
        logger.debug("=== ROUTE DETECTION START ===")
        
        # Refresh Steam node ID in case it changed
        self._update_steam_node()
        
        if not self.steam_node_id:
            logger.error("Steam node not found!")
            logger.debug("=== ROUTE DETECTION END ===")
            return routes
        
        logger.debug(f"Looking for routes to Steam node {self.steam_node_id}")
        
        try:
            # First, get all source info via pw-dump (fast, single call)
            logger.debug("Step 1: Caching node info via pw-dump...")
            try:
                result = subprocess.run(
                    ['pw-dump'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                source_cache = {}
                if result.returncode == 0:
                    nodes = json.loads(result.stdout)
                    source_cache_count = 0
                    for node in nodes:
                        if node.get('type') == 'PipeWire:Interface:Node':
                            node_id = node.get('id')
                            props = node.get('info', {}).get('props', {})
                            source_cache[node_id] = {
                                'node.description': props.get('node.description', ''),
                                'application.name': props.get('application.name', '')
                            }
                            source_cache_count += 1
                    logger.debug(f"  Cached {source_cache_count} nodes")
                else:
                    logger.warning(f"  pw-dump failed: {result.returncode}")
                    source_cache = {}
            except Exception as e:
                logger.warning(f"  Exception during pw-dump: {e}", exc_info=True)
                source_cache = {}
            
            # Then get links
            logger.debug("Step 2: Getting links via pw-cli...")
            result = subprocess.run(
                ['pw-cli', 'list-objects', 'Link'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            logger.debug(f"  pw-cli returned code: {result.returncode}")
            
            if result.returncode == 0:
                # Parse pw-cli output
                lines = result.stdout.split('\n')
                logger.debug(f"  Parsing {len(lines)} lines")
                
                current_link = None
                output_node = None
                output_port = None
                input_node = None
                input_port = None
                links_checked = 0
                
                for line in lines:
                    # Match link ID line
                    id_match = re.match(r'\s*id\s+(\d+)', line)
                    if id_match:
                        if current_link is not None and input_node == self.steam_node_id:
                            # Previous link was to Steam, store it
                            links_checked += 1
                            cached = source_cache.get(output_node, {})
                            source_name = cached.get('node.description') or \
                                         cached.get('application.name') or f"Node {output_node}"
                            if not source_name:
                                source_name = f"Node {output_node}"
                            channel = self._get_channel_label(output_port)
                            logger.debug(f"    ✓ Found: Link {current_link}, Node {output_node} → Steam ({source_name}) [{channel}]")
                            routes.append({
                                'link_id': current_link,
                                'source_node_id': output_node,
                                'source_port_id': output_port,
                                'source_name': source_name,
                                'target_node_id': input_node,
                                'target_port_id': input_port,
                                'channel': channel
                            })
                        elif current_link is not None:
                            links_checked += 1
                            if input_node:
                                logger.debug(f"    ✗ Link {current_link}: {output_node} → {input_node} (not to Steam)")
                        
                        current_link = int(id_match.group(1))
                        output_node = None
                        output_port = None
                        input_node = None
                        input_port = None
                        continue
                    
                    # Match output node
                    out_match = re.search(r'link\.output\.node\s+=\s+"?(\d+)"?', line)
                    if out_match:
                        output_node = int(out_match.group(1))
                    
                    # Match output port
                    out_port_match = re.search(r'link\.output\.port\s+=\s+"?(\d+)"?', line)
                    if out_port_match:
                        output_port = int(out_port_match.group(1))
                    
                    # Match input node  
                    in_match = re.search(r'link\.input\.node\s+=\s+"?(\d+)"?', line)
                    if in_match:
                        input_node = int(in_match.group(1))
                    
                    # Match input port
                    in_port_match = re.search(r'link\.input\.port\s+=\s+"?(\d+)"?', line)
                    if in_port_match:
                        input_port = int(in_port_match.group(1))
                
                # Don't forget last link
                if current_link is not None and input_node == self.steam_node_id:
                    links_checked += 1
                    cached = source_cache.get(output_node, {})
                    source_name = cached.get('node.description') or \
                                 cached.get('application.name') or f"Node {output_node}"
                    if not source_name:
                        source_name = f"Node {output_node}"
                    channel = self._get_channel_label(output_port)
                    logger.debug(f"    ✓ Found (last): Link {current_link}, Node {output_node} → Steam ({source_name}) [{channel}]")
                    routes.append({
                        'link_id': current_link,
                        'source_node_id': output_node,
                        'source_port_id': output_port,
                        'source_name': source_name,
                        'target_node_id': input_node,
                        'target_port_id': input_port,
                        'channel': channel
                    })
                
                logger.debug(f"  Checked {links_checked} links total")
            
            logger.debug(f"Result: Found {len(routes)} route(s)")
            logger.debug(f"=== ROUTE DETECTION DEBUG END ===\n")
        except Exception as e:
            logger.debug(f"Error getting current routes: {e}")
            logger.debug(f"=== ROUTE DETECTION DEBUG END ===\n")

        return routes

    def _get_channel_label(self, port_id: int) -> str:
        """Get human-readable channel label (Left/Right) from port ID"""
        if port_id is None:
            return "Unknown"
        # Even port IDs are typically left channel, odd are right
        if port_id % 2 == 0:
            return "Left"
        else:
            return "Right"

    def _get_node_info(self, node_id: int) -> Dict:
        """Get node properties"""
        try:
            result = subprocess.run(
                ['pw-cli', 'info', str(node_id)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                props = {}
                for line in result.stdout.split('\n'):
                    # Parse key = value pairs
                    match = re.search(r'\*?\s*(\w+(?:\.\w+)*)\s*=\s*["\']?([^"\']*)["\']?', line)
                    if match:
                        props[match.group(1)] = match.group(2)
                return props
        except Exception as e:
            logger.debug(f"Error getting node info: {e}")
        return {}

    def create_audio_routing(self, source_ids: List[int], target_node_id: int) -> Tuple[bool, str]:
        """Create audio routing from sources to target node
        
        First disconnects existing routes (game→sink, game→Steam, sink→Steam), 
        then creates direct routes.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.debug(f"\n=== ROUTING DEBUG START ===")
            logger.debug(f"Target Steam node ID: {target_node_id}")
            logger.debug(f"Source node IDs: {source_ids}")
            
            if not target_node_id:
                return False, "Steam node ID not set - is Steam running?"
            
            # Find the audio sink node (analog output device)
            audio_sink_id = None
            try:
                result = subprocess.run(['pw-dump'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for node in data:
                        if node.get('type') == 'PipeWire:Interface:Node':
                            props = node.get('info', {}).get('props', {})
                            node_name = props.get('node.name', '')
                            # Look for ALSA analog stereo output
                            if 'alsa_output' in node_name and 'analog-stereo' in node_name:
                                audio_sink_id = node.get('id')
                                logger.debug(f"Found audio sink: node {audio_sink_id} ({props.get('node.description')})")
                                break
            except Exception as e:
                logger.warning(f"Could not detect audio sink: {e}")
            
            if not audio_sink_id:
                logger.warning("Audio sink not found - will only disconnect game→Steam routes")
            
            # Disconnect only routes that would interfere with clean recording:
            # 1. Audio Sink → Steam (prevents ALL system audio from being recorded)
            # 2. Game → Steam (any existing direct routes, we'll recreate them)
            # 
            # IMPORTANT: Do NOT disconnect Game → Audio Sink routes!
            # Game audio needs to continue playing through speakers.
            routes_to_remove = []
            
            try:
                logger.debug(f"Looking for routes to remove...")
                result = subprocess.run(
                    ['pw-cli', 'list-objects', 'Link'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                logger.debug(f"pw-cli list-objects returned code: {result.returncode}")
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    logger.debug(f"Parsing {len(lines)} lines of link data")
                    current_link = None
                    output_node = None
                    input_node = None
                    
                    for line in lines:
                        id_match = re.match(r'\s*id\s+(\d+)', line)
                        if id_match:
                            # Check previous link
                            if current_link is not None:
                                # Case 1: Audio sink → Steam (blocks ALL system audio from recording)
                                if audio_sink_id and output_node == audio_sink_id and input_node == target_node_id:
                                    logger.debug(f"  Found sink({audio_sink_id})→Steam link: {current_link} (will remove)")
                                    routes_to_remove.append(current_link)
                                # Case 2: Selected game → Steam (existing direct route, will recreate)
                                elif output_node in source_ids and input_node == target_node_id:
                                    logger.debug(f"  Found game({output_node})→Steam link: {current_link} (will remove)")
                                    routes_to_remove.append(current_link)
                                # REMOVED: Don't disconnect game→sink! Game audio must reach speakers.
                            
                            current_link = int(id_match.group(1))
                            output_node = None
                            input_node = None
                            continue
                        
                        out_match = re.search(r'link\.output\.node\s+=\s+"?(\d+)"?', line)
                        if out_match:
                            output_node = int(out_match.group(1))
                        
                        in_match = re.search(r'link\.input\.node\s+=\s+"?(\d+)"?', line)
                        if in_match:
                            input_node = int(in_match.group(1))
                    
                    # Check last link
                    if current_link is not None:
                        if audio_sink_id and output_node == audio_sink_id and input_node == target_node_id:
                            logger.debug(f"  Found sink({audio_sink_id})→Steam link (last): {current_link} (will remove)")
                            routes_to_remove.append(current_link)
                        elif output_node in source_ids and input_node == target_node_id:
                            logger.debug(f"  Found game({output_node})→Steam link (last): {current_link} (will remove)")
                            routes_to_remove.append(current_link)
            except Exception as e:
                logger.debug(f"Error finding links to remove: {e}")
            
            # Remove all interfering routes
            logger.debug(f"Removing {len(routes_to_remove)} existing routes: {routes_to_remove}")
            for link_id in routes_to_remove:
                result = _run_pw_cli_safe('destroy', link_id, timeout=3)
                if result and result.returncode == 0:
                    logger.debug(f"  ✓ Destroyed link {link_id}")
                elif result is None:
                    logger.error(f"  ✗ Timeout destroying link {link_id}")
                else:
                    logger.error(f"  ✗ Failed destroying link {link_id}: code {result.returncode}")
            
            # Give PipeWire a moment to settle after disconnection
            import time
            time.sleep(1.0)  # Increased from 0.5s
            
            # Validate source nodes before creating routes
            # Filter out any Bluetooth devices, sinks, or invalid nodes
            valid_source_ids = []
            for source_id in source_ids:
                try:
                    result = subprocess.run(['pw-dump'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        for node in data:
                            if node.get('id') == source_id:
                                props = node.get('info', {}).get('props', {})
                                node_name = props.get('node.name', '').lower()
                                device_name = props.get('device.name', '').lower()
                                node_desc = props.get('node.description', '').lower()
                                media_class = props.get('media.class', '')
                                
                                # Skip Bluetooth devices
                                if any(bt in node_name for bt in ['bluez', 'bluetooth', 'bt_', 'hci']):
                                    logger.warning(f"Skipping Bluetooth node {source_id}: {node_name}")
                                    continue
                                if any(bt in device_name for bt in ['bluez', 'bluetooth', 'bt_', 'hci']):
                                    logger.warning(f"Skipping Bluetooth device {source_id}: {device_name}")
                                    continue
                                if any(bt in node_desc for bt in ['bluetooth', 'headset', 'earbuds', 'airpods']):
                                    logger.warning(f"Skipping Bluetooth node {source_id}: {node_desc}")
                                    continue
                                
                                # Skip audio sinks (output devices)
                                if 'alsa_output' in node_name or 'Audio/Sink' in media_class:
                                    logger.warning(f"Skipping audio sink {source_id}: {node_name}")
                                    continue
                                
                                # Valid source - add to list
                                valid_source_ids.append(source_id)
                                logger.debug(f"Validated source {source_id}: {props.get('application.name', node_name)}")
                                break
                except Exception as e:
                    logger.error(f"Error validating source {source_id}: {e}")
            
            if not valid_source_ids:
                return False, "No valid audio sources to route (all sources were filtered out)"
            
            if len(valid_source_ids) < len(source_ids):
                logger.warning(f"Filtered out {len(source_ids) - len(valid_source_ids)} invalid sources")
            
            source_ids = valid_source_ids
            
            # Now create new direct routes using port-specific connections
            connected = []
            failed = []
            
            logger.debug(f"Creating {len(source_ids)} source→Steam routes using create-link")
            for source_id in source_ids:
                # Get available ports for this source (output ports) and target (input ports)
                source_ports = _get_available_ports(source_id, "out")
                target_ports = _get_available_ports(target_node_id, "in")
                
                if not source_ports:
                    logger.error(f"  ✗ No output ports found for source {source_id}")
                    failed.append(f"Node {source_id}: no output ports")
                    continue
                
                if not target_ports:
                    logger.error(f"  ✗ No input ports found for target {target_node_id}")
                    failed.append(f"Node {source_id}: target has no input ports")
                    continue
                
                # Connect ALL available ports (for stereo: left and right channels)
                num_ports = min(len(source_ports), len(target_ports))
                logger.debug(f"  Connecting {num_ports} channels: {source_ports[:num_ports]} → {target_ports[:num_ports]}")
                
                source_connected = False
                for i in range(num_ports):
                    source_port = source_ports[i]
                    target_port = target_ports[i]
                    
                    logger.debug(f"    Channel {i}: {source_id}:{source_port} → {target_node_id}:{target_port}")
                    # Create link with properties to allow multiple simultaneous outputs:
                    # - object.linger: persist the link
                    # - link.passive: don't make this link exclusive (allow game→speakers to continue)
                    # - link.dont-remix: don't change the channel layout
                    result = _run_pw_cli_safe('create-link', source_id, source_port, target_node_id, target_port, 
                                             '{ object.linger=true link.passive=true link.dont-remix=true }', timeout=5)
                    
                    if result is None:
                        logger.error(f"      ✗ Timeout creating link for channel {i}")
                    elif result.returncode == 0:
                        logger.debug(f"      ✓ Successfully created link for channel {i}")
                        source_connected = True
                    else:
                        err_msg = result.stderr.strip() if result.stderr.strip() else f"code {result.returncode}"
                        logger.error(f"      ✗ Failed to create link for channel {i}: {err_msg}")
                
                if source_connected:
                    connected.append(source_id)
                    logger.debug(f"    ✓ Connected {source_id} ({num_ports} channels)")
                else:
                    failed.append(f"Node {source_id}: all channels failed")
            
            message = f"Removed {len(routes_to_remove)} existing route(s), connected {len(connected)} source(s)"
            if failed:
                message += f" ({len(failed)} failed)"
            
            logger.debug(f"Result: {message}")
            logger.debug(f"=== ROUTING DEBUG END ===\n")
            
            return len(failed) == 0, message
        except Exception as e:
            logger.debug(f"Error creating audio routing: {e}")
            return False, str(e)

    def remove_routing(self, link_id: int) -> bool:
        """Remove an audio routing link"""
        try:
            result = subprocess.run(
                ['pw-cli', 'destroy', str(link_id)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Error removing routing: {e}")
            return False

    def disconnect_all_from_steam(self) -> Tuple[bool, str]:
        """Disconnect all sources from Steam recording
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        routes = self.get_current_routes()
        disconnected = 0
        failed = 0
        
        for route in routes:
            if self.remove_routing(route['link_id']):
                disconnected += 1
            else:
                failed += 1
        
        message = f"Disconnected {disconnected} routes"
        if failed > 0:
            message += f" ({failed} failed)"
        
        return failed == 0, message
    
    def reconnect_sink_to_steam(self) -> Tuple[bool, str]:
        """Reconnect the audio sink (speakers) to Steam recording
        
        This restores the default behavior where all audio (system, browser, game, etc.)
        goes through the sink and gets recorded by Steam.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.debug("=== SINK RECONNECTION START ===")
            
            result = subprocess.run(
                ['pw-dump'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return False, "Failed to query audio sink"
            
            data = json.loads(result.stdout)
            
            # Collect all sinks and categorize them
            analog_sinks = []  # Analog stereo speakers (preferred)
            other_sinks = []   # Other non-GPU sinks
            gpu_sinks = []     # GPU/HDMI sinks (avoid)
            
            for node in data:
                if node.get('type') == 'PipeWire:Interface:Node':
                    props = node.get('info', {}).get('props', {})
                    media_class = props.get('media.class', '')
                    node_name = props.get('node.name', '')
                    
                    # Only process actual sinks
                    if 'Audio/Sink' not in media_class:
                        continue
                    
                    logger.debug(f"Found sink: {node_name} (node {node.get('id')})")
                    
                    # Categorize the sink
                    is_gpu = any(skip in node_name.lower() for skip in ['navi', 'nvidia', 'hdmi', 'gpu', 'displayport', 'dp-'])
                    is_virtual = any(skip in node_name.lower() for skip in ['echo-cancel', 'dummy', 'freewheel'])
                    is_analog = 'Analog' in node_name or 'Stereo' in node_name
                    
                    node_entry = (node.get('id'), node_name)
                    
                    if is_virtual:
                        logger.debug(f"  → Virtual sink, skipping")
                        continue
                    elif is_gpu:
                        logger.debug(f"  → GPU/HDMI sink, deprioritizing")
                        gpu_sinks.append(node_entry)
                    elif is_analog:
                        logger.debug(f"  → Analog stereo (preferred)")
                        analog_sinks.append(node_entry)
                    else:
                        logger.debug(f"  → Other hardware sink")
                        other_sinks.append(node_entry)
            
            # Pick the best sink: prefer analog stereo, then other hardware, avoid GPU
            sink_node_id = None
            sink_node_name = None
            
            if analog_sinks:
                sink_node_id, sink_node_name = analog_sinks[0]
                logger.debug(f"Selected analog sink: {sink_node_name} (node {sink_node_id})")
            elif other_sinks:
                sink_node_id, sink_node_name = other_sinks[0]
                logger.debug(f"Selected other sink: {sink_node_name} (node {sink_node_id})")
            elif gpu_sinks:
                logger.warning("No non-GPU sinks available, using GPU sink as fallback")
                sink_node_id, sink_node_name = gpu_sinks[0]
                logger.debug(f"Selected GPU sink (fallback): {sink_node_name} (node {sink_node_id})")
            
            if not sink_node_id:
                logger.warning("No audio sink found")
                return False, "No audio sink found in system"
            
            logger.info(f"Using sink: {sink_node_name} (node {sink_node_id})")
            
            # Get Steam's recording node ID
            steam_id = self.steam_node_id
            if not steam_id:
                logger.warning("Steam recording node not found")
                return False, "Steam recording node not found"
            
            logger.debug(f"Reconnecting sink {sink_node_id} to Steam {steam_id}")
            
            # Get available ports for both nodes
            sink_ports = _get_available_ports(sink_node_id, "out")
            steam_ports = _get_available_ports(steam_id, "in")
            
            if not sink_ports or not steam_ports:
                logger.warning(f"Missing ports: sink={sink_ports}, steam={steam_ports}")
                return False, "Could not find audio ports for sink or Steam"
            
            # Create links from sink to Steam
            num_ports = min(len(sink_ports), len(steam_ports))
            connected = 0
            
            for i in range(num_ports):
                sink_port = sink_ports[i]
                steam_port = steam_ports[i]
                
                logger.debug(f"Creating link {sink_node_id}:{sink_port} → {steam_id}:{steam_port}")
                
                result = _run_pw_cli_safe(
                    'create-link', 
                    str(sink_node_id), str(sink_port), 
                    str(steam_id), str(steam_port),
                    '{ "object.linger": "true" }',
                    timeout=5
                )
                
                if result and result.returncode == 0:
                    logger.debug(f"✓ Successfully created sink link for channel {i}")
                    connected += 1
                else:
                    logger.warning(f"✗ Failed to create sink link for channel {i}")
            
            if connected > 0:
                logger.info(f"Sink reconnected with {connected} channel(s)")
                logger.debug("=== SINK RECONNECTION END ===")
                return True, f"Sink reconnected: {sink_node_name} ({connected} channel(s))"
            else:
                logger.error("No sink links were created")
                logger.debug("=== SINK RECONNECTION END ===")
                return False, "Failed to create sink links"
        
        except subprocess.TimeoutExpired:
            logger.error("Sink reconnection timeout")
            logger.debug("=== SINK RECONNECTION END ===")
            return False, "Operation timed out"
        except Exception as e:
            logger.error(f"Error reconnecting sink: {e}", exc_info=True)
            logger.debug("=== SINK RECONNECTION END ===")
            return False, f"Error: {e}"
