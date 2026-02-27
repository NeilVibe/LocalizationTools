"""No-Voice engine – extract SCRIPT LocStr entries without SoundEventName."""

import logging
from pathlib import Path

from .. import config
from . import input_parser

logger = logging.getLogger(__name__)


def extract_novoice(
    entries: list[dict],
    *,
    category_map: dict[str, str],
    voiced_sids: set[str],
    log_fn=None,
) -> tuple[list[dict], int]:
    """Filter entries to SCRIPT-type that have no voice.

    Returns ``(extracted_entries, orphan_count)``.
    Orphans = entries not found in the EXPORT index at all.
    """
    result: list[dict] = []
    orphans = 0

    for e in entries:
        sid_lower = e["string_id"].lower()

        cat = category_map.get(sid_lower, "")
        if not cat:
            orphans += 1
            continue

        if cat not in config.SCRIPT_CATEGORIES:
            continue

        if sid_lower in voiced_sids:
            continue

        result.append(e)

    # Sort ascending by StringID
    result.sort(key=lambda x: x["string_id"].lower())

    if log_fn:
        log_fn(f"  Found {len(result)} no-voice entries ({orphans} orphans skipped)")

    return result, orphans


def extract_novoice_folder(
    source_folder: Path,
    *,
    category_map: dict[str, str],
    voiced_sids: set[str],
    log_fn=None,
    progress_fn=None,
) -> dict[str, list[dict]]:
    """Extract no-voice entries from all XML/Excel in *source_folder*.

    Returns ``{LANG: [entries]}``.
    """
    # Split progress: parsing=0-60%, filtering=60-100%
    parse_prog = (lambda v: progress_fn(v * 0.6)) if progress_fn else None
    by_lang = input_parser.parse_input_folder(
        source_folder, log_fn=log_fn, progress_fn=parse_prog,
    )
    result: dict[str, list[dict]] = {}

    langs = sorted(by_lang)
    for i, lang in enumerate(langs, 1):
        if progress_fn:
            progress_fn(60 + (i * 40 / max(len(langs), 1)))
        if log_fn:
            log_fn(f"Filtering {lang} ({len(by_lang[lang]):,} entries)...")
        extracted, _ = extract_novoice(
            by_lang[lang],
            category_map=category_map,
            voiced_sids=voiced_sids,
            log_fn=log_fn,
        )
        if extracted:
            result[lang] = extracted

    return result
