"""
LDM Translation Memory Manager

Handles TM upload, parsing, and management.
REUSES existing file handlers for TXT and XML parsing.

Supported formats:
- TXT/TSV: Column 5 = Source, Column 6 = Target (via txt_handler.py)
- XML: StrOrigin = Source, Str = Target (via xml_handler.py)
- Excel: Column A (0) = Source, Column B (1) = Target (simple parser)

Uses bulk_insert_tm_entries() for high-performance import (20k+ entries/sec).
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Callable, BinaryIO
from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

# Reuse existing handlers
from server.tools.ldm.file_handlers.txt_handler import parse_txt_file
from server.tools.ldm.file_handlers.xml_handler import parse_xml_file

# Database utilities - COPY TEXT for 3-5x faster uploads (P21)
from server.database.db_utils import bulk_copy_tm_entries, bulk_insert_tm_entries
from server.database.models import LDMTranslationMemory, LDMTMEntry


class TMManager:
    """
    Translation Memory Manager for LDM.

    Handles:
    - TM file upload and parsing (TXT, XML, Excel)
    - Bulk import with progress tracking
    - TM CRUD operations
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # TM Upload and Parsing
    # =========================================================================

    def upload_tm(
        self,
        file_content: bytes,
        filename: str,
        name: str,
        owner_id: int,
        source_lang: str = "ko",
        target_lang: str = "en",
        description: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Upload and parse a TM file.

        Args:
            file_content: Raw file bytes
            filename: Original filename (determines parser)
            name: Display name for the TM
            owner_id: User ID of TM owner
            source_lang: Source language code (default: ko)
            target_lang: Target language code (default: en)
            description: Optional TM description
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with tm_id, entry_count, status, time_seconds
        """
        start_time = datetime.now()

        # Determine file type and parse
        file_ext = Path(filename).suffix.lower()

        logger.info(f"Uploading TM: {name} ({filename}) - {len(file_content):,} bytes")

        try:
            # Parse file based on type
            if file_ext in ['.txt', '.tsv']:
                entries = self._parse_txt_for_tm(file_content, filename)
            elif file_ext == '.xml':
                entries = self._parse_xml_for_tm(file_content, filename)
            elif file_ext in ['.xlsx', '.xls']:
                entries = self._parse_excel_for_tm(file_content, filename)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")

            if not entries:
                raise ValueError("No valid entries found in file")

            logger.info(f"Parsed {len(entries):,} TM entries from {filename}")

            # Create TM record
            tm = LDMTranslationMemory(
                name=name,
                description=description,
                owner_id=owner_id,
                source_lang=source_lang,
                target_lang=target_lang,
                entry_count=0,  # Will be updated after insert
                status="indexing"
            )
            self.db.add(tm)
            self.db.commit()

            logger.info(f"Created TM record: id={tm.id}")

            # Bulk insert entries using COPY TEXT (3-5x faster for PostgreSQL)
            inserted = bulk_copy_tm_entries(
                self.db,
                tm.id,
                entries,
                progress_callback=progress_callback
            )

            # Update TM record
            tm.entry_count = inserted
            tm.status = "ready"
            self.db.commit()

            elapsed = (datetime.now() - start_time).total_seconds()
            rate = inserted / elapsed if elapsed > 0 else 0

            logger.info(f"TM import complete: {inserted:,} entries in {elapsed:.2f}s ({rate:,.0f}/sec)")

            return {
                "tm_id": tm.id,
                "name": tm.name,
                "entry_count": inserted,
                "status": tm.status,
                "time_seconds": round(elapsed, 2),
                "rate_per_second": round(rate)
            }

        except Exception as e:
            logger.error(f"TM upload failed: {e}")
            raise

    # =========================================================================
    # Parsers - Convert to TM Entry Format
    # =========================================================================

    def _parse_txt_for_tm(self, file_content: bytes, filename: str) -> List[Dict]:
        """
        Parse TXT file for TM entries.
        REUSES txt_handler.py (Column 5 = Source, Column 6 = Target).
        """
        rows = parse_txt_file(file_content, filename)

        # Convert to TM entry format
        entries = []
        for row in rows:
            source = row.get("source")
            target = row.get("target")

            # TM entries need both source and target
            if source and target:
                entries.append({
                    "source_text": source,
                    "target_text": target
                })

        return entries

    def _parse_xml_for_tm(self, file_content: bytes, filename: str) -> List[Dict]:
        """
        Parse XML file for TM entries.
        REUSES xml_handler.py (StrOrigin = Source, Str = Target).
        """
        rows = parse_xml_file(file_content, filename)

        # Convert to TM entry format
        entries = []
        for row in rows:
            source = row.get("source")
            target = row.get("target")

            # TM entries need both source and target
            if source and target:
                entries.append({
                    "source_text": source,
                    "target_text": target
                })

        return entries

    def _parse_excel_for_tm(
        self,
        file_content: bytes,
        filename: str,
        source_col: int = 0,
        target_col: int = 1
    ) -> List[Dict]:
        """
        Parse Excel file for TM entries.
        Simple parser: Column A (0) = Source, Column B (1) = Target.

        Args:
            file_content: Raw Excel bytes
            filename: For logging
            source_col: Source column index (default: 0 = Column A)
            target_col: Target column index (default: 1 = Column B)
        """
        try:
            import openpyxl
            from io import BytesIO

            wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True, data_only=True)
            ws = wb.active

            entries = []
            for row_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
                if not row or len(row) <= max(source_col, target_col):
                    continue

                source = str(row[source_col] or "").strip()
                target = str(row[target_col] or "").strip()

                # TM entries need both source and target
                if source and target:
                    entries.append({
                        "source_text": source,
                        "target_text": target
                    })

            wb.close()
            logger.info(f"Parsed Excel {filename}: {len(entries)} TM entries")
            return entries

        except ImportError:
            logger.error("openpyxl not installed - cannot parse Excel files")
            raise ValueError("Excel support requires openpyxl package")
        except Exception as e:
            logger.error(f"Failed to parse Excel file {filename}: {e}")
            raise

    # =========================================================================
    # TM CRUD Operations
    # =========================================================================

    def list_tms(self, owner_id: Optional[int] = None) -> List[Dict]:
        """
        List all Translation Memories.

        Args:
            owner_id: Filter by owner (optional)

        Returns:
            List of TM info dicts
        """
        query = self.db.query(LDMTranslationMemory)

        if owner_id:
            query = query.filter(LDMTranslationMemory.owner_id == owner_id)

        tms = query.order_by(LDMTranslationMemory.created_at.desc()).all()

        return [
            {
                "id": tm.id,
                "name": tm.name,
                "description": tm.description,
                "source_lang": tm.source_lang,
                "target_lang": tm.target_lang,
                "entry_count": tm.entry_count,
                "status": tm.status,
                "created_at": tm.created_at.isoformat() if tm.created_at else None
            }
            for tm in tms
        ]

    def get_tm(self, tm_id: int) -> Optional[Dict]:
        """Get a single TM by ID."""
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            return None

        return {
            "id": tm.id,
            "name": tm.name,
            "description": tm.description,
            "source_lang": tm.source_lang,
            "target_lang": tm.target_lang,
            "entry_count": tm.entry_count,
            "status": tm.status,
            "created_at": tm.created_at.isoformat() if tm.created_at else None
        }

    def delete_tm(self, tm_id: int) -> bool:
        """
        Delete a Translation Memory and all its entries.

        Args:
            tm_id: TM ID to delete

        Returns:
            True if deleted, False if not found
        """
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            return False

        # Entries are deleted via CASCADE
        self.db.delete(tm)
        self.db.commit()

        logger.info(f"Deleted TM: id={tm_id} name={tm.name}")
        return True

    def add_entry(
        self,
        tm_id: int,
        source_text: str,
        target_text: str
    ) -> Optional[Dict]:
        """
        Add a single entry to a TM (for Adaptive TM feature).

        Args:
            tm_id: TM ID
            source_text: Source text
            target_text: Target text

        Returns:
            Entry info dict or None if TM not found
        """
        tm = self.db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            return None

        # Use COPY TEXT for consistency (handles hash generation)
        entries = [{"source_text": source_text, "target_text": target_text}]
        inserted = bulk_copy_tm_entries(self.db, tm_id, entries)

        if inserted > 0:
            # Update entry count
            tm.entry_count = (tm.entry_count or 0) + 1
            self.db.commit()

            return {
                "tm_id": tm_id,
                "source_text": source_text,
                "target_text": target_text,
                "entry_count": tm.entry_count
            }

        return None

    # =========================================================================
    # TM Search (Basic - Full 5-tier cascade in tm_search.py)
    # =========================================================================

    def search_exact(self, tm_id: int, source_text: str) -> Optional[Dict]:
        """
        Search for exact match in TM using hash.
        O(1) lookup using source_hash index.

        Args:
            tm_id: TM ID to search
            source_text: Source text to find

        Returns:
            Match dict or None
        """
        import hashlib
        from server.database.db_utils import normalize_text_for_hash

        # Generate hash for lookup
        normalized = normalize_text_for_hash(source_text)
        source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

        entry = self.db.query(LDMTMEntry).filter(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_hash == source_hash
        ).first()

        if entry:
            return {
                "source_text": entry.source_text,
                "target_text": entry.target_text,
                "similarity": 1.0,
                "tier": 1,
                "strategy": "perfect_whole_match"
            }

        return None

    def search_like(
        self,
        tm_id: int,
        pattern: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search TM using LIKE pattern (for quick suggestions).

        Args:
            tm_id: TM ID to search
            pattern: Search pattern (will be wrapped with %)
            limit: Max results

        Returns:
            List of matches
        """
        entries = self.db.query(LDMTMEntry).filter(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_text.ilike(f"%{pattern}%")
        ).limit(limit).all()

        return [
            {
                "source_text": e.source_text,
                "target_text": e.target_text,
                "similarity": 0.0,  # LIKE doesn't provide similarity
                "tier": 0,
                "strategy": "like_search"
            }
            for e in entries
        ]
