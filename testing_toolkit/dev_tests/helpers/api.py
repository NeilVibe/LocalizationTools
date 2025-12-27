"""
API Helper for Dev Testing

Usage:
    from helpers.api import LDMApi

    api = LDMApi()
    api.login()
    projects = api.get_projects()
    files = api.get_files(project_id=8)
"""

import requests
from typing import List, Dict, Any, Optional

API_URL = "http://localhost:8888"

class LDMApi:
    """LDM API helper with authentication."""

    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url
        self.token = None
        self.headers = {}

    def login(self, username: str = "admin", password: str = "admin123") -> bool:
        """Login and store token."""
        resp = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            return True
        return False

    def _get(self, endpoint: str) -> Any:
        """Make authenticated GET request."""
        resp = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> Any:
        """Make authenticated POST request."""
        resp = requests.post(
            f"{self.base_url}{endpoint}",
            json=data,
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()

    def _delete(self, endpoint: str) -> Any:
        """Make authenticated DELETE request."""
        resp = requests.delete(f"{self.base_url}{endpoint}", headers=self.headers)
        resp.raise_for_status()
        return resp.json() if resp.text else None

    # Projects

    def get_projects(self) -> List[Dict]:
        """Get all projects."""
        return self._get("/api/ldm/projects")

    def create_project(self, name: str, description: str = None) -> Dict:
        """Create a new project."""
        return self._post("/api/ldm/projects", {
            "name": name,
            "description": description
        })

    # Files

    def get_files(self, project_id: int) -> List[Dict]:
        """Get files for a project."""
        return self._get(f"/api/ldm/projects/{project_id}/files")

    def upload_file(self, project_id: int, file_path: str) -> Dict:
        """Upload a file to a project."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'project_id': str(project_id)}
            resp = requests.post(
                f"{self.base_url}/api/ldm/files/upload",
                files=files,
                data=data,
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    # Rows

    def get_rows(self, file_id: int, offset: int = 0, limit: int = 50,
                 search: str = None) -> Dict:
        """Get rows for a file with optional search."""
        params = f"file_id={file_id}&offset={offset}&limit={limit}"
        if search:
            params += f"&search={search}"
        return self._get(f"/api/ldm/rows?{params}")

    # Health

    def health_check(self) -> Dict:
        """Check server health (no auth needed)."""
        resp = requests.get(f"{self.base_url}/health")
        return resp.json()


if __name__ == "__main__":
    # Test API helper
    api = LDMApi()

    # Health check
    health = api.health_check()
    print(f"Server status: {health.get('status')}")
    print(f"Database: {health.get('database_type')}")

    # Login
    if api.login():
        print("\nLogin successful!")

        # Get projects
        projects = api.get_projects()
        print(f"\nProjects: {len(projects)}")
        for p in projects:
            print(f"  {p['id']}: {p['name']}")

            # Get files for each project
            files = api.get_files(p['id'])
            print(f"    Files: {len(files)}")
            for f in files:
                print(f"      {f['id']}: {f['name']}")
    else:
        print("Login failed!")
