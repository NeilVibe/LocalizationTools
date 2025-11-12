"""
QuickSearch Searcher

Handles search operations on dictionaries.
"""

from typing import List, Tuple, Optional, Dict
from loguru import logger


class Searcher:
    """
    Search engine for QuickSearch dictionaries.

    Supports:
    - Contains matching
    - Exact matching
    - Search with reference dictionary
    - Multi-line search
    """

    def __init__(self):
        """Initialize searcher."""
        self.current_dict = None
        self.reference_dict = None
        self.reference_enabled = False

    def load_dictionary(self, dictionary: Dict):
        """
        Load main dictionary for searching.

        Args:
            dictionary: Dictionary object with split_dict and whole_dict
        """
        self.current_dict = dictionary
        logger.info("Main dictionary loaded into searcher")

    def load_reference_dictionary(self, dictionary: Dict):
        """
        Load reference dictionary.

        Args:
            dictionary: Reference dictionary object
        """
        self.reference_dict = dictionary
        self.reference_enabled = True
        logger.info("Reference dictionary loaded into searcher")

    def toggle_reference(self, enabled: bool):
        """
        Enable or disable reference dictionary.

        Args:
            enabled: True to enable, False to disable
        """
        self.reference_enabled = enabled
        logger.info(f"Reference dictionary {'enabled' if enabled else 'disabled'}")

    def search_one_line(
        self,
        query: str,
        match_type: str = "contains",
        start_index: int = 0,
        limit: int = 50
    ) -> List[Tuple]:
        """
        Search for a single query string.

        Args:
            query: Search query
            match_type: "contains" or "exact" (default: "contains")
            start_index: Starting index for pagination (default: 0)
            limit: Maximum number of results to return (default: 50)

        Returns:
            List of tuples:
            - If reference enabled: (korean, translation, reference_translation, string_id)
            - If reference disabled: (korean, translation, string_id)
        """
        if not self.current_dict:
            logger.warning("No dictionary loaded for search")
            return []

        if not query or query.isspace():
            return []

        query_str = str(query).strip()

        split_dict = self.current_dict.get('split_dict', {})
        whole_dict = self.current_dict.get('whole_dict', {})
        stringid_to_entry = self.current_dict.get('stringid_to_entry', {})

        ref_split_dict = self.reference_dict.get('split_dict', {}) if self.reference_dict else {}
        ref_whole_dict = self.reference_dict.get('whole_dict', {}) if self.reference_dict else {}

        results = []

        # --- Fast path: StringId direct lookup ---
        if query_str in stringid_to_entry:
            korean, translation = stringid_to_entry[query_str]

            if self.reference_enabled and self.reference_dict:
                # Get reference translation
                ref_translation = None
                if korean in ref_split_dict and ref_split_dict[korean]:
                    ref_translation = ref_split_dict[korean][0][0]
                elif korean in ref_whole_dict and ref_whole_dict[korean]:
                    ref_translation = ref_whole_dict[korean][0][0]

                return [(korean, translation, ref_translation, query_str)]
            else:
                return [(korean, translation, query_str)]

        # --- Standard search ---
        query_lower = query.lower()

        def check_match(text1: str, text2: str, stringid: str) -> bool:
            """Check if query matches any of the texts."""
            if match_type == "contains":
                return (
                    query_lower in str(text1).lower() or
                    query_lower in str(text2).lower() or
                    query_lower in str(stringid).lower()
                )
            else:  # exact match
                return (
                    query_lower == str(text1).lower() or
                    query_lower == str(text2).lower() or
                    query_lower == str(stringid).lower()
                )

        def is_valid_entry(korean: str, translation: str, stringid: str) -> bool:
            """Check if entry is valid."""
            return bool(korean.strip() and translation.strip())

        # Search in split_dict
        for korean, translations in split_dict.items():
            for translation, stringid in translations:
                if check_match(korean, translation, stringid) and is_valid_entry(korean, translation, stringid):
                    if self.reference_enabled and self.reference_dict:
                        # Get reference translation
                        ref_translation = None
                        if korean in ref_split_dict and ref_split_dict[korean]:
                            ref_translation = ref_split_dict[korean][0][0]
                        elif korean in ref_whole_dict and ref_whole_dict[korean]:
                            ref_translation = ref_whole_dict[korean][0][0]

                        results.append((korean, translation, ref_translation, stringid))
                    else:
                        results.append((korean, translation, stringid))

        # Search in whole_dict
        for korean, translations in whole_dict.items():
            for translation, stringid in translations:
                if check_match(korean, translation, stringid) and is_valid_entry(korean, translation, stringid):
                    if self.reference_enabled and self.reference_dict:
                        # Get reference translation
                        ref_translation = None
                        if korean in ref_split_dict and ref_split_dict[korean]:
                            ref_translation = ref_split_dict[korean][0][0]
                        elif korean in ref_whole_dict and ref_whole_dict[korean]:
                            ref_translation = ref_whole_dict[korean][0][0]

                        results.append((korean, translation, ref_translation, stringid))
                    else:
                        results.append((korean, translation, stringid))

        # Search in reference dictionary (if enabled and query not in main dict)
        if self.reference_enabled and self.reference_dict:
            for korean, ref_translations in ref_split_dict.items():
                for ref_translation, _ in ref_translations:
                    if query_lower in str(ref_translation).lower():
                        # Find corresponding main translation
                        translation = None
                        stringid = None

                        if korean in split_dict and split_dict[korean]:
                            translation, stringid = split_dict[korean][0]
                        elif korean in whole_dict and whole_dict[korean]:
                            translation, stringid = whole_dict[korean][0]

                        if translation and is_valid_entry(korean, translation, stringid):
                            # Check if not already in results
                            if (korean, translation, ref_translation, stringid) not in results:
                                results.append((korean, translation, ref_translation, stringid))

            for korean, ref_translations in ref_whole_dict.items():
                for ref_translation, _ in ref_translations:
                    if query_lower in str(ref_translation).lower():
                        # Find corresponding main translation
                        translation = None
                        stringid = None

                        if korean in split_dict and split_dict[korean]:
                            translation, stringid = split_dict[korean][0]
                        elif korean in whole_dict and whole_dict[korean]:
                            translation, stringid = whole_dict[korean][0]

                        if translation and is_valid_entry(korean, translation, stringid):
                            # Check if not already in results
                            if (korean, translation, ref_translation, stringid) not in results:
                                results.append((korean, translation, ref_translation, stringid))

        # Sort by length of korean text (shorter first)
        results.sort(key=lambda x: len(str(x[0])))

        # Apply pagination
        total_count = len(results)
        results = results[start_index:start_index + limit]

        logger.info(f"Search completed: query='{query}', match_type={match_type}, found={total_count}, returned={len(results)}")

        return results, total_count

    def search_multi_line(
        self,
        queries: List[str],
        match_type: str = "contains",
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for multiple queries (one per line).

        Args:
            queries: List of search queries
            match_type: "contains" or "exact" (default: "contains")
            limit: Maximum number of results per query (default: 50)

        Returns:
            List of dicts with:
            - line: Query string
            - matches: List of match tuples
        """
        results = []

        for query in queries:
            if not query or query.isspace():
                continue

            matches, total = self.search_one_line(query, match_type=match_type, start_index=0, limit=limit)

            results.append({
                'line': query.strip(),
                'matches': matches,
                'total_count': total
            })

        logger.info(f"Multi-line search completed: {len(queries)} queries, {sum(len(r['matches']) for r in results)} total matches")

        return results
