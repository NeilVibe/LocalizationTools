"""
LanguageTool client for grammar/spelling checking.
Connects to LanguageTool server (configured in config.py).

LAZY LOAD: Server starts on-demand and stops after idle timeout (5 min).
Saves ~900MB RAM when grammar check not in use.
"""

import httpx
import asyncio
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

# Import URL from central config (never hardcode!)
from server.config import LANGUAGETOOL_URL
IDLE_TIMEOUT_SECONDS = 300  # 5 minutes
STARTUP_TIMEOUT_SECONDS = 30  # Max wait for server to start
STARTUP_CHECK_INTERVAL = 1.0  # Check every second during startup


class LanguageToolClient:
    """
    Client for LanguageTool API with lazy loading.

    The LanguageTool server starts on-demand when needed and
    stops automatically after 5 minutes of inactivity.
    """

    def __init__(self, base_url: str = LANGUAGETOOL_URL):
        self.base_url = base_url
        self._last_use: Optional[datetime] = None
        self._idle_task: Optional[asyncio.Task] = None
        self._starting = False

    async def _start_server(self) -> bool:
        """Start the LanguageTool systemd service."""
        if self._starting:
            # Already starting, wait for it
            for _ in range(STARTUP_TIMEOUT_SECONDS):
                await asyncio.sleep(STARTUP_CHECK_INTERVAL)
                if await self.is_available():
                    return True
            return False

        self._starting = True
        try:
            logger.info("Starting LanguageTool server (lazy load)...")

            # Start via systemctl
            result = subprocess.run(
                ["sudo", "systemctl", "start", "languagetool"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"Failed to start LanguageTool: {result.stderr}")
                return False

            # Wait for server to be ready
            for i in range(STARTUP_TIMEOUT_SECONDS):
                await asyncio.sleep(STARTUP_CHECK_INTERVAL)
                if await self.is_available():
                    logger.success(f"LanguageTool started in {i+1}s")
                    return True

            logger.error("LanguageTool failed to start within timeout")
            return False
        finally:
            self._starting = False

    async def _stop_server(self) -> None:
        """Stop the LanguageTool systemd service."""
        logger.info("Stopping LanguageTool server (idle timeout)...")
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "languagetool"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("LanguageTool stopped (saving ~900MB RAM)")
            else:
                logger.warning(f"Failed to stop LanguageTool: {result.stderr}")
        except Exception as e:
            logger.error(f"Error stopping LanguageTool: {e}")

    async def _idle_monitor(self) -> None:
        """Background task that stops server after idle timeout."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            if self._last_use is None:
                continue

            idle_time = datetime.now() - self._last_use
            if idle_time.total_seconds() >= IDLE_TIMEOUT_SECONDS:
                if await self.is_available():
                    await self._stop_server()
                    self._last_use = None
                break  # Task complete

        self._idle_task = None

    def _update_last_use(self) -> None:
        """Update last use timestamp and start idle monitor if needed."""
        self._last_use = datetime.now()

        # Start idle monitor if not running
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_monitor())

    async def ensure_running(self) -> bool:
        """Ensure the LanguageTool server is running, start if needed."""
        if await self.is_available():
            self._update_last_use()
            return True

        # Server not running, start it
        if await self._start_server():
            self._update_last_use()
            return True

        return False

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

        # Lazy load: ensure server is running
        if not await self.ensure_running():
            return {"matches": [], "error": "Server unavailable (failed to start)"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    data={"text": text, "language": language}
                )
                response.raise_for_status()
                self._update_last_use()
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
        # Ensure running once for the whole batch
        if not await self.ensure_running():
            return [{"matches": [], "error": "Server unavailable"} for _ in texts]

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

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the LanguageTool service."""
        available = await self.is_available()
        return {
            "available": available,
            "server_url": self.base_url,
            "last_use": self._last_use.isoformat() if self._last_use else None,
            "idle_timeout_seconds": IDLE_TIMEOUT_SECONDS,
            "lazy_load_enabled": True
        }


# Singleton instance
languagetool = LanguageToolClient()
