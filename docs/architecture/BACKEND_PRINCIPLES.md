# Backend Principles

**Backend is Flawless** | **Wrapper Pattern** | **Design Philosophy**

---

## 🏛️ CORE PRINCIPLE: BACKEND IS FLAWLESS

**RULE:** Unless explicitly told "there is a bug in the backend", assume **ALL backend code is 100% FLAWLESS**

---

## 🎯 WHAT THIS MEANS

### Backend Code (`client/tools/xls_transfer/`, all Python modules):

- ✅ **PROVEN:** Thoroughly tested and working in production
- ✅ **COMPLETE:** All logic, algorithms, and processing is correct
- ❌ **DO NOT MODIFY:** Never change core backend functionality
- ✅ **ONLY WRAP:** Create API endpoints, GUI layers, integrations

---

## 🔧 YOUR JOB DURING MIGRATION

1. **Create wrapper layers** (API endpoints, GUI components, integrations)
2. **Call backend correctly** (use proper function names, parameters, types)
3. **Maintain clean structure** (organized routes, proper imports, clear separation)
4. **Add monitoring/logging** (comprehensive logging at wrapper layer)

---

## 📝 EXAMPLE: XLSTransfer API

### ✅ CORRECT: Wrapper calls backend properly

```python
from client.tools.xls_transfer import embeddings

split_dict, whole_dict, split_embeddings, whole_embeddings = embeddings.process_excel_for_dictionary(
    excel_files=file_list,
    progress_tracker=None
)
```

### ❌ WRONG: Modifying backend core

```python
# NEVER change these files unless user says "there's a bug in the backend"
# - client/tools/xls_transfer/core.py
# - client/tools/xls_transfer/embeddings.py
# - client/tools/xls_transfer/translation.py
```

---

## 🚨 IF YOU ENCOUNTER ERRORS

### Debugging Workflow:

1. ✅ Check your wrapper code (API endpoint, parameter mapping, function calls)
2. ✅ Verify you're calling backend functions correctly (names, parameters, types)
3. ❌ Do NOT assume backend is wrong
4. ❓ If truly stuck, ask user: "Should I modify the backend, or is this a wrapper issue?"

---

## 🔍 THE WRAPPER PATTERN

### Layer Architecture:

```
┌─────────────────────────────────────────┐
│ GUI Layer (Svelte/Electron)            │
│ - User interactions                     │
│ - File selections                       │
│ - Button clicks                         │
└─────────────────────────────────────────┘
              ↓ IPC or HTTP
┌─────────────────────────────────────────┐
│ API/Wrapper Layer (FastAPI/Scripts)    │
│ - Validate inputs                       │
│ - Transform data formats                │
│ - Add logging/monitoring                │
│ - Error handling                        │
└─────────────────────────────────────────┘
              ↓ Function calls
┌─────────────────────────────────────────┐
│ Backend Core (FLAWLESS - DO NOT TOUCH) │
│ - Business logic                        │
│ - Algorithms                            │
│ - Data processing                       │
└─────────────────────────────────────────┘
```

---

## 📋 WRAPPER LAYER RESPONSIBILITIES

### Input Validation:
```python
# Wrapper validates before calling backend
if not excel_files:
    raise ValueError("No Excel files provided")

for file_path in excel_files:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

# Now call backend (which is FLAWLESS)
result = backend.process_files(excel_files)
```

### Data Transformation:
```python
# Wrapper transforms API format → Backend format
api_selections = {
    "file1.xlsx": {"Sheet1": {"kr": "A", "trans": "B"}}
}

# Transform to backend expected format
backend_selections = transform_selections(api_selections)

# Call backend with correct format
result = backend.create_dictionary(backend_selections)
```

### Error Handling:
```python
# Wrapper adds comprehensive error handling
try:
    result = backend.process_files(files)
    logger.success("Processing completed", {"file_count": len(files)})
except Exception as e:
    logger.error("Processing failed", {"error": str(e)})
    raise HTTPException(status_code=500, detail=str(e))
```

---

## ⚠️ CRITICAL: SACRED CODE COMPONENTS

**NEVER CHANGE WITHOUT EXPLICIT USER APPROVAL:**

### XLSTransfer Backend:
- `clean_text()` in `core.py:103` - Removes `_x000D_` (critical for Excel exports)
- `simple_number_replace()` in `core.py:253` - Preserves game codes like `{ItemID}`
- `analyze_code_patterns()` in `core.py:336` - Detects game code patterns
- `generate_embeddings()` in `embeddings.py:80` - 768-dim Korean BERT embeddings
- `create_faiss_index()` in `embeddings.py:137` - FAISS IndexFlatIP with L2 normalization

### Model Configuration:
```python
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"  # Korean-specific BERT (768-dim)
# NEVER change this to any other model!
```

---

## 🧪 HOW TO VERIFY YOU HAVEN'T BROKEN ANYTHING

### 1. Check Backend Hasn't Changed:
```bash
# Verify model name is correct
grep -r "paraphrase-multilingual" locaNext/src/ client/
# Should return NOTHING! If found = you hallucinated!

# Check core functions
python3 -c "from client.tools.xls_transfer.core import simple_number_replace; \
print(simple_number_replace('{Code}Hi', 'Bye'))"
# Should output: {Code}Bye
```

### 2. Run Backend Tests:
```bash
# All backend unit tests must pass
python3 -m pytest tests/unit/test_xls_transfer*.py -v
```

### 3. Test via Wrapper:
```bash
# Test API endpoint (wrapper layer)
curl -X POST http://localhost:8888/api/v2/xlstransfer/test/translate-text \
  -H "Content-Type: application/json" \
  -d '{"text":"안녕하세요","threshold":0.99}'
```

---

## 📚 RELATED DOCUMENTATION

- **CLAUDE_AI_WARNINGS.md** - AI hallucination prevention (5 documented types)
- **XLSTransfer_Migration_Audit.md** - Complete audit of what was changed
- **XLSTRANSFER_GUIDE.md** - XLSTransfer complete reference
- **CODING_STANDARDS.md** - Coding rules and patterns
