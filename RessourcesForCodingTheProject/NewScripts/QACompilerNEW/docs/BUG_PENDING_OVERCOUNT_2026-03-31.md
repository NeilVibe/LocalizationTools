# BUG: Tracker Pending Overcount (2026-03-31)

## Symptom

Colleague reported: "tracker states way too many pendings, it's not true, I checked myself we have way less."

Debug log showed: **3,010 pending** (grand total 10,768 issues).

## Root Cause — SCREENSHOT Counted as Real Issue Evidence

All masterfiles use the same English header format per user block:
```
TESTER_STATUS_{name} | STATUS_{name} | COMMENT_{name} | MEMO_{name} | SCREENSHOT_{name}
```

The phantom detection logic checks if a tester actually wrote feedback when they
marked `TESTER_STATUS = ISSUE`. If no feedback → phantom → auto-nonissue.

The problem: `SCREENSHOT_{user}` was included alongside `COMMENT_{user}` and
`MEMO_{user}` in the evidence check. A row where the tester ONLY attached a
screenshot but wrote NO comment was treated as a real issue.

**The chain that inflated pending:**

1. Tester marks `TESTER_STATUS = ISSUE`
2. Tester attaches a screenshot but writes NO comment
3. Old code: SCREENSHOT has content → `has_comment = True` → **real issue**
4. Manager STATUS is empty (no comment to respond to, so manager never fills it in)
5. Empty STATUS → classified as **pending**

**Team rule:** Only COMMENT (+ MEMO) count as real issue evidence.
Screenshot alone does NOT make an issue real.

## Fix — 4 Code Paths

The SCREENSHOT-as-evidence bug existed in **4 locations** across 3 files.
All 4 were patched to use `(comment_cols, memo_cols)` instead of
`(comment_cols, memo_cols, screenshot_cols)`:

| # | File | Function | Line |
|---|------|----------|------|
| 1 | `tracker/masterfile_pending.py` | `_read_master_statuses()` | `_COMMENT_PREFIXES` |
| 2 | `core/tracker_update.py` | `aggregate_manager_stats_from_files()` | streaming iter_rows path |
| 3 | `core/tracker_update.py` | `aggregate_manager_stats()` | ws.cell path |
| 4 | `core/compiler.py` | `collect_all_master_data()` | compilation path |

Two other paths in `core/processing.py` already only checked COMMENT — no fix needed.

## Additional Changes

- **Phantom logging:** All 4 paths now log phantom counts per sheet for debugging
- **Positional fallback:** `masterfile_pending.py` gained positional comment column
  detection as safety net (uses block structure STATUS+1/+2 when named headers not found)

## How to Verify

Run the standalone debug:
```
python tracker/masterfile_pending.py --use-main
```

Check `logs/MASTERFILE_PENDING_DEBUG.log`:
- PHANTOM ISSUES counts should increase (screenshot-only rows now caught)
- Grand total pending should drop significantly from 3,010

## History

- **v2.6 (2026-03-26):** Introduced phantom detection. Dropped pending 3,728 → 1,452.
  But SCREENSHOT was included in the evidence check, leaving screenshot-only phantom
  rows uncaught. The 1,452 figure was still partially inflated by this.
- **v2.6.1 (2026-03-31):** Removed SCREENSHOT from evidence. Fixed all 4 code paths.
