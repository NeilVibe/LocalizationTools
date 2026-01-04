# LAUNCHER-Style Patch Update System

## Problem

Current auto-update downloads **624MB installer** for every update, even for a 1-line fix.
- User sees full NSIS wizard
- Feels like reinstall, not update
- Wastes bandwidth and time (5-10 min on slow connection)

## Solution: Component-Based Patch Updates

Like game launchers (Steam, Epic, Battle.net), only download what changed.

```
╔════════════════════════════════════════════════════════════════╗
║  LAUNCHER-STYLE UPDATE FLOW                                    ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║   [Check for Update]                                           ║
║         │                                                      ║
║         ▼                                                      ║
║   [Compare manifest.json]                                      ║
║         │                                                      ║
║   ┌─────┴─────────────────────────────────┐                   ║
║   │ Local              Remote             │                   ║
║   │ app.asar: abc123   app.asar: def456   │ ← Changed!       ║
║   │ server: xyz789     server: xyz789     │ ← Same           ║
║   │ python: 3.11.9     python: 3.11.9     │ ← Same           ║
║   │ model: qwen1.5     model: qwen1.5     │ ← Same           ║
║   └───────────────────────────────────────┘                   ║
║         │                                                      ║
║         ▼                                                      ║
║   [Download only: app.asar (18MB)]                            ║
║         │                                                      ║
║         ▼                                                      ║
║   [Hot-swap: Replace in-place]                                ║
║         │                                                      ║
║         ▼                                                      ║
║   [Restart app - DONE!]                                       ║
║                                                                ║
║   Total download: 18MB instead of 624MB (97% reduction)       ║
╚════════════════════════════════════════════════════════════════╝
```

## Architecture

### 1. Component Manifest (manifest.json)

Generated at build time, hosted alongside releases:

```json
{
  "version": "26.104.1600",
  "buildDate": "2026-01-04T16:00:00Z",
  "components": {
    "app.asar": {
      "version": "26.104.1600",
      "sha256": "abc123...",
      "size": 18874368,
      "url": "patches/26.104.1600/app.asar"
    },
    "server": {
      "version": "26.104.1600",
      "sha256": "def456...",
      "size": 10485760,
      "url": "patches/26.104.1600/server.zip"
    },
    "python": {
      "version": "3.11.9",
      "sha256": "xyz789...",
      "required": true,
      "url": "components/python-3.11.9.zip"
    },
    "model": {
      "version": "qwen2-0.5b",
      "sha256": "model123...",
      "optional": true,
      "url": "components/qwen2-0.5b.zip"
    }
  },
  "minVersion": "25.1201.0000",
  "releaseNotes": "Bug fixes and performance improvements"
}
```

### 2. Local State Tracking

Store component versions in `resources/component-state.json`:

```json
{
  "installed": "26.104.1200",
  "components": {
    "app.asar": { "version": "26.104.1200", "sha256": "old123..." },
    "server": { "version": "26.104.1200", "sha256": "old456..." },
    "python": { "version": "3.11.9", "sha256": "xyz789..." },
    "model": { "version": "qwen2-0.5b", "sha256": "model123..." }
  }
}
```

### 3. Update Flow

```javascript
async function checkForPatchUpdate() {
  // 1. Fetch remote manifest
  const remote = await fetch('releases/latest/manifest.json');

  // 2. Load local state
  const local = loadComponentState();

  // 3. Compare components
  const updates = [];
  for (const [name, component] of Object.entries(remote.components)) {
    if (local.components[name]?.sha256 !== component.sha256) {
      updates.push({ name, ...component });
    }
  }

  // 4. Calculate total download size
  const totalSize = updates.reduce((sum, u) => sum + u.size, 0);

  return {
    hasUpdates: updates.length > 0,
    updates,
    totalSize,
    version: remote.version
  };
}

async function applyPatchUpdates(updates) {
  const tempDir = path.join(app.getPath('temp'), 'locanext-update');

  for (const update of updates) {
    // Download component
    await downloadWithProgress(update.url, tempDir);

    // Verify hash
    const hash = await calculateSha256(downloadedFile);
    if (hash !== update.sha256) throw new Error('Hash mismatch');

    // Apply (different strategies per component)
    await applyComponent(update.name, downloadedFile);
  }

  // Update local state
  saveComponentState(updates);
}
```

### 4. Component Application Strategies

| Component | Strategy | Requires Restart? |
|-----------|----------|-------------------|
| app.asar | Direct file replace | Yes (app restart) |
| server/ | Unzip to resources/server | Yes (backend restart) |
| python/ | Unzip to resources/tools/python | Yes (full restart) |
| model | Unzip to model directory | No (reload on next use) |

### 5. Beautiful Update UI

```
┌─────────────────────────────────────────────────────┐
│                    🚀 Update Available              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Version 26.104.1600                                │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ ████████████████░░░░░░░░░░░░░░░░░ 45%         │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  Downloading: app.asar (8.1 / 18 MB)               │
│  Speed: 2.3 MB/s                                    │
│                                                     │
│  Components to update:                              │
│  ✅ Frontend (app.asar) - 18 MB                    │
│  ⬜ Backend (server) - 10 MB                       │
│  ⏭️ Python runtime - unchanged                     │
│  ⏭️ AI model - unchanged                           │
│                                                     │
│  Total: 28 MB (instead of 624 MB - 95% saved!)    │
│                                                     │
│         [Update Now]     [Remind Later]            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Basic ASAR Hot-Swap (Quick Win)
- Generate app.asar separately in CI
- Upload as release asset alongside installer
- Check app.asar version/hash
- Download and replace if changed
- Restart app

**Effort:** 2-3 hours
**Impact:** 97% reduction for frontend-only updates

### Phase 2: Full Component System
- Generate manifest.json in CI
- Track all components
- Smart delta detection
- Beautiful UI with progress

**Effort:** 1-2 days
**Impact:** Minimal downloads for any update type

### Phase 3: Binary Delta Patches (Advanced)
- Use bsdiff/xdelta for binary diffs
- Generate patches between versions
- Apply patches instead of full files
- Even smaller downloads (1-5MB typical)

**Effort:** 1 week
**Impact:** Game-launcher level efficiency

## CI/CD Changes Required

### Build Workflow Additions

```yaml
# After electron-builder
- name: Generate Update Components
  run: |
    # Extract app.asar from installer
    7z x dist/LocaNext_Setup.exe -opatch-temp

    # Create component manifest
    node scripts/generate-manifest.js

    # Upload components
    - app.asar
    - server.zip
    - manifest.json
```

## Migration Path

1. **v26.104.x:** Add manifest generation (no client changes)
2. **v26.105.x:** Add patch-check to updater (try patch first, fallback to full)
3. **v26.106.x:** Full patch system with UI
4. **v27.x:** Remove full-installer updates entirely

## Fallback Strategy

Always keep full installer as fallback:
- If patch fails → offer full installer
- If local state corrupted → full reinstall
- First install → full installer (obviously)

---

*Design created: 2026-01-04*
*Status: Ready for implementation*
