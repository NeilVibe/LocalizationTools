# LocalizationTools - Project Overview

## 🗺️ For Future Claude Assistants - Read This First!

**This section helps you navigate and continue development on this project.**

### Quick Start Checklist
1. ✅ Read this entire Claude.md file first (15 min)
2. ✅ Review Roadmap.md for current progress
3. ✅ Check TESTING.md for test documentation
4. ✅ Review project structure below
5. ✅ Run tests to verify everything works: `pytest`

### Key Documentation Files
- **Claude.md** (this file) - Project overview, architecture, standards
- **Roadmap.md** - Development roadmap, progress tracking
- **README.md** - User-facing documentation
- **TESTING.md** - Complete testing guide
- **ADMIN_SETUP.md** - Admin user setup guide
- **STATS_DASHBOARD_SPEC.md** - Dashboard specifications

### Critical Rules (READ BEFORE CODING!)
1. **CLEAN CODE ONLY** - No temp files, no bloat, archive unused code
2. **TEST EVERYTHING** - Add tests for every new feature
3. **UPDATE ROADMAP** - After completing tasks, update Roadmap.md
4. **COMMIT OFTEN** - Clean, descriptive commit messages
5. **NO GLOBALS** - Use dependency injection, modular code

---

## Project Purpose

LocalizationTools is a desktop application suite that consolidates multiple Python-based localization/translation tools into a single, user-friendly interface. The primary goals are:

1. **Usage Analytics**: Track which tools and functions are being used, by whom, and how often
2. **Centralized Access**: Provide easy access to all localization tools in one place
3. **Performance Metrics**: Collect detailed statistics on processing times and usage patterns
4. **User Adoption Tracking**: Demonstrate tool adoption and usage frequency to management

## The Problem We're Solving

Currently, the tools exist as individual Python scripts compiled into executables. This creates several challenges:

- **Difficult to track usage**: No centralized logging of who uses what and when
- **Hard to measure impact**: Cannot demonstrate tool adoption rates or frequency
- **Maintenance overhead**: Many separate executables to update and distribute
- **Poor visibility**: Management cannot see the value and usage statistics
- **User friction**: Users must manage multiple separate programs

## Solution Architecture

**IMPORTANT: Multi-Tool Suite Architecture**

This is a **comprehensive, scalable multi-tool platform**, not just a single-tool application. The architecture is designed from the ground up to support 10+ localization tools in a unified, centralized system.

### Application Entry Points

**PRODUCTION APPLICATION (Main):**
- `client/main.py` - **THE CORE APPLICATION**
- Unified Gradio interface with tabbed layout
- Each tool gets its own tab
- Centralized logging, analytics, and user management
- Scalable architecture for adding new tools
- **This is what users will run in production**

**Development Tools (Optional - Intentionally Kept):**
- `run_xlstransfer.py` - Standalone launcher for XLSTransfer ONLY
  - **Purpose**: Quick testing/debugging of single tool without launching full app
  - **When to use**: Development, debugging, isolated testing
  - **When NOT to use**: Production (use client/main.py instead)
  - **Keep or archive?**: KEEP - legitimate dev tool, common pattern
  - Similar to running `pytest tests/unit/specific_test.py` vs entire test suite

### Client-Side Application (User's Computer)

**Technology**: Gradio Desktop App
**Size**: ~500MB-1GB (one-time download)

**Contains**:
- Gradio web interface (runs locally, opens in desktop window)
- Python runtime and all dependencies
- **All localization tools (10+ tools)** - scalable architecture
- ML models (Korean BERT, FAISS indices)
- Local processing engine
- Centralized logging and analytics client

**Key Features**:
- **Tabbed interface** - one tab per tool, infinitely expandable
- File upload/download for all tools
- Real-time progress tracking
- Beautiful, modern UI
- All processing uses USER's CPU (not server)
- Works offline once downloaded
- **Centralized logging** - all tool usage tracked automatically

### Server-Side (Central Logging Server)

**Technology**: FastAPI + PostgreSQL/SQLite
**Size**: Lightweight (handles logs only)

**Responsibilities**:
- Receive usage logs from all clients
- Store analytics data
- Serve admin dashboard
- Push update notifications
- User authentication (optional)

**Does NOT Handle**:
- File processing
- ML model inference
- User files or data
- Heavy computation

### Admin Dashboard

**Technology**: Gradio or React
**Access**: Web-based (your.company.com:8885)

**Features**:
- Real-time usage statistics
- User activity tracking
- Function usage heatmaps
- Performance metrics (processing times)
- Tool popularity rankings
- Export reports for management

## Data Flow

```
USER MACHINE                           CENTRAL SERVER
┌─────────────────┐                   ┌──────────────────┐
│  Gradio App     │                   │  FastAPI Server  │
│  (Desktop)      │                   │  (port 8888)     │
│                 │                   │                  │
│  User uploads   │                   │                  │
│  Excel file     │                   │                  │
│       ↓         │                   │                  │
│  Processing     │    Usage Log      │  Store in DB     │
│  (User's CPU)   │─────────────────→ │                  │
│       ↓         │    {user_id,      │       ↓          │
│  Download       │     tool,         │  Admin Dashboard │
│  result         │     function,     │  (port 8885)     │
│                 │     duration,     │                  │
│                 │     timestamp}    │  Shows stats     │
└─────────────────┘                   └──────────────────┘
```

## Key Technologies

### Client Application
- **Gradio**: Web UI framework (Python-based)
- **PyInstaller**: Package Python app as standalone executable
- **sentence-transformers**: Korean BERT model for semantic matching
- **FAISS**: Vector similarity search
- **pandas/openpyxl**: Excel processing
- **requests**: Send logs to server

### Server
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Primary database (production) - robust, scalable, supports concurrent connections
- **SQLite**: Development/testing database
- **uvicorn**: ASGI server
- **SQLAlchemy**: ORM for database
- **bcrypt**: Password hashing for security
- **psycopg2**: PostgreSQL adapter

### Admin Dashboard
- **Gradio**: Quick dashboard UI
- **Plotly/matplotlib**: Charts and graphs
- **pandas**: Data analysis

## Initial Tools to Implement

Starting with the most impactful tools:

1. **XLSTransfer** (Primary focus)
   - AI-powered translation transfer between Excel files
   - Creates translation dictionaries using embeddings
   - Multiple transfer modes (whole/split)
   - Newline checking and adaptation

2. **Additional Tools** (To be selected from existing scripts)
   - TFM tools (TFMFULL, TFMLITE)
   - Quick Search tools
   - Korean similarity checker
   - Stack/remove duplicate tools
   - Others based on usage priority

## Database Architecture

### PostgreSQL Schema

The application uses a comprehensive PostgreSQL database with the following tables:

**Core Tables**:
- **users**: User authentication (username/password), profiles, roles, department info
- **sessions**: Active user sessions tracking (session_id, IP, machine_id, app_version)
- **log_entries**: Main usage logs (every tool execution recorded with full details)

**Analytics Tables**:
- **tool_usage_stats**: Daily aggregated statistics per tool
- **function_usage_stats**: Function-level usage statistics
- **performance_metrics**: Detailed performance data (CPU, memory, processing times)
- **user_activity_summary**: Daily active user tracking

**Management Tables**:
- **app_versions**: Version management and update tracking
- **update_history**: Track when users update their app
- **error_logs**: Detailed error tracking with stack traces
- **announcements**: Push notifications to users
- **user_feedback**: Collect feedback and feature requests

**Key Features**:
- UUID-based session tracking
- JSONB fields for flexible metadata
- Pre-computed views for dashboard performance
- Automated daily statistics aggregation
- Indexes optimized for common queries

See `database_schema.sql` for complete schema definition.

### Development vs Production

**Local Testing** (SQLite):
- Both client and server run on localhost
- No port forwarding needed
- SQLite database for simplicity
- Client: `localhost:7860`
- Server: `localhost:8888`
- Admin: `localhost:8885`

**Production** (PostgreSQL):
- PostgreSQL on dedicated server
- Handles concurrent user connections
- Automated backups
- SSL encrypted connections
- Access via company domain

## User Experience Flow

1. **First Time**:
   - User downloads LocalizationTools.exe (~500MB)
   - Runs executable (no installation required)
   - App opens in desktop window
   - User logs in with company credentials (username/password)
   - Sees tabbed interface with all available tools

2. **Daily Use**:
   - Open LocalizationTools app
   - Select tool from tabs
   - Upload files
   - Configure settings
   - Click "Process"
   - See live progress
   - Download results
   - (App automatically logs usage to server)

3. **Updates**:
   - App checks for updates on launch
   - Notifies user if new version available
   - One-click update (downloads only changes)

## Privacy & Security

### Data That Stays Local (Never Sent to Server)
- User's files
- Processing results
- Translation data
- Any sensitive content
- ML models and embeddings

### Data Sent to Server (Analytics Only)
- User ID (anonymous or authenticated)
- Tool name used
- Function executed
- Timestamp
- Duration (seconds)
- File size (MB) - metadata only
- Rows processed (count only)
- Success/error status

## Benefits

### For Users
- Single app for all localization tools
- Modern, intuitive interface
- Fast processing (uses their CPU)
- Works offline
- Regular updates
- Progress tracking

### For You (Developer)
- Detailed usage analytics
- Easy to demonstrate tool adoption
- Centralized updates
- Single codebase to maintain
- Clear metrics for management

### For Management
- Quantifiable usage data
- ROI demonstration
- User adoption metrics
- Tool effectiveness measurements
- Data-driven decisions

## XLSTransfer Module Architecture

**Status**: Refactoring COMPLETE ✓ (49 functions across 4 modules)

The XLSTransfer tool has been refactored from a 1435-line monolithic script into a clean, modular architecture:

### Module Structure

**client/tools/xls_transfer/**
- `config.py` - Tool-specific configuration (thresholds, paths, settings)
- `core.py` - **15 functions**: Text processing, column conversion, code pattern handling
- `embeddings.py` - **13 functions**: Model loading, embedding generation, FAISS operations
- `translation.py` - **10 functions + TranslationProgress class**: Matching logic, statistics
- `excel_utils.py` - **11 functions**: Excel file reading/writing, newline checking, combining
- `__init__.py` - Clean exports of all 49 functions

### Key Features
- **Type hints** throughout all functions
- **Comprehensive docstrings** with examples
- **No global variables** - everything modular
- **Logging integration** with loguru
- **Progress tracking** integration
- **Reusable and testable** - ready for unit tests

### Functions Available
- Text cleaning and code preservation
- Korean BERT model loading and caching
- Embedding generation and FAISS indexing
- Similarity-based translation matching
- Multi-mode matching (whole text + split fallback)
- Excel operations (read, write, combine, adapt)
- Newline mismatch detection and auto-fixing
- Translation statistics and analysis

## Deployment Strategy

### Phase 1: MVP (Minimum Viable Product)
- Single tool (XLSTransfer) in Gradio interface ← **Modules ready!**
- Basic logging to central server
- Simple admin dashboard

### Phase 2: Multi-Tool Integration
- Add 3-5 most-used tools
- Enhanced UI with tabs
- Improved analytics

### Phase 3: Advanced Features
- User authentication
- Advanced analytics dashboard
- Auto-updates
- Notification system

### Phase 4: Production
- Full tool suite (10+ tools)
- Comprehensive dashboard
- Export reports
- Performance optimizations

## Success Metrics

We will track:
- Daily Active Users (DAU)
- Monthly Active Users (MAU)
- Tool usage frequency
- Most popular functions
- Average processing times
- User retention
- Feature adoption rates

This data will demonstrate the value and impact of your localization tools to management.

---

## Development Standards & Project Organization

### Clean Code Policy

This project follows **STRICT clean code standards**:

**Core Principles**:
1. **No clutter in main directories** - Keep working directories clean
2. **Archive everything unused** - Old code, test scripts, experiments go to ARCHIVE
3. **Clear structure** - Every file has a purpose and place
4. **No orphaned files** - If you create it, you organize it OR archive it
5. **Document everything** - Code comments, README files, clear naming
6. **Challenge everything** - If a file exists, it must have a DOCUMENTED purpose
7. **If not using it, archive it** - No "maybe we'll need this later" files sitting around

### ARCHIVE Folder Structure

All temporary, experimental, and deprecated code goes into the ARCHIVE folder:

```
ARCHIVE/
├── old_code/               # Deprecated code versions
│   ├── v0.1_initial/
│   └── refactored_2025-01/
├── test_scripts/           # One-off test scripts
│   ├── test_embedding_speed.py
│   └── test_db_connection.py
├── experiments/            # Experimental features
│   └── alternate_ui_approach/
├── deprecated_tools/       # Removed tools
└── notes/                  # Development notes, ideas
    └── meeting_notes_2025-01.md
```

**When to Archive**:
- ✅ After solving a problem with temporary test script
- ✅ When refactoring code (keep old version in archive)
- ✅ Experimental features that didn't make it
- ✅ Old versions of files after major updates
- ✅ Debug scripts once issue is resolved

**Never Archive**:
- ❌ Active development code
- ❌ Required dependencies
- ❌ Documentation (unless outdated)
- ❌ Test files that are part of test suite

### Project Resources

**RessourcesForCodingTheProject/**:
- Contains all original scripts and test data
- Reference material for development
- Test Excel/text files for validation
- Original monolith scripts before refactoring

**Structure**:
```
RessourcesForCodingTheProject/
├── MAIN PYTHON SCRIPTS/        # Primary tools (XLSTransfer, etc.)
├── SECONDARY PYTHON SCRIPTS/   # Additional utilities
└── datausedfortesting/         # Test files for validation
```

### Code Quality Standards

**Python Code**:
- Follow PEP 8 style guide
- Type hints where appropriate
- Docstrings for all functions/classes
- Maximum 100 characters per line
- No unused imports

**File Naming**:
- `snake_case` for Python files
- Clear, descriptive names
- No abbreviations unless obvious
- Version in filename only if archived

**Git Commits**:
- Clear commit messages
- One logical change per commit
- Reference issue/task if applicable

**Testing**:
- **Comprehensive testing framework with pytest**
- **86 unit tests (100% passing)** covering all utility modules
- Test structure: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Coverage requirement: 80% minimum (enforced by pytest.ini)
- Test files mirror source structure
- All critical functions have tests
- Shared fixtures in `tests/conftest.py`
- Detailed testing guide in `tests/README.md`
- Test markers for organization (unit, integration, e2e, client, server, etc.)
- Integration tests for API endpoints (to be added)
- See `tests/README.md` for comprehensive testing documentation

This clean code approach ensures:
- Easy onboarding for new developers
- Quick debugging and maintenance
- Professional codebase presentation
- Scalable project structure

---

## 📂 Complete Project Structure Guide

**For Future Claude Assistants: This is your map!**

```
LocalizationTools/
│
├── 📄 Documentation (READ THESE FIRST!)
│   ├── Claude.md                    # ← YOU ARE HERE - Project overview
│   ├── Roadmap.md                   # Development roadmap (45% complete)
│   ├── README.md                    # User documentation
│   ├── TESTING.md                   # Complete testing guide
│   ├── ADMIN_SETUP.md               # Admin setup instructions
│   └── STATS_DASHBOARD_SPEC.md      # Dashboard specifications
│
├── 🖥️ Client Application
│   ├── client/
│   │   ├── main.py                  # ← PRODUCTION APP (multi-tool suite)
│   │   ├── config.py                # Client configuration
│   │   ├── utils/                   # Client utilities (TESTED ✅)
│   │   │   ├── logger.py            # Usage logging (18 tests)
│   │   │   ├── progress.py          # Progress tracking (27 tests)
│   │   │   └── file_handler.py      # File operations (41 tests)
│   │   └── tools/                   # Tool implementations
│   │       └── xls_transfer/        # XLSTransfer tool (49 functions)
│   │           ├── core.py          # Text processing (15 functions)
│   │           ├── embeddings.py    # ML embeddings (13 functions)
│   │           ├── translation.py   # Translation logic (10 functions)
│   │           ├── excel_utils.py   # Excel operations (11 functions)
│   │           ├── ui.py            # Gradio UI (7 tabs, 730 lines)
│   │           └── config.py        # Tool configuration
│   │
├── ⚙️ Server (FastAPI)
│   ├── server/
│   │   ├── main.py                  # FastAPI app (27 routes)
│   │   ├── config.py                # Server configuration
│   │   ├── api/                     # API endpoints
│   │   │   ├── auth.py              # Authentication (JWT, bcrypt)
│   │   │   ├── logs.py              # Log submission & stats
│   │   │   ├── sessions.py          # Session management
│   │   │   └── schemas.py           # Pydantic models
│   │   ├── database/                # Database layer
│   │   │   ├── models.py            # SQLAlchemy models (12 tables)
│   │   │   ├── db_setup.py          # DB initialization
│   │   │   └── __init__.py          # Clean exports
│   │   ├── utils/                   # Server utilities
│   │   │   ├── auth.py              # Password hashing, JWT
│   │   │   └── dependencies.py      # FastAPI dependencies
│   │   └── admin/                   # Admin dashboard
│   │       └── dashboard.py         # Gradio admin UI (5 tabs)
│   │
├── 🧪 Testing (94 tests - ALL PASSING ✅)
│   ├── tests/
│   │   ├── conftest.py              # Shared fixtures
│   │   ├── unit/                    # Unit tests (86 tests)
│   │   │   └── client/
│   │   │       ├── test_utils_logger.py       # 18 tests
│   │   │       ├── test_utils_progress.py     # 27 tests
│   │   │       └── test_utils_file_handler.py # 41 tests
│   │   ├── integration/             # Integration tests (8 tests)
│   │   │   ├── test_server_startup.py
│   │   │   └── test_api_endpoints.py
│   │   ├── e2e/                     # End-to-end (future)
│   │   ├── fixtures/                # Test data
│   │   └── helpers/                 # Test utilities
│   │
├── 🛠️ Scripts & Utilities
│   ├── scripts/
│   │   ├── create_admin.py          # Initialize admin user
│   │   └── test_admin_login.py      # Test authentication
│   ├── run_xlstransfer.py           # XLSTransfer standalone (dev tool)
│   └── run_admin_dashboard.py       # Admin dashboard launcher
│
├── 📦 Resources & Archive
│   ├── RessourcesForCodingTheProject/  # Original scripts, test data
│   │   ├── MAIN PYTHON SCRIPTS/        # Source material
│   │   ├── SECONDARY PYTHON SCRIPTS/   # Additional tools
│   │   └── datausedfortesting/         # Test files
│   └── ARCHIVE/                        # Deprecated code ONLY
│       ├── old_code/                   # Previous versions
│       ├── test_scripts/               # One-off tests
│       └── experiments/                # Failed experiments
│
└── ⚙️ Configuration Files
    ├── pytest.ini                   # Test configuration (80% coverage)
    ├── requirements.txt             # Python dependencies
    ├── database_schema.sql          # Database schema reference
    └── .gitignore                   # Git ignore rules
```

### Where to Find Things

**Adding a new tool?**
- Create module in `client/tools/your_tool/`
- Add UI in `client/tools/your_tool/ui.py`
- Integrate in `client/main.py`
- Add tests in `tests/unit/client/`

**Modifying the server?**
- API endpoints: `server/api/`
- Database models: `server/database/models.py`
- Configuration: `server/config.py`
- Add integration tests in `tests/integration/`

**Need test data?**
- Check `RessourcesForCodingTheProject/datausedfortesting/`
- Create fixtures in `tests/conftest.py`
- Add test helpers in `tests/helpers/`

**Something not working?**
- Check `Roadmap.md` for current status
- Review `TESTING.md` for test guide
- Run `pytest -v` to verify tests
- Check logs in `server/data/logs/` or `client/data/logs/`

### File Naming Conventions

**Python modules:** `snake_case.py`
**Test files:** `test_module_name.py`
**Config files:** `config.py`, `settings.py`
**Documentation:** `UPPERCASE.md`
**Scripts:** Descriptive names (`create_admin.py`, `run_xlstransfer.py`)

### When to Archive

Move to `ARCHIVE/` when:
- ✅ Code is superseded by refactored version
- ✅ Feature is deprecated
- ✅ Test script is no longer needed
- ✅ Experiment failed or completed

**NEVER archive:**
- ❌ Active code
- ❌ Current tests
- ❌ Dependencies
- ❌ Documentation (unless outdated)
