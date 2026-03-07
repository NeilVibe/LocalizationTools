# QuickTranslate Developer Guide

Build, CI/CD, and development reference.

---

## 1. Project Structure

```
QuickTranslate/
├── main.py                    ← Entry point (GUI launch, --smoke-test flag)
├── config.py                  ← Paths, matching modes, language discovery, settings I/O
├── QuickTranslate.spec        ← PyInstaller build spec
├── requirements.txt           ← Core deps (lxml, openpyxl, xlsxwriter)
├── requirements-ml.txt        ← ML deps (model2vec, faiss-cpu, numpy)
├── QUICKTRANSLATE_BUILD.txt   ← CI trigger file (edit + push = build)
├── core/                      ← Business logic
│   ├── matching.py            ← Shared utilities (format_multiple_matches)
│   ├── xml_transfer.py        ← TRANSFER: merge corrections into target XML
│   ├── xml_parser.py          ← XML parsing (lxml with ElementTree fallback)
│   ├── xml_io.py              ← XML read/write utilities
│   ├── excel_io.py            ← Excel read/write, column detection, output generation
│   ├── source_scanner.py      ← Auto-recursive language detection from folder/file names
│   ├── language_loader.py     ← Load languagedata_*.xml into indexes
│   ├── indexing.py            ← StringID/StrOrigin index builders
│   ├── eventname_resolver.py  ← EventName → StringID 3-step waterfall
│   ├── missing_translation_finder.py ← Find Missing Translations engine
│   ├── checker.py             ← Check Korean + Check Patterns
│   ├── quality_checker.py     ← Wrong script + AI hallucination detection
│   ├── korean_detection.py    ← Unicode-range Korean text detection
│   ├── text_utils.py          ← Normalization helpers
│   ├── fuzzy_matching.py      ← Model2Vec + FAISS HNSW fuzzy StrOrigin matching
│   ├── category_mapper.py     ← StringID → EXPORT category mapping
│   ├── postprocess.py         ← Golden rule enforcement (empty StrOrigin → empty Str)
│   ├── failure_report.py      ← Excel failure report + fuzzy match report generation
│   └── __init__.py            ← Public API re-exports
├── gui/
│   ├── app.py                 ← Main tkinter GUI (all buttons, layout, event handlers)
│   ├── missing_params_dialog.py ← Find Missing parameter dialog (match mode, threshold)
│   ├── exclude_dialog.py      ← Folder exclusion dialog for Find Missing
│   └── __init__.py
├── utils/
│   └── file_io.py             ← Text file reading utility
├── installer/
│   └── QuickTranslate.iss     ← Inno Setup script
├── docs/
│   ├── USER_GUIDE.md          ← End-user documentation
│   ├── DEV_GUIDE.md           ← This file
│   ├── LINEBREAK_SAFEGUARDS.md ← <br/> pipeline: golden rules, 3-layer defense, all functions
│   ├── PYINSTALLER_ML_BUNDLING.md ← Historical PyInstaller + ML DLL investigation
│   └── FAISS_IMPLEMENTATION.md
└── archive/                   ← Deprecated/legacy code (excluded from builds)
```

---

## 2. CI/CD Pipeline

**Workflow file:** `LocalizationTools/.github/workflows/quicktranslate-build.yml`

### Triggers

- **Push:** Any commit that changes `QUICKTRANSLATE_BUILD.txt` (the trigger file)
- **Manual:** GitHub Actions → workflow_dispatch (with optional "skip safety" input)

### Version Format

`YY.Mdd.HHmm` in KST (Asia/Seoul). Example: `26.212.1430` = 2026 Feb 12, 14:30 KST.

### 3-Job Pipeline

```
Job 1: Validation (ubuntu)
  ├── Check build trigger (QUICKTRANSLATE_BUILD.txt changed or manual dispatch)
  └── Generate version string (KST timestamp)

Job 2: Safety Checks (ubuntu)
  ├── Python syntax validation (py_compile on all .py files)
  ├── Module import validation (config, core, utils)
  ├── Full application test (all module imports)
  ├── Flake8 critical errors (E9, F63, F7, F82 — fails build)
  └── pip-audit security scan (advisory, doesn't fail build)

Job 3: Build & Release (windows)
  ├── Install deps: requirements.txt + ML deps (model2vec, faiss-cpu, numpy) + PyInstaller
  ├── Verify ML deps (model2vec, faiss, numpy importable)
  ├── PyInstaller build (QuickTranslate.spec)
  ├── Post-build verification:
  │   ├── QuickTranslate.exe exists
  │   ├── _internal/ directory exists (clean layout)
  │   └── No DLLs in root (only exe + _internal/)
  ├── Smoke test: run actual exe with --smoke-test (all imports verified)
  ├── Build size gate: must be < 500 MB (Model2Vec builds are ~160 MB)
  ├── Inno Setup installer build
  ├── Create Portable.zip + Source.zip
  └── GitHub Release (tag: quicktranslate-vX.X.X)
```

### Release Artifacts

| Artifact | Contents |
|----------|---------|
| `QuickTranslate_vX.X.X_Setup.exe` | Windows installer (Inno Setup, drive selection) |
| `QuickTranslate_vX.X.X_Portable.zip` | Standalone exe + `_internal/` + working folders |
| `QuickTranslate_vX.X.X_Source.zip` | Python source (excludes dist/build/__pycache__/archive) |

---

## 3. PyInstaller Build

### Critical Rule

**Use `hiddenimports` for packages with native DLLs. Use `collect_all` only for pure-Python packages.**

See `docs/PYINSTALLER_ML_BUNDLING.md` for the full historical investigation.

| Package | collect_all? | Why |
|---------|:-----------:|-----|
| numpy, faiss, tokenizers, safetensors | **No** | Native DLLs — must be flat |
| model2vec | **No** | Has native deps, keep flat |
| requests, urllib3, certifi | **Yes** | Pure Python — needs configs/certs |

### No Runtime Hook Needed

With Model2Vec (no torch), there's no complex DLL chain to manage. PyInstaller's standard binary analysis handles all native deps correctly.

### Crash Logging

With `console=False` (GUI app), errors are invisible. `main.py` redirects stderr to `QuickTranslate_crash.log` when running as a frozen exe. Unhandled exceptions also show a tkinter error dialog.

### Smoke Test

`python main.py --smoke-test` (or the built exe with `--smoke-test`) tests all critical imports inside the actual bundle. CI verifies `SMOKE_TEST_PASSED` appears in output.

---

## 4. How to Trigger a Build

### Method 1: Edit Trigger File (Standard)

```bash
# Edit QUICKTRANSLATE_BUILD.txt (content doesn't matter, just needs a change)
echo "build $(date)" >> QUICKTRANSLATE_BUILD.txt
git add QUICKTRANSLATE_BUILD.txt
git commit -m "Trigger QuickTranslate build"
git push
```

CI detects the file change and starts the 3-job pipeline. Check the Releases page for output.

### Method 2: Manual Dispatch

GitHub → Actions → "QuickTranslate Build & Release" → Run workflow. Optional: check "Skip safety checks" (not recommended).

---

## 5. Local Development

### Requirements

- Python 3.11+
- Core: `pip install -r requirements.txt` (lxml, openpyxl, xlsxwriter)
- ML (optional, for fuzzy matching): `pip install -r requirements-ml.txt` (model2vec, faiss-cpu, numpy)
- Fuzzy matching also needs the `Model2Vec/` model folder next to the app

### Run

```bash
python main.py              # Launch GUI
python main.py --smoke-test # Test all imports and exit
python main.py --verbose    # Debug logging
```

### Testing

The smoke test (`--smoke-test`) is the primary validation. It tests all critical imports that have caused runtime failures in the past. No separate test suite — the app is validated through the CI smoke test on the actual built executable.

### Code Conventions

- Python 3.11+, PEP 8
- `from __future__ import annotations` in every `.py` file
- Type hints on function signatures
- `lxml` preferred, `xml.etree.ElementTree` fallback (checked at import time)
- All config in `config.py` (paths, matching modes, language lists)
- Column detection is always case-insensitive via `_detect_column_indices()`
- Korean text detection via Unicode range checks (`korean_detection.py`)
- **Linebreak handling:** See `docs/LINEBREAK_SAFEGUARDS.md` for the complete `<br/>` pipeline (golden rules, boundary conversions, three-layer defense)
