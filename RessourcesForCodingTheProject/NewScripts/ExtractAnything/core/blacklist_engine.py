"""Blacklist engine – find LocStr entries containing blacklisted terms."""

import logging
from pathlib import Path

from . import input_parser

logger = logging.getLogger(__name__)


def search_blacklist(
    entries: list[dict],
    terms: list[str],
    *,
    log_fn=None,
) -> list[dict]:
    """Search *entries* for any substring match against *terms*.

    Returns one result per (entry, term) match with ``matched_term`` added.
    """
    if not terms:
        return []

    terms_lower = [(t, t.lower()) for t in terms]
    matches: list[dict] = []

    for e in entries:
        sv = e.get("str_value", "")
        if not sv:
            continue
        sv_lower = sv.lower()

        for term_orig, term_low in terms_lower:
            if term_low in sv_lower:
                match = dict(e)
                match["matched_term"] = term_orig
                matches.append(match)

    if log_fn:
        log_fn(f"  {len(matches)} blacklist matches found")

    return matches


def search_blacklist_folder(
    target_folder: Path,
    blacklist: dict[str, list[str]],
    *,
    log_fn=None,
    progress_fn=None,
) -> dict[str, list[dict]]:
    """Search all XML/Excel in *target_folder* per-language against *blacklist*.

    *blacklist* is ``{LANG: [terms]}``.
    Returns ``{LANG: [match_entries]}``.
    """
    # Split progress: parsing=0-60%, searching=60-100%
    parse_prog = (lambda v: progress_fn(v * 0.6)) if progress_fn else None
    by_lang = input_parser.parse_input_folder(
        target_folder, log_fn=log_fn, progress_fn=parse_prog,
    )
    result: dict[str, list[dict]] = {}

    langs = sorted(by_lang)
    for i, lang in enumerate(langs, 1):
        if progress_fn:
            progress_fn(60 + (i * 40 / max(len(langs), 1)))

        terms = blacklist.get(lang, [])
        if not terms:
            if log_fn:
                log_fn(f"  {lang}: no blacklist terms, skipping")
            continue

        if log_fn:
            log_fn(f"Searching {lang} ({len(by_lang[lang]):,} entries, {len(terms)} terms)...")

        matches = search_blacklist(by_lang[lang], terms, log_fn=log_fn)
        if matches:
            result[lang] = matches

    return result
