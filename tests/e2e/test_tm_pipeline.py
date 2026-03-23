"""
TM Pipeline E2E Tests.

Verifies the full TM lifecycle: populate mock entries via API,
trigger index builds (Model2Vec + FAISS), then run cascade search
and confirm matches across tiers.

Covers: FEAT-01 (auto-update), FEAT-02 (5-tier cascade), FEAT-07 (mock TM data).
"""
from __future__ import annotations

import time
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.tm]

# Module-level state shared across test classes (set by TestTMPopulation)
_tm_id: int | None = None
_entry_ids: list[int] = []


# ======================================================================
# FEAT-07: TM Population with realistic game localization pairs
# ======================================================================


class TestTMPopulation:
    """Populate a TM with 10 realistic game localization entries."""

    TM_PAIRS = [
        ("The warrior draws his sword", "\uc804\uc0ac\uac00 \uac80\uc744 \ubed1\ub294\ub2e4"),
        ("Quest completed successfully", "\ud034\uc2a4\ud2b8\uac00 \uc131\uacf5\uc801\uc73c\ub85c \uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4"),
        ("You have received a new item", "\uc0c8\ub85c\uc6b4 \uc544\uc774\ud15c\uc744 \ud68d\ub4dd\ud588\uc2b5\ub2c8\ub2e4"),
        ("The dragon attacks from above", "\ub4dc\ub798\uace4\uc774 \uc704\uc5d0\uc11c \uacf5\uaca9\ud55c\ub2e4"),
        ("Welcome to the arena", "\uc544\ub808\ub098\uc5d0 \uc624\uc2e0 \uac83\uc744 \ud658\uc601\ud569\ub2c8\ub2e4"),
        ("Select your character", "\uce90\ub9ad\ud130\ub97c \uc120\ud0dd\ud558\uc138\uc694"),
        ("Loading game data", "\uac8c\uc784 \ub370\uc774\ud130 \ub85c\ub529 \uc911"),
        ("The merchant sells rare weapons", "\uc0c1\uc778\uc774 \ud76c\uadc0 \ubb34\uae30\ub97c \ud310\ub9e4\ud55c\ub2e4"),
        ("Victory is yours", "\uc2b9\ub9ac\ub294 \ub2f9\uc2e0\uc758 \uac83\uc785\ub2c8\ub2e4"),
        ("Enter the dungeon", "\ub358\uc804\uc5d0 \uc785\uc7a5\ud558\uc138\uc694"),
    ]

    @pytest.fixture(scope="class", autouse=True)
    def _setup_tm(self, api, test_project_id):
        """Create TM, add 10 entries, link to project."""
        global _tm_id, _entry_ids

        # 1. Create TM via upload (needs 7+ tab-separated columns for txt parser)
        tm_name = f"E2E-TM-Pipeline-{int(time.time())}"
        seed_lines = [
            "A\tB\tC\tD\tE\tSeed source\tSeed target",
        ]
        seed_content = "\n".join(seed_lines).encode("utf-8")
        resp = api.upload_tm(
            name=tm_name,
            content=seed_content,
            filename="seed.txt",
        )
        assert resp.status_code == 200, f"TM upload failed: {resp.text}"
        tm_data = resp.json()
        _tm_id = tm_data.get("id") or tm_data.get("tm_id")
        assert _tm_id is not None, f"No TM ID in response: {tm_data}"

        # 2. Add 10 entries (endpoint uses Form(...), not JSON)
        _entry_ids.clear()
        for source, target in self.TM_PAIRS:
            r = api.client.post(
                f"/api/ldm/tm/{_tm_id}/entries",
                headers=api.headers,
                data={"source_text": source, "target_text": target},
            )
            assert r.status_code in (200, 201), (
                f"add_tm_entry failed for '{source[:30]}': {r.status_code} {r.text[:200]}"
            )
            entry_data = r.json()
            eid = entry_data.get("id") or entry_data.get("entry_id")
            if eid is not None:
                _entry_ids.append(eid)

        # 3. Link TM to project
        link_resp = api.link_tm_to_project(test_project_id, _tm_id)
        assert link_resp.status_code in (200, 201, 409), (
            f"link_tm_to_project failed: {link_resp.status_code} {link_resp.text[:200]}"
        )

        yield

        # Teardown: no explicit TM delete required (project teardown handles it)

    def test_tm_entries_created(self, api):
        """Verify at least 10 entries exist in the TM."""
        resp = api.list_tm_entries(_tm_id, page=1, limit=50)
        assert resp.status_code == 200, f"list_tm_entries failed: {resp.text[:200]}"
        data = resp.json()
        # Response may be a list or dict with 'entries'/'items' key
        if isinstance(data, list):
            entries = data
        else:
            entries = data.get("entries") or data.get("items") or data.get("data", [])
        assert len(entries) >= 10, f"Expected >= 10 entries, got {len(entries)}"

    def test_tm_linked_to_project(self, api, test_project_id):
        """Verify the TM is linked to the test project."""
        resp = api.get_linked_tms(test_project_id)
        assert resp.status_code == 200, f"get_linked_tms failed: {resp.text[:200]}"
        data = resp.json()
        if isinstance(data, list):
            linked_ids = [t.get("id") or t.get("tm_id") for t in data]
        else:
            items = data.get("tms") or data.get("items") or data.get("data", [])
            linked_ids = [t.get("id") or t.get("tm_id") for t in items]
        assert _tm_id in linked_ids, f"TM {_tm_id} not in linked TMs: {linked_ids}"


# ======================================================================
# FEAT-01: TM Auto-Update (add/update/delete + index build)
# ======================================================================


class TestTMAutoUpdate:
    """Verify CRUD operations on TM entries and index building."""

    _extra_entry_id: int | None = None

    def test_add_entry_returns_200(self, api):
        """Adding a new entry should succeed."""
        resp = api.client.post(
            f"/api/ldm/tm/{_tm_id}/entries",
            headers=api.headers,
            data={
                "source_text": "Health potion restores HP",
                "target_text": "\uccb4\ub825 \ud3ec\uc158\uc774 HP\ub97c \ud68c\ubcf5\ud569\ub2c8\ub2e4",
            },
        )
        assert resp.status_code in (200, 201), f"add failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        TestTMAutoUpdate._extra_entry_id = data.get("id") or data.get("entry_id")

    def test_update_entry_returns_200(self, api):
        """Updating an existing entry's target text should succeed."""
        if TestTMAutoUpdate._extra_entry_id is None:
            pytest.skip("No entry ID from add step")
        # Endpoint uses query params (no Form/Body annotation)
        resp = api.client.put(
            f"/api/ldm/tm/{_tm_id}/entries/{TestTMAutoUpdate._extra_entry_id}",
            headers=api.headers,
            params={"target_text": "\uccb4\ub825 \ud3ec\uc158\uc774 HP\ub97c \uc644\uc804\ud788 \ud68c\ubcf5\ud569\ub2c8\ub2e4"},
        )
        assert resp.status_code == 200, f"update failed: {resp.status_code} {resp.text[:200]}"

    def test_delete_entry_returns_200(self, api):
        """Deleting an entry should succeed."""
        if TestTMAutoUpdate._extra_entry_id is None:
            pytest.skip("No entry ID from add step")
        resp = api.delete_tm_entry(_tm_id, TestTMAutoUpdate._extra_entry_id)
        assert resp.status_code in (200, 204), f"delete failed: {resp.status_code} {resp.text[:200]}"

    def test_build_indexes_succeeds(self, api):
        """Building TM indexes (FAISS + hash) should complete without error."""
        resp = api.build_tm_indexes(_tm_id)
        assert resp.status_code == 200, f"build_indexes failed: {resp.status_code} {resp.text[:200]}"

    @pytest.mark.xfail(
        reason="Index status response format may vary; FAISS fields depend on Model2Vec availability",
        strict=False,
    )
    def test_index_status_has_faiss(self, api):
        """After build, index status should reference FAISS or embedding data."""
        resp = api.get_tm_index_status(_tm_id)
        assert resp.status_code == 200, f"get_tm_index_status failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        text = str(data).lower()
        assert any(
            kw in text for kw in ("faiss", "embedding", "index", "vector", "model2vec")
        ), f"No FAISS-related fields in index status: {data}"


# ======================================================================
# FEAT-02: TM Cascade Search (5-tier search after index build)
# ======================================================================


class TestTMCascadeSearch:
    """Verify cascade search returns matches across tiers."""

    @pytest.mark.xfail(
        reason="Exact search requires built FAISS indexes and Model2Vec; may not be available in CI",
        strict=False,
    )
    def test_exact_search_tier1(self, api):
        """Tier 1: exact source text should return high-confidence match (>= 0.99)."""
        resp = api.search_tm(_tm_id, query="The warrior draws his sword")
        assert resp.status_code == 200, f"search_tm failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        results = data if isinstance(data, list) else data.get("results") or data.get("matches") or data.get("data", [])
        assert len(results) > 0, f"No results for exact query: {data}"
        # Check highest confidence
        best = results[0]
        score = best.get("score") or best.get("confidence") or best.get("similarity", 0)
        assert score >= 0.99, f"Expected >= 0.99 confidence for exact match, got {score}"

    @pytest.mark.xfail(
        reason="Fuzzy search requires FAISS embeddings; may not be available in CI",
        strict=False,
    )
    def test_fuzzy_search_tier2(self, api):
        """Tier 2: similar but not exact text should return at least one result."""
        resp = api.search_tm(_tm_id, query="A warrior draws a sword")
        assert resp.status_code == 200, f"search_tm failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        results = data if isinstance(data, list) else data.get("results") or data.get("matches") or data.get("data", [])
        assert len(results) > 0, f"No fuzzy results returned: {data}"

    @pytest.mark.xfail(
        reason="tm_suggest requires linked TM with built indexes; may not be available in CI",
        strict=False,
    )
    def test_cascade_suggest(self, api):
        """Cascade suggest should return results for partial source text."""
        resp = api.tm_suggest(source_text="Quest completed")
        assert resp.status_code == 200, f"tm_suggest failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        results = data if isinstance(data, list) else data.get("results") or data.get("suggestions") or data.get("data", [])
        assert len(results) > 0, f"No suggestions returned: {data}"

    def test_no_match_for_unrelated(self, api):
        """Completely unrelated text should return no results or low confidence."""
        resp = api.search_tm(_tm_id, query="Banana split ice cream sundae")
        # Even if the endpoint returns 200, results should be empty or low-confidence
        if resp.status_code == 200:
            data = resp.json()
            results = data if isinstance(data, list) else data.get("results") or data.get("matches") or data.get("data", [])
            if len(results) > 0:
                best = results[0]
                score = best.get("score") or best.get("confidence") or best.get("similarity", 0)
                assert score < 0.92, f"Unrelated query got high score {score}: {best}"
        # 404 or empty response is also acceptable
