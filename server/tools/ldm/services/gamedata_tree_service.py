"""GameData Tree Service -- hierarchical XML tree parsing via lxml.

Phase 27: Tree Backend -- lxml-based tree walking that understands both
XML-nested hierarchies (GimmickGroup > GimmickInfo > SealData) and
reference-based hierarchies (SkillNode ParentNodeId).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from lxml import etree

from server.tools.ldm.schemas.gamedata import (
    FolderTreeDataResponse,
    GameDataTreeResponse,
    TreeNode,
)
from server.tools.ldm.services.gamedata_browse_service import EDITABLE_ATTRS


# Reference attribute names used for parent-child resolution.
_PARENT_REF_ATTRS = ("ParentNodeId", "ParentId")
_NODE_ID_ATTRS = ("NodeId", "Id", "Key")


class GameDataTreeService:
    """Parses XML gamedata files into hierarchical TreeNode JSON trees.

    Handles two hierarchy styles:
    1. XML-nested: Direct child elements map to children (e.g. GimmickGroupInfo > GimmickInfo).
    2. Reference-based: Flat sibling elements linked by ParentNodeId/ParentId attributes
       are restructured into a nested tree (e.g. SkillNode ParentNodeId).
    """

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()

    # -- Path validation (same logic as GameDataBrowseService) ----------------

    def _validate_path(self, path: str) -> Path:
        """Resolve *path* and ensure it lives within ``self.base_dir``."""
        path_obj = Path(path)
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            candidate = (self.base_dir / path).resolve()
            if candidate.exists():
                resolved = candidate
            else:
                cwd_candidate = Path(path).resolve()
                resolved = cwd_candidate if cwd_candidate.exists() else candidate
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError(
                f"Path {path} is outside allowed base directory {self.base_dir}"
            )
        return resolved

    # -- Public API -----------------------------------------------------------

    def parse_file(
        self, xml_path: str, max_depth: int = -1
    ) -> GameDataTreeResponse:
        """Parse a single XML file and return a hierarchical tree response.

        Args:
            xml_path: Path to XML file (absolute or relative to base_dir).
            max_depth: Maximum nesting depth. -1 means unlimited, 0 means no children.

        Returns:
            GameDataTreeResponse with nested TreeNode roots.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
            ValueError: If the path is outside the allowed base directory.
            etree.XMLSyntaxError: If XML cannot be parsed even with recover mode.
        """
        resolved = self._validate_path(xml_path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")

        root = self._parse_xml(resolved)

        # Build initial subtrees from direct children of XML root element.
        # Use findall("*") for lxml tree walking (TREE-05 requirement).
        children = [c for c in root.findall("*") if isinstance(c.tag, str)]
        if not children:
            return GameDataTreeResponse(
                roots=[],
                file_path=str(resolved),
                entity_type="",
                node_count=0,
            )

        entity_type = children[0].tag
        roots: List[TreeNode] = []

        for idx, child_el in enumerate(children):
            tree_node = self._build_subtree(
                child_el,
                depth=0,
                max_depth=max_depth,
                id_prefix=f"r{idx}",
            )
            roots.append(tree_node)

        # Resolve reference-based parent-child relationships.
        if max_depth != 0:
            roots = self._resolve_parent_references(roots, max_depth)

        node_count = self._count_nodes(roots)
        logger.debug(
            f"[TreeService] Parsed {resolved.name}: {len(roots)} roots, "
            f"{node_count} total nodes, entity_type={entity_type}"
        )

        return GameDataTreeResponse(
            roots=roots,
            file_path=str(resolved),
            entity_type=entity_type,
            node_count=node_count,
        )

    def parse_folder(
        self, folder_path: str, max_depth: int = -1
    ) -> FolderTreeDataResponse:
        """Parse all XML files in a folder recursively.

        Args:
            folder_path: Path to folder (absolute or relative to base_dir).
            max_depth: Maximum nesting depth per file.

        Returns:
            FolderTreeDataResponse with tree data for each XML file.
        """
        resolved = self._validate_path(folder_path)
        if not resolved.is_dir():
            raise FileNotFoundError(f"Not a directory: {resolved}")

        files: List[GameDataTreeResponse] = []
        total_nodes = 0

        for xml_file in sorted(resolved.rglob("*.xml")):
            try:
                result = self.parse_file(str(xml_file), max_depth=max_depth)
                files.append(result)
                total_nodes += result.node_count
            except Exception as exc:
                logger.warning(
                    f"[TreeService] Skipping {xml_file.name}: {exc}"
                )

        logger.debug(
            f"[TreeService] Parsed folder {resolved}: "
            f"{len(files)} files, {total_nodes} total nodes"
        )

        return FolderTreeDataResponse(
            files=files,
            base_path=str(resolved),
            total_nodes=total_nodes,
        )

    # -- XML parsing ----------------------------------------------------------

    def _parse_xml(self, path: Path) -> etree._Element:
        """Parse XML using battle-tested sanitizer pipeline (GRAFTED from MDG).

        Uses sanitize_and_parse() which provides 5-stage sanitization,
        virtual ROOT wrapper, and dual-pass (strict then recovery) parsing.
        The returned element is the virtual ROOT — iterate children for entities.
        """
        from server.tools.ldm.services.xml_sanitizer import sanitize_and_parse

        root = sanitize_and_parse(path)
        if root is None:
            raise etree.XMLSyntaxError(
                f"Failed to parse {path.name} even with sanitization + recovery", 0, 0, 0
            )
        return root

    # -- Tree building --------------------------------------------------------

    def _build_subtree(
        self,
        element: etree._Element,
        depth: int,
        max_depth: int,
        id_prefix: str,
    ) -> TreeNode:
        """Recursively build a TreeNode from an lxml element.

        Args:
            element: The lxml element to convert.
            depth: Current depth in the tree.
            max_depth: Maximum allowed depth (-1 = unlimited).
            id_prefix: Prefix for generating unique node IDs.
        """
        tag = element.tag
        attributes = dict(element.attrib)
        editable = list(EDITABLE_ATTRS.get(tag, []))

        node = TreeNode(
            node_id=id_prefix,
            tag=tag,
            attributes=attributes,
            editable_attrs=editable,
        )

        # Stop recursion if max_depth reached.
        if max_depth != -1 and depth >= max_depth:
            return node

        # Recurse into XML child elements via findall (skip comments/PIs).
        child_elements = element.findall("*")
        for child_idx, child_el in enumerate(child_elements):
            child_node = self._build_subtree(
                child_el,
                depth=depth + 1,
                max_depth=max_depth,
                id_prefix=f"{id_prefix}_c{child_idx}",
            )
            child_node.parent_id = node.node_id
            node.children.append(child_node)

        return node

    # -- Reference-based hierarchy resolution ---------------------------------

    def _resolve_parent_references(
        self, roots: List[TreeNode], max_depth: int
    ) -> List[TreeNode]:
        """Restructure flat ParentId/ParentNodeId references into nested children.

        For each root node, checks if its direct children use ParentNodeId or
        ParentId attributes. If so, re-parents them into a proper hierarchy:
        - ParentNodeId="0" or ParentId="0" -> stays as direct child of root
        - ParentNodeId="N" -> becomes child of the node whose NodeId/Id == "N"
        """
        for root in roots:
            if not root.children:
                continue

            # Detect if children use parent reference attributes.
            parent_ref_attr = self._detect_parent_ref_attr(root.children)
            if parent_ref_attr is None:
                continue

            # Detect which attribute is the node identifier (NodeId, Id, Key).
            node_id_attr = self._detect_node_id_attr(root.children)
            if node_id_attr is None:
                continue

            logger.debug(
                f"[TreeService] Resolving {parent_ref_attr} references "
                f"using {node_id_attr} for {root.tag}"
            )

            # Build lookup: identifier value -> TreeNode
            node_lookup: Dict[str, TreeNode] = {}
            for child in root.children:
                id_val = child.attributes.get(node_id_attr, "")
                if id_val:
                    node_lookup[id_val] = child

            # Separate root-level nodes (parent=0) from nested ones.
            root_children: List[TreeNode] = []
            nested_children: List[TreeNode] = []

            for child in root.children:
                parent_val = child.attributes.get(parent_ref_attr, "")
                if parent_val == "0" or parent_val == "":
                    root_children.append(child)
                else:
                    nested_children.append(child)

            # Re-parent nested children under their parent nodes.
            for child in nested_children:
                parent_val = child.attributes.get(parent_ref_attr, "")
                parent_node = node_lookup.get(parent_val)
                if parent_node is not None:
                    child.parent_id = parent_node.node_id
                    parent_node.children.append(child)
                else:
                    # Parent not found -- keep as root-level child.
                    logger.warning(
                        f"[TreeService] Parent {node_id_attr}={parent_val} "
                        f"not found for {child.tag} "
                        f"{node_id_attr}={child.attributes.get(node_id_attr)}"
                    )
                    root_children.append(child)

            # Apply max_depth pruning after re-parenting.
            if max_depth > 0:
                for rc in root_children:
                    self._prune_depth(rc, current_depth=1, max_depth=max_depth)

            root.children = root_children

        return roots

    def _detect_parent_ref_attr(
        self, children: List[TreeNode]
    ) -> Optional[str]:
        """Detect which parent reference attribute is used (if any)."""
        for child in children:
            for attr_name in _PARENT_REF_ATTRS:
                if attr_name in child.attributes:
                    return attr_name
        return None

    def _detect_node_id_attr(
        self, children: List[TreeNode]
    ) -> Optional[str]:
        """Detect which node identifier attribute is used."""
        for child in children:
            for attr_name in _NODE_ID_ATTRS:
                if attr_name in child.attributes:
                    return attr_name
        return None

    def _prune_depth(
        self, node: TreeNode, current_depth: int, max_depth: int
    ) -> None:
        """Recursively prune children beyond max_depth."""
        if current_depth >= max_depth:
            node.children = []
            return
        for child in node.children:
            self._prune_depth(child, current_depth + 1, max_depth)

    # -- Helpers --------------------------------------------------------------

    def _count_nodes(self, nodes: List[TreeNode]) -> int:
        """Count total nodes in a tree (recursive)."""
        count = 0
        for node in nodes:
            count += 1
            count += self._count_nodes(node.children)
        return count
