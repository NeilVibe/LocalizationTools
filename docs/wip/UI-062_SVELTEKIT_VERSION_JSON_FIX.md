# UI-062: SvelteKit version.json Fix

**Created:** 2025-12-28 | **Status:** PLANNING

---

## Problem Statement

In Electron with file:// protocol, SvelteKit's internal version check fails:
- Error: `net::ERR_FILE_NOT_FOUND` for `file:///C:/_app/version.json`
- The app tries to fetch `/_app/version.json` which resolves to `C:/_app/version.json`
- Should resolve relative to the app directory

## Technical Analysis

### Root Cause

SvelteKit's runtime code in `build/_app/immutable/chunks/*.js`:
```javascript
const Ut = globalThis.__sveltekit_dworcj?.assets ?? A ?? "";
// Later in version check function:
const r = await fetch(`${Ut}/_app/version.json`, {
  headers: { pragma: "no-cache", "cache-control": "no-cache" }
});
```

- `Ut` (assets base URL) is empty string in file:// mode
- Fetch to `/_app/version.json` becomes absolute path `file:///C:/_app/version.json`
- The file exists at `build/_app/version.json` but the path is wrong

### What version.json Does

```json
{"version":"1766842353946"}
```

- SvelteKit uses this for cache invalidation
- Compares local version hash with server version
- If different, triggers app refresh for new version
- **Non-critical** for Electron (no server, no hot updates)

## Solution Options

### Option 1: Intercept fetch in preload.js (RECOMMENDED)
**Complexity:** Low | **Risk:** Low | **Effectiveness:** High

Override `window.fetch` before app loads to intercept `/_app/version.json` requests.

```javascript
// In preload.js - intercept before SvelteKit loads
const originalFetch = window.fetch;
window.fetch = function(url, options) {
  // Intercept SvelteKit version check
  if (url.includes('/_app/version.json')) {
    // Return success with dummy version (caching not needed in Electron)
    return Promise.resolve(new Response(
      JSON.stringify({ version: "electron-local" }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ));
  }
  return originalFetch.call(this, url, options);
};
```

**Pros:**
- Clean, minimal change
- No build process changes
- Easy to understand and maintain

**Cons:**
- Disables version checking entirely (fine for Electron)

### Option 2: Protocol handler in main.js
**Complexity:** Medium | **Risk:** Medium | **Effectiveness:** High

Register custom protocol or intercept file:// requests.

```javascript
// In main.js
const { protocol } = require('electron');

protocol.interceptFileProtocol('file', (request, callback) => {
  const url = request.url.replace('file:///', '');
  if (url.includes('_app/version.json')) {
    callback({ path: path.join(__dirname, '../build/_app/version.json') });
  } else {
    callback({ url: request.url });
  }
});
```

**Pros:**
- Actually loads the real version.json
- Proper file resolution

**Cons:**
- More complex
- Modifies Electron's default behavior

### Option 3: Post-build script
**Complexity:** High | **Risk:** High | **Effectiveness:** High

Modify the built JS to use relative paths.

**Pros:**
- Fixes at source

**Cons:**
- Fragile (breaks on SvelteKit updates)
- Complex regex/AST manipulation
- Build process dependency

## Recommended Approach

**Option 1: Intercept fetch in preload.js**

Reasons:
1. Minimal code change
2. Electron doesn't need version checking anyway
3. No side effects
4. Easy to maintain
5. Doesn't require build process changes

## Implementation Plan

### Phase 1: Preparation (This Commit)
1. Create this documentation
2. Update ISSUES_TO_FIX.md with plan
3. Commit as "STABLE PREPARATION"

### Phase 2: Implementation
1. Modify `electron/preload.js`
2. Add fetch interceptor for `/_app/version.json`
3. Return mock response with stable version

### Phase 3: Verification
1. Build the app
2. Test in Electron
3. Verify no console error
4. Document findings

## Success Criteria

- [ ] No `net::ERR_FILE_NOT_FOUND` for version.json
- [ ] App functions normally
- [ ] Update checking (via electron-updater) still works
- [ ] No performance impact

---

## Findings & Learnings

### SvelteKit + Electron Architecture Notes

1. **SvelteKit's Static Adapter** outputs to `build/` directory
2. **Assets** are in `build/_app/` with versioned filenames
3. **file:// protocol** doesn't support relative root paths like `/_app/`
4. **Electron preload** runs before page content, ideal for patching

### Key Files

| File | Purpose |
|------|---------|
| `locaNext/build/_app/version.json` | SvelteKit version hash |
| `locaNext/build/_app/immutable/chunks/*.js` | SvelteKit runtime with version check |
| `locaNext/svelte.config.js` | Already has `paths: { relative: true }` |
| `locaNext/electron/preload.js` | Where we'll add the fix |

### Why `paths: { relative: true }` Isn't Enough

The config only affects static imports and asset paths. The version.json fetch is done dynamically at runtime using a hardcoded path pattern.

---

*Document created for UI-062 resolution*
