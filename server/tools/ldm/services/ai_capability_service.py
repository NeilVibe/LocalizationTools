"""
Phase 45: AI Capability Service - Runtime AI engine detection.

Detects availability of AI engines (Model2Vec, FAISS, Ollama, TTS, Image Gen)
at runtime to prevent hard-crashes when engines are missing in offline bundles.

Each probe is wrapped in try/except -- never crashes, never raises.
Returns three-state: "available", "unavailable", "checking".
"""
from __future__ import annotations

import os
import shutil
import time
from typing import Dict

from loguru import logger

from server.tools.shared.embedding_engine import is_light_mode


class AICapabilityService:
    """Runtime AI engine availability detection."""

    def __init__(self) -> None:
        self._capabilities: Dict[str, str] = {}
        self._last_check: float = 0.0

    def check_all(self) -> Dict[str, str]:
        """
        Probe each AI engine and return availability dict.

        Each probe is wrapped in try/except -- never crashes.
        Values: "available" | "unavailable"
        """
        logger.info("[AI-CAPS] Probing AI engine availability...")
        caps: Dict[str, str] = {}

        # 1. Model2Vec Embeddings
        caps["embeddings"] = self._check_embeddings()

        # 2. FAISS Semantic Search
        caps["semantic_search"] = self._check_faiss()

        # 3. Ollama AI Summary (Qwen3)
        caps["ai_summary"] = self._check_ollama()

        # 4. TTS (Qwen-TTS)
        caps["tts"] = self._check_tts()

        # 5. Image Generation (fal.ai)
        caps["image_gen"] = self._check_image_gen()

        self._capabilities = caps
        self._last_check = time.time()

        available_count = sum(1 for v in caps.values() if v == "available")
        logger.info(f"[AI-CAPS] Probe complete: {available_count}/{len(caps)} engines available")
        for engine, status in caps.items():
            logger.debug(f"[AI-CAPS]   {engine}: {status}")

        return caps

    def _check_embeddings(self) -> str:
        """Check if Model2Vec is importable and model path exists."""
        try:
            from model2vec import StaticModel  # noqa: F401
            # Also check for bundled model path
            from server.tools.shared.embedding_engine import Model2VecEngine
            local_path = Model2VecEngine._find_local_model_path()
            if local_path:
                logger.debug(f"[AI-CAPS] Model2Vec: found local model at {local_path}")
            else:
                logger.debug("[AI-CAPS] Model2Vec: importable (will download from HuggingFace)")
            return "available"
        except ImportError:
            logger.debug("[AI-CAPS] Model2Vec: model2vec package not installed")
            return "unavailable"
        except Exception as e:
            logger.debug(f"[AI-CAPS] Model2Vec probe error: {e}")
            return "unavailable"

    def _check_faiss(self) -> str:
        """Check if FAISS is importable and functional."""
        try:
            import faiss  # noqa: F401
            # Quick functional check
            faiss.IndexFlatIP(1)
            return "available"
        except ImportError:
            logger.debug("[AI-CAPS] FAISS: faiss-cpu package not installed")
            return "unavailable"
        except Exception as e:
            logger.debug(f"[AI-CAPS] FAISS probe error: {e}")
            return "unavailable"

    def _check_ollama(self) -> str:
        """Check if Ollama is running and responsive."""
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if resp.status_code == 200:
                return "available"
            logger.debug(f"[AI-CAPS] Ollama: responded with status {resp.status_code}")
            return "unavailable"
        except ImportError:
            logger.debug("[AI-CAPS] Ollama: httpx package not installed")
            return "unavailable"
        except Exception as e:
            logger.debug(f"[AI-CAPS] Ollama probe error: {e}")
            return "unavailable"

    def _check_tts(self) -> str:
        """Check if Qwen-TTS CLI or endpoint is available."""
        try:
            if shutil.which("qwen-tts") is not None:
                return "available"
            # Also check for the TTS Python package
            try:
                import qwen_tts  # noqa: F401
                return "available"
            except ImportError:
                pass
            logger.debug("[AI-CAPS] TTS: qwen-tts CLI not found and package not installed")
            return "unavailable"
        except Exception as e:
            logger.debug(f"[AI-CAPS] TTS probe error: {e}")
            return "unavailable"

    def _check_image_gen(self) -> str:
        """Check if FAL_KEY environment variable is set for fal.ai."""
        try:
            fal_key = os.environ.get("FAL_KEY")
            if fal_key:
                return "available"
            logger.debug("[AI-CAPS] Image Gen: FAL_KEY not set")
            return "unavailable"
        except Exception as e:
            logger.debug(f"[AI-CAPS] Image Gen probe error: {e}")
            return "unavailable"

    def get_capabilities(self) -> Dict[str, str]:
        """Return cached capabilities. If empty, calls check_all() first."""
        if not self._capabilities:
            self.check_all()
        return self._capabilities

    def is_available(self, engine: str) -> bool:
        """Check if a specific engine is available."""
        return self._capabilities.get(engine) == "available"

    def get_status(self) -> dict:
        """Return full status dict including capabilities, timestamps, and mode."""
        if not self._capabilities:
            self.check_all()
        return {
            "capabilities": self._capabilities,
            "last_check": self._last_check,
            "light_mode": is_light_mode(),
        }


# Singleton
_service_instance: AICapabilityService | None = None


def get_ai_capability_service() -> AICapabilityService:
    """Get the singleton AICapabilityService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AICapabilityService()
    return _service_instance
