from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path


def save_config(path: Path, config: dict) -> None:
    """Save config JSON with restrictive OS permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    if sys.platform == "win32":
        try:
            subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.getlogin()}:F"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
    else:
        try:
            os.chmod(str(path), 0o600)
        except OSError:
            pass


def load_config(path: Path) -> dict:
    """Load config from JSON. Returns {} if missing/invalid."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}
