# DOC-003: Image Cache-Busting Fix

**Date:** 2026-03-17
**Status:** Fixed (3-layer defense)

---

## Problem

- Gemini AI-generated character portraits (512x512, ~400KB) replaced old PIL placeholder images (256x256) at the same URLs
- Backend thumbnail endpoint (`GET /api/ldm/mapdata/thumbnail/{name}`) had `Cache-Control: public, max-age=86400` (24h cache)
- Browsers kept serving the old cached placeholder images, ignoring the new files on disk
- Users reported "no images" or seeing old V/SAGE letter placeholders instead of AI portraits

## Root Cause

Browser HTTP cache. The thumbnail URL didn't change when the underlying file was replaced, so browsers served stale cached responses.

## Fix Applied (3 layers)

### Layer 1: Frontend cache-busting (immediate, HMR)

- Added `?v=${Date.now()}` query param to all thumbnail `<img src>` URLs in:
  - `GameDataContextPanel.svelte` (Media tab)
  - Codex components (if applicable)
  - Map components (if applicable)
- Pattern: `{@const thumbUrl = `${API_BASE}${mediaData.thumbnail_url}?v=${Date.now()}`}`
- Takes effect immediately via Vite HMR

### Layer 2: Backend cache headers (next restart)

- Changed `Cache-Control: public, max-age=86400` to `Cache-Control: no-cache, must-revalidate` + ETag
- ETag based on file mtime for proper conditional requests
- File: `server/tools/ldm/routes/mapdata.py`

### Layer 3: Auto-index on startup (next restart)

- Added gamedata index auto-build to `server/main.py` lifespan function
- Eliminates "index lost on restart" bug

## Other Bugs Fixed

- **AI Context tab not auto-triggering:** Added explicit fetch in `switchTab()` function
- **Index lost on restart:** Auto-build in server lifespan

## Lesson Learned

When replacing image files at the same URL path, ALWAYS bust the browser cache. Either:

- Add version/timestamp query params on frontend
- Use `Cache-Control: no-cache` with ETag on backend
- Both (defense in depth)
