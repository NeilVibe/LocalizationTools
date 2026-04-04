# LocaNext Testing Toolkit

**Autonomous Multi-Dimensional Testing System for LocaNext**

---

## 📁 Structure (NEW - 2025-12-11)

```
testing_toolkit/
├── README.md                    # This file
├── ADD_TEST_MODE_GUIDE.md       # How to add TEST MODE to apps
├── TEST_FILES_MANIFEST.md       # Required test files
├── test_qwen_faiss.py          # ⭐ NEW: Qwen + FAISS integration test
│
├── cdp/                         # ⭐ Organized CDP tests
│   ├── utils/
│   │   └── cdp-client.js       # Shared CDP connection utility
│   ├── apps/                    # Per-app test suites
│   │   ├── xlstransfer/        # XLSTransfer tests
│   │   ├── quicksearch/        # QuickSearch tests
│   │   ├── krsimilar/          # KR Similar tests
│   │   └── ldm/                # ⭐ LDM tests
│   │       └── test_file_upload.js
│   └── runners/
│       └── run_test.js         # CLI test runner
│
├── scripts/                     # Legacy scripts
│   ├── run_test.js             # Single test runner (old)
│   └── run_all_tests.js        # Full test suite (old)
│
├── setup/                       # Setup scripts
│   ├── check_prerequisites.sh
│   └── launch_and_test.sh
│
└── test-data/                   # Test files
```

---

## 🎯 Multi-Dimensional Testing (NEW)

| Dimension | Environment | Command | Use Case |
|-----------|-------------|---------|----------|
| **DEV** | API only | `node test.js dev` | Backend validation |
| **APP** | electron:dev | `node test.js app` | Development testing |
| **EXE** | LocaNext.exe | `node test.js exe` | Production validation |

### Why 3 Dimensions?

```
┌─────────────────────────────────────────────────────────────────┐
│  DEV                  APP                   EXE                 │
│  (Backend Only)       (Dev Mode)            (Production)        │
│                                                                 │
│  ┌──────────┐        ┌──────────┐          ┌──────────┐        │
│  │ curl/API │        │ Electron │          │ LocaNext │        │
│  │ requests │        │ + DevTools│          │   .exe   │        │
│  └────┬─────┘        └────┬─────┘          └────┬─────┘        │
│       │                   │                     │               │
│       ▼                   ▼                     ▼               │
│  ┌──────────┐        ┌──────────┐          ┌──────────┐        │
│  │ Backend  │        │ Backend  │          │ Backend  │        │
│  │ :8888    │        │ :8888    │          │ :8888    │        │
│  └──────────┘        └──────────┘          └──────────┘        │
│                                                                 │
│  Tests:              Tests:                Tests:               │
│  - API endpoints     - UI rendering        - Full integration   │
│  - Data parsing      - Navigation          - File paths         │
│  - Auth flow         - Component state     - Windows compat     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

**CRITICAL:** CDP tests must run from **Windows PowerShell**, not WSL. CDP binds to Windows localhost which WSL2 cannot reach.

### Step 1: Launch App (from WSL)

```bash
# Kill existing and launch
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T 2>/dev/null
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &
```

### Step 2: Run CDP Tests (from Windows PowerShell)

```powershell
# Access test scripts via UNC path
Push-Location '\\wsl.localhost\Ubuntu2\home\<USERNAME>\LocalizationTools\testing_toolkit\cdp'

# Login and test
node login.js
node quick_check.js
node test_server_status.js
node test_bug029.js
```

### Alternative: Pure Windows

```cmd
cd D:\LocalizationTools\testing_toolkit\cdp
node login.js && node quick_check.js
```

---

## 🧪 Available Tests

### LDM (LanguageData Manager) - NEW

| Test | File | What it Tests |
|------|------|---------------|
| File Upload | `cdp/apps/ldm/test_file_upload.js` | Upload TXT/XML, parse rows |

### XLSTransfer

| Function | Command | Time |
|----------|---------|------|
| createDictionary | `node run_test.js xlsTransfer.createDictionary` | ~20s |
| loadDictionary | `node run_test.js xlsTransfer.loadDictionary` | ~5s |
| translateExcel | `node run_test.js xlsTransfer.translateExcel` | ~10s |
| getStatus | `node run_test.js xlsTransfer.getStatus` | instant |

### QuickSearch

| Function | Command | Time |
|----------|---------|------|
| loadDictionary | `node run_test.js quickSearch.loadDictionary` | ~15s |
| search | `node run_test.js quickSearch.search` | ~5s |
| getStatus | `node run_test.js quickSearch.getStatus` | instant |

### KR Similar

| Function | Command | Time |
|----------|---------|------|
| loadDictionary | `node run_test.js krSimilar.loadDictionary` | ~45s |
| search | `node run_test.js krSimilar.search` | ~10s |
| getStatus | `node run_test.js krSimilar.getStatus` | instant |

---

## 🔧 CDP Client API

```javascript
const {
    connect,         // Connect to CDP
    evaluate,        // Run JS in page
    navigateToApp,   // Switch app (ldm, xlstransfer, etc.)
    waitForSelector, // Wait for DOM element
} = require('./utils/cdp-client');

// Example
const cdp = await connect();
await navigateToApp(cdp, 'ldm');
const result = await evaluate(cdp, 'window.ldmTest.getStatus()');
```

---

## Troubleshooting

### CDP not accessible
```powershell
# From Windows PowerShell (NOT WSL!)
curl http://127.0.0.1:9222/json

# Or from WSL, use Windows curl:
/mnt/c/Windows/System32/curl.exe -s http://127.0.0.1:9222/json
```

### Kill stuck processes
```bash
# From WSL
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe /T
```

### Test files not found
```bash
ls -la /mnt/d/TestFilesForLocaNext/
```

---

## 🧠 ML/Embedding Tests

### Qwen + FAISS Integration Test

Tests the full embedding pipeline for KR Similar and LDM TM:

```bash
python3 testing_toolkit/test_qwen_faiss.py
```

**What it tests:**
| Test | Description |
|------|-------------|
| Library Imports | PyTorch, FAISS, SentenceTransformers |
| Qwen Model Loading | Qwen3-Embedding-0.6B (1024-dim) |
| Embedding Generation | Batch encoding performance |
| FAISS HNSW Index | Index creation and configuration |
| Similarity Search | Cross-lingual KR↔EN matching |
| KR Similar Integration | Module imports, dictionary listing |
| LDM TM Integration | Fallback text search |
| Batch Performance | Throughput benchmarking |

**Expected output:**
```
Total: 8/8 passed
[SUCCESS] All Qwen + FAISS tests passed!
```

**Note:** Existing BDO dictionary (768-dim KR-SBERT) needs rebuild for Qwen (1024-dim).

---

## 🎨 Svelte 5 UIUX Testing

### Philosophy: Auto-Adaptive UI

Modern UI should **adapt automatically** - no hardcoded pixel widths for main content.

| Principle | Implementation | Verification |
|-----------|----------------|--------------|
| **Percentage widths** | `style="flex: 0 0 {percent}%"` | Resize window, columns adapt |
| **Reactive state** | `let width = $state(50)` | Change state, UI updates instantly |
| **Clear separators** | `border-right: 2px solid` | Visible line between columns |
| **No clutter** | Remove pagination, footers | Screenshot shows clean UI |

### Visual Verification Protocol

**See:** [MASTER_TEST_PROTOCOL.md - Phase 6](MASTER_TEST_PROTOCOL.md#phase-6-ai-visual-verification-protocol)

1. **Take screenshot** via CDP
2. **Read image** (Claude can analyze PNGs)
3. **Verify fix** is visible
4. **Document proof** in ISSUES_TO_FIX.md

### AI State of Mind

When verifying UIUX fixes:

```
1. Be skeptical  - Code changes ≠ working UI
2. Be visual     - Screenshots reveal user experience
3. Be thorough   - Test edge cases
4. Be precise    - Document exactly what changed
5. Be demanding  - Require proof before marking VERIFIED
```

### Example: Column Layout Test

```javascript
// Get layout info via CDP
const layoutInfo = await Runtime.evaluate({
    expression: `
        const cells = document.querySelectorAll('.cell');
        return Array.from(cells).map(c => ({
            class: c.className,
            left: c.getBoundingClientRect().left,
            width: c.getBoundingClientRect().width
        }));
    `
});

// Verify: columns adjacent, no gaps, fill width
```

---

## Related Docs

| Doc | Description |
|-----|-------------|
| [cdp/README.md](cdp/README.md) | CDP testing guide (primary) |
| [MASTER_TEST_PROTOCOL.md](MASTER_TEST_PROTOCOL.md) | Complete Build → Install → Test workflow |
| [ADD_TEST_MODE_GUIDE.md](ADD_TEST_MODE_GUIDE.md) | Add TEST MODE to new apps |
| [docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed install process |

---

*Updated: 2025-12-21 | Build 312 (VERIFIED)*
