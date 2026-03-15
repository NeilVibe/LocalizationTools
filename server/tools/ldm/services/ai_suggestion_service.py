"""
AI Suggestion Service -- Generate ranked translation suggestions via Ollama/Qwen3.

Generates 3 translation suggestions with blended confidence scores combining
embedding similarity (via Model2Vec FAISS) and LLM certainty. Includes entity
context enrichment, in-memory caching, and graceful fallback when Ollama is
unavailable.

Phase 17: AI Translation Suggestions (Plan 01)
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from server.tools.shared.embedding_engine import get_embedding_engine


# =============================================================================
# Response Schema (sent to Ollama as JSON format constraint)
# =============================================================================


class SuggestionItem(BaseModel):
    """A single translation suggestion with confidence and reasoning."""
    text: str
    confidence: float
    reasoning: str


class AISuggestionResponse(BaseModel):
    """Pydantic model defining the structured JSON schema for Ollama output."""
    suggestions: List[SuggestionItem]


# =============================================================================
# AISuggestionService
# =============================================================================


class AISuggestionService:
    """Service for generating AI translation suggestions via Ollama REST API.

    Uses httpx to POST to the local Ollama endpoint with Qwen3-4B model.
    Blends embedding similarity with LLM confidence for ranked suggestions.
    Caches results in-memory per StringID + source_text hash.
    Handles unavailability gracefully.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 15.0
    BLEND_WEIGHT_EMBEDDING = 0.4
    BLEND_WEIGHT_LLM = 0.6

    def __init__(self) -> None:
        self._cache: Dict[str, list] = {}
        self._available: Optional[bool] = None

    def _find_similar_segments(self, source_text: str, top_k: int = 3) -> list[dict]:
        """Find similar translation segments using EmbeddingEngine.

        Uses Model2Vec embedding engine to find semantically similar segments
        from the TM FAISS index. Returns empty list gracefully if engine or
        index is not available.

        Args:
            source_text: Source text to find similar segments for.
            top_k: Number of similar segments to return.

        Returns:
            List of dicts with source, target, similarity keys.
        """
        try:
            engine = get_embedding_engine()
            if not engine.is_loaded:
                engine.load()

            # Try to use TMSearcher FAISS index if available
            try:
                from server.tools.ldm.indexing.searcher import TMSearcher
                searcher = TMSearcher.get_instance()
                if searcher and hasattr(searcher, "whole_index") and searcher.whole_index is not None:
                    query_embedding = engine.encode([source_text], normalize=True)
                    scores, indices = searcher.whole_index.search(query_embedding, top_k)
                    results = []
                    for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                        if idx >= 0 and idx < len(searcher.whole_mapping):
                            entry = searcher.whole_mapping[idx]
                            results.append({
                                "source": entry.get("source", ""),
                                "target": entry.get("target", ""),
                                "similarity": float(score),
                            })
                    return results
            except Exception:
                pass  # TMSearcher not available, that's fine

            # No FAISS index available
            return []

        except Exception as exc:
            logger.debug(f"[AI Suggestions] Similar segments unavailable: {exc}")
            return []

    def _blend_confidence(self, llm_confidence: float, similar_segments: list[dict]) -> float:
        """Blend LLM confidence with embedding similarity score.

        Formula: 0.4 * max_embedding_similarity + 0.6 * llm_confidence
        Clamped to [0.0, 1.0].

        Args:
            llm_confidence: Confidence score from LLM (0.0-1.0).
            similar_segments: List of similar segments with similarity scores.

        Returns:
            Blended confidence score clamped to [0.0, 1.0].
        """
        if not similar_segments:
            return min(1.0, max(0.0, llm_confidence))

        max_embedding_sim = max(s["similarity"] for s in similar_segments)
        blended = self.BLEND_WEIGHT_EMBEDDING * max_embedding_sim + self.BLEND_WEIGHT_LLM * llm_confidence
        return min(1.0, max(0.0, blended))

    async def generate_suggestions(
        self,
        string_id: str,
        source_text: str,
        target_lang: str,
        entity_type: str,
        surrounding_context: list[dict],
    ) -> dict:
        """Generate ranked translation suggestions for the given source text.

        Args:
            string_id: Unique string identifier.
            source_text: Source text to translate.
            target_lang: Target language code (e.g., "KR").
            entity_type: Type of entity (Item, Character, etc.).
            surrounding_context: List of {source, target} context pairs.

        Returns:
            Dict with suggestions (list) and status (generated|cached|unavailable|error).
        """
        # Cache key includes source_text hash to invalidate on text changes
        text_hash = hashlib.md5(source_text.encode()).hexdigest()[:8]
        cache_key = f"{string_id}:{target_lang}:{text_hash}"

        # Cache hit
        if cache_key in self._cache:
            return {"suggestions": self._cache[cache_key], "status": "cached"}

        # Step 1: Find similar segments (enrichment, not required)
        similar_segments = self._find_similar_segments(source_text)

        # Step 2: Build prompt
        prompt = self._build_prompt(
            source_text, target_lang, entity_type, surrounding_context, similar_segments
        )

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": AISuggestionResponse.model_json_schema(),
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 500,
                        },
                    },
                )

            # Parse Ollama response
            resp_data = response.json()
            inner_json = json.loads(resp_data["response"])
            raw_suggestions = inner_json["suggestions"]

            # Step 4: Blend confidence for each suggestion
            blended_suggestions = []
            for s in raw_suggestions:
                blended_conf = self._blend_confidence(s["confidence"], similar_segments)
                blended_suggestions.append({
                    "text": s["text"],
                    "confidence": blended_conf,
                    "reasoning": s["reasoning"],
                })

            # Sort by confidence descending
            blended_suggestions.sort(key=lambda x: x["confidence"], reverse=True)

            # Cache and return
            self._cache[cache_key] = blended_suggestions
            self._available = True
            logger.debug(f"[AI Suggestions] Generated {len(blended_suggestions)} suggestions for {string_id}")
            return {"suggestions": blended_suggestions, "status": "generated"}

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            self._available = False
            logger.warning(f"[AI Suggestions] Ollama unavailable: {exc}")
            return {"suggestions": [], "status": "unavailable"}

        except Exception as exc:
            logger.warning(f"[AI Suggestions] Error generating suggestions for {string_id}: {exc}")
            return {"suggestions": [], "status": "error"}

    def _build_prompt(
        self,
        source_text: str,
        target_lang: str,
        entity_type: str,
        surrounding_context: list[dict],
        similar_segments: list[dict],
    ) -> str:
        """Build the prompt for Ollama structured output.

        Args:
            source_text: Source text to translate.
            target_lang: Target language code.
            entity_type: Entity type for context.
            surrounding_context: Neighboring translation pairs (max 4).
            similar_segments: Similar TM segments (max 3).

        Returns:
            Prompt string for Ollama.
        """
        # Truncate inputs to prevent prompt injection / excessive tokens
        source_text = source_text[:500]
        target_lang = target_lang[:10]
        entity_type = entity_type[:50]

        parts = [
            "You are a professional game localization translator. "
            "Generate exactly 3 translation suggestions for the source text below.",
            "",
            f"Source text: {source_text}",
            f"Target language: {target_lang}",
            f"Entity type: {entity_type}",
        ]

        # Add similar segments as translation examples
        if similar_segments:
            parts.append("")
            parts.append("Similar translations from the translation memory:")
            for seg in similar_segments[:3]:
                sim_pct = int(seg["similarity"] * 100)
                parts.append(f"  Source: {seg['source'][:200]} -> Target: {seg['target'][:200]} (similarity: {sim_pct}%)")

        # Add surrounding context
        if surrounding_context:
            parts.append("")
            parts.append("Surrounding context (nearby translations):")
            for ctx in surrounding_context[:4]:
                src = str(ctx.get("source", ""))[:200]
                tgt = str(ctx.get("target", ""))[:200]
                parts.append(f"  {src} -> {tgt}")

        parts.append("")
        parts.append(
            "Provide 3 translation suggestions ranked by quality. "
            "Each suggestion must have: text (the translation), "
            "confidence (0.0-1.0 how confident you are), "
            "reasoning (brief explanation of translation choice)."
        )

        return "\n".join(parts)

    def clear_cache(self) -> None:
        """Clear the in-memory suggestion cache."""
        self._cache.clear()
        logger.debug("[AI Suggestions] Cache cleared")

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

_service_instance: Optional[AISuggestionService] = None


def get_ai_suggestion_service() -> AISuggestionService:
    """Get or create the singleton AISuggestionService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AISuggestionService()
    return _service_instance
