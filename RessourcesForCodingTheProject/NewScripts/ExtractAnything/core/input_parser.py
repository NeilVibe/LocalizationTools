"""Unified input parsing – XML or Excel → common entry format."""

import logging
from pathlib import Path

import config
from . import xml_parser, language_utils
from .text_utils import normalize_newlines

logger = logging.getLogger(__name__)

# Default file patterns for folder parsing (rglob doesn't support brace expansion)
_DEFAULT_PATTERNS: tuple[str, ...] = ("*.xml", "*.xlsx")


def parse_xml_entries(
    xml_path: Path,
    language: str = "UNKNOWN",
) -> list[dict]:
    """Parse a languagedata XML file into the common entry format."""
    raw = xml_parser.read_xml_raw(xml_path)
    if raw is None:
        return []

    root = xml_parser.parse_root_from_string(raw)
    elements = xml_parser.iter_locstr(root)
    entries: list[dict] = []

    for elem in elements:
        _, sid = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
        if not sid:
            continue
        _, so = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
        _, sv = xml_parser.get_attr(elem, config.STR_ATTRS)

        # Normalize newlines to canonical <br/> at the entry point —
        # ensures ALL downstream consumers (Excel write, XML write, diff)
        # see consistent format regardless of source XML encoding.
        so = normalize_newlines(so) if so else ""
        sv = normalize_newlines(sv) if sv else ""

        raw_attribs = dict(elem.attrib)

        entries.append({
            "string_id": sid,
            "str_origin": so,
            "str_value": sv,
            "raw_attribs": raw_attribs,
            "language": language,
            "source_file": str(xml_path),
        })

    return entries


def parse_input_file(
    path: Path,
    language: str = "UNKNOWN",
    valid_codes: set[str] | None = None,
    log_fn=None,
) -> tuple[list[dict], str]:
    """Auto-detect XML or Excel and parse to common format.

    Returns ``(entries, detected_language)``.
    """
    suffix = path.suffix.lower()

    if suffix in (".xml",):
        lang = language_utils.extract_language_from_filename(path.name, valid_codes)
        if lang == "UNKNOWN":
            lang = language
        entries = parse_xml_entries(path, language=lang)
        return entries, lang

    if suffix in (".xlsx", ".xls"):
        from .excel_reader import read_entries_from_excel

        lang = language_utils.extract_language_from_filename(path.name, valid_codes)
        if lang == "UNKNOWN":
            lang = language
        entries = read_entries_from_excel(path, language=lang, log_fn=log_fn)
        return entries, lang

    logger.warning("Unsupported file type: %s", path.name)
    return [], language


def parse_input_folder(
    folder: Path,
    *,
    valid_codes: set[str] | None = None,
    file_pattern: str | tuple[str, ...] | None = None,
    log_fn=None,
    progress_fn=None,
) -> dict[str, list[dict]]:
    """Parse all matching files in *folder* -> ``{LANG: [entries]}``.

    Groups by detected language code.

    *file_pattern* defaults to ``_DEFAULT_PATTERNS`` (XML + Excel).
    Pass a single string like ``"*.xml"`` to restrict to one type.

    *progress_fn* is called with a float 0-100.
    *log_fn* is called with ``(msg, tag)`` for per-file feedback.
    """
    result: dict[str, list[dict]] = {}

    patterns = _DEFAULT_PATTERNS if file_pattern is None else (
        (file_pattern,) if isinstance(file_pattern, str) else file_pattern
    )
    pattern_desc = ", ".join(patterns)

    # Multi-glob with dedup (rglob doesn't support brace expansion)
    seen: set[Path] = set()
    files: list[Path] = []
    for pat in patterns:
        for f in folder.rglob(pat):
            if f.is_file() and not f.name.startswith("~$") and f not in seen:
                seen.add(f)
                files.append(f)
    files.sort()

    if not files:
        logger.warning("No %s files in %s", pattern_desc, folder)
        if log_fn:
            log_fn(f"No files matching ({pattern_desc}) found in {folder.name}/", "warning")
        return result

    total = len(files)
    if log_fn:
        log_fn(f"Parsing {total} file{'s' if total != 1 else ''} ({pattern_desc})...")

    for i, fpath in enumerate(files, 1):
        if progress_fn:
            progress_fn(i * 100 / total)

        entries, lang = parse_input_file(fpath, valid_codes=valid_codes, log_fn=log_fn)
        if entries:
            result.setdefault(lang, []).extend(entries)
            if log_fn:
                log_fn(f"  {fpath.name}: {len(entries):,} entries ({lang})")
        else:
            if log_fn:
                log_fn(f"  {fpath.name}: 0 entries", "warning")

    # Log summary
    total_entries = sum(len(v) for v in result.values())
    if log_fn:
        log_fn(
            f"Parsed {total} files -> {total_entries:,} entries "
            f"across {len(result)} language{'s' if len(result) != 1 else ''}",
            "success" if total_entries > 0 else "warning",
        )

    return result
