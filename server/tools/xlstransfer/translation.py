"""
XLSTransfer Translation Matching

Semantic similarity-based translation matching using FAISS.
CLEAN, modular functions for finding best translation matches.
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import numpy as np
import pandas as pd
import faiss
from loguru import logger

# Lazy import for SentenceTransformer (takes ~30s to load PyTorch)
# Import only when model is actually needed, not at module load time
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from server.tools.xlstransfer import config
from server.tools.xlstransfer.core import clean_text, simple_number_replace
from server.tools.xlstransfer.embeddings import get_model


# ============================================
# Single Text Matching
# ============================================

def find_best_match(
    text: str,
    faiss_index: faiss.IndexFlatIP,
    kr_sentences: pd.Series,
    translation_dict: Dict[str, str],
    threshold: float = None,
    model: Optional["SentenceTransformer"] = None
) -> Tuple[str, str, float]:
    """
    Find the best matching translation for a given text.

    Args:
        text: Text to translate (Korean)
        faiss_index: FAISS index with reference embeddings
        kr_sentences: Series of reference Korean sentences
        translation_dict: Dictionary mapping Korean to translation
        threshold: Similarity threshold (0.0-1.0), uses config default if None
        model: SentenceTransformer model (loads if None)

    Returns:
        Tuple of (matched_korean, translation, similarity_score)
        Returns ("", "", 0.0) if no match above threshold

    Example:
        >>> text = "안녕하세요"
        >>> korean, translation, score = find_best_match(text, index, sentences, trans_dict)
        >>> print(f"{korean} -> {translation} (score: {score:.3f})")
    """
    if threshold is None:
        threshold = config.DEFAULT_FAISS_THRESHOLD

    if model is None:
        model = get_model()

    # Clean text
    cleaned_text = clean_text(text)

    if not isinstance(cleaned_text, str) or not cleaned_text.strip():
        return "", "", 0.0

    try:
        # Generate embedding
        text_embedding = model.encode([cleaned_text])

        # Normalize for cosine similarity
        faiss.normalize_L2(text_embedding)

        # Search for nearest neighbor
        distances, indices = faiss_index.search(text_embedding, 1)

        best_match_index = indices[0][0]
        similarity_score = float(distances[0][0])

        # Check if match is above threshold
        if similarity_score < threshold:
            logger.debug(f"No match found for '{cleaned_text[:30]}...' (score: {similarity_score:.3f} < {threshold})")
            return "", "", similarity_score

        # Get matched Korean text
        if best_match_index >= len(kr_sentences):
            logger.warning(f"Invalid index {best_match_index} (max: {len(kr_sentences)})")
            return "", "", 0.0

        matched_korean = kr_sentences.iloc[best_match_index]
        translation = translation_dict.get(matched_korean, "")

        logger.debug(f"Match found: '{cleaned_text[:30]}...' -> '{translation[:30]}...' (score: {similarity_score:.3f})")

        return matched_korean, translation, similarity_score

    except Exception as e:
        logger.error(f"Error finding match for '{cleaned_text[:30]}...': {e}")
        return "", "", 0.0


# ============================================
# Batch Processing
# ============================================

def process_batch(
    texts: List[str],
    faiss_index: faiss.IndexFlatIP,
    kr_sentences: pd.Series,
    translation_dict: Dict[str, str],
    threshold: float = None,
    model: Optional["SentenceTransformer"] = None,
    preserve_codes: bool = True
) -> List[Tuple[str, str, float]]:
    """
    Process a batch of texts and find matches.

    Args:
        texts: List of texts to translate
        faiss_index: FAISS index
        kr_sentences: Series of reference sentences
        translation_dict: Translation dictionary
        threshold: Similarity threshold
        model: SentenceTransformer model
        preserve_codes: Whether to preserve game codes

    Returns:
        List of tuples (matched_korean, translation, score) for each text

    Example:
        >>> texts = ["안녕하세요", "감사합니다"]
        >>> results = process_batch(texts, index, sentences, trans_dict)
        >>> len(results)
        2
    """
    results = []

    for text in texts:
        matched_korean, translation, score = find_best_match(
            text, faiss_index, kr_sentences, translation_dict, threshold, model
        )

        # Preserve game codes if enabled
        if preserve_codes and translation and isinstance(text, str):
            translation = simple_number_replace(text, translation)

        results.append((matched_korean, translation, score))

    return results


# ============================================
# Multi-Mode Matching
# ============================================

def translate_text_multi_mode(
    text: str,
    split_index: Optional[faiss.IndexFlatIP],
    split_sentences: Optional[pd.Series],
    split_dict: Optional[Dict[str, str]],
    whole_index: Optional[faiss.IndexFlatIP],
    whole_sentences: Optional[pd.Series],
    whole_dict: Optional[Dict[str, str]],
    threshold: float = None,
    model: Optional["SentenceTransformer"] = None
) -> str:
    """
    Translate text using multi-mode matching (whole first, then split fallback).

    Args:
        text: Text to translate
        split_index: FAISS index for split mode (line-by-line)
        split_sentences: Reference sentences for split mode
        split_dict: Translation dictionary for split mode
        whole_index: FAISS index for whole mode (full text blocks)
        whole_sentences: Reference sentences for whole mode
        whole_dict: Translation dictionary for whole mode
        threshold: Similarity threshold
        model: SentenceTransformer model

    Returns:
        Translated text (empty string if no match)

    Example:
        >>> text = "안녕하세요\\n감사합니다"
        >>> translation = translate_text_multi_mode(text, split_idx, split_sent, ...)
        >>> print(translation)
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    cleaned_text = clean_text(text)

    # Try whole mode first
    if whole_index is not None and whole_sentences is not None and whole_dict is not None:
        _, translation, score = find_best_match(
            cleaned_text, whole_index, whole_sentences, whole_dict, threshold, model
        )

        if translation:
            logger.debug(f"Whole mode match found (score: {score:.3f})")
            return translation

    # Fall back to split mode (line-by-line)
    if split_index is not None and split_sentences is not None and split_dict is not None:
        lines = cleaned_text.split('\n')
        translated_lines = []

        for line in lines:
            if not line.strip():
                continue

            _, translation, score = find_best_match(
                line, split_index, split_sentences, split_dict, threshold, model
            )

            if translation.strip():
                translated_lines.append(translation)
                logger.debug(f"Split mode match: '{line[:30]}...' -> '{translation[:30]}...' (score: {score:.3f})")

        if translated_lines:
            return '\n'.join(translated_lines)

    logger.debug(f"No match found for '{cleaned_text[:30]}...'")
    return ""


# ============================================
# Statistics and Analysis
# ============================================

def get_match_statistics(
    results: List[Tuple[str, str, float]]
) -> Dict[str, any]:
    """
    Calculate statistics from translation results.

    Args:
        results: List of (matched_korean, translation, score) tuples

    Returns:
        Dictionary with statistics

    Example:
        >>> results = [("안녕", "Hello", 0.95), ("감사", "Thanks", 0.98)]
        >>> stats = get_match_statistics(results)
        >>> stats['match_rate']
        1.0
    """
    total = len(results)
    matched = sum(1 for _, trans, _ in results if trans)
    scores = [score for _, trans, score in results if trans]

    stats = {
        'total': total,
        'matched': matched,
        'unmatched': total - matched,
        'match_rate': matched / total if total > 0 else 0.0,
        'avg_score': np.mean(scores) if scores else 0.0,
        'min_score': np.min(scores) if scores else 0.0,
        'max_score': np.max(scores) if scores else 0.0,
        'median_score': np.median(scores) if scores else 0.0
    }

    return stats


def filter_by_threshold(
    results: List[Tuple[str, str, float]],
    threshold: float
) -> List[Tuple[str, str, float]]:
    """
    Filter results to only include matches above threshold.

    Args:
        results: List of (matched_korean, translation, score) tuples
        threshold: Minimum score threshold

    Returns:
        Filtered results

    Example:
        >>> results = [("안녕", "Hello", 0.95), ("감사", "Thanks", 0.85)]
        >>> filtered = filter_by_threshold(results, 0.90)
        >>> len(filtered)
        1
    """
    return [(k, t, s) for k, t, s in results if s >= threshold]


def get_low_confidence_matches(
    results: List[Tuple[str, str, float]],
    threshold: float = 0.90
) -> List[Tuple[str, str, float]]:
    """
    Get matches with confidence below threshold (for review).

    Args:
        results: List of (matched_korean, translation, score) tuples
        threshold: Confidence threshold

    Returns:
        Low confidence matches

    Example:
        >>> results = [("안녕", "Hello", 0.95), ("감사", "Thanks", 0.85)]
        >>> low_conf = get_low_confidence_matches(results, 0.90)
        >>> len(low_conf)
        1
    """
    return [(k, t, s) for k, t, s in results if t and s < threshold]


# ============================================
# Progress Tracking
# ============================================

class TranslationProgress:
    """Track translation progress and statistics."""

    def __init__(self, total_items: int):
        """Initialize progress tracker."""
        self.total = total_items
        self.processed = 0
        self.matched = 0
        self.scores = []

    def update(self, matched: bool, score: float = 0.0):
        """Update progress with result."""
        self.processed += 1
        if matched:
            self.matched += 1
            self.scores.append(score)

    def get_stats(self) -> Dict[str, any]:
        """Get current statistics."""
        return {
            'total': self.total,
            'processed': self.processed,
            'matched': self.matched,
            'match_rate': self.matched / self.processed if self.processed > 0 else 0.0,
            'avg_score': np.mean(self.scores) if self.scores else 0.0,
            'progress': self.processed / self.total if self.total > 0 else 0.0
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"TranslationProgress("
            f"processed={stats['processed']}/{stats['total']}, "
            f"matched={stats['matched']} ({stats['match_rate']:.1%}), "
            f"avg_score={stats['avg_score']:.3f})"
        )


# Example usage
if __name__ == "__main__":
    import doctest
    # Run doctests
    print("Running doctests...")
    doctest.testmod()

    print("\nTranslation module loaded successfully!")
    print("Functions available:")
    print("- find_best_match(): Find best translation for single text")
    print("- process_batch(): Process multiple texts")
    print("- translate_text_multi_mode(): Multi-mode translation")
    print("- get_match_statistics(): Calculate statistics")
    print("- TranslationProgress: Track translation progress")
