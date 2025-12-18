"""
Embedding Engine Abstraction for LocaNext TM Search.

Provides a unified interface for generating text embeddings with multiple backends:
- Model2Vec (default): Fast, lightweight, 79x faster than Qwen
- Qwen: Deep semantic understanding, opt-in for batch/quality work

Usage:
    from server.tools.shared import EmbeddingEngine, get_embedding_engine

    # Get current engine (respects user preference)
    engine = get_embedding_engine()
    embeddings = engine.encode(["text1", "text2"])

    # Force specific engine
    engine = get_embedding_engine("qwen")
    embeddings = engine.encode(["text1", "text2"])

Engine selection is stored per-user in settings and can be changed via API/UI.
"""

import os
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional, Union
from pathlib import Path

from loguru import logger

# Global engine cache (lazy loaded)
_engines = {}
_current_engine_name = "model2vec"  # Default


class EmbeddingEngine(ABC):
    """Abstract base class for embedding engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Output embedding dimension."""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload the model to free memory."""
        pass

    @abstractmethod
    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode texts into embeddings.

        Args:
            texts: Single text or list of texts
            normalize: Whether to L2-normalize (for cosine similarity)
            show_progress: Show progress bar for large batches

        Returns:
            numpy array of shape (n_texts, dimension)
        """
        pass


class Model2VecEngine(EmbeddingEngine):
    """
    Model2Vec embedding engine - FAST and lightweight.

    Uses minishlab/potion-multilingual-128M for Korean-English TM search.
    - 101 languages supported (including Korean)
    - 79x faster embedding than Qwen
    - 256-dim embeddings (compact)
    - ~128MB model size
    - Excellent for real-time TM search
    """

    MODEL_NAME = "minishlab/potion-multilingual-128M"  # 101 languages incl Korean

    def __init__(self):
        self._model = None
        self._dimension = 256  # potion-multilingual-128M output dim

    @property
    def name(self) -> str:
        return "Model2Vec (Fast)"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        logger.info(f"Loading Model2Vec engine: {self.MODEL_NAME}")
        try:
            from model2vec import StaticModel
            self._model = StaticModel.from_pretrained(self.MODEL_NAME)
            # Update dimension from actual model
            test_emb = self._model.encode(["test"])
            self._dimension = test_emb.shape[1]
            logger.info(f"Model2Vec loaded: dim={self._dimension}")
        except Exception as e:
            logger.error(f"Failed to load Model2Vec: {e}")
            raise

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Model2Vec unloaded")

    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        if not self.is_loaded:
            self.load()

        # Handle single string
        if isinstance(texts, str):
            texts = [texts]

        # Model2Vec encode
        embeddings = self._model.encode(texts)
        embeddings = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid div by zero
            embeddings = embeddings / norms

        return embeddings


class QwenEngine(EmbeddingEngine):
    """
    Qwen embedding engine - DEEP semantic understanding.

    Uses Qwen/Qwen3-Embedding-0.6B via SentenceTransformers.
    - 600M parameters
    - 1024-dim embeddings (rich)
    - ~2.3GB model size
    - Best for batch processing, quality-critical work
    """

    MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

    def __init__(self):
        self._model = None
        self._dimension = 1024  # Qwen output dim

    @property
    def name(self) -> str:
        return "Qwen (Deep Semantic)"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        logger.info(f"Loading Qwen engine: {self.MODEL_NAME}")
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"Qwen loaded: dim={self._dimension}")
        except Exception as e:
            logger.error(f"Failed to load Qwen: {e}")
            raise

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Qwen unloaded")

    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        if not self.is_loaded:
            self.load()

        # Handle single string
        if isinstance(texts, str):
            texts = [texts]

        # SentenceTransformer encode
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        return embeddings


# =============================================================================
# Engine Registry and Selection
# =============================================================================

AVAILABLE_ENGINES = {
    "model2vec": Model2VecEngine,
    "qwen": QwenEngine,
}


def get_available_engines() -> List[dict]:
    """
    Get list of available engines with metadata.

    Returns:
        List of dicts with engine info for UI display.
    """
    return [
        {
            "id": "model2vec",
            "name": "Model2Vec (Fast)",
            "description": "79x faster, lightweight. Best for real-time search.",
            "dimension": 256,
            "memory_mb": 128,
            "default": True,
        },
        {
            "id": "qwen",
            "name": "Qwen (Deep Semantic)",
            "description": "Deep understanding. Best for batch/quality work.",
            "dimension": 1024,
            "memory_mb": 2300,
            "default": False,
        },
    ]


def get_current_engine_name() -> str:
    """Get the currently selected engine name."""
    return _current_engine_name


def set_current_engine(engine_name: str) -> None:
    """
    Set the current embedding engine.

    Args:
        engine_name: "model2vec" or "qwen"
    """
    global _current_engine_name

    if engine_name not in AVAILABLE_ENGINES:
        raise ValueError(f"Unknown engine: {engine_name}. Available: {list(AVAILABLE_ENGINES.keys())}")

    _current_engine_name = engine_name
    logger.info(f"Embedding engine set to: {engine_name}")


def get_embedding_engine(engine_name: Optional[str] = None) -> EmbeddingEngine:
    """
    Get an embedding engine instance (cached).

    Args:
        engine_name: Specific engine name, or None for current default.

    Returns:
        EmbeddingEngine instance (lazy-loaded).
    """
    global _engines

    if engine_name is None:
        engine_name = _current_engine_name

    if engine_name not in AVAILABLE_ENGINES:
        raise ValueError(f"Unknown engine: {engine_name}")

    if engine_name not in _engines:
        _engines[engine_name] = AVAILABLE_ENGINES[engine_name]()

    return _engines[engine_name]


def preload_engine(engine_name: Optional[str] = None) -> None:
    """
    Preload an engine into memory.

    Useful for warming up before user interaction.
    """
    engine = get_embedding_engine(engine_name)
    engine.load()


def unload_engine(engine_name: str) -> None:
    """
    Unload an engine to free memory.

    Useful when switching engines or low on memory.
    """
    if engine_name in _engines:
        _engines[engine_name].unload()
        del _engines[engine_name]
