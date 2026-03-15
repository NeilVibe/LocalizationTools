"""Unit tests for CLI merge, gamedev-merge, export, detect commands."""
from __future__ import annotations

import base64
import json
import os
from unittest.mock import patch, MagicMock

import pytest

# We need to import the CLI module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
import locanext_cli


# ============================================================================
# cmd_merge
# ============================================================================

class TestCmdMerge:
    """Tests for cmd_merge command."""

    @patch("locanext_cli.requests.request")
    def test_cmd_merge_calls_correct_endpoint(self, mock_request):
        """cmd_merge calls POST /api/ldm/files/{target}/merge with correct body."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "matched": 10,
            "skipped": 2,
            "total": 12,
            "match_type_counts": {"strict": 8, "fuzzy": 2},
            "rows_updated": 10,
        }
        mock_request.return_value = mock_resp

        locanext_cli.cmd_merge(target_id=5, source_id=3, mode="cascade", threshold=0.85)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "post"  # method
        assert "/api/ldm/files/5/merge" in call_args[0][1]  # url
        body = call_args[1].get("json") or call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("json")
        assert body["source_file_id"] == 3
        assert body["match_mode"] == "cascade"
        assert body["threshold"] == 0.85

    @patch("locanext_cli.requests.request")
    def test_cmd_merge_with_cjk_flag(self, mock_request):
        """cmd_merge passes is_cjk flag correctly."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "matched": 5, "skipped": 0, "total": 5,
            "match_type_counts": {}, "rows_updated": 5,
        }
        mock_request.return_value = mock_resp

        locanext_cli.cmd_merge(target_id=1, source_id=2, mode="strict", threshold=0.9, is_cjk=True)

        body = mock_request.call_args[1].get("json")
        assert body["is_cjk"] is True
        assert body["match_mode"] == "strict"
        assert body["threshold"] == 0.9


# ============================================================================
# cmd_gamedev_merge
# ============================================================================

class TestCmdGamedevMerge:
    """Tests for cmd_gamedev_merge command."""

    @patch("locanext_cli.requests.request")
    def test_cmd_gamedev_merge_calls_endpoint(self, mock_request):
        """cmd_gamedev_merge calls POST /api/ldm/files/{id}/gamedev-merge."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_nodes": 50,
            "changed_nodes": 10,
            "added_nodes": 5,
            "removed_nodes": 2,
            "modified_attributes": 8,
            "rows_updated": 15,
            "output_xml": base64.b64encode(b"<root/>").decode(),
        }
        mock_request.return_value = mock_resp

        locanext_cli.cmd_gamedev_merge(file_id=5)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "post"
        assert "/api/ldm/files/5/gamedev-merge" in call_args[0][1]

    @patch("locanext_cli.requests.request")
    def test_cmd_gamedev_merge_saves_xml(self, mock_request, tmp_path):
        """When API returns base64 output_xml, writes decoded bytes to output file."""
        xml_content = b"<Root><Item Name='Sword'/></Root>"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_nodes": 1, "changed_nodes": 1, "added_nodes": 0,
            "removed_nodes": 0, "modified_attributes": 1, "rows_updated": 1,
            "output_xml": base64.b64encode(xml_content).decode(),
        }
        mock_request.return_value = mock_resp

        output_file = tmp_path / "merged.xml"
        locanext_cli.cmd_gamedev_merge(file_id=5, output_path=str(output_file))

        assert output_file.exists()
        assert output_file.read_bytes() == xml_content


# ============================================================================
# cmd_export
# ============================================================================

class TestCmdExport:
    """Tests for cmd_export command."""

    @patch("locanext_cli.requests.get")
    def test_cmd_export_calls_download(self, mock_get):
        """cmd_export calls GET /api/ldm/files/{id}/download."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b"<xml>data</xml>"
        mock_get.return_value = mock_resp

        locanext_cli.cmd_export(file_id=5, fmt="xml", output_path="/dev/null")

        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "/api/ldm/files/5/download" in call_url

    @patch("locanext_cli.requests.get")
    def test_cmd_export_saves_file(self, mock_get, tmp_path):
        """Response content is written to output file path."""
        file_content = b"col1\tcol2\nval1\tval2\n"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = file_content
        mock_get.return_value = mock_resp

        output_file = tmp_path / "export.txt"
        locanext_cli.cmd_export(file_id=5, fmt="txt", output_path=str(output_file))

        assert output_file.exists()
        assert output_file.read_bytes() == file_content

    @patch("locanext_cli.requests.get")
    def test_cmd_export_with_status_filter(self, mock_get, tmp_path):
        """cmd_export passes status_filter as query param."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b"data"
        mock_get.return_value = mock_resp

        output_file = tmp_path / "export.xml"
        locanext_cli.cmd_export(file_id=5, fmt="xml", output_path=str(output_file), status_filter="reviewed")

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params", {})
        assert params.get("status_filter") == "reviewed"


# ============================================================================
# cmd_detect
# ============================================================================

class TestCmdDetect:
    """Tests for cmd_detect command."""

    @patch("locanext_cli.requests.request")
    def test_cmd_detect_prints_file_type(self, mock_request, capsys):
        """cmd_detect calls GET /api/ldm/files/{id} and prints file_type."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 5,
            "name": "test_file.xml",
            "file_type": "gamedev",
        }
        mock_request.return_value = mock_resp

        locanext_cli.cmd_detect(file_id=5)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "get"
        assert "/api/ldm/files/5" in call_args[0][1]

        captured = capsys.readouterr()
        assert "gamedev" in captured.out

    @patch("locanext_cli.requests.request")
    def test_cmd_detect_defaults_to_translator(self, mock_request, capsys):
        """cmd_detect defaults to 'translator' when file_type is missing."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 5,
            "name": "old_file.xml",
        }
        mock_request.return_value = mock_resp

        locanext_cli.cmd_detect(file_id=5)

        captured = capsys.readouterr()
        assert "translator" in captured.out
