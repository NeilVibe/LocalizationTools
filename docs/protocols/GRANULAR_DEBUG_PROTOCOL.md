# Granular Debug Protocol (GDP)

> **The art of microscopic logging to achieve autonomous bug detection and resolution.**

## Overview

This protocol documents the systematic debugging methodology discovered during the TM Paste Bug investigation (2026-01-11). The key insight: **bugs hide in the gaps between what you THINK the code does and what it ACTUALLY does**. Granular logging illuminates those gaps.

---

## The TM Paste Case Study

### The Problem
- User: "I cut, I moved, I tried to paste. Nothing is happening."
- Backend log showed: `TM 19 assigned to unassigned`
- Expected: TM assigned to Offline Storage folder

### The Journey

| Phase | What I Did | What I Learned |
|-------|-----------|----------------|
| 1 | Added basic logging to `handlePaste()` | Function was being called |
| 2 | Logged clipboard contents | Clipboard had correct TM data |
| 3 | Logged breadcrumb state | Location type was 'folder', ID was 'local-902787874' |
| 4 | Discovered `local-` prefix | Local folders use string IDs, not integers |
| 5 | Added local folder detection | Code path was correct |
| 6 | Logs not appearing in backend | **INFO logs not forwarded!** |
| 7 | Changed to WARNING level | Now visible in backend logs |
| 8 | Logged treeData lookup | Platform found, Project found, ID=66 |
| 9 | Logged final assignmentData | `{project_id: 66}` - CORRECT! |
| 10 | **BUT** backend still said "unassigned" | Data not reaching server! |
| 11 | Checked backend endpoint signature | **Query params, not body!** |
| 12 | Fixed API call format | **BUG FIXED** |

### The Real Bug
```javascript
// WRONG - Backend ignores body for this endpoint
const response = await fetch(url, {
  method: 'PATCH',
  body: JSON.stringify(assignmentData)  // ❌ Ignored!
});

// RIGHT - Backend expects query parameters
const url = `${API_BASE}/api/ldm/tm/${tm.id}/assign?project_id=66`;
const response = await fetch(url, { method: 'PATCH' });  // ✅
```

---

## The Protocol

### Level 1: Entry Point Logging
Log when a function is called and with what inputs.

```javascript
function handlePaste() {
  logger.info('handlePaste called', {
    clipboardLength: clipboardItems.length,
    clipboardOperation,
    breadcrumb: breadcrumb.map(b => ({ type: b.type, id: b.id, name: b.name }))
  });
```

**Purpose**: Confirm the function runs and with what context.

### Level 2: Decision Point Logging
Log at every `if/else` branch, every `.find()`, every conditional.

```javascript
const currentLocation = breadcrumb[breadcrumb.length - 1];
logger.info('Current paste target location', {
  type: currentLocation.type,
  id: currentLocation.id,
  name: currentLocation.name
});

if (currentLocation.type === 'folder') {
  const folderId = currentLocation.id;
  if (typeof folderId === 'string' && folderId.startsWith('local-')) {
    logger.warning('Detected local folder', { folderId });
    // ...
  }
}
```

**Purpose**: Know exactly which code path executed.

### Level 3: Variable State Logging
Log the ACTUAL contents of variables, not just that they exist.

```javascript
// BAD - tells you nothing
logger.info('Found platform');

// GOOD - tells you everything
logger.info('Found platform', {
  found: !!offlineStoragePlatform,
  platformId: offlineStoragePlatform?.id,
  projectCount: offlineStoragePlatform?.projects?.length,
  projectNames: offlineStoragePlatform?.projects?.map(p => p.name)
});
```

**Purpose**: See the actual data, not assumptions about it.

### Level 4: Pre-Action Logging
Log what you're ABOUT to do, with exact parameters.

```javascript
logger.info('Assignment data for paste', { assignmentData });

// Before API call
logger.apiCall(url, 'PATCH', { params: assignmentData });
```

**Purpose**: Verify the data right before it's used.

### Level 5: Post-Action Logging
Log results AND failures with full context.

```javascript
if (response.ok) {
  const result = await response.json();
  logger.success('TM paste API success', { tmId: tm.id, result });
} else {
  const errorText = await response.text();
  logger.error('Failed to paste TM', {
    tmId: tm.id,
    status: response.status,
    error: errorText
  });
}
```

**Purpose**: Confirm what actually happened.

---

## Log Level Strategy

### The Remote Logging Reality

```
Frontend Logger → Remote Log Endpoint → Backend Log File
                         ↓
              Only WARNING and ERROR forwarded!
```

**Critical Insight**: During active debugging, use WARNING level for logs you NEED to see:

```javascript
// During debugging - use WARNING to ensure visibility
logger.warning('Debug: assignmentData contents', { assignmentData });

// After fix confirmed - downgrade to INFO
logger.info('Assignment data for paste', { assignmentData });
```

### Level Selection Guide

| Level | When to Use | Forwarded to Backend? |
|-------|-------------|----------------------|
| `logger.info()` | Normal flow, routine operations | NO |
| `logger.warning()` | Unusual but handled situations, DEBUG MODE | YES |
| `logger.error()` | Failures, exceptions | YES |
| `logger.success()` | Confirmations of important operations | Depends |

---

## The API Contract Check

### Always Verify: Body vs Query Parameters

**Backend signature tells you the truth:**

```python
# Query parameters (no Body() decorator)
async def assign_tm(
    tm_id: int,
    platform_id: Optional[int] = None,  # ← Query param
    project_id: Optional[int] = None,   # ← Query param
):

# Body parameter (has Body() decorator)
async def create_tm(
    data: TMCreateRequest = Body(...),  # ← JSON body
):
```

**Frontend must match:**

```javascript
// For query params
const url = `${API}/endpoint?param1=value1&param2=value2`;
fetch(url, { method: 'PATCH' });

// For body
fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});
```

---

## Debug Escalation Checklist

When a bug persists despite code looking correct:

```
□ 1. ENTRY LOGS - Is the function being called?
□ 2. INPUT LOGS - What data is coming in?
□ 3. DECISION LOGS - Which branch executed?
□ 4. VARIABLE LOGS - What do variables actually contain?
□ 5. PRE-ACTION LOGS - What's being sent/used?
□ 6. POST-ACTION LOGS - What came back?
□ 7. LOG VISIBILITY - Are my logs actually appearing? (check level)
□ 8. API CONTRACT - Does frontend match backend expectations?
□ 9. DATA FORMAT - String vs int? Body vs params? Correct keys?
□ 10. NETWORK TAB - What's actually going over the wire?
```

---

## Pattern: The Logging Sandwich

Wrap any suspicious operation with before/after logging:

```javascript
// BEFORE
logger.warning('About to lookup project', {
  platformName: offlineStoragePlatform?.name,
  projectsAvailable: offlineStoragePlatform?.projects?.map(p => p.name)
});

// THE OPERATION
const project = offlineStoragePlatform?.projects?.find(p => p.name === 'Offline Storage');

// AFTER
logger.warning('Project lookup result', {
  found: !!project,
  projectId: project?.id,
  projectName: project?.name
});
```

---

## Anti-Patterns

### 1. Silent Assumptions
```javascript
// BAD - assumes it worked
const project = platform.projects.find(p => p.name === 'X');
assignmentData = { project_id: project.id };

// GOOD - verifies it worked
const project = platform.projects.find(p => p.name === 'X');
if (!project) {
  logger.error('Project not found', { searchName: 'X', available: platform.projects.map(p => p.name) });
  return;
}
```

### 2. Logging Without Context
```javascript
// BAD
logger.info('Processing');
logger.info('Done');

// GOOD
logger.info('Processing TM paste', { tmCount: tms.length, targetLocation: location.name });
logger.info('TM paste complete', { successCount, failCount, target: location.name });
```

### 3. Trusting Default Log Levels
```javascript
// During active debugging, don't use INFO if you NEED to see it
logger.info('Critical debug info');  // ❌ Might not appear

logger.warning('Critical debug info');  // ✅ Will appear
```

---

## Quick Reference

### Adding Debug Logging

```javascript
// 1. Function entry
logger.info('functionName called', { inputParams });

// 2. Each decision point
logger.info('Condition check', { condition, result: condition ? 'branch A' : 'branch B' });

// 3. Variable inspection
logger.warning('Variable state', { varName: variable, type: typeof variable });

// 4. Before external calls
logger.info('API call', { url, method, params });

// 5. After external calls
logger.info('API response', { status, data: result });
```

### The Golden Rule

> **If you can't see it in the logs, you don't know what happened.**

When debugging: Log MORE than you think you need. You can always remove logs later. You can't debug what you can't see.

---

## Related Docs

- `testing_toolkit/DEV_MODE_PROTOCOL.md` - Dev server testing
- `docs/cicd/TROUBLESHOOTING.md` - CI/CD debugging
- Remote logging endpoint: `POST /api/v1/remote-logs/frontend`

---

*Protocol established: 2026-01-11*
*Case study: TM Paste Bug - Query Params vs Body*

---

## Case Study 2: Patch Updater Download Bug (2026-01-17)

### The Problem
- Patch update download times out after 2 minutes
- UI shows "13.3 KB / 17.9 MB" and stays blocked
- PowerShell downloads the same file in 12.8 seconds

### The GDP Journey

| Phase | What I Did | What I Found |
|-------|-----------|--------------|
| 1 | Added debug log file to main process | Can't see main process console from CDP |
| 2 | Logged generateInitialState | ASAR interception bug discovered! |
| 3 | Fixed ASAR with original-fs | Hash now computes correctly |
| 4 | Logged downloadFile | HTTP 200 received, first chunk OK |
| 5 | Logged every data chunk | Only first chunk received, then NOTHING |
| 6 | Added inactivity timer | Confirmed: data flow stops after first chunk |
| 7 | Tested PowerShell download | Works perfectly (12.8s for 18MB) |
| 8 | Root cause: Node.js http blocks in Electron | Use PowerShell as workaround |

### Bug 1: ASAR Interception

```javascript
// WRONG - Electron intercepts and tries to read from INSIDE app.asar
const content = fs.readFileSync('path/to/app.asar');

// RIGHT - Use original-fs to bypass ASAR module
import originalFs from 'original-fs';
const content = originalFs.readFileSync('path/to/app.asar');
```

GDP log that revealed it:
```
HASH FAILED {"error":"ENOENT, not found in ...app.asar",
"stack":"at readFileFromArchiveSync..."}
```

### Bug 2: Node.js HTTP Blocking

GDP log showing the stall:
```
[08:07:36.398] Download progress {"percent":"0.1","chunks":1}
... NO MORE LOGS FOR 2 MINUTES ...
[08:09:36.412] REQUEST TIMEOUT
```

**Root cause:** Unknown - Node.js http socket stalls after first chunk inside Electron main process on Windows.

**Initial workaround (Build 476):** PowerShell via child_process
```javascript
// Works but blocked in corporate environments!
spawn('powershell.exe', ['-Command', `Invoke-WebRequest...`])
```

**Correct solution (Build 477):** Electron's net module
```javascript
import { net } from 'electron';

// Uses Chromium's networking stack - not Node.js, not blocked
const request = net.request(url);
request.on('response', (response) => {
  response.on('data', (chunk) => fileStream.write(chunk));
  response.on('end', () => resolve());
});
request.end();
```

**Lesson learned:** Should have tried Electron `net` module FIRST before external tools.

### Key Lesson: Windows/Electron Quirks

When debugging Electron on Windows:
1. **Main process logs** - Write to a file in userData since console isn't visible
2. **ASAR traps** - Any `fs` operation on files in resources/ might be intercepted
3. **Electron net module FIRST** - For HTTP, try `net` module before external tools (PowerShell blocked in corp)
4. **Test outside Electron** - Verify the operation works in pure Node.js first
5. **original-fs for real files** - Bypass ASAR interception with `import originalFs from 'original-fs'`

---

## Case Study 3: Python Partial Installs (2026-01-17)

### The Problem
- First-time setup completes deps step successfully
- Model download fails with `ModuleNotFoundError: No module named 'yaml'`
- PyYAML shows "Requirement already satisfied" in pip output

### GDP Discovery

```
Log says: Requirement already satisfied: pyyaml>=5.1 (6.0.2)
BUT:     ModuleNotFoundError: No module named 'yaml'

Check site-packages:
- PyYAML-6.0.2.dist-info/ EXISTS (metadata)
- yaml/ folder MISSING (actual module)
```

**Root cause:** Partial installation - pip metadata exists but module files missing.

### Debugging Mistake Made

| Mistake | Correct Approach |
|---------|------------------|
| ❌ Checked AppData for logs | ✅ Check app's `logs/` directory (next to exe) |
| ❌ Assumed CDP meant app working | ✅ Check actual screen title in CDP response |
| ❌ Looked for `patch-updater-debug.log` | ✅ Realize patch updater runs AFTER first-time setup |

### Key Lesson: Log Location

```javascript
// In logger.js - Production logs go NEXT TO THE EXE
if (isPackaged) {
  return path.join(exeDir, 'logs');  // C:\...\LocaNext\logs\
}
```

**NOT AppData!** Read the logger.js source code to find log location.

### The Fix

```powershell
# Force reinstall to get actual module files
python -m pip install --force-reinstall pyyaml
```

### Multiple Missing Modules

After fixing yaml, found another: `socketio`

**Pattern:** When one module is partially installed, others might be too. Check ALL key imports.

### GDP Checklist for Python Deps

```
□ Check log in correct location (app's logs/ dir, not AppData)
□ Search for "ModuleNotFoundError" in logs
□ Verify module folder exists in site-packages (not just dist-info)
□ If "Requirement already satisfied" but import fails → partial install
□ Force reinstall: pip install --force-reinstall <package>
□ Test import directly with Python exe
```

---

## How to Debug Efficiently (Lessons Learned)

### RULE 1: Find the Log Location FIRST

**Before running ANY debug command:**
1. Read the logger source code
2. Find where logs are written
3. Check THAT location

```javascript
// Example from logger.js:
if (isPackaged) {
  return path.join(exeDir, 'logs');  // NEXT TO EXE, not AppData!
}
```

**Common mistake:** Assuming logs are in AppData when they're actually next to the exe.

### RULE 2: Understand the Execution Flow

```
App Launch
  ↓
First-Time Setup (if needed)
  ↓ deps → model → verify
Main App Load
  ↓
Backend Start
  ↓
Patch Updater Check  ← Debug log only exists AFTER this point!
```

**Common mistake:** Looking for patch-updater-debug.log when app is still on first-time setup.

### RULE 3: Read Source Code, Not Assumptions

| Wrong | Right |
|-------|-------|
| "Logs should be in AppData" | Read logger.js to find actual path |
| "CDP means app is working" | Check CDP response for actual screen title |
| "pip says installed = working" | Check if module folder exists, not just dist-info |

### RULE 4: Microscopic vs Telescope Debugging

**Telescope (wrong for this):** Screenshots, UI checks, broad searches
**Microscopic (right for this):** Log files, exact error messages, source code

```bash
# WRONG - telescope
Take screenshot to see what's happening

# RIGHT - microscopic
Get-Content app/logs/locanext_app.log -Tail 50
Get-Content app/logs/locanext_error.log
```

### RULE 5: Follow the Error Chain

```
Error: "No module named 'yaml'"
  ↓
Check: Is yaml folder in site-packages?
  ↓ NO
Check: Is dist-info there?
  ↓ YES - partial install!
Fix: pip install --force-reinstall pyyaml
  ↓
New Error: "No module named 'socketio'"
  ↓
Same pattern - check and fix
```

### Quick Reference: Windows App Debugging

```powershell
# 1. Find logs (ALWAYS first step)
Get-ChildItem "C:\Path\To\App\logs"

# 2. Read main log (last 50 lines)
Get-Content "C:\Path\To\App\logs\locanext_app.log" -Tail 50

# 3. Search for errors
Get-Content "C:\Path\To\App\logs\locanext_app.log" | Select-String "ERROR|Exception|ModuleNotFoundError"

# 4. Check Python imports directly
& "C:\Path\To\App\python\python.exe" -c "import module_name; print('OK')"

# 5. Check CDP status
Invoke-RestMethod -Uri "http://localhost:9222/json"
```
