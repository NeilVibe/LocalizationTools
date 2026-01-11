"""Repository interfaces - abstract base classes."""

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.repositories.interfaces.file_repository import FileRepository
from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.interfaces.project_repository import ProjectRepository
from server.repositories.interfaces.folder_repository import FolderRepository
from server.repositories.interfaces.platform_repository import PlatformRepository

__all__ = ["TMRepository", "AssignmentTarget", "FileRepository", "RowRepository", "ProjectRepository", "FolderRepository", "PlatformRepository"]
