# DOC-002: Chrome Persistent 404 Error Cache for Audio/Video URLs

**Discovered:** 2026-03-18
**Severity:** Critical (hours of debugging)
**Affects:** Any `<audio>` or `<video>` element with cross-origin src

---

## Symptom

- Audio plays in **incognito mode** but NOT in normal Chrome
- Clearing browser cache (`Ctrl+Shift+R`, "Clear site data", `chrome://settings/clearBrowserData`) does NOT fix it
- Only specific URLs fail — others work fine
- No errors in DevTools Console (silent failure)

## Root Cause

Chrome has a **separate error cache layer** for media resources (`<audio>`, `<video>`). When a media URL returns a 404 or CORS error, Chrome caches that failure response and **refuses to retry** the URL — even after:

- Hard refresh (`Ctrl+Shift+R`)
- "Clear site data" in DevTools Application tab
- Clearing "Cached images and files" in Chrome settings
- Running `caches.keys().then(k => k.forEach(c => caches.delete(c)))`

This error cache is:
- **Per-URL** — only the specific URLs that got errors are blocked
- **Profile-scoped** — incognito (separate profile) doesn't have it
- **NOT clearable** through normal cache-clearing UI
- **Persistent across browser restarts**

## How It Happened (Our Case)

1. `GameDataContextPanel.svelte` had a bug: used `VoicePath` attribute (`audio/characters/elder_varon_greeting.wem`) as the audio stream key
2. This produced URL: `/api/ldm/mapdata/audio/stream/audio/characters/elder_varon_greeting.wem` → **404**
3. Chrome cached this 404 for the `<audio>` element's src
4. Bug was fixed: URL changed to `/api/ldm/mapdata/audio/stream/Character_ElderVaron` → **200**
5. BUT Chrome still served the cached 404 for ElderVaron and ShadowKira (the first 2 characters clicked when the bug existed)
6. Grimjaw, Lune, Drakmar worked because they were never clicked during the broken period

## The Fix

**Add cache-busting timestamp to ALL media src URLs:**

```svelte
<!-- BROKEN — Chrome caches 404 forever -->
<audio src="{API_BASE}{mediaData.stream_url}">

<!-- FIXED — Each load is a "new" URL -->
<audio src="{API_BASE}{mediaData.stream_url}?v={Date.now()}">
```

## Additional Fixes Applied

### 1. Svelte `<audio>` Reactivity Bug

`<source src>` inside `<audio>` does NOT update reactively in Svelte. The browser caches the initial source and ignores subsequent reactive updates.

```svelte
<!-- BROKEN — src doesn't update when switching characters -->
<audio controls>
  <source src="{url}" type="audio/wav" />
</audio>

<!-- FIXED — {#key} forces element recreation -->
{#key url}
  <audio controls src="{url}?v={Date.now()}">
  </audio>
{/key}
```

### 2. Cross-Origin Audio Loading

When loading audio from a different port (Vite :5173 → Backend :8888), the `<audio>` element needs `crossorigin="anonymous"`:

```svelte
<audio controls crossorigin="anonymous" src="{url}">
```

Without this, the browser may silently block the audio load even with CORS headers configured on the server.

### 3. VoicePath vs StrKey

XML `VoicePath` attributes contain **production file paths** (`audio/characters/elder_varon_greeting.wem`) that don't exist in DEV mode. Audio lookup must use **StrKey** (`Character_ElderVaron`) which maps to TTS-generated WAV files.

```python
# WRONG — VoicePath is a production file path
stream_url = f"/api/ldm/mapdata/audio/stream/{voice_path_value}"

# RIGHT — StrKey maps to actual WAV files
stream_url = f"/api/ldm/mapdata/audio/stream/{strkey_value}"
```

### 4. Lazy Audio Index Loading

The `MapDataService._strkey_to_audio` dictionary must be lazily populated from the `audio/` directory, since TTS-generated WAV files may not exist at server startup time.

## Prevention Rules

1. **ALWAYS** add `?v=${Date.now()}` to `<audio>` and `<video>` `src` attributes
2. **ALWAYS** use `{#key url}` in Svelte when the audio/video source is reactive
3. **ALWAYS** add `crossorigin="anonymous"` for cross-origin media
4. **NEVER** use `<source>` child elements for reactive media — use `src=` directly on `<audio>`/`<video>`
5. **NEVER** use production file paths (VoicePath, AudioFile) as DEV mode stream keys — use StrKey
6. When debugging "works in incognito but not normal" → suspect **cached error responses** for media URLs

## Files Modified

| File | Change |
|------|--------|
| `server/main.py` | DEV init: XML-based StrKey→texture mapping + audio WAV index |
| `server/tools/ldm/services/mapdata_service.py` | Fuzzy image matching + lazy audio loading |
| `server/tools/ldm/routes/mapdata.py` | Direct WAV serve + Path→str fix |
| `server/tools/ldm/services/gamedata_context_service.py` | StrKey-first audio lookup |
| `locaNext/src/lib/components/ldm/GameDataContextPanel.svelte` | `{#key}` + cache-bust + crossorigin + native `<audio>` |
| `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` | `audioExists` API check before rendering player |

## Debugging Timeline

| Step | Result |
|------|--------|
| API curl tests | All 200 — backend correct |
| Playwright tests | All 5 characters play — code correct |
| Browser cache clear | Still broken — not a normal cache issue |
| Vite restart | Still broken — not HMR cache |
| Extension check | Touch VPN disabled — not extensions |
| Incognito test | **Works!** — profile-level cache issue |
| Chrome media engagement scores | Low scores but not the cause |
| Cache-busting timestamp | **Fixed!** — Chrome 404 error cache was the culprit |

**Total debugging time:** ~3 hours
**Lesson:** Always cache-bust media URLs. Chrome's error cache for audio/video is a hidden trap.

---

*Documented: 2026-03-19*
*Related: DOC-001 (Install vs Update Confusion)*
