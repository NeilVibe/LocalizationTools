# Coding Standards

**Rules** | **Patterns** | **Conventions** | **Common Pitfalls**

---

## 🎨 CRITICAL RULES (MUST FOLLOW!)

### 0. LDM ABSORBS, NEVER DEPENDS

**LDM is the future. Legacy apps will be deprecated.**

```
WRONG:  LDM imports from xlstransfer/, quicksearch/, kr_similar/
RIGHT:  Shared code lives in server/utils/, everyone imports from there
```

When absorbing features into LDM:
1. **Move shared logic** to `server/utils/` (embeddings, text processing, QA helpers)
2. **LDM imports from utils/** - never from legacy app folders
3. **Legacy apps also import from utils/** - until they're deprecated
4. **When ready:** Delete legacy app folders, LDM remains untouched

**LDM must be fully independent. No imports from legacy apps.**

---

### 1. CLEAN PROJECT ALWAYS
- No temporary files in project root
- Archive unused code to `archive/`
- Delete obvious bloat (temp test files, etc.)
- Keep `.gitignore` updated

### 2. TEST EVERYTHING
- Add unit tests for new functions
- Add integration tests for API endpoints
- Run `pytest` before committing
- Maintain 80%+ test coverage

### 3. UPDATE DOCUMENTATION
- Update `Roadmap.md` after completing tasks
- Update `CLAUDE.md` if architecture changes
- Add comments to complex code
- Document new patterns

### 4. MODULAR CODE ONLY
- No global variables (except configuration)
- Use dependency injection
- Each function does ONE thing
- Type hints required

### 5. DON'T PARSE WHAT YOU ALREADY HAVE (AU-006 LESSON)

**BEFORE writing regex, parsing, or extraction code - ASK:**
- Does this value already exist somewhere?
- Is there a variable/output I can use directly?
- Am I duplicating logic that exists elsewhere?

**BAD (AU-006):**
```powershell
# Regex to extract version from version.py... WHY??
if ($content -match 'VERSION\s*=\s*"([^"]+)"') { $version = $Matches[1] }
```

**GOOD:**
```powershell
# CI already has the version - just use it
$version = $env:VERSION  # from ${{ needs.job.outputs.version }}
```

**The Rule:** If the data exists, use it directly. Don't create a second path to the same data.

### 5. ASYNC BY DEFAULT (Backend)
- All new endpoints should be async
- Use `AsyncSession` for database
- Use `async def` for new functions
- See existing async endpoints as examples

---

## 📝 FILE NAMING CONVENTIONS

- `*_async.py` - Async versions of modules
- `test_*.py` - Test files
- `*_utils.py` - Utility modules
- `*_config.py` - Configuration files

---

## 📦 IMPORT ORDER

```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import FastAPI
from sqlalchemy import select

# Local
from server.database.models import User
from server.utils.auth import verify_token
```

---

## 🏗️ KEY PATTERNS

### 1. The Tool Restructuring Pattern

**XLSTransfer is the TEMPLATE for all future tools.**

```
Monolithic Script (1435 lines, globals, hard to maintain)
↓
Restructure into Clean Modules:
├── core.py - Core business logic functions
├── module1.py - Specific functionality domain
├── module2.py - Another functionality domain
└── utils.py - Utility functions

Benefits:
✅ Testable (each function isolated)
✅ Reusable (import what you need)
✅ Maintainable (clear separation of concerns)
✅ Framework-agnostic (works with Gradio, Electron, CLI, etc.)
```

**When adding a new tool:**
1. Take the monolithic .py script
2. Follow XLSTransfer pattern (see `server/tools/xlstransfer/`)
3. Break into modules by functionality
4. Add type hints and docstrings
5. Write unit tests
6. Integrate into LocaNext (add to Apps dropdown, design one-page GUI)

---

### 2. Async Architecture (Backend)

**All new endpoints are async for 10-100x better concurrency.**

```python
# Pattern: Async endpoint with async DB
@router.post("/submit")
async def submit_logs(
    submission: LogSubmission,
    db: AsyncSession = Depends(get_async_db),  # Async session
    current_user: dict = Depends(get_current_active_user_async)  # Async auth
):
    async with db.begin():  # Async transaction
        result = await db.execute(select(User)...)  # Async query
        user = result.scalar_one_or_none()

    await emit_log_entry({...})  # Async WebSocket emit
    return LogResponse(...)
```

**Files:** `server/api/*_async.py`, `server/utils/dependencies.py`

---

### 3. WebSocket Real-Time Updates

**Pattern:** Emit events from API endpoints, clients receive live updates

```python
# Server-side (emit event)
from server.utils.websocket import emit_log_entry

await emit_log_entry({
    'user_id': user_id,
    'tool_name': 'XLSTransfer',
    'status': 'success',
    'timestamp': datetime.utcnow().isoformat()
})

# Client-side (JavaScript/Svelte)
socket.on('log_entry', (data) => {
    // Update UI in real-time
});
```

**Files:** `server/utils/websocket.py`

---

### 4. Comprehensive Logging

**Every HTTP request is logged at every microstep:**

```
[Request ID] → POST /api/v2/logs/submit | Client: 127.0.0.1 | User-Agent: ...
[Request ID] ← 200 POST /api/v2/logs/submit | Duration: 45.23ms
```

**Slow requests automatically flagged:**
```
[Request ID] SLOW REQUEST: POST /api/v2/logs/submit took 1205.34ms
```

**See `docs/LOGGING_PROTOCOL.md` for complete requirements.**

---

### 5. Database Architecture

**PostgreSQL is REQUIRED for all text data. No SQLite.**

```
TEXT DATA → PostgreSQL (shared, synced across users)
COMPUTED FILES → Local disk (heavy, rebuildable from DB)
```

| PostgreSQL | Local Disk |
|------------|------------|
| LDM rows (source/target) | FAISS indexes |
| TM entries | Embeddings (.npy) |
| Projects, files metadata | Hash lookups (.pkl) |
| Users, sessions, logs | ML models |

- **PostgreSQL + PgBouncer:** 1000 connections, real-time sync
  - Required for multi-user collaboration
  - See: `docs/deployment/POSTGRESQL_SETUP.md`
  - See: `docs/history/wip-archive/P21_DATABASE_POWERHOUSE.md`

- **Redis:** Optional caching layer
  - To enable: Set `REDIS_ENABLED=true`
  - Falls back silently if unavailable

- **Celery:** Optional background tasks
  - To enable: Set `CELERY_ENABLED=true`

---

### 6. Factor Architecture for Progress Tracking (Frontend)

**All async operations MUST use Factor Architecture for progress tracking.**

```javascript
// Module: locaNext/src/lib/utils/trackedOperation.js

// Pattern 1: createTracker() - Manual control (RECOMMENDED)
import { createTracker } from "$lib/utils/trackedOperation.js";

async function loadDictionary() {
  const tracker = createTracker('ToolName', 'Operation Name');
  tracker.start();
  tracker.update(25, 'Loading...');

  try {
    const result = await someAsyncOperation();
    tracker.complete('Operation completed successfully!');
    return result;
  } catch (error) {
    tracker.fail(error.message);
    throw error;
  }
}

// Pattern 2: withProgress() - Auto-wrapping
import { withProgress } from "$lib/utils/trackedOperation.js";

const result = await withProgress('ToolName', 'Operation', async (progress) => {
  progress.update(50, 'Halfway done...');
  return await someAsyncOperation();
});

// Pattern 3: parseProgress() - For Python stderr output
import { parseProgress } from "$lib/utils/trackedOperation.js";

const progressHandler = (data) => {
  if (data.type === 'stderr') {
    const parsed = parseProgress(data.data);  // Handles: "X%", "Row X/Y", "Step X of Y"
    if (parsed) tracker.update(parsed.progress, parsed.message);
  }
};
window.electron.onPythonOutput(progressHandler);
```

**When adding a new tool:**
1. Import `createTracker` from `$lib/utils/trackedOperation.js`
2. Create tracker at start of each async operation
3. Update progress at meaningful points
4. Complete or fail at the end
5. GlobalStatusBar and TaskManager auto-display progress

**Benefits:**
- DRY: One implementation, used everywhere
- Consistent: Same progress format across all tools
- Maintainable: Fix bugs in ONE place
- Extensible: Add new tools with zero boilerplate

**Files:** `locaNext/src/lib/utils/trackedOperation.js`, `locaNext/src/lib/stores/globalProgress.js`

---

### 7. Factor Architecture for Progress Tracking (Backend)

**All backend long-running operations MUST use TrackedOperation context manager.**

```python
# Module: server/utils/progress_tracker.py

# Pattern 1: Context Manager (RECOMMENDED) - Auto create/complete/fail
from server.utils.progress_tracker import TrackedOperation

def process_tm(file_id, user_id):
    with TrackedOperation("TM Processing", user_id, tool_name="LDM") as op:
        op.update(25, "Generating embeddings...")
        embeddings = generate_embeddings()

        op.update(75, "Building FAISS index...")
        build_faiss(embeddings)

    # AUTO: Creates DB record on enter
    # AUTO: Emits WebSocket start event
    # AUTO: Updates DB + WebSocket on op.update()
    # AUTO: Marks complete on clean exit
    # AUTO: Marks failed on exception (with error message)

# Pattern 2: Manual Tracker (for existing code)
from server.utils.progress_tracker import ProgressTracker

tracker = ProgressTracker(operation_id)
tracker.update(50, "Halfway done...")
tracker.complete()  # or tracker.fail("Error message")
```

**When adding a new backend operation:**
1. Import `TrackedOperation` from `server/utils/progress_tracker.py`
2. Wrap long-running code in `with TrackedOperation(...) as op:`
3. Call `op.update(percent, message)` at meaningful points
4. TaskManager auto-displays progress via WebSocket

**Benefits:**
- AUTO: DB record created/updated/completed
- AUTO: WebSocket events emitted
- AUTO: Exception handling (marks failed)
- SYNC-SAFE: Works in sync functions (bridges to async WebSocket)

**Files:** `server/utils/progress_tracker.py`, `server/api/progress_operations.py`

---

## 🚨 COMMON PITFALLS TO AVOID

### 1. LAZY IMPORTS FOR HEAVY ML LIBRARIES (RECURRING ISSUE!)

**⚠️ THIS IS A RECURRING BUG - ALWAYS CHECK FOR THIS!**

Heavy ML libraries (`sentence_transformers`, `torch`, `transformers`) take **3-30+ seconds to import**.
Module-level imports cause:
- CI build failures (30s timeout exceeded)
- Slow server startup (3-7s → 30+s)
- Poor user experience

```python
# ❌ WRONG - Module-level import (blocks startup!)
from sentence_transformers import SentenceTransformer
import torch

MODELS_AVAILABLE = True  # This triggers import immediately!

class MyManager:
    def load_model(self):
        self.model = SentenceTransformer(MODEL_NAME)  # SentenceTransformer already imported!


# ✅ CORRECT - Lazy import pattern
from typing import TYPE_CHECKING

# Type hints only - no runtime import
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
    import torch

# Lazy availability check
_models_available: Optional[bool] = None

def _check_models_available() -> bool:
    """Lazy check if ML models are available. Cached after first call."""
    global _models_available
    if _models_available is None:
        try:
            import sentence_transformers  # noqa: F401
            import torch  # noqa: F401
            _models_available = True
        except ImportError:
            _models_available = False
    return _models_available

class MyManager:
    def load_model(self):
        # LAZY IMPORT: Only when actually needed
        from sentence_transformers import SentenceTransformer
        import torch

        if not _check_models_available():
            raise RuntimeError("ML libraries not available")

        self.model = SentenceTransformer(MODEL_NAME)
```

**Impact of this pattern:**
| Pattern | Import Time | CI Build |
|---------|-------------|----------|
| Eager import | 3-30s | ❌ Fails |
| Lazy import | 0.1-0.8s | ✅ Passes |

**Files that MUST use lazy imports:**
- Any file importing `sentence_transformers`
- Any file importing `torch` or `transformers`
- Any file importing heavy ML/AI libraries

**How to check for violations:**
```bash
# Find eager imports (should return nothing in module scope)
grep -rn "^from sentence_transformers\|^import torch\|^from torch" server/ --include="*.py"

# Check try-blocks at module level
grep -rn "try:" -A3 server/ --include="*.py" | grep "sentence_transformers\|torch"
```

**History:** This bug has recurred multiple times:
- Build 299: `kr_similar/embeddings.py` - Fixed 2025-12-18
- (Add future occurrences here)

---

### 2. Don't Mix Async and Sync DB Sessions (was #1)

```python
# ❌ WRONG
@router.post("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):  # Sync session in async endpoint!
    user = db.query(User).first()  # Blocks async event loop!

# ✅ CORRECT
@router.post("/endpoint")
async def my_endpoint(db: AsyncSession = Depends(get_async_db)):  # Async session
    result = await db.execute(select(User))  # Non-blocking
    user = result.scalar_one_or_none()
```

---

### 2. Don't Forget to Commit Async Transactions

```python
# ❌ WRONG
async with db.begin():
    user.last_login = datetime.utcnow()
    # No commit! Changes lost!

# ✅ CORRECT
async with db.begin():
    user.last_login = datetime.utcnow()
    # auto-commits when exiting context manager
# OR
db.add(user)
await db.commit()
```

---

### 3. Don't Archive Critical Code

**KEEP** (these are needed):
- Server code (all of it)
- Tool modules (`server/tools/*/`)
- Tests
- Documentation
- Configuration files
- Setup scripts

**ARCHIVE** (temporary/deprecated):
- Gradio UI files (already done ✅)
- Temporary test scripts
- Old implementations that are replaced

---

### 4. Don't Skip Documentation Updates

**After completing a task:**
1. ✅ Update `Roadmap.md` (mark task complete)
2. ✅ Update `CLAUDE.md` if architecture changed
3. ✅ Add comments to complex code
4. ✅ Document new patterns/conventions

---

### 5. Don't Use Print Statements

```python
# ❌ WRONG
print("User logged in")

# ✅ CORRECT
from loguru import logger
logger.info("User logged in", {"username": username})
```

---

### 6. Don't Hardcode Values

```python
# ❌ WRONG
threshold = 0.99

# ✅ CORRECT
from server.client_config.client_config import DEFAULT_THRESHOLD
threshold = config.get('threshold', DEFAULT_THRESHOLD)
```

---

## 🎓 LEARNING RESOURCES

### Understanding the Codebase

**Want to understand async endpoints?**
→ Read: `server/api/auth_async.py` (7 well-documented endpoints)

**Want to understand database models?**
→ Read: `server/database/models.py` (13 tables with relationships)

**Want to understand tool restructuring?**
→ Read: `server/tools/xlstransfer/` (template for all tools)

**Want to understand WebSocket events?**
→ Read: `server/utils/websocket.py` (event emitters, connection management)

**Want to understand testing patterns?**
→ Read: `tests/test_async_infrastructure.py` (async DB testing examples)

---

### Key Files to Read First

1. `server/main.py` - Server entry point, middleware, routes
2. `server/api/logs_async.py` - Example async endpoints with WebSocket
3. `server/tools/xlstransfer/core.py` - Tool restructuring example
4. `server/utils/dependencies.py` - Async DB session management

---

## 📚 Related Documentation

- **LOGGING_PROTOCOL.md** - Comprehensive logging requirements
- **ASYNC_PATTERNS.md** - Async architecture patterns
- **BACKEND_PRINCIPLES.md** - Backend design principles
- **BEST_PRACTICES.md** - Additional best practices
- **testing/README.md** - Testing hub
