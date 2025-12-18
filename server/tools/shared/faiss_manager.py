"""
Centralized FAISS HNSW Index Management.

This module provides a single source of truth for FAISS operations
across all LocaNext tools (LDM, KR Similar, XLS Transfer).

Benefits:
- DRY: Fix bugs once, applies everywhere
- Incremental add: Built into the interface
- Config changes: One place to tune HNSW parameters
- Testing: Single module to unit test

Usage:
    from server.tools.shared import FAISSManager

    # Create new index
    index = FAISSManager.create_index(dim=1024)
    FAISSManager.add_vectors(index, embeddings)
    FAISSManager.save_index(index, path)

    # Load and search
    index = FAISSManager.load_index(path)
    distances, indices = FAISSManager.search(index, query, k=10)

    # Incremental add (load or create, add, save)
    index = FAISSManager.incremental_add(path, new_vectors, dim=1024)
"""

from pathlib import Path
from typing import Tuple, Optional
import numpy as np

from loguru import logger

# Lazy import FAISS to avoid startup delay
_faiss = None


def _get_faiss():
    """Lazy import FAISS module."""
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


class FAISSManager:
    """
    Centralized FAISS HNSW index management.

    All HNSW configuration is defined here as the single source of truth.
    """

    # HNSW Configuration (single source of truth)
    HNSW_M = 32                    # Connections per layer (higher = better recall, more memory)
    HNSW_EF_CONSTRUCTION = 400     # Build-time accuracy (higher = slower build, better index)
    HNSW_EF_SEARCH = 500           # Search-time accuracy (higher = slower search, better recall)

    @classmethod
    def create_index(cls, dim: int) -> "faiss.Index":
        """
        Create a new HNSW index with standard configuration.

        Args:
            dim: Embedding dimension (e.g., 1024 for Qwen, 256 for Model2Vec)

        Returns:
            Configured FAISS HNSW index
        """
        faiss = _get_faiss()

        index = faiss.IndexHNSWFlat(dim, cls.HNSW_M, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = cls.HNSW_EF_CONSTRUCTION
        index.hnsw.efSearch = cls.HNSW_EF_SEARCH

        logger.debug(f"Created FAISS HNSW index (dim={dim}, M={cls.HNSW_M})")
        return index

    @staticmethod
    def load_index(path: Path) -> "faiss.Index":
        """
        Load an existing FAISS index from disk.

        Args:
            path: Path to the .index file

        Returns:
            Loaded FAISS index

        Raises:
            FileNotFoundError: If index file doesn't exist
        """
        faiss = _get_faiss()

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"FAISS index not found: {path}")

        index = faiss.read_index(str(path))
        logger.debug(f"Loaded FAISS index from {path} ({index.ntotal} vectors)")
        return index

    @staticmethod
    def save_index(index: "faiss.Index", path: Path) -> None:
        """
        Save a FAISS index to disk.

        Args:
            index: FAISS index to save
            path: Destination path for .index file
        """
        faiss = _get_faiss()

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(path))
        logger.debug(f"Saved FAISS index to {path} ({index.ntotal} vectors)")

    @staticmethod
    def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        """
        Normalize vectors for inner product search.

        FAISS METRIC_INNER_PRODUCT requires normalized vectors
        for cosine similarity behavior.

        Args:
            vectors: Input vectors (will be modified in place)

        Returns:
            Normalized vectors (same array, modified in place)
        """
        faiss = _get_faiss()

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        faiss.normalize_L2(vectors)
        return vectors

    @classmethod
    def add_vectors(cls, index: "faiss.Index", vectors: np.ndarray, normalize: bool = True) -> None:
        """
        Add vectors to an existing index.

        Args:
            index: FAISS index to add to
            vectors: Vectors to add (N x dim)
            normalize: Whether to normalize vectors (default True)
        """
        if vectors.size == 0:
            logger.debug("No vectors to add")
            return

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)

        if normalize:
            vectors = cls.normalize_vectors(vectors)

        before = index.ntotal
        index.add(vectors)
        logger.debug(f"Added {vectors.shape[0]} vectors to index ({before} -> {index.ntotal})")

    @classmethod
    def search(
        cls,
        index: "faiss.Index",
        query: np.ndarray,
        k: int = 10,
        normalize: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.

        Args:
            index: FAISS index to search
            query: Query vectors (N x dim or 1D for single query)
            k: Number of neighbors to return
            normalize: Whether to normalize query (default True)

        Returns:
            Tuple of (distances, indices) arrays
        """
        # Handle single query
        if query.ndim == 1:
            query = query.reshape(1, -1)

        query = np.ascontiguousarray(query, dtype=np.float32)

        if normalize:
            query = cls.normalize_vectors(query)

        distances, indices = index.search(query, k)
        return distances, indices

    @classmethod
    def load_or_create(cls, path: Path, dim: int) -> "faiss.Index":
        """
        Load existing index or create a new one.

        Args:
            path: Path to .index file
            dim: Dimension for new index (if creating)

        Returns:
            FAISS index (loaded or newly created)
        """
        path = Path(path)

        if path.exists():
            return cls.load_index(path)

        return cls.create_index(dim)

    @classmethod
    def incremental_add(
        cls,
        path: Path,
        new_vectors: np.ndarray,
        dim: int,
        normalize: bool = True
    ) -> "faiss.Index":
        """
        Add vectors to existing index or create new, then save.

        This is the main method for incremental updates:
        1. Load existing index (or create new)
        2. Add new vectors
        3. Save updated index

        Args:
            path: Path to .index file
            new_vectors: New vectors to add
            dim: Dimension for new index (if creating)
            normalize: Whether to normalize vectors

        Returns:
            Updated FAISS index
        """
        index = cls.load_or_create(path, dim)
        cls.add_vectors(index, new_vectors, normalize=normalize)
        cls.save_index(index, path)
        return index

    @classmethod
    def build_index(
        cls,
        vectors: np.ndarray,
        path: Optional[Path] = None,
        normalize: bool = True
    ) -> "faiss.Index":
        """
        Build a new index from scratch with given vectors.

        Args:
            vectors: All vectors to index
            path: Optional path to save index
            normalize: Whether to normalize vectors

        Returns:
            Built FAISS index
        """
        if vectors.size == 0:
            raise ValueError("Cannot build index with no vectors")

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        dim = vectors.shape[1]

        if normalize:
            vectors = cls.normalize_vectors(vectors)

        index = cls.create_index(dim)
        index.add(vectors)

        logger.info(f"Built FAISS HNSW index with {index.ntotal} vectors (dim={dim})")

        if path:
            cls.save_index(index, path)

        return index

    @staticmethod
    def get_index_size(index: "faiss.Index") -> int:
        """Get the number of vectors in the index."""
        return index.ntotal

    @staticmethod
    def is_empty(index: "faiss.Index") -> bool:
        """Check if index has no vectors."""
        return index.ntotal == 0
