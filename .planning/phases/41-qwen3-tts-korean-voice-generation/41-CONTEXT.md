# Phase 41: Qwen3-TTS Korean Voice Generation - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Deep research session (2026-03-17)

<domain>
## Phase Boundary

Install Qwen3-TTS 1.7B CustomVoice model and integrate Korean voice generation into the LocaNext Codex. Generate unique voice audio for each of the 5 game characters using their Korean descriptions, with different voice profiles per character. Wire up frontend audio playback in entity detail views.

</domain>

<decisions>
## Implementation Decisions

### TTS Model
- Qwen3-TTS 1.7B CustomVoice (Apache 2.0)
- Install: `pip install -U qwen-tts`
- FlashAttention 2 for 30-40% speedup: `pip install -U flash-attn --no-build-isolation`
- Model ID: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`
- VRAM: 6-8 GB on RTX 4070 Ti (12GB available)
- Native Korean voice: "Sohee" (warm female)
- Voice cloning: 3s reference audio supported
- Latency: 97ms streaming

### Backend Service
- New file: `server/tools/ldm/services/tts_service.py`
- Singleton pattern (same as CodexService, WorldMapService)
- Lazy model loading (load on first TTS request, not on startup)
- Generate .wav files, store in mock_gamedata/audio/
- Cache generated audio by strkey (don't regenerate if file exists)

### API Endpoint
- `POST /api/ldm/codex/generate-voice/{strkey}` — generate voice for entity
- `GET /api/ldm/codex/audio/{strkey}` — serve generated audio file (already exists partially)
- Response: `{ "audio_url": "/api/ldm/codex/audio/{strkey}", "duration_ms": 1500 }`

### Voice Profiles (5 Characters)
- 장로 바론 (Elder Varon) — deep, wise, elderly male voice
- 그림자 암살자 키라 (Shadow Assassin Kira) — sharp, cold, female voice
- 대장장이 그림조 (Blacksmith Grimjaw) — gruff, strong, male voice
- 정찰병 루네 (Scout Lune) — young, alert, female voice
- 마법사 드라크마르 (Mage Drakmar) — mysterious, echoing, male voice

### Frontend
- CodexEntityDetail.svelte already has audio player section
- Wire it to use generated audio URL
- Show "Generate Voice" button if no audio exists
- Loading state while generating (~2-5s)
- Auto-play option after generation

### Claude's Discretion
- Voice generation prompt engineering (how to describe each character's voice style)
- Error handling for GPU OOM (graceful fallback)
- Whether to use streaming or batch generation
- Audio format (wav vs mp3 — wav for quality, mp3 for size)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend Patterns
- `server/tools/ldm/services/codex_service.py` — singleton service pattern, entity registry
- `server/tools/ldm/routes/codex.py` — existing audio endpoint pattern
- `server/tools/ldm/schemas/codex.py` — CodexEntity schema (has audio_key field)

### Frontend
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — entity detail with audio player
- `locaNext/src/lib/components/pages/CodexPage.svelte` — page that hosts entity detail

### Test Fixtures
- `tests/fixtures/mock_gamedata/audio/` — existing audio placeholder files
- `tests/fixtures/mock_gamedata/StaticInfo/characterinfo/characterinfo_showcase.staticinfo.xml` — character data

### Project Rules
- `CLAUDE.md` — loguru logger only, never print()
- `CLAUDE.md` — Svelte 5 runes, optimistic UI

</canonical_refs>

<specifics>
## Specific Ideas

- Use character's Korean description as the TTS input text
- Each character gets a distinct voice by modifying the generation parameters
- For voice cloning: could use the existing .wem audio files as reference (if convertible)
- Store generated audio alongside existing texture/audio fixtures
- The Sohee base voice can be modified via prompt engineering for different characters

</specifics>

<deferred>
## Deferred Ideas

- Real-time streaming TTS (generate as user reads) — v2
- Voice cloning from uploaded reference audio — v2
- Multi-language TTS (generate same line in KR/JP/EN) — v2
- Integration with game engine audio pipeline — v2

</deferred>

---

*Phase: 41-qwen3-tts-korean-voice-generation*
*Context gathered: 2026-03-18 via deep research session*
