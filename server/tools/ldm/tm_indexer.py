"""
LDM Translation Memory Indexer

Builds indexes for 5-Tier Cascade TM Search:
- Tier 1: whole_text_lookup (hash index for O(1) exact match)
- Tier 2: whole FAISS HNSW (semantic whole-text search)
- Tier 3: line_lookup (hash index for O(1) line match)
- Tier 4: line FAISS HNSW (semantic line-by-line search)

Uses Qwen3-Embedding-0.6B for embeddings (same as KR Similar).
Storage: server/data/ldm_tm/{tm_id}/

Architecture follows WebTranslatorNew 5-Tier Cascade + Dual Threshold pattern.
"""

import os
import json
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import torch
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("sentence_transformers/faiss not available - TM indexing disabled")

from server.database.models import LDMTranslationMemory, LDMTMEntry, LDMTMIndex


# Model name (P20: Unified Qwen model)
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

# FAISS HNSW parameters (optimized for 50k-500k entries)
HNSW_M = 32  # Connections per layer
HNSW_EF_CONSTRUCTION = 400  # Build-time accuracy
HNSW_EF_SEARCH = 500  # Search-time accuracy


def normalize_for_hash(text: str) -> str:
    """
    Normalize text for hash-based lookup.
    Handles newlines, whitespace, case.
    """
    if not text:
        return ""
    # Normalize newlines to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Lowercase for case-insensitive matching
    text = text.lower()
    # Normalize whitespace but preserve structure
    lines = [' '.join(line.split()) for line in text.split('\n')]
    return '\n'.join(lines)


def normalize_for_embedding(text: str) -> str:
    """
    Normalize text for embedding generation.
    Less aggressive than hash normalization.
    """
    if not text:
        return ""
    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Basic whitespace cleanup
    return ' '.join(text.split())


class TMIndexer:
    """
    TM Index Builder for LDM.

    Creates and manages indexes for fast TM search:
    - Hash indexes for exact match (Tier 1, 3)
    - FAISS HNSW indexes for semantic search (Tier 2, 4)

    Storage structure:
    server/data/ldm_tm/{tm_id}/
    ├── metadata.json
    ├── hash/
    │   ├── whole_lookup.pkl
    │   └── line_lookup.pkl
    ├── embeddings/
    │   ├── whole.npy
    │   ├── whole_mapping.pkl
    │   ├── line.npy
    │   └── line_mapping.pkl
    └── faiss/
        ├── whole.index
        └── line.index
    """

    def __init__(self, db: Session, data_dir: str = None):
        """
        Initialize TMIndexer.

        Args:
            db: SQLAlchemy session
            data_dir: Base directory for TM data (default: server/data/ldm_tm)
        """
        self.db = db
        self.model = None
        self.device = None

        # Set data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "ldm_tm"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"TMIndexer initialized", {"data_dir": str(self.data_dir)})

    def _ensure_model_loaded(self):
        """Load the embedding model if not already loaded."""
        if not MODELS_AVAILABLE:
            raise RuntimeError("sentence_transformers/faiss not available")

        if self.model is None:
            logger.info(f"Loading embedding model: {MODEL_NAME}")
            self.model = SentenceTransformer(MODEL_NAME)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            logger.success(f"Model loaded on {self.device}")

    def get_tm_path(self, tm_id: int) -> Path:
        """Get the storage path for a TM."""
        return self.data_dir / str(tm_id)

    # =========================================================================
    # Main Index Building
    # =========================================================================

    def build_indexes(
        self,
        tm_id: int,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Build all indexes for a TM.

        Args:
            tm_id: Translation Memory ID
            progress_callback: Optional callback (stage, current, total)

        Returns:
            Dict with build results
        """
        start_time = datetime.now()

        # Get TM and entries
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            raise ValueError(f"TM not found: {tm_id}")

        logger.info(f"Building indexes for TM: {tm.name} (id={tm_id})")

        # Update status
        tm.status = "indexing"
        self.db.commit()

        try:
            # Load entries
            entries = self.db.query(LDMTMEntry).filter(
                LDMTMEntry.tm_id == tm_id
            ).all()

            if not entries:
                raise ValueError(f"No entries found for TM: {tm_id}")

            logger.info(f"Loaded {len(entries):,} entries")

            # Convert to list of dicts
            entry_list = [
                {
                    "id": e.id,
                    "source_text": e.source_text,
                    "target_text": e.target_text
                }
                for e in entries
            ]

            # Create storage directory
            tm_path = self.get_tm_path(tm_id)
            tm_path.mkdir(parents=True, exist_ok=True)
            (tm_path / "hash").mkdir(exist_ok=True)
            (tm_path / "embeddings").mkdir(exist_ok=True)
            (tm_path / "faiss").mkdir(exist_ok=True)

            # Build hash indexes
            if progress_callback:
                progress_callback("Building hash indexes", 0, 4)

            whole_lookup = self._build_whole_lookup(entry_list)
            self._save_pickle(whole_lookup, tm_path / "hash" / "whole_lookup.pkl")
            self._track_index(tm_id, "whole_hash", tm_path / "hash" / "whole_lookup.pkl")

            line_lookup = self._build_line_lookup(entry_list)
            self._save_pickle(line_lookup, tm_path / "hash" / "line_lookup.pkl")
            self._track_index(tm_id, "line_hash", tm_path / "hash" / "line_lookup.pkl")

            if progress_callback:
                progress_callback("Building embeddings", 1, 4)

            # Build embeddings + FAISS indexes
            self._ensure_model_loaded()

            # Whole embeddings
            whole_result = self._build_whole_embeddings(entry_list, tm_path)
            self._track_index(tm_id, "whole_faiss", tm_path / "faiss" / "whole.index")

            if progress_callback:
                progress_callback("Building line embeddings", 2, 4)

            # Line embeddings
            line_result = self._build_line_embeddings(entry_list, tm_path)
            self._track_index(tm_id, "line_faiss", tm_path / "faiss" / "line.index")

            if progress_callback:
                progress_callback("Saving metadata", 3, 4)

            # Save metadata
            metadata = {
                "tm_id": tm_id,
                "tm_name": tm.name,
                "entry_count": len(entry_list),
                "whole_lookup_count": len(whole_lookup),
                "line_lookup_count": len(line_lookup),
                "whole_embeddings_count": whole_result["count"],
                "line_embeddings_count": line_result["count"],
                "embedding_dim": whole_result.get("dim", 0),
                "model": MODEL_NAME,
                "created_at": datetime.now().isoformat()
            }
            self._save_json(metadata, tm_path / "metadata.json")

            # Update TM status
            tm.status = "ready"
            tm.storage_path = str(tm_path)
            self.db.commit()

            elapsed = (datetime.now() - start_time).total_seconds()

            if progress_callback:
                progress_callback("Complete", 4, 4)

            logger.success(f"Index build complete for TM {tm_id} in {elapsed:.2f}s")

            return {
                "tm_id": tm_id,
                "entry_count": len(entry_list),
                "whole_lookup_count": len(whole_lookup),
                "line_lookup_count": len(line_lookup),
                "whole_embeddings_count": whole_result["count"],
                "line_embeddings_count": line_result["count"],
                "time_seconds": round(elapsed, 2),
                "status": "ready"
            }

        except Exception as e:
            logger.error(f"Index build failed for TM {tm_id}: {e}")
            tm.status = "error"
            self.db.commit()
            raise

    # =========================================================================
    # Hash Index Builders (Tier 1 & 3)
    # =========================================================================

    def _build_whole_lookup(self, entries: List[Dict]) -> Dict[str, Dict]:
        """
        Build whole_text_lookup for Tier 1 (exact whole match).

        Maps normalized source text to entry info.
        O(1) lookup time.
        """
        logger.info("Building whole_text_lookup...")
        lookup = {}

        for entry in entries:
            source = entry["source_text"]
            if not source:
                continue

            # Primary key: normalized text
            normalized = normalize_for_hash(source)
            if normalized and normalized not in lookup:
                lookup[normalized] = {
                    "entry_id": entry["id"],
                    "source_text": source,
                    "target_text": entry["target_text"]
                }

            # Also index stripped version
            stripped = normalized.strip()
            if stripped and stripped != normalized and stripped not in lookup:
                lookup[stripped] = {
                    "entry_id": entry["id"],
                    "source_text": source,
                    "target_text": entry["target_text"]
                }

        logger.info(f"Built whole_text_lookup: {len(lookup):,} entries")
        return lookup

    def _build_line_lookup(self, entries: List[Dict]) -> Dict[str, Dict]:
        """
        Build line_lookup for Tier 3 (exact line match).

        Maps individual lines to their translations.
        Useful for multi-line text where some lines match exactly.
        """
        logger.info("Building line_lookup...")
        lookup = {}

        for entry in entries:
            source = entry["source_text"]
            target = entry["target_text"]

            if not source:
                continue

            # Split into lines
            source_lines = source.split('\n')
            target_lines = (target or "").split('\n')

            for i, line in enumerate(source_lines):
                if not line.strip():
                    continue

                normalized_line = normalize_for_hash(line)
                if not normalized_line:
                    continue

                # Get corresponding target line
                target_line = target_lines[i] if i < len(target_lines) else ""

                # Only store if not already present (first occurrence wins)
                if normalized_line not in lookup:
                    lookup[normalized_line] = {
                        "entry_id": entry["id"],
                        "source_line": line,
                        "target_line": target_line,
                        "line_num": i,
                        "total_lines": len(source_lines)
                    }

        logger.info(f"Built line_lookup: {len(lookup):,} entries")
        return lookup

    # =========================================================================
    # Embedding Index Builders (Tier 2 & 4)
    # =========================================================================

    def _build_whole_embeddings(
        self,
        entries: List[Dict],
        tm_path: Path,
        batch_size: int = 64
    ) -> Dict[str, Any]:
        """
        Build whole-text embeddings and FAISS HNSW index for Tier 2.

        Args:
            entries: List of TM entries
            tm_path: Storage path
            batch_size: Encoding batch size

        Returns:
            Dict with build stats
        """
        logger.info("Building whole-text embeddings...")

        # Prepare texts for embedding
        texts = []
        mapping = []  # idx -> entry_id

        for entry in entries:
            source = entry["source_text"]
            if not source:
                continue

            normalized = normalize_for_embedding(source)
            if normalized:
                texts.append(normalized)
                mapping.append({
                    "entry_id": entry["id"],
                    "source_text": source,
                    "target_text": entry["target_text"]
                })

        if not texts:
            logger.warning("No texts to embed for whole embeddings")
            return {"count": 0, "dim": 0}

        # Generate embeddings
        logger.info(f"Encoding {len(texts):,} whole texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            device=self.device
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build FAISS HNSW index
        dim = embeddings.shape[1]
        logger.info(f"Building FAISS HNSW index (dim={dim}, M={HNSW_M})...")

        index = faiss.IndexHNSWFlat(dim, HNSW_M, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
        index.hnsw.efSearch = HNSW_EF_SEARCH
        index.add(embeddings)

        # Save embeddings, mapping, and index
        np.save(tm_path / "embeddings" / "whole.npy", embeddings)
        self._save_pickle(mapping, tm_path / "embeddings" / "whole_mapping.pkl")
        faiss.write_index(index, str(tm_path / "faiss" / "whole.index"))

        logger.info(f"Built whole embeddings: {len(texts):,} entries, dim={dim}")
        return {"count": len(texts), "dim": dim}

    def _build_line_embeddings(
        self,
        entries: List[Dict],
        tm_path: Path,
        batch_size: int = 64
    ) -> Dict[str, Any]:
        """
        Build line-by-line embeddings and FAISS index for Tier 4.

        Generates embeddings for each line in multi-line texts.
        """
        logger.info("Building line embeddings...")

        # Extract lines
        texts = []
        mapping = []  # idx -> (entry_id, line_num, source_line, target_line)

        for entry in entries:
            source = entry["source_text"]
            target = entry["target_text"] or ""

            if not source:
                continue

            source_lines = source.split('\n')
            target_lines = target.split('\n')

            for i, line in enumerate(source_lines):
                if not line.strip():
                    continue

                normalized = normalize_for_embedding(line)
                if not normalized or len(normalized) < 3:  # Skip very short lines
                    continue

                target_line = target_lines[i] if i < len(target_lines) else ""

                texts.append(normalized)
                mapping.append({
                    "entry_id": entry["id"],
                    "line_num": i,
                    "source_line": line,
                    "target_line": target_line
                })

        if not texts:
            logger.warning("No texts to embed for line embeddings")
            return {"count": 0, "dim": 0}

        # Generate embeddings
        logger.info(f"Encoding {len(texts):,} lines...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            device=self.device
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build FAISS HNSW index
        dim = embeddings.shape[1]
        logger.info(f"Building FAISS HNSW line index (dim={dim})...")

        index = faiss.IndexHNSWFlat(dim, HNSW_M, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
        index.hnsw.efSearch = HNSW_EF_SEARCH
        index.add(embeddings)

        # Save
        np.save(tm_path / "embeddings" / "line.npy", embeddings)
        self._save_pickle(mapping, tm_path / "embeddings" / "line_mapping.pkl")
        faiss.write_index(index, str(tm_path / "faiss" / "line.index"))

        logger.info(f"Built line embeddings: {len(texts):,} lines, dim={dim}")
        return {"count": len(texts), "dim": dim}

    # =========================================================================
    # Index Loading
    # =========================================================================

    def load_indexes(self, tm_id: int) -> Dict[str, Any]:
        """
        Load all indexes for a TM into memory.

        Returns:
            Dict with all loaded indexes
        """
        tm_path = self.get_tm_path(tm_id)

        if not tm_path.exists():
            raise FileNotFoundError(f"TM indexes not found: {tm_path}")

        logger.info(f"Loading indexes for TM {tm_id}...")

        # Load metadata
        metadata = self._load_json(tm_path / "metadata.json")

        # Load hash indexes
        whole_lookup = self._load_pickle(tm_path / "hash" / "whole_lookup.pkl")
        line_lookup = self._load_pickle(tm_path / "hash" / "line_lookup.pkl")

        # Load embeddings and mappings
        whole_embeddings = np.load(tm_path / "embeddings" / "whole.npy")
        whole_mapping = self._load_pickle(tm_path / "embeddings" / "whole_mapping.pkl")

        line_embeddings = np.load(tm_path / "embeddings" / "line.npy")
        line_mapping = self._load_pickle(tm_path / "embeddings" / "line_mapping.pkl")

        # Load FAISS indexes
        whole_index = faiss.read_index(str(tm_path / "faiss" / "whole.index"))
        line_index = faiss.read_index(str(tm_path / "faiss" / "line.index"))

        logger.success(f"Loaded all indexes for TM {tm_id}")

        return {
            "tm_id": tm_id,
            "metadata": metadata,
            "whole_lookup": whole_lookup,
            "line_lookup": line_lookup,
            "whole_embeddings": whole_embeddings,
            "whole_mapping": whole_mapping,
            "whole_index": whole_index,
            "line_embeddings": line_embeddings,
            "line_mapping": line_mapping,
            "line_index": line_index
        }

    def delete_indexes(self, tm_id: int) -> bool:
        """
        Delete all indexes for a TM.

        Args:
            tm_id: TM ID

        Returns:
            True if deleted
        """
        tm_path = self.get_tm_path(tm_id)

        if tm_path.exists():
            import shutil
            shutil.rmtree(tm_path)
            logger.info(f"Deleted indexes for TM {tm_id}")

            # Remove tracking records
            self.db.query(LDMTMIndex).filter(LDMTMIndex.tm_id == tm_id).delete()
            self.db.commit()

            return True

        return False

    # =========================================================================
    # Helpers
    # =========================================================================

    def _track_index(self, tm_id: int, index_type: str, file_path: Path):
        """Track index file in database."""
        from datetime import datetime

        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Check if record exists
        existing = self.db.query(LDMTMIndex).filter(
            LDMTMIndex.tm_id == tm_id,
            LDMTMIndex.index_type == index_type
        ).first()

        if existing:
            existing.index_path = str(file_path)
            existing.file_size = file_size
            existing.status = "ready"
            existing.built_at = datetime.utcnow()
        else:
            index_record = LDMTMIndex(
                tm_id=tm_id,
                index_type=index_type,
                index_path=str(file_path),
                file_size=file_size,
                status="ready",
                built_at=datetime.utcnow()
            )
            self.db.add(index_record)

        self.db.commit()

    def _save_pickle(self, data: Any, path: Path):
        """Save data as pickle file."""
        with open(path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def _load_pickle(self, path: Path) -> Any:
        """Load pickle file."""
        with open(path, 'rb') as f:
            return pickle.load(f)

    def _save_json(self, data: Dict, path: Path):
        """Save data as JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_json(self, path: Path) -> Dict:
        """Load JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
