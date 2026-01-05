"""
Background Tasks Module

Celery-based background task processing.
"""

from server.tasks.celery_app import celery_app, CELERY_ENABLED
from server.tasks.background_tasks import (
    aggregate_daily_stats,
    cleanup_old_logs,
    send_daily_report,
    process_large_batch,
    purge_expired_trash
)

__all__ = [
    'celery_app',
    'CELERY_ENABLED',
    'aggregate_daily_stats',
    'cleanup_old_logs',
    'send_daily_report',
    'process_large_batch',
    'purge_expired_trash'
]
