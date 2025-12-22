"""
LDM Indexing - P37 Refactored Components.

Extracted from tm_indexer.py (2105 lines) during P37 refactoring.

Components:
- utils.py (72 lines) - Normalization functions
- indexer.py (540 lines) - TMIndexer class
- searcher.py (380 lines) - TMSearcher class (5-Tier Cascade)
- sync_manager.py (583 lines) - TMSyncManager class
"""

from .utils import (
    normalize_newlines_universal,
    normalize_for_hash,
    normalize_for_embedding,
)

from .indexer import TMIndexer
from .searcher import TMSearcher, DEFAULT_THRESHOLD, NPC_THRESHOLD
from .sync_manager import TMSyncManager

__all__ = [
    # Utils
    "normalize_newlines_universal",
    "normalize_for_hash",
    "normalize_for_embedding",
    # Classes
    "TMIndexer",
    "TMSearcher",
    "TMSyncManager",
    # Thresholds
    "DEFAULT_THRESHOLD",
    "NPC_THRESHOLD",
]
