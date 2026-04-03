"""Audio Codex API endpoints -- bulk list, category tree, detail, playback.

Phase 48->108: Audio Codex UI -- MDG-exact playback via winsound.
All data comes from MegaIndex D10/D11/D20/D21/C4/C5 dicts.

Endpoints:
  GET  /codex/audio            - Bulk audio list with category/search filtering
  GET  /codex/audio/categories - Category tree from D20 export_path grouping
  POST /codex/audio/play/{event_name}  - Play audio via winsound (MDG-exact)
  POST /codex/audio/stop               - Stop playback
  GET  /codex/audio/playback-status    - Playback state for frontend polling
  POST /codex/audio/cleanup            - Clean cached WAV files
  GET  /codex/audio/stream/{event_name} - WEM-to-WAV streaming (DEV fallback)
  GET  /codex/audio/{event_name}        - Full audio detail
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_audio import (
    AudioCardResponse,
    AudioCategoryNode,
    AudioCategoryTreeResponse,
    AudioDetailResponse,
    AudioListResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index
from server.tools.ldm.services.media_converter import get_media_converter
from server.tools.ldm.services.perforce_path_service import convert_to_wsl_path


router = APIRouter(prefix="/codex/audio", tags=["Codex Audio"])


# =============================================================================
# Helpers
# =============================================================================


def _build_audio_card(event_name: str, mega, language: str = "eng") -> AudioCardResponse:
    """Build an AudioCardResponse from MegaIndex lookups."""
    event_lower = event_name.lower()
    return AudioCardResponse(
        event_name=event_name,
        string_id=mega.event_to_stringid_lookup(event_name),
        script_kr=mega.get_script_kr(event_name),
        script_eng=mega.get_script_eng(event_name),
        export_path=mega.event_to_export_path.get(event_lower),
        has_wem=mega.get_audio_path_by_event_for_lang(event_name, language) is not None,
        xml_order=mega.event_to_xml_order.get(event_lower),
    )


def _build_category_tree(
    event_to_export_path: Dict[str, str],
) -> List[AudioCategoryNode]:
    """Build nested category tree from D20 export_path grouping.

    Each export_path like "Dialog/QuestDialog/SubFolder" becomes a nested tree:
    Dialog -> QuestDialog -> SubFolder with counts at each level.
    """
    # Count events per full path
    path_counts: Dict[str, int] = defaultdict(int)
    for _event, export_path in event_to_export_path.items():
        if export_path:
            path_counts[export_path] += 1

    # Build tree structure from all paths
    # node_map: full_path -> {name, children_map, count}
    node_map: Dict[str, dict] = {}

    for full_path, count in path_counts.items():
        parts = full_path.split("/")
        for i, part in enumerate(parts):
            current_path = "/".join(parts[: i + 1])
            if current_path not in node_map:
                node_map[current_path] = {
                    "name": part,
                    "full_path": current_path,
                    "count": 0,
                    "children": {},
                }
            # Only leaf paths get the count
            if current_path == full_path:
                node_map[current_path]["count"] += count

            # Wire parent -> child
            if i > 0:
                parent_path = "/".join(parts[:i])
                if parent_path in node_map:
                    node_map[parent_path]["children"][current_path] = True

    def _to_node(path: str) -> AudioCategoryNode:
        info = node_map[path]
        children = []
        for child_path in sorted(info["children"].keys()):
            children.append(_to_node(child_path))
        # Roll up count: own count + sum of children
        total_count = info["count"] + sum(c.count for c in children)
        return AudioCategoryNode(
            name=info["name"],
            full_path=info["full_path"],
            count=total_count,
            children=children,
        )

    # Find root nodes (paths with no parent in node_map)
    roots = []
    for path in sorted(node_map.keys()):
        parts = path.split("/")
        if len(parts) == 1:
            roots.append(_to_node(path))

    return roots


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/cleanup")
async def cleanup_audio_cache(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Clean up cached WAV files from WEM-to-WAV conversions.

    MDG-exact: audio_handler.cleanup_temp_files() equivalent.
    """
    try:
        converter = get_media_converter()
        count = converter.cleanup_wav_cache()
        return {"count": count}
    except Exception as exc:
        logger.error(f"[Audio Codex] cleanup_audio_cache failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/play/{event_name}")
async def play_audio(
    event_name: str,
    language: str = Query(default="eng", description="Audio language folder"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Play audio via winsound -- MDG-exact AudioHandler.play() port.

    Converts WEM -> WAV via vgmstream-cli, then plays via winsound.PlaySound()
    in a background thread. On Linux (DEV), returns error gracefully.
    """
    try:
        from server.tools.ldm.services.audio_playback import get_audio_playback
        player = get_audio_playback()
        result = player.play(event_name, language=language)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Audio Codex] play_audio failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop")
async def stop_audio(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Stop audio playback -- MDG-exact AudioHandler.stop() port."""
    try:
        from server.tools.ldm.services.audio_playback import get_audio_playback
        player = get_audio_playback()
        return player.stop()
    except Exception as exc:
        logger.error(f"[Audio Codex] stop_audio failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/playback-status")
async def get_playback_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get current playback state for frontend polling."""
    try:
        from server.tools.ldm.services.audio_playback import get_audio_playback
        player = get_audio_playback()
        return player.get_status()
    except Exception as exc:
        logger.error(f"[Audio Codex] get_playback_status failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/categories", response_model=AudioCategoryTreeResponse)
async def get_audio_categories(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get hierarchical category tree from D20 export_path grouping.

    Returns nested tree structure with event counts per category.
    """
    try:
        mega = get_mega_index()
        categories = _build_category_tree(mega.event_to_export_path)
        total_events = len(mega.event_to_stringid)  # D11, matches list_audio source

        # Phase 110: diagnostic logging for tree structure
        def _max_depth(nodes, d=1):
            if not nodes:
                return d
            return max(_max_depth(n.children, d + 1) for n in nodes)

        depth = _max_depth(categories, 0) if categories else 0
        sample_paths = list(mega.event_to_export_path.values())[:5]
        logger.info(
            f"[PHASE110:AUDIO] category tree: {len(categories)} roots, "
            f"max_depth={depth}, total_events={total_events}, "
            f"sample_paths={sample_paths}"
        )

        return AudioCategoryTreeResponse(
            categories=categories,
            total_events=total_events,
        )
    except Exception as exc:
        logger.error(f"[Audio Codex] get_audio_categories failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stream/{event_name}")
async def stream_audio(
    event_name: str,
    language: str = Query(default="eng", description="Audio language folder (eng, kor, jpn, etc.)"),
):
    """Stream WAV audio for an event_name.

    Looks up WEM path via MegaIndex D10, converts WEM -> WAV via MediaConverter,
    and returns the WAV file. Unauthenticated for <audio> element compatibility.
    """
    try:
        mega = get_mega_index()
        wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)

        if wem_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"No audio found for event '{event_name}' in language '{language}'",
            )

        logger.info(f"[Audio Codex] Streaming: event={event_name}, wem_path={wem_path}, exists={wem_path.exists()}")

        # If the path is already a WAV file, serve it directly
        if wem_path.suffix.lower() == ".wav" and wem_path.exists():
            logger.info(f"[Audio Codex] Serving WAV directly: {wem_path} ({wem_path.stat().st_size} bytes)")
            return FileResponse(str(wem_path), media_type="audio/wav")

        # Convert Windows path to WSL path, then WEM -> WAV
        wsl_path = convert_to_wsl_path(str(wem_path))
        converter = get_media_converter()

        wav_path = await asyncio.to_thread(
            converter.convert_wem_to_wav, Path(wsl_path)
        )
        if wav_path is None:
            logger.error(f"[Audio Codex] Conversion returned None for {wem_path}")
            raise HTTPException(status_code=500, detail="Audio conversion failed")

        wav_size = wav_path.stat().st_size if wav_path.exists() else 0
        logger.info(f"[Audio Codex] Serving converted WAV: {wav_path} ({wav_size} bytes)")
        return FileResponse(str(wav_path), media_type="audio/wav")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Audio Codex] stream_audio failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Audio streaming failed: {exc}")


@router.get("/{event_name}", response_model=AudioDetailResponse)
async def get_audio_detail(
    event_name: str,
    language: str = Query(default="eng", description="Audio language folder (eng, kor, jpn, etc.)"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get full audio detail for a single event.

    Returns all MegaIndex lookups plus computed stream URL.
    """
    try:
        mega = get_mega_index()

        # Check event exists in D11 (events with StringId linkage)
        string_id = mega.event_to_stringid_lookup(event_name)
        if string_id is None:
            # Also check D10 (events with WEM path but no StringId)
            wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)
            if wem_path is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Audio event not found: {event_name}",
                )

        wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)
        has_wem = wem_path is not None
        event_lower = event_name.lower()

        return AudioDetailResponse(
            event_name=event_name,
            string_id=string_id,
            script_kr=mega.get_script_kr(event_name),
            script_eng=mega.get_script_eng(event_name),
            export_path=mega.event_to_export_path.get(event_lower),
            has_wem=has_wem,
            xml_order=mega.event_to_xml_order.get(event_lower),
            wem_path=str(wem_path) if wem_path else None,
            stream_url=f"/api/ldm/codex/audio/stream/{event_name}?language={language}" if has_wem else None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Audio Codex] get_audio_detail failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=AudioListResponse)
async def list_audio(
    category: Optional[str] = Query(None, description="Filter by D20 export_path prefix"),
    q: Optional[str] = Query(None, description="Search across event_name, script, stringid"),
    language: str = Query(default="eng", description="Audio language folder (eng, kor, jpn, etc.)"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get all audio events with optional category filtering and text search.

    - category: filters by D20 export_path prefix (e.g. "Dialog/QuestDialog")
    - q: searches across event_name, script_kr (C4), script_eng (C5), string_id (D11)
    """
    try:
        mega = get_mega_index()

        # Master list: all events from D11 (events with StringId linkage)
        all_events = list(mega.event_to_stringid.keys())

        # Category filter via D20 export_path prefix
        if category:
            category_lower = category.lower()
            all_events = [
                ev for ev in all_events
                if mega.event_to_export_path.get(ev, "").lower().startswith(category_lower)
            ]

        # Text search filtering
        if q:
            q_lower = q.lower()
            filtered = []
            for ev in all_events:
                # Check event_name
                if q_lower in ev:
                    filtered.append(ev)
                    continue
                # Check string_id
                sid = mega.event_to_stringid.get(ev, "")
                if q_lower in sid.lower():
                    filtered.append(ev)
                    continue
                # Check script_kr (C4)
                script_kr = mega.get_script_kr(ev)
                if script_kr and q_lower in script_kr.lower():
                    filtered.append(ev)
                    continue
                # Check script_eng (C5)
                script_eng = mega.get_script_eng(ev)
                if script_eng and q_lower in script_eng.lower():
                    filtered.append(ev)
                    continue
            all_events = filtered

        # MDG sort: (export_path, xml_order, strkey) for category browse
        # search.py:get_entries_by_export_path sorts (export_path, xml_order, strkey)
        # search.py:search sorts (has_image, match_score, name_length) -- not applicable for bulk load
        def _sort_key(ev: str):
            export_path = mega.event_to_export_path.get(ev, "")
            order = mega.event_to_xml_order.get(ev)
            if order is not None:
                return (export_path, 0, order, ev)
            return (export_path, 1, 0, ev)

        all_events.sort(key=_sort_key)

        # Build cards for ALL matching events
        items = [_build_audio_card(ev, mega, language=language) for ev in all_events]

        return AudioListResponse(
            items=items,
            total=len(items),
            category_filter=category,
        )
    except Exception as exc:
        logger.error(f"[Audio Codex] list_audio failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
