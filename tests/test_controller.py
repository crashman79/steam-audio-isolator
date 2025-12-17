"""Tests for controller module"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from steam_pipewire.pipewire.controller import (
    PipeWireController,
    _get_available_ports,
    _run_pw_cli_safe
)


class TestPipeWireController:
    """Test PipeWireController class"""

    def test_init(self):
        """Test controller initialization"""
        controller = PipeWireController()
        assert controller.active_routes == {}

    @patch('steam_pipewire.pipewire.controller._get_available_ports')
    @patch('steam_pipewire.pipewire.controller._run_pw_cli_safe')
    def test_connect_nodes_success(self, mock_pw_cli, mock_get_ports):
        """Test successful node connection"""
        # Mock port discovery
        mock_get_ports.side_effect = [[101], [201]]  # source port, dest port
        
        # Mock pw-cli connect success
        mock_pw_cli.return_value = Mock(
            returncode=0,
            stdout="connected 101 => 201 (link 350)"
        )

        controller = PipeWireController()
        success = controller.connect_nodes(137, 154)
        
        assert success is True
        assert 137 in controller.active_routes
        assert controller.active_routes[137]['target_node'] == 154

    @patch('steam_pipewire.pipewire.controller._get_available_ports')
    @patch('steam_pipewire.pipewire.controller._run_pw_cli_safe')
    def test_connect_nodes_no_ports(self, mock_pw_cli, mock_get_ports):
        """Test connection failure when no ports available"""
        # Mock no ports found
        mock_get_ports.return_value = []

        controller = PipeWireController()
        success = controller.connect_nodes(137, 154)
        
        assert success is False
        assert 137 not in controller.active_routes

    @patch('steam_pipewire.pipewire.controller._run_pw_cli_safe')
    def test_disconnect_node(self, mock_pw_cli):
        """Test disconnecting a node"""
        mock_pw_cli.return_value = Mock(returncode=0)

        controller = PipeWireController()
        
        # Set up existing route
        controller.active_routes[137] = {
            'target_node': 154,
            'link_ids': [350, 351]
        }

        success = controller.disconnect_node(137)
        
        assert success is True
        assert 137 not in controller.active_routes
        # Should have called destroy for each link
        assert mock_pw_cli.call_count == 2

    def test_disconnect_node_not_connected(self):
        """Test disconnecting node that isn't connected"""
        controller = PipeWireController()
        
        success = controller.disconnect_node(137)
        
        # Should return True (nothing to disconnect)
        assert success is True

    @patch('steam_pipewire.pipewire.controller._run_pw_cli_safe')
    def test_disconnect_all(self, mock_pw_cli):
        """Test disconnecting all routes"""
        mock_pw_cli.return_value = Mock(returncode=0)

        controller = PipeWireController()
        controller.active_routes = {
            137: {'target_node': 154, 'link_ids': [350]},
            200: {'target_node': 154, 'link_ids': [351, 352]}
        }

        controller.disconnect_all()
        
        assert controller.active_routes == {}
        # Should have called destroy for all links (3 total)
        assert mock_pw_cli.call_count == 3

    @patch('subprocess.run')
    def test_get_active_routes(self, mock_run):
        """Test getting active routes from pw-dump"""
        import json
        
        # Mock pw-dump output with link objects
        mock_data = [
            {
                "id": 350,
                "type": "PipeWire:Interface:Link",
                "info": {
                    "props": {
                        "link.output.node": "137",
                        "link.input.node": "154",
                        "link.output.port": "101",
                        "link.input.port": "201"
                    }
                }
            }
        ]
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )

        controller = PipeWireController()
        routes = controller.get_active_routes()
        
        assert len(routes) >= 1
        # Check route structure
        for route in routes:
            assert 'link_id' in route
            assert 'source_node' in route
            assert 'target_node' in route

    @patch('subprocess.run')
    def test_get_available_ports_function(self, mock_run):
        """Test _get_available_ports helper function"""
        import json
        
        mock_data = [
            {
                "id": 101,
                "type": "PipeWire:Interface:Port",
                "info": {
                    "props": {
                        "node.id": "137",
                        "port.direction": "out",
                        "port.name": "output_FL"
                    }
                }
            },
            {
                "id": 102,
                "type": "PipeWire:Interface:Port",
                "info": {
                    "props": {
                        "node.id": "137",
                        "port.direction": "in",
                        "port.name": "input"
                    }
                }
            }
        ]
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )

        # Get output ports for node 137
        ports = _get_available_ports(137, "out")
        assert 101 in ports
        assert 102 not in ports  # Wrong direction

    def test_run_pw_cli_safe_success(self):
        """Test _run_pw_cli_safe helper function"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr=""
            )

            result = _run_pw_cli_safe('list-objects', 'Node')
            
            assert result is not None
            assert result.returncode == 0

    def test_run_pw_cli_safe_timeout(self):
        """Test _run_pw_cli_safe with timeout"""
        import subprocess
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('pw-cli', 5)

            result = _run_pw_cli_safe('list-objects', 'Node')
            
            assert result is None

    @patch('steam_pipewire.pipewire.controller._run_pw_cli_safe')
    def test_apply_routing_profile(self, mock_pw_cli):
        """Test applying a routing profile"""
        mock_pw_cli.return_value = Mock(returncode=0)

        controller = PipeWireController()
        
        profile = {
            'enabled_sources': [137, 200],
            'steam_node_id': 154
        }

        with patch.object(controller, 'connect_nodes', return_value=True) as mock_connect:
            success = controller.apply_routing_profile(profile)
            
            assert success is True
            assert mock_connect.call_count == 2

    def test_is_node_connected(self):
        """Test checking if node is connected"""
        controller = PipeWireController()
        
        controller.active_routes[137] = {
            'target_node': 154,
            'link_ids': [350]
        }

        assert controller.is_node_connected(137) is True
        assert controller.is_node_connected(200) is False

    def test_get_connection_info(self):
        """Test getting connection info for a node"""
        controller = PipeWireController()
        
        controller.active_routes[137] = {
            'target_node': 154,
            'link_ids': [350, 351],
            'timestamp': 1234567890
        }

        info = controller.get_connection_info(137)
        
        assert info is not None
        assert info['target_node'] == 154
        assert len(info['link_ids']) == 2

        # Non-existent node
        info = controller.get_connection_info(999)
        assert info is None
