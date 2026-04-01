"""Data models for the PostgreSQL setup wizard."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class StepResult:
    """Result of a single setup step."""
    step: str
    status: Literal["done", "skipped", "failed"]
    duration_ms: int = 0
    message: str = ""
    error_code: str | None = None
    error_detail: str | None = None
    stderr: str | None = None


@dataclass
class SetupResult:
    """Result of the full setup run."""
    success: bool
    steps: list[StepResult] = field(default_factory=list)
    lan_ip: str | None = None
    failed_step: str | None = None
    error_code: str | None = None
    error_detail: str | None = None


@dataclass
class SetupConfig:
    """Configuration for setup steps."""
    pg_bin_dir: str | None = None
    data_dir: str | None = None
    pg_port: int = 5432
    pg_superuser: str = "postgres"
    service_user: str = "locanext_service"
    service_db: str = "localizationtools"
