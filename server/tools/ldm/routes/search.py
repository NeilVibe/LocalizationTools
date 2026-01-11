"""
EXPLORER-004: Explorer Search Endpoint
Full recursive search like "Everything" - fast, beautiful paths

P10-SEARCH: Refactored to use Repository Pattern with ONE code path.
The repository factory selects PostgreSQL or SQLite based on mode.
"""

from fastapi import APIRouter, Depends, Query, Request
from typing import List, Dict, Any

from server.utils.dependencies import get_current_active_user_async
from server.repositories import (
    PlatformRepository, ProjectRepository, FolderRepository, FileRepository,
    get_platform_repository, get_project_repository,
    get_folder_repository, get_file_repository
)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_explorer(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    platform_repo: PlatformRepository = Depends(get_platform_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Full recursive search across all entities.
    Returns matches with complete Linux-style paths.

    P10-SEARCH: Uses Repository Pattern - ONE code path for both online and offline.
    The repository factory selects the appropriate adapter based on auth token.
    """
    results = []

    # P10: ONE code path - repositories handle both PostgreSQL and SQLite
    # Search all entity types using repository search() methods
    platforms = await platform_repo.search(q)
    projects = await project_repo.search(q)
    folders = await folder_repo.search(q)
    files = await file_repo.search(q)

    # Build caches for path construction
    # (repositories return normalized dicts, we can build paths from them)
    platforms_cache = {p["id"]: p for p in await platform_repo.get_all()}
    projects_cache = {}
    folders_cache = {}

    # Load all projects for path building
    all_projects = await project_repo.get_all()
    for proj in all_projects:
        projects_cache[proj["id"]] = proj

    # Load all folders for path building (we need all folders, not just matching ones)
    # This is necessary to build full paths from nested folders
    for proj in all_projects:
        proj_folders = await folder_repo.get_all(proj["id"])
        for f in proj_folders:
            folders_cache[f["id"]] = f

    def build_folder_path(folder_id: int) -> List[Dict[str, Any]]:
        """Build path from folder to root (recursive)"""
        path = []
        current_id = folder_id
        visited = set()  # Prevent infinite loops

        while current_id and current_id not in visited:
            visited.add(current_id)
            folder = folders_cache.get(current_id)
            if not folder:
                break
            path.insert(0, {
                'type': 'folder',
                'id': folder['id'],
                'name': folder['name']
            })
            current_id = folder.get('parent_id')

        return path

    def build_full_path(project_id: int, folder_id: int = None) -> List[Dict[str, Any]]:
        """Build complete path: platform / project / folders"""
        path = []

        # Add platform if exists
        project = projects_cache.get(project_id)
        if project:
            platform_id = project.get('platform_id')
            if platform_id:
                platform = platforms_cache.get(platform_id)
                if platform:
                    path.append({
                        'type': 'platform',
                        'id': platform['id'],
                        'name': platform['name']
                    })

            # Add project
            path.append({
                'type': 'project',
                'id': project['id'],
                'name': project['name']
            })

        # Add folder path
        if folder_id:
            path.extend(build_folder_path(folder_id))

        return path

    def path_to_string(path: List[Dict[str, Any]]) -> str:
        """Convert path to Linux-style string"""
        if not path:
            return "/"
        return '/' + '/'.join(p['name'] for p in path)

    # Process platform results
    for p in platforms:
        path = [{'type': 'platform', 'id': p['id'], 'name': p['name']}]
        results.append({
            'type': 'platform',
            'id': p['id'],
            'name': p['name'],
            'path': path,
            'pathString': path_to_string(path)
        })

    # Process project results
    for proj in projects:
        path = build_full_path(proj['id'])
        results.append({
            'type': 'project',
            'id': proj['id'],
            'name': proj['name'],
            'path': path,
            'pathString': path_to_string(path)
        })

    # Process folder results
    for folder in folders:
        project_id = folder.get('project_id')
        path = build_full_path(project_id, folder['id']) if project_id else []
        results.append({
            'type': 'folder',
            'id': folder['id'],
            'name': folder['name'],
            'project_id': project_id,
            'path': path,
            'pathString': path_to_string(path)
        })

    # Process file results
    for file in files:
        project_id = file.get('project_id')
        folder_id = file.get('folder_id')

        # Check if it's a local file (SQLite offline mode)
        sync_status = file.get('sync_status')
        if sync_status == 'local':
            # Local file in Offline Storage
            path = [
                {'type': 'offline-storage', 'id': 0, 'name': 'Offline Storage'},
                {'type': 'local-file', 'id': file['id'], 'name': file['name']}
            ]
            results.append({
                'type': 'local-file',
                'id': file['id'],
                'name': file['name'],
                'path': path,
                'pathString': f"/Offline Storage/{file['name']}"
            })
        else:
            # Regular file
            path = build_full_path(project_id, folder_id) if project_id else []
            file_entry = {'type': 'file', 'id': file['id'], 'name': file['name']}
            path.append(file_entry)
            results.append({
                'type': 'file',
                'id': file['id'],
                'name': file['name'],
                'project_id': project_id,
                'folder_id': folder_id,
                'path': path,
                'pathString': path_to_string(path)
            })

    # Sort by path for beautiful grouping
    results.sort(key=lambda x: x['pathString'].lower())

    return {
        'query': q,
        'count': len(results),
        'results': results[:100]  # Max 100 results
    }
