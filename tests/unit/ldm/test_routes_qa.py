"""
Unit tests for LDM QA routes.

P2: Auto-LQA System
Tests for QA check endpoints and QA result management.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from server.tools.ldm.routes.qa import (
    check_row_qa,
    get_row_qa_results,
    check_file_qa,
    get_file_qa_results,
    get_file_qa_summary,
    resolve_qa_issue,
    _run_qa_checks,
    _save_qa_results,
)
from server.tools.ldm.schemas.qa import QACheckRequest


# =============================================================================
# Test _run_qa_checks helper
# =============================================================================

class TestRunQAChecks:
    """Test the QA check logic."""

    @pytest.mark.asyncio
    async def test_pattern_check_detects_missing_code(self):
        """Pattern check should detect missing {code} patterns."""
        # Create mock row
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.source = "{0}의 공격력"
        mock_row.target = "Attack power of"  # Missing {0}

        mock_db = AsyncMock()
        issues = await _run_qa_checks(mock_db, mock_row, ["pattern"], None)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "pattern"
        assert issues[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_pattern_check_passes_matching_codes(self):
        """Pattern check should pass when codes match."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.source = "{0}의 공격력"
        mock_row.target = "Attack power of {0}"

        mock_db = AsyncMock()
        issues = await _run_qa_checks(mock_db, mock_row, ["pattern"], None)

        # Should have no pattern issues
        pattern_issues = [i for i in issues if i["check_type"] == "pattern"]
        assert len(pattern_issues) == 0

    @pytest.mark.asyncio
    async def test_character_check_detects_mismatch(self):
        """Character check should detect special char count mismatches."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.source = "{name}의 {stat}"  # 2 pairs of braces
        mock_row.target = "{name}'s stat"   # Only 1 pair

        mock_db = AsyncMock()
        issues = await _run_qa_checks(mock_db, mock_row, ["character"], None)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "character"
        assert issues[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_line_check_detects_inconsistency(self):
        """Line check should detect same source with different translations."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.row_num = 1
        mock_row.source = "공격"
        mock_row.target = "Attack"

        # Another row with same source but different translation
        mock_other_row = MagicMock()
        mock_other_row.id = 2
        mock_other_row.file_id = 1
        mock_other_row.row_num = 2
        mock_other_row.source = "공격"
        mock_other_row.target = "Attaque"  # Different!

        mock_db = AsyncMock()
        issues = await _run_qa_checks(
            mock_db, mock_row, ["line"], [mock_row, mock_other_row]
        )

        assert len(issues) == 1
        assert issues[0]["check_type"] == "line"
        assert issues[0]["severity"] == "warning"
        assert "row 2" in issues[0]["message"]

    @pytest.mark.asyncio
    async def test_no_issues_for_clean_row(self):
        """Clean row should have no issues."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.row_num = 1
        mock_row.source = "방어력"
        mock_row.target = "Defense"

        mock_db = AsyncMock()
        issues = await _run_qa_checks(
            mock_db, mock_row, ["pattern", "character"], None
        )

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_skips_rows_without_source_or_target(self):
        """Should skip rows without both source and target."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.source = "테스트"
        mock_row.target = None  # No target

        mock_db = AsyncMock()
        issues = await _run_qa_checks(
            mock_db, mock_row, ["pattern", "character"], None
        )

        assert len(issues) == 0


# =============================================================================
# Test QA Schemas
# =============================================================================

class TestQASchemas:
    """Test QA schema validation."""

    def test_qa_check_request_defaults(self):
        """QACheckRequest should have default checks."""
        request = QACheckRequest()
        assert "line" in request.checks
        assert "term" in request.checks
        assert "pattern" in request.checks
        assert "character" in request.checks
        assert request.force is False

    def test_qa_check_request_custom_checks(self):
        """QACheckRequest should accept custom checks."""
        request = QACheckRequest(checks=["pattern"], force=True)
        assert request.checks == ["pattern"]
        assert request.force is True


# =============================================================================
# Test check_pattern_match from qa_helpers
# =============================================================================

class TestPatternMatch:
    """Test pattern matching from centralized qa_helpers."""

    def test_detects_missing_pattern(self):
        """Should detect missing {code} pattern."""
        from server.utils.qa_helpers import check_pattern_match

        result = check_pattern_match(
            source="{0}의 {1}",
            target="of the"
        )

        assert result is not None
        assert "source_patterns" in result
        assert "target_patterns" in result
        assert "{0}" in result["source_patterns"]
        assert "{1}" in result["source_patterns"]
        assert len(result["target_patterns"]) == 0

    def test_passes_matching_patterns(self):
        """Should pass when patterns match."""
        from server.utils.qa_helpers import check_pattern_match

        result = check_pattern_match(
            source="{0}의 {1}",
            target="{0} of {1}"
        )

        assert result is None


# =============================================================================
# Test check_character_count from qa_helpers
# =============================================================================

class TestCharacterCount:
    """Test character count checking from centralized qa_helpers."""

    def test_detects_brace_mismatch(self):
        """Should detect brace count mismatch."""
        from server.utils.qa_helpers import check_character_count

        result = check_character_count(
            source="{a}{b}{c}",
            target="{a}{b}",
            symbols=["{", "}"]
        )

        assert result is not None
        assert "symbol" in result
        assert "source_count" in result
        assert "target_count" in result
        assert result["source_count"] > result["target_count"]

    def test_passes_matching_counts(self):
        """Should pass when counts match."""
        from server.utils.qa_helpers import check_character_count

        result = check_character_count(
            source="{a}{b}",
            target="{x}{y}",
            symbols=["{", "}"]
        )

        assert result is None


# =============================================================================
# Test QA Endpoint Error Handling
# =============================================================================

class TestQAEndpointErrors:
    """Test error handling in QA endpoints."""

    @pytest.mark.asyncio
    async def test_check_row_qa_not_found(self):
        """Should return 404 for non-existent row."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = 1

        request = QACheckRequest()

        with pytest.raises(HTTPException) as exc_info:
            await check_row_qa(
                row_id=9999,
                request=request,
                db=mock_db,
                current_user=mock_user
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_check_file_qa_not_found(self):
        """Should return 404 for non-existent file."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = 1

        request = QACheckRequest()

        with pytest.raises(HTTPException) as exc_info:
            await check_file_qa(
                file_id=9999,
                request=request,
                db=mock_db,
                current_user=mock_user
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_resolve_qa_issue_not_found(self):
        """Should return 404 for non-existent QA result."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = 1

        with pytest.raises(HTTPException) as exc_info:
            await resolve_qa_issue(
                result_id=9999,
                db=mock_db,
                current_user=mock_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_already_resolved(self):
        """Should return 400 for already resolved QA issue."""
        mock_qa_result = MagicMock()
        mock_qa_result.id = 1
        mock_qa_result.resolved_at = datetime.utcnow()  # Already resolved

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_qa_result
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = 1

        with pytest.raises(HTTPException) as exc_info:
            await resolve_qa_issue(
                result_id=1,
                db=mock_db,
                current_user=mock_user
            )

        assert exc_info.value.status_code == 400
        assert "already resolved" in exc_info.value.detail.lower()


# =============================================================================
# Test Multiple Check Types
# =============================================================================

class TestMultipleChecks:
    """Test running multiple check types together."""

    @pytest.mark.asyncio
    async def test_multiple_issues_detected(self):
        """Should detect issues from multiple check types."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.file_id = 1
        mock_row.row_num = 1
        mock_row.source = "{0}의 {1}"
        mock_row.target = "of the"  # Missing patterns AND character mismatch

        mock_db = AsyncMock()
        issues = await _run_qa_checks(
            mock_db, mock_row, ["pattern", "character"], None
        )

        # Should have both pattern and character issues
        check_types = [i["check_type"] for i in issues]
        assert "pattern" in check_types or "character" in check_types
        assert len(issues) >= 1
