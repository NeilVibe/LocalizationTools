"""Hardware detection for PostgreSQL performance tuning.

Uses psutil to detect RAM, CPU cores, and storage type.
All detection is local-only, no network calls.
"""
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger


@dataclass
class HardwareInfo:
    """Detected hardware specifications."""
    ram_gb: int           # Total RAM in GB (rounded down)
    physical_cores: int   # Physical CPU cores (not hyperthreaded)
    logical_cores: int    # Logical CPU cores (with hyperthreading)
    is_ssd: bool          # Best-effort SSD detection
    os_name: str          # 'nt' or 'posix'


def detect_hardware(data_dir: str = "") -> HardwareInfo:
    """Detect hardware specs using psutil.

    Falls back to conservative defaults if detection fails.
    SSD detection uses heuristic: Windows WMI query or assume SSD
    for modern systems (conservative default: True).
    """
    import os
    import psutil

    # RAM
    try:
        ram_bytes = psutil.virtual_memory().total
        ram_gb = int(ram_bytes / (1024 ** 3))
    except Exception as e:
        logger.warning("RAM detection failed, defaulting to 8GB: {}", e)
        ram_gb = 8

    # CPU cores
    try:
        physical_cores = psutil.cpu_count(logical=False) or 4
        logical_cores = psutil.cpu_count(logical=True) or physical_cores
    except Exception as e:
        logger.warning("CPU detection failed, defaulting to 4 cores: {}", e)
        physical_cores = 4
        logical_cores = 4

    # SSD detection (best-effort)
    is_ssd = True  # Default: assume SSD (modern systems)
    if os.name == "nt" and data_dir:
        try:
            import subprocess
            # Use PowerShell to query disk type
            drive_letter = os.path.splitdrive(data_dir)[0]
            if drive_letter:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f"(Get-PhysicalDisk | Where-Object {{ $_.DeviceId -eq "
                     f"(Get-Partition -DriveLetter '{drive_letter[0]}').DiskNumber }}).MediaType"],
                    capture_output=True, text=True, timeout=5,
                )
                if "HDD" in result.stdout:
                    is_ssd = False
                    logger.info("Detected HDD storage")
                else:
                    logger.info("Detected SSD storage")
        except Exception:
            logger.debug("SSD detection failed, assuming SSD")

    info = HardwareInfo(
        ram_gb=ram_gb,
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        is_ssd=is_ssd,
        os_name=os.name,
    )
    logger.info(
        "Hardware detected: {}GB RAM, {} physical / {} logical cores, SSD={}",
        info.ram_gb, info.physical_cores, info.logical_cores, info.is_ssd,
    )
    return info
