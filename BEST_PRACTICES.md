# Development Best Practices & Common Pitfalls

**Purpose**: Document lessons learned to avoid repeating mistakes across different apps and components.

**Organization**: Grouped by technology/layer for easy reference.

---

## Table of Contents
- [Svelte / Frontend](#svelte--frontend)
- [Python / Backend](#python--backend)
- [SQL / Database](#sql--database)
- [API / Network](#api--network)
- [Architecture](#architecture)

---

## Svelte / Frontend

### Modal State Management

**Problem**: Modals that accumulate stale data when reopened, causing bugs or displaying old selections.

**Root Cause**:
- Modal visibility (`showModal`) and modal data are separate state variables
- Closing modal (`showModal = false`) doesn't automatically clear the data
- Reopening shows leftover data from previous interactions

**Solution Pattern**:
```javascript
// ❌ BAD: Only toggling visibility
on:click:button--secondary={() => showModal = false}

// ✅ GOOD: Proper cleanup function
function closeModal() {
  logger.info("Closing modal");
  showModal = false;
  // Data cleared when reopening in openModal()
  // OR clear it here if needed immediately
}

async function openModal(params) {
  // ALWAYS clear/reset data at the START
  modalData = [];  // Clear old data

  // Then populate with fresh data
  for (const item of params) {
    // Process and add new data
    modalData = [...modalData, newItem];
  }

  showModal = true;
}

// In template
<Modal
  bind:open={showModal}
  on:click:button--secondary={closeModal}
  on:click:button--primary={executeModalAction}
>
```

**Key Principles**:
1. **Clear data at the START of open**, not at close
2. **Use dedicated close function** instead of inline `() => showModal = false`
3. **Log state changes** for debugging
4. **Never assume modal data is clean** - always reset

**Real Example**: `XLSTransfer.svelte:686-704`
- `closeUploadSettings()` only closes modal
- `openUploadSettingsGUI()` starts with `uploadSettingsData = []` to ensure clean state

**When to Apply**: Any modal that:
- Displays dynamic data from files/API
- Allows user selections/input
- Can be opened multiple times in one session

---

### Svelte Reactivity Triggers

**Problem**: Array/object mutations don't trigger reactive updates.

**Root Cause**: Svelte detects reactivity through assignments, not mutations.

**Solution Pattern**:
```javascript
// ❌ BAD: Mutations don't trigger updates
myArray.push(item);
myObject.property = value;

// ✅ GOOD: Reassignment triggers reactivity
myArray = [...myArray, item];
myArray = myArray.filter(x => x.id !== id);
myObject = { ...myObject, property: value };
```

**Real Example**: `XLSTransfer.svelte:788`
```javascript
// Was: uploadSettingsData.push(fileDataEntry); // ❌ No reactivity
uploadSettingsData = [...uploadSettingsData, fileDataEntry]; // ✅ Triggers update
```

**Reference**: [Svelte Reactivity Docs](https://svelte.dev/docs#component-format-script-2-assignments-are-reactive)

---

## Python / Backend

### Working Directory for File Operations

**Problem**: Python modules can't find files when called from different working directories.

**Root Cause**:
- Relative paths (`SplitExcelDictionary.pkl`) resolve from current working directory
- FastAPI server runs from project root, but may execute code that expects files elsewhere
- When `process_operation.py` is called via API, `os.getcwd()` is server directory, not where files are saved

**Solution Pattern**:
```python
# ❌ BAD: Assumes current directory has files
def my_operation():
    if not os.path.exists('MyFile.pkl'):
        raise FileNotFoundError("File not found")
    with open('MyFile.pkl', 'rb') as f:
        data = pickle.load(f)

# ✅ GOOD: Change to correct directory, then restore
def my_operation():
    original_cwd = os.getcwd()
    try:
        # Change to where files are actually located
        os.chdir('/path/to/project/root')

        if not os.path.exists('MyFile.pkl'):
            raise FileNotFoundError("File not found")
        with open('MyFile.pkl', 'rb') as f:
            data = pickle.load(f)
    finally:
        # Always restore original directory
        os.chdir(original_cwd)

# ✅ BETTER: Use absolute paths from config
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
DICT_FILE = PROJECT_ROOT / 'SplitExcelDictionary.pkl'

def my_operation():
    if not DICT_FILE.exists():
        raise FileNotFoundError(f"File not found: {DICT_FILE}")
    with open(DICT_FILE, 'rb') as f:
        data = pickle.load(f)
```

**Real Example**: `server/api/xlstransfer_async.py:607-617`
```python
# Change to project root (where dictionary files are)
original_cwd = os.getcwd()
try:
    os.chdir(project_root)
    logger.info(f"Changed working directory to: {project_root}")
    result = process_operation.translate_excel(path_selections, threshold)
finally:
    os.chdir(original_cwd)
```

**Key Principles**:
1. **Never assume working directory** - always verify or set it
2. **Use try/finally** to restore original directory
3. **Prefer absolute paths** from config when possible
4. **Log directory changes** for debugging

**When to Apply**:
- Calling legacy code that uses relative paths
- File operations in API endpoints
- Module functions that load/save files

---

## SQL / Database

*To be added as we encounter patterns*

---

## API / Network

*To be added as we encounter patterns*

---

## Architecture

### Dual-Mode Components (Electron + Browser)

**Principle**: Components should work identically in both Electron and Browser modes.

**Pattern**:
```javascript
if (isElectron) {
  // Electron: Call via IPC
  result = await window.electron.executePython({ ... });
} else {
  // Browser: Call via API
  result = await api.someEndpoint(files, params);
}

// Both paths should return same result structure
if (result.success) {
  // Handle success the same way
}
```

**Key Points**:
- Modal logic should be identical for both modes
- Only the data fetching layer differs (IPC vs HTTP)
- Test both paths thoroughly

---

## Contributing

When you discover a new pattern or fix a bug:

1. **Document it here** under the appropriate section
2. **Include**:
   - Problem description
   - Root cause
   - Code example (bad vs good)
   - Real file/line reference from our codebase
   - When to apply the pattern
3. **Keep it concise** - this is a quick reference, not a tutorial

---

**Last Updated**: 2025-11-09
