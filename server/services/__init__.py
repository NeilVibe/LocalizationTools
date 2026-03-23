"""
Service Layer for LocaNext.

Services contain business logic extracted from thick API route files.
"""

from server.services.auth_service import AuthService
from server.services.db_stats_service import DbStatsService
from server.services.health_service import HealthService
from server.services.progress_service import ProgressService
from server.services.rankings_service import RankingsService
from server.services.remote_logging_service import RemoteLoggingService
from server.services.stats_service import StatsService
from server.services.sync_service import SyncService
from server.services.telemetry_service import TelemetryService
from server.services.transfer_adapter import TransferAdapter, init_quicktranslate

__all__ = [
    "AuthService",
    "DbStatsService",
    "HealthService",
    "ProgressService",
    "RankingsService",
    "RemoteLoggingService",
    "StatsService",
    "SyncService",
    "TelemetryService",
    "TransferAdapter",
    "init_quicktranslate",
]
