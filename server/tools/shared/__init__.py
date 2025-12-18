"""
Shared utilities for LocaNext tools.

This module provides common functionality used across multiple tools:
- FAISSManager: Centralized FAISS HNSW index management
- EmbeddingEngine: Unified embedding interface (Model2Vec, Qwen)
"""

from .faiss_manager import FAISSManager
from .embedding_engine import (
    EmbeddingEngine,
    Model2VecEngine,
    QwenEngine,
    get_embedding_engine,
    get_available_engines,
    get_current_engine_name,
    set_current_engine,
    preload_engine,
    unload_engine,
)

__all__ = [
    "FAISSManager",
    "EmbeddingEngine",
    "Model2VecEngine",
    "QwenEngine",
    "get_embedding_engine",
    "get_available_engines",
    "get_current_engine_name",
    "set_current_engine",
    "preload_engine",
    "unload_engine",
]
