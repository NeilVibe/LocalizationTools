"""
Row endpoints - List rows, update row, project tree.

Migrated from api.py lines 660-933
"""

import asyncio
from datetime import datetime
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, text
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.db_utils import is_postgresql
from server.database.models import (
    LDMProject, LDMFile, LDMFolder, LDMRow, LDMEditHistory,
    LDMActiveTM, LDMTranslationMemory
)
from server.tools.ldm.schemas import PaginatedRows, RowResponse, RowUpdate
from server.tools.ldm.websocket import broadcast_cell_update

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================

# P5: Fuzzy search threshold (0.0-1.0, lower = more fuzzy)
FUZZY_SEARCH_THRESHOLD = 0.3


async def _fuzzy_search_rows(
    db: AsyncSession,
    file_id: int,
    search: str,
    fields: list,
    page: int,
    limit: int
) -> tuple:
    """
    Perform fuzzy search using PostgreSQL pg_trgm similarity.

    Uses trigram matching for fuzzy text search with similarity ranking.
    Falls back to ILIKE for SQLite.

    Args:
        db: Async database session
        file_id: File ID to search within
        search: Search term
        fields: List of field names to search (source, target, string_id)
        page: Page number (1-indexed)
        limit: Results per page

    Returns:
        Tuple of (rows, total_count)
    """
    offset = (page - 1) * limit

    if not is_postgresql():
        # SQLite fallback: Use ILIKE (contain mode)
        logger.debug(f"Fuzzy search fallback to ILIKE for SQLite")
        from sqlalchemy import or_

        query = select(LDMRow).where(LDMRow.file_id == file_id)
        field_conditions = []
        search_pattern = f"%{search}%"

        for field in fields:
            column = getattr(LDMRow, field, None)
            if column:
                field_conditions.append(column.ilike(search_pattern))

        if field_conditions:
            query = query.where(or_(*field_conditions))

        # Count
        count_query = select(func.count(LDMRow.id)).where(LDMRow.file_id == file_id)
        if field_conditions:
            count_query = count_query.where(or_(*field_conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Paginated results
        query = query.order_by(LDMRow.row_num).offset(offset).limit(limit)
        result = await db.execute(query)
        rows = result.scalars().all()

        return rows, total

    # PostgreSQL: Use pg_trgm similarity
    logger.debug(f"Fuzzy search using pg_trgm similarity, threshold={FUZZY_SEARCH_THRESHOLD}")

    # Build similarity conditions for each field
    sim_expressions = []
    for field in fields:
        if field == "source":
            sim_expressions.append(f"similarity(lower(source), lower(:search))")
        elif field == "target":
            sim_expressions.append(f"similarity(lower(target), lower(:search))")
        elif field == "string_id":
            sim_expressions.append(f"similarity(lower(string_id), lower(:search))")

    if not sim_expressions:
        sim_expressions = ["similarity(lower(source), lower(:search))"]

    # Use GREATEST to get max similarity across fields
    max_sim = f"GREATEST({', '.join(sim_expressions)})"

    # Count query
    count_sql = text(f"""
        SELECT COUNT(*) FROM ldm_rows
        WHERE file_id = :file_id
        AND {max_sim} >= :threshold
    """)

    count_result = await db.execute(count_sql, {
        "file_id": file_id,
        "search": search,
        "threshold": FUZZY_SEARCH_THRESHOLD
    })
    total = count_result.scalar()

    # Main query - order by similarity DESC
    search_sql = text(f"""
        SELECT id, file_id, row_num, string_id, source, target, status,
               qa_flag_count, updated_at, updated_by,
               {max_sim} as sim_score
        FROM ldm_rows
        WHERE file_id = :file_id
        AND {max_sim} >= :threshold
        ORDER BY sim_score DESC, row_num ASC
        OFFSET :offset LIMIT :limit
    """)

    result = await db.execute(search_sql, {
        "file_id": file_id,
        "search": search,
        "threshold": FUZZY_SEARCH_THRESHOLD,
        "offset": offset,
        "limit": limit
    })

    # Convert raw results to LDMRow-like objects
    raw_rows = result.fetchall()
    rows = []
    for r in raw_rows:
        # Create a simple object with the row data
        row = LDMRow(
            id=r.id,
            file_id=r.file_id,
            row_num=r.row_num,
            string_id=r.string_id,
            source=r.source,
            target=r.target,
            status=r.status,
            qa_flag_count=r.qa_flag_count,
            updated_at=r.updated_at,
            updated_by=r.updated_by
        )
        rows.append(row)

    logger.info(f"Fuzzy search found {len(rows)} rows (total={total}) for '{search}'")
    return rows, total


async def _get_project_linked_tm(db: AsyncSession, project_id: int, user_id: int) -> Optional[int]:
    """
    FEAT-001: Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.
    """
    result = await db.execute(
        select(LDMActiveTM.tm_id)
        .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
        .where(
            LDMActiveTM.project_id == project_id,
            LDMTranslationMemory.owner_id == user_id  # User must own the TM
        )
        .order_by(LDMActiveTM.priority)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _auto_sync_tm_indexes(tm_id: int, user_id: int):
    """
    Background task to auto-sync TM indexes after entry modifications.
    Model2Vec is fast (~29k sentences/sec), so this runs quickly.
    """
    from server.tools.ldm.tm_indexer import TMSyncManager
    from server.utils.progress_tracker import TrackedOperation

    sync_db = next(get_db())
    try:
        tm = sync_db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == user_id
        ).first()

        if not tm:
            logger.warning(f"Auto-sync skipped: TM {tm_id} not found or not owned by user {user_id}")
            return

        with TrackedOperation(
            f"Auto-sync TM: {tm.name}",
            user_id,
            tool_name="LDM",
            function_name="auto_sync_tm",
            silent=True,
            parameters={"tm_id": tm_id, "tm_name": tm.name}
        ) as op:
            sync_manager = TMSyncManager(sync_db, tm_id)
            result = sync_manager.sync()

            tm.status = "ready"
            tm.updated_at = datetime.utcnow()
            sync_db.commit()

            op.update(100, f"Synced: +{result['stats']['insert']} entries")

        logger.info(
            f"Auto-sync TM {tm_id}: INSERT={result['stats']['insert']}, "
            f"UPDATE={result['stats']['update']}, time={result['time_seconds']:.2f}s"
        )
    except Exception as e:
        logger.error(f"Auto-sync failed for TM {tm_id}: {e}")
    finally:
        sync_db.close()


# =============================================================================
# Row Endpoints
# =============================================================================

@router.get("/files/{file_id}/rows", response_model=PaginatedRows)
async def list_rows(
    file_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    search_mode: Optional[str] = Query("contain", description="Search mode: contain, exact, not_contain, fuzzy"),
    search_fields: Optional[str] = Query("source,target", description="Comma-separated fields: string_id, source, target"),
    status: Optional[str] = None,
    filter: Optional[str] = Query(None, description="Filter: all, confirmed, unconfirmed, qa_flagged"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get paginated rows for a file.

    Search Modes:
    - contain: Text contains search term (default, case-insensitive)
    - exact: Exact match only (case-insensitive)
    - not_contain: Exclude rows containing term
    - fuzzy: Trigram similarity search using pg_trgm (ranked by similarity)

    Search Fields:
    - string_id, source, target (comma-separated)

    Filters:
    - all: All rows (default)
    - confirmed: status = 'approved' or 'reviewed'
    - unconfirmed: status = 'pending' or 'translated'
    - qa_flagged: qa_flag_count > 0
    """
    # Verify file access
    result = await db.execute(
        select(LDMFile).options(selectinload(LDMFile.project)).where(
            LDMFile.id == file_id
        )
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # P5: Fuzzy search - use dedicated pg_trgm similarity search
    if search and search_mode == "fuzzy":
        # Parse search fields
        fields = [f.strip() for f in (search_fields or "source,target").split(",")]
        valid_fields = {"string_id", "source", "target"}
        fields = [f for f in fields if f in valid_fields]
        if not fields:
            fields = ["source", "target"]

        # Use dedicated fuzzy search function
        rows, total = await _fuzzy_search_rows(db, file_id, search, fields, page, limit)
        total_pages = (total + limit - 1) // limit

        return PaginatedRows(
            rows=rows,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    # Build query
    query = select(LDMRow).where(LDMRow.file_id == file_id)

    # PERF: Track if we need to run COUNT query or can use cached row_count
    needs_count_query = False

    if search:
        needs_count_query = True
        # Parse search fields
        fields = [f.strip() for f in (search_fields or "source,target").split(",")]
        valid_fields = {"string_id", "source", "target"}
        fields = [f for f in fields if f in valid_fields]
        if not fields:
            fields = ["source", "target"]  # Default fallback

        # Build field conditions based on search mode
        field_conditions = []
        for field in fields:
            column = getattr(LDMRow, field, None)
            if column is None:
                continue

            if search_mode == "exact":
                # Exact match (case-insensitive)
                field_conditions.append(func.lower(column) == func.lower(search))
            elif search_mode == "not_contain":
                # Does not contain (case-insensitive)
                search_pattern = f"%{search}%"
                field_conditions.append(~column.ilike(search_pattern))
            else:  # "contain" (default)
                search_pattern = f"%{search}%"
                field_conditions.append(column.ilike(search_pattern))

        # Combine conditions: OR for contain/exact/fuzzy, AND for not_contain
        if field_conditions:
            if search_mode == "not_contain":
                # For "not contain", ALL fields must not contain the term
                from sqlalchemy import and_
                query = query.where(and_(*field_conditions))
            else:
                # For other modes, ANY field can match
                from sqlalchemy import or_
                query = query.where(or_(*field_conditions))

    if status:
        needs_count_query = True
        query = query.where(LDMRow.status == status)

    # P2: Auto-LQA - Additional filters
    if filter == "confirmed":
        needs_count_query = True
        query = query.where(LDMRow.status.in_(["approved", "reviewed"]))
    elif filter == "unconfirmed":
        needs_count_query = True
        query = query.where(LDMRow.status.in_(["pending", "translated"]))
    elif filter == "qa_flagged":
        needs_count_query = True
        query = query.where(LDMRow.qa_flag_count > 0)

    # PERF: Use cached row_count when no filters, avoid slow COUNT(*) on 500K+ rows
    if needs_count_query:
        count_query = select(func.count(LDMRow.id)).where(LDMRow.file_id == file_id)
        if search:
            # Rebuild same search conditions for count query
            fields = [f.strip() for f in (search_fields or "source,target").split(",")]
            valid_fields = {"string_id", "source", "target"}
            fields = [f for f in fields if f in valid_fields]
            if not fields:
                fields = ["source", "target"]

            field_conditions = []
            for field in fields:
                column = getattr(LDMRow, field, None)
                if column is None:
                    continue
                if search_mode == "exact":
                    field_conditions.append(func.lower(column) == func.lower(search))
                elif search_mode == "not_contain":
                    search_pattern = f"%{search}%"
                    field_conditions.append(~column.ilike(search_pattern))
                else:  # contain (fuzzy handled separately above)
                    search_pattern = f"%{search}%"
                    field_conditions.append(column.ilike(search_pattern))

            if field_conditions:
                if search_mode == "not_contain":
                    from sqlalchemy import and_
                    count_query = count_query.where(and_(*field_conditions))
                else:
                    from sqlalchemy import or_
                    count_query = count_query.where(or_(*field_conditions))
        if status:
            count_query = count_query.where(LDMRow.status == status)
        if filter == "confirmed":
            count_query = count_query.where(LDMRow.status.in_(["approved", "reviewed"]))
        elif filter == "unconfirmed":
            count_query = count_query.where(LDMRow.status.in_(["pending", "translated"]))
        elif filter == "qa_flagged":
            count_query = count_query.where(LDMRow.qa_flag_count > 0)
        total_result = await db.execute(count_query)
        total = total_result.scalar()
    else:
        # PERF: Use cached count - O(1) instead of COUNT(*) on 500K rows
        total = file.row_count

    # Get paginated rows
    offset = (page - 1) * limit
    query = query.order_by(LDMRow.row_num).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    total_pages = (total + limit - 1) // limit

    return PaginatedRows(
        rows=rows,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.put("/rows/{row_id}", response_model=RowResponse)
async def update_row(
    row_id: int,
    update: RowUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Update a row's target text or status (source is READ-ONLY)."""
    # Get row with file and project
    result = await db.execute(
        select(LDMRow).options(
            selectinload(LDMRow.file).selectinload(LDMFile.project)
        ).where(LDMRow.id == row_id)
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if row.file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Save history before update
    old_target = row.target
    old_status = row.status

    # Update row
    if update.target is not None:
        row.target = update.target
        # Auto-set status to translated if target is set and was pending
        if row.status == "pending" and update.target:
            row.status = "translated"

    if update.status is not None:
        row.status = update.status

    row.updated_by = current_user["user_id"]
    row.updated_at = datetime.utcnow()

    # Create edit history
    history = LDMEditHistory(
        row_id=row_id,
        user_id=current_user["user_id"],
        old_target=old_target,
        new_target=row.target,
        old_status=old_status,
        new_status=row.status
    )
    db.add(history)

    await db.commit()
    await db.refresh(row)

    # Broadcast cell update to all viewers (real-time sync)
    try:
        await broadcast_cell_update(
            file_id=row.file_id,
            row_id=row.id,
            row_num=row.row_num,
            target=row.target,
            status=row.status,
            updated_by=current_user["user_id"],
            updated_by_username=current_user["username"]
        )
    except Exception as e:
        # WebSocket broadcast failure shouldn't fail the API call
        logger.warning(f"WebSocket broadcast failed for row {row_id}: {e}")

    # FEAT-001: Auto-add to linked TM if status is 'reviewed'
    tm_updated = False
    if row.status == "reviewed" and row.source and row.target:
        try:
            # Get project's linked TM
            project_id = row.file.project_id
            linked_tm_id = await _get_project_linked_tm(db, project_id, current_user["user_id"])

            if linked_tm_id:
                # Add entry to TM in background thread
                def _add_to_tm():
                    sync_db = next(get_db())
                    try:
                        from server.tools.ldm.tm_manager import TMManager
                        tm_manager = TMManager(sync_db)
                        return tm_manager.add_entry(linked_tm_id, row.source, row.target)
                    finally:
                        sync_db.close()

                result = await asyncio.to_thread(_add_to_tm)

                if result:
                    # Trigger index rebuild in background
                    background_tasks.add_task(
                        _auto_sync_tm_indexes,
                        linked_tm_id,
                        current_user["user_id"]
                    )
                    tm_updated = True
                    logger.info(f"FEAT-001: Auto-added to TM {linked_tm_id}: row_id={row_id}")
        except Exception as e:
            # Don't fail the row update, just log warning
            logger.warning(f"FEAT-001: Auto-add to TM failed: {e}")

    user_id = current_user["user_id"]
    logger.info(f"Row updated: id={row_id}, user={user_id}, tm_updated={tm_updated}")
    return row


# =============================================================================
# Project Tree (Full structure for File Explorer)
# =============================================================================

@router.get("/projects/{project_id}/tree")
async def get_project_tree(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get full project tree structure (folders + files) for File Explorer."""
    # Verify project ownership
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all folders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.project_id == project_id)
    )
    folders = result.scalars().all()

    # Get all files
    result = await db.execute(
        select(LDMFile).where(LDMFile.project_id == project_id)
    )
    files = result.scalars().all()

    # Build lookup dicts for O(n) tree building instead of O(n*m)
    folders_by_parent = defaultdict(list)
    files_by_folder = defaultdict(list)

    for folder in folders:
        folders_by_parent[folder.parent_id].append(folder)
    for file in files:
        files_by_folder[file.folder_id].append(file)

    def build_tree(parent_id=None):
        tree = []

        # Add folders at this level (O(1) lookup)
        for folder in folders_by_parent.get(parent_id, []):
            tree.append({
                "type": "folder",
                "id": folder.id,
                "name": folder.name,
                "children": build_tree(folder.id)
            })

        # Add files at this level (O(1) lookup)
        for file in files_by_folder.get(parent_id, []):
            tree.append({
                "type": "file",
                "id": file.id,
                "name": file.name,
                "format": file.format,
                "row_count": file.row_count
            })

        return tree

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description
        },
        "tree": build_tree(None)
    }
