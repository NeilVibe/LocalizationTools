"""Pure path-based filtering logic – no GUI dependencies."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def precompute_path_filter(
    selected_paths: list[str],
) -> tuple[tuple[str, ...], frozenset[str]]:
    """Split *selected_paths* into folder prefixes and exact file paths.

    Returns ``(folder_prefixes, file_set)`` where both are lowercased and
    ``/``-normalized.  Folder prefixes include a trailing ``/``.
    """
    prefixes: list[str] = []
    files: list[str] = []

    for p in selected_paths:
        norm = p.replace("\\", "/").lower()
        if norm.endswith(".xml"):
            files.append(norm)
        else:
            # Ensure trailing / for unambiguous prefix matching
            if not norm.endswith("/"):
                norm += "/"
            prefixes.append(norm)

    return tuple(prefixes), frozenset(files)


def filter_entries_by_path(
    entries: list[dict],
    path_map: dict[str, str],
    prefixes: tuple[str, ...],
    files: frozenset[str],
) -> list[dict]:
    """Return entries whose SID maps to a selected path.

    * If *prefixes* and *files* are both empty, returns *entries* unchanged.
    * SIDs not found in *path_map* are excluded (cannot confirm location).
    """
    if not prefixes and not files:
        return entries

    if not path_map:
        return entries

    result: list[dict] = []
    for entry in entries:
        sid = entry.get("string_id", "")
        if not sid:
            continue
        rel = path_map.get(sid.lower())
        if not rel:
            continue
        rel_norm = rel.replace("\\", "/").lower()
        # Check exact file match
        if files and rel_norm in files:
            result.append(entry)
            continue
        # Check folder prefix match
        if prefixes and any(rel_norm.startswith(p) for p in prefixes):
            result.append(entry)

    return result
