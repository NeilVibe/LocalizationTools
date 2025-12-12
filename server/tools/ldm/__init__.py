"""
LDM (LanguageData Manager) - Real-time collaborative CAT tool

Modules:
- api: REST API endpoints for projects, folders, files, rows
- websocket: Real-time sync via WebSocket
- models: Database models (LDMProject, LDMFolder, LDMFile, LDMRow)
- file_handlers: Parse TXT/XML files into database rows
- tm_indexer: TM indexing and 5-Tier Cascade search
"""

from server.tools.ldm.tm_indexer import (
    TMIndexer,
    TMSearcher,
    TMSyncManager,
    normalize_newlines_universal,
    normalize_for_hash,
    normalize_for_embedding,
    DEFAULT_THRESHOLD,
    NPC_THRESHOLD,
)

__all__ = [
    'api',
    'websocket',
    'models',
    'TMIndexer',
    'TMSearcher',
    'TMSyncManager',
    'normalize_newlines_universal',
    'normalize_for_hash',
    'normalize_for_embedding',
    'DEFAULT_THRESHOLD',
    'NPC_THRESHOLD',
]
