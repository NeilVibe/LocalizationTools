"""
GameData API endpoints -- folder browsing, column detection, and attribute editing.

Phase 18: Game Dev Grid -- provides REST endpoints for the Game Dev Grid
file explorer to browse gamedata folders, detect XML entity columns, and
save inline edits back to XML files.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from lxml import etree
from lxml.etree import XMLSyntaxError

from server.utils.dependencies import get_current_active_user_async

from server.tools.ldm.schemas.gamedata import (
    BrowseRequest,
    CrossRefItem,
    CrossRefsResponse,
    FileColumnsRequest,
    FileColumnsResponse,
    FolderTreeDataRequest,
    FolderTreeDataResponse,
    FolderTreeResponse,
    GameDataContextRequest,
    GameDataContextResponse,
    GameDataRow,
    GameDataRowsRequest,
    GameDataRowsResponse,
    GameDataTreeResponse,
    GameDevSaveRequest,
    GameDevSaveResponse,
    IndexBuildRequest,
    IndexBuildResponse,
    IndexSearchRequest,
    IndexSearchResult,
    IndexSearchResponse,
    IndexStatusResponse,
    DetectEntitiesRequest,
    MediaContext,
    RelatedEntity,
    TMSuggestion,
    TreeNode,
    TreeRequest,
)
from server.tools.ldm.indexing.gamedata_indexer import get_gamedata_indexer
from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher
from server.tools.ldm.services.gamedata_browse_service import (
    EDITABLE_ATTRS,
    GameDataBrowseService,
)
from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service
from server.tools.ldm.services.gamedata_edit_service import GameDataEditService
from server.tools.ldm.services.gamedata_tree_service import GameDataTreeService
from server.repositories import get_row_repository


router = APIRouter(tags=["GameData"])

# Default base directory for gamedata -- can be overridden via settings
# Uses the mock_gamedata from Phase 15 when available, falls back to project root
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root


def _get_base_dir() -> Path:
    """Get the base directory for gamedata operations.

    Checks for mock_gamedata first (Phase 15), then falls back to project root.
    """
    mock_dir = _DEFAULT_BASE_DIR / "tests" / "fixtures" / "mock_gamedata"
    if mock_dir.is_dir():
        return mock_dir
    return _DEFAULT_BASE_DIR


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/gamedata/browse", response_model=FolderTreeResponse)
async def browse_gamedata(
    request: BrowseRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Browse a gamedata folder and return tree structure with XML metadata.

    Args:
        request: Contains path to browse and optional max_depth.

    Returns:
        FolderTreeResponse with recursive folder tree and XML file metadata.
    """
    base_dir = _get_base_dir()
    browse_path = request.path if request.path else str(base_dir)

    try:
        svc = GameDataBrowseService(base_dir=base_dir)
        root_node = svc.scan_folder(browse_path, max_depth=request.max_depth)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")
    except Exception as e:
        logger.error(f"[GameData API] browse_gamedata failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return FolderTreeResponse(root=root_node, base_path=str(base_dir))


@router.post("/gamedata/register-browser-folder")
async def register_browser_folder(
    request: dict,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Register a browser-selected folder.

    In browser DEV mode, the File System Access API provides a folder handle.
    This endpoint returns the mock_gamedata path for the Game Dev Grid.
    """
    base_dir = _get_base_dir()
    return {"path": str(base_dir), "folder_name": request.get("folder_name", "")}


@router.post("/gamedata/columns", response_model=FileColumnsResponse)
async def detect_columns(
    request: FileColumnsRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Detect dynamic columns for an XML file's entities.

    Used by the frontend to configure grid columns before loading entity data.

    Args:
        request: Contains xml_path to analyze.

    Returns:
        FileColumnsResponse with column hints and editable attribute list.
    """
    base_dir = _get_base_dir()

    try:
        svc = GameDataBrowseService(base_dir=base_dir)
        result = svc.detect_columns(request.xml_path)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.xml_path}")
    except XMLSyntaxError as e:
        logger.warning(f"[GameData API] Malformed XML: {request.xml_path}: {e}")
        raise HTTPException(status_code=422, detail=f"Malformed XML: {e}")
    except Exception as e:
        logger.error(f"[GameData API] detect_columns failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return result


@router.put("/gamedata/save", response_model=GameDevSaveResponse)
async def save_gamedata(
    request: GameDevSaveRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Save an inline edit to a specific XML entity attribute.

    Preserves br-tags correctly through lxml round-trip.

    Args:
        request: Contains xml_path, entity_index, attr_name, and new_value.

    Returns:
        GameDevSaveResponse with success status and message.
    """
    base_dir = _get_base_dir()

    try:
        svc = GameDataEditService(base_dir=base_dir)
        success = svc.update_entity_attribute(
            xml_path=request.xml_path,
            entity_index=request.entity_index,
            attr_name=request.attr_name,
            new_value=request.new_value,
        )
    except ValueError as e:
        logger.warning(f"[GameData API] Invalid request: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.xml_path}")
    except XMLSyntaxError as e:
        logger.warning(f"[GameData API] Malformed XML: {request.xml_path}: {e}")
        raise HTTPException(status_code=422, detail=f"Malformed XML: {e}")
    except Exception as e:
        logger.error(f"[GameData API] save_gamedata failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not success:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid entity index {request.entity_index}",
        )

    return GameDevSaveResponse(
        success=True,
        message=f"Updated {request.attr_name} on entity {request.entity_index}",
    )


@router.post("/gamedata/rows", response_model=GameDataRowsResponse)
async def get_gamedata_rows(
    request: GameDataRowsRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Read entities from a gamedata XML file and return paginated rows.

    Returns rows in a format compatible with VirtualGrid, with entity
    attributes flattened into extra_data.  Supports text search across
    all attribute values and server-side pagination.

    Args:
        request: Contains xml_path, page, limit, and optional search term.

    Returns:
        GameDataRowsResponse with paginated rows and total counts.
    """
    base_dir = _get_base_dir()

    # --- path validation (reuse browse service) -------------------------
    svc = GameDataBrowseService(base_dir=base_dir)
    try:
        resolved = svc._validate_path(request.xml_path)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=403, detail=str(e))

    if not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {request.xml_path}",
        )

    # --- parse XML -------------------------------------------------------
    try:
        tree = etree.parse(str(resolved))
    except XMLSyntaxError as e:
        logger.warning(f"[GameData API] Malformed XML: {request.xml_path}: {e}")
        raise HTTPException(status_code=422, detail=f"Malformed XML: {e}")
    except Exception as e:
        logger.error(f"[GameData API] get_gamedata_rows parse failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    root = tree.getroot()
    entities = list(root)

    # --- Identifying-attribute heuristic ---------------------------------
    _IDENT_ATTRS = ("StrKey", "Key", "ID", "Name", "Id")

    def _string_id(elem: etree._Element) -> str:
        """Return the first identifying attribute value, or the tag name."""
        for attr in _IDENT_ATTRS:
            val = elem.get(attr)
            if val is not None:
                return val
        # Fallback: first attribute value (if any)
        if elem.attrib:
            return next(iter(elem.attrib.values()))
        return elem.tag

    def _target_value(elem: etree._Element) -> str:
        """Return the first editable attribute value or the tag name."""
        editable = EDITABLE_ATTRS.get(elem.tag, [])
        for attr in editable:
            val = elem.get(attr)
            if val is not None:
                return val
        return elem.tag

    # --- build row dicts -------------------------------------------------
    all_rows: list[GameDataRow] = []
    search_lower = request.search.lower().strip()

    for idx, entity in enumerate(entities):
        attrs = dict(entity.attrib)

        # Search filter: match against any attribute value
        if search_lower:
            matched = any(
                search_lower in val.lower() for val in attrs.values()
            )
            if not matched:
                continue

        extra = dict(attrs)
        extra["source_xml_path"] = str(resolved)
        extra["entity_index"] = idx

        all_rows.append(
            GameDataRow(
                id=idx,
                row_num=idx + 1,
                string_id=_string_id(entity),
                source=entity.tag,
                target=_target_value(entity),
                status="pending",
                extra_data=extra,
            )
        )

    # --- paginate --------------------------------------------------------
    total = len(all_rows)
    page = max(1, request.page)
    limit = max(1, min(request.limit, 500))  # cap at 500
    total_pages = max(1, (total + limit - 1) // limit)

    start = (page - 1) * limit
    end = start + limit
    page_rows = all_rows[start:end]

    logger.debug(
        f"[GameData API] Returning {len(page_rows)}/{total} rows "
        f"(page {page}/{total_pages}) for {resolved.name}"
    )

    return GameDataRowsResponse(
        rows=page_rows,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


# =============================================================================
# Tree endpoints (Phase 27)
# =============================================================================


@router.post("/gamedata/tree", response_model=GameDataTreeResponse)
async def get_gamedata_tree(
    request: TreeRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Parse an XML gamedata file and return hierarchical tree with nested nodes.

    Handles both XML-nested hierarchies (GimmickGroup > GimmickInfo) and
    reference-based hierarchies (SkillNode ParentNodeId).

    Args:
        request: Contains path to XML file and optional max_depth (-1 = unlimited).

    Returns:
        GameDataTreeResponse with nested TreeNode roots.
    """
    base_dir = _get_base_dir()
    try:
        svc = GameDataTreeService(base_dir=base_dir)
        result = svc.parse_file(request.path, max_depth=request.max_depth)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.path}")
    except XMLSyntaxError as e:
        logger.warning(f"[GameData API] Malformed XML: {request.path}: {e}")
        raise HTTPException(status_code=422, detail=f"Malformed XML: {e}")
    except Exception as e:
        logger.error(f"[GameData API] get_gamedata_tree failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return result


@router.post("/gamedata/tree/folder", response_model=FolderTreeDataResponse)
async def get_gamedata_tree_folder(
    request: FolderTreeDataRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Parse all XML files in a folder and return combined hierarchical tree.

    Used by the tree UI to load an entire gamedata folder at once.

    Args:
        request: Contains path to folder and optional max_depth.

    Returns:
        FolderTreeDataResponse with tree data for each XML file.
    """
    base_dir = _get_base_dir()
    try:
        svc = GameDataTreeService(base_dir=base_dir)
        result = svc.parse_folder(request.path, max_depth=request.max_depth)
    except ValueError as e:
        logger.warning(f"[GameData API] Path traversal attempt: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")
    except Exception as e:
        logger.error(f"[GameData API] get_gamedata_tree_folder failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return result


# =============================================================================
# Index endpoints (Phase 29: Multi-Tier Indexing)
# =============================================================================


@router.post("/gamedata/index/build", response_model=IndexBuildResponse)
async def build_gamedata_index(
    request: IndexBuildRequest,
    user=Depends(get_current_active_user_async),
):
    """Build multi-tier indexes from a gamedata folder.

    Parses all XML files in folder via GameDataTreeService.parse_folder(),
    then feeds TreeNode data to GameDataIndexer.build_from_folder_tree().
    """
    indexer = get_gamedata_indexer()
    tree_service = GameDataTreeService(base_dir=_get_base_dir())

    try:
        folder_data = tree_service.parse_folder(request.path)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if folder_data.total_nodes == 0:
        raise HTTPException(status_code=400, detail="No entities found in folder")

    try:
        result = indexer.build_from_folder_tree(folder_data)
    except Exception as e:
        logger.error(f"[GameData API] Index build failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Index build failed: {e}")

    # Phase 30: Build reverse index for cross-reference resolution
    try:
        context_service = get_gamedata_context_service()
        context_service.build_reverse_index(folder_data)
    except Exception as e:
        logger.warning(f"[GameData API] Reverse index build failed (non-fatal): {e}")

    return IndexBuildResponse(**result, status="ready")


@router.post("/gamedata/index/search", response_model=IndexSearchResponse)
async def search_gamedata_index(
    request: IndexSearchRequest,
    user=Depends(get_current_active_user_async),
):
    """Search gamedata entities using 6-tier cascade."""
    indexer = get_gamedata_indexer()
    if not indexer.is_ready:
        raise HTTPException(status_code=400, detail="Index not built yet")

    try:
        searcher = GameDataSearcher(indexer.indexes)
        result = searcher.search(request.query, top_k=request.top_k, threshold=request.threshold)
    except Exception as e:
        logger.error(f"[GameData API] Search failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return IndexSearchResponse(
        tier=result["tier"],
        tier_name=result["tier_name"],
        results=[IndexSearchResult(**r) for r in result["results"]],
        perfect_match=result["perfect_match"],
    )


@router.post("/gamedata/index/detect")
async def detect_entities_in_text(
    request: DetectEntitiesRequest,
    user=Depends(get_current_active_user_async),
):
    """Detect entity names in text via Aho-Corasick scan."""
    indexer = get_gamedata_indexer()
    if not indexer.is_ready:
        raise HTTPException(status_code=400, detail="Index not built yet")

    try:
        searcher = GameDataSearcher(indexer.indexes)
        entities = searcher.detect_entities(request.text)
    except Exception as e:
        logger.error(f"[GameData API] Entity detection failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")

    return {"entities": entities}


@router.get("/gamedata/index/status", response_model=IndexStatusResponse)
async def get_index_status(
    user=Depends(get_current_active_user_async),
):
    """Get current index build status."""
    indexer = get_gamedata_indexer()
    status = indexer.get_status()
    return IndexStatusResponse(**status)


# =============================================================================
# Context Intelligence endpoint (Phase 30)
# =============================================================================


@router.post("/gamedata/context", response_model=GameDataContextResponse)
async def get_gamedata_context(
    request: GameDataContextRequest,
    user=Depends(get_current_active_user_async),
    row_repo=Depends(get_row_repository),
):
    """Get combined context intelligence for a gamedata entity.

    Returns cross-references, related entities, TM suggestions from
    language data, and media context for the given node.
    """
    context_service = get_gamedata_context_service()

    # Reconstruct minimal TreeNode from request
    node = TreeNode(
        node_id=request.node_id,
        tag=request.tag,
        attributes=request.attributes,
        editable_attrs=request.editable_attrs,
    )

    try:
        cross_refs_data = context_service.get_cross_refs(request.node_id, node)
        cross_refs = CrossRefsResponse(
            forward=[CrossRefItem(**ref) for ref in cross_refs_data["forward"]],
            backward=[CrossRefItem(**ref) for ref in cross_refs_data["backward"]],
        )
    except Exception as e:
        logger.error(f"[GameData API] Cross-ref resolution failed: {e}")
        cross_refs = CrossRefsResponse()

    try:
        related_data = context_service.get_related(node)
        related = [RelatedEntity(**r) for r in related_data]
    except Exception as e:
        logger.error(f"[GameData API] Related search failed: {e}")
        related = []

    # TM suggestions (conditional on StrKey)
    has_strkey = context_service.has_strkey(node)
    tm_suggestions = []
    if has_strkey:
        try:
            tm_data = await context_service.get_tm_suggestions(node, row_repo)
            tm_suggestions = [TMSuggestion(**s) for s in tm_data]
        except Exception as e:
            logger.error(f"[GameData API] TM suggestions failed: {e}")

    try:
        media_data = context_service.get_media(node)
        media = MediaContext(**media_data)
    except Exception as e:
        logger.error(f"[GameData API] Media resolution failed: {e}")
        media = MediaContext()

    return GameDataContextResponse(
        cross_refs=cross_refs,
        related=related,
        tm_suggestions=tm_suggestions,
        has_strkey=has_strkey,
        media=media,
    )
