"""XML Tools engine – miscellaneous XML operations on LocStr elements.

Grafted from QSS misceallenousextractforXML.py with adaptations for
ExtractAnything patterns (log_fn callbacks, xml_parser reuse, regex fixes).
"""

from __future__ import annotations

import logging
import os
import re
import stat
from copy import deepcopy
from pathlib import Path
from typing import Callable

from lxml import etree

import config
from . import xml_parser

logger = logging.getLogger(__name__)

LogFn = Callable[[str, str], None] | None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_xml_files(path: str | Path) -> list[Path]:
    """Return a list with a single file or all *.xml files inside a folder."""
    p = Path(path)
    if p.is_file():
        return [p]
    if not p.is_dir():
        return []
    return sorted(p.rglob("*.xml"))


def _make_writable(path: Path) -> None:
    """Remove read-only attribute (best-effort)."""
    try:
        current = os.stat(path).st_mode
        if not current & stat.S_IWRITE:
            os.chmod(path, current | stat.S_IWRITE)
    except Exception:
        pass


def _parse_xml_file(file_path: Path):
    """Read, sanitise, ROOT-wrap, and parse an XML file.

    Returns an lxml root element (the synthetic <ROOT>) or None.
    Uses xml_parser.read_xml_raw for encoding fallback and
    xml_parser.sanitize_xml for robust sanitisation.
    """
    raw = xml_parser.read_xml_raw(file_path)
    if raw is None:
        return None

    clean = xml_parser.sanitize_xml(raw)
    wrapped = "<ROOT>\n" + clean + "\n</ROOT>"
    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        return etree.fromstring(wrapped.encode("utf-8"), parser=parser)
    except Exception as exc:
        logger.warning("Cannot parse %s: %s", file_path.name, exc)
        return None


def _write_children(root, file_path: Path) -> None:
    """Write all children of the synthetic ROOT back to file."""
    _make_writable(file_path)
    with open(file_path, "w", encoding="utf-8") as out:
        for child in root:
            out.write(
                etree.tostring(child, encoding="utf-8",
                               pretty_print=True).decode("utf-8")
            )


def _compile_regex(pattern: str, *, log_fn: LogFn = None,
                   case_sensitive: bool = False) -> re.Pattern | None:
    """Compile a user-provided regex, reporting errors via log_fn."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.compile(pattern, flags)
    except re.error as err:
        msg = f"Invalid regex '{pattern}': {err}"
        logger.warning(msg)
        if log_fn:
            log_fn(msg, "error")
        return None


def _iter_locstr(root):
    """Iterate LocStr elements using xml_parser's case-variant helper."""
    return xml_parser.iter_locstr(root)


def _get_str(elem) -> str | None:
    """Get Str attribute value (case-insensitive)."""
    _, val = xml_parser.get_attr(elem, config.STR_ATTRS)
    return val


def _set_str(elem, value: str) -> None:
    """Set Str attribute (uses canonical 'Str' name)."""
    name, _ = xml_parser.get_attr(elem, config.STR_ATTRS)
    elem.set(name or "Str", value)


def _get_strorigin(elem) -> str | None:
    """Get StrOrigin attribute value (case-insensitive)."""
    _, val = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
    return val


def _set_strorigin(elem, value: str) -> None:
    """Set StrOrigin attribute (uses canonical 'StrOrigin' name)."""
    name, _ = xml_parser.get_attr(elem, config.STRORIGIN_ATTRS)
    elem.set(name or "StrOrigin", value)


def _get_stringid(elem) -> str | None:
    """Get StringId attribute value (case-insensitive)."""
    _, val = xml_parser.get_attr(elem, config.STRINGID_ATTRS)
    return val


# ---------------------------------------------------------------------------
# 1. Restore Str from StrOrigin
# ---------------------------------------------------------------------------

def restore_str_from_strorigin(
    path: str | Path,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> int:
    """Copy StrOrigin → Str for every LocStr where StrOrigin exists."""
    files = _get_xml_files(path)
    if not files:
        if log_fn:
            log_fn("No XML files found.", "warning")
        return 0

    changed = 0
    for i, f in enumerate(files, 1):
        if progress_fn:
            progress_fn(i * 100 // len(files))

        root = _parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in _iter_locstr(root):
            so = _get_strorigin(loc)
            if so is not None:
                _set_str(loc, so)
                mod = True

        if mod:
            try:
                _write_children(root, f)
                changed += 1
                if log_fn:
                    log_fn(f"  Restored: {f.name}")
            except Exception as exc:
                logger.error("Write failed %s: %s", f.name, exc)
                if log_fn:
                    log_fn(f"  ERROR writing {f.name}: {exc}", "error")

    return changed


# ---------------------------------------------------------------------------
# 2. Swap Str ↔ StrOrigin
# ---------------------------------------------------------------------------

def swap_str_with_strorigin(
    path: str | Path,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> int:
    """Swap Str and StrOrigin values for every LocStr."""
    files = _get_xml_files(path)
    if not files:
        if log_fn:
            log_fn("No XML files found.", "warning")
        return 0

    changed = 0
    for i, f in enumerate(files, 1):
        if progress_fn:
            progress_fn(i * 100 // len(files))

        root = _parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in _iter_locstr(root):
            str_val = _get_str(loc)
            so_val = _get_strorigin(loc)
            if str_val is not None or so_val is not None:
                _set_str(loc, so_val if so_val is not None else "")
                _set_strorigin(loc, str_val if str_val is not None else "")
                mod = True

        if mod:
            try:
                _write_children(root, f)
                changed += 1
                if log_fn:
                    log_fn(f"  Swapped: {f.name}")
            except Exception as exc:
                logger.error("Write failed %s: %s", f.name, exc)
                if log_fn:
                    log_fn(f"  ERROR writing {f.name}: {exc}", "error")

    return changed


# ---------------------------------------------------------------------------
# 3. Extract Rows (Single Condition)
# ---------------------------------------------------------------------------

def extract_rows(
    path: str | Path,
    attr: str,
    regex: str,
    is_contained: bool,
    *,
    log_fn: LogFn = None,
) -> str | None:
    """Extract LocStr rows matching a regex on the selected field.

    *attr* can be ``"Str"``, ``"StrOrigin"``, or ``"StrOrStrOrigin"``.
    If *is_contained* is True, keep matches; otherwise keep non-matches.
    Returns a pretty-printed XML string or None.
    """
    pat = _compile_regex(regex, log_fn=log_fn)
    if pat is None:
        return None

    files = _get_xml_files(path)
    matches: list = []

    for f in files:
        root = _parse_xml_file(f)
        if root is None:
            continue

        for loc in _iter_locstr(root):
            if attr == "StrOrStrOrigin":
                val_str = _get_str(loc) or ""
                val_so = _get_strorigin(loc) or ""
                found = bool(pat.search(val_str) or pat.search(val_so))
            elif attr == "StrOrigin":
                val = _get_strorigin(loc) or ""
                found = bool(pat.search(val))
            else:  # Str
                val = _get_str(loc) or ""
                found = bool(pat.search(val))

            if (is_contained and found) or (not is_contained and not found):
                matches.append(deepcopy(loc))

    if not matches:
        if log_fn:
            log_fn("No matching rows found.", "info")
        return None

    if log_fn:
        log_fn(f"Found {len(matches):,} matching rows.", "success")

    new_root = etree.Element("LocStrs")
    for m in matches:
        new_root.append(m)

    return etree.tostring(new_root, pretty_print=True,
                          encoding="utf-8").decode("utf-8")


# ---------------------------------------------------------------------------
# 3b. Extract Rows (Dual AND: Str + StrOrigin)
# ---------------------------------------------------------------------------

def extract_rows_dual(
    path: str | Path,
    regex_str: str,
    is_contained_str: bool,
    regex_so: str,
    is_contained_so: bool,
    *,
    log_fn: LogFn = None,
) -> str | None:
    """Extract LocStr rows satisfying BOTH conditions (AND).

    Each condition applies to Str or StrOrigin respectively.
    Empty regex means "no condition" for that field.
    """
    pat_str = _compile_regex(regex_str, log_fn=log_fn) if regex_str else None
    pat_so = _compile_regex(regex_so, log_fn=log_fn) if regex_so else None

    # If a non-empty regex failed to compile, _compile_regex already logged
    if regex_str and pat_str is None:
        return None
    if regex_so and pat_so is None:
        return None

    files = _get_xml_files(path)
    matches: list = []

    for f in files:
        root = _parse_xml_file(f)
        if root is None:
            continue

        for loc in _iter_locstr(root):
            val_str = _get_str(loc) or ""
            val_so = _get_strorigin(loc) or ""

            # Str condition
            if pat_str is None:
                ok_str = True
            else:
                found = bool(pat_str.search(val_str))
                ok_str = found if is_contained_str else not found

            # StrOrigin condition
            if pat_so is None:
                ok_so = True
            else:
                found = bool(pat_so.search(val_so))
                ok_so = found if is_contained_so else not found

            if ok_str and ok_so:
                matches.append(deepcopy(loc))

    if not matches:
        if log_fn:
            log_fn("No matching rows found.", "info")
        return None

    if log_fn:
        log_fn(f"Found {len(matches):,} matching rows.", "success")

    new_root = etree.Element("LocStrs")
    for m in matches:
        new_root.append(m)

    return etree.tostring(new_root, pretty_print=True,
                          encoding="utf-8").decode("utf-8")


# ---------------------------------------------------------------------------
# 4. Erase Str content matching regex
# ---------------------------------------------------------------------------

def erase_str_matching(
    path: str | Path,
    regex: str,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> int:
    """Regex-sub matching content from Str attribute values (in-place)."""
    pat = _compile_regex(regex, log_fn=log_fn)
    if pat is None:
        return 0

    files = _get_xml_files(path)
    if not files:
        if log_fn:
            log_fn("No XML files found.", "warning")
        return 0

    changed = 0
    for i, f in enumerate(files, 1):
        if progress_fn:
            progress_fn(i * 100 // len(files))

        root = _parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in _iter_locstr(root):
            val = _get_str(loc)
            if val and pat.search(val):
                _set_str(loc, pat.sub("", val))
                mod = True

        if mod:
            try:
                _write_children(root, f)
                changed += 1
                if log_fn:
                    log_fn(f"  Erased matches: {f.name}")
            except Exception as exc:
                logger.error("Write failed %s: %s", f.name, exc)
                if log_fn:
                    log_fn(f"  ERROR writing {f.name}: {exc}", "error")

    return changed


# ---------------------------------------------------------------------------
# 5. Modify Str by regex replace (raw text)
# ---------------------------------------------------------------------------

def modify_str_matching(
    path: str | Path,
    search_regex: str,
    replacement: str,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> int:
    """Replace occurrences of *search_regex* in Str attribute values.

    Works on raw XML text so entity sequences (e.g. ``&lt;br/&gt;``) are
    matched literally.  Case-sensitive.

    Uses negative lookbehind ``(?<![A-Za-z])`` to match only standalone
    ``Str=`` attributes, avoiding StrOrigin, StringId, etc.
    """
    user_pat = _compile_regex(search_regex, log_fn=log_fn, case_sensitive=True)
    if user_pat is None:
        return 0

    # Match only standalone Str="..." — negative lookbehind prevents matching
    # StrOrigin="...", StringId="...", etc.
    attr_pat = re.compile(
        r'((?<![A-Za-z])Str\s*=\s*")'   # group-1: attribute head
        r'((?:[^"\\]|\\.)*)"',           # group-2: attribute value
        re.DOTALL,
    )

    files = _get_xml_files(path)
    if not files:
        if log_fn:
            log_fn("No XML files found.", "warning")
        return 0

    changed_files = 0
    for idx, fpath in enumerate(files, 1):
        if progress_fn:
            progress_fn(idx * 100 // len(files))

        raw = xml_parser.read_xml_raw(fpath)
        if raw is None:
            continue

        file_modified = False

        def repl(match: re.Match) -> str:
            nonlocal file_modified
            head = match.group(1)
            value = match.group(2)
            new_value, n = user_pat.subn(replacement, value)
            if n:
                file_modified = True
            return f'{head}{new_value}"'

        new_xml = attr_pat.sub(repl, raw)

        if file_modified:
            _make_writable(fpath)
            fpath.write_text(new_xml, encoding="utf-8")
            changed_files += 1
            if log_fn:
                log_fn(f"  Modified: {fpath.name}")

    return changed_files


# ---------------------------------------------------------------------------
# 6. Stack KR/Translation
# ---------------------------------------------------------------------------

def stack_kr_translation(
    path: str | Path,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> int:
    """Append Str value after StrOrigin separated by ``<br/>``.

    lxml auto-escapes to ``&lt;br/&gt;`` on disk — this is correct per
    the project's XML pipeline conventions.
    """
    files = _get_xml_files(path)
    if not files:
        if log_fn:
            log_fn("No XML files found.", "warning")
        return 0

    changed = 0
    for i, f in enumerate(files, 1):
        if progress_fn:
            progress_fn(i * 100 // len(files))

        root = _parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in _iter_locstr(root):
            str_val = _get_str(loc)
            if str_val is None:
                continue

            so_val = _get_strorigin(loc) or ""
            new_so = (so_val + "<br/>" + str_val) if so_val else str_val

            if new_so != so_val:
                _set_strorigin(loc, new_so)
                mod = True

        if mod:
            try:
                _write_children(root, f)
                changed += 1
                if log_fn:
                    log_fn(f"  Stacked: {f.name}")
            except Exception as exc:
                logger.error("Write failed %s: %s", f.name, exc)
                if log_fn:
                    log_fn(f"  ERROR writing {f.name}: {exc}", "error")

    return changed


# ---------------------------------------------------------------------------
# 7. Replace StrOrigin in target by StringId from source
# ---------------------------------------------------------------------------

def replace_strorigin_by_stringid(
    source_folder: str | Path,
    target_folder: str | Path,
    *,
    log_fn: LogFn = None,
    progress_fn: Callable | None = None,
) -> tuple[int, int, int]:
    """Replace StrOrigin in TARGET XMLs using SOURCE XMLs matched by StringId.

    Returns ``(files_updated, locstrs_edited, errors)``.
    """
    source_folder = Path(source_folder)
    target_folder = Path(target_folder)

    # Build StringId → StrOrigin map from SOURCE
    if log_fn:
        log_fn("Building StringId → StrOrigin map from source...", "header")

    sid_to_so: dict[str, str] = {}
    for xml_file in _get_xml_files(source_folder):
        src_root = _parse_xml_file(xml_file)
        if src_root is None:
            continue
        for loc in _iter_locstr(src_root):
            sid = _get_stringid(loc)
            so = _get_strorigin(loc)
            if sid and so is not None:
                sid_to_so[sid] = so

    if not sid_to_so:
        if log_fn:
            log_fn("No StrOrigin values found in SOURCE.", "warning")
        return 0, 0, 0

    if log_fn:
        log_fn(f"Source map: {len(sid_to_so):,} StringId entries.", "info")

    xml_files = _get_xml_files(target_folder)
    if not xml_files:
        if log_fn:
            log_fn("No XML files in target folder.", "warning")
        return 0, 0, 0

    changed_files = 0
    total_locstrs = 0
    errors = 0

    for idx, xml_file in enumerate(xml_files, 1):
        if progress_fn:
            progress_fn(idx * 100 // len(xml_files))
        if log_fn:
            log_fn(f"  [{idx}/{len(xml_files)}] {xml_file.name}")

        tgt_root = _parse_xml_file(xml_file)
        if tgt_root is None:
            errors += 1
            continue

        modified = False
        for loc in _iter_locstr(tgt_root):
            sid = _get_stringid(loc)
            if sid is None:
                continue
            new_so = sid_to_so.get(sid)
            if new_so is not None and _get_strorigin(loc) != new_so:
                _set_strorigin(loc, new_so)
                modified = True
                total_locstrs += 1

        if modified:
            try:
                _write_children(tgt_root, xml_file)
                changed_files += 1
            except Exception as exc:
                logger.error("Write failed %s: %s", xml_file.name, exc)
                if log_fn:
                    log_fn(f"  ERROR writing {xml_file.name}: {exc}", "error")
                errors += 1

    return changed_files, total_locstrs, errors
