# Session Context - Last Working State

**Updated:** 2025-12-12 23:50 KST | **By:** Claude

---

## Session Summary: CODE REVIEW - Group H In Progress

### Current Status

**Phase 3 Fix Sprint - Group H (Scale Issues) IN PROGRESS**

6 issues remain OPEN - all affect scalability at 100+ users / 50M+ rows:

| Issue | Problem | Impact |
|-------|---------|--------|
| **DR4-001** | Sync TMManager in async | Server freezes |
| **DR4-002** | Repeated sync pattern | Same as above |
| **DR4-003** | TM O(n) search loop | Timeout at 1M rows |
| **DR4-005** | Backup loads all to RAM | OOM at 50M rows |
| **DR8-001** | Auth disabled on 13 endpoints | Security gap |
| **DR8-002** | New engine per sync call | Connection exhaustion |

### Issue Count

| Status | Count |
|--------|-------|
| **OPEN** | 6 |
| **FIXED** | 29 |
| **ACCEPT** | 30 |
| **DEFER** | 1 |
| **Total** | 66 |

---

## What Was Done This Session

1. **Completed Groups A-G** (29 fixes)
2. **Implemented DEV_MODE** - Localhost auto-auth for testing
3. **Updated Protocol** - Stricter classification rules (v2.3)
4. **Re-classified issues** - 4 moved from ACCEPT to OPEN

---

## Key Protocol Update

**STRICT Classification Rules Added (Protocol v2.3):**

```
OPEN [ ] = ANY issue that:
- Breaks at scale (100+ users, 1M+ rows)
- Blocks event loop in async code
- Uses unbounded memory
- Creates connections outside pool
- Has O(n) where O(1) possible

ACCEPT [~] = ONLY:
- Pure style preference
- Intentional design (documented)
- CLI/script code (not server)
```

**Project goal: 100+ users, 50M+ rows. Issues breaking this = OPEN.**

---

## Next Steps: Fix Group H

### 1. DR4-001/002: Async TMManager (Priority: HIGH)
- Refactor `server/tools/ldm/tm.py` to async
- Update all LDM endpoints using TMManager
- Remove `next(get_db())` hacks

### 2. DR4-003: TM Search Performance
- Replace O(n) Python loop with database FTS
- Or use trigram index / FAISS

### 3. DR4-005: Backup Streaming
- Stream backup instead of loading all to memory
- Use chunked queries

### 4. DR8-002: Connection Pooling
- Use shared engine from `db_setup.py`
- Don't create new engine per call

### 5. DR8-001: Re-enable Auth
- Uncomment `Depends(require_admin)` on 13 endpoints
- DEV_MODE handles localhost testing

---

## Files to Modify

| File | Changes |
|------|---------|
| `server/tools/ldm/tm.py` | Make TMManager async |
| `server/tools/ldm/api.py` | Use async db, fix search |
| `server/api/base_tool_api.py` | Use shared engine |
| `server/api/stats.py` | Re-enable auth (13 places) |

---

## Docs Reference

| Doc | Purpose |
|-----|---------|
| [ISSUES_20251212.md](../code-review/ISSUES_20251212.md) | Full issue list (6 OPEN) |
| [CODE_REVIEW_PROTOCOL.md](../code-review/CODE_REVIEW_PROTOCOL.md) | Protocol v2.3 |

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
