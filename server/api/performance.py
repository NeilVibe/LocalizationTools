"""
Performance Summary API endpoint.

Exposes collected PerfTimer metrics as JSON with p50/p95/max/count/avg
per instrumented operation. No authentication required (dev/diagnostic).

Usage:
    GET /api/performance/summary -> {"operations": {"op_name": {"p50": ..., ...}}}
    POST /api/performance/reset -> {"status": "reset", "operations_cleared": N}
"""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from server.utils.perf_timer import get_metrics_summary, _metrics, _metrics_lock


router = APIRouter(prefix="/api/performance", tags=["Performance"])


class OperationStats(BaseModel):
    p50: float
    p95: float
    max: float
    count: int
    avg: float


class PerformanceSummaryResponse(BaseModel):
    operations: dict[str, OperationStats]


@router.get("/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary():
    """
    Return p50/p95/max/count/avg statistics for each instrumented operation.

    Reads from the in-memory ring buffer populated by PerfTimer context managers
    across all hot paths (embedding, FAISS, TM CRUD, merge, upload).
    """
    return get_metrics_summary()


@router.post("/reset")
async def reset_performance_metrics():
    """
    Clear all collected performance metrics.

    Useful during development to reset counters between test runs.
    """
    with _metrics_lock:
        count = len(_metrics)
        _metrics.clear()

    return {"status": "reset", "operations_cleared": count}
