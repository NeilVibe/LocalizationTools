"""
GameData API endpoints -- folder browsing, column detection, and attribute editing.

Phase 18: Game Dev Grid -- provides REST endpoints for the Game Dev Grid
file explorer to browse gamedata folders, detect XML entity columns, and
save inline edits back to XML files.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from lxml import etree
from lxml.etree import XMLSyntaxError

from server.utils.dependencies import get_current_active_user_async

import httpx

from server.tools.ldm.schemas.gamedata import (
    AISummaryRequest,
    AISummaryResponse,
    BrowseRequest,
    CrossRefItem,
    CrossRefsResponse,
    DictionaryLookupRequest,
    DictionaryLookupResponse,
    DictionaryMatch,
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
from server.tools.ldm.services.mega_index import get_mega_index
from server.tools.ldm.services.xml_sanitizer import sanitize_and_parse
from server.tools.ldm.services.category_mapper import TwoTierCategoryMapper, get_text_state
from server.tools.ldm.indexing.gamedata_indexer import get_gamedata_indexer
from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher
from server.tools.ldm.services.gamedata_browse_service import (
    EDITABLE_ATTRS,
    GameDataBrowseService,
)
from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service
from server.tools.ldm.services.gamedata_edit_service import GameDataEditService
from server.tools.ldm.services.gamedata_tree_service import GameDataTreeService
from server.repositories import get_row_repository, get_tm_repository


router = APIRouter(tags=["GameData"])

# Default base directory for gamedata -- can be overridden via settings
# Uses the mock_gamedata from Phase 15 when available, falls back to project root
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root


def _get_base_dir() -> Path:
    """Get the base directory for gamedata operations.

    Priority:
    1. GAMEDATA_BASE_DIR env var (user-configured, e.g. Perforce root)
    2. In DEV mode: mock_gamedata if it exists (for testing)
    3. PerforcePathService configured drive root (e.g. D:\perforce\cd\cd_beta\resource)
    4. Project root (fallback for unconfigured state)
    """
    import os
    env_dir = os.getenv("GAMEDATA_BASE_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if p.is_dir():
            return p

    # Only use mock_gamedata in DEV mode -- production builds should not be locked to test fixtures
    if os.getenv("DEV_MODE", "false").lower() == "true":
        mock_dir = _DEFAULT_BASE_DIR / "tests" / "fixtures" / "mock_gamedata"
        if mock_dir.is_dir():
            return mock_dir

    # Production: use PerforcePathService drive root as base directory.
    # This allows browsing Perforce game data outside the install directory.
    # Uses generate_paths() directly (Windows paths) instead of resolved WSL paths,
    # because WSL paths (/mnt/d/...) don't exist on Windows.
    try:
        from server.tools.ldm.services.perforce_path_service import get_perforce_path_service, generate_paths
        path_svc = get_perforce_path_service()
        status = path_svc.get_status()
        drive = status["drive"]
        branch = status["branch"]
        if drive != "MOCK":
            raw_paths = generate_paths(drive, branch)
            knowledge_path = Path(raw_paths["knowledge_folder"])
            gamedata_root = knowledge_path.parent.parent  # .../resource/GameData
            if gamedata_root.is_dir():
                return gamedata_root
            logger.warning(f"GameData root not found: {gamedata_root} -- using install directory")
    except ImportError:
        logger.debug("PerforcePathService not available, using default base dir")
    except (KeyError, TypeError) as e:
        logger.warning(f"PerforcePathService misconfigured: {e} -- using default base dir")
    except Exception as e:
        logger.error(f"Unexpected error resolving Perforce base dir: {e}")

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
        root_node = await asyncio.to_thread(svc.scan_folder, browse_path, request.max_depth)
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


@router.post("/gamedata/trigger-mega-build")
async def trigger_mega_build(
    _user=Depends(get_current_active_user_async),
):
    """Trigger MegaIndex build after gamedata folder is loaded.

    Non-blocking response -- the frontend fires this as fire-and-forget
    after the gamedata folder tree loads.  Returns immediately with status.
    """
    try:
        mi = get_mega_index()
        if mi._built:
            return {"status": "already_built", "stats": mi.stats()}
        mi.build()
        return {"status": "success", "stats": mi.stats()}
    except Exception as e:
        logger.error(f"MegaIndex auto-build failed: {e}")
        return {"status": "error", "error": str(e)}


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
        result = await asyncio.to_thread(svc.detect_columns, request.xml_path)
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
        success = await asyncio.to_thread(
            svc.update_entity_attribute,
            request.xml_path, request.entity_index, request.attr_name, request.new_value,
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

    # --- parse XML (sanitized + virtual root + dual-pass) ----------------
    root = await asyncio.to_thread(sanitize_and_parse, resolved)
    if root is None:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse XML: {request.xml_path}",
        )
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

    # --- Category mapper for this file (LDE two-tier algorithm) -----------
    category_mapper = TwoTierCategoryMapper(base_folder=resolved.parent.parent)
    file_stem = resolved.stem
    if file_stem.endswith(".loc"):
        file_stem = file_stem[:-4]
    file_category = category_mapper.get_category(resolved)

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

        # LDE enrichment: category, file_name, text_state
        extra["category"] = file_category
        extra["file_name"] = file_stem
        # Detect Korean in any text-like attribute for text_state
        text_for_detection = ""
        for text_attr in ("Str", "StrOrigin", "Name", "Desc", "DescOrigin"):
            val = attrs.get(text_attr, "")
            if val:
                text_for_detection = val
                break
        extra["text_state"] = get_text_state(text_for_detection)

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


@router.post("/gamedata/context/ai-summary", response_model=AISummaryResponse)
async def get_ai_summary(
    request: AISummaryRequest,
    user=Depends(get_current_active_user_async),
):
    """Generate an AI context summary for a gamedata entity using Qwen3 via Ollama.

    On-demand endpoint -- only called when user clicks "Generate AI Context".
    Checks Ollama availability first to fail fast.
    """
    # Check Ollama availability first (fast fail)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.get("http://localhost:11434/api/tags")
    except Exception:
        return AISummaryResponse(summary="", available=False)

    context_service = get_gamedata_context_service()

    # Reconstruct minimal TreeNode from request
    node = TreeNode(
        node_id=request.node_id,
        tag=request.tag,
        attributes=request.attributes,
        editable_attrs=request.editable_attrs,
    )

    # Get cross-refs and related for context
    try:
        cross_refs = context_service.get_cross_refs(request.node_id, node)
    except Exception:
        cross_refs = {"forward": [], "backward": []}

    try:
        related = context_service.get_related(node)
    except Exception:
        related = []

    # Generate AI summary
    summary = await context_service.generate_ai_summary(node, cross_refs, related)

    return AISummaryResponse(
        summary=summary,
        model="qwen3",
        available=True,
    )


# =============================================================================
# Dictionary Lookup endpoint (Phase 38A)
# =============================================================================


def _tier_to_match_type(tier: int) -> str:
    """Map cascade tier number to match_type category."""
    if tier <= 1:
        return "exact"
    elif tier <= 4:
        return "similar"
    return "fuzzy"


@router.post("/gamedata/dictionary-lookup", response_model=DictionaryLookupResponse)
async def dictionary_lookup(
    request: DictionaryLookupRequest,
    user=Depends(get_current_active_user_async),
    row_repo=Depends(get_row_repository),
    tm_repo=Depends(get_tm_repository),
):
    """Search for matching terms in loaded gamedata index + TM entries.

    Combines results from the 6-tier cascade search (gamedata index) and
    TM suggestion service (language data). Deduplicates by source text
    and returns sorted by score descending.
    """
    start = time.perf_counter()
    results: list[DictionaryMatch] = []
    # Dedup within each category: gamedata entities vs TM translations
    seen_gamedata: set[str] = set()
    seen_tm: set[str] = set()

    # --- 1. Gamedata index search (if index is built) ---
    indexer = get_gamedata_indexer()
    if indexer.is_ready:
        try:
            searcher = GameDataSearcher(indexer.indexes)
            cascade = searcher.search(
                request.text,
                top_k=request.top_k,
                threshold=request.threshold,
            )
            tier = cascade["tier"]
            tier_name = cascade["tier_name"]

            for r in cascade["results"]:
                source = r.get("entity_name", "")
                if not source or source in seen_gamedata:
                    continue
                seen_gamedata.add(source)
                results.append(DictionaryMatch(
                    source=source,
                    target=r.get("entity_desc", ""),
                    score=r.get("score", 0.0),
                    tier=tier,
                    tier_name=tier_name,
                    match_type=_tier_to_match_type(tier),
                ))
        except Exception as e:
            logger.warning(f"[DictionaryLookup] Gamedata search failed: {e}")

    def _add_tm_result(source: str, target: str, similarity: float, tier_label: str):
        """Add a TM translation result (deduped separately from gamedata)."""
        if not source or source in seen_tm:
            return
        seen_tm.add(source)
        if similarity >= 0.99:
            match_type, tier = "exact", 1
        elif similarity >= 0.90:
            match_type, tier = "similar", 2
        else:
            match_type, tier = "fuzzy", 5
        results.append(DictionaryMatch(
            source=source,
            target=target,
            score=similarity,
            tier=tier,
            tier_name=tier_label,
            match_type=match_type,
        ))

    # --- 2. TM suggestions from project rows (if loaded) ---
    try:
        tm_results = await row_repo.suggest_similar(
            source=request.text,
            threshold=request.threshold,
            max_results=request.top_k,
        )
        for s in tm_results:
            _add_tm_result(
                s.get("source", ""),
                s.get("target", ""),
                s.get("similarity", 0.0),
                "tm_suggestion",
            )
    except Exception as e:
        logger.debug(f"[DictionaryLookup] TM suggest failed (expected offline): {e}")

    # --- 3. TM entries search (Translation Memory databases) ---
    try:
        all_tms = await tm_repo.get_all()
        for tm in all_tms:
            tm_id = tm.get("id") if isinstance(tm, dict) else getattr(tm, "id", None)
            if not tm_id:
                continue
            tm_entries = await tm_repo.search_similar(
                tm_id=tm_id,
                source=request.text,
                threshold=request.threshold,
                max_results=request.top_k,
            )
            tm_name = (tm.get("name") if isinstance(tm, dict) else getattr(tm, "name", "TM"))
            for s in tm_entries:
                _add_tm_result(
                    s.get("source", ""),
                    s.get("target", ""),
                    s.get("similarity", 0.0),
                    f"tm:{tm_name}",
                )
    except Exception as e:
        logger.debug(f"[DictionaryLookup] TM entries search failed: {e}")

    # --- 4. Sort by score descending, cap at top_k ---
    results.sort(key=lambda m: m.score, reverse=True)
    results = results[: request.top_k]

    elapsed_ms = (time.perf_counter() - start) * 1000

    return DictionaryLookupResponse(
        results=results,
        query=request.text,
        search_time_ms=round(elapsed_ms, 2),
    )
