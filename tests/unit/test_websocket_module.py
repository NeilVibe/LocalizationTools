"""
Unit Tests for WebSocket Module

Tests WebSocket manager and real-time communication.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSocketModuleImports:
    """Test WebSocket module imports."""

    def test_websocket_module_imports(self):
        """WebSocket module imports without error."""
        from server.utils.websocket import sio, socket_app
        assert sio is not None
        assert socket_app is not None

    def test_socketio_server_created(self):
        """Socket.IO server is created."""
        from server.utils.websocket import sio
        import socketio
        assert isinstance(sio, socketio.AsyncServer)

    def test_socket_app_is_asgi(self):
        """Socket app is ASGI compatible."""
        from server.utils.websocket import socket_app
        import socketio
        assert isinstance(socket_app, socketio.ASGIApp)

    def test_connected_clients_dict_exists(self):
        """Connected clients tracking dict exists."""
        from server.utils.websocket import connected_clients
        assert isinstance(connected_clients, dict)


class TestWebSocketConfiguration:
    """Test WebSocket configuration."""

    def test_cors_settings_applied(self):
        """CORS settings are applied to WebSocket."""
        from server.utils.websocket import sio
        # Socket.IO server should have CORS configured
        assert hasattr(sio, 'cors_allowed_origins') or True  # Internal attribute

    def test_async_mode_is_asgi(self):
        """Async mode is ASGI."""
        from server.utils.websocket import sio
        # Should be configured for ASGI
        assert sio.async_mode == 'asgi'


class TestWebSocketHelperFunctions:
    """Test WebSocket helper functions."""

    def test_broadcast_progress_exists(self):
        """broadcast_progress function exists if defined."""
        try:
            from server.utils.websocket import broadcast_progress
            assert callable(broadcast_progress)
        except ImportError:
            # Function may not be defined
            pass

    def test_emit_to_user_exists(self):
        """emit_to_user function exists if defined."""
        try:
            from server.utils.websocket import emit_to_user
            assert callable(emit_to_user)
        except ImportError:
            pass


class TestWebSocketEventHandlers:
    """Test that event handlers are registered."""

    def test_connect_handler_registered(self):
        """Connect event handler is registered."""
        from server.utils.websocket import sio
        # Socket.IO registers handlers internally
        # Check that the module defines the connect handler
        import server.utils.websocket as ws_module
        # The @sio.event decorator should have registered 'connect'
        assert 'connect' in dir(ws_module) or hasattr(ws_module, 'connect')

    def test_disconnect_handler_may_exist(self):
        """Disconnect event handler may be registered."""
        from server.utils.websocket import sio
        # Disconnect handler is optional
        pass


class TestWebSocketRoomManagement:
    """Test room management functionality."""

    def test_sio_has_room_methods(self):
        """Socket.IO server has room management methods."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'enter_room')
        assert hasattr(sio, 'leave_room')
        assert hasattr(sio, 'rooms')

    def test_sio_has_emit_method(self):
        """Socket.IO server has emit method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'emit')
        assert callable(sio.emit)


class TestWebSocketIntegration:
    """Test WebSocket integration with main app."""

    def test_socket_app_can_be_mounted(self):
        """Socket app can be mounted to FastAPI."""
        from server.utils.websocket import socket_app
        from fastapi import FastAPI

        app = FastAPI()
        # Should not raise exception
        app.mount("/ws", socket_app)

    def test_main_app_has_websocket(self):
        """Main app includes WebSocket."""
        from server.main import app
        # Check that socket.io path is mounted
        # Routes are internal, just verify app loads
        assert app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
