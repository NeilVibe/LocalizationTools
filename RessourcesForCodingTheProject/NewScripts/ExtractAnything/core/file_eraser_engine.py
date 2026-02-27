"""File Eraser engine – move files whose stem matches source stems to backup."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def collect_source_stems(source_folder: Path) -> set[str]:
    """Collect all file stems (case-insensitive) from *source_folder*."""
    stems: set[str] = set()
    for fpath in source_folder.rglob("*"):
        if fpath.is_file():
            stems.add(fpath.stem.lower())
    return stems


def find_matches(target_folder: Path, stems: set[str]) -> list[Path]:
    """Find all files in *target_folder* whose stem matches *stems*."""
    matches: list[Path] = []
    for fpath in sorted(target_folder.rglob("*")):
        if fpath.is_file() and fpath.stem.lower() in stems:
            matches.append(fpath)
    return matches


def erase_files(
    source_folder: Path,
    target_folder: Path,
    *,
    backup_dir: Path | None = None,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, Path]:
    """Move matched files to *backup_dir*.

    Returns ``(moved_count, backup_dir_used)``.
    """
    stems = collect_source_stems(source_folder)
    if not stems:
        if log_fn:
            log_fn("No source files found.", "warning")
        return 0, Path()

    if log_fn:
        log_fn(f"Collected {len(stems)} source stems.")

    matches = find_matches(target_folder, stems)
    if not matches:
        if log_fn:
            log_fn("No matching files in target folder.", "info")
        return 0, Path()

    if log_fn:
        log_fn(f"Found {len(matches)} files to move.")

    # Create backup directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if backup_dir is None:
        import config
        backup_dir = config.SCRIPT_DIR / f"Erased_Files_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for i, fpath in enumerate(matches, 1):
        if progress_fn:
            progress_fn(i * 100 // len(matches))

        dest = backup_dir / fpath.name
        # Collision handling
        if dest.exists():
            base = fpath.stem
            ext = fpath.suffix
            counter = 1
            while dest.exists():
                dest = backup_dir / f"{base}_{counter}{ext}"
                counter += 1

        try:
            shutil.move(str(fpath), str(dest))
            moved += 1
            if log_fn:
                log_fn(f"  Moved: {fpath.name}")
        except Exception as exc:
            if log_fn:
                log_fn(f"  Failed to move {fpath.name}: {exc}", "error")

    if log_fn:
        log_fn(f"Moved {moved}/{len(matches)} files → {backup_dir}", "success")

    return moved, backup_dir
