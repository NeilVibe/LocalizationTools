# Code Review Protocol

**Owner:** Development Team | **Version:** 2.1

---

## Overview

| Type | Frequency | Duration | Scope |
|------|-----------|----------|-------|
| **Quick Scan** | Weekly | ~1 hour | Automated scans, surface issues |
| **Deep Review** | Bi-weekly | ~2-4 hours | Full manual code review |

**Full codebase review = 16 Deep Review sessions**

---

## Critical Rule: REVIEW ALL FIRST, FIX LATER

```
┌─────────────────────────────────────────────────────────────────┐
│  DO NOT FIX ISSUES DURING REVIEW SESSIONS                       │
│                                                                 │
│  Phase 1: Complete ALL 12 sessions (review only, document)     │
│  Phase 2: Consolidate findings, prioritize across codebase     │
│  Phase 3: Fix in batches by type/priority                      │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Approach?

1. **Full Picture First**
   - Same issue may appear in multiple sessions (e.g., JSON→JSONB)
   - Batch fixes are more efficient than one-off patches

2. **Better Prioritization**
   - After 12 sessions: "50 issues total, 5 HIGH, 20 MEDIUM, 25 LOW"
   - Can prioritize by actual impact across entire codebase

3. **No Context Loss**
   - Related issues fixed together
   - Single migration script vs 12 separate ones

4. **Working System**
   - Issues are technical debt, not blocking bugs
   - System works fine during review phase

### Exception: Fix Immediately ONLY If

| Condition | Example |
|-----------|---------|
| **Security vulnerability** | SQL injection, exposed secrets |
| **Data corruption risk** | Silent data loss, race condition |
| **Blocking bug** | App crashes, feature broken |

If none of these apply → **DOCUMENT ONLY, DO NOT FIX**

---

## STRICT Issue Classification Rules

**FIX EVERYTHING. NO EXCUSES. NO DEFER.**

### What is OPEN [ ]
```
ANY issue that:
- Breaks at scale (100+ users, 1M+ rows)
- Blocks event loop in async code
- Uses unbounded memory (loads all to RAM)
- Creates new connections instead of using pool
- Disables security features
- Has O(n) or worse where O(1) is possible

ALL OPEN ISSUES MUST BE FIXED. No exceptions.
```

### What is FIXED [x]
```
Issue resolved with actual code changes.
Must be tested and verified working.
```

### What is ACCEPT [~]
```
ONLY these qualify (truly not issues):
- Pure style preference (naming, formatting)
- Intentional design choice (documented)
- CLI/script code (not server code)
- Placeholder for planned feature (documented TODO)

If it affects production at scale → NOT ACCEPT
```

### DEFER IS NOT ALLOWED [-]
```
❌ DEFER IS REMOVED FROM THIS PROTOCOL

Previous excuses that are NO LONGER VALID:
- "Too much work" → Do the work
- "Operations are fast" → Still blocks, still fix
- "Requires refactor" → Do the refactor
- "2-3 hours of work" → Spend the 2-3 hours

If an issue breaks at scale, FIX IT.
No task files. No "later". No excuses.
```

### Common Mistakes (DON'T DO THIS)
```
❌ "Works fine now" → Still breaks at scale, FIX IT
❌ "Quick operations" → Still blocks async, FIX IT
❌ "Acceptable for internal tool" → We target 100+ users, FIX IT
❌ "Minor tech debt" → If it affects scale, FIX IT
❌ "Too much work" → DO THE WORK
❌ "Created a task file" → THAT'S NOT FIXING IT
```

**RULE: Code review is not complete until ALL issues are FIXED or ACCEPT.**

Project goal: 100+ concurrent users, 50M+ rows.
Any issue that breaks this = MUST BE FIXED.

---

## Per-Session Workflow

### Step 1: Read Files
```bash
# Read all files for the session
# Use Read tool or cat
```

### Step 2: Review Using Checklist
- Use the per-file checklist (see below)
- Note issues with file:line references
- Categorize: HIGH / MEDIUM / LOW

### Step 3: Add to Issue List
```
docs/code-review/ISSUES_YYYYMMDD.md
```

Add new section for this session:
- Session header with files reviewed (LOC)
- Issues found (with severity, file:line)
- **DO NOT FIX - just document**

### Step 4: Update Tracking
- Update `CODE_REVIEW_PROTOCOL.md` history table
- Update `SESSION_CONTEXT.md`
- Update `Roadmap.md` session status

### Step 5: Move to Next Session
- **DO NOT FIX** issues from this session
- Proceed to next session
- Repeat until Session 12 complete

---

## Folder Structure

```
docs/code-review/
├── CODE_REVIEW_PROTOCOL.md       ← This file (protocol)
├── ISSUES_YYYYMMDD.md            ← ONE active issue list (all issues)
│
└── history/                      ← Archived when complete
    └── ISSUES_YYYYMMDD.md        ← Old completed issue lists
```

**Rules:**
- ONE issue list at a time
- Quick scan + Deep review sessions = same file
- DateTime in filename = creation date
- When all fixed → move to `history/`

---

# PART 1: QUICK SCAN (Weekly)

Fast automated checks + immediate fixes.

## Process

### Step 1: Run Scans
```bash
cd /home/neil1988/LocalizationTools

# Duplicates
grep -rhn "^def \|^async def " server/ --include="*.py" | \
  sed 's/.*def //' | sed 's/(.*$//' | sort | uniq -c | sort -rn | head -10

# TODO/FIXME
grep -rn "TODO\|FIXME" server/ --include="*.py" | wc -l

# print() statements
grep -rn "print(" server/ --include="*.py" | wc -l

# console.log
grep -rn "console.log" locaNext/src/ --include="*.svelte" | wc -l

# Large files
find server/ -name "*.py" -exec wc -l {} \; | awk '$1 > 500' | sort -rn
```

### Step 2: Create ISSUES_YYYYMMDD.md
### Step 3: Fix issues
### Step 4: Pass 2 - Re-run scans to verify
### Step 5: Commit

---

# PART 2: DEEP REVIEW (Bi-weekly)

Full manual code review. **One module per session.**

---

## Module Order (Most Logical Flow)

Review in dependency order - bottom-up, so foundations are solid before reviewing code that depends on them.

| Session | Module | Why This Order |
|---------|--------|----------------|
| **1** | **Database & Models** | Foundation - everything depends on this |
| **2** | **Utils & Core** | Shared utilities used everywhere |
| **3** | **Auth & Security** | Critical - must be solid |
| **4** | **LDM Backend** | Main app #4, most complex |
| **5** | **XLSTransfer** | Tool #1 |
| **6** | **QuickSearch** | Tool #2 |
| **7** | **KR Similar** | Tool #3 |
| **8** | **API Layer** | All endpoints, ties everything together |
| **9** | **Frontend - Core** | Svelte components, stores |
| **10** | **Frontend - LDM** | LDM UI components |
| **11** | **Admin Dashboard** | Admin UI |
| **12** | **Scripts & Config** | Build, deploy scripts |
| **13** | **CI/CD Workflows** | GitHub + Gitea automation |
| **14** | **Tests** | Test quality and coverage |
| **15** | **Electron/Desktop** | Desktop app security |
| **16** | **Installer** | Distribution packages |

---

## Session 1: Database & Models

**Files:**
```
server/database/
├── __init__.py
├── db_setup.py
├── db_utils.py
└── models.py

server/config.py
```

**Review Focus:**
- [ ] Models complete and correct?
- [ ] Relationships defined properly?
- [ ] Indexes on frequently queried columns?
- [ ] No N+1 query patterns in utils?
- [ ] Connection pooling configured?
- [ ] Migrations strategy?

---

## Session 2: Utils & Core

**Files:**
```
server/utils/
├── __init__.py
├── cache.py
├── dependencies.py
├── progress_tracker.py
├── text_utils.py
├── websocket.py
└── client/
    ├── file_handler.py
    ├── logger.py
    └── progress.py
```

**Review Focus:**
- [ ] Factor Power - no duplicates?
- [ ] Each util has single responsibility?
- [ ] Error handling consistent?
- [ ] Logging consistent?
- [ ] WebSocket thread-safe?

---

## Session 3: Auth & Security

**Files:**
```
server/api/auth.py
server/api/auth_async.py
server/utils/dependencies.py (auth parts)
```

**Review Focus:**
- [ ] Password hashing secure? (bcrypt)
- [ ] JWT implementation correct?
- [ ] Token expiration handled?
- [ ] Rate limiting?
- [ ] No secrets in code?
- [ ] All endpoints require auth?
- [ ] CORS configured correctly?

---

## Session 4: LDM Backend

**Files:**
```
server/tools/ldm/
├── __init__.py
├── api.py (1300+ lines - main focus)
├── tm.py
├── tm_indexer.py
├── websocket.py
└── file_handlers/
    ├── txt_handler.py
    └── xml_handler.py
```

**Review Focus:**
- [ ] File parsing robust? (encoding, malformed)
- [ ] Row locking for multi-user?
- [ ] TM search tiers correct?
- [ ] WebSocket events complete?
- [ ] Large file handling? (memory)
- [ ] Export formats correct?

---

## Session 5: XLSTransfer

**Files:**
```
server/tools/xlstransfer/
├── __init__.py
├── config.py
├── core.py
├── embeddings.py
├── translation.py
├── process_operation.py
├── excel_utils.py
└── cli/

server/api/xlstransfer_async.py
```

**Review Focus:**
- [ ] Matches original XLSTransfer0225.py exactly?
- [ ] Embedding generation efficient?
- [ ] FAISS index handling correct?
- [ ] Excel read/write preserves formatting?
- [ ] Progress tracking complete?

---

## Session 6: QuickSearch

**Files:**
```
server/tools/quicksearch/
├── __init__.py
├── parser.py
├── searcher.py
└── api.py
```

**Review Focus:**
- [ ] Matches original QuickSearch0818.py?
- [ ] Split vs whole mode correct?
- [ ] Search ranking accurate?
- [ ] StringID handling correct?

---

## Session 7: KR Similar

**Files:**
```
server/tools/kr_similar/
├── __init__.py
├── core.py
├── embeddings.py
└── searcher.py

server/api/kr_similar_async.py
```

**Review Focus:**
- [ ] Matches original KRSIMILAR0124.py?
- [ ] Korean text normalization correct?
- [ ] Similarity threshold logic?
- [ ] Auto-translate structure adaptation?

---

## Session 8: API Layer

**Files:**
```
server/api/
├── __init__.py
├── stats.py
├── updates.py
├── progress_operations.py
└── (already reviewed: auth, xlstransfer, kr_similar)

server/main.py
```

**Review Focus:**
- [ ] All endpoints have auth?
- [ ] Input validation on all endpoints?
- [ ] Error responses consistent?
- [ ] OpenAPI docs accurate?
- [ ] Rate limiting where needed?

---

## Session 9: Frontend - Core

**Files:**
```
locaNext/src/
├── App.svelte
├── lib/
│   ├── stores/
│   ├── services/
│   └── utils/
└── routes/
```

**Review Focus:**
- [ ] Store management clean?
- [ ] API calls centralized?
- [ ] Error handling in UI?
- [ ] Loading states?
- [ ] Reactive statements correct?

---

## Session 10: Frontend - LDM

**Files:**
```
locaNext/src/lib/components/ldm/
├── ProjectExplorer.svelte
├── FileExplorer.svelte
├── EditorPanel.svelte
├── TranslationGrid.svelte
└── ...
```

**Review Focus:**
- [ ] Grid performance with large files?
- [ ] Real-time sync working?
- [ ] Edit conflicts handled?
- [ ] Keyboard shortcuts?
- [ ] Accessibility?

---

## Session 11: Admin Dashboard

**Files:**
```
adminDashboard/src/
├── App.svelte
├── lib/
│   ├── components/
│   └── services/
└── routes/
```

**Review Focus:**
- [ ] Admin-only access enforced?
- [ ] User management complete?
- [ ] Stats accurate?
- [ ] Logs accessible?

---

## Session 12: Scripts & Config

**Files:**
```
scripts/
├── start_all_servers.sh
├── stop_all_servers.sh
├── check_servers.sh
└── ...

package.json, requirements.txt
Dockerfile, docker-compose.yml
```

**Review Focus:**
- [ ] Scripts idempotent?
- [ ] Dependencies pinned?
- [ ] Docker build works?
- [ ] Environment configs correct?

---

## Session 13: CI/CD Workflows (ADDED 2025-12-13)

**Files:**
```
.gitea/workflows/build.yml
.github/workflows/build-electron.yml
```

**Review Focus:**
- [ ] Job dependencies correct? (tests before build)
- [ ] Environment variables at correct level? (job vs step)
- [ ] Secrets handled securely?
- [ ] Both workflows in sync? (Gitea and GitHub)
- [ ] Test coverage complete? (no unintended skips)
- [ ] Server stays running during tests?
- [ ] Admin user created for integration tests?
- [ ] Model-dependent tests properly deselected?

**CI/CD Gotchas Learned:**
```
1. Gitea host mode ≠ Docker mode
   - services: block doesn't work in host mode
   - Must use PostgreSQL installed on host

2. Environment variables
   - Job-level env may not propagate to all steps
   - Always set step-level env for critical vars

3. pytest module-level skipif
   - Evaluates at import time, not runtime
   - Server must be running BEFORE pytest starts

4. Workflow sync
   - Keep Gitea and GitHub workflows in sync
   - Same fixes needed in both places
```

---

## Session 13B: CI/CD Infrastructure (ADDED 2025-12-15)

**CRITICAL: This is DIFFERENT from Session 13 (workflow files)**

Session 13 reviews `.yml` workflow files.
Session 13B reviews INFRASTRUCTURE that runs workflows.

**Why separate?** The 706% CPU incident (2025-12-14) was NOT caught by workflow review because the bug was in systemd service configuration, not workflow files.

**Locations to check:**
```bash
# Linux systemd services
/etc/systemd/system/gitea*.service
/etc/systemd/system/*runner*.service

# Linux runner files
~/gitea/*.sh
~/gitea/config.yaml
~/gitea/.runner

# Windows runner
C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\
```

**Review Focus:**

### Linux Services (DANGER ZONE)
- [ ] **NO `Restart=always` without limits** ← 706% CPU ROOT CAUSE
- [ ] `StartLimitBurst` + `StartLimitIntervalSec` set?
- [ ] Service dependencies correct? (`Requires=`, `After=`)
- [ ] `PartOf=` used for dependent services?
- [ ] Resource limits set? (`CPUQuota`, `MemoryMax`)

### Runner Configuration
- [ ] Only ONE runner per platform registered?
- [ ] Polling interval reasonable? (not < 5s)
- [ ] Token expiration handled?
- [ ] Non-ephemeral mode for stability?

### Commands to Run:
```bash
# Check for dangerous Restart=always
grep -r "Restart=always" /etc/systemd/system/ 2>/dev/null

# Check registered runners
systemctl list-units | grep -iE "gitea|runner"

# Check restart limits exist
grep -r "StartLimitBurst" /etc/systemd/system/gitea*.service 2>/dev/null

# Check service dependencies
systemctl show gitea-runner.service --property=Requires,After 2>/dev/null

# Check restart count
systemctl show gitea-runner.service --property=NRestarts 2>/dev/null
```

### Safe systemd Template (REFERENCE)
```ini
[Unit]
Description=Gitea Actions Runner
After=gitea.service network.target
Requires=gitea.service
PartOf=gitea.service

[Service]
Type=simple
User=neil1988
WorkingDirectory=/home/neil1988/gitea
ExecStart=/home/neil1988/gitea/act_runner daemon
Restart=on-failure          # NOT "always"
RestartSec=30               # 30 second cooldown
StartLimitBurst=3           # Max 3 restarts...
StartLimitIntervalSec=300   # ...in 5 minutes
CPUQuota=100%
MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

**Full guide:** [docs/cicd/RUNNER_SERVICE_SETUP.md](../cicd/RUNNER_SERVICE_SETUP.md)

### Incident Log
| Date | Issue | Root Cause | Prevention |
|------|-------|------------|------------|
| 2025-12-14 | 706% CPU (506 restarts) | `Restart=always` + no limits | Add `StartLimitBurst=3` |

---

## Session 14: Tests (ADDED 2025-12-13)

**Files:**
```
tests/
├── unit/
├── api/
├── e2e/
└── conftest.py
```

**Review Focus:**
- [ ] Skip conditions legitimate?
- [ ] Test coverage adequate?
- [ ] Fixtures properly shared?
- [ ] No hardcoded values?
- [ ] Archive tests excluded?

---

## Session 15: Electron/Desktop (ADDED 2025-12-13)

**Files:**
```
locaNext/electron/
├── main.js
├── preload.js
└── ...
```

**Review Focus (SECURITY CRITICAL):**
- [ ] contextIsolation: true?
- [ ] nodeIntegration: false?
- [ ] No remote module usage?
- [ ] IPC channels validated?
- [ ] File system access restricted?
- [ ] Auto-updater signed?

---

## Session 16: Installer (ADDED 2025-12-13)

**Files:**
```
installer/
├── locanext_electron.iss
├── locanext_light.iss
└── ...
```

**Review Focus:**
- [ ] All required files included?
- [ ] Uninstaller complete?
- [ ] Registry entries correct?
- [ ] Embedded Python packages complete?

---

## Per-File Checklist (Use for Every File)

### Quality
- [ ] Clear names?
- [ ] Functions < 50 lines?
- [ ] No dead code?
- [ ] No magic numbers?

### Logic
- [ ] Edge cases? (null, empty, invalid)
- [ ] Off-by-one errors?
- [ ] Race conditions?

### Errors
- [ ] Exceptions caught?
- [ ] Logged?
- [ ] User-friendly messages?

### Security
- [ ] Input validated?
- [ ] SQL safe?
- [ ] No secrets?

### Architecture
- [ ] Single responsibility?
- [ ] Factor Power? (no duplicates)
- [ ] Right layer?

---

## Issue Entry Format

Add to `ISSUES_YYYYMMDD.md` under the session section:

```markdown
## Deep Review Session N: [Module Name]

**Files:** `path/to/files/` (X files, Y LOC)

### [ ] DR{N}-001: Short Title
**Priority:** HIGH/MEDIUM/LOW | **File:** `path/file.py:123`
**Issue:** What's wrong
**Fix:** How to fix

### [~] DR{N}-002: Another Issue
**Priority:** LOW | **File:** `path/file.py:456`
**Accept:** Why this is acceptable
```

**Status markers:**
- `[ ]` OPEN - needs fixing
- `[x]` FIXED - resolved
- `[~]` ACCEPT - not a real issue
- `[-]` DEFER - postponed

---

## Review Schedule

### Phase 1: Review (Current)

| Session | Module | Status | Issues |
|---------|--------|--------|--------|
| 1 | Database & Models | ✅ Done | 8 |
| 2 | Utils & Core | ✅ Done | 8 |
| 3 | Auth & Security | ✅ Done | 9 (1H!) |
| 4 | LDM Backend | ✅ Done | 8 |
| 5 | XLSTransfer | ✅ Done | 5 |
| 6 | QuickSearch | ✅ Done | 4 |
| 7 | KR Similar | ✅ Done | 3 |
| 8 | API Layer | ✅ Done | 3 |
| 9 | Frontend Core | ✅ Done | 2 |
| 10 | Frontend LDM | ✅ Done | 3 |
| 11 | Admin Dashboard | ✅ Done | 2 |
| 12 | Scripts & Config | ✅ Done | 2 |

**All issues go to:** [ISSUES_20251212.md](ISSUES_20251212.md)

### Phase 2: Consolidation ✅ COMPLETE

**Document:** [CONSOLIDATED_ISSUES.md](CONSOLIDATED_ISSUES.md)

31 open issues grouped into 7 categories:

| Group | Issues | Priority |
|-------|--------|----------|
| A. Hardcoded URLs | 4 | MEDIUM |
| B. Database/SQL | 6 | MEDIUM |
| C. Async/Sync Mixing | 5 | MEDIUM |
| D. Auth Refactor | 5 | MEDIUM |
| E. Code Bugs | 8 | MEDIUM |
| F. Performance | 2 | DEFER |
| G. DEV_MODE Feature | 1 | MEDIUM |

### Phase 3: Fix Sprint

```
Week N:   Consolidation + prioritization
Week N+1: Fix HIGH priority issues
Week N+2: Fix MEDIUM priority issues
Week N+3: Fix LOW priority issues (if time)
Week N+4: Verification pass
```

**Fix Sprint Rules:**
- One commit per issue group (not per issue)
- Run tests after each commit
- Update issue status in reports
- Final verification: re-run all scans

---

## History

| Date | Type | Session | Issues | Status |
|------|------|---------|--------|--------|
| 2025-12-12 | Quick | Week 1 | 9 | ✅ 4 fixed, 4 acceptable, 1 deferred |
| 2025-12-12 | Deep | Session 1 | 8 | ✅ Documented (no fixes yet) |
| 2025-12-12 | Deep | Session 2 | 8 | ✅ Documented (no fixes yet) |
| 2025-12-12 | Deep | Session 3 | 9 | ⚠️ 1 HIGH (fixed) |
| 2025-12-12 | Deep | Session 4 | 8 | ✅ Documented |
| 2025-12-12 | Deep | Session 5 | 5 | ✅ Documented |
| 2025-12-12 | Deep | Session 6 | 4 | ✅ Documented |
| 2025-12-12 | Deep | Session 7 | 3 | ✅ Documented |
| 2025-12-12 | Deep | Session 8 | 3 | ✅ Documented |
| 2025-12-12 | Deep | Session 9 | 2 | ✅ Clean |
| 2025-12-12 | Deep | Session 10 | 3 | ✅ Documented |
| 2025-12-12 | Deep | Session 11 | 2 | ✅ Clean |
| 2025-12-12 | Deep | Session 12 | 2 | ✅ Clean |
| 2025-12-12 | Phase 2 | Consolidation | - | ✅ 31 issues grouped |
| 2025-12-12 | Phase 3 | Fix Sprint | - | ✅ 29 fixed, 34 accept, 2 open, 1 defer |

---

## Review Cycle 1: CLOSED ✅

**Date:** 2025-12-12 to 2025-12-13
**ID:** ISSUES_20251212
**Result:** 66 issues → 36 fixed, 30 acceptable, 0 deferred, 0 open
**PASS 2 Verified:** Yes

### Key Fixes Made
- **DEV_MODE feature** - Localhost auto-auth for testing
- **JSONB migration** - All JSON columns updated + migration script
- **Auth hardening** - Rate limiting, audit logging, deprecation warning
- **Hardcoded URLs** - Now use config
- **Code bugs** - Missing imports, lxml guards, etc.
- **Async/Sync patterns** - All TM endpoints + main.py now async
- **Scale optimizations** - pg_trgm search, chunked queries, shared engine

### Archive
Issue file archived to `docs/code-review/history/ISSUES_20251212.md`

---

## Code Review Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  PASS 1: Initial Review + Fix                                   │
│  - Quick Scan (automated scans)                                 │
│  - Deep Review (all 12 sessions, document only)                 │
│  - Consolidate findings                                         │
│  - Fix all issues (NO DEFER)                                    │
├─────────────────────────────────────────────────────────────────┤
│  PASS 2: Full Verification (SAME AS PASS 1)                     │
│  - Quick Scan (automated scans again)                           │
│  - Deep Review (all 12 sessions again)                          │
│  - Verify fixes are correct                                     │
│  - Verify no new issues introduced                              │
│  - Fix any new issues found                                     │
│  - Confirm 0 OPEN issues remain                                 │
├─────────────────────────────────────────────────────────────────┤
│  CLOSE: Archive                                                 │
│  - Only after PASS 2 confirms 100% clean                        │
│  - Move ISSUES_YYYYMMDD.md to history/                          │
│  - Code review ID = datetime (unique identifier)                │
└─────────────────────────────────────────────────────────────────┘
```

### CRITICAL: PASS 2 is a FULL review, not a quick check

```
PASS 2 = PASS 1 (full process repeated)

❌ WRONG: "Just run scans and spot-check"
✅ RIGHT: "Full 12-session deep review again"

Purpose of PASS 2:
1. Verify all fixes are actually correct
2. Catch issues introduced by fixes
3. Re-validate all ACCEPT decisions
4. Ensure 100% confidence before CLOSE
```

### ACCEPT Criteria (Strict)

```
ACCEPT [~] means:
- Fixing it would provide ZERO benefit
- Not "too hard" or "too much work"
- Not "works fine for now"
- Genuinely not an issue

Ask: "Would fixing this EVER make the code better?"
- If YES → FIX IT (not ACCEPT)
- If NO → ACCEPT (truly not an issue)
```

### When PASS 2 Complete
- All 12 sessions reviewed
- All scans pass
- 0 OPEN issues
- All ACCEPT decisions re-validated
- Update issue file status to CLOSED
- Move to `docs/code-review/history/`
- Update history/README.md with summary

---

## Retention Policy

```
┌─────────────────────────────────────────────────────────────────┐
│  RETENTION: 6 MONTHS                                            │
│                                                                 │
│  - Keep closed review files for 6 months                        │
│  - After 6 months: DELETE the issue file                        │
│  - Update history/README.md to keep summary line                │
│  - Summary stays forever, details get deleted                   │
│                                                                 │
│  Why: Prevents bloat, summaries capture key info                │
└─────────────────────────────────────────────────────────────────┘
```

### Cleanup Checklist (Every 6 Months)

```bash
# 1. Find old reviews
find docs/code-review/history -name "ISSUES_*.md" -mtime +180

# 2. Delete old files (keep README.md!)
rm docs/code-review/history/ISSUES_YYYYMMDD.md

# 3. Verify summary still in README.md
# The one-liner summary row should remain

# 4. Record cleanup date
# Update "Last cleanup" in history/README.md
```

---

*Protocol v3.0 - Updated 2025-12-13 (Added Sessions 13-16: CI/CD, Tests, Electron, Installer)*
