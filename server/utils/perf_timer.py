"""
Performance Timer Utility for LocaNext.

Provides a context manager for measuring operation durations,
an in-memory ring buffer for metrics collection, and a summary
function for p50/p95/max/count/avg statistics.

Usage:
    from server.utils.perf_timer import PerfTimer, get_metrics_summary

    with PerfTimer("faiss_search", k=10) as t:
        results = index.search(query, k)
    # t.duration_ms is available after exit

    summary = get_metrics_summary()
    # {"operations": {"faiss_search": {"p50": ..., "p95": ..., ...}}}
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict

import numpy as np
from loguru import logger

# Thread-safe in-memory ring buffer: operation_name -> deque of records
_metrics: Dict[str, deque] = {}
_metrics_lock = threading.Lock()

# Max records per operation
_RING_BUFFER_SIZE = 1000


def record_metric(operation: str, duration_ms: float, **kwargs: Any) -> None:
    """
    Store a metric record in the in-memory ring buffer.

    Args:
        operation: Operation name (e.g., "faiss_search", "embedding_encode")
        duration_ms: Duration in milliseconds
        **kwargs: Additional fields to store (e.g., batch_size, file_size_bytes)
    """
    record = {
        "operation": operation,
        "duration_ms": duration_ms,
        "timestamp": time.time(),
        **kwargs,
    }

    with _metrics_lock:
        if operation not in _metrics:
            _metrics[operation] = deque(maxlen=_RING_BUFFER_SIZE)
        _metrics[operation].append(record)


def get_metrics_summary() -> dict:
    """
    Compute p50/p95/max/count/avg for each operation from the ring buffer.

    Returns:
        {"operations": {"faiss_search": {"p50": ..., "p95": ..., "max": ..., "count": ..., "avg": ...}, ...}}
    """
    with _metrics_lock:
        snapshot = {op: list(dq) for op, dq in _metrics.items()}

    operations = {}
    for op, records in snapshot.items():
        if not records:
            operations[op] = {"p50": 0.0, "p95": 0.0, "max": 0.0, "count": 0, "avg": 0.0}
            continue

        durations = np.array([r["duration_ms"] for r in records], dtype=np.float64)
        operations[op] = {
            "p50": float(np.percentile(durations, 50)),
            "p95": float(np.percentile(durations, 95)),
            "max": float(np.max(durations)),
            "count": len(records),
            "avg": float(np.mean(durations)),
        }

    return {"operations": operations}


def reset_metrics() -> int:
    """
    Clear all collected metrics from the ring buffer.

    Returns:
        Number of operation keys cleared.
    """
    with _metrics_lock:
        count = len(_metrics)
        _metrics.clear()
    return count


class PerfTimer:
    """
    Context manager for measuring operation duration.

    On exit, automatically records the metric and emits a structured log line.

    Usage:
        with PerfTimer("faiss_search", k=10, index_size=5000) as t:
            results = index.search(query, k)
        print(t.duration_ms)
    """

    def __init__(self, operation: str, **extra: Any):
        self.operation = operation
        self.extra = extra
        self.duration_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "PerfTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.perf_counter() - self._start
        self.duration_ms = elapsed * 1000.0

        # Record to ring buffer
        record_metric(self.operation, self.duration_ms, **self.extra)

        # Structured log line
        extra_str = " | ".join(f"{k}={v}" for k, v in self.extra.items())
        if extra_str:
            logger.info(
                "perf | op={} | duration_ms={:.1f} | {}",
                self.operation,
                self.duration_ms,
                extra_str,
            )
        else:
            logger.info(
                "perf | op={} | duration_ms={:.1f}",
                self.operation,
                self.duration_ms,
            )

        return None  # Don't suppress exceptions


def perf_timer(operation: str, **extra: Any) -> PerfTimer:
    """
    Convenience function to create a PerfTimer.

    Args:
        operation: Operation name
        **extra: Additional fields to log and record

    Returns:
        PerfTimer context manager

    Usage:
        with perf_timer("upload", file_size_bytes=1024):
            process_file(data)
    """
    return PerfTimer(operation, **extra)
