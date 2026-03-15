"""
Naming Coherence Service -- find similar entity names + AI naming suggestions.

Uses CodexService FAISS search for embedding-similar entity names and Qwen3
via Ollama for AI-generated naming alternatives. Follows AISuggestionService
patterns for caching, Ollama integration, and graceful fallback.

Phase 21: AI Naming Coherence + Placeholders (Plan 01)
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from server.tools.ldm.schemas.naming import NamingSuggestionItem


# =============================================================================
# Response Schema (sent to Ollama as JSON format constraint)
# =============================================================================


class NamingSuggestionSchema(BaseModel):
    """Pydantic model defining the structured JSON schema for Ollama output."""

    suggestions: List[NamingSuggestionItem]


# =============================================================================
# Helper: get CodexService singleton (imported lazily to avoid circular deps)
# =============================================================================


def _get_codex_service():
    """Import and return the CodexService singleton from the codex route."""
    from server.tools.ldm.routes.codex import _get_codex_service as get_svc
    return get_svc()


# =============================================================================
# NamingCoherenceService
# =============================================================================


class NamingCoherenceService:
    """Service for entity naming coherence via FAISS similarity + Qwen3 suggestions.

    Uses CodexService for embedding-based similar name lookup and Ollama REST
    API with Qwen3-4B for generating coherent naming alternatives. Caches
    results in-memory and handles Ollama unavailability gracefully.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 15.0
    MAX_CACHE_SIZE = 500

    def __init__(self) -> None:
        self._cache: OrderedDict[str, list] = OrderedDict()
        self._available: Optional[bool] = None

    def find_similar_names(
        self, name: str, entity_type: str = None, limit: int = 10
    ) -> List[dict]:
        """Find similar entity names via CodexService FAISS search.

        Args:
            name: Entity name to search for.
            entity_type: Optional filter by entity type.
            limit: Maximum number of results.

        Returns:
            List of dicts with name, strkey, similarity, entity_type -- sorted
            by similarity descending.
        """
        try:
            codex = _get_codex_service()
            response = codex.search(query=name, entity_type=entity_type, limit=limit)

            items = []
            for result in response.results:
                items.append({
                    "name": result.entity.name,
                    "strkey": result.entity.strkey,
                    "similarity": result.similarity,
                    "entity_type": result.entity.entity_type,
                })

            # Already sorted by CodexService, but ensure descending order
            items.sort(key=lambda x: x["similarity"], reverse=True)
            return items

        except Exception as exc:
            logger.debug(f"[Naming] find_similar_names failed: {exc}")
            return []

    async def suggest_names(
        self,
        name: str,
        entity_type: str,
        similar_names: List[dict],
    ) -> dict:
        """Generate AI naming suggestions via Ollama/Qwen3.

        Args:
            name: Current entity name.
            entity_type: Type of entity (character, item, etc.).
            similar_names: List of similar name dicts for context.

        Returns:
            Dict with suggestions (list), status (ok|cached|unavailable|error).
        """
        cache_key = f"{entity_type}:{name}"

        # Cache hit
        if cache_key in self._cache:
            return {"suggestions": self._cache[cache_key], "status": "cached"}

        # Build prompt
        prompt = self._build_naming_prompt(name, entity_type, similar_names)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": NamingSuggestionSchema.model_json_schema(),
                        "options": {
                            "temperature": 0.8,
                            "num_predict": 500,
                        },
                    },
                )

            # Parse Ollama response
            resp_data = response.json()
            inner_json = json.loads(resp_data["response"])
            raw_suggestions = inner_json["suggestions"]

            # Normalize to dicts
            suggestions = [
                {
                    "name": s["name"],
                    "confidence": min(1.0, max(0.0, s["confidence"])),
                    "reasoning": s["reasoning"],
                }
                for s in raw_suggestions
            ]

            # Sort by confidence descending
            suggestions.sort(key=lambda x: x["confidence"], reverse=True)

            # Cache with FIFO eviction
            if len(self._cache) >= self.MAX_CACHE_SIZE:
                self._cache.popitem(last=False)
            self._cache[cache_key] = suggestions
            self._available = True
            logger.debug(f"[Naming] Generated {len(suggestions)} suggestions for {entity_type}:{name}")
            return {"suggestions": suggestions, "status": "ok"}

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            self._available = False
            logger.warning(f"[Naming] Ollama unavailable: {exc}")
            return {"suggestions": [], "status": "unavailable"}

        except Exception as exc:
            logger.warning(f"[Naming] Error generating suggestions for {entity_type}:{name}: {exc}")
            return {"suggestions": [], "status": "error"}

    def _build_naming_prompt(
        self,
        name: str,
        entity_type: str,
        similar_names: List[dict],
    ) -> str:
        """Build the prompt for Ollama structured output.

        Args:
            name: Current entity name.
            entity_type: Entity type for context.
            similar_names: Similar existing names for pattern context.

        Returns:
            Prompt string for Ollama.
        """
        name = name[:500]
        entity_type = entity_type[:50]

        parts = [
            "You are a game world designer specializing in naming consistency. "
            "Generate exactly 3 alternative names for the entity below that fit "
            "the existing naming patterns in the game world.",
            "",
            f"Entity type: {entity_type}",
            f"Current name: {name}",
        ]

        if similar_names:
            parts.append("")
            parts.append("Existing similar names in the game world:")
            for sn in similar_names[:10]:
                sim_pct = int(sn.get("similarity", 0) * 100)
                parts.append(f"  - {sn['name']} (similarity: {sim_pct}%)")

        parts.append("")
        parts.append(
            "Provide 3 alternative naming suggestions that maintain coherence "
            "with the existing naming patterns. Each suggestion must have: "
            "name (the suggested name), confidence (0.0-1.0 how well it fits "
            "the pattern), reasoning (brief explanation of naming choice)."
        )
        parts.append("")
        parts.append("/no_think")

        return "\n".join(parts)

    def clear_cache(self) -> None:
        """Clear the in-memory naming suggestion cache."""
        self._cache.clear()
        logger.debug("[Naming] Cache cleared")

    def get_status(self) -> dict:
        """Return service health info.

        Returns:
            Dict with available (bool|None), cache_size (int), model (str).
        """
        return {
            "available": self._available,
            "cache_size": len(self._cache),
            "model": self.MODEL,
        }


# =============================================================================
# Singleton
# =============================================================================

_naming_service: Optional[NamingCoherenceService] = None


def get_naming_coherence_service() -> NamingCoherenceService:
    """Get or create the singleton NamingCoherenceService instance."""
    global _naming_service
    if _naming_service is None:
        _naming_service = NamingCoherenceService()
    return _naming_service
