"""
Unit tests for LDM QA routes.

P2: Auto-LQA System
P10: Updated to use Repository Pattern mocking.
Tests for QA check endpoints and QA result management.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from server.tools.ldm.routes.qa import (
    _run_qa_checks,
    _build_line_check_index,
    _build_term_automaton,
    _apply_noise_filter,
    MAX_ISSUES_PER_TERM,
)
from server.tools.ldm.schemas.qa import QACheckRequest
from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import (
    get_qa_repository,
    get_row_repository,
    get_tm_repository,
    get_file_repository,
)

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


# =============================================================================
# Helper function to create row dicts (P10: Repository returns dicts)
# =============================================================================

def make_row_dict(id=1, file_id=1, row_num=1, source="", target="", **kwargs):
    """Create a row dict matching Repository Pattern output."""
    return {
        "id": id,
        "file_id": file_id,
        "row_num": row_num,
        "source": source,
        "target": target,
        "status": kwargs.get("status", "pending"),
        "string_id": kwargs.get("string_id"),
        "created_at": datetime(2025, 1, 1).isoformat(),
        "updated_at": datetime(2025, 1, 1).isoformat(),
    }


# =============================================================================
# Test _run_qa_checks helper
# P10: Now takes row dict instead of (db, LDMRow)
# =============================================================================

class TestRunQAChecks:
    """Test the QA check logic."""

    @pytest.mark.asyncio
    async def test_pattern_check_detects_missing_code(self):
        """Pattern check should detect missing {code} patterns."""
        # P10: Row is now a dict
        row = make_row_dict(
            source="{0}의 공격력",
            target="Attack power of"  # Missing {0}
        )

        issues = await _run_qa_checks(row, ["pattern"], None, None)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "pattern"
        assert issues[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_pattern_check_passes_matching_codes(self):
        """Pattern check should pass when codes match."""
        row = make_row_dict(
            source="{0}의 공격력",
            target="Attack power of {0}"
        )

        issues = await _run_qa_checks(row, ["pattern"], None, None)

        # Should have no pattern issues
        pattern_issues = [i for i in issues if i["check_type"] == "pattern"]
        assert len(pattern_issues) == 0

    @pytest.mark.asyncio
    async def test_line_check_detects_inconsistency(self):
        """Line check should detect same source with different translations."""
        row = make_row_dict(
            id=1, row_num=1,
            source="공격",
            target="Attack"
        )

        # Another row with same source but different translation
        other_row = make_row_dict(
            id=2, row_num=2,
            source="공격",
            target="Attaque"  # Different!
        )

        issues = await _run_qa_checks(row, ["line"], [row, other_row], None)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "line"
        assert issues[0]["severity"] == "warning"
        assert "row 2" in issues[0]["message"]

    @pytest.mark.asyncio
    async def test_term_check_detects_missing_term(self):
        """Term check should detect missing glossary terms."""
        row = make_row_dict(
            source="공격 증가",  # Contains isolated glossary term "공격"
            target="Increase power"  # Missing "Attack"
        )

        glossary_terms = [("공격", "Attack"), ("방어", "Defense")]

        issues = await _run_qa_checks(row, ["term"], None, glossary_terms)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "term"
        assert issues[0]["severity"] == "warning"
        assert "Attack" in issues[0]["message"]

    @pytest.mark.asyncio
    async def test_term_check_passes_when_term_present(self):
        """Term check should pass when glossary term is in translation."""
        row = make_row_dict(
            source="공격 증가",  # Contains isolated glossary term "공격"
            target="Attack increase"  # Contains "Attack"
        )

        glossary_terms = [("공격", "Attack")]

        issues = await _run_qa_checks(row, ["term"], None, glossary_terms)

        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) == 0

    @pytest.mark.asyncio
    async def test_no_issues_for_clean_row(self):
        """Clean row should have no issues."""
        row = make_row_dict(
            source="방어력",
            target="Defense"
        )

        issues = await _run_qa_checks(row, ["pattern"], None, None)

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_skips_rows_without_source_or_target(self):
        """Should skip rows without both source and target."""
        row = make_row_dict(
            source="테스트",
            target=None  # No target
        )

        issues = await _run_qa_checks(row, ["pattern"], None, None)

        assert len(issues) == 0


# =============================================================================
# Test Enhanced Line Check (051-02: Group-based inconsistency detection)
# =============================================================================

class TestEnhancedLineCheck:
    """Test group-based Line Check that reports ALL inconsistencies."""

    @pytest.mark.asyncio
    async def test_line_check_reports_all_inconsistencies(self):
        """Line Check with 3 rows: same source, 2 different translations -> flags both."""
        row1 = make_row_dict(id=1, row_num=1, source="공격", target="Attack")
        row2 = make_row_dict(id=2, row_num=2, source="공격", target="Attaque")
        row3 = make_row_dict(id=3, row_num=3, source="공격", target="Attack")
        all_rows = [row1, row2, row3]

        # Check row1 - should see row2 as inconsistent
        issues = await _run_qa_checks(row1, ["line"], all_rows, None)
        assert len(issues) >= 1
        assert all(i["check_type"] == "line" for i in issues)
        # Should report row2's different translation
        other_row_nums = [i["details"]["other_row_num"] for i in issues]
        assert 2 in other_row_nums

    @pytest.mark.asyncio
    async def test_line_check_identical_pairs_no_issues(self):
        """Line Check with identical source+target pairs -> no issues."""
        row1 = make_row_dict(id=1, row_num=1, source="공격", target="Attack")
        row2 = make_row_dict(id=2, row_num=2, source="공격", target="Attack")
        all_rows = [row1, row2]

        issues = await _run_qa_checks(row1, ["line"], all_rows, None)
        line_issues = [i for i in issues if i["check_type"] == "line"]
        assert len(line_issues) == 0

    @pytest.mark.asyncio
    async def test_line_check_empty_rows_skipped(self):
        """Line Check with empty source or target -> skipped gracefully."""
        row1 = make_row_dict(id=1, row_num=1, source="공격", target="Attack")
        empty_row = make_row_dict(id=2, row_num=2, source="공격", target="")
        no_source = make_row_dict(id=3, row_num=3, source="", target="Attack")
        all_rows = [row1, empty_row, no_source]

        issues = await _run_qa_checks(row1, ["line"], all_rows, None)
        line_issues = [i for i in issues if i["check_type"] == "line"]
        assert len(line_issues) == 0

    @pytest.mark.asyncio
    async def test_line_check_details_include_other_info(self):
        """Line Check results include other_row_num and other_target in details."""
        row1 = make_row_dict(id=1, row_num=1, source="공격", target="Attack")
        row2 = make_row_dict(id=2, row_num=5, source="공격", target="Attaque")
        all_rows = [row1, row2]

        issues = await _run_qa_checks(row1, ["line"], all_rows, None)
        assert len(issues) == 1
        details = issues[0]["details"]
        assert "other_row_num" in details
        assert details["other_row_num"] == 5
        assert "other_target" in details
        assert details["other_target"] == "Attaque"

    def test_build_line_check_index(self):
        """_build_line_check_index creates correct grouping."""
        rows = [
            make_row_dict(id=1, row_num=1, source="공격", target="Attack"),
            make_row_dict(id=2, row_num=2, source="공격", target="Attaque"),
            make_row_dict(id=3, row_num=3, source="방어", target="Defense"),
        ]
        index = _build_line_check_index(rows)
        assert "공격" in index
        assert len(index["공격"]) == 2
        assert "방어" in index
        assert len(index["방어"]) == 1


# =============================================================================
# Test QA Schemas
# =============================================================================

class TestQASchemas:
    """Test QA schema validation."""

    def test_qa_check_request_defaults(self):
        """QACheckRequest should have default checks."""
        request = QACheckRequest()
        assert "line" in request.checks
        assert "pattern" in request.checks
        assert "term" in request.checks
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
# Test QA Endpoint Error Handling (P10: Using Repository mocks)
# =============================================================================

class TestQAEndpointErrors:
    """Test error handling in QA endpoints using Repository Pattern."""

    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories."""
        qa_repo = MagicMock()
        qa_repo.get_for_row = AsyncMock(return_value=[])
        qa_repo.get_for_file = AsyncMock(return_value=[])
        qa_repo.get = AsyncMock(return_value=None)
        qa_repo.create_bulk = AsyncMock(return_value=[])
        qa_repo.resolve = AsyncMock(return_value=None)

        row_repo = MagicMock()
        row_repo.get = AsyncMock(return_value=None)
        row_repo.get_with_file = AsyncMock(return_value=None)
        row_repo.get_all_for_file = AsyncMock(return_value=[])

        file_repo = MagicMock()
        file_repo.get = AsyncMock(return_value=None)

        tm_repo = MagicMock()
        tm_repo.get_active_for_file = AsyncMock(return_value=[])
        tm_repo.get_glossary_terms = AsyncMock(return_value=[])

        return {
            "qa_repo": qa_repo,
            "row_repo": row_repo,
            "file_repo": file_repo,
            "tm_repo": tm_repo,
        }

    @pytest.fixture
    def client_with_qa_repos(self, mock_repos):
        """TestClient with mocked QA repositories."""
        mock_user = {
            "user_id": 1,
            "username": "testuser",
            "role": "user",
            "is_active": True,
        }

        async def override_get_user():
            return mock_user

        fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
        fastapi_app.dependency_overrides[get_qa_repository] = lambda: mock_repos["qa_repo"]
        fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_repos["row_repo"]
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repos["tm_repo"]
        fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_repos["file_repo"]

        client = TestClient(wrapped_app)
        yield client, mock_repos

        fastapi_app.dependency_overrides.clear()

    def test_check_row_qa_not_found(self, client_with_qa_repos):
        """Should return 404 for non-existent row."""
        client, repos = client_with_qa_repos
        repos["row_repo"].get_with_file.return_value = None

        response = client.post("/api/ldm/rows/9999/check-qa", json={"checks": ["pattern"]})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_check_file_qa_not_found(self, client_with_qa_repos):
        """Should return 404 for non-existent file."""
        client, repos = client_with_qa_repos
        repos["file_repo"].get.return_value = None

        response = client.post("/api/ldm/files/9999/check-qa", json={"checks": ["pattern"]})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_resolve_qa_issue_not_found(self, client_with_qa_repos):
        """Should return 404 for non-existent QA result."""
        client, repos = client_with_qa_repos
        repos["qa_repo"].get.return_value = None

        response = client.post("/api/ldm/qa-results/9999/resolve")
        assert response.status_code == 404

    def test_resolve_already_resolved(self, client_with_qa_repos):
        """Should return 400 for already resolved QA issue."""
        client, repos = client_with_qa_repos
        # QA result that's already resolved
        repos["qa_repo"].get.return_value = {
            "id": 1,
            "row_id": 1,
            "check_type": "pattern",
            "severity": "error",
            "message": "Test",
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": 1,
        }

        response = client.post("/api/ldm/qa-results/1/resolve")
        assert response.status_code == 400
        assert "already resolved" in response.json()["detail"].lower()


# =============================================================================
# Test Enhanced Term Check (051-02: Service-level automaton + noise filter)
# =============================================================================

class TestEnhancedTermCheck:
    """Test Term Check with pre-built automaton and noise filter."""

    @pytest.mark.asyncio
    async def test_term_check_finds_missing_glossary_term(self):
        """Term Check finds 'Iron Sword' in source, flags when translation missing."""
        row = make_row_dict(
            source="Iron Sword is powerful",
            target="C'est puissant"  # Missing "Iron Sword" equivalent
        )
        glossary = [("Iron Sword", "Epee de fer")]

        issues = await _run_qa_checks(row, ["term"], None, glossary)
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) >= 1
        assert "Epee de fer" in term_issues[0]["message"]

    @pytest.mark.asyncio
    async def test_term_check_isolation_prevents_partial_match(self):
        """Term Check with is_isolated prevents 'Iron' matching inside 'Ironclad'."""
        row = make_row_dict(
            source="Ironclad defense",
            target="Defense incassable"
        )
        glossary = [("Iron", "Fer")]

        issues = await _run_qa_checks(row, ["term"], None, glossary)
        term_issues = [i for i in issues if i["check_type"] == "term"]
        # "Iron" in "Ironclad" is NOT isolated -> should NOT flag
        assert len(term_issues) == 0

    @pytest.mark.asyncio
    async def test_term_check_no_glossary_no_issues(self):
        """Term Check with no glossary terms -> no issues."""
        row = make_row_dict(
            source="Some text here",
            target="Du texte ici"
        )

        issues = await _run_qa_checks(row, ["term"], None, [])
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) == 0

    def test_noise_filter_removes_frequent_terms(self):
        """Noise filter: term triggering >6 issues is excluded."""
        # Create issues where "Attack" triggers 7 times (> MAX_ISSUES_PER_TERM)
        all_issues = []
        for i in range(7):
            all_issues.append({
                "check_type": "term",
                "severity": "warning",
                "message": f"Missing term 'Attack' for '공격'",
                "details": {"glossary_source": "공격", "glossary_target": "Attack"}
            })
        # Add a normal term that triggers once
        all_issues.append({
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term 'Defense' for '방어'",
            "details": {"glossary_source": "방어", "glossary_target": "Defense"}
        })

        filtered = _apply_noise_filter(all_issues)
        # "Attack" (7 hits) should be removed, "Defense" (1 hit) should remain
        assert len(filtered) == 1
        assert filtered[0]["details"]["glossary_target"] == "Defense"

    def test_build_term_automaton(self):
        """_build_term_automaton creates automaton and term_map."""
        glossary = [("공격", "Attack"), ("방어", "Defense")]
        automaton, term_map = _build_term_automaton(glossary)

        # Should have entries
        assert len(term_map) == 2
        # Automaton should find terms in text
        hits = list(automaton.iter("공격 증가 방어"))
        assert len(hits) >= 2

    @pytest.mark.asyncio
    async def test_term_check_with_prebuilt_automaton(self):
        """File-level QA should accept pre-built automaton."""
        row = make_row_dict(
            source="공격 증가",
            target="Increase power"  # Missing "Attack"
        )
        glossary = [("공격", "Attack")]
        automaton, term_map = _build_term_automaton(glossary)

        issues = await _run_qa_checks(
            row, ["term"], None, glossary,
            term_automaton=automaton, term_map=term_map
        )
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) >= 1


# =============================================================================
# Test Multiple Check Types
# =============================================================================

class TestMultipleChecks:
    """Test running multiple check types together."""

    @pytest.mark.asyncio
    async def test_multiple_issues_detected(self):
        """Should detect issues from multiple check types."""
        row = make_row_dict(
            source="{0}의 {1}",
            target="of the"  # Missing patterns
        )

        issues = await _run_qa_checks(row, ["pattern"], None, None)

        # Should have pattern issue
        check_types = [i["check_type"] for i in issues]
        assert "pattern" in check_types
        assert len(issues) >= 1
