"""
KR Similar API Endpoints (Using BaseToolAPI Pattern)

REST API for KR Similar - Korean semantic similarity search tool.
App #3 in the LocaNext platform.

Migrated from KRSIMILAR0124.py desktop app to web API.
"""

from fastapi import Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import time
from pathlib import Path

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.tools.kr_similar.embeddings import EmbeddingsManager, DICT_TYPES
from server.tools.kr_similar.searcher import SimilaritySearcher
from loguru import logger


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateDictionaryRequest(BaseModel):
    """Request model for create dictionary."""
    dict_type: str  # BDO, BDM, BDC, CD
    kr_column: int = 5
    trans_column: int = 6


class LoadDictionaryRequest(BaseModel):
    """Request model for load dictionary."""
    dict_type: str


class SearchSimilarRequest(BaseModel):
    """Request model for similarity search."""
    query: str
    threshold: float = 0.85
    top_k: int = 10
    use_whole: bool = False


class ExtractSimilarRequest(BaseModel):
    """Request model for similar string extraction."""
    min_char_length: int = 50
    similarity_threshold: float = 0.85
    filter_same_category: bool = True


class AutoTranslateRequest(BaseModel):
    """Request model for auto-translation."""
    similarity_threshold: float = 0.85


# ============================================================================
# KR SIMILAR API CLASS
# ============================================================================

class KRSimilarAPI(BaseToolAPI):
    """
    KR Similar REST API using BaseToolAPI pattern.

    Provides:
    - Dictionary creation from language files
    - Semantic similarity search
    - Similar string extraction
    - Auto-translation using similarity matching
    """

    def __init__(self):
        super().__init__(
            tool_name="KRSimilar",
            router_prefix="/api/v2/kr-similar",
            temp_dir="/tmp/krsimilar_uploads",
            router_tags=["KRSimilar"]
        )

        # Initialize embeddings manager and searcher
        self.embeddings_manager = EmbeddingsManager()
        self.searcher = SimilaritySearcher(self.embeddings_manager)

        # Register routes
        self._register_routes()

        logger.success("KRSimilar API initialized")

    def _register_routes(self):
        """Register all endpoint routes."""
        self.router.get("/health")(self.health)
        self.router.post("/create-dictionary")(self.create_dictionary)
        self.router.post("/load-dictionary")(self.load_dictionary)
        self.router.post("/search")(self.search_similar)
        self.router.post("/extract-similar")(self.extract_similar)
        self.router.post("/auto-translate")(self.auto_translate)
        self.router.get("/list-dictionaries")(self.list_dictionaries)
        self.router.get("/status")(self.status)
        self.router.delete("/clear")(self.clear_dictionary)

    # ========================================================================
    # ENDPOINTS
    # ========================================================================

    async def health(self):
        """Check if KRSimilar modules are loaded."""
        logger.info("KRSimilar health check requested")

        status = {
            "status": "ok",
            "modules_loaded": {
                "embeddings_manager": self.embeddings_manager is not None,
                "searcher": self.searcher is not None
            },
            "current_dictionary": self.embeddings_manager.current_dict_type,
            "models_available": self.embeddings_manager.get_status().get("models_available", False)
        }

        return status

    async def create_dictionary(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        dict_type: str = Form(...),
        kr_column: int = Form(5),
        trans_column: int = Form(6),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Create embeddings dictionary from language data files.

        Args:
            files: List of tab-separated language data files
            dict_type: Dictionary type (BDO, BDM, BDC, CD)
            kr_column: Korean text column index (default: 5)
            trans_column: Translation column index (default: 6)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("create_dictionary", user_info,
                                files_count=len(files),
                                dict_type=dict_type)

        # Validate dict_type
        if dict_type not in DICT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dict_type: {dict_type}. Must be one of {DICT_TYPES}"
            )

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name=f"Create KR Similar Dictionary {dict_type} ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files], "dict_type": dict_type}
        )

        await self.emit_start_event(operation, user_info)

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files(files, "Language file")

            # Queue background task
            background_tasks.add_task(
                self._run_create_dictionary_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                dict_type=dict_type,
                kr_column=kr_column,
                trans_column=trans_column
            )

            logger.success(f"Dictionary creation queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={
                    "files_count": len(files),
                    "dict_type": dict_type
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

    async def load_dictionary(
        self,
        dict_type: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Load existing dictionary into memory.

        Args:
            dict_type: Dictionary type to load (BDO, BDM, BDC, CD)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("load_dictionary", user_info, dict_type=dict_type)

        # Validate dict_type
        if dict_type not in DICT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dict_type: {dict_type}. Must be one of {DICT_TYPES}"
            )

        try:
            # Load dictionary
            self.embeddings_manager.load_dictionary(dict_type)

            split_pairs = len(self.embeddings_manager.split_dict) if self.embeddings_manager.split_dict else 0
            whole_pairs = len(self.embeddings_manager.whole_dict) if self.embeddings_manager.whole_dict else 0

            elapsed_time = time.time() - start_time

            self.log_function_success("load_dictionary", user_info, elapsed_time,
                                      dict_type=dict_type,
                                      split_pairs=split_pairs,
                                      whole_pairs=whole_pairs)

            return self.success_response(
                message=f"Dictionary loaded: {dict_type}",
                data={
                    "dict_type": dict_type,
                    "split_pairs": split_pairs,
                    "whole_pairs": whole_pairs,
                    "total_pairs": split_pairs + whole_pairs
                },
                elapsed_time=elapsed_time
            )

        except FileNotFoundError as e:
            logger.error(f"Dictionary not found: {dict_type}")
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="load_dictionary",
                elapsed_time=time.time() - start_time
            )

    async def search_similar(
        self,
        query: str = Form(...),
        threshold: float = Form(0.85),
        top_k: int = Form(10),
        use_whole: bool = Form(False),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Search for similar Korean strings.

        Args:
            query: Korean text to search for
            threshold: Minimum similarity threshold (0.0-1.0)
            top_k: Maximum results to return
            use_whole: Use whole embeddings instead of split
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("search_similar", user_info,
                                query_preview=query[:50] + "..." if len(query) > 50 else query,
                                threshold=threshold,
                                top_k=top_k)

        try:
            # Search
            results = self.searcher.find_similar(
                query=query,
                threshold=threshold,
                top_k=top_k,
                use_whole=use_whole
            )

            elapsed_time = time.time() - start_time

            self.log_function_success("search_similar", user_info, elapsed_time,
                                      results_count=len(results))

            return self.success_response(
                message=f"Found {len(results)} similar strings",
                data={
                    "results": results,
                    "count": len(results),
                    "threshold": threshold,
                    "query": query
                },
                elapsed_time=elapsed_time
            )

        except RuntimeError as e:
            if "No dictionary loaded" in str(e):
                raise HTTPException(status_code=400, detail="No dictionary loaded. Load a dictionary first.")
            raise
        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="search_similar",
                elapsed_time=time.time() - start_time
            )

    async def extract_similar(
        self,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        min_char_length: int = Form(50),
        similarity_threshold: float = Form(0.85),
        filter_same_category: bool = Form(True),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Extract groups of similar strings from a file.

        Used for quality checks to find strings that should have
        consistent translations.

        Args:
            file: Language data file
            min_char_length: Minimum character length to consider
            similarity_threshold: Minimum similarity (0.0-1.0)
            filter_same_category: Filter out same-category matches
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("extract_similar", user_info,
                                filename=file.filename,
                                min_char_length=min_char_length,
                                similarity_threshold=similarity_threshold)

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="extract_similar",
            operation_name=f"Extract Similar Strings ({file.filename})",
            file_info={"filename": file.filename}
        )

        await self.emit_start_event(operation, user_info)

        try:
            # Save uploaded file
            file_paths = await self.save_uploaded_files([file], "Input file")

            # Queue background task
            background_tasks.add_task(
                self._run_extract_similar_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_path=file_paths[0],
                min_char_length=min_char_length,
                similarity_threshold=similarity_threshold,
                filter_same_category=filter_same_category
            )

            logger.success(f"Similar extraction queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"filename": file.filename}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="extract_similar",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def auto_translate(
        self,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        similarity_threshold: float = Form(0.85),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Auto-translate a file using semantic similarity matching.

        Requires a dictionary to be loaded first.

        Args:
            file: Language data file to translate
            similarity_threshold: Minimum similarity for matching (0.0-1.0)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("auto_translate", user_info,
                                filename=file.filename,
                                similarity_threshold=similarity_threshold)

        if not self.embeddings_manager.split_index:
            raise HTTPException(
                status_code=400,
                detail="No dictionary loaded. Load a dictionary first."
            )

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="auto_translate",
            operation_name=f"Auto-Translate ({file.filename})",
            file_info={"filename": file.filename}
        )

        await self.emit_start_event(operation, user_info)

        try:
            # Save uploaded file
            file_paths = await self.save_uploaded_files([file], "Input file")

            # Queue background task
            background_tasks.add_task(
                self._run_auto_translate_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_path=file_paths[0],
                similarity_threshold=similarity_threshold
            )

            logger.success(f"Auto-translation queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"filename": file.filename}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="auto_translate",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def list_dictionaries(self, current_user: dict = Depends(get_current_active_user_async)):
        """
        List all available dictionaries.

        Returns list of dictionaries with metadata.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("list_dictionaries", user_info)

        try:
            dictionaries = self.embeddings_manager.list_available_dictionaries()

            elapsed_time = time.time() - start_time

            self.log_function_success("list_dictionaries", user_info, elapsed_time,
                                      dictionaries_count=len(dictionaries))

            return self.success_response(
                message=f"Found {len(dictionaries)} available dictionaries",
                data={
                    "dictionaries": dictionaries,
                    "count": len(dictionaries),
                    "available_types": DICT_TYPES
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="list_dictionaries",
                elapsed_time=time.time() - start_time
            )

    async def status(self, current_user: dict = Depends(get_current_active_user_async)):
        """Get current KRSimilar status."""
        user_info = self.extract_user_info(current_user)
        logger.info(f"KRSimilar status requested by {user_info['username']}")

        embeddings_status = self.embeddings_manager.get_status()
        searcher_status = self.searcher.get_status()

        return {
            "tool_name": self.tool_name,
            "temp_directory": str(self.temp_dir),
            "embeddings": embeddings_status,
            "searcher": searcher_status,
            "available_dict_types": DICT_TYPES
        }

    async def clear_dictionary(self, current_user: dict = Depends(get_current_active_user_async)):
        """Clear currently loaded dictionary from memory."""
        user_info = self.extract_user_info(current_user)

        logger.info(f"Clearing dictionary requested by {user_info['username']}")

        self.embeddings_manager.split_embeddings = None
        self.embeddings_manager.split_dict = None
        self.embeddings_manager.split_index = None
        self.embeddings_manager.whole_embeddings = None
        self.embeddings_manager.whole_dict = None
        self.embeddings_manager.whole_index = None
        self.embeddings_manager.current_dict_type = None

        return self.success_response(
            message="Dictionary cleared from memory",
            data={"current_dictionary": None}
        )

    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================

    def _run_create_dictionary_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        dict_type: str,
        kr_column: int,
        trans_column: int
    ):
        """Background task for dictionary creation."""
        def task():
            logger.info(f"Creating dictionary {dict_type} from {len(file_paths)} files")

            result = self.embeddings_manager.create_dictionary(
                file_paths=file_paths,
                dict_type=dict_type,
                kr_column=kr_column,
                trans_column=trans_column
            )

            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name=f"Create Dictionary {dict_type}"
        )
        wrapped()

    def _run_extract_similar_background(
        self,
        operation_id: int,
        user_info: dict,
        file_path: str,
        min_char_length: int,
        similarity_threshold: float,
        filter_same_category: bool
    ):
        """Background task for similar string extraction."""
        def task():
            import pandas as pd

            logger.info(f"Extracting similar strings from {file_path}")

            # Load data
            data = pd.read_csv(
                file_path,
                delimiter="\t",
                header=None,
                on_bad_lines='skip'
            )

            # Extract similar
            results = self.searcher.extract_similar_strings(
                data=data,
                min_char_length=min_char_length,
                similarity_threshold=similarity_threshold,
                filter_same_category=filter_same_category
            )

            return {
                "groups_found": len(results),
                "results": results
            }

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="extract_similar",
            operation_name="Extract Similar Strings"
        )
        wrapped()

    def _run_auto_translate_background(
        self,
        operation_id: int,
        user_info: dict,
        file_path: str,
        similarity_threshold: float
    ):
        """Background task for auto-translation."""
        def task():
            import pandas as pd
            from pathlib import Path

            logger.info(f"Auto-translating {file_path}")

            # Load data
            data = pd.read_csv(
                file_path,
                delimiter="\t",
                header=None,
                on_bad_lines='skip'
            )

            # Auto-translate
            result_df = self.searcher.auto_translate(
                data=data,
                similarity_threshold=similarity_threshold
            )

            # Save result
            input_path = Path(file_path)
            output_path = input_path.parent / f"{input_path.stem}_translated.txt"
            result_df.to_csv(output_path, sep='\t', header=False, index=False)

            return {
                "rows_processed": len(data),
                "output_file": str(output_path)
            }

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="auto_translate",
            operation_name="Auto-Translate"
        )
        wrapped()


# ============================================================================
# INITIALIZE AND EXPORT ROUTER
# ============================================================================

kr_similar_api = KRSimilarAPI()
router = kr_similar_api.router
