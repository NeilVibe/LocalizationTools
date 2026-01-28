"""
Search Module

One-line and multi-line search functionality.
"""

from typing import List, Optional, Tuple, Union
from dataclasses import dataclass

try:
    from core.dictionary import Dictionary
except ImportError:
    from .dictionary import Dictionary


@dataclass
class SearchResult:
    """A single search result."""
    korean: str  # Korean/source text
    translation: str  # Translation
    reference: Optional[str] = None  # Reference translation (optional)
    string_id: str = ""  # StringID


def search_one_line(
    query: str,
    dictionary: Dictionary,
    match_type: str = "contains",
    reference_dict: Optional[Dictionary] = None,
    start_index: int = 0,
    limit: int = 50
) -> List[SearchResult]:
    """
    Search for a single query in the dictionary.

    Args:
        query: Search query
        dictionary: Dictionary to search
        match_type: "contains" or "exact"
        reference_dict: Optional reference dictionary
        start_index: Starting index for pagination
        limit: Maximum results to return

    Returns:
        List of SearchResult objects
    """
    if not query or query.isspace():
        return []

    query_str = query.strip()
    query_lower = query_str.lower()
    results: List[SearchResult] = []

    # Fast path: StringID direct lookup
    if query_str in dictionary.stringid_lookup:
        kr, fr = dictionary.stringid_lookup[query_str]
        ref_fr = None

        if reference_dict:
            ref_fr = _get_reference(kr, reference_dict)

        return [SearchResult(
            korean=kr,
            translation=fr,
            reference=ref_fr,
            string_id=query_str
        )]

    def matches(text1: str, text2: str, stringid: str) -> bool:
        """Check if query matches any field."""
        if match_type == "contains":
            return (
                query_lower in str(text1).lower() or
                query_lower in str(text2).lower() or
                query_lower in str(stringid).lower()
            )
        else:  # exact
            return (
                query_lower == str(text1).lower() or
                query_lower == str(text2).lower() or
                query_lower == str(stringid).lower()
            )

    def is_valid(kr: str, fr: str) -> bool:
        """Check if entry is valid."""
        return bool(kr.strip() and fr.strip())

    # Search split dictionary
    for kr, translations in dictionary.split_dict.items():
        for fr, stringid in translations:
            if matches(kr, fr, stringid) and is_valid(kr, fr):
                ref_fr = _get_reference(kr, reference_dict) if reference_dict else None
                results.append(SearchResult(
                    korean=kr,
                    translation=fr,
                    reference=ref_fr,
                    string_id=stringid
                ))

    # Search whole dictionary
    for kr, translations in dictionary.whole_dict.items():
        for fr, stringid in translations:
            if matches(kr, fr, stringid) and is_valid(kr, fr):
                ref_fr = _get_reference(kr, reference_dict) if reference_dict else None
                results.append(SearchResult(
                    korean=kr,
                    translation=fr,
                    reference=ref_fr,
                    string_id=stringid
                ))

    # Search reference dictionary for reference text matches
    if reference_dict:
        for kr, ref_translations in reference_dict.split_dict.items():
            for ref_fr, _ in ref_translations:
                if query_lower in str(ref_fr).lower():
                    # Find main translation
                    fr, stringid = _get_main_translation(kr, dictionary)
                    if fr and is_valid(kr, fr):
                        results.append(SearchResult(
                            korean=kr,
                            translation=fr,
                            reference=ref_fr,
                            string_id=stringid
                        ))

        for kr, ref_translations in reference_dict.whole_dict.items():
            for ref_fr, _ in ref_translations:
                if query_lower in str(ref_fr).lower():
                    fr, stringid = _get_main_translation(kr, dictionary)
                    if fr and is_valid(kr, fr):
                        results.append(SearchResult(
                            korean=kr,
                            translation=fr,
                            reference=ref_fr,
                            string_id=stringid
                        ))

    # Sort by Korean text length
    results.sort(key=lambda x: len(x.korean))

    # Paginate
    if start_index >= len(results):
        return []

    return results[start_index:start_index + limit]


def search_multi_line(
    queries: Union[str, List[str]],
    dictionary: Dictionary,
    match_type: str = "contains",
    reference_dict: Optional[Dictionary] = None
) -> List[SearchResult]:
    """
    Search for multiple queries (one per line).

    Args:
        queries: Newline-separated string or list of queries
        dictionary: Dictionary to search
        match_type: "contains" or "exact"
        reference_dict: Optional reference dictionary

    Returns:
        List of SearchResult objects (one per query, in order)
    """
    if isinstance(queries, str):
        query_list = [q.strip() for q in queries.split('\n') if q.strip()]
    else:
        query_list = [q.strip() for q in queries if q.strip()]

    results: List[SearchResult] = []

    for query in query_list:
        # Get first result for each query
        search_results = search_one_line(
            query,
            dictionary,
            match_type,
            reference_dict,
            start_index=0,
            limit=1
        )

        if search_results:
            results.append(search_results[0])
        else:
            # No result found - add placeholder
            results.append(SearchResult(
                korean="❓❓",
                translation="❓❓",
                reference="❓❓" if reference_dict else None,
                string_id=""
            ))

    return results


def _get_reference(korean: str, reference_dict: Dictionary) -> Optional[str]:
    """Get reference translation for Korean text."""
    if not reference_dict:
        return None

    # Check split dict
    if korean in reference_dict.split_dict and reference_dict.split_dict[korean]:
        return reference_dict.split_dict[korean][0][0]

    # Check whole dict
    if korean in reference_dict.whole_dict and reference_dict.whole_dict[korean]:
        return reference_dict.whole_dict[korean][0][0]

    return None


def _get_main_translation(korean: str, dictionary: Dictionary) -> Tuple[Optional[str], str]:
    """Get main translation and StringID for Korean text."""
    # Check split dict
    if korean in dictionary.split_dict and dictionary.split_dict[korean]:
        fr, stringid = dictionary.split_dict[korean][0]
        return fr, stringid

    # Check whole dict
    if korean in dictionary.whole_dict and dictionary.whole_dict[korean]:
        fr, stringid = dictionary.whole_dict[korean][0]
        return fr, stringid

    return None, ""


def format_search_results(
    results: List[SearchResult],
    include_reference: bool = False,
    include_stringid: bool = False
) -> str:
    """
    Format search results for display.

    Args:
        results: List of SearchResult objects
        include_reference: Whether to include reference translations
        include_stringid: Whether to include StringIDs

    Returns:
        Formatted string
    """
    lines = []

    for result in results:
        lines.append(result.korean)
        lines.append(result.translation)

        if include_reference and result.reference:
            lines.append(result.reference)

        if include_stringid and result.string_id:
            lines.append(f"[{result.string_id}]")

        lines.append("")  # Blank line between results

    return "\n".join(lines)
