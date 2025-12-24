# Auto-LQA (Localization Quality Assurance) - WIP

**Status:** PRIORITY 1 | **Effort:** High | **Created:** 2025-12-25

---

## Overview

Comprehensive QA system for LDM with LIVE checking and full file reports.

---

## CRITICAL: LDM Independence (Rule #0)

**LDM absorbs, never depends.** QA helpers go in `server/utils/`, NOT imported from `quicksearch/`.

```
WRONG:  from server.tools.quicksearch.qa_tools import extract_code_patterns
RIGHT:  from server.utils.qa_helpers import extract_code_patterns
```

### Files to Create in server/utils/

| File | Move From | Functions |
|------|-----------|-----------|
| `qa_helpers.py` | `quicksearch/qa_tools.py` | `extract_code_patterns`, `is_korean`, `is_sentence`, `has_punctuation`, `preprocess_text_for_char_count` |

Legacy apps (`quicksearch/`) will also import from `server/utils/` - backwards compatible.

### QA Checks Available

| Check | Source Code | Description |
|-------|-------------|-------------|
| **Line Check** | `qa_tools.py` → `line_check()` | Same source with different translations (whole string comparison) |
| **Term Check** | `qa_tools.py` → `term_check()` | Missing glossary terms in translation (word-based, Aho-Corasick) |
| **Pattern Check** | `qa_tools.py` → `pattern_sequence_check()` | `{code}` pattern mismatches between source/target |
| **Character Check** | `qa_tools.py` → `character_count_check()` | Special character count mismatches (`{`, `}`, etc.) |
| **Grammar Check** | LanguageTool (P2) | Spelling/grammar/style (central server) |

---

## Two Modes of Operation

### 1. LIVE QA Mode (Auto-Check on Confirm)

```
User confirms a cell → Auto QA runs → Flag appears if issues found
```

- Toggle button: "Use QA" (like "Use TM")
- Runs immediately after cell confirmation
- Only checks the confirmed cell (fast)
- Shows QA flag icon on cell if issues found
- Once checked, cell is marked (no re-check unless modified)

### 2. Full File QA Mode (Right-Click → Run QA)

```
Right-click file → "Run Full QA" → QA Menu shows report
```

- Runs all checks on entire file
- Results displayed in QA Menu
- Comprehensive report per check type
- Export to Excel option

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         LDM Frontend                         │
├─────────────────────────────────────────────────────────────┤
│  Toolbar                                                     │
│  └── [Use TM] [Use QA] toggles                              │
│                                                              │
│  FileExplorer                                                │
│  └── Right-click → "Run Full QA"                            │
│                                                              │
│  DataGrid                                                    │
│  ├── QA Flag icon on flagged cells                          │
│  └── Filter: All | Confirmed | Unconfirmed | QA Flagged     │
│                                                              │
│  Edit Modal                                                  │
│  ├── Left: Source/Target editing                            │
│  ├── Right-Top: TM Suggestions                              │
│  └── Right-Bottom: QA Results (if flagged)                  │
│                                                              │
│  QA Menu (Slide-out panel or Modal)                         │
│  ├── File selector (which file's QA report)                 │
│  ├── Summary: X issues across Y checks                      │
│  └── Tabs: Line | Term | Pattern | Character | Grammar      │
│      └── Each tab: List of issues, click to navigate        │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### New Table: `qa_results`

```sql
CREATE TABLE qa_results (
    id SERIAL PRIMARY KEY,
    row_id INTEGER REFERENCES ldm_rows(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES ldm_files(id) ON DELETE CASCADE,
    check_type VARCHAR(50) NOT NULL,  -- 'line', 'term', 'pattern', 'character', 'grammar'
    severity VARCHAR(20) DEFAULT 'warning',  -- 'error', 'warning', 'info'
    message TEXT NOT NULL,
    details JSONB,  -- Check-specific details
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,  -- NULL = unresolved
    UNIQUE(row_id, check_type, message)  -- Prevent duplicates
);

CREATE INDEX idx_qa_results_row ON qa_results(row_id);
CREATE INDEX idx_qa_results_file ON qa_results(file_id);
CREATE INDEX idx_qa_results_unresolved ON qa_results(file_id) WHERE resolved_at IS NULL;
```

### New Column on `ldm_rows`

```sql
ALTER TABLE ldm_rows ADD COLUMN qa_checked_at TIMESTAMP;
ALTER TABLE ldm_rows ADD COLUMN qa_flag_count INTEGER DEFAULT 0;
```

---

## Backend Endpoints

### Single Row QA (for LIVE mode)

```
POST /api/ldm/rows/{row_id}/check-qa
```

Request:
```json
{
    "checks": ["line", "term", "pattern", "character"]
}
```

Response:
```json
{
    "row_id": 123,
    "issues": [
        {
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term 'Attack' (expected: 'Attaque')",
            "details": {"korean_term": "공격", "expected": "Attaque"}
        }
    ],
    "issue_count": 1,
    "checked_at": "2025-12-25T10:00:00Z"
}
```

### Full File QA

```
POST /api/ldm/files/{file_id}/check-qa
```

Request:
```json
{
    "checks": ["line", "term", "pattern", "character"],
    "force": false  // true = re-check all, false = skip already checked
}
```

Response:
```json
{
    "file_id": 456,
    "total_rows": 500,
    "rows_checked": 500,
    "summary": {
        "line": {"issue_count": 5, "severity": "warning"},
        "term": {"issue_count": 12, "severity": "warning"},
        "pattern": {"issue_count": 2, "severity": "error"},
        "character": {"issue_count": 0, "severity": "ok"}
    },
    "total_issues": 19,
    "checked_at": "2025-12-25T10:00:00Z"
}
```

### Get QA Results for File

```
GET /api/ldm/files/{file_id}/qa-results?check_type=term
```

Response:
```json
{
    "file_id": 456,
    "check_type": "term",
    "issues": [
        {
            "id": 1,
            "row_id": 123,
            "row_number": 45,
            "source": "공격력 증가",
            "target": "Increase power",
            "message": "Missing term 'Attack' (expected: 'Attaque')",
            "severity": "warning",
            "details": {...},
            "resolved": false
        }
    ],
    "total_count": 12
}
```

### Get QA Results for Row (Edit Modal)

```
GET /api/ldm/rows/{row_id}/qa-results
```

### Mark QA Issue Resolved

```
POST /api/ldm/qa-results/{result_id}/resolve
```

### Filter Rows by QA Status

```
GET /api/ldm/files/{file_id}/rows?filter=qa_flagged
GET /api/ldm/files/{file_id}/rows?filter=confirmed
GET /api/ldm/files/{file_id}/rows?filter=unconfirmed
```

---

## Frontend Components

### 1. QA Toggle Button

**Location:** Toolbar (next to "Use TM")

```svelte
<ToggleButton
    label="Use QA"
    bind:checked={useQA}
    icon={QAIcon}
/>
```

**Behavior:**
- When ON: Auto-run QA after each cell confirmation
- Persisted in user preferences

### 2. QA Flag Icon on Cells

**Location:** DataGrid row

```svelte
{#if row.qa_flag_count > 0}
    <QAFlagIcon
        count={row.qa_flag_count}
        on:click={() => openEditModal(row)}
    />
{/if}
```

**Design:**
- Small warning icon (yellow/orange)
- Badge with count if multiple issues
- Tooltip: "3 QA issues"

### 3. Row Filter Dropdown

**Location:** Toolbar or above DataGrid

```svelte
<Select bind:value={rowFilter}>
    <Option value="all">All Rows</Option>
    <Option value="confirmed">Confirmed</Option>
    <Option value="unconfirmed">Unconfirmed</Option>
    <Option value="qa_flagged">QA Flagged</Option>
</Select>
```

### 4. Edit Modal - QA Results Panel

**Location:** Right side of Edit Modal, below TM Suggestions

```svelte
{#if row.qa_flag_count > 0}
    <QAResultsPanel {rowId}>
        <!-- Grouped by check type -->
        <QAIssue type="term" message="Missing 'Attack'" />
        <QAIssue type="pattern" message="{code} mismatch" />
    </QAResultsPanel>
{/if}
```

**Design:**
- Collapsible sections per check type
- Each issue shows message + "Dismiss" button
- Clicking issue highlights relevant text

### 5. QA Menu (Slide-out Panel)

**Location:** Right side slide-out (like a drawer)

**Trigger:**
- Right-click file → "View QA Report"
- Or dedicated QA button in toolbar

```svelte
<QAMenu {fileId}>
    <QASummary {summary} />

    <Tabs>
        <Tab label="Line Check" count={5}>
            <QAIssueList issues={lineIssues} />
        </Tab>
        <Tab label="Term Check" count={12}>
            <QAIssueList issues={termIssues} />
        </Tab>
        <Tab label="Pattern" count={2}>
            <QAIssueList issues={patternIssues} />
        </Tab>
        <Tab label="Character" count={0}>
            <QAIssueList issues={charIssues} />
        </Tab>
        <Tab label="Grammar" count={8} disabled={!grammarAvailable}>
            <QAIssueList issues={grammarIssues} />
        </Tab>
    </Tabs>

    <Button on:click={exportToExcel}>Export Report</Button>
</QAMenu>
```

**Design Principles:**
- Spacious, minimalistic, slick
- Clear visual hierarchy
- Each check type has distinct color/icon
- Clickable issues navigate to row in DataGrid
- Multi-modal support (Svelte 5 portals)

---

## UI/UX Design Guidelines

### Visual Language

| Check Type | Icon | Color | Severity |
|------------|------|-------|----------|
| Line | ⚖️ | Blue | Warning |
| Term | 📝 | Orange | Warning |
| Pattern | `{}` | Red | Error |
| Character | #️⃣ | Red | Error |
| Grammar | ✏️ | Yellow | Warning |

### Spacing & Layout

- Use consistent 8px grid
- Cards with subtle shadows
- Generous padding (16-24px)
- Clear section dividers
- Readable font sizes (14-16px)

### Interaction Patterns

- Click issue → Jump to row in DataGrid
- Double-click issue → Open Edit Modal
- Hover issue → Show full details tooltip
- Dismiss issue → Mark resolved (with undo)

---

## Implementation Phases

### Phase 1: Backend Endpoints (Effort: Medium)

| Step | Task | File |
|------|------|------|
| 1.1 | Create `qa_results` table migration | `migrations/` |
| 1.2 | Add `qa_checked_at`, `qa_flag_count` to rows | `migrations/` |
| 1.3 | Create `qa.py` route file | `routes/qa.py` |
| 1.4 | Implement single row QA endpoint | `routes/qa.py` |
| 1.5 | Implement full file QA endpoint | `routes/qa.py` |
| 1.6 | Implement QA results retrieval | `routes/qa.py` |
| 1.7 | Add row filter by QA status | `routes/tm_entries.py` |
| 1.8 | Unit tests | `tests/` |

### Phase 2: LIVE QA Mode (Effort: Medium)

| Step | Task | File |
|------|------|------|
| 2.1 | Add "Use QA" toggle to toolbar | `Toolbar.svelte` |
| 2.2 | Hook into cell confirm action | `EditModal.svelte` |
| 2.3 | Call single row QA endpoint | `api/ldm.ts` |
| 2.4 | Update row with QA results | `stores/` |
| 2.5 | Add QA flag icon to DataGrid | `DataGrid.svelte` |
| 2.6 | Persist toggle preference | `stores/` |

### Phase 3: Edit Modal QA Panel (Effort: Medium)

| Step | Task | File |
|------|------|------|
| 3.1 | Create `QAResultsPanel.svelte` | `components/` |
| 3.2 | Fetch QA results for row | `api/ldm.ts` |
| 3.3 | Display issues grouped by type | `QAResultsPanel.svelte` |
| 3.4 | Add dismiss/resolve functionality | `QAResultsPanel.svelte` |
| 3.5 | Layout: position below TM panel | `EditModal.svelte` |

### Phase 4: Row Filtering (Effort: Low)

| Step | Task | File |
|------|------|------|
| 4.1 | Add filter dropdown to toolbar | `Toolbar.svelte` |
| 4.2 | Implement filter API call | `api/ldm.ts` |
| 4.3 | Update DataGrid with filtered rows | `DataGrid.svelte` |

### Phase 5: QA Menu (Full Reports) (Effort: High)

| Step | Task | File |
|------|------|------|
| 5.1 | Create `QAMenu.svelte` slide-out | `components/` |
| 5.2 | Add context menu "Run Full QA" | `FileExplorer.svelte` |
| 5.3 | Create summary component | `QASummary.svelte` |
| 5.4 | Create tabbed issue lists | `QAIssueList.svelte` |
| 5.5 | Implement click-to-navigate | `QAMenu.svelte` |
| 5.6 | Add Excel export | `QAMenu.svelte` |
| 5.7 | Style with design guidelines | `*.svelte` |

### Phase 6: Testing (Effort: Medium)

| Step | Task |
|------|------|
| 6.1 | Unit tests for all QA endpoints |
| 6.2 | Integration tests with fixtures |
| 6.3 | CDP E2E tests for full flow |
| 6.4 | Test LIVE mode with real data |
| 6.5 | Test filtering and navigation |

---

## Files to Create/Modify

### Backend

| File | Action | Purpose |
|------|--------|---------|
| `server/migrations/XXX_add_qa_tables.py` | NEW | Database schema |
| `server/tools/ldm/routes/qa.py` | NEW | QA endpoints |
| `server/tools/ldm/router.py` | EDIT | Register QA router |
| `server/tools/ldm/routes/tm_entries.py` | EDIT | Add filter param |
| `server/tests/tools/ldm/test_qa.py` | NEW | Unit tests |

### Frontend

| File | Action | Purpose |
|------|--------|---------|
| `locaNext/src/lib/components/ldm/Toolbar.svelte` | EDIT | Add QA toggle + filter |
| `locaNext/src/lib/components/ldm/DataGrid.svelte` | EDIT | Add QA flag icon |
| `locaNext/src/lib/components/ldm/EditModal.svelte` | EDIT | Add QA panel |
| `locaNext/src/lib/components/ldm/QAResultsPanel.svelte` | NEW | QA results in modal |
| `locaNext/src/lib/components/ldm/QAMenu.svelte` | NEW | Full QA report menu |
| `locaNext/src/lib/components/ldm/QASummary.svelte` | NEW | Summary stats |
| `locaNext/src/lib/components/ldm/QAIssueList.svelte` | NEW | Issue list per type |
| `locaNext/src/lib/components/ldm/QAFlagIcon.svelte` | NEW | Flag icon component |
| `locaNext/src/lib/components/ldm/FileExplorer.svelte` | EDIT | Context menu item |
| `locaNext/src/lib/api/ldm.ts` | EDIT | QA API functions |
| `locaNext/src/lib/stores/qa.ts` | NEW | QA state management |

### Tests

| File | Action | Purpose |
|------|--------|---------|
| `testing_toolkit/cdp/test_qa_live.js` | NEW | E2E LIVE mode test |
| `testing_toolkit/cdp/test_qa_full.js` | NEW | E2E full QA test |
| `testing_toolkit/cdp/fixtures/qa_test_file.xml` | NEW | Test fixture with known issues |

---

## Test Fixtures

### `qa_test_file.xml` - Contains Known Issues

```xml
<?xml version="1.0" encoding="utf-8"?>
<Root>
    <!-- Line Check: Same source, different translations -->
    <LocStr StringId="1" StrOrigin="공격" Str="Attack"/>
    <LocStr StringId="2" StrOrigin="공격" Str="Attaque"/>  <!-- ISSUE -->

    <!-- Term Check: Missing term -->
    <LocStr StringId="3" StrOrigin="공격력 증가" Str="Increase power"/>  <!-- ISSUE: missing Attack -->

    <!-- Pattern Check: Mismatched {code} -->
    <LocStr StringId="4" StrOrigin="{0}의 공격력" Str="Attack power of"/>  <!-- ISSUE: missing {0} -->

    <!-- Character Check: Mismatched braces -->
    <LocStr StringId="5" StrOrigin="{name}의 {stat}" Str="{name}'s stat"/>  <!-- ISSUE: missing {stat} -->

    <!-- Clean entry (no issues) -->
    <LocStr StringId="6" StrOrigin="방어력" Str="Defense"/>
</Root>
```

---

## QA Check Details

### Line Check
- **What:** Finds same source text with different translations
- **Why:** Inconsistent terminology across files
- **Severity:** Warning
- **Fix:** Standardize translations

### Term Check
- **What:** Finds glossary terms in source missing from target
- **Why:** Important terms must be translated consistently
- **Severity:** Warning
- **Fix:** Add missing term to translation

### Pattern Check
- **What:** Finds `{code}` patterns that don't match
- **Why:** Code patterns must be preserved exactly
- **Severity:** Error
- **Fix:** Match patterns exactly

### Character Check
- **What:** Finds special character count mismatches
- **Why:** Formatting characters must be preserved
- **Severity:** Error
- **Fix:** Match character counts

### Grammar Check (P2)
- **What:** Spelling/grammar/style issues
- **Why:** Quality assurance for target language
- **Severity:** Warning
- **Fix:** Accept suggestion or dismiss

---

## Integration with LanguageTool (P2)

After Auto-LQA is battle-tested:

1. Add "Grammar" tab to QA Menu
2. Grammar check runs with Full File QA
3. LIVE mode can optionally include grammar (may be slow)
4. Requires central server connection
5. Graceful degradation when offline

See: [LANGUAGETOOL_IMPLEMENTATION.md](LANGUAGETOOL_IMPLEMENTATION.md)

---

## Checklist

### Phase 1: Backend
- [ ] Create migration for `qa_results` table
- [ ] Add columns to `ldm_rows`
- [ ] Create `routes/qa.py`
- [ ] POST `/rows/{id}/check-qa` (single row)
- [ ] POST `/files/{id}/check-qa` (full file)
- [ ] GET `/files/{id}/qa-results`
- [ ] GET `/rows/{id}/qa-results`
- [ ] POST `/qa-results/{id}/resolve`
- [ ] Add `filter` param to rows endpoint
- [ ] Unit tests

### Phase 2: LIVE QA
- [ ] Add "Use QA" toggle to Toolbar
- [ ] Hook into confirm action
- [ ] Call QA endpoint on confirm
- [ ] Update row state with results
- [ ] Show QA flag icon
- [ ] Persist preference

### Phase 3: Edit Modal QA Panel
- [ ] Create QAResultsPanel.svelte
- [ ] Fetch results for row
- [ ] Display grouped issues
- [ ] Dismiss functionality
- [ ] Layout in EditModal

### Phase 4: Row Filtering
- [ ] Add filter dropdown
- [ ] API integration
- [ ] Update DataGrid

### Phase 5: QA Menu
- [ ] Create QAMenu slide-out
- [ ] Context menu trigger
- [ ] Summary component
- [ ] Tabbed issue lists
- [ ] Click-to-navigate
- [ ] Excel export
- [ ] Polish styling

### Phase 6: Testing
- [ ] Create test fixtures
- [ ] Unit tests for endpoints
- [ ] Integration tests
- [ ] CDP E2E: LIVE mode
- [ ] CDP E2E: Full QA
- [ ] CDP E2E: Filtering

---

*Created: 2025-12-25 | Priority 1 | Battle-test before LanguageTool*
