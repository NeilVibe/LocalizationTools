"""
Merge-to-disk endpoints — write corrections directly to files on disk.

POST /api/ldm/merge/to-file     -- Merge source DB rows into a single target file on disk
POST /api/ldm/merge/to-folder   -- Merge source folder files into target folder on disk (suffix matching)

These endpoints use QuickTranslate's battle-tested xml_transfer engine:
- Parse target XML with lxml
- Apply corrections via loc.set("Str", new_str)
- Make file writable (chmod) if needed
- Write modified XML back to disk
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import get_row_repository, get_file_repository

router = APIRouter(tags=["LDM"])


# =============================================================================
# Request / Response models
# =============================================================================


class MergeToFileRequest(BaseModel):
    """Merge source DB rows into a single target file on disk."""
    source_file_id: int = Field(..., description="File ID in DB containing corrections")
    target_path: str = Field(..., description="Absolute path to target file on disk")
    match_mode: str = Field(default="strict", description="strict, stringid_only, strorigin_only, etc.")
    dry_run: bool = Field(default=False, description="Preview without writing")
    only_untranslated: bool = Field(default=False, description="Only fill empty/Korean targets")
    ignore_spaces: bool = Field(default=False)
    ignore_punctuation: bool = Field(default=False)


class MergeToFolderRequest(BaseModel):
    """Merge source folder's files into target folder on disk, matched by language suffix."""
    source_file_ids: list[int] = Field(..., description="List of file IDs in DB (source folder contents)")
    target_folder_path: str = Field(..., description="Absolute path to target folder on disk")
    match_mode: str = Field(default="strict")
    dry_run: bool = Field(default=False)
    only_untranslated: bool = Field(default=False)
    ignore_spaces: bool = Field(default=False)
    ignore_punctuation: bool = Field(default=False)
    unique_only: bool = Field(default=False)
    non_script_only: bool = Field(default=False)
    all_categories: bool = Field(default=False)


# =============================================================================
# Helpers: Convert DB rows → correction dicts for QT engine
# =============================================================================


def _db_rows_to_corrections(rows: list[dict]) -> list[dict]:
    """Convert DB row dicts to QT correction format.

    DB row: {id, string_id, source, target, status, ...}
    QT correction: {string_id, str_origin, corrected, desc_origin, category, ...}
    """
    corrections = []
    for row in rows:
        target = (row.get("target") or "").strip()
        source = (row.get("source") or "").strip()
        string_id = (row.get("string_id") or "").strip()

        if not target or not source:
            continue

        corrections.append({
            "string_id": string_id,
            "str_origin": source,
            "corrected": target,
            "desc_origin": (row.get("desc_origin") or "").strip(),
            "category": (row.get("category") or "Uncategorized"),
            "filepath": (row.get("filepath") or "").strip(),
        })
    return corrections


def _extract_language_suffix(filename: str) -> Optional[str]:
    """Extract language code from filename like languagedata_KOR.loc.xml → KOR."""
    import re
    # Standard pattern: languagedata_XXX.loc.xml or languagedata_XXX.xml
    m = re.match(r"languagedata_([a-zA-Z\-]+)", filename, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Fallback: last underscore segment before extension
    stem = Path(filename).stem
    if stem.endswith(".loc"):
        stem = stem[:-4]
    parts = stem.split("_")
    if len(parts) >= 2:
        return parts[-1].upper()
    return None


# =============================================================================
# Single file merge-to-disk
# =============================================================================


@router.post("/merge/to-file")
async def merge_to_file(
    request: MergeToFileRequest,
    current_user: dict = Depends(get_current_active_user_async),
    row_repo=Depends(get_row_repository),
):
    """Merge corrections from a DB file into a target XML file on disk.

    Flow:
    1. Fetch source rows from DB
    2. Convert to QT correction format
    3. Call merge_corrections_to_xml (or appropriate match mode)
    4. QT engine parses target, applies corrections, writes back to disk
    5. Return stats
    """
    from server.services.merge.xml_transfer import (
        merge_corrections_to_xml,
        merge_corrections_stringid_only,
    )

    target_path = Path(request.target_path)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Target file not found: {request.target_path}")

    # Fetch source rows
    source_rows = await row_repo.get_all_for_file(request.source_file_id)
    if not source_rows:
        raise HTTPException(status_code=404, detail=f"No rows for source file {request.source_file_id}")

    # Convert to QT correction format
    corrections = _db_rows_to_corrections(source_rows)
    if not corrections:
        return {"matched": 0, "updated": 0, "not_found": 0, "message": "No valid corrections after filtering"}

    logger.info(
        "[MERGE-TO-DISK] file: source=%d (%d corrections) → %s, mode=%s",
        request.source_file_id, len(corrections), target_path.name, request.match_mode,
    )

    # Run QT merge engine (CPU-bound)
    mode = request.match_mode

    def _do_merge():
        if mode == "stringid_only":
            return merge_corrections_stringid_only(
                xml_path=target_path,
                corrections=corrections,
                dry_run=request.dry_run,
                only_untranslated=request.only_untranslated,
            )
        else:
            # strict mode (default) — uses full (StringID, StrOrigin) matching
            return merge_corrections_to_xml(
                xml_path=target_path,
                corrections=corrections,
                dry_run=request.dry_run,
                only_untranslated=request.only_untranslated,
            )

    result = await asyncio.to_thread(_do_merge)

    action = "preview" if request.dry_run else "written"
    logger.info(
        "[MERGE-TO-DISK] %s: matched=%d, updated=%d, not_found=%d, file=%s",
        action, result.get("matched", 0), result.get("updated", 0),
        result.get("not_found", 0), target_path.name,
    )

    return result


# =============================================================================
# Folder merge-to-disk (with language suffix matching)
# =============================================================================


@router.post("/merge/to-folder")
async def merge_to_folder(
    request: MergeToFolderRequest,
    current_user: dict = Depends(get_current_active_user_async),
    row_repo=Depends(get_row_repository),
    file_repo=Depends(get_file_repository),
):
    """Merge corrections from DB files into a target folder on disk.

    Flow:
    1. Fetch all source rows, group by language suffix from their filename
    2. Scan target folder for XML files, group by language suffix
    3. For each matching language: merge corrections into target files
    4. Write all modified files back to disk
    5. Return per-file and aggregate stats

    Uses SSE streaming for live progress.
    """
    from server.services.merge.xml_transfer import merge_corrections_to_xml

    target_folder = Path(request.target_folder_path)
    if not target_folder.is_dir():
        raise HTTPException(status_code=404, detail=f"Target folder not found: {request.target_folder_path}")

    # Fetch all source files and group corrections by language
    lang_corrections: dict[str, list[dict]] = {}

    for file_id in request.source_file_ids:
        rows = await row_repo.get_all_for_file(file_id)
        if not rows:
            continue

        # Get filename to extract language suffix
        file_meta = await file_repo.get(file_id)
        if not file_meta:
            continue

        filename = file_meta.get("name", "") or file_meta.get("original_filename", "")
        lang = _extract_language_suffix(filename)
        if not lang:
            logger.warning("[MERGE-TO-FOLDER] Cannot extract language from %s, skipping", filename)
            continue

        corrections = _db_rows_to_corrections(rows)
        if corrections:
            if lang not in lang_corrections:
                lang_corrections[lang] = []
            lang_corrections[lang].extend(corrections)

    if not lang_corrections:
        return {"message": "No valid corrections found", "files_processed": 0}

    # Scan target folder for XML files grouped by language suffix
    target_files_by_lang: dict[str, list[Path]] = {}
    for f in target_folder.rglob("*.xml"):
        lang = _extract_language_suffix(f.name)
        if lang:
            if lang not in target_files_by_lang:
                target_files_by_lang[lang] = []
            target_files_by_lang[lang].append(f)

    # Also scan .loc.xml files
    for f in target_folder.rglob("*.loc.xml"):
        lang = _extract_language_suffix(f.name)
        if lang and lang not in target_files_by_lang:
            # Already caught by *.xml glob, but ensure coverage
            pass

    logger.info(
        "[MERGE-TO-FOLDER] %d source languages, %d target languages, folder=%s",
        len(lang_corrections), len(target_files_by_lang), target_folder,
    )

    # Merge each matching language
    results = {
        "files_processed": 0,
        "total_matched": 0,
        "total_updated": 0,
        "total_not_found": 0,
        "per_language": {},
        "per_file": {},
        "unmatched_languages": [],
    }

    async def _merge_lang(lang: str, corrections: list[dict], target_files: list[Path]):
        lang_stats = {"matched": 0, "updated": 0, "not_found": 0, "files": 0}

        for target_path in target_files:
            def _do_merge():
                return merge_corrections_to_xml(
                    xml_path=target_path,
                    corrections=corrections,
                    dry_run=request.dry_run,
                    only_untranslated=request.only_untranslated,
                )

            file_result = await asyncio.to_thread(_do_merge)

            lang_stats["matched"] += file_result.get("matched", 0)
            lang_stats["updated"] += file_result.get("updated", 0)
            lang_stats["not_found"] += file_result.get("not_found", 0)
            lang_stats["files"] += 1
            results["per_file"][str(target_path)] = {
                "matched": file_result.get("matched", 0),
                "updated": file_result.get("updated", 0),
            }

        return lang_stats

    for lang, corrections in lang_corrections.items():
        target_files = target_files_by_lang.get(lang, [])
        if not target_files:
            results["unmatched_languages"].append(lang)
            logger.warning("[MERGE-TO-FOLDER] No target files for language %s", lang)
            continue

        lang_stats = await _merge_lang(lang, corrections, target_files)
        results["per_language"][lang] = lang_stats
        results["files_processed"] += lang_stats["files"]
        results["total_matched"] += lang_stats["matched"]
        results["total_updated"] += lang_stats["updated"]
        results["total_not_found"] += lang_stats["not_found"]

    action = "preview" if request.dry_run else "written"
    logger.info(
        "[MERGE-TO-FOLDER] %s: %d files, matched=%d, updated=%d",
        action, results["files_processed"], results["total_matched"], results["total_updated"],
    )

    return results
