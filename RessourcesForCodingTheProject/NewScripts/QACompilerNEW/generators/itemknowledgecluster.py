"""
ItemKnowledgeCluster Datasheet Generator
==========================================
Mega datasheet that clusters all item-knowledge relationships using
3-pass matching: KnowledgeKey → exact name → fuzzy difflib.

Output: Single mega-sheet per language with clusters ordered by
greedy nearest-neighbor similarity for gradient adjacency.

Columns: DataType | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID
"""

import difflib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from config import RESOURCE_FOLDER, LANGUAGE_FOLDER, DATASHEET_OUTPUT, STATUS_OPTIONS
from generators.base import (
    get_logger,
    parse_xml_file,
    iter_xml_files,
    load_language_tables,
    normalize_placeholders,
    autofit_worksheet,
    THIN_BORDER,
    resolve_translation,
    get_export_index,
    add_status_dropdown,
)
from generators.newitem import _find_knowledge_key

log = get_logger("ItemKnowledgeCluster")

# =============================================================================
# KOREAN STRING COLLECTION (for coverage tracking)
# =============================================================================

_collected_korean_strings: set = set()


def reset_korean_collection() -> None:
    global _collected_korean_strings
    _collected_korean_strings = set()


def get_collected_korean_strings() -> set:
    return _collected_korean_strings.copy()


def _collect_korean_string(text: str) -> None:
    if text:
        normalized = normalize_placeholders(text)
        if normalized:
            _collected_korean_strings.add(normalized)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ClusterRow:
    """Single row in a cluster."""
    data_type: str       # "ItemData", "KnowledgeData", "KnowledgeMatch-Exact",
                         # "KnowledgeMatch-Fuzzy(85%)", "ItemMatch-Fuzzy(82%)"
    kor_text: str
    source_file: str
    fuzzy_score: float = 0.0


@dataclass
class ItemCluster:
    """All rows belonging to one item (anchor)."""
    item_strkey: str
    item_name: str       # Anchor for inter-cluster ordering
    rows: List[ClusterRow] = field(default_factory=list)


# =============================================================================
# STATICINFO SCANNING
# =============================================================================

@dataclass
class ItemRecord:
    """Raw item data from XML."""
    strkey: str
    name: str
    desc: str
    knowledge_key: str
    source_file: str


@dataclass
class KnowledgeRecord:
    """Raw knowledge data from XML."""
    strkey: str
    name: str
    desc: str
    source_file: str


def scan_all_staticinfo(
    folder: Path,
) -> Tuple[List[ItemRecord], List[KnowledgeRecord]]:
    """Scan entire RESOURCE_FOLDER for all ItemInfo + KnowledgeInfo elements.

    Returns:
        (items, knowledges) - raw records from XML
    """
    log.info("Scanning all StaticInfo in %s", folder)
    items: List[ItemRecord] = []
    knowledges: List[KnowledgeRecord] = []
    seen_item_keys: Set[str] = set()
    seen_knowledge_keys: Set[str] = set()

    if not folder.exists():
        log.warning("Folder does not exist: %s", folder)
        return items, knowledges

    file_count = 0
    for path in iter_xml_files(folder):
        root = parse_xml_file(path)
        if root is None:
            continue
        file_count += 1
        src = path.name

        for el in root.iter("ItemInfo"):
            sk = el.get("StrKey") or ""
            if not sk or sk in seen_item_keys:
                continue
            seen_item_keys.add(sk)
            items.append(ItemRecord(
                strkey=sk,
                name=el.get("ItemName") or "",
                desc=el.get("ItemDesc") or "",
                knowledge_key=_find_knowledge_key(el),
                source_file=src,
            ))

        for el in root.iter("KnowledgeInfo"):
            sk = el.get("StrKey") or ""
            if not sk or sk in seen_knowledge_keys:
                continue
            seen_knowledge_keys.add(sk)
            knowledges.append(KnowledgeRecord(
                strkey=sk,
                name=el.get("Name") or "",
                desc=el.get("Desc") or "",
                source_file=src,
            ))

    log.info("Scanned %d files: %d items, %d knowledges",
             file_count, len(items), len(knowledges))
    return items, knowledges


# =============================================================================
# FUZZY MATCHING
# =============================================================================

def find_fuzzy_matches(
    anchor_name: str,
    all_name_index: Dict[str, List[Tuple[str, str, str, str]]],
    exclude_strkeys: Set[str],
    threshold: float = 0.80,
    max_matches: int = 5,
) -> List[Tuple[str, str, str, str, float]]:
    """Find fuzzy matches for anchor_name against all names in the index.

    Args:
        anchor_name: The name to match against
        all_name_index: {name: [(strkey, desc, source_file, tag), ...]}
                        tag = "Knowledge" or "Item"
        exclude_strkeys: StrKeys to skip (already matched in Pass 1/2)
        threshold: Minimum similarity ratio (0.0 - 1.0)
        max_matches: Maximum fuzzy matches to return

    Returns:
        List of (strkey, name, desc, source_file, score, tag) sorted by score desc
    """
    if not anchor_name:
        return []

    matches: List[Tuple[str, str, str, str, float, str]] = []

    for name, records in all_name_index.items():
        if name == anchor_name:
            continue  # Exact match handled separately
        ratio = difflib.SequenceMatcher(None, anchor_name, name).ratio()
        if ratio >= threshold:
            for strkey, desc, source_file, tag in records:
                if strkey not in exclude_strkeys:
                    matches.append((strkey, name, desc, source_file, ratio, tag))

    # Sort by score descending, limit
    matches.sort(key=lambda x: -x[4])
    return matches[:max_matches]


# =============================================================================
# CLUSTER BUILDER
# =============================================================================

def build_clusters(
    items: List[ItemRecord],
    knowledges: List[KnowledgeRecord],
) -> List[ItemCluster]:
    """Build item clusters with 3-pass knowledge matching.

    Pass 1: KnowledgeKey direct lookup
    Pass 2: Exact name match (ItemName == KnowledgeInfo.Name)
    Pass 3: Fuzzy difflib matching against ALL names (Knowledge + Item)
    """
    log.info("Building clusters...")

    # Build knowledge maps
    knowledge_by_key: Dict[str, KnowledgeRecord] = {}
    knowledge_by_name: Dict[str, List[KnowledgeRecord]] = defaultdict(list)
    for kr in knowledges:
        if kr.strkey:
            knowledge_by_key[kr.strkey] = kr
        if kr.name:
            knowledge_by_name[kr.name].append(kr)

    # Build combined name index for fuzzy matching
    # {name: [(strkey, desc, source_file, tag), ...]}
    all_name_index: Dict[str, List[Tuple[str, str, str, str]]] = defaultdict(list)
    for kr in knowledges:
        if kr.name:
            all_name_index[kr.name].append((kr.strkey, kr.desc, kr.source_file, "Knowledge"))
    for ir in items:
        if ir.name:
            all_name_index[ir.name].append((ir.strkey, ir.desc, ir.source_file, "Item"))

    clusters: List[ItemCluster] = []
    pass1_count = pass2_count = pass3_count = 0

    for item in items:
        cluster = ItemCluster(item_strkey=item.strkey, item_name=item.name)
        exclude_strkeys: Set[str] = {item.strkey}

        # ItemData rows (always)
        if item.name:
            cluster.rows.append(ClusterRow("ItemData", item.name, item.source_file))
            _collect_korean_string(item.name)
        if item.desc:
            cluster.rows.append(ClusterRow("ItemData", item.desc, item.source_file))
            _collect_korean_string(item.desc)

        # Pass 1: KnowledgeKey lookup
        if item.knowledge_key and item.knowledge_key in knowledge_by_key:
            kr = knowledge_by_key[item.knowledge_key]
            exclude_strkeys.add(kr.strkey)
            if kr.name:
                cluster.rows.append(ClusterRow("KnowledgeData", kr.name, kr.source_file))
                _collect_korean_string(kr.name)
            if kr.desc:
                cluster.rows.append(ClusterRow("KnowledgeData", kr.desc, kr.source_file))
                _collect_korean_string(kr.desc)
            pass1_count += 1

        # Pass 2: Exact name match
        if item.name and item.name in knowledge_by_name:
            for kr in knowledge_by_name[item.name]:
                if kr.strkey not in exclude_strkeys:
                    exclude_strkeys.add(kr.strkey)
                    if kr.name:
                        cluster.rows.append(ClusterRow("KnowledgeMatch-Exact", kr.name, kr.source_file))
                        _collect_korean_string(kr.name)
                    if kr.desc:
                        cluster.rows.append(ClusterRow("KnowledgeMatch-Exact", kr.desc, kr.source_file))
                        _collect_korean_string(kr.desc)
                    pass2_count += 1
                    break  # Take first non-duplicate match

        # Pass 3: Fuzzy matching across ALL names
        fuzzy_hits = find_fuzzy_matches(item.name, all_name_index, exclude_strkeys)
        for strkey, name, desc, source_file, score, src_tag in fuzzy_hits:
            pct = int(score * 100)
            tag = "KnowledgeMatch-Fuzzy" if src_tag == "Knowledge" else "ItemMatch-Fuzzy"
            dtype = f"{tag}({pct}%)"

            if name:
                cluster.rows.append(ClusterRow(dtype, name, source_file, score))
                _collect_korean_string(name)
            if desc:
                cluster.rows.append(ClusterRow(dtype, desc, source_file, score))
                _collect_korean_string(desc)
            exclude_strkeys.add(strkey)
            pass3_count += 1

        clusters.append(cluster)

    log.info("Clusters built: %d total | Pass1(KnowledgeKey): %d | Pass2(ExactName): %d | Pass3(Fuzzy): %d",
             len(clusters), pass1_count, pass2_count, pass3_count)
    return clusters


# =============================================================================
# INTER-CLUSTER ORDERING
# =============================================================================

def order_clusters_by_similarity(clusters: List[ItemCluster]) -> List[ItemCluster]:
    """Greedy nearest-neighbor ordering by anchor name similarity.

    Start with first cluster, always pick the most similar unvisited
    anchor name next. Creates a gradient where related items appear adjacent.
    """
    if len(clusters) <= 1:
        return clusters

    log.info("Ordering %d clusters by name similarity...", len(clusters))

    ordered: List[ItemCluster] = []
    remaining = list(range(len(clusters)))

    # Start with first cluster
    current_idx = remaining.pop(0)
    ordered.append(clusters[current_idx])

    while remaining:
        current_name = clusters[current_idx].item_name or ""
        best_idx = -1
        best_score = -1.0

        for idx in remaining:
            candidate_name = clusters[idx].item_name or ""
            if not current_name or not candidate_name:
                score = 0.0
            else:
                score = difflib.SequenceMatcher(None, current_name, candidate_name).ratio()
            if score > best_score:
                best_score = score
                best_idx = idx

        remaining.remove(best_idx)
        ordered.append(clusters[best_idx])
        current_idx = best_idx

    log.info("Cluster ordering complete")
    return ordered


# =============================================================================
# EXCEL WRITER
# =============================================================================

_header_font = Font(bold=True, color="FFFFFF")
_header_fill = PatternFill("solid", fgColor="4F81BD")
_fill_a = PatternFill("solid", fgColor="E2EFDA")  # Light green
_fill_b = PatternFill("solid", fgColor="FCE4D6")  # Light orange


def write_cluster_excel(
    clusters: List[ItemCluster],
    lang_tbl: Dict[str, List[Tuple[str, str]]],
    lang_code: str,
    export_index: Dict[str, Set[str]],
    output_path: Path,
) -> None:
    """Write ItemKnowledgeCluster Excel with one mega-sheet.

    7 columns: DataType | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "ItemKnowledgeCluster"
    code = lang_code.upper()

    headers = [
        "DataType",
        "SourceText (KR)",
        f"Translation ({code})",
        "STATUS",
        "COMMENT",
        "SCREENSHOT",
        "STRINGID",
    ]

    # Write header row
    for col_idx, txt in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, txt)
        cell.font = _header_font
        cell.fill = _header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    excel_row = 2
    current_fill = _fill_a

    for cluster in clusters:
        if not cluster.rows:
            continue

        # Alternate fill per cluster for visual grouping
        current_fill = _fill_b if current_fill == _fill_a else _fill_a

        for crow in cluster.rows:
            trans, sid = resolve_translation(crow.kor_text, lang_tbl, crow.source_file, export_index)
            vals = [crow.data_type, crow.kor_text, trans, "", "", "", sid]
            for ci, val in enumerate(vals, 1):
                cell = ws.cell(excel_row, ci, val)
                cell.fill = current_fill
                cell.border = THIN_BORDER
                if ci == 4:  # STATUS
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            # STRINGID as text format (prevent scientific notation)
            ws.cell(excel_row, 7).number_format = '@'
            excel_row += 1

    # Sheet cosmetics
    if excel_row > 2:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{excel_row - 1}"
    ws.freeze_panes = "A2"

    add_status_dropdown(ws, col=4)
    autofit_worksheet(ws)

    wb.save(output_path)
    log.info("ItemKnowledgeCluster Excel saved: %s (%d rows)", output_path.name, excel_row - 2)


# =============================================================================
# MAIN GENERATOR
# =============================================================================

def generate_itemknowledgecluster_datasheets() -> Dict:
    """Generate ItemKnowledgeCluster mega datasheets for all languages.

    Pipeline:
    1. Load language tables
    2. Scan all StaticInfo for ItemInfo + KnowledgeInfo
    3. Build clusters (3-pass matching)
    4. Order clusters by name similarity
    5. Get EXPORT index
    6. For each language: write mega-sheet Excel

    Returns:
        Dict with results
    """
    result = {
        "category": "ItemKnowledgeCluster",
        "files_created": 0,
        "errors": [],
    }

    reset_korean_collection()

    log.info("=" * 70)
    log.info("ItemKnowledgeCluster Datasheet Generator")
    log.info("=" * 70)

    DATASHEET_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_folder = DATASHEET_OUTPUT / "ItemKnowledgeCluster"
    output_folder.mkdir(exist_ok=True)

    item_folder = RESOURCE_FOLDER / "iteminfo"
    if not item_folder.exists():
        item_folder = RESOURCE_FOLDER

    if not RESOURCE_FOLDER.exists():
        result["errors"].append(f"Resource folder not found: {RESOURCE_FOLDER}")
        log.error("Resource folder not found: %s", RESOURCE_FOLDER)
        return result

    if not LANGUAGE_FOLDER.exists():
        result["errors"].append(f"Language folder not found: {LANGUAGE_FOLDER}")
        log.error("Language folder not found: %s", LANGUAGE_FOLDER)
        return result

    try:
        # 1. Load language tables
        lang_tables = load_language_tables(LANGUAGE_FOLDER)
        if not lang_tables:
            result["errors"].append("No language tables found!")
            log.warning("No language tables found!")
            return result

        # 2. Scan all StaticInfo (items from iteminfo, knowledge from knowledgeinfo)
        items_raw, knowledges_raw = scan_all_staticinfo(item_folder)

        # Also scan knowledgeinfo folder separately
        knowledge_folder = RESOURCE_FOLDER / "knowledgeinfo"
        if knowledge_folder.exists():
            _, extra_knowledges = scan_all_staticinfo(knowledge_folder)
            # Merge, avoiding duplicates
            seen_keys = {k.strkey for k in knowledges_raw}
            for kr in extra_knowledges:
                if kr.strkey not in seen_keys:
                    knowledges_raw.append(kr)
                    seen_keys.add(kr.strkey)
            log.info("After merging knowledgeinfo folder: %d knowledge records total",
                     len(knowledges_raw))

        if not items_raw:
            result["errors"].append("No item data found!")
            log.warning("No item data found!")
            return result

        # 3. Build clusters (3-pass matching)
        clusters = build_clusters(items_raw, knowledges_raw)

        # 4. Order clusters by name similarity
        clusters = order_clusters_by_similarity(clusters)

        # 5. Get EXPORT index
        export_index = get_export_index()

        # 6. Generate Excel per language
        log.info("Processing languages...")
        total = len(lang_tables)

        for idx, (code, tbl) in enumerate(lang_tables.items(), 1):
            log.info("(%d/%d) Language %s", idx, total, code.upper())
            excel_path = output_folder / f"ItemKnowledgeCluster_LQA_{code.upper()}.xlsx"
            write_cluster_excel(clusters, tbl, code, export_index, excel_path)
            result["files_created"] += 1

        log.info("=" * 70)
        log.info("Done! Output folder: %s", output_folder)
        log.info("=" * 70)

    except Exception as e:
        result["errors"].append(f"Generator error: {e}")
        log.exception("Error in ItemKnowledgeCluster generator: %s", e)

    return result


# Allow standalone execution for testing
if __name__ == "__main__":
    result = generate_itemknowledgecluster_datasheets()
    print(f"\nResult: {result}")
