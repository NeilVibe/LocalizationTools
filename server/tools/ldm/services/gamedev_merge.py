"""
Game Dev Merge Service -- parallel tree walk diff + in-place apply.

Novel algorithm for Game Dev XML files (non-LocStr):
- Position-based tree comparison (NOT attribute-value matching)
- Detects MODIFIED/ADDED/REMOVED at node and attribute levels
- In-place lxml tree modification preserves document order
- No postprocessing pipeline (attribute values written as-is)

Completely separate from TranslatorMergeService.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from lxml import etree

from server.tools.ldm.file_handlers.xml_handler import parse_gamedev_nodes

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change detected between original XML and current rows."""

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


@dataclass
class AttributeChange:
    """A single attribute-level change."""

    name: str
    old_value: Optional[str]
    new_value: Optional[str]


@dataclass
class NodeChange:
    """A node-level change detected by diff_trees."""

    change_type: ChangeType
    tag: str
    position: int  # 0-based position in iteration order
    depth: int
    attribute_changes: list[AttributeChange] = field(default_factory=list)
    children_changes: list[NodeChange] = field(default_factory=list)
    # For ADDED nodes: full attribute dict to create element
    new_attributes: Optional[dict] = None
    # For ADDED nodes: parent position (-1 = root)
    parent_position: int = -1
    # Reference to original element (for MODIFIED/REMOVED apply)
    _element: Optional[object] = field(default=None, repr=False)


@dataclass
class GameDevMergeResult:
    """Result of a Game Dev merge operation."""

    total_nodes: int = 0
    changed_nodes: int = 0
    added_nodes: int = 0
    removed_nodes: int = 0
    modified_attributes: int = 0
    changes: list[NodeChange] = field(default_factory=list)
    output_xml: bytes = b""


class GameDevMergeService:
    """Merge Game Dev XML by diffing original tree against current DB rows.

    Algorithm:
    1. Parse original XML tree into elements (same iteration as parse_gamedev_nodes)
    2. Walk elements and rows in parallel, matching by sequential position
    3. Detect attribute-level differences
    4. Apply changes in-place to original lxml tree
    5. Serialize back to bytes
    """

    def diff_trees(
        self,
        original: etree._Element,
        current_rows: list[dict],
        max_depth: int = 3,
    ) -> list[NodeChange]:
        """Compare original XML tree against current rows.

        Parallel walk: iterate original elements in document order (same as
        parse_gamedev_nodes) and compare against rows by sequential position.

        Args:
            original: lxml root element of original XML
            current_rows: Current state rows (from DB) with extra_data
            max_depth: Maximum depth to consider (deeper nodes = pass through)

        Returns:
            List of NodeChange objects describing all differences
        """
        changes: list[NodeChange] = []

        # Collect original elements in same order as parse_gamedev_nodes
        original_elements: list[tuple[etree._Element, int]] = []
        for elem in original.iter():
            if elem is original:
                continue
            if isinstance(elem, (etree._Comment, etree._ProcessingInstruction)):
                continue
            depth = self._get_depth(elem, original)
            if depth > max_depth:
                continue
            original_elements.append((elem, depth))

        # Build row index for efficient lookup
        row_idx = 0
        elem_idx = 0

        # Track which rows and elements are matched
        matched_rows: set[int] = set()
        matched_elems: set[int] = set()

        # Walk both sequences in parallel
        while elem_idx < len(original_elements) and row_idx < len(current_rows):
            elem, elem_depth = original_elements[elem_idx]
            row = current_rows[row_idx]
            row_extra = row.get("extra_data", {})
            row_tag = row_extra.get("node_name", row.get("source", ""))
            row_depth = row_extra.get("depth", 1)
            row_attrs = row_extra.get("attributes", {})

            # Check if this is the same node (tag + depth match at same position)
            if elem.tag == row_tag and elem_depth == row_depth:
                # Matched pair -- compare attributes
                attr_changes = self._diff_attributes(dict(elem.attrib), row_attrs)
                if attr_changes:
                    change = NodeChange(
                        change_type=ChangeType.MODIFIED,
                        tag=elem.tag,
                        position=elem_idx,
                        depth=elem_depth,
                        attribute_changes=attr_changes,
                        _element=elem,
                    )
                    changes.append(change)
                else:
                    changes.append(NodeChange(
                        change_type=ChangeType.UNCHANGED,
                        tag=elem.tag,
                        position=elem_idx,
                        depth=elem_depth,
                        _element=elem,
                    ))
                matched_rows.add(row_idx)
                matched_elems.add(elem_idx)
                elem_idx += 1
                row_idx += 1
            else:
                # Mismatch -- determine if element was removed or row was added
                # Look ahead in rows to see if current element matches a future row
                found_in_rows = False
                for look_row_idx in range(row_idx + 1, min(row_idx + 10, len(current_rows))):
                    lr = current_rows[look_row_idx]
                    lr_extra = lr.get("extra_data", {})
                    if (elem.tag == lr_extra.get("node_name", lr.get("source", ""))
                            and elem_depth == lr_extra.get("depth", 1)):
                        # Current element matches a future row -- rows before that are ADDED
                        for add_idx in range(row_idx, look_row_idx):
                            add_row = current_rows[add_idx]
                            add_extra = add_row.get("extra_data", {})
                            changes.append(NodeChange(
                                change_type=ChangeType.ADDED,
                                tag=add_extra.get("node_name", add_row.get("source", "")),
                                position=elem_idx,  # Insert before current element
                                depth=add_extra.get("depth", 1),
                                new_attributes=add_extra.get("attributes", {}),
                                parent_position=-1,
                            ))
                            matched_rows.add(add_idx)
                        row_idx = look_row_idx
                        found_in_rows = True
                        break

                if not found_in_rows:
                    # Look ahead in elements to see if current row matches a future element
                    found_in_elems = False
                    for look_elem_idx in range(elem_idx + 1, min(elem_idx + 10, len(original_elements))):
                        le, le_depth = original_elements[look_elem_idx]
                        if (le.tag == row_tag and le_depth == row_depth):
                            # Current row matches a future element -- elements before that are REMOVED
                            for rem_idx in range(elem_idx, look_elem_idx):
                                rem_elem, rem_depth = original_elements[rem_idx]
                                changes.append(NodeChange(
                                    change_type=ChangeType.REMOVED,
                                    tag=rem_elem.tag,
                                    position=rem_idx,
                                    depth=rem_depth,
                                    _element=rem_elem,
                                ))
                                matched_elems.add(rem_idx)
                            elem_idx = look_elem_idx
                            found_in_elems = True
                            break

                    if not found_in_elems:
                        # Element removed, row added -- treat as removal + addition
                        changes.append(NodeChange(
                            change_type=ChangeType.REMOVED,
                            tag=elem.tag,
                            position=elem_idx,
                            depth=elem_depth,
                            _element=elem,
                        ))
                        matched_elems.add(elem_idx)
                        elem_idx += 1

        # Remaining original elements are REMOVED
        while elem_idx < len(original_elements):
            elem, depth = original_elements[elem_idx]
            changes.append(NodeChange(
                change_type=ChangeType.REMOVED,
                tag=elem.tag,
                position=elem_idx,
                depth=depth,
                _element=elem,
            ))
            elem_idx += 1

        # Remaining rows are ADDED
        while row_idx < len(current_rows):
            row = current_rows[row_idx]
            row_extra = row.get("extra_data", {})
            changes.append(NodeChange(
                change_type=ChangeType.ADDED,
                tag=row_extra.get("node_name", row.get("source", "")),
                position=len(original_elements),  # Append at end
                depth=row_extra.get("depth", 1),
                new_attributes=row_extra.get("attributes", {}),
                parent_position=-1,
            ))
            row_idx += 1

        return changes

    def apply_changes(
        self,
        root: etree._Element,
        changes: list[NodeChange],
    ) -> None:
        """Apply changes in-place to the original lxml tree.

        Args:
            root: lxml root element to modify in-place
            changes: List of NodeChange objects from diff_trees
        """
        # Separate by type for ordered processing
        modifications = [c for c in changes if c.change_type == ChangeType.MODIFIED]
        removals = [c for c in changes if c.change_type == ChangeType.REMOVED]
        additions = [c for c in changes if c.change_type == ChangeType.ADDED]

        # Apply modifications first (no position changes)
        for change in modifications:
            elem = change._element
            if elem is None:
                logger.warning("MODIFIED change has no element reference at position %d", change.position)
                continue
            for attr_change in change.attribute_changes:
                if attr_change.new_value is None:
                    # Attribute removed
                    if attr_change.name in elem.attrib:
                        del elem.attrib[attr_change.name]
                elif attr_change.old_value is None:
                    # Attribute added
                    elem.set(attr_change.name, attr_change.new_value)
                else:
                    # Attribute modified
                    elem.set(attr_change.name, attr_change.new_value)

        # Apply removals in REVERSE position order to avoid index shifting
        removals_sorted = sorted(removals, key=lambda c: c.position, reverse=True)
        for change in removals_sorted:
            elem = change._element
            if elem is None:
                logger.warning("REMOVED change has no element reference at position %d", change.position)
                continue
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
            else:
                logger.warning("Cannot remove element at position %d: no parent", change.position)

        # Apply additions (insert at position)
        # Collect elements in document order for position calculation
        for change in additions:
            new_elem = etree.Element(change.tag)
            if change.new_attributes:
                for k, v in change.new_attributes.items():
                    new_elem.set(k, v)

            # Find the right parent based on depth
            if change.depth == 1:
                # Top-level element, insert into root
                # Find insertion point based on position among current children
                self._insert_at_depth1(root, new_elem, change.position, changes)
            else:
                # Nested element -- find parent by walking current tree
                # For simplicity, append to root (position handling for nested adds is complex)
                root.append(new_elem)
                logger.debug("Added nested element %s at depth %d (appended to root)", change.tag, change.depth)

    def _insert_at_depth1(
        self,
        root: etree._Element,
        new_elem: etree._Element,
        position: int,
        all_changes: list[NodeChange],
    ) -> None:
        """Insert a depth-1 element at the right position in root.

        Uses the position index from diff to determine where among current
        root children to insert.
        """
        # Count how many top-level elements exist before this position
        # that haven't been removed
        children = list(root)
        # Filter out comments/PIs
        element_children = [c for c in children if isinstance(c, etree._Element)]

        # Find which element in the current tree corresponds to the insertion point
        # Position is relative to the original document order iteration
        # For additions, we insert before the element at this position
        # Simple heuristic: use min of position and len(element_children)
        insert_idx = min(position, len(element_children))
        if insert_idx < len(children):
            # Find the actual index in children (including comments)
            actual_idx = 0
            elem_count = 0
            for i, child in enumerate(children):
                if isinstance(child, etree._Element):
                    if elem_count == insert_idx:
                        actual_idx = i
                        break
                    elem_count += 1
                actual_idx = i + 1
            root.insert(actual_idx, new_elem)
        else:
            root.append(new_elem)

    def merge(
        self,
        original_xml: bytes,
        current_rows: list[dict],
        max_depth: int = 3,
    ) -> GameDevMergeResult:
        """Full merge: parse original, diff against rows, apply changes, serialize.

        Args:
            original_xml: Original XML file bytes
            current_rows: Current state rows (from DB) with extra_data
            max_depth: Maximum depth to consider

        Returns:
            GameDevMergeResult with counts and output_xml bytes
        """
        # Parse original XML
        parser = etree.XMLParser(recover=True, remove_blank_text=False)
        root = etree.fromstring(original_xml, parser=parser)

        # Detect original encoding
        encoding = "utf-8"
        try:
            text_start = original_xml[:200].decode("utf-8", errors="ignore")
            if 'encoding="' in text_start:
                enc_start = text_start.index('encoding="') + len('encoding="')
                enc_end = text_start.index('"', enc_start)
                encoding = text_start[enc_start:enc_end]
        except (ValueError, UnicodeDecodeError):
            pass

        # Diff
        changes = self.diff_trees(root, current_rows, max_depth=max_depth)

        # Apply
        self.apply_changes(root, changes)

        # Serialize
        output_xml = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding=encoding,
        )

        # Count results
        modified = [c for c in changes if c.change_type == ChangeType.MODIFIED]
        added = [c for c in changes if c.change_type == ChangeType.ADDED]
        removed = [c for c in changes if c.change_type == ChangeType.REMOVED]
        total_attr_changes = sum(len(c.attribute_changes) for c in modified)

        result = GameDevMergeResult(
            total_nodes=len(changes),
            changed_nodes=len(modified) + len(added) + len(removed),
            added_nodes=len(added),
            removed_nodes=len(removed),
            modified_attributes=total_attr_changes,
            changes=changes,
            output_xml=output_xml,
        )

        logger.info(
            "Game Dev merge: %d total, %d changed (%d modified, %d added, %d removed), %d attr changes",
            result.total_nodes,
            result.changed_nodes,
            len(modified),
            result.added_nodes,
            result.removed_nodes,
            result.modified_attributes,
        )

        return result

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _get_depth(elem: etree._Element, root: etree._Element) -> int:
        """Count depth from root (1-based for direct children)."""
        depth = 0
        parent = elem.getparent()
        while parent is not None and parent is not root:
            depth += 1
            parent = parent.getparent()
        if elem is not root:
            depth += 1
        return depth

    @staticmethod
    def _diff_attributes(
        original_attrs: dict[str, str],
        current_attrs: dict[str, str],
    ) -> list[AttributeChange]:
        """Compare two attribute dicts and return list of changes.

        Detects:
        - Modified: same key, different value
        - Added: key in current but not original
        - Removed: key in original but not current
        """
        changes: list[AttributeChange] = []
        all_keys = set(original_attrs.keys()) | set(current_attrs.keys())

        for key in all_keys:
            old_val = original_attrs.get(key)
            new_val = current_attrs.get(key)

            if old_val == new_val:
                continue

            changes.append(AttributeChange(
                name=key,
                old_value=old_val,
                new_value=new_val,
            ))

        return changes
