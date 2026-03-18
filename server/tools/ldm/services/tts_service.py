"""TTS Service -- Qwen3-TTS Korean voice generation for Codex entities.

Phase 41: Qwen3-TTS Korean Voice Generation -- wraps Qwen3-TTS 1.7B
VoiceDesign model for character-specific voice generation with disk caching.

Uses VoiceDesign (not CustomVoice) so each character gets a truly distinct
voice timbre, not just emotion variations of the same speaker.
"""

from __future__ import annotations

import re
import threading
import wave
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from server.tools.ldm.schemas.codex import CodexEntity


# =============================================================================
# Voice Profiles — VoiceDesign instructs (MUST be English/Chinese)
# =============================================================================

VOICE_PROFILES: Dict[str, Dict[str, str]] = {
    "Character_ElderVaron": {
        "instruct": (
            "Elderly male, 70+ years old, deep resonant bass voice, "
            "very slow and deliberate pace, wise and solemn, "
            "warm grandfatherly undertone, suitable for ancient sage narration"
        ),
        "monologue": (
            "나는 바론... 이 봉인된 도서관의 수호자다. "
            "삼백 년이 넘는 세월 동안, 나는 이곳에서 고대의 지식을 지켜왔다. "
            "세상은 균형 위에 서 있고, 그 열쇠는 바로 이 도서관 깊은 곳에 잠들어 있지. "
            "하지만 어둠이 다시 움직이고 있다... 그래서 네가 필요한 것이다. "
            "들어오너라. 현자의 결사가 너를 기다리고 있었다."
        ),
    },
    "Character_ShadowKira": {
        "instruct": (
            "Young adult female, 25 years old, sharp and cold voice, "
            "medium-fast pace, menacing and confident, slightly husky "
            "with predatory edge, suitable for villain character"
        ),
        "monologue": (
            "보이지 않는다고? 좋아, 그게 정상이야. "
            "나는 키라. 어둠의 교단이 길러낸 마지막 걸작. "
            "그림자 속에서 태어나, 그림자 속에서 움직이지. 흔적 같은 건 남기지 않아. "
            "저 늙은 현자가 지키는 도서관... 그 안에 내가 원하는 것이 있어. "
            "방해하지 마. 다음에 내 존재를 느꼈을 땐, 이미 늦을 테니까."
        ),
    },
    "Character_Grimjaw": {
        "instruct": (
            "Middle-aged male, 45 years old, rough gravelly voice, "
            "medium pace, gruff but warm-hearted, powerful and booming, "
            "slightly hoarse from forge smoke, suitable for dwarven craftsman"
        ),
        "monologue": (
            "허! 또 검 하나 만들어 달라는 놈이 찾아왔군. "
            "난 그림죠. 검은별 금속을 다룰 수 있는 유일한 대장장이지. "
            "내 필생의 역작, 검은별 대검... 어둠을 베고 빛을 담는 검이야. "
            "하지만 아직 그걸 들 자격이 있는 자는 나타나지 않았어. "
            "그래서, 네 실력은 어떤데? 어디 한번 보여봐."
        ),
    },
    "Character_Lune": {
        "instruct": (
            "Young female, 20 years old, light and nimble voice, "
            "fast pace, alert and energetic, bright clear soprano "
            "with playful undertone, suitable for elven scout character"
        ),
        "monologue": (
            "쉿, 조용히. 이 숲에는 귀를 가진 것들이 많아. "
            "나는 루네. 봉인된 도서관으로 가는 길을 아는 건 나뿐이야. "
            "모든 샛길, 모든 함정, 어둠의 교단이 심어둔 감시자들의 위치까지... "
            "전부 내 머릿속에 있어. "
            "자, 따라와. 한 발짝이라도 벗어나면 돌아갈 수 없을지도 몰라."
        ),
    },
    "Character_Drakmar": {
        "instruct": (
            "Adult male, 35 years old, rich baritone voice, "
            "measured and precise pace, intellectual and mysterious, "
            "smooth with subtle intensity, suitable for scholar mage narration"
        ),
        "monologue": (
            "흥미롭군... 여기까지 들어올 수 있다니. "
            "나는 드라크마르. 이 도서관의 고대 문서를 해독하는 자다. "
            "장로 바론은 나를 오른팔이라 부르지만... 솔직히 나는 그 이상을 원한다. "
            "금지된 지식이라고? 금지된 것은 없어. 이해하지 못하는 것만 있을 뿐이지. "
            "내 연구를 방해한다면... 그건 보장할 수 없어."
        ),
    },
}

DEFAULT_VOICE_PROFILE: Dict[str, Optional[str]] = {
    "instruct": (
        "Young adult, clear and neutral voice, medium pace, "
        "friendly and professional, suitable for game narration"
    ),
    "monologue": None,
}


# =============================================================================
# TTSService
# =============================================================================


class TTSService:
    """Wraps Qwen3-TTS VoiceDesign for Korean voice generation with disk cache.

    Uses VoiceDesign model so each character gets a truly distinct voice timbre.
    Singleton via get_tts_service(). Model loads lazily on first request.
    """

    def __init__(self, audio_dir: Path) -> None:
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._available: Optional[bool] = None
        self._load_lock = threading.Lock()

    @property
    def available(self) -> bool:
        """Whether qwen-tts is importable and GPU is accessible."""
        if self._available is None:
            try:
                import qwen_tts  # noqa: F401
                self._available = True
            except ImportError:
                logger.info("[TTS] qwen-tts package not installed -- unavailable")
                self._available = False
            except Exception as exc:
                logger.error(f"[TTS] qwen-tts import failed: {exc}")
                self._available = False
        return self._available

    def _load_model(self) -> None:
        """Lazy-load the Qwen3-TTS VoiceDesign model (thread-safe)."""
        import time

        start = time.monotonic()
        try:
            from qwen_tts import Qwen3TTSModel

            self._model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
            )
            elapsed = time.monotonic() - start
            logger.info(f"[TTS] VoiceDesign model loaded in {elapsed:.1f}s")
        except ImportError:
            logger.error("[TTS] qwen_tts module not available")
            self._available = False
            raise
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(f"[TTS] Model load failed after {elapsed:.1f}s: {exc}")
            self._available = False
            raise

    @staticmethod
    def _sanitize_strkey(strkey: str) -> str:
        """Sanitize StrKey for safe filesystem use."""
        cleaned = strkey.replace("\x00", "").replace("/", "").replace("\\", "").replace("..", "")
        cleaned = re.sub(r"[^\w\-.]", "_", cleaned)
        return cleaned or "_empty_"

    def get_cached_audio_path(self, strkey: str) -> Optional[Path]:
        """Return path to cached WAV if it exists, else None."""
        safe_key = self._sanitize_strkey(strkey)
        path = self.audio_dir / f"{safe_key}.wav"
        # Verify resolved path stays within audio_dir
        try:
            path.resolve().relative_to(self.audio_dir.resolve())
        except ValueError:
            logger.warning(f"[TTS] Path traversal attempt: {strkey}")
            return None
        return path if path.exists() else None

    def get_audio_duration_ms(self, wav_path: Path) -> int:
        """Get duration of a WAV file in milliseconds."""
        try:
            with wave.open(str(wav_path), "rb") as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return int((frames / rate) * 1000)
        except Exception as exc:
            logger.warning(f"[TTS] Failed to read WAV duration for {wav_path}: {exc}")
            return 0

    def _build_text(self, entity: CodexEntity, profile: dict) -> str:
        """Build the best TTS text from entity data.

        Priority:
        1. Character monologue (if defined in voice profile — best quality)
        2. Entity description field
        3. CharacterDesc from attributes (Korean desc for characters)
        4. Entity name as fallback
        """
        monologue = profile.get("monologue")
        if monologue:
            return monologue

        if entity.description:
            return entity.description.replace("<br/>", "\n")

        attrs = entity.attributes or {}
        char_desc = attrs.get("CharacterDesc", "")
        if char_desc:
            return char_desc.replace("<br/>", "\n")

        desc_kr = attrs.get("DescriptionKR", "")
        if desc_kr:
            return desc_kr.replace("<br/>", "\n")

        return entity.name

    def generate_voice(self, entity: CodexEntity) -> Path:
        """Generate Korean voice audio for an entity. SYNC — wrap in asyncio.to_thread.

        Uses VoiceDesign model for truly distinct character voices.
        Caches result to disk; returns path to the .wav file.
        """
        safe_key = self._sanitize_strkey(entity.strkey)

        # Check cache first
        cached = self.get_cached_audio_path(entity.strkey)
        if cached:
            logger.debug(f"[TTS] Cache hit for {safe_key}")
            return cached

        # Thread-safe lazy model load (double-checked locking)
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    self._load_model()

        profile = VOICE_PROFILES.get(entity.strkey, DEFAULT_VOICE_PROFILE)
        text = self._build_text(entity, profile)

        if not text.strip():
            raise ValueError(f"No text available for TTS generation: {safe_key}")

        logger.info(
            f"[TTS] Generating voice for {safe_key} "
            f"({len(text)} chars, VoiceDesign)"
        )

        # Generate audio using VoiceDesign
        try:
            wav_arrays, sample_rate = self._model.generate_voice_design(
                text=text,
                instruct=profile["instruct"],
                language="korean",
                non_streaming_mode=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.05,
                max_new_tokens=2048,
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            if "out of memory" in exc_str or "oom" in exc_str:
                logger.error(f"[TTS] GPU OOM for {safe_key} -- disabling TTS")
                self._available = False
                raise ValueError("GPU out of memory -- TTS temporarily disabled")
            raise

        # Validate output
        if not wav_arrays:
            raise ValueError(f"TTS model returned no audio for {safe_key}")

        import numpy as np
        import soundfile as sf

        wav_data = wav_arrays[0]
        if not isinstance(wav_data, np.ndarray):
            raise ValueError(f"Unexpected TTS output type: {type(wav_data)}")

        # Atomic write: temp file then rename
        out_path = self.audio_dir / f"{safe_key}.wav"
        tmp_path = out_path.with_suffix(".tmp")
        try:
            sf.write(str(tmp_path), wav_data, sample_rate)
            tmp_path.rename(out_path)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            logger.error(f"[TTS] Failed to save WAV for {safe_key}: {exc}")
            raise ValueError(f"Voice generated but failed to save: {exc}")

        file_size = out_path.stat().st_size
        duration_ms = self.get_audio_duration_ms(out_path)
        logger.info(
            f"[TTS] Generated voice for {safe_key} "
            f"({file_size} bytes, {duration_ms}ms, {sample_rate}Hz)"
        )
        return out_path


# =============================================================================
# Singleton
# =============================================================================

_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the singleton TTSService instance."""
    global _tts_service
    if _tts_service is None:
        project_root = Path(__file__).resolve().parents[4]
        audio_dir = project_root / "audio"
        _tts_service = TTSService(audio_dir=audio_dir)
        logger.info(f"[TTS] Service initialized (audio_dir={audio_dir})")
    return _tts_service
