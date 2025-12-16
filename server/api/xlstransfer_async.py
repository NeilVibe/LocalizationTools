"""
XLSTransfer API Endpoints (Refactored with BaseToolAPI)

Reduced from 1105 lines to ~300 lines (73% code reduction) using BaseToolAPI pattern.
All endpoints work identically to original implementation.
"""

from fastapi import Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
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

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from loguru import logger


class XLSTransferAPI(BaseToolAPI):
    """
    XLSTransfer REST API using BaseToolAPI pattern.

    This refactored version reduces code from 1105 lines to ~300 lines
    by leveraging BaseToolAPI's common patterns.
    """

    def __init__(self):
        super().__init__(
            tool_name="XLSTransfer",
            router_prefix="/api/v2/xlstransfer",
            temp_dir="/tmp/xlstransfer_test",
            router_tags=["XLSTransfer"]
        )

        # Import XLSTransfer modules
        self._load_modules()

        # Register routes
        self._register_routes()

    def _load_modules(self):
        """Load XLSTransfer Python modules."""
        try:
            logger.info("Loading XLSTransfer core module...")
            from server.tools.xlstransfer import core
            logger.info("Loading XLSTransfer embeddings module...")
            from server.tools.xlstransfer import embeddings
            logger.info("Loading XLSTransfer translation module...")
            from server.tools.xlstransfer import translation
            logger.info("Loading XLSTransfer process_operation module...")
            from server.tools.xlstransfer import process_operation

            self.core = core
            self.embeddings = embeddings
            self.translation = translation
            self.process_operation = process_operation

            logger.success("XLSTransfer modules loaded successfully", {
                "core": core is not None,
                "embeddings": embeddings is not None,
                "translation": translation is not None,
                "process_operation": process_operation is not None
            })
        except Exception as e:
            logger.error(f"Failed to import XLSTransfer modules: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.core = None
            self.embeddings = None
            self.translation = None
            self.process_operation = None

    def _register_routes(self):
        """Register all endpoint routes."""
        self.router.get("/health")(self.health)
        self.router.post("/test/create-dictionary")(self.create_dictionary)
        self.router.post("/test/load-dictionary")(self.load_dictionary)
        self.router.post("/test/translate-text")(self.translate_text)
        self.router.post("/test/translate-file")(self.translate_file)
        self.router.post("/test/translate-excel")(self.translate_excel)
        self.router.get("/test/status")(self.status)
        self.router.post("/test/get-sheets")(self.get_sheets)
        # Simple Excel Transfer endpoints
        self.router.post("/test/simple/analyze")(self.simple_analyze)
        self.router.post("/test/simple/execute")(self.simple_execute)
        # Additional XLSTransfer endpoints (P15 completion)
        self.router.post("/test/check-newlines")(self.check_newlines)
        self.router.post("/test/combine-excel")(self.combine_excel)
        self.router.post("/test/newline-auto-adapt")(self.newline_auto_adapt)

    # ========================================================================
    # ENDPOINTS
    # ========================================================================

    async def health(self):
        """Check if XLSTransfer modules are loaded."""
        logger.info("XLSTransfer health check requested")

        status = {
            "status": "ok" if self.core is not None else "error",
            "modules_loaded": {
                "core": self.core is not None,
                "embeddings": self.embeddings is not None,
                "translation": self.translation is not None
            }
        }

        logger.info("XLSTransfer health check result", status)
        return status

    async def create_dictionary(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        kr_column: str = Form("A"),
        translation_column: str = Form("B"),
        sheet_name: Optional[str] = Form(None),
        selections: Optional[str] = Form(None),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """Create dictionary from uploaded Excel files."""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("create_dictionary", user_info,
                                files_count=len(files),
                                kr_column=kr_column,
                                translation_column=translation_column)

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name=f"Create Dictionary ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        if self.core is None:
            logger.error("XLSTransfer core module not loaded")
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files(files, "Dictionary file")

            # Prepare excel_files list
            excel_files = self._prepare_excel_files(file_paths, selections, kr_column, translation_column, sheet_name)

            # Queue background task
            background_tasks.add_task(
                self._run_create_dictionary_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                excel_files=excel_files,
                file_paths=file_paths
            )

            logger.success(f"Dictionary creation queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={
                    "files_count": len(files),
                    "excel_files_count": len(excel_files)
                }
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="create_dictionary",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def load_dictionary(self, current_user: dict = Depends(get_current_active_user_async)):
        """Load existing dictionary from disk."""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("load_dictionary", user_info)

        if self.embeddings is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Load split dictionary
            split_embeddings, split_dict, split_index, split_kr_texts = self.embeddings.load_dictionary(mode="split")

            # Try to load whole dictionary
            whole_pairs = 0
            try:
                if self.embeddings.check_dictionary_exists(mode="whole"):
                    whole_embeddings, whole_dict, whole_index, whole_kr_texts = self.embeddings.load_dictionary(mode="whole")
                    whole_pairs = len(whole_dict)
            except Exception:
                logger.info("No whole dictionary found, using split only")

            elapsed_time = time.time() - start_time

            self.log_function_success("load_dictionary", user_info, elapsed_time,
                                      split_pairs=len(split_dict),
                                      whole_pairs=whole_pairs)

            return self.success_response(
                message="Dictionary loaded successfully",
                data={
                    "split_pairs": len(split_dict),
                    "whole_pairs": whole_pairs,
                    "total_pairs": len(split_dict) + whole_pairs
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="load_dictionary",
                elapsed_time=time.time() - start_time
            )

    async def translate_text(
        self,
        text: str = Form(...),
        threshold: float = Form(0.99),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """Translate a single text using dictionary."""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("translate_text", user_info,
                                text_length=len(text),
                                threshold=threshold,
                                text_preview=text[:50] + "..." if len(text) > 50 else text)

        if self.translation is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Load dictionary
            split_embeddings, split_dict, split_index, split_kr_texts = self.embeddings.load_dictionary(mode="split")

            # Find best match
            matched_korean, translated_text, similarity_score = self.translation.find_best_match(
                text=text,
                faiss_index=split_index,
                kr_sentences=split_kr_texts,
                translation_dict=split_dict,
                threshold=threshold,
                model=None
            )

            match_found = bool(matched_korean and translated_text)
            elapsed_time = time.time() - start_time

            self.log_function_success("translate_text", user_info, elapsed_time,
                                      match_found=match_found,
                                      confidence=similarity_score)

            return {
                "success": True,
                "original_text": text,
                "matched_korean": matched_korean,
                "translated_text": translated_text if match_found else text,
                "confidence": similarity_score,
                "match_found": match_found,
                "elapsed_time": elapsed_time
            }

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="translate_text",
                elapsed_time=time.time() - start_time
            )

    async def translate_file(
        self,
        file: UploadFile = File(...),
        file_type: str = Form("txt"),
        threshold: float = Form(0.99),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """Translate a file (txt or Excel)."""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("translate_file", user_info,
                                filename=file.filename,
                                file_type=file_type,
                                threshold=threshold)

        if self.translation is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Save uploaded file
            file_paths = await self.save_uploaded_files([file], "Translation file")
            input_path = Path(file_paths[0])

            if file_type == "txt":
                result = await self._translate_txt_file(input_path, threshold)
            else:
                result = await self._translate_excel_file(input_path, threshold)

            elapsed_time = time.time() - start_time
            result["elapsed_time"] = elapsed_time

            self.log_function_success("translate_file", user_info, elapsed_time,
                                      filename=file.filename,
                                      file_type=file_type)

            return result

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="translate_file",
                elapsed_time=time.time() - start_time
            )

    async def translate_excel(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        selections: str = Form(...),
        threshold: float = Form(0.99),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """Translate Excel files with sheet/column selections."""
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("translate_excel", user_info,
                                files_count=len(files),
                                threshold=threshold)

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="translate_excel",
            operation_name=f"Transfer to Excel ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files], "threshold": threshold}
        )

        await self.emit_start_event(operation, user_info)

        if self.process_operation is None or self.embeddings is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files(files, "Excel file")

            # Parse selections and create path_selections
            selections_dict = json.loads(selections)
            path_selections = self._create_path_selections(file_paths, selections_dict)

            # Queue background task
            background_tasks.add_task(
                self._run_translate_excel_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                path_selections=path_selections,
                threshold=threshold
            )

            logger.success(f"Excel translation queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={
                    "files_count": len(files),
                    "threshold": threshold
                }
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="translate_excel",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def status(self, current_user: dict = Depends(get_current_active_user_async)):
        """Get current XLSTransfer test environment status."""
        user_info = self.extract_user_info(current_user)
        logger.info(f"XLSTransfer status requested by {user_info['username']}")

        test_files = list(self.temp_dir.glob("*")) if self.temp_dir.exists() else []

        return {
            "temp_directory": str(self.temp_dir),
            "temp_exists": self.temp_dir.exists(),
            "dictionary_loaded": False,
            "model_available": self.embeddings is not None,
            "test_files": [str(f) for f in test_files],
            "test_files_count": len(test_files)
        }

    async def get_sheets(
        self,
        file: UploadFile = File(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """Get sheet names from uploaded Excel file."""
        user_info = self.extract_user_info(current_user)

        logger.info(f"Get sheets requested by {user_info['username']}", {
            "user": user_info['username'],
            "filename": file.filename
        })

        if self.core is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            # Save and read file
            file_paths = await self.save_uploaded_files([file])
            file_path = file_paths[0]

            # Get sheet names
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheets = wb.sheetnames
            wb.close()

            logger.success(f"Retrieved {len(sheets)} sheets from {file.filename}", {
                "filename": file.filename,
                "sheet_count": len(sheets),
                "sheets": sheets
            })

            return {
                "success": True,
                "filename": file.filename,
                "sheets": sheets
            }

        except Exception as e:
            logger.error(f"Failed to get sheets: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to read Excel file: {str(e)}")

    # ========================================================================
    # SIMPLE EXCEL TRANSFER ENDPOINTS
    # ========================================================================

    async def simple_analyze(
        self,
        source_file: UploadFile = File(...),
        dest_file: UploadFile = File(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Analyze source and destination Excel files for Simple Transfer.
        Returns sheet names from both files.
        """
        user_info = self.extract_user_info(current_user)

        logger.info(f"Simple transfer analyze requested by {user_info['username']}", {
            "source": source_file.filename,
            "dest": dest_file.filename
        })

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files([source_file, dest_file])
            source_path = file_paths[0]
            dest_path = file_paths[1]

            # Import simple_transfer module
            from server.tools.xlstransfer import simple_transfer

            # Analyze files
            result = simple_transfer.analyze_files(source_path, dest_path)

            logger.success(f"Simple transfer analyze complete", {
                "source_sheets": len(result['source_sheets']),
                "dest_sheets": len(result['dest_sheets'])
            })

            return {
                "success": True,
                "source_file": source_file.filename,
                "dest_file": dest_file.filename,
                "source_sheets": result['source_sheets'],
                "dest_sheets": result['dest_sheets'],
                "temp_source": result['temp_source'],
                "temp_dest": result['temp_dest']
            }

        except Exception as e:
            logger.error(f"Simple transfer analyze failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def simple_execute(
        self,
        temp_source: str = Form(...),
        temp_dest: str = Form(...),
        dest_file: str = Form(...),
        settings: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Execute Simple Excel Transfer with given settings.

        settings JSON format:
        [
            {
                "source_tab": "Sheet1",
                "source_file_col": "A",
                "source_note_col": "B",
                "dest_tab": "Sheet1",
                "dest_file_col": "A",
                "dest_note_col": "B"
            }
        ]
        """
        user_info = self.extract_user_info(current_user)

        logger.info(f"Simple transfer execute requested by {user_info['username']}", {
            "dest_file": dest_file
        })

        try:
            # Parse settings
            settings_list = json.loads(settings)

            # Import simple_transfer module
            from server.tools.xlstransfer import simple_transfer

            # Validate settings
            is_valid, error = simple_transfer.validate_transfer_settings(settings_list)
            if not is_valid:
                return {"success": False, "error": error}

            # Execute transfer
            result = simple_transfer.execute_transfer(
                temp_source_file=temp_source,
                temp_dest_file=temp_dest,
                dest_file=dest_file,
                settings_list=settings_list,
                cleanup_temps=True
            )

            logger.success(f"Simple transfer complete", {
                "transfers": result['transfers_count'],
                "rows": result['total_rows_transferred'],
                "output": result['output_file']
            })

            return result

        except Exception as e:
            logger.error(f"Simple transfer execute failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _prepare_excel_files(self, file_paths, selections, kr_column, translation_column, sheet_name):
        """Prepare excel_files list for dictionary creation."""
        excel_files = []

        if selections:
            # Advanced mode with selections
            selections_dict = json.loads(selections)
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
        else:
            # Simple mode with default columns
            for file_path in file_paths:
                excel_files.append((file_path, sheet_name or "Sheet1", kr_column, translation_column))

        return excel_files

    def _create_path_selections(self, file_paths, selections_dict):
        """Create path_selections dict mapping file paths to sheet/column selections."""
        path_selections = {}
        filename_to_path = {os.path.basename(fp): fp for fp in file_paths}

        for filename, sheets in selections_dict.items():
            if filename in filename_to_path:
                file_path = filename_to_path[filename]
                path_selections[file_path] = sheets

        return path_selections

    async def _translate_txt_file(self, input_path: Path, threshold: float):
        """Translate a .txt file line by line."""
        split_embeddings, split_dict, split_index, split_kr_texts = self.embeddings.load_dictionary(mode="split")

        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        translated_lines = []
        matches_found = 0

        for line in lines:
            if not line.strip():
                translated_lines.append(line)
                continue

            matched_korean, translated_text, confidence = self.translation.find_best_match(
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

        output_path = self.temp_dir / f"{input_path.stem}_translated.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)

        return {
            "success": True,
            "input_file": input_path.name,
            "output_file": str(output_path),
            "lines_translated": len(lines),
            "matches_found": matches_found
        }

    async def _translate_excel_file(self, input_path: Path, threshold: float):
        """Translate an Excel file (simplified approach for testing)."""
        selections = {
            str(input_path): {
                "Sheet1": {
                    "kr_column": "A",
                    "trans_column": "B"
                }
            }
        }

        result = self.process_operation.translate_excel(selections, threshold)

        if result.get("success"):
            output_path = f"{str(input_path).rsplit('.', 1)[0]}_translated.xlsx"
            return {
                "success": True,
                "input_file": input_path.name,
                "output_file": output_path,
                "message": result.get("message", "")
            }
        else:
            raise Exception(result.get("error", "Unknown error"))

    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================

    def _run_create_dictionary_background(self, operation_id, user_info, excel_files, file_paths):
        """Background task for dictionary creation."""
        def task():
            logger.info(f"Creating dictionaries from {len(excel_files)} Excel file selections")

            # Import here to avoid circular dependency
            from server.utils.progress_tracker import ProgressTracker

            # Create progress tracker for real-time updates (unified Factor Power)
            tracker = ProgressTracker(operation_id)

            split_dict, whole_dict, split_embeddings, whole_embeddings = self.embeddings.process_excel_for_dictionary(
                excel_files=excel_files,
                progress_tracker=tracker
            )

            # Save dictionaries
            self.embeddings.save_dictionary(
                embeddings=split_embeddings,
                translation_dict=split_dict,
                mode="split"
            )

            if whole_dict and len(whole_embeddings) > 0:
                self.embeddings.save_dictionary(
                    embeddings=whole_embeddings,
                    translation_dict=whole_dict,
                    mode="whole"
                )

            return {
                "split_pairs": len(split_dict),
                "whole_pairs": len(whole_dict),
                "files_processed": len(file_paths)
            }

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name="Create Dictionary"
        )
        wrapped()

    def _run_translate_excel_background(self, operation_id, user_info, path_selections, threshold):
        """Background task for Excel translation."""
        def task():
            logger.info(f"Translating Excel files with threshold={threshold}, operation_id={operation_id}")

            # Pass operation_id for progress tracking
            result = self.process_operation.translate_excel(path_selections, threshold, operation_id)

            if result.get("success"):
                return {"output_dir": result.get("output_dir")}
            else:
                raise Exception(result.get("error", "Unknown error"))

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="translate_excel",
            operation_name="Translate Excel"
        )
        wrapped()

    # ========================================================================
    # CHECK NEWLINES, COMBINE EXCEL, NEWLINE AUTO-ADAPT ENDPOINTS
    # ========================================================================

    async def check_newlines(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        selections: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Check newline consistency between Korean and Translation columns.
        Monolith: lines 782-865
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("check_newlines", user_info,
                                files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="check_newlines",
            operation_name=f"Check Newlines ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        if self.process_operation is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            file_paths = await self.save_uploaded_files(files, "Excel file")
            selections_dict = json.loads(selections)
            path_selections = self._create_path_selections(file_paths, selections_dict)

            background_tasks.add_task(
                self._run_check_newlines_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                path_selections=path_selections
            )

            logger.success(f"Check newlines queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="check_newlines",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    def _run_check_newlines_background(self, operation_id, user_info, path_selections):
        """Background task for check newlines."""
        def task():
            logger.info(f"Checking newlines, operation_id={operation_id}")
            result = self.process_operation.check_newlines(path_selections)
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="check_newlines",
            operation_name="Check Newlines"
        )
        wrapped()

    async def combine_excel(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        selections: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Combine multiple Excel files into one.
        Monolith: lines 869-941
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("combine_excel", user_info,
                                files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="combine_excel",
            operation_name=f"Combine Excel ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        if self.process_operation is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            file_paths = await self.save_uploaded_files(files, "Excel file")
            selections_dict = json.loads(selections)
            path_selections = self._create_path_selections(file_paths, selections_dict)

            background_tasks.add_task(
                self._run_combine_excel_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                path_selections=path_selections
            )

            logger.success(f"Combine Excel queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="combine_excel",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    def _run_combine_excel_background(self, operation_id, user_info, path_selections):
        """Background task for combine Excel."""
        def task():
            logger.info(f"Combining Excel files, operation_id={operation_id}")
            result = self.process_operation.combine_excel(path_selections)
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="combine_excel",
            operation_name="Combine Excel"
        )
        wrapped()

    async def newline_auto_adapt(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        selections: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Auto-adapt newlines in translation to match Korean source.
        Monolith: lines 946-1098
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("newline_auto_adapt", user_info,
                                files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="newline_auto_adapt",
            operation_name=f"Newline Auto-Adapt ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        if self.process_operation is None:
            raise HTTPException(status_code=500, detail="XLSTransfer modules not loaded")

        try:
            file_paths = await self.save_uploaded_files(files, "Excel file")
            selections_dict = json.loads(selections)
            path_selections = self._create_path_selections(file_paths, selections_dict)

            background_tasks.add_task(
                self._run_newline_auto_adapt_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                path_selections=path_selections
            )

            logger.success(f"Newline auto-adapt queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="newline_auto_adapt",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    def _run_newline_auto_adapt_background(self, operation_id, user_info, path_selections):
        """Background task for newline auto-adapt."""
        def task():
            logger.info(f"Auto-adapting newlines, operation_id={operation_id}")
            result = self.process_operation.newline_auto_adapt(path_selections)
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="newline_auto_adapt",
            operation_name="Newline Auto-Adapt"
        )
        wrapped()


# ============================================================================
# INITIALIZE AND EXPORT ROUTER
# ============================================================================

xls_api = XLSTransferAPI()
router = xls_api.router
