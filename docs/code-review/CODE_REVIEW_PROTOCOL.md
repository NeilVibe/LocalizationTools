# Code Review Protocol

**Owner:** Development Team | **Version:** 2.1

---

## Overview

| Type | Frequency | Duration | Scope |
|------|-----------|----------|-------|
| **Quick Scan** | Weekly | ~1 hour | Automated scans, surface issues |
| **Deep Review** | Bi-weekly | ~2-4 hours | Full manual code review |

**Full codebase review = 12 Deep Review sessions**

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
| **12** | **Scripts & Config** | Build, deploy, CI/CD |

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

.github/workflows/
package.json, requirements.txt
Dockerfile, docker-compose.yml
```

**Review Focus:**
- [ ] Scripts idempotent?
- [ ] CI/CD complete?
- [ ] Dependencies pinned?
- [ ] Docker build works?
- [ ] Environment configs correct?

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

## Review Cycle 1: COMPLETE ✅

**Date:** 2025-12-12
**Result:** 66 issues → 29 fixed, 34 acceptable, 2 deferred (performance), 1 deferred (future)

### Key Fixes Made
- **DEV_MODE feature** - Localhost auto-auth for testing
- **JSONB migration** - All JSON columns updated + migration script
- **Auth hardening** - Rate limiting, audit logging, deprecation warning
- **Hardcoded URLs** - Now use config
- **Code bugs** - Missing imports, lxml guards, etc.

### Still Open (2 issues)
- DR4-001/DR4-002: Sync calls in async context (TMManager) - requires architecture refactor

### Archive
When starting next cycle, move `ISSUES_20251212.md` to `docs/code-review/history/`

---

## Next Review Cycle (PASS 2)

**When:** After significant new code or every 2-4 weeks

### What to Review
1. **New code since last review** - Any new files/features
2. **Modified files** - Check if fixes introduced new issues
3. **Deferred items** - Re-evaluate DR4-001/DR4-002
4. **Fresh scan** - Run Quick Scan commands again

### How to Start
```bash
# Create new issue file
touch docs/code-review/ISSUES_YYYYMMDD.md

# Archive old one
mv docs/code-review/ISSUES_20251212.md docs/code-review/history/
```

---

*Protocol v2.2 - Updated 2025-12-12 (Cycle 1 Complete)*
