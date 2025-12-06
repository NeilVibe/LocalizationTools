"""
QuickSearch API Endpoints (Using BaseToolAPI Pattern)

REST API for QuickSearch dictionary search tool.
Migrated from QuickSearch0818.py desktop app to web API.
"""

from fastapi import Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import time
from pathlib import Path

from server.api.base_tool_api import BaseToolAPI
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.tools.quicksearch.dictionary import DictionaryManager, GAMES, LANGUAGES
from server.tools.quicksearch.searcher import Searcher
from server.tools.quicksearch import qa_tools
from loguru import logger


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateDictionaryRequest(BaseModel):
    """Request model for create dictionary."""
    game: str
    language: str
    file_type: str  # "xml" or "txt"


class LoadDictionaryRequest(BaseModel):
    """Request model for load dictionary."""
    game: str
    language: str


class SearchRequest(BaseModel):
    """Request model for search."""
    query: str
    match_type: str = "contains"  # "contains" or "exact"
    start_index: int = 0
    limit: int = 50


class SearchMultilineRequest(BaseModel):
    """Request model for multi-line search."""
    queries: List[str]
    match_type: str = "contains"
    limit: int = 50


class SetReferenceRequest(BaseModel):
    """Request model for set reference dictionary."""
    game: str
    language: str


class ToggleReferenceRequest(BaseModel):
    """Request model for toggle reference."""
    enabled: bool


# ============================================================================
# QUICKSEARCH API CLASS
# ============================================================================

class QuickSearchAPI(BaseToolAPI):
    """
    QuickSearch REST API using BaseToolAPI pattern.

    Provides dictionary search functionality for game translations.
    """

    def __init__(self):
        super().__init__(
            tool_name="QuickSearch",
            router_prefix="/api/v2/quicksearch",
            temp_dir="/tmp/quicksearch_uploads",
            router_tags=["QuickSearch"]
        )

        # Initialize dictionary manager and searcher
        self.dict_manager = DictionaryManager()
        self.searcher = Searcher()

        # Register routes
        self._register_routes()

        logger.success("QuickSearch API initialized")

    def _register_routes(self):
        """Register all endpoint routes."""
        self.router.get("/health")(self.health)
        self.router.post("/create-dictionary")(self.create_dictionary)
        self.router.post("/load-dictionary")(self.load_dictionary)
        self.router.post("/search")(self.search)
        self.router.post("/search-multiline")(self.search_multiline)
        self.router.post("/set-reference")(self.set_reference)
        self.router.post("/toggle-reference")(self.toggle_reference)
        self.router.get("/list-dictionaries")(self.list_dictionaries)
        # QA Tools endpoints
        self.router.post("/qa/extract-glossary")(self.qa_extract_glossary)
        self.router.post("/qa/line-check")(self.qa_line_check)
        self.router.post("/qa/term-check")(self.qa_term_check)
        self.router.post("/qa/pattern-check")(self.qa_pattern_check)
        self.router.post("/qa/character-count")(self.qa_character_count)

    # ========================================================================
    # ENDPOINTS
    # ========================================================================

    async def health(self):
        """Check if QuickSearch modules are loaded."""
        logger.info("QuickSearch health check requested")

        status = {
            "status": "ok",
            "modules_loaded": {
                "dictionary_manager": self.dict_manager is not None,
                "searcher": self.searcher is not None
            },
            "current_dictionary": None,
            "reference_dictionary": None
        }

        if self.dict_manager.current_dict:
            status["current_dictionary"] = f"{self.dict_manager.current_game}-{self.dict_manager.current_language}"

        if self.dict_manager.reference_dict:
            status["reference_dictionary"] = f"{self.dict_manager.reference_game}-{self.dict_manager.reference_language}"

        return status

    async def create_dictionary(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        game: str = Form(...),
        language: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Create dictionary from uploaded XML/TXT/TSV files.

        Args:
            files: List of files to process
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("create_dictionary", user_info,
                                files_count=len(files),
                                game=game,
                                language=language)

        # Validate game and language
        if game not in GAMES:
            raise HTTPException(status_code=400, detail=f"Invalid game: {game}. Must be one of {GAMES}")
        if language not in LANGUAGES:
            raise HTTPException(status_code=400, detail=f"Invalid language: {language}. Must be one of {LANGUAGES}")

        # Create ActiveOperation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name=f"Create Dictionary {game}-{language} ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files], "game": game, "language": language}
        )

        await self.emit_start_event(operation, user_info)

        try:
            # Save uploaded files
            file_paths = await self.save_uploaded_files(files, "Dictionary file")

            # Queue background task
            background_tasks.add_task(
                self._run_create_dictionary_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                game=game,
                language=language
            )

            logger.success(f"Dictionary creation queued as operation {operation.operation_id}")

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={
                    "files_count": len(files),
                    "game": game,
                    "language": language
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
        game: str = Form(...),
        language: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Load existing dictionary into memory.

        Args:
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("load_dictionary", user_info, game=game, language=language)

        # Validate game and language
        if game not in GAMES:
            raise HTTPException(status_code=400, detail=f"Invalid game: {game}")
        if language not in LANGUAGES:
            raise HTTPException(status_code=400, detail=f"Invalid language: {language}")

        try:
            # Load dictionary
            dictionary = self.dict_manager.load_dictionary(game, language, as_reference=False)

            # Load into searcher
            self.searcher.load_dictionary(dictionary)

            pairs_count = len(dictionary.get('split_dict', {})) + len(dictionary.get('whole_dict', {}))
            elapsed_time = time.time() - start_time

            self.log_function_success("load_dictionary", user_info, elapsed_time,
                                      game=game,
                                      language=language,
                                      pairs_count=pairs_count)

            return self.success_response(
                message=f"Dictionary loaded successfully: {game}-{language}",
                data={
                    "game": game,
                    "language": language,
                    "pairs_count": pairs_count,
                    "creation_date": dictionary.get('creation_date', 'Unknown')
                },
                elapsed_time=elapsed_time
            )

        except FileNotFoundError as e:
            logger.error(f"Dictionary not found: {game}-{language}")
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="load_dictionary",
                elapsed_time=time.time() - start_time
            )

    async def search(
        self,
        query: str = Form(...),
        match_type: str = Form("contains"),
        start_index: int = Form(0),
        limit: int = Form(50),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Search dictionary for query string.

        Args:
            query: Search query
            match_type: "contains" or "exact" (default: "contains")
            start_index: Starting index for pagination (default: 0)
            limit: Maximum results to return (default: 50)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("search", user_info,
                                query_preview=query[:50] + "..." if len(query) > 50 else query,
                                match_type=match_type,
                                limit=limit)

        try:
            # Perform search
            results, total_count = self.searcher.search_one_line(
                query=query,
                match_type=match_type,
                start_index=start_index,
                limit=limit
            )

            # Format results
            formatted_results = []
            for result in results:
                if len(result) == 4:  # With reference
                    korean, translation, ref_translation, string_id = result
                    formatted_results.append({
                        "korean": korean,
                        "translation": translation,
                        "reference": ref_translation,
                        "string_id": string_id
                    })
                else:  # Without reference
                    korean, translation, string_id = result
                    formatted_results.append({
                        "korean": korean,
                        "translation": translation,
                        "string_id": string_id
                    })

            elapsed_time = time.time() - start_time

            self.log_function_success("search", user_info, elapsed_time,
                                      results_count=len(formatted_results),
                                      total_count=total_count)

            return self.success_response(
                message=f"Search completed: {total_count} results found",
                data={
                    "results": formatted_results,
                    "total_count": total_count,
                    "returned_count": len(formatted_results),
                    "start_index": start_index,
                    "limit": limit
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="search",
                elapsed_time=time.time() - start_time
            )

    async def search_multiline(
        self,
        queries: List[str] = Form(...),
        match_type: str = Form("contains"),
        limit: int = Form(50),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Search for multiple queries (one per line).

        Args:
            queries: List of search queries
            match_type: "contains" or "exact" (default: "contains")
            limit: Maximum results per query (default: 50)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("search_multiline", user_info,
                                queries_count=len(queries),
                                match_type=match_type)

        try:
            # Perform multi-line search
            results = self.searcher.search_multi_line(
                queries=queries,
                match_type=match_type,
                limit=limit
            )

            # Format results
            formatted_results = []
            for item in results:
                matches = []
                for match in item['matches']:
                    if len(match) == 4:  # With reference
                        korean, translation, ref_translation, string_id = match
                        matches.append({
                            "korean": korean,
                            "translation": translation,
                            "reference": ref_translation,
                            "string_id": string_id
                        })
                    else:  # Without reference
                        korean, translation, string_id = match
                        matches.append({
                            "korean": korean,
                            "translation": translation,
                            "string_id": string_id
                        })

                formatted_results.append({
                    "line": item['line'],
                    "matches": matches,
                    "total_count": item['total_count']
                })

            elapsed_time = time.time() - start_time
            total_matches = sum(len(r['matches']) for r in formatted_results)

            self.log_function_success("search_multiline", user_info, elapsed_time,
                                      queries_count=len(queries),
                                      total_matches=total_matches)

            return self.success_response(
                message=f"Multi-line search completed: {total_matches} total matches",
                data={
                    "results": formatted_results,
                    "queries_count": len(queries),
                    "total_matches": total_matches
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="search_multiline",
                elapsed_time=time.time() - start_time
            )

    async def set_reference(
        self,
        game: str = Form(...),
        language: str = Form(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Load reference dictionary for comparison.

        Args:
            game: Game code (BDO, BDM, BDC, CD)
            language: Language code (EN, FR, etc.)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("set_reference", user_info, game=game, language=language)

        # Validate game and language
        if game not in GAMES:
            raise HTTPException(status_code=400, detail=f"Invalid game: {game}")
        if language not in LANGUAGES:
            raise HTTPException(status_code=400, detail=f"Invalid language: {language}")

        try:
            # Load reference dictionary
            dictionary = self.dict_manager.load_dictionary(game, language, as_reference=True)

            # Load into searcher
            self.searcher.load_reference_dictionary(dictionary)

            pairs_count = len(dictionary.get('split_dict', {})) + len(dictionary.get('whole_dict', {}))
            elapsed_time = time.time() - start_time

            self.log_function_success("set_reference", user_info, elapsed_time,
                                      game=game,
                                      language=language,
                                      pairs_count=pairs_count)

            return self.success_response(
                message=f"Reference dictionary loaded: {game}-{language}",
                data={
                    "game": game,
                    "language": language,
                    "pairs_count": pairs_count,
                    "reference_enabled": self.searcher.reference_enabled
                },
                elapsed_time=elapsed_time
            )

        except FileNotFoundError as e:
            logger.error(f"Reference dictionary not found: {game}-{language}")
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="set_reference",
                elapsed_time=time.time() - start_time
            )

    async def toggle_reference(
        self,
        enabled: bool = Form(...),
        current_user: dict = Depends(get_current_active_user_async)
    ):
        """
        Enable or disable reference dictionary display.

        Args:
            enabled: True to enable, False to disable
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("toggle_reference", user_info, enabled=enabled)

        try:
            # Toggle reference
            self.searcher.toggle_reference(enabled)

            elapsed_time = time.time() - start_time

            self.log_function_success("toggle_reference", user_info, elapsed_time, enabled=enabled)

            return self.success_response(
                message=f"Reference dictionary {'enabled' if enabled else 'disabled'}",
                data={
                    "reference_enabled": enabled
                },
                elapsed_time=elapsed_time
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="toggle_reference",
                elapsed_time=time.time() - start_time
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
            # Get available dictionaries
            dictionaries = self.dict_manager.list_available_dictionaries()

            elapsed_time = time.time() - start_time

            self.log_function_success("list_dictionaries", user_info, elapsed_time,
                                      dictionaries_count=len(dictionaries))

            return self.success_response(
                message=f"Found {len(dictionaries)} available dictionaries",
                data={
                    "dictionaries": dictionaries,
                    "count": len(dictionaries)
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

    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================

    def _run_create_dictionary_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        game: str,
        language: str
    ):
        """Background task for dictionary creation."""
        def task():
            logger.info(f"Creating dictionary {game}-{language} from {len(file_paths)} files")

            # Create dictionary
            split_dict, whole_dict, string_keys, stringid_to_entry = self.dict_manager.create_dictionary(
                file_paths=file_paths,
                game=game,
                language=language
            )

            total_pairs = len(split_dict) + len(whole_dict)

            return {
                "split_pairs": len(split_dict),
                "whole_pairs": len(whole_dict),
                "total_pairs": total_pairs,
                "game": game,
                "language": language
            }

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="create_dictionary",
            operation_name=f"Create Dictionary {game}-{language}"
        )
        wrapped()

    # ========================================================================
    # QA TOOLS ENDPOINTS
    # ========================================================================

    async def qa_extract_glossary(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        filter_sentences: bool = Form(True),
        glossary_length_threshold: int = Form(15),
        min_occurrence: int = Form(2),
        sort_method: str = Form("alphabetical"),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Extract glossary terms from uploaded files.

        Uses Aho-Corasick for fast occurrence counting.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("qa_extract_glossary", user_info,
                                files_count=len(files),
                                filter_sentences=filter_sentences,
                                threshold=glossary_length_threshold)

        # Create operation
        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="qa_extract_glossary",
            operation_name=f"Extract Glossary ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        try:
            file_paths = await self.save_uploaded_files(files, "QA file")

            background_tasks.add_task(
                self._run_qa_extract_glossary_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold,
                min_occurrence=min_occurrence,
                sort_method=sort_method
            )

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="qa_extract_glossary",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def qa_line_check(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        glossary_files: Optional[List[UploadFile]] = File(None),
        filter_sentences: bool = Form(True),
        glossary_length_threshold: int = Form(15),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Find inconsistent translations - same source with different translations.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("qa_line_check", user_info, files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="qa_line_check",
            operation_name=f"Line Check ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        try:
            file_paths = await self.save_uploaded_files(files, "Source file")
            glossary_file_paths = None
            if glossary_files and len(glossary_files) > 0 and glossary_files[0].filename:
                glossary_file_paths = await self.save_uploaded_files(glossary_files, "Glossary file")

            background_tasks.add_task(
                self._run_qa_line_check_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                glossary_file_paths=glossary_file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold
            )

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="qa_line_check",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def qa_term_check(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        glossary_files: Optional[List[UploadFile]] = File(None),
        filter_sentences: bool = Form(True),
        glossary_length_threshold: int = Form(15),
        max_issues_per_term: int = Form(6),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Check if glossary terms appear in source but their translations are missing from target.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("qa_term_check", user_info, files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="qa_term_check",
            operation_name=f"Term Check ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        try:
            file_paths = await self.save_uploaded_files(files, "Source file")
            glossary_file_paths = None
            if glossary_files and len(glossary_files) > 0 and glossary_files[0].filename:
                glossary_file_paths = await self.save_uploaded_files(glossary_files, "Glossary file")

            background_tasks.add_task(
                self._run_qa_term_check_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                glossary_file_paths=glossary_file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold,
                max_issues_per_term=max_issues_per_term
            )

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="qa_term_check",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def qa_pattern_check(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Check if {code} patterns in StrOrigin match patterns in Str.
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("qa_pattern_check", user_info, files_count=len(files))

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="qa_pattern_check",
            operation_name=f"Pattern Check ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        try:
            file_paths = await self.save_uploaded_files(files, "Source file")

            background_tasks.add_task(
                self._run_qa_pattern_check_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths
            )

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files)}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="qa_pattern_check",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    async def qa_character_count(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        symbol_set: str = Form("BDO"),
        custom_symbols: Optional[str] = Form(None),
        current_user: dict = Depends(get_current_active_user_async),
        db: AsyncSession = Depends(get_async_db)
    ):
        """
        Check if special character counts match between StrOrigin and Str.

        symbol_set: "BDO" ({, }) or "BDM" (▶, {, }, 🔗, |)
        custom_symbols: Optional custom symbols string (each char is a symbol)
        """
        start_time = time.time()
        user_info = self.extract_user_info(current_user)

        self.log_function_start("qa_character_count", user_info,
                                files_count=len(files),
                                symbol_set=symbol_set)

        operation = await self.create_operation(
            db=db,
            user_info=user_info,
            function_name="qa_character_count",
            operation_name=f"Character Count ({len(files)} file{'s' if len(files) > 1 else ''})",
            file_info={"files": [f.filename for f in files]}
        )

        await self.emit_start_event(operation, user_info)

        try:
            file_paths = await self.save_uploaded_files(files, "Source file")

            # Parse custom symbols
            symbols = None
            if custom_symbols and custom_symbols.strip():
                symbols = list(custom_symbols.strip())

            background_tasks.add_task(
                self._run_qa_character_count_background,
                operation_id=operation.operation_id,
                user_info=user_info,
                file_paths=file_paths,
                symbols=symbols,
                symbol_set=symbol_set
            )

            return self.operation_started_response(
                operation_id=operation.operation_id,
                operation_name=operation.operation_name,
                additional_info={"files_count": len(files), "symbol_set": symbol_set}
            )

        except Exception as e:
            await self.handle_endpoint_error(
                error=e,
                user_info=user_info,
                function_name="qa_character_count",
                elapsed_time=time.time() - start_time,
                db=db,
                operation=operation
            )

    # ========================================================================
    # QA BACKGROUND TASKS
    # ========================================================================

    def _run_qa_extract_glossary_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        filter_sentences: bool,
        glossary_length_threshold: int,
        min_occurrence: int,
        sort_method: str
    ):
        """Background task for glossary extraction."""
        def task():
            logger.info(f"Extracting glossary from {len(file_paths)} files")
            result = qa_tools.extract_glossary(
                file_paths=file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold,
                min_occurrence=min_occurrence,
                sort_method=sort_method
            )
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="qa_extract_glossary",
            operation_name="Extract Glossary"
        )
        wrapped()

    def _run_qa_line_check_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        glossary_file_paths: Optional[List[str]],
        filter_sentences: bool,
        glossary_length_threshold: int
    ):
        """Background task for line check."""
        def task():
            logger.info(f"Running line check on {len(file_paths)} files")
            result = qa_tools.line_check(
                file_paths=file_paths,
                glossary_file_paths=glossary_file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold
            )
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="qa_line_check",
            operation_name="Line Check"
        )
        wrapped()

    def _run_qa_term_check_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        glossary_file_paths: Optional[List[str]],
        filter_sentences: bool,
        glossary_length_threshold: int,
        max_issues_per_term: int
    ):
        """Background task for term check."""
        def task():
            logger.info(f"Running term check on {len(file_paths)} files")
            result = qa_tools.term_check(
                file_paths=file_paths,
                glossary_file_paths=glossary_file_paths,
                filter_sentences=filter_sentences,
                glossary_length_threshold=glossary_length_threshold,
                max_issues_per_term=max_issues_per_term
            )
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="qa_term_check",
            operation_name="Term Check"
        )
        wrapped()

    def _run_qa_pattern_check_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str]
    ):
        """Background task for pattern check."""
        def task():
            logger.info(f"Running pattern check on {len(file_paths)} files")
            result = qa_tools.pattern_sequence_check(file_paths=file_paths)
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="qa_pattern_check",
            operation_name="Pattern Check"
        )
        wrapped()

    def _run_qa_character_count_background(
        self,
        operation_id: int,
        user_info: dict,
        file_paths: List[str],
        symbols: Optional[List[str]],
        symbol_set: str
    ):
        """Background task for character count check."""
        def task():
            logger.info(f"Running character count check on {len(file_paths)} files")
            result = qa_tools.character_count_check(
                file_paths=file_paths,
                symbols=symbols,
                symbol_set=symbol_set
            )
            return result

        wrapped = self.create_background_task(
            task_func=task,
            operation_id=operation_id,
            user_info=user_info,
            function_name="qa_character_count",
            operation_name="Character Count"
        )
        wrapped()


# ============================================================================
# INITIALIZE AND EXPORT ROUTER
# ============================================================================

quicksearch_api = QuickSearchAPI()
router = quicksearch_api.router
