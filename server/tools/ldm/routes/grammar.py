"""
Grammar/spelling check routes for LDM.
Uses central LanguageTool server for spell/grammar checking.

P10: DB Abstraction Layer - Uses FileRepository and RowRepository for FULL PARITY.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional

from server.utils.languagetool import languagetool
from loguru import logger
from server.utils.dependencies import get_current_active_user_async
from server.repositories import FileRepository, RowRepository, get_file_repository, get_row_repository

router = APIRouter(tags=["ldm-grammar"])


class GrammarError(BaseModel):
    """Single grammar/spelling error."""
    row_id: int
    row_num: int
    text: str
    message: str
    short_message: Optional[str] = None
    offset: int
    length: int
    replacements: List[str]
    rule_id: str
    category: str


class GrammarCheckResponse(BaseModel):
    """Response for grammar check endpoint."""
    file_id: int
    language: str
    total_rows: int
    rows_checked: int
    rows_with_errors: int
    total_errors: int
    errors: List[GrammarError]
    server_available: bool


class GrammarStatusResponse(BaseModel):
    """Response for grammar status endpoint."""
    available: bool
    server_url: str


@router.get("/grammar/status", response_model=GrammarStatusResponse)
async def grammar_status(
    current_user: dict = Depends(get_current_active_user_async)
):
    """Check if LanguageTool server is available."""
    available = await languagetool.is_available()
    return GrammarStatusResponse(
        available=available,
        server_url=languagetool.base_url
    )


@router.post("/files/{file_id}/check-grammar", response_model=GrammarCheckResponse)
async def check_grammar(
    file_id: int,
    language: str = Query("en-US", description="Language code (en-US, de-DE, fr, es, etc.)"),
    file_repo: FileRepository = Depends(get_file_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check spelling/grammar for all target text in a file.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    Uses central LanguageTool server.

    Supported languages: en-US, en-GB, de-DE, fr, es, pt-BR, pt-PT, ru, pl, nl, it, uk, zh-CN, ja
    Note: Korean (ko) is NOT supported.
    """
    logger.debug(f"[GRAMMAR] check_grammar: file_id={file_id}, language={language}")

    # Check server availability
    if not await languagetool.is_available():
        raise HTTPException(
            status_code=503,
            detail="LanguageTool server is not available. Grammar check requires network connection to central server."
        )

    # Get file using repository
    file = await file_repo.get(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get rows using repository (no pagination for grammar check)
    rows = await row_repo.get_for_file(file_id, limit=10000)

    if not rows:
        return GrammarCheckResponse(
            file_id=file_id,
            language=language,
            total_rows=0,
            rows_checked=0,
            rows_with_errors=0,
            total_errors=0,
            errors=[],
            server_available=True
        )

    logger.info(f"[GRAMMAR] check_grammar: file_id={file_id}, language={language}, rows={len(rows)}")

    errors = []
    rows_with_errors = set()
    rows_checked = 0

    for row in rows:
        target_text = row.get("target", "")
        if not target_text or not target_text.strip():
            continue

        rows_checked += 1
        result = await languagetool.check(target_text, language)

        for match in result.get("matches", []):
            rule = match.get("rule", {})
            errors.append(GrammarError(
                row_id=row["id"],
                row_num=row.get("row_num", 0),
                text=target_text,
                message=match.get("message", ""),
                short_message=match.get("shortMessage"),
                offset=match.get("offset", 0),
                length=match.get("length", 0),
                replacements=[r.get("value", "") for r in match.get("replacements", [])[:5]],
                rule_id=rule.get("id", "UNKNOWN"),
                category=rule.get("category", {}).get("name", "Unknown")
            ))
            rows_with_errors.add(row["id"])

    logger.info(f"[GRAMMAR] check_grammar complete: file_id={file_id}, errors={len(errors)}, rows_with_errors={len(rows_with_errors)}")

    return GrammarCheckResponse(
        file_id=file_id,
        language=language,
        total_rows=len(rows),
        rows_checked=rows_checked,
        rows_with_errors=len(rows_with_errors),
        total_errors=len(errors),
        errors=errors,
        server_available=True
    )


@router.post("/rows/{row_id}/check-grammar")
async def check_row_grammar(
    row_id: int,
    language: str = Query("en-US", description="Language code"),
    row_repo: RowRepository = Depends(get_row_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check spelling/grammar for a single row's target text.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    """
    logger.debug(f"[GRAMMAR] check_row_grammar: row_id={row_id}, language={language}")

    if not await languagetool.is_available():
        raise HTTPException(
            status_code=503,
            detail="LanguageTool server is not available"
        )

    # Get row using repository
    row = await row_repo.get(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    target_text = row.get("target", "")
    if not target_text or not target_text.strip():
        return {"row_id": row_id, "matches": [], "checked": False}

    result = await languagetool.check(target_text, language)

    matches = []
    for match in result.get("matches", []):
        rule = match.get("rule", {})
        matches.append({
            "message": match.get("message", ""),
            "short_message": match.get("shortMessage"),
            "offset": match.get("offset", 0),
            "length": match.get("length", 0),
            "replacements": [r.get("value", "") for r in match.get("replacements", [])[:5]],
            "rule_id": rule.get("id", "UNKNOWN"),
            "category": rule.get("category", {}).get("name", "Unknown")
        })

    logger.debug(f"[GRAMMAR] check_row_grammar complete: row_id={row_id}, matches={len(matches)}")

    return {
        "row_id": row_id,
        "text": target_text,
        "language": language,
        "matches": matches,
        "checked": True
    }
