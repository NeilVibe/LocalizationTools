"""
Shared utilities for LocaNext tools.

This module provides common functionality used across multiple tools:
- FAISSManager: Centralized FAISS HNSW index management
- EmbeddingEngine: Unified embedding interface (Model2Vec, Qwen)
- TMLoader: Unified TM entry loading (LIMIT-002)
"""

from .faiss_manager import FAISSManager, ThreadSafeIndex
from .embedding_engine import (
    EmbeddingEngine,
    Model2VecEngine,
    QwenEngine,
    Model2VecModelAdapter,
    get_embedding_engine,
    get_available_engines,
    get_current_engine_name,
    set_current_engine,
    preload_engine,
    unload_engine,
    is_light_mode,
    get_model2vec_adapter,
)
from .tm_loader import TMLoader

__all__ = [
    "FAISSManager",
    "ThreadSafeIndex",
    "EmbeddingEngine",
    "Model2VecEngine",
    "QwenEngine",
    "Model2VecModelAdapter",
    "get_embedding_engine",
    "get_available_engines",
    "get_current_engine_name",
    "set_current_engine",
    "preload_engine",
    "unload_engine",
    "is_light_mode",
    "get_model2vec_adapter",
    "TMLoader",
]
