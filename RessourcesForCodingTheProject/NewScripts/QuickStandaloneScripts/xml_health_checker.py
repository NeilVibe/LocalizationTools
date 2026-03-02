#!/usr/bin/env python3
# coding: utf-8
"""
XML Health Checker v1.0
========================
Standalone GUI tool that performs comprehensive health checks on languagedata
XML files. Detects all potential XML issues including broken/malformed elements,
encoding problems, wrong newline representations, unbalanced brackets,
duplicate StringIDs, missing attributes, and more.

Input:
  - Data Folder: folder containing languagedata XML files (any depth)

Output (in HealthCheck_Output/ next to script):
  - Per-language text report (.txt) with all findings grouped by category
  - Summary in GUI log

Usage: python xml_health_checker.py
"""

import json
import re
import sys
import time
import logging
import datetime as _dt
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Try lxml first (preserves attribute order, recovery mode), fallback to stdlib
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("XMLHealthChecker")
logger.setLevel(logging.DEBUG)

# =============================================================================
# CONSTANTS
# =============================================================================

# Detect script directory (supports PyInstaller frozen exe)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

SETTINGS_FILE = SCRIPT_DIR / "xml_health_checker_settings.json"
OUTPUT_DIR = SCRIPT_DIR / "HealthCheck_Output"

# LocStr tag and attribute variants (case-insensitive matching)
LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
STRINGID_ATTRS = ('StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId')
STRORIGIN_ATTRS = ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN')
STR_ATTRS = ('Str', 'str', 'STR')

# =============================================================================
# SETTINGS PERSISTENCE
# =============================================================================

def _load_settings() -> dict:
    """Load persisted settings from JSON."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(settings: dict):
    """Save settings to JSON."""
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)


# =============================================================================
# XML READING & SANITIZATION
# =============================================================================

def _read_xml_raw(xml_path: Path) -> Optional[str]:
    """Read XML file with encoding fallback (latin-1 always succeeds)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return xml_path.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return None  # Unreachable — latin-1 decodes any byte sequence


# Fix bare & that aren't valid XML entities
_bad_amp = re.compile(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)')
# Fix malformed self-closing tags like </>
_bad_selfclose = re.compile(r'</>')
# Fix unescaped < inside attribute values, but PRESERVE <br/> tags
_attr_dangerous_lt = re.compile(r'<(?![bB][rR]\s*/?>)')


def _escape_attr_lt(m):
    """Escape < inside attribute values, preserving <br/> tags."""
    content = m.group(1)
    content = _attr_dangerous_lt.sub('&lt;', content)
    return '="' + content + '"'


# Matches attribute values containing <
_attr_with_lt = re.compile(r'="([^"]*<[^"]*)"')


def sanitize_xml(raw: str) -> str:
    """Fix common XML issues in game data files before parsing.
    PRESERVES <br/> tags inside attribute values."""
    raw = _bad_selfclose.sub('', raw)
    raw = _attr_with_lt.sub(_escape_attr_lt, raw)
    raw = _bad_amp.sub('&amp;', raw)
    return raw


def _parse_root(raw: str):
    """Parse sanitized XML string and return root element."""
    sanitized = sanitize_xml(raw)
    try:
        if USING_LXML:
            parser = etree.XMLParser(
                recover=True, encoding="utf-8",
                resolve_entities=False, load_dtd=False, no_network=True,
            )
            return etree.fromstring(sanitized.encode("utf-8"), parser)
        else:
            return etree.fromstring(sanitized)
    except Exception as e:
        logger.error("XML parse error: %s", e)
        return None


def get_attr_value(attrs: dict, attr_variants: tuple) -> str:
    """Get attribute value from dict, trying multiple case variants."""
    for attr_name in attr_variants:
        if attr_name in attrs:
            return attrs[attr_name]
    return ""


def iter_locstr(root) -> list:
    """Iterate all LocStr elements (case-insensitive tag matching)."""
    elements = []
    for tag in LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def discover_xml_files(folder: Path) -> Dict[str, List[Path]]:
    """
    Discover all XML files in folder (recursive), grouped by language suffix.

    Looks for languagedata_*.xml files AND any .xml file in language-named
    subfolders. Returns {lang_code: [paths]}.
    """
    lang_files: Dict[str, List[Path]] = {}
    lang_re = re.compile(r'languagedata_(.+)\.xml', re.IGNORECASE)

    # Strategy 1: languagedata_*.xml files (anywhere in tree)
    for xml_file in sorted(folder.rglob("*.xml")):
        m = lang_re.match(xml_file.name)
        if m:
            code = m.group(1).upper()
            lang_files.setdefault(code, []).append(xml_file)
            continue

    # Strategy 2: Language-coded subfolders (e.g. FRE/, GER/)
    # Only if no languagedata files found
    if not lang_files:
        for xml_file in sorted(folder.rglob("*.xml")):
            # Check parent folder name for language code
            parent = xml_file.parent.name.upper()
            # Suffix detection: folder_FRE or just FRE
            parts = parent.split("_")
            code = parts[-1] if parts else parent
            if len(code) == 3 and code.isalpha():
                lang_files.setdefault(code, []).append(xml_file)

    # Strategy 3: All XML files ungrouped (single-language scenario)
    if not lang_files:
        all_xml = sorted(folder.rglob("*.xml"))
        if all_xml:
            lang_files["ALL"] = all_xml

    return lang_files


# =============================================================================
# HEALTH CHECK: BROKEN XML (raw text level)
# =============================================================================

# Regex to extract self-closing LocStr elements from raw XML text
_LOCSTR_RE = re.compile(r'<LocStr\b[^>]*/\s*>', re.DOTALL | re.IGNORECASE)
# Regex to extract StringId from raw (possibly broken) LocStr text
_RAW_STRINGID_RE = re.compile(r'StringId\s*=\s*"([^"]*?)"', re.IGNORECASE)


def check_broken_xml(raw: str, filename: str) -> List[Dict]:
    """
    Detect malformed LocStr elements by strict-parsing each one individually.

    Recovery-mode lxml silently creates elements with missing/wrong attributes
    when XML is malformed (e.g. StrOrigin""dada", Str"<bad"). Those broken
    nodes then pass through all other checks undetected.

    This function reads raw file text, extracts each <LocStr .../> fragment,
    and tries a strict lxml parse. Any fragment that fails strict parse is
    broken XML.
    """
    issues = []
    for m in _LOCSTR_RE.finditer(raw):
        fragment = m.group()
        test_xml = f'<r>{fragment}</r>'
        try:
            if USING_LXML:
                etree.fromstring(test_xml.encode('utf-8'))
            else:
                etree.fromstring(test_xml)
        except Exception:
            sid_match = _RAW_STRINGID_RE.search(fragment)
            sid = sid_match.group(1) if sid_match else "(unknown)"
            # Truncate fragment for display
            preview = fragment[:200] + "..." if len(fragment) > 200 else fragment
            issues.append({
                "check": "BROKEN_XML",
                "severity": "CRITICAL",
                "file": filename,
                "string_id": sid,
                "detail": f"Malformed LocStr element — strict parse fails",
                "raw": preview,
            })
    return issues


# =============================================================================
# HEALTH CHECK: FILE-LEVEL ISSUES
# =============================================================================

def check_file_level(raw: str, filepath: Path) -> List[Dict]:
    """Check file-level XML issues before element-level analysis."""
    issues = []
    filename = filepath.name

    # Check 1: Encoding declaration mismatch (only if declaration exists)
    enc_match = re.search(r'<\?xml[^>]*encoding=["\']([^"\']+)["\']', raw, re.IGNORECASE)
    if enc_match:
        declared = enc_match.group(1).lower()
        if declared not in ("utf-8", "utf8"):
            issues.append({
                "check": "ENCODING_MISMATCH",
                "severity": "WARNING",
                "file": filename,
                "string_id": "-",
                "detail": f"Declared encoding '{declared}' — expected 'utf-8'",
            })

    # Check 4: Bare & (unfixed XML entities)
    bare_amps = _bad_amp.findall(raw)
    if bare_amps:
        count = len(_bad_amp.findall(raw))
        issues.append({
            "check": "BARE_AMPERSAND",
            "severity": "WARNING",
            "file": filename,
            "string_id": "-",
            "detail": f"{count} bare '&' found (not part of &amp;/&lt;/&gt;/etc.) — sanitizer fixes these but source is malformed",
        })

    # Check 5: Malformed self-closing tags </>
    selfclose_count = len(_bad_selfclose.findall(raw))
    if selfclose_count:
        issues.append({
            "check": "MALFORMED_SELFCLOSE",
            "severity": "WARNING",
            "file": filename,
            "string_id": "-",
            "detail": f"{selfclose_count} malformed </> tags found",
        })

    # Check 6: Try strict parse (no recovery mode)
    sanitized = sanitize_xml(raw)
    try:
        if USING_LXML:
            strict_parser = etree.XMLParser(
                recover=False, encoding="utf-8",
                resolve_entities=False, load_dtd=False, no_network=True,
            )
            etree.fromstring(sanitized.encode("utf-8"), strict_parser)
        else:
            etree.fromstring(sanitized)
    except Exception as e:
        err_msg = str(e)
        # Truncate long error messages
        if len(err_msg) > 300:
            err_msg = err_msg[:300] + "..."
        issues.append({
            "check": "STRICT_PARSE_FAIL",
            "severity": "ERROR",
            "file": filename,
            "string_id": "-",
            "detail": f"Strict XML parse fails (recovery mode may hide issues): {err_msg}",
        })

    # Check 7: Empty file
    stripped = raw.strip()
    if not stripped:
        issues.append({
            "check": "EMPTY_FILE",
            "severity": "ERROR",
            "file": filename,
            "string_id": "-",
            "detail": "File is empty",
        })
    elif '<LocStr' not in raw and '<locstr' not in raw.lower():
        issues.append({
            "check": "NO_LOCSTR_ELEMENTS",
            "severity": "WARNING",
            "file": filename,
            "string_id": "-",
            "detail": "File contains no LocStr elements",
        })

    return issues


# =============================================================================
# HEALTH CHECK: ELEMENT-LEVEL ISSUES
# =============================================================================

# Regex to find any <br...> tag variant
_BR_TAG_RE = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)

# Wrong newline patterns
_WRONG_BR_VARIANTS = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)


def _has_wrong_newlines(text: str) -> Optional[str]:
    """
    Check if text contains wrong newline representations.

    The only correct newline format in XML language data is <br/>.
    Returns description of the issue, or None if clean.
    """
    if not text:
        return None

    problems = []

    # Actual newline / carriage return characters (from &#10; / &#13; in XML)
    if '\n' in text:
        problems.append("literal \\n character")
    if '\r' in text:
        problems.append("literal \\r character")

    # Literal \n or \r as text (backslash + letter — someone typed it)
    if '\\n' in text:
        problems.append("escaped \\\\n text")
    if '\\r' in text:
        problems.append("escaped \\\\r text")

    # Unicode line separator / paragraph separator
    if '\u2028' in text:
        problems.append("Unicode line separator U+2028")
    if '\u2029' in text:
        problems.append("Unicode paragraph separator U+2029")

    # Wrong <br> variants (not exactly <br/>)
    for m in _BR_TAG_RE.finditer(text):
        tag = m.group()
        if tag != '<br/>':
            problems.append(f"wrong br variant: {tag}")
            break  # One is enough

    if problems:
        return "; ".join(problems)
    return None


def _has_unbalanced_brackets(text: str) -> Optional[str]:
    """
    Check if curly brackets in text are properly paired and nested.
    Returns description of the issue, or None if clean.
    """
    if not text:
        return None
    depth = 0
    for i, ch in enumerate(text):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                context = text[max(0, i - 20):i + 20]
                return f"closing '}}' without opening '{{' near: ...{context}..."
    if depth > 0:
        return f"{depth} unclosed opening '{{' bracket(s)"
    return None


def _check_empty_attributes(attrs: dict, filename: str) -> List[Dict]:
    """Check for empty or whitespace-only critical attributes."""
    issues = []
    sid = get_attr_value(attrs, STRINGID_ATTRS)
    so = get_attr_value(attrs, STRORIGIN_ATTRS)
    sv = get_attr_value(attrs, STR_ATTRS)

    sid_display = sid if sid else "(empty)"

    if not sid.strip():
        issues.append({
            "check": "EMPTY_STRINGID",
            "severity": "ERROR",
            "file": filename,
            "string_id": sid_display,
            "detail": "StringID is empty or missing",
        })

    if not so.strip():
        issues.append({
            "check": "EMPTY_STRORIGIN",
            "severity": "WARNING",
            "file": filename,
            "string_id": sid_display,
            "detail": "StrOrigin is empty or missing",
        })

    # Empty Str is not necessarily wrong — some entries are intentionally blank
    # But flag it as info if StringID exists
    if sid.strip() and not sv.strip():
        issues.append({
            "check": "EMPTY_STR",
            "severity": "INFO",
            "file": filename,
            "string_id": sid_display,
            "detail": "Str value is empty (may be intentional)",
        })

    return issues


def _check_suspicious_characters(text: str, attr_name: str, sid: str, filename: str) -> List[Dict]:
    """Check for suspicious/control characters in attribute values."""
    issues = []
    if not text:
        return issues

    # Check for null bytes
    if '\x00' in text:
        issues.append({
            "check": "NULL_BYTE",
            "severity": "CRITICAL",
            "file": filename,
            "string_id": sid,
            "detail": f"Null byte (\\x00) found in {attr_name}",
        })

    # Check for other control characters (except \t which might be OK)
    control_chars = []
    for i, ch in enumerate(text):
        code = ord(ch)
        if code < 32 and ch not in ('\n', '\r', '\t'):
            control_chars.append(f"U+{code:04X} at pos {i}")
    if control_chars:
        preview = ", ".join(control_chars[:5])
        if len(control_chars) > 5:
            preview += f" ... ({len(control_chars)} total)"
        issues.append({
            "check": "CONTROL_CHARS",
            "severity": "WARNING",
            "file": filename,
            "string_id": sid,
            "detail": f"Control characters in {attr_name}: {preview}",
        })

    return issues


def check_elements(root, filename: str) -> List[Dict]:
    """Run all element-level health checks on parsed XML."""
    issues = []
    elements = iter_locstr(root)
    sid_counter: Counter = Counter()
    sid_origin_counter: Counter = Counter()

    for elem in elements:
        attrs = dict(elem.attrib)
        sid = get_attr_value(attrs, STRINGID_ATTRS)
        so = get_attr_value(attrs, STRORIGIN_ATTRS)
        sv = get_attr_value(attrs, STR_ATTRS)

        sid_display = sid if sid.strip() else "(empty)"

        # Track for duplicate detection
        if sid.strip():
            sid_counter[sid] += 1
            key = (sid, so)
            sid_origin_counter[key] += 1

        # Check 1: Empty/missing attributes
        issues.extend(_check_empty_attributes(attrs, filename))

        # Check 2: Wrong newlines in Str
        nl_issue = _has_wrong_newlines(sv)
        if nl_issue:
            issues.append({
                "check": "WRONG_NEWLINE_STR",
                "severity": "ERROR",
                "file": filename,
                "string_id": sid_display,
                "detail": f"Wrong newline in Str: {nl_issue}",
            })

        # Check 3: Wrong newlines in StrOrigin
        nl_issue_so = _has_wrong_newlines(so)
        if nl_issue_so:
            issues.append({
                "check": "WRONG_NEWLINE_STRORIGIN",
                "severity": "ERROR",
                "file": filename,
                "string_id": sid_display,
                "detail": f"Wrong newline in StrOrigin: {nl_issue_so}",
            })

        # Check 4: Unbalanced curly brackets in Str
        bracket_issue = _has_unbalanced_brackets(sv)
        if bracket_issue:
            issues.append({
                "check": "UNBALANCED_BRACKETS",
                "severity": "ERROR",
                "file": filename,
                "string_id": sid_display,
                "detail": f"Unbalanced brackets in Str: {bracket_issue}",
            })

        # Check 5: Pattern code mismatch (StrOrigin vs Str)
        if so.strip() and sv.strip():
            origin_patterns = set(re.findall(r'\{.*?\}', so))
            str_patterns = set(re.findall(r'\{.*?\}', sv))
            # Normalize staticinfo patterns
            origin_normalized = {_normalize_staticinfo(p) for p in origin_patterns}
            str_normalized = {_normalize_staticinfo(p) for p in str_patterns}
            if origin_normalized != str_normalized:
                missing = origin_normalized - str_normalized
                extra = str_normalized - origin_normalized
                parts = []
                if missing:
                    parts.append(f"missing: {', '.join(sorted(missing))}")
                if extra:
                    parts.append(f"extra: {', '.join(sorted(extra))}")
                issues.append({
                    "check": "PATTERN_MISMATCH",
                    "severity": "ERROR",
                    "file": filename,
                    "string_id": sid_display,
                    "detail": f"Pattern code mismatch — {'; '.join(parts)}",
                })

        # Check 6: Suspicious characters in all attributes
        issues.extend(_check_suspicious_characters(sv, "Str", sid_display, filename))
        issues.extend(_check_suspicious_characters(so, "StrOrigin", sid_display, filename))
        issues.extend(_check_suspicious_characters(sid, "StringID", sid_display, filename))

        # Check 7: Extremely long Str value (possible data corruption)
        if len(sv) > 10000:
            issues.append({
                "check": "EXTREME_LENGTH",
                "severity": "WARNING",
                "file": filename,
                "string_id": sid_display,
                "detail": f"Str value is {len(sv):,} characters long — possible corruption",
            })

        # Check 8: Unescaped < or > in Str (that survived sanitization)
        # After lxml parse, <br/> is unescaped. Check for other bare < >
        if sv:
            stripped = _BR_TAG_RE.sub('', sv)
            # Also strip known markup tags
            stripped = re.sub(r'</?(?:PAColor|Scale|color|Style:)[^>]*>', '', stripped, flags=re.IGNORECASE)
            if '<' in stripped or ('>' in stripped and '{' not in stripped):
                issues.append({
                    "check": "UNESCAPED_ANGLE_BRACKET",
                    "severity": "WARNING",
                    "file": filename,
                    "string_id": sid_display,
                    "detail": "Possible unescaped < or > in Str (not <br/> or known markup)",
                })

    # Check 9: Duplicate StringIDs (same StringID appearing multiple times)
    for sid, count in sid_counter.items():
        if count > 1:
            issues.append({
                "check": "DUPLICATE_STRINGID",
                "severity": "WARNING",
                "file": filename,
                "string_id": sid,
                "detail": f"StringID appears {count} times in file",
            })

    # Check 10: Exact duplicate entries (same StringID + StrOrigin)
    for (sid, so), count in sid_origin_counter.items():
        if count > 1:
            issues.append({
                "check": "EXACT_DUPLICATE",
                "severity": "ERROR",
                "file": filename,
                "string_id": sid,
                "detail": f"Exact duplicate (same StringID + StrOrigin) appears {count} times",
            })

    return issues


def _normalize_staticinfo(code: str) -> str:
    """Normalize staticinfo patterns by stripping variable parts after #."""
    if re.search(r'\{[^{}]*Staticinfo:[^{}]*#', code, re.I):
        return code.split('#', 1)[0] + '#}'
    return code


# =============================================================================
# REPORT WRITING
# =============================================================================

SEVERITY_ORDER = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}


def write_report(issues: List[Dict], output_path: Path, lang: str, file_count: int, elapsed: float):
    """Write a text report of all issues found."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("=" * 70)
    lines.append(f"  XML HEALTH CHECK REPORT — {lang}")
    lines.append("=" * 70)
    lines.append(f"  Generated: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Files checked: {file_count}")
    lines.append(f"  Elapsed: {elapsed:.1f}s")
    lines.append(f"  Total issues: {len(issues)}")
    lines.append("")

    # Count by severity
    sev_counts = Counter(i["severity"] for i in issues)
    for sev in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
        if sev in sev_counts:
            lines.append(f"  {sev}: {sev_counts[sev]}")
    lines.append("")

    # Count by check type
    check_counts = Counter(i["check"] for i in issues)
    lines.append("  Issues by type:")
    for check, count in sorted(check_counts.items()):
        lines.append(f"    {check}: {count}")
    lines.append("")

    # Sort issues: severity first, then check type, then file, then StringID
    sorted_issues = sorted(issues, key=lambda i: (
        SEVERITY_ORDER.get(i["severity"], 99),
        i["check"],
        i["file"],
        i["string_id"],
    ))

    # Group by check type
    current_check = None
    for issue in sorted_issues:
        if issue["check"] != current_check:
            current_check = issue["check"]
            lines.append("")
            lines.append("-" * 70)
            lines.append(f"  [{issue['severity']}] {current_check}")
            lines.append("-" * 70)

        lines.append(f"  File:     {issue['file']}")
        lines.append(f"  StringID: {issue['string_id']}")
        lines.append(f"  Detail:   {issue['detail']}")
        if "raw" in issue:
            lines.append(f"  Raw:      {issue['raw']}")
        lines.append("")

    if not issues:
        lines.append("  No issues found — all files are healthy!")
        lines.append("")

    output_path.write_text('\n'.join(lines), encoding='utf-8')


# =============================================================================
# GUI APPLICATION
# =============================================================================

class XMLHealthCheckerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XML Health Checker v1.0")
        self.root.geometry("800x650")
        self.root.minsize(700, 500)
        self._build_ui()
        self._load_persisted_settings()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 3}
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            main,
            text="XML Health Checker",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            main,
            text="Comprehensive health checks on languagedata XML files",
            font=("Segoe UI", 9),
        ).pack(pady=(0, 10))

        # Data folder
        self.folder_var = tk.StringVar()
        f_folder = ttk.LabelFrame(main, text="DATA FOLDER (folder with languagedata XML files)", padding=5)
        f_folder.pack(fill="x", **pad)
        folder_row = ttk.Frame(f_folder)
        folder_row.pack(fill="x")
        ttk.Entry(folder_row, textvariable=self.folder_var, width=60).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            folder_row, text="Browse...",
            command=lambda: self._browse_folder(self.folder_var, "Data Folder"),
        ).pack(side="right", padx=(0, 3))
        ttk.Button(folder_row, text="Save", command=self._save_folder_setting).pack(side="right")

        # Checks selection
        checks_frame = ttk.LabelFrame(main, text="Checks to run", padding=5)
        checks_frame.pack(fill="x", **pad)

        self.chk_broken = tk.BooleanVar(value=True)
        self.chk_file_level = tk.BooleanVar(value=True)
        self.chk_newlines = tk.BooleanVar(value=True)
        self.chk_brackets = tk.BooleanVar(value=True)
        self.chk_patterns = tk.BooleanVar(value=True)
        self.chk_duplicates = tk.BooleanVar(value=True)
        self.chk_attrs = tk.BooleanVar(value=True)
        self.chk_chars = tk.BooleanVar(value=True)

        row1 = ttk.Frame(checks_frame)
        row1.pack(fill="x")
        ttk.Checkbutton(row1, text="Broken XML (raw parse)", variable=self.chk_broken).pack(side="left", padx=5)
        ttk.Checkbutton(row1, text="File-level issues", variable=self.chk_file_level).pack(side="left", padx=5)
        ttk.Checkbutton(row1, text="Wrong newlines", variable=self.chk_newlines).pack(side="left", padx=5)
        ttk.Checkbutton(row1, text="Unbalanced brackets", variable=self.chk_brackets).pack(side="left", padx=5)

        row2 = ttk.Frame(checks_frame)
        row2.pack(fill="x", pady=(3, 0))
        ttk.Checkbutton(row2, text="Pattern mismatches", variable=self.chk_patterns).pack(side="left", padx=5)
        ttk.Checkbutton(row2, text="Duplicate StringIDs", variable=self.chk_duplicates).pack(side="left", padx=5)
        ttk.Checkbutton(row2, text="Empty attributes", variable=self.chk_attrs).pack(side="left", padx=5)
        ttk.Checkbutton(row2, text="Suspicious chars", variable=self.chk_chars).pack(side="left", padx=5)

        # Output info
        out_frame = ttk.LabelFrame(main, text="Output", padding=5)
        out_frame.pack(fill="x", **pad)
        ttk.Label(out_frame, text=f"Output directory: {OUTPUT_DIR}", font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Label(out_frame, text="Per language: text report (.txt) with all findings", font=("Segoe UI", 8)).pack(anchor="w")

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=10)
        self.run_btn = ttk.Button(btn_frame, text="RUN HEALTH CHECK", width=30, command=self._run)
        self.run_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Log", width=12, command=self._clear_log).pack(side="left", padx=5)

        # Log
        f_log = ttk.LabelFrame(main, text="Log", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(f_log, height=18, font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info", foreground="black")
        self.log.tag_config("success", foreground="green")
        self.log.tag_config("warning", foreground="#CC8800")
        self.log.tag_config("error", foreground="red")
        self.log.tag_config("critical", foreground="#CC0000", font=("Consolas", 9, "bold"))
        self.log.tag_config("header", foreground="blue", font=("Consolas", 9, "bold"))

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------

    def _log(self, msg: str, tag: str = "info"):
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.root.update_idletasks()

    def _browse_folder(self, var: tk.StringVar, title: str):
        path = filedialog.askdirectory(title=f"Select {title}")
        if path:
            var.set(path)

    def _clear_log(self):
        self.log.delete("1.0", "end")

    def _save_folder_setting(self):
        folder = self.folder_var.get().strip()
        if not folder:
            return
        settings = _load_settings()
        settings["data_folder"] = folder
        _save_settings(settings)
        messagebox.showinfo("Saved", f"Data folder saved:\n{folder}")

    def _load_persisted_settings(self):
        settings = _load_settings()
        folder = settings.get("data_folder", "")
        if folder:
            self.folder_var.set(folder)

    # -----------------------------------------------------------------
    # MAIN LOGIC
    # -----------------------------------------------------------------

    def _run(self):
        self.log.delete("1.0", "end")

        folder = self.folder_var.get().strip()

        if not folder:
            messagebox.showerror("Error", "Please select the data folder.")
            return
        folder_path = Path(folder)
        if not folder_path.is_dir():
            messagebox.showerror("Error", f"Folder not found:\n{folder_path}")
            return

        # Build enabled checks set
        enabled = set()
        if self.chk_broken.get():
            enabled.add("broken_xml")
        if self.chk_file_level.get():
            enabled.add("file_level")
        if self.chk_newlines.get():
            enabled.add("newlines")
        if self.chk_brackets.get():
            enabled.add("brackets")
        if self.chk_patterns.get():
            enabled.add("patterns")
        if self.chk_duplicates.get():
            enabled.add("duplicates")
        if self.chk_attrs.get():
            enabled.add("attrs")
        if self.chk_chars.get():
            enabled.add("chars")

        if not enabled:
            messagebox.showerror("Error", "Please select at least one check to run.")
            return

        self.run_btn.config(state="disabled")

        try:
            self._execute(folder_path, enabled)
        except Exception as e:
            self._log(f"\nERROR: {e}", "error")
            logger.exception("XMLHealthChecker failed")
        finally:
            self.run_btn.config(state="normal")

    def _execute(self, folder_path: Path, enabled: set):
        t_start = time.time()

        self._log("=" * 60, "header")
        self._log("  XML HEALTH CHECKER v1.0", "header")
        self._log("=" * 60, "header")
        self._log(f"\nData folder: {folder_path}", "info")

        # Step 1: Discover files
        self._log("Discovering XML files...", "info")
        lang_files = discover_xml_files(folder_path)

        if not lang_files:
            self._log("No XML files found in folder.", "error")
            return

        total_files = sum(len(f) for f in lang_files.values())
        self._log(f"  Found {total_files} XML files across {len(lang_files)} language(s)", "info")
        for lang in sorted(lang_files.keys()):
            self._log(f"    {lang}: {len(lang_files[lang])} files", "info")

        # Step 2: Enabled checks summary
        self._log(f"\nEnabled checks: {', '.join(sorted(enabled))}", "info")

        # Step 3: Run checks per language
        self._log(f"\n{'=' * 60}", "header")
        self._log("  RUNNING CHECKS...", "header")
        self._log(f"{'=' * 60}", "header")

        all_lang_issues: Dict[str, List[Dict]] = {}
        grand_total_issues = 0
        grand_total_critical = 0
        grand_total_errors = 0
        grand_total_warnings = 0

        languages = sorted(lang_files.keys())
        num_langs = len(languages)

        for lang_idx, lang in enumerate(languages, 1):
            files = lang_files[lang]
            self._log(f"\n[{lang_idx}/{num_langs}] {lang} — {len(files)} files", "header")

            lang_issues: List[Dict] = []
            t_lang = time.time()

            for file_idx, xml_path in enumerate(files, 1):
                self._log(f"  Checking {xml_path.name}... ({file_idx}/{len(files)})", "info")

                # Read raw content
                raw = _read_xml_raw(xml_path)
                if raw is None:
                    lang_issues.append({
                        "check": "READ_FAILURE",
                        "severity": "CRITICAL",
                        "file": xml_path.name,
                        "string_id": "-",
                        "detail": "Failed to read file with any encoding",
                    })
                    continue

                # File-level checks
                if "file_level" in enabled:
                    lang_issues.extend(check_file_level(raw, xml_path))

                # Broken XML check (raw text level)
                if "broken_xml" in enabled:
                    broken = check_broken_xml(raw, xml_path.name)
                    lang_issues.extend(broken)
                    if broken:
                        self._log(f"    BROKEN XML: {len(broken)} malformed LocStr elements", "critical")

                # Parse for element-level checks
                root = _parse_root(raw)
                if root is None:
                    lang_issues.append({
                        "check": "PARSE_FAILURE",
                        "severity": "CRITICAL",
                        "file": xml_path.name,
                        "string_id": "-",
                        "detail": "Failed to parse XML even with recovery mode",
                    })
                    continue

                elements = iter_locstr(root)

                # Element-level checks (filtered by enabled flags)
                sid_counter: Counter = Counter()
                sid_origin_counter: Counter = Counter()

                for elem in elements:
                    attrs = dict(elem.attrib)
                    sid = get_attr_value(attrs, STRINGID_ATTRS)
                    so = get_attr_value(attrs, STRORIGIN_ATTRS)
                    sv = get_attr_value(attrs, STR_ATTRS)
                    sid_display = sid if sid.strip() else "(empty)"

                    # Track for duplicate detection
                    if sid.strip():
                        sid_counter[sid] += 1
                        sid_origin_counter[(sid, so)] += 1

                    # Empty attributes
                    if "attrs" in enabled:
                        if not sid.strip():
                            lang_issues.append({
                                "check": "EMPTY_STRINGID",
                                "severity": "ERROR",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": "StringID is empty or missing",
                            })
                        if not so.strip():
                            lang_issues.append({
                                "check": "EMPTY_STRORIGIN",
                                "severity": "WARNING",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": "StrOrigin is empty or missing",
                            })
                        if sid.strip() and not sv.strip():
                            lang_issues.append({
                                "check": "EMPTY_STR",
                                "severity": "INFO",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": "Str value is empty (may be intentional)",
                            })

                    # Wrong newlines
                    if "newlines" in enabled:
                        nl_issue = _has_wrong_newlines(sv)
                        if nl_issue:
                            lang_issues.append({
                                "check": "WRONG_NEWLINE_STR",
                                "severity": "ERROR",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": f"Wrong newline in Str: {nl_issue}",
                            })
                        nl_issue_so = _has_wrong_newlines(so)
                        if nl_issue_so:
                            lang_issues.append({
                                "check": "WRONG_NEWLINE_STRORIGIN",
                                "severity": "ERROR",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": f"Wrong newline in StrOrigin: {nl_issue_so}",
                            })

                    # Unbalanced brackets
                    if "brackets" in enabled:
                        bracket_issue = _has_unbalanced_brackets(sv)
                        if bracket_issue:
                            lang_issues.append({
                                "check": "UNBALANCED_BRACKETS",
                                "severity": "ERROR",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": f"Unbalanced brackets in Str: {bracket_issue}",
                            })

                    # Pattern mismatch
                    if "patterns" in enabled:
                        if so.strip() and sv.strip():
                            origin_patterns = set(re.findall(r'\{.*?\}', so))
                            str_patterns = set(re.findall(r'\{.*?\}', sv))
                            origin_norm = {_normalize_staticinfo(p) for p in origin_patterns}
                            str_norm = {_normalize_staticinfo(p) for p in str_patterns}
                            if origin_norm != str_norm:
                                missing = origin_norm - str_norm
                                extra = str_norm - origin_norm
                                parts = []
                                if missing:
                                    parts.append(f"missing: {', '.join(sorted(missing))}")
                                if extra:
                                    parts.append(f"extra: {', '.join(sorted(extra))}")
                                lang_issues.append({
                                    "check": "PATTERN_MISMATCH",
                                    "severity": "ERROR",
                                    "file": xml_path.name,
                                    "string_id": sid_display,
                                    "detail": f"Pattern code mismatch — {'; '.join(parts)}",
                                })

                    # Suspicious characters
                    if "chars" in enabled:
                        lang_issues.extend(_check_suspicious_characters(sv, "Str", sid_display, xml_path.name))
                        lang_issues.extend(_check_suspicious_characters(so, "StrOrigin", sid_display, xml_path.name))
                        lang_issues.extend(_check_suspicious_characters(sid, "StringID", sid_display, xml_path.name))

                        # Extreme length
                        if len(sv) > 10000:
                            lang_issues.append({
                                "check": "EXTREME_LENGTH",
                                "severity": "WARNING",
                                "file": xml_path.name,
                                "string_id": sid_display,
                                "detail": f"Str value is {len(sv):,} characters long — possible corruption",
                            })

                        # Unescaped angle brackets
                        if sv:
                            stripped = _BR_TAG_RE.sub('', sv)
                            stripped = re.sub(r'</?(?:PAColor|Scale|color|Style:)[^>]*>', '', stripped, flags=re.IGNORECASE)
                            if '<' in stripped or ('>' in stripped and '{' not in stripped):
                                lang_issues.append({
                                    "check": "UNESCAPED_ANGLE_BRACKET",
                                    "severity": "WARNING",
                                    "file": xml_path.name,
                                    "string_id": sid_display,
                                    "detail": "Possible unescaped < or > in Str (not <br/> or known markup)",
                                })

                # Duplicate checks (per file)
                if "duplicates" in enabled:
                    for dup_sid, count in sid_counter.items():
                        if count > 1:
                            lang_issues.append({
                                "check": "DUPLICATE_STRINGID",
                                "severity": "WARNING",
                                "file": xml_path.name,
                                "string_id": dup_sid,
                                "detail": f"StringID appears {count} times in file",
                            })
                    for (dup_sid, dup_so), count in sid_origin_counter.items():
                        if count > 1:
                            lang_issues.append({
                                "check": "EXACT_DUPLICATE",
                                "severity": "ERROR",
                                "file": xml_path.name,
                                "string_id": dup_sid,
                                "detail": f"Exact duplicate (same StringID + StrOrigin) appears {count} times",
                            })

                # Reset counters per file
                sid_counter.clear()
                sid_origin_counter.clear()

            elapsed_lang = time.time() - t_lang
            all_lang_issues[lang] = lang_issues

            # Per-language summary
            sev_counts = Counter(i["severity"] for i in lang_issues)
            crit = sev_counts.get("CRITICAL", 0)
            errs = sev_counts.get("ERROR", 0)
            warns = sev_counts.get("WARNING", 0)
            infos = sev_counts.get("INFO", 0)
            total = len(lang_issues)

            grand_total_issues += total
            grand_total_critical += crit
            grand_total_errors += errs
            grand_total_warnings += warns

            if total == 0:
                self._log(f"  [{lang}] HEALTHY — no issues [{elapsed_lang:.1f}s]", "success")
            else:
                severity_tag = "critical" if crit > 0 else "error" if errs > 0 else "warning"
                parts = []
                if crit:
                    parts.append(f"{crit} CRITICAL")
                if errs:
                    parts.append(f"{errs} errors")
                if warns:
                    parts.append(f"{warns} warnings")
                if infos:
                    parts.append(f"{infos} info")
                self._log(f"  [{lang}] {total} issues: {', '.join(parts)} [{elapsed_lang:.1f}s]", severity_tag)

        # Step 4: Write reports
        total_elapsed = time.time() - t_start

        self._log(f"\n{'=' * 60}", "header")
        self._log("  SUMMARY", "header")
        self._log(f"{'=' * 60}", "header")
        self._log(f"  Files checked: {total_files}", "info")
        self._log(f"  Languages: {num_langs}", "info")
        self._log(f"  Total time: {total_elapsed:.1f}s", "info")
        self._log("", "info")

        if grand_total_issues == 0:
            self._log("  ALL FILES HEALTHY — no issues found!", "success")
        else:
            tag = "critical" if grand_total_critical else "error" if grand_total_errors else "warning"
            self._log(f"  Total issues: {grand_total_issues}", tag)
            if grand_total_critical:
                self._log(f"    CRITICAL: {grand_total_critical}", "critical")
            if grand_total_errors:
                self._log(f"    ERROR: {grand_total_errors}", "error")
            if grand_total_warnings:
                self._log(f"    WARNING: {grand_total_warnings}", "warning")

        # Write reports for languages with issues
        has_output = False
        if grand_total_issues > 0:
            timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = OUTPUT_DIR / f"healthcheck_{timestamp}"

            self._log(f"\n{'─' * 60}", "info")
            self._log("WRITING REPORTS...", "header")
            self._log(f"{'─' * 60}", "info")

            for lang in sorted(all_lang_issues.keys()):
                issues = all_lang_issues[lang]
                if not issues:
                    continue

                report_path = output_dir / f"HEALTH_{lang}.txt"
                write_report(issues, report_path, lang, len(lang_files[lang]), total_elapsed)
                has_output = True

                sev_counts = Counter(i["severity"] for i in issues)
                self._log(f"  {report_path.name}: {len(issues)} issues", "success")

            if has_output:
                self._log(f"\n  Output: {output_dir}", "success")

        self._log(f"\n{'=' * 60}", "header")
        self._log("  DONE", "header")
        self._log(f"{'=' * 60}", "header")

    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = XMLHealthCheckerApp()
    app.run()


if __name__ == "__main__":
    main()
