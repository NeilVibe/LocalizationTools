"""
LDM WebSocket Handlers

Real-time collaboration features for LanguageData Manager:
- File room management (join/leave file for updates)
- Cell update broadcasts (when someone edits a row)
- Presence tracking (who's viewing which file)
- Row locking (prevent conflicts when editing)
"""

from typing import Dict, Set, Optional
from datetime import datetime
import asyncio
from loguru import logger

# Import the shared Socket.IO instance
from server.utils.websocket import sio, connected_clients

# Debug: Log when module is imported (confirms event handlers will be registered)
logger.info("LDM WebSocket module loading - registering event handlers...")


# ============================================================================
# LDM State Management
# ============================================================================

# Track file viewers: file_id -> set of {sid, user_id, username}
ldm_file_viewers: Dict[int, Set[tuple]] = {}

# Track active row locks: (file_id, row_id) -> {sid, user_id, username, locked_at}
ldm_row_locks: Dict[tuple, Dict] = {}


# ============================================================================
# Room Management
# ============================================================================

@sio.event
async def ldm_join_file(sid, data):
    """
    Join a file room for real-time updates.

    Data: {file_id: int}
    """
    file_id = data.get('file_id')
    if not file_id:
        await sio.emit('ldm_error', {'message': 'file_id required'}, to=sid)
        return

    client_info = connected_clients.get(sid)
    if not client_info:
        await sio.emit('ldm_error', {'message': 'Not authenticated'}, to=sid)
        return

    room_name = f"ldm_file_{file_id}"

    # Join the file room
    await sio.enter_room(sid, room_name)
    client_info['rooms'].add(room_name)

    # Track viewer
    if file_id not in ldm_file_viewers:
        ldm_file_viewers[file_id] = set()

    viewer_info = (sid, client_info.get('user_id'), client_info.get('username'))
    ldm_file_viewers[file_id].add(viewer_info)

    logger.info(f"LDM: User {client_info.get('username')} joined file {file_id}")

    # Confirm join
    await sio.emit('ldm_file_joined', {
        'file_id': file_id,
        'message': 'Joined file room'
    }, to=sid)

    # Broadcast updated presence to all viewers
    await broadcast_file_presence(file_id)


@sio.event
async def ldm_leave_file(sid, data):
    """
    Leave a file room.

    Data: {file_id: int}
    """
    file_id = data.get('file_id')
    if not file_id:
        return

    room_name = f"ldm_file_{file_id}"

    # Leave the room
    await sio.leave_room(sid, room_name)
    if sid in connected_clients:
        connected_clients[sid]['rooms'].discard(room_name)

    # Remove from viewers
    if file_id in ldm_file_viewers:
        ldm_file_viewers[file_id] = {
            v for v in ldm_file_viewers[file_id] if v[0] != sid
        }
        if not ldm_file_viewers[file_id]:
            del ldm_file_viewers[file_id]

    # Release any locks held by this user
    await release_user_locks(sid, file_id)

    client_info = connected_clients.get(sid, {})
    logger.info(f"LDM: User {client_info.get('username')} left file {file_id}")

    # Broadcast updated presence
    await broadcast_file_presence(file_id)


# ============================================================================
# Presence Tracking
# ============================================================================

async def broadcast_file_presence(file_id: int):
    """
    Broadcast current viewers of a file to all viewers.
    """
    room_name = f"ldm_file_{file_id}"

    viewers = []
    if file_id in ldm_file_viewers:
        for sid, user_id, username in ldm_file_viewers[file_id]:
            viewers.append({
                'user_id': user_id,
                'username': username
            })

    await sio.emit('ldm_presence', {
        'file_id': file_id,
        'viewers': viewers,
        'count': len(viewers)
    }, room=room_name)


@sio.event
async def ldm_get_presence(sid, data):
    """
    Get current viewers of a file.

    Data: {file_id: int}
    """
    file_id = data.get('file_id')
    if not file_id:
        return

    viewers = []
    if file_id in ldm_file_viewers:
        for _, user_id, username in ldm_file_viewers[file_id]:
            viewers.append({
                'user_id': user_id,
                'username': username
            })

    await sio.emit('ldm_presence', {
        'file_id': file_id,
        'viewers': viewers,
        'count': len(viewers)
    }, to=sid)


# ============================================================================
# Row Locking
# ============================================================================

@sio.event
async def ldm_lock_row(sid, data):
    """
    Lock a row for editing (prevents others from editing same row).

    Data: {file_id: int, row_id: int}

    DEBUG NOTE: If this event is never received while ldm_join_file works,
    check for client-side issues (socket reconnection, auth expiry).
    The @sio.event decorator should register this handler at module import time.
    """
    # Debug: Log that handler was invoked
    logger.debug(f"LDM DEBUG: ldm_lock_row handler invoked - sid={sid}, data={data}")

    file_id = data.get('file_id')
    row_id = data.get('row_id')

    logger.info(f"LDM: Lock request for row {row_id} in file {file_id} from {sid}")

    if not file_id or not row_id:
        await sio.emit('ldm_error', {'message': 'file_id and row_id required'}, to=sid)
        return

    client_info = connected_clients.get(sid)
    if not client_info:
        logger.warning(f"LDM: Lock denied - client {sid} not authenticated")
        await sio.emit('ldm_error', {'message': 'Not authenticated'}, to=sid)
        return

    lock_key = (file_id, row_id)

    # Check if row is already locked by someone else
    if lock_key in ldm_row_locks:
        existing_lock = ldm_row_locks[lock_key]
        logger.info(f"LDM: Lock exists for row {row_id}: sid={existing_lock['sid']}, username={existing_lock['username']}")
        if existing_lock['sid'] != sid:
            # Row is locked by another user
            logger.warning(f"LDM: Lock denied for row {row_id} - already locked by {existing_lock['username']}")
            await sio.emit('ldm_lock_denied', {
                'file_id': file_id,
                'row_id': row_id,
                'locked_by': existing_lock['username'],
                'locked_at': existing_lock['locked_at'].isoformat()
            }, to=sid)
            return

    # Grant the lock
    ldm_row_locks[lock_key] = {
        'sid': sid,
        'user_id': client_info.get('user_id'),
        'username': client_info.get('username'),
        'locked_at': datetime.utcnow()
    }

    logger.info(f"LDM: Row {row_id} locked by {client_info.get('username')} in file {file_id}")

    # Confirm lock to requester
    await sio.emit('ldm_lock_granted', {
        'file_id': file_id,
        'row_id': row_id
    }, to=sid)

    # Broadcast lock to all file viewers
    room_name = f"ldm_file_{file_id}"
    await sio.emit('ldm_row_locked', {
        'file_id': file_id,
        'row_id': row_id,
        'locked_by': client_info.get('username'),
        'user_id': client_info.get('user_id')
    }, room=room_name, skip_sid=sid)


@sio.event
async def ldm_unlock_row(sid, data):
    """
    Release a row lock.

    Data: {file_id: int, row_id: int}
    """
    file_id = data.get('file_id')
    row_id = data.get('row_id')

    if not file_id or not row_id:
        return

    lock_key = (file_id, row_id)

    # Only the lock owner can release
    if lock_key in ldm_row_locks:
        existing_lock = ldm_row_locks[lock_key]
        if existing_lock['sid'] == sid:
            del ldm_row_locks[lock_key]

            client_info = connected_clients.get(sid, {})
            logger.info(f"LDM: Row {row_id} unlocked by {client_info.get('username')} in file {file_id}")

            # Confirm unlock
            await sio.emit('ldm_lock_released', {
                'file_id': file_id,
                'row_id': row_id
            }, to=sid)

            # Broadcast unlock to all file viewers
            room_name = f"ldm_file_{file_id}"
            await sio.emit('ldm_row_unlocked', {
                'file_id': file_id,
                'row_id': row_id
            }, room=room_name)


async def release_user_locks(sid: str, file_id: Optional[int] = None):
    """
    Release all locks held by a user (on disconnect or file leave).
    """
    locks_to_remove = []

    for lock_key, lock_info in ldm_row_locks.items():
        if lock_info['sid'] == sid:
            if file_id is None or lock_key[0] == file_id:
                locks_to_remove.append(lock_key)

    for lock_key in locks_to_remove:
        del ldm_row_locks[lock_key]

        f_id, r_id = lock_key
        room_name = f"ldm_file_{f_id}"
        await sio.emit('ldm_row_unlocked', {
            'file_id': f_id,
            'row_id': r_id
        }, room=room_name)


@sio.event
async def ldm_get_locks(sid, data):
    """
    Get all locked rows for a file.

    Data: {file_id: int}
    """
    file_id = data.get('file_id')
    if not file_id:
        return

    # Clean up stale locks (no username = invalid session)
    stale_keys = []
    for (f_id, r_id), lock_info in ldm_row_locks.items():
        if f_id == file_id and not lock_info.get('username'):
            stale_keys.append((f_id, r_id))
    for key in stale_keys:
        logger.warning(f"LDM: Removing stale lock: {key}")
        del ldm_row_locks[key]

    locks = []
    for (f_id, r_id), lock_info in ldm_row_locks.items():
        if f_id == file_id:
            locks.append({
                'row_id': r_id,
                'locked_by': lock_info['username'],
                'user_id': lock_info['user_id'],
                'locked_at': lock_info['locked_at'].isoformat()
            })

    await sio.emit('ldm_locks', {
        'file_id': file_id,
        'locks': locks
    }, to=sid)


# ============================================================================
# Cell Update Broadcasting
# ============================================================================

async def broadcast_cell_update(
    file_id: int,
    row_id: int,
    row_num: int,
    target: Optional[str],
    status: str,
    updated_by: int,
    updated_by_username: str
):
    """
    Broadcast a cell update to all viewers of a file.

    Called from the API after a successful row update.
    """
    room_name = f"ldm_file_{file_id}"

    await sio.emit('ldm_cell_update', {
        'file_id': file_id,
        'row_id': row_id,
        'row_num': row_num,
        'target': target,
        'status': status,
        'updated_by': updated_by,
        'updated_by_username': updated_by_username,
        'updated_at': datetime.utcnow().isoformat()
    }, room=room_name)

    logger.info(f"LDM: Cell update broadcast for row {row_id} in file {file_id}")


async def broadcast_row_added(
    file_id: int,
    row_data: Dict
):
    """
    Broadcast when a new row is added (rare, but possible).
    """
    room_name = f"ldm_file_{file_id}"

    await sio.emit('ldm_row_added', {
        'file_id': file_id,
        'row': row_data
    }, room=room_name)


async def broadcast_row_deleted(
    file_id: int,
    row_id: int
):
    """
    Broadcast when a row is deleted.
    """
    room_name = f"ldm_file_{file_id}"

    await sio.emit('ldm_row_deleted', {
        'file_id': file_id,
        'row_id': row_id
    }, room=room_name)


# ============================================================================
# Disconnect Handler Extension
# ============================================================================

# Store original disconnect handler
_original_disconnect = None


def setup_ldm_disconnect_handler():
    """
    Extend the disconnect handler to clean up LDM state.
    """
    global _original_disconnect

    # Get original handler if exists
    if 'disconnect' in sio.handlers.get('/', {}):
        _original_disconnect = sio.handlers['/']['disconnect']

    @sio.event
    async def disconnect(sid):
        # Clean up LDM state first
        # Remove from all file viewer lists
        files_to_update = []
        for file_id, viewers in list(ldm_file_viewers.items()):
            ldm_file_viewers[file_id] = {v for v in viewers if v[0] != sid}
            if ldm_file_viewers[file_id]:
                files_to_update.append(file_id)
            else:
                del ldm_file_viewers[file_id]

        # Release all locks
        await release_user_locks(sid)

        # Update presence for affected files
        for file_id in files_to_update:
            await broadcast_file_presence(file_id)

        # Call original disconnect handler
        if _original_disconnect:
            await _original_disconnect(sid)


# ============================================================================
# Utility Functions
# ============================================================================

def get_file_viewers(file_id: int) -> list:
    """Get list of users viewing a file."""
    viewers = []
    if file_id in ldm_file_viewers:
        for _, user_id, username in ldm_file_viewers[file_id]:
            viewers.append({
                'user_id': user_id,
                'username': username
            })
    return viewers


def get_file_locks(file_id: int) -> list:
    """Get list of locked rows in a file."""
    locks = []
    for (f_id, r_id), lock_info in ldm_row_locks.items():
        if f_id == file_id:
            locks.append({
                'row_id': r_id,
                'locked_by': lock_info['username'],
                'user_id': lock_info['user_id']
            })
    return locks


def is_row_locked(file_id: int, row_id: int, exclude_sid: Optional[str] = None) -> Optional[Dict]:
    """
    Check if a row is locked.

    Returns lock info if locked, None if not locked.
    If exclude_sid is provided, ignores locks by that session.
    """
    lock_key = (file_id, row_id)
    if lock_key in ldm_row_locks:
        lock_info = ldm_row_locks[lock_key]
        if exclude_sid and lock_info['sid'] == exclude_sid:
            return None
        return {
            'locked_by': lock_info['username'],
            'user_id': lock_info['user_id']
        }
    return None


# ============================================================================
# Export
# ============================================================================

__all__ = [
    'broadcast_cell_update',
    'broadcast_row_added',
    'broadcast_row_deleted',
    'broadcast_file_presence',
    'get_file_viewers',
    'get_file_locks',
    'is_row_locked',
    'setup_ldm_disconnect_handler'
]

# Auto-setup the disconnect handler when module is imported
setup_ldm_disconnect_handler()

# Debug: Confirm all handlers registered
logger.info("LDM WebSocket module loaded - handlers registered: ldm_join_file, ldm_leave_file, ldm_lock_row, ldm_unlock_row, ldm_get_presence, ldm_get_locks")
