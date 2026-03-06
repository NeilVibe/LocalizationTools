"""
WEM Audio Index Utilities.

Scans audio folders for .wem files to determine HasAudio status.
Uses the same battle-tested pattern as MapDataGenerator AudioIndex.scan_folder().
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


def build_wem_index(audio_folder: Path) -> Set[str]:
    """
    Build a set of event names from .wem files in audio folder.

    Same logic as MapDataGenerator AudioIndex.scan_folder():
    rglob("*.wem") + stem.lower() + first-seen-wins dedup.

    Args:
        audio_folder: Folder containing .wem files (recursive)

    Returns:
        Set of lowercase event names (wem file stems)
    """
    if not audio_folder or not audio_folder.exists():
        logger.warning("Audio folder not found: %s", audio_folder)
        return set()

    wem_index: Set[str] = set()
    for wem_path in audio_folder.rglob("*.wem"):
        wem_index.add(wem_path.stem.lower())

    logger.info("Found %d WEM files in %s", len(wem_index), audio_folder)
    return wem_index
