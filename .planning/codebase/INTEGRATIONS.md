# External Integrations

**Analysis Date:** 2026-03-14

## APIs & External Services

**Grammar/Spelling Checking:**
- **LanguageTool** - Grammar and spelling correction
  - SDK/Client: `server/utils/languagetool.py` (custom httpx-based client)
  - Connection: `LANGUAGETOOL_URL` env var (default: `http://localhost:8081/v2/check`)
  - Architecture: Lazy-load service (starts on-demand, stops after 5min idle)
  - API Endpoint: HTTP POST to `/v2/check` with text payload
  - Used by: QA tools, grammar checking features

**Central Telemetry Server:**
- **Remote Logging Hub** - Aggregates logs from desktop apps
  - Connection: `CENTRAL_SERVER_URL` env var (optional)
  - Protocol: HTTP, custom payload (logs array)
  - Heartbeat: `TELEMETRY_HEARTBEAT_INTERVAL` (default: 300s)
  - Offline buffering: Queue up to `TELEMETRY_MAX_QUEUE_SIZE` (1000 logs)
  - Implementation: `locaNext/electron/telemetry.js` (Electron side)
  - Retry behavior: `TELEMETRY_RETRY_INTERVAL` (default: 60s) when unavailable

## Data Storage

**Databases:**

**PostgreSQL (Production/Online):**
- Type: Relational (OLTP)
- Client: SQLAlchemy ORM + psycopg2 (sync) + asyncpg (async)
- Connection: `postgresql://user:pass@host:5432/localizationtools`
- Pool settings: size=5, max_overflow=10, recycle=3600s
- Timeout: 3s connection check (for auto-fallback to SQLite)
- Schema: 50+ tables for users, projects, files, rows, TM, QA, logs, sessions
- Features: JSONB columns for flexible data, indexes on search paths
- Config location: `server/config.py` (lines 180-222)

**SQLite (Offline Mode/Fallback):**
- Type: Embedded relational
- Client: aiosqlite (async), sqlite3 (Python stdlib)
- Location: `server/data/offline.db`
- Schema: Identical to PostgreSQL schema (dialect-agnostic)
- Use case: Fallback when PostgreSQL unavailable (P33 - Offline Mode)
- Features: JSON type for compatibility, indexes preserved
- Config location: `server/config.py` (lines 202-204)

**File Storage:**
- Type: Local filesystem
- Locations:
  - Data: `server/data/` directory
  - Logs: `server/data/logs/`
  - Updates: `server/data/updates/`
  - SQLite DB: `server/data/offline.db`
- No S3 or cloud storage integration

**Caching:**
- **Redis (Optional):**
  - Type: In-memory key-value store
  - Configuration: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
  - Purpose: Distributed caching (TTL=300s default), Celery broker
  - Status: Graceful fallback if unavailable (operations continue without cache)
  - Client: redis-asyncio
  - Config location: `server/utils/cache.py` (lines 24-28)

## Authentication & Identity

**Auth Provider:**
- Type: Custom JWT-based authentication
- Implementation: `server/utils/auth.py` + `server/api/auth.py`
- Tokens:
  - **Access Token:** 30 minutes (configurable `ACCESS_TOKEN_EXPIRE_MINUTES`)
  - **Refresh Token:** 7 days (configurable `REFRESH_TOKEN_EXPIRE_DAYS`)
- Algorithm: HS256 (HMAC-SHA256)
- Signing Key: `SECRET_KEY` env var (256-bit recommended)
- Storage: JWT in Authorization header (`Bearer <token>`)

**Password Hashing:**
- Algorithm: bcrypt
- Rounds: 12 (BCRYPT_ROUNDS in config)
- Library: passlib with bcrypt backend

**WebSocket Authentication:**
- Socket.IO connection with optional `auth` token
- User rooms: Auto-join `user_{user_id}` room on successful auth
- Token verification: `server/utils/websocket.py` (lines 70-80)

**DEV Mode (Localhost-only):**
- Auto-authentication for localhost requests (127.0.0.1)
- Enabled: `DEV_MODE=true` env var
- Disabled if `PRODUCTION=true` is set
- Use case: Autonomous testing without manual login

**Multi-User Support:**
- User table: `users` with username, email, password_hash, role
- Roles: user, admin, superadmin
- Team/Department: Optional team assignment per user
- Sessions: Per-user sessions table for login tracking

## Monitoring & Observability

**Error Tracking:**
- Sentry: Commented out in requirements (optional)
  - Activation: Uncomment `sentry-sdk==2.14.0` and set `SENTRY_DSN`
  - Not currently integrated

**Logging:**
- Framework: loguru (structured logging)
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Output:
  - **Console:** Formatted output to stdout
  - **File:** `server/data/logs/server.log` (rotated at 50MB)
  - **Error File:** `server/data/logs/error.log` (errors only, 6-month retention)
  - **Access Logs:** `server/data/logs/access.log` (HTTP requests)
- Retention: 3 months (server.log), 6 months (error.log)
- Rotation: 50MB per file
- Format: `{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}`
- Logger: Never use `print()`, always use `logger` (CRITICAL per CLAUDE.md)

**Performance Metrics:**
- Collection: Enabled (`COLLECT_PERFORMANCE_METRICS=True`)
- Sample rate: 100% (`PERFORMANCE_METRICS_SAMPLE_RATE=1.0`)
- Metrics: Response times, resource usage via middleware
- Implementation: `server/middleware/PerformanceLoggingMiddleware`

**Health Checks:**
- Endpoint: `GET /health` (REST API)
- WebSocket Status: `GET /health/detailed` (includes WebSocket stats)
- DB Status: Connection check + active connection count
- Checks: Database connectivity, WebSocket readiness, service uptime

## CI/CD & Deployment

**Hosting:**
- **Desktop App (Windows):** NSIS installer (LocaNext.exe)
  - Auto-updater: electron-updater
  - Release URL: `http://<GITEA_HOST>:3000/<GIT_USER>/LocaNext/releases/download/latest` (Gitea)

**CI Pipelines:**
- **GitHub Actions:** Frontend/NewScript tools (`build-electron.yml`, `quicktranslate-build.yml`, etc.)
  - Triggers: Commit to main
  - Output: Release artifacts
  - Config: `.github/workflows/`

- **Gitea CI/CD:** LocaNext main app (`build.yml`)
  - Triggers: Commit to main
  - Runner: Windows (for PyInstaller + Electron-builder)
  - Output: LocaNext.exe release
  - Config: `.gitea/workflows/build.yml`
  - Status tracking: `GitSQLite` (Gitea's SQLite) via SQL queries

## Environment Configuration

**Required Environment Variables:**

**Security (Critical for Production):**
- `SECRET_KEY` - JWT signing key (256-bit, generated with `secrets.token_urlsafe(32)`)
- `API_KEY` - Client-server API authentication (384-bit, generated with `secrets.token_urlsafe(48)`)

**Database:**
- `DATABASE_MODE` - "auto", "postgresql", or "sqlite"
- `POSTGRES_USER` - Default: "localization_admin"
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_HOST` - Default: "localhost"
- `POSTGRES_PORT` - Default: 5432
- `POSTGRES_DB` - Default: "localizationtools"
- `SQLITE_DATABASE_PATH` - SQLite file location (default: `server/data/offline.db`)
- `POSTGRES_CONNECT_TIMEOUT` - Fallback check timeout (default: 3s)

**CORS & Security:**
- `CORS_ORIGINS` - Comma-separated allowed origins (e.g., `http://192.168.11.100:5173,http://192.168.11.100:5175`)
- `ALLOWED_IP_RANGE` - CIDR range to restrict access (e.g., `192.168.11.0/24`)
- `IP_FILTER_ALLOW_LOCALHOST` - Always allow localhost (default: true)
- `IP_FILTER_LOG_BLOCKED` - Log blocked IP attempts (default: true)

**JWT & Tokens:**
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 60
- `REFRESH_TOKEN_EXPIRE_DAYS` - Default: 30

**Rate Limiting:**
- `RATE_LIMIT_ENABLED` - Default: true
- `RATE_LIMIT_PER_MINUTE` - Default: 60
- `RATE_LIMIT_PER_HOUR` - Default: 1000

**Telemetry:**
- `CENTRAL_SERVER_URL` - Central server endpoint (optional)
- `TELEMETRY_ENABLED` - Default: true
- `TELEMETRY_HEARTBEAT_INTERVAL` - Default: 300s
- `TELEMETRY_RETRY_INTERVAL` - Default: 60s
- `TELEMETRY_MAX_QUEUE_SIZE` - Default: 1000

**Logging:**
- `LOG_LEVEL` - Default: INFO
- `LOG_RETENTION_DAYS` - Default: 90
- `SESSION_RETENTION_DAYS` - Default: 30
- `ERROR_LOG_RETENTION_DAYS` - Default: 180

**Optional Services:**
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` - For Redis caching
- `REDIS_ENABLED` - Default: false
- `CELERY_BROKER_URL` - Celery broker (Redis)
- `CELERY_ENABLED` - Default: false
- `LANGUAGETOOL_HOST`, `LANGUAGETOOL_PORT` - Grammar check server

**Advanced:**
- `DEV_MODE` - Localhost auto-auth (never production)
- `PRODUCTION` - Production flag (disables DEV_MODE)
- `SECURITY_MODE` - "strict" or "warn" for insecure defaults
- `DEBUG` - Debug logging (default: false)
- `ENABLE_DOCS` - Swagger/ReDoc API docs (disable in production)

**Secrets Location:**
- Source: `.env` file (gitignored, never committed)
- Platform-specific user config: Windows `%APPDATA%\LocaNext\server-config.json`, Linux `~/.config/locanext/server-config.json`
- Environment: System environment variables (highest priority)
- CI/CD: GitHub Secrets / Gitea CI secrets

## Webhooks & Callbacks

**Incoming:**
- **Health Check:** `GET /health` - Public endpoint, no auth
- **Detailed Health:** `GET /health/detailed` - Database/WebSocket status
- **No incoming webhooks** from external services

**Outgoing:**
- **Auto-Update:** Electron-updater checks `UPDATE_DOWNLOAD_URL_BASE` (configurable)
- **Telemetry:** Desktop app sends logs to `CENTRAL_SERVER_URL` (if configured)
- **LanguageTool:** HTTP POST to external grammar check service (if running)

**Real-time Bidirectional:**
- **WebSocket (Socket.IO):**
  - Path: `/socket.io`
  - CORS: Same as REST API (`config.CORS_ORIGINS`)
  - Events:
    - `connect` - Client connects with optional auth token
    - `disconnect` - Client disconnects
    - `emit_log_entry` - Server broadcasts log to clients
    - `emit_error_report` - Server broadcasts error alerts
    - `emit_session_update` - Server broadcasts session changes
    - `broadcast_cell_update` - Real-time cell updates in LDM tool
  - Rooms:
    - `user_{user_id}` - Per-user private room
    - Shared project/file rooms for collaborative features
  - Implementation: `server/utils/websocket.py` + `server/tools/ldm/websocket.py`

---

*Integration audit: 2026-03-14*
