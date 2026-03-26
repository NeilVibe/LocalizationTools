"""
NUMBER CHECK Module — Smart Numeric Consistency

Detects numeric inconsistencies between source (StrOrigin) and target (Str).

Smart normalisation pipeline (applied before digit extraction):
  1. Mask code identifiers (item_02, quest_desc_03)
  2. Convert multiplier patterns (10배, x10, 10x → leave the number, drop suffix)
  3. Convert Roman numerals I–L (1–50) to digits (standalone only)
  4. Convert number words to digits (per-language: Korean, EN, FR, DE, ES, IT, PT, RU, JPN/ZHO)
  5. Convert ordinal words/suffixes (1st, 2nd, first, second → digits)
  6. Extract remaining digits as multiset (Counter)
  7. Compare source vs target multisets

This dramatically reduces false positives vs naive digit extraction.
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
# Number word dictionaries (value → list of words, case-insensitive)
# =============================================================================

# Korean native (고유어) — used for counting things
_KR_NATIVE = {
    '1': ['하나', '한'], '2': ['둘', '두'], '3': ['셋', '세'],
    '4': ['넷', '네'], '5': ['다섯'], '6': ['여섯'],
    '7': ['일곱'], '8': ['여덟'], '9': ['아홉'], '10': ['열'],
}

# Korean Sino (한자어) — used for dates, money, formal
# NOTE: Single-char Sino-Korean (일,이,삼...) are EXCLUDED because they're
# too ambiguous (일=day/work, 이=this, 사=company, 오=come...).
# Only multi-char compounds would be safe, but those are rare in game text.
_KR_SINO = {}

_EN = {
    '1': ['one', 'first'], '2': ['two', 'second'], '3': ['three', 'third'],
    '4': ['four', 'fourth'], '5': ['five', 'fifth'], '6': ['six', 'sixth'],
    '7': ['seven', 'seventh'], '8': ['eight', 'eighth'], '9': ['nine', 'ninth'],
    '10': ['ten', 'tenth'],
}

_FR = {
    '1': ['un', 'une', 'premier', 'première'], '2': ['deux', 'deuxième'],
    '3': ['trois', 'troisième'], '4': ['quatre', 'quatrième'],
    '5': ['cinq', 'cinquième'], '6': ['six', 'sixième'],
    '7': ['sept', 'septième'], '8': ['huit', 'huitième'],
    '9': ['neuf', 'neuvième'], '10': ['dix', 'dixième'],
}

_DE = {
    '1': ['eins', 'ein', 'eine', 'erste', 'erster', 'erstes'],
    '2': ['zwei', 'zweite'], '3': ['drei', 'dritte'],
    '4': ['vier', 'vierte'], '5': ['fünf', 'fünfte'],
    '6': ['sechs', 'sechste'], '7': ['sieben', 'siebte'],
    '8': ['acht', 'achte'], '9': ['neun', 'neunte'],
    '10': ['zehn', 'zehnte'],
}

_ES = {
    '1': ['uno', 'una', 'primero', 'primera'], '2': ['dos', 'segundo', 'segunda'],
    '3': ['tres', 'tercero', 'tercera'], '4': ['cuatro', 'cuarto'],
    '5': ['cinco', 'quinto'], '6': ['seis', 'sexto'],
    '7': ['siete', 'séptimo'], '8': ['ocho', 'octavo'],
    '9': ['nueve', 'noveno'], '10': ['diez', 'décimo'],
}

_IT = {
    '1': ['uno', 'una', 'primo', 'prima'], '2': ['due', 'secondo', 'seconda'],
    '3': ['tre', 'terzo'], '4': ['quattro', 'quarto'],
    '5': ['cinque', 'quinto'], '6': ['sei', 'sesto'],
    '7': ['sette', 'settimo'], '8': ['otto', 'ottavo'],
    '9': ['nove', 'nono'], '10': ['dieci', 'decimo'],
}

_PT = {
    '1': ['um', 'uma', 'primeiro', 'primeira'], '2': ['dois', 'duas', 'segundo'],
    '3': ['três', 'terceiro'], '4': ['quatro', 'quarto'],
    '5': ['cinco', 'quinto'], '6': ['seis', 'sexto'],
    '7': ['sete', 'sétimo'], '8': ['oito', 'oitavo'],
    '9': ['nove', 'nono'], '10': ['dez', 'décimo'],
}

_RU = {
    '1': ['один', 'одна', 'одно', 'первый', 'первая'],
    '2': ['два', 'две', 'второй', 'вторая'],
    '3': ['три', 'третий', 'третья'], '4': ['четыре', 'четвёртый'],
    '5': ['пять', 'пятый'], '6': ['шесть', 'шестой'],
    '7': ['семь', 'седьмой'], '8': ['восемь', 'восьмой'],
    '9': ['девять', 'девятый'], '10': ['десять', 'десятый'],
}

# CJK numerals (shared by Japanese and Chinese)
_CJK = {
    '1': ['一'], '2': ['二'], '3': ['三'], '4': ['四'], '5': ['五'],
    '6': ['六'], '7': ['七'], '8': ['八'], '9': ['九'], '10': ['十'],
    '100': ['百'], '1000': ['千'], '10000': ['万', '萬'],
}

# Map language codes to word dictionaries (source always gets Korean)
_LANG_WORD_MAPS: Dict[str, List[Dict[str, List[str]]]] = {
    # Source (Korean) always uses Korean native + Sino
    '_SOURCE': [_KR_NATIVE, _KR_SINO, _CJK],
    # Target languages
    'ENG': [_EN], 'FRE': [_FR], 'GER': [_DE],
    'SPA': [_ES], 'SPA-ES': [_ES], 'SPA-MX': [_ES],
    'ITA': [_IT],
    'POR': [_PT], 'POR-BR': [_PT], 'POR-PT': [_PT],
    'RUS': [_RU],
    'JPN': [_CJK], 'ZHO': [_CJK], 'ZHO-CN': [_CJK], 'ZHO-TW': [_CJK],
    'KOR': [_KR_NATIVE, _KR_SINO, _CJK],
}


def _build_word_to_digit(dicts: List[Dict[str, List[str]]]) -> Dict[str, str]:
    """Build a flat word→digit lookup from multiple dictionaries."""
    result = {}
    for d in dicts:
        for digit, words in d.items():
            for w in words:
                result[w.lower()] = digit
    return result


# =============================================================================
# Roman numerals (I–L, i.e. 1–50)
# =============================================================================

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

# Roman numeral regex — matches standalone uppercase Roman numerals
# Requires word boundary on both sides. For single "I", requires context.
_RE_ROMAN = re.compile(
    r'\b((?:XL(?:IX|VIII|VII|VI|V|IV|III|II|I)?)|(?:XXX(?:IX|VIII|VII|VI|V|IV|III|II|I)?)'
    r'|(?:XX(?:IX|VIII|VII|VI|V|IV|III|II|I)?)|(?:X(?:IX|VIII|VII|VI|V|IV|III|II|I)?)'
    r'|(?:IX|VIII|VII|VI|V|IV|III|II))\b'
)

# Context words that make standalone "I" likely a Roman numeral, not pronoun
_ROMAN_I_CONTEXT = re.compile(
    r'(?:chapter|part|phase|level|type|vol|volume|act|stage|tier|grade|rank|class|book|no|#)\s*$',
    re.IGNORECASE,
)


# =============================================================================
# Identifier masking — skip code-like tokens BUT preserve multiplier numbers
# =============================================================================

# Identifiers with underscore: item_02, quest_01_desc (always mask)
_RE_UNDERSCORE_ID = re.compile(r'\b[a-zA-Z_]\w*_\w+\b')

# Version-like: v2.0, v1.3.5 (mask)
_RE_VERSION = re.compile(r'\bv\d+(?:\.\d+)+\b', re.IGNORECASE)

# Hex colors: 0xFF00, #FF0000 (mask)
_RE_HEX = re.compile(r'(?:0x|#)[0-9a-fA-F]{2,}')


# =============================================================================
# Multiplier patterns — normalise x10, 10x, 10배 to just the number
# =============================================================================

# x10, X10 (prefix x)
_RE_X_PREFIX = re.compile(r'\bx(\d+)\b', re.IGNORECASE)
# 10x, 10X (suffix x)
_RE_X_SUFFIX = re.compile(r'\b(\d+)x\b', re.IGNORECASE)
# 10배 (Korean multiplier suffix)
_RE_BAE_SUFFIX = re.compile(r'(\d+)배')


# =============================================================================
# Ordinal suffixes: 1st, 2nd, 3rd, 4th...
# =============================================================================

_RE_ORDINAL_SUFFIX = re.compile(r'\b(\d+)(?:st|nd|rd|th)\b', re.IGNORECASE)


# =============================================================================
# Digit extraction
# =============================================================================

_RE_NUMBER = re.compile(
    r'(?:\d{1,3}(?:,\d{3})+|\d+)'  # integer (with or without commas)
    r'(?:\.\d+)?'                    # optional decimal
)


def _normalise_number(raw: str) -> str:
    """Normalise a raw number string: strip commas, leading zeros, trailing decimal zeros."""
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
    try:
        return float(x)
    except ValueError:
        return 0.0


# =============================================================================
# Smart number extraction (the main pipeline)
# =============================================================================

def extract_numbers(text: str, word_dicts: List[Dict[str, List[str]]] = None) -> Counter:
    """Extract all numbers from text using smart normalisation.

    Pipeline:
      1. Mask identifiers (underscore IDs, versions, hex)
      2. Normalise multipliers (x10 → 10, 10배 → 10)
      3. Normalise ordinal suffixes (1st → 1)
      4. Convert Roman numerals to digits
      5. Convert number words to digits (per-language)
      6. Extract remaining digits as Counter

    Args:
        text: Input text
        word_dicts: List of word→digit dictionaries for this language

    Returns:
        Counter of normalised number strings
    """
    if not text:
        return Counter()

    t = text

    # Step 1: Mask identifiers (replace with spaces to preserve boundaries)
    t = _RE_UNDERSCORE_ID.sub(' ', t)
    t = _RE_VERSION.sub(' ', t)
    t = _RE_HEX.sub(' ', t)

    # Step 2: Normalise multipliers — keep the number, drop the multiplier
    t = _RE_X_PREFIX.sub(r' \1 ', t)
    t = _RE_X_SUFFIX.sub(r' \1 ', t)
    t = _RE_BAE_SUFFIX.sub(r' \1 ', t)

    # Step 3: Normalise ordinal suffixes (1st → 1)
    t = _RE_ORDINAL_SUFFIX.sub(r' \1 ', t)

    # Step 4: Roman numerals (multi-char first, then single I with context)
    def _replace_roman(m):
        val = m.group(1)
        if val in _ROMAN_MAP:
            return f' {_ROMAN_MAP[val]} '
        return m.group(0)

    t = _RE_ROMAN.sub(_replace_roman, t)

    # Handle standalone "I" with context check
    # Look for "Chapter I", "Part I", etc.
    t = re.sub(
        r'(?<=\s)I(?=\s|$|[,.])',
        lambda m: ' 1 ' if _ROMAN_I_CONTEXT.search(t[:m.start()]) else m.group(0),
        t,
    )

    # Step 5: Number words → digits
    if word_dicts:
        word_lookup = _build_word_to_digit(word_dicts)
        # Sort by longest word first to avoid partial matches
        sorted_words = sorted(word_lookup.keys(), key=len, reverse=True)
        for word in sorted_words:
            digit = word_lookup[word]
            # Korean/CJK chars: \b doesn't work — use simple contains match
            # (Korean words like 다섯, 하나, 열 are distinctive enough)
            # Skip single-char CJK ideographs (一, 二...) — ambiguous in context
            has_cjk = any('\u4e00' <= c <= '\u9fff' for c in word)
            has_korean = any('\uac00' <= c <= '\ud7af' for c in word)
            if has_korean or has_cjk:
                if has_cjk and len(word) == 1:
                    continue  # Skip ambiguous single CJK (一, 二, 三...)
                if has_korean and len(word) == 1:
                    # Single-char Korean words (한, 두, 세, 네, 열) need boundaries
                    # to avoid matching inside verbs/compounds (모으세요, 세계, 네가...)
                    # Require not surrounded by other Hangul syllables
                    kr_boundary = re.compile(
                        r'(?<![\uac00-\ud7af])' + re.escape(word) + r'(?![\uac00-\ud7af])'
                    )
                    t = kr_boundary.sub(f' {digit} ', t)
                else:
                    # Longer Korean words (다섯, 여섯, 일곱...) are distinctive
                    t = t.replace(word, f' {digit} ')
            else:
                # Latin/Cyrillic: use \b word boundaries
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                t = pattern.sub(f' {digit} ', t)

    # Step 6: Extract digits
    raw_matches = _RE_NUMBER.findall(t)
    return Counter(_normalise_number(m) for m in raw_matches)


# =============================================================================
# Display helpers
# =============================================================================

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


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class NumberIssue:
    """A single numeric inconsistency between source and target."""
    string_id: str
    str_origin: str
    str_text: str
    source_numbers: str
    target_numbers: str
    missing_in_target: str
    extra_in_target: str


# =============================================================================
# Main engine
# =============================================================================

def _get_word_dicts(lang: str, side: str) -> List[Dict[str, List[str]]]:
    """Get the word dictionaries for a language and side (source/target)."""
    if side == 'source':
        return _LANG_WORD_MAPS.get('_SOURCE', [])
    return _LANG_WORD_MAPS.get(lang, _LANG_WORD_MAPS.get(lang.split('-')[0], [_EN]))


def _run_number_check_single(
    lang: str,
    files: List[str],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[NumberIssue]:
    """Run number check on a single language's files."""
    issues: List[NumberIssue] = []
    src_dicts = _get_word_dicts(lang, 'source')
    tgt_dicts = _get_word_dicts(lang, 'target')

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

        src_nums = extract_numbers(source, src_dicts)
        tgt_nums = extract_numbers(target, tgt_dicts)

        if not src_nums and not tgt_nums:
            continue

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
