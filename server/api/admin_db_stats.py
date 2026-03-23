"""
Admin Database Statistics API

Thin route handlers delegating to DbStatsService.
Provides database performance metrics for monitoring:
- Connection count and pool status
- Query performance stats
- Table sizes and row counts
- PostgreSQL configuration status
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from loguru import logger

from server.utils.dependencies import get_db, require_admin
from server.services.db_stats_service import DbStatsService

router = APIRouter(prefix="/api/v2/admin/db", tags=["Admin Database"])


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_db_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get database performance statistics.

    Returns connection pool status, query stats, and configuration.
    Requires admin authentication.
    """
    service = DbStatsService(db)
    return service.get_stats()


@router.get("/health", dependencies=[Depends(require_admin)])
async def get_db_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Quick database health check with performance assessment.

    Returns:
    - status: healthy/warning/critical
    - issues: List of detected issues
    - recommendations: Suggested fixes
    """
    service = DbStatsService(db)
    return service.get_health()
