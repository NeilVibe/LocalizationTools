"""
LDM Services

Business logic extracted from tm_manager.py.
"""

# EMB-001: Auto-indexing service
from .indexing_service import (
    trigger_auto_indexing,
    trigger_auto_indexing_async,
    check_indexing_needed,
)

# Services will be populated during Phase 3 migration
# from .tm_service import TMService
# from .entry_service import EntryService
# from .file_service import FileService
# from .project_service import ProjectService

__all__ = [
    # EMB-001: Auto-indexing
    "trigger_auto_indexing",
    "trigger_auto_indexing_async", 
    "check_indexing_needed",
]
