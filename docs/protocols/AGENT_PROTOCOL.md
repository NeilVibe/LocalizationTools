# Agent Protocol

> Unified guide: agent types, orchestration, parallel patterns, debug workflow, and anti-patterns.
> Merged from: AGENT_ORCHESTRATION.md, PARALLEL_AGENT_PROTOCOL.md, DEBUG_AND_SUBAGENTS.md, AGENT_QUICK_REFERENCE.md

---

## Quick Reference

### Agent Types

| Agent | Purpose | Tools | Best For |
|-------|---------|-------|----------|
| **Bash** | Command execution | Shell | Git, npm, server checks |
| **Explore** | Codebase exploration | All except Edit/Write | "How does X work?" |
| **Plan** | Implementation design | All except Edit/Write | Architecture, feature planning |
| **general-purpose** | Multi-step complex tasks | All | Research + action combined |
| **gdp-debugger** | EXTREME precision debugging | Read, Grep, Glob, Bash | Exact line of failure, data corruption |
| **vite-debugger** | Frontend debugging | Read, Grep, Glob, Bash | Svelte, HMR, bundle, reactivity |
| **nodejs-debugger** | Backend debugging | Read, Grep, Glob, Bash | API, IPC, Electron main process |
| **python-debugger** | Backend API/DB debugging | Read, Grep, Glob, Bash | Async issues, database queries |
| **windows-debugger** | Packaged Windows app only | Read, Grep, Glob, Bash | Bugs only in .exe builds |
| **code-reviewer** | Code quality review | Read, Grep, Glob | Bugs, security, patterns |
| **dev-tester** | Test execution | Read, Grep, Glob, Bash | Playwright tests |
| **ci-specialist** | CI/CD workflows | Read, Grep, Glob, Bash | Build failures |
| **security-auditor** | Vulnerability analysis | Read, Grep, Glob | OWASP, injection risks |

### Specialist Agents

| Agent | Project |
|-------|---------|
| **quicksearch-specialist** | QuickSearch (search, dictionary) |
| **qacompiler-specialist** | QACompiler (generator, tracker) |
| **xls-transfer-specialist** | XLS Transfer (Excel data) |
| **tm-specialist** | Translation Memory ops |
| **mapdatagenerator-specialist** | MapDataGenerator |

### Decision Flowchart

```
Is it a bug?
├─ YES → gdp-debugger
│        ├─ Frontend? → + vite-debugger
│        └─ Backend?  → + python-debugger / nodejs-debugger
│
└─ NO → Is it new code?
        ├─ YES → Plan → Explore → general-purpose → code-reviewer
        │
        └─ NO → Is it understanding?
                ├─ YES → Explore (parallel, 3-6 agents)
                │
                └─ NO → Is it security?
                        ├─ YES → security-auditor + code-reviewer
                        └─ NO → general-purpose
```

### Agent Count by Task

| Task Type | Agents | Notes |
|-----------|--------|-------|
| Simple bug | 1-2 | gdp-debugger + code-reviewer |
| Complex bug | 3-7 | Multiple investigation angles |
| Feature (small) | 2-4 | Plan → Explore → implement → review |
| Feature (large) | 5-10 | Parallel components + review |
| Code review | 2-4 | code-reviewer + security-auditor (parallel) |
| Investigation | 3-6 | Multiple Explore agents (parallel) |
| Documentation | 1 per file | Parallel review agents |
| Refactoring | 3-6 | Explore + Plan + implement |
| Verification | 5-9 | Bash (tests), Explore (logs), UI checks |

---

## Conductor Pattern

Main Claude is the single point of coordination. Agents NEVER communicate directly.

```
                    MAIN CLAUDE (Conductor)
                    │  Understands full context
                    │  Spawns, aggregates, synthesizes
                    │
          ┌─────────┼─────────┬─────────┐
          ▼         ▼         ▼         ▼
      Agent 1   Agent 2   Agent 3   Agent N
      Task A    Task B    Task C    Task N
          │         │         │         │
          └─────────┴─────────┴─────────┘
                         │
                    Results Aggregation
                    by Main Claude
```

### Communication Rules

```
❌ WRONG: Agent 1 → Agent 2 (direct)
✅ RIGHT: Agent 1 → Main Claude → Agent 2
```

1. Main Claude spawns Agent A with specific task
2. Agent A completes task, returns results
3. Main Claude analyzes results
4. If follow-up needed, Main Claude spawns Agent B with new context
5. Agent B has NO knowledge of Agent A unless Main Claude provides it

**Why:** Consistency (single source of truth), context control, no conflicting info, traceable decisions.

### Aggregation Workflow

```
COLLECT    → Agent findings arrive
CATEGORIZE → Group by type (bugs, improvements, questions)
PRIORITIZE → Order by severity/impact
DEDUPLICATE → Multiple agents may find same issue
VALIDATE   → Cross-check conflicting findings
ACTION     → Create ordered fix list
DISPATCH   → Spawn fix agents for each action item
```

---

## Parallel Patterns

**Core philosophy:** Never do sequentially what can be done in parallel.

```
SEQUENTIAL (WRONG)           PARALLEL (RIGHT)
Bug A → Bug B → Bug C       Bug A ─┐
Total: 30 min                Bug B ─┼─→ All at once!
                             Bug C ─┘
                             Total: 10 min
```

### When Parallel vs Sequential

| Parallel | Sequential |
|----------|------------|
| Tasks are independent | Task B needs output from Task A |
| Searching multiple areas | Build before test |
| Multiple read-only operations | Fix before verification |
| Review + audit simultaneously | Migration before schema check |

**Key Rule:** All Task calls must be in a SINGLE assistant message to run simultaneously.

### Pattern 1: One Agent Per Issue

```
Issues: [BUG-001, BUG-002, BUG-003]
Agent 1 → BUG-001 | Agent 2 → BUG-002 | Agent 3 → BUG-003
Wait for all → Collect results
```

### Pattern 2: One Agent Per File

```
Files: [file1.ts, file2.ts, file3.ts]
Agent 1 → file1.ts | Agent 2 → file2.ts | Agent 3 → file3.ts
Wait for all → Merge findings
```

### Pattern 3: One Agent Per Concern (Layered)

```
Agent 1: Check routes     (server/tools/ldm/routes/)
Agent 2: Check services   (server/services/)
Agent 3: Check repos      (server/repositories/)
Agent 4: Check database   (server/database/)
```

### Pattern 4: Analyze-Discuss-Conclude-Fix

```
Phase 1 (Parallel):
  Agent 1 (Analyze): Deep dive into the issue
  Agent 2 (Discuss): Consider alternative explanations
  Agent 3 (Explore): Find related code

Phase 2 (Sequential):
  Agent 4 (Conclude): Synthesize findings from Phase 1

Phase 3 (Parallel):
  Agent 5 (Document): Write the analysis
  Agent 6 (Fix): Implement the solution
```

### Pattern 5: Fan-Out Verification

```
After a fix, verify from multiple angles simultaneously:
Agent 1: Unit tests     | Agent 4: TypeScript check | Agent 7: DB state
Agent 2: Integration    | Agent 5: ESLint          | Agent 8: UI rendering
Agent 3: E2E (browsers) | Agent 6: Log check       | Agent 9: API responses
```

### Pattern 6: Divide by Error Pattern

```
Agent 1: Find missing "await" statements
Agent 2: Find sqlite3.Row without dict()
Agent 3: Find sync functions calling async
Agent 4: Find unhandled exceptions
```

---

## Debug Workflow

### Step 1: Reproduce — Identify the Code Path

**ALWAYS ask: Which mode was the user in?**

| User Action | Code Path | Database |
|-------------|-----------|----------|
| Upload to Project | `files.py:upload_file()` | PostgreSQL |
| Upload to Offline Storage | `files.py:_upload_to_local_storage()` | SQLite |
| Register TM (online) | `files.py` → `TMManager` | PostgreSQL |
| Register TM (offline) | `files.py` → `tm_repo.create()` | SQLite |

### Step 2: Check Logs

```bash
tail -50 /tmp/locanext/backend.log                              # Backend
grep "FRONTEND" /tmp/locanext/backend.log | tail -10            # Frontend
cat /tmp/locanext/backend.log | tr -cd '\11\12\15\40-\176' | grep -i "error\|exception" | tail -20  # Errors (binary-safe)
> /tmp/locanext/backend.log                                      # Clear for fresh capture
```

### Step 3: Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `'coroutine' object is not subscriptable` | Missing `await` | Add `await` before async call |
| `'coroutine' object is not iterable` | Missing `await` | Add `await` before async call |
| `coroutine was never awaited` | Missing `await` | Add `await` or use `asyncio.run()` |
| `'sqlite3.Row' has no attribute 'get'` | Row not converted | Use `dict(row)` first |
| `database is locked` | Concurrent access | Kill zombies, reinit DB |

### Step 4: Fix and Test

```bash
# Restart backend
pkill -f "python.*server/main" 2>/dev/null || true
sleep 2
DEV_MODE=true python3 server/main.py > /tmp/locanext/backend.log 2>&1 &
sleep 4

# Test BOTH paths
curl -H "Authorization: Bearer {JWT_TOKEN}" ...              # PostgreSQL path
curl -H "Authorization: Bearer OFFLINE_MODE_test123" ...     # SQLite path
```

### Database Reset

```bash
./scripts/db_manager.sh nuke           # Full nuclear reset
./scripts/db_manager.sh sqlite-reinit  # SQLite only
./scripts/db_manager.sh status -v      # Check status
```

---

## Common Combinations

### Bug Hunting
```
1. gdp-debugger     → Find root cause
2. code-reviewer    → Verify fix correctness
```

### New Feature
```
1. Plan             → Design approach
2. Explore          → Understand existing code
3. general-purpose  → Implement
4. code-reviewer    → Review implementation
```

### Security Review
```
1. security-auditor → OWASP checks (parallel)
2. code-reviewer    → Logic review (parallel)
3. general-purpose  → Fix findings
```

### Frontend Issue
```
1. vite-debugger    → Debug UI/reactivity
2. code-reviewer    → Review Svelte 5 patterns
```

### Backend Issue
```
1. python-debugger  → Debug API/async
2. gdp-debugger     → Trace execution flow
```

### Codebase Understanding
```
1. Explore (x3-6)   → Parallel investigation
2. Plan             → Synthesize findings
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Agent Explosion** | 20+ agents, chaos | Limit to 10, batch if needed |
| **Vague Tasks** | "Look at this file" | Specific question or goal |
| **No Aggregation** | Raw agent dumps | Synthesize before acting |
| **Agent Chaining** | A spawns B spawns C | Main Claude controls all |
| **Duplicate Work** | Multiple agents same task | Clear task boundaries |
| **Sequential for Independent** | Run A → wait → run B → wait | Parallel in one message |
| **Single Agent Multiple Issues** | One agent does BUG-001 through BUG-003 | One agent per bug |
| **Over-Parallelization** | 50 agents for trivial tasks | Match count to complexity |
| **Not Sharing Work** | "I'll review all 20 files myself" | Spawn agents, batch files |

**Quick rules:**
1. Always gdp-debugger for bugs — never guess, always trace
2. Parallel for reads, sequential for writes
3. Plan before complex features — 10 min saves 2 hours
4. Code review after every change
5. Security audit for any endpoint accepting user input

---

## Case Studies

### Case Study 1: Folder Operations Debugging (9 Agents)

**Problem:** Folders not showing correctly, intermittent failures

| Agent | Task | Finding |
|-------|------|---------|
| 1 | Trace error logs | `IntegrityError` on folder creation |
| 2 | Analyze folder_repo.py | Race condition in get_or_create |
| 3 | Check database schema | Foreign key constraint issue |
| 4 | Review recent commits | New validation added without migration |
| 5 | Examine test failures | 3 tests timing-dependent |
| 6 | Check API layer | Missing transaction wrapper |
| 7 | Check WebSocket sync | Clean |
| 8 | Propose fix | Add SELECT FOR UPDATE |
| 9 | Validate fix | Confirmed safe for SQLite and PostgreSQL |

**Result:** Add row-level locking, wrap in transaction, add migration, fix timing tests.

### Case Study 2: Session 60 — aiosqlite Migration (4 Parallel Agents)

**Problem:** File upload and TM registration broken. Initial debugging tested PostgreSQL path (worked), but user was on SQLite path (different code).

**Lesson:** ALWAYS identify which code path the user is on (Online=PostgreSQL, Offline=SQLite).

| Agent | Task | Result |
|-------|------|--------|
| python-debugger | Debug TM | Found 3 bugs in pretranslate.py |
| python-debugger | Debug QA | Clean |
| gdp-debugger | Find all missing await | Routes clean |
| python-debugger | Debug sync/folders | Clean |

**9 bugs found:**
- `files.py:570,1466,1478` — Missing `await` on async calls
- `pretranslate.py:75,508,537` — Sync calling async without bridge
- `tm_repo.py:69-78,100-108,245-248` — `sqlite3.Row.get()` doesn't exist (need `dict(row)`)

### Case Study 3: Schema Mismatch (5-Agent Pipeline)

**Problem:** Frontend and backend schema diverged

```
Agent 1 (Analyze) → 8 mismatches identified
Agent 2 (Discuss) → Backend correct for 5, Frontend for 3
Agent 3 (Conclude) → Migration steps documented
Agent 4 (Document) → Types updated, changelog written
Agent 5 (Fix) → All tests pass, PR ready
```

---

## Invocation Reference

### Basic Agent

```
Task: "Analyze the folder API endpoints"
Agent: code-reviewer
```

### Parallel Batch (one message)

```
Task 1: "Check FolderTree.svelte for bugs"
Task 2: "Check folder.py API routes"
Task 3: "Check folder database queries"
Task 4: "Check WebSocket folder sync"
```

### Agent with GDP Protocol

```
Task: "Debug the folder deletion issue using GDP protocol"
Agent: gdp-debugger
Instructions: |
  1. Follow GRANULAR_DEBUG_PROTOCOL.md
  2. Add microscopic logging
  3. Trace the exact failure point
  4. Report findings with evidence
```

### Chained Agents (Dependencies)

```
Phase 1 (Parallel): Task A: "Analyze" | Task B: "Explore"
Phase 2 (After 1):  Task C: "Synthesize findings from A and B"
Phase 3 (Parallel): Task D: "Document" | Task E: "Fix"
```

---

## Project-Specific Defaults

| Project | Primary Agent | Secondary |
|---------|---------------|-----------|
| LocaNext (main) | general-purpose | vite-debugger, nodejs-debugger |
| QuickSearch | quicksearch-specialist | code-reviewer |
| QACompiler | qacompiler-specialist | code-reviewer |
| MapDataGenerator | mapdatagenerator-specialist | code-reviewer |

---

*Merged 2026-04-04 from 4 source files (1,240 lines → single protocol). Source: AGENT_ORCHESTRATION.md, PARALLEL_AGENT_PROTOCOL.md, DEBUG_AND_SUBAGENTS.md, AGENT_QUICK_REFERENCE.md*
