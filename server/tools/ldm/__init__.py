"""
LDM (LanguageData Manager) - Real-time collaborative CAT tool

Modules:
- api: REST API endpoints for projects, folders, files, rows
- websocket: Real-time sync via WebSocket
- models: Database models (LDMProject, LDMFolder, LDMFile, LDMRow)
- file_handlers: Parse TXT/XML files into database rows
"""

__all__ = ['api', 'websocket', 'models']
