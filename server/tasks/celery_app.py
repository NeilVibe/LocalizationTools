"""
Celery Application Configuration

Background task processing with Celery.
"""

import os
from celery import Celery
from loguru import logger

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "False").lower() == "true"

# Create Celery app
celery_app = Celery(
    "localizationtools",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['server.tasks.background_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

logger.info(f"Celery configured with broker: {CELERY_BROKER_URL}")

__all__ = ['celery_app', 'CELERY_ENABLED']
