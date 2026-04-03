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

from server.utils.perf_timer import PerfTimer

# Global engine cache (lazy loaded)
_engines = {}
_current_engine_name = "model2vec"  # Default

# Light mode detection cache
_light_mode: Optional[bool] = None


def is_light_mode() -> bool:
    """
    Check if LocaNext is running in Light Mode (no torch/sentence-transformers).

    Lazy-checks if sentence_transformers + torch are importable, caches result.
    Returns True when Qwen/torch is NOT available -> Model2Vec only.
    """
    global _light_mode
    if _light_mode is None:
        try:
            import sentence_transformers  # noqa: F401
            import torch  # noqa: F401
            _light_mode = False
        except ImportError:
            _light_mode = True
            logger.warning("Light Mode: torch/sentence-transformers not available. Using Model2Vec only. Match quality may be reduced (256-dim vs 1024-dim).")
    return _light_mode


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

    @staticmethod
    def _find_local_model_path() -> Optional[Path]:
        """Find Model2Vec model folder.

        Priority:
        1. LOCANEXT_MODELS_PATH env var (set by main.js in production)
        2. Next to exe / project root (QuickTranslate pattern)
        """
        # Priority 1: Env var from main.js (production Electron app)
        env_path = os.environ.get("LOCANEXT_MODELS_PATH")
        logger.info(f"[Model2Vec] LOCANEXT_MODELS_PATH={env_path}")
        if env_path:
            p = Path(env_path) / "Model2Vec"
            logger.info(f"[Model2Vec] Checking env var path: {p} (is_dir={p.is_dir()}, config={p / 'config.json'})")
            if p.is_dir() and (p / "config.json").exists():
                logger.info(f"[Model2Vec] FOUND via LOCANEXT_MODELS_PATH: {p}")
                return p
            else:
                logger.warning(f"[Model2Vec] Env var path exists but no Model2Vec: {p}")

        # Priority 2: Next to exe or project root (DEV mode / standalone)
        current = Path(__file__).resolve().parent
        for _ in range(10):
            candidate = current / "Model2Vec"
            if candidate.is_dir() and (candidate / "config.json").exists():
                logger.info(f"[Model2Vec] Found at: {candidate}")
                return candidate
            if current == current.parent:
                break
            current = current.parent

        logger.warning("[Model2Vec] Not found. Place Model2Vec/ folder next to LocaNext.exe or set LOCANEXT_MODELS_PATH")
        return None

    def load(self) -> None:
        if self._model is not None:
            return

        try:
            from model2vec import StaticModel

            # Check for bundled local model first (no internet needed)
            local_path = self._find_local_model_path()
            if local_path:
                logger.info(f"Loading Model2Vec from local path: {local_path}")
                self._model = StaticModel.from_pretrained(str(local_path))
            else:
                logger.info(f"Loading Model2Vec from HuggingFace: {self.MODEL_NAME}")
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

        with PerfTimer("embedding_encode", batch_size=len(texts), engine="model2vec"):
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

        with PerfTimer("embedding_encode", batch_size=len(texts), engine="qwen"):
            # SentenceTransformer encode
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress
            )
            embeddings = np.array(embeddings, dtype=np.float32)

        return embeddings


# =============================================================================
# Model2Vec Adapter -- SentenceTransformer-compatible wrapper for Light Mode
# =============================================================================

class Model2VecModelAdapter:
    """
    Wraps Model2VecEngine with a SentenceTransformer.encode()-compatible signature.

    Used by XLSTransfer and KR Similar as a drop-in replacement when
    torch/sentence-transformers are not available (Light Mode).

    Accepts and ignores kwargs like batch_size, show_progress_bar,
    convert_to_tensor, normalize_embeddings, device, etc.
    """

    def __init__(self):
        self._engine = None

    def _ensure_loaded(self):
        if self._engine is None:
            # Reuse the central engine cache to avoid duplicate model in memory
            self._engine = get_embedding_engine("model2vec")
            self._engine.load()

    def encode(self, texts, batch_size=None, show_progress_bar=False,
               convert_to_tensor=False, normalize_embeddings=True,
               device=None, **kwargs):
        """SentenceTransformer.encode()-compatible interface."""
        self._ensure_loaded()
        return self._engine.encode(texts, normalize=normalize_embeddings)

    def to(self, device):
        """No-op for device placement (Model2Vec is CPU-only)."""
        return self

    def save(self, path):
        """No-op for model saving."""
        logger.debug("Model2VecModelAdapter.save() is a no-op")


# Singleton adapter instance
_model2vec_adapter: Optional[Model2VecModelAdapter] = None


def get_model2vec_adapter() -> Model2VecModelAdapter:
    """Get a cached Model2VecModelAdapter instance."""
    global _model2vec_adapter
    if _model2vec_adapter is None:
        _model2vec_adapter = Model2VecModelAdapter()
    return _model2vec_adapter


# =============================================================================
# Engine Registry and Selection
# =============================================================================

def _get_available_engine_registry() -> dict:
    """Dynamic engine registry -- excludes QwenEngine in light mode."""
    registry = {"model2vec": Model2VecEngine}
    if not is_light_mode():
        registry["qwen"] = QwenEngine
    return registry


# Static reference for internal use only -- external callers use get_available_engines()
_AVAILABLE_ENGINES = {
    "model2vec": Model2VecEngine,
    "qwen": QwenEngine,
}


def get_available_engines() -> List[dict]:
    """
    Get list of available engines with metadata.

    Returns only engines that are actually usable (excludes Qwen in light mode).
    """
    engines = [
        {
            "id": "model2vec",
            "name": "Model2Vec (Fast)",
            "description": "79x faster, lightweight. Best for real-time search.",
            "dimension": 256,
            "memory_mb": 128,
            "default": True,
        },
    ]

    if not is_light_mode():
        engines.append({
            "id": "qwen",
            "name": "Qwen (Deep Semantic)",
            "description": "Deep understanding. Best for batch/quality work.",
            "dimension": 1024,
            "memory_mb": 2300,
            "default": False,
        })

    return engines


def get_current_engine_name() -> str:
    """Get the currently selected engine name."""
    return _current_engine_name


def set_current_engine(engine_name: str) -> None:
    """
    Set the current embedding engine.

    Args:
        engine_name: "model2vec" or "qwen"

    Raises:
        ValueError: If engine_name is "qwen" in light mode, or unknown engine.
    """
    global _current_engine_name

    registry = _get_available_engine_registry()

    if engine_name not in registry:
        if engine_name == "qwen" and is_light_mode():
            raise ValueError("Qwen engine is not available in Light Mode (torch/sentence-transformers not installed). Use 'model2vec' instead.")
        raise ValueError(f"Unknown engine: {engine_name}. Available: {list(registry.keys())}")

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
    global _engines, _current_engine_name

    if engine_name is None:
        engine_name = _current_engine_name

    registry = _get_available_engine_registry()

    if engine_name not in registry:
        if engine_name == "qwen" and is_light_mode():
            logger.warning(f"Qwen requested but Light Mode active -- falling back to model2vec")
            engine_name = "model2vec"
            _current_engine_name = "model2vec"
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    if engine_name not in _engines:
        _engines[engine_name] = registry[engine_name]()

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
