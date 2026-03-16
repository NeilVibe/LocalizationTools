"""Typed API client wrapper for LocaNext E2E tests.

Provides named methods for every API subsystem so that test files
never hard-code URL strings.  Each method returns the raw
``httpx.Response`` (via FastAPI ``TestClient``) so callers can assert
on ``status_code`` first, then parse ``.json()`` as needed.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi.testclient import TestClient


class APIClient:
    """Thin typed wrapper around :class:`TestClient` with auth headers baked in."""

    def __init__(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        self.client = client
        self.headers = auth_headers

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs: Any):
        kwargs.setdefault("headers", self.headers)
        return self.client.get(url, **kwargs)

    def _post(self, url: str, **kwargs: Any):
        kwargs.setdefault("headers", self.headers)
        return self.client.post(url, **kwargs)

    def _put(self, url: str, **kwargs: Any):
        kwargs.setdefault("headers", self.headers)
        return self.client.put(url, **kwargs)

    def _patch(self, url: str, **kwargs: Any):
        kwargs.setdefault("headers", self.headers)
        return self.client.patch(url, **kwargs)

    def _delete(self, url: str, **kwargs: Any):
        kwargs.setdefault("headers", self.headers)
        return self.client.delete(url, **kwargs)

    # ==================================================================
    # Auth  (/api/v2/auth)
    # ==================================================================

    def login(self, username: str = "admin", password: str = "admin123"):
        """POST /api/v2/auth/login"""
        return self.client.post(
            "/api/v2/auth/login",
            data={"username": username, "password": password},
        )

    def login_json(self, username: str = "admin", password: str = "admin123"):
        """POST /api/v2/auth/login  (JSON body variant)"""
        return self.client.post(
            "/api/v2/auth/login",
            json={"username": username, "password": password},
        )

    def register(self, username: str, password: str, email: str, **kwargs: Any):
        """POST /api/v2/auth/register"""
        body = {"username": username, "password": password, "email": email, **kwargs}
        return self._post("/api/v2/auth/register", json=body)

    def get_me(self):
        """GET /api/v2/auth/me"""
        return self._get("/api/v2/auth/me")

    def list_users(self):
        """GET /api/v2/auth/users"""
        return self._get("/api/v2/auth/users")

    def get_user(self, user_id: int):
        """GET /api/v2/auth/users/{user_id}"""
        return self._get(f"/api/v2/auth/users/{user_id}")

    def activate_user(self, user_id: int):
        """PUT /api/v2/auth/users/{user_id}/activate"""
        return self._put(f"/api/v2/auth/users/{user_id}/activate")

    def deactivate_user(self, user_id: int):
        """PUT /api/v2/auth/users/{user_id}/deactivate"""
        return self._put(f"/api/v2/auth/users/{user_id}/deactivate")

    def change_password(self, current_password: str, new_password: str):
        """PUT /api/v2/auth/me/password"""
        return self._put(
            "/api/v2/auth/me/password",
            json={"current_password": current_password, "new_password": new_password},
        )

    def admin_create_user(self, username: str, password: str, email: str, **kwargs: Any):
        """POST /api/v2/auth/admin/users"""
        body = {"username": username, "password": password, "email": email, **kwargs}
        return self._post("/api/v2/auth/admin/users", json=body)

    def admin_update_user(self, user_id: int, **kwargs: Any):
        """PUT /api/v2/auth/admin/users/{user_id}"""
        return self._put(f"/api/v2/auth/admin/users/{user_id}", json=kwargs)

    def admin_reset_password(self, user_id: int, new_password: str):
        """PUT /api/v2/auth/admin/users/{user_id}/reset-password"""
        return self._put(
            f"/api/v2/auth/admin/users/{user_id}/reset-password",
            json={"new_password": new_password},
        )

    def admin_delete_user(self, user_id: int):
        """DELETE /api/v2/auth/admin/users/{user_id}"""
        return self._delete(f"/api/v2/auth/admin/users/{user_id}")

    # ==================================================================
    # Projects  (/api/ldm/projects)
    # ==================================================================

    def create_project(self, name: str, description: Optional[str] = None, platform_id: Optional[int] = None):
        """POST /api/ldm/projects"""
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if platform_id is not None:
            body["platform_id"] = platform_id
        return self._post("/api/ldm/projects", json=body)

    def list_projects(self):
        """GET /api/ldm/projects"""
        return self._get("/api/ldm/projects")

    def get_project(self, project_id: int):
        """GET /api/ldm/projects/{project_id}"""
        return self._get(f"/api/ldm/projects/{project_id}")

    def rename_project(self, project_id: int, name: str):
        """PATCH /api/ldm/projects/{project_id}/rename"""
        return self._patch(f"/api/ldm/projects/{project_id}/rename", params={"name": name})

    def delete_project(self, project_id: int, permanent: bool = False):
        """DELETE /api/ldm/projects/{project_id}"""
        return self._delete(f"/api/ldm/projects/{project_id}", params={"permanent": permanent})

    def set_project_restriction(self, project_id: int, is_restricted: bool):
        """PUT /api/ldm/projects/{project_id}/restriction"""
        return self._put(f"/api/ldm/projects/{project_id}/restriction", params={"is_restricted": is_restricted})

    def list_project_access(self, project_id: int):
        """GET /api/ldm/projects/{project_id}/access"""
        return self._get(f"/api/ldm/projects/{project_id}/access")

    def grant_project_access(self, project_id: int, user_ids: list[int]):
        """POST /api/ldm/projects/{project_id}/access"""
        return self._post(f"/api/ldm/projects/{project_id}/access", json={"user_ids": user_ids})

    def revoke_project_access(self, project_id: int, user_id: int):
        """DELETE /api/ldm/projects/{project_id}/access/{user_id}"""
        return self._delete(f"/api/ldm/projects/{project_id}/access/{user_id}")

    def get_project_tree(self, project_id: int):
        """GET /api/ldm/projects/{project_id}/tree"""
        return self._get(f"/api/ldm/projects/{project_id}/tree")

    # ==================================================================
    # Folders  (/api/ldm/folders)
    # ==================================================================

    def list_folders(self, project_id: int):
        """GET /api/ldm/projects/{project_id}/folders"""
        return self._get(f"/api/ldm/projects/{project_id}/folders")

    def create_folder(self, name: str, project_id: int, parent_id: Optional[int] = None):
        """POST /api/ldm/folders"""
        body: dict[str, Any] = {"name": name, "project_id": project_id}
        if parent_id is not None:
            body["parent_id"] = parent_id
        return self._post("/api/ldm/folders", json=body)

    def get_folder_contents(self, folder_id: int):
        """GET /api/ldm/folders/{folder_id}"""
        return self._get(f"/api/ldm/folders/{folder_id}")

    def rename_folder(self, folder_id: int, name: str):
        """PATCH /api/ldm/folders/{folder_id}/rename"""
        return self._patch(f"/api/ldm/folders/{folder_id}/rename", params={"name": name})

    def move_folder(self, folder_id: int, parent_id: Optional[int]):
        """PATCH /api/ldm/folders/{folder_id}/move"""
        return self._patch(f"/api/ldm/folders/{folder_id}/move", json={"parent_id": parent_id})

    def delete_folder(self, folder_id: int, permanent: bool = False):
        """DELETE /api/ldm/folders/{folder_id}"""
        return self._delete(f"/api/ldm/folders/{folder_id}", params={"permanent": permanent})

    # ==================================================================
    # Files  (/api/ldm/files)
    # ==================================================================

    def upload_file(
        self,
        project_id: int,
        filename: str,
        content: bytes,
        content_type: str = "text/xml",
        folder_id: Optional[int] = None,
    ):
        """POST /api/ldm/files/upload"""
        data: dict[str, str] = {"project_id": str(project_id)}
        if folder_id is not None:
            data["folder_id"] = str(folder_id)
        return self._post(
            "/api/ldm/files/upload",
            data=data,
            files={"file": (filename, content, content_type)},
        )

    def list_files(self, project_id: int):
        """GET /api/ldm/files?project_id={project_id}"""
        return self._get("/api/ldm/files", params={"project_id": project_id})

    def get_file(self, file_id: int):
        """GET /api/ldm/files/{file_id}"""
        return self._get(f"/api/ldm/files/{file_id}")

    def download_file(self, file_id: int, fmt: str = "xml"):
        """GET /api/ldm/files/{file_id}/download"""
        return self._get(f"/api/ldm/files/{file_id}/download", params={"format": fmt})

    def delete_file(self, file_id: int, permanent: bool = False):
        """DELETE /api/ldm/files/{file_id}"""
        return self._delete(f"/api/ldm/files/{file_id}", params={"permanent": permanent})

    def move_file(self, file_id: int, folder_id: Optional[int]):
        """PATCH /api/ldm/files/{file_id}/move"""
        return self._patch(f"/api/ldm/files/{file_id}/move", json={"folder_id": folder_id})

    def rename_file(self, file_id: int, name: str):
        """PATCH /api/ldm/files/{file_id}/rename"""
        return self._patch(f"/api/ldm/files/{file_id}/rename", params={"name": name})

    def file_to_tm(self, file_id: int, name: str, **kwargs: Any):
        """POST /api/ldm/files/{file_id}/to-tm"""
        body = {"name": name, **kwargs}
        return self._post(f"/api/ldm/files/{file_id}/to-tm", json=body)

    # ==================================================================
    # Rows  (/api/ldm/files/{file_id}/rows, /api/ldm/rows/{row_id})
    # ==================================================================

    def list_rows(
        self,
        file_id: int,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        search_mode: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ):
        """GET /api/ldm/files/{file_id}/rows"""
        params: dict[str, Any] = {"page": page, "limit": limit}
        if search is not None:
            params["search"] = search
        if search_mode is not None:
            params["search_mode"] = search_mode
        if status is not None:
            params["status"] = status
        if category is not None:
            params["category"] = category
        return self._get(f"/api/ldm/files/{file_id}/rows", params=params)

    def update_row(self, row_id: int, target: Optional[str] = None, status: Optional[str] = None):
        """PUT /api/ldm/rows/{row_id}"""
        body: dict[str, Any] = {}
        if target is not None:
            body["target"] = target
        if status is not None:
            body["status"] = status
        return self._put(f"/api/ldm/rows/{row_id}", json=body)

    # ==================================================================
    # TM CRUD  (/api/ldm/tm)
    # ==================================================================

    def upload_tm(self, name: str, content: bytes, filename: str = "tm.txt", **kwargs: Any):
        """POST /api/ldm/tm/upload"""
        data = {"name": name, **{k: str(v) for k, v in kwargs.items()}}
        return self._post(
            "/api/ldm/tm/upload",
            data=data,
            files={"file": (filename, content, "text/plain")},
        )

    def list_tms(self):
        """GET /api/ldm/tm"""
        return self._get("/api/ldm/tm")

    def get_tm(self, tm_id: int):
        """GET /api/ldm/tm/{tm_id}"""
        return self._get(f"/api/ldm/tm/{tm_id}")

    def delete_tm(self, tm_id: int):
        """DELETE /api/ldm/tm/{tm_id}"""
        return self._delete(f"/api/ldm/tm/{tm_id}")

    def export_tm(self, tm_id: int, fmt: str = "text", columns: Optional[str] = None):
        """GET /api/ldm/tm/{tm_id}/export"""
        params: dict[str, str] = {"format": fmt}
        if columns:
            params["columns"] = columns
        return self._get(f"/api/ldm/tm/{tm_id}/export", params=params)

    # ==================================================================
    # TM Entries  (/api/ldm/tm/{tm_id}/entries)
    # ==================================================================

    def list_tm_entries(self, tm_id: int, page: int = 1, limit: int = 50):
        """GET /api/ldm/tm/{tm_id}/entries"""
        return self._get(f"/api/ldm/tm/{tm_id}/entries", params={"page": page, "limit": limit})

    def add_tm_entry(self, tm_id: int, source_text: str, target_text: str, **kwargs: Any):
        """POST /api/ldm/tm/{tm_id}/entries"""
        body = {"source_text": source_text, "target_text": target_text, **kwargs}
        return self._post(f"/api/ldm/tm/{tm_id}/entries", json=body)

    def update_tm_entry(self, tm_id: int, entry_id: int, **kwargs: Any):
        """PUT /api/ldm/tm/{tm_id}/entries/{entry_id}"""
        return self._put(f"/api/ldm/tm/{tm_id}/entries/{entry_id}", json=kwargs)

    def delete_tm_entry(self, tm_id: int, entry_id: int):
        """DELETE /api/ldm/tm/{tm_id}/entries/{entry_id}"""
        return self._delete(f"/api/ldm/tm/{tm_id}/entries/{entry_id}")

    def confirm_tm_entry(self, tm_id: int, entry_id: int):
        """POST /api/ldm/tm/{tm_id}/entries/{entry_id}/confirm"""
        return self._post(f"/api/ldm/tm/{tm_id}/entries/{entry_id}/confirm")

    def bulk_confirm_tm_entries(self, tm_id: int, entry_ids: list[int]):
        """POST /api/ldm/tm/{tm_id}/entries/bulk-confirm"""
        return self._post(f"/api/ldm/tm/{tm_id}/entries/bulk-confirm", json={"entry_ids": entry_ids})

    # ==================================================================
    # TM Search  (/api/ldm/tm/suggest, /api/ldm/tm/{tm_id}/search)
    # ==================================================================

    def tm_suggest(self, source_text: str, file_id: Optional[int] = None, **kwargs: Any):
        """GET /api/ldm/tm/suggest"""
        params: dict[str, Any] = {"source_text": source_text, **kwargs}
        if file_id is not None:
            params["file_id"] = file_id
        return self._get("/api/ldm/tm/suggest", params=params)

    def search_tm(self, tm_id: int, query: str, **kwargs: Any):
        """GET /api/ldm/tm/{tm_id}/search"""
        return self._get(f"/api/ldm/tm/{tm_id}/search", params={"query": query, **kwargs})

    def search_tm_exact(self, tm_id: int, source_text: str):
        """GET /api/ldm/tm/{tm_id}/search/exact"""
        return self._get(f"/api/ldm/tm/{tm_id}/search/exact", params={"source_text": source_text})

    # ==================================================================
    # TM Indexes  (/api/ldm/tm/{tm_id}/build-indexes, etc.)
    # ==================================================================

    def build_tm_indexes(self, tm_id: int):
        """POST /api/ldm/tm/{tm_id}/build-indexes"""
        return self._post(f"/api/ldm/tm/{tm_id}/build-indexes")

    def get_tm_index_status(self, tm_id: int):
        """GET /api/ldm/tm/{tm_id}/indexes"""
        return self._get(f"/api/ldm/tm/{tm_id}/indexes")

    def get_tm_sync_status(self, tm_id: int):
        """GET /api/ldm/tm/{tm_id}/sync-status"""
        return self._get(f"/api/ldm/tm/{tm_id}/sync-status")

    def sync_tm_indexes(self, tm_id: int):
        """POST /api/ldm/tm/{tm_id}/sync"""
        return self._post(f"/api/ldm/tm/{tm_id}/sync")

    # ==================================================================
    # TM Linking  (/api/ldm/projects/{pid}/link-tm, etc.)
    # ==================================================================

    def link_tm_to_project(self, project_id: int, tm_id: int, priority: int = 0):
        """POST /api/ldm/projects/{project_id}/link-tm"""
        return self._post(f"/api/ldm/projects/{project_id}/link-tm", json={"tm_id": tm_id, "priority": priority})

    def unlink_tm_from_project(self, project_id: int, tm_id: int):
        """DELETE /api/ldm/projects/{project_id}/link-tm/{tm_id}"""
        return self._delete(f"/api/ldm/projects/{project_id}/link-tm/{tm_id}")

    def get_linked_tms(self, project_id: int):
        """GET /api/ldm/projects/{project_id}/linked-tms"""
        return self._get(f"/api/ldm/projects/{project_id}/linked-tms")

    # ==================================================================
    # TM Assignment  (/api/ldm/tm/{tm_id}/assignment, etc.)
    # ==================================================================

    def get_tm_assignment(self, tm_id: int):
        """GET /api/ldm/tm/{tm_id}/assignment"""
        return self._get(f"/api/ldm/tm/{tm_id}/assignment")

    def assign_tm(self, tm_id: int, **kwargs: Any):
        """PATCH /api/ldm/tm/{tm_id}/assign"""
        return self._patch(f"/api/ldm/tm/{tm_id}/assign", json=kwargs)

    def activate_tm(self, tm_id: int, **kwargs: Any):
        """PATCH /api/ldm/tm/{tm_id}/activate"""
        return self._patch(f"/api/ldm/tm/{tm_id}/activate", json=kwargs)

    def get_active_tms_for_file(self, file_id: int):
        """GET /api/ldm/files/{file_id}/active-tms"""
        return self._get(f"/api/ldm/files/{file_id}/active-tms")

    def get_tm_tree(self):
        """GET /api/ldm/tm-tree"""
        return self._get("/api/ldm/tm-tree")

    # ==================================================================
    # TM Leverage  (/api/ldm/files/{file_id}/leverage)
    # ==================================================================

    def get_file_leverage(self, file_id: int):
        """GET /api/ldm/files/{file_id}/leverage"""
        return self._get(f"/api/ldm/files/{file_id}/leverage")

    # ==================================================================
    # Pretranslate  (/api/ldm/pretranslate)
    # ==================================================================

    def pretranslate(self, file_id: int, tm_id: int, **kwargs: Any):
        """POST /api/ldm/pretranslate"""
        body = {"file_id": file_id, "tm_id": tm_id, **kwargs}
        return self._post("/api/ldm/pretranslate", json=body)

    # ==================================================================
    # Merge  (/api/ldm/files/{file_id}/merge, gamedev-merge)
    # ==================================================================

    def merge_file(self, file_id: int, **kwargs: Any):
        """POST /api/ldm/files/{file_id}/merge"""
        return self._post(f"/api/ldm/files/{file_id}/merge", **kwargs)

    def gamedev_merge_file(self, file_id: int, **kwargs: Any):
        """POST /api/ldm/files/{file_id}/gamedev-merge"""
        return self._post(f"/api/ldm/files/{file_id}/gamedev-merge", **kwargs)

    # ==================================================================
    # GameData  (/api/ldm/gamedata)
    # ==================================================================

    def browse_gamedata(self, path: str = "", max_depth: int = 1):
        """POST /api/ldm/gamedata/browse"""
        return self._post("/api/ldm/gamedata/browse", json={"path": path, "max_depth": max_depth})

    def detect_columns(self, xml_path: str):
        """POST /api/ldm/gamedata/columns"""
        return self._post("/api/ldm/gamedata/columns", json={"xml_path": xml_path})

    def save_gamedata(self, xml_path: str, entity_index: int, attr_name: str, new_value: str):
        """PUT /api/ldm/gamedata/save"""
        return self._put("/api/ldm/gamedata/save", json={
            "xml_path": xml_path,
            "entity_index": entity_index,
            "attr_name": attr_name,
            "new_value": new_value,
        })

    def get_gamedata_tree(self, path: str, max_depth: int = -1):
        """POST /api/ldm/gamedata/tree"""
        return self._post("/api/ldm/gamedata/tree", json={"path": path, "max_depth": max_depth})

    def get_gamedata_tree_folder(self, path: str, max_depth: int = -1):
        """POST /api/ldm/gamedata/tree/folder"""
        return self._post("/api/ldm/gamedata/tree/folder", json={"path": path, "max_depth": max_depth})

    # ==================================================================
    # Codex  (/api/ldm/codex)
    # ==================================================================

    def search_codex(self, query: str, entity_type: Optional[str] = None, limit: int = 20):
        """GET /api/ldm/codex/search"""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        return self._get("/api/ldm/codex/search", params=params)

    def get_codex_entity(self, entity_type: str, strkey: str):
        """GET /api/ldm/codex/entity/{entity_type}/{strkey}"""
        return self._get(f"/api/ldm/codex/entity/{entity_type}/{strkey}")

    def list_codex_entities(self, entity_type: str):
        """GET /api/ldm/codex/list/{entity_type}"""
        return self._get(f"/api/ldm/codex/list/{entity_type}")

    def get_codex_types(self):
        """GET /api/ldm/codex/types"""
        return self._get("/api/ldm/codex/types")

    # ==================================================================
    # WorldMap  (/api/ldm/worldmap)
    # ==================================================================

    def get_worldmap(self):
        """GET /api/ldm/worldmap/data"""
        return self._get("/api/ldm/worldmap/data")

    # ==================================================================
    # AI Suggestions  (/api/ldm/ai-suggestions)
    # ==================================================================

    def ai_suggestions_status(self):
        """GET /api/ldm/ai-suggestions/status"""
        return self._get("/api/ldm/ai-suggestions/status")

    def get_ai_suggestions(self, string_id: str):
        """GET /api/ldm/ai-suggestions/{string_id}"""
        return self._get(f"/api/ldm/ai-suggestions/{string_id}")

    # ==================================================================
    # Naming  (/api/ldm/naming)
    # ==================================================================

    def naming_similar(self, entity_type: str, **kwargs: Any):
        """GET /api/ldm/naming/similar/{entity_type}"""
        return self._get(f"/api/ldm/naming/similar/{entity_type}", params=kwargs)

    def naming_suggest(self, entity_type: str, **kwargs: Any):
        """GET /api/ldm/naming/suggest/{entity_type}"""
        return self._get(f"/api/ldm/naming/suggest/{entity_type}", params=kwargs)

    def naming_status(self):
        """GET /api/ldm/naming/status"""
        return self._get("/api/ldm/naming/status")

    # ==================================================================
    # Search  (/api/ldm/search, /api/ldm/semantic-search)
    # ==================================================================

    def search_explorer(self, query: str, **kwargs: Any):
        """GET /api/ldm/search"""
        return self._get("/api/ldm/search", params={"q": query, **kwargs})

    def search_semantic(self, query: str, **kwargs: Any):
        """GET /api/ldm/semantic-search"""
        return self._get("/api/ldm/semantic-search", params={"query": query, **kwargs})

    # ==================================================================
    # QA  (/api/ldm/rows/{row_id}/check-qa, /api/ldm/files/{file_id}/check-qa)
    # ==================================================================

    def check_row_qa(self, row_id: int, checks: Optional[list[str]] = None, force: bool = False):
        """POST /api/ldm/rows/{row_id}/check-qa"""
        body: dict[str, Any] = {"force": force}
        if checks:
            body["checks"] = checks
        return self._post(f"/api/ldm/rows/{row_id}/check-qa", json=body)

    def get_row_qa_results(self, row_id: int):
        """GET /api/ldm/rows/{row_id}/qa-results"""
        return self._get(f"/api/ldm/rows/{row_id}/qa-results")

    def check_file_qa(self, file_id: int, checks: Optional[list[str]] = None, force: bool = False):
        """POST /api/ldm/files/{file_id}/check-qa"""
        body: dict[str, Any] = {"force": force}
        if checks:
            body["checks"] = checks
        return self._post(f"/api/ldm/files/{file_id}/check-qa", json=body)

    def get_file_qa_results(self, file_id: int, check_type: Optional[str] = None):
        """GET /api/ldm/files/{file_id}/qa-results"""
        params: dict[str, str] = {}
        if check_type:
            params["check_type"] = check_type
        return self._get(f"/api/ldm/files/{file_id}/qa-results", params=params)

    def get_file_qa_summary(self, file_id: int):
        """GET /api/ldm/files/{file_id}/qa-summary"""
        return self._get(f"/api/ldm/files/{file_id}/qa-summary")

    def resolve_qa_issue(self, result_id: int):
        """POST /api/ldm/qa-results/{result_id}/resolve"""
        return self._post(f"/api/ldm/qa-results/{result_id}/resolve")

    # ==================================================================
    # Grammar  (/api/ldm/grammar)
    # ==================================================================

    def grammar_status(self):
        """GET /api/ldm/grammar/status"""
        return self._get("/api/ldm/grammar/status")

    def check_file_grammar(self, file_id: int):
        """POST /api/ldm/files/{file_id}/check-grammar"""
        return self._post(f"/api/ldm/files/{file_id}/check-grammar")

    def check_row_grammar(self, row_id: int):
        """POST /api/ldm/rows/{row_id}/check-grammar"""
        return self._post(f"/api/ldm/rows/{row_id}/check-grammar")

    # ==================================================================
    # Context  (/api/ldm/context)
    # ==================================================================

    def get_context_status(self):
        """GET /api/ldm/context/status"""
        return self._get("/api/ldm/context/status")

    def get_context_by_string_id(self, string_id: str):
        """GET /api/ldm/context/{string_id}"""
        return self._get(f"/api/ldm/context/{string_id}")

    def detect_entities_in_text(self, text: str):
        """POST /api/ldm/context/detect"""
        return self._post("/api/ldm/context/detect", json={"text": text})

    # ==================================================================
    # MapData  (/api/ldm/mapdata)
    # ==================================================================

    def get_mapdata_status(self):
        """GET /api/ldm/mapdata/status"""
        return self._get("/api/ldm/mapdata/status")

    def configure_mapdata(self, **kwargs: Any):
        """POST /api/ldm/mapdata/configure"""
        return self._post("/api/ldm/mapdata/configure", json=kwargs)

    def get_image_context(self, string_id: str):
        """GET /api/ldm/mapdata/image/{string_id}"""
        return self._get(f"/api/ldm/mapdata/image/{string_id}")

    def get_audio_context(self, string_id: str):
        """GET /api/ldm/mapdata/audio/{string_id}"""
        return self._get(f"/api/ldm/mapdata/audio/{string_id}")

    def get_combined_context(self, string_id: str):
        """GET /api/ldm/mapdata/context/{string_id}"""
        return self._get(f"/api/ldm/mapdata/context/{string_id}")

    def get_thumbnail(self, texture_name: str):
        """GET /api/ldm/mapdata/thumbnail/{texture_name}"""
        return self._get(f"/api/ldm/mapdata/thumbnail/{texture_name}")

    def stream_audio(self, string_id: str):
        """GET /api/ldm/mapdata/audio/stream/{string_id}"""
        return self._get(f"/api/ldm/mapdata/audio/stream/{string_id}")

    # ==================================================================
    # Trash  (/api/ldm/trash)
    # ==================================================================

    def list_trash(self):
        """GET /api/ldm/trash"""
        return self._get("/api/ldm/trash")

    def restore_from_trash(self, trash_id: int):
        """POST /api/ldm/trash/{trash_id}/restore"""
        return self._post(f"/api/ldm/trash/{trash_id}/restore")

    def permanent_delete_trash(self, trash_id: int):
        """DELETE /api/ldm/trash/{trash_id}"""
        return self._delete(f"/api/ldm/trash/{trash_id}")

    def empty_trash(self):
        """POST /api/ldm/trash/empty"""
        return self._post("/api/ldm/trash/empty")

    # ==================================================================
    # Platforms  (/api/ldm/platforms)
    # ==================================================================

    def list_platforms(self):
        """GET /api/ldm/platforms"""
        return self._get("/api/ldm/platforms")

    def create_platform(self, name: str, **kwargs: Any):
        """POST /api/ldm/platforms"""
        return self._post("/api/ldm/platforms", json={"name": name, **kwargs})

    def get_platform(self, platform_id: int):
        """GET /api/ldm/platforms/{platform_id}"""
        return self._get(f"/api/ldm/platforms/{platform_id}")

    def update_platform(self, platform_id: int, **kwargs: Any):
        """PATCH /api/ldm/platforms/{platform_id}"""
        return self._patch(f"/api/ldm/platforms/{platform_id}", json=kwargs)

    def delete_platform(self, platform_id: int, permanent: bool = False):
        """DELETE /api/ldm/platforms/{platform_id}"""
        return self._delete(f"/api/ldm/platforms/{platform_id}", params={"permanent": permanent})

    def assign_project_to_platform(self, project_id: int, platform_id: Optional[int]):
        """PATCH /api/ldm/projects/{project_id}/platform"""
        return self._patch(f"/api/ldm/projects/{project_id}/platform", json={"platform_id": platform_id})

    # ==================================================================
    # Capabilities (admin)  (/api/ldm/admin/capabilities)
    # ==================================================================

    def list_available_capabilities(self):
        """GET /api/ldm/admin/capabilities/available"""
        return self._get("/api/ldm/admin/capabilities/available")

    def grant_capability(self, user_id: int, capability: str, **kwargs: Any):
        """POST /api/ldm/admin/capabilities"""
        return self._post("/api/ldm/admin/capabilities", json={"user_id": user_id, "capability": capability, **kwargs})

    def revoke_capability(self, capability_id: int):
        """DELETE /api/ldm/admin/capabilities/{capability_id}"""
        return self._delete(f"/api/ldm/admin/capabilities/{capability_id}")

    def list_all_capabilities(self):
        """GET /api/ldm/admin/capabilities"""
        return self._get("/api/ldm/admin/capabilities")

    def list_user_capabilities(self, user_id: int):
        """GET /api/ldm/admin/capabilities/user/{user_id}"""
        return self._get(f"/api/ldm/admin/capabilities/user/{user_id}")

    # ==================================================================
    # Settings  (/api/ldm/settings)
    # ==================================================================

    def list_embedding_engines(self):
        """GET /api/ldm/settings/embedding-engines"""
        return self._get("/api/ldm/settings/embedding-engines")

    def get_current_embedding_engine(self):
        """GET /api/ldm/settings/embedding-engine"""
        return self._get("/api/ldm/settings/embedding-engine")

    def set_embedding_engine(self, engine: str):
        """POST /api/ldm/settings/embedding-engine"""
        return self._post("/api/ldm/settings/embedding-engine", json={"engine": engine})

    # ==================================================================
    # Maintenance  (/api/ldm/maintenance)
    # ==================================================================

    def check_stale_tms(self):
        """POST /api/ldm/maintenance/check-stale"""
        return self._post("/api/ldm/maintenance/check-stale")

    def get_stale_tms(self):
        """GET /api/ldm/maintenance/stale-tms"""
        return self._get("/api/ldm/maintenance/stale-tms")

    def queue_tm_sync(self, tm_id: int):
        """POST /api/ldm/maintenance/sync/{tm_id}"""
        return self._post(f"/api/ldm/maintenance/sync/{tm_id}")

    def get_maintenance_status(self):
        """GET /api/ldm/maintenance/sync-status"""
        return self._get("/api/ldm/maintenance/sync-status")

    def cancel_tm_sync(self, tm_id: int):
        """DELETE /api/ldm/maintenance/sync/{tm_id}"""
        return self._delete(f"/api/ldm/maintenance/sync/{tm_id}")

    # ==================================================================
    # Health  (/api/ldm/health)
    # ==================================================================

    def health(self):
        """GET /api/ldm/health"""
        return self._get("/api/ldm/health")

    # ==================================================================
    # Admin overview (global health)
    # ==================================================================

    def admin_health(self):
        """GET /health  (top-level FastAPI health)"""
        return self._get("/health")
