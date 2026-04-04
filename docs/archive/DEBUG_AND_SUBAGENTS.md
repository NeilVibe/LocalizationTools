# Debug Protocol & Subagent System

> Complete guide to debugging LocaNext and using parallel subagents effectively

---

## Table of Contents

1. [Debug Workflow](#debug-workflow)
2. [Subagent System](#subagent-system)
3. [Parallel Multi-Agent Debugging](#parallel-multi-agent-debugging)
4. [Quick Reference](#quick-reference)
5. [Session 60 Case Study](#session-60-case-study)

---

## Debug Workflow

### Step 1: Reproduce the Bug

```
User reports: "File upload doesn't work"
                    ↓
Ask: WHERE did they try? (DEV mode? Offline Storage? Online?)
                    ↓
This matters because: DIFFERENT CODE PATHS!
```

### Step 2: Check Logs

```bash
# Backend logs (ALWAYS check first)
tail -50 /tmp/locanext/backend.log

# Live follow
tail -f /tmp/locanext/backend.log

# Errors only
cat /tmp/locanext/backend.log | tr -cd '\11\12\15\40-\176' | grep -i "error\|exception" | tail -20

# Frontend logs (sent to backend via remote-logger)
grep "FRONTEND" /tmp/locanext/backend.log | tail -10

# Clear logs for fresh capture
> /tmp/locanext/backend.log
```

### Step 3: Identify the Code Path

**Critical Lesson from Session 60:**

| User Action | Code Path | Why Different |
|-------------|-----------|---------------|
| Upload to Project | `files.py:upload_file()` | PostgreSQL |
| Upload to Offline Storage | `files.py:_upload_to_local_storage()` | SQLite |
| Register TM (online) | `files.py` → `TMManager` | PostgreSQL |
| Register TM (offline) | `files.py` → `tm_repo.create()` | SQLite |

**ALWAYS ask: Which mode was the user in?**

### Step 4: Find the Bug

Common patterns after aiosqlite migration:

```python
# Pattern 1: Missing await
# ERROR: 'coroutine' object is not subscriptable
result = offline_db.get_data()      # WRONG
result = await offline_db.get_data() # RIGHT

# Pattern 2: sqlite3.Row vs dict
# ERROR: 'sqlite3.Row' object has no attribute 'get'
row = await cursor.fetchone()
value = row.get("key")              # WRONG - Row doesn't have .get()
row = dict(await cursor.fetchone())
value = row.get("key")              # RIGHT - convert to dict first

# Pattern 3: Sync calling async
# ERROR: coroutine was never awaited
def sync_function():
    result = async_db_call()        # WRONG - can't await in sync

def sync_function():
    import asyncio
    result = asyncio.run(async_db_call())  # RIGHT - bridge sync/async
```

### Step 5: Fix and Test

```bash
# Make the fix, then restart backend
pkill -f "python.*server/main" 2>/dev/null || true
sleep 2
DEV_MODE=true python3 server/main.py > /tmp/locanext/backend.log 2>&1 &
sleep 4

# Test the specific action
curl -s -X POST "http://localhost:8888/api/ldm/files/upload" \
  -H "Authorization: Bearer OFFLINE_MODE_test123" \
  -F "file=@tests/fixtures/sample_language_data.txt" \
  -F "storage=local"
```

---

## Subagent System

### What Are Subagents?

Subagents are specialized AI workers spawned via the `Task` tool. They run autonomously with specific tools and return results.

### Available Subagents

| Subagent | Purpose | Tools Available |
|----------|---------|-----------------|
| `gdp-debugger` | **EXTREME precision** - microscopic root cause | Read, Grep, Glob, Bash |
| `python-debugger` | Backend API, database, async issues | Read, Grep, Glob, Bash |
| `vite-debugger` | Frontend Svelte/Vite UI, reactivity | Read, Grep, Glob, Bash |
| `nodejs-debugger` | Electron main process, IPC | Read, Grep, Glob, Bash |
| `windows-debugger` | Bugs ONLY in packaged Windows app | Read, Grep, Glob, Bash |
| `code-reviewer` | Code review after writing | Read, Grep, Glob |
| `dev-tester` | Run Playwright tests | Read, Grep, Glob, Bash |
| `ci-specialist` | CI/CD workflows, build failures | Read, Grep, Glob, Bash |
| `security-auditor` | Security vulnerabilities | Read, Grep, Glob |
| `Explore` | Codebase exploration | All except Edit/Write |
| `Plan` | Implementation planning | All except Edit/Write |

### When to Use Each

| Scenario | Best Subagent |
|----------|---------------|
| 500 error from API | `python-debugger` |
| UI button does nothing | `vite-debugger` |
| Need exact line causing bug | `gdp-debugger` |
| Build failed in CI | `ci-specialist` |
| After writing code | `code-reviewer` |
| Find pattern across codebase | `gdp-debugger` |
| Understand architecture | `Explore` |

---

## Parallel Multi-Agent Debugging

### The Power of Parallel Agents

Instead of debugging sequentially (slow), launch multiple agents simultaneously:

```
SEQUENTIAL (slow):
  Debug TM → wait → Debug QA → wait → Debug Files → wait
  Total: 3x time

PARALLEL (fast):
  Debug TM ─┐
  Debug QA ─┼─→ All results at once!
  Debug Files─┘
  Total: 1x time
```

### How to Launch Parallel Agents

**Key Rule:** All Task calls must be in a SINGLE assistant message.

Example from Session 60:

```
User: "debug TM, QA, and other functions"

Claude: [Launches 4 agents in ONE message]
  - Task(python-debugger, "Debug TM registration...")
  - Task(python-debugger, "Debug QA functionality...")
  - Task(gdp-debugger, "Find ALL missing await...")
  - Task(python-debugger, "Debug sync/folders...")

Result: All 4 run simultaneously, return together
```

### Parallel Agent Strategies

**Strategy 1: Divide by Feature**
```
Agent 1: Debug TM functionality
Agent 2: Debug QA functionality
Agent 3: Debug File operations
Agent 4: Debug Sync operations
```

**Strategy 2: Divide by Layer**
```
Agent 1: Check routes (server/tools/ldm/routes/)
Agent 2: Check services (server/services/)
Agent 3: Check repositories (server/repositories/)
Agent 4: Check database (server/database/)
```

**Strategy 3: Divide by Pattern**
```
Agent 1: Find missing "await" statements
Agent 2: Find sqlite3.Row without dict()
Agent 3: Find sync functions calling async
Agent 4: Find unhandled exceptions
```

### Combining Results

After parallel agents return, Claude combines their findings:

```
Agent 1 found: 3 issues in pretranslate.py
Agent 2 found: QA routes clean
Agent 3 found: All routes clean
Agent 4 found: Sync clean

COMBINED: Only pretranslate.py has bugs!
```

---

## Quick Reference

### Log Commands

```bash
# Check backend
tail -50 /tmp/locanext/backend.log

# Check for errors
grep -i "error\|exception" /tmp/locanext/backend.log | tail -20

# Frontend logs
grep "FRONTEND" /tmp/locanext/backend.log | tail -10

# Clear for fresh test
> /tmp/locanext/backend.log
```

### Test Commands

```bash
# Test Offline Storage upload
curl -s -X POST "http://localhost:8888/api/ldm/files/upload" \
  -H "Authorization: Bearer OFFLINE_MODE_test123" \
  -F "file=@tests/fixtures/sample_language_data.txt" \
  -F "storage=local"

# Test TM registration
curl -s -X POST "http://localhost:8888/api/ldm/files/{FILE_ID}/register-as-tm" \
  -H "Authorization: Bearer OFFLINE_MODE_test123" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test TM", "source_language": "KR", "target_language": "EN"}'
```

### Common Error → Fix

| Error | Cause | Fix |
|-------|-------|-----|
| `'coroutine' object is not subscriptable` | Missing `await` | Add `await` before async call |
| `'coroutine' object is not iterable` | Missing `await` | Add `await` before async call |
| `coroutine was never awaited` | Missing `await` | Add `await` or use `asyncio.run()` |
| `'sqlite3.Row' has no attribute 'get'` | Row not converted | Use `dict(row)` first |
| `database is locked` | Concurrent access | Kill zombie processes, reinit DB |

### Database Reset

```bash
# Full nuclear reset (SQLite + PostgreSQL)
./scripts/db_manager.sh nuke

# SQLite only
./scripts/db_manager.sh sqlite-reinit

# Check status
./scripts/db_manager.sh status -v
```

---

## Session 60 Case Study

### The Problem

User reported: "File upload doesn't work" and "TM registration doesn't work"

### Initial Debugging (WRONG)

I tested via API with admin user → **PostgreSQL path** → worked fine!

But user was in **Offline Storage** → **SQLite path** → different code!

### The Lesson

**ALWAYS identify which code path the user is on:**

```
Online mode (admin user)     →  PostgreSQL  →  Different code
Offline Storage (OFFLINE_MODE) →  SQLite    →  Different code
```

### Parallel Agent Debug

Launched 4 agents simultaneously:

| Agent | Task | Result |
|-------|------|--------|
| python-debugger | Debug TM | Found 3 bugs in pretranslate.py |
| python-debugger | Debug QA | Clean |
| gdp-debugger | Find all missing await | Routes clean |
| python-debugger | Debug sync/folders | Clean |

### Bugs Found

1. `files.py:570` - Missing `await` on `remove_subscription()`
2. `files.py:1466` - Missing `await` on `create_local_file()`
3. `files.py:1478` - Missing `await` on `add_rows_to_local_file()`
4. `pretranslate.py:75` - Sync calling async without bridge
5. `pretranslate.py:508` - Sync calling async without bridge
6. `pretranslate.py:537` - Sync calling async without bridge
7. `tm_repo.py:69-78` - `sqlite3.Row.get()` doesn't exist
8. `tm_repo.py:100-108` - Same issue
9. `tm_repo.py:245-248` - Same issue

### Fixes Applied

```python
# Missing await
result = await offline_db.create_local_file(...)

# Sync calling async
import asyncio
result = asyncio.run(offline_db.get_local_file(file_id))

# sqlite3.Row to dict
assignment = await cursor.fetchone()
assignment = dict(assignment)  # ADD THIS
value = assignment.get("key")  # Now works!
```

### Result

All File Explorer and TM functionality working in Offline Storage mode.

---

## Tips & Tricks

### 1. Always Test BOTH Paths

```bash
# Test PostgreSQL path
curl -H "Authorization: Bearer {JWT_TOKEN}" ...

# Test SQLite path
curl -H "Authorization: Bearer OFFLINE_MODE_test123" ...
```

### 2. Use Parallel Agents for Systematic Search

When you need to check multiple areas, don't do it sequentially. Launch agents in parallel.

### 3. GDP for Precision

When you need the EXACT line causing a bug, use `gdp-debugger`. It does microscopic analysis.

### 4. Check Logs BEFORE and AFTER

```bash
> /tmp/locanext/backend.log  # Clear
# Do the action
tail -50 /tmp/locanext/backend.log  # Check
```

### 5. Binary File Logs

If grep says "binary file matches":
```bash
cat /tmp/locanext/backend.log | tr -cd '\11\12\15\40-\176' | grep "pattern"
```

---

*Created: Session 60 - After debugging aiosqlite migration issues*
*Last Updated: 2026-01-31*
