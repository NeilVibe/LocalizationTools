"""
Project Settings API -- Phase 56, Plan 02

Provides path validation for LOC PATH and EXPORT PATH settings.
Validates that paths exist, are directories, and contain languagedata files.
Includes WSL path translation for DEV_MODE (Windows paths -> /mnt/ paths).
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from server import config

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================================================
# Models
# ============================================================================

class PathValidationRequest(BaseModel):
    """Request body for path validation."""
    path: str


class PathValidationResponse(BaseModel):
    """Response from path validation."""
    valid: bool
    error: str | None = None
    hint: str | None = None
    files_found: int = 0
    file_types: list[str] = []


# ============================================================================
# Helpers
# ============================================================================

# Pattern: drive letter like C:\, D:\, E:\, F:\ (case-insensitive)
_DRIVE_LETTER_RE = re.compile(r"^([A-Za-z]):[\\\/]")


def translate_wsl_path(path_str: str) -> str:
    """Translate Windows drive-letter paths to WSL /mnt/ paths in DEV_MODE.

    Examples:
        C:\\Users\\MYCOM\\test -> /mnt/c/Users/MYCOM/test
        D:\\LOC\\project      -> /mnt/d/LOC/project
        /mnt/c/already/linux  -> /mnt/c/already/linux (unchanged)
    """
    if not config.DEV_MODE:
        return path_str

    match = _DRIVE_LETTER_RE.match(path_str)
    if match:
        drive = match.group(1).lower()
        rest = path_str[3:].replace("\\", "/")
        translated = f"/mnt/{drive}/{rest}"
        logger.debug(f"WSL path translation: {path_str} -> {translated}")
        return translated

    return path_str


def validate_path_logic(path_str: str) -> PathValidationResponse:
    """Core validation logic (testable without HTTP).

    Checks:
    1. Path exists
    2. Path is a directory
    3. Directory contains languagedata_*.* files
    """
    p = Path(path_str)

    if not p.exists():
        return PathValidationResponse(valid=False, error="Path does not exist")

    if not p.is_dir():
        return PathValidationResponse(valid=False, error="Path is not a directory")

    # Glob for languagedata_*.* (any extension: .xml, .txt, .xlsx)
    files = sorted(p.glob("languagedata_*.*"))

    if not files:
        return PathValidationResponse(
            valid=False,
            error="No languagedata files found",
            hint="Expected files like languagedata_fre.xml or languagedata_fr.txt",
        )

    return PathValidationResponse(
        valid=True,
        files_found=len(files),
        file_types=[f.name for f in files],
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/validate-path", response_model=PathValidationResponse)
async def validate_path(body: PathValidationRequest):
    """Validate a filesystem path for languagedata files.

    Translates Windows drive-letter paths to WSL paths in DEV_MODE.
    Checks existence, is_dir, and presence of languagedata_*.* files.
    """
    translated = translate_wsl_path(body.path)
    logger.info(f"Validating path: {translated}")
    result = validate_path_logic(translated)
    if not result.valid:
        logger.warning(f"Path validation failed: {result.error} ({translated})")
    else:
        logger.info(f"Path valid: {result.files_found} files found in {translated}")
    return result
