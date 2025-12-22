"""
TM Sync Manager - PKL vs DB Synchronization.

Extracted from tm_indexer.py during P37 refactoring.
"""

import json
import pickle
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

from server.database.models import LDMTMEntry
from server.tools.shared import FAISSManager, get_embedding_engine, get_current_engine_name
from .utils import normalize_for_hash, normalize_for_embedding


class TMSyncManager:
    """
    Manages synchronization between DB (central) and PKL/FAISS (local).

    Sync Strategy:
    - DB is always up-to-date (source of truth)
    - PKL/FAISS is local cache, synced on demand
    - Uses pd.merge on Source to detect:
      - INSERT: in DB, not in PKL
      - UPDATE: in both, but Target changed
      - DELETE: in PKL, not in DB
      - UNCHANGED: same Source and Target
    """

    def __init__(self, db: Session, tm_id: int, data_dir: str = None):
        """
        Initialize TMSyncManager.

        Args:
            db: SQLAlchemy session
            tm_id: Translation Memory ID
            data_dir: Base directory for TM data
        """
        self.db = db
        self.tm_id = tm_id
        self._engine = None

        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "ldm_tm"

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
        """Get current TM entries from database."""
        entries = self.db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == self.tm_id).all()
        return [
            {"id": e.id, "source_text": e.source_text, "target_text": e.target_text, "string_id": e.string_id}
            for e in entries
        ]

    def get_pkl_state(self) -> Optional[Dict]:
        """Load current PKL state (embeddings + mapping)."""
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

            return {"embeddings": embeddings, "mapping": mapping, "lookup": lookup}
        except Exception as e:
            logger.error(f"Failed to load PKL state: {e}")
            return None

    def compute_diff(self, db_entries: List[Dict], pkl_state: Optional[Dict]) -> Dict[str, Any]:
        """
        Compute diff between DB and PKL using pd.merge on Source.

        Returns:
            Dict with insert, update, delete, unchanged, stats
        """
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas required for TM sync")

        db_df = pd.DataFrame(db_entries)
        if db_df.empty:
            return {
                "insert": [], "update": [], "delete": [], "unchanged": [],
                "stats": {"insert": 0, "update": 0, "delete": 0, "unchanged": 0}
            }

        db_df["source_normalized"] = db_df["source_text"].apply(normalize_for_hash)

        if pkl_state is None or not pkl_state.get("mapping"):
            insert_list = db_df.to_dict("records")
            return {
                "insert": insert_list, "update": [], "delete": [], "unchanged": [],
                "stats": {"insert": len(insert_list), "update": 0, "delete": 0, "unchanged": 0}
            }

        pkl_mapping = pkl_state["mapping"]
        pkl_df = pd.DataFrame(pkl_mapping)

        if pkl_df.empty:
            insert_list = db_df.to_dict("records")
            return {
                "insert": insert_list, "update": [], "delete": [], "unchanged": [],
                "stats": {"insert": len(insert_list), "update": 0, "delete": 0, "unchanged": 0}
            }

        pkl_df["source_normalized"] = pkl_df["source_text"].apply(normalize_for_hash)

        merged = pd.merge(db_df, pkl_df, on="source_normalized", how="outer",
                          suffixes=("_db", "_pkl"), indicator=True)

        insert_mask = merged["_merge"] == "left_only"
        delete_mask = merged["_merge"] == "right_only"
        both_mask = merged["_merge"] == "both"

        if both_mask.any():
            both_df = merged[both_mask].copy()
            both_df["target_db_norm"] = both_df["target_text_db"].fillna("").apply(str.strip)
            both_df["target_pkl_norm"] = both_df["target_text_pkl"].fillna("").apply(str.strip)
            both_df["target_changed"] = both_df["target_db_norm"] != both_df["target_pkl_norm"]

            update_df = both_df[both_df["target_changed"]]
            unchanged_df = both_df[~both_df["target_changed"]]
        else:
            update_df = pd.DataFrame()
            unchanged_df = pd.DataFrame()

        insert_list = []
        for _, row in merged[insert_mask].iterrows():
            insert_list.append({
                "id": row.get("id_db") or row.get("id"),
                "source_text": row.get("source_text_db") or row.get("source_text"),
                "target_text": row.get("target_text_db") or row.get("target_text"),
                "source_normalized": row["source_normalized"],
                "string_id": row.get("string_id_db") or row.get("string_id")
            })

        update_list = []
        for _, row in update_df.iterrows():
            update_list.append({
                "id": row.get("id_db"),
                "source_text": row.get("source_text_db"),
                "target_text": row.get("target_text_db"),
                "source_normalized": row["source_normalized"],
                "old_target": row.get("target_text_pkl"),
                "string_id": row.get("string_id_db")
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
                "source_normalized": row["source_normalized"],
                "string_id": row.get("string_id_db")
            })

        return {
            "insert": insert_list, "update": update_list,
            "delete": delete_list, "unchanged": unchanged_list,
            "stats": {
                "insert": len(insert_list), "update": len(update_list),
                "delete": len(delete_list), "unchanged": len(unchanged_list)
            }
        }

    def _return_sync_result(self, diff, start_time, embeddings_gen, embeddings_reused):
        """Helper to return sync result dict."""
        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "tm_id": self.tm_id, "status": "synced", "sync_mode": "incremental",
            "stats": diff["stats"], "final_count": len(diff["unchanged"]) + len(diff["insert"]),
            "embeddings_generated": embeddings_gen, "embeddings_reused": embeddings_reused,
            "time_seconds": round(elapsed, 2)
        }

    def _incremental_sync(
        self, diff: Dict[str, Any], pkl_state: Dict[str, Any],
        progress_callback: Optional[Callable], start_time: datetime
    ) -> Dict[str, Any]:
        """PERF-001: Incremental FAISS sync for INSERT-only changes."""
        stats = diff["stats"]
        insert_entries = diff["insert"]
        unchanged_entries = diff["unchanged"]

        if progress_callback:
            progress_callback("Generating embeddings (incremental)", 2, 5)

        self._ensure_model_loaded()

        texts_to_embed = [normalize_for_embedding(e["source_text"]) for e in insert_entries]
        texts_to_embed = [t for t in texts_to_embed if t]

        if not texts_to_embed:
            logger.warning("No valid texts to embed in incremental sync")
            return self._return_sync_result(diff, start_time, 0, len(unchanged_entries))

        logger.info(f"PERF-001: Embedding {len(texts_to_embed)} new entries using {self.model.name}")
        new_embeddings = self.model.encode(texts_to_embed, normalize=True, show_progress=False)
        new_embeddings = np.array(new_embeddings, dtype=np.float32)

        if progress_callback:
            progress_callback("Updating indexes (incremental)", 3, 5)

        existing_embeddings = pkl_state["embeddings"]
        existing_mapping = pkl_state.get("mapping", [])

        new_mapping_entries = [{
            "entry_id": entry["id"], "source_text": entry["source_text"],
            "target_text": entry["target_text"], "string_id": entry.get("string_id")
        } for entry in insert_entries]

        combined_embeddings = np.vstack([existing_embeddings, new_embeddings])
        combined_mapping = existing_mapping + new_mapping_entries

        np.save(self.tm_path / "embeddings" / "whole.npy", combined_embeddings)
        with open(self.tm_path / "embeddings" / "whole_mapping.pkl", 'wb') as f:
            pickle.dump(combined_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)

        faiss_index_path = self.tm_path / "faiss" / "whole.index"
        FAISSManager.incremental_add(
            path=faiss_index_path, new_vectors=new_embeddings,
            dim=new_embeddings.shape[1], normalize=True
        )

        logger.info(f"PERF-001: Added {len(new_embeddings)} vectors to existing index")

        # Update hash lookups
        whole_lookup_path = self.tm_path / "hash" / "whole_lookup.pkl"
        line_lookup_path = self.tm_path / "hash" / "line_lookup.pkl"

        whole_lookup = {}
        line_lookup = {}
        if whole_lookup_path.exists():
            with open(whole_lookup_path, 'rb') as f:
                whole_lookup = pickle.load(f)
        if line_lookup_path.exists():
            with open(line_lookup_path, 'rb') as f:
                line_lookup = pickle.load(f)

        for entry in insert_entries:
            src = entry["source_text"]
            if not src:
                continue
            normalized = normalize_for_hash(src)
            if not normalized:
                continue

            entry_data = {
                "entry_id": entry["id"], "source_text": src,
                "target_text": entry["target_text"], "string_id": entry.get("string_id")
            }

            if normalized not in whole_lookup:
                if entry.get("string_id"):
                    whole_lookup[normalized] = {"variations": [entry_data], "source_text": src}
                else:
                    whole_lookup[normalized] = entry_data
            else:
                existing = whole_lookup[normalized]
                if "variations" in existing:
                    existing["variations"].append(entry_data)
                elif entry.get("string_id"):
                    whole_lookup[normalized] = {"variations": [existing, entry_data], "source_text": src}

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
                    "entry_id": entry["id"], "source_line": line,
                    "target_line": target_line, "line_num": i, "total_lines": len(source_lines)
                }

        with open(whole_lookup_path, 'wb') as f:
            pickle.dump(whole_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(line_lookup_path, 'wb') as f:
            pickle.dump(line_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

        if progress_callback:
            progress_callback("Saving metadata", 4, 5)

        final_count = len(unchanged_entries) + len(insert_entries)
        metadata = {
            "tm_id": self.tm_id, "entry_count": final_count,
            "whole_lookup_count": len(whole_lookup), "line_lookup_count": len(line_lookup),
            "whole_embeddings_count": len(combined_mapping),
            "embedding_dim": combined_embeddings.shape[1],
            "model": self._engine.name if self._engine else "unknown",
            "synced_at": datetime.now().isoformat(),
            "sync_stats": stats, "sync_mode": "incremental"
        }
        with open(self.tm_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback("Complete", 5, 5)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"PERF-001: TM {self.tm_id} incremental sync complete in {elapsed:.2f}s")

        return {
            "tm_id": self.tm_id, "status": "synced", "sync_mode": "incremental",
            "stats": stats, "final_count": final_count,
            "embeddings_generated": len(insert_entries),
            "embeddings_reused": len(unchanged_entries),
            "time_seconds": round(elapsed, 2)
        }

    def sync(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Dict[str, Any]:
        """
        Synchronize PKL/FAISS with DB.

        Steps:
        1. Load DB entries
        2. Load current PKL state
        3. Compute diff
        4. Generate embeddings for INSERT/UPDATE
        5. Copy existing embeddings for UNCHANGED
        6. Rebuild all indexes
        """
        start_time = datetime.now()

        if progress_callback:
            progress_callback("Loading DB entries", 0, 5)

        db_entries = self.get_db_entries()
        if not db_entries:
            logger.warning(f"No entries in DB for TM {self.tm_id}")
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                "tm_id": self.tm_id, "status": "empty",
                "stats": {"insert": 0, "update": 0, "delete": 0, "unchanged": 0},
                "time_seconds": round(elapsed, 2)
            }

        pkl_state = self.get_pkl_state()

        if progress_callback:
            progress_callback("Computing diff", 1, 5)

        diff = self.compute_diff(db_entries, pkl_state)
        stats = diff["stats"]

        logger.info(f"TM {self.tm_id} sync diff: INSERT={stats['insert']}, UPDATE={stats['update']}, "
                    f"DELETE={stats['delete']}, UNCHANGED={stats['unchanged']}")

        faiss_index_path = self.tm_path / "faiss" / "whole.index"
        can_incremental = (
            stats['update'] == 0 and stats['delete'] == 0 and stats['insert'] > 0 and
            faiss_index_path.exists() and pkl_state is not None and
            pkl_state.get("embeddings") is not None
        )

        if can_incremental:
            logger.info(f"PERF-001: Using incremental FAISS add for {stats['insert']} new entries")
            return self._incremental_sync(diff, pkl_state, progress_callback, start_time)

        if stats['update'] > 0 or stats['delete'] > 0:
            logger.info("Full rebuild required (UPDATE/DELETE detected)")

        needs_embedding = diff["insert"] + diff["update"]

        if progress_callback:
            progress_callback("Generating embeddings", 2, 5)

        self._ensure_model_loaded()

        final_entries = diff["unchanged"] + diff["insert"] + diff["update"]

        pkl_source_to_idx = {}
        if pkl_state and pkl_state.get("mapping"):
            for idx, m in enumerate(pkl_state["mapping"]):
                src_norm = normalize_for_hash(m.get("source_text", ""))
                pkl_source_to_idx[src_norm] = idx

        new_embeddings = []
        new_mapping = []

        expected_dim = self.model.dimension if hasattr(self.model, 'dimension') else 256
        cached_dim = None
        if pkl_state and pkl_state.get("embeddings") is not None and len(pkl_state["embeddings"]) > 0:
            cached_dim = pkl_state["embeddings"][0].shape[0] if hasattr(pkl_state["embeddings"][0], 'shape') else len(pkl_state["embeddings"][0])

        use_cached = cached_dim is not None and cached_dim == expected_dim

        if not use_cached and cached_dim is not None:
            logger.warning(f"Embedding dimension mismatch: cached={cached_dim}, model={expected_dim}. Re-embedding all.")
            needs_embedding = diff["unchanged"] + diff["insert"] + diff["update"]
        else:
            for entry in diff["unchanged"]:
                src_norm = entry.get("source_normalized") or normalize_for_hash(entry["source_text"])
                if src_norm in pkl_source_to_idx and pkl_state["embeddings"] is not None:
                    idx = pkl_source_to_idx[src_norm]
                    if idx < len(pkl_state["embeddings"]):
                        new_embeddings.append(pkl_state["embeddings"][idx])
                        new_mapping.append({
                            "entry_id": entry["id"], "source_text": entry["source_text"],
                            "target_text": entry["target_text"], "string_id": entry.get("string_id")
                        })

        if needs_embedding:
            texts_to_embed = [normalize_for_embedding(e["source_text"]) for e in needs_embedding]
            texts_to_embed = [t for t in texts_to_embed if t]

            if texts_to_embed:
                logger.info(f"Embedding {len(texts_to_embed)} new/changed entries using {self.model.name}...")
                embeddings = self.model.encode(texts_to_embed, normalize=True, show_progress=False)
                embeddings = np.array(embeddings, dtype=np.float32)

                for i, entry in enumerate(needs_embedding):
                    if i < len(embeddings):
                        new_embeddings.append(embeddings[i])
                        new_mapping.append({
                            "entry_id": entry["id"], "source_text": entry["source_text"],
                            "target_text": entry["target_text"], "string_id": entry.get("string_id")
                        })

        if progress_callback:
            progress_callback("Rebuilding indexes", 3, 5)

        whole_lookup = {}
        line_lookup = {}

        if new_embeddings:
            new_embeddings = np.array(new_embeddings, dtype=np.float32)

            self.tm_path.mkdir(parents=True, exist_ok=True)
            (self.tm_path / "hash").mkdir(exist_ok=True)
            (self.tm_path / "embeddings").mkdir(exist_ok=True)
            (self.tm_path / "faiss").mkdir(exist_ok=True)

            np.save(self.tm_path / "embeddings" / "whole.npy", new_embeddings)
            with open(self.tm_path / "embeddings" / "whole_mapping.pkl", 'wb') as f:
                pickle.dump(new_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)

            FAISSManager.build_index(new_embeddings, path=self.tm_path / "faiss" / "whole.index", normalize=True)

            for entry in final_entries:
                src = entry["source_text"]
                if not src:
                    continue
                normalized = normalize_for_hash(src)
                if not normalized:
                    continue

                entry_data = {
                    "entry_id": entry["id"], "source_text": src,
                    "target_text": entry["target_text"], "string_id": entry.get("string_id")
                }

                if normalized not in whole_lookup:
                    if entry.get("string_id"):
                        whole_lookup[normalized] = {"variations": [entry_data], "source_text": src}
                    else:
                        whole_lookup[normalized] = entry_data
                else:
                    existing = whole_lookup[normalized]
                    if "variations" in existing:
                        existing["variations"].append(entry_data)
                    elif entry.get("string_id"):
                        whole_lookup[normalized] = {"variations": [existing, entry_data], "source_text": src}

            with open(self.tm_path / "hash" / "whole_lookup.pkl", 'wb') as f:
                pickle.dump(whole_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

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
                        "entry_id": entry["id"], "source_line": line,
                        "target_line": target_line, "line_num": i, "total_lines": len(source_lines)
                    }

            with open(self.tm_path / "hash" / "line_lookup.pkl", 'wb') as f:
                pickle.dump(line_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Rebuilt indexes: {len(whole_lookup)} whole, {len(line_lookup)} lines")

        if progress_callback:
            progress_callback("Saving metadata", 4, 5)

        metadata = {
            "tm_id": self.tm_id, "entry_count": len(final_entries),
            "whole_lookup_count": len(whole_lookup), "line_lookup_count": len(line_lookup),
            "whole_embeddings_count": len(new_mapping),
            "embedding_dim": new_embeddings.shape[1] if len(new_embeddings) > 0 else 0,
            "model": self._engine.name if self._engine else "unknown",
            "synced_at": datetime.now().isoformat(), "sync_stats": stats
        }
        with open(self.tm_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback("Complete", 5, 5)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"TM {self.tm_id} sync complete in {elapsed:.2f}s")

        return {
            "tm_id": self.tm_id, "status": "synced", "sync_mode": "full",
            "stats": stats, "final_count": len(final_entries),
            "embeddings_generated": len(needs_embedding),
            "embeddings_reused": len(diff["unchanged"]),
            "time_seconds": round(elapsed, 2)
        }
