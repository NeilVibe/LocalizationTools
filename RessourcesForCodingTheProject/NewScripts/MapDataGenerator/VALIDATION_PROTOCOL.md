# MapDataGenerator Validation Protocol

> Comprehensive validation checklist for MapDataGenerator before deployment.
>
> **CRITICAL:** This project uses tkinter/ttk GUI - special validation needed!

---

## Quick Start

```bash
# Run full validation locally (BEFORE pushing!)
python ci_validate.py

# Quick mode (skip slow checks)
python ci_validate.py --quick

# With fix suggestions
python ci_validate.py --fix

# Headless (no GUI test)
python ci_validate.py --no-gui

# With Xvfb on Linux
xvfb-run python ci_validate.py
```

---

## Table of Contents

1. [Syntax and Compile Check](#1-syntax-and-compile-check)
2. [Import Verification](#2-import-verification)
3. [GUI Widget Validation (CRITICAL!)](#3-gui-widget-validation-critical)
4. [Code Review Checklist](#4-code-review-checklist)
5. [Security Audit](#5-security-audit)
6. [Quick Reference Commands](#6-quick-reference-commands)

---

## 1. Syntax and Compile Check

Verify the code has no syntax errors and can be parsed by Python.

### Commands

```bash
# Basic compile check - catches syntax errors
python3 -m py_compile main.py config.py

# All files at once
for f in *.py core/*.py gui/*.py utils/*.py; do
    python3 -m py_compile "$f" && echo "OK: $f" || echo "FAIL: $f"
done

# Using ci_validate.py
python ci_validate.py --quick  # Runs syntax check
```

### What It Catches

- Syntax errors (missing colons, brackets, quotes)
- Invalid Python constructs
- Encoding issues
- Indentation errors

---

## 2. Import Verification

Ensure all imports are available - **INCLUDING GUI MODULES!**

### CRITICAL: Include GUI Modules

The `ttk.cget("background")` crash bug was missed because GUI modules weren't validated!

```python
# MUST validate ALL of these:
MODULES_TO_CHECK = [
    'config',
    'core.xml_parser',
    'core.language',
    'core.linkage',
    'core.search',
    'core.dds_handler',
    'utils.filters',
    # GUI - CRITICAL! These caused runtime crash if not validated
    'gui.app',
    'gui.result_panel',
    'gui.search_panel',
    'gui.map_canvas',
    'gui.image_viewer',
    'gui.audio_viewer',
]
```

### Commands

```bash
# Test all imports
python -c "
import sys
sys.path.insert(0, '.')

modules = [
    'config',
    'core.xml_parser',
    'gui.app',
    'gui.result_panel',
]

for mod in modules:
    try:
        __import__(mod)
        print(f'OK: {mod}')
    except Exception as e:
        print(f'FAIL: {mod}: {e}')
        sys.exit(1)
"
```

---

## 3. GUI Widget Validation (CRITICAL!)

**THIS IS THE #1 SOURCE OF BUGS!** ttk widgets are NOT the same as tk widgets.

### The Problem Pattern (CAUSES CRASH)

```python
# ❌ WRONG - ttk widgets DON'T support cget("background")
bg = self._detail_frame.cget("background")
# TclError: unknown option "-background"

# ❌ WRONG - hasattr doesn't help!
bg = frame.cget("background") if hasattr(frame, "cget") else "#f0f0f0"
# STILL CRASHES! cget() exists but fails for ttk
```

### The Correct Patterns

```python
from tkinter import ttk

# ✅ CORRECT - Use ttk.Style for ttk widget colors
style = ttk.Style()
bg_color = style.lookup("TLabelframe", "background") or "#f0f0f0"

# ✅ CORRECT - For tk.Text inside ttk container
text_widget = tk.Text(ttk_frame, background=bg_color)
```

### ttk Style Names

| Widget | Style Name |
|--------|------------|
| ttk.Frame | TFrame |
| ttk.LabelFrame | TLabelframe |
| ttk.Button | TButton |
| ttk.Label | TLabel |
| ttk.Entry | TEntry |
| ttk.Treeview | Treeview |
| ttk.Combobox | TCombobox |

### What Works on ttk vs tk

| Operation | tk.Widget | ttk.Widget |
|-----------|-----------|------------|
| `.cget("background")` | ✅ Works | ❌ CRASH |
| `.configure(bg="red")` | ✅ Works | ❌ CRASH |
| `["background"]` | ✅ Works | ❌ CRASH |
| `style.lookup(stylename, "background")` | N/A | ✅ Works |

### GUI Smoke Test

```bash
# Headless test with Xvfb (Linux)
xvfb-run python -c "
from gui.app import MapDataGeneratorApp
app = MapDataGeneratorApp()
print('GUI instantiation successful!')
"

# Windows (has display by default)
python -c "from gui.app import MapDataGeneratorApp; app = MapDataGeneratorApp(); print('OK')"
```

---

## 4. Code Review Checklist

### Thread Safety (GUI Applications)

```python
# BAD - Direct GUI update from background thread
def background_task():
    result = heavy_computation()
    self.label.config(text=result)  # CRASH!

# GOOD - Schedule update on main thread
def background_task():
    result = heavy_computation()
    self.root.after(0, lambda: self.label.config(text=result))
```

### Division by Zero Checks

```python
# BAD
percentage = (count / total) * 100

# GOOD
percentage = (count / total * 100) if total > 0 else 0
```

### None Handling

```python
# BAD
text = data['text'].strip()

# GOOD
text = data.get('text', '').strip()
```

### Dictionary Key Access Safety

```python
# BAD
value = config['setting']

# GOOD
value = config.get('setting', 'default_value')
```

### Error Handling

```python
# BAD - Bare except
try:
    process_file()
except:
    pass

# GOOD - Specific exceptions with logging
import logging

try:
    process_file()
except FileNotFoundError as e:
    logging.error(f"File not found: {e}")
    raise
except ValueError as e:
    logging.warning(f"Invalid value: {e}")
    return None
```

---

## 5. Security Audit

### XXE Vulnerability (XML Parser Hardening)

MapDataGenerator uses lxml with `recover=True` for XML parsing.

```python
# SECURE - lxml with recovery mode (what we use)
from lxml import etree
parser = etree.XMLParser(recover=True)
tree = etree.parse(xml_file, parser)
```

### Path Traversal Prevention

```python
import os

# SECURE - Validate path is within allowed directory
def read_file_secure(user_input, base_dir):
    base_dir = os.path.abspath(base_dir)
    requested_path = os.path.abspath(os.path.join(base_dir, user_input))

    if not requested_path.startswith(base_dir + os.sep):
        raise ValueError("Path traversal detected!")

    return open(requested_path).read()
```

### Secrets Detection

```bash
# Search for potential secrets in code
grep -rn -E "(password|secret|api_key|token)\s*=\s*['\"]" *.py core/*.py gui/*.py
```

---

## 6. Quick Reference Commands

### Full Validation Script

```bash
# Use ci_validate.py for comprehensive validation
python ci_validate.py           # All checks
python ci_validate.py --quick   # Fast checks only
python ci_validate.py --fix     # Show fix suggestions
python ci_validate.py --no-gui  # Skip GUI test
```

### One-Liner Checks

```bash
# Quick syntax check
python3 -m py_compile main.py && echo "OK"

# Check all Python files
for f in *.py core/*.py gui/*.py; do python3 -m py_compile "$f" || exit 1; done

# Import test (including GUI!)
python -c "from gui.app import MapDataGeneratorApp; print('OK')"

# Headless GUI test
xvfb-run python -c "from gui.app import MapDataGeneratorApp; app = MapDataGeneratorApp()"

# Flake8 critical errors
flake8 . --select=E9,F63,F7,F82 --exclude=__pycache__,build,dist
```

### CI Trigger

```bash
# Trigger build
echo "Build" >> MAPDATAGENERATOR_BUILD.txt
git add MAPDATAGENERATOR_BUILD.txt
git commit -m "Trigger MapDataGenerator build"
git push origin main
```

---

## Summary Checklist

Before deploying MapDataGenerator:

- [ ] `python ci_validate.py` passes
- [ ] Syntax check passes
- [ ] All imports available (INCLUDING GUI!)
- [ ] GUI smoke test passes (app instantiates)
- [ ] No ttk.cget("background") patterns
- [ ] Thread safety verified (GUI updates from main thread)
- [ ] Division by zero protected
- [ ] None values handled
- [ ] Error handling is specific and logged
- [ ] No hardcoded secrets
- [ ] XML parser uses lxml with recovery mode

---

## CI/CD Pipeline

MapDataGenerator uses GitHub Actions with 5 validation checks:

| Check | What It Catches |
|-------|-----------------|
| 1. Python Syntax | SyntaxError |
| 2. Module Imports | Missing imports (INCLUDING GUI!) |
| 3. Flake8 | Undefined names, critical errors |
| 4. Security Audit | Vulnerable dependencies |
| 5. GUI Smoke Test | **Runtime crashes from ttk/tk misuse** |

**CHECK 5 is CRITICAL** - It catches errors that static analysis CANNOT detect!

---

*Last updated: 2026-02-01*
