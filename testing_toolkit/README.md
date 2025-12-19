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

## 🚀 Quick Start

### NEW: Multi-Dimensional Tests

```bash
# Install dependencies
cd testing_toolkit/cdp
npm install ws

# Test LDM file upload in DEV mode (API only)
node apps/ldm/test_file_upload.js dev

# Test in APP mode (need electron:dev + CDP)
cd locaNext && npm run electron:dev -- --remote-debugging-port=9222 &
cd testing_toolkit/cdp
node apps/ldm/test_file_upload.js app

# Test in EXE mode (need LocaNext.exe + CDP)
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &
cd ~/LocalizationTools/testing_toolkit/cdp
node apps/ldm/test_file_upload.js exe
```

### Legacy Tests (still work)

```bash
cd testing_toolkit/scripts
npm install

# Run all tests
bash ../setup/launch_and_test.sh

# Run specific test
node run_test.js xlsTransfer.createDictionary
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

## 🔍 Troubleshooting

### CDP not accessible
```bash
# Check if app is running with CDP
curl http://localhost:9222/json
```

### Kill stuck processes
```bash
# WSL
pkill -f LocaNext

# Windows
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
```

### Test files not found
```bash
ls -la /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/
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

## 📚 Related Docs

| Doc | Description |
|-----|-------------|
| [cdp/README.md](cdp/README.md) | CDP testing guide (primary) |
| [BUILD_TEST_PROTOCOL.md](BUILD_TEST_PROTOCOL.md) | Build → Test workflow |
| [ADD_TEST_MODE_GUIDE.md](ADD_TEST_MODE_GUIDE.md) | Add TEST MODE to new apps |
| [docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed install process |
| [docs/testing/README.md](../docs/testing/README.md) | Testing overview |

---

*Updated: 2025-12-19 | Build 300*
