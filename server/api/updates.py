"""
App Updates API
Serve Electron app updates from local server
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pathlib import Path
from loguru import logger
import yaml

router = APIRouter(prefix="/updates", tags=["Updates"])

# Path to store built Electron apps
UPDATES_DIR = Path(__file__).parent.parent.parent / "updates"
UPDATES_DIR.mkdir(exist_ok=True)


@router.get("/latest.yml")
async def get_latest_manifest():
    """
    Serve the latest.yml manifest file for electron-updater

    This file tells the app what version is available and where to download it.
    """
    manifest_path = UPDATES_DIR / "latest.yml"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="No updates available")

    # Return as plain text (YAML)
    with open(manifest_path, 'r') as f:
        content = f.read()

    return Response(content=content, media_type="text/yaml")


@router.get("/download/{filename}")
async def download_installer(filename: str):
    """
    Download the .exe installer or .nupkg update file

    Args:
        filename: Name of the file to download (e.g., "LocaNext-Setup-1.0.0.exe")
    """
    file_path = UPDATES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security: Only allow .exe, .nupkg, .zip files
    if not filename.endswith(('.exe', '.nupkg', '.zip', '.yml')):
        raise HTTPException(status_code=403, detail="Invalid file type")

    logger.info(f"Serving update file: {filename}")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@router.get("/version")
async def get_current_version():
    """
    Get current available version

    Returns:
        dict: Version info including version number and release notes
    """
    manifest_path = UPDATES_DIR / "latest.yml"

    if not manifest_path.exists():
        return {"version": None, "message": "No updates available"}

    with open(manifest_path, 'r') as f:
        data = yaml.safe_load(f)

    return {
        "version": data.get("version"),
        "releaseDate": data.get("releaseDate"),
        "files": [f["url"] for f in data.get("files", [])]
    }


@router.post("/upload")
async def upload_update():
    """
    Upload new update (admin only)

    Future: Implement file upload for admins to push new versions
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")
