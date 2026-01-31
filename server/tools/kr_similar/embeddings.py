"""
KR Similar Embeddings Manager

Handles Korean BERT model loading, embedding generation,
and dictionary creation/loading for similarity search.

Uses the same model as XLSTransfer: snunlp/KR-SBERT-V40K-klueNLI-augSTS

IMPORTANT: Heavy ML libraries (sentence_transformers, torch) are imported LAZILY
to avoid 3-30+ second startup delays. See docs/CODING_STANDARDS.md for details.
"""

import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

# LAZY IMPORT PATTERN: Heavy ML libraries imported only when needed
# This prevents 3-30+ second startup delays (sentence_transformers loads PyTorch)
# Type hints use TYPE_CHECKING to avoid runtime import
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
    import torch

# Lazy availability check - don't import at module level
_models_available: Optional[bool] = None


def _check_models_available() -> bool:
    """Lazy check if ML models are available. Cached after first call."""
    global _models_available
    if _models_available is None:
        try:
            import sentence_transformers  # noqa: F401
            import faiss  # noqa: F401
            import torch  # noqa: F401
            _models_available = True
        except ImportError:
            _models_available = False
            logger.warning("sentence_transformers/faiss not available - embeddings disabled")
    return _models_available


# For backwards compatibility with code that checks MODELS_AVAILABLE
# Note: This is checked lazily on first access via _check_models_available()
def _get_models_available():
    """Wrapper for backwards compatibility."""
    return _check_models_available()


# Module-level constant for backwards compatibility
# Use _check_models_available() for lazy checking
MODELS_AVAILABLE = True  # Assume True, actual check done lazily in _ensure_model_loaded

from server.tools.kr_similar.core import KRSimilarCore, normalize_text
from server.tools.shared import FAISSManager


# Supported dictionary types (games)
DICT_TYPES = ["BDO", "BDM", "BDC", "CD"]

# Model name (P20: Unified Qwen model for all tools)
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


class EmbeddingsManager:
    """
    Manages Korean BERT embeddings for similarity search.

    Handles:
    - Model loading (shared with XLSTransfer)
    - Embedding generation from text
    - Dictionary creation from language files
    - Dictionary saving/loading
    - FAISS index creation
    """

    def __init__(self, dictionaries_dir: str = None):
        """
        Initialize EmbeddingsManager.

        Args:
            dictionaries_dir: Directory for storing dictionaries
        """
        self.model = None
        self.device = None

        # Set dictionaries directory
        if dictionaries_dir:
            self.dictionaries_dir = Path(dictionaries_dir)
        else:
            # Default: server/data/kr_similar_dictionaries
            self.dictionaries_dir = Path(__file__).parent.parent.parent / "data" / "kr_similar_dictionaries"

        self.dictionaries_dir.mkdir(parents=True, exist_ok=True)

        # Current loaded dictionaries
        self.split_embeddings = None
        self.split_dict = None
        self.split_index = None

        self.whole_embeddings = None
        self.whole_dict = None
        self.whole_index = None

        self.current_dict_type = None

        logger.info(f"EmbeddingsManager initialized", {
            "dictionaries_dir": str(self.dictionaries_dir)
        })

    def _ensure_model_loaded(self):
        """Load the model if not already loaded. Uses lazy imports."""
        if not _check_models_available():
            raise RuntimeError("sentence_transformers not available")

        if self.model is None:
            # LAZY IMPORT: Import heavy ML libraries only when model is needed
            from sentence_transformers import SentenceTransformer
            import torch

            logger.info("Loading Korean BERT model...", {"model": MODEL_NAME})
            self.model = SentenceTransformer(MODEL_NAME)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            logger.success("Korean BERT model loaded", {
                "model": MODEL_NAME,
                "device": str(self.device)
            })

    def encode_texts(self, texts: List[str], batch_size: int = 1000, progress_callback: callable = None) -> np.ndarray:
        """
        Encode texts to embeddings using Korean BERT.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            progress_callback: Optional callback for progress updates

        Returns:
            NumPy array of embeddings
        """
        self._ensure_model_loaded()

        embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, device=self.device)
            embeddings.extend(batch_embeddings)

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

            logger.debug(f"Encoded {min(i + batch_size, total)}/{total} texts")

        return np.array(embeddings)

    def create_dictionary(
        self,
        file_paths: List[str],
        dict_type: str,
        kr_column: int = 5,
        trans_column: int = 6,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Create embeddings dictionary from language files.

        Creates both 'split' (line-by-line) and 'whole' (full text) embeddings.

        Args:
            file_paths: List of language data file paths
            dict_type: Dictionary type (BDO, BDM, BDC, CD)
            kr_column: Korean text column index
            trans_column: Translation column index
            progress_callback: Optional progress callback

        Returns:
            Dict with creation results
        """
        if dict_type not in DICT_TYPES:
            raise ValueError(f"Invalid dict_type: {dict_type}. Must be one of {DICT_TYPES}")

        logger.info(f"Creating dictionary for {dict_type}", {
            "files_count": len(file_paths),
            "dict_type": dict_type
        })

        # Load and combine all files
        all_data = []
        for file_path in file_paths:
            try:
                data = KRSimilarCore.parse_language_file(file_path, kr_column, trans_column)
                all_data.append(data)
                logger.info(f"Loaded {len(data)} rows from {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        if not all_data:
            raise ValueError("No data loaded from files")

        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined {len(combined_data)} total rows")

        # Normalize texts
        logger.info("Normalizing texts...")
        combined_data['Korean'] = combined_data['Korean'].apply(normalize_text)
        combined_data['Translation'] = combined_data['Translation'].apply(normalize_text)

        # Process split embeddings
        split_result = self._process_embeddings_type('split', combined_data, dict_type, progress_callback)

        # Process whole embeddings
        whole_result = self._process_embeddings_type('whole', combined_data, dict_type, progress_callback)

        return {
            "dict_type": dict_type,
            "split_pairs": split_result["pairs"],
            "whole_pairs": whole_result["pairs"],
            "total_pairs": split_result["pairs"] + whole_result["pairs"]
        }

    def _process_embeddings_type(
        self,
        embedding_type: str,
        data: pd.DataFrame,
        dict_type: str,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Process embeddings for a specific type (split or whole).
        Supports incremental update (monolith lines 137-192).

        Args:
            embedding_type: 'split' or 'whole'
            data: DataFrame with Korean and Translation columns
            dict_type: Dictionary type
            progress_callback: Optional progress callback

        Returns:
            Dict with processing results
        """
        logger.info(f"Processing {embedding_type} embeddings for {dict_type}")

        if embedding_type == 'split':
            processed_data = KRSimilarCore.process_split_data(data)
        else:
            processed_data = data.copy()

        # Group by Korean text and select most frequent translation
        processed_data = processed_data.groupby('Korean')['Translation'].agg(
            lambda x: x.value_counts().index[0] if len(x) > 0 else ''
        ).reset_index()

        # Prepare paths
        dict_dir = self.dictionaries_dir / dict_type
        dict_dir.mkdir(parents=True, exist_ok=True)
        embeddings_file = dict_dir / f'{embedding_type}_embeddings.npy'
        dict_file = dict_dir / f'{embedding_type}_translation_dict.pkl'

        # MONOLITH LINES 137-192: Incremental update logic
        if embeddings_file.exists() and dict_file.exists():
            logger.info(f"Found existing {embedding_type} embeddings, performing incremental update")

            # Load existing data (monolith lines 143-148)
            existing_embeddings = np.load(embeddings_file)
            with open(dict_file, 'rb') as f:
                existing_dict = pickle.load(f)

            # Identify new or changed strings (monolith lines 150-154)
            existing_data = pd.DataFrame(list(existing_dict.items()), columns=['Korean', 'French'])
            merged_data = pd.merge(
                processed_data, existing_data,
                on='Korean', how='outer', suffixes=('_new', '_old')
            )
            # Find entries where translation is new or changed
            new_or_changed = merged_data[
                merged_data['Translation'] != merged_data['French']
            ].dropna(subset=['Translation'])

            if len(new_or_changed) == 0:
                logger.info(f"No new or changed strings found for {embedding_type}")
                return {"pairs": len(existing_dict)}

            logger.info(f"Identified {len(new_or_changed)} new or changed {embedding_type} strings")

            # Generate embeddings only for new/changed (monolith lines 157-190)
            new_embeddings = self.encode_texts(
                new_or_changed['Korean'].tolist(),
                progress_callback=progress_callback
            )

            # Update embeddings array - append new ones
            # For changed strings, we need to replace; for new, append
            korean_to_idx = {k: i for i, k in enumerate(existing_dict.keys())}
            updated_embeddings = existing_embeddings.copy()

            for i, korean_text in enumerate(new_or_changed['Korean']):
                if korean_text in korean_to_idx:
                    # Replace existing embedding
                    idx = korean_to_idx[korean_text]
                    updated_embeddings[idx] = new_embeddings[i]
                else:
                    # Append new embedding
                    updated_embeddings = np.vstack([updated_embeddings, new_embeddings[i:i+1]])

            # Update translation dictionary
            translation_dict = existing_dict.copy()
            for _, row in new_or_changed.iterrows():
                translation_dict[row['Korean']] = row['Translation']

            embeddings = updated_embeddings
        else:
            # Full generation (no existing data)
            total_texts = len(processed_data)
            logger.info(f"Total unique {embedding_type} pairs: {total_texts}")

            # Generate all embeddings
            embeddings = self.encode_texts(
                processed_data['Korean'].tolist(),
                progress_callback=progress_callback
            )

            # Create translation dictionary
            translation_dict = dict(zip(processed_data['Korean'], processed_data['Translation']))

        # Save updated embeddings and dictionary (monolith lines 195-198)
        np.save(embeddings_file, embeddings)
        with open(dict_file, 'wb') as f:
            pickle.dump(translation_dict, f)

        logger.success(f"{embedding_type.capitalize()} embeddings saved", {
            "dict_type": dict_type,
            "pairs": len(translation_dict),
            "embeddings_shape": embeddings.shape
        })

        return {"pairs": len(translation_dict)}

    def load_tm(self, tm_id: int, db_session=None) -> bool:
        """
        Load TM data and build indexes.

        LIMIT-002: Uses TMLoader to support both PostgreSQL and SQLite offline mode.

        Args:
            tm_id: Translation Memory ID
            db_session: Optional SQLAlchemy session (ignored, kept for API compatibility)

        Returns:
            True if loaded successfully
        """
        logger.info(f"Loading TM {tm_id} for KR Similar...")

        try:
            # Use TMLoader for unified PostgreSQL/SQLite loading
            from server.tools.shared.tm_loader import TMLoader

            entries = TMLoader.load_entries(tm_id)

            if not entries:
                logger.warning(f"No entries found for TM {tm_id}")
                return False

            logger.info(f"Loaded {len(entries)} entries from TM {tm_id}")

            self._ensure_model_loaded()

            # Build dictionaries (similar to create_dictionary but from TMLoader)
            split_pairs = []
            whole_pairs = []

            for entry in entries:
                # TMLoader returns dicts, not ORM objects
                source = entry.get("source_text", "")
                target = entry.get("target_text", "") or ""

                if not source:
                    continue

                # Split mode: line by line (for texts with multiple lines)
                source_lines = source.split('\n')
                target_lines = target.split('\n')

                if len(source_lines) == len(target_lines) and len(source_lines) > 1:
                    # Line counts match - use split mode
                    for src_line, tgt_line in zip(source_lines, target_lines):
                        src_line = normalize_text(src_line)
                        tgt_line = tgt_line.strip()
                        if src_line:
                            split_pairs.append((src_line, tgt_line))
                else:
                    # Use whole mode
                    whole_pairs.append((normalize_text(source), target))

            # Deduplicate and build dictionaries
            self.split_dict = {}
            for src, tgt in split_pairs:
                if src not in self.split_dict:
                    self.split_dict[src] = tgt

            self.whole_dict = {}
            for src, tgt in whole_pairs:
                if src not in self.whole_dict:
                    self.whole_dict[src] = tgt

            logger.info(f"Built {len(self.split_dict)} split, {len(self.whole_dict)} whole pairs")

            # Generate embeddings and build indexes using FAISSManager
            if self.split_dict:
                split_texts = list(self.split_dict.keys())
                logger.info(f"Encoding {len(split_texts)} split texts...")
                self.split_embeddings = self.encode_texts(split_texts)

                self.split_index = FAISSManager.create_index(self.split_embeddings.shape[1])
                FAISSManager.add_vectors(self.split_index, self.split_embeddings, normalize=True)

            if self.whole_dict:
                whole_texts = list(self.whole_dict.keys())
                logger.info(f"Encoding {len(whole_texts)} whole texts...")
                self.whole_embeddings = self.encode_texts(whole_texts)

                self.whole_index = FAISSManager.create_index(self.whole_embeddings.shape[1])
                FAISSManager.add_vectors(self.whole_index, self.whole_embeddings, normalize=True)

            self.current_dict_type = f"tm_{tm_id}"

            logger.success(f"Loaded TM {tm_id} for KR Similar: {len(self.split_dict)} split, {len(self.whole_dict)} whole")
            return True

        except Exception as e:
            logger.exception(f"Failed to load TM {tm_id}: {e}")
            return False

    def load_dictionary(self, dict_type: str) -> bool:
        """
        Load dictionary into memory for searching.

        Args:
            dict_type: Dictionary type to load (BDO, BDM, BDC, CD)

        Returns:
            True if loaded successfully

        Note:
            For TM-based loading, use load_tm(tm_id) instead.
        """
        if dict_type not in DICT_TYPES:
            raise ValueError(f"Invalid dict_type: {dict_type}. Must be one of {DICT_TYPES}. For TM loading, use load_tm(tm_id) instead.")

        dict_dir = self.dictionaries_dir / dict_type

        # Check if dictionary exists
        split_embeddings_file = dict_dir / 'split_embeddings.npy'
        split_dict_file = dict_dir / 'split_translation_dict.pkl'
        whole_embeddings_file = dict_dir / 'whole_embeddings.npy'
        whole_dict_file = dict_dir / 'whole_translation_dict.pkl'

        if not split_embeddings_file.exists():
            raise FileNotFoundError(f"Dictionary not found: {dict_type}")

        logger.info(f"Loading dictionary: {dict_type}")

        # Load split embeddings
        self.split_embeddings = np.load(split_embeddings_file)
        with open(split_dict_file, 'rb') as f:
            self.split_dict = pickle.load(f)

        # Create FAISS HNSW index for split using FAISSManager
        self.split_index = FAISSManager.create_index(self.split_embeddings.shape[1])
        FAISSManager.add_vectors(self.split_index, self.split_embeddings, normalize=True)

        # Load whole embeddings if available
        if whole_embeddings_file.exists():
            self.whole_embeddings = np.load(whole_embeddings_file)
            with open(whole_dict_file, 'rb') as f:
                self.whole_dict = pickle.load(f)

            # Create FAISS HNSW index for whole using FAISSManager
            self.whole_index = FAISSManager.create_index(self.whole_embeddings.shape[1])
            FAISSManager.add_vectors(self.whole_index, self.whole_embeddings, normalize=True)
        else:
            self.whole_embeddings = None
            self.whole_dict = None
            self.whole_index = None

        self.current_dict_type = dict_type

        logger.success(f"Dictionary loaded: {dict_type}", {
            "split_pairs": len(self.split_dict),
            "whole_pairs": len(self.whole_dict) if self.whole_dict else 0
        })

        return True

    def list_available_dictionaries(self) -> List[Dict[str, Any]]:
        """
        List all available dictionaries.

        Returns:
            List of dictionary info dicts
        """
        dictionaries = []

        for dict_type in DICT_TYPES:
            dict_dir = self.dictionaries_dir / dict_type
            split_file = dict_dir / 'split_embeddings.npy'

            if split_file.exists():
                # Get metadata
                split_dict_file = dict_dir / 'split_translation_dict.pkl'
                whole_dict_file = dict_dir / 'whole_translation_dict.pkl'

                split_pairs = 0
                whole_pairs = 0

                try:
                    with open(split_dict_file, 'rb') as f:
                        split_pairs = len(pickle.load(f))
                except Exception:
                    pass

                try:
                    if whole_dict_file.exists():
                        with open(whole_dict_file, 'rb') as f:
                            whole_pairs = len(pickle.load(f))
                except Exception:
                    pass

                dictionaries.append({
                    "dict_type": dict_type,
                    "split_pairs": split_pairs,
                    "whole_pairs": whole_pairs,
                    "total_pairs": split_pairs + whole_pairs,
                    "created": os.path.getmtime(split_file)
                })

        return dictionaries

    def check_dictionary_exists(self, dict_type: str) -> bool:
        """Check if a dictionary exists."""
        dict_dir = self.dictionaries_dir / dict_type
        return (dict_dir / 'split_embeddings.npy').exists()

    def get_status(self) -> Dict[str, Any]:
        """Get current embeddings manager status."""
        return {
            "model_loaded": self.model is not None,
            "current_dict_type": self.current_dict_type,
            "split_pairs": len(self.split_dict) if self.split_dict else 0,
            "whole_pairs": len(self.whole_dict) if self.whole_dict else 0,
            "dictionaries_dir": str(self.dictionaries_dir),
            "models_available": MODELS_AVAILABLE
        }
