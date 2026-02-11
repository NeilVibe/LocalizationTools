"""
Fuzzy Korean Matching using KR-SBERT + FAISS.

Semantic similarity matching for Korean text using:
- Model: snunlp/KR-SBERT-V40K-klueNLI-augSTS (768-dim, 447MB)
- Index: FAISS IndexFlatIP with inner product (cosine similarity after normalization)

Model folder 'KRTransformer/' must be placed alongside the app.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

# Module-level cache for model and index
_cached_model = None
_cached_index = None
_cached_index_path = None  # Track which folder the index was built for
_cached_texts = None  # StrOrigin texts corresponding to index vectors
_cached_entries = None  # Full entry dicts corresponding to index vectors
_cache_lock = threading.Lock()


def check_model_available() -> Tuple[bool, str]:
    """
    Check if the KRTransformer model folder exists and contains model files.

    Returns:
        Tuple of (available: bool, message: str)
    """
    model_path = config.KRTRANSFORMER_PATH

    if not model_path.exists():
        return False, (
            f"KRTransformer model not found.\n\n"
            f"Please place the model folder at:\n"
            f"{model_path}\n\n"
            f"The model (snunlp/KR-SBERT-V40K-klueNLI-augSTS) can be copied from:\n"
            f"models/kr-sbert.deprecated/"
        )

    # Check for essential model files
    has_config = (model_path / "config.json").exists()
    has_model = (
        (model_path / "model.safetensors").exists()
        or (model_path / "pytorch_model.bin").exists()
    )

    if not has_config or not has_model:
        return False, (
            f"KRTransformer folder exists but appears incomplete.\n\n"
            f"Path: {model_path}\n"
            f"config.json: {'Found' if has_config else 'MISSING'}\n"
            f"model weights: {'Found' if has_model else 'MISSING'}\n\n"
            f"Please ensure the full model is present."
        )

    return True, f"Model ready at: {model_path}"


def load_model(progress_callback: Optional[Callable[[str], None]] = None):
    """
    Load the KR-SBERT model. Cached after first load.

    Args:
        progress_callback: Optional callback for status updates

    Returns:
        SentenceTransformer model instance

    Raises:
        ImportError: If sentence-transformers is not installed
        FileNotFoundError: If model folder is missing
        RuntimeError: If model loading fails
    """
    global _cached_model

    with _cache_lock:
        if _cached_model is not None:
            return _cached_model

    available, message = check_model_available()
    if not available:
        raise FileNotFoundError(message)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is not installed.\n\n"
            "Install with: pip install sentence-transformers faiss-cpu"
        )

    model_path = config.KRTRANSFORMER_PATH

    if progress_callback:
        progress_callback("Loading KR-SBERT model...")

    logger.info(f"Loading KR-SBERT model from: {model_path}")
    model = SentenceTransformer(str(model_path))
    logger.info("KR-SBERT model loaded successfully")

    with _cache_lock:
        _cached_model = model

    return model


def build_faiss_index(
    texts: List[str],
    entries: List[dict],
    model,
    progress_callback: Optional[Callable[[str], None]] = None,
    batch_size: int = 100,
):
    """
    Build a FAISS IndexFlatIP index from a list of texts.

    Uses the same proven pattern as TFM FULL, XLSTransfer, and KR Similar monoliths:
    - Batch encoding (batch_size=100) to avoid memory spikes
    - IndexFlatIP for instant index building and 100% accurate search
    - L2 normalization for cosine similarity via inner product

    Args:
        texts: List of StrOrigin strings to encode
        entries: List of entry dicts corresponding to each text
        model: Loaded SentenceTransformer model
        progress_callback: Optional callback for status updates
        batch_size: Number of texts to encode per batch (default: 100)

    Returns:
        FAISS index with normalized vectors added
    """
    global _cached_index, _cached_texts, _cached_entries

    try:
        import numpy as np
        import faiss
    except ImportError:
        raise ImportError(
            "faiss-cpu or numpy is not installed.\n\n"
            "Install with: pip install -r requirements-ml.txt"
        )

    if not texts:
        raise ValueError("No texts provided to build index")

    total = len(texts)
    logger.info(f"Encoding {total} texts in batches of {batch_size}...")

    # Batch encoding - same pattern as TFM FULL monolith (batch_size=100)
    all_embeddings = []
    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        all_embeddings.extend(batch_embeddings)

        done = min(i + batch_size, total)
        if progress_callback:
            progress_callback(f"Encoding {done}/{total} texts...")
        if done % 500 == 0 or done == total:
            logger.info(f"Embedding progress: {done}/{total}")

    embeddings = np.array(all_embeddings, dtype=np.float32)
    embeddings = np.ascontiguousarray(embeddings)

    if progress_callback:
        progress_callback(f"Building FAISS index ({total} vectors, {embeddings.shape[1]}d)...")

    # Normalize for cosine similarity via inner product
    faiss.normalize_L2(embeddings)

    # IndexFlatIP - same as TFM FULL, XLSTransfer, KR Similar monoliths
    # Instant build, 100% accurate, perfect for <200K vectors
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    logger.info(f"FAISS index built: {index.ntotal} vectors, {dim}d")

    with _cache_lock:
        _cached_index = index
        _cached_texts = texts
        _cached_entries = entries

    return index


def search_fuzzy(
    query_text: str,
    model,
    index,
    texts: List[str],
    entries: List[dict],
    threshold: float = 0.85,
    k: int = 1,
) -> List[Tuple[dict, float]]:
    """
    Search the FAISS index for the closest match to query_text.

    Args:
        query_text: Korean text to search for
        model: Loaded SentenceTransformer model
        index: Built FAISS index
        texts: StrOrigin texts corresponding to index vectors
        entries: Entry dicts corresponding to index vectors
        threshold: Minimum similarity score (0.0 - 1.0)
        k: Number of results to return

    Returns:
        List of (entry_dict, similarity_score) tuples above threshold
    """
    import numpy as np
    import faiss

    if not query_text or not query_text.strip():
        return []

    # Encode query
    query_embedding = model.encode([query_text.strip()], convert_to_numpy=True, show_progress_bar=False)
    query_embedding = np.ascontiguousarray(query_embedding, dtype=np.float32)
    faiss.normalize_L2(query_embedding)

    # Search
    distances, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(entries):
            continue
        if score >= threshold:
            results.append((entries[idx], float(score)))

    return results


def find_matches_fuzzy(
    corrections: List[Dict],
    target_texts: List[str],
    target_entries: List[dict],
    model,
    index,
    threshold: float = 0.85,
    progress_callback: Optional[Callable[[str], None]] = None,
    log_callback=None,
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Match corrections against target entries using FAISS fuzzy search.

    For each correction, encodes its StrOrigin and searches the FAISS index
    for the best semantic match. Returns enriched corrections with
    fuzzy_target_string_id for use with merge_corrections_fuzzy.

    Args:
        corrections: List of correction dicts with string_id, str_origin, corrected
        target_texts: StrOrigin texts in the FAISS index
        target_entries: Entry dicts corresponding to index vectors
        model: Loaded SentenceTransformer model
        index: Built FAISS index
        threshold: Minimum similarity score (0.0 - 1.0)
        progress_callback: Optional callback for status updates
        log_callback: Optional callback for GUI console messages

    Returns:
        Tuple of (matched, unmatched, stats) where matched corrections are
        enriched with fuzzy_target_string_id and fuzzy_score
    """
    matched = []
    unmatched = []
    scores = []
    total = len(corrections)

    logger.info(f"FAISS fuzzy search: {total} corrections, threshold={threshold:.2f}, "
                f"index has {index.ntotal} vectors")

    if log_callback:
        log_callback(f"    Fuzzy searching {total} items...", 'info')

    t_start = time.perf_counter()
    last_log_time = t_start

    for i, c in enumerate(corrections):
        if progress_callback and i % 50 == 0:
            progress_callback(f"Fuzzy matching... {i+1}/{total}")

        query = c.get("str_origin", "").strip()
        if not query:
            unmatched.append(c)
            continue

        results = search_fuzzy(query, model, index, target_texts, target_entries, threshold, k=1)
        if results:
            best_entry, score = results[0]
            enriched = {
                **c,
                "fuzzy_target_string_id": best_entry["string_id"],
                "fuzzy_target_str_origin": best_entry["str_origin"],
                "fuzzy_score": score,
            }
            matched.append(enriched)
            scores.append(score)
        else:
            unmatched.append(c)

        done = i + 1
        now = time.perf_counter()
        if now - last_log_time >= 10 or done == total:
            elapsed = now - t_start
            avg = sum(scores) / len(scores) if scores else 0.0
            rate = done / elapsed if elapsed > 0 else 0
            logger.info(
                f"FAISS search: {done}/{total} processed, "
                f"{len(matched)} matches (avg: {avg:.3f}), "
                f"{rate:.0f} items/sec"
            )
            last_log_time = now

    elapsed_total = time.perf_counter() - t_start

    stats = {
        "total": total,
        "matched": len(matched),
        "unmatched": len(unmatched),
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "threshold": threshold,
        "elapsed_sec": round(elapsed_total, 2),
    }

    logger.info(
        f"FAISS fuzzy COMPLETE: {len(matched)}/{total} matched in {elapsed_total:.1f}s "
        f"(avg={stats['avg_score']:.3f}, min={stats['min_score']:.3f}, "
        f"threshold={threshold:.2f})"
    )

    return matched, unmatched, stats


def get_cached_index_info() -> Optional[Dict]:
    """
    Get info about the currently cached FAISS index.

    Returns:
        Dict with ntotal, dim, path or None if no index cached
    """
    if _cached_index is None:
        return None

    return {
        "ntotal": _cached_index.ntotal,
        "path": _cached_index_path,
        "texts_count": len(_cached_texts) if _cached_texts else 0,
    }


def clear_cache():
    """Clear all cached model and index data."""
    global _cached_model, _cached_index, _cached_index_path, _cached_texts, _cached_entries
    with _cache_lock:
        _cached_model = None
        _cached_index = None
        _cached_index_path = None
        _cached_texts = None
        _cached_entries = None
    logger.info("Fuzzy matching cache cleared")


def build_index_from_folder(
    folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    preloaded_entries: Optional[List[dict]] = None,
    stringid_filter: Optional[set] = None,
    only_untranslated: bool = False,
) -> Tuple[List[str], List[dict]]:
    """
    Scan a folder for XML entries and prepare texts + entries lists for indexing.

    This extracts StrOrigin values from all XML files in the folder,
    suitable for building a FAISS index.

    Args:
        folder: Path to folder containing XML files
        progress_callback: Optional callback for status updates
        preloaded_entries: Optional pre-scanned entries to use instead of rescanning.
                          If provided, skips the folder scan and uses these directly.
        stringid_filter: Optional set of StringIDs to include. If provided, only entries
                        with StringIDs in this set are included. DRAMATICALLY reduces size.
        only_untranslated: If True, only include entries where Str contains Korean.

    Returns:
        Tuple of (texts, entries) where texts are StrOrigin values
        and entries are full entry dicts
    """
    from .korean_detection import is_korean_text

    if preloaded_entries is not None:
        all_entries_list = preloaded_entries
    else:
        from .indexing import scan_folder_for_entries_with_context

        # Only scan ONE language file - StrOrigin is the same across all languages
        # This reduces scan from 2.2M entries (13 files) to ~170K (1 file)
        found_languagedata = [False]  # Use list to allow mutation in closure

        def single_language_filter(f):
            name_lower = f.name.lower()
            # Non-languagedata XML files (export folder structure) - always include
            if not name_lower.startswith('languagedata_'):
                return True
            # For languagedata files, only take ONE (prefer KOR)
            if 'languagedata_kor' in name_lower:
                found_languagedata[0] = True
                return True
            # If we already have a languagedata file, skip the rest
            if found_languagedata[0]:
                return False
            # Take the first languagedata file if no KOR yet
            if name_lower.endswith('.xml'):
                found_languagedata[0] = True
                return True
            return False

        if progress_callback:
            filter_info = f" (StringID filter: {len(stringid_filter)})" if stringid_filter else ""
            progress_callback(f"Scanning {folder.name} (single language file){filter_info}...")

        # CRITICAL: Pass stringid_filter to scan so entries are skipped DURING parsing
        all_entries_list, _, _, _, _ = scan_folder_for_entries_with_context(
            folder, progress_callback, file_filter=single_language_filter,
            stringid_filter=stringid_filter  # FILTER DURING SCAN, NOT AFTER!
        )

    texts = []
    entries = []
    skipped_stringid = 0
    skipped_translated = 0

    for entry in all_entries_list:
        str_origin = entry.get("str_origin", "").strip()
        if not str_origin:
            continue

        # Filter 1: Only include entries with matching StringIDs
        if stringid_filter is not None:
            sid = entry.get("string_id", "")
            if sid not in stringid_filter:
                skipped_stringid += 1
                continue

        # Filter 2: Only include untranslated entries (Str has Korean)
        if only_untranslated:
            str_value = entry.get("str_value", "")
            if str_value and str_value.strip() and not is_korean_text(str_value):
                skipped_translated += 1
                continue

        texts.append(str_origin)
        entries.append(entry)

    if stringid_filter is not None:
        logger.info(f"Filtered by StringID: {len(texts)} kept, {skipped_stringid} skipped")
    if only_untranslated:
        logger.info(f"Filtered translated: {skipped_translated} skipped")
    logger.info(f"Extracted {len(texts)} StrOrigin texts from {folder}")
    return texts, entries
