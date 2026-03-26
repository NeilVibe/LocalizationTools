"""
NUMBER CHECK Module

Detects numeric inconsistencies between source (StrOrigin) and target (Str) text.

Algorithm:
  1. Extract all standalone numbers from source text → multiset (Counter)
  2. Extract all standalone numbers from target text → multiset (Counter)
  3. Compare multisets — flag if they differ (missing or extra numbers)

Numbers are normalised: leading zeros stripped, trailing decimal zeros stripped.
Handles integers, decimals, and comma-separated thousands. Hyphens are ignored.
Skips numbers embedded in identifiers (e.g. item_02, stage3).
Uses Counter (multiset) so "10 + 10 = 20" correctly requires two 10s.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.xml_parser import parse_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------------

# Step 1: Mask identifier-like tokens so their embedded digits are ignored.
# Matches: item_02, stage3_clear, v2.0, 0xFF00, quest_01_desc
_RE_IDENTIFIER = re.compile(r'[a-zA-Z_]\w*(?:\.\w+)*')

# Step 2: Extract standalone numbers from cleaned text.
# Matches: 100, 3.5, 1,000, 1,234.56
# Does NOT match negative signs — hyphens are ignored.
_RE_NUMBER = re.compile(
    r'(?:\d{1,3}(?:,\d{3})+|\d+)'  # integer part (with or without commas)
    r'(?:\.\d+)?'            # optional decimal part
)


def _normalise_number(raw: str) -> str:
    """Normalise a raw number string for consistent comparison.

    - Strips commas (thousands separator)
    - Strips leading zeros from integer part
    - Strips trailing zeros from decimal part
    - Returns canonical string form
    """
    s = raw.replace(',', '')

    if '.' in s:
        int_part, dec_part = s.split('.', 1)
        int_part = int_part.lstrip('0') or '0'
        dec_part = dec_part.rstrip('0')
        if dec_part:
            return f"{int_part}.{dec_part}"
        return int_part

    return s.lstrip('0') or '0'


def _safe_sort_key(x: str) -> float:
    """Sort key for normalised number strings, with fallback for edge cases."""
    try:
        return float(x)
    except ValueError:
        return 0.0


def extract_numbers(text: str) -> Counter:
    """Extract all standalone numbers from text, returning a Counter (multiset).

    Identifiers (e.g. item_02, stage3, v2.0) are masked before extraction
    so their embedded digits are not treated as translatable numbers.
    """
    if not text:
        return Counter()
    # Mask identifiers so their digits aren't extracted
    cleaned = _RE_IDENTIFIER.sub(' ', text)
    raw_matches = _RE_NUMBER.findall(cleaned)
    return Counter(_normalise_number(m) for m in raw_matches)


def _counter_to_display(c: Counter) -> str:
    """Convert Counter to display string. Shows duplicates: '10, 10, 20'."""
    items = []
    for num in sorted(c.keys(), key=_safe_sort_key):
        items.extend([num] * c[num])
    return ', '.join(items)


def _counter_diff(a: Counter, b: Counter) -> Counter:
    """Items in a that are missing or under-represented in b."""
    diff = Counter()
    for key, count in a.items():
        missing = count - b.get(key, 0)
        if missing > 0:
            diff[key] = missing
    return diff


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NumberIssue:
    """A single numeric inconsistency between source and target."""
    string_id: str
    str_origin: str
    str_text: str
    source_numbers: str      # comma-separated list of numbers found in source
    target_numbers: str      # comma-separated list of numbers found in target
    missing_in_target: str   # numbers in source but not in target
    extra_in_target: str     # numbers in target but not in source


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def _run_number_check_single(
    lang: str,
    files: List[str],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[NumberIssue]:
    """Run number check on a single language's files."""
    issues: List[NumberIssue] = []

    all_entries = []
    for i, fpath in enumerate(files):
        try:
            entries = parse_file(fpath)
            all_entries.extend(entries)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", fpath, exc)
        if progress_callback and (i + 1) % 5 == 0:
            progress_callback(f"[{lang}] Parsed {i + 1}/{len(files)} files")

    if progress_callback:
        progress_callback(f"[{lang}] {len(all_entries)} entries loaded, checking numbers...")

    for entry in all_entries:
        source = entry.str_origin
        target = entry.str
        if not source or not target:
            continue

        src_nums = extract_numbers(source)
        tgt_nums = extract_numbers(target)

        # Skip entries where neither side has numbers
        if not src_nums and not tgt_nums:
            continue

        # Compare multisets
        if src_nums == tgt_nums:
            continue

        missing = _counter_diff(src_nums, tgt_nums)
        extra = _counter_diff(tgt_nums, src_nums)

        issues.append(NumberIssue(
            string_id=entry.string_id,
            str_origin=source,
            str_text=target,
            source_numbers=_counter_to_display(src_nums),
            target_numbers=_counter_to_display(tgt_nums),
            missing_in_target=_counter_to_display(missing) if missing else '',
            extra_in_target=_counter_to_display(extra) if extra else '',
        ))

    return issues


def run_number_check_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """Run number check on all selected languages.

    Returns {lang: issue_count}.
    """
    from utils.excel_writer import write_number_check_excel

    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}
    languages = sorted(lang_files.keys())
    total = len(languages)

    for idx, lang in enumerate(languages, start=1):
        if progress_callback:
            progress_callback(f"NUM CHECK {lang} ({idx}/{total})...")

        files = [str(p) for p in lang_files[lang]]
        issues = _run_number_check_single(
            lang=lang,
            files=files,
            progress_callback=progress_callback,
        )

        output_path = output_dir / f"NumCheck_{lang}.xlsx"
        ok = write_number_check_excel(issues, str(output_path), lang_code=lang)
        results[lang] = len(issues)

        if progress_callback:
            if ok:
                progress_callback(f"NUM CHECK {lang}: {len(issues)} issues → {output_path.name}")
            else:
                progress_callback(f"NUM CHECK {lang}: ERROR writing {output_path.name}")

    return results
