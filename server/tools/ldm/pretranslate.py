"""
LDM Unified Pretranslation Engine

Routes pretranslation requests to the appropriate engine:
- Standard TM: 5-tier cascade (hash + FAISS + ngram)
- XLS Transfer: Whole/split matching with code preservation
- KR Similar: Structure adaptation with triangle markers

Embedding Engine Usage:
- Standard TM: User's choice (Model2Vec fast / Qwen deep) via UI toggle
- XLS Transfer: Always Qwen (quality > speed for batch pretranslation)
- KR Similar: Always Qwen (quality > speed for batch pretranslation)

All engines use LOCAL processing (FAISS indexes). No external API required.
"""

from typing import List, Dict, Any, Optional, Callable
from loguru import logger
from sqlalchemy.orm import Session

from server.database.models import LDMRow, LDMFile, LDMTranslationMemory


class PretranslationEngine:
    """
    Unified pretranslation with engine selection.

    Engines:
    - standard: TM 5-tier cascade (tm_indexer.py)
    - xls_transfer: XLS Transfer logic (xlstransfer/translation.py)
    - kr_similar: KR Similar logic (kr_similar/searcher.py)
    """

    def __init__(self, db: Session):
        self.db = db
        self._tm_searcher = None
        self._xls_manager = None
        self._kr_searcher = None

    def pretranslate(
        self,
        file_id: int,
        engine: str,
        dictionary_id: int,
        threshold: float = 0.92,
        skip_existing: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Pretranslate a file using selected engine.
        P9: Supports both PostgreSQL and SQLite (local) files.

        Args:
            file_id: LDM file ID to pretranslate
            engine: "standard" | "xls_transfer" | "kr_similar"
            dictionary_id: TM ID (for standard) or dictionary ID (for xls/kr)
            threshold: Similarity threshold (default 0.92)
            skip_existing: Skip rows that already have translations
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with stats: matched, skipped, total, time_seconds
        """
        from datetime import datetime
        start_time = datetime.now()

        # Try PostgreSQL first
        file = self.db.query(LDMFile).filter(LDMFile.id == file_id).first()
        is_local_file = False

        if not file:
            # P9: Fallback to SQLite for local files
            import asyncio
            from server.database.offline import get_offline_db
            offline_db = get_offline_db()
            local_file = asyncio.run(offline_db.get_local_file(file_id))
            if not local_file:
                raise ValueError(f"File not found: id={file_id}")
            is_local_file = True

        if is_local_file:
            # P9: Get rows from SQLite
            rows = self._get_local_rows(file_id, skip_existing)
        else:
            # Get rows from PostgreSQL
            rows_query = self.db.query(LDMRow).filter(LDMRow.file_id == file_id)

            if skip_existing:
                # Skip rows with non-empty target
                rows_query = rows_query.filter(
                    (LDMRow.target == None) | (LDMRow.target == "")
                )

            rows = rows_query.order_by(LDMRow.row_num).all()

        if not rows:
            return {
                "matched": 0,
                "skipped": 0,
                "total": 0,
                "time_seconds": 0,
                "message": "No rows to pretranslate"
            }

        logger.info(f"Pretranslating {len(rows)} rows from file {file_id} using {engine} engine")

        # Route to engine
        if engine == "standard":
            result = self._pretranslate_standard(rows, dictionary_id, threshold, progress_callback)
        elif engine == "xls_transfer":
            result = self._pretranslate_xls_transfer(rows, dictionary_id, threshold, progress_callback)
        elif engine == "kr_similar":
            result = self._pretranslate_kr_similar(rows, dictionary_id, threshold, progress_callback)
        else:
            raise ValueError(f"Unknown engine: {engine}")

        elapsed = (datetime.now() - start_time).total_seconds()
        result["time_seconds"] = round(elapsed, 2)
        result["engine"] = engine
        result["file_id"] = file_id

        logger.info(f"Pretranslation complete: {result['matched']}/{result['total']} matched in {elapsed:.2f}s")

        return result

    def _pretranslate_standard(
        self,
        rows: List[LDMRow],
        tm_id: int,
        threshold: float,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> Dict[str, Any]:
        """
        Pretranslate using Standard TM (5-tier cascade).

        Uses TMSearcher from tm_indexer.py.
        Includes staleness check and incremental sync (BUG-014, BUG-015, BUG-022).
        """
        from server.tools.ldm.tm_indexer import TMIndexer, TMSearcher
        from datetime import datetime

        # Verify TM exists
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            raise ValueError(f"TM not found: id={tm_id}")

        # Load TM indexes
        indexer = TMIndexer(self.db)

        # Check if indexes exist
        try:
            indexes = indexer.load_indexes(tm_id)
        except FileNotFoundError:
            indexes = None

        # BUG-014/BUG-015: Staleness check and auto-rebuild
        needs_rebuild = False

        if not indexes or not indexes.get("whole_lookup"):
            # No indexes exist - need to build
            logger.info(f"No indexes found for TM {tm_id}, building...")
            needs_rebuild = True
        elif tm.indexed_at is None:
            # Never indexed - need to build
            logger.info(f"TM {tm_id} was never indexed, building...")
            needs_rebuild = True
        elif tm.updated_at and tm.indexed_at < tm.updated_at:
            # TM was modified since last index - rebuild
            logger.info(f"TM {tm_id} is stale (indexed: {tm.indexed_at}, updated: {tm.updated_at}), rebuilding...")
            needs_rebuild = True

        if needs_rebuild:
            # BUG-022 FIX: Use incremental sync instead of full rebuild
            # TASK-001: Track sync with TrackedOperation for UI feedback
            from server.tools.ldm.tm_indexer import TMSyncManager
            from server.utils.progress_tracker import TrackedOperation

            logger.info(f"Syncing indexes for TM {tm_id} (incremental update)...")

            with TrackedOperation(
                operation_name=f"Sync TM: {tm.name}",
                user_id=tm.owner_id,
                tool_name="LDM",
                function_name="sync_tm",
                parameters={"tm_id": tm_id}
            ) as tracker:
                tracker.update(10, "Computing diff...")
                sync_manager = TMSyncManager(self.db, tm_id)
                sync_result = sync_manager.sync()
                tracker.update(100, f"Done: +{sync_result['stats']['insert']} ~{sync_result['stats']['update']}")

            logger.info(f"TM sync complete: INSERT={sync_result['stats']['insert']}, UPDATE={sync_result['stats']['update']}, UNCHANGED={sync_result['stats']['unchanged']}")
            indexes = indexer.load_indexes(tm_id)

            # Update indexed_at timestamp
            tm.indexed_at = datetime.utcnow()
            self.db.commit()

        if not indexes:
            raise ValueError(f"Failed to load indexes for TM {tm_id}")

        # Create searcher
        searcher = TMSearcher(indexes, threshold=threshold)

        total = len(rows)
        matched = 0
        skipped = 0

        for i, row in enumerate(rows):
            if not row.source or not row.source.strip():
                skipped += 1
                continue

            # Search TM - get multiple results to check StringID variations
            result = searcher.search(row.source, top_k=10, threshold=threshold)

            if result["results"]:
                best_match = None

                # If row has StringID, try to find matching variation
                if row.string_id:
                    # DEBUG: Log StringID matching (INFO level to see in CI)
                    result_string_ids = [m.get("string_id") for m in result["results"]]
                    logger.info(f"DEBUG StringID: Looking for '{row.string_id}' in {result_string_ids}")

                    for match in result["results"]:
                        if match.get("string_id") == row.string_id:
                            best_match = match
                            logger.debug(f"DEBUG StringID: Matched! target='{best_match['target_text']}'")
                            break

                # Fallback to first result if no StringID match
                if not best_match:
                    best_match = result["results"][0]
                    if row.string_id:
                        logger.warning(f"DEBUG StringID: No match found for '{row.string_id}', using fallback")

                row.target = best_match["target_text"]
                matched += 1

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)

        self.db.commit()

        return {
            "matched": matched,
            "skipped": skipped,
            "total": total,
            "threshold": threshold
        }

    def _pretranslate_xls_transfer(
        self,
        rows: List[LDMRow],
        dictionary_id: int,
        threshold: float,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> Dict[str, Any]:
        """
        Pretranslate using XLS Transfer engine.

        Uses translate_text_multi_mode from xlstransfer/translation.py.
        Preserves game codes ({ItemID}, <PAColor>, etc.).
        Includes staleness check and incremental sync (BUG-014, BUG-015, BUG-022).
        """
        # Factor Power: Import from centralized utils where possible
        from server.utils.code_patterns import simple_number_replace
        # ML components still from xlstransfer (TODO: move to utils when ready)
        from server.tools.xlstransfer.translation import translate_text_multi_mode
        from server.tools.xlstransfer.embeddings import EmbeddingsManager
        from datetime import datetime

        # BUG-014/BUG-015: Staleness check before loading
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == dictionary_id
        ).first()

        if tm:
            # Check if TM is stale and needs sync
            if tm.indexed_at is None or (tm.updated_at and tm.indexed_at < tm.updated_at):
                # BUG-022 FIX: Use incremental sync instead of full rebuild
                # TASK-001: Track sync with TrackedOperation for UI feedback
                from server.tools.ldm.tm_indexer import TMSyncManager
                from server.utils.progress_tracker import TrackedOperation

                logger.info(f"TM {dictionary_id} is stale for XLS Transfer, syncing indexes (incremental)...")

                with TrackedOperation(
                    operation_name=f"Sync TM: {tm.name}",
                    user_id=tm.owner_id,
                    tool_name="LDM",
                    function_name="sync_tm",
                    parameters={"tm_id": dictionary_id, "engine": "xls_transfer"}
                ) as tracker:
                    tracker.update(10, "Computing diff...")
                    sync_manager = TMSyncManager(self.db, dictionary_id)
                    sync_result = sync_manager.sync()
                    tracker.update(100, f"Done: +{sync_result['stats']['insert']} ~{sync_result['stats']['update']}")

                logger.info(f"TM sync complete: INSERT={sync_result['stats']['insert']}, UPDATE={sync_result['stats']['update']}, UNCHANGED={sync_result['stats']['unchanged']}")
                tm.indexed_at = datetime.utcnow()
                self.db.commit()

        # Load TM using EmbeddingsManager
        embeddings_mgr = EmbeddingsManager()

        # Load TM data (load_dictionary now accepts tm_id)
        if not embeddings_mgr.load_dictionary(dictionary_id):
            raise ValueError(f"Failed to load TM {dictionary_id} for XLS Transfer")

        total = len(rows)
        matched = 0
        skipped = 0

        for i, row in enumerate(rows):
            if not row.source or not row.source.strip():
                skipped += 1
                continue

            # Translate using XLS Transfer
            translation = translate_text_multi_mode(
                row.source,
                split_index=embeddings_mgr.split_index,
                split_sentences=embeddings_mgr.split_sentences,
                split_dict=embeddings_mgr.split_dict,
                whole_index=embeddings_mgr.whole_index,
                whole_sentences=embeddings_mgr.whole_sentences,
                whole_dict=embeddings_mgr.whole_dict,
                threshold=threshold,
                model=embeddings_mgr.model
            )

            if translation:
                # Apply code preservation
                final_translation = simple_number_replace(row.source, translation)
                row.target = final_translation
                matched += 1

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)

        self.db.commit()

        return {
            "matched": matched,
            "skipped": skipped,
            "total": total,
            "threshold": threshold
        }

    def _pretranslate_kr_similar(
        self,
        rows: List[LDMRow],
        dictionary_id: int,
        threshold: float,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> Dict[str, Any]:
        """
        Pretranslate using KR Similar engine.

        Uses SimilaritySearcher from kr_similar/searcher.py.
        Handles structure adaptation and triangle markers.
        Includes staleness check and incremental sync (BUG-014, BUG-015, BUG-022).
        """
        # Factor Power: Import from centralized utils where possible
        from server.utils.code_patterns import adapt_structure
        from server.utils.text_utils import normalize_korean_text as normalize_text
        # ML components still from kr_similar (TODO: move to utils when ready)
        from server.tools.kr_similar.searcher import SimilaritySearcher
        from server.tools.kr_similar.embeddings import EmbeddingsManager
        from datetime import datetime

        # BUG-014/BUG-015: Staleness check before loading
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == dictionary_id
        ).first()

        if tm:
            # Check if TM is stale and needs sync
            if tm.indexed_at is None or (tm.updated_at and tm.indexed_at < tm.updated_at):
                # BUG-022 FIX: Use incremental sync instead of full rebuild
                # TASK-001: Track sync with TrackedOperation for UI feedback
                from server.tools.ldm.tm_indexer import TMSyncManager
                from server.utils.progress_tracker import TrackedOperation

                logger.info(f"TM {dictionary_id} is stale for KR Similar, syncing indexes (incremental)...")

                with TrackedOperation(
                    operation_name=f"Sync TM: {tm.name}",
                    user_id=tm.owner_id,
                    tool_name="LDM",
                    function_name="sync_tm",
                    parameters={"tm_id": dictionary_id, "engine": "kr_similar"}
                ) as tracker:
                    tracker.update(10, "Computing diff...")
                    sync_manager = TMSyncManager(self.db, dictionary_id)
                    sync_result = sync_manager.sync()
                    tracker.update(100, f"Done: +{sync_result['stats']['insert']} ~{sync_result['stats']['update']}")

                logger.info(f"TM sync complete: INSERT={sync_result['stats']['insert']}, UPDATE={sync_result['stats']['update']}, UNCHANGED={sync_result['stats']['unchanged']}")
                tm.indexed_at = datetime.utcnow()
                self.db.commit()

        # Load TM (not dictionary - dictionary_id is actually tm_id)
        embeddings_mgr = EmbeddingsManager()

        # Use load_tm for TM-based pretranslation
        if not embeddings_mgr.load_tm(dictionary_id):
            raise ValueError(f"Failed to load TM {dictionary_id} for KR Similar")

        # Create searcher
        searcher = SimilaritySearcher(embeddings_manager=embeddings_mgr)

        total = len(rows)
        matched = 0
        skipped = 0

        for i, row in enumerate(rows):
            if not row.source or not row.source.strip():
                skipped += 1
                continue

            source_text = row.source
            translation = None

            # Handle triangle markers (line-by-line) using find_similar for each line
            if '\u25b6' in source_text or '\n' in source_text:
                # Line-by-line matching
                lines = source_text.replace('\\n', '\n').split('\n')
                translated_lines = []
                any_match = False

                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:
                        translated_lines.append('')
                        continue

                    # Remove triangle marker for search
                    search_text = line_stripped.lstrip('\u25b6').strip()
                    if not search_text:
                        translated_lines.append(line_stripped)
                        continue

                    # Search using find_similar (split mode for lines)
                    results = searcher.find_similar(
                        search_text,
                        threshold=threshold,
                        top_k=1,
                        use_whole=False
                    )

                    if results:
                        trans = results[0].get("translation", "")
                        # Preserve triangle marker if original had it
                        if line_stripped.startswith('\u25b6'):
                            translated_lines.append('\u25b6' + trans)
                        else:
                            translated_lines.append(trans)
                        any_match = True
                    else:
                        translated_lines.append(line_stripped)

                if any_match:
                    translation = '\n'.join(translated_lines)
            else:
                # Whole text matching
                results = searcher.find_similar(
                    source_text,
                    threshold=threshold,
                    top_k=1,
                    use_whole=True
                )

                if results:
                    trans = results[0].get("translation", "")
                    # Apply structure adaptation
                    translation = adapt_structure(source_text, trans)

            if translation:
                row.target = translation
                matched += 1

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)

        self.db.commit()

        return {
            "matched": matched,
            "skipped": skipped,
            "total": total,
            "threshold": threshold
        }

    def _get_local_rows(self, file_id: int, skip_existing: bool) -> List:
        """
        P9: Get rows from SQLite for local files.
        Returns row-like objects compatible with the pretranslation engines.
        """
        import asyncio
        from server.database.offline import get_offline_db

        offline_db = get_offline_db()
        rows_data = asyncio.run(offline_db.get_rows_for_file(file_id))

        if skip_existing:
            rows_data = [r for r in rows_data if not r.get("target")]

        # Sort by row_num
        rows_data.sort(key=lambda x: x.get("row_num", 0))

        # Create row-like objects
        class RowLike:
            def __init__(self, data, offline_db):
                self.id = data.get("id")
                self.file_id = data.get("file_id")
                self.row_num = data.get("row_num", 0)
                self.string_id = data.get("string_id", "")
                self.source = data.get("source", "")
                self.target = data.get("target", "")
                self.status = data.get("status", "pending")
                self._offline_db = offline_db
                self._is_local = True

            def __setattr__(self, name, value):
                if name.startswith('_') or name in ('id', 'file_id', 'row_num', 'string_id', 'source', 'status'):
                    object.__setattr__(self, name, value)
                elif name == 'target':
                    object.__setattr__(self, name, value)
                    # P9: Immediately save to SQLite when target is updated
                    if hasattr(self, '_is_local') and self._is_local:
                        try:
                            import asyncio
                            asyncio.run(self._offline_db.update_row_in_local_file(self.id, target=value))
                        except Exception as e:
                            logger.warning(f"P9: Failed to save target to SQLite: {e}")

        return [RowLike(r, offline_db) for r in rows_data]


def pretranslate_file(
    db: Session,
    file_id: int,
    engine: str,
    dictionary_id: int,
    threshold: float = 0.92,
    skip_existing: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    """
    Convenience function for pretranslating a file.

    Args:
        db: Database session
        file_id: LDM file ID
        engine: "standard" | "xls_transfer" | "kr_similar"
        dictionary_id: TM ID or dictionary ID
        threshold: Similarity threshold
        skip_existing: Skip rows with existing translations
        progress_callback: Optional progress callback

    Returns:
        Pretranslation result dict
    """
    engine_instance = PretranslationEngine(db)
    return engine_instance.pretranslate(
        file_id=file_id,
        engine=engine,
        dictionary_id=dictionary_id,
        threshold=threshold,
        skip_existing=skip_existing,
        progress_callback=progress_callback
    )
