"""
WebSocket Manager

Real-time communication using Socket.IO for live updates.
"""

import socketio
from loguru import logger
from typing import Dict, List, Optional
import asyncio

# Import CORS settings from config
from server import config


# Create async Socket.IO server
# Uses same CORS settings as main app for consistency
_ws_cors_origins = '*' if config.CORS_ALLOW_ALL else config.CORS_ORIGINS

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=_ws_cors_origins,
    logger=False,
    engineio_logger=False
)

if config.CORS_ALLOW_ALL:
    logger.warning("WebSocket CORS: Allowing ALL origins (development mode)")
else:
    logger.info(f"WebSocket CORS: Restricted to {len(config.CORS_ORIGINS)} whitelisted origins")

# Socket.IO ASGI app
# We'll use the standard /socket.io path for compatibility
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='/socket.io'
)


# ============================================================================
# Connection Management
# ============================================================================

# Track connected clients
connected_clients: Dict[str, Dict] = {}  # sid -> {user_id, username, rooms}


@sio.event
async def connect(sid, environ, auth):
    """
    Handle client connection.

    Clients should provide auth token in the auth dict.
    """
    logger.info(f"Client connecting: {sid}")

    # Store client info
    connected_clients[sid] = {
        'user_id': None,
        'username': None,
        'rooms': set(),
        'connected_at': asyncio.get_event_loop().time()
    }

    # Authenticate if token provided
    if auth and 'token' in auth:
        from server.utils.auth import verify_token

        payload = verify_token(auth['token'])
        if payload:
            user_id = payload.get('user_id')
            username = payload.get('username')

            connected_clients[sid]['user_id'] = user_id
            connected_clients[sid]['username'] = username

            # Auto-join user's personal room
            await sio.enter_room(sid, f"user_{user_id}")
            connected_clients[sid]['rooms'].add(f"user_{user_id}")

            logger.info(f"Client authenticated: {username} (ID: {user_id})")

            # Send welcome message
            await sio.emit('authenticated', {
                'user_id': user_id,
                'username': username,
                'message': 'Successfully authenticated'
            }, to=sid)
        else:
            logger.warning(f"Invalid token for client {sid}")
            await sio.emit('auth_error', {'message': 'Invalid token'}, to=sid)
    else:
        logger.info(f"Client {sid} connected without authentication")

    # Notify about connection
    await sio.emit('connected', {
        'message': 'Connected to LocalizationTools server',
        'sid': sid
    }, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    client_info = connected_clients.get(sid, {})
    username = client_info.get('username', 'Unknown')

    logger.info(f"Client disconnecting: {sid} ({username})")

    # Remove from all rooms
    rooms = client_info.get('rooms', set())
    for room in rooms:
        await sio.leave_room(sid, room)

    # Remove from connected clients
    if sid in connected_clients:
        del connected_clients[sid]


# ============================================================================
# Room Management
# ============================================================================

@sio.event
async def join_room(sid, data):
    """
    Join a specific room for targeted updates.

    Rooms: 'admin', 'logs', 'sessions', 'errors', etc.
    """
    room = data.get('room')
    if not room:
        await sio.emit('error', {'message': 'Room name required'}, to=sid)
        return

    client_info = connected_clients.get(sid)
    if not client_info:
        await sio.emit('error', {'message': 'Not connected'}, to=sid)
        return

    # Check permissions for certain rooms
    if room == 'admin':
        # Only admin users can join admin room
        # For now, we'll allow it - add auth check as needed
        pass

    await sio.enter_room(sid, room)
    connected_clients[sid]['rooms'].add(room)

    logger.info(f"Client {sid} joined room: {room}")
    await sio.emit('room_joined', {'room': room}, to=sid)


@sio.event
async def leave_room(sid, data):
    """Leave a specific room."""
    room = data.get('room')
    if not room:
        return

    await sio.leave_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]['rooms'].discard(room)

    logger.info(f"Client {sid} left room: {room}")
    await sio.emit('room_left', {'room': room}, to=sid)


# ============================================================================
# Event Emitters (for server to broadcast)
# ============================================================================

async def emit_log_entry(log_data: Dict):
    """
    Broadcast new log entry to subscribers.

    Args:
        log_data: Log entry data (tool_name, status, duration, etc.)
    """
    await sio.emit('log_entry', log_data, room='logs')

    # Also send to user's personal room
    user_id = log_data.get('user_id')
    if user_id:
        await sio.emit('log_entry', log_data, room=f"user_{user_id}")


async def emit_error_report(error_data: Dict):
    """
    Broadcast error report to admins.

    Args:
        error_data: Error report data
    """
    await sio.emit('error_report', error_data, room='admin')
    await sio.emit('error_report', error_data, room='errors')


async def emit_session_update(session_data: Dict, event_type: str):
    """
    Broadcast session update.

    Args:
        session_data: Session data
        event_type: 'start', 'heartbeat', 'end'
    """
    await sio.emit('session_update', {
        'type': event_type,
        'session': session_data
    }, room='sessions')

    # Send to admin room
    await sio.emit('session_update', {
        'type': event_type,
        'session': session_data
    }, room='admin')


async def emit_user_update(user_data: Dict, event_type: str):
    """
    Broadcast user update (registration, activation, etc.).

    Args:
        user_data: User data
        event_type: 'created', 'activated', 'deactivated'
    """
    await sio.emit('user_update', {
        'type': event_type,
        'user': user_data
    }, room='admin')


async def emit_stats_update(stats_data: Dict):
    """
    Broadcast statistics update.

    Args:
        stats_data: Statistics data
    """
    await sio.emit('stats_update', stats_data, room='admin')


async def emit_operation_start(operation_data: Dict):
    """
    Broadcast operation start event.

    Args:
        operation_data: Operation data (operation_id, user_id, tool_name, operation_name, etc.)
    """
    user_id = operation_data.get('user_id')

    # Send to user's personal room
    if user_id:
        await sio.emit('operation_start', operation_data, room=f"user_{user_id}")

    # Send to progress subscribers
    await sio.emit('operation_start', operation_data, room='progress')

    logger.info(f"Emitted operation_start for user {user_id}: {operation_data.get('operation_name')}")


async def emit_progress_update(operation_data: Dict):
    """
    Broadcast real-time progress update.

    Args:
        operation_data: Operation data including progress_percentage, current_step, etc.
    """
    user_id = operation_data.get('user_id')
    operation_id = operation_data.get('operation_id')

    # Send to user's personal room
    if user_id:
        await sio.emit('progress_update', operation_data, room=f"user_{user_id}")

    # Send to progress subscribers
    await sio.emit('progress_update', operation_data, room='progress')

    logger.debug(f"Emitted progress_update for operation {operation_id}: {operation_data.get('progress_percentage', 0):.1f}%")


async def emit_operation_complete(operation_data: Dict):
    """
    Broadcast operation completion event.

    Args:
        operation_data: Operation data with final status
    """
    user_id = operation_data.get('user_id')

    # Send to user's personal room
    if user_id:
        await sio.emit('operation_complete', operation_data, room=f"user_{user_id}")

    # Send to progress subscribers
    await sio.emit('operation_complete', operation_data, room='progress')

    logger.success(f"Emitted operation_complete for user {user_id}: {operation_data.get('operation_name')}")


async def emit_operation_failed(operation_data: Dict):
    """
    Broadcast operation failure event.

    Args:
        operation_data: Operation data with error details
    """
    user_id = operation_data.get('user_id')

    # Send to user's personal room
    if user_id:
        await sio.emit('operation_failed', operation_data, room=f"user_{user_id}")

    # Send to progress subscribers and errors room
    await sio.emit('operation_failed', operation_data, room='progress')
    await sio.emit('operation_failed', operation_data, room='errors')

    logger.error(f"Emitted operation_failed for user {user_id}: {operation_data.get('operation_name')} - {operation_data.get('error_message')}")


# ============================================================================
# Utility Functions
# ============================================================================

async def get_connected_users() -> List[Dict]:
    """Get list of connected users."""
    users = []
    for sid, info in connected_clients.items():
        if info.get('username'):
            users.append({
                'sid': sid,
                'user_id': info.get('user_id'),
                'username': info.get('username'),
                'rooms': list(info.get('rooms', set()))
            })
    return users


async def disconnect_user(user_id: int):
    """Disconnect all sessions for a specific user."""
    for sid, info in list(connected_clients.items()):
        if info.get('user_id') == user_id:
            await sio.disconnect(sid)
            logger.info(f"Disconnected user {user_id} (sid: {sid})")


async def broadcast_message(message: str, room: Optional[str] = None):
    """
    Broadcast a message to all clients or specific room.

    Args:
        message: Message to broadcast
        room: Optional room name (broadcasts to all if None)
    """
    await sio.emit('broadcast', {'message': message}, room=room)


# ============================================================================
# Health Check
# ============================================================================

@sio.event
async def ping(sid):
    """Ping-pong for connection health check."""
    await sio.emit('pong', to=sid)


# ============================================================================
# Client Event Handlers
# ============================================================================

@sio.event
async def subscribe(sid, data):
    """
    Subscribe to specific event types.

    Clients can subscribe to: 'logs', 'sessions', 'errors', 'stats', 'progress'
    """
    event_types = data.get('events', [])

    for event_type in event_types:
        if event_type in ['logs', 'sessions', 'errors', 'stats', 'progress', 'admin']:
            await sio.enter_room(sid, event_type)
            if sid in connected_clients:
                connected_clients[sid]['rooms'].add(event_type)

    logger.info(f"Client {sid} subscribed to: {event_types}")
    await sio.emit('subscribed', {'events': event_types}, to=sid)


@sio.event
async def unsubscribe(sid, data):
    """Unsubscribe from specific event types."""
    event_types = data.get('events', [])

    for event_type in event_types:
        await sio.leave_room(sid, event_type)
        if sid in connected_clients:
            connected_clients[sid]['rooms'].discard(event_type)

    logger.info(f"Client {sid} unsubscribed from: {event_types}")
    await sio.emit('unsubscribed', {'events': event_types}, to=sid)


# Export for use in other modules
__all__ = [
    'sio',
    'socket_app',
    'emit_log_entry',
    'emit_error_report',
    'emit_session_update',
    'emit_user_update',
    'emit_stats_update',
    'emit_operation_start',
    'emit_progress_update',
    'emit_operation_complete',
    'emit_operation_failed',
    'get_connected_users',
    'disconnect_user',
    'broadcast_message'
]
