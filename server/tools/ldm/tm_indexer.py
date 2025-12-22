"""
LDM Translation Memory Indexer - Re-export Module.

P37 REFACTORING: Split 2105-line monolith into modular components.

Components:
- indexing/utils.py      - Normalization functions
- indexing/indexer.py    - TMIndexer (build/load/delete indexes)
- indexing/searcher.py   - TMSearcher (5-Tier Cascade search)
- indexing/sync_manager.py - TMSyncManager (DB<->PKL sync)

This file re-exports everything for backward compatibility.
Existing code using `from server.tools.ldm.tm_indexer import X` continues to work.
"""

# Re-export utilities
from .indexing.utils import (
    normalize_newlines_universal,
    normalize_for_hash,
    normalize_for_embedding,
)

# Re-export thresholds
from .indexing.searcher import (
    DEFAULT_THRESHOLD,
    NPC_THRESHOLD,
)

# Re-export classes
from .indexing.indexer import TMIndexer
from .indexing.searcher import TMSearcher
from .indexing.sync_manager import TMSyncManager

# For code that checks MODELS_AVAILABLE
try:
    import faiss
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Re-export all public names
__all__ = [
    # Utilities
    "normalize_newlines_universal",
    "normalize_for_hash",
    "normalize_for_embedding",
    # Thresholds
    "DEFAULT_THRESHOLD",
    "NPC_THRESHOLD",
    # Classes
    "TMIndexer",
    "TMSearcher",
    "TMSyncManager",
    # Constants
    "MODELS_AVAILABLE",
]
