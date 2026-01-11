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
