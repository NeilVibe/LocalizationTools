"""
TM Maintenance Module.

EMB-003: Login-time stale index check and background sync.
"""

from .manager import TMMaintenanceManager
from .schemas import StaleTMInfo, MaintenanceResult

__all__ = ["TMMaintenanceManager", "StaleTMInfo", "MaintenanceResult"]
