# Code Review Protocol

**Owner:** Development Team

---

## Overview

| Type | Frequency | Duration | Scope |
|------|-----------|----------|-------|
| **Quick Scan** | Weekly | ~1 hour | Automated scans, surface issues |
| **Deep Review** | Bi-weekly | ~4-8 hours | Full manual code review |

**Full codebase review = 6 Deep Review sessions (12 weeks)**

---

## Folder Structure

```
docs/code-review/
├── CODE_REVIEW_PROTOCOL.md       ← This file
├── ISSUES_YYYYMMDD.md            ← Quick scan issues
└── DEEP_REVIEW_[MODULE]_YYYYMMDD.md  ← Deep review per module
```

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

## Deep Review Output Template

Create `DEEP_REVIEW_[MODULE]_YYYYMMDD.md`:

```markdown
# Deep Review: [Module Name]

**Date:** YYYY-MM-DD
**Reviewer:** Claude
**Files Reviewed:** X

## Summary

| Severity | Count |
|----------|-------|
| Critical | X |
| Major | X |
| Minor | X |
| Suggestions | X |

## Findings

### [CRITICAL] filename.py:123 - Description
**Problem:** What's wrong
**Fix:** How to fix

### [MAJOR] filename.py:456 - Description
...

## Action Items
- [ ] Fix critical issues
- [ ] Fix major issues
- [ ] Review minor issues

## Pass 2 Verification
- [ ] All critical fixed
- [ ] All major fixed
- [ ] No regressions
```

---

## Review Schedule

| Week | Date | Type | Module |
|------|------|------|--------|
| 1 | 2025-12-12 | Quick | All (done) |
| 2 | 2025-12-19 | Deep | Database & Models |
| 3 | 2025-12-26 | Quick | - |
| 4 | 2026-01-02 | Deep | Utils & Core |
| ... | ... | ... | ... |

---

## History

| Date | Type | Module | Issues | Fixed | Status |
|------|------|--------|--------|-------|--------|
| 2025-12-12 | Quick | All | 9 | 4 | ✓ Pass 2 Clean |

---

*Protocol v2.0 - Updated 2025-12-12*
