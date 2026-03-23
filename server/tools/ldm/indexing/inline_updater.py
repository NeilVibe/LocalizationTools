"""
Inline TM Updater - Per-entry FAISS + hash updates without full rebuild.

Replaces heavy pandas-based full-diff background sync with synchronous
per-entry updates that complete before the HTTP response returns (~6ms per entry).

Usage:
    from server.tools.ldm.indexing.inline_updater import get_inline_updater

    updater = get_inline_updater(tm_id=1)
    updater.add_entry(entry_id=42, source_text="Hello", target_text="Bonjour")
    updater.update_entry(entry_id=42, source_text="Hi", target_text="Salut", old_source_text="Hello")
    updater.remove_entry(entry_id=42, source_text="Hi")
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from loguru import logger

from server.tools.shared.faiss_manager import FAISSManager, ThreadSafeIndex
from server.tools.shared import get_embedding_engine, get_current_engine_name
from .utils import normalize_for_hash, normalize_for_embedding


class InlineTMUpdater:
    """
    Inline TM index updater for single-entry CRUD on FAISS + hash lookups.

    Thread-safe via ThreadSafeIndex. Lazily loads all resources on first use.
    Persists changes to disk after each operation.
    """

    def __init__(self, tm_id: int, data_dir: str = None):
        self.tm_id = tm_id

        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = (
                Path(__file__).parent.parent.parent.parent / "data" / "ldm_tm"
            )

        self.tm_path = self._data_dir / str(tm_id)

        # Lazy-loaded resources
        self._engine = None
        self._ts_index: Optional[ThreadSafeIndex] = None
        self._whole_lookup: Optional[Dict] = None
        self._line_lookup: Optional[Dict] = None
        self._whole_mapping: Optional[List] = None
        self._whole_embeddings: Optional[np.ndarray] = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load embedding engine, FAISS index, and hash lookups."""
        if self._loaded:
            return

        # Load embedding engine
        engine_name = get_current_engine_name()
        self._engine = get_embedding_engine(engine_name)
        if not self._engine.is_loaded:
            self._engine.load()

        # Load or create FAISS index
        faiss_path = self.tm_path / "faiss" / "whole.index"
        if faiss_path.exists():
            index = FAISSManager.load_index(faiss_path)
            # Check if it's already an IDMap2 index
            try:
                import faiss as _faiss
                if not isinstance(index, _faiss.IndexIDMap2):
                    logger.info(
                        f"Migrating plain index to IDMap2 for tm_id={self.tm_id}"
                    )
                    index = FAISSManager.convert_to_idmap(
                        index, self._engine.dimension
                    )
                    FAISSManager.save_index(index, faiss_path)
            except ImportError:
                pass
            self._ts_index = ThreadSafeIndex(index)
        else:
            index = FAISSManager.create_idmap_index(self._engine.dimension)
            self._ts_index = ThreadSafeIndex(index)

        # Load hash lookups (pickle is safe here -- internal data, not user input)
        whole_lookup_path = self.tm_path / "hash" / "whole_lookup.pkl"
        line_lookup_path = self.tm_path / "hash" / "line_lookup.pkl"

        if whole_lookup_path.exists():
            with open(whole_lookup_path, "rb") as f:
                self._whole_lookup = pickle.load(f)  # noqa: S301 (trusted internal data)
        else:
            self._whole_lookup = {}

        if line_lookup_path.exists():
            with open(line_lookup_path, "rb") as f:
                self._line_lookup = pickle.load(f)  # noqa: S301 (trusted internal data)
        else:
            self._line_lookup = {}

        # Load mapping and embeddings
        mapping_path = self.tm_path / "embeddings" / "whole_mapping.pkl"
        embeddings_path = self.tm_path / "embeddings" / "whole.npy"

        if mapping_path.exists():
            with open(mapping_path, "rb") as f:
                self._whole_mapping = pickle.load(f)  # noqa: S301 (trusted internal data)
        else:
            self._whole_mapping = []

        if embeddings_path.exists():
            self._whole_embeddings = np.load(embeddings_path)
        else:
            self._whole_embeddings = None

        self._loaded = True
        logger.debug(
            f"InlineTMUpdater loaded for tm_id={self.tm_id}: "
            f"index={self._ts_index.ntotal} vectors, "
            f"whole_lookup={len(self._whole_lookup)}, "
            f"line_lookup={len(self._line_lookup)}"
        )

    def add_entry(
        self,
        entry_id: int,
        source_text: str,
        target_text: str,
        string_id: str = None,
    ) -> None:
        """
        Add a single TM entry to FAISS index and hash lookups.

        Args:
            entry_id: Database entry ID
            source_text: Source language text
            target_text: Target language text
            string_id: Optional string identifier
        """
        self._ensure_loaded()

        # Encode embedding
        text = normalize_for_embedding(source_text)
        embedding = self._engine.encode([text], normalize=True)
        embedding = np.ascontiguousarray(embedding, dtype=np.float32)
        FAISSManager.normalize_vectors(embedding)

        # Add to FAISS with explicit ID
        self._ts_index.add_with_ids(
            embedding, np.array([entry_id], dtype=np.int64)
        )

        # Update whole_lookup (mirrors sync_manager._incremental_sync pattern)
        self._add_to_whole_lookup(entry_id, source_text, target_text, string_id)

        # Update line_lookup
        self._add_to_line_lookup(entry_id, source_text, target_text)

        # Update mapping and embeddings
        self._whole_mapping.append(entry_id)
        if self._whole_embeddings is not None:
            self._whole_embeddings = np.vstack(
                [self._whole_embeddings, embedding]
            )
        else:
            self._whole_embeddings = embedding.copy()

        self._persist()
        logger.info(
            f"Inline add: tm_id={self.tm_id}, entry_id={entry_id}, "
            f"source={source_text[:30]}..."
        )

    def update_entry(
        self,
        entry_id: int,
        source_text: str,
        target_text: str,
        string_id: str = None,
        old_source_text: str = None,
    ) -> None:
        """
        Update an existing TM entry: remove old data, add new.

        Args:
            entry_id: Database entry ID
            source_text: New source language text
            target_text: New target language text
            string_id: Optional string identifier
            old_source_text: Previous source text (needed to clean old hash entries)
        """
        self._ensure_loaded()

        # Remove old vector from FAISS
        import faiss as _faiss

        id_array = np.array([entry_id], dtype=np.int64)
        id_selector = _faiss.IDSelectorBatch(
            len(id_array), _faiss.swig_ptr(id_array)
        )
        self._ts_index.remove_ids(id_selector)

        # Remove old hash entries
        if old_source_text:
            self._remove_from_whole_lookup(entry_id, old_source_text)
            self._remove_from_line_lookup(entry_id, old_source_text)

        # Remove from mapping and embeddings
        self._remove_from_mapping(entry_id)

        # Add new data (encode + FAISS + lookups)
        text = normalize_for_embedding(source_text)
        embedding = self._engine.encode([text], normalize=True)
        embedding = np.ascontiguousarray(embedding, dtype=np.float32)
        FAISSManager.normalize_vectors(embedding)

        self._ts_index.add_with_ids(
            embedding, np.array([entry_id], dtype=np.int64)
        )

        self._add_to_whole_lookup(entry_id, source_text, target_text, string_id)
        self._add_to_line_lookup(entry_id, source_text, target_text)

        self._whole_mapping.append(entry_id)
        if self._whole_embeddings is not None:
            self._whole_embeddings = np.vstack(
                [self._whole_embeddings, embedding]
            )
        else:
            self._whole_embeddings = embedding.copy()

        self._persist()
        logger.info(
            f"Inline update: tm_id={self.tm_id}, entry_id={entry_id}, "
            f"source={source_text[:30]}..."
        )

    def remove_entry(self, entry_id: int, source_text: str) -> None:
        """
        Remove a TM entry from FAISS index and hash lookups.

        Args:
            entry_id: Database entry ID
            source_text: Source text (needed to clean hash entries)
        """
        self._ensure_loaded()

        # Remove vector from FAISS
        import faiss as _faiss

        id_array = np.array([entry_id], dtype=np.int64)
        id_selector = _faiss.IDSelectorBatch(
            len(id_array), _faiss.swig_ptr(id_array)
        )
        self._ts_index.remove_ids(id_selector)

        # Remove from hash lookups
        self._remove_from_whole_lookup(entry_id, source_text)
        self._remove_from_line_lookup(entry_id, source_text)

        # Remove from mapping and embeddings
        self._remove_from_mapping(entry_id)

        self._persist()
        logger.info(
            f"Inline remove: tm_id={self.tm_id}, entry_id={entry_id}, "
            f"source={source_text[:30]}..."
        )

    def add_entries_batch(self, entries: List[dict]) -> None:
        """
        Add multiple TM entries in a single batch operation.

        Args:
            entries: List of dicts with keys: id, source_text, target_text, string_id (optional)
        """
        if not entries:
            return

        self._ensure_loaded()

        # Batch encode
        texts = [normalize_for_embedding(e["source_text"]) for e in entries]
        embeddings = self._engine.encode(texts, normalize=True)
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        FAISSManager.normalize_vectors(embeddings)

        # Batch FAISS add
        ids = np.array([e["id"] for e in entries], dtype=np.int64)
        self._ts_index.add_with_ids(embeddings, ids)

        # Update hash lookups for each entry
        for entry in entries:
            self._add_to_whole_lookup(
                entry["id"],
                entry["source_text"],
                entry["target_text"],
                entry.get("string_id"),
            )
            self._add_to_line_lookup(
                entry["id"], entry["source_text"], entry["target_text"]
            )

        # Update mapping and embeddings
        self._whole_mapping.extend(e["id"] for e in entries)
        if self._whole_embeddings is not None:
            self._whole_embeddings = np.vstack(
                [self._whole_embeddings, embeddings]
            )
        else:
            self._whole_embeddings = embeddings.copy()

        self._persist()
        logger.info(
            f"Inline batch add: tm_id={self.tm_id}, count={len(entries)}"
        )

    # ---- Private helpers ----

    def _add_to_whole_lookup(
        self,
        entry_id: int,
        source_text: str,
        target_text: str,
        string_id: str = None,
    ) -> None:
        """Add entry to whole_lookup dict (mirrors sync_manager pattern)."""
        if not source_text:
            return
        normalized = normalize_for_hash(source_text)
        if not normalized:
            return

        entry_data = {
            "entry_id": entry_id,
            "source_text": source_text,
            "target_text": target_text,
            "string_id": string_id,
        }

        if normalized not in self._whole_lookup:
            if string_id:
                self._whole_lookup[normalized] = {
                    "variations": [entry_data],
                    "source_text": source_text,
                }
            else:
                self._whole_lookup[normalized] = entry_data
        else:
            existing = self._whole_lookup[normalized]
            if "variations" in existing:
                existing["variations"].append(entry_data)
            elif string_id:
                self._whole_lookup[normalized] = {
                    "variations": [existing, entry_data],
                    "source_text": source_text,
                }

    def _add_to_line_lookup(
        self, entry_id: int, source_text: str, target_text: str
    ) -> None:
        """Add entry lines to line_lookup dict (mirrors sync_manager pattern)."""
        if not source_text:
            return

        target = target_text or ""
        source_lines = source_text.split("\n")
        target_lines = target.split("\n")

        for i, line in enumerate(source_lines):
            if not line.strip():
                continue
            normalized_line = normalize_for_hash(line)
            if not normalized_line or normalized_line in self._line_lookup:
                continue
            target_line = target_lines[i] if i < len(target_lines) else ""
            self._line_lookup[normalized_line] = {
                "entry_id": entry_id,
                "source_line": line,
                "target_line": target_line,
                "line_num": i,
                "total_lines": len(source_lines),
            }

    def _remove_from_whole_lookup(
        self, entry_id: int, source_text: str
    ) -> None:
        """Remove entry from whole_lookup dict."""
        if not source_text:
            return
        normalized = normalize_for_hash(source_text)
        if not normalized or normalized not in self._whole_lookup:
            return

        existing = self._whole_lookup[normalized]
        if "variations" in existing:
            existing["variations"] = [
                v for v in existing["variations"] if v.get("entry_id") != entry_id
            ]
            if not existing["variations"]:
                del self._whole_lookup[normalized]
            elif len(existing["variations"]) == 1:
                # Unwrap single variation
                self._whole_lookup[normalized] = existing["variations"][0]
        elif existing.get("entry_id") == entry_id:
            del self._whole_lookup[normalized]

    def _remove_from_line_lookup(
        self, entry_id: int, source_text: str
    ) -> None:
        """Remove entry lines from line_lookup dict."""
        if not source_text:
            return

        source_lines = source_text.split("\n")
        for line in source_lines:
            if not line.strip():
                continue
            normalized_line = normalize_for_hash(line)
            if not normalized_line:
                continue
            if normalized_line in self._line_lookup:
                if self._line_lookup[normalized_line].get("entry_id") == entry_id:
                    del self._line_lookup[normalized_line]

    def _remove_from_mapping(self, entry_id: int) -> None:
        """Remove entry from whole_mapping and whole_embeddings."""
        if entry_id not in self._whole_mapping:
            return

        idx = self._whole_mapping.index(entry_id)
        self._whole_mapping.pop(idx)

        if self._whole_embeddings is not None and idx < len(self._whole_embeddings):
            self._whole_embeddings = np.delete(self._whole_embeddings, idx, axis=0)
            if len(self._whole_embeddings) == 0:
                self._whole_embeddings = None

    def _persist(self) -> None:
        """Save all in-memory state to disk."""
        # Ensure directories exist
        (self.tm_path / "faiss").mkdir(parents=True, exist_ok=True)
        (self.tm_path / "hash").mkdir(parents=True, exist_ok=True)
        (self.tm_path / "embeddings").mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss_path = self.tm_path / "faiss" / "whole.index"
        FAISSManager.save_index(self._ts_index.index, faiss_path)

        # Save hash lookups (pickle is safe -- internal data structures, not user input)
        with open(self.tm_path / "hash" / "whole_lookup.pkl", "wb") as f:
            pickle.dump(self._whole_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(self.tm_path / "hash" / "line_lookup.pkl", "wb") as f:
            pickle.dump(self._line_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Save mapping
        with open(self.tm_path / "embeddings" / "whole_mapping.pkl", "wb") as f:
            pickle.dump(self._whole_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Save embeddings
        if self._whole_embeddings is not None:
            np.save(self.tm_path / "embeddings" / "whole.npy", self._whole_embeddings)


# Module-level cache for updater instances
_updater_cache: Dict[int, InlineTMUpdater] = {}


def get_inline_updater(tm_id: int) -> InlineTMUpdater:
    """
    Get or create a cached InlineTMUpdater for the given TM ID.

    Args:
        tm_id: Translation Memory ID

    Returns:
        Cached InlineTMUpdater instance
    """
    if tm_id not in _updater_cache:
        _updater_cache[tm_id] = InlineTMUpdater(tm_id)
    return _updater_cache[tm_id]
