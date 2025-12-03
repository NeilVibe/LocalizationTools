# Coding Standards

**Rules** | **Patterns** | **Conventions** | **Common Pitfalls**

---

## 🎨 CRITICAL RULES (MUST FOLLOW!)

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

### 5. Optional Services

**All optional services gracefully degrade if unavailable:**

- **PostgreSQL:** Configured, ready to use, but SQLite is default
  - To enable: Set `DATABASE_TYPE=postgresql` in environment
  - See: `docs/POSTGRESQL_SETUP.md`

- **Redis:** Caching layer with graceful fallback
  - To enable: Set `REDIS_ENABLED=true`
  - Falls back silently if unavailable
  - See: `server/utils/cache.py`

- **Celery:** Background tasks (daily stats, cleanup)
  - To enable: Set `CELERY_ENABLED=true`
  - Optional, not required for core functionality
  - See: `server/tasks/`

---

## 🚨 COMMON PITFALLS TO AVOID

### 1. Don't Mix Async and Sync DB Sessions

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
- **TESTING_GUIDE.md** - Testing procedures
