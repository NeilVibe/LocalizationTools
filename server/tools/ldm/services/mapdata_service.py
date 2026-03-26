"""
MapData Context Service - StrKey-to-image/audio index lookups.

Provides image and audio context for translation grid rows using
MegaIndex's unified data lookups. Indexes entries under multiple keys
(StrKey, StringID, KnowledgeKey) for robust lookup.

Phase 5: Visual Polish and Integration (Plan 01)
Phase 45: MegaIndex migration -- delegates all data to MegaIndex instead
of independent XML parsing. One parse to rule them all.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

from server.tools.ldm.services.perforce_path_service import get_perforce_path_service


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ImageContext:
    """Image context for a translation grid row."""
    texture_name: str
    dds_path: str
    thumbnail_url: str
    has_image: bool
    fallback_reason: str = ""  # Why media not found (empty = found)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AudioContext:
    """Audio context for a translation grid row."""
    event_name: str
    wem_path: str
    script_kr: str
    script_eng: str
    duration_seconds: Optional[float] = None
    fallback_reason: str = ""  # Why media not found (empty = found)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeLookup:
    """Knowledge entry from KnowledgeInfo XML -- maps StrKey to entity metadata."""
    strkey: str
    name: str
    desc: str
    ui_texture_name: str
    group_key: str
    source_file: str


# =============================================================================
# MapDataService
# =============================================================================

class MapDataService:
    """Service for StrKey-to-image/audio context lookups.

    Maintains pre-indexed maps for fast O(1) lookups by StrKey, StringID,
    or KnowledgeKey. Delegates data population to MegaIndex.
    Gracefully degrades: returns None when unloaded.
    """

    def __init__(self):
        self._strkey_to_image: Dict[str, ImageContext] = {}
        self._strkey_to_audio: Dict[str, AudioContext] = {}
        self._knowledge_table: Dict[str, KnowledgeLookup] = {}
        self._dds_index: Dict[str, Path] = {}
        self._loaded: bool = False
        self._branch: str = "mainline"
        self._drive: str = "F"
        self._path_service = get_perforce_path_service()

    def initialize(self, branch: str = "mainline", drive: str = "F") -> bool:
        """Initialize the service by populating indexes from MegaIndex.

        Triggers MegaIndex build if needed, then populates:
        1. Knowledge table from MegaIndex knowledge_by_strkey
        2. DDS index from MegaIndex dds_by_stem
        3. Image chains from MegaIndex strkey_to_image_path (C1)

        Gracefully degrades: if MegaIndex has no data, logs warnings and
        marks as loaded with empty indexes.

        Args:
            branch: Perforce branch name
            drive: Drive letter

        Returns:
            True if initialization succeeded.
        """
        from server.tools.ldm.services.mega_index import get_mega_index

        self._branch = branch
        self._drive = drive

        # Configure path service (still needed for thumbnail URL generation etc.)
        self._path_service.configure(drive, branch)

        # Trigger MegaIndex build if not already built
        mega = get_mega_index()
        if not mega._built:
            mega.build()

        # Populate knowledge table from MegaIndex D1
        self._knowledge_table = {}
        for strkey, e in mega.knowledge_by_strkey.items():
            self._knowledge_table[strkey] = KnowledgeLookup(
                strkey=e.strkey,
                name=e.name,
                desc=e.desc,
                ui_texture_name=e.ui_texture_name,
                group_key=e.group_key,
                source_file=e.source_file,
            )

        # DDS index from MegaIndex D9 (direct reference, same type Dict[str, Path])
        self._dds_index = mega.dds_by_stem

        # Image chains from MegaIndex C1 (strkey_to_image_path)
        self._strkey_to_image = {}
        for strkey, dds_path in mega.strkey_to_image_path.items():
            knowledge = mega.knowledge_by_strkey.get(strkey)
            texture_name = knowledge.ui_texture_name if knowledge else ""
            self._strkey_to_image[strkey] = ImageContext(
                texture_name=texture_name,
                dds_path=str(dds_path),
                thumbnail_url=f"/api/ldm/mapdata/thumbnail/{texture_name}" if texture_name else "",
                has_image=True,
            )

        self._loaded = True
        logger.info(
            f"[MAPDATA] Initialized from MegaIndex: {len(self._knowledge_table)} knowledge entries, "
            f"{len(self._dds_index)} DDS textures, "
            f"{len(self._strkey_to_image)} image chains resolved"
        )
        return True

    def get_image_context(self, string_id: str) -> Optional[ImageContext]:
        """Look up image context by StrKey, StringID, or KnowledgeKey.

        Path resolution uses whatever branch+drive is configured via
        PerforcePathService (see Phase 90 BranchDriveSelector).

        Lookup order:
        1. Exact match in pre-indexed _strkey_to_image (from initialize/C1)
        2. C7 bridge: StringID -> entity StrKey -> C1 image path
        3. Fuzzy partial match against indexed StrKeys

        Returns None only if service is not loaded.
        Returns ImageContext with has_image=False and fallback_reason when
        media cannot be resolved (instead of None).
        """
        if not self._loaded:
            return None

        # 1. Exact match (pre-indexed from initialize or cached)
        result = self._strkey_to_image.get(string_id)
        if result:
            return result

        # Track reason through the lookup chain
        reason = ""

        # 2. C7 bridge: StringID -> entity -> knowledge -> C1 image path
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()
        entity_info = mega.stringid_to_entity.get(string_id)
        if entity_info:
            entity_type, entity_strkey = entity_info
            # Try direct C1 lookup with entity strkey
            img_path = mega.strkey_to_image_path.get(entity_strkey)
            if img_path:
                knowledge = mega.knowledge_by_strkey.get(entity_strkey)
                texture_name = knowledge.ui_texture_name if knowledge else ""
                ctx = ImageContext(
                    texture_name=texture_name,
                    dds_path=str(img_path),
                    thumbnail_url=f"/api/ldm/mapdata/thumbnail/{texture_name}" if texture_name else "",
                    has_image=True,
                )
                self._strkey_to_image[string_id] = ctx  # cache
                return ctx

            # C1 lookup failed -- determine specific reason
            knowledge = mega.knowledge_by_strkey.get(entity_strkey)
            if not knowledge:
                reason = f"Entity '{entity_strkey}' not in knowledge index"
            elif not knowledge.ui_texture_name:
                reason = f"Entity '{entity_strkey}' has no UITextureName attribute"
            else:
                reason = f"Texture '{knowledge.ui_texture_name}' not found in DDS index"

            # Scan knowledge entries whose strkey matches the entity name
            entity_name_lower = entity_strkey.lower()
            for k_strkey, k_entry in mega.knowledge_by_strkey.items():
                if entity_name_lower in k_strkey.lower() or k_strkey.lower() in entity_name_lower:
                    img_path = mega.strkey_to_image_path.get(k_strkey)
                    if img_path:
                        ctx = ImageContext(
                            texture_name=k_entry.ui_texture_name,
                            dds_path=str(img_path),
                            thumbnail_url=f"/api/ldm/mapdata/thumbnail/{k_entry.ui_texture_name}" if k_entry.ui_texture_name else "",
                            has_image=True,
                        )
                        self._strkey_to_image[string_id] = ctx
                        return ctx
        else:
            reason = "Entity not found for this StringID"

        # 3. Fuzzy: try partial match against indexed StrKeys
        sid_lower = string_id.lower().replace("_", "")
        for key, ctx in self._strkey_to_image.items():
            key_lower = key.lower().replace("_", "")
            if sid_lower in key_lower or key_lower in sid_lower:
                # Don't cache fuzzy matches — loose criterion may match wrong entity
                return ctx

        return ImageContext(
            texture_name="",
            dds_path="",
            thumbnail_url="",
            has_image=False,
            fallback_reason=reason or "No matching entity or texture found",
        )

    def get_knowledge_lookup(self, strkey: str) -> Optional[KnowledgeLookup]:
        """Look up raw KnowledgeLookup entry by StrKey.

        Used by ContextService.resolve_chain() to access UITextureName
        and other metadata for step-by-step chain resolution.

        Args:
            strkey: The StrKey to look up.

        Returns:
            KnowledgeLookup or None if not found.
        """
        return self._knowledge_table.get(strkey)

    def get_audio_context(self, string_id: str) -> Optional[AudioContext]:
        """Look up audio context by StrKey, StringID, or KnowledgeKey.

        Uses MegaIndex C3 (stringid_to_audio_path) for direct StringId->WEM
        lookup, with C4/C5 (event_to_script) for Korean/English script text.
        Falls back to lazy-loaded TTS WAV files.

        Returns None only if service is not loaded.
        Returns AudioContext with empty fields and fallback_reason when
        audio cannot be resolved (instead of None).
        """
        if not self._loaded:
            return None

        # Check cached audio first
        result = self._strkey_to_audio.get(string_id)
        if result:
            return result

        # Try MegaIndex C3: StringId -> audio WEM path
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()

        wem_path = mega.stringid_to_audio_path.get(string_id)
        if wem_path:
            # Get event name for script lookup via R3
            event_name = mega.stringid_to_event.get(string_id, "")
            script_kr = ""
            script_eng = ""
            if event_name:
                script_kr = mega.event_to_script_kr.get(event_name.lower(), "")
                script_eng = mega.event_to_script_eng.get(event_name.lower(), "")

            audio_ctx = AudioContext(
                event_name=event_name or f"Voice: {string_id}",
                wem_path=str(wem_path),
                script_kr=script_kr,
                script_eng=script_eng,
                duration_seconds=None,
            )
            # Cache for future lookups
            self._strkey_to_audio[string_id] = audio_ctx
            return audio_ctx

        # Also try StrKey-based audio path from C2
        audio_path_c2 = mega.strkey_to_audio_path.get(string_id)
        if audio_path_c2:
            audio_ctx = AudioContext(
                event_name=f"Voice: {string_id}",
                wem_path=str(audio_path_c2),
                script_kr="",
                script_eng="",
                duration_seconds=None,
            )
            self._strkey_to_audio[string_id] = audio_ctx
            return audio_ctx

        # Lazy-populate audio index from TTS WAV files as final fallback
        if not self._strkey_to_audio:
            self._lazy_load_audio()

        result = self._strkey_to_audio.get(string_id)
        if result:
            return result

        # Fuzzy match for audio (same partial strategy as images)
        sid_lower = string_id.lower().replace("_", "")
        for key, ctx in self._strkey_to_audio.items():
            key_lower = key.lower().replace("_", "")
            if sid_lower in key_lower or key_lower in sid_lower:
                # Don't cache fuzzy matches — loose criterion may match wrong entity
                return ctx

        return AudioContext(
            event_name="",
            wem_path="",
            script_kr="",
            script_eng="",
            fallback_reason="No audio event linked to this StringID",
        )

    def _lazy_load_audio(self) -> None:
        """Lazily scan audio/ directory for WAV files and populate _strkey_to_audio."""
        # Try project root audio/ dir (TTS-generated files)
        for candidate in [
            Path(__file__).resolve().parents[3] / "audio",  # project root
            Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "mock_gamedata" / "audio",
        ]:
            if candidate.is_dir():
                for wav_file in candidate.glob("*.wav"):
                    strkey = wav_file.stem
                    if strkey not in self._strkey_to_audio:
                        self._strkey_to_audio[strkey] = AudioContext(
                            event_name=f"Voice: {strkey.replace('_', ' ')}",
                            wem_path=str(wav_file),
                            script_kr="",
                            script_eng="",
                            duration_seconds=None,
                        )
                if self._strkey_to_audio:
                    logger.info(f"[MAPDATA] Lazy-loaded {len(self._strkey_to_audio)} audio entries from {candidate}")

    def get_status(self) -> dict:
        """Return service status info."""
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()

        status = {
            "loaded": self._loaded,
            "branch": self._branch,
            "drive": self._drive,
            "image_count": len(self._strkey_to_image),
            "audio_count": len(self._strkey_to_audio),
            "path_service": self._path_service.get_status(),
            "mega_index_built": mega._built,
        }
        if mega._built:
            status["mega_index_entity_counts"] = mega.entity_counts()
        return status


# =============================================================================
# Singleton instance
# =============================================================================

_service_instance: Optional[MapDataService] = None


def get_mapdata_service() -> MapDataService:
    """Get or create the singleton MapDataService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MapDataService()
    return _service_instance
