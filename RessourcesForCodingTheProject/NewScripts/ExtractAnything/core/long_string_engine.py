"""Long String engine – extract LocStr entries above a visible-character threshold."""

import logging
from pathlib import Path

import config
from . import xml_parser, input_parser
from .text_utils import visible_char_count

logger = logging.getLogger(__name__)


def extract_long_strings(
    entries: list[dict],
    *,
    min_chars: int = 200,
    category_map: dict[str, str] | None = None,
    subfolder_map: dict[str, str] | None = None,
    log_fn=None,
) -> list[dict]:
    """Filter entries to SCRIPT-type whose Str exceeds *min_chars*.

    Excludes entries in NarrationDialog subfolder.
    Returns entries enriched with ``char_count``.
    """
    result: list[dict] = []

    for e in entries:
        sv = e.get("str_value", "")
        if not sv:
            continue

        sid_lower = e["string_id"].lower()

        # Category filter: SCRIPT only
        if category_map:
            cat = category_map.get(sid_lower, "")
            if cat not in config.SCRIPT_CATEGORIES:
                continue

        # Subfolder exclusion: NarrationDialog
        if subfolder_map:
            sub = subfolder_map.get(sid_lower, "").lower()
            if sub in config.EXCLUDE_SUBFOLDERS:
                continue

        count = visible_char_count(sv)
        if count >= min_chars:
            entry = dict(e)
            entry["char_count"] = count
            result.append(entry)

    # Sort descending by char_count
    result.sort(key=lambda x: x["char_count"], reverse=True)

    if log_fn:
        log_fn(f"  Found {len(result)} entries >= {min_chars} chars")

    return result


def extract_long_strings_folder(
    source_folder: Path,
    *,
    min_chars: int = 200,
    category_map: dict[str, str] | None = None,
    subfolder_map: dict[str, str] | None = None,
    log_fn=None,
    progress_fn=None,
) -> dict[str, list[dict]]:
    """Extract long strings from all XML/Excel in *source_folder*.

    Returns ``{LANG: [entries_with_char_count]}``.
    """
    # Split progress: parsing=0-60%, filtering=60-100%
    parse_progress = (lambda v: progress_fn(v * 0.6)) if progress_fn else None
    by_lang = input_parser.parse_input_folder(
        source_folder, log_fn=log_fn, progress_fn=parse_progress,
    )
    result: dict[str, list[dict]] = {}

    langs = sorted(by_lang)
    for i, lang in enumerate(langs, 1):
        if progress_fn:
            progress_fn(60 + (i * 40 / max(len(langs), 1)))
        if log_fn:
            log_fn(f"Filtering {lang} ({len(by_lang[lang]):,} entries)...")
        extracted = extract_long_strings(
            by_lang[lang],
            min_chars=min_chars,
            category_map=category_map,
            subfolder_map=subfolder_map,
            log_fn=log_fn,
        )
        if extracted:
            result[lang] = extracted

    return result
