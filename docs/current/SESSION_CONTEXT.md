# Session Context — 2026-04-02 Evening

## Current Work
- Audio Codex fixes CODED, not yet committed
- Master plan written: `docs/current/PLAN_LIGHT_BUILD_AND_AUDIO.md`

## What's Ready to Commit
- `server/tools/ldm/services/media_converter.py` — RIFF shortcut removed, PCM validation, CREATE_NO_WINDOW
- `server/tools/ldm/services/audio_playback.py` — SND_NODEFAULT, WEM check, diagnostic logging
- `locaNext/src/lib/components/pages/AudioCodexPage.svelte` — language change keeps selection
- `locaNext/src/lib/components/ldm/AudioExportTree.svelte` — AUTO_EXPAND_DEPTH=0

## Next Steps (in order)
1. Commit audio fixes → trigger build
2. Verify admin dashboard works (port 5174, user CRUD)
3. Server Settings redesign for Option B
4. Admin LAN exposure (0.0.0.0 binding)
5. Light Build connection flow

## Key Decisions Made
- **Option B confirmed:** Light build connects to Admin's FastAPI over HTTP. No direct PG.
- **Admin Dashboard EXISTS:** `adminDashboard/` — 6 pages, user CRUD, 17 endpoints
- **No PG in Light build:** Users only need Server IP. Backend handles everything.
