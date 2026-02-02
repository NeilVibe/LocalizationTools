"""
Korean MISS String Extractor.

Extract Korean strings from target XML that do NOT exist in source XML.
Used to identify untranslated or missing localization entries.

REWRITE v2.0 - Correct logic:
1. Build StringID -> File path index from EXPORT folder
2. Parse SOURCE file to build (StringID, StrOrigin) lookup
3. Parse TARGET file to find all Korean LocStr elements
4. Match against SOURCE lookup
5. Filter by excluded paths using EXPORT index
6. PRINT results to terminal (not just GUI log)
"""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

from .xml_parser import sanitize_xml_content, iter_locstr_elements
from .text_utils import normalize_for_matching


# Korean character ranges:
# - Hangul Syllables: AC00-D7AF (most common)
# - Hangul Jamo: 1100-11FF (consonants/vowels)
# - Hangul Compatibility Jamo: 3130-318F (compatibility)
KOREAN_FULL_REGEX = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]')


def contains_korean(text: str) -> bool:
    """
    Check if text contains any Korean characters.

    Covers full Korean Unicode ranges:
    - Hangul Syllables (AC00-D7AF)
    - Hangul Jamo (1100-11FF)
    - Hangul Compatibility Jamo (3130-318F)

    Args:
        text: Text to check

    Returns:
        True if text contains Korean characters
    """
    if not text:
        return False
    return bool(KOREAN_FULL_REGEX.search(text))


def normalize_strorigin(text: str) -> str:
    """
    Normalize StrOrigin text for comparison.

    Uses the canonical normalize_for_matching() from text_utils.

    Args:
        text: StrOrigin text to normalize

    Returns:
        Normalized text string (lowercase, whitespace normalized)
    """
    return normalize_for_matching(text)


def _parse_xml_to_root(xml_path: Path) -> Optional[ET.Element]:
    """
    Parse XML file with sanitization.

    Args:
        xml_path: Path to XML file

    Returns:
        Root element or None if parsing fails
    """
    try:
        content = xml_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try with latin-1 fallback
        content = xml_path.read_text(encoding='latin-1')

    content = sanitize_xml_content(content)

    if USING_LXML:
        wrapped = f"<ROOT>\n{content}\n</ROOT>"
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(huge_tree=True)
            )
        except ET.XMLSyntaxError:
            # Try recovery mode
            try:
                return ET.fromstring(
                    wrapped.encode("utf-8"),
                    parser=ET.XMLParser(recover=True, huge_tree=True)
                )
            except Exception:
                return None
    else:
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            return None


def build_export_index(
    export_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    """
    Build StringID -> File path index from EXPORT folder.

    Scans all .loc.xml files in EXPORT folder and builds an index
    mapping each StringID to its file path (e.g., "System/Gimmick/file.xml").

    Args:
        export_folder: Path to export__ folder
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping StringID to relative file path (e.g., "System/Gimmick/item.loc.xml")
    """
    if not export_folder.exists():
        print(f"[EXPORT INDEX] ERROR: Export folder not found: {export_folder}")
        return {}

    stringid_to_filepath: Dict[str, str] = {}
    xml_files = list(export_folder.rglob("*.loc.xml"))
    total_files = len(xml_files)

    print(f"[EXPORT INDEX] Scanning {total_files} .loc.xml files in: {export_folder}")

    for i, xml_file in enumerate(xml_files):
        if progress_callback and i % 100 == 0:
            progress_callback(f"Indexing EXPORT files... {i+1}/{total_files}")

        try:
            # Get relative path from export folder
            rel_path = xml_file.relative_to(export_folder)
            rel_path_str = str(rel_path).replace("\\", "/")

            root = _parse_xml_to_root(xml_file)
            if root is None:
                continue

            for elem in iter_locstr_elements(root):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID') or '')
                if string_id:
                    stringid_to_filepath[string_id] = rel_path_str

        except Exception as e:
            print(f"[EXPORT INDEX] Warning: Failed to parse {xml_file}: {e}")
            continue

    print(f"[EXPORT INDEX] Indexed {len(stringid_to_filepath)} StringIDs")
    return stringid_to_filepath


def _build_source_lookup(root: ET.Element) -> Set[Tuple[str, str]]:
    """
    Build lookup set of (StringID, normalized_StrOrigin) from source XML.

    Args:
        root: Root element of source XML

    Returns:
        Set of (StringID, normalized_StrOrigin) tuples
    """
    lookup: Set[Tuple[str, str]] = set()

    for elem in iter_locstr_elements(root):
        string_id = (elem.get('StringId') or elem.get('StringID') or
                    elem.get('stringid') or elem.get('STRINGID') or '')
        str_origin = (elem.get('StrOrigin') or elem.get('strorigin') or
                     elem.get('STRORIGIN') or '')

        if string_id:
            normalized_origin = normalize_strorigin(str_origin)
            lookup.add((string_id, normalized_origin))

    return lookup


def _collect_korean_locstr(root: ET.Element) -> List[Dict]:
    """
    Collect all LocStr elements where Str attribute contains Korean.

    Args:
        root: Root element of target XML

    Returns:
        List of dicts with LocStr data (string_id, str_origin, str_value, elem)
    """
    korean_elements: List[Dict] = []

    for elem in iter_locstr_elements(root):
        str_value = (elem.get('Str') or elem.get('str') or
                    elem.get('STR') or '')

        if contains_korean(str_value):
            string_id = (elem.get('StringId') or elem.get('StringID') or
                        elem.get('stringid') or elem.get('STRINGID') or '')
            str_origin = (elem.get('StrOrigin') or elem.get('strorigin') or
                         elem.get('STRORIGIN') or '')

            korean_elements.append({
                "string_id": string_id,
                "str_origin": str_origin,
                "str_value": str_value,
                "elem": elem,
            })

    return korean_elements


def _filter_by_excluded_paths(
    elements: List[Dict],
    stringid_to_filepath: Dict[str, str],
    excluded_paths: Optional[List[str]]
) -> Tuple[List[Dict], int, List[Dict]]:
    """
    Filter out elements whose File path (from EXPORT index) starts with excluded paths.

    Args:
        elements: List of LocStr dicts
        stringid_to_filepath: StringID -> file path mapping from EXPORT index
        excluded_paths: List of path prefixes to exclude (e.g., "System/MultiChange")

    Returns:
        Tuple of (filtered elements, count of filtered out, filtered_out_elements)
    """
    if not excluded_paths:
        return elements, 0, []

    filtered: List[Dict] = []
    filtered_out: List[Dict] = []

    for item in elements:
        string_id = item["string_id"]
        file_path = stringid_to_filepath.get(string_id, "")
        # Normalize path separators and lowercase for case-insensitive matching
        file_path_normalized = file_path.replace('\\', '/').lower()

        excluded = False
        for exc_path in excluded_paths:
            exc_path_normalized = exc_path.replace('\\', '/').lower()
            if file_path_normalized.startswith(exc_path_normalized):
                excluded = True
                item["excluded_path"] = exc_path
                item["file_path"] = file_path
                filtered_out.append(item)
                break

        if not excluded:
            item["file_path"] = file_path
            filtered.append(item)

    return filtered, len(filtered_out), filtered_out


def _write_output_xml(elements: List[Dict], output_path: Path) -> None:
    """
    Write LocStr elements to output XML file.

    Args:
        elements: List of LocStr dicts with 'elem' key
        output_path: Path for output file
    """
    # Build XML content
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<LocStrList>')

    for item in elements:
        elem = item["elem"]
        # Reconstruct LocStr element as string
        attribs = []
        for key, value in elem.attrib.items():
            # Escape special characters in attribute values
            escaped_value = (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            attribs.append(f'{key}="{escaped_value}"')

        attrib_str = ' '.join(attribs)
        lines.append(f'  <LocStr {attrib_str} />')

    lines.append('</LocStrList>')

    # Write to file
    output_path.write_text('\n'.join(lines), encoding='utf-8')


def _print_separator(char: str = "=", length: int = 80):
    """Print a separator line."""
    print(char * length)


def _print_sample_items(items: List[Dict], title: str, max_items: int = 10):
    """Print sample items with details."""
    if not items:
        return

    print(f"\n{title} (showing first {min(len(items), max_items)} of {len(items)}):")
    print("-" * 60)

    for i, item in enumerate(items[:max_items]):
        string_id = item.get("string_id", "N/A")
        str_origin = item.get("str_origin", "")[:50]
        str_value = item.get("str_value", "")[:50]
        file_path = item.get("file_path", "N/A")

        print(f"  [{i+1}] StringID: {string_id}")
        print(f"      File: {file_path}")
        if str_origin:
            print(f"      StrOrigin: {str_origin}...")
        if str_value:
            print(f"      Str (KOR): {str_value}...")
        print()


def extract_korean_misses(
    source_file: str,
    target_file: str,
    output_file: str,
    export_folder: Optional[str] = None,
    excluded_paths: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict:
    """
    Extract Korean strings from target that do NOT exist in source.

    CORRECT LOGIC:
    1. Build StringID -> File path index from EXPORT folder
    2. Parse SOURCE file to build (StringID, StrOrigin) lookup
    3. Parse TARGET file to find all Korean LocStr elements
    4. Match against SOURCE lookup (StringID + normalized StrOrigin)
    5. Filter by excluded paths using EXPORT index
    6. PRINT detailed results to terminal
    7. Write remaining MISS nodes to output file

    Args:
        source_file: Path to source XML file (reference/corrections)
        target_file: Path to target XML file (contains Korean strings to check)
        output_file: Path for output XML file (will contain MISS strings)
        export_folder: Path to EXPORT folder for StringID -> File path mapping
                       If None, uses config.EXPORT_FOLDER
        excluded_paths: List of path prefixes to exclude from results
            (e.g., ["System/MultiChange", "System/Gimmick"])
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with statistics:
        {
            "total_target_korean": int,  # Korean strings in target
            "hits": int,                  # Matched with source
            "misses_before_filter": int,  # Misses before path filter
            "filtered_out": int,          # Removed by path filter
            "final_misses": int,          # Written to output
            "excluded_paths_used": list   # Paths that were filtered
        }

    Raises:
        FileNotFoundError: If source or target file doesn't exist
        ValueError: If XML parsing fails
    """
    source_path = Path(source_file)
    target_path = Path(target_file)
    output_path = Path(output_file)

    # Get export folder from config if not provided
    if export_folder is None:
        import config
        export_folder_path = config.EXPORT_FOLDER
    else:
        export_folder_path = Path(export_folder)

    # Print header to terminal
    _print_separator("=")
    print("KOREAN MISS EXTRACTOR - Terminal Debug Output")
    _print_separator("=")
    print()
    print("[FILE SELECTION]")
    print(f"  SOURCE file (reference): {source_path}")
    print(f"    - Absolute path: {source_path.absolute()}")
    print(f"    - Exists: {source_path.exists()}")
    if source_path.exists():
        source_size = source_path.stat().st_size
        print(f"    - File size: {source_size:,} bytes ({source_size / 1024:.1f} KB)")
    print()
    print(f"  TARGET file (to check): {target_path}")
    print(f"    - Absolute path: {target_path.absolute()}")
    print(f"    - Exists: {target_path.exists()}")
    if target_path.exists():
        target_size = target_path.stat().st_size
        print(f"    - File size: {target_size:,} bytes ({target_size / 1024:.1f} KB)")
    print()
    print(f"  OUTPUT file: {output_path}")
    print(f"    - Absolute path: {output_path.absolute()}")
    print(f"    - Output directory exists: {output_path.parent.exists()}")
    print()
    print("[EXPORT FOLDER CONFIGURATION]")
    print(f"  Export folder: {export_folder_path}")
    print(f"    - Absolute path: {export_folder_path.absolute() if export_folder_path.exists() else 'N/A'}")
    print(f"    - Exists: {export_folder_path.exists()}")
    if export_folder_path.exists():
        loc_xml_count = len(list(export_folder_path.rglob("*.loc.xml")))
        print(f"    - Contains {loc_xml_count} .loc.xml files")
    print()
    print("[EXCLUSION PATHS CONFIGURATION]")
    if excluded_paths:
        for i, exc_path in enumerate(excluded_paths, 1):
            print(f"  [{i}] {exc_path}")
        print(f"  Note: StringIDs from these paths will be EXCLUDED from final misses")
    else:
        print("  (No exclusion paths configured - all misses will be included)")
    _print_separator("-")

    # Validate input files exist
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_file}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Build EXPORT index (StringID -> File path)
    print("\n[STEP 1] Building EXPORT index (StringID -> File path mapping)...")
    print("  Purpose: Map each StringID to its file path for exclusion filtering")
    if progress_callback:
        progress_callback("Building EXPORT index...")

    stringid_to_filepath = build_export_index(export_folder_path, progress_callback)

    print(f"\n[EXPORT INDEX RESULT]")
    print(f"  Total StringIDs indexed: {len(stringid_to_filepath):,}")
    if stringid_to_filepath:
        # Show sample paths
        sample_paths = list(set(stringid_to_filepath.values()))[:5]
        print(f"  Sample file paths in index:")
        for sp in sample_paths:
            print(f"    - {sp}")
    else:
        print("  [WARNING] EXPORT index is empty - path filtering will not work!")

    # Step 2: Parse source XML and build lookup
    print("\n[STEP 2] Parsing SOURCE file (building reference lookup)...")
    print("  Purpose: Build set of (StringID, StrOrigin) tuples from SOURCE")
    print("  These are the translations we HAVE (reference)")
    if progress_callback:
        progress_callback("Parsing source file...")

    source_root = _parse_xml_to_root(source_path)
    if source_root is None:
        raise ValueError(f"Failed to parse source XML: {source_file}")

    source_lookup = _build_source_lookup(source_root)

    print(f"\n[SOURCE LOOKUP RESULT]")
    print(f"  Total (StringID, StrOrigin) pairs: {len(source_lookup):,}")
    print(f"  Matching logic: TUPLE match - both StringID AND StrOrigin must match")
    print(f"  StrOrigin normalization: lowercase + whitespace collapse + HTML unescape")
    if source_lookup:
        # Show sample entries
        sample_entries = list(source_lookup)[:3]
        print(f"  Sample lookup entries:")
        for sid, sorigin in sample_entries:
            print(f"    - StringID: {sid}")
            print(f"      StrOrigin (normalized): {sorigin[:60]}{'...' if len(sorigin) > 60 else ''}")

    # Step 3: Parse target XML and collect Korean LocStr
    print("\n[STEP 3] Parsing TARGET file and collecting Korean strings...")
    print("  Purpose: Find all LocStr elements where 'Str' attribute contains Korean")
    print("  Korean detection: Unicode ranges AC00-D7AF, 1100-11FF, 3130-318F")
    if progress_callback:
        progress_callback("Parsing target file...")

    target_root = _parse_xml_to_root(target_path)
    if target_root is None:
        raise ValueError(f"Failed to parse target XML: {target_file}")

    korean_elements = _collect_korean_locstr(target_root)
    total_target_korean = len(korean_elements)

    print(f"\n[TARGET KOREAN STRINGS RESULT]")
    print(f"  Total LocStr elements with Korean: {total_target_korean:,}")
    if korean_elements:
        # Count unique StringIDs
        unique_string_ids = len(set(e["string_id"] for e in korean_elements))
        print(f"  Unique StringIDs: {unique_string_ids:,}")
        print(f"  Sample Korean strings from TARGET:")
        for e in korean_elements[:3]:
            print(f"    - StringID: {e['string_id']}")
            print(f"      Str (Korean): {e['str_value'][:50]}{'...' if len(e['str_value']) > 50 else ''}")

    # Step 4: Find HITS and MISSES
    print("\n[STEP 4] Matching TARGET against SOURCE lookup...")
    print("  Matching algorithm:")
    print("    1. For each Korean LocStr in TARGET:")
    print("    2. Create key = (StringID, normalize(StrOrigin))")
    print("    3. Check if key exists in SOURCE lookup set")
    print("    4. If YES -> HIT (string exists in source)")
    print("    5. If NO  -> MISS (string NOT in source)")
    if progress_callback:
        progress_callback("Matching against source...")

    hits: List[Dict] = []
    misses: List[Dict] = []

    for item in korean_elements:
        string_id = item["string_id"]
        str_origin = item["str_origin"]

        normalized_origin = normalize_strorigin(str_origin)
        key = (string_id, normalized_origin)

        if key in source_lookup:
            hits.append(item)
        else:
            misses.append(item)

    hits_count = len(hits)
    misses_before_filter = len(misses)

    print(f"\n[MATCHING RESULT]")
    print(f"  Total Korean strings checked: {total_target_korean:,}")
    print(f"  ─────────────────────────────────────")
    print(f"  HITS (found in source):     {hits_count:,} ({hits_count/total_target_korean*100:.1f}%)" if total_target_korean > 0 else "  HITS: 0")
    print(f"  MISSES (NOT in source):     {misses_before_filter:,} ({misses_before_filter/total_target_korean*100:.1f}%)" if total_target_korean > 0 else "  MISSES: 0")
    print(f"  ─────────────────────────────────────")
    print(f"  HIT means: (StringID, StrOrigin) tuple EXISTS in SOURCE")
    print(f"  MISS means: (StringID, StrOrigin) tuple NOT FOUND in SOURCE")

    # Step 5: Filter by excluded paths
    print("\n[STEP 5] Filtering MISSES by excluded paths...")
    print("  Filtering algorithm:")
    print("    1. For each MISS, get its StringID")
    print("    2. Look up file path from EXPORT index: StringID -> path")
    print("    3. Check if path starts with any excluded path prefix")
    print("    4. If YES -> EXCLUDE (remove from results)")
    print("    5. If NO  -> KEEP (write to output)")
    if excluded_paths:
        print(f"  Excluded path prefixes:")
        for exc in excluded_paths:
            print(f"    - {exc}")
    if progress_callback:
        progress_callback("Filtering by excluded paths...")

    excluded_paths_list = excluded_paths if excluded_paths else []
    filtered_misses, filtered_out, filtered_out_items = _filter_by_excluded_paths(
        misses, stringid_to_filepath, excluded_paths_list
    )

    final_misses = len(filtered_misses)

    print(f"\n[FILTERING RESULT]")
    print(f"  MISSES before filtering: {misses_before_filter:,}")
    print(f"  Filtered OUT (excluded): {filtered_out:,}")
    print(f"  FINAL MISSES to write:   {final_misses:,}")
    if filtered_out > 0:
        # Count by exclusion path
        exclusion_counts: Dict[str, int] = {}
        for item in filtered_out_items:
            exc_path = item.get("excluded_path", "unknown")
            exclusion_counts[exc_path] = exclusion_counts.get(exc_path, 0) + 1
        print(f"  Exclusion breakdown:")
        for exc_path, count in sorted(exclusion_counts.items()):
            print(f"    - {exc_path}: {count:,} items")

    # Step 6: Print detailed results to terminal
    print("\n")
    _print_separator("=")
    print("FINAL RESULTS SUMMARY")
    _print_separator("=")
    print()
    print("┌─────────────────────────────────────────────────────────────┐")
    print(f"│  SOURCE file: {source_path.name:<44} │")
    print(f"│  TARGET file: {target_path.name:<44} │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│  Source lookup entries:          {len(source_lookup):>10,}              │")
    print(f"│  Korean strings in Target:       {total_target_korean:>10,}              │")
    print("├─────────────────────────────────────────────────────────────┤")
    hit_pct = (hits_count/total_target_korean*100) if total_target_korean > 0 else 0
    miss_pct = (misses_before_filter/total_target_korean*100) if total_target_korean > 0 else 0
    print(f"│  HITS (in source):               {hits_count:>10,}  ({hit_pct:>5.1f}%)    │")
    print(f"│  MISSES (not in source):         {misses_before_filter:>10,}  ({miss_pct:>5.1f}%)    │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│  Filtered out (excluded paths):  {filtered_out:>10,}              │")
    print(f"│  ═══════════════════════════════════════════════════       │")
    print(f"│  FINAL MISSES (written):         {final_misses:>10,}              │")
    print("└─────────────────────────────────────────────────────────────┘")
    print()
    _print_separator("-")

    # Print sample HITS
    _print_sample_items(hits, "SAMPLE HITS (matched in source)", 5)

    # Print sample MISSES (final)
    _print_sample_items(filtered_misses, "SAMPLE FINAL MISSES (not in source)", 10)

    # Print filtered out items
    if filtered_out_items:
        print(f"\nFILTERED OUT ITEMS (excluded paths) - first 5 of {len(filtered_out_items)}:")
        print("-" * 60)
        for i, item in enumerate(filtered_out_items[:5]):
            print(f"  [{i+1}] StringID: {item.get('string_id', 'N/A')}")
            print(f"      Excluded by: {item.get('excluded_path', 'N/A')}")
            print(f"      Full path: {item.get('file_path', 'N/A')}")
            print()

    # Step 7: Write output XML
    print("\n[STEP 7] Writing output XML...")
    print(f"  Writing {final_misses:,} LocStr elements to output file")
    if progress_callback:
        progress_callback("Writing output XML...")

    _write_output_xml(filtered_misses, output_path)

    # Get output file size
    output_size = output_path.stat().st_size if output_path.exists() else 0

    print(f"\n[OUTPUT FILE RESULT]")
    print(f"  File: {output_path}")
    print(f"  Size: {output_size:,} bytes ({output_size / 1024:.1f} KB)")
    print(f"  Elements written: {final_misses:,}")

    print()
    _print_separator("=")
    print("EXTRACTION COMPLETE - ALL DEBUG INFO PRINTED TO TERMINAL")
    _print_separator("=")

    return {
        "total_target_korean": total_target_korean,
        "hits": hits_count,
        "misses_before_filter": misses_before_filter,
        "filtered_out": filtered_out,
        "final_misses": final_misses,
        "excluded_paths_used": excluded_paths_list,
    }
