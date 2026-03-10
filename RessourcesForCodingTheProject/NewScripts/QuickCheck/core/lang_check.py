"""
LANG CHECK Module

Detects text in the wrong language using two layers:
  Layer 1: Unicode script check (fast, deterministic) — catches completely wrong scripts
  Layer 2: fast-langdetect statistical check — distinguishes same-script languages
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.xml_parser import parse_file
from utils.unicode_utils import compute_script_ratios, strip_codes_and_markup, is_numbers_only

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# fast-langdetect (optional — graceful degradation if unavailable)
# ---------------------------------------------------------------------------

try:
    from fast_langdetect import detect as _fl_detect
    _HAS_FASTLANG = True
    # Use 'lite' model (lid.176.ftz, 917KB, bundled with package)
    # No internet download needed — fully offline safe
    _FL_MODEL = "lite"
except ImportError:
    _HAS_FASTLANG = False
    _FL_MODEL = None
    logger.warning("fast-langdetect not available — LANG CHECK will use script detection only")


# ---------------------------------------------------------------------------
# Language code mapping: our codes → BCP-47
# ---------------------------------------------------------------------------

_OUR_TO_BCP47: Dict[str, str] = {
    "ENG": "en",
    "FRE": "fr",
    "GER": "de",
    "ITA": "it",
    "POL": "pl",
    "POR-BR": "pt",
    "SPA-ES": "es",
    "SPA-MX": "es",
    "TUR": "tr",
    "RUS": "ru",
    "JPN": "ja",
    "ZHO-CN": "zh",
    "ZHO-TW": "zh",
    "KOR": "ko",
}

# Expected dominant script per language
_EXPECTED_SCRIPT: Dict[str, str] = {
    "ENG": "Latin", "FRE": "Latin", "GER": "Latin", "ITA": "Latin",
    "POL": "Latin", "POR-BR": "Latin", "SPA-ES": "Latin", "SPA-MX": "Latin",
    "TUR": "Latin",
    "RUS": "Cyrillic",
    "JPN": "CJK",      # JPN uses CJK + Hiragana + Katakana
    "ZHO-CN": "CJK", "ZHO-TW": "CJK",
    "KOR": "Hangul",
}

# Languages where statistical detection is useful (same-script disambiguation)
_STATISTICAL_LANGS = {
    "ENG", "FRE", "GER", "ITA", "POL", "POR-BR", "SPA-ES", "SPA-MX", "TUR",
    "JPN", "ZHO-CN", "ZHO-TW", "KOR",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LangIssue:
    """A single wrong-language detection."""
    string_id: str
    str_origin: str
    str_text: str
    expected_lang: str
    detected_lang: str
    confidence: float
    detection_method: str   # "Script" or "Statistical"
    details: str


# ---------------------------------------------------------------------------
# Layer 1: Unicode script check
# ---------------------------------------------------------------------------

def _check_script(text: str, expected_lang: str) -> Optional[LangIssue]:
    """Check if text has the wrong Unicode script for the expected language.

    Returns a LangIssue if wrong script detected, None otherwise.
    """
    ratios = compute_script_ratios(text)
    if not ratios:
        return None

    expected_script = _EXPECTED_SCRIPT.get(expected_lang)
    if not expected_script:
        return None

    expected_ratio = ratios.get(expected_script, 0.0)

    if expected_lang == "KOR":
        # Korean: flag if 0% Hangul and >50% Latin
        latin_ratio = ratios.get("Latin", 0.0)
        if expected_ratio == 0.0 and latin_ratio > 0.5:
            return LangIssue(
                string_id="", str_origin="", str_text="",
                expected_lang=expected_lang,
                detected_lang="Latin script",
                confidence=1.0,
                detection_method="Script",
                details=f"No Hangul found, {latin_ratio:.0%} Latin characters",
            )

    elif expected_lang == "RUS":
        # Russian: flag if 0% Cyrillic and >50% Latin
        latin_ratio = ratios.get("Latin", 0.0)
        if expected_ratio == 0.0 and latin_ratio > 0.5:
            return LangIssue(
                string_id="", str_origin="", str_text="",
                expected_lang=expected_lang,
                detected_lang="Latin script",
                confidence=1.0,
                detection_method="Script",
                details=f"No Cyrillic found, {latin_ratio:.0%} Latin characters",
            )

    elif expected_lang == "JPN":
        # Japanese: should have Hiragana OR Katakana OR CJK
        jpn_ratio = (ratios.get("CJK", 0.0)
                     + ratios.get("Hiragana", 0.0)
                     + ratios.get("Katakana", 0.0))
        latin_ratio = ratios.get("Latin", 0.0)
        hangul_ratio = ratios.get("Hangul", 0.0)
        if jpn_ratio == 0.0 and (latin_ratio > 0.5 or hangul_ratio > 0.5):
            dominant = "Latin" if latin_ratio > hangul_ratio else "Hangul"
            return LangIssue(
                string_id="", str_origin="", str_text="",
                expected_lang=expected_lang,
                detected_lang=f"{dominant} script",
                confidence=1.0,
                detection_method="Script",
                details=f"No CJK/Hiragana/Katakana found, dominant script: {dominant}",
            )

    elif expected_lang in ("ZHO-CN", "ZHO-TW"):
        # Chinese: should have CJK
        cjk_ratio = ratios.get("CJK", 0.0)
        latin_ratio = ratios.get("Latin", 0.0)
        hangul_ratio = ratios.get("Hangul", 0.0)
        if cjk_ratio == 0.0 and (latin_ratio > 0.5 or hangul_ratio > 0.5):
            dominant = "Latin" if latin_ratio > hangul_ratio else "Hangul"
            return LangIssue(
                string_id="", str_origin="", str_text="",
                expected_lang=expected_lang,
                detected_lang=f"{dominant} script",
                confidence=1.0,
                detection_method="Script",
                details=f"No CJK found, dominant script: {dominant}",
            )

    elif expected_script == "Latin":
        # Latin-script languages: flag if dominant script is non-Latin
        hangul_ratio = ratios.get("Hangul", 0.0)
        cjk_ratio = ratios.get("CJK", 0.0)
        cyrillic_ratio = ratios.get("Cyrillic", 0.0)
        wrong_ratio = hangul_ratio + cjk_ratio + cyrillic_ratio
        if wrong_ratio > 0.5:
            parts = []
            if hangul_ratio > 0.1:
                parts.append(f"Hangul {hangul_ratio:.0%}")
            if cjk_ratio > 0.1:
                parts.append(f"CJK {cjk_ratio:.0%}")
            if cyrillic_ratio > 0.1:
                parts.append(f"Cyrillic {cyrillic_ratio:.0%}")
            return LangIssue(
                string_id="", str_origin="", str_text="",
                expected_lang=expected_lang,
                detected_lang="Non-Latin script",
                confidence=1.0,
                detection_method="Script",
                details=f"Expected Latin, found: {', '.join(parts)}",
            )

    return None


# ---------------------------------------------------------------------------
# Layer 2: Statistical language detection
# ---------------------------------------------------------------------------

def _check_statistical(text: str, expected_lang: str, confidence_threshold: float) -> Optional[LangIssue]:
    """Use fast-langdetect to check if text is in the wrong language.

    Returns a LangIssue if wrong language detected with sufficient confidence.
    """
    if not _HAS_FASTLANG:
        return None

    expected_bcp47 = _OUR_TO_BCP47.get(expected_lang)
    if not expected_bcp47:
        return None

    # SPA-ES and SPA-MX both map to "es" — skip cross-check between them
    # (handled implicitly: both expect "es")

    try:
        result = _fl_detect(text, model=_FL_MODEL)
    except Exception as exc:
        logger.debug("fast-langdetect failed on text (len=%d): %s", len(text), exc)
        return None

    if not result:
        return None

    # detect() returns list of dicts: [{"lang": "en", "score": 0.97}]
    top = result[0] if isinstance(result, list) else result
    if not isinstance(top, dict) or "lang" not in top:
        return None

    detected_lang = top["lang"]
    confidence = top.get("score", 0.0)

    if confidence < confidence_threshold:
        return None

    # Compare: normalize both to base language for comparison
    detected_base = detected_lang.split("-")[0] if "-" in detected_lang else detected_lang
    expected_base = expected_bcp47.split("-")[0] if "-" in expected_bcp47 else expected_bcp47

    if detected_base == expected_base:
        return None  # Matches expected

    return LangIssue(
        string_id="", str_origin="", str_text="",
        expected_lang=expected_lang,
        detected_lang=detected_lang,
        confidence=confidence,
        detection_method="Statistical",
        details=f"Expected {expected_bcp47}, detected {detected_lang} (confidence: {confidence:.2f})",
    )


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def _run_lang_check_single(
    lang: str,
    files: List[str],
    min_text_length: int,
    confidence_threshold: float,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[LangIssue]:
    """Run language detection on a single language's files."""
    issues: List[LangIssue] = []

    # Parse all files
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
        progress_callback(f"[{lang}] {len(all_entries)} entries loaded, checking...")

    use_statistical = lang in _STATISTICAL_LANGS and _HAS_FASTLANG

    for entry in all_entries:
        text = entry.str
        if not text:
            continue

        # Clean text
        cleaned = strip_codes_and_markup(text)
        if not cleaned or is_numbers_only(cleaned):
            continue

        # Layer 1: Script check (always, even for short strings)
        script_issue = _check_script(cleaned, lang)
        if script_issue:
            script_issue.string_id = entry.string_id
            script_issue.str_origin = entry.str_origin
            script_issue.str_text = text
            issues.append(script_issue)
            continue  # Skip Layer 2 if script already wrong

        # Layer 2: Statistical check (only for longer strings)
        if use_statistical and len(cleaned) >= min_text_length:
            stat_issue = _check_statistical(cleaned, lang, confidence_threshold)
            if stat_issue:
                stat_issue.string_id = entry.string_id
                stat_issue.str_origin = entry.str_origin
                stat_issue.str_text = text
                issues.append(stat_issue)

    return issues


def run_lang_check_all_languages(
    lang_files: Dict[str, List[Path]],
    output_dir: Path,
    min_text_length: int = 8,
    confidence_threshold: float = 0.7,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """Run language detection on all selected languages.

    Returns {lang: issue_count}.
    """
    from utils.excel_writer import write_lang_check_excel

    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}
    languages = sorted(lang_files.keys())
    total = len(languages)

    for idx, lang in enumerate(languages, start=1):
        if lang not in _OUR_TO_BCP47 and lang not in _EXPECTED_SCRIPT:
            if progress_callback:
                progress_callback(f"LANG CHECK {lang}: skipped (no mapping)")
            results[lang] = 0
            continue

        if progress_callback:
            progress_callback(f"LANG CHECK {lang} ({idx}/{total})...")

        files = [str(p) for p in lang_files[lang]]
        issues = _run_lang_check_single(
            lang=lang,
            files=files,
            min_text_length=min_text_length,
            confidence_threshold=confidence_threshold,
            progress_callback=progress_callback,
        )

        output_path = output_dir / f"LangCheck_{lang}.xlsx"
        ok = write_lang_check_excel(issues, str(output_path), lang_code=lang)
        results[lang] = len(issues)

        if progress_callback:
            if ok:
                progress_callback(f"LANG CHECK {lang}: {len(issues)} issues → {output_path.name}")
            else:
                progress_callback(f"LANG CHECK {lang}: ERROR writing {output_path.name}")

    return results
