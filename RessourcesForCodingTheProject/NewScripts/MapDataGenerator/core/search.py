"""
Search Module (REWRITTEN)

Multi-mode search functionality:
- MAP mode: Search FactionNodeVerified
- CHARACTER mode: Search CharacterItem
- ITEM mode: Search ItemEntry

All search results are GUARANTEED to have images (image-first architecture).

Supports:
- Contains search
- Exact match search
- Fuzzy search (using SequenceMatcher)
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union

from .linkage import (
    LinkageResolver, DataMode,
    FactionNodeVerified, CharacterItem, ItemEntry
)
from .language import LanguageTable, get_translation

try:
    from utils.filters import normalize_for_search, contains_korean
except ImportError:
    from ..utils.filters import normalize_for_search, contains_korean

log = logging.getLogger(__name__)


# =============================================================================
# SEARCH RESULT (UNIFIED)
# =============================================================================

@dataclass
class SearchResult:
    """
    Unified search result for all modes.

    GUARANTEED: Every SearchResult has ui_texture_name and dds_path
    (because image-first architecture only collects verified entries).
    """
    strkey: str
    name_kr: str
    name_translated: str
    desc_kr: str
    desc_translated: str
    ui_texture_name: str  # GUARANTEED non-empty
    dds_path: Path  # GUARANTEED valid path

    # Optional fields (mode-dependent)
    position: Optional[Tuple[float, float]] = None  # MAP mode only
    group: str = ""  # GROUP name (CHARACTER) or GROUP_NAME (ITEM)

    # Search metadata
    match_score: float = 0.0
    match_field: str = ""

    @property
    def position_str(self) -> str:
        """Get position as formatted string."""
        if self.position:
            return f"({self.position[0]:.1f}, {self.position[1]:.1f})"
        return ""


# =============================================================================
# SEARCH ENGINE (MULTI-MODE)
# =============================================================================

class SearchEngine:
    """
    Multi-mode search engine.

    Supports three modes:
    - MAP: Search FactionNodeVerified
    - CHARACTER: Search CharacterItem
    - ITEM: Search ItemEntry

    All results are guaranteed to have images (image-first architecture).
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
        self._mode: DataMode = DataMode.MAP

    def set_mode(self, mode: Union[DataMode, str]) -> None:
        """
        Set search mode and rebuild index.

        Args:
            mode: DataMode enum or string ('map', 'character', 'item')
        """
        if isinstance(mode, str):
            mode = DataMode(mode.lower())

        if self._mode != mode:
            self._mode = mode
            self._build_search_index()
            log.info("Search mode changed to: %s", mode.value)

    @property
    def mode(self) -> DataMode:
        """Get current search mode."""
        return self._mode

    def set_language_table(self, table: LanguageTable) -> None:
        """
        Set the language table for translations.

        Args:
            table: Language table {normalized_korean: [(translation, stringid), ...]}
        """
        self._lang_table = table
        self._build_search_index()

    def _build_search_index(self) -> None:
        """Build search index based on current mode."""
        self._search_index.clear()

        if self._mode == DataMode.MAP:
            self._build_index_map()
        elif self._mode == DataMode.CHARACTER:
            self._build_index_character()
        elif self._mode == DataMode.ITEM:
            self._build_index_item()

    def _build_index_map(self) -> None:
        """Build search index for MAP mode (FactionNodes + KnowledgeInfo items)."""
        # Index FactionNodes (have map positions)
        for strkey, node in self._resolver.faction_nodes.items():
            terms = []

            # Korean name
            if node.name_kr:
                terms.append(normalize_for_search(node.name_kr))

            # Translated name
            name_tr, _ = get_translation(node.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Description
            if node.desc_kr:
                terms.append(normalize_for_search(node.desc_kr))

            # Translated description
            desc_tr, _ = get_translation(node.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr))

            # StrKey
            terms.append(strkey.lower())

            self._search_index[strkey] = terms

        faction_count = len(self._search_index)

        # ALSO index Items (KnowledgeInfo entries with images)
        for strkey, item in self._resolver.items.items():
            if strkey in self._search_index:
                continue  # Already indexed as FactionNode

            terms = []

            # Korean name
            if item.name_kr:
                terms.append(normalize_for_search(item.name_kr))

            # Translated name
            name_tr, _ = get_translation(item.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Description
            if item.desc_kr:
                terms.append(normalize_for_search(item.desc_kr))

            # Translated description
            desc_tr, _ = get_translation(item.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr))

            # Group name
            if item.group_name:
                terms.append(normalize_for_search(item.group_name))

            # StrKey
            terms.append(strkey.lower())

            self._search_index[strkey] = terms

        log.info("Built MAP search index: %d FactionNodes + %d KnowledgeInfo = %d total",
                 faction_count, len(self._search_index) - faction_count, len(self._search_index))

    def _build_index_character(self) -> None:
        """Build search index for CHARACTER mode."""
        for strkey, char in self._resolver.characters.items():
            terms = []

            # Korean name
            if char.name_kr:
                terms.append(normalize_for_search(char.name_kr))

            # Translated name
            name_tr, _ = get_translation(char.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Description
            if char.desc_kr:
                terms.append(normalize_for_search(char.desc_kr))

            # Translated description
            desc_tr, _ = get_translation(char.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr))

            # Group
            if char.group:
                terms.append(normalize_for_search(char.group))

            # StrKey
            terms.append(strkey.lower())

            self._search_index[strkey] = terms

        log.info("Built CHARACTER search index with %d entries", len(self._search_index))

    def _build_index_item(self) -> None:
        """Build search index for ITEM mode."""
        for strkey, item in self._resolver.items.items():
            terms = []

            # Korean name
            if item.name_kr:
                terms.append(normalize_for_search(item.name_kr))

            # Translated name
            name_tr, _ = get_translation(item.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Description
            if item.desc_kr:
                terms.append(normalize_for_search(item.desc_kr))

            # Translated description
            desc_tr, _ = get_translation(item.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr))

            # Group name
            if item.group_name:
                terms.append(normalize_for_search(item.group_name))

            # StrKey
            terms.append(strkey.lower())

            self._search_index[strkey] = terms

        log.info("Built ITEM search index with %d entries", len(self._search_index))

    def search(
        self,
        query: str,
        match_type: str = "contains",
        limit: int = 100,
        start_index: int = 0
    ) -> List[SearchResult]:
        """
        Search for entries matching the query.

        Args:
            query: Search query
            match_type: "contains", "exact", or "fuzzy"
            limit: Maximum results to return
            start_index: Starting index for pagination

        Returns:
            List of SearchResult objects (all guaranteed to have images)
        """
        if not query or query.isspace():
            return []

        query_normalized = normalize_for_search(query)
        results: List[SearchResult] = []

        # Direct StrKey lookup (fast path)
        if query in self._search_index:
            result = self._get_result_by_strkey(query)
            if result:
                result.match_field = "strkey"
                result.match_score = 1.0
                return [result]

        # Search all entries
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
                result = self._get_result_by_strkey(strkey)
                if result:
                    result.match_score = match_score
                    result.match_field = match_field
                    results.append(result)

        # Sort by match score (descending) then by Korean name
        results.sort(key=lambda r: (-r.match_score, len(r.name_kr)))

        # Paginate
        if start_index >= len(results):
            return []

        return results[start_index:start_index + limit]

    def _get_result_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        """Get SearchResult for a strkey based on current mode."""
        if self._mode == DataMode.MAP:
            return self._node_to_result(strkey)
        elif self._mode == DataMode.CHARACTER:
            return self._character_to_result(strkey)
        elif self._mode == DataMode.ITEM:
            return self._item_to_result(strkey)
        return None

    def _node_to_result(self, strkey: str) -> Optional[SearchResult]:
        """Convert FactionNodeVerified or ItemEntry to SearchResult for MAP mode."""
        # First try FactionNode
        node = self._resolver.get_node(strkey)
        if node:
            name_tr, _ = get_translation(node.name_kr, self._lang_table, node.name_kr)
            desc_tr, _ = get_translation(node.desc_kr, self._lang_table, "")

            return SearchResult(
                strkey=node.strkey,
                name_kr=node.name_kr,
                name_translated=name_tr,
                desc_kr=node.desc_kr,
                desc_translated=desc_tr,
                ui_texture_name=node.ui_texture_name,
                dds_path=node.dds_path,
                position=node.position_2d,
                group="",
            )

        # Fallback to ItemEntry (KnowledgeInfo)
        item = self._resolver.get_item(strkey)
        if item:
            name_tr, _ = get_translation(item.name_kr, self._lang_table, item.name_kr)
            desc_tr, _ = get_translation(item.desc_kr, self._lang_table, "")

            return SearchResult(
                strkey=item.strkey,
                name_kr=item.name_kr,
                name_translated=name_tr,
                desc_kr=item.desc_kr,
                desc_translated=desc_tr,
                ui_texture_name=item.ui_texture_name,
                dds_path=item.dds_path,
                position=None,  # Items don't have map positions
                group=item.group_name,
            )

        return None

    def _character_to_result(self, strkey: str) -> Optional[SearchResult]:
        """Convert CharacterItem to SearchResult."""
        char = self._resolver.get_character(strkey)
        if not char:
            return None

        name_tr, _ = get_translation(char.name_kr, self._lang_table, char.name_kr)
        desc_tr, _ = get_translation(char.desc_kr, self._lang_table, "")

        return SearchResult(
            strkey=char.strkey,
            name_kr=char.name_kr,
            name_translated=name_tr,
            desc_kr=char.desc_kr,
            desc_translated=desc_tr,
            ui_texture_name=char.ui_texture_name,
            dds_path=char.dds_path,
            position=None,
            group=char.group,
        )

    def _item_to_result(self, strkey: str) -> Optional[SearchResult]:
        """Convert ItemEntry to SearchResult."""
        item = self._resolver.get_item(strkey)
        if not item:
            return None

        name_tr, _ = get_translation(item.name_kr, self._lang_table, item.name_kr)
        desc_tr, _ = get_translation(item.desc_kr, self._lang_table, "")

        return SearchResult(
            strkey=item.strkey,
            name_kr=item.name_kr,
            name_translated=name_tr,
            desc_kr=item.desc_kr,
            desc_translated=desc_tr,
            ui_texture_name=item.ui_texture_name,
            dds_path=item.dds_path,
            position=None,
            group=item.group_name,
        )

    def _get_field_name(self, index: int) -> str:
        """Get field name from index."""
        fields = ["name_kr", "name_tr", "desc_kr", "desc_tr", "group", "strkey"]
        return fields[index] if index < len(fields) else "unknown"

    def get_all_entries(self, limit: int = 100, start_index: int = 0) -> List[SearchResult]:
        """
        Get all entries for current mode (for initial display or browsing).

        Args:
            limit: Maximum results to return
            start_index: Starting index for pagination

        Returns:
            List of SearchResult objects
        """
        results = []
        strkeys = list(self._search_index.keys())

        # Sort by Korean name
        def get_name(sk):
            if self._mode == DataMode.MAP:
                node = self._resolver.get_node(sk)
                return node.name_kr if node else ""
            elif self._mode == DataMode.CHARACTER:
                char = self._resolver.get_character(sk)
                return char.name_kr if char else ""
            elif self._mode == DataMode.ITEM:
                item = self._resolver.get_item(sk)
                return item.name_kr if item else ""
            return ""

        strkeys.sort(key=get_name)

        for strkey in strkeys[start_index:start_index + limit]:
            result = self._get_result_by_strkey(strkey)
            if result:
                results.append(result)

        return results

    def get_entry_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        """
        Get a single entry by StrKey.

        Args:
            strkey: Entry StrKey

        Returns:
            SearchResult or None
        """
        return self._get_result_by_strkey(strkey)

    @property
    def total_entries(self) -> int:
        """Get total number of searchable entries for current mode."""
        return len(self._search_index)

    # Legacy compatibility
    @property
    def total_nodes(self) -> int:
        """Legacy: Get total number of searchable entries."""
        return self.total_entries

    def get_all_nodes(self, limit: int = 100, start_index: int = 0) -> List[SearchResult]:
        """Legacy: Get all nodes (redirects to get_all_entries)."""
        return self.get_all_entries(limit, start_index)

    def get_node_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        """Legacy: Get node by strkey (redirects to get_entry_by_strkey)."""
        return self.get_entry_by_strkey(strkey)
