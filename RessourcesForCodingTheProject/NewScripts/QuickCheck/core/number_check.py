"""
NUMBER CHECK Module — Two-Pass Numeric Consistency

Pass 1 (digit-to-digit):
  - Only triggers if SOURCE (Korean) has at least one digit
  - Extract digits from both source and target
  - Compare as multisets — if equal, PASS

Pass 2 (smart reconciliation — only on mismatches):
  - For each "missing" digit in target, check if the word/Roman form exists
    (e.g. source has 1 but target has "one" or "I" → not an issue)
  - For each "extra" digit in target, check if source has the word form
  - Supports: number words (10 languages), Roman numerals (I–L),
    multipliers (10배, x10), ordinal suffixes (1st, 2nd)
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.xml_parser import parse_file

logger = logging.getLogger(__name__)

# =============================================================================
# Identifier masking (skip code-like tokens)
# =============================================================================

# Unicode-aware: catches 벤치마크_0002 AND Benchmark_0002
_RE_UNDERSCORE_ID = re.compile(r'[\w][\w]*_[\w]+', re.UNICODE)
_RE_VERSION = re.compile(r'\bv\d+(?:\.\d+)+\b', re.IGNORECASE)
_RE_HEX = re.compile(r'(?:0x|#)[0-9a-fA-F]{2,}')

# Format placeholders — {0}, {1}, {0:d}, {count}, %d, %s, %1$s, %02d, %%
_RE_FORMAT_BRACE = re.compile(r'\{[^}]*\}')
_RE_FORMAT_PERCENT = re.compile(r'%(?:%|\d*\$?[dsf]|\d*\.\d*[dsf]|0\d+[dsf])')

# Rich-text / markup tags with numbers — <size=14>, <color=#FF>, <sprite=3>
_RE_RICH_TAG = re.compile(r'<[^>]*=\s*[^>]*>', re.IGNORECASE)

# File extensions with numeric-like names — icon_01.png, sound.mp3
_RE_FILE_EXT = re.compile(r'[\w.-]+\.(?:png|jpg|jpeg|gif|bmp|mp3|wav|ogg|mp4|avi|fbx|prefab)\b',
                          re.IGNORECASE)

# Dot-separated identifiers — item.001, quest.013
_RE_DOT_ID = re.compile(r'\b[a-zA-Z]\w*\.\d{2,}\b')

# CamelCase/PascalCase identifiers ending with digits — Item0002, NPC001, Quest013
_RE_CAMEL_ID = re.compile(r'\b[A-Z][a-zA-Z]+\d{2,}\b')

# =============================================================================
# Multiplier patterns — normalise x10, 10x, 10배 → just the number
# =============================================================================

_RE_X_PREFIX = re.compile(r'\bx(\d+)\b', re.IGNORECASE)
_RE_X_SUFFIX = re.compile(r'\b(\d+)x\b', re.IGNORECASE)
_RE_BAE_SUFFIX = re.compile(r'(\d+)배')

# =============================================================================
# Ordinal suffixes: 1st, 2nd, 3rd, 4th → just the digit
# =============================================================================

_RE_ORDINAL_SUFFIX = re.compile(r'\b(\d+)(?:st|nd|rd|th)\b', re.IGNORECASE)

# =============================================================================
# Digit extraction
# =============================================================================

_RE_NUMBER = re.compile(
    r'(?:\d{1,3}(?:,\d{3})+|\d+)'
    r'(?:\.\d+)?'
)


def _mask_and_normalise(text: str) -> str:
    """Mask identifiers + normalise multipliers/ordinals. Returns cleaned text."""
    t = text
    # --- Layer 1: Code-like tokens (mask BEFORE number extraction) ---
    t = _RE_FORMAT_BRACE.sub(' ', t)    # {0}, {count}, {0:d}
    t = _RE_FORMAT_PERCENT.sub(' ', t)  # %d, %1$s, %02d
    t = _RE_RICH_TAG.sub(' ', t)        # <size=14>, <color=#FF>
    t = _RE_FILE_EXT.sub(' ', t)        # icon_01.png, sound.mp3
    t = _RE_DOT_ID.sub(' ', t)          # item.001, quest.013
    t = _RE_CAMEL_ID.sub(' ', t)        # Item0002, NPC001
    t = _RE_UNDERSCORE_ID.sub(' ', t)   # 벤치마크_0002, Benchmark_0002
    t = _RE_VERSION.sub(' ', t)         # v1.2.3
    t = _RE_HEX.sub(' ', t)            # 0xFF, #FF00
    # --- Layer 2: Normalise multipliers/ordinals (keep the number) ---
    t = _RE_X_PREFIX.sub(r' \1 ', t)
    t = _RE_X_SUFFIX.sub(r' \1 ', t)
    t = _RE_BAE_SUFFIX.sub(r' \1 ', t)
    t = _RE_ORDINAL_SUFFIX.sub(r' \1 ', t)
    return t


def _shared_token_mask(source: str, target: str) -> tuple:
    """Nuclear false-positive killer: find tokens that appear identically in BOTH
    source and target (e.g. code IDs, placeholders). Mask them from both before
    number extraction so they never cause mismatches.

    Returns (masked_source, masked_target).
    """
    # Extract all tokens that contain digits
    re_digit_token = re.compile(r'(?:[\w.]+\d[\w.]*|\d[\w.]+)', re.UNICODE)
    src_tokens = set(re_digit_token.findall(source))
    tgt_tokens = set(re_digit_token.findall(target))
    shared = src_tokens & tgt_tokens
    if not shared:
        return source, target
    # Mask shared tokens from both (longest first to avoid partial matches)
    ms, mt = source, target
    for token in sorted(shared, key=len, reverse=True):
        ms = ms.replace(token, ' ')
        mt = mt.replace(token, ' ')
    return ms, mt


def _normalise_number(raw: str) -> str:
    """Strip commas, leading zeros, trailing decimal zeros."""
    s = raw.replace(',', '')
    if '.' in s:
        int_part, dec_part = s.split('.', 1)
        int_part = int_part.lstrip('0') or '0'
        dec_part = dec_part.rstrip('0')
        return f"{int_part}.{dec_part}" if dec_part else int_part
    return s.lstrip('0') or '0'


def _extract_digits(text: str) -> Counter:
    """Extract digit-based numbers from text (after masking). No word conversion."""
    if not text:
        return Counter()
    cleaned = _mask_and_normalise(text)
    return Counter(_normalise_number(m) for m in _RE_NUMBER.findall(cleaned))


def _safe_sort_key(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0


# =============================================================================
# Pass 2: Word/Roman equivalence tables (digit → word forms)
# Used ONLY to reconcile mismatches, never for primary extraction.
# =============================================================================

# digit → list of equivalent word forms (all lowercase)
_WORD_EQUIVALENTS: Dict[str, List[str]] = {
    '1': ['one', 'first', 'un', 'une', 'eins', 'ein', 'eine', 'uno', 'una',
          'um', 'uma', 'один', 'одна', 'одно', 'premier', 'première',
          'primero', 'primera', 'primo', 'prima', 'primeiro', 'primeira',
          'erste', 'erster', 'первый', 'первая',
          '하나', '한'],
    '2': ['two', 'second', 'deux', 'zwei', 'dos', 'due', 'dois', 'duas',
          'два', 'две', 'deuxième', 'segundo', 'segunda', 'secondo', 'seconda',
          'zweite', 'второй', 'вторая',
          '둘', '두'],
    '3': ['three', 'third', 'trois', 'drei', 'tres', 'tre', 'três',
          'три', 'troisième', 'tercero', 'tercera', 'terzo', 'terceiro',
          'dritte', 'третий', 'третья',
          '셋', '세'],
    '4': ['four', 'fourth', 'quatre', 'vier', 'cuatro', 'quattro', 'quatro',
          'четыре', 'quatrième', 'cuarto', 'vierte', 'четвёртый',
          '넷', '네'],
    '5': ['five', 'fifth', 'cinq', 'fünf', 'cinco', 'cinque',
          'пять', 'cinquième', 'quinto', 'fünfte', 'пятый',
          '다섯'],
    '6': ['six', 'sixth', 'sechs', 'seis', 'sei', 'шесть',
          'sixième', 'sexto', 'sechste', 'шестой',
          '여섯'],
    '7': ['seven', 'seventh', 'sept', 'sieben', 'siete', 'sette', 'sete',
          'семь', 'septième', 'séptimo', 'settimo', 'sétimo', 'siebte', 'седьмой',
          '일곱'],
    '8': ['eight', 'eighth', 'huit', 'acht', 'ocho', 'otto', 'oito',
          'восемь', 'huitième', 'octavo', 'ottavo', 'oitavo', 'achte', 'восьмой',
          '여덟'],
    '9': ['nine', 'ninth', 'neuf', 'neun', 'nueve', 'nove',
          'девять', 'neuvième', 'noveno', 'nono', 'neunte', 'девятый',
          '아홉'],
    '10': ['ten', 'tenth', 'dix', 'zehn', 'diez', 'dieci', 'dez',
           'десять', 'dixième', 'décimo', 'decimo', 'zehnte', 'десятый',
           '열'],
}

# Build reverse lookup: word → digit (for quick checks)
_WORD_TO_DIGIT: Dict[str, str] = {}
for _d, _words in _WORD_EQUIVALENTS.items():
    for _w in _words:
        _WORD_TO_DIGIT[_w.lower()] = _d

# Roman numerals I–L
_ROMAN_MAP = {
    'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5',
    'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'X': '10',
    'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15',
    'XVI': '16', 'XVII': '17', 'XVIII': '18', 'XIX': '19', 'XX': '20',
    'XXI': '21', 'XXII': '22', 'XXIII': '23', 'XXIV': '24', 'XXV': '25',
    'XXVI': '26', 'XXVII': '27', 'XXVIII': '28', 'XXIX': '29', 'XXX': '30',
    'XXXI': '31', 'XXXII': '32', 'XXXIII': '33', 'XXXIV': '34', 'XXXV': '35',
    'XXXVI': '36', 'XXXVII': '37', 'XXXVIII': '38', 'XXXIX': '39', 'XL': '40',
    'XLI': '41', 'XLII': '42', 'XLIII': '43', 'XLIV': '44', 'XLV': '45',
    'XLVI': '46', 'XLVII': '47', 'XLVIII': '48', 'XLIX': '49', 'L': '50',
}

# Roman numeral regex (multi-char only — single I handled separately)
_RE_ROMAN = re.compile(
    r'\b((?:XL(?:IX|VIII|VII|VI|V|IV|III|II|I)?)|(?:XXX(?:IX|VIII|VII|VI|V|IV|III|II|I)?)'
    r'|(?:XX(?:IX|VIII|VII|VI|V|IV|III|II|I)?)|(?:X(?:IX|VIII|VII|VI|V|IV|III|II|I)?)'
    r'|(?:IX|VIII|VII|VI|V|IV|III|II))\b'
)


def _text_has_word_for_digit(text: str, digit: str) -> bool:
    """Check if text contains a word/Roman equivalent of the given digit.

    Used in Pass 2 to reconcile mismatches.
    E.g. digit='1', text='Need one item' → True (because 'one' = 1)
    E.g. digit='3', text='Phase III' → True (because III = 3)
    """
    # Check word equivalents
    word_forms = _WORD_EQUIVALENTS.get(digit, [])
    text_lower = text.lower()
    for word in word_forms:
        # Korean words: simple contains (multi-char are distinctive)
        if any('\uac00' <= c <= '\ud7af' for c in word):
            if word in text_lower:
                return True
        else:
            # Latin/Cyrillic: word boundary match
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                return True

    # Check Roman numerals
    for roman, roman_digit in _ROMAN_MAP.items():
        if roman_digit == digit:
            # Multi-char Roman: word boundary match
            if len(roman) > 1:
                if re.search(r'\b' + roman + r'\b', text):
                    return True
            # Single I: only match if clearly a numeral (after Chapter/Part/etc.)
            elif roman == 'I':
                if re.search(
                    r'(?:chapter|part|phase|level|type|vol|act|stage|tier|no|#)\s+I\b',
                    text, re.IGNORECASE,
                ):
                    return True

    return False


# =============================================================================
# Display helpers
# =============================================================================

def _counter_to_display(c: Counter) -> str:
    items = []
    for num in sorted(c.keys(), key=_safe_sort_key):
        items.extend([num] * c[num])
    return ', '.join(items)


def _counter_diff(a: Counter, b: Counter) -> Counter:
    diff = Counter()
    for key, count in a.items():
        missing = count - b.get(key, 0)
        if missing > 0:
            diff[key] = missing
    return diff


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class NumberIssue:
    string_id: str
    str_origin: str
    str_text: str
    source_numbers: str
    target_numbers: str
    missing_in_target: str
    extra_in_target: str
    category: str = ''


# =============================================================================
# Main engine — Two-Pass
# =============================================================================

def _run_number_check_single(
    lang: str,
    files: List[str],
    progress_callback: Optional[Callable[[str], None]] = None,
    category_index: Optional[Dict[str, str]] = None,
) -> List[NumberIssue]:
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

        # === PASS 0: Shared-token elimination ===
        # Tokens identical in both sides are code artifacts, not translation issues.
        masked_src, masked_tgt = _shared_token_mask(source, target)

        # === PASS 1: Digit-to-digit (source must have digits) ===
        src_nums = _extract_digits(masked_src)
        if not src_nums:
            continue  # No digits in source → skip entirely

        tgt_nums = _extract_digits(masked_tgt)
        if src_nums == tgt_nums:
            continue  # Digits match perfectly → PASS

        # === PASS 2: Smart reconciliation ===
        # Check each "missing" digit — does target have word/Roman form?
        missing_raw = _counter_diff(src_nums, tgt_nums)
        missing_real = Counter()
        for digit, count in missing_raw.items():
            if _text_has_word_for_digit(target, digit):
                continue  # Target has word equivalent → not actually missing
            missing_real[digit] = count

        # Check each "extra" digit — does source have word/Roman form?
        extra_raw = _counter_diff(tgt_nums, src_nums)
        extra_real = Counter()
        for digit, count in extra_raw.items():
            if _text_has_word_for_digit(source, digit):
                continue  # Source has word equivalent → not actually extra
            extra_real[digit] = count

        # After Pass 2, if nothing remains → PASS
        if not missing_real and not extra_real:
            continue

        cat = ''
        if category_index and entry.string_id:
            cat = category_index.get(entry.string_id, '')

        issues.append(NumberIssue(
            string_id=entry.string_id,
            str_origin=source,
            str_text=target,
            source_numbers=_counter_to_display(src_nums),
            target_numbers=_counter_to_display(tgt_nums),
            missing_in_target=_counter_to_display(missing_real) if missing_real else '',
            extra_in_target=_counter_to_display(extra_real) if extra_real else '',
            category=cat,
        ))

    return issues


def run_number_check_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    category_index: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """Run number check on all selected languages. Returns {lang: issue_count}."""
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
            category_index=category_index,
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
