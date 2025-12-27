# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-27 15:10 | **Build:** 398 (in progress) | **CI:** Online | **Issues:** 15 OPEN

> **SESSION STATUS:** Build 398 triggered with UI-057 hover fix (correct CSS variable). Created documentation overhaul: CONFUSION_HISTORY.md, SMART_UPDATE_PROTOCOL.md.

---

## CURRENT STATE

| Item | Status |
|------|--------|
| **Open Issues** | 15 (6 HIGH, 7 MEDIUM, 4 LOW) |
| **Build 397** | SUCCESS - deployed but hover fix was wrong CSS variable |
| **Build 398** | IN PROGRESS (correct hover CSS fix) |
| **New Docs** | CONFUSION_HISTORY.md, SMART_UPDATE_PROTOCOL.md |

---

## WHAT I DID (2025-12-27 Continued)

### 1. Discovered UI-057 Fix Was Wrong
- Build 397 deployed successfully BUT hover still mismatched
- Root cause: I used `--cds-layer-hover-02` for source, but target uses `--cds-layer-hover-01`
- **Fix:** Changed source hover to use same `--cds-layer-hover-01` as target
- Triggered Build 398 with correct fix

### 2. Created CONFUSION_HISTORY.md
- Documents all confusions from this session
- Prevents repeating mistakes
- Location: `docs/wip/CONFUSION_HISTORY.md`

### 3. Created SMART_UPDATE_PROTOCOL.md
- Three refresh methods: Hot Reload, Auto-Update, Full Reinstall
- Claude should use Auto-Update instead of full reinstall
- Location: `docs/wip/SMART_UPDATE_PROTOCOL.md`

### 4. Learned Key Facts
- **Credentials:** admin/admin123 works, NOT neil/neil
- **CDP Tests:** Must run from Windows, not WSL
- **Env Vars:** Don't pass from WSL to Windows node
- **CSS Verify:** Always extract app.asar to verify CSS is deployed

---

## UI-055 STATUS (Modal Bloat)

**VERIFIED WORKING in Build 397:**
- FileExplorer: 0 modals when closed (was 7)
- TMManager: 0 modals when closed (was 5)
- 10 modals still exist from Settings panel (not fixed yet)

**Settings Panel Modals Still Need Fix:**
- ChangePassword.svelte
- AboutModal.svelte
- PreferencesModal.svelte (Display Settings x2)
- UserProfileModal.svelte
- UpdateModal.svelte
- GridColumnsModal.svelte
- ReferenceSettingsModal.svelte
- ServerStatus.svelte

---

## UI-057 STATUS (Hover Colors)

| Build | Status | Issue |
|-------|--------|-------|
| 397 | WRONG | Used `--cds-layer-hover-02` (different from target) |
| 398 | PENDING | Uses `--cds-layer-hover-01` (same as target) |

---

## REMAINING ISSUES (15 OPEN)

### HIGH (6)
- UI-059: Row selection state inconsistent
- UI-060: Click on source cell opens edit
- UI-061: Routing error on page load
- UI-062: version.json not found
- UI-074: Missing /api/ldm/files endpoint
- UI-075: Console error objects logged

### MEDIUM (7)
- UI-063: CSS text overflow (20+ elements)
- UI-064: Status colors conflict with hover
- UI-065: Edit icon visibility
- UI-066: Placeholder row column count
- UI-067: Filter dropdown height
- UI-068: Resize handle invisible
- UI-069: QA/Edit icon overlap

### LOW (4)
- UI-070: Empty divs (9)
- UI-071: Reference "No match" styling
- UI-072: TM empty message styling
- UI-073: Shortcut bar space

---

## WHAT I MUST DO NEXT

1. **Wait for Build 398** to complete
2. **Use Auto-Update** (not full reinstall) - see SMART_UPDATE_PROTOCOL.md
3. **Login as admin/admin123** (not neil/neil)
4. **Verify hover CSS** by extracting app.asar
5. **Take screenshots** as proof
6. **Fix remaining Settings panel modals** (UI-055 incomplete)

---

## BUILD STATUS CHECK

```bash
python3 -c "
import sqlite3
from datetime import datetime
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title, started FROM action_run ORDER BY id DESC LIMIT 5')
status_map = {0: 'UNK', 1: 'OK', 2: 'FAIL', 3: 'CANCEL', 4: 'SKIP', 5: 'WAIT', 6: 'RUN'}
for r in c.fetchall():
    when = datetime.fromtimestamp(r[3]).strftime('%H:%M') if r[3] else 'N/A'
    print(f'Run {r[0]}: {status_map.get(r[1], r[1]):6} | {when} | {r[2][:45]}')"
```

---

## KEY DOCS (Updated)

| Topic | Doc |
|-------|-----|
| Full Issue List | `docs/wip/ISSUES_TO_FIX.md` |
| **Confusion History** | `docs/wip/CONFUSION_HISTORY.md` (NEW) |
| **Smart Update** | `docs/wip/SMART_UPDATE_PROTOCOL.md` (NEW) |
| Test Protocol | `testing_toolkit/MASTER_TEST_PROTOCOL.md` |
| CDP Testing | `testing_toolkit/cdp/README.md` |
| Troubleshooting | `docs/cicd/TROUBLESHOOTING.md` |

---

## CREDENTIALS

| User | Password | Use For |
|------|----------|---------|
| admin | admin123 | Superadmin login (WORKS) |
| neil | ??? | User exists but password unknown |
| ci_tester | ci_test_pass_2024 | CI tests (Gitea secrets) |

---

*Next: Wait Build 398 -> Auto-Update -> Login admin/admin123 -> Verify -> Screenshot*
