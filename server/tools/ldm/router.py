"""
LDM Main Router - Aggregates all LDM sub-routers.

P37 REFACTORING: All routes migrated from 3144-line api.py to modular files.

Structure:
- routes/health.py       - Health check
- routes/projects.py     - Project CRUD
- routes/folders.py      - Folder CRUD
- routes/files.py        - File upload/download/list
- routes/rows.py         - Row operations + project tree
- routes/tm_crud.py      - TM upload/list/delete/export
- routes/tm_search.py    - TM suggest/search
- routes/tm_entries.py   - TM entry CRUD + confirm
- routes/tm_indexes.py   - TM index build/sync
- routes/tm_linking.py   - Project-TM linking
- routes/pretranslate.py - Pretranslation
- routes/sync.py         - Offline-to-online sync
- routes/settings.py     - Embedding engine settings
"""

from fastapi import APIRouter

# Create main router with LDM prefix
router = APIRouter(prefix="/api/ldm", tags=["LDM"])

# =============================================================================
# Import all sub-routers
# =============================================================================

from .routes.health import router as health_router
from .routes.projects import router as projects_router
from .routes.folders import router as folders_router
from .routes.files import router as files_router
from .routes.rows import router as rows_router
from .routes.tm_crud import router as tm_crud_router
from .routes.tm_search import router as tm_search_router
from .routes.tm_entries import router as tm_entries_router
from .routes.tm_indexes import router as tm_indexes_router
from .routes.tm_linking import router as tm_linking_router
from .routes.pretranslate import router as pretranslate_router
from .routes.sync import router as sync_router
from .routes.settings import router as settings_router

# =============================================================================
# Include all routers
# =============================================================================

router.include_router(health_router)
router.include_router(projects_router)
router.include_router(folders_router)
router.include_router(files_router)
router.include_router(rows_router)
router.include_router(tm_crud_router)
router.include_router(tm_search_router)
router.include_router(tm_entries_router)
router.include_router(tm_indexes_router)
router.include_router(tm_linking_router)
router.include_router(pretranslate_router)
router.include_router(sync_router)
router.include_router(settings_router)

# =============================================================================
# WebSocket endpoint (still needs special handling)
# =============================================================================
# WebSocket routes are imported from websocket.py and need to be added
# to the main app separately due to FastAPI WebSocket handling requirements.
# See: server/tools/ldm/websocket.py
