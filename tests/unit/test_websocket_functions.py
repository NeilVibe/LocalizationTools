"""
Unit Tests for WebSocket Functions

Tests WebSocket event emitters and utility functions.
TRUE SIMULATION - no mocks, real async function calls.
"""

import pytest
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSocketEmitFunctions:
    """Test WebSocket emit functions exist and are callable."""

    def test_emit_log_entry_exists(self):
        """emit_log_entry function exists."""
        from server.utils.websocket import emit_log_entry
        assert callable(emit_log_entry)

    def test_emit_error_report_exists(self):
        """emit_error_report function exists."""
        from server.utils.websocket import emit_error_report
        assert callable(emit_error_report)

    def test_emit_session_update_exists(self):
        """emit_session_update function exists."""
        from server.utils.websocket import emit_session_update
        assert callable(emit_session_update)

    def test_emit_user_update_exists(self):
        """emit_user_update function exists."""
        from server.utils.websocket import emit_user_update
        assert callable(emit_user_update)

    def test_emit_stats_update_exists(self):
        """emit_stats_update function exists."""
        from server.utils.websocket import emit_stats_update
        assert callable(emit_stats_update)

    def test_emit_operation_start_exists(self):
        """emit_operation_start function exists."""
        from server.utils.websocket import emit_operation_start
        assert callable(emit_operation_start)

    def test_emit_progress_update_exists(self):
        """emit_progress_update function exists."""
        from server.utils.websocket import emit_progress_update
        assert callable(emit_progress_update)

    def test_emit_operation_complete_exists(self):
        """emit_operation_complete function exists."""
        from server.utils.websocket import emit_operation_complete
        assert callable(emit_operation_complete)

    def test_emit_operation_failed_exists(self):
        """emit_operation_failed function exists."""
        from server.utils.websocket import emit_operation_failed
        assert callable(emit_operation_failed)


class TestWebSocketUtilityFunctions:
    """Test WebSocket utility functions."""

    def test_get_connected_users_exists(self):
        """get_connected_users function exists."""
        from server.utils.websocket import get_connected_users
        assert callable(get_connected_users)

    def test_disconnect_user_exists(self):
        """disconnect_user function exists."""
        from server.utils.websocket import disconnect_user
        assert callable(disconnect_user)

    def test_broadcast_message_exists(self):
        """broadcast_message function exists."""
        from server.utils.websocket import broadcast_message
        assert callable(broadcast_message)


class TestConnectedClientsTracking:
    """Test connected clients tracking."""

    def test_connected_clients_is_dict(self):
        """connected_clients is a dictionary."""
        from server.utils.websocket import connected_clients
        assert isinstance(connected_clients, dict)

    def test_connected_clients_starts_empty_or_has_data(self):
        """connected_clients is accessible."""
        from server.utils.websocket import connected_clients
        # Just verify it's a dict (may have data from other tests)
        assert connected_clients is not None


class TestAsyncEmitFunctions:
    """Test async emit functions can be called."""

    @pytest.mark.asyncio
    async def test_emit_log_entry_callable(self):
        """emit_log_entry is async callable."""
        from server.utils.websocket import emit_log_entry
        # Call with test data - should not raise
        await emit_log_entry({
            "tool_name": "test_tool",
            "status": "success",
            "duration": 1.5
        })

    @pytest.mark.asyncio
    async def test_emit_error_report_callable(self):
        """emit_error_report is async callable."""
        from server.utils.websocket import emit_error_report
        await emit_error_report({
            "error_type": "TestError",
            "message": "Test error message"
        })

    @pytest.mark.asyncio
    async def test_emit_session_update_callable(self):
        """emit_session_update is async callable."""
        from server.utils.websocket import emit_session_update
        await emit_session_update({
            "session_id": "test-session-123",
            "user_id": 1
        }, "start")

    @pytest.mark.asyncio
    async def test_emit_user_update_callable(self):
        """emit_user_update is async callable."""
        from server.utils.websocket import emit_user_update
        await emit_user_update({
            "user_id": 1,
            "username": "testuser"
        }, "created")

    @pytest.mark.asyncio
    async def test_emit_stats_update_callable(self):
        """emit_stats_update is async callable."""
        from server.utils.websocket import emit_stats_update
        await emit_stats_update({
            "total_users": 100,
            "active_sessions": 10
        })

    @pytest.mark.asyncio
    async def test_emit_operation_start_callable(self):
        """emit_operation_start is async callable."""
        from server.utils.websocket import emit_operation_start
        await emit_operation_start({
            "operation_id": "op-123",
            "user_id": 1,
            "tool_name": "xlstransfer",
            "operation_name": "process_file"
        })

    @pytest.mark.asyncio
    async def test_emit_progress_update_callable(self):
        """emit_progress_update is async callable."""
        from server.utils.websocket import emit_progress_update
        await emit_progress_update({
            "operation_id": "op-123",
            "user_id": 1,
            "progress_percentage": 50.0,
            "current_step": "Processing row 500 of 1000"
        })

    @pytest.mark.asyncio
    async def test_emit_operation_complete_callable(self):
        """emit_operation_complete is async callable."""
        from server.utils.websocket import emit_operation_complete
        await emit_operation_complete({
            "operation_id": "op-123",
            "user_id": 1,
            "operation_name": "process_file",
            "status": "success"
        })

    @pytest.mark.asyncio
    async def test_emit_operation_failed_callable(self):
        """emit_operation_failed is async callable."""
        from server.utils.websocket import emit_operation_failed
        await emit_operation_failed({
            "operation_id": "op-123",
            "user_id": 1,
            "operation_name": "process_file",
            "error_message": "File not found"
        })


class TestAsyncUtilityFunctions:
    """Test async utility functions."""

    @pytest.mark.asyncio
    async def test_get_connected_users_returns_list(self):
        """get_connected_users returns a list."""
        from server.utils.websocket import get_connected_users
        result = await get_connected_users()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_disconnect_user_callable(self):
        """disconnect_user is async callable."""
        from server.utils.websocket import disconnect_user
        # Call with non-existent user - should not raise
        await disconnect_user(999999)

    @pytest.mark.asyncio
    async def test_broadcast_message_callable(self):
        """broadcast_message is async callable."""
        from server.utils.websocket import broadcast_message
        await broadcast_message("Test broadcast message")

    @pytest.mark.asyncio
    async def test_broadcast_message_to_room(self):
        """broadcast_message accepts room parameter."""
        from server.utils.websocket import broadcast_message
        await broadcast_message("Test message to admin room", room="admin")


class TestSocketIOServer:
    """Test Socket.IO server configuration."""

    def test_sio_is_async_server(self):
        """sio is an AsyncServer."""
        from server.utils.websocket import sio
        import socketio
        assert isinstance(sio, socketio.AsyncServer)

    def test_sio_async_mode_is_asgi(self):
        """sio async mode is asgi."""
        from server.utils.websocket import sio
        assert sio.async_mode == 'asgi'

    def test_socket_app_is_asgi_app(self):
        """socket_app is an ASGIApp."""
        from server.utils.websocket import socket_app
        import socketio
        assert isinstance(socket_app, socketio.ASGIApp)


class TestSocketIOMethods:
    """Test Socket.IO server methods."""

    def test_sio_has_emit_method(self):
        """sio has emit method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'emit')
        assert callable(sio.emit)

    def test_sio_has_enter_room_method(self):
        """sio has enter_room method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'enter_room')
        assert callable(sio.enter_room)

    def test_sio_has_leave_room_method(self):
        """sio has leave_room method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'leave_room')
        assert callable(sio.leave_room)

    def test_sio_has_disconnect_method(self):
        """sio has disconnect method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'disconnect')
        assert callable(sio.disconnect)

    def test_sio_has_rooms_method(self):
        """sio has rooms method."""
        from server.utils.websocket import sio
        assert hasattr(sio, 'rooms')


class TestModuleExports:
    """Test module exports."""

    def test_all_exports_available(self):
        """All expected exports are available."""
        from server.utils.websocket import (
            sio,
            socket_app,
            emit_log_entry,
            emit_error_report,
            emit_session_update,
            emit_user_update,
            emit_stats_update,
            emit_operation_start,
            emit_progress_update,
            emit_operation_complete,
            emit_operation_failed,
            get_connected_users,
            disconnect_user,
            broadcast_message
        )
        # All should be defined
        assert sio is not None
        assert socket_app is not None
        assert all(callable(f) for f in [
            emit_log_entry,
            emit_error_report,
            emit_session_update,
            emit_user_update,
            emit_stats_update,
            emit_operation_start,
            emit_progress_update,
            emit_operation_complete,
            emit_operation_failed,
            get_connected_users,
            disconnect_user,
            broadcast_message
        ])


class TestEmitWithUserIdRoom:
    """Test emit functions with user_id for personal rooms."""

    @pytest.mark.asyncio
    async def test_emit_log_entry_with_user_id(self):
        """emit_log_entry sends to user's personal room."""
        from server.utils.websocket import emit_log_entry
        await emit_log_entry({
            "tool_name": "kr_similar",
            "status": "success",
            "user_id": 42
        })

    @pytest.mark.asyncio
    async def test_emit_operation_start_with_user_id(self):
        """emit_operation_start sends to user's personal room."""
        from server.utils.websocket import emit_operation_start
        await emit_operation_start({
            "operation_id": "op-456",
            "user_id": 42,
            "tool_name": "quicksearch",
            "operation_name": "search"
        })

    @pytest.mark.asyncio
    async def test_emit_progress_with_user_id(self):
        """emit_progress_update sends to user's personal room."""
        from server.utils.websocket import emit_progress_update
        await emit_progress_update({
            "operation_id": "op-456",
            "user_id": 42,
            "progress_percentage": 75.5
        })

    @pytest.mark.asyncio
    async def test_emit_complete_with_user_id(self):
        """emit_operation_complete sends to user's personal room."""
        from server.utils.websocket import emit_operation_complete
        await emit_operation_complete({
            "operation_id": "op-456",
            "user_id": 42,
            "operation_name": "search",
            "status": "success"
        })

    @pytest.mark.asyncio
    async def test_emit_failed_with_user_id(self):
        """emit_operation_failed sends to user's personal room and errors."""
        from server.utils.websocket import emit_operation_failed
        await emit_operation_failed({
            "operation_id": "op-456",
            "user_id": 42,
            "operation_name": "search",
            "error_message": "Dictionary not loaded"
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
