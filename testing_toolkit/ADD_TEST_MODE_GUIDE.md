# Adding TEST MODE to New Apps

**Complete Guide for Future Claude Sessions**

This guide explains how to add autonomous testing capability to any new LocaNext app, enabling full CDP-based testing without human interaction.

---

## Overview

Every app in LocaNext should expose a `window.{appName}Test` object that allows:
1. Executing functions without file dialogs
2. Using predefined test files
3. Checking status via CDP

---

## Step-by-Step Implementation

### Step 1: Define TEST_CONFIG

At the top of your Svelte component, define test configuration:

```javascript
// ================================
// TEST MODE CONFIGURATION
// ================================

// Path to test files (Windows path format)
const TEST_FILES_PATH = 'D:\\TestFilesForLocaNext\\{AppName}';

const TEST_CONFIG = {
  // One config object per testable function
  functionOne: {
    file: `${TEST_FILES_PATH}\\test_file_1.xlsx`,
    sheet: 'Sheet1',
    // Add all parameters needed to skip the dialog
    param1: 'value1',
    param2: 'value2'
  },
  functionTwo: {
    file: `${TEST_FILES_PATH}\\test_file_2.txt`,
    // ... parameters
  }
};
```

### Step 2: Create Test State Object

Create a plain object for CDP access (Svelte reactivity doesn't work with CDP):

```javascript
// Test state for CDP access (bypasses Svelte reactivity)
const _testState = {
  isProcessing: false,
  statusMessage: '',
  lastResult: null
};
```

### Step 3: Create Test Functions

For each user-facing function, create a test version that skips dialogs:

```javascript
async function testFunctionOne() {
  logger.info('TEST MODE: Starting functionOne', TEST_CONFIG.functionOne);

  // Update both Svelte state AND test state
  isProcessing = true;
  _testState.isProcessing = true;
  _testState.statusMessage = 'TEST: Starting...';

  try {
    // Use TEST_CONFIG values instead of dialog results
    const testFile = TEST_CONFIG.functionOne.file;
    const params = {
      file: testFile,
      sheet: TEST_CONFIG.functionOne.sheet,
      param1: TEST_CONFIG.functionOne.param1
    };

    // Call the actual implementation
    const result = await doFunctionOne(params);

    // Update state with result
    _testState.lastResult = result;
    _testState.statusMessage = `TEST: Complete - ${result.count} items processed`;
    _testState.isProcessing = false;
    isProcessing = false;

    logger.info('TEST MODE: functionOne complete', { result });

  } catch (error) {
    _testState.statusMessage = `TEST ERROR: ${error.message}`;
    _testState.isProcessing = false;
    isProcessing = false;
    logger.error('TEST MODE: functionOne failed', { error: error.message });
  }
}
```

### Step 4: Expose via Window Object

At the end of your `<script>` section, expose the test interface:

```javascript
// ================================
// TEST MODE INTERFACE (CDP Access)
// ================================
if (typeof window !== 'undefined') {
  window.{appName}Test = {
    // Test functions (one per feature)
    functionOne: () => testFunctionOne(),
    functionTwo: () => testFunctionTwo(),
    functionThree: () => testFunctionThree(),

    // Status getter (always include this!)
    getStatus: () => ({
      isProcessing: _testState.isProcessing,
      statusMessage: _testState.statusMessage,
      lastResult: _testState.lastResult,
      // Add app-specific state
      isDictionaryLoaded: isDictionaryLoaded,
      currentFile: currentFile
    })
  };
}
```

### Step 5: Update CDP Test Runner

Add the new app to `testing_toolkit/scripts/run_test.js`:

```javascript
const TEST_FUNCTIONS = {
  // ... existing apps ...

  {appName}: {
    functionOne: 'window.{appName}Test.functionOne()',
    functionTwo: 'window.{appName}Test.functionTwo()',
    functionThree: 'window.{appName}Test.functionThree()',
    getStatus: 'JSON.stringify(window.{appName}Test.getStatus())'
  }
};
```

### Step 6: Update Full Test Suite

Add to `testing_toolkit/scripts/run_all_tests.js`:

```javascript
const ALL_TESTS = [
  // ... existing tests ...

  // {AppName}
  { app: '{appName}', func: 'functionOne', expr: 'window.{appName}Test.functionOne()', wait: 20, slow: false },
  { app: '{appName}', func: 'functionTwo', expr: 'window.{appName}Test.functionTwo()', wait: 10, slow: false, requires: 'functionOneDone' }
];

const STATUS_EXPRESSIONS = {
  // ... existing ...
  {appName}: 'JSON.stringify(window.{appName}Test.getStatus())'
};
```

### Step 7: Create Test Files

Create test files in `D:\TestFilesForLocaNext\{AppName}\`:

```
D:\TestFilesForLocaNext\{AppName}\
├── test_file_1.xlsx     ← For functionOne
├── test_file_2.txt      ← For functionTwo
└── README.txt           ← Document file structure
```

### Step 8: Update Manifest

Add to `testing_toolkit/TEST_FILES_MANIFEST.md`:

```markdown
### {AppName}

| File | Purpose | Structure | Size |
|------|---------|-----------|------|
| `test_file_1.xlsx` | FunctionOne test | Col A: Korean, Col B: Translation | ~100 rows |
| `test_file_2.txt` | FunctionTwo test | Tab-separated, UTF-8 | Small |
```

### Step 9: Document Test Commands

Update `docs/testing/AUTONOMOUS_TESTING_PROTOCOL.md`:

```markdown
### {AppName} (`window.{appName}Test`)

| Function | Test Command | Description | Status |
|----------|--------------|-------------|--------|
| functionOne | `window.{appName}Test.functionOne()` | Description here | ✅ Working |
| functionTwo | `window.{appName}Test.functionTwo()` | Description here | ✅ Working |
| Get Status | `window.{appName}Test.getStatus()` | Returns state | ✅ Working |
```

---

## Complete Example: LD Manager

Here's how TEST MODE would look for the future LD Manager (P17):

### TEST_CONFIG
```javascript
const LD_TEST_CONFIG = {
  loadFile: {
    file: 'D:\\TestFilesForLocaNext\\LDManager\\sample_language_data.txt',
    format: 'txt'
  },
  editCell: {
    row: 5,
    column: 'Str',
    newValue: 'Test Translation'
  },
  commitChanges: {
    targetFile: 'D:\\TestFilesForLocaNext\\LDManager\\target_file.txt',
    backup: true
  },
  runQA: {
    checks: ['lineCheck', 'termCheck', 'patternCheck']
  }
};
```

### Window Object
```javascript
window.ldManagerTest = {
  loadFile: () => testLoadFile(),
  editCell: () => testEditCell(),
  commitChanges: () => testCommitChanges(),
  runQA: () => testRunQA(),
  getStatus: () => ({
    isProcessing: _ldTestState.isProcessing,
    statusMessage: _ldTestState.statusMessage,
    fileLoaded: !!currentFile,
    rowCount: rowCount,
    modifiedCount: modifiedCells.length,
    lastCommitResult: _ldTestState.lastCommitResult
  })
};
```

### Test Files
```
D:\TestFilesForLocaNext\LDManager\
├── sample_language_data.txt    ← 1000-row test file
├── sample_language_data.xml    ← XML format test
├── target_file.txt             ← Commit target
└── expected_output.txt         ← For verification
```

---

## Checklist for New Apps

- [ ] `TEST_CONFIG` defined with all test parameters
- [ ] `_testState` object for CDP access
- [ ] Test function for each user-facing feature
- [ ] `window.{appName}Test` object exposed
- [ ] `getStatus()` function included
- [ ] Test files created in `D:\TestFilesForLocaNext\{AppName}\`
- [ ] `run_test.js` updated with new app
- [ ] `run_all_tests.js` updated with test sequence
- [ ] `TEST_FILES_MANIFEST.md` updated
- [ ] `AUTONOMOUS_TESTING_PROTOCOL.md` updated with commands table

---

## Testing Your Implementation

```bash
# 1. Launch app with CDP
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "Start-Process -FilePath 'D:\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'"

# 2. Wait for app
sleep 25

# 3. Test your new app
cd testing_toolkit/scripts
node run_test.js {appName}.functionOne --wait 30
node run_test.js {appName}.getStatus

# 4. Run full suite
node run_all_tests.js --app {appName}
```

---

## Common Patterns

### Pattern 1: File Loading Functions
```javascript
async function testLoadFile() {
  const testFile = TEST_CONFIG.loadFile.file;
  // Skip file dialog, load directly
  await loadFileInternal(testFile);
}
```

### Pattern 2: Functions Requiring Prior State
```javascript
async function testTranslate() {
  if (!isDictionaryLoaded) {
    _testState.statusMessage = 'TEST ERROR: Load dictionary first!';
    return;
  }
  // Proceed with test
}
```

### Pattern 3: Long-Running Operations
```javascript
async function testBuildEmbeddings() {
  // Use smaller test file for faster testing
  const testFile = TEST_CONFIG.buildEmbeddings.smallFile;  // 100 rows, not 40K
  // ...
}
```

### Pattern 4: Progress Updates
```javascript
// Update BOTH Svelte state and test state
const updateProgress = (message) => {
  statusMessage = message;
  _testState.statusMessage = message;
};
```

---

*Template created: 2025-12-07*
*For: Future Claude sessions adding new apps to LocaNext*
