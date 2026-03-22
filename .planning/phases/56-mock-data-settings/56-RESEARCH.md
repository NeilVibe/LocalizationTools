# Phase 56: Mock Data + Settings - Research

**Researched:** 2026-03-22
**Domain:** SQLite database setup, project/platform CRUD, Settings UI, language detection
**Confidence:** HIGH

## Summary

Phase 56 is the foundation for v6.0 Showcase Offline Transfer. It requires two independent deliverables: (1) a CLI script that wipes and repopulates the SQLite database with 3 mock projects (project_FRE, project_ENG, project_MULTI), and (2) a Settings page (or modal section) for LOC PATH and EXPORT PATH with validation and persistence.

The existing codebase has a mature repository pattern (3-mode: PostgreSQL, server-SQLite, offline-SQLite), platform/project/folder/file models, and a preferences store backed by localStorage. The mock script will operate directly on the server-local SQLite database (`server/data/offline.db`), creating a platform + 3 projects + folders via the repository layer or direct SQL. The Settings page will need a new dedicated page or section in the existing PreferencesModal, with backend persistence for paths that survive app restarts.

**Primary recommendation:** Build the CLI script as `scripts/setup_mock_data.py` using direct SQLite operations (not the async repository layer) for simplicity and reliability. For Settings, add LOC PATH and EXPORT PATH to the existing preferences store with a new backend endpoint for path validation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOCK-01 | CLI script wipes DB and creates mock platform with project_FRE, project_ENG, project_MULTI | Repository pattern documented, SQLite schema understood, server-local DB path at `server/data/offline.db` |
| MOCK-02 | Mock projects auto-detect language from project name (project_FRE = French, etc.) | QuickTranslate has LANGUAGE_NAMES map and suffix detection in `source_scanner.py`. Language suffix pattern: `_FRE`, `_ENG`, etc. |
| MOCK-03 | project_MULTI contains subfolders with language-suffixed files for multi-language merge testing | Folder model (LDMFolder) supports nesting via parent_id. QuickTranslate expects `corrections_FRE/`, `corrections_ENG/` suffix pattern |
| MOCK-04 | Test languagedata files from test123 directory loadable as mock LOC data | test123 exists at `C:\Users\MYCOM\Desktop\oldoldVold\test123` (confirmed accessible from WSL). Contains `languagedata_fr PC 0904 1847.txt` (1M+ lines) and `.xlsx` variants |
| SET-01 | User can configure LOC PATH in Settings page (persistent, per-project) | No existing LOC PATH setting. Preferences store uses localStorage. Need per-project persistence = backend storage (not just localStorage) |
| SET-02 | User can configure EXPORT PATH in Settings page (persistent, per-project) | Same infrastructure as SET-01 |
| SET-03 | Settings validate paths exist and contain expected files (languagedata_*.xml) | Need backend validation endpoint. Path validation must handle Windows paths from WSL context |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| SQLite + aiosqlite | Database (server-local mode) | Already the offline/fallback DB engine |
| SQLAlchemy | ORM models (LDMPlatform, LDMProject, LDMFolder, LDMFile) | Already in use for all DB operations |
| FastAPI | Backend API | Existing API framework |
| Carbon Components Svelte | UI components | Existing UI library |
| Svelte 5 Runes | Frontend state management | Project standard |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| argparse | CLI script argument parsing | Mock data script `--confirm-wipe` flag |
| pathlib | Path validation and manipulation | Both mock script and settings validation |

### No New Dependencies Needed
This phase uses only existing project dependencies. No new packages to install.

## Architecture Patterns

### Existing Project Structure (Relevant Parts)
```
server/
  config.py                     # SQLITE_DATABASE_PATH, ACTIVE_DATABASE_TYPE
  database/
    models.py                   # LDMPlatform, LDMProject, LDMFolder, LDMFile, LDMRow
    db_setup.py                 # Engine creation, table initialization
    server_sqlite.py            # ServerSQLiteDatabase (ldm_* tables)
    offline.py                  # OfflineDatabase (offline_* tables)
    offline_schema.sql          # offline_* table DDL
  repositories/
    factory.py                  # 3-mode detection (PostgreSQL/server-SQLite/offline)
    sqlite/
      base.py                   # SchemaMode enum, TABLE_MAP
      platform_repo.py          # CRUD for platforms
      project_repo.py           # CRUD for projects (negative IDs for local)
      folder_repo.py            # CRUD for folders
      file_repo.py              # CRUD for files
  api/                          # FastAPI route modules
scripts/
  setup_mock_data.py            # NEW: mock DB setup script (to create)
locaNext/src/lib/
  stores/preferences.js         # localStorage-backed preferences (fonts, columns, etc.)
  components/PreferencesModal.svelte  # Current preferences UI (fonts only)
  components/pages/FilesPage.svelte   # File explorer with platform/project/folder navigation
```

### Pattern 1: Database Mode Detection
**What:** The server supports 3 database modes: PostgreSQL (online), server-local SQLite (fallback), and offline SQLite (Electron app). The mock script should target SERVER mode SQLite (`ldm_*` tables) since DEV_MODE uses this when PostgreSQL is unavailable.
**When to use:** Mock data creation
**Key insight:** `config.ACTIVE_DATABASE_TYPE` tracks which DB is active. In DEV_MODE without PostgreSQL, it falls back to SQLite at `server/data/offline.db` using `ldm_*` tables (same schema as PostgreSQL).

### Pattern 2: Repository CRUD for Projects
**What:** Projects are created via repository pattern with negative IDs for locally-created items.
**Key code from `project_repo.py`:**
```python
# SERVER mode: standard columns only
await conn.execute(
    f"""INSERT INTO {self._table('projects')}
       (id, name, description, platform_id, owner_id, is_restricted, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (project_id, unique_name, description, platform_id, owner_id, 0, now, now)
)
```

### Pattern 3: Preferences Store (localStorage)
**What:** `preferences.js` uses Svelte writable store backed by `localStorage.getItem('locaNext_preferences')`. Auto-saves on changes. Merged with defaults on load.
**Limitation for SET-01/02:** localStorage is per-browser, not per-project. LOC PATH and EXPORT PATH need to be **per-project** and persist across app restarts. Two options:
1. Store in localStorage keyed by project ID (simple, client-only)
2. Store in the database as project metadata (robust, server-side)

**Recommendation:** Use localStorage keyed by project ID for v6.0 (matches existing pattern, no backend changes needed for storage). Add a backend validation-only endpoint to check paths.

### Pattern 4: Navigation and Page Structure
**What:** Navigation uses a store (`currentPage` writable). Pages are: files, tm, grid, tm-entries, gamedev, codex, worldmap, item-codex, character-codex, audio-codex, region-codex. There is NO dedicated Settings page -- only a PreferencesModal for fonts and a dropdown menu.
**For SET-01/02:** Add a "Settings" item to the Settings dropdown menu in the layout, which opens a dedicated SettingsPage (or extend PreferencesModal with a new tab/section for paths).

### Pattern 5: Language Detection from Project Name
**What:** No existing language detection from project names in LocaNext. QuickTranslate detects languages from file/folder suffixes (e.g., `_FRE`, `_ENG`) using `source_scanner.py::_get_valid_language_codes()`.
**For MOCK-02:** Create a simple mapping function:
```python
LANGUAGE_SUFFIX_MAP = {
    "FRE": "French", "ENG": "English", "GER": "German",
    "ITA": "Italian", "JPN": "Japanese", "KOR": "Korean",
    "POL": "Polish", "POR-BR": "Portuguese (BR)", "RUS": "Russian",
    "SPA-ES": "Spanish (ES)", "SPA-MX": "Spanish (MX)",
    "TUR": "Turkish", "ZHO-CN": "Chinese (Simplified)",
    "ZHO-TW": "Chinese (Traditional)", "MULTI": "Multi-Language"
}

def detect_language_from_name(project_name: str) -> tuple[str, str]:
    """Extract language code and display name from project name suffix."""
    parts = project_name.upper().rsplit("_", 1)
    if len(parts) == 2 and parts[1] in LANGUAGE_SUFFIX_MAP:
        return parts[1], LANGUAGE_SUFFIX_MAP[parts[1]]
    return "UNKNOWN", "Unknown"
```

### Anti-Patterns to Avoid
- **Using async repositories in CLI script:** The mock script runs standalone, not inside FastAPI. Use sync `sqlite3` directly, not the async `aiosqlite` repository layer.
- **Copying test123 files into the repo:** The 1M+ line languagedata files are massive. Point LOC PATH to the Windows path, do not copy them.
- **Modifying Sacred Scripts:** Never change QuickTranslate source code. The language detection map for LocaNext is a separate implementation.
- **Using `print()` in the script:** Use `loguru` logger as per project rules.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path validation on Windows paths | Custom path checker | `pathlib.Path` + `os.path.exists()` | Handles WSL/Windows path differences |
| Language code to name mapping | Hardcoded strings everywhere | Central `LANGUAGE_SUFFIX_MAP` dict | QuickTranslate uses similar pattern in `config.py` |
| SQLite table creation | Manual CREATE TABLE | Use existing `Base.metadata.create_all(engine)` from models.py | Models already define all `ldm_*` tables |

## Common Pitfalls

### Pitfall 1: Wrong SQLite Table Prefix
**What goes wrong:** Writing to `offline_*` tables instead of `ldm_*` tables, or vice versa.
**Why it happens:** Two SQLite schemas coexist -- `offline_*` (Electron offline mode) and `ldm_*` (server-local SQLite fallback). DEV_MODE uses server-local.
**How to avoid:** The mock script must target `ldm_*` tables. Verify by checking `config.ACTIVE_DATABASE_TYPE` or just use the `ldm_*` table names directly.
**Warning signs:** Projects created but not visible in the file explorer (wrong table prefix).

### Pitfall 2: Test123 Files Are Tab-Separated TXT, Not XML
**What goes wrong:** Assuming test123 contains XML `languagedata_*.xml` files when they're actually tab-separated `.txt` files.
**Why it happens:** MOCK-04 says "test languagedata files from test123 directory" but the actual files are `languagedata_fr PC 0904 1847.txt` (tab-separated, 1M+ lines) and `.xlsx`. SET-03 validates for `languagedata_*.xml`.
**How to avoid:** For MOCK-04, the LOC PATH validation should accept both `.txt` and `.xml` formats. The actual QuickTranslate transfer also handles `.txt` format. Alternatively, the mock script could copy a small subset and convert to XML format.
**Warning signs:** Path validation rejects the test123 directory because it only looks for `.xml`.

### Pitfall 3: Per-Project Settings vs Global Settings
**What goes wrong:** Storing LOC/EXPORT paths globally when they need to be per-project.
**Why it happens:** The existing preferences store is global (single `locaNext_preferences` key in localStorage).
**How to avoid:** Key settings by project ID: `locaNext_project_settings_{projectId}` in localStorage. Or add a `settings` JSON column to the project model.
**Warning signs:** Changing LOC PATH for one project affects all projects.

### Pitfall 4: Windows Paths from WSL
**What goes wrong:** Backend path validation fails because it runs in WSL but receives Windows paths like `C:\Users\MYCOM\Desktop\...`.
**Why it happens:** In DEV mode, the backend runs in WSL but the user enters Windows-style paths.
**How to avoid:** The validation endpoint must translate Windows paths to WSL paths (`C:\Users\MYCOM\...` -> `/mnt/c/Users/MYCOM/...`) before checking existence. The production Windows build won't need this translation.
**Warning signs:** Valid paths fail validation in DEV mode.

### Pitfall 5: Foreign Key Constraints
**What goes wrong:** Creating projects without a valid platform_id or owner_id causes constraint violations.
**Why it happens:** `ldm_projects` has FK to `ldm_platforms.id` and `users.user_id`.
**How to avoid:** The mock script must create: (1) admin user first (or use existing), (2) platform, (3) projects under that platform. Use the existing `create_admin.py` pattern for the user.
**Warning signs:** "FOREIGN KEY constraint failed" errors.

## Code Examples

### Example 1: Direct SQLite Mock Data Creation
```python
"""scripts/setup_mock_data.py -- CLI mock DB setup for v6.0"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from loguru import logger

# Database path (same as server/config.py)
DB_PATH = Path(__file__).parent.parent / "server" / "data" / "offline.db"

def wipe_and_create(db_path: Path):
    """Wipe ldm_* tables and create mock platform + projects."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    now = datetime.utcnow().isoformat()

    # Wipe existing data
    for table in ["ldm_rows", "ldm_files", "ldm_folders", "ldm_projects", "ldm_platforms"]:
        conn.execute(f"DELETE FROM {table}")

    # Ensure admin user exists (user_id=1)
    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, username, password_hash, role, is_active, created_at)
        VALUES (1, 'admin', '$2b$12$...hash...', 'admin', 1, ?)
    """, (now,))

    # Create platform
    conn.execute("""
        INSERT INTO ldm_platforms (id, name, owner_id, description, created_at, updated_at)
        VALUES (1, 'v6.0 Showcase', 1, 'Mock platform for offline transfer demo', ?, ?)
    """, (now, now))

    # Create 3 projects
    projects = [
        (1, "project_FRE", "French localization project"),
        (2, "project_ENG", "English localization project"),
        (3, "project_MULTI", "Multi-language merge testing"),
    ]
    for pid, name, desc in projects:
        conn.execute("""
            INSERT INTO ldm_projects (id, name, owner_id, platform_id, description, created_at, updated_at)
            VALUES (?, ?, 1, 1, ?, ?, ?)
        """, (pid, name, desc, now, now))

    # Create subfolders for project_MULTI (MOCK-03)
    conn.execute("""
        INSERT INTO ldm_folders (id, project_id, name, created_at)
        VALUES (1, 3, 'corrections_FRE', ?)
    """, (now,))
    conn.execute("""
        INSERT INTO ldm_folders (id, project_id, name, created_at)
        VALUES (2, 3, 'corrections_ENG', ?)
    """, (now,))

    conn.commit()
    conn.close()
    logger.info(f"Mock data created: 1 platform, 3 projects, 2 folders")
```

### Example 2: Language Badge Component Pattern
```svelte
<script>
  /** Language badge -- derives language from project name suffix */
  let { projectName = '' } = $props();

  const LANG_MAP = {
    FRE: { label: 'French', color: '#3b82f6' },
    ENG: { label: 'English', color: '#10b981' },
    GER: { label: 'German', color: '#f59e0b' },
    MULTI: { label: 'Multi', color: '#8b5cf6' },
  };

  let langInfo = $derived(() => {
    const suffix = projectName.toUpperCase().split('_').pop();
    return LANG_MAP[suffix] || { label: 'Unknown', color: '#6b7280' };
  });
</script>

<span class="lang-badge" style="background: {langInfo().color}">
  {langInfo().label}
</span>
```

### Example 3: Per-Project Settings Store Pattern
```javascript
// Store project settings keyed by project ID in localStorage
const SETTINGS_PREFIX = 'locaNext_project_settings_';

export function getProjectSettings(projectId) {
  const stored = localStorage.getItem(`${SETTINGS_PREFIX}${projectId}`);
  return stored ? JSON.parse(stored) : { locPath: '', exportPath: '' };
}

export function setProjectSettings(projectId, settings) {
  localStorage.setItem(`${SETTINGS_PREFIX}${projectId}`, JSON.stringify(settings));
}
```

### Example 4: Path Validation Endpoint
```python
@router.post("/api/settings/validate-path")
async def validate_path(body: PathValidationRequest):
    """Validate that a path exists and contains expected files."""
    path = Path(body.path)

    # WSL translation for DEV mode
    if str(path).startswith(("C:\\", "D:\\", "E:\\", "F:\\")):
        drive = str(path)[0].lower()
        rest = str(path)[3:].replace("\\", "/")
        path = Path(f"/mnt/{drive}/{rest}")

    if not path.exists():
        return {"valid": False, "error": "Path does not exist"}
    if not path.is_dir():
        return {"valid": False, "error": "Path is not a directory"}

    # Check for languagedata files
    lang_files = list(path.glob("languagedata_*.*"))
    if not lang_files:
        return {"valid": False, "error": "No languagedata files found",
                "hint": "Expected files like languagedata_fre.xml or languagedata_fr.txt"}

    return {"valid": True, "files_found": len(lang_files),
            "languages": [f.stem.replace("languagedata_", "") for f in lang_files]}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual DB seeding | CLI scripts with `--confirm-wipe` | v3.0 (Phase 15) | `tools/generate_mega_index_mockdata.py` established the pattern |
| Global preferences only | Per-project settings | v6.0 (this phase) | LOC/EXPORT paths must be project-scoped |
| No language badges | Auto-detect from project name suffix | v6.0 (this phase) | New feature, no prior implementation |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in project) |
| Config file | None detected -- needs setup if validation required |
| Quick run command | `python -m pytest tests/ -x --tb=short` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOCK-01 | Script creates platform + 3 projects in DB | unit | `python -m pytest tests/test_mock_data.py::test_wipe_and_create -x` | Wave 0 |
| MOCK-02 | Language auto-detection from project name | unit | `python -m pytest tests/test_mock_data.py::test_language_detection -x` | Wave 0 |
| MOCK-03 | project_MULTI has language-suffixed subfolders | unit | `python -m pytest tests/test_mock_data.py::test_multi_project_folders -x` | Wave 0 |
| MOCK-04 | test123 languagedata files loadable | integration | `python -m pytest tests/test_mock_data.py::test_languagedata_loading -x` | Wave 0 |
| SET-01 | LOC PATH configurable and persistent | manual-only | Manual: set path in UI, restart, verify persisted | N/A |
| SET-02 | EXPORT PATH configurable and persistent | manual-only | Manual: set path in UI, restart, verify persisted | N/A |
| SET-03 | Path validation shows errors for invalid paths | unit | `python -m pytest tests/test_path_validation.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_mock_data.py -x --tb=short`
- **Per wave merge:** Full test suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mock_data.py` -- covers MOCK-01, MOCK-02, MOCK-03, MOCK-04
- [ ] `tests/test_path_validation.py` -- covers SET-03

## Open Questions

1. **Per-project settings storage mechanism**
   - What we know: localStorage is global. LOC/EXPORT paths must be per-project.
   - What's unclear: Should we key localStorage by project ID, or add a `settings` JSON column to `ldm_projects`?
   - Recommendation: localStorage keyed by project ID (`locaNext_project_settings_{id}`) is simpler and consistent with existing preferences pattern. Backend DB storage is more robust but adds migration complexity. Use localStorage for v6.0.

2. **Settings page vs modal**
   - What we know: Current Settings menu has: Preferences (fonts), About, Change Password, Logout. No dedicated Settings page exists.
   - What's unclear: Should LOC/EXPORT path settings be a new page in the navigation, or a section in the existing PreferencesModal?
   - Recommendation: Add a "Project Settings" section to the PreferencesModal (reuse existing modal pattern). Alternatively, add a project-level right-click menu "Configure Paths" on the project in FilesPage. The modal approach is less disruptive.

3. **test123 file format compatibility**
   - What we know: test123 contains `.txt` (tab-separated, 1M+ lines) and `.xlsx` files, not `.xml`. SET-03 validates for `languagedata_*.xml`.
   - What's unclear: Should path validation accept `.txt` and `.xlsx` too, or only `.xml`?
   - Recommendation: Accept `languagedata_*.*` (any extension) for now. QuickTranslate handles both formats. The validation message should list found file types.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of `server/database/models.py` -- all LDM table definitions
- Direct codebase analysis of `server/repositories/sqlite/` -- repository CRUD patterns
- Direct codebase analysis of `server/config.py` -- database mode detection, paths
- Direct codebase analysis of `locaNext/src/lib/stores/preferences.js` -- localStorage persistence
- Direct codebase analysis of `locaNext/src/routes/+layout.svelte` -- Settings dropdown menu
- Direct codebase analysis of `RessourcesForCodingTheProject/NewScripts/QuickTranslate/` -- language detection patterns
- Direct filesystem check of `test123/` -- confirmed file existence and format

### Secondary (MEDIUM confidence)
- `tools/generate_mega_index_mockdata.py` -- existing mock data CLI pattern (v3.0)
- `.planning/milestones/v3.0-REQUIREMENTS.md` -- prior MOCK-01 through MOCK-08 requirements

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new deps
- Architecture: HIGH -- all patterns directly observed in codebase
- Pitfalls: HIGH -- identified from actual code analysis (table prefixes, FK constraints, path formats)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable codebase, internal patterns)
