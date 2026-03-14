"""
Integration test: Full offline workflow in SQLite-only mode.

Exercises the COMPLETE demo narrative using SQLite repositories directly:
  create hierarchy -> create rows -> edit -> confirm -> TM ops -> QA ops -> trash -> export

Runs parametrized against both SERVER_LOCAL (ldm_* tables) and OFFLINE (offline_* tables).
No live server needed -- pure repository-level validation.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Reuse stability conftest infrastructure
# ---------------------------------------------------------------------------
from tests.stability.conftest import (
    DbMode,
    _get_schema_mode,
    _make_repo,
    _make_test_db,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _server_local_template_db(tmp_path_factory):
    """Create server_local template DB once per session."""
    template_dir = tmp_path_factory.mktemp("integration_templates")
    template_path = template_dir / "server_local_template.db"

    from sqlalchemy import create_engine
    from server.database.models import Base
    engine = create_engine(f"sqlite:///{template_path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    return str(template_path)


@pytest.fixture(params=["server_local", "offline"], ids=["server_local", "offline"])
def mode(request):
    """Parametrize across both SQLite modes."""
    return DbMode.SERVER_LOCAL if request.param == "server_local" else DbMode.OFFLINE


@pytest.fixture
def clean_db(mode, tmp_path, _server_local_template_db):
    """Provide a fresh SQLite database for each test."""
    if mode == DbMode.SERVER_LOCAL:
        db_path = tmp_path / "server_local_test.db"
        shutil.copy2(_server_local_template_db, str(db_path))
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
        conn.close()
        return str(db_path)
    else:
        db_path = tmp_path / "offline_test.db"
        conn = sqlite3.connect(str(db_path))
        schema_path = Path(__file__).parent.parent.parent / "server" / "database" / "offline_schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
        conn.close()
        return str(db_path)


def _repo(mode, clean_db, repo_class):
    """Helper: create a repo instance wired to the test database."""
    return _make_repo(mode, clean_db, repo_class, _get_schema_mode(mode))


# ---------------------------------------------------------------------------
# Full Workflow Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestOfflineWorkflow:
    """End-to-end offline workflow: hierarchy -> rows -> edit -> TM -> QA -> trash -> export."""

    async def test_full_demo_workflow(self, mode, clean_db):
        """
        Complete demo narrative in a single test method.

        Steps: create hierarchy, insert rows, edit, confirm, TM create+entries,
        QA create with check_type, trash a row, retrieve all rows for export.
        """
        from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
        from server.repositories.sqlite.project_repo import SQLiteProjectRepository
        from server.repositories.sqlite.folder_repo import SQLiteFolderRepository
        from server.repositories.sqlite.file_repo import SQLiteFileRepository
        from server.repositories.sqlite.row_repo import SQLiteRowRepository
        from server.repositories.sqlite.tm_repo import SQLiteTMRepository
        from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository
        from server.repositories.sqlite.trash_repo import SQLiteTrashRepository

        schema_mode = _get_schema_mode(mode)

        # Build repos
        platform_repo = _repo(mode, clean_db, SQLitePlatformRepository)
        project_repo = _repo(mode, clean_db, SQLiteProjectRepository)
        folder_repo = _repo(mode, clean_db, SQLiteFolderRepository)
        file_repo = _repo(mode, clean_db, SQLiteFileRepository)
        row_repo = _repo(mode, clean_db, SQLiteRowRepository)
        tm_repo = _repo(mode, clean_db, SQLiteTMRepository)
        qa_repo = _repo(mode, clean_db, SQLiteQAResultRepository)
        trash_repo = _repo(mode, clean_db, SQLiteTrashRepository)

        # =====================================================================
        # Step 1: Create hierarchy  (platform -> project -> folder -> file)
        # =====================================================================
        platform = await platform_repo.create(name="PC", owner_id=1, description="PC Platform")
        assert platform is not None
        assert platform["name"] == "PC"
        platform_id = platform["id"]

        project = await project_repo.create(
            name="Dark Souls IV", owner_id=1,
            description="Action RPG", platform_id=platform_id,
        )
        assert project is not None
        project_id = project["id"]

        folder = await folder_repo.create(name="UI", project_id=project_id)
        assert folder is not None
        folder_id = folder["id"]

        file = await file_repo.create(
            name="menu_strings.xml",
            original_filename="menu_strings.xml",
            format="xml",
            project_id=project_id,
            folder_id=folder_id,
            source_language="ko",
            target_language="en",
        )
        assert file is not None
        file_id = file["id"]

        # =====================================================================
        # Step 2: Create 5 rows with Korean source and English target
        # =====================================================================
        row_data = [
            {"row_num": 0, "string_id": "MENU_NEW_GAME",  "source": "새 게임",      "target": "New Game",   "status": "normal"},
            {"row_num": 1, "string_id": "MENU_CONTINUE",   "source": "계속하기",     "target": "Continue",   "status": "normal"},
            {"row_num": 2, "string_id": "MENU_SETTINGS",   "source": "설정",         "target": "Settings",   "status": "normal"},
            {"row_num": 3, "string_id": "MENU_QUIT",       "source": "종료",         "target": "Quit",       "status": "normal"},
            {"row_num": 4, "string_id": "MENU_CREDITS",    "source": "크레딧",       "target": "Credits",    "status": "pending"},
        ]

        created_rows = []
        for rd in row_data:
            # Small delay between rows to ensure unique negative IDs
            time.sleep(0.002)
            row = await row_repo.create(
                file_id=file_id,
                row_num=rd["row_num"],
                source=rd["source"],
                target=rd["target"],
                string_id=rd["string_id"],
                status=rd["status"],
            )
            assert row is not None, f"Failed to create row {rd['string_id']}"
            created_rows.append(row)

        assert len(created_rows) == 5

        # =====================================================================
        # Step 3: Edit a row -- update target text
        # =====================================================================
        edit_row_id = created_rows[0]["id"]
        updated = await row_repo.update(edit_row_id, target="Start New Game")
        assert updated is not None
        assert updated["target"] == "Start New Game"

        # Verify persisted
        re_read = await row_repo.get(edit_row_id)
        assert re_read["target"] == "Start New Game"

        # =====================================================================
        # Step 4: Confirm a row -- change status
        # =====================================================================
        confirm_row_id = created_rows[1]["id"]
        confirmed = await row_repo.update(confirm_row_id, status="confirmed")
        assert confirmed is not None
        assert confirmed["status"] == "confirmed"

        re_read = await row_repo.get(confirm_row_id)
        assert re_read["status"] == "confirmed"

        # =====================================================================
        # Step 5: TM operations -- create TM, add entries, retrieve
        # =====================================================================
        tm = await tm_repo.create(name="UI_TM", source_lang="ko", target_lang="en")
        assert tm is not None
        tm_id = tm["id"]
        assert tm["name"] == "UI_TM"

        # Add entries
        tm_entries = [
            {"source": "새 게임",  "target": "New Game",  "string_id": "MENU_NEW_GAME"},
            {"source": "계속하기", "target": "Continue",   "string_id": "MENU_CONTINUE"},
            {"source": "설정",    "target": "Settings",   "string_id": "MENU_SETTINGS"},
        ]
        count = await tm_repo.add_entries_bulk(tm_id, tm_entries)
        assert count == 3

        # Retrieve entries
        entries = await tm_repo.get_entries(tm_id)
        assert len(entries) == 3

        # Verify TM data integrity
        sources = {e["source_text"] for e in entries}
        assert "새 게임" in sources
        assert "계속하기" in sources

        # =====================================================================
        # Step 6: QA operations -- store results with check_type, retrieve
        # =====================================================================
        qa_row_id = created_rows[2]["id"]

        # Create line_check result
        qa_line = await qa_repo.create(
            row_id=qa_row_id,
            file_id=file_id,
            check_type="line",
            severity="warning",
            message="Inconsistent translation for same source text",
            details={"source_count": 2, "target_variants": ["Settings", "Options"]},
        )
        assert qa_line is not None
        assert qa_line["check_type"] == "line"

        # Create term_check result
        time.sleep(0.002)
        qa_term = await qa_repo.create(
            row_id=qa_row_id,
            file_id=file_id,
            check_type="term",
            severity="error",
            message="Missing glossary term in target",
            details={"term": "설정", "expected": "Settings"},
        )
        assert qa_term is not None
        assert qa_term["check_type"] == "term"

        # Retrieve QA results by file
        qa_results = await qa_repo.get_for_file(file_id)
        assert len(qa_results) >= 2
        check_types = {r["check_type"] for r in qa_results}
        assert "line" in check_types, "line check_type must work in offline schema"
        assert "term" in check_types, "term check_type must work in offline schema"

        # Get QA summary
        summary = await qa_repo.get_summary(file_id)
        assert summary["line"] >= 1
        assert summary["term"] >= 1
        assert summary["total"] >= 2

        # =====================================================================
        # Step 7: Trash operations -- move row to trash, verify retrievable
        # =====================================================================
        trash_row_id = created_rows[3]["id"]
        trash_row_data = created_rows[3]

        trash_item = await trash_repo.create(
            item_type="row",
            item_id=trash_row_id,
            item_name=trash_row_data["string_id"],
            item_data={"source": trash_row_data["source"], "target": trash_row_data["target"]},
            deleted_by=1,
            parent_project_id=project_id,
        )
        assert trash_item is not None
        assert trash_item["item_type"] == "row"
        assert trash_item["status"] == "trashed"

        # Verify retrievable from trash
        retrieved_trash = await trash_repo.get(trash_item["id"])
        assert retrieved_trash is not None
        assert retrieved_trash["item_name"] == "MENU_QUIT"

        # =====================================================================
        # Step 8: Export verification -- retrieve all rows, verify counts
        # =====================================================================
        all_rows = await row_repo.get_all_for_file(file_id)
        assert len(all_rows) == 5  # All 5 rows still exist (trash is separate table)

        # Verify data integrity of key rows
        row_map = {r["string_id"]: r for r in all_rows}
        assert row_map["MENU_NEW_GAME"]["target"] == "Start New Game"  # Was edited
        assert row_map["MENU_CONTINUE"]["status"] == "confirmed"       # Was confirmed
        assert row_map["MENU_SETTINGS"]["source"] == "설정"            # Unchanged

        # Verify file row_count was updated
        file_data = await file_repo.get(file_id)
        assert file_data["row_count"] == 5
