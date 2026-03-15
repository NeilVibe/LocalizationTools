# Phase 12: Game Dev Merge - Research

**Researched:** 2026-03-15
**Domain:** Position-based XML tree merge for game data files
**Confidence:** MEDIUM-HIGH

## Summary

Game Dev Merge is the NOVEL phase in v2.0 -- unlike Translator Merge (Phase 09) which was ported directly from QuickTranslate, there is NO existing implementation to port. This requires design work. The core problem: given an original XML file on disk and modified rows in LocaNext's database, detect what changed and produce a merged XML output preserving document order.

The fundamental difference from Translator Merge is that Game Dev Merge is **position-based** (matching by tree position + tag name), not match-type-based (StringID/StrOrigin/fuzzy). Game Dev XML files have no StringIDs -- they have structural nodes with named attributes (ItemName, Grade, Stats, etc.). The merge must operate at three levels: node level (add/remove/modify whole nodes), attribute level (update individual attribute values), and depth level (handle parent > children > sub-children).

The recommended approach is a **parallel tree walk** algorithm: parse the original XML from disk, reconstruct the expected tree from LocaNext rows (using `extra_data`), then walk both trees comparing nodes by position + tag name. Changes are classified as ADD/REMOVE/MODIFY at each level. The output XML is built by applying changes to the original tree (preserving lxml document order), not by building a new tree from scratch. This approach naturally handles depth because tree walking is recursive.

**Primary recommendation:** Build a `GameDevMergeService` that takes original XML bytes + current DB rows, computes a diff (list of `NodeChange` objects), applies changes to the original lxml tree, and serializes back to XML. Keep completely separate from `TranslatorMergeService` -- no shared base class.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GMERGE-01 | Global export identifies all changed nodes across entire file | Diff algorithm compares original tree vs current rows; `NodeChange` dataclass tracks change_type per node |
| GMERGE-02 | Merge operates at node level (add/remove/modify nodes) | Three node-level operations: INSERT at position, REMOVE from tree, MODIFY attributes; applied to original tree |
| GMERGE-03 | Merge operates at attribute value level within nodes | `AttributeChange` tracks per-attribute old/new values; `elem.set(attr, new_val)` for targeted updates |
| GMERGE-04 | Merge handles parent > children > sub-children depth correctly | Recursive tree walk with `extra_data.depth` for reconstruction; lxml preserves parent-child naturally |
| GMERGE-05 | Position-based merge preserves XML document order | Apply changes IN PLACE to original lxml tree (never rebuild); lxml preserves insertion order |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=4.9.0 | XML parsing, tree manipulation, serialization | Already used by XMLParsingEngine; preserves attribute order and document structure |
| loguru | existing | Structured logging | Project standard, already imported |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| deepdiff | optional | Tree comparison (NOT recommended) | Do NOT use -- too general, can't handle position-based matching well |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom tree diff | xmldiff / deepdiff | These are generic diff tools -- they use edit-distance algorithms, not position-based matching. Our use case is simpler (same structure, modified values) and more specific (preserve document order). Custom is better. |
| Rebuilding tree from rows | Modifying original tree in-place | Rebuilding loses comments, processing instructions, whitespace, and document order. In-place modification preserves everything. |

**Installation:**
```bash
# No new packages needed -- lxml already installed
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/
    gamedev_merge.py          # GameDevMergeService + NodeChange + MergeResult
  routes/
    merge.py                  # Extended: add gamedev merge endpoint
  file_handlers/
    xml_handler.py            # Already has parse_gamedev_nodes() -- reuse
```

### Pattern 1: Parallel Tree Walk Diff
**What:** Walk the original XML tree and the "current state" tree (reconstructed from DB rows) simultaneously, comparing nodes at each position by tag name + position index.
**When to use:** Detecting changes between original file and modified rows.
**Example:**
```python
# Source: Custom design based on lxml tree structure
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from lxml import etree


class ChangeType(Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"      # Attribute values changed
    ADDED = "added"            # New node not in original
    REMOVED = "removed"        # Node in original but deleted


@dataclass
class AttributeChange:
    name: str
    old_value: Optional[str]
    new_value: Optional[str]


@dataclass
class NodeChange:
    """Represents a change at a single node."""
    change_type: ChangeType
    tag: str
    position: int              # Position among siblings
    depth: int
    attribute_changes: list[AttributeChange] = field(default_factory=list)
    children_changes: list[NodeChange] = field(default_factory=list)


def diff_trees(
    original: etree._Element,
    current_attrs: list[dict],   # From DB rows extra_data
    depth: int = 0,
) -> list[NodeChange]:
    """Compare original XML tree against current state from DB rows."""
    changes = []
    # Walk original children and match against current_attrs by position + tag
    # ... recursive implementation
    return changes
```

### Pattern 2: In-Place Tree Modification
**What:** Apply computed changes to the ORIGINAL lxml tree rather than building a new tree. This preserves comments, processing instructions, whitespace, and document order.
**When to use:** Producing the merged output XML.
**Example:**
```python
# Source: lxml API -- tree modification
def apply_changes(root: etree._Element, changes: list[NodeChange]) -> None:
    """Apply changes to the original tree in-place."""
    for change in changes:
        if change.change_type == ChangeType.MODIFIED:
            elem = _find_element_by_position(root, change)
            for attr_change in change.attribute_changes:
                if attr_change.new_value is None:
                    # Attribute removed
                    if attr_change.name in elem.attrib:
                        del elem.attrib[attr_change.name]
                else:
                    elem.set(attr_change.name, attr_change.new_value)
        elif change.change_type == ChangeType.ADDED:
            parent = _find_parent_by_position(root, change)
            new_elem = etree.SubElement(parent, change.tag)
            for attr_change in change.attribute_changes:
                if attr_change.new_value is not None:
                    new_elem.set(attr_change.name, attr_change.new_value)
        elif change.change_type == ChangeType.REMOVED:
            elem = _find_element_by_position(root, change)
            elem.getparent().remove(elem)
```

### Pattern 3: Row-to-Tree Reconstruction
**What:** Reconstruct a tree state from the current DB rows' `extra_data` fields. Each Game Dev row stores `node_name`, `attributes`, `values`, `children_count`, and `depth` in `extra_data`. This reconstructed state is compared against the original file.
**When to use:** Building the "current state" for diffing against the original XML.
**Example:**
```python
# Existing data shape from parse_gamedev_nodes():
# row["extra_data"] = {
#     "node_name": "Item",
#     "attributes": {"Name": "Iron Sword", "Type": "Weapon", "Value": "150"},
#     "values": None,  # text content
#     "children_count": 2,
#     "depth": 1,
# }
# row["source"] = "Item"  (tag name)
# row["target"] = "Name=Iron Sword, Type=Weapon, Value=150"  (formatted)
```

### Pattern 4: Export-then-Diff Approach (Recommended for GMERGE-01)
**What:** For "global export identifies all changed nodes" -- re-parse the original file from disk, compare against current DB rows, and return a change summary.
**When to use:** Before merge, to show the user what will change.
**Example:**
```python
@dataclass
class GameDevMergeResult:
    total_nodes: int = 0
    changed_nodes: int = 0
    added_nodes: int = 0
    removed_nodes: int = 0
    modified_attributes: int = 0
    changes: list[NodeChange] = field(default_factory=list)
    output_xml: Optional[bytes] = None
```

### Anti-Patterns to Avoid
- **Sharing base class with TranslatorMergeService:** These are fundamentally different algorithms. Translator merge operates on flat rows with text matching. Game Dev merge operates on tree structure with position matching. A shared base would be an abstraction that helps nobody.
- **Rebuilding XML from rows only:** You lose comments, processing instructions, whitespace formatting, and any structure not captured in `extra_data`. Always modify the original tree in-place.
- **String comparison for change detection:** Comparing `_format_attributes(elem)` strings is fragile. Compare the `attributes` dict from `extra_data` directly against original element's `attrib` dict.
- **Applying Translator postprocess pipeline to Game Dev output:** The 7-step CJK postprocess modifies text content. Game Dev attributes include non-text values (coordinates, IDs, formulas). Only postprocess explicitly text-content attributes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML tree manipulation | Custom DOM implementation | lxml etree API | lxml handles namespaces, attribute order, encoding, serialization correctly. Hand-rolling loses edge cases. |
| XML serialization | Manual string building | `etree.tostring(root, pretty_print=True, xml_declaration=True, encoding=encoding)` | lxml handles escaping, encoding, declaration automatically. Manual building produces broken XML on edge cases. |
| Attribute order preservation | OrderedDict tracking | lxml (preserves insertion order natively since 4.x) | lxml already does this. Don't add complexity. |

**Key insight:** lxml's tree API is the right level of abstraction. It preserves document order, handles encoding, and provides in-place modification. The custom code should be the DIFF ALGORITHM only -- everything else delegates to lxml.

## Common Pitfalls

### Pitfall 1: Position Shifts When Nodes Are Added/Removed
**What goes wrong:** If the user adds a node at position 3, all subsequent original nodes shift by 1. A naive position-based lookup finds the wrong node.
**Why it happens:** Comparing by absolute position index breaks when the node count changes between original and current state.
**How to avoid:** Match by (tag_name, relative_position_among_same_tag_siblings) rather than absolute index. Or: process removals in reverse order (highest position first) and additions in forward order to avoid index shifting.
**Warning signs:** Merged output has attributes from the wrong node. Tests pass with modify-only but fail with add+modify.

### Pitfall 2: extra_data Reconstruction Fidelity
**What goes wrong:** `parse_gamedev_nodes()` stores `attributes` as a flat dict in `extra_data`. If the user modifies a row in the UI (e.g., changing an attribute value), the updated row must update `extra_data.attributes` -- not just `target` (which is the formatted display string).
**Why it happens:** `bulk_update()` currently only supports `target` and `status` fields. It does NOT update `extra_data`. If the user edits a Game Dev row, the `extra_data` stays stale.
**How to avoid:** Either (a) extend `bulk_update()` to support `extra_data` updates, or (b) for Phase 12 scope, treat `extra_data` as the source of truth for current state (the user edits `extra_data.attributes` through the API, not just `target`). Decision: extend `bulk_update()` to handle `extra_data` -- this is a prerequisite for Game Dev merge.
**Warning signs:** Merge shows "no changes" even after the user modified values.

### Pitfall 3: Postprocess Corrupting Non-Text Attributes (Pitfall 13 from PITFALLS.md)
**What goes wrong:** The Translator postprocess pipeline normalizes apostrophes, strips invisible chars, and cleans CJK punctuation. If applied to Game Dev attributes like `Value="150"` or `EffectId="BUFF_001"`, it could corrupt data (e.g., normalizing a hyphen in a formula).
**Why it happens:** Blindly applying postprocess_rows() to all Game Dev merge output.
**How to avoid:** Game Dev merge has NO postprocessing pipeline. Attribute values are written as-is. If text-content postprocessing is ever needed, it must be limited to explicitly designated text attributes (e.g., `Name`, `Description`), not structural attributes.
**Warning signs:** Numeric values or IDs change after merge.

### Pitfall 4: Document Order Loss When Using etree.SubElement for Additions
**What goes wrong:** `etree.SubElement(parent, tag)` always appends to the END of parent's children. If the user added a node at position 2 (between existing nodes 1 and 3), it ends up at position N+1 instead.
**How to avoid:** Use `parent.insert(position, new_elem)` instead of `SubElement` for additions at specific positions. lxml's `insert()` preserves document order.
**Warning signs:** Added nodes always appear at the end of their parent, regardless of intended position.

### Pitfall 5: br-tag in Game Dev Text Attributes
**What goes wrong:** Some Game Dev attributes contain text with `<br/>` tags (e.g., Description fields). The br-tag three-layer defense from Translator mode must also apply to text-content attributes in Game Dev mode.
**How to avoid:** During XML serialization, lxml auto-escapes `<br/>` to `&lt;br/&gt;` in attribute values (this is correct behavior for on-disk format). No manual escaping needed. Just ensure NO manual escaping is added on top of lxml's auto-escaping.
**Warning signs:** Double-escaped br-tags: `&amp;lt;br/&amp;gt;` in output.

### Pitfall 6: Depth Mismatch Between Rows and Original Tree
**What goes wrong:** `parse_gamedev_nodes()` uses `max_depth=3` by default. If the original file has nodes deeper than 3 levels, they are NOT in the DB rows. During merge, these deep nodes in the original tree have no corresponding row and could be incorrectly flagged as "removed."
**How to avoid:** When diffing, nodes in the original tree that are beyond `max_depth` should be treated as UNCHANGED (pass through). Only nodes that have corresponding rows in the DB should be checked for changes.
**Warning signs:** Deep nested nodes disappear from output after merge.

## Code Examples

### Verified: Game Dev Row Data Shape (from xml_handler.py)
```python
# Source: server/tools/ldm/file_handlers/xml_handler.py:parse_gamedev_nodes()
# Each Game Dev row in the DB looks like:
{
    "row_num": 1,
    "string_id": None,              # Game Dev rows have no StringID
    "source": "Item",               # Tag name
    "target": "Name=Iron Sword, Type=Weapon, Value=150",  # Formatted display
    "status": "pending",
    "extra_data": {
        "node_name": "Item",
        "attributes": {"Name": "Iron Sword", "Type": "Weapon", "Value": "150", "Grade": "Common"},
        "values": None,             # Text content of element
        "children_count": 2,        # Direct children count
        "depth": 1,                 # Depth from root
    }
}
```

### Verified: Existing bulk_update Limitation
```python
# Source: server/repositories/sqlite/row_repo.py:bulk_update()
# Currently only updates: target, status
# MUST be extended to also update: extra_data
# For Game Dev merge, extra_data.attributes is the real data
```

### Verified: lxml In-Place Modification
```python
# Source: lxml API (HIGH confidence)
from lxml import etree

root = etree.fromstring(b'<Items><Item Name="Sword" Value="100"/></Items>')
item = root[0]

# Modify attribute
item.set("Value", "200")

# Add attribute
item.set("NewAttr", "test")

# Remove attribute
del item.attrib["Name"]

# Insert child at position
new_child = etree.Element("Stats")
new_child.set("Attack", "25")
item.insert(0, new_child)  # Insert at position 0

# Remove node
root.remove(item)

# Serialize preserving order
output = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")
```

### Verified: Existing Merge Route Pattern (from merge.py)
```python
# Source: server/tools/ldm/routes/merge.py
# Game Dev merge endpoint should follow this same pattern:
# 1. Validate request
# 2. Fetch rows from DB
# 3. Call service (compute changes)
# 4. Apply via bulk_update (transactional)
# 5. Return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| String-based XML diff | Tree-based comparison | lxml 4.x+ | Attribute order preserved, position-based matching possible |
| Full tree rebuild from data | In-place modification of original | Design decision | Preserves comments, PIs, whitespace |
| Shared merge abstraction | Separate Translator + GameDev services | Phase 12 design | Avoids forced abstraction, cleaner code |

## Open Questions

1. **How should the user trigger Game Dev merge?**
   - What we know: Translator merge uses `POST /files/{file_id}/merge` with a source_file_id. Game Dev merge is different -- there's no "source file" in the same sense.
   - What's unclear: Is the "source" the original file on disk? The current DB rows represent the edited state. The merge produces output XML from the diff.
   - Recommendation: Game Dev merge endpoint should be `POST /files/{file_id}/gamedev-merge` or `POST /files/{file_id}/export-merged`. Input is file_id only (DB rows are the current state, original XML is re-parsed from disk/stored metadata). Output is the merged XML bytes.

2. **Where is the original XML stored for comparison?**
   - What we know: `parse_xml_file()` receives `file_content: bytes` at upload time. Metadata stores root_element, encoding, etc. But the raw XML bytes are not stored in the DB.
   - What's unclear: How to access the original file for diffing. Options: (a) store raw bytes in DB at upload, (b) re-read from disk path, (c) store in file system with a reference.
   - Recommendation: Store the original XML bytes in a new column or file-system cache at upload time. The file metadata already has encoding and root info, but the full original bytes are needed for tree reconstruction.

3. **Should bulk_update be extended for extra_data, or use a separate update path?**
   - What we know: Current bulk_update only handles `target` and `status`. Game Dev rows need `extra_data` updates (attribute changes).
   - Recommendation: Extend bulk_update in both SQLite and PostgreSQL repos to support `extra_data`. This is a small, well-scoped change. Serialize with `json.dumps()` like bulk_create already does.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `tests/conftest.py` |
| Quick run command | `python -m pytest tests/unit/ldm/test_gamedev_merge.py -x` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GMERGE-01 | Diff detects all changed nodes across file | unit | `python -m pytest tests/unit/ldm/test_gamedev_merge.py::TestDiffDetection -x` | Wave 0 |
| GMERGE-02 | Node-level add/remove/modify operations | unit | `python -m pytest tests/unit/ldm/test_gamedev_merge.py::TestNodeOperations -x` | Wave 0 |
| GMERGE-03 | Attribute-level merge (individual values) | unit | `python -m pytest tests/unit/ldm/test_gamedev_merge.py::TestAttributeMerge -x` | Wave 0 |
| GMERGE-04 | Depth handling (parent > children > sub-children) | unit | `python -m pytest tests/unit/ldm/test_gamedev_merge.py::TestDepthHandling -x` | Wave 0 |
| GMERGE-05 | Position-based merge preserves document order | unit | `python -m pytest tests/unit/ldm/test_gamedev_merge.py::TestDocumentOrder -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_gamedev_merge.py -x`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_gamedev_merge.py` -- covers GMERGE-01 through GMERGE-05
- [ ] `tests/fixtures/xml/gamedev_modified.xml` -- modified version of gamedev_sample.xml for diff testing
- [ ] Extend `tests/fixtures/xml/gamedev_sample.xml` with deeper nesting for GMERGE-04

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/file_handlers/xml_handler.py` -- parse_gamedev_nodes() data shape, verified by reading source
- `server/tools/ldm/services/translator_merge.py` -- MergeResult pattern, service architecture, verified by reading source
- `server/tools/ldm/services/xml_parsing.py` -- XMLParsingEngine singleton, lxml usage patterns
- `server/tools/ldm/routes/merge.py` -- Existing merge endpoint pattern (transactional bulk_update)
- `server/repositories/sqlite/row_repo.py` -- bulk_update supports target+status only (limitation identified)
- `tests/fixtures/xml/gamedev_sample.xml` -- Real Game Dev XML structure with nesting
- lxml API documentation -- tree manipulation, in-place modification, attribute handling

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` -- Pitfall 8 (position vs match-type confusion), Pitfall 13 (postprocess corruption)
- `.planning/research/SUMMARY.md` -- GameDevMergeEngine architecture recommendation
- `.planning/research/FEATURES.md` -- D3 feature specification (position-aware XML merge)

### Tertiary (LOW confidence)
- Game Dev merge algorithm design -- no existing implementation anywhere in codebase; algorithm is custom design based on XML tree properties and lxml capabilities

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- lxml already in use, no new dependencies needed
- Architecture: MEDIUM-HIGH -- service pattern proven by TranslatorMergeService, but diff algorithm is novel
- Pitfalls: HIGH -- identified from codebase inspection (bulk_update limitation, extra_data shape, depth handling)
- Algorithm design: MEDIUM -- parallel tree walk is sound but untested; edge cases (add+remove+reorder) need careful implementation

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no external dependency changes expected)
