"""
Sync to Central endpoints - Offline to online synchronization.

Migrated from api.py lines 2786-3042
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import (
    LDMProject, LDMFile, LDMRow,
    LDMTranslationMemory, LDMTMEntry
)
from server.tools.ldm.schemas import (
    SyncFileToCentralRequest, SyncFileToCentralResponse,
    SyncTMToCentralRequest, SyncTMToCentralResponse
)

router = APIRouter(tags=["LDM"])


@router.post("/sync-to-central", response_model=SyncFileToCentralResponse)
async def sync_file_to_central(
    request: SyncFileToCentralRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Sync a file from local SQLite to central PostgreSQL.

    This endpoint:
    1. Reads file metadata + all rows from local SQLite
    2. Creates new file record in PostgreSQL (destination project)
    3. Bulk inserts all rows to PostgreSQL
    4. Returns the new file_id in central DB

    Use this when:
    - User worked offline (SQLite mode)
    - User reconnected (went online)
    - User wants to upload local work to central server

    The file data is passed as JSON (not re-read from disk).
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"Sync to central: file_id={request.file_id}, dest_project={request.destination_project_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Verify destination project exists and user has access
    project_result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == request.destination_project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Destination project not found or access denied")

    # Read from local SQLite database
    # The SQLite file is at server/data/locanext.db
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data", "locanext.db"
    )

    if not os.path.exists(sqlite_path):
        raise HTTPException(
            status_code=400,
            detail="No local database found. You may not have worked offline."
        )

    try:
        # Create SQLite engine and session
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        sqlite_session = Session(sqlite_engine)

        try:
            # Read the file from SQLite
            local_file = sqlite_session.query(LDMFile).filter(LDMFile.id == request.file_id).first()

            if not local_file:
                raise HTTPException(status_code=404, detail="File not found in local database")

            # Read all rows for this file from SQLite
            local_rows = sqlite_session.query(LDMRow).filter(
                LDMRow.file_id == request.file_id
            ).order_by(LDMRow.row_num).all()

            logger.info(f"Read {len(local_rows)} rows from local SQLite for file {request.file_id}")

            # Create new file in PostgreSQL
            new_file = LDMFile(
                project_id=request.destination_project_id,
                folder_id=None,  # Goes to project root
                name=local_file.name,
                original_filename=local_file.original_filename,
                format=local_file.format,
                row_count=len(local_rows),
                source_language=local_file.source_language,
                target_language=local_file.target_language,
                extra_data=local_file.extra_data,
                created_by=current_user["user_id"]
            )
            db.add(new_file)
            await db.flush()

            # Create rows in PostgreSQL
            for local_row in local_rows:
                new_row = LDMRow(
                    file_id=new_file.id,
                    row_num=local_row.row_num,
                    string_id=local_row.string_id,
                    source=local_row.source,
                    target=local_row.target,
                    status=local_row.status,
                    extra_data=local_row.extra_data
                )
                db.add(new_row)

            await db.commit()

            logger.success(f"Synced file to central: local_id={request.file_id} → central_id={new_file.id}, rows={len(local_rows)}")

            return SyncFileToCentralResponse(
                success=True,
                new_file_id=new_file.id,
                rows_synced=len(local_rows),
                message=f"Successfully synced {len(local_rows)} rows to central server"
            )

        finally:
            sqlite_session.close()
            sqlite_engine.dispose()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sync failed. Check server logs.")


@router.post("/tm/sync-to-central", response_model=SyncTMToCentralResponse)
async def sync_tm_to_central(
    request: SyncTMToCentralRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Sync a Translation Memory from local SQLite to central PostgreSQL.

    This endpoint:
    1. Reads TM metadata + all entries from local SQLite
    2. Creates new TM record in PostgreSQL
    3. Bulk inserts all entries to PostgreSQL
    4. Returns the new tm_id in central DB
    """
    from server.config import ACTIVE_DATABASE_TYPE

    logger.info(f"Sync TM to central: tm_id={request.tm_id}")

    # Verify we're online (connected to PostgreSQL)
    if ACTIVE_DATABASE_TYPE != "postgresql":
        raise HTTPException(
            status_code=400,
            detail="Cannot sync to central server while in offline mode. Connect to server first."
        )

    # Read from local SQLite database
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data", "locanext.db"
    )

    if not os.path.exists(sqlite_path):
        raise HTTPException(
            status_code=400,
            detail="No local database found. You may not have worked offline."
        )

    try:
        # Create SQLite engine and session
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        sqlite_session = Session(sqlite_engine)

        try:
            # Read the TM from SQLite
            local_tm = sqlite_session.query(LDMTranslationMemory).filter(
                LDMTranslationMemory.id == request.tm_id
            ).first()

            if not local_tm:
                raise HTTPException(status_code=404, detail="Translation Memory not found in local database")

            # Read all entries for this TM from SQLite
            local_entries = sqlite_session.query(LDMTMEntry).filter(
                LDMTMEntry.tm_id == request.tm_id
            ).all()

            logger.info(f"Read {len(local_entries)} entries from local SQLite for TM {request.tm_id}")

            # Create new TM in PostgreSQL
            new_tm = LDMTranslationMemory(
                name=local_tm.name,
                description=local_tm.description,
                owner_id=current_user["user_id"],
                source_lang=local_tm.source_lang,
                target_lang=local_tm.target_lang,
                entry_count=len(local_entries),
                status="pending"  # Will need re-indexing on server
            )
            db.add(new_tm)
            await db.flush()

            # Bulk insert entries to PostgreSQL
            for local_entry in local_entries:
                new_entry = LDMTMEntry(
                    tm_id=new_tm.id,
                    source_text=local_entry.source_text,
                    target_text=local_entry.target_text,
                    source_hash=local_entry.source_hash,
                    created_by=local_entry.created_by,
                    change_date=local_entry.change_date
                )
                db.add(new_entry)

            await db.commit()

            logger.success(f"Synced TM to central: local_id={request.tm_id} → central_id={new_tm.id}, entries={len(local_entries)}")

            return SyncTMToCentralResponse(
                success=True,
                new_tm_id=new_tm.id,
                entries_synced=len(local_entries),
                message=f"Successfully synced {len(local_entries)} TM entries to central server. Run 'Build Indexes' on the server to enable semantic search."
            )

        finally:
            sqlite_session.close()
            sqlite_engine.dispose()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TM sync to central failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM sync failed. Check server logs.")
