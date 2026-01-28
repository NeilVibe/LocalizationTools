"""
Search Module

Provides search functionality for FactionNode data:
- Contains search
- Exact match search
- Fuzzy search (using SequenceMatcher)

Searches across: name (KR), name (translated), description, StrKey
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Tuple

from .linkage import FactionNode, LinkageResolver
from .language import LanguageTable, get_translation

try:
    from utils.filters import normalize_for_search, contains_korean
except ImportError:
    from ..utils.filters import normalize_for_search, contains_korean

log = logging.getLogger(__name__)


# =============================================================================
# SEARCH RESULT
# =============================================================================

@dataclass
class SearchResult:
    """Represents a single search result."""
    strkey: str
    name_kr: str
    name_translated: str
    desc_kr: str
    desc_translated: str
    position: Tuple[float, float]  # 2D position (x, z)
    ui_texture_name: Optional[str] = None
    match_score: float = 0.0  # For fuzzy matching
    match_field: str = ""  # Which field matched

    @property
    def position_str(self) -> str:
        """Get position as formatted string."""
        return f"({self.position[0]:.1f}, {self.position[1]:.1f})"


# =============================================================================
# SEARCH ENGINE
# =============================================================================

class SearchEngine:
    """
    Search engine for FactionNode data.

    Supports:
    - Contains search: query in text.lower()
    - Exact match: full string equality
    - Fuzzy search: SequenceMatcher ratio > threshold
    """

    def __init__(
        self,
        resolver: LinkageResolver,
        fuzzy_threshold: float = 0.6
    ):
        """
        Initialize search engine.

        Args:
            resolver: LinkageResolver with loaded data
            fuzzy_threshold: Minimum ratio for fuzzy matches (0.0-1.0)
        """
        self._resolver = resolver
        self._fuzzy_threshold = fuzzy_threshold
        self._lang_table: LanguageTable = {}
        self._search_index: Dict[str, List[str]] = {}  # strkey -> searchable terms

    def set_language_table(self, table: LanguageTable) -> None:
        """
        Set the language table for translations.

        Args:
            table: Language table {normalized_korean: [(translation, stringid), ...]}
        """
        self._lang_table = table
        self._build_search_index()

    def _build_search_index(self) -> None:
        """Build search index for faster searching."""
        self._search_index.clear()

        for strkey, node in self._resolver.faction_nodes.items():
            terms = []

            # Add Korean name
            if node.name_kr:
                terms.append(normalize_for_search(node.name_kr))

            # Add translated name
            name_tr, _ = get_translation(node.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Add description
            if node.desc_kr:
                terms.append(normalize_for_search(node.desc_kr))

            # Add translated description
            desc_tr, _ = get_translation(node.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr))

            # Add strkey
            terms.append(strkey.lower())

            self._search_index[strkey] = terms

        log.info("Built search index with %d entries", len(self._search_index))

    def search(
        self,
        query: str,
        match_type: str = "contains",
        limit: int = 100,
        start_index: int = 0
    ) -> List[SearchResult]:
        """
        Search for nodes matching the query.

        Args:
            query: Search query
            match_type: "contains", "exact", or "fuzzy"
            limit: Maximum results to return
            start_index: Starting index for pagination

        Returns:
            List of SearchResult objects
        """
        if not query or query.isspace():
            return []

        query_normalized = normalize_for_search(query)
        results: List[SearchResult] = []

        # Direct StrKey lookup (fast path)
        if query in self._resolver.faction_nodes:
            node = self._resolver.faction_nodes[query]
            result = self._node_to_result(node)
            result.match_field = "strkey"
            result.match_score = 1.0
            return [result]

        # Search all nodes
        for strkey, terms in self._search_index.items():
            match_score = 0.0
            match_field = ""

            if match_type == "contains":
                for i, term in enumerate(terms):
                    if query_normalized in term:
                        match_score = 1.0
                        match_field = self._get_field_name(i)
                        break

            elif match_type == "exact":
                for i, term in enumerate(terms):
                    if query_normalized == term:
                        match_score = 1.0
                        match_field = self._get_field_name(i)
                        break

            elif match_type == "fuzzy":
                best_score = 0.0
                best_field = ""
                for i, term in enumerate(terms):
                    ratio = SequenceMatcher(None, query_normalized, term).ratio()
                    if ratio > best_score:
                        best_score = ratio
                        best_field = self._get_field_name(i)

                if best_score >= self._fuzzy_threshold:
                    match_score = best_score
                    match_field = best_field

            if match_score > 0:
                node = self._resolver.faction_nodes[strkey]
                result = self._node_to_result(node)
                result.match_score = match_score
                result.match_field = match_field
                results.append(result)

        # Sort by match score (descending) then by Korean name
        results.sort(key=lambda r: (-r.match_score, len(r.name_kr)))

        # Paginate
        if start_index >= len(results):
            return []

        return results[start_index:start_index + limit]

    def _node_to_result(self, node: FactionNode) -> SearchResult:
        """Convert FactionNode to SearchResult."""
        name_tr, _ = get_translation(node.name_kr, self._lang_table, node.name_kr)
        desc_tr, _ = get_translation(node.desc_kr, self._lang_table, "")

        ui_texture = self._resolver.resolve_ui_texture(node.strkey)

        return SearchResult(
            strkey=node.strkey,
            name_kr=node.name_kr,
            name_translated=name_tr,
            desc_kr=node.desc_kr,
            desc_translated=desc_tr,
            position=node.position_2d,
            ui_texture_name=ui_texture,
        )

    def _get_field_name(self, index: int) -> str:
        """Get field name from index."""
        fields = ["name_kr", "name_tr", "desc_kr", "desc_tr", "strkey"]
        return fields[index] if index < len(fields) else "unknown"

    def get_all_nodes(self, limit: int = 100, start_index: int = 0) -> List[SearchResult]:
        """
        Get all nodes (for initial display or browsing).

        Args:
            limit: Maximum results to return
            start_index: Starting index for pagination

        Returns:
            List of SearchResult objects
        """
        results = []
        nodes = list(self._resolver.faction_nodes.values())

        # Sort by Korean name
        nodes.sort(key=lambda n: n.name_kr)

        for node in nodes[start_index:start_index + limit]:
            result = self._node_to_result(node)
            results.append(result)

        return results

    def get_node_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        """
        Get a single node by StrKey.

        Args:
            strkey: Node StrKey

        Returns:
            SearchResult or None
        """
        node = self._resolver.get_node(strkey)
        if node:
            return self._node_to_result(node)
        return None

    @property
    def total_nodes(self) -> int:
        """Get total number of searchable nodes."""
        return len(self._resolver.faction_nodes)
