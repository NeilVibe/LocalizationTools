"""
Search Module - SIMPLIFIED

Unified search across all modes using DataEntry structure.
Prioritizes entries with images but shows all results.
"""

import logging
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union

# Ensure parent directory is in sys.path for PyInstaller compatibility
sys.path.insert(0, str(Path(__file__).parent.parent))

from .linkage import LinkageResolver, DataMode, DataEntry
from .language import LanguageTable, get_translation
from utils.filters import normalize_for_search, contains_korean

log = logging.getLogger(__name__)


# =============================================================================
# SEARCH RESULT
# =============================================================================

@dataclass
class SearchResult:
    """Unified search result."""
    strkey: str
    name_kr: str
    name_translated: str
    desc_kr: str
    desc_translated: str
    ui_texture_name: str
    dds_path: Optional[Path]
    has_image: bool  # True if DDS exists

    # Optional fields - position has all 3 values (X, Y, Z)
    position: Optional[Tuple[float, float, float]] = None  # Full 3D position
    group: str = ""

    # CHARACTER-specific fields
    use_macro: str = ""  # Race/Gender
    age: str = ""  # Age
    job: str = ""  # Job

    # ITEM-specific fields
    string_id: str = ""  # StringID

    # Search metadata
    match_score: float = 0.0
    match_field: str = ""

    @property
    def position_str(self) -> str:
        """Full 3D position string (X, Y, Z)."""
        if self.position:
            return f"({self.position[0]:.1f}, {self.position[1]:.1f}, {self.position[2]:.1f})"
        return ""

    @property
    def position_2d_str(self) -> str:
        """2D position string (X, Z) for map display."""
        if self.position:
            return f"({self.position[0]:.1f}, {self.position[2]:.1f})"
        return ""


# =============================================================================
# SEARCH ENGINE
# =============================================================================

class SearchEngine:
    """Unified search engine for all modes."""

    def __init__(
        self,
        resolver: LinkageResolver,
        fuzzy_threshold: float = 0.6
    ):
        self._resolver = resolver
        self._fuzzy_threshold = fuzzy_threshold
        self._lang_table: LanguageTable = {}
        self._search_index: Dict[str, List[str]] = {}
        self._mode: DataMode = DataMode.MAP

    def set_mode(self, mode: Union[DataMode, str]) -> None:
        """Set search mode and rebuild index."""
        if isinstance(mode, str):
            mode = DataMode(mode.lower())

        self._mode = mode
        self._build_search_index()
        log.info("Search mode: %s, indexed %d entries", mode.value, len(self._search_index))

    @property
    def mode(self) -> DataMode:
        return self._mode

    def set_language_table(self, table: LanguageTable) -> None:
        """Set language table for translations."""
        self._lang_table = table
        self._build_search_index()

    def _build_search_index(self) -> None:
        """Build search index from all entries."""
        self._search_index.clear()

        for strkey, entry in self._resolver.entries.items():
            terms = []

            # Korean name
            if entry.name_kr:
                terms.append(normalize_for_search(entry.name_kr))

            # Translated name
            name_tr, _ = get_translation(entry.name_kr, self._lang_table)
            if name_tr:
                terms.append(normalize_for_search(name_tr))

            # Description (first 200 chars)
            if entry.desc_kr:
                desc_short = entry.desc_kr[:200]
                terms.append(normalize_for_search(desc_short))

            # Translated description
            desc_tr, _ = get_translation(entry.desc_kr, self._lang_table)
            if desc_tr:
                terms.append(normalize_for_search(desc_tr[:200]))

            # Group
            if entry.group:
                terms.append(normalize_for_search(entry.group))

            # StrKey
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
        """Search for entries matching query."""
        if not query or query.isspace():
            return []

        query_normalized = normalize_for_search(query)
        results: List[SearchResult] = []

        # Direct StrKey lookup
        if query in self._search_index:
            result = self._entry_to_result(query)
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
                result = self._entry_to_result(strkey)
                if result:
                    result.match_score = match_score
                    result.match_field = match_field
                    results.append(result)

        # Sort: prioritize entries with images, then by score, then by name length
        results.sort(key=lambda r: (-int(r.has_image), -r.match_score, len(r.name_kr)))

        # Paginate
        if start_index >= len(results):
            return []

        return results[start_index:start_index + limit]

    def _entry_to_result(self, strkey: str) -> Optional[SearchResult]:
        """Convert DataEntry to SearchResult."""
        entry = self._resolver.get_entry(strkey)
        if not entry:
            return None

        # For AUDIO mode: use knowledge_key as ENG script (stored there during load)
        if entry.entry_type == "Audio":
            # Audio: name is event_name, desc_kr is KOR script, knowledge_key is ENG script
            name_tr = entry.name_kr  # Event name doesn't need translation
            desc_tr = entry.knowledge_key  # ENG script stored in knowledge_key
        else:
            # Other modes: use language table for translations
            name_tr, _ = get_translation(entry.name_kr, self._lang_table, entry.name_kr)
            desc_tr, _ = get_translation(entry.desc_kr, self._lang_table, "")

        # For ITEM mode, extract StringID from translation lookup
        string_id = ""
        if entry.entry_type == "Item" and entry.name_kr:
            _, string_id = get_translation(entry.name_kr, self._lang_table, "")

        return SearchResult(
            strkey=entry.strkey,
            name_kr=entry.name_kr,
            name_translated=name_tr,
            desc_kr=entry.desc_kr,
            desc_translated=desc_tr,
            ui_texture_name=entry.ui_texture_name,
            dds_path=entry.dds_path,
            has_image=entry.has_image,
            position=entry.position,  # Full 3D position (X, Y, Z)
            group=entry.group,
            use_macro=entry.use_macro,
            age=entry.age,
            job=entry.job,
            string_id=string_id,
        )

    def _get_field_name(self, index: int) -> str:
        fields = ["name_kr", "name_tr", "desc_kr", "desc_tr", "group", "strkey"]
        return fields[index] if index < len(fields) else "unknown"

    def get_all_entries(self, limit: int = 100, start_index: int = 0) -> List[SearchResult]:
        """Get all entries for browsing."""
        results = []

        # Sort by: has_image (True first), then name
        sorted_keys = sorted(
            self._search_index.keys(),
            key=lambda sk: (
                -int(self._resolver.get_entry(sk).has_image if self._resolver.get_entry(sk) else False),
                self._resolver.get_entry(sk).name_kr if self._resolver.get_entry(sk) else ""
            )
        )

        for strkey in sorted_keys[start_index:start_index + limit]:
            result = self._entry_to_result(strkey)
            if result:
                results.append(result)

        return results

    def get_entry_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        """Get single entry by StrKey."""
        return self._entry_to_result(strkey)

    @property
    def total_entries(self) -> int:
        return len(self._search_index)

    # Legacy compatibility
    @property
    def total_nodes(self) -> int:
        return self.total_entries

    def get_all_nodes(self, limit: int = 100, start_index: int = 0) -> List[SearchResult]:
        return self.get_all_entries(limit, start_index)

    def get_node_by_strkey(self, strkey: str) -> Optional[SearchResult]:
        return self.get_entry_by_strkey(strkey)
