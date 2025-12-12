"""
LDM Backup Service

Smart backup system for disaster recovery:
- Automatic backups before destructive operations (pre_delete, pre_import)
- Scheduled backups (daily/weekly)
- Project/file/TM specific backups
- Retention policy with auto-cleanup
- Restore functionality
"""

import os
import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from sqlalchemy.orm import Session
from server.database.models import (
    LDMBackup, LDMProject, LDMFolder, LDMFile, LDMRow,
    LDMEditHistory, LDMTranslationMemory, LDMTMEntry
)
from server.database.db_utils import chunked_query


class BackupService:
    """
    Smart backup service for LDM data.

    Backup types:
    - full: All LDM tables (disaster recovery)
    - project: Single project + files + rows + history
    - file: Single file + rows + history
    - tm: Single TM + entries

    Triggers:
    - pre_delete: Before deleting project/file/TM
    - pre_import: Before large TM import (>10k entries)
    - scheduled: Daily/weekly automatic backup
    - manual: User-initiated backup
    """

    # Retention policies (days) - SMART EXPIRATION
    RETENTION = {
        "pre_delete": 7,     # Keep delete backups 7 days (recoverable window)
        "pre_import": 3,     # Keep import backups 3 days (rollback window)
        "scheduled": 7,      # Keep scheduled backups 7 days
        "manual": 30,        # Keep manual backups 30 days (user-initiated)
    }

    # Max backups to keep per type (prevents disk bloat)
    MAX_BACKUPS = {
        "full": 3,           # Only 3 full backups (they're big)
        "project": 5,        # 5 per project type
        "file": 10,          # 10 file backups
        "tm": 5,             # 5 TM backups
    }

    # Compression enabled by default (saves 70-90% space)
    USE_COMPRESSION = True

    def __init__(self, backup_dir: str = None):
        """
        Initialize backup service.

        Args:
            backup_dir: Directory to store backups. Defaults to server/data/backups/
        """
        if backup_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "data" / "backups"
        else:
            base_dir = Path(backup_dir)

        self.backup_dir = base_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BackupService initialized: {self.backup_dir}")

    # =========================================================================
    # Core Backup Methods
    # =========================================================================

    def create_backup(
        self,
        db: Session,
        backup_type: str,
        trigger: str,
        project_id: int = None,
        file_id: int = None,
        tm_id: int = None,
        user_id: int = None,
        description: str = None
    ) -> Optional[LDMBackup]:
        """
        Create a backup.

        Args:
            db: Database session
            backup_type: "full", "project", "file", or "tm"
            trigger: "pre_delete", "pre_import", "scheduled", or "manual"
            project_id: Project ID (for project backup)
            file_id: File ID (for file backup)
            tm_id: TM ID (for TM backup)
            user_id: User who triggered the backup
            description: Optional description

        Returns:
            LDMBackup record or None if failed
        """
        try:
            # Generate backup filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{backup_type}_{trigger}_{timestamp}"

            if project_id:
                backup_name = f"project_{project_id}_{trigger}_{timestamp}"
            elif file_id:
                backup_name = f"file_{file_id}_{trigger}_{timestamp}"
            elif tm_id:
                backup_name = f"tm_{tm_id}_{trigger}_{timestamp}"

            backup_path = self.backup_dir / f"{backup_name}.json"

            # Collect data based on type
            logger.info(f"Creating {backup_type} backup: {backup_name}")

            if backup_type == "full":
                data = self._collect_full_backup(db)
            elif backup_type == "project":
                data = self._collect_project_backup(db, project_id)
            elif backup_type == "file":
                data = self._collect_file_backup(db, file_id)
            elif backup_type == "tm":
                data = self._collect_tm_backup(db, tm_id)
            else:
                logger.error(f"Unknown backup type: {backup_type}")
                return None

            # Add metadata
            data["_metadata"] = {
                "backup_type": backup_type,
                "trigger": trigger,
                "timestamp": datetime.utcnow().isoformat(),
                "description": description,
                "version": "1.0",
                "compressed": self.USE_COMPRESSION
            }

            # Write backup file (with optional gzip compression)
            if self.USE_COMPRESSION:
                backup_path = self.backup_dir / f"{backup_name}.json.gz"
                json_bytes = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
                with gzip.open(backup_path, "wb", compresslevel=6) as f:
                    f.write(json_bytes)
                uncompressed_size = len(json_bytes)
                file_size = backup_path.stat().st_size
                compression_ratio = (1 - file_size / uncompressed_size) * 100 if uncompressed_size > 0 else 0
                logger.info(f"Compressed backup: {file_size} bytes ({compression_ratio:.1f}% saved)")
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                file_size = backup_path.stat().st_size

            # Calculate expiration
            retention_days = self.RETENTION.get(trigger, 30)
            expires_at = datetime.utcnow() + timedelta(days=retention_days)

            # Create backup record
            backup = LDMBackup(
                backup_type=backup_type,
                project_id=project_id,
                file_id=file_id,
                tm_id=tm_id,
                backup_path=str(backup_path),
                file_size=file_size,
                status="completed",
                trigger=trigger,
                created_by=user_id,
                expires_at=expires_at
            )

            db.add(backup)
            db.commit()

            logger.success(f"Backup created: {backup_path} ({file_size} bytes)")

            # Cleanup old backups
            self._cleanup_old_backups(db, backup_type)

            return backup

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Record failed backup
            backup = LDMBackup(
                backup_type=backup_type,
                project_id=project_id,
                file_id=file_id,
                tm_id=tm_id,
                backup_path="",
                status="failed",
                error_message=str(e),
                trigger=trigger,
                created_by=user_id
            )
            db.add(backup)
            db.commit()
            return None

    # =========================================================================
    # Data Collection Methods
    # =========================================================================

    def _collect_full_backup(self, db: Session) -> Dict[str, Any]:
        """Collect all LDM data for full backup."""
        data = {
            "projects": [],
            "folders": [],
            "files": [],
            "rows": [],
            "edit_history": [],
            "tms": [],
            "tm_entries": []
        }

        # Projects
        for p in db.query(LDMProject).all():
            data["projects"].append({
                "id": p.id, "name": p.name, "owner_id": p.owner_id,
                "description": p.description, "created_at": p.created_at
            })

        # Folders
        for f in db.query(LDMFolder).all():
            data["folders"].append({
                "id": f.id, "project_id": f.project_id, "parent_id": f.parent_id,
                "name": f.name, "created_at": f.created_at
            })

        # Files
        for f in db.query(LDMFile).all():
            data["files"].append({
                "id": f.id, "project_id": f.project_id, "folder_id": f.folder_id,
                "name": f.name, "original_filename": f.original_filename,
                "format": f.format, "row_count": f.row_count,
                "source_language": f.source_language, "target_language": f.target_language
            })

        # Rows (can be large!) - use chunked query to avoid OOM
        for chunk in chunked_query(db, LDMRow, [], chunk_size=5000):
            for r in chunk:
                data["rows"].append({
                    "id": r.id, "file_id": r.file_id, "row_num": r.row_num,
                    "string_id": r.string_id, "source": r.source, "target": r.target,
                    "status": r.status
                })

        # TMs
        for tm in db.query(LDMTranslationMemory).all():
            data["tms"].append({
                "id": tm.id, "name": tm.name, "owner_id": tm.owner_id,
                "source_lang": tm.source_lang, "target_lang": tm.target_lang,
                "entry_count": tm.entry_count, "status": tm.status
            })

        # TM Entries (can be very large!) - use chunked query to avoid OOM
        for chunk in chunked_query(db, LDMTMEntry, [], chunk_size=5000):
            for e in chunk:
                data["tm_entries"].append({
                    "id": e.id, "tm_id": e.tm_id,
                    "source_text": e.source_text, "target_text": e.target_text,
                    "source_hash": e.source_hash
                })

        logger.info(f"Full backup: {len(data['projects'])} projects, {len(data['files'])} files, {len(data['rows'])} rows")
        return data

    def _collect_project_backup(self, db: Session, project_id: int) -> Dict[str, Any]:
        """Collect single project data."""
        data = {"project": None, "folders": [], "files": [], "rows": [], "edit_history": []}

        project = db.query(LDMProject).filter(LDMProject.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        data["project"] = {
            "id": project.id, "name": project.name, "owner_id": project.owner_id,
            "description": project.description
        }

        # Folders
        for f in db.query(LDMFolder).filter(LDMFolder.project_id == project_id).all():
            data["folders"].append({"id": f.id, "parent_id": f.parent_id, "name": f.name})

        # Files
        file_ids = []
        for f in db.query(LDMFile).filter(LDMFile.project_id == project_id).all():
            file_ids.append(f.id)
            data["files"].append({
                "id": f.id, "folder_id": f.folder_id, "name": f.name,
                "original_filename": f.original_filename, "format": f.format,
                "row_count": f.row_count
            })

        # Rows
        for r in db.query(LDMRow).filter(LDMRow.file_id.in_(file_ids)).all():
            data["rows"].append({
                "id": r.id, "file_id": r.file_id, "row_num": r.row_num,
                "string_id": r.string_id, "source": r.source, "target": r.target,
                "status": r.status
            })

        # Edit history
        row_ids = [r["id"] for r in data["rows"]]
        for h in db.query(LDMEditHistory).filter(LDMEditHistory.row_id.in_(row_ids)).all():
            data["edit_history"].append({
                "id": h.id, "row_id": h.row_id, "user_id": h.user_id,
                "old_target": h.old_target, "new_target": h.new_target,
                "edited_at": h.edited_at
            })

        logger.info(f"Project backup: {len(data['files'])} files, {len(data['rows'])} rows")
        return data

    def _collect_file_backup(self, db: Session, file_id: int) -> Dict[str, Any]:
        """Collect single file data."""
        data = {"file": None, "rows": [], "edit_history": []}

        file = db.query(LDMFile).filter(LDMFile.id == file_id).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        data["file"] = {
            "id": file.id, "project_id": file.project_id, "folder_id": file.folder_id,
            "name": file.name, "original_filename": file.original_filename,
            "format": file.format, "row_count": file.row_count
        }

        # Rows
        row_ids = []
        for r in db.query(LDMRow).filter(LDMRow.file_id == file_id).all():
            row_ids.append(r.id)
            data["rows"].append({
                "id": r.id, "row_num": r.row_num, "string_id": r.string_id,
                "source": r.source, "target": r.target, "status": r.status
            })

        # Edit history
        for h in db.query(LDMEditHistory).filter(LDMEditHistory.row_id.in_(row_ids)).all():
            data["edit_history"].append({
                "id": h.id, "row_id": h.row_id, "user_id": h.user_id,
                "old_target": h.old_target, "new_target": h.new_target,
                "edited_at": h.edited_at
            })

        logger.info(f"File backup: {len(data['rows'])} rows, {len(data['edit_history'])} history entries")
        return data

    def _collect_tm_backup(self, db: Session, tm_id: int) -> Dict[str, Any]:
        """Collect single TM data."""
        data = {"tm": None, "entries": []}

        tm = db.query(LDMTranslationMemory).filter(LDMTranslationMemory.id == tm_id).first()
        if not tm:
            raise ValueError(f"TM {tm_id} not found")

        data["tm"] = {
            "id": tm.id, "name": tm.name, "owner_id": tm.owner_id,
            "source_lang": tm.source_lang, "target_lang": tm.target_lang,
            "entry_count": tm.entry_count, "status": tm.status
        }

        # Entries
        for e in db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm_id).all():
            data["entries"].append({
                "id": e.id, "source_text": e.source_text, "target_text": e.target_text,
                "source_hash": e.source_hash
            })

        logger.info(f"TM backup: {len(data['entries'])} entries")
        return data

    # =========================================================================
    # Cleanup & Maintenance
    # =========================================================================

    def _cleanup_old_backups(self, db: Session, backup_type: str):
        """Remove old backups based on retention policy."""
        now = datetime.utcnow()

        # Remove expired backups
        expired = db.query(LDMBackup).filter(
            LDMBackup.expires_at < now,
            LDMBackup.status == "completed"
        ).all()

        for backup in expired:
            self._delete_backup_file(backup.backup_path)
            db.delete(backup)
            logger.info(f"Deleted expired backup: {backup.backup_path}")

        # Keep only MAX_BACKUPS per type
        max_count = self.MAX_BACKUPS.get(backup_type, 10)
        all_backups = db.query(LDMBackup).filter(
            LDMBackup.backup_type == backup_type,
            LDMBackup.status == "completed"
        ).order_by(LDMBackup.created_at.desc()).all()

        if len(all_backups) > max_count:
            for backup in all_backups[max_count:]:
                self._delete_backup_file(backup.backup_path)
                db.delete(backup)
                logger.info(f"Deleted excess backup: {backup.backup_path}")

        db.commit()

    def _delete_backup_file(self, backup_path: str):
        """Safely delete a backup file."""
        try:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
        except Exception as e:
            logger.warning(f"Could not delete backup file {backup_path}: {e}")

    # =========================================================================
    # Restore Methods
    # =========================================================================

    def restore_backup(self, db: Session, backup_id: int) -> bool:
        """
        Restore from a backup.

        Args:
            db: Database session
            backup_id: ID of backup to restore

        Returns:
            True if successful
        """
        backup = db.query(LDMBackup).filter(LDMBackup.id == backup_id).first()
        if not backup:
            logger.error(f"Backup {backup_id} not found")
            return False

        if backup.status != "completed":
            logger.error(f"Cannot restore backup with status: {backup.status}")
            return False

        if not os.path.exists(backup.backup_path):
            logger.error(f"Backup file not found: {backup.backup_path}")
            return False

        try:
            # Update status
            backup.status = "restoring"
            db.commit()

            # Load backup data (handle compressed and uncompressed)
            if backup.backup_path.endswith(".gz"):
                with gzip.open(backup.backup_path, "rb") as f:
                    data = json.loads(f.read().decode("utf-8"))
            else:
                with open(backup.backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            # Restore based on type
            if backup.backup_type == "file":
                self._restore_file_backup(db, data)
            elif backup.backup_type == "project":
                self._restore_project_backup(db, data)
            elif backup.backup_type == "tm":
                self._restore_tm_backup(db, data)
            else:
                logger.warning(f"Full restore not implemented (too dangerous)")
                backup.status = "completed"
                db.commit()
                return False

            backup.status = "completed"
            db.commit()
            logger.success(f"Backup {backup_id} restored successfully")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            backup.status = "completed"  # Reset status
            backup.error_message = f"Restore failed: {e}"
            db.commit()
            return False

    def _restore_file_backup(self, db: Session, data: Dict):
        """Restore a file backup (rows only, preserves file record)."""
        file_id = data["file"]["id"]

        # Delete existing rows
        db.query(LDMRow).filter(LDMRow.file_id == file_id).delete()

        # Restore rows
        for r in data["rows"]:
            row = LDMRow(
                file_id=file_id,
                row_num=r["row_num"],
                string_id=r.get("string_id"),
                source=r.get("source"),
                target=r.get("target"),
                status=r.get("status", "pending")
            )
            db.add(row)

        db.commit()
        logger.info(f"Restored {len(data['rows'])} rows for file {file_id}")

    def _restore_project_backup(self, db: Session, data: Dict):
        """Restore project backup."""
        # This would restore files and rows
        # Implementation depends on whether we want to merge or replace
        logger.warning("Project restore: merging rows into existing files")

        for file_data in data["files"]:
            file_id = file_data["id"]
            file_rows = [r for r in data["rows"] if r["file_id"] == file_id]

            # Delete existing rows
            db.query(LDMRow).filter(LDMRow.file_id == file_id).delete()

            # Restore rows
            for r in file_rows:
                row = LDMRow(
                    file_id=file_id,
                    row_num=r["row_num"],
                    string_id=r.get("string_id"),
                    source=r.get("source"),
                    target=r.get("target"),
                    status=r.get("status", "pending")
                )
                db.add(row)

        db.commit()

    def _restore_tm_backup(self, db: Session, data: Dict):
        """Restore TM backup."""
        tm_id = data["tm"]["id"]

        # Delete existing entries
        db.query(LDMTMEntry).filter(LDMTMEntry.tm_id == tm_id).delete()

        # Restore entries
        for e in data["entries"]:
            entry = LDMTMEntry(
                tm_id=tm_id,
                source_text=e["source_text"],
                target_text=e.get("target_text"),
                source_hash=e["source_hash"]
            )
            db.add(entry)

        db.commit()
        logger.info(f"Restored {len(data['entries'])} entries for TM {tm_id}")

    # =========================================================================
    # Convenience Methods (call before destructive operations)
    # =========================================================================

    def backup_before_delete_project(self, db: Session, project_id: int, user_id: int = None) -> Optional[LDMBackup]:
        """Create backup before deleting a project."""
        return self.create_backup(
            db, backup_type="project", trigger="pre_delete",
            project_id=project_id, user_id=user_id,
            description=f"Auto-backup before project deletion"
        )

    def backup_before_delete_file(self, db: Session, file_id: int, user_id: int = None) -> Optional[LDMBackup]:
        """Create backup before deleting a file."""
        return self.create_backup(
            db, backup_type="file", trigger="pre_delete",
            file_id=file_id, user_id=user_id,
            description=f"Auto-backup before file deletion"
        )

    def backup_before_delete_tm(self, db: Session, tm_id: int, user_id: int = None) -> Optional[LDMBackup]:
        """Create backup before deleting a TM."""
        return self.create_backup(
            db, backup_type="tm", trigger="pre_delete",
            tm_id=tm_id, user_id=user_id,
            description=f"Auto-backup before TM deletion"
        )

    def backup_before_import(self, db: Session, tm_id: int, entry_count: int, user_id: int = None) -> Optional[LDMBackup]:
        """Create backup before large TM import (>10k entries)."""
        if entry_count < 10000:
            logger.debug(f"Skipping pre-import backup ({entry_count} entries < 10k threshold)")
            return None

        return self.create_backup(
            db, backup_type="tm", trigger="pre_import",
            tm_id=tm_id, user_id=user_id,
            description=f"Auto-backup before importing {entry_count} entries"
        )

    def scheduled_full_backup(self, db: Session) -> Optional[LDMBackup]:
        """Create scheduled full backup."""
        return self.create_backup(
            db, backup_type="full", trigger="scheduled",
            description="Scheduled full backup"
        )


# Singleton instance
_backup_service: Optional[BackupService] = None

def get_backup_service() -> BackupService:
    """Get or create backup service singleton."""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service
