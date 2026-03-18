# Phase 42 Plan 01 Summary: Fix LDM Grid Regression

**Status:** COMPLETE
**Duration:** ~15 min

## Root Cause
Svelte 5 `$bindable()` cleanup race condition. When `openFileInGrid()` switched `$currentPage` to 'grid', FilesPage unmounted and its `bind:selectedFileId` cleanup reset `selectedFileId` to null before GridPage could read it.

## Fix
Changed GridPage to derive `fileId` and `fileName` from the `$openFile` navigation store (authoritative source set by `openFileInGrid()`) instead of relying solely on the prop from LDM.svelte's local state.

```javascript
// Before: fileId from prop only (race-vulnerable)
let { fileId = null, fileName = '' } = $props();

// After: fallback to openFile store
let { fileId: propFileId = null, fileName: propFileName = '' } = $props();
let fileId = $derived(propFileId ?? $openFile?.id ?? null);
let fileName = $derived(propFileName || $openFile?.name || $openFile?.original_filename || '');
```

## Files Modified
- `locaNext/src/lib/components/pages/GridPage.svelte` (lines 18-31)

## Verification
- API chain: all endpoints return 200 (platforms, projects, files, rows)
- Playwright: double-click file → grid shows rows with correct filename
- Screenshot: `phase42-plan01-grid-fix-verified.png`
