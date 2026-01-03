"""
DB-002: Auto-rename helper for duplicate names.

When creating or pasting a file with a duplicate name, automatically
generates a unique name with suffix: test.txt -> test_1.txt -> test_2.txt

Like Windows Explorer behavior.
"""

import re
from typing import Type, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.database.models import LDMProject, LDMFolder, LDMFile


async def generate_unique_name(
    db: AsyncSession,
    model_class: Type,
    requested_name: str,
    project_id: Optional[int] = None,
    platform_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    exclude_id: Optional[int] = None,
) -> str:
    """
    Generate unique name with auto-numbering if duplicate exists.

    Args:
        db: Database session
        model_class: LDMProject, LDMFolder, or LDMFile
        requested_name: The name user wants
        project_id: For folders/files - the project scope
        platform_id: For projects - the platform scope
        parent_id: For folders - the parent folder (can be None for root)
        folder_id: For files - the folder (can be None for root)
        exclude_id: ID to exclude from check (for rename operations)

    Returns:
        Original name if available, or name with _N suffix

    Example:
        test.txt -> test.txt (if available)
        test.txt -> test_1.txt (if test.txt exists)
        test.txt -> test_2.txt (if test.txt and test_1.txt exist)
    """

    # Extract base name and extension
    if '.' in requested_name and not requested_name.startswith('.'):
        base_name, ext = requested_name.rsplit('.', 1)
        ext = f".{ext}"
    else:
        base_name = requested_name
        ext = ""

    # Build query based on model type
    if model_class == LDMProject:
        query = select(model_class.name).where(model_class.platform_id == platform_id)
    elif model_class == LDMFolder:
        query = select(model_class.name).where(
            model_class.project_id == project_id,
            model_class.parent_id == parent_id
        )
    elif model_class == LDMFile:
        query = select(model_class.name).where(
            model_class.project_id == project_id,
            model_class.folder_id == folder_id
        )
    else:
        raise ValueError(f"Unsupported model class: {model_class}")

    # Exclude self if renaming
    if exclude_id:
        query = query.where(model_class.id != exclude_id)

    result = await db.execute(query)
    existing_names = set(row[0] for row in result.fetchall())

    # If name is available, return it
    if requested_name not in existing_names:
        return requested_name

    # Find highest existing number suffix
    # Pattern: base_name + optional _N + extension
    # Examples: test_1.txt, test_2.txt, report_3, etc.
    escaped_base = re.escape(base_name)
    escaped_ext = re.escape(ext)
    pattern = re.compile(rf"^{escaped_base}_(\d+){escaped_ext}$")

    numbers = []
    for name in existing_names:
        match = pattern.match(name)
        if match:
            numbers.append(int(match.group(1)))

    # Generate next number
    next_num = max(numbers) + 1 if numbers else 1

    return f"{base_name}_{next_num}{ext}"


async def check_name_exists(
    db: AsyncSession,
    model_class: Type,
    name: str,
    project_id: Optional[int] = None,
    platform_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Check if a name already exists in the given scope.

    Returns True if name exists (duplicate), False if available.
    """

    if model_class == LDMProject:
        query = select(model_class.id).where(
            model_class.platform_id == platform_id,
            model_class.name == name
        )
    elif model_class == LDMFolder:
        query = select(model_class.id).where(
            model_class.project_id == project_id,
            model_class.parent_id == parent_id,
            model_class.name == name
        )
    elif model_class == LDMFile:
        query = select(model_class.id).where(
            model_class.project_id == project_id,
            model_class.folder_id == folder_id,
            model_class.name == name
        )
    else:
        raise ValueError(f"Unsupported model class: {model_class}")

    # Exclude self if renaming
    if exclude_id:
        query = query.where(model_class.id != exclude_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None
