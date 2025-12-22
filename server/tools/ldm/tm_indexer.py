"""
LDM Translation Memory Indexer

Builds indexes for 5-Tier Cascade TM Search:
- Tier 1: whole_text_lookup (hash index for O(1) exact match)
- Tier 2: whole FAISS HNSW (semantic whole-text search)
- Tier 3: line_lookup (hash index for O(1) line match)
- Tier 4: line FAISS HNSW (semantic line-by-line search)

FEAT-005: Uses Model2Vec by default (79x faster than Qwen).
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
    import faiss
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("faiss not available - TM indexing disabled")

from server.database.models import LDMTranslationMemory, LDMTMEntry, LDMTMIndex
from server.tools.shared import FAISSManager, get_embedding_engine, get_current_engine_name

# FAISS HNSW parameters now managed by FAISSManager (server/tools/shared/faiss_manager.py)


def normalize_newlines_universal(text: str) -> str:
    """
    Universal newline normalization for ALL formats.

    Handles:
    - \\n (escaped newlines in TEXT files)
    - \r\n, \r (Windows/Mac line endings)
    - <br/>, <br /> (XML unescaped)
    - &lt;br/&gt;, &lt;br /&gt; (XML escaped)

    All converted to canonical \n for consistent matching.
    """
    if not text:
        return text

    # 1. Escaped \\n → \n (TEXT files store as literal backslash-n)
    text = text.replace('\\n', '\n')

    # 2. XML <br/> variants → \n
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')
    text = text.replace('<BR/>', '\n')
    text = text.replace('<BR />', '\n')

    # 3. HTML-escaped &lt;br/&gt; variants → \n
    text = text.replace('&lt;br/&gt;', '\n')
    text = text.replace('&lt;br /&gt;', '\n')
    text = text.replace('&LT;BR/&GT;', '\n')
    text = text.replace('&LT;BR /&GT;', '\n')

    # 4. Windows/Mac line endings → \n
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')

    return text


def normalize_for_hash(text: str) -> str:
    """
    Normalize text for hash-based lookup.
    Handles newlines, whitespace, case.
    """
    if not text:
        return ""
    # Universal newline normalization first
    text = normalize_newlines_universal(text)
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
    # Universal newline normalization
    text = normalize_newlines_universal(text)
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
        self._engine = None  # EmbeddingEngine instance (lazy loaded)

        # Set data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "ldm_tm"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"TMIndexer initialized", {"data_dir": str(self.data_dir)})

    def _ensure_model_loaded(self):
        """Load the embedding engine if not already loaded."""
        if not MODELS_AVAILABLE:
            raise RuntimeError("faiss not available - TM indexing disabled")

        if self._engine is None or not self._engine.is_loaded:
            engine_name = get_current_engine_name()
            logger.info(f"Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"Embedding engine loaded: {self._engine.name} (dim={self._engine.dimension})")

    @property
    def model(self):
        """Backward compatibility: return engine for code that uses self.model.encode()."""
        self._ensure_model_loaded()
        return self._engine

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

            # Convert to list of dicts (include string_id for StringID mode)
            entry_list = [
                {
                    "id": e.id,
                    "source_text": e.source_text,
                    "target_text": e.target_text,
                    "string_id": e.string_id  # Include StringID metadata
                }
                for e in entries
            ]

            # DEBUG: Log StringID presence for troubleshooting
            stringid_count = sum(1 for e in entry_list if e.get("string_id"))
            logger.info(f"DEBUG: {stringid_count}/{len(entry_list)} entries have string_id")

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
                "model": self._engine.name if self._engine else "unknown",
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

        For StringID mode: stores list of variations for same source text.
        For Standard mode: stores single entry (first one wins).
        """
        logger.info("Building whole_text_lookup...")
        lookup = {}

        for entry in entries:
            source = entry["source_text"]
            if not source:
                continue

            # Primary key: normalized text
            normalized = normalize_for_hash(source)
            if not normalized:
                continue

            entry_data = {
                "entry_id": entry["id"],
                "source_text": source,
                "target_text": entry["target_text"],
                "string_id": entry.get("string_id")  # Include StringID metadata
            }

            if normalized not in lookup:
                # First entry for this source - store as single or list
                if entry.get("string_id"):
                    # StringID mode: store as list of variations
                    lookup[normalized] = {
                        "variations": [entry_data],
                        "source_text": source
                    }
                else:
                    # Standard mode: store single entry
                    lookup[normalized] = entry_data
            else:
                # Additional entry for same source
                existing = lookup[normalized]
                if "variations" in existing:
                    # Already in variations mode - append
                    existing["variations"].append(entry_data)
                elif entry.get("string_id"):
                    # Convert to variations mode
                    lookup[normalized] = {
                        "variations": [existing, entry_data],
                        "source_text": source
                    }
                # else: Standard mode - keep first entry only

            # Also index stripped version (same logic)
            stripped = normalized.strip()
            if stripped and stripped != normalized and stripped not in lookup:
                if entry.get("string_id"):
                    lookup[stripped] = {
                        "variations": [entry_data],
                        "source_text": source
                    }
                else:
                    lookup[stripped] = entry_data

        # DEBUG: Log variations with string_ids
        variations_count = sum(1 for v in lookup.values() if "variations" in v)
        logger.info(f"Built whole_text_lookup: {len(lookup):,} entries, {variations_count} with variations")

        # Sample first entry with variations to verify string_id stored
        for key, val in lookup.items():
            if "variations" in val:
                sample_sids = [v.get("string_id") for v in val["variations"]]
                logger.info(f"DEBUG: Sample variations for '{key[:20]}...': string_ids={sample_sids}")
                break

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
                        "total_lines": len(source_lines),
                        "string_id": entry.get("string_id")  # Include StringID metadata
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
                    "target_text": entry["target_text"],
                    "string_id": entry.get("string_id")  # Include StringID metadata
                })

        if not texts:
            logger.warning("No texts to embed for whole embeddings")
            return {"count": 0, "dim": 0}

        # Generate embeddings using current engine (Model2Vec or Qwen)
        logger.info(f"Encoding {len(texts):,} whole texts using {self.model.name}...")
        embeddings = self.model.encode(texts, normalize=True, show_progress=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        # Build FAISS HNSW index using FAISSManager (handles normalization)
        dim = embeddings.shape[1]
        logger.info(f"Building FAISS HNSW index (dim={dim}, M={FAISSManager.HNSW_M})...")

        index = FAISSManager.build_index(
            embeddings,
            path=tm_path / "faiss" / "whole.index",
            normalize=True
        )

        # Save embeddings and mapping (index already saved by FAISSManager)
        np.save(tm_path / "embeddings" / "whole.npy", embeddings)
        self._save_pickle(mapping, tm_path / "embeddings" / "whole_mapping.pkl")

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
                    "target_line": target_line,
                    "string_id": entry.get("string_id")  # Include StringID metadata
                })

        if not texts:
            logger.warning("No texts to embed for line embeddings")
            return {"count": 0, "dim": 0}

        # Generate embeddings using current engine
        logger.info(f"Encoding {len(texts):,} lines using {self.model.name}...")
        embeddings = self.model.encode(texts, normalize=True, show_progress=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        # Build FAISS HNSW index using FAISSManager (handles normalization)
        dim = embeddings.shape[1]
        logger.info(f"Building FAISS HNSW line index (dim={dim})...")

        index = FAISSManager.build_index(
            embeddings,
            path=tm_path / "faiss" / "line.index",
            normalize=True
        )

        # Save embeddings and mapping (index already saved by FAISSManager)
        np.save(tm_path / "embeddings" / "line.npy", embeddings)
        self._save_pickle(mapping, tm_path / "embeddings" / "line_mapping.pkl")

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

        # Line embeddings are optional (may not exist if TM has no multi-line entries)
        line_npy_path = tm_path / "embeddings" / "line.npy"
        line_mapping_path = tm_path / "embeddings" / "line_mapping.pkl"
        if line_npy_path.exists():
            line_embeddings = np.load(line_npy_path)
            line_mapping = self._load_pickle(line_mapping_path)
        else:
            line_embeddings = None
            line_mapping = []
            logger.debug(f"No line embeddings for TM {tm_id} (optional)")

        # Load FAISS indexes using FAISSManager
        whole_index = FAISSManager.load_index(tm_path / "faiss" / "whole.index")

        # Line FAISS index is optional
        line_index_path = tm_path / "faiss" / "line.index"
        if line_index_path.exists():
            line_index = FAISSManager.load_index(line_index_path)
        else:
            line_index = None
            logger.debug(f"No line FAISS index for TM {tm_id} (optional)")

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


# =============================================================================
# TM Searcher - 5-Tier Cascade Search
# =============================================================================

# Default threshold for TM matching (92%)
DEFAULT_THRESHOLD = 0.92

# NPC (Neil's Probabilistic Check) threshold for Target verification
# Originally 80%, but empirical testing showed:
# - "Save" vs "Save file" = 70.6% (should pass but fails at 80%)
# - "Save" vs "Save changes" = 61.3%
# - Korean longer text works better (~89%)
# Lowered to 65% to catch valid variations while rejecting wrong translations
# (Save vs Delete = 59%, which correctly fails at 65%)
NPC_THRESHOLD = 0.65


class TMSearcher:
    """
    5-Tier Cascade TM Search.

    Tier 1: Perfect whole match (hash) → Show if exists
    Tier 2: Whole embedding match (FAISS) → Top 3 ≥92%
    Tier 3: Perfect line match (hash) → Show if exists
    Tier 4: Line embedding match (FAISS) → Top 3 ≥92%
    Tier 5: N-gram fallback → Top 3 ≥92%

    FEAT-005: Uses Model2Vec by default (79x faster than Qwen).

    Usage:
        searcher = TMSearcher(indexes)
        results = searcher.search("query text")
    """

    def __init__(
        self,
        indexes: Dict[str, Any],
        model=None,  # EmbeddingEngine or None
        threshold: float = DEFAULT_THRESHOLD
    ):
        """
        Initialize TMSearcher with loaded indexes.

        Args:
            indexes: Dict from TMIndexer.load_indexes()
            model: EmbeddingEngine instance (will load default if None)
            threshold: Similarity threshold (default 0.92)
        """
        self.indexes = indexes
        self.threshold = threshold
        self._engine = model  # EmbeddingEngine (lazy loaded)

        # Extract indexes for easy access
        self.whole_lookup = indexes.get("whole_lookup", {})
        self.line_lookup = indexes.get("line_lookup", {})
        self.whole_index = indexes.get("whole_index")
        self.line_index = indexes.get("line_index")
        self.whole_mapping = indexes.get("whole_mapping", [])
        self.line_mapping = indexes.get("line_mapping", [])

    def _ensure_model_loaded(self):
        """Load embedding engine if not already loaded."""
        if self._engine is None or not self._engine.is_loaded:
            if not MODELS_AVAILABLE:
                raise RuntimeError("faiss not available")
            engine_name = get_current_engine_name()
            logger.info(f"Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"Embedding engine loaded: {self._engine.name}")

    @property
    def model(self):
        """Backward compatibility: return engine for code that uses self.model.encode()."""
        self._ensure_model_loaded()
        return self._engine

    def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        Perform 5-Tier Cascade search.

        Args:
            query: Source text to search
            top_k: Max results for embedding tiers (default 3)
            threshold: Override default threshold

        Returns:
            Dict with:
                - tier: Which tier produced results (1-5)
                - tier_name: Tier description
                - results: List of match dicts
                - perfect_match: True if Tier 1 or 3
        """
        if not query:
            return {"tier": 0, "tier_name": "empty", "results": [], "perfect_match": False}

        threshold = threshold or self.threshold

        # Normalize query
        query_normalized = normalize_for_hash(query)
        query_for_embedding = normalize_for_embedding(query)

        # =====================================================================
        # TIER 1: Perfect Whole Match (Hash Lookup)
        # =====================================================================
        # DEBUG: Log Tier 1 attempt
        logger.info(f"DEBUG Tier1: query='{query[:30]}', normalized='{query_normalized[:30]}', lookup_size={len(self.whole_lookup)}")
        if query_normalized in self.whole_lookup:
            match = self.whole_lookup[query_normalized]
            logger.info(f"DEBUG Tier1: MATCH FOUND! has_variations={'variations' in match}")

            # Handle both standard and variations structures
            if "variations" in match:
                # StringID mode: return all variations
                results = []
                for var in match["variations"]:
                    results.append({
                        "entry_id": var["entry_id"],
                        "source_text": var["source_text"],
                        "target_text": var["target_text"],
                        "string_id": var.get("string_id"),
                        "score": 1.0,
                        "match_type": "perfect_whole"
                    })
            else:
                # Standard mode: single entry
                results = [{
                    "entry_id": match["entry_id"],
                    "source_text": match["source_text"],
                    "target_text": match["target_text"],
                    "string_id": match.get("string_id"),
                    "score": 1.0,
                    "match_type": "perfect_whole"
                }]

            return {
                "tier": 1,
                "tier_name": "perfect_whole",
                "perfect_match": True,
                "results": results
            }

        # =====================================================================
        # TIER 2: Whole Embedding Match (FAISS)
        # =====================================================================
        if self.whole_index and self.whole_mapping:
            self._ensure_model_loaded()

            # Generate query embedding
            query_embedding = self.model.encode(
                [query_for_embedding],
                normalize=True,
                show_progress=False
            )
            query_embedding = np.array(query_embedding, dtype=np.float32)

            # Search FAISS
            scores, indices = self.whole_index.search(query_embedding, min(top_k * 2, 20))

            # Filter by threshold
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < 0 or idx >= len(self.whole_mapping):
                    continue
                if score < threshold:
                    continue

                match = self.whole_mapping[idx]
                results.append({
                    "entry_id": match["entry_id"],
                    "source_text": match["source_text"],
                    "target_text": match["target_text"],
                    "string_id": match.get("string_id"),
                    "score": float(score),
                    "match_type": "whole_embedding"
                })

                if len(results) >= top_k:
                    break

            if results:
                logger.debug(f"Tier 2 matches: {len(results)} results")
                return {
                    "tier": 2,
                    "tier_name": "whole_embedding",
                    "perfect_match": False,
                    "results": results
                }

        # =====================================================================
        # TIER 3: Perfect Line Match (Hash Lookup)
        # =====================================================================
        query_lines = query.split('\n')
        line_matches = []

        for i, line in enumerate(query_lines):
            line_normalized = normalize_for_hash(line)
            if not line_normalized:
                continue

            if line_normalized in self.line_lookup:
                match = self.line_lookup[line_normalized]
                line_matches.append({
                    "entry_id": match["entry_id"],
                    "source_line": match["source_line"],
                    "target_line": match["target_line"],
                    "string_id": match.get("string_id"),
                    "query_line_num": i,
                    "tm_line_num": match["line_num"],
                    "score": 1.0,
                    "match_type": "perfect_line"
                })

        if line_matches:
            logger.debug(f"Tier 3 matches: {len(line_matches)} lines")
            return {
                "tier": 3,
                "tier_name": "perfect_line",
                "perfect_match": True,
                "results": line_matches
            }

        # =====================================================================
        # TIER 4: Line Embedding Match (FAISS)
        # =====================================================================
        if self.line_index and self.line_mapping and query_lines:
            self._ensure_model_loaded()

            line_results = []

            for i, line in enumerate(query_lines):
                line_for_embedding = normalize_for_embedding(line)
                if not line_for_embedding or len(line_for_embedding) < 3:
                    continue

                # Generate line embedding
                line_embedding = self.model.encode(
                    [line_for_embedding],
                    normalize=True,
                    show_progress=False
                )
                line_embedding = np.array(line_embedding, dtype=np.float32)

                # Search FAISS for this line
                scores, indices = self.line_index.search(line_embedding, min(top_k * 2, 20))

                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0 or idx >= len(self.line_mapping):
                        continue
                    if score < threshold:
                        continue

                    match = self.line_mapping[idx]
                    line_results.append({
                        "entry_id": match["entry_id"],
                        "source_line": match["source_line"],
                        "target_line": match["target_line"],
                        "string_id": match.get("string_id"),
                        "query_line_num": i,
                        "tm_line_num": match["line_num"],
                        "score": float(score),
                        "match_type": "line_embedding"
                    })
                    break  # Best match per query line

            if line_results:
                # Sort by score, take top_k
                line_results.sort(key=lambda x: x["score"], reverse=True)
                logger.debug(f"Tier 4 matches: {len(line_results)} lines")
                return {
                    "tier": 4,
                    "tier_name": "line_embedding",
                    "perfect_match": False,
                    "results": line_results[:top_k]
                }

        # =====================================================================
        # TIER 5: N-gram Fallback (Character Similarity)
        # =====================================================================
        results = self._ngram_search(query_normalized, top_k, threshold)

        if results:
            logger.debug(f"Tier 5 matches: {len(results)} results")
            return {
                "tier": 5,
                "tier_name": "ngram_fallback",
                "perfect_match": False,
                "results": results
            }

        # No matches found
        return {
            "tier": 0,
            "tier_name": "no_match",
            "perfect_match": False,
            "results": []
        }

    def _ngram_search(
        self,
        query: str,
        top_k: int,
        threshold: float,
        n: int = 3
    ) -> List[Dict]:
        """
        N-gram based fallback search for Tier 5.

        Uses character n-grams for fuzzy matching.
        Less accurate than embeddings but catches edge cases.

        Args:
            query: Normalized query text
            top_k: Max results
            threshold: Similarity threshold
            n: N-gram size (default 3)

        Returns:
            List of matches
        """
        if not query or len(query) < n:
            return []

        # Generate query n-grams
        query_ngrams = self._get_ngrams(query, n)
        if not query_ngrams:
            return []

        # Score candidates from whole_lookup
        scores = []
        for normalized_text, match in self.whole_lookup.items():
            if not normalized_text or len(normalized_text) < n:
                continue

            candidate_ngrams = self._get_ngrams(normalized_text, n)
            if not candidate_ngrams:
                continue

            # Jaccard similarity on n-grams
            intersection = len(query_ngrams & candidate_ngrams)
            union = len(query_ngrams | candidate_ngrams)
            score = intersection / union if union > 0 else 0

            if score >= threshold:
                scores.append((score, match))

        # Sort by score, take top_k
        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, match in scores[:top_k]:
            results.append({
                "entry_id": match["entry_id"],
                "source_text": match["source_text"],
                "target_text": match["target_text"],
                "score": score,
                "match_type": "ngram"
            })

        return results

    def _get_ngrams(self, text: str, n: int) -> set:
        """Generate character n-grams from text."""
        if len(text) < n:
            return set()
        return set(text[i:i+n] for i in range(len(text) - n + 1))

    def search_batch(
        self,
        queries: List[str],
        top_k: int = 3,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Batch search for multiple queries.

        Args:
            queries: List of source texts
            top_k: Max results per query
            threshold: Override threshold

        Returns:
            List of search results (one per query)
        """
        return [self.search(q, top_k, threshold) for q in queries]

    def npc_check(
        self,
        user_target: str,
        tm_matches: List[Dict],
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        NPC (Neil's Probabilistic Check) - Verify translation consistency.

        Checks if user's Target translation is consistent with TM Targets
        for the matched Source entries.

        Flow:
        1. Embed user's Target (1 embedding call)
        2. Embed each TM Target from matches (or use cached if available)
        3. Compute cosine similarity
        4. If any match ≥80%, translation is consistent
        5. If no matches, flag potential inconsistency

        Args:
            user_target: User's translation (Target text)
            tm_matches: List of TM matches from search results
            threshold: Similarity threshold (default 0.80 / NPC_THRESHOLD)

        Returns:
            Dict with:
                - consistent: True if any TM Target matches ≥threshold
                - best_match: Best matching TM entry (if any)
                - best_score: Highest similarity score
                - all_scores: List of (tm_target, score) pairs
                - warning: Warning message if inconsistent
        """
        if not user_target or not tm_matches:
            return {
                "consistent": False,
                "best_match": None,
                "best_score": 0.0,
                "all_scores": [],
                "warning": "No target text or TM matches to check"
            }

        threshold = threshold or NPC_THRESHOLD

        # Normalize user target
        user_target_normalized = normalize_for_embedding(user_target)
        if not user_target_normalized:
            return {
                "consistent": False,
                "best_match": None,
                "best_score": 0.0,
                "all_scores": [],
                "warning": "Empty target text after normalization"
            }

        # Load model
        self._ensure_model_loaded()

        # Embed user's target (1 call)
        user_embedding = self.model.encode(
            [user_target_normalized],
            normalize=True,
            show_progress=False
        )
        user_embedding = np.array(user_embedding, dtype=np.float32)

        # Get TM targets to compare
        tm_targets = []
        for match in tm_matches:
            # Handle both whole and line match formats
            target = match.get("target_text") or match.get("target_line", "")
            if target:
                tm_targets.append((match, target))

        if not tm_targets:
            return {
                "consistent": False,
                "best_match": None,
                "best_score": 0.0,
                "all_scores": [],
                "warning": "No TM targets to compare against"
            }

        # Embed TM targets
        tm_target_texts = [normalize_for_embedding(t[1]) for t in tm_targets]
        tm_target_texts = [t if t else " " for t in tm_target_texts]  # Handle empty

        tm_embeddings = self.model.encode(
            tm_target_texts,
            normalize=True,
            show_progress=False
        )
        tm_embeddings = np.array(tm_embeddings, dtype=np.float32)

        # Compute cosine similarities (dot product since normalized)
        similarities = np.dot(tm_embeddings, user_embedding.T).flatten()

        # Find best match
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_match = tm_targets[best_idx][0]

        # Build all scores
        all_scores = [
            {
                "tm_target": tm_targets[i][1],
                "score": float(similarities[i]),
                "entry_id": tm_targets[i][0].get("entry_id")
            }
            for i in range(len(similarities))
        ]
        all_scores.sort(key=lambda x: x["score"], reverse=True)

        # Check consistency
        consistent = best_score >= threshold

        result = {
            "consistent": consistent,
            "best_match": best_match,
            "best_score": best_score,
            "all_scores": all_scores,
            "threshold": threshold
        }

        if not consistent:
            result["warning"] = (
                f"Target translation may be inconsistent. "
                f"Best TM match similarity: {best_score:.1%} (threshold: {threshold:.0%})"
            )
        else:
            result["message"] = (
                f"Translation consistent with TM. "
                f"Best match: {best_score:.1%} similarity"
            )

        return result

    def search_with_npc(
        self,
        source: str,
        user_target: str,
        top_k: int = 3,
        search_threshold: float = None,
        npc_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Combined search + NPC check in one call.

        Performs 5-Tier Cascade search, then runs NPC on results.

        Args:
            source: Source text to search
            user_target: User's translation to verify
            top_k: Max TM results
            search_threshold: TM search threshold (default 0.92)
            npc_threshold: NPC threshold (default 0.80)

        Returns:
            Dict with search results + NPC verification
        """
        # Perform search
        search_result = self.search(source, top_k, search_threshold)

        # Run NPC if we have matches
        if search_result["results"]:
            npc_result = self.npc_check(
                user_target,
                search_result["results"],
                npc_threshold
            )
        else:
            npc_result = {
                "consistent": None,  # Can't verify without matches
                "best_match": None,
                "best_score": 0.0,
                "all_scores": [],
                "message": "No TM matches found for NPC verification"
            }

        return {
            "search": search_result,
            "npc": npc_result
        }


# =============================================================================
# TM Sync Manager - PKL vs DB Synchronization
# =============================================================================

class TMSyncManager:
    """
    Manages synchronization between DB (central) and PKL/FAISS (local).

    Sync Strategy:
    - DB is always up-to-date (source of truth)
    - PKL/FAISS is local cache, synced on demand
    - Uses pd.merge on Source to detect:
      - INSERT: in DB, not in PKL
      - UPDATE: in both, but Target changed
      - DELETE: in PKL, not in DB (don't copy)
      - UNCHANGED: same Source and Target (copy existing embedding)

    FEAT-005: Uses Model2Vec by default (79x faster than Qwen).
    - Only embedding INSERT/UPDATE entries
    - Reusing existing embeddings for UNCHANGED entries

    Usage:
        sync_manager = TMSyncManager(db, tm_id)
        result = sync_manager.sync()
    """

    def __init__(
        self,
        db: Session,
        tm_id: int,
        data_dir: str = None
    ):
        """
        Initialize TMSyncManager.

        Args:
            db: SQLAlchemy session
            tm_id: Translation Memory ID
            data_dir: Base directory for TM data
        """
        self.db = db
        self.tm_id = tm_id
        self._engine = None  # EmbeddingEngine (lazy loaded)

        # Set data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "ldm_tm"

        self.tm_path = self.data_dir / str(tm_id)

    def _ensure_model_loaded(self):
        """Load embedding engine if not already loaded."""
        if self._engine is None or not self._engine.is_loaded:
            if not MODELS_AVAILABLE:
                raise RuntimeError("faiss not available")
            engine_name = get_current_engine_name()
            logger.info(f"Loading embedding engine: {engine_name}")
            self._engine = get_embedding_engine(engine_name)
            self._engine.load()
            logger.success(f"Embedding engine loaded: {self._engine.name}")

    @property
    def model(self):
        """Backward compatibility: return engine for code that uses self.model.encode()."""
        self._ensure_model_loaded()
        return self._engine

    def get_db_entries(self) -> List[Dict]:
        """
        Get current TM entries from database.

        Returns:
            List of entry dicts with source_text, target_text, id
        """
        entries = self.db.query(LDMTMEntry).filter(
            LDMTMEntry.tm_id == self.tm_id
        ).all()

        return [
            {
                "id": e.id,
                "source_text": e.source_text,
                "target_text": e.target_text,
                "string_id": e.string_id  # Include StringID for variations
            }
            for e in entries
        ]

    def get_pkl_state(self) -> Optional[Dict]:
        """
        Load current PKL state (embeddings + mapping).

        Returns:
            Dict with embeddings, mapping, lookup if exists, else None
        """
        whole_emb_path = self.tm_path / "embeddings" / "whole.npy"
        whole_map_path = self.tm_path / "embeddings" / "whole_mapping.pkl"
        whole_lookup_path = self.tm_path / "hash" / "whole_lookup.pkl"

        if not whole_map_path.exists():
            return None

        try:
            embeddings = np.load(whole_emb_path) if whole_emb_path.exists() else None
            with open(whole_map_path, 'rb') as f:
                mapping = pickle.load(f)
            lookup = None
            if whole_lookup_path.exists():
                with open(whole_lookup_path, 'rb') as f:
                    lookup = pickle.load(f)

            return {
                "embeddings": embeddings,
                "mapping": mapping,
                "lookup": lookup
            }
        except Exception as e:
            logger.error(f"Failed to load PKL state: {e}")
            return None

    def compute_diff(
        self,
        db_entries: List[Dict],
        pkl_state: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Compute diff between DB and PKL using pd.merge on Source.

        Args:
            db_entries: Current DB entries
            pkl_state: Current PKL state (or None for fresh build)

        Returns:
            Dict with:
                - insert: entries to add (in DB, not in PKL)
                - update: entries to update (Target changed)
                - delete: entries to remove (in PKL, not in DB)
                - unchanged: entries with same Source+Target
        """
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas required for TM sync")

        # Build DB dataframe
        db_df = pd.DataFrame(db_entries)
        if db_df.empty:
            return {
                "insert": [],
                "update": [],
                "delete": [],
                "unchanged": [],
                "stats": {"insert": 0, "update": 0, "delete": 0, "unchanged": 0}
            }

        # Normalize source for comparison
        db_df["source_normalized"] = db_df["source_text"].apply(normalize_for_hash)

        # If no PKL state, everything is INSERT
        if pkl_state is None or not pkl_state.get("mapping"):
            insert_list = db_df.to_dict("records")
            return {
                "insert": insert_list,
                "update": [],
                "delete": [],
                "unchanged": [],
                "stats": {
                    "insert": len(insert_list),
                    "update": 0,
                    "delete": 0,
                    "unchanged": 0
                }
            }

        # Build PKL dataframe from mapping
        pkl_mapping = pkl_state["mapping"]
        pkl_df = pd.DataFrame(pkl_mapping)

        if pkl_df.empty:
            insert_list = db_df.to_dict("records")
            return {
                "insert": insert_list,
                "update": [],
                "delete": [],
                "unchanged": [],
                "stats": {
                    "insert": len(insert_list),
                    "update": 0,
                    "delete": 0,
                    "unchanged": 0
                }
            }

        pkl_df["source_normalized"] = pkl_df["source_text"].apply(normalize_for_hash)

        # Merge on normalized source
        merged = pd.merge(
            db_df,
            pkl_df,
            on="source_normalized",
            how="outer",
            suffixes=("_db", "_pkl"),
            indicator=True
        )

        # Categorize
        insert_mask = merged["_merge"] == "left_only"
        delete_mask = merged["_merge"] == "right_only"
        both_mask = merged["_merge"] == "both"

        # For 'both': check if Target changed
        if both_mask.any():
            both_df = merged[both_mask].copy()
            # Compare targets (normalize for fair comparison)
            both_df["target_db_norm"] = both_df["target_text_db"].fillna("").apply(str.strip)
            both_df["target_pkl_norm"] = both_df["target_text_pkl"].fillna("").apply(str.strip)
            both_df["target_changed"] = both_df["target_db_norm"] != both_df["target_pkl_norm"]

            update_df = both_df[both_df["target_changed"]]
            unchanged_df = both_df[~both_df["target_changed"]]
        else:
            update_df = pd.DataFrame()
            unchanged_df = pd.DataFrame()

        # Build result lists
        insert_list = []
        for _, row in merged[insert_mask].iterrows():
            insert_list.append({
                "id": row.get("id_db") or row.get("id"),
                "source_text": row.get("source_text_db") or row.get("source_text"),
                "target_text": row.get("target_text_db") or row.get("target_text"),
                "source_normalized": row["source_normalized"]
            })

        update_list = []
        for _, row in update_df.iterrows():
            update_list.append({
                "id": row.get("id_db"),
                "source_text": row.get("source_text_db"),
                "target_text": row.get("target_text_db"),
                "source_normalized": row["source_normalized"],
                "old_target": row.get("target_text_pkl")
            })

        delete_list = []
        for _, row in merged[delete_mask].iterrows():
            delete_list.append({
                "id": row.get("id_pkl"),
                "source_text": row.get("source_text_pkl"),
                "target_text": row.get("target_text_pkl"),
                "source_normalized": row["source_normalized"]
            })

        unchanged_list = []
        for _, row in unchanged_df.iterrows():
            unchanged_list.append({
                "id": row.get("id_db"),
                "source_text": row.get("source_text_db"),
                "target_text": row.get("target_text_db"),
                "source_normalized": row["source_normalized"]
            })

        return {
            "insert": insert_list,
            "update": update_list,
            "delete": delete_list,
            "unchanged": unchanged_list,
            "stats": {
                "insert": len(insert_list),
                "update": len(update_list),
                "delete": len(delete_list),
                "unchanged": len(unchanged_list)
            }
        }

    def _incremental_sync(
        self,
        diff: Dict[str, Any],
        pkl_state: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int, int], None]],
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        PERF-001: Incremental FAISS sync for INSERT-only changes.

        Instead of rebuilding the entire FAISS index, this method:
        1. Loads the existing FAISS index
        2. Generates embeddings only for new INSERT entries
        3. Adds new vectors to existing index (incremental)
        4. Appends to existing embeddings/mapping files

        This reduces sync time from ~10s to ~0.1s for small additions.

        Args:
            diff: Result from compute_diff()
            pkl_state: Current PKL state (embeddings, mapping)
            progress_callback: Optional progress callback
            start_time: Sync start time for elapsed calculation

        Returns:
            Dict with sync results
        """
        stats = diff["stats"]
        insert_entries = diff["insert"]
        unchanged_entries = diff["unchanged"]

        if progress_callback:
            progress_callback("Generating embeddings (incremental)", 2, 5)

        # Load model for embedding new entries
        self._ensure_model_loaded()

        # Generate embeddings only for INSERT entries
        texts_to_embed = [
            normalize_for_embedding(e["source_text"])
            for e in insert_entries
        ]
        texts_to_embed = [t for t in texts_to_embed if t]

        if not texts_to_embed:
            logger.warning("No valid texts to embed in incremental sync")
            return self._return_sync_result(diff, start_time, 0, len(unchanged_entries))

        logger.info(f"PERF-001: Embedding {len(texts_to_embed)} new entries (incremental) using {self.model.name}")
        new_embeddings = self.model.encode(
            texts_to_embed,
            normalize=True,
            show_progress=False
        )
        new_embeddings = np.array(new_embeddings, dtype=np.float32)

        if progress_callback:
            progress_callback("Updating indexes (incremental)", 3, 5)

        # Load existing embeddings and mapping
        existing_embeddings = pkl_state["embeddings"]
        existing_mapping = pkl_state.get("mapping", [])

        # Build new mapping entries for INSERTs
        new_mapping_entries = []
        for entry in insert_entries:
            new_mapping_entries.append({
                "entry_id": entry["id"],
                "source_text": entry["source_text"],
                "target_text": entry["target_text"],
                "string_id": entry.get("string_id")  # Include StringID for variations
            })

        # Append new embeddings to existing
        combined_embeddings = np.vstack([existing_embeddings, new_embeddings])
        combined_mapping = existing_mapping + new_mapping_entries

        # Save updated embeddings and mapping
        np.save(self.tm_path / "embeddings" / "whole.npy", combined_embeddings)
        with open(self.tm_path / "embeddings" / "whole_mapping.pkl", 'wb') as f:
            pickle.dump(combined_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)

        # PERF-001: Incremental FAISS add (load existing + add new vectors)
        faiss_index_path = self.tm_path / "faiss" / "whole.index"
        FAISSManager.incremental_add(
            path=faiss_index_path,
            new_vectors=new_embeddings,
            dim=new_embeddings.shape[1],
            normalize=True
        )

        logger.info(f"PERF-001: Added {len(new_embeddings)} vectors to existing index")

        # Update hash lookups (need to add new entries)
        whole_lookup_path = self.tm_path / "hash" / "whole_lookup.pkl"
        line_lookup_path = self.tm_path / "hash" / "line_lookup.pkl"

        # Load existing lookups
        whole_lookup = {}
        line_lookup = {}
        if whole_lookup_path.exists():
            with open(whole_lookup_path, 'rb') as f:
                whole_lookup = pickle.load(f)
        if line_lookup_path.exists():
            with open(line_lookup_path, 'rb') as f:
                line_lookup = pickle.load(f)

        # Add new entries to whole lookup (with variations support for StringID mode)
        for entry in insert_entries:
            src = entry["source_text"]
            if not src:
                continue
            normalized = normalize_for_hash(src)
            if not normalized:
                continue

            entry_data = {
                "entry_id": entry["id"],
                "source_text": src,
                "target_text": entry["target_text"],
                "string_id": entry.get("string_id")
            }

            if normalized not in whole_lookup:
                # First entry for this source
                if entry.get("string_id"):
                    # StringID mode: store as list of variations
                    whole_lookup[normalized] = {
                        "variations": [entry_data],
                        "source_text": src
                    }
                else:
                    # Standard mode: store single entry
                    whole_lookup[normalized] = entry_data
            else:
                # Additional entry for same source
                existing = whole_lookup[normalized]
                if "variations" in existing:
                    # Already in variations mode - append
                    existing["variations"].append(entry_data)
                elif entry.get("string_id"):
                    # Convert to variations mode
                    whole_lookup[normalized] = {
                        "variations": [existing, entry_data],
                        "source_text": src
                    }

        # Add new entries to line lookup
        for entry in insert_entries:
            source = entry["source_text"]
            target = entry["target_text"] or ""
            if not source:
                continue

            source_lines = source.split('\n')
            target_lines = target.split('\n')

            for i, line in enumerate(source_lines):
                if not line.strip():
                    continue
                normalized_line = normalize_for_hash(line)
                if not normalized_line or normalized_line in line_lookup:
                    continue
                target_line = target_lines[i] if i < len(target_lines) else ""
                line_lookup[normalized_line] = {
                    "entry_id": entry["id"],
                    "source_line": line,
                    "target_line": target_line,
                    "line_num": i,
                    "total_lines": len(source_lines)
                }

        # Save updated lookups
        with open(whole_lookup_path, 'wb') as f:
            pickle.dump(whole_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(line_lookup_path, 'wb') as f:
            pickle.dump(line_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

        if progress_callback:
            progress_callback("Saving metadata", 4, 5)

        # Update metadata
        final_count = len(unchanged_entries) + len(insert_entries)
        metadata = {
            "tm_id": self.tm_id,
            "entry_count": final_count,
            "whole_lookup_count": len(whole_lookup),
            "line_lookup_count": len(line_lookup),
            "whole_embeddings_count": len(combined_mapping),
            "embedding_dim": combined_embeddings.shape[1],
            "model": self._engine.name if self._engine else "unknown",
            "synced_at": datetime.now().isoformat(),
            "sync_stats": stats,
            "sync_mode": "incremental"  # PERF-001 marker
        }
        with open(self.tm_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback("Complete", 5, 5)

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.success(
            f"PERF-001: TM {self.tm_id} incremental sync complete in {elapsed:.2f}s: "
            f"INSERT={stats['insert']} (added to existing {stats['unchanged']} entries)"
        )

        return {
            "tm_id": self.tm_id,
            "status": "synced",
            "sync_mode": "incremental",
            "stats": stats,
            "final_count": final_count,
            "embeddings_generated": len(insert_entries),
            "embeddings_reused": len(unchanged_entries),
            "time_seconds": round(elapsed, 2)
        }

    def sync(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Synchronize PKL/FAISS with DB.

        Steps:
        1. Load DB entries
        2. Load current PKL state
        3. Compute diff (INSERT/UPDATE/DELETE/UNCHANGED)
        4. Generate embeddings only for INSERT/UPDATE
        5. Copy existing embeddings for UNCHANGED
        6. Rebuild all indexes

        Args:
            progress_callback: Optional (stage, current, total)

        Returns:
            Dict with sync results
        """
        start_time = datetime.now()

        if progress_callback:
            progress_callback("Loading DB entries", 0, 5)

        # 1. Get current DB state
        db_entries = self.get_db_entries()
        if not db_entries:
            logger.warning(f"No entries in DB for TM {self.tm_id}")
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                "tm_id": self.tm_id,
                "status": "empty",
                "stats": {"insert": 0, "update": 0, "delete": 0, "unchanged": 0},
                "time_seconds": round(elapsed, 2)
            }

        # 2. Load current PKL state
        pkl_state = self.get_pkl_state()

        if progress_callback:
            progress_callback("Computing diff", 1, 5)

        # 3. Compute diff
        diff = self.compute_diff(db_entries, pkl_state)
        stats = diff["stats"]

        logger.info(
            f"TM {self.tm_id} sync diff: "
            f"INSERT={stats['insert']}, UPDATE={stats['update']}, "
            f"DELETE={stats['delete']}, UNCHANGED={stats['unchanged']}"
        )

        # PERF-001: Check if we can use incremental FAISS add
        # Conditions: INSERT only (no UPDATE/DELETE), existing index exists
        faiss_index_path = self.tm_path / "faiss" / "whole.index"
        can_incremental = (
            stats['update'] == 0 and
            stats['delete'] == 0 and
            stats['insert'] > 0 and
            faiss_index_path.exists() and
            pkl_state is not None and
            pkl_state.get("embeddings") is not None
        )

        if can_incremental:
            logger.info(f"PERF-001: Using incremental FAISS add for {stats['insert']} new entries")
            return self._incremental_sync(diff, pkl_state, progress_callback, start_time)

        # Full rebuild path (UPDATE or DELETE detected)
        if stats['update'] > 0 or stats['delete'] > 0:
            logger.info("Full rebuild required (UPDATE/DELETE detected)")

        # If nothing to embed, rebuild from unchanged only
        needs_embedding = diff["insert"] + diff["update"]

        if progress_callback:
            progress_callback("Generating embeddings", 2, 5)

        # 4. Build new embeddings
        self._ensure_model_loaded()

        # Prepare all entries for final state
        final_entries = diff["unchanged"] + diff["insert"] + diff["update"]

        # Build source->index mapping from PKL for unchanged entries
        pkl_source_to_idx = {}
        if pkl_state and pkl_state.get("mapping"):
            for idx, m in enumerate(pkl_state["mapping"]):
                src_norm = normalize_for_hash(m.get("source_text", ""))
                pkl_source_to_idx[src_norm] = idx

        # Generate embeddings
        new_embeddings = []
        new_mapping = []

        # Check if cached embeddings are compatible with current model dimension
        expected_dim = self.model.dimension if hasattr(self.model, 'dimension') else 256
        cached_dim = None
        if pkl_state and pkl_state.get("embeddings") is not None and len(pkl_state["embeddings"]) > 0:
            cached_dim = pkl_state["embeddings"][0].shape[0] if hasattr(pkl_state["embeddings"][0], 'shape') else len(pkl_state["embeddings"][0])

        use_cached = cached_dim is not None and cached_dim == expected_dim

        if not use_cached and cached_dim is not None:
            logger.warning(f"Embedding dimension mismatch: cached={cached_dim}, model={expected_dim}. Re-embedding all entries.")
            # Add unchanged entries to needs_embedding for re-embedding
            needs_embedding = diff["unchanged"] + diff["insert"] + diff["update"]
        else:
            # First, copy unchanged embeddings (dimensions match)
            for entry in diff["unchanged"]:
                src_norm = entry.get("source_normalized") or normalize_for_hash(entry["source_text"])
                if src_norm in pkl_source_to_idx and pkl_state["embeddings"] is not None:
                    idx = pkl_source_to_idx[src_norm]
                    if idx < len(pkl_state["embeddings"]):
                        new_embeddings.append(pkl_state["embeddings"][idx])
                        new_mapping.append({
                            "entry_id": entry["id"],
                            "source_text": entry["source_text"],
                            "target_text": entry["target_text"],
                            "string_id": entry.get("string_id")  # Include StringID for variations
                        })

        # Then generate new embeddings for INSERT/UPDATE
        if needs_embedding:
            texts_to_embed = [
                normalize_for_embedding(e["source_text"])
                for e in needs_embedding
            ]
            texts_to_embed = [t for t in texts_to_embed if t]

            if texts_to_embed:
                logger.info(f"Embedding {len(texts_to_embed)} new/changed entries using {self.model.name}...")
                embeddings = self.model.encode(
                    texts_to_embed,
                    normalize=True,
                    show_progress=False
                )
                embeddings = np.array(embeddings, dtype=np.float32)

                for i, entry in enumerate(needs_embedding):
                    if i < len(embeddings):
                        new_embeddings.append(embeddings[i])
                        new_mapping.append({
                            "entry_id": entry["id"],
                            "source_text": entry["source_text"],
                            "target_text": entry["target_text"],
                            "string_id": entry.get("string_id")  # Include StringID for variations
                        })

        if progress_callback:
            progress_callback("Rebuilding indexes", 3, 5)

        # 5. Rebuild all indexes
        whole_lookup = {}
        line_lookup = {}

        if new_embeddings:
            new_embeddings = np.array(new_embeddings, dtype=np.float32)

            # Ensure directory exists
            self.tm_path.mkdir(parents=True, exist_ok=True)
            (self.tm_path / "hash").mkdir(exist_ok=True)
            (self.tm_path / "embeddings").mkdir(exist_ok=True)
            (self.tm_path / "faiss").mkdir(exist_ok=True)

            # Save embeddings and mapping
            np.save(self.tm_path / "embeddings" / "whole.npy", new_embeddings)
            with open(self.tm_path / "embeddings" / "whole_mapping.pkl", 'wb') as f:
                pickle.dump(new_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Build FAISS index using FAISSManager
            # NOTE: Currently full rebuild. PERF-001 will add incremental add support.
            FAISSManager.build_index(
                new_embeddings,
                path=self.tm_path / "faiss" / "whole.index",
                normalize=True
            )

            # Rebuild hash lookup (with variations support for StringID mode)
            for entry in final_entries:
                src = entry["source_text"]
                if not src:
                    continue
                normalized = normalize_for_hash(src)
                if not normalized:
                    continue

                entry_data = {
                    "entry_id": entry["id"],
                    "source_text": src,
                    "target_text": entry["target_text"],
                    "string_id": entry.get("string_id")
                }

                if normalized not in whole_lookup:
                    # First entry for this source
                    if entry.get("string_id"):
                        # StringID mode: store as list of variations
                        whole_lookup[normalized] = {
                            "variations": [entry_data],
                            "source_text": src
                        }
                    else:
                        # Standard mode: store single entry
                        whole_lookup[normalized] = entry_data
                else:
                    # Additional entry for same source
                    existing = whole_lookup[normalized]
                    if "variations" in existing:
                        # Already in variations mode - append
                        existing["variations"].append(entry_data)
                    elif entry.get("string_id"):
                        # Convert to variations mode
                        whole_lookup[normalized] = {
                            "variations": [existing, entry_data],
                            "source_text": src
                        }
            with open(self.tm_path / "hash" / "whole_lookup.pkl", 'wb') as f:
                pickle.dump(whole_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Rebuild line lookup
            for entry in final_entries:
                source = entry["source_text"]
                target = entry["target_text"] or ""
                if not source:
                    continue

                source_lines = source.split('\n')
                target_lines = target.split('\n')

                for i, line in enumerate(source_lines):
                    if not line.strip():
                        continue
                    normalized_line = normalize_for_hash(line)
                    if not normalized_line or normalized_line in line_lookup:
                        continue
                    target_line = target_lines[i] if i < len(target_lines) else ""
                    line_lookup[normalized_line] = {
                        "entry_id": entry["id"],
                        "source_line": line,
                        "target_line": target_line,
                        "line_num": i,
                        "total_lines": len(source_lines)
                    }
            with open(self.tm_path / "hash" / "line_lookup.pkl", 'wb') as f:
                pickle.dump(line_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Rebuilt indexes: {len(whole_lookup)} whole, {len(line_lookup)} lines")

        if progress_callback:
            progress_callback("Saving metadata", 4, 5)

        # 6. Save metadata
        metadata = {
            "tm_id": self.tm_id,
            "entry_count": len(final_entries),
            "whole_lookup_count": len(whole_lookup),
            "line_lookup_count": len(line_lookup),
            "whole_embeddings_count": len(new_mapping),
            "embedding_dim": new_embeddings.shape[1] if len(new_embeddings) > 0 else 0,
            "model": self._engine.name if self._engine else "unknown",
            "synced_at": datetime.now().isoformat(),
            "sync_stats": stats
        }
        with open(self.tm_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback("Complete", 5, 5)

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.success(
            f"TM {self.tm_id} sync complete in {elapsed:.2f}s: "
            f"INSERT={stats['insert']}, UPDATE={stats['update']}, "
            f"DELETE={stats['delete']}, UNCHANGED={stats['unchanged']}"
        )

        return {
            "tm_id": self.tm_id,
            "status": "synced",
            "sync_mode": "full",  # Full rebuild (UPDATE/DELETE detected)
            "stats": stats,
            "final_count": len(final_entries),
            "embeddings_generated": len(needs_embedding),
            "embeddings_reused": len(diff["unchanged"]),
            "time_seconds": round(elapsed, 2)
        }
