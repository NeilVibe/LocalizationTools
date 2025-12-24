"""
LDM API Routes

All API endpoints split by domain.
"""

from .health import router as health_router
from .projects import router as projects_router
from .folders import router as folders_router
from .files import router as files_router
from .rows import router as rows_router
from .tm_crud import router as tm_crud_router
from .tm_entries import router as tm_entries_router
from .tm_search import router as tm_search_router
from .tm_indexes import router as tm_indexes_router
from .tm_linking import router as tm_linking_router
from .pretranslate import router as pretranslate_router
from .sync import router as sync_router
from .settings import router as settings_router
from .qa import router as qa_router

__all__ = [
    "health_router",
    "projects_router",
    "folders_router",
    "files_router",
    "rows_router",
    "tm_crud_router",
    "tm_entries_router",
    "tm_search_router",
    "tm_indexes_router",
    "tm_linking_router",
    "pretranslate_router",
    "sync_router",
    "settings_router",
    "qa_router",
]
