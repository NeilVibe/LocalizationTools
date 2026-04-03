# Client-Side vs Server-Side Processing

> **Rule: 99% local, 1% sync.** Each Electron app runs its own embedded Python backend. Heavy processing NEVER goes over the network. Only lightweight DB sync (language data, TM, users) uses PostgreSQL.

## Architecture

```
User's PC (LOCAL — 99%)              Shared PostgreSQL (SYNC — 1%)
├── Embedded Python FastAPI          ├── Language data rows
├── GameData/XML parsing             ├── TM entries
├── MegaIndex (in-memory, 1GB+)     ├── File/project/folder metadata
├── FAISS indexes + Model2Vec        ├── User auth/sessions
├── Audio conversion (WEM→WAV)       ├── WebSocket real-time sync
├── Merge to disk (XML write)        ├── Telemetry/logs/stats
├── XLSTransfer/QuickSearch          └── AI API proxy (key security)
└── All UI rendering (Svelte 5)
```

## LOCAL — Runs on Each User's PC

| Feature | Route | DB? |
|---------|-------|-----|
| GameData browse/tree/rows/save | `/api/ldm/gamedata/*` | NO |
| MegaIndex build/status/entity | `/api/ldm/mega/*` | NO |
| All Codex pages (items, chars, quests, skills, audio, regions, gimmicks) | `/api/ldm/codex/*` | NO |
| MapData images/audio | `/api/ldm/mapdata/*` | NO |
| World Map | `/api/ldm/worldmap` | NO |
| XLSTransfer (dictionary, translate) | `/api/v2/xlstransfer/*` | Optional (tracking) |
| QuickSearch (dictionary, search, QA) | `/api/v2/quicksearch/*` | Optional (tracking) |
| KR-Similar | `/api/v2/kr-similar/*` | NO |
| Model2Vec embedding | (startup) | NO |
| FAISS index search | (in TM search) | NO |
| Audio playback | (winsound) | NO |
| Merge to file/folder | `/api/ldm/merge/to-*` | YES (reads rows) |
| Merge preview/execute | `/api/merge/*` | YES (reads rows) |

## SYNCED — Through Shared PostgreSQL

| Feature | Route | Why Server |
|---------|-------|-----------|
| Language data rows | `/api/ldm/rows/*` | Multi-user real-time editing |
| Projects/folders/files | `/api/ldm/projects/*`, `/folders/*`, `/files/*` | Shared file explorer |
| TM CRUD/search/entries | `/api/ldm/tm/*` | Shared translation memory |
| TM index build | `/api/ldm/tm/indexes/build` | Reads entries from DB → local FAISS |
| Pretranslate | `/api/ldm/pretranslate` | DB read + write |
| QA checks | `/api/ldm/qa/*` | Operates on DB rows |
| Search (FTS) | `/api/ldm/search` | DB full-text search |
| Auth/users | `/api/v2/auth/*` | Security |
| Sessions/presence | `/api/v2/sessions/*` | Who's editing what |
| WebSocket | `/ws/socket.io` | Real-time sync |
| Logs/telemetry/stats | `/api/v2/logs/*`, `/api/v2/stats/*` | Monitoring |
| AI suggestions | `/api/ldm/ai/*` | API key security |

## Factory Pattern (How It Works)

```python
# server/repositories/factory.py — 3-mode auto-detection
def get_row_repository(request, db, user):
    if _is_offline_mode(request):       # OFFLINE_MODE_ token
        return SQLiteRowRepo(OFFLINE)   # offline_* tables
    elif _is_server_local():            # ACTIVE_DATABASE_TYPE == "sqlite"
        return SQLiteRowRepo(SERVER)    # ldm_* tables (SQLite)
    else:
        return PostgreSQLRowRepo(db)    # ldm_* tables (PostgreSQL)
```

Route code is identical regardless of mode. Only the injected repository changes.

## Graceful Degradation

| Missing | Still Works | Disabled |
|---------|-------------|----------|
| No Perforce | Language data, TM, all DB | GameData, Codex, MegaIndex, Audio |
| No Model2Vec | TM hash search, GameData | TM semantic search |
| No PostgreSQL | All local + SQLite fallback | Multi-user sync |
| No network | All local features | Remote sync, AI, telemetry |

---

*Last updated: 2026-04-03 — Phase 111 architecture documentation*
