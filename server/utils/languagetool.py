"""
LanguageTool client for grammar/spelling checking.
Connects to central LanguageTool server at 172.28.150.120:8081
"""

import httpx
from typing import Optional, List, Dict, Any
from loguru import logger

LANGUAGETOOL_URL = "http://172.28.150.120:8081/v2/check"


class LanguageToolClient:
    """Client for LanguageTool API."""

    def __init__(self, base_url: str = LANGUAGETOOL_URL):
        self.base_url = base_url

    async def check(self, text: str, language: str = "en-US") -> Dict[str, Any]:
        """
        Check text for spelling/grammar errors.

        Args:
            text: Text to check
            language: Language code (en-US, de-DE, fr, es, etc.)

        Returns:
            Dict with matches (errors) and metadata
        """
        if not text or not text.strip():
            return {"matches": [], "language": {"code": language}}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    data={"text": text, "language": language}
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning("LanguageTool server not available")
            return {"matches": [], "error": "Server unavailable"}
        except httpx.TimeoutException:
            logger.warning("LanguageTool request timed out")
            return {"matches": [], "error": "Request timed out"}
        except Exception as e:
            logger.error(f"LanguageTool error: {e}")
            return {"matches": [], "error": str(e)}

    async def check_batch(self, texts: List[str], language: str = "en-US") -> List[Dict[str, Any]]:
        """
        Check multiple texts in batch.

        Args:
            texts: List of texts to check
            language: Language code

        Returns:
            List of results, one per text
        """
        results = []
        for text in texts:
            result = await self.check(text, language)
            results.append(result)
        return results

    async def is_available(self) -> bool:
        """Check if LanguageTool server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.base_url,
                    data={"text": "test", "language": "en-US"}
                )
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
languagetool = LanguageToolClient()
