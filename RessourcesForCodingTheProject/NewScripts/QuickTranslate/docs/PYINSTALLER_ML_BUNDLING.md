# PyInstaller + ML Dependencies: Windows Build Guide

> **Hard-won knowledge from the QuickTranslate c10.dll WinError 1114 investigation (Feb 2026).**
> This document applies to ANY NewScripts tool that needs to bundle torch, sentence-transformers, FAISS, or similar ML packages with PyInstaller for Windows.

---

## The Problem

When bundling torch/FAISS/sentence-transformers into a PyInstaller exe, the app crashes on **fresh Windows machines** (no Visual C++ Redistributable installed) with:

```
WinError 1114: A dynamic link library (DLL) initialization routine failed.
Error loading C:\..._internal\torch\lib\c10.dll or one of its dependencies.
```

The app works fine on the developer's machine (which has VC++ Redist installed system-wide).

---

## Root Cause: `collect_all('torch')` Creates Subdirectory DLLs

### How PyInstaller Collects Dependencies

PyInstaller has two ways to include packages:

| Method | What it does | DLL placement |
|--------|-------------|--------------|
| `collect_all('torch')` | Copies ENTIRE torch directory tree | `_internal/torch/lib/c10.dll` (subdirectory) |
| `hiddenimports=['torch']` | Traces imports, binary analysis finds DLLs | `_internal/c10.dll` (flat, same dir as vcruntime) |

### Why Subdirectory DLLs Break on Fresh Machines

```
_internal/
  vcruntime140.dll     ← VC++ runtime lives HERE
  msvcp140.dll
  torch/
    lib/
      c10.dll          ← c10.dll depends on vcruntime140.dll
      torch_cpu.dll       but can't find it in PARENT directory!
```

On Windows, Python 3.8+ uses **secure DLL search** that ignores PATH for implicit DLL dependencies. When `c10.dll` loads and needs `vcruntime140.dll`, Windows only searches:
1. The directory where c10.dll lives (`torch/lib/`) - **NOT THERE**
2. System32 - **NOT THERE** (fresh machine, no VC++ Redist installed)
3. Directories registered via `os.add_dll_directory()` - only if set up correctly

On the dev machine it works because VC++ Redist is installed system-wide (in System32).

### Why `hidden-import` Works

With `hiddenimports=['torch']`, PyInstaller's binary analysis traces the dependency tree:
1. `torch/__init__.py` imports `torch._C`
2. `torch._C` is `_C.pyd` which depends on `c10.dll`, `torch_cpu.dll`
3. Binary analysis collects these as **flat binaries** in `_internal/`

Result:
```
_internal/
  vcruntime140.dll     ← Same directory!
  msvcp140.dll
  c10.dll              ← Can find vcruntime140.dll!
  torch_cpu.dll
  torch_python.dll
```

**All DLLs in the same directory = Windows loader finds everything.**

---

## The Battle-Tested Pattern

This is the PyInstaller command used for XLSTransfer and KRSimilar monolith builds:

```bash
pyinstaller --clean --onefile --console \
  --hidden-import="tqdm" \
  --hidden-import="regex" \
  --hidden-import="requests" \
  --hidden-import="packaging" \
  --hidden-import="filelock" \
  --hidden-import="numpy" \
  --hidden-import="tokenizers" \
  --hidden-import="torch" \
  --copy-metadata="tqdm" \
  --copy-metadata="regex" \
  --copy-metadata="requests" \
  --copy-metadata="packaging" \
  --copy-metadata="filelock" \
  --copy-metadata="numpy" \
  --copy-metadata="tokenizers" \
  --copy-metadata="torch" \
  MyScript.py
```

Key points:
- `--hidden-import` for ML packages (NOT `collect_all`)
- `--copy-metadata` for packages that check their own version at runtime
- No runtime hook needed (DLLs are flat)

---

## The .spec File Pattern (QuickTranslate Solution)

For a GUI app with a `.spec` file, translate the command-line pattern:

### Strategy 1: hidden-import + copy-metadata (packages with DLLs)

```python
from PyInstaller.utils.hooks import copy_metadata

# Packages with native DLLs/extensions - let binary analysis place them flat
METADATA_PACKAGES = [
    'torch', 'numpy', 'tqdm', 'regex', 'requests',
    'packaging', 'filelock', 'tokenizers',
    'faiss-cpu', 'sentence-transformers', 'transformers',
    'huggingface-hub', 'safetensors',
]

ml_datas = []
for pkg in METADATA_PACKAGES:
    try:
        ml_datas += copy_metadata(pkg)
    except Exception:
        pass  # Some packages may not have metadata
```

### Strategy 2: collect_all (ONLY pure-Python packages with data files)

```python
from PyInstaller.utils.hooks import collect_all

# ONLY pure-Python packages that need JSON configs, vocab files, etc.
# NEVER use collect_all for packages with DLLs (torch, numpy, faiss, tokenizers)
COLLECT_ALL_PACKAGES = [
    'sentence_transformers',  # Needs config JSONs, model configs
    'transformers',           # Needs tokenizer vocabs, config files
    'huggingface_hub',        # Needs config files
]

for pkg in COLLECT_ALL_PACKAGES:
    d, b, h = collect_all(pkg)
    ml_datas += d
    ml_binaries += b
    ml_hiddenimports += h
```

### Hidden imports list

```python
hiddenimports=[
    # ML packages (Strategy 1 - flat DLL placement)
    'torch',
    'numpy',
    'safetensors',
    'safetensors.torch',
    'tokenizers',
    'tqdm', 'tqdm.auto',
    'regex',
    'requests',
    'packaging', 'packaging.version',
    'filelock',
    'typing_extensions',
    'yaml',
    # FAISS (import name != distribution name)
    'faiss',
    'faiss.swigfaiss',
    'faiss.swigfaiss_avx2',
    'faiss.loader',
    # ... your app's own modules
]
```

### Torch size optimization

```python
excludes=[
    'scipy', 'scikit-learn', 'matplotlib', 'pandas',
    # CPU-only app - exclude CUDA/unused torch subpackages
    'torch.distributed', 'torch.testing', 'torch.cuda',
    'torch.backends.cudnn', 'torch.onnx',
    'torch.utils.tensorboard', 'torch._dynamo',
    'torch.compiler', 'torch.fx',
]
```

### Disable UPX

```python
exe = EXE(..., upx=False)     # Avoid AV false positives
coll = COLLECT(..., upx=False) # Never compress DLLs
```

---

## Runtime Hook (Safety Net)

Even with flat DLL placement, keep a runtime hook as defense-in-depth.
File: `runtime_hook_torch.py`

### Three layers of defense:

1. **Layer A: `os.add_dll_directory()` with saved handles**
   - Register `_internal/` and `torch/lib/` (if it exists)
   - Save handles in a global list to prevent garbage collection
   - GC of handles = directory removed from search path!

2. **Layer B: PATH modification**
   - Fallback for legacy DLL search

3. **Layer C: Pre-load DLLs via `ctypes.WinDLL()`**
   - Load vcruntime140.dll, c10.dll etc. into process memory
   - Once loaded, Windows finds them by base name for any dependent DLL
   - Search BOTH `_internal/` and `torch/lib/` (in case DLLs end up in either)

### Critical DLLs to pre-load:
```python
runtime_dlls = [
    'vcruntime140.dll',      # VC++ runtime
    'vcruntime140_1.dll',    # VC++ runtime (C++ exceptions)
    'msvcp140.dll',          # C++ standard library
    'concrt140.dll',         # Concurrency Runtime (torch parallel)
    'libiomp5md.dll',        # Intel OpenMP (may be in _internal/ OR torch/lib/)
    'vcomp140.dll',          # MSVC OpenMP
]
```

### Diagnostic logging:
```python
def _hook_warn(msg):
    """Write to stderr. Invisible with console=False but captured in debug mode."""
    try:
        print(f"[runtime_hook_torch] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass
```

---

## CI Workflow: CPU-Only Torch

### Pip install order (CRITICAL)

```yaml
# Step 1: CPU-only torch FIRST (from PyTorch's dedicated index)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Step 2: ML deps. Torch is already satisfied, pip won't re-download.
# DO NOT use --extra-index-url (pip can find CUDA torch on PyPI and override!)
pip install sentence-transformers faiss-cpu numpy

# Step 3: Build tools (with hooks-contrib for better torch hooks)
pip install "pyinstaller>=6.0,<7.0" pyinstaller-hooks-contrib
```

### Verification (MUST PASS)

```yaml
python -c "
import torch
v = torch.__version__
assert '+cpu' in v, f'FATAL: Expected CPU-only torch, got {v}'
print(f'torch {v} - CPU-only confirmed')
"
```

### Why `--extra-index-url` is dangerous:
- `pip install sentence-transformers --extra-index-url https://download.pytorch.org/whl/cpu`
- `--extra-index-url` ADDS the CPU index but doesn't make it primary
- pip may find a "newer" CUDA torch on PyPI and silently replace CPU torch
- Result: ~2.5GB CUDA torch instead of ~200MB CPU torch

---

## Crash Logging (console=False)

With `console=False` (GUI app), errors are invisible. Add crash logging:

```python
# In main.py, at startup:
if getattr(sys, 'frozen', False):
    _crash_log = BASE_DIR / "QuickTranslate_crash.log"
    try:
        sys.stderr = open(str(_crash_log), 'a', encoding='utf-8')
    except Exception:
        pass

# In the main() exception handler:
except Exception as e:
    # Write to crash log
    with open(str(BASE_DIR / "crash.log"), 'a') as f:
        traceback.print_exc(file=f)

    # Show visible error dialog
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", f"{e}\n\nSee crash.log for details")
```

---

## Investigation Timeline (How We Found It)

### Day 1: "sentence-transformers not found"
- Colleague ran QuickTranslate exe, fuzzy matching failed
- ML packages (torch, sentence-transformers, faiss) were intentionally excluded from build
- Fix: Add them to PyInstaller spec with `collect_all()`

### Day 2: "WinError 1114 c10.dll"
- Build worked on dev machine, failed on fresh machine
- Created runtime hook v1: added `torch/lib/` to DLL search path
- Still failed → v2: added `_internal/` (where vcruntime140.dll lives)
- Still failed → v3: saved `add_dll_directory()` handles (GC was removing them)
- Still failed → v4: pre-load DLLs via `ctypes.WinDLL()`
- Still failed on fresh machine (works on dev machine with VC++ installed)

### Day 3: The breakthrough
- Checked how battle-tested XLSTransfer/KRSimilar builds work
- They use `--hidden-import` + `--copy-metadata`, NOT `collect_all()`
- **`collect_all('torch')` preserves subdirectory structure → DLL path issue**
- **`hidden-import` lets binary analysis place DLLs flat → no path issue**
- Rewrote spec file to use hidden-import pattern
- Added crash logging so errors are visible on fresh machines

### Key lesson:
> **NEVER use `collect_all()` for packages with complex DLL structures (torch, numpy, faiss).
> Use `hiddenimports` + `copy_metadata` and let PyInstaller's binary analysis handle flat DLL placement.**

---

## Quick Reference: collect_all vs hidden-import

| Package | Use collect_all? | Why |
|---------|-----------------|-----|
| `torch` | **NO** | DLLs in torch/lib/ create subdirectory problem |
| `numpy` | **NO** | Has native DLLs, binary analysis handles them |
| `faiss` / `faiss_cpu` | **NO** | Native .pyd + vendored DLLs in faiss_cpu.libs/ |
| `tokenizers` | **NO** | Rust binary (.pyd), keep flat |
| `safetensors` | **NO** | Rust binary (.pyd), keep flat |
| `sentence_transformers` | **YES** | Pure Python, needs JSON configs |
| `transformers` | **YES** | Pure Python, needs vocab/config files |
| `huggingface_hub` | **YES** | Pure Python, needs config files |

---

## Checklist for Future ML Builds

- [ ] Use `hiddenimports` + `copy_metadata` for packages with DLLs
- [ ] Use `collect_all` ONLY for pure-Python packages with data files
- [ ] Install CPU-only torch via `--index-url https://download.pytorch.org/whl/cpu`
- [ ] DO NOT use `--extra-index-url` (CUDA override risk)
- [ ] Verify `+cpu` in torch version string
- [ ] Include runtime hook as safety net (3-layer defense)
- [ ] Add crash logging + tkinter error dialog (console=False hides errors)
- [ ] Disable UPX (`upx=False` on both EXE and COLLECT)
- [ ] Exclude unused torch subpackages (cuda, cudnn, dynamo, etc.)
- [ ] Install `pyinstaller-hooks-contrib` for better torch hooks
- [ ] Test on a FRESH Windows machine (not dev machine with VC++ installed)

---

*Document created: Feb 2026*
*Based on: QuickTranslate WinError 1114 investigation (5 build iterations)*
