# Python Compatibility Protocol for NewScripts Projects

## Problem

ExtractAnything used Python 3.10+ type annotation syntax that crashes on older Python:

```python
# BREAKS on Python 3.9 and below:
LOC_FOLDER: Path | None = None          # PEP 604 union syntax (3.10+)
def foo(x: list[str]) -> dict[str, int]  # PEP 585 lowercase generics (3.9+ runtime)
```

**Error:** `TypeError: unsupported operand type(s) for |: type and NoneType`

This happens because `Path | None` uses the `|` operator on type objects at runtime, which only works in Python 3.10+. Similarly, `list[str]` as a runtime expression only works in Python 3.9+.

## Root Cause

ExtractAnything was coded with modern Python syntax without considering that:
1. Users may have Python 3.7-3.9 installed
2. Source distributions get renamed (e.g., `ExtractAnything_v26.227_Source`) — folder name dots break package imports
3. The exe (PyInstaller) bundles its own Python, but source users bring their own

## Working Pattern (QuickTranslate / QACompiler)

Both projects use **traditional `typing` module imports** that work on Python 3.7+:

```python
from typing import Dict, List, Optional, Set, Tuple, Union, Callable

# Instead of Path | None:
LOC_FOLDER: Optional[Path] = None

# Instead of list[str]:
def foo(x: List[str]) -> Dict[str, int]: ...

# Instead of str | int | None:
def bar(x: Union[str, int, None]) -> Optional[str]: ...
```

**Key facts:**
- QuickTranslate: targets Python 3.11 in CI but writes compatible annotations
- QACompiler: targets Python 3.10 in CI, zero `X | None` usage, zero lowercase generics
- Both use `from typing import Dict, List, Optional, ...` exclusively

## The Fix: `from __future__ import annotations`

PEP 563 (Python 3.7+) provides `from __future__ import annotations` which makes ALL type annotations **strings** (deferred evaluation). This means the runtime never evaluates `Path | None` or `list[str]` — they're just stored as documentation strings.

```python
from __future__ import annotations  # MUST be first import (after docstring)

# Now these are ALL fine on Python 3.7+:
LOC_FOLDER: Path | None = None
def foo(x: list[str]) -> dict[str, int]: ...
```

### Why this is better than manual conversion:
- **1 line per file** vs 211 individual type annotation changes
- **Zero risk of typos** in manual conversions
- **Future-proof** — any annotation syntax works
- **Already used** in QACompiler's `quest.py`

### Caveats:
- Must be the FIRST statement after docstrings (PEP requirement)
- Code that calls `typing.get_type_hints()` at runtime may need adjustment (rare)
- `dataclass` fields still work correctly

## Two Compatibility Issues Fixed

### Issue 1: Parent-Relative Imports (Fixed earlier)
```python
# BROKE when folder renamed:
from .. import config
from ..core.X import Y

# FIXED — direct imports:
import config
from core.X import Y
```
`main.py` adds project root to `sys.path` so direct imports work regardless of folder name.

### Issue 2: Python 3.10+ Type Annotations (Fixed now)
```python
# BROKE on Python 3.9 and below:
LOC_FOLDER: Path | None = None

# FIXED — from __future__ import annotations:
from __future__ import annotations
LOC_FOLDER: Path | None = None  # now a string, never evaluated
```

## Protocol for All NewScripts Projects

### MUST DO:
1. **Add `from __future__ import annotations`** as first import in EVERY `.py` file
2. **Use direct imports** (`import config`, `from core.X import Y`) — never parent-relative (`from ..`)
3. **`main.py` must add its directory to `sys.path`** before any project imports
4. **CI must validate imports** by running `python -c "import module"` from project dir

### NEVER DO:
1. Never use `X | None` without `from __future__ import annotations`
2. Never use lowercase generics (`list[str]`) without `from __future__ import annotations`
3. Never use `from .. import` (parent-relative imports) — breaks on folder rename
4. Never hardcode the folder name in imports (`from ExtractAnything.config import ...`)

## Files Changed

20 files received `from __future__ import annotations`:
- `config.py`
- `core/validators.py`, `language_utils.py`, `diff_engine.py`, `excel_writer.py`
- `core/input_parser.py`, `excel_reader.py`, `path_filter.py` (already had it)
- `core/long_string_engine.py`, `novoice_engine.py`, `string_eraser_engine.py`
- `core/file_eraser_engine.py`, `blacklist_engine.py`, `export_index.py`, `xml_writer.py`
- `gui/path_filter_dialog.py`, `base_tab.py`, `app.py`, `diff_tab.py`, `blacklist_tab.py`
