"""
Unique Key Generator
====================
Three-level unique key system for reliable translation matching.

Level 1: StrOrigin + StringId (most reliable - both match)
Level 2: StringId only (when StrOrigin changed but StringId exists)
Level 3: StrOrigin + Filename + Adjacent Nodes (context-aware, for when both changed)
"""

import hashlib
from typing import Optional


def _normalize_text(text: str) -> str:
    """
    Normalize text for consistent hashing.

    - Strip whitespace
    - Normalize unicode
    - Convert to lowercase for comparison
    """
    if not text:
        return ""
    # Strip and normalize whitespace
    return " ".join(text.strip().split())


def _sha256_hash(content: str) -> str:
    """Generate SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_level1_key(str_origin: str, string_id: str) -> str:
    """
    Level 1: StrOrigin + StringId combined key.

    Most reliable match - both the Korean text AND the ID match.
    This is the primary lookup key.

    Args:
        str_origin: Korean original text (StrOrigin attribute)
        string_id: String ID (StringId attribute)

    Returns:
        SHA256 hash of normalized "origin|id"
    """
    normalized_origin = _normalize_text(str_origin)
    normalized_id = string_id.strip() if string_id else ""

    combined = f"{normalized_origin}|{normalized_id}"
    return _sha256_hash(combined)


def generate_level2_key(string_id: str) -> str:
    """
    Level 2: StringId only.

    Used when StrOrigin changed but StringId still exists.
    May return multiple matches if ID is reused across files.

    Args:
        string_id: String ID (StringId attribute)

    Returns:
        Normalized string ID (not hashed, used as direct lookup)
    """
    return string_id.strip() if string_id else ""


def generate_level3_key(
    str_origin: str,
    filename: str,
    prev_origin: Optional[str] = None,
    prev_id: Optional[str] = None,
    next_origin: Optional[str] = None,
    next_id: Optional[str] = None
) -> str:
    """
    Level 3: Context-aware key with adjacent nodes.

    For string B at position N:
    - Previous neighbor A is at position N-1
    - Next neighbor C is at position N+1
    - Key = hash(StrOrigin_B, Filename, context_A, context_C)

    If neighbors match, confirms correct position even with changed IDs.

    Args:
        str_origin: Korean original text of THIS entry
        filename: XML filename (for disambiguation)
        prev_origin: StrOrigin of previous entry (N-1)
        prev_id: StringId of previous entry (N-1)
        next_origin: StrOrigin of next entry (N+1)
        next_id: StringId of next entry (N+1)

    Returns:
        SHA256 hash of combined context
    """
    # Normalize all inputs
    norm_origin = _normalize_text(str_origin)
    norm_filename = filename.lower().strip() if filename else ""

    # Build context strings for neighbors
    prev_context = ""
    if prev_origin or prev_id:
        prev_context = f"{_normalize_text(prev_origin or '')}|{(prev_id or '').strip()}"

    next_context = ""
    if next_origin or next_id:
        next_context = f"{_normalize_text(next_origin or '')}|{(next_id or '').strip()}"

    # Combine all elements
    combined = f"{norm_origin}||{norm_filename}||{prev_context}||{next_context}"
    return _sha256_hash(combined)


def generate_all_keys(
    str_origin: str,
    string_id: str,
    filename: str,
    prev_origin: Optional[str] = None,
    prev_id: Optional[str] = None,
    next_origin: Optional[str] = None,
    next_id: Optional[str] = None
) -> dict:
    """
    Generate all three key levels for an entry.

    Convenience function that returns all keys at once.

    Args:
        str_origin: Korean original text (StrOrigin attribute)
        string_id: String ID (StringId attribute)
        filename: XML filename
        prev_origin: StrOrigin of previous entry
        prev_id: StringId of previous entry
        next_origin: StrOrigin of next entry
        next_id: StringId of next entry

    Returns:
        dict with keys: level1, level2, level3
    """
    return {
        "level1": generate_level1_key(str_origin, string_id),
        "level2": generate_level2_key(string_id),
        "level3": generate_level3_key(
            str_origin, filename,
            prev_origin, prev_id,
            next_origin, next_id
        )
    }
