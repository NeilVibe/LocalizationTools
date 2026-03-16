"""AI Image Service -- Gemini image generation for Codex entities.

Phase 31: Codex AI Image Generation -- wraps Google Gemini SDK for
entity-type-aware image generation with disk caching by StrKey.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from server.tools.ldm.schemas.codex import CodexEntity


# =============================================================================
# Prompt Templates
# =============================================================================

PROMPT_TEMPLATES: Dict[str, str] = {
    "character": (
        "A character portrait for a fantasy RPG game. "
        "Name: {name}. Race: {Race}. Job: {Job}. "
        "{description_clause}"
        "Style: detailed character portrait, anime RPG art, "
        "dramatic lighting, upper body shot. "
        "{grade_glow}"
    ),
    "item": (
        "A game item icon for a fantasy RPG. "
        "Item: {name}. Type: {ItemType}. "
        "{description_clause}"
        "Style: game UI icon, clean edges, centered on dark background, "
        "slight glow effect. "
        "{grade_glow}"
    ),
    "skill": (
        "A skill effect icon for a fantasy RPG game. "
        "Skill: {name}. "
        "{description_clause}"
        "Style: game UI skill icon, magical effect, "
        "glowing energy, centered on dark circular background."
    ),
    "region": (
        "A landscape scene for a fantasy RPG game region. "
        "Region: {name}. "
        "{description_clause}"
        "Style: landscape painting, wide establishing shot, "
        "atmospheric lighting, fantasy world environment."
    ),
    "gimmick": (
        "A magical seal or sigil icon for a fantasy RPG game. "
        "Seal: {name}. "
        "{description_clause}"
        "Style: magical sigil, glowing runes, centered on dark background, "
        "mystical energy."
    ),
    "faction": (
        "A heraldic faction banner for '{name}' in a fantasy game. "
        "Medieval banner design with faction emblem, ornate border, faction colors. "
        "Professional game art, heraldic style."
    ),
    "skilltree": (
        "A skill tree diagram visualization for '{name}' in a fantasy game. "
        "Branching progression paths with connected nodes, magical borders, "
        "class-themed decorations. Game UI illustration style."
    ),
}

ASPECT_RATIOS: Dict[str, str] = {
    "character": "3:4",
    "faction": "3:4",
    "region": "16:9",
    "skilltree": "16:9",
}
# Default for all others: "1:1"

GRADE_GLOW: Dict[str, str] = {
    "Common": "",
    "Uncommon": "Slight magical glow.",
    "Rare": "Bright magical aura.",
    "Epic": "Intense purple-gold magical aura.",
    "Legendary": "Brilliant golden divine radiance.",
}


# =============================================================================
# AIImageService
# =============================================================================


class AIImageService:
    """Wraps Gemini SDK for entity image generation with disk cache.

    Singleton via get_ai_image_service(). Gracefully unavailable when
    GEMINI_API_KEY is not set.
    """

    MODEL = "gemini-3-pro-image-preview"
    CACHE_DIR = Path(__file__).resolve().parents[4] / "server" / "data" / "cache" / "ai_images" / "by_strkey"

    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=api_key)
                self._available = True
                logger.info("[AI Image] Service initialized (Gemini available)")
            except ImportError as exc:
                logger.warning(f"[AI Image] google-genai package not installed: {exc}")
                self._client = None
                self._available = False
            except Exception as exc:
                logger.error(f"[AI Image] Failed to create Gemini client: {exc}")
                self._client = None
                self._available = False
        else:
            self._client = None
            self._available = False
            logger.info("[AI Image] Service initialized (no GEMINI_API_KEY -- unavailable)")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether the Gemini API is available for image generation."""
        return self._available

    # -------------------------------------------------------------------------
    # Cache operations
    # -------------------------------------------------------------------------

    def get_cached_image_path(self, strkey: str) -> Optional[Path]:
        """Return path to cached PNG if it exists, else None."""
        safe_key = self._sanitize_strkey(strkey)
        path = self.CACHE_DIR / safe_key / "generated.png"
        return path if path.exists() else None

    def save_to_cache(self, strkey: str, png_bytes: bytes, prompt: str) -> Optional[Path]:
        """Write PNG + metadata.json to cache directory.

        Returns the path on success, None on disk failure (logged but not raised).
        """
        try:
            safe_key = self._sanitize_strkey(strkey)
            cache_dir = self.CACHE_DIR / safe_key
            cache_dir.mkdir(parents=True, exist_ok=True)

            png_path = cache_dir / "generated.png"
            png_path.write_bytes(png_bytes)

            metadata = {
                "model": self.MODEL,
                "prompt": prompt,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            meta_path = cache_dir / "metadata.json"
            meta_path.write_text(json.dumps(metadata, indent=2))

            logger.debug(f"[AI Image] Cached image for {safe_key} ({len(png_bytes)} bytes)")
            return png_path
        except OSError as exc:
            logger.error(f"[AI Image] Failed to write cache for {strkey}: {exc}")
            return None

    # -------------------------------------------------------------------------
    # Prompt building
    # -------------------------------------------------------------------------

    def build_prompt(self, entity: CodexEntity) -> str:
        """Build a generation prompt from entity attributes."""
        attrs = entity.attributes or {}
        name = entity.name or entity.strkey

        # Description clause
        description_clause = ""
        if entity.description:
            description_clause = f"Description: {entity.description}. "

        # Grade glow
        grade = attrs.get("Grade", "")
        grade_glow = GRADE_GLOW.get(grade, "")

        template = PROMPT_TEMPLATES.get(entity.entity_type)
        if template is None:
            # Fallback for unknown entity types
            return (
                f"A fantasy {entity.entity_type} named {name}. "
                f"{description_clause}"
                "Style: game art, clean design."
            )

        # Build substitution dict with safe defaults
        subs = {
            "name": name,
            "description_clause": description_clause,
            "grade_glow": grade_glow,
            "Race": attrs.get("Race", "unknown race"),
            "Job": attrs.get("Job", "adventurer"),
            "ItemType": attrs.get("ItemType", "item"),
        }

        return template.format(**subs)

    def _get_aspect_ratio(self, entity_type: str) -> str:
        """Return aspect ratio string for the entity type."""
        return ASPECT_RATIOS.get(entity_type, "1:1")

    # -------------------------------------------------------------------------
    # Sanitization
    # -------------------------------------------------------------------------

    def _sanitize_strkey(self, strkey: str) -> str:
        """Sanitize StrKey for safe filesystem use."""
        # Strip null bytes
        cleaned = strkey.replace("\x00", "")
        # Strip path separators
        cleaned = cleaned.replace("/", "").replace("\\", "")
        # Strip path traversal
        cleaned = cleaned.replace("..", "")
        # Remove any remaining dangerous characters
        cleaned = re.sub(r"[^\w\-.]", "_", cleaned)

        if not cleaned:
            cleaned = "_empty_"

        # Verify resolved path stays within CACHE_DIR
        resolved = (self.CACHE_DIR / cleaned).resolve()
        cache_resolved = self.CACHE_DIR.resolve()
        try:
            resolved.relative_to(cache_resolved)
        except ValueError:
            logger.warning(f"[AI Image] Path traversal attempt: {strkey}")
            cleaned = "_sanitized_"

        return cleaned

    # -------------------------------------------------------------------------
    # Image generation
    # -------------------------------------------------------------------------

    def generate_image(self, entity: CodexEntity) -> bytes:
        """Generate an image via Gemini SDK. SYNC -- wrap in asyncio.to_thread.

        Args:
            entity: The CodexEntity to generate an image for.

        Returns:
            Raw PNG bytes.

        Raises:
            ValueError: If Gemini response contains no image data.
            RuntimeError: If service is unavailable.
        """
        if not self._available or self._client is None:
            raise RuntimeError("AI Image service unavailable (no GEMINI_API_KEY)")

        from google.genai import types

        prompt = self.build_prompt(entity)
        aspect = self._get_aspect_ratio(entity.entity_type)

        logger.info(f"[AI Image] Generating image for {entity.entity_type}/{entity.strkey}")

        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect,
                    image_size="1K",
                ),
            ),
        )

        # Extract PNG from response parts
        for part in response.parts:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data

        raise ValueError("No image in Gemini response")


# =============================================================================
# Singleton
# =============================================================================

_service_instance: Optional[AIImageService] = None


def get_ai_image_service() -> AIImageService:
    """Get or create the singleton AIImageService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AIImageService()
    return _service_instance
