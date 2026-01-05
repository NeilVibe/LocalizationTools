"""
EXPLORER-004: Explorer Search Endpoint
Full recursive search like "Everything" - fast, beautiful paths
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMPlatform, LDMProject, LDMFolder, LDMFile

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_explorer(
    q: str = Query(..., min_length=1, description="Search query"),
    mode: str = Query("online", description="Search mode: 'online' (search all), 'offline' (local files only)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Full recursive search across all entities.
    Returns matches with complete Linux-style paths.

    Mode:
    - 'online' (default): Search PostgreSQL + Offline Storage
    - 'offline': Only search Offline Storage (local files)
    """
    results = []

    # P9: In offline mode, search ALL SQLite data (synced + local)
    if mode == "offline":
        try:
            from server.database.offline import get_offline_db
            offline_db = get_offline_db()

            # Use the clean search_all method from offline.py
            data = offline_db.search_all(q)

            # Transform to search results format
            for p in data["platforms"]:
                results.append({
                    'type': 'platform', 'id': p['id'], 'name': p['name'],
                    'path': [{'type': 'platform', 'id': p['id'], 'name': p['name']}],
                    'pathString': f"/{p['name']}"
                })

            for p in data["projects"]:
                path_str = f"/{p['platform_name']}/{p['name']}" if p.get('platform_name') else f"/{p['name']}"
                results.append({
                    'type': 'project', 'id': p['id'], 'name': p['name'],
                    'path': [], 'pathString': path_str
                })

            for f in data["folders"]:
                path_str = f"/{f['project_name']}/{f['name']}" if f.get('project_name') else f"/{f['name']}"
                results.append({
                    'type': 'folder', 'id': f['id'], 'name': f['name'],
                    'path': [], 'pathString': path_str
                })

            for f in data["files"]:
                if f['sync_status'] == 'local':
                    path_str = f"/Offline Storage/{f['name']}"
                    file_type = 'local-file'
                else:
                    path_str = f"/{f['project_name']}/{f['name']}" if f.get('project_name') else f"/{f['name']}"
                    file_type = 'file'
                results.append({
                    'type': file_type, 'id': f['id'], 'name': f['name'],
                    'path': [], 'pathString': path_str
                })

        except Exception as e:
            pass

        results.sort(key=lambda x: x['pathString'].lower())
        return {
            'query': q,
            'count': len(results),
            'results': results[:100]
        }

    # Online mode: search PostgreSQL + Offline Storage
    search_term = f"%{q.lower()}%"

    # Pre-fetch all data for fast path building (cached in memory)
    platforms_cache = {}
    projects_cache = {}
    folders_cache = {}

    # Load all platforms
    all_platforms = await db.execute(select(LDMPlatform))
    for p in all_platforms.scalars():
        platforms_cache[p.id] = {'id': p.id, 'name': p.name}

    # Load all projects
    all_projects = await db.execute(select(LDMProject))
    for proj in all_projects.scalars():
        projects_cache[proj.id] = {
            'id': proj.id,
            'name': proj.name,
            'platform_id': proj.platform_id
        }

    # Load all folders
    all_folders = await db.execute(select(LDMFolder))
    for f in all_folders.scalars():
        folders_cache[f.id] = {
            'id': f.id,
            'name': f.name,
            'parent_id': f.parent_id,
            'project_id': f.project_id
        }

    def build_folder_path(folder_id: int) -> List[dict]:
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
            current_id = folder['parent_id']

        return path

    def build_full_path(project_id: int, folder_id: int = None) -> List[dict]:
        """Build complete path: platform / project / folders"""
        path = []

        # Add platform if exists
        project = projects_cache.get(project_id)
        if project:
            if project['platform_id']:
                platform = platforms_cache.get(project['platform_id'])
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

    def path_to_string(path: List[dict]) -> str:
        """Convert path to Linux-style string"""
        return '/' + '/'.join(p['name'] for p in path)

    # Search platforms
    matching_platforms = await db.execute(
        select(LDMPlatform).where(LDMPlatform.name.ilike(search_term))
    )
    for p in matching_platforms.scalars():
        path = [{'type': 'platform', 'id': p.id, 'name': p.name}]
        results.append({
            'type': 'platform',
            'id': p.id,
            'name': p.name,
            'path': path,
            'pathString': path_to_string(path)
        })

    # Search projects
    matching_projects = await db.execute(
        select(LDMProject).where(LDMProject.name.ilike(search_term))
    )
    for proj in matching_projects.scalars():
        path = build_full_path(proj.id)
        results.append({
            'type': 'project',
            'id': proj.id,
            'name': proj.name,
            'path': path,
            'pathString': path_to_string(path)
        })

    # Search folders (full recursive)
    matching_folders = await db.execute(
        select(LDMFolder).where(LDMFolder.name.ilike(search_term))
    )
    for folder in matching_folders.scalars():
        path = build_full_path(folder.project_id, folder.id)
        results.append({
            'type': 'folder',
            'id': folder.id,
            'name': folder.name,
            'project_id': folder.project_id,
            'path': path,
            'pathString': path_to_string(path)
        })

    # Search files (full recursive)
    matching_files = await db.execute(
        select(LDMFile).where(LDMFile.name.ilike(search_term))
    )
    for file in matching_files.scalars():
        path = build_full_path(file.project_id, file.folder_id)
        file_entry = {'type': 'file', 'id': file.id, 'name': file.name}
        path.append(file_entry)
        results.append({
            'type': 'file',
            'id': file.id,
            'name': file.name,
            'project_id': file.project_id,
            'folder_id': file.folder_id,
            'path': path,
            'pathString': path_to_string(path)
        })

    # P9: Also search Offline Storage (SQLite local files)
    try:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()

        # Search local files in Offline Storage
        local_files = offline_db.search_local_files(q)
        for f in local_files:
            path = [
                {'type': 'offline-storage', 'id': 0, 'name': 'Offline Storage'},
                {'type': 'local-file', 'id': f['id'], 'name': f['name']}
            ]
            results.append({
                'type': 'local-file',
                'id': f['id'],
                'name': f['name'],
                'path': path,
                'pathString': f"/Offline Storage/{f['name']}"
            })
    except Exception as e:
        # Don't fail search if offline DB unavailable
        pass

    # Sort by path for beautiful grouping
    results.sort(key=lambda x: x['pathString'].lower())

    return {
        'query': q,
        'count': len(results),
        'results': results[:100]  # Max 100 results
    }
