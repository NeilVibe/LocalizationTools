# XLSTransfer Guide

**Dual-Mode Architecture** | **Browser + Electron** | **API Endpoints** | **GUI Features**

---

## 🎯 DUAL-MODE ARCHITECTURE

**IMPORTANT**: XLSTransfer uses ONE component that works in BOTH Browser and Electron modes!

### One Component, Two Modes:

- `locaNext/src/lib/components/apps/XLSTransfer.svelte` - Single source of truth
- Detects `isElectron` flag on mount
- **Browser Mode**: Uses API calls to backend (`/api/v2/xlstransfer/...`)
- **Electron Mode**: Uses IPC to Python scripts (`window.electron.executePython()`)
- **SAME Upload Settings Modal in both modes** ✅

### Why This Matters:
- ✅ Testing in browser = Testing production Electron app
- ✅ No surprises after building .exe
- ✅ Faster development (no Electron rebuild during testing)
- ✅ Full testing capability in WSL2 headless environment

---

## 🖥️ GUI FEATURES

### ✅ Multi-File Selection
- Native/browser file picker with `multiSelections` enabled
- Can select multiple Excel files at once

### ✅ Upload Settings Modal (lines 988-1029)
- Shows each file with all available sheets
- Per-sheet checkbox to enable/disable
- When sheet selected, shows:
  - "KR Column" text input (e.g., A, B, C)
  - "Translation Column" text input (e.g., D, E, F)
- Full validation (column letters, at least one sheet selected)

### ✅ Selections Data Structure
```javascript
selections = {
  "/path/to/file1.xlsx": {
    "Sheet1": { kr_column: "A", trans_column: "B" },
    "Sheet2": { kr_column: "C", trans_column: "D" }
  },
  "/path/to/file2.xlsx": {
    "Data": { kr_column: "A", trans_column: "E" }
  }
}
```

### ✅ 10 Buttons (Exact Replica of Original)
1. "Create dictionary" (lowercase 'd')
2. "Load dictionary"
3. "Transfer to Close" (initially disabled)
4. "최소 일치율" threshold entry (default: 0.99)
5. "STOP"
6. "Transfer to Excel" (initially disabled)
7. "Check Newlines"
8. "Combine Excel Files"
9. "Newline Auto Adapt"
10. "Simple Excel Transfer"

---

## 🔄 BACKEND INTEGRATION

### Electron Mode:
1. GUI opens Upload Settings modal
2. User selects sheets and enters column letters
3. Builds selections object
4. Calls Python script via IPC: `process_operation.py create_dictionary selections threshold`
5. Python processes each file/sheet/column combination

### Browser Mode:
1. GUI opens Upload Settings modal (SAME modal!)
2. User selects sheets and enters column letters
3. Builds selections object
4. Calls REST API: `POST /api/v2/xlstransfer/test/create-dictionary` with files + selections
5. Backend API processes via Python modules (same code as Electron!)

---

## 🌐 API ENDPOINTS

**Location:** `server/api/xlstransfer_async.py`

### Available Endpoints:
- `POST /api/v2/xlstransfer/test/create-dictionary` - Create dictionary (supports selections JSON)
- `POST /api/v2/xlstransfer/test/get-sheets` - Get sheet names from Excel file
- `POST /api/v2/xlstransfer/test/load-dictionary` - Load existing dictionary
- `POST /api/v2/xlstransfer/test/translate-text` - Translate single text
- `POST /api/v2/xlstransfer/test/translate-file` - Translate .txt or Excel file
- `GET /api/v2/xlstransfer/health` - Check module status

### Dual-Mode Implementation Status:
- ✅ Upload Settings Modal works in both Browser and Electron
- ✅ `openUploadSettingsGUI()` - Dual-mode (API for browser, IPC for Electron)
- ✅ `executeUploadSettings()` - Dual-mode (API for browser, Python for Electron)
- ✅ `/api/v2/xlstransfer/test/get-sheets` - Get Excel sheet names (browser mode)
- ✅ `/api/v2/xlstransfer/test/create-dictionary` - Accepts selections parameter
- ✅ Browser testing = Electron production testing

---

## 🧩 BACKEND MODULES

**Template for all future tools** - Located in `server/tools/xlstransfer/`:

### Core Modules:
- `core.py` - 49 functions, core business logic
- `embeddings.py` - BERT + FAISS integration
- `translation.py` - Matching logic
- `excel_utils.py` - Excel operations

### Backend Scripts:
- `get_sheets.py` - Extract Excel sheet names
- `load_dictionary.py` - Load embeddings & FAISS index
- `process_operation.py` - 5 operations (539 lines)
- `translate_file.py` - .txt file translation
- `simple_transfer.py` - Simple transfer operations

---

## ⚠️ CRITICAL: SACRED CODE COMPONENTS

**NEVER CHANGE WITHOUT EXPLICIT USER APPROVAL:**

### Model Location & Name:
```python
# Local installation (ALREADY in project - do NOT download):
MODEL_PATH = "client/models/KR-SBERT-V40K-klueNLI-augSTS/"  # 447MB, fully installed
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"  # Korean-specific BERT (768-dim)

# NEVER use:
# - paraphrase-multilingual-MiniLM-L12-v2 ❌ WRONG
# - paraphrase-multilingual-mpnet-base-v2 ❌ WRONG
# - Any other model ❌ WRONG
```

### Core Algorithms (VERIFIED IDENTICAL TO ORIGINAL):
- `clean_text()` in `server/tools/xlstransfer/core.py:103` - Removes `_x000D_` (critical for Excel exports)
- `simple_number_replace()` in `core.py:253` - Preserves game codes like `{ItemID}`
- `analyze_code_patterns()` in `core.py:336` - Detects game code patterns
- `generate_embeddings()` in `embeddings.py:80` - 768-dim Korean BERT embeddings
- `create_faiss_index()` in `embeddings.py:137` - FAISS IndexFlatIP with L2 normalization
- Split/Whole mode logic - Based on newline count matching
- FAISS threshold: 0.99 default (configurable 0.80-1.00)

---

## 🧪 TESTING

**Ready for Full Testing:**
- All infrastructure complete
- Monitoring system ready (240+ log statements)
- Browser and Electron use identical workflow
- Test in browser → Build .exe → Ship to users

---

## 🚨 GUI RECONSTRUCTION HISTORY

**CRITICAL DISCOVERY (2025-11-09)**: Previous GUI had **hallucinated features** that didn't exist in original!

### What Was Wrong:
1. ❌ "Find Duplicate Entries" button - Didn't exist in original
2. ❌ "Check Space Consistency" - Didn't exist
3. ❌ "Merge Multiple Dictionaries" - Didn't exist
4. ❌ "Validate Dictionary Format" - Didn't exist
5. ❌ AI Model selector in GUI - Model should be hardcoded
6. ❌ Accordion UI layout - Original uses simple vertical layout
7. ❌ Wrong threshold default - Used 0.85, should be 0.99
8. ❌ Wrong button names - Capitalization errors

### Lesson Learned:
**ALWAYS compare against original source** when migrating UIs. Don't trust previous implementations without verification!

---

## 📚 Related Documentation

- **CLAUDE_AI_WARNINGS.md** - AI hallucination prevention guide
- **XLSTransfer_Migration_Audit.md** - Complete 13-section audit
- **ADD_NEW_APP_GUIDE.md** - Using XLSTransfer as template for new tools
