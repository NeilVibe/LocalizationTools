# Master Plan: Audio Codex Polish + Light Build Option B

**Created:** 2026-04-02
**Status:** IN PROGRESS
**Goal:** Fix Audio Codex to MDG quality + Enable Light Build users to connect to Admin's FastAPI

---

## Phase A: Audio Codex Fixes (CODED — needs commit + build)

| # | Task | Status | Notes |
|---|------|--------|-------|
| A1 | Audio playback: remove RIFF header shortcut, always vgmstream | DONE | Root cause of "default ding" sound |
| A2 | Audio playback: add SND_NODEFAULT + CREATE_NO_WINDOW | DONE | Matches MDG subprocess pattern |
| A3 | Audio playback: add PCM WAV validation on cache + post-conversion | DONE | Invalidates corrupt cached WEM-copies |
| A4 | Audio playback: add diagnostic logging throughout pipeline | DONE | WEM path, vgmstream output, WAV size |
| A5 | Language change: keep selection (don't clear selectedAudio/Event) | DONE | MDG: language only changes audio folder |
| A6 | Explorer tree: AUTO_EXPAND_DEPTH = 0 (fully collapsed) | DONE | User drills down by clicking |
| A7 | Commit all changes | TODO | |
| A8 | Trigger build (user approval required) | TODO | |

**Files modified:**
- `server/tools/ldm/services/media_converter.py`
- `server/tools/ldm/services/audio_playback.py`
- `locaNext/src/lib/components/pages/AudioCodexPage.svelte`
- `locaNext/src/lib/components/ldm/AudioExportTree.svelte`

---

## Phase B: Verify Existing Infrastructure

| # | Task | Status | Notes |
|---|------|--------|-------|
| B1 | Verify admin dashboard starts (`cd adminDashboard && npm run dev`) | TODO | Port 5174, built Nov 2025 |
| B2 | Verify user creation works (create user → login in main app) | TODO | Backend APIs may have changed |
| B3 | Verify admin dashboard API client matches current backend | TODO | Check `adminDashboard/src/lib/api/client.js` |
| B4 | Document what works and what's broken | TODO | |

**Why this matters:** If admin dashboard user CRUD is broken, we fix it BEFORE building Option B. No point connecting Light builds if admin can't create users.

---

## Phase C: Server Settings Redesign (Option B UX)

**Current problem:** ServerSettingsModal shows PostgreSQL internals (`locanext_service`, port 5432, database name). Users see this and think they need to enter their LocaNext login credentials. WRONG.

**For Option B, users only need:** Server IP address. That's it.

| # | Task | Status | Notes |
|---|------|--------|-------|
| C1 | New health check endpoint: `GET /api/health` (no auth) | TODO | Returns `{status, version, server_mode, users_count}` |
| C2 | Redesign ServerSettingsModal for Light build | TODO | ONLY: Server Address field + Test + Save |
| C3 | "Test Connection" tests FastAPI health, NOT PG directly | TODO | Hit `/api/health` on admin's IP |
| C4 | Save server IP to local config (`server-config.json`) | TODO | Already have `config.save_user_config()` |
| C5 | On app startup: if server IP configured, set API_BASE | TODO | Check `getApiBase()` in `api.js` |
| C6 | Admin mode: keep PG status info but label clearly | TODO | "Internal — managed automatically" |

**New ServerSettingsModal layout (Light build):**
```
┌─────────────────────────────────┐
│ Server Connection               │
│                                 │
│ [Online ✓] Connected to PEARL   │
│ LAN IP: 10.0.0.1            │
│                                 │
│ Server Address: [10.0.0.1 ] │
│                                 │
│ [Test Connection] [Save]        │
│                                 │
│ Status: Connected (12ms)        │
│ Server: LocaNext v14.0          │
│ Users: 3 active                 │
└─────────────────────────────────┘
```

---

## Phase D: Admin LAN Exposure

| # | Task | Status | Notes |
|---|------|--------|-------|
| D1 | Add server_mode="lan_server" config option | TODO | Already in server-config.json schema |
| D2 | When lan_server: bind FastAPI on 0.0.0.0:8888 | TODO | Currently hardcoded to localhost |
| D3 | CORS: allow LAN subnet when in lan_server mode | TODO | Auto-detect /24 subnet |
| D4 | Show admin's LAN IP in admin dashboard | TODO | `_get_lan_ip()` already exists |
| D5 | "Enable LAN Access" button in admin dashboard or setup wizard | TODO | Toggles server_mode |
| D6 | Restart required notification after enabling | TODO | |

**Where FastAPI binds (server/main.py):**
```python
# Current: uvicorn.run(app, host="127.0.0.1", port=8888)
# Option B: uvicorn.run(app, host="0.0.0.0", port=8888)  # when lan_server mode
```

---

## Phase E: Light Build Connection Flow

| # | Task | Status | Notes |
|---|------|--------|-------|
| E1 | Light build: detect no local PG → show "Connect to Server" | TODO | Check light-mode.flag |
| E2 | First-run: prompt for server IP (or show settings modal) | TODO | |
| E3 | API_BASE switching: all API calls go to admin IP | TODO | Change `getApiBase()` logic |
| E4 | Login: user logs in with credentials admin created | TODO | Same /api/auth/login endpoint, different host |
| E5 | JWT token: store locally, send to admin's backend | TODO | Already works — just different host |
| E6 | Local features: MegaIndex/FAISS/audio still use local backend | TODO | Hybrid: DB from admin, compute local |
| E7 | Handle offline/disconnect: graceful fallback | TODO | Toast + retry |

**The key insight:** For MVP, the Light build can run NO local backend at all. It's just the Svelte frontend pointing at admin's IP. MegaIndex, audio, etc. all come from admin's server. This is the SIMPLEST approach.

**Later:** Hybrid mode where Light build runs local backend for heavy compute but uses admin's PG for data.

---

## Phase F: Build & End-to-End Test

| # | Task | Status | Notes |
|---|------|--------|-------|
| F1 | Build Full Admin (with PG, setup wizard) | TODO | BUILD_TRIGGER.txt = "Build" |
| F2 | Build Light (no PG, server IP settings) | TODO | BUILD_TRIGGER.txt = "Build Light" |
| F3 | Test: Admin installs → setup wizard → PG up | TODO | On PEARL |
| F4 | Test: Admin opens dashboard → creates user account | TODO | localhost:5174 |
| F5 | Test: Admin enables LAN access | TODO | |
| F6 | Test: User installs Light → enters admin IP → connects | TODO | On user PC |
| F7 | Test: User logs in → sees data → can edit | TODO | |
| F8 | Test: Audio playback works on both builds | TODO | vgmstream conversion |

---

## Priority Order

1. **Phase A** — Commit audio fixes, trigger build (QUICK)
2. **Phase B** — Verify admin dashboard works (QUICK)
3. **Phase C** — Server Settings redesign (MEDIUM, 1 session)
4. **Phase D** — Admin LAN exposure (MEDIUM, same session as C)
5. **Phase E** — Light Build connection flow (MEDIUM-LARGE, 1-2 sessions)
6. **Phase F** — End-to-end testing (after E)

---

## Architecture Summary (Option B)

```
ADMIN PC (PEARL)                         USER PC (Light Build)
┌──────────────────────┐                ┌──────────────────────┐
│ LocaNext Full Admin  │                │ LocaNext Light       │
│                      │                │                      │
│ Svelte Frontend ─────┼── port 5173    │ Svelte Frontend ─────┤
│        │             │                │        │             │
│        ▼             │                │        │ API_BASE =  │
│ FastAPI Backend ─────┼── port 8888 ◄──┼────────┘ PEARL:8888  │
│        │             │    (0.0.0.0)   │                      │
│        ▼             │                │ No local backend     │
│ PostgreSQL ──────────┼── port 5432    │ No PostgreSQL        │
│   (localhost only)   │                │ No setup wizard      │
│                      │                │                      │
│ Admin Dashboard ─────┼── port 5174    │                      │
│   (localhost only)   │                └──────────────────────┘
└──────────────────────┘
```

**Data flow:** User's browser → HTTP → Admin's FastAPI → PG → response back
**Auth flow:** User enters admin IP → logs in with admin-created credentials → gets JWT → uses JWT for all requests
**No PG exposure:** Users never see PostgreSQL. Never need PG credentials. Backend handles everything.
