"""GameData Context Intelligence Service -- cross-refs, related entities, TM suggestions, media, AI summary.

Phase 30: Context Intelligence Panel (Plans 01 + 02)

Provides:
- Reverse index for backward cross-reference resolution
- Forward + backward cross-ref resolution for any TreeNode
- Related entity search via 6-tier cascade (GameDataSearcher)
- TM suggestions from loaded language data (conditional on StrKey)
- Media resolution (texture + audio attribute detection)
- AI context summary generation via Ollama/Qwen3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from server.tools.ldm.schemas.gamedata import TreeNode, FolderTreeDataResponse
from server.tools.ldm.indexing.gamedata_indexer import get_gamedata_indexer
from server.tools.ldm.indexing.gamedata_searcher import GameDataSearcher
from server.tools.ldm.services.gamedata_browse_service import EDITABLE_ATTRS


# Attributes whose names suggest cross-references (same set as GameDataTree.svelte)
CROSS_REF_ATTRS = {
    "LearnKnowledgeKey", "RequireSkillKey", "LinkedQuestKey", "RegionKey",
    "ParentNodeId", "ParentId", "TargetKey", "ItemKey", "CharacterKey",
    "GimmickKey", "SealKey", "FactionKey", "SkillKey", "KnowledgeKey",
    "RewardKey",
}

# Identity attributes that should NOT be treated as cross-references
IDENTITY_ATTRS = {"Key", "NodeId", "Id", "StrKey"}

# Attributes that indicate texture/image references
TEXTURE_ATTRS = ("TextureName", "IconTexture", "Texture", "ImagePath", "UITextureName", "TextureKey", "TexturePath", "SkillIcon")

# Attributes that indicate audio/voice references
VOICE_ATTRS = ("VoiceId", "SoundId", "AudioFile", "VoicePath", "VoiceKey", "VoicePath")


def _is_cross_ref_attr(attr_name: str) -> bool:
    """Check if an attribute name represents a cross-reference."""
    if attr_name in CROSS_REF_ATTRS:
        return True
    if attr_name in IDENTITY_ATTRS:
        return False
    if attr_name.endswith("Key") or attr_name.endswith("Id"):
        return True
    return False


class GameDataContextService:
    """Context intelligence for gamedata entities.

    Resolves cross-references (forward + backward), finds related entities
    via cascade search, provides TM suggestions from language data, and
    detects media assets.
    """

    def __init__(self):
        self._reverse_index: Dict[str, List[Dict[str, Any]]] = {}
        self._entity_names: Dict[str, str] = {}  # node_id -> display name
        self._ai_cache: Dict[str, str] = {}  # cache_key -> summary string

    # =========================================================================
    # 1. Reverse Index Builder
    # =========================================================================

    def build_reverse_index(self, folder_tree_data: FolderTreeDataResponse) -> None:
        """Walk all TreeNodes and build reverse cross-reference index.

        For each node, scans all attribute values for cross-reference patterns
        and records them so backward lookups are O(1).

        Also indexes the whole_lookup from GameDataIndexer for value-based
        cross-ref resolution.
        """
        self._reverse_index = {}
        self._entity_names = {}

        indexer = get_gamedata_indexer()
        whole_lookup = {}
        if indexer.is_ready and indexer.indexes:
            whole_lookup = indexer.indexes.get("whole_lookup", {})

        total_refs = 0

        for file_data in folder_tree_data.files:
            for root in file_data.roots:
                total_refs += self._walk_for_reverse_index(
                    root, file_data.file_path, whole_lookup
                )

        logger.info(
            f"[ContextService] Reverse index built: "
            f"{len(self._reverse_index)} targets, {total_refs} total refs, "
            f"{len(self._entity_names)} named entities"
        )

    def _walk_for_reverse_index(
        self,
        node: TreeNode,
        file_path: str,
        whole_lookup: Dict[str, Any],
    ) -> int:
        """Recursively walk tree, building reverse index entries. Returns ref count."""
        ref_count = 0

        # Index entity display name
        editable = EDITABLE_ATTRS.get(node.tag, [])
        if editable:
            name = str(node.attributes.get(editable[0], ""))
            if name:
                self._entity_names[node.node_id] = name

        # Scan attributes for cross-references
        for attr_name, attr_value in node.attributes.items():
            attr_value_str = str(attr_value)
            if not attr_value_str or attr_value_str == "0":
                continue

            if not _is_cross_ref_attr(attr_name):
                continue

            # Try to find the target in whole_lookup (normalized)
            from server.tools.ldm.indexing.utils import normalize_for_hash
            normalized = normalize_for_hash(attr_value_str)
            target_data = whole_lookup.get(normalized) if normalized else None

            if target_data:
                target_node_id = target_data["node_id"]
                entry = {
                    "source_node_id": node.node_id,
                    "source_tag": node.tag,
                    "source_attr": attr_name,
                    "source_file": file_path,
                    "source_name": self._entity_names.get(node.node_id, node.tag),
                }
                if target_node_id not in self._reverse_index:
                    self._reverse_index[target_node_id] = []
                self._reverse_index[target_node_id].append(entry)
                ref_count += 1

        # Recurse into children
        for child in node.children:
            ref_count += self._walk_for_reverse_index(child, file_path, whole_lookup)

        return ref_count

    # =========================================================================
    # 2. Cross-Ref Resolver
    # =========================================================================

    def get_cross_refs(self, node_id: str, node: TreeNode) -> Dict[str, Any]:
        """Get forward and backward cross-references for a node.

        Forward refs: attributes in this node that point to other entities.
        Backward refs: other entities that point to this node (from reverse index).
        """
        indexer = get_gamedata_indexer()
        whole_lookup = {}
        if indexer.is_ready and indexer.indexes:
            whole_lookup = indexer.indexes.get("whole_lookup", {})

        forward: List[Dict[str, str]] = []
        backward: List[Dict[str, str]] = []

        # Forward references
        from server.tools.ldm.indexing.utils import normalize_for_hash
        for attr_name, attr_value in node.attributes.items():
            attr_value_str = str(attr_value)
            if not attr_value_str or attr_value_str == "0":
                continue

            if not _is_cross_ref_attr(attr_name):
                continue

            normalized = normalize_for_hash(attr_value_str)
            target_data = whole_lookup.get(normalized) if normalized else None

            if target_data:
                forward.append({
                    "node_id": target_data["node_id"],
                    "tag": target_data["tag"],
                    "name": target_data.get("entity_name", target_data["tag"]),
                    "via_attr": attr_name,
                })

        # Backward references (from reverse index)
        back_refs = self._reverse_index.get(node_id, [])
        for ref in back_refs:
            backward.append({
                "node_id": ref["source_node_id"],
                "tag": ref["source_tag"],
                "name": ref.get("source_name", ref["source_tag"]),
                "via_attr": ref["source_attr"],
            })

        return {
            "forward": forward,
            "backward": backward,
        }

    # =========================================================================
    # 3. Related Entities
    # =========================================================================

    def get_related(self, node: TreeNode, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find semantically similar entities via cascade search.

        Uses the entity name from first editable attr or Key attr as query.
        Filters out self (same node_id).
        """
        indexer = get_gamedata_indexer()
        if not indexer.is_ready or not indexer.indexes:
            return []

        # Get entity name for search query
        editable = EDITABLE_ATTRS.get(node.tag, [])
        entity_name = ""
        if editable:
            entity_name = str(node.attributes.get(editable[0], ""))
        if not entity_name:
            entity_name = str(node.attributes.get("Key", ""))
        if not entity_name:
            return []

        try:
            searcher = GameDataSearcher(indexer.indexes)
            result = searcher.search(entity_name, top_k=top_k + 2, threshold=0.85)

            related = []
            for r in result.get("results", []):
                if r["node_id"] == node.node_id:
                    continue  # Skip self
                related.append({
                    "entity_name": r["entity_name"],
                    "entity_desc": r.get("entity_desc", ""),
                    "node_id": r["node_id"],
                    "tag": r["tag"],
                    "score": r["score"],
                    "match_type": r["match_type"],
                    "tier_name": result.get("tier_name", ""),
                })
                if len(related) >= top_k:
                    break

            return related
        except Exception as e:
            logger.error(f"[ContextService] Related search failed: {e}")
            return []

    # =========================================================================
    # 4. TM Suggestions from Language Data
    # =========================================================================

    async def get_tm_suggestions(
        self,
        node: TreeNode,
        row_repo,
        threshold: float = 0.50,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get TM suggestions when entity has a StrKey in language data.

        Checks if entity has StrKey attribute. If not, returns empty list.
        Uses row_repo.suggest_similar() (same method as /tm/suggest endpoint).

        Returns list of {source, target, similarity, file_name}.
        On error (e.g., offline mode with SQLite), returns empty list gracefully.
        """
        # Check for StrKey attribute
        str_key = str(node.attributes.get("StrKey", ""))
        if not str_key:
            # Fallback: check for attrs ending in "StrKey"
            for attr_name, attr_value in node.attributes.items():
                if attr_name.endswith("StrKey") and attr_value:
                    str_key = str(attr_value)
                    break

        if not str_key:
            return []

        # Get entity name/description for search
        editable = EDITABLE_ATTRS.get(node.tag, [])
        source_text = ""
        if editable:
            source_text = str(node.attributes.get(editable[0], ""))
        if not source_text:
            source_text = str_key

        try:
            suggestions = await row_repo.suggest_similar(
                source=source_text,
                threshold=threshold,
                max_results=max_results,
            )
            return [
                {
                    "source": s.get("source", ""),
                    "target": s.get("target", ""),
                    "similarity": s.get("similarity", 0.0),
                    "file_name": s.get("file_name", ""),
                }
                for s in suggestions
            ]
        except Exception as e:
            logger.warning(f"[ContextService] TM suggestions failed (expected in offline): {e}")
            return []

    # =========================================================================
    # 5. Media Resolver
    # =========================================================================

    def get_media(self, node: TreeNode) -> Dict[str, Any]:
        """Check for texture and audio references in node attributes.

        Returns media context with URLs if assets are found.
        """
        result: Dict[str, Any] = {
            "has_image": False,
            "texture_name": "",
            "thumbnail_url": "",
            "has_audio": False,
            "voice_id": "",
            "stream_url": "",
        }

        # Check for texture/image
        for attr in TEXTURE_ATTRS:
            value = str(node.attributes.get(attr, ""))
            if value:
                result["has_image"] = True
                result["texture_name"] = value
                result["thumbnail_url"] = f"/api/ldm/mapdata/thumbnail/{value}"
                break

        # Check for audio/voice
        for attr in VOICE_ATTRS:
            value = str(node.attributes.get(attr, ""))
            if value:
                result["has_audio"] = True
                result["voice_id"] = value
                result["stream_url"] = f"/api/ldm/mapdata/audio/stream/{value}"
                break

        # Fallback: check if StrKey has audio in MapDataService
        if not result["has_audio"]:
            strkey = str(node.attributes.get("StrKey", ""))
            if strkey:
                from server.tools.ldm.services.mapdata_service import get_mapdata_service
                mapdata_svc = get_mapdata_service()
                audio_ctx = mapdata_svc.get_audio_context(strkey)
                if audio_ctx:
                    result["has_audio"] = True
                    result["voice_id"] = strkey
                    result["stream_url"] = f"/api/ldm/mapdata/audio/stream/{strkey}"

        return result

    # =========================================================================
    # 6. AI Context Summary (Qwen3 via Ollama)
    # =========================================================================

    OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
    OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
    AI_MODEL = "qwen3:8b"
    AI_TIMEOUT = 30.0
    AI_THINK = False  # Disable Qwen3 thinking mode for clean output
    AI_SYSTEM_PROMPT = (
        "You are a game data analyst for an MMORPG. "
        "Given entity data, write exactly 2-3 factual sentences explaining what this entity is, "
        "what it does in the game, and how it connects to other entities. "
        "Do not start with 'This entity' or 'Based on'. Do not add disclaimers or caveats. "
        "Always write in Korean (한국어). "
        "Output only the summary, nothing else."
    )

    async def generate_ai_summary(
        self,
        node: TreeNode,
        cross_refs: Dict[str, Any],
        related: List[Dict[str, Any]],
    ) -> str:
        """Generate an AI context summary for a game entity using Qwen3 via Ollama.

        Builds a prompt from the entity's attributes, cross-references, and related
        entities, then calls Ollama to generate a concise narrative summary.

        Args:
            node: The TreeNode to summarize.
            cross_refs: Dict with 'forward' and 'backward' lists.
            related: List of related entity dicts.

        Returns:
            Summary string, or empty string on error.
        """
        # Cache hit
        cache_key = f"{node.node_id}_{node.tag}"
        if cache_key in self._ai_cache:
            logger.debug(f"[ContextService] AI cache hit for {cache_key}")
            return self._ai_cache[cache_key]

        # Build entity name
        editable = EDITABLE_ATTRS.get(node.tag, [])
        entity_name = ""
        if editable:
            entity_name = str(node.attributes.get(editable[0], ""))
        if not entity_name:
            entity_name = str(node.attributes.get("Key", node.tag))

        # Build prompt parts
        parts = [
            f"Entity: {entity_name}",
            f"Type: {node.tag}",
        ]

        # Key attributes (top 5 non-empty)
        attr_count = 0
        attr_lines = []
        for attr_name, attr_value in node.attributes.items():
            val = str(attr_value)
            if val and attr_count < 5:
                attr_lines.append(f"  {attr_name}: {val[:100]}")
                attr_count += 1
        if attr_lines:
            parts.append("Key attributes:")
            parts.extend(attr_lines)

        # Cross-references summary
        forward = cross_refs.get("forward", [])
        backward = cross_refs.get("backward", [])
        if forward or backward:
            ref_tags = set()
            for ref in forward:
                ref_tags.add(ref.get("tag", "unknown"))
            for ref in backward:
                ref_tags.add(ref.get("tag", "unknown"))
            total_refs = len(forward) + len(backward)
            parts.append(
                f"Cross-references: Referenced by/to {total_refs} entities: "
                f"{', '.join(sorted(ref_tags))}"
            )

        # Related entities (top 3)
        if related:
            related_names = [
                f"{r.get('entity_name', '?')} ({r.get('score', 0):.0%})"
                for r in related[:3]
            ]
            parts.append(f"Similar to: {', '.join(related_names)}")

        parts.append("\n한국어로 작성하세요. 간결하고 사실적인 요약을 작성하세요.")
        prompt = "\n".join(parts)

        try:
            async with httpx.AsyncClient(timeout=self.AI_TIMEOUT) as client:
                response = await client.post(
                    self.OLLAMA_GENERATE_URL,
                    json={
                        "model": self.AI_MODEL,
                        "prompt": prompt,
                        "system": self.AI_SYSTEM_PROMPT,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 150,
                            "repeat_penalty": 1.1,
                        },
                        "think": self.AI_THINK,
                    },
                )
                if response.status_code != 200:
                    logger.warning(f"[ContextService] Ollama returned HTTP {response.status_code}")
                    return ""

                data = response.json()
                summary = data.get("response", "").strip()

                logger.debug(f"[ContextService] AI summary generated ({len(summary)} chars)")

                # Cache the result
                if summary:
                    self._ai_cache[cache_key] = summary
                    # Cap cache at 200 entries
                    if len(self._ai_cache) > 200:
                        oldest = next(iter(self._ai_cache))
                        del self._ai_cache[oldest]

                return summary

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning(f"[ContextService] Ollama unavailable for AI summary: {exc}")
            return ""
        except Exception as exc:
            logger.error(f"[ContextService] AI summary generation failed: {exc}")
            return ""

    # =========================================================================
    # Helpers
    # =========================================================================

    def has_strkey(self, node: TreeNode) -> bool:
        """Check if entity has a StrKey attribute (language data linkage)."""
        if node.attributes.get("StrKey"):
            return True
        for attr_name in node.attributes:
            if attr_name.endswith("StrKey") and node.attributes[attr_name]:
                return True
        return False


# =============================================================================
# Singleton
# =============================================================================

_context_service_instance: Optional[GameDataContextService] = None


def get_gamedata_context_service() -> GameDataContextService:
    """Get or create the singleton GameDataContextService instance."""
    global _context_service_instance
    if _context_service_instance is None:
        _context_service_instance = GameDataContextService()
    return _context_service_instance
