"""
XLSTransfer API Endpoints (Async)
Exposes XLSTransfer operations via REST API for testing without GUI
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import os
import sys
import json
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import User
from loguru import logger

router = APIRouter(prefix="/api/v2/xlstransfer", tags=["XLSTransfer"])

# Import XLSTransfer modules
try:
    from client.tools.xls_transfer import core, embeddings, translation
    logger.success("XLSTransfer modules loaded successfully", {
        "core": core is not None,
        "embeddings": embeddings is not None,
        "translation": translation is not None
    })
except ImportError as e:
    logger.error(f"Failed to import XLSTransfer modules: {e}")
    core = None
    embeddings = None
    translation = None


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


@router.post("/test/create-dictionary")
async def test_create_dictionary(
    files: List[UploadFile] = File(...),
    kr_column: str = Form("KR"),
    translation_column: str = Form("Translation"),
    sheet_name: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Test dictionary creation with uploaded Excel files

    This simulates the "Create dictionary" button
    """
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"Dictionary creation started by user: {username}", {
        "user": username,
        "files_count": len(files),
        "kr_column": kr_column,
        "translation_column": translation_column,
        "sheet_name": sheet_name
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
        logger.info("Creating dictionaries from uploaded files", {
            "file_count": len(file_paths),
            "kr_column": kr_column,
            "translation_column": translation_column
        })

        # Prepare file list for processing (file_path, sheet_name, kr_column, trans_column)
        excel_files = []
        for file_path in file_paths:
            excel_files.append((file_path, sheet_name or "Sheet1", kr_column, translation_column))

        # Process Excel files to create dictionaries
        split_dict, whole_dict, split_embeddings, whole_embeddings = embeddings.process_excel_for_dictionary(
            excel_files=excel_files,
            progress_tracker=None
        )

        logger.info("Dictionaries created, saving to disk", {
            "split_pairs": len(split_dict),
            "whole_pairs": len(whole_dict)
        })

        # Save dictionaries to disk
        # Save split dictionary
        embeddings.save_dictionary(
            embeddings=split_embeddings,
            translation_dict=split_dict,
            mode="split"
        )

        # Save whole dictionary if it exists
        if whole_dict and len(whole_embeddings) > 0:
            embeddings.save_dictionary(
                embeddings=whole_embeddings,
                translation_dict=whole_dict,
                mode="whole"
            )

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "message": "Dictionaries created successfully",
            "files_processed": len(file_paths),
            "split_pairs": len(split_dict),
            "whole_pairs": len(whole_dict),
            "total_pairs": len(split_dict) + len(whole_dict),
            "elapsed_time": elapsed_time
        }

        logger.success(f"Dictionary creation completed in {elapsed_time:.2f}s", {
            "user": username,
            "files_processed": len(file_paths),
            "split_pairs": len(split_dict),
            "whole_pairs": len(whole_dict),
            "elapsed_time": elapsed_time
        })

        return response

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Dictionary creation failed after {elapsed_time:.2f}s: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })
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

        # Load dictionary files
        result = embeddings.load_dictionary()

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "message": "Dictionary loaded successfully",
            "entries_loaded": result.get("entries_count", 0),
            "model_loaded": result.get("model_name", "unknown")
        }

        logger.success(f"Dictionary loaded in {elapsed_time:.2f}s", {
            "user": username,
            "entries_loaded": result.get("entries_count", 0),
            "model_name": result.get("model_name", "unknown"),
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
        logger.info("Translating text using loaded dictionary")

        # Translate text
        result = translation.translate_single_text(
            text=text,
            threshold=threshold
        )

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "original_text": text,
            "translated_text": result.get("translation", text),
            "confidence": result.get("confidence", 0.0),
            "match_found": result.get("match_found", False)
        }

        logger.success(f"Text translated in {elapsed_time:.3f}s", {
            "user": username,
            "match_found": result.get("match_found", False),
            "confidence": result.get("confidence", 0.0),
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
            # Translate txt file
            result = translation.translate_txt_file(
                input_path=str(input_path),
                threshold=threshold
            )
        else:
            logger.info(f"Translating Excel file: {file.filename}")
            # Translate Excel file
            result = translation.translate_excel_file(
                input_path=str(input_path),
                threshold=threshold
            )

        elapsed_time = time.time() - start_time

        response = {
            "success": True,
            "input_file": file.filename,
            "output_file": result.get("output_path", ""),
            "lines_translated": result.get("lines_translated", 0),
            "matches_found": result.get("matches_found", 0),
            "statistics": result.get("statistics", {})
        }

        logger.success(f"File translation completed in {elapsed_time:.2f}s", {
            "user": username,
            "filename": file.filename,
            "file_type": file_type,
            "lines_translated": result.get("lines_translated", 0),
            "matches_found": result.get("matches_found", 0),
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
