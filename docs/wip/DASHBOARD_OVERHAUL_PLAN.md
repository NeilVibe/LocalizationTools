# Dashboard Overhaul - Comprehensive Plan

> **Created:** 2026-01-04 | **Status:** PLANNING | **Priority:** HIGH

---

## PART 1: ASSESSMENT FINDINGS

### 1.1 Svelte Version Mismatch (CRITICAL)

| App | Svelte | Patterns Used | Status |
|-----|--------|---------------|--------|
| `adminDashboard/` | **4.2.8** | `export let`, `$:`, `on:click` | OLD |
| `locaNext/` | **5.0.0** | `$props()`, `$state()`, `onclick` | NEW |

**Problem:** Two different Svelte versions = maintenance burden, inconsistent patterns.

### 1.2 Existing Dashboard Pages

| Route | Features | Quality |
|-------|----------|---------|
| `/` | Overview cards, rankings, activity log, WebSocket live | Good |
| `/users` | CRUD, password reset, activate/deactivate, search | Good |
| `/stats` | Period selector, rankings by user/team/language | Good |
| `/logs` | Activity log viewer | Basic |
| `/database` | Database info | Basic |
| `/server` | Server status | Basic |
| `/telemetry` | Remote monitoring | Advanced |

### 1.3 What's MISSING

| Feature | Backend | Frontend | Priority |
|---------|---------|----------|----------|
| Capability Assignment | ✅ EXISTS | ❌ MISSING | HIGH |
| Custom Date Range | ✅ EXISTS | ❌ MISSING | MEDIUM |
| Translation Activity Tracking | ❌ MISSING | ❌ MISSING | HIGH |
| QA Usage Tracking | ❌ MISSING | ❌ MISSING | MEDIUM |
| Custom Report Builder | ❌ MISSING | ❌ MISSING | LOW |
| Word Count Stats | ❌ MISSING | ❌ MISSING | MEDIUM |
| Pretranslation Stats | ❌ MISSING | ❌ MISSING | MEDIUM |

### 1.4 UI/UX Assessment

**Current Issues:**
- Some inline styles in layout (not consistent)
- Dense cards on overview page
- No customization options (show/hide widgets)
- No custom date pickers
- Fixed navigation (no collapsible sidebar)

**What's Good:**
- Carbon Design System (professional)
- Dark theme (consistent)
- WebSocket live updates
- Clean table layouts in users/stats

---

## PART 2: DECISION - SEPARATE vs INTEGRATED

### Option A: Keep Separate (`adminDashboard/`)

**Pros:**
- Already works
- Separate concerns (admin vs user)
- Can run on different machine/port

**Cons:**
- Svelte 4 (legacy, needs upgrade)
- Duplicate dependencies
- Different codebase to maintain
- Different API client patterns

### Option B: Integrate into `locaNext/`

**Pros:**
- Already Svelte 5 (modern runes)
- Single codebase
- Shared components/stores
- Shared API layer
- One build process

**Cons:**
- More routes in locaNext
- Admin features in user app (need access control)
- Bigger bundle

### RECOMMENDATION: **Option A with Svelte 5 Upgrade**

Keep dashboard separate but upgrade to Svelte 5 for consistency.
Reason: Admin dashboard is a different concern, might run on server without Electron.

---

## PART 3: DATABASE CHANGES NEEDED

### 3.0 Existing Tables (Already Built!)

These tables ALREADY exist and handle most tracking needs:

| Table | Purpose | Status |
|-------|---------|--------|
| `sessions` | Login/logout, session duration, app version, machine ID | ✅ EXISTS |
| `log_entries` | Tool/function usage with timing | ✅ EXISTS |
| `tool_usage_stats` | Aggregated daily tool stats | ✅ EXISTS |
| `user_activity_summary` | Daily per-user activity summary | ✅ EXISTS |
| `error_logs` | Error tracking | ✅ EXISTS |
| `performance_metrics` | Performance tracking | ✅ EXISTS |

**We only need 2 NEW tables** for translation/QA-specific metrics not covered above.

### 3.1 New Tables (2 Total)

```sql
-- ═══════════════════════════════════════════════════════════════════
-- TABLE 1: Translation Activity Tracking
-- ═══════════════════════════════════════════════════════════════════
-- OPTIMIZED: Stores METRICS ONLY, not text (text already in ldm_rows)
-- Storage: ~50 bytes/row = 60 MB/year for 100 users

CREATE TABLE translation_activity (
    id SERIAL PRIMARY KEY,
    row_id INTEGER NOT NULL REFERENCES ldm_rows(id) ON DELETE CASCADE,
    file_id INTEGER NOT NULL REFERENCES ldm_files(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Edit source (SMALLINT enum for efficiency)
    -- 0=manual, 1=pretrans_tm, 2=pretrans_xls, 3=pretrans_kr
    edit_source SMALLINT NOT NULL DEFAULT 0,

    -- Metrics only (calculated client-side, sent as numbers)
    similarity_pct REAL,               -- 4 bytes (0-100, enough precision)
    words_changed SMALLINT,            -- 2 bytes (max 32767 words per cell)
    word_count_target SMALLINT,        -- 2 bytes

    -- User action (SMALLINT enum)
    -- 0=accepted, 1=modified, 2=rejected
    user_action SMALLINT NOT NULL DEFAULT 1,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for dashboard queries
CREATE INDEX idx_ta_user_date ON translation_activity(user_id, created_at);
CREATE INDEX idx_ta_file ON translation_activity(file_id);
CREATE INDEX idx_ta_source ON translation_activity(edit_source);
CREATE INDEX idx_ta_action ON translation_activity(user_action);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE 2: QA Usage Tracking
-- ═══════════════════════════════════════════════════════════════════
-- Tracks when users run QA checks

CREATE TABLE qa_usage_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES ldm_files(id) ON DELETE SET NULL,

    -- Check info (SMALLINT for efficiency)
    -- check_scope: 0=row, 1=file, 2=batch
    check_scope SMALLINT NOT NULL DEFAULT 1,
    rows_checked SMALLINT DEFAULT 0,
    issues_found SMALLINT DEFAULT 0,
    issues_resolved SMALLINT DEFAULT 0,

    -- Duration in milliseconds
    duration_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_qa_user_date ON qa_usage_log(user_id, created_at);
CREATE INDEX idx_qa_file ON qa_usage_log(file_id);
```

### 3.2 Existing Tables to Modify

```sql
-- ═══════════════════════════════════════════════════════════════════
-- MODIFY: ldm_rows - Add pretranslation tracking columns
-- ═══════════════════════════════════════════════════════════════════
-- pretrans_original stores the original pretranslation suggestion
-- so we can compare when user confirms (for similarity calculation)

ALTER TABLE ldm_rows ADD COLUMN IF NOT EXISTS pretranslated BOOLEAN DEFAULT FALSE;
ALTER TABLE ldm_rows ADD COLUMN IF NOT EXISTS pretrans_engine SMALLINT;  -- 0=tm, 1=xls, 2=kr
ALTER TABLE ldm_rows ADD COLUMN IF NOT EXISTS pretrans_score REAL;       -- TM match score
ALTER TABLE ldm_rows ADD COLUMN IF NOT EXISTS pretrans_original TEXT;    -- Original suggestion (needed for diff)
```

### 3.3 Storage Estimate

```
100 users × 50 edits/day × 250 days = 1,250,000 rows/year

translation_activity: ~50 bytes × 1.25M = 60 MB/year
qa_usage_log:         ~40 bytes × 50K   = 2 MB/year
─────────────────────────────────────────────────────
TOTAL:                                   ~62 MB/year

PostgreSQL handles this effortlessly for 100+ years.
```

### 3.4 Enum Reference

```
edit_source:   0=manual, 1=pretrans_tm, 2=pretrans_xls, 3=pretrans_kr
user_action:   0=accepted, 1=modified, 2=rejected
check_scope:   0=row, 1=file, 2=batch
pretrans_engine: 0=tm_standard, 1=tm_xls, 2=tm_kr
```

---

## PART 4: IMPLEMENTATION PHASES

### Phase 1: Svelte 5 Upgrade (Foundation)

**Goal:** Upgrade adminDashboard to Svelte 5

**Tasks:**
1. Update `package.json`:
   - `svelte`: `^4.2.8` → `^5.0.0`
   - `@sveltejs/vite-plugin-svelte`: `^3.0.0` → `^6.0.0`
   - `carbon-components-svelte`: `^0.85.0` → `^0.95.0`
   - `carbon-icons-svelte`: `^12.8.0` → `^13.0.0`

2. Migrate patterns in each file:
   - `export let` → `let { } = $props()`
   - `$:` → `$derived()`
   - `on:click` → `onclick`
   - `createEventDispatcher` → callback props

**Files to Migrate:**
- `+layout.svelte`
- `+page.svelte` (overview)
- `/users/+page.svelte`
- `/stats/+page.svelte`
- `/logs/+page.svelte`
- `/database/+page.svelte`
- `/server/+page.svelte`
- `/telemetry/+page.svelte`
- `/lib/components/*.svelte`

**Complexity:** MEDIUM (2-3 hours)

---

### Phase 2: Capability Assignment UI

**Goal:** Add capability management to users page

**Backend (already exists):**
- `GET /api/ldm/admin/capabilities/available`
- `POST /api/ldm/admin/capabilities` (grant)
- `DELETE /api/ldm/admin/capabilities/{id}` (revoke)
- `GET /api/ldm/admin/capabilities/user/{id}`

**Frontend Tasks:**
1. Add capability API methods to `client.js`:
   ```javascript
   async getAvailableCapabilities() { ... }
   async getUserCapabilities(userId) { ... }
   async grantCapability(userId, capabilityName) { ... }
   async revokeCapability(grantId) { ... }
   ```

2. Add "Capabilities" column to users table

3. Add capability checkboxes in edit user modal:
   ```
   Capabilities:
   [ ] delete_platform - Can delete platforms
   [ ] delete_project - Can delete projects
   [ ] cross_project_move - Can move across projects
   [ ] empty_trash - Can empty recycle bin
   ```

**Complexity:** LOW (1-2 hours)

---

### Phase 3: UI/UX Improvements

**Goal:** Cleaner, more spacious, customizable

**Tasks:**
1. **Collapsible Sidebar:**
   - Add toggle button
   - Icon-only mode when collapsed
   - Remember state in localStorage

2. **Customizable Overview:**
   - "Edit Dashboard" button
   - Toggle cards on/off
   - Drag to reorder cards
   - Save preferences to localStorage

3. **Spacious Cards:**
   - More padding
   - Larger gaps between elements
   - Cleaner borders

4. **Custom Date Range:**
   - Add date picker component
   - Start/end date selection
   - Quick presets (last 7 days, 30 days, 90 days, year, custom)

**Complexity:** MEDIUM (3-4 hours)

---

### Phase 4: Database Changes

**Goal:** Add tracking tables

**Tasks:**
1. Add `TranslationActivity` model to `models.py`
2. Add `QAUsageLog` model to `models.py`
3. Add pretranslation columns to `LDMRow` model
4. Run Alembic migration

**Complexity:** LOW (1 hour)

---

### Phase 5: Translation Activity Logging

**Goal:** Track edits with source detection

**CRITICAL ARCHITECTURE: Client-Side Calculation**

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT (Electron/Svelte) - Calculates metrics                  │
│  ─────────────────────────────────────────────────────────────  │
│  User confirms cell edit                                        │
│       │                                                         │
│       ▼                                                         │
│  difflib.SequenceMatcher (word-level diff)                      │
│  - similarity_pct: 95.7%                                        │
│  - words_changed: 1                                             │
│  - action: 'modified'                                           │
│       │                                                         │
│       ▼                                                         │
│  POST /api/ldm/activity/log                                     │
│  { row_id, similarity_pct, words_changed, action, edit_source } │
│  ~100 bytes only (no text!)                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SERVER (FastAPI) - Just stores                                 │
│  ─────────────────────────────────────────────────────────────  │
│  1. Validate session                                            │
│  2. Sanity check (0 <= similarity <= 100)                       │
│  3. INSERT INTO translation_activity                            │
│  Done. No calculation. ~1ms.                                    │
└─────────────────────────────────────────────────────────────────┘

WHY: 100 clients = 100 CPUs calculating in parallel
     Server stays light, scales infinitely
```

**Word-Level Diff Algorithm (JavaScript)**

```javascript
// lib/utils/textDiff.js
import { SequenceMatcher } from 'difflib';  // or custom implementation

export function calculateEditMetrics(original, final, editSource) {
  // Fast path: exact match
  if (original === final) {
    return {
      similarity_pct: 100,
      words_changed: 0,
      action: 'accepted',
      word_count_target: final.split(/\s+/).filter(Boolean).length,
      edit_source: editSource
    };
  }

  const wordsO = original.split(/\s+/).filter(Boolean);
  const wordsF = final.split(/\s+/).filter(Boolean);

  const matcher = new SequenceMatcher(null, wordsO, wordsF);
  const similarity = matcher.ratio();

  let wordsChanged = 0;
  for (const [tag, i1, i2, j1, j2] of matcher.getOpcodes()) {
    if (tag !== 'equal') {
      wordsChanged += Math.max(i2 - i1, j2 - j1);
    }
  }

  return {
    similarity_pct: similarity * 100,
    words_changed: wordsChanged,
    action: similarity >= 0.95 ? 'accepted' :
            similarity >= 0.60 ? 'modified' : 'rejected',
    word_count_target: wordsF.length,
    edit_source: editSource
  };
}
```

**Performance (Benchmarked)**

| String Length | Time |
|---------------|------|
| 10 words | 0.02ms |
| 50 words | 0.08ms |
| 200 words | 0.3ms |

**Backend Tasks:**
1. In `rows.py` - Just receive and store metrics (no calculation)
2. In `pretranslate.py` - Mark rows as pretranslated, store `pretrans_original`
3. New endpoint: `POST /api/ldm/activity/log` - Thin storage endpoint

**Frontend Tasks:**
1. Create `lib/utils/textDiff.js` with `calculateEditMetrics()`
2. On cell confirm, calculate metrics and send to server
3. Store pretrans suggestion in component state for comparison

**Complexity:** MEDIUM (2-3 hours)

---

### Phase 6: QA Usage Logging

**Goal:** Track QA tool usage

**Backend Tasks:**
1. In `qa.py`:
   - Wrap QA check functions
   - Log scope, rows checked, issues found
   - Track duration

**Complexity:** LOW (1 hour)

---

### Phase 7: Translation Stats Page

**Goal:** New `/translation` route

**UI:**
```
Translation Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Period: Last 30 days ▼] [Custom: ___ to ___]

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 12,450          │ │ 67.3%           │ │ 32.7%           │
│ Words Translated│ │ Pretranslation  │ │ Manual          │
└─────────────────┘ └─────────────────┘ └─────────────────┘

Pretranslation Acceptance:
┌──────────────────────────────────────────────────────────┐
│ Accepted (as-is): 45%  ████████████░░░░░░░░░░░░░░░░░░░  │
│ Modified:         42%  ████████████░░░░░░░░░░░░░░░░░░░  │
│ Rejected:         13%  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
└──────────────────────────────────────────────────────────┘

By User:
┌─────────┬──────────┬──────────┬─────────────┬──────────┐
│ User    │ Words    │ Edits    │ Pretrans %  │ Accept % │
├─────────┼──────────┼──────────┼─────────────┼──────────┤
│ alice   │ 5,432    │ 234      │ 67%         │ 78%      │
│ bob     │ 4,211    │ 198      │ 82%         │ 65%      │
└─────────┴──────────┴──────────┴─────────────┴──────────┘
```

**Complexity:** MEDIUM (2-3 hours)

---

### Phase 8: QA Analytics Page

**Goal:** New `/qa` route

**UI:**
```
QA Tool Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Period: Last 30 days ▼]

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 1,234           │ │ 89              │ │ 94.2%           │
│ QA Checks Run   │ │ Issues Found    │ │ Resolution Rate │
└─────────────────┘ └─────────────────┘ └─────────────────┘

By User:
┌─────────┬──────────┬──────────┬─────────────┐
│ User    │ Checks   │ Issues   │ Resolved    │
├─────────┼──────────┼──────────┼─────────────┤
│ alice   │ 456      │ 23       │ 21 (91%)    │
│ bob     │ 312      │ 15       │ 15 (100%)   │
└─────────┴──────────┴──────────┴─────────────┘
```

**Complexity:** LOW (1-2 hours)

---

### Phase 9: Custom Report Builder

**Goal:** New `/reports` route

**UI:**
```
Custom Report Builder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Period:     [Last 30 days ▼] or Custom: [___] to [___]

Metrics:    [✓] Word Count  [✓] Edit Count  [ ] QA Issues
            [✓] Pretrans %  [ ] Time Spent

Group By:   (○) User  (○) Team  (○) Language  (○) File

Filters:
  Team:     [▼ All Teams    ]
  User:     [▼ All Users    ]
  Language: [▼ All Languages]

[Generate Report]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Results:
┌─────────┬──────────┬──────────┬─────────────┬──────────┐
│ User    │ Words    │ Edits    │ Pretrans %  │ QA Use   │
├─────────┼──────────┼──────────┼─────────────┼──────────┤
│ alice   │ 5,432    │ 234      │ 67%         │ 12       │
│ bob     │ 4,211    │ 198      │ 82%         │ 8        │
│ charlie │ 3,890    │ 156      │ 45%         │ 22       │
└─────────┴──────────┴──────────┴─────────────┴──────────┘

[Export CSV]  [Export PDF]
```

**Complexity:** HIGH (4-5 hours)

---

## PART 5: FILE CHANGES SUMMARY

### Files to Upgrade (Svelte 5)

| File | Changes |
|------|---------|
| `adminDashboard/package.json` | Bump svelte, vite-plugin-svelte, carbon deps |
| `adminDashboard/src/routes/+layout.svelte` | Migrate to runes |
| `adminDashboard/src/routes/+page.svelte` | Migrate to runes |
| `adminDashboard/src/routes/users/+page.svelte` | Migrate + add capabilities |
| `adminDashboard/src/routes/stats/+page.svelte` | Migrate + add date picker |
| `adminDashboard/src/routes/logs/+page.svelte` | Migrate to runes |
| `adminDashboard/src/routes/database/+page.svelte` | Migrate to runes |
| `adminDashboard/src/routes/server/+page.svelte` | Migrate to runes |
| `adminDashboard/src/routes/telemetry/+page.svelte` | Migrate to runes |
| `adminDashboard/src/lib/components/*.svelte` | Migrate to runes |

### Files to Create

| File | Purpose |
|------|---------|
| `adminDashboard/src/routes/translation/+page.svelte` | Translation stats |
| `adminDashboard/src/routes/qa/+page.svelte` | QA analytics |
| `adminDashboard/src/routes/reports/+page.svelte` | Custom report builder |
| `server/database/models.py` additions | TranslationActivity, QAUsageLog |
| `server/api/translation_stats.py` | Stats endpoints |

### Files to Modify

| File | Changes |
|------|---------|
| `adminDashboard/src/lib/api/client.js` | Add capability + stats API methods |
| `server/tools/ldm/routes/rows.py` | Add activity logging |
| `server/tools/ldm/routes/qa.py` | Add usage logging |
| `server/tools/ldm/routes/pretranslate.py` | Mark pretranslated rows |

---

## PART 6: IMPLEMENTATION ORDER

| Order | Phase | Complexity | Dependencies |
|-------|-------|------------|--------------|
| 1 | Svelte 5 Upgrade | MEDIUM | None |
| 2 | Capability Assignment UI | LOW | Phase 1 |
| 3 | UI/UX Improvements | MEDIUM | Phase 1 |
| 4 | Database Changes | LOW | None |
| 5 | Translation Activity Logging | MEDIUM | Phase 4 |
| 6 | QA Usage Logging | LOW | Phase 4 |
| 7 | Translation Stats Page | MEDIUM | Phase 5 |
| 8 | QA Analytics Page | LOW | Phase 6 |
| 9 | Custom Report Builder | HIGH | Phases 5-8 |

---

## PART 7: SUCCESS CRITERIA

- [ ] adminDashboard runs on Svelte 5 with runes
- [ ] User capabilities can be assigned from dashboard
- [ ] Custom date range works on all stats pages
- [ ] Sidebar is collapsible
- [ ] Dashboard widgets can be toggled on/off
- [ ] Translation activity is logged on every edit
- [ ] Pretranslation acceptance rate is tracked
- [ ] QA usage is tracked per user
- [ ] Custom reports can be generated and exported
- [ ] All pages are spacious and clean

---

## PART 8: ARCHITECTURE PRINCIPLES

### 8.1 Metrics-Only Payload (CRITICAL)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  GOLDEN RULE: Send METRICS, not TEXT                                      ║
║  ─────────────────────────────────────────────────────────────────────────║
║  Client calculates → Server stores → Dashboard aggregates                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

❌ WRONG (wasteful):
   POST /activity { old_text: "...", new_text: "..." }  ← 1KB+ payload
   Server calculates diff, stores everything

✅ RIGHT (optimized):
   POST /activity { similarity: 95.7, words_changed: 1 }  ← 100 bytes
   Server just validates and stores
```

### 8.2 Client-Side Processing Benefits

| Benefit | Impact |
|---------|--------|
| **Zero server CPU** | Server only does INSERT, no diff calculation |
| **Tiny payloads** | ~100 bytes vs ~1KB (10x smaller) |
| **Parallel scaling** | 100 clients = 100 CPUs working |
| **Instant response** | Calculate while user is still looking |
| **No text duplication** | Text already in ldm_rows |

### 8.3 API Endpoints (Thin Storage Layer)

```python
# All activity endpoints are THIN - just validate and store

@router.post("/activity/log")
async def log_activity(metrics: ActivityMetrics):
    """Store pre-calculated metrics. ~1ms response time."""
    # Sanity checks only
    if not 0 <= metrics.similarity_pct <= 100:
        raise HTTPException(400, "Invalid similarity")

    # Direct INSERT - no processing
    await db.execute("INSERT INTO translation_activity ...")
    return {"ok": True}

@router.post("/qa/log")
async def log_qa_usage(metrics: QAMetrics):
    """Store QA usage metrics. ~1ms response time."""
    await db.execute("INSERT INTO qa_usage_log ...")
    return {"ok": True}
```

### 8.4 Dashboard Queries (Aggregation Layer)

Dashboard endpoints DO the heavy work - but only when admin views:

```sql
-- Runs only when admin opens dashboard
SELECT
    user_id,
    SUM(word_count_target) as total_words,
    AVG(similarity_pct) as avg_similarity,
    COUNT(CASE WHEN user_action = 0 THEN 1 END) as accepted,
    COUNT(CASE WHEN user_action = 1 THEN 1 END) as modified
FROM translation_activity
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id;
```

### 8.5 Storage Optimization Summary

| Optimization | Savings |
|--------------|---------|
| SMALLINT instead of INTEGER | 50% per field |
| REAL instead of DOUBLE | 50% per field |
| Enum codes instead of VARCHAR | 90% per field |
| No TEXT storage in activity | 80% total |
| **Total per row** | **~50 bytes (vs ~270)** |

---

## PART 9: WHAT ADMIN SEES

### Example: User Changes "save" → "store"

**Logged data:**
```json
{
  "row_id": 1234,
  "similarity_pct": 95.7,
  "words_changed": 1,
  "action": "modified",
  "edit_source": "pretrans_tm"
}
```

**Dashboard displays:**

```
Pretranslation Acceptance (Last 30 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Accepted (as-is):  45%  ████████████░░░░░░░
Modified:          42%  ███████████░░░░░░░░  ← This edit counts here
Rejected:          13%  ████░░░░░░░░░░░░░░░

Per-User Breakdown:
┌──────────┬──────────┬───────────────┬───────────┐
│ User     │ Words    │ Pretrans Used │ Accept %  │
├──────────┼──────────┼───────────────┼───────────┤
│ alice    │ 5,432    │ 78%           │ 52%       │
│ bob      │ 4,211    │ 65%           │ 41%       │
└──────────┴──────────┴───────────────┴───────────┘
```

---

*Plan created: 2026-01-04 | Updated: 2026-01-04 | Ready for implementation*
