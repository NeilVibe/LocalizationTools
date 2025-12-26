"""
Grammar/spelling check routes for LDM.
Uses central LanguageTool server for spell/grammar checking.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.languagetool import languagetool
from loguru import logger
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMRow, LDMFile

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check spelling/grammar for all target text in a file.
    Uses central LanguageTool server.

    Supported languages: en-US, en-GB, de-DE, fr, es, pt-BR, pt-PT, ru, pl, nl, it, uk, zh-CN, ja
    Note: Korean (ko) is NOT supported.
    """
    # Check server availability
    if not await languagetool.is_available():
        raise HTTPException(
            status_code=503,
            detail="LanguageTool server is not available. Grammar check requires network connection to central server."
        )

    # Get file info
    from sqlalchemy import select
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get file rows
    result = await db.execute(
        select(LDMRow)
        .where(LDMRow.file_id == file_id)
        .order_by(LDMRow.row_num)
    )
    rows = result.scalars().all()

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

    logger.info(f"LDM GRAMMAR CHECK: file_id={file_id}, language={language}, rows={len(rows)}")

    errors = []
    rows_with_errors = set()
    rows_checked = 0

    for row in rows:
        target_text = row.target
        if not target_text or not target_text.strip():
            continue

        rows_checked += 1
        result = await languagetool.check(target_text, language)

        for match in result.get("matches", []):
            rule = match.get("rule", {})
            errors.append(GrammarError(
                row_id=row.id,
                row_num=row.row_num,
                text=target_text,
                message=match.get("message", ""),
                short_message=match.get("shortMessage"),
                offset=match.get("offset", 0),
                length=match.get("length", 0),
                replacements=[r.get("value", "") for r in match.get("replacements", [])[:5]],
                rule_id=rule.get("id", "UNKNOWN"),
                category=rule.get("category", {}).get("name", "Unknown")
            ))
            rows_with_errors.add(row.id)

    logger.info(f"LDM GRAMMAR CHECK complete: {len(errors)} errors in {len(rows_with_errors)} rows")

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check spelling/grammar for a single row's target text.
    """
    if not await languagetool.is_available():
        raise HTTPException(
            status_code=503,
            detail="LanguageTool server is not available"
        )

    from sqlalchemy import select
    result = await db.execute(select(LDMRow).where(LDMRow.id == row_id))
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if not row.target or not row.target.strip():
        return {"row_id": row_id, "matches": [], "checked": False}

    result = await languagetool.check(row.target, language)

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

    return {
        "row_id": row_id,
        "text": row.target,
        "language": language,
        "matches": matches,
        "checked": True
    }
