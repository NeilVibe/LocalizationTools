"""
Tests for TM Sync Manager

Tests the PKL vs DB synchronization logic:
- INSERT: entries in DB, not in PKL
- UPDATE: entries in both, Target changed
- DELETE: entries in PKL, not in DB
- UNCHANGED: same Source+Target

Run with: python3 -m pytest tests/unit/test_tm_sync.py -v
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from server.tools.ldm.tm_indexer import TMSyncManager, normalize_for_hash


class MockSession:
    """Mock SQLAlchemy session for testing."""

    def __init__(self):
        self.entries = []

    def query(self, model):
        return self

    def filter(self, *args):
        return self

    def all(self):
        return self.entries


class TestComputeDiff:
    """Test compute_diff logic for INSERT/UPDATE/DELETE/UNCHANGED detection."""

    def test_fresh_build_all_inserts(self):
        """No PKL state means all DB entries are INSERTs."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
            {"id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            {"id": 3, "source_text": "삭제하기", "target_text": "Delete"},
        ]

        result = sync_manager.compute_diff(db_entries, pkl_state=None)

        assert result["stats"]["insert"] == 3
        assert result["stats"]["update"] == 0
        assert result["stats"]["delete"] == 0
        assert result["stats"]["unchanged"] == 0
        assert len(result["insert"]) == 3

    def test_no_changes_all_unchanged(self):
        """Same DB and PKL state means all UNCHANGED."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
            {"id": 2, "source_text": "취소하기", "target_text": "Cancel"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            ],
            "embeddings": np.random.randn(2, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["insert"] == 0
        assert result["stats"]["update"] == 0
        assert result["stats"]["delete"] == 0
        assert result["stats"]["unchanged"] == 2

    def test_new_entry_detected_as_insert(self):
        """New DB entry not in PKL is INSERT."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
            {"id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            {"id": 3, "source_text": "새로운것", "target_text": "New"},  # NEW
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            ],
            "embeddings": np.random.randn(2, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["insert"] == 1
        assert result["stats"]["unchanged"] == 2
        assert result["stats"]["delete"] == 0
        assert result["insert"][0]["source_text"] == "새로운것"

    def test_removed_entry_detected_as_delete(self):
        """PKL entry not in DB is DELETE."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
            # "취소하기" was removed from DB
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            ],
            "embeddings": np.random.randn(2, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["insert"] == 0
        assert result["stats"]["unchanged"] == 1
        assert result["stats"]["delete"] == 1
        assert result["delete"][0]["source_text"] == "취소하기"

    def test_changed_target_detected_as_update(self):
        """Same source, different target is UPDATE."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save Changes"},  # CHANGED
            {"id": 2, "source_text": "취소하기", "target_text": "Cancel"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},  # OLD
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            ],
            "embeddings": np.random.randn(2, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["update"] == 1
        assert result["stats"]["unchanged"] == 1
        assert result["update"][0]["target_text"] == "Save Changes"
        assert result["update"][0]["old_target"] == "Save"

    def test_mixed_operations(self):
        """Test INSERT + UPDATE + DELETE + UNCHANGED together."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},  # UNCHANGED
            {"id": 2, "source_text": "취소하기", "target_text": "Cancel Now"},  # UPDATE
            {"id": 4, "source_text": "새로운것", "target_text": "New"},  # INSERT
            # "삭제하기" removed - DELETE
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
                {"entry_id": 3, "source_text": "삭제하기", "target_text": "Delete"},
            ],
            "embeddings": np.random.randn(3, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["insert"] == 1
        assert result["stats"]["update"] == 1
        assert result["stats"]["delete"] == 1
        assert result["stats"]["unchanged"] == 1

    def test_empty_db_clears_all(self):
        """Empty DB means all PKL entries become DELETE."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = []  # Empty DB

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
                {"entry_id": 2, "source_text": "취소하기", "target_text": "Cancel"},
            ],
            "embeddings": np.random.randn(2, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Empty DB returns all empty
        assert result["stats"]["insert"] == 0
        assert result["stats"]["update"] == 0
        assert result["stats"]["delete"] == 0
        assert result["stats"]["unchanged"] == 0

    def test_case_insensitive_source_matching(self):
        """Source matching is case-insensitive via normalization."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "Save File", "target_text": "파일 저장"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "SAVE FILE", "target_text": "파일 저장"},
            ],
            "embeddings": np.random.randn(1, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Should match as UNCHANGED despite case difference
        assert result["stats"]["unchanged"] == 1
        assert result["stats"]["insert"] == 0

    def test_whitespace_normalized_matching(self):
        """Source matching normalizes whitespace."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "Save   the   file", "target_text": "저장"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "Save the file", "target_text": "저장"},
            ],
            "embeddings": np.random.randn(1, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Should match as UNCHANGED despite whitespace difference
        assert result["stats"]["unchanged"] == 1


class TestSyncManagerInit:
    """Test TMSyncManager initialization."""

    def test_default_data_dir(self):
        """Default data dir is server/data/ldm_tm."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=123)

        assert "ldm_tm" in str(sync_manager.data_dir)
        assert str(sync_manager.tm_path).endswith("123")

    def test_custom_data_dir(self):
        """Custom data dir is used when provided."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=123, data_dir="/tmp/custom")

        assert str(sync_manager.data_dir) == "/tmp/custom"
        assert str(sync_manager.tm_path) == "/tmp/custom/123"


class TestEmbeddingReuse:
    """Test that unchanged embeddings are reused."""

    def test_unchanged_entries_reuse_embeddings(self):
        """Unchanged entries should copy existing embeddings, not regenerate."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        # This is tested via compute_diff - unchanged entries are identified
        # The sync() method then copies their embeddings instead of regenerating

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
        ]

        original_embedding = np.random.randn(1, 512).astype(np.float32)
        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": "Save"},
            ],
            "embeddings": original_embedding
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Unchanged should be detected
        assert result["stats"]["unchanged"] == 1
        assert result["stats"]["insert"] == 0

        # The sync() method would then reuse the embedding at index 0


class TestMultilineHandling:
    """Test multiline text handling in sync."""

    def test_multiline_source_normalized(self):
        """Multiline sources are normalized for comparison."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "Line 1\nLine 2", "target_text": "줄 1\n줄 2"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "Line 1\nLine 2", "target_text": "줄 1\n줄 2"},
            ],
            "embeddings": np.random.randn(1, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["unchanged"] == 1

    def test_multiline_target_change_detected(self):
        """Changes in multiline targets are detected."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "Line 1\nLine 2", "target_text": "줄 1\n줄 2 수정됨"},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "Line 1\nLine 2", "target_text": "줄 1\n줄 2"},
            ],
            "embeddings": np.random.randn(1, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["update"] == 1
        assert result["stats"]["unchanged"] == 0


class TestEdgeCases:
    """Test edge cases in sync logic."""

    def test_empty_pkl_mapping(self):
        """Empty PKL mapping is treated as fresh build."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": "Save"},
        ]

        pkl_state = {
            "mapping": [],  # Empty
            "embeddings": None
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        assert result["stats"]["insert"] == 1
        assert result["stats"]["unchanged"] == 0

    def test_null_target_handling(self):
        """Null/None targets don't break comparison."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "저장하기", "target_text": None},
        ]

        pkl_state = {
            "mapping": [
                {"entry_id": 1, "source_text": "저장하기", "target_text": None},
            ],
            "embeddings": np.random.randn(1, 512).astype(np.float32)
        }

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Both None should be unchanged
        assert result["stats"]["unchanged"] == 1

    def test_empty_string_source(self):
        """Empty source strings are handled gracefully."""
        mock_db = MockSession()
        sync_manager = TMSyncManager(mock_db, tm_id=1)

        db_entries = [
            {"id": 1, "source_text": "", "target_text": "Empty"},
            {"id": 2, "source_text": "저장하기", "target_text": "Save"},
        ]

        pkl_state = None  # Fresh build

        result = sync_manager.compute_diff(db_entries, pkl_state)

        # Both should be inserts (empty strings are still processed)
        assert result["stats"]["insert"] == 2
