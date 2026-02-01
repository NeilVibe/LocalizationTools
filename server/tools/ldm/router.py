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
- routes/qa.py           - QA checks (P2: Auto-LQA)
- routes/grammar.py      - Grammar/spelling check (P5: LanguageTool)
- routes/maintenance.py  - EMB-003: TM stale index check + sync
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
from .routes.qa import router as qa_router
from .routes.grammar import router as grammar_router
from .routes.platforms import router as platforms_router
from .routes.tm_assignment import router as tm_assignment_router
from .routes.trash import router as trash_router  # EXPLORER-008: Recycle Bin
from .routes.search import router as search_router  # EXPLORER-004: Explorer Search
from .routes.capabilities import router as capabilities_router  # EXPLORER-009: Privileged Operations
from .routes.maintenance import router as maintenance_router  # EMB-003: TM Maintenance

# =============================================================================
# Include all routers
# =============================================================================

router.include_router(health_router)
router.include_router(platforms_router)  # Platforms before projects (TM Hierarchy)
router.include_router(tm_assignment_router)  # TM assignment (TM Hierarchy)
router.include_router(projects_router)
router.include_router(folders_router)
router.include_router(files_router)
router.include_router(rows_router)
# UI-052 FIX: tm_search_router MUST come before tm_crud_router
# because /tm/suggest must be matched before /tm/{tm_id}
router.include_router(tm_search_router)  # Has /tm/suggest - specific route first
router.include_router(tm_crud_router)    # Has /tm/{tm_id} - generic route after
router.include_router(tm_entries_router)
router.include_router(tm_indexes_router)
router.include_router(tm_linking_router)
router.include_router(pretranslate_router)
router.include_router(sync_router)
router.include_router(settings_router)
router.include_router(qa_router)
router.include_router(grammar_router)
router.include_router(trash_router)  # EXPLORER-008: Recycle Bin
router.include_router(search_router)  # EXPLORER-004: Explorer Search
router.include_router(capabilities_router)  # EXPLORER-009: Privileged Operations (Admin)
router.include_router(maintenance_router)  # EMB-003: TM Maintenance (stale check + sync)

# =============================================================================
# WebSocket endpoint (still needs special handling)
# =============================================================================
# WebSocket routes are imported from websocket.py and need to be added
# to the main app separately due to FastAPI WebSocket handling requirements.
# See: server/tools/ldm/websocket.py
