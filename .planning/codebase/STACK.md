# Technology Stack

**Analysis Date:** 2026-03-14

## Languages

**Primary:**
- **Python** 3.8+ - Backend server, data processing, ML/NLP tools
- **JavaScript/TypeScript** - Frontend apps (Svelte 5), Electron desktop app, CLI tools
- **HTML/CSS** - Landing page, UI templates
- **SQL** - PostgreSQL and SQLite schemas

**Secondary:**
- **PowerShell** - Windows installer and build scripts
- **Bash** - Linux/WSL automation and server control scripts

## Runtime

**Environment:**
- **Node.js** - Frontend build and Electron main process
- **Python 3.8+** - Backend server and tools execution
- **Electron 39.0.0** - Desktop application runtime (LocaNext.exe)

**Package Manager:**
- **npm** - Node.js package management (frontend)
- **pip** - Python package management (backend)
- Lockfiles: `package-lock.json` (npm), `requirements.txt` (pip pinned versions)

## Frameworks

**Frontend:**
- **Svelte 5** - UI framework with runes (`$state`, `$derived`, `$effect`)
- **SvelteKit 2.0.0** - Meta-framework with static adapter
- **Vite 7.0.0** / **Vite 6.4.1** - Build tool and dev server
- **Carbon Components Svelte 0.95.0** - IBM's design system components
- **Carbon Icons Svelte 13.0.0** - Icon library

**Desktop:**
- **Electron 39.0.0** - Cross-platform desktop app runtime
- **Electron-builder 26.0.0** - Build/package for Windows/macOS/Linux
- **Electron-updater 6.6.2** - Auto-update mechanism

**Backend:**
- **FastAPI 0.115.0** - Async REST API framework
- **Uvicorn 0.30.6** - ASGI server with WebSocket support
- **SQLAlchemy 2.0.32** - ORM for database abstraction
- **Alembic 1.13.2** - Database schema migrations

**WebSocket/Real-time:**
- **Socket.IO** (python-socketio 5.14.0+) - Server-side real-time communication
- **socket.io-client 4.6.0** - Client-side WebSocket connection

**Testing:**
- **Playwright 1.57.0** - Headless browser testing (E2E)
- **pytest 8.3.2** - Python testing framework
- **pytest-asyncio 0.24.0** - Async test support
- **pytest-cov 5.0.0** - Coverage reporting
- **pytest-xdist 3.5.0** - Parallel test execution

**Build/Dev:**
- **electron-builder** - Windows NSIS installer, macOS DMG, Linux AppImage
- **concurrently 9.0.0** - Run multiple processes during dev
- **cross-env 10.0.0** - Cross-platform environment variables
- **wait-on 9.0.0** - Wait for server startup before launching Electron

## Key Dependencies

**Critical Backend:**
- **sentence-transformers 2.7.0** - Text embedding generation (semantic search)
- **transformers 4.46.0+** - NLP models and tokenizers
- **torch 2.3.1** - Deep learning framework (CPU-only, GPU optional)
- **faiss-cpu 1.8.0** - Vector similarity search and indexing
- **model2vec 0.3.0+** - Fast multilingual embeddings (79x faster than KR-SBERT)
- **lxml 4.9.0+** - XML parsing for QA/data tools

**Data Processing:**
- **pandas 2.2.2** - Data manipulation and analysis
- **numpy 1.26.4** - Numerical computing
- **openpyxl 3.1.5** - Read Excel files
- **xlrd 2.0.1** - Read XLS files
- **xlsxwriter 3.2.0** - Write Excel files (PyInstaller-friendly)

**HTTP/Networking:**
- **requests 2.32.4+** - HTTP client library
- **httpx 0.27.0** - Async HTTP client

**Authentication & Security:**
- **python-jose[cryptography] 3.4.0+** - JWT token generation/verification
- **PyJWT 2.9.0** - JWT library
- **passlib[bcrypt] 1.7.4** - Password hashing framework
- **bcrypt 4.2.0** - Bcrypt algorithm (BCRYPT_ROUNDS=12)
- **python-dotenv 1.0.1** - Environment variable loading

**Data Validation:**
- **pydantic 2.9.0** - Data validation and settings management
- **pydantic-settings 2.5.2** - Environment-based configuration
- **email-validator 2.2.0** - Email validation

**Logging:**
- **loguru 0.7.2** - Structured logging (replaces print statements)

**Configuration:**
- **pyyaml 6.0.2** - YAML parsing
- **toml 0.10.2** - TOML parsing

**Background Tasks:**
- **celery** - Distributed task queue (optional, Redis-based)

**System/Utilities:**
- **psutil 6.0.0** - System and process utilities
- **python-multipart 0.0.18+** - Multipart form handling (CVE fix)
- **aiosqlite 0.20.0** - Async SQLite support
- **asyncpg 0.29.0+** - Async PostgreSQL driver

**Build & Distribution:**
- **pyinstaller 6.10.0** - Create standalone Python executables
- **setuptools 78.1.1+** - Package building (CVE fix)
- **wheel 0.44.0** - Wheel package format

**Code Quality (Dev only):**
- **black 24.8.0** - Code formatter
- **flake8 7.1.1** - Linter
- **mypy 1.11.2** - Static type checker
- **isort 5.13.2** - Import statement sorter

**Visualization (Admin Dashboard):**
- **plotly 5.24.0** - Interactive charts
- **matplotlib 3.9.2** - 2D plotting
- **seaborn 0.13.2** - Statistical visualization

## Configuration

**Environment:**
- Loaded from `.env` file at project root (gitignored)
- Environment variables override `.env` values
- User config stored in `server-config.json` (platform-specific paths):
  - Windows: `%APPDATA%\LocaNext\server-config.json`
  - Linux/macOS: `~/.config/locanext/server-config.json`

**Critical Configurations:**
- `SECRET_KEY` - JWT signing (required for production)
- `API_KEY` - Client-server communication (required for production)
- `POSTGRES_*` - Database credentials and host
- `DATABASE_MODE` - "auto" (PostgreSQL with SQLite fallback), "postgresql", or "sqlite"
- `CORS_ORIGINS` - Comma-separated allowed origins
- `LOG_LEVEL` - Logging verbosity (INFO, DEBUG, WARNING)

**Build Configurations:**
- `vite.config.js` (LocaNext) - Vite build config with SvelteKit plugin, base set to `./` for Electron
- `svelte.config.js` (LocaNext & adminDashboard) - SvelteKit adapter (static), relative paths
- `tsconfig.json` - TypeScript configuration (if present)

## Database Configuration

**PostgreSQL (Online Mode):**
- Host: Configurable via `POSTGRES_HOST` (default: localhost)
- Port: Configurable via `POSTGRES_PORT` (default: 5432)
- Database: `localizationtools` (configurable)
- Driver: `psycopg2-binary` (sync) + `asyncpg` (async)
- Connection pooling: SQLAlchemy pool (size=5, max_overflow=10)
- Reconnect timeout: 3 seconds (for fallback detection)

**SQLite (Offline Mode):**
- Location: `server/data/offline.db` (configurable)
- Driver: `aiosqlite` for async access
- No connection pooling (SQLite limitation)
- Auto-fallback when PostgreSQL unavailable

**Schema Management:**
- Alembic migrations in `server/database/migrations/`
- SQLAlchemy ORM models in `server/database/models.py`
- Dialect-agnostic JSON types (JSONB on PostgreSQL, JSON on SQLite)

## External Services Integration

**LanguageTool (Grammar Checking):**
- Service: Grammar/spelling check server
- Configuration: `LANGUAGETOOL_URL` (default: `http://localhost:8081/v2/check`)
- Implementation: Lazy-load, starts on-demand, auto-stops after 5min idle
- Client: `server/utils/languagetool.py` using httpx

**Redis (Optional Caching):**
- Broker: For Celery background tasks (optional)
- Configuration: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Fallback: Graceful degradation if Redis unavailable
- Usage: Cache (TTL=300s), Stats cache (TTL=60s)

**Central Server Telemetry:**
- Endpoint: Configurable via `CENTRAL_SERVER_URL`
- Heartbeat: Every 300s (configurable)
- Offline queue: Max 1000 logs when unavailable
- Retry interval: 60s

## Platform Requirements

**Development:**
- **OS:** Windows (WSL2 preferred) / Linux / macOS
- **Node.js:** 18.0.0+
- **Python:** 3.8 - 3.12
- **RAM:** 8GB minimum (ML models consume 2-4GB)
- **Storage:** 10GB (ML models, node_modules, venv)

**Desktop Application (Windows):**
- **OS:** Windows 7 SP1+
- **Architecture:** x64 (Electron 39)
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 2GB installation
- **GPU:** Optional (ML inference faster with CUDA-capable GPU)
- **Build tool:** electron-builder creates NSIS installer
- **Distribution:** Gitea releases + auto-updater

**Server Deployment:**
- **OS:** Linux (Ubuntu 20.04+ or CentOS 8+)
- **Python:** 3.8 - 3.12
- **Database:** PostgreSQL 12+ (production) or SQLite (fallback)
- **Optional:** Redis 6+ (for caching/Celery)
- **Port requirements:** 8888 (backend), 5173 (frontend dev), 5174 (admin dashboard)

## Build & Release Pipeline

**GitHub Actions (Frontend/NewScripts):**
- Workflows in `.github/workflows/`
- Builds: Electron, QuickTranslate, QACompiler, LanguageDataExporter, etc.
- Output: Releases, built artifacts

**Gitea CI/CD (LocaNext):**
- Workflow: `.gitea/workflows/build.yml`
- Windows runner: PyInstaller + Electron-builder
- Output: LocaNext.exe in Gitea releases

**Desktop Build Process:**
- npm run build (Vite) → SvelteKit generates static files
- electron-builder packages files
- NSIS installer created for Windows
- Auto-updater configured for releases

---

*Stack analysis: 2026-03-14*
