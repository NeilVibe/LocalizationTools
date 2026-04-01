"""Tests for server.setup.credential_store — config save/load with OS permissions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from server.setup.credential_store import load_config, save_config


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "subdir" / "config.json"


class TestSaveLoadRoundtrip:
    """save_config + load_config must roundtrip correctly."""

    def test_roundtrip(self, config_path: Path):
        data = {"host": "192.168.1.10", "port": 5432, "nested": {"key": "value"}}
        save_config(config_path, data)
        loaded = load_config(config_path)
        assert loaded == data

    def test_creates_parent_dirs(self, config_path: Path):
        assert not config_path.parent.exists()
        save_config(config_path, {"a": 1})
        assert config_path.exists()

    def test_file_is_valid_json(self, config_path: Path):
        save_config(config_path, {"x": [1, 2, 3]})
        raw = config_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed == {"x": [1, 2, 3]}

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions only")
    def test_restrictive_permissions(self, config_path: Path):
        save_config(config_path, {"secret": "pw"})
        mode = config_path.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"


class TestLoadConfig:
    """load_config edge cases."""

    def test_missing_file_returns_empty_dict(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.json"
        assert load_config(missing) == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json {{{", encoding="utf-8")
        assert load_config(bad) == {}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path):
        empty = tmp_path / "empty.json"
        empty.write_text("", encoding="utf-8")
        assert load_config(empty) == {}
