"""
XLSTransfer Embedding Generation

Model loading, embedding generation, FAISS index creation, and dictionary management.
CLEAN, modular functions for semantic similarity search.
"""

from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from pathlib import Path
import pickle
import numpy as np
import pandas as pd
import faiss
from loguru import logger

from server.tools.xlstransfer import config
from server.tools.xlstransfer.core import clean_text, excel_column_to_index
from server.tools.shared import FAISSManager
# Factor Power: Use centralized progress tracker
from server.utils.progress_tracker import ProgressTracker

# Lazy import for SentenceTransformer (takes ~30s to load PyTorch)
# Import only when model is actually needed, not at module load time
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


# ============================================
# Model Management
# ============================================

_model_instance: Optional["SentenceTransformer"] = None


def load_model(model_path: Optional[Path] = None) -> "SentenceTransformer":
    """
    Load Korean BERT model for embedding generation.

    Args:
        model_path: Path to model directory (uses config default if None)

    Returns:
        Loaded SentenceTransformer model

    Note:
        Model is cached after first load for efficiency.
        SentenceTransformer is imported lazily here to avoid slow startup (~30s PyTorch load).
    """
    # Lazy import - only load heavy ML libraries when model is actually needed
    from sentence_transformers import SentenceTransformer

    global _model_instance

    if _model_instance is not None:
        logger.info("Using cached model instance")
        return _model_instance

    if model_path is None:
        model_path = config.get_model_path()

    logger.info(f"Loading Korean BERT model from {model_path}")

    if config.OFFLINE_MODE and model_path.exists():
        # Load from local path
        _model_instance = SentenceTransformer(str(model_path))
    else:
        # Download from HuggingFace
        _model_instance = SentenceTransformer(config.MODEL_NAME)
        # Save locally for future use
        try:
            _model_instance.save(str(model_path))
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not save model to {model_path}: {e}")

    logger.info("Model loaded successfully")
    return _model_instance


def get_model() -> "SentenceTransformer":
    """
    Get the current model instance (loads if not already loaded).

    Returns:
        SentenceTransformer model instance
    """
    return load_model()


# ============================================
# Embedding Generation
# ============================================

def generate_embeddings(
    texts: List[str],
    batch_size: int = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> np.ndarray:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of Korean texts to embed
        batch_size: Number of texts to process at once (uses config default if None)
        progress_tracker: Optional progress tracker for UI updates

    Returns:
        Numpy array of embeddings (shape: [len(texts), embedding_dim])

    Example:
        >>> texts = ["안녕하세요", "감사합니다"]
        >>> embeddings = generate_embeddings(texts)
        >>> embeddings.shape
        (2, 384)
    """
    if batch_size is None:
        batch_size = config.EMBEDDING_BATCH_SIZE

    model = get_model()
    embeddings = []

    total_batches = (len(texts) + batch_size - 1) // batch_size

    logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = model.encode(batch_texts, convert_to_tensor=False)
        embeddings.extend(batch_embeddings)

        if progress_tracker:
            # Calculate progress percentage for embedding batch
            progress_pct = (min(i + batch_size, len(texts)) / len(texts)) * 100
            progress_tracker.update(
                progress_pct,
                current_step=f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} texts"
            )

        # Log progress every 100 texts or at completion
        if (i + batch_size) % 100 == 0 or (i + batch_size) >= len(texts):
            logger.info(f"Embedding progress: {min(i + batch_size, len(texts))}/{len(texts)}")

    embeddings_array = np.array(embeddings, dtype=np.float32)
    logger.info(f"Generated {len(embeddings_array)} embeddings with shape {embeddings_array.shape}")

    return embeddings_array


# ============================================
# FAISS Index Creation
# ============================================

def create_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Create FAISS HNSW index for fast similarity search.

    Uses WebTranslatorNew pattern for O(log n) search performance.

    Args:
        embeddings: Numpy array of embeddings

    Returns:
        FAISS HNSW index with normalized embeddings

    Example:
        >>> embeddings = np.random.rand(100, 768).astype(np.float32)
        >>> index = create_faiss_index(embeddings)
        >>> index.ntotal
        100
    """
    logger.info(f"Creating FAISS HNSW index for {len(embeddings)} embeddings")

    # Create FAISS HNSW index using FAISSManager (handles normalization)
    embedding_dim = embeddings.shape[1]
    index = FAISSManager.create_index(embedding_dim)
    FAISSManager.add_vectors(index, embeddings, normalize=True)

    logger.info(f"FAISS HNSW index created with {index.ntotal} vectors (dim={embedding_dim})")

    return index


# ============================================
# Dictionary Management
# ============================================

def safe_most_frequent(series: pd.Series) -> Any:
    """
    Get the most frequent value from a pandas Series.

    Args:
        series: Pandas Series

    Returns:
        Most frequent value, or pd.NA if series is empty

    Example:
        >>> s = pd.Series(["a", "b", "a", "c", "a"])
        >>> safe_most_frequent(s)
        'a'
    """
    if series.empty or series.isna().all():
        return pd.NA
    return series.value_counts().index[0]


def create_translation_dictionary(
    kr_texts: List[str],
    translations: List[str]
) -> Dict[str, str]:
    """
    Create translation dictionary, keeping most frequent translation for each Korean text.

    Args:
        kr_texts: List of Korean texts
        translations: List of corresponding translations

    Returns:
        Dictionary mapping Korean text to most frequent translation

    Example:
        >>> kr = ["안녕", "안녕", "감사"]
        >>> trans = ["Hello", "Hi", "Thanks"]
        >>> create_translation_dictionary(kr, trans)
        {'안녕': 'Hello', '감사': 'Thanks'}
    """
    logger.info(f"Creating translation dictionary from {len(kr_texts)} translation pairs")

    # Create DataFrame
    df = pd.DataFrame({'KR': kr_texts, 'Translation': translations})

    # Group by Korean text and get most frequent translation
    most_freq_trans = df.groupby('KR')['Translation'].agg(safe_most_frequent).reset_index()

    # Remove rows with NA
    most_freq_trans = most_freq_trans.dropna()

    # Convert to dictionary
    translation_dict = dict(zip(most_freq_trans['KR'], most_freq_trans['Translation']))

    logger.info(f"Created dictionary with {len(translation_dict)} unique translations")

    return translation_dict


# ============================================
# Dictionary Save/Load
# ============================================

def save_dictionary(
    embeddings: np.ndarray,
    translation_dict: Dict[str, str],
    mode: str,
    output_dir: Optional[Path] = None
) -> Tuple[Path, Path]:
    """
    Save embeddings and translation dictionary to files.

    Args:
        embeddings: Numpy array of embeddings
        translation_dict: Translation dictionary
        mode: "split" or "whole"
        output_dir: Directory to save files (uses current dir if None)

    Returns:
        Tuple of (embeddings_path, dictionary_path)

    Example:
        >>> embeddings = np.random.rand(10, 384).astype(np.float32)
        >>> trans_dict = {"안녕": "Hello"}
        >>> emb_path, dict_path = save_dictionary(embeddings, trans_dict, "split")
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    # Get file names from config
    dict_files = config.get_dictionary_files()

    if mode == "split":
        emb_file = output_dir / dict_files['split_embeddings']
        dict_file = output_dir / dict_files['split_dictionary']
    elif mode == "whole":
        emb_file = output_dir / dict_files['whole_embeddings']
        dict_file = output_dir / dict_files['whole_dictionary']
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'split' or 'whole'")

    # Save embeddings
    np.save(str(emb_file), embeddings)
    logger.info(f"Saved embeddings to {emb_file}")

    # Save dictionary
    with open(dict_file, 'wb') as f:
        pickle.dump(translation_dict, f)
    logger.info(f"Saved dictionary to {dict_file}")

    return emb_file, dict_file


def load_dictionary(
    mode: str,
    input_dir: Optional[Path] = None
) -> Tuple[np.ndarray, Dict[str, str], faiss.IndexFlatIP, pd.Series]:
    """
    Load embeddings and translation dictionary from files.

    Args:
        mode: "split" or "whole"
        input_dir: Directory containing files (uses current dir if None)

    Returns:
        Tuple of (embeddings, translation_dict, faiss_index, kr_texts)

    Raises:
        FileNotFoundError: If dictionary files don't exist

    Example:
        >>> emb, trans_dict, index, texts = load_dictionary("split")
        >>> len(trans_dict)
        1000
    """
    if input_dir is None:
        input_dir = Path.cwd()
    else:
        input_dir = Path(input_dir)

    # Get file names from config
    dict_files = config.get_dictionary_files()

    if mode == "split":
        emb_file = input_dir / dict_files['split_embeddings']
        dict_file = input_dir / dict_files['split_dictionary']
    elif mode == "whole":
        emb_file = input_dir / dict_files['whole_embeddings']
        dict_file = input_dir / dict_files['whole_dictionary']
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'split' or 'whole'")

    # Check if files exist
    if not emb_file.exists():
        raise FileNotFoundError(f"Embeddings file not found: {emb_file}")
    if not dict_file.exists():
        raise FileNotFoundError(f"Dictionary file not found: {dict_file}")

    logger.info(f"Loading {mode} mode dictionary from {input_dir}")

    # Load dictionary
    with open(dict_file, 'rb') as f:
        translation_dict = pickle.load(f)

    # Load embeddings
    embeddings = np.load(str(emb_file))

    # Create FAISS index
    faiss_index = create_faiss_index(embeddings.copy())

    # Create series of Korean texts
    kr_texts = pd.Series(list(translation_dict.keys()), dtype=str)

    logger.info(f"Loaded {mode} mode: {len(translation_dict)} translations, {len(embeddings)} embeddings")

    return embeddings, translation_dict, faiss_index, kr_texts


def check_dictionary_exists(mode: str, input_dir: Optional[Path] = None) -> bool:
    """
    Check if dictionary files exist for a given mode.

    Args:
        mode: "split" or "whole"
        input_dir: Directory to check (uses current dir if None)

    Returns:
        True if both embedding and dictionary files exist

    Example:
        >>> check_dictionary_exists("split")
        True
    """
    if input_dir is None:
        input_dir = Path.cwd()
    else:
        input_dir = Path(input_dir)

    dict_files = config.get_dictionary_files()

    if mode == "split":
        emb_file = input_dir / dict_files['split_embeddings']
        dict_file = input_dir / dict_files['split_dictionary']
    elif mode == "whole":
        emb_file = input_dir / dict_files['whole_embeddings']
        dict_file = input_dir / dict_files['whole_dictionary']
    else:
        return False

    return emb_file.exists() and dict_file.exists()


# ============================================
# Excel Processing for Dictionary Creation
# ============================================

def process_excel_for_dictionary(
    excel_files: List[Tuple[str, str, str, str]],
    progress_tracker: Optional[ProgressTracker] = None
) -> Tuple[Dict[str, str], Dict[str, str], np.ndarray, np.ndarray]:
    """
    Process Excel files to create split and whole translation dictionaries.

    Args:
        excel_files: List of tuples (file_path, sheet_name, kr_column, trans_column)
        progress_tracker: Optional progress tracker

    Returns:
        Tuple of (split_dict, whole_dict, split_embeddings, whole_embeddings)

    Note:
        - Split mode: Splits on newlines if KR and translation have same line count
        - Whole mode: Keeps as single block if line counts differ
    """
    logger.info(f"Processing {len(excel_files)} Excel files for dictionary creation")

    all_kr_texts_split = []
    all_trans_texts_split = []
    all_kr_texts_whole = []
    all_trans_texts_whole = []

    total_rows = 0

    # Process each Excel file
    for file_path, sheet_name, kr_column, trans_column in excel_files:
        logger.info(f"Processing {Path(file_path).name} - Sheet: {sheet_name}")

        # Read Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        # Get column indices
        kr_idx = excel_column_to_index(kr_column)
        trans_idx = excel_column_to_index(trans_column)

        # Extract columns and drop NaN rows
        df = df.iloc[:, [kr_idx, trans_idx]].dropna()

        # Clean texts
        kr_texts = df.iloc[:, 0].apply(clean_text).tolist()
        trans_texts = df.iloc[:, 1].apply(clean_text).tolist()

        total_rows += len(kr_texts)

        # Separate into split and whole modes
        for kr, trans in zip(kr_texts, trans_texts):
            kr_lines = kr.split('\n')
            trans_lines = trans.split('\n')

            if len(kr_lines) == len(trans_lines):
                # Split mode: line counts match
                all_kr_texts_split.extend(kr_lines)
                all_trans_texts_split.extend(trans_lines)
            else:
                # Whole mode: line counts don't match
                all_kr_texts_whole.append(kr)
                all_trans_texts_whole.append(trans)

        if progress_tracker:
            progress_tracker.update(1.0, current_step=f"Processed {Path(file_path).name}")

    logger.info(f"Total rows processed: {total_rows}")
    logger.info(f"Split texts: {len(all_kr_texts_split)}, Whole texts: {len(all_kr_texts_whole)}")

    # Create dictionaries
    split_dict = create_translation_dictionary(all_kr_texts_split, all_trans_texts_split)
    whole_dict = create_translation_dictionary(all_kr_texts_whole, all_trans_texts_whole)

    # Generate embeddings
    logger.info("Generating split embeddings...")
    split_embeddings = generate_embeddings(
        list(split_dict.keys()),
        progress_tracker=progress_tracker
    )

    whole_embeddings = np.array([])
    if whole_dict:
        logger.info("Generating whole embeddings...")
        whole_embeddings = generate_embeddings(
            list(whole_dict.keys()),
            progress_tracker=progress_tracker
        )

    return split_dict, whole_dict, split_embeddings, whole_embeddings


# =============================================================================
# EmbeddingsManager - Load TM data from PostgreSQL for LDM Pipeline
# =============================================================================

class EmbeddingsManager:
    """
    Manages TM-based embeddings for XLS Transfer pretranslation.

    Loads TM entries from PostgreSQL and builds FAISS indexes for the
    XLS Transfer translation pipeline.

    Usage:
        mgr = EmbeddingsManager()
        if mgr.load_tm(tm_id):
            translation = translate_text_multi_mode(
                text,
                split_index=mgr.split_index,
                split_sentences=mgr.split_sentences,
                split_dict=mgr.split_dict,
                whole_index=mgr.whole_index,
                whole_sentences=mgr.whole_sentences,
                whole_dict=mgr.whole_dict,
                threshold=0.92,
                model=mgr.model
            )
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize EmbeddingsManager.

        Args:
            data_dir: Directory for caching indexes (default: server/data/ldm_tm)
        """
        self.model = None

        # Set data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "ldm_tm"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Current loaded state
        self.current_tm_id = None
        self.split_index = None
        self.split_sentences = None
        self.split_dict = None
        self.whole_index = None
        self.whole_sentences = None
        self.whole_dict = None

        logger.info(f"XLS Transfer EmbeddingsManager initialized", {
            "data_dir": str(self.data_dir)
        })

    def _ensure_model_loaded(self):
        """Load the model if not already loaded."""
        if self.model is None:
            self.model = get_model()

    def load_tm(self, tm_id: int, db_session=None) -> bool:
        """
        Load TM data from PostgreSQL and build indexes.

        Uses existing PKL indexes if available (built by TMIndexer),
        otherwise builds fresh indexes from TM entries.

        Args:
            tm_id: Translation Memory ID
            db_session: Optional SQLAlchemy session (creates one if not provided)

        Returns:
            True if loaded successfully
        """
        if self.current_tm_id == tm_id and self.split_index is not None:
            logger.info(f"TM {tm_id} already loaded")
            return True

        logger.info(f"Loading TM {tm_id} for XLS Transfer...")

        tm_path = self.data_dir / str(tm_id)

        # Try to load from existing PKL files (built by TMIndexer)
        whole_mapping_path = tm_path / "embeddings" / "whole_mapping.pkl"
        whole_emb_path = tm_path / "embeddings" / "whole.npy"

        if whole_mapping_path.exists() and whole_emb_path.exists():
            logger.info(f"Loading from existing PKL indexes...")
            return self._load_from_pkl(tm_id, tm_path)

        # Fall back to building from PostgreSQL
        logger.info(f"Building indexes from PostgreSQL...")
        return self._build_from_db(tm_id, db_session)

    def _load_from_pkl(self, tm_id: int, tm_path: Path) -> bool:
        """
        Load indexes from existing PKL files.

        Standard TM's TMIndexer creates these files - we reuse them.
        """
        try:
            self._ensure_model_loaded()

            # Load whole embeddings and mapping
            whole_emb_path = tm_path / "embeddings" / "whole.npy"
            whole_mapping_path = tm_path / "embeddings" / "whole_mapping.pkl"

            embeddings = np.load(whole_emb_path)
            with open(whole_mapping_path, 'rb') as f:
                mapping = pickle.load(f)

            # Build dictionaries and sentence lists
            self.whole_sentences = []
            self.whole_dict = {}
            self.split_sentences = []
            self.split_dict = {}

            for entry in mapping:
                source = entry.get("source_text", "")
                target = entry.get("target_text", "")

                if not source:
                    continue

                # For whole mode
                self.whole_sentences.append(source)
                self.whole_dict[source] = target

                # For split mode (line by line)
                source_lines = source.split('\n')
                target_lines = (target or "").split('\n')

                for i, src_line in enumerate(source_lines):
                    src_line = src_line.strip()
                    if src_line and src_line not in self.split_dict:
                        tgt_line = target_lines[i].strip() if i < len(target_lines) else ""
                        self.split_sentences.append(src_line)
                        self.split_dict[src_line] = tgt_line

            # Build FAISS indexes from embeddings using FAISSManager
            dim = embeddings.shape[1]

            self.whole_index = FAISSManager.create_index(dim)
            FAISSManager.add_vectors(self.whole_index, embeddings, normalize=True)

            # Build split index from split sentences
            if self.split_sentences:
                logger.info(f"Encoding {len(self.split_sentences)} split sentences...")
                split_embeddings = self.model.encode(
                    self.split_sentences,
                    batch_size=64,
                    show_progress_bar=False
                )
                split_embeddings = np.array(split_embeddings, dtype=np.float32)

                self.split_index = FAISSManager.create_index(dim)
                FAISSManager.add_vectors(self.split_index, split_embeddings, normalize=True)

            # Convert sentences to pd.Series for translate_text_multi_mode
            self.split_sentences = pd.Series(self.split_sentences, dtype=str)
            self.whole_sentences = pd.Series(self.whole_sentences, dtype=str)

            self.current_tm_id = tm_id

            logger.success(f"Loaded TM {tm_id}: {len(self.whole_dict)} whole, {len(self.split_dict)} split")
            return True

        except Exception as e:
            logger.error(f"Failed to load from PKL: {e}")
            return False

    def _build_from_db(self, tm_id: int, db_session=None) -> bool:
        """
        Build indexes from TM entries using TMLoader.

        LIMIT-002: Uses TMLoader to support both PostgreSQL and SQLite offline mode.
        """
        try:
            # Use TMLoader for unified PostgreSQL/SQLite loading
            from server.tools.shared.tm_loader import TMLoader

            entries = TMLoader.load_entries(tm_id)

            if not entries:
                logger.warning(f"No entries found for TM {tm_id}")
                return False

            logger.info(f"Loaded {len(entries)} entries from TM {tm_id}")

            self._ensure_model_loaded()

            # Build dictionaries
            self.whole_sentences = []
            self.whole_dict = {}
            self.split_sentences = []
            self.split_dict = {}

            for entry in entries:
                # TMLoader returns dicts, not ORM objects
                source = entry.get("source_text", "")
                target = entry.get("target_text", "") or ""

                if not source:
                    continue

                # Whole mode
                if source not in self.whole_dict:
                    self.whole_sentences.append(source)
                    self.whole_dict[source] = target

                # Split mode
                source_lines = source.split('\n')
                target_lines = target.split('\n')

                for i, src_line in enumerate(source_lines):
                    src_line = src_line.strip()
                    if src_line and src_line not in self.split_dict:
                        tgt_line = target_lines[i].strip() if i < len(target_lines) else ""
                        self.split_sentences.append(src_line)
                        self.split_dict[src_line] = tgt_line

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(self.whole_sentences)} whole, {len(self.split_sentences)} split...")

            if self.whole_sentences:
                whole_emb = self.model.encode(
                    self.whole_sentences,
                    batch_size=64,
                    show_progress_bar=False
                )
                whole_emb = np.array(whole_emb, dtype=np.float32)

                dim = whole_emb.shape[1]
                self.whole_index = FAISSManager.create_index(dim)
                FAISSManager.add_vectors(self.whole_index, whole_emb, normalize=True)

            if self.split_sentences:
                split_emb = self.model.encode(
                    self.split_sentences,
                    batch_size=64,
                    show_progress_bar=False
                )
                split_emb = np.array(split_emb, dtype=np.float32)

                dim = split_emb.shape[1]
                self.split_index = FAISSManager.create_index(dim)
                FAISSManager.add_vectors(self.split_index, split_emb, normalize=True)

            # Convert to pd.Series
            self.split_sentences = pd.Series(self.split_sentences, dtype=str)
            self.whole_sentences = pd.Series(self.whole_sentences, dtype=str)

            self.current_tm_id = tm_id

            logger.success(f"Built indexes for TM {tm_id}: {len(self.whole_dict)} whole, {len(self.split_dict)} split")
            return True

        except Exception as e:
            logger.exception(f"Failed to build from DB: {e}")
            return False

    def load_dictionary(self, tm_id: int, db_session=None) -> bool:
        """
        Alias for load_tm() - maintains compatibility with pretranslate.py interface.

        Args:
            tm_id: Translation Memory ID
            db_session: Optional SQLAlchemy session

        Returns:
            True if loaded successfully
        """
        return self.load_tm(tm_id, db_session)

    def get_status(self) -> Dict[str, Any]:
        """Get current manager status."""
        return {
            "model_loaded": self.model is not None,
            "current_tm_id": self.current_tm_id,
            "whole_count": len(self.whole_dict) if self.whole_dict else 0,
            "split_count": len(self.split_dict) if self.split_dict else 0,
            "whole_index_ready": self.whole_index is not None,
            "split_index_ready": self.split_index is not None
        }


# Example usage
if __name__ == "__main__":
    # Test model loading
    print("Loading model...")
    model = load_model()
    print(f"Model loaded: {model}")

    # Test embedding generation
    print("\nGenerating embeddings...")
    texts = ["안녕하세요", "감사합니다", "미안합니다"]
    embeddings = generate_embeddings(texts)
    print(f"Generated {len(embeddings)} embeddings with shape {embeddings.shape}")

    # Test FAISS index
    print("\nCreating FAISS index...")
    index = create_faiss_index(embeddings)
    print(f"FAISS index created with {index.ntotal} vectors")
