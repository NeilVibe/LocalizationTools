"""
XLSTransfer API Endpoints (Async)
Exposes XLSTransfer operations via REST API for testing without GUI
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import os
import sys
import json
import time
import httpx
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import User, ActiveOperation
from server.utils.websocket import emit_operation_start, emit_progress_update, emit_operation_complete, emit_operation_failed
from loguru import logger

router = APIRouter(prefix="/api/v2/xlstransfer", tags=["XLSTransfer"])

# Import XLSTransfer modules
try:
    from client.tools.xls_transfer import core, embeddings, translation, process_operation
    logger.success("XLSTransfer modules loaded successfully", {
        "core": core is not None,
        "embeddings": embeddings is not None,
        "translation": translation is not None,
        "process_operation": process_operation is not None
    })
except ImportError as e:
    logger.error(f"Failed to import XLSTransfer modules: {e}")
    core = None
    embeddings = None
    translation = None
    process_operation = None


@router.get("/health")
async def xlstransfer_health():
    """Check if XLSTransfer modules are loaded"""
    logger.info("XLSTransfer health check requested")

    status = {
        "status": "ok" if core is not None else "error",
        "modules_loaded": {
            "core": core is not None,
            "embeddings": embeddings is not None,
            "translation": translation is not None
        }
    }

    logger.info("XLSTransfer health check result", status)
    return status


def run_create_dictionary_background(
    operation_id: int,
    user_id: int,
    username: str,
    excel_files: list,
    file_paths: list
):
    """
    Background task to create dictionary without blocking the server.
    This runs in a thread pool, keeping the FastAPI event loop free.
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    import server.config as config

    try:
        logger.info(f"Background task started for operation {operation_id}")

        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Create dictionaries (ProgressTracker handles progress updates)
        split_dict, whole_dict, split_embeddings, whole_embeddings = embeddings.process_excel_for_dictionary(
            excel_files=excel_files,
            progress_tracker=None  # TODO: Pass operation_id when process_operation supports it
        )

        logger.info("Dictionaries created, saving to disk", {
            "split_pairs": len(split_dict),
            "whole_pairs": len(whole_dict)
        })

        # Save dictionaries to disk
        embeddings.save_dictionary(
            embeddings=split_embeddings,
            translation_dict=split_dict,
            mode="split"
        )

        if whole_dict and len(whole_embeddings) > 0:
            embeddings.save_dictionary(
                embeddings=whole_embeddings,
                translation_dict=whole_dict,
                mode="whole"
            )

        # Restore directory
        os.chdir(original_cwd)

        # Update database with final status
        engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})
        db_session = Session(engine)

        try:
            operation = db_session.query(ActiveOperation).filter(ActiveOperation.operation_id == operation_id).first()

            operation.status = "completed"
            operation.progress_percentage = 100.0
            operation.completed_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            db_session.commit()

            # Emit WebSocket completion event
            asyncio.run(emit_operation_complete({
                'operation_id': operation_id,
                'user_id': user_id,
                'username': username,
                'tool_name': 'XLSTransfer',
                'function_name': 'create_dictionary',
                'operation_name': operation.operation_name,
                'status': 'completed',
                'progress_percentage': 100.0,
                'started_at': operation.started_at.isoformat(),
                'completed_at': operation.completed_at.isoformat()
            }))

            logger.success(f"Dictionary creation completed for operation {operation_id}", {
                "split_pairs": len(split_dict),
                "whole_pairs": len(whole_dict),
                "files_processed": len(file_paths)
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Background dictionary creation failed: {str(e)}", {
            "operation_id": operation_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        # Update database with failed status
        try:
            engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})
            db_session = Session(engine)

            operation = db_session.query(ActiveOperation).filter(ActiveOperation.operation_id == operation_id).first()
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            db_session.commit()

            # Emit WebSocket failure event
            asyncio.run(emit_operation_failed({
                'operation_id': operation_id,
                'user_id': user_id,
                'username': username,
                'tool_name': 'XLSTransfer',
                'function_name': 'create_dictionary',
                'operation_name': operation.operation_name if operation else "Create Dictionary",
                'status': 'failed',
                'error_message': str(e),
                'started_at': operation.started_at.isoformat() if operation and operation.started_at else None,
                'completed_at': operation.completed_at.isoformat() if operation and operation.completed_at else None
            }))

            db_session.close()
        except Exception as db_error:
            logger.error(f"Failed to update operation status: {db_error}")


@router.post("/test/create-dictionary")
async def test_create_dictionary(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    kr_column: str = Form("A"),
    translation_column: str = Form("B"),
    sheet_name: Optional[str] = Form(None),
    selections: Optional[str] = Form(None),  # JSON string of sheet/column selections
    current_user: dict = Depends(get_current_active_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Test dictionary creation with uploaded Excel files

    This simulates the "Create dictionary" button
    Supports both simple mode (kr_column, translation_column) and advanced mode (selections)
    """
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")
    user_id = current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", None)

    logger.info(f"Dictionary creation started by user: {username}", {
        "user": username,
        "files_count": len(files),
        "kr_column": kr_column,
        "translation_column": translation_column,
        "sheet_name": sheet_name
    })

    # Create ActiveOperation record for progress tracking
    operation = ActiveOperation(
        user_id=user_id,
        username=username,
        tool_name="XLSTransfer",
        function_name="create_dictionary",
        operation_name=f"Create Dictionary ({len(files)} file{'s' if len(files) > 1 else ''})",
        status="running",
        progress_percentage=0.0,
        completed_steps=0,
        file_info={"files": [f.filename for f in files]},
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    operation_id = operation.operation_id
    logger.success(f"Created ActiveOperation record: ID={operation_id}")

    # Emit WebSocket event for operation start
    await emit_operation_start({
        'operation_id': operation_id,
        'user_id': user_id,
        'username': username,
        'tool_name': 'XLSTransfer',
        'function_name': 'create_dictionary',
        'operation_name': operation.operation_name,
        'status': 'running',
        'progress_percentage': 0.0,
        'started_at': operation.started_at.isoformat()
    })

    if core is None:
        logger.error("XLSTransfer core module not loaded - cannot create dictionary")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    # Save uploaded files to temp directory
    temp_dir = Path("/tmp/xlstransfer_test")
    temp_dir.mkdir(exist_ok=True)

    logger.info(f"Saving {len(files)} uploaded files to temp directory", {"temp_dir": str(temp_dir)})

    file_paths = []
    for i, file in enumerate(files, 1):
        file_path = temp_dir / file.filename
        file_size = 0
        with open(file_path, "wb") as f:
            content = await file.read()
            file_size = len(content)
            f.write(content)
        file_paths.append(str(file_path))

        logger.info(f"Saved file {i}/{len(files)}: {file.filename}", {
            "filename": file.filename,
            "size_bytes": file_size,
            "path": str(file_path)
        })

    try:
        # Prepare file list for processing (file_path, sheet_name, kr_column, trans_column)
        excel_files = []

        if selections:
            # Advanced mode: Use selections from Upload Settings Modal
            logger.info("Using advanced mode with selections", {
                "file_count": len(file_paths)
            })

            selections_dict = json.loads(selections)
            # selections format: {"filename1.xlsx": {"Sheet1": {"kr_column": "A", "trans_column": "B"}}}

            # Map filenames to saved paths
            filename_to_path = {os.path.basename(fp): fp for fp in file_paths}

            for filename, sheets in selections_dict.items():
                if filename in filename_to_path:
                    file_path = filename_to_path[filename]
                    for sheet_name, columns in sheets.items():
                        excel_files.append((
                            file_path,
                            sheet_name,
                            columns['kr_column'],
                            columns['trans_column']
                        ))
                        logger.info(f"Added selection: {filename} - {sheet_name}", {
                            "kr_column": columns['kr_column'],
                            "trans_column": columns['trans_column']
                        })
        else:
            # Simple mode: Use default columns for all files
            logger.info("Using simple mode with default columns", {
                "file_count": len(file_paths),
                "kr_column": kr_column,
                "translation_column": translation_column
            })

            for file_path in file_paths:
                excel_files.append((file_path, sheet_name or "Sheet1", kr_column, translation_column))

        logger.info("Queuing dictionary creation as background task", {
            "excel_files_count": len(excel_files),
            "mode": "advanced" if selections else "simple",
            "operation_id": operation_id
        })

        # Add background task to run dictionary creation without blocking
        background_tasks.add_task(
            run_create_dictionary_background,
            operation_id=operation_id,
            user_id=user_id,
            username=username,
            excel_files=excel_files,
            file_paths=file_paths
        )

        logger.success(f"Dictionary creation queued as operation {operation_id}")

        # Return immediately with 202 Accepted (operation in progress)
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "message": "Dictionary creation started",
                "operation_id": operation_id,
                "operation_name": operation.operation_name,
                "files_count": len(files),
                "excel_files_count": len(excel_files),
                "status": "running",
                "note": "Check /api/progress/operations/{operation_id} for real-time progress"
            }
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Dictionary creation failed after {elapsed_time:.2f}s: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })

        # Mark operation as failed
        try:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(operation)

            # Emit WebSocket event for operation failure
            await emit_operation_failed({
                'operation_id': operation_id,
                'user_id': user_id,
                'username': username,
                'tool_name': 'XLSTransfer',
                'function_name': 'create_dictionary',
                'operation_name': operation.operation_name,
                'status': 'failed',
                'error_message': str(e),
                'started_at': operation.started_at.isoformat(),
                'completed_at': operation.completed_at.isoformat()
            })
        except Exception as db_error:
            logger.error(f"Failed to update operation status: {db_error}")

        raise HTTPException(status_code=500, detail=f"Dictionary creation failed: {str(e)}")


@router.post("/test/load-dictionary")
async def test_load_dictionary(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Test loading existing dictionary

    This simulates the "Load dictionary" button
    """
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"Dictionary load requested by user: {username}", {"user": username})

    if embeddings is None:
        logger.error("XLSTransfer embeddings module not loaded - cannot load dictionary")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    try:
        logger.info("Loading dictionary files from disk")

        # Load split dictionary (primary mode)
        split_embeddings, split_dict, split_index, split_kr_texts = embeddings.load_dictionary(mode="split")

        logger.info("Split dictionary loaded", {
            "split_pairs": len(split_dict)
        })

        # Try to load whole dictionary if it exists
        whole_pairs = 0
        try:
            if embeddings.check_dictionary_exists(mode="whole"):
                whole_embeddings, whole_dict, whole_index, whole_kr_texts = embeddings.load_dictionary(mode="whole")
                whole_pairs = len(whole_dict)
                logger.info("Whole dictionary loaded", {"whole_pairs": whole_pairs})
        except Exception:
            logger.info("No whole dictionary found, using split only")

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "message": "Dictionary loaded successfully",
            "split_pairs": len(split_dict),
            "whole_pairs": whole_pairs,
            "total_pairs": len(split_dict) + whole_pairs,
            "elapsed_time": elapsed_time
        }

        logger.success(f"Dictionary loaded in {elapsed_time:.2f}s", {
            "user": username,
            "split_pairs": len(split_dict),
            "whole_pairs": whole_pairs,
            "elapsed_time": elapsed_time
        })

        return response

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Dictionary load failed after {elapsed_time:.2f}s: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })
        raise HTTPException(status_code=500, detail=f"Dictionary load failed: {str(e)}")


@router.post("/test/translate-text")
async def test_translate_text(
    text: str = Form(...),
    threshold: float = Form(0.99),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Test text translation

    This simulates translating a single text entry
    """
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"Text translation requested by user: {username}", {
        "user": username,
        "text_length": len(text),
        "threshold": threshold,
        "text_preview": text[:50] + "..." if len(text) > 50 else text
    })

    if translation is None:
        logger.error("XLSTransfer translation module not loaded - cannot translate")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    try:
        logger.info("Loading dictionary for translation")

        # Load split dictionary (primary mode)
        split_embeddings, split_dict, split_index, split_kr_texts = embeddings.load_dictionary(mode="split")

        logger.info("Translating text using find_best_match", {
            "dictionary_size": len(split_dict),
            "text_preview": text[:50] + "..." if len(text) > 50 else text
        })

        # Find best match using backend function
        matched_korean, translated_text, similarity_score = translation.find_best_match(
            text=text,
            faiss_index=split_index,
            kr_sentences=split_kr_texts,
            translation_dict=split_dict,
            threshold=threshold,
            model=None  # Will use default model
        )

        match_found = bool(matched_korean and translated_text)

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "original_text": text,
            "matched_korean": matched_korean,
            "translated_text": translated_text if match_found else text,
            "confidence": similarity_score,
            "match_found": match_found,
            "elapsed_time": elapsed_time
        }

        logger.success(f"Text translated in {elapsed_time:.3f}s", {
            "user": username,
            "match_found": match_found,
            "confidence": similarity_score,
            "elapsed_time": elapsed_time
        })

        return response

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Text translation failed after {elapsed_time:.3f}s: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/test/translate-file")
async def test_translate_file(
    file: UploadFile = File(...),
    file_type: str = Form("txt"),  # "txt" or "excel"
    threshold: float = Form(0.99),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Test file translation (txt or Excel)

    This simulates "Transfer to Close" (txt) or "Transfer to Excel"
    """
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"File translation requested by user: {username}", {
        "user": username,
        "filename": file.filename,
        "file_type": file_type,
        "threshold": threshold
    })

    if translation is None:
        logger.error("XLSTransfer translation module not loaded - cannot translate file")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    # Save uploaded file
    temp_dir = Path("/tmp/xlstransfer_test")
    temp_dir.mkdir(exist_ok=True)

    input_path = temp_dir / file.filename
    file_size = 0
    with open(input_path, "wb") as f:
        content = await file.read()
        file_size = len(content)
        f.write(content)

    logger.info(f"File uploaded and saved: {file.filename}", {
        "size_bytes": file_size,
        "path": str(input_path)
    })

    try:
        if file_type == "txt":
            logger.info(f"Translating .txt file: {file.filename}")

            # Load dictionary
            split_embeddings, split_dict, split_index, split_kr_texts = embeddings.load_dictionary(mode="split")

            # Read txt file line by line
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Translate each line
            translated_lines = []
            matches_found = 0

            for line in lines:
                if not line.strip():
                    translated_lines.append(line)
                    continue

                # Find best match
                matched_korean, translated_text, confidence = translation.find_best_match(
                    text=line.strip(),
                    faiss_index=split_index,
                    kr_sentences=split_kr_texts,
                    translation_dict=split_dict,
                    threshold=threshold,
                    model=None
                )

                if matched_korean and translated_text:
                    translated_lines.append(translated_text + '\n')
                    matches_found += 1
                else:
                    translated_lines.append(line)

            # Write output file
            output_path = temp_dir / f"{Path(file.filename).stem}_translated.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(translated_lines)

            elapsed_time = time.time() - start_time

            response = {
                "success": True,
                "input_file": file.filename,
                "output_file": str(output_path),
                "lines_translated": len(lines),
                "matches_found": matches_found,
                "elapsed_time": elapsed_time
            }

        else:
            logger.info(f"Translating Excel file: {file.filename}")

            # For Excel, we need to use process_operation.translate_excel()
            # This requires a specific "selections" format
            # For testing, we'll use a simplified approach: translate column A to column B in Sheet1

            selections = {
                str(input_path): {
                    "Sheet1": {
                        "kr_column": "A",
                        "trans_column": "B"
                    }
                }
            }

            # Call backend function
            result = process_operation.translate_excel(selections, threshold)

            elapsed_time = time.time() - start_time

            if result.get("success"):
                output_path = f"{str(input_path).rsplit('.', 1)[0]}_translated.xlsx"
                response = {
                    "success": True,
                    "input_file": file.filename,
                    "output_file": output_path,
                    "message": result.get("message", ""),
                    "elapsed_time": elapsed_time
                }
            else:
                raise Exception(result.get("error", "Unknown error"))

        logger.success(f"File translation completed in {elapsed_time:.2f}s", {
            "user": username,
            "filename": file.filename,
            "file_type": file_type,
            "elapsed_time": elapsed_time
        })

        return response

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"File translation failed after {elapsed_time:.2f}s: {str(e)}", {
            "user": username,
            "filename": file.filename,
            "file_type": file_type,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })
        raise HTTPException(status_code=500, detail=f"File translation failed: {str(e)}")


def run_translate_excel_background(
    operation_id: int,
    user_id: int,
    username: str,
    path_selections: dict,
    threshold: float
):
    """
    Background task to run Excel translation without blocking the server.
    This runs in a thread pool, keeping the FastAPI event loop free.
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    import server.config as config

    try:
        logger.info(f"Background task started for operation {operation_id}")

        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Run the translation (ProgressTracker handles progress updates)
        result = process_operation.translate_excel(path_selections, threshold, operation_id)

        # Restore directory
        os.chdir(original_cwd)

        # Update database with final status
        engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})
        db_session = Session(engine)

        try:
            operation = db_session.query(ActiveOperation).filter(ActiveOperation.operation_id == operation_id).first()

            if result.get("success"):
                operation.status = "completed"
                operation.progress_percentage = 100.0
                operation.completed_at = datetime.utcnow()
                operation.updated_at = datetime.utcnow()
                db_session.commit()

                logger.success(f"Operation {operation_id} completed successfully")

                # Emit WebSocket completion event
                asyncio.run(emit_operation_complete({
                    'operation_id': operation_id,
                    'user_id': user_id,
                    'username': username,
                    'tool_name': 'XLSTransfer',
                    'function_name': 'translate_excel',
                    'operation_name': operation.operation_name,
                    'status': 'completed',
                    'progress_percentage': 100.0,
                    'started_at': operation.started_at.isoformat(),
                    'completed_at': operation.completed_at.isoformat()
                }))
            else:
                operation.status = "failed"
                operation.error_message = result.get("error", "Unknown error")
                operation.completed_at = datetime.utcnow()
                operation.updated_at = datetime.utcnow()
                db_session.commit()

                logger.error(f"Operation {operation_id} failed: {operation.error_message}")

                # Emit WebSocket failure event
                asyncio.run(emit_operation_failed({
                    'operation_id': operation_id,
                    'user_id': user_id,
                    'username': username,
                    'tool_name': 'XLSTransfer',
                    'function_name': 'translate_excel',
                    'operation_name': operation.operation_name,
                    'status': 'failed',
                    'error_message': operation.error_message,
                    'started_at': operation.started_at.isoformat(),
                    'completed_at': operation.completed_at.isoformat()
                }))

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Background task failed for operation {operation_id}: {e}", exc_info=True)

        # Try to mark as failed in database
        try:
            engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})
            db_session = Session(engine)
            operation = db_session.query(ActiveOperation).filter(ActiveOperation.operation_id == operation_id).first()
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            db_session.commit()
            db_session.close()
        except:
            pass


@router.post("/test/translate-excel")
async def test_translate_excel(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    selections: str = Form(...),  # JSON string of sheet/column selections
    threshold: float = Form(0.99),
    current_user: dict = Depends(get_current_active_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Translate Excel files with sheet/column selections

    This simulates "Transfer to Excel" with Upload Settings Modal
    Accepts multiple files and translates specified sheets/columns
    Returns translated Excel file for download
    """
    from fastapi.responses import FileResponse

    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")
    user_id = current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", None)

    logger.info(f"Excel translation requested by user: {username}", {
        "user": username,
        "files_count": len(files),
        "threshold": threshold
    })

    # Create ActiveOperation record for progress tracking
    operation = ActiveOperation(
        user_id=user_id,
        username=username,
        tool_name="XLSTransfer",
        function_name="translate_excel",
        operation_name=f"Transfer to Excel ({len(files)} file{'s' if len(files) > 1 else ''})",
        status="running",
        progress_percentage=0.0,
        completed_steps=0,
        file_info={"files": [f.filename for f in files], "threshold": threshold},
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    operation_id = operation.operation_id
    logger.success(f"Created ActiveOperation record: ID={operation_id}")

    # Emit WebSocket event for operation start
    await emit_operation_start({
        'operation_id': operation_id,
        'user_id': user_id,
        'username': username,
        'tool_name': 'XLSTransfer',
        'function_name': 'translate_excel',
        'operation_name': operation.operation_name,
        'status': 'running',
        'progress_percentage': 0.0,
        'started_at': operation.started_at.isoformat()
    })

    if process_operation is None or embeddings is None:
        logger.error("XLSTransfer modules not loaded - cannot translate Excel")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    # Save uploaded files to temp directory
    temp_dir = Path("/tmp/xlstransfer_test")
    temp_dir.mkdir(exist_ok=True)

    logger.info(f"Saving {len(files)} uploaded files to temp directory", {"temp_dir": str(temp_dir)})

    file_paths = []
    for i, file in enumerate(files, 1):
        file_path = temp_dir / file.filename
        file_size = 0
        with open(file_path, "wb") as f:
            content = await file.read()
            file_size = len(content)
            f.write(content)
        file_paths.append(str(file_path))

        logger.info(f"Saved file {i}/{len(files)}: {file.filename}", {
            "filename": file.filename,
            "size_bytes": file_size,
            "path": str(file_path)
        })

    try:
        # Parse selections
        logger.info("Parsing selections for Excel translation")
        selections_dict = json.loads(selections)

        # Map filenames to saved paths for selections
        filename_to_path = {os.path.basename(fp): fp for fp in file_paths}

        # Build selections with full file paths
        path_selections = {}
        for filename, sheets in selections_dict.items():
            if filename in filename_to_path:
                file_path = filename_to_path[filename]
                path_selections[file_path] = sheets

                logger.info(f"Processing selections for: {filename}", {
                    "file_path": file_path,
                    "sheets": list(sheets.keys())
                })

        logger.info("Loading dictionary for translation")

        # Load dictionary (required for translation)
        try:
            split_embeddings, split_dict, split_index, split_kr_texts = embeddings.load_dictionary(mode="split")
            logger.info("Dictionary loaded successfully", {
                "split_pairs": len(split_dict)
            })
        except Exception as e:
            logger.error(f"Failed to load dictionary: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Dictionary not loaded. Please load or create a dictionary first."
            )

        logger.info("Starting Excel translation with process_operation.translate_excel", {
            "selections_count": len(path_selections),
            "threshold": threshold
        })

        # Add background task to run translation without blocking
        background_tasks.add_task(
            run_translate_excel_background,
            operation_id=operation_id,
            user_id=user_id,
            username=username,
            path_selections=path_selections,
            threshold=threshold
        )

        logger.success(f"Excel translation queued as operation {operation_id}")

        # Return immediately with 202 Accepted (operation in progress)
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "message": "Translation started",
                "operation_id": operation_id,
                "operation_name": operation.operation_name,
                "files_count": len(files),
                "status": "running",
                "note": "Check /api/progress/operations/{operation_id} for real-time progress"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Excel translation failed during setup: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })

        # Mark operation as failed
        try:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            await db.commit()

            await emit_operation_failed({
                'operation_id': operation_id,
                'user_id': user_id,
                'username': username,
                'tool_name': 'XLSTransfer',
                'function_name': 'translate_excel',
                'operation_name': operation.operation_name,
                'status': 'failed',
                'error_message': str(e),
                'started_at': operation.started_at.isoformat() if operation.started_at else None
            })
        except:
            pass

        raise HTTPException(status_code=500, detail=f"Failed to start translation: {str(e)}")


@router.get("/test/status")
async def test_status(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get current XLSTransfer test environment status
    """
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"XLSTransfer status requested by user: {username}", {"user": username})

    temp_dir = Path("/tmp/xlstransfer_test")
    test_files = list(temp_dir.glob("*")) if temp_dir.exists() else []

    status = {
        "temp_directory": str(temp_dir),
        "temp_exists": temp_dir.exists(),
        "dictionary_loaded": False,  # TODO: Check actual status
        "model_available": embeddings is not None,
        "test_files": [str(f) for f in test_files],
        "test_files_count": len(test_files)
    }

    logger.info("XLSTransfer status retrieved", {
        "user": username,
        "temp_exists": temp_dir.exists(),
        "model_available": embeddings is not None,
        "test_files_count": len(test_files)
    })

    return status


@router.post("/test/get-sheets")
async def test_get_sheets(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get sheet names from an uploaded Excel file

    This is for the Upload Settings Modal in browser mode
    """
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"Get sheets requested by user: {username}", {
        "user": username,
        "filename": file.filename
    })

    if core is None:
        logger.error("XLSTransfer core module not loaded")
        raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

    # Save uploaded file temporarily
    temp_dir = Path("/tmp/xlstransfer_test")
    temp_dir.mkdir(exist_ok=True)

    file_path = temp_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"File saved temporarily: {file.filename}", {
        "path": str(file_path),
        "size_bytes": len(content)
    })

    try:
        # Get sheet names using openpyxl
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheets = wb.sheetnames
        wb.close()

        logger.success(f"Retrieved {len(sheets)} sheets from {file.filename}", {
            "filename": file.filename,
            "sheet_count": len(sheets),
            "sheets": sheets
        })

        response_data = {
            "success": True,
            "filename": file.filename,
            "sheets": sheets
        }

        logger.info(f"RESPONSE being sent to frontend: {response_data}")

        return response_data

    except Exception as e:
        logger.error(f"Failed to get sheets from {file.filename}: {str(e)}", {
            "filename": file.filename,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail=f"Failed to read Excel file: {str(e)}")
