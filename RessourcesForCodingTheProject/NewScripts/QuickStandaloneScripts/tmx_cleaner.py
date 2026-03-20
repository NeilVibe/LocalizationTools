#!/usr/bin/env python3
"""
TMX Cleaner — Standalone script to strip ALL CAT tool markup from TMX files.

Strips MemoQ, Trados, Phrase, Wordfast, and generic placeholder formats
from <seg> contents, producing clean plain text with only real content
preserved ({placeholders}, %params#, &lt;br/&gt;, etc.).

Usage:
    python tmx_cleaner.py <file_or_folder>       # Clean TMX file(s) in-place
    python tmx_cleaner.py <file_or_folder> --dry  # Preview changes without writing

Handles: <ph>, <bpt>/<ept>, <it>, <x/>, <g>, <ph type='fmt'>,
         self-closing <ph/>, MemoQ mq:rxt/mq:rxt-req/mq:tag,
         Trados/Phrase/Wordfast formats, zero-width chars, newline normalization.
"""
from __future__ import annotations

import os
import re
import html
import stat
import sys
import argparse
from lxml import etree


# =============================================================================
# COMPILED REGEX PATTERNS
# =============================================================================

# Segment boundary
SEG_RE = re.compile(r'(<seg[^>]*>)(.*?)(</seg>)', re.DOTALL | re.IGNORECASE)

# Zero-width characters (ZWSP, ZWNJ, ZWJ, Word Joiner, BOM)
ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')

# --- MemoQ Staticinfo/Item/Character bpt/ept pairs ---
# Matches BOTH quote styles:
#   &quot;...&quot;  (HTML-escaped quotes, common in TMX files)
#   "..."          (plain quotes, common in Excel-exported data)
# Matches ANY StaticInfo category: Knowledge, Item, Character, etc.
# → {StaticInfo:Category:ID#inner_text}
#
# Pattern A: &quot; escaped quotes
MEMOQ_BPT_EPT_ESCAPED_RE = re.compile(
    r'<bpt\b[^>]*>'
    r'&lt;mq:rxt(?:-req)?\s+displaytext=&quot;[^&]*&quot;\s+'
    r'val=&quot;\{Static[Ii]nfo:(\w+):([^#}]+)#&quot;&gt;</bpt>'
    r'(.*?)'
    r'<ept\b[^>]*>.*?</ept>',
    flags=re.DOTALL | re.IGNORECASE
)
# Pattern B: plain " quotes
MEMOQ_BPT_EPT_PLAIN_RE = re.compile(
    r'<bpt\b[^>]*>'
    r'&lt;mq:rxt(?:-req)?\s+displaytext="[^"]*"\s+'
    r'val="\{Static[Ii]nfo:(\w+):([^#}]+)#"&gt;</bpt>'
    r'(.*?)'
    r'<ept\b[^>]*>.*?</ept>',
    flags=re.DOTALL | re.IGNORECASE
)

# --- Generic <bpt>...<ept> pairs (Trados bold/italic/etc.) ---
# Keep inner text between the pair, discard the tags
GENERIC_BPT_EPT_RE = re.compile(
    r'<bpt\b[^>]*>[^<]*</bpt>(.*?)<ept\b[^>]*>[^<]*</ept>',
    flags=re.DOTALL | re.IGNORECASE
)

# --- Non-fmt <ph>...</ph> (captures inner content) ---
PH_RE = re.compile(
    r'<ph\b(?![^>]*\btype=[\'"]fmt[\'"])[^>]*>(.*?)</ph>',
    flags=re.DOTALL | re.IGNORECASE
)

# --- Self-closing <ph .../> ---
PH_SELFCLOSE_RE = re.compile(
    r'<ph\b[^>]*/\s*>',
    flags=re.IGNORECASE
)

# --- <ph type='fmt'> (MemoQ formatting whitespace) ---
PH_FMT_RE = re.compile(
    r"<ph\b[^>]*\btype=['\"]fmt['\"][^>]*>.*?</ph>",
    flags=re.DOTALL | re.IGNORECASE
)

# --- <it> tags (Trados isolated tags) ---
IT_RE = re.compile(
    r'<it\b[^>]*>.*?</it>',
    flags=re.DOTALL | re.IGNORECASE
)

# --- <x/> self-closing tags ---
X_RE = re.compile(
    r'<x\b[^>]*/?>',
    flags=re.IGNORECASE
)

# --- <g>text</g> tags (keep inner text) ---
G_RE = re.compile(
    r'<g\b[^>]*>(.*?)</g>',
    flags=re.DOTALL | re.IGNORECASE
)

# --- Formatting content detection inside decoded <ph> ---
# Word/XLIFF formatting like <cf ...>, </cf>, <b>, </b>, <i>, </i>, etc.
FORMATTING_CONTENT_RE = re.compile(
    r'^<(?:cf\b|/cf|b>|/b>|i>|/i>|u>|/u>|sub>|/sub>|sup>|/sup>)',
    flags=re.IGNORECASE
)

# --- BR tag normalization ---
BR_VARIANTS_RE = re.compile(
    r'<\s*br\s*/?\s*>|'           # <br>, <br/>, <br />, etc.
    r'<\s*br\s*/(?=\s|[^>\s])|'   # <br/ (malformed, no >)
    r'<\s*br(?=\s+[^/>\s])|'      # <br (malformed)
    r'br\s*/\s*>|'                # br/> missing opening <
    r'&lt;\s*br\s*/?\s*&gt;|'     # &lt;br/&gt; variants
    r'&amp;lt;br\s*/&amp;gt;',    # double-escaped variants
    flags=re.IGNORECASE
)


# =============================================================================
# CORE CLEANING FUNCTION
# =============================================================================

def clean_segment(content: str) -> str:
    """
    Clean a single <seg> content string.
    Strips all CAT tool markup, returns plain text.

    This is the core function — everything else is file I/O around it.
    """
    # 1) Strip zero-width characters
    content = ZERO_WIDTH_RE.sub('', content)

    # 2) MemoQ StaticInfo bpt/ept → {StaticInfo:Category:ID#inner}
    def _staticinfo_repl(m):
        category, ident, inner = m.group(1), m.group(2), m.group(3)
        return f'{{StaticInfo:{category}:{ident}#{inner}}}'
    content = MEMOQ_BPT_EPT_ESCAPED_RE.sub(_staticinfo_repl, content)
    content = MEMOQ_BPT_EPT_PLAIN_RE.sub(_staticinfo_repl, content)

    # 3) Generic <bpt>...<ept> pairs → keep inner text
    content = GENERIC_BPT_EPT_RE.sub(r'\1', content)

    # 4) Non-fmt <ph>...</ph> → smart 5-priority extraction
    def _ph_repl(m):
        ph_inner = m.group(1)
        if not ph_inner or ph_inner.isspace():
            return ''
        decoded = html.unescape(ph_inner)

        # P1: extract val="..."
        vm = re.search(r'val="([^"]+)"', decoded)
        if vm:
            val = vm.group(1)
            # Re-encode & to preserve entities like &desc;
            val = val.replace('&', '&amp;')
            return val

        # P2: formatting content (cf, b, i, etc.) → remove
        if FORMATTING_CONTENT_RE.search(decoded):
            return ''

        # P3: displaytext with no val → extract displaytext
        dm = re.search(r'displaytext="([^"]+)"', decoded)
        if dm:
            return dm.group(1)

        # P4: structural XML tag (NOT <br/>) → remove
        stripped = decoded.strip()
        if (stripped.startswith('<') and stripped.endswith('>')
                and not re.match(r'<\s*br\s*/?\s*>', stripped, re.IGNORECASE)):
            return ''

        # P5: keep raw inner text as-is (NEVER delete real content)
        return ph_inner

    content = PH_RE.sub(_ph_repl, content)

    # 5) Self-closing <ph .../> → remove
    content = PH_SELFCLOSE_RE.sub('', content)

    # 6) <ph type='fmt'> → remove
    content = PH_FMT_RE.sub('', content)

    # 7) <it> tags → remove
    content = IT_RE.sub('', content)

    # 8) <x/> tags → remove
    content = X_RE.sub('', content)

    # 9) <g>text</g> → keep inner text
    content = G_RE.sub(r'\1', content)

    # 10) Normalize newlines → &lt;br/&gt;
    content = re.sub(r'\r\n|\r|\n', '&lt;br/&gt;', content)
    content = content.replace('\\n', '&lt;br/&gt;')

    # 11) Normalize all <br> variants → &lt;br/&gt;
    content = BR_VARIANTS_RE.sub('&lt;br/&gt;', content)

    return content


def clean_tmx_string(tmx_text: str) -> str:
    """Clean all <seg> contents in a TMX string."""
    def _seg_repl(m):
        open_tag, content, close_tag = m.groups()
        return f"{open_tag}{clean_segment(content)}{close_tag}"
    return SEG_RE.sub(_seg_repl, tmx_text)


# =============================================================================
# FILE I/O
# =============================================================================

def detect_encoding(raw_bytes: bytes) -> str:
    """Detect encoding from BOM or default to utf-8."""
    if raw_bytes.startswith(b'\xff\xfe') or raw_bytes.startswith(b'\xfe\xff'):
        return 'utf-16'
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    return 'utf-8'


def read_file(path: str) -> str:
    """Read a file with auto-detected encoding."""
    raw = open(path, 'rb').read()
    enc = detect_encoding(raw)
    try:
        return raw.decode(enc)
    except UnicodeDecodeError:
        return raw.decode('utf-8', errors='replace')


def make_writable(path: str):
    """Ensure file is writable."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass


def clean_and_write(fpath: str, dry_run: bool = False) -> tuple[int, int]:
    """
    Clean a single TMX file. Returns (segments_found, segments_changed).
    """
    raw_text = read_file(fpath)

    # Clean
    cleaned = clean_tmx_string(raw_text)

    # Count changes
    orig_segs = SEG_RE.findall(raw_text)
    new_segs = SEG_RE.findall(cleaned)
    changed = sum(1 for o, n in zip(orig_segs, new_segs) if o[1] != n[1])

    if dry_run:
        if changed > 0:
            print(f"  [DRY] Would change {changed}/{len(orig_segs)} segments in: {fpath}")
            # Show first 3 changes
            shown = 0
            for o, n in zip(orig_segs, new_segs):
                if o[1] != n[1] and shown < 3:
                    print(f"    BEFORE: {o[1][:120]}")
                    print(f"    AFTER:  {n[1][:120]}")
                    print()
                    shown += 1
        else:
            print(f"  [DRY] No changes needed: {fpath}")
        return len(orig_segs), changed

    if changed == 0:
        print(f"  [OK] Already clean: {fpath}")
        return len(orig_segs), 0

    # Re-structure with lxml for clean output
    body_only = re.sub(r'^<\?xml[^>]*\?>\s*', '', cleaned, flags=re.MULTILINE)
    body_only = re.sub(r'<!DOCTYPE[^>]*>\s*', '', body_only, flags=re.IGNORECASE)

    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    try:
        root = etree.fromstring(body_only.encode('utf-8'), parser=parser)
        make_writable(fpath)
        tree = etree.ElementTree(root)
        tree.write(
            fpath,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
            doctype='<!DOCTYPE tmx SYSTEM "tmx14.dtd">'
        )
    except Exception:
        # Fallback: write cleaned text as-is
        make_writable(fpath)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(cleaned)

    print(f"  [CLEANED] {changed}/{len(orig_segs)} segments changed: {fpath}")
    return len(orig_segs), changed


def clean_path(path: str, dry_run: bool = False):
    """Clean a single file or all TMX files in a folder recursively."""
    if os.path.isfile(path):
        if path.lower().endswith('.tmx'):
            clean_and_write(path, dry_run)
        else:
            print(f"[ERROR] Not a TMX file: {path}")
    elif os.path.isdir(path):
        total_files = 0
        total_segs = 0
        total_changed = 0
        for dirpath, _, filenames in os.walk(path):
            for fn in filenames:
                if fn.lower().endswith('.tmx'):
                    fpath = os.path.join(dirpath, fn)
                    segs, changed = clean_and_write(fpath, dry_run)
                    total_files += 1
                    total_segs += segs
                    total_changed += changed
        print(f"\n[DONE] {total_files} files, {total_segs} segments, {total_changed} changed")
    else:
        print(f"[ERROR] Path not found: {path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='TMX Cleaner — Strip all CAT tool markup from TMX files'
    )
    parser.add_argument('path', help='TMX file or folder to clean')
    parser.add_argument('--dry', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    clean_path(args.path, dry_run=args.dry)


if __name__ == '__main__':
    main()
