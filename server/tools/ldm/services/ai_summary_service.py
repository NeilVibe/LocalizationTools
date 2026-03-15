"""
AI Summary Service -- Generate contextual summaries via local Ollama/Qwen3.

Calls the Ollama REST API with structured JSON schema to produce 2-line
contextual summaries for game entities (characters, items, regions).
Results are cached in-memory per StringID with graceful fallback when
Ollama is unavailable.

Phase 13: AI Summaries (Plan 01)
"""

from __future__ import annotations

import json
from typing import Dict, Optional

import httpx
from loguru import logger
from pydantic import BaseModel


# =============================================================================
# Response Schema (sent to Ollama as JSON format constraint)
# =============================================================================


class AISummaryResponse(BaseModel):
    """Pydantic model defining the structured JSON schema for Ollama output."""
    summary: str
    entity_type: str


# =============================================================================
# AISummaryService
# =============================================================================


class AISummaryService:
    """Service for generating AI contextual summaries via Ollama REST API.

    Uses httpx to POST to the local Ollama endpoint with Qwen3-4B model.
    Caches results in-memory per StringID. Handles unavailability gracefully.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 10.0

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._available: Optional[bool] = None

    async def generate_summary(
        self,
        string_id: str,
        entity_name: str,
        entity_type: str,
        source_text: str,
    ) -> dict:
        """Generate an AI summary for the given entity context.

        Args:
            string_id: Unique string identifier (cache key).
            entity_name: Name of the entity (character, item, region).
            entity_type: Type of entity (character, item, region, unknown).
            source_text: Source text for context.

        Returns:
            Dict with ai_summary (str|None) and ai_status (generated|cached|unavailable|error).
        """
        # Cache hit
        if string_id in self._cache:
            return {"ai_summary": self._cache[string_id], "ai_status": "cached"}

        prompt = self._build_prompt(entity_name, entity_type, source_text)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": AISummaryResponse.model_json_schema(),
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 200,
                        },
                    },
                )

            # Parse Ollama response
            resp_data = response.json()
            inner_json = json.loads(resp_data["response"])
            summary = inner_json["summary"]

            # Cache and return
            self._cache[string_id] = summary
            self._available = True
            logger.debug(f"[AI] Generated summary for {string_id}: {summary[:50]}...")
            return {"ai_summary": summary, "ai_status": "generated"}

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            self._available = False
            logger.warning(f"[AI] Ollama unavailable: {exc}")
            return {"ai_summary": None, "ai_status": "unavailable"}

        except Exception as exc:
            logger.warning(f"[AI] Error generating summary for {string_id}: {exc}")
            return {"ai_summary": None, "ai_status": "error"}

    def _build_prompt(self, entity_name: str, entity_type: str, source_text: str) -> str:
        """Build the prompt for Ollama structured output.

        Args:
            entity_name: Name of the entity.
            entity_type: Type (character, item, region, etc.).
            source_text: Source text for context.

        Returns:
            Prompt string for Ollama.
        """
        return (
            f"You are a game localization assistant. "
            f"Generate a concise 1-2 sentence contextual summary for translators.\n\n"
            f"Entity name: {entity_name}\n"
            f"Entity type: {entity_type}\n"
            f"Source text: {source_text}\n\n"
            f"Provide a brief summary describing who/what this entity is and "
            f"any relevant context for translation."
        )

    def clear_cache(self) -> None:
        """Clear the in-memory summary cache."""
        self._cache.clear()
        logger.debug("[AI] Cache cleared")

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

_service_instance: Optional[AISummaryService] = None


def get_ai_summary_service() -> AISummaryService:
    """Get or create the singleton AISummaryService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AISummaryService()
    return _service_instance
