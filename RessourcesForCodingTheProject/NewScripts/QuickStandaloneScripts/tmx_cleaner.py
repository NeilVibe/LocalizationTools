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
        category, ident, inner = m.group(1).strip(), m.group(2).strip(), m.group(3)
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
    with open(path, 'rb') as f:
        raw = f.read()
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
# TMX → EXCEL CONVERSION (clean + dedup + export)
# =============================================================================

def parse_tmx_to_rows(fpath: str) -> list[dict]:
    """
    Parse a TMX file into a list of row dicts.
    Each row: {changedate, creationdate, creationid, changeid, client, project,
               domain, subject, corrected, aligned, x_document, x_context,
               ko_seg, tgt_seg, tgt_lang}

    Cleans all <seg> contents during extraction.
    """
    raw_text = read_file(fpath)

    # Strip XML decl and DOCTYPE
    body = re.sub(r'^<\?xml[^>]*\?>\s*', '', raw_text, flags=re.MULTILINE)
    body = re.sub(r'<!DOCTYPE[^>]*>\s*', '', body, flags=re.IGNORECASE)

    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    try:
        root = etree.fromstring(body.encode('utf-8'), parser=parser)
    except Exception as e:
        print(f"[ERROR] Cannot parse {fpath}: {e}")
        return []

    XML_NS = "http://www.w3.org/XML/1998/namespace"
    rows = []

    for tu in root.iter('tu'):
        row = {
            'changedate': tu.get('changedate', ''),
            'creationdate': tu.get('creationdate', ''),
            'creationid': tu.get('creationid', ''),
            'changeid': tu.get('changeid', ''),
            'client': '',
            'project': '',
            'domain': '',
            'subject': '',
            'corrected': '',
            'aligned': '',
            'x_document': '',
            'x_context': '',
            'ko_seg': '',
            'tgt_seg': '',
            'tgt_lang': '',
        }

        # Extract <prop> values
        for prop in tu.findall('prop'):
            ptype = prop.get('type', '')
            pval = (prop.text or '').strip()
            if ptype == 'client':
                row['client'] = pval
            elif ptype == 'project':
                row['project'] = pval
            elif ptype == 'domain':
                row['domain'] = pval
            elif ptype == 'subject':
                row['subject'] = pval
            elif ptype == 'corrected':
                row['corrected'] = pval
            elif ptype == 'aligned':
                row['aligned'] = pval
            elif ptype == 'x-document':
                row['x_document'] = pval
            elif ptype == 'x-context':
                row['x_context'] = pval

        # Extract <tuv> segments
        for tuv in tu.findall('tuv'):
            lang = tuv.get(f'{{{XML_NS}}}lang', tuv.get('lang', '')).lower()
            seg = tuv.find('seg')
            if seg is None:
                continue

            # Get raw seg content (including child tags) as string
            seg_text = etree.tostring(seg, encoding='unicode', method='xml')
            # Strip <seg> and </seg> wrappers
            seg_text = re.sub(r'^<seg[^>]*>', '', seg_text)
            seg_text = re.sub(r'</seg>$', '', seg_text)
            seg_text = seg_text.strip()

            # Clean the segment
            cleaned = clean_segment(seg_text)

            if lang == 'ko':
                row['ko_seg'] = cleaned
            else:
                row['tgt_seg'] = cleaned
                row['tgt_lang'] = lang

        rows.append(row)

    return rows


def dedup_rows(rows: list[dict]) -> list[dict]:
    """
    Deduplicate by (x_context, ko_seg).
    Keep the row with the LATEST changedate.
    """
    # Warn if most rows lack x-context (dedup becomes KO-text-only)
    empty_ctx = sum(1 for r in rows if not r['x_context'])
    if rows and empty_ctx > len(rows) * 0.5:
        print(f"  WARNING: {empty_ctx}/{len(rows)} rows have no x-context — dedup is by KO text only")

    seen: dict[tuple, dict] = {}

    for row in rows:
        key = (row['x_context'], row['ko_seg'])
        if key in seen:
            # Keep the one with later changedate (string compare works for YYYYMMDDTHHMMSSZ format)
            if row['changedate'] > seen[key]['changedate']:
                seen[key] = row
        else:
            seen[key] = row

    return list(seen.values())


def write_excel(rows: list[dict], output_path: str):
    """Write rows to Excel using xlsxwriter."""
    import xlsxwriter

    wb = xlsxwriter.Workbook(output_path)
    ws = wb.add_worksheet('TMX Clean')

    # Headers
    headers = [
        'KO (Source)', 'EN (Target)', 'x-context', 'x-document',
        'changedate', 'creationdate', 'changeid', 'creationid',
        'client', 'project', 'domain', 'subject',
        'corrected', 'aligned', 'tgt_lang'
    ]
    keys = [
        'ko_seg', 'tgt_seg', 'x_context', 'x_document',
        'changedate', 'creationdate', 'changeid', 'creationid',
        'client', 'project', 'domain', 'subject',
        'corrected', 'aligned', 'tgt_lang'
    ]

    # Header format
    hdr_fmt = wb.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
    cell_fmt = wb.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})

    for col, h in enumerate(headers):
        ws.write(0, col, h, hdr_fmt)

    for row_idx, row in enumerate(rows, 1):
        for col, key in enumerate(keys):
            ws.write(row_idx, col, row.get(key, ''), cell_fmt)

    # Column widths
    ws.set_column(0, 0, 50)   # KO
    ws.set_column(1, 1, 50)   # EN
    ws.set_column(2, 2, 22)   # x-context
    ws.set_column(3, 3, 30)   # x-document
    ws.set_column(4, 5, 20)   # dates
    ws.set_column(6, 7, 15)   # ids
    ws.set_column(8, 14, 12)  # props

    # Autofilter
    ws.autofilter(0, 0, len(rows), len(headers) - 1)

    wb.close()
    print(f"[EXCEL] Written {len(rows)} rows to: {output_path}")


def clean_and_convert_to_excel(fpath: str):
    """
    Full pipeline: TMX → clean → dedup → Excel.
    Output file: same name as input but _clean.xlsx
    """
    print(f"[1/3] Parsing and cleaning: {fpath}")
    rows = parse_tmx_to_rows(fpath)
    print(f"       Found {len(rows)} TU entries")

    print(f"[2/3] Deduplicating by (x-context + KO seg), keeping latest changedate...")
    before = len(rows)
    rows = dedup_rows(rows)
    dupes = before - len(rows)
    print(f"       {dupes} duplicates removed → {len(rows)} unique rows")

    # Output path: same name but _clean.xlsx
    base = os.path.splitext(fpath)[0]
    output_path = f"{base}_clean.xlsx"

    print(f"[3/3] Writing Excel...")
    write_excel(rows, output_path)
    print(f"\n[DONE] {output_path}")
    return output_path


# =============================================================================
# CLI
# =============================================================================

def pick_file():
    """Open a tkinter file dialog to select a TMX file."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    fpath = filedialog.askopenfilename(
        title="Select TMX file to clean and convert to Excel",
        filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")]
    )
    root.destroy()
    return fpath


def main():
    parser = argparse.ArgumentParser(
        description='TMX Cleaner — Strip CAT tool markup from TMX, convert to Excel'
    )
    parser.add_argument('path', nargs='?', default=None,
                        help='TMX file or folder (opens file picker if omitted)')
    parser.add_argument('--dry', action='store_true',
                        help='Preview changes without writing')
    parser.add_argument('--tmx-only', action='store_true',
                        help='Clean TMX in-place without Excel conversion')
    args = parser.parse_args()

    path = args.path
    if not path:
        path = pick_file()
        if not path:
            print("[CANCELLED] No file selected.")
            return
        # File picker → always do Excel conversion
        clean_and_convert_to_excel(path)
        return

    if args.tmx_only:
        clean_path(path, dry_run=args.dry)
    else:
        if os.path.isfile(path):
            clean_and_convert_to_excel(path)
        else:
            # Folder mode: process each TMX
            for dirpath, _, filenames in os.walk(path):
                for fn in filenames:
                    if fn.lower().endswith('.tmx'):
                        clean_and_convert_to_excel(os.path.join(dirpath, fn))


if __name__ == '__main__':
    main()
