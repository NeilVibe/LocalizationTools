"""
LDM Translation Memory Module

Provides Translation Memory (TM) suggestions for the LDM editor.
Reuses the KR Similar fuzzy matching engine for semantic similarity.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

# Factor Power: Import from centralized utils
from server.utils.text_utils import normalize_korean_text as normalize_text

# Import ML components from KR Similar (TODO: move to utils when ready)
try:
    from server.tools.kr_similar.embeddings import EmbeddingsManager
    from server.tools.kr_similar.searcher import SimilaritySearcher
    KR_SIMILAR_AVAILABLE = True
except ImportError:
    KR_SIMILAR_AVAILABLE = False
    logger.warning("KR Similar not available - TM will use text matching only")

from server.database.models import LDMRow, LDMFile


class TranslationMemory:
    """
    Translation Memory for LDM.

    Provides TM suggestions when editing translations:
    - Finds similar source texts in the database
    - Returns their translations as suggestions
    - Supports fuzzy matching (70%+ similarity)
    """

    def __init__(self, db: Session = None):
        """
        Initialize Translation Memory.

        Args:
            db: Optional database session for queries
        """
        self.db = db
        self.embeddings_manager = None
        self.searcher = None
        self._initialized = False

        # TM settings
        self.similarity_threshold = 0.70  # 70% minimum for suggestions
        self.max_suggestions = 5  # Maximum TM suggestions to return

        logger.info("TranslationMemory initialized")

    def _init_semantic_search(self):
        """Initialize semantic search components (lazy loading)."""
        if not KR_SIMILAR_AVAILABLE:
            return False

        if self._initialized:
            return True

        try:
            self.embeddings_manager = EmbeddingsManager()
            self.searcher = SimilaritySearcher(self.embeddings_manager)
            self._initialized = True
            logger.success("TM semantic search initialized")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize semantic search: {e}")
            return False

    def get_suggestions(
        self,
        source_text: str,
        file_id: Optional[int] = None,
        project_id: Optional[int] = None,
        exclude_row_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Translation Memory suggestions for a source text.

        Searches the database for similar source texts and returns
        their translations as suggestions.

        Args:
            source_text: Korean source text to find matches for
            file_id: Optional - limit to same file
            project_id: Optional - limit to same project
            exclude_row_id: Optional - exclude this row from results

        Returns:
            List of TM suggestions with:
            - source: The matched source text
            - target: The existing translation
            - similarity: Match percentage (0.0-1.0)
            - row_id: Source row ID
            - file_name: Source file name
        """
        if not source_text or not source_text.strip():
            return []

        if not self.db:
            logger.warning("No database session for TM lookup")
            return []

        suggestions = []

        # Try semantic search first
        if self._init_semantic_search():
            suggestions = self._semantic_search(
                source_text, file_id, project_id, exclude_row_id
            )

        # Fall back to text matching if no semantic results
        if not suggestions:
            suggestions = self._text_search(
                source_text, file_id, project_id, exclude_row_id
            )

        # Sort by similarity (descending) and limit results
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:self.max_suggestions]

    def _semantic_search(
        self,
        source_text: str,
        file_id: Optional[int],
        project_id: Optional[int],
        exclude_row_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search.

        NOTE: Semantic search is not yet implemented. This returns []
        to trigger fallback to text search in the caller.

        Future implementation would require:
        1. Indexing all translated rows in the project/file
        2. Using FAISS to find similar embeddings
        3. Returning matches above threshold

        See: DR4-004 in docs/code-review/ISSUES_20251212.md
        """
        # Returns empty to trigger text search fallback
        return []

    def _text_search(
        self,
        source_text: str,
        file_id: Optional[int],
        project_id: Optional[int],
        exclude_row_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Perform simple text-based search (fallback)."""
        try:
            normalized = source_text.strip().lower()

            # Build query for rows with translations
            query = select(
                LDMRow.id,
                LDMRow.source,
                LDMRow.target,
                LDMRow.file_id,
                LDMFile.name.label('file_name')
            ).join(
                LDMFile, LDMRow.file_id == LDMFile.id
            ).where(
                LDMRow.target.isnot(None),
                LDMRow.target != ''
            )

            # Scope by file if specified
            if file_id:
                query = query.where(LDMRow.file_id == file_id)
            elif project_id:
                query = query.where(LDMFile.project_id == project_id)

            # Exclude current row
            if exclude_row_id:
                query = query.where(LDMRow.id != exclude_row_id)

            # Limit search to reasonable number
            query = query.limit(1000)

            result = self.db.execute(query)
            rows = result.fetchall()

            suggestions = []
            for row in rows:
                if row.source:
                    # Calculate simple similarity
                    similarity = self._calculate_similarity(
                        normalized,
                        row.source.strip().lower()
                    )

                    if similarity >= self.similarity_threshold:
                        suggestions.append({
                            'source': row.source,
                            'target': row.target,
                            'similarity': similarity,
                            'row_id': row.id,
                            'file_name': row.file_name
                        })

            logger.debug(f"TM text search found {len(suggestions)} matches", {
                "query_preview": source_text[:30],
                "threshold": self.similarity_threshold
            })

            return suggestions

        except Exception as e:
            logger.error(f"TM text search failed: {e}")
            return []

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.

        Uses Levenshtein-based similarity for simple matching.
        For full semantic matching, use the semantic search path.
        """
        if not text1 or not text2:
            return 0.0

        # Exact match
        if text1 == text2:
            return 1.0

        # Prefix/suffix match bonus
        if text1.startswith(text2) or text2.startswith(text1):
            shorter = min(len(text1), len(text2))
            longer = max(len(text1), len(text2))
            return 0.8 * (shorter / longer)

        # Character-level similarity (simplified Jaccard)
        chars1 = set(text1)
        chars2 = set(text2)
        intersection = len(chars1 & chars2)
        union = len(chars1 | chars2)

        if union == 0:
            return 0.0

        jaccard = intersection / union

        # Word-level similarity for bonus
        words1 = set(text1.split())
        words2 = set(text2.split())
        if words1 and words2:
            word_intersection = len(words1 & words2)
            word_union = len(words1 | words2)
            word_jaccard = word_intersection / word_union if word_union > 0 else 0

            # Combine char and word similarity
            return 0.4 * jaccard + 0.6 * word_jaccard

        return jaccard


# Convenience function for API use
def get_tm_suggestions(
    db: Session,
    source_text: str,
    file_id: Optional[int] = None,
    project_id: Optional[int] = None,
    exclude_row_id: Optional[int] = None,
    threshold: float = 0.70,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Get Translation Memory suggestions.

    Convenience function for use in API endpoints.

    Args:
        db: Database session
        source_text: Korean source text
        file_id: Optional file scope
        project_id: Optional project scope
        exclude_row_id: Row to exclude from results
        threshold: Minimum similarity (default 70%)
        max_results: Maximum suggestions to return

    Returns:
        List of TM suggestions
    """
    tm = TranslationMemory(db)
    tm.similarity_threshold = threshold
    tm.max_suggestions = max_results

    return tm.get_suggestions(
        source_text,
        file_id=file_id,
        project_id=project_id,
        exclude_row_id=exclude_row_id
    )
