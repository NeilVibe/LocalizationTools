"""
Performance Summary API endpoint.

Exposes collected PerfTimer metrics as JSON with p50/p95/max/count/avg
per instrumented operation. Requires admin authentication.

Usage:
    GET /api/performance/summary -> {"operations": {"op_name": {"p50": ..., ...}}}
    POST /api/performance/reset -> {"status": "reset", "operations_cleared": N}
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from server.utils.dependencies import require_admin_async
from server.utils.perf_timer import get_metrics_summary, reset_metrics


router = APIRouter(prefix="/api/performance", tags=["Performance"])


class OperationStats(BaseModel):
    p50: float = Field(ge=0)
    p95: float = Field(ge=0)
    max: float = Field(ge=0)
    count: int = Field(ge=0)
    avg: float = Field(ge=0)


class PerformanceSummaryResponse(BaseModel):
    operations: dict[str, OperationStats]


class PerformanceResetResponse(BaseModel):
    status: Literal["reset"]
    operations_cleared: int = Field(ge=0)


@router.get("/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    _admin: dict = Depends(require_admin_async),
):
    """
    Return p50/p95/max/count/avg statistics for each instrumented operation.

    Reads from the in-memory ring buffer populated by PerfTimer context managers
    across all hot paths (embedding, FAISS, TM CRUD, merge, upload).
    """
    return get_metrics_summary()


@router.post("/reset", response_model=PerformanceResetResponse)
async def reset_performance_metrics(
    _admin: dict = Depends(require_admin_async),
):
    """
    Clear all collected performance metrics.

    Useful during development to reset counters between test runs.
    """
    count = reset_metrics()
    return {"status": "reset", "operations_cleared": count}
