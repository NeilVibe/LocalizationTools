"""
KR Similar Searcher Module

Handles semantic similarity search using FAISS indexes.
Provides similar string extraction and auto-translation capabilities.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - similarity search disabled")

from server.tools.kr_similar.core import normalize_text, adapt_structure


class SimilaritySearcher:
    """
    Semantic similarity searcher for Korean texts.

    Provides:
    - Find similar strings (for quality checks)
    - Extract similar string groups
    - Auto-translate using semantic matching
    """

    def __init__(self, embeddings_manager=None):
        """
        Initialize SimilaritySearcher.

        Args:
            embeddings_manager: EmbeddingsManager instance for model access
        """
        self.embeddings_manager = embeddings_manager
        self.model = None  # Lazy loaded
        logger.info("SimilaritySearcher initialized")

    def _ensure_model(self):
        """Ensure model is loaded."""
        if self.model is None:
            if self.embeddings_manager is None:
                raise RuntimeError("EmbeddingsManager not set")
            self.embeddings_manager._ensure_model_loaded()
            self.model = self.embeddings_manager.model

    def find_similar(
        self,
        query: str,
        threshold: float = 0.85,
        top_k: int = 10,
        use_whole: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find similar strings to query.

        Args:
            query: Query text (Korean)
            threshold: Minimum similarity threshold (0.0-1.0)
            top_k: Maximum results to return
            use_whole: Use whole embeddings instead of split

        Returns:
            List of matches with korean, translation, and similarity score
        """
        if self.embeddings_manager is None:
            raise RuntimeError("EmbeddingsManager not set")

        if not self.embeddings_manager.split_index:
            raise RuntimeError("No dictionary loaded")

        self._ensure_model()

        # Normalize query
        normalized_query = normalize_text(query)

        # Encode query
        query_embedding = self.model.encode([normalized_query])
        faiss.normalize_L2(query_embedding)

        # Choose index and dictionary
        if use_whole and self.embeddings_manager.whole_index:
            index = self.embeddings_manager.whole_index
            translation_dict = self.embeddings_manager.whole_dict
            kr_texts = list(translation_dict.keys())
        else:
            index = self.embeddings_manager.split_index
            translation_dict = self.embeddings_manager.split_dict
            kr_texts = list(translation_dict.keys())

        # Search
        distances, indices = index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if dist >= threshold and idx < len(kr_texts):
                korean = kr_texts[idx]
                translation = translation_dict.get(korean, "")
                results.append({
                    "korean": korean,
                    "translation": translation,
                    "similarity": float(dist),
                    "match_type": "whole" if use_whole else "split"
                })

        logger.debug(f"Found {len(results)} similar strings", {
            "query_preview": normalized_query[:50],
            "threshold": threshold,
            "results_count": len(results)
        })

        return results

    def extract_similar_strings(
        self,
        data: pd.DataFrame,
        min_char_length: int = 50,
        similarity_threshold: float = 0.85,
        filter_same_category: bool = True,
        progress_callback: callable = None
    ) -> List[Dict[str, Any]]:
        """
        Extract groups of similar strings from a DataFrame.

        Used for quality checks to find strings that should have
        consistent translations.

        Args:
            data: DataFrame with columns from language file
            min_char_length: Minimum character length to consider
            similarity_threshold: Minimum similarity (0.0-1.0)
            filter_same_category: Filter out same-category matches
            progress_callback: Optional progress callback

        Returns:
            List of similar string groups
        """
        self._ensure_model()

        # Normalize texts (column 5 = Korean)
        if 5 in data.columns:
            data['normalized_text'] = data[5].apply(normalize_text)
        elif 'Korean' in data.columns:
            data['normalized_text'] = data['Korean'].apply(normalize_text)
        else:
            raise ValueError("Data must have Korean text in column 5 or 'Korean' column")

        # Filter by length
        data = data[data['normalized_text'].str.len() >= min_char_length].reset_index(drop=True)
        total = len(data)

        logger.info(f"Processing {total} strings for similarity extraction")

        # Generate embeddings
        embeddings = self.model.encode(data['normalized_text'].tolist(), show_progress_bar=False)

        # Normalize and create index
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        # Find similar pairs
        similar_groups = []
        processed = 0

        for idx, row in data.iterrows():
            normalized_text = row['normalized_text']
            embedding = embeddings[idx].reshape(1, -1)

            # Search for similar (skip self)
            distances, indices = index.search(embedding, 11)  # Get 10 + self

            for dist, ind in zip(distances[0], indices[0]):
                if ind == idx:  # Skip self
                    continue

                if similarity_threshold <= dist < 1.0:
                    similar_text = data.iloc[ind]['normalized_text']
                    if similar_text != normalized_text:
                        group = sorted([normalized_text, similar_text])
                        if group not in similar_groups:
                            similar_groups.append(group)
                        break
                elif dist >= 1.0:
                    continue
                else:
                    break

            processed += 1
            if progress_callback and processed % 100 == 0:
                progress_callback(processed, total)

        logger.info(f"Found {len(similar_groups)} similar groups before deduplication")

        # Deduplicate
        unique_groups = []
        for group in similar_groups:
            if group not in unique_groups:
                unique_groups.append(group)

        # Category filtering
        if filter_same_category and 0 in data.columns:
            filtered_groups = []
            for group in unique_groups:
                rows = []
                for text in group:
                    matching = data[data['normalized_text'] == text]
                    if not matching.empty:
                        rows.append(matching.iloc[0])

                if len(rows) == 2:
                    if rows[0][0] != rows[1][0]:  # Different categories
                        filtered_groups.append(group)
            unique_groups = filtered_groups

        logger.success(f"Extracted {len(unique_groups)} similar string groups")

        # Format results
        results = []
        for group in unique_groups:
            group_data = []
            for text in group:
                matching = data[data['normalized_text'] == text]
                if not matching.empty:
                    row = matching.iloc[0]
                    group_data.append({
                        "text": text,
                        "original": str(row.get(5, row.get('Korean', text))),
                        "category": str(row.get(0, 'unknown'))
                    })
            results.append({"group": group_data})

        return results

    def auto_translate(
        self,
        data: pd.DataFrame,
        similarity_threshold: float = 0.85,
        progress_callback: callable = None
    ) -> pd.DataFrame:
        """
        Auto-translate strings using semantic similarity matching.

        Finds similar Korean strings in the loaded dictionary and
        applies their translations.

        Args:
            data: DataFrame with Korean text (column 5 or 'Korean')
            similarity_threshold: Minimum similarity for matching
            progress_callback: Optional progress callback

        Returns:
            DataFrame with added/updated translation column
        """
        if self.embeddings_manager is None or not self.embeddings_manager.split_index:
            raise RuntimeError("No dictionary loaded")

        self._ensure_model()

        total = len(data)
        replaced_count = 0

        # Prepare result DataFrame
        result = data.copy()
        if 'Translation' not in result.columns and 6 in result.columns:
            result.rename(columns={6: 'Translation'}, inplace=True)
        elif 'Translation' not in result.columns:
            result['Translation'] = ''

        split_index = self.embeddings_manager.split_index
        split_dict = self.embeddings_manager.split_dict
        split_kr_texts = list(split_dict.keys())

        whole_index = self.embeddings_manager.whole_index
        whole_dict = self.embeddings_manager.whole_dict
        whole_kr_texts = list(whole_dict.keys()) if whole_dict else []

        for idx, row in result.iterrows():
            # Get Korean text
            if 5 in row.index:
                original_text = str(row[5])
            elif 'Korean' in row.index:
                original_text = str(row['Korean'])
            else:
                continue

            normalized_text = normalize_text(original_text)

            # Handle triangle markers (line-by-line)
            if '▶' in original_text:
                translated_lines = []
                lines = normalized_text.split('\\n')
                line_changed = False

                for line in lines:
                    if not line.strip():
                        translated_lines.append('')
                        continue

                    embedding = self.model.encode([line])
                    faiss.normalize_L2(embedding)
                    distances, indices = split_index.search(embedding, 1)

                    if distances[0][0] >= similarity_threshold:
                        best_korean = split_kr_texts[indices[0][0]]
                        translation = split_dict[best_korean]
                        translated_lines.append(translation.strip())
                        line_changed = True
                    else:
                        translated_lines.append(line.strip())

                if line_changed:
                    reconstructed = '\\n'.join('▶' + line if line else '' for line in translated_lines)
                    result.at[idx, 'Translation'] = reconstructed
                    replaced_count += 1

            else:
                # Whole text matching
                embedding = self.model.encode([normalized_text])
                faiss.normalize_L2(embedding)

                if whole_index:
                    distances, indices = whole_index.search(embedding, 1)
                    if distances[0][0] >= similarity_threshold:
                        best_korean = whole_kr_texts[indices[0][0]]
                        translation = whole_dict[best_korean]
                        adapted = adapt_structure(original_text, translation)
                        result.at[idx, 'Translation'] = adapted
                        replaced_count += 1
                else:
                    # Fallback to split
                    distances, indices = split_index.search(embedding, 1)
                    if distances[0][0] >= similarity_threshold:
                        best_korean = split_kr_texts[indices[0][0]]
                        translation = split_dict[best_korean]
                        result.at[idx, 'Translation'] = translation
                        replaced_count += 1

            if progress_callback and (idx + 1) % 100 == 0:
                progress_callback(idx + 1, total)

        logger.success(f"Auto-translated {replaced_count}/{total} strings")

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get searcher status."""
        return {
            "model_loaded": self.model is not None,
            "embeddings_manager_set": self.embeddings_manager is not None,
            "dictionary_loaded": self.embeddings_manager.split_index is not None if self.embeddings_manager else False,
            "faiss_available": FAISS_AVAILABLE
        }
