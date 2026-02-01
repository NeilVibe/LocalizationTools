# Python Validation Protocol

> Comprehensive validation checklist for Python applications before deployment.

---

## Table of Contents

1. [Syntax and Compile Check](#1-syntax-and-compile-check)
2. [Import Verification](#2-import-verification)
3. [Code Review Checklist](#3-code-review-checklist)
4. [Security Audit](#4-security-audit)
5. [Variable and Function Check](#5-variable-and-function-check)
6. [Regression Check](#6-regression-check)
7. [Quick Reference Commands](#7-quick-reference-commands)

---

## 1. Syntax and Compile Check

Verify the code has no syntax errors and can be parsed by Python.

### Commands

```bash
# Basic compile check - catches syntax errors
python3 -m py_compile <file.py>

# AST parsing - deeper syntax validation
python3 -c "import ast; ast.parse(open('<file.py>').read())"

# Multiple files at once
for f in *.py; do python3 -m py_compile "$f" && echo "OK: $f" || echo "FAIL: $f"; done
```

### What It Catches

- Syntax errors (missing colons, brackets, quotes)
- Invalid Python constructs
- Encoding issues
- Indentation errors

### Example Output

```
# Success: No output (silent success)
$ python3 -m py_compile wordcount7.py

# Failure: Shows error location
$ python3 -m py_compile broken.py
  File "broken.py", line 42
    def process(self
                   ^
SyntaxError: '(' was never closed
```

---

## 2. Import Verification

Ensure all imports are available and identify unused imports.

### Check All Imports Are Available

```bash
# Extract and test imports
python3 -c "
import ast
import sys

with open('<file.py>', 'r') as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.append(alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module.split('.')[0])

for imp in sorted(set(imports)):
    try:
        __import__(imp)
        print(f'OK: {imp}')
    except ImportError as e:
        print(f'MISSING: {imp} - {e}')
        sys.exit(1)
"
```

### Identify Unused Imports

```bash
# Using pylint (if available)
pylint --disable=all --enable=W0611 <file.py>

# Manual check - find imports not used in code
python3 -c "
import ast
import re

with open('<file.py>', 'r') as f:
    content = f.read()
    tree = ast.parse(content)

imports = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            imports[name] = alias.name
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            name = alias.asname or alias.name
            imports[name] = f'{node.module}.{alias.name}'

# Check usage (simple pattern match)
for name, full_import in imports.items():
    # Count occurrences (excluding import lines)
    pattern = rf'\b{re.escape(name)}\b'
    matches = len(re.findall(pattern, content))
    if matches <= 1:  # Only in import statement
        print(f'POSSIBLY UNUSED: {name} (from {full_import})')
"
```

### Common Import Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Install with `pip install <package>` |
| Circular import | Refactor to avoid circular dependencies |
| Unused import | Remove or comment with `# noqa: F401` if needed |

---

## 3. Code Review Checklist

### Thread Safety (GUI Applications)

GUI frameworks (Tkinter, PyQt, etc.) require UI updates from the main thread.

```python
# BAD - Direct GUI update from background thread
def background_task():
    result = heavy_computation()
    self.label.config(text=result)  # CRASH or undefined behavior!

# GOOD - Schedule update on main thread (Tkinter)
def background_task():
    result = heavy_computation()
    self.root.after(0, lambda: self.label.config(text=result))

# GOOD - Using queue for thread communication
import queue
import threading

class ThreadSafeApp:
    def __init__(self):
        self.update_queue = queue.Queue()
        self.check_queue()

    def check_queue(self):
        try:
            while True:
                callback = self.update_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def thread_safe_update(self, callback):
        self.update_queue.put(callback)
```

### Division by Zero Checks

```python
# BAD
percentage = (count / total) * 100

# GOOD
percentage = (count / total * 100) if total > 0 else 0

# GOOD - With explicit check
if total == 0:
    percentage = 0
else:
    percentage = (count / total) * 100
```

### None Handling

```python
# BAD - Assumes value exists
text = data['text'].strip()

# GOOD - Check for None
text = data.get('text', '').strip()

# GOOD - Explicit None check
text = data.get('text')
if text is not None:
    text = text.strip()
else:
    text = ''
```

### Dictionary Key Access Safety

```python
# BAD - KeyError if key missing
value = config['setting']

# GOOD - With default value
value = config.get('setting', 'default_value')

# GOOD - Check existence first
if 'setting' in config:
    value = config['setting']
else:
    value = 'default_value'

# For nested dictionaries
# BAD
value = data['level1']['level2']['level3']

# GOOD
value = data.get('level1', {}).get('level2', {}).get('level3', default)
```

### Error Handling Consistency

```python
# BAD - Bare except
try:
    process_file()
except:
    pass

# BAD - Too broad
try:
    process_file()
except Exception:
    print("Error occurred")

# GOOD - Specific exceptions with logging
import logging

try:
    process_file()
except FileNotFoundError as e:
    logging.error(f"File not found: {e}")
    raise
except PermissionError as e:
    logging.error(f"Permission denied: {e}")
    raise
except ValueError as e:
    logging.warning(f"Invalid value: {e}")
    return None
```

---

## 4. Security Audit

### XXE Vulnerability (XML Parser Hardening)

```python
# VULNERABLE - Default XML parsing allows XXE attacks
import xml.etree.ElementTree as ET
tree = ET.parse(untrusted_file)  # DANGEROUS!

# SECURE - Disable external entities with defusedxml
from defusedxml import ElementTree as ET
tree = ET.parse(untrusted_file)

# SECURE - Manual hardening (if defusedxml not available)
from xml.etree.ElementTree import XMLParser
import xml.etree.ElementTree as ET

class SecureXMLParser:
    def __init__(self):
        self.parser = XMLParser()
        # Disable DTD processing
        self.parser.entity = {}

    def parse(self, source):
        return ET.parse(source, parser=self.parser)
```

### Path Traversal Prevention

```python
import os

# VULNERABLE
def read_file(user_input):
    path = f"/data/{user_input}"  # User could input "../../../etc/passwd"
    return open(path).read()

# SECURE - Validate path is within allowed directory
def read_file_secure(user_input):
    base_dir = os.path.abspath("/data")
    requested_path = os.path.abspath(os.path.join(base_dir, user_input))

    # Ensure the resolved path is within base directory
    if not requested_path.startswith(base_dir + os.sep):
        raise ValueError("Path traversal detected!")

    if not os.path.exists(requested_path):
        raise FileNotFoundError(f"File not found: {user_input}")

    return open(requested_path).read()
```

### Command Injection Prevention

```python
import subprocess
import shlex

# VULNERABLE - Shell injection possible
def run_command(user_input):
    os.system(f"process {user_input}")  # User could input "; rm -rf /"

# SECURE - Use subprocess with list arguments
def run_command_secure(user_input):
    # Validate input first
    if not user_input.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid characters in input")

    # Use list form (no shell interpretation)
    result = subprocess.run(
        ["process", user_input],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout
```

### Secrets Detection

```bash
# Search for potential secrets in code
grep -rn -E "(password|secret|api_key|token|credentials)\s*=\s*['\"]" <file.py>

# Check for hardcoded IPs/URLs
grep -rn -E "https?://[0-9a-zA-Z]" <file.py>

# Look for base64 encoded strings (potential secrets)
grep -rn -E "[A-Za-z0-9+/]{40,}={0,2}" <file.py>
```

```python
# BAD - Hardcoded credentials
API_KEY = "sk-abc123secret456"
DATABASE_PASSWORD = "admin123"

# GOOD - Environment variables
import os
API_KEY = os.environ.get("API_KEY")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable not set")

# GOOD - Configuration file (with proper permissions)
import json
with open("/etc/myapp/config.json") as f:
    config = json.load(f)
API_KEY = config.get("api_key")
```

---

## 5. Variable and Function Check

### Variables Defined Before Use

```bash
# Using pyflakes
pyflakes <file.py>

# Manual AST check for undefined names
python3 -c "
import ast
import builtins

with open('<file.py>', 'r') as f:
    tree = ast.parse(f.read())

# Get all defined names
defined = set(dir(builtins))
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        defined.add(node.name)
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        defined.add(node.id)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            defined.add(alias.asname or alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            defined.add(alias.asname or alias.name)

# This is a simplified check - full analysis requires scope tracking
print('Defined names:', len(defined))
"
```

### Function Call Verification

```python
# Check function signatures match calls
import inspect

def verify_function_call(func, *args, **kwargs):
    sig = inspect.signature(func)
    try:
        sig.bind(*args, **kwargs)
        return True
    except TypeError as e:
        print(f"Invalid call: {e}")
        return False
```

### Unused Variable Detection

```bash
# Using pylint
pylint --disable=all --enable=W0612,W0613 <file.py>

# W0612 = Unused variable
# W0613 = Unused argument
```

### Type Consistency Checks

```bash
# Using mypy for static type checking
mypy <file.py>

# With strict mode
mypy --strict <file.py>

# Ignore missing stubs for third-party libraries
mypy --ignore-missing-imports <file.py>
```

### Return Value Handling

```python
# BAD - Ignoring return value that indicates error
open(filename)  # What if it fails?

# BAD - Not checking for None return
result = find_item(items, key)
process(result.value)  # AttributeError if result is None

# GOOD - Handle return values properly
try:
    f = open(filename)
except FileNotFoundError:
    handle_missing_file()
    return

# GOOD - Check for None
result = find_item(items, key)
if result is not None:
    process(result.value)
else:
    handle_not_found()
```

---

## 6. Regression Check

### Compare with Original Version

```bash
# Side-by-side diff
diff -y original.py modified.py | head -100

# Unified diff (better for patches)
diff -u original.py modified.py

# Count changes
diff original.py modified.py | grep -c "^[<>]"

# Visual diff (if available)
meld original.py modified.py
```

### Feature Preservation Checklist

```bash
# Extract all function definitions
grep -n "^def \|^    def \|^class " <file.py>

# Compare function lists
diff <(grep -o "def [a-zA-Z_]*" original.py | sort) \
     <(grep -o "def [a-zA-Z_]*" modified.py | sort)

# Check class methods preserved
python3 -c "
import ast

def get_definitions(filename):
    with open(filename) as f:
        tree = ast.parse(f.read())

    defs = {'classes': [], 'functions': [], 'methods': {}}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            defs['classes'].append(node.name)
            defs['methods'][node.name] = [
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
            # Top-level functions only
            pass

    return defs

original = get_definitions('original.py')
modified = get_definitions('modified.py')

# Compare
for cls in original['classes']:
    if cls not in modified['classes']:
        print(f'MISSING CLASS: {cls}')
    elif set(original['methods'].get(cls, [])) != set(modified['methods'].get(cls, [])):
        print(f'METHODS CHANGED in {cls}')
        print(f'  Original: {original[\"methods\"][cls]}')
        print(f'  Modified: {modified[\"methods\"].get(cls, [])}')
"
```

### Functional Testing

```python
# Create test cases for critical functionality
import unittest

class RegressionTests(unittest.TestCase):
    def test_feature_1_preserved(self):
        """Verify feature 1 still works as expected."""
        result = feature_1(test_input)
        self.assertEqual(result, expected_output)

    def test_edge_cases_still_handled(self):
        """Verify edge cases don't break."""
        self.assertIsNone(process(None))
        self.assertEqual(process([]), [])
        self.assertEqual(process(""), "")

if __name__ == "__main__":
    unittest.main()
```

---

## 7. Quick Reference Commands

### Full Validation Script

```bash
#!/bin/bash
# validate.sh - Complete Python validation

FILE=$1

if [ -z "$FILE" ]; then
    echo "Usage: ./validate.sh <python_file>"
    exit 1
fi

echo "=== Python Validation: $FILE ==="
echo

echo "1. Syntax Check..."
python3 -m py_compile "$FILE" && echo "   PASS" || { echo "   FAIL"; exit 1; }

echo "2. AST Parse..."
python3 -c "import ast; ast.parse(open('$FILE').read())" && echo "   PASS" || { echo "   FAIL"; exit 1; }

echo "3. Import Check..."
python3 -c "
import ast
with open('$FILE', 'r') as f:
    tree = ast.parse(f.read())
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.add(alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split('.')[0])
failed = False
for imp in sorted(imports):
    try:
        __import__(imp)
    except ImportError as e:
        print(f'   MISSING: {imp}')
        failed = True
if failed:
    exit(1)
print('   PASS')
"

echo "4. Security Scan..."
if grep -qE "(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]" "$FILE"; then
    echo "   WARNING: Potential hardcoded secrets found"
    grep -n -E "(password|secret|api_key)\s*=\s*['\"]" "$FILE"
else
    echo "   PASS"
fi

echo
echo "=== Validation Complete ==="
```

### One-Liner Checks

```bash
# Quick syntax check
python3 -m py_compile file.py && echo "OK"

# Check all Python files in directory
find . -name "*.py" -exec python3 -m py_compile {} \; -print

# Import test
python3 -c "import file"  # (for modules)

# Run with all warnings
python3 -W all file.py

# Check for common issues with pylint (if installed)
pylint --disable=C,R file.py  # Only errors and warnings
```

### IDE Integration

Most IDEs (VS Code, PyCharm) provide real-time validation. Ensure these are enabled:

- **Pylint/Pyflakes** - Static analysis
- **Mypy** - Type checking
- **Black/isort** - Formatting (not validation, but catches issues)

---

## Summary Checklist

Before deploying any Python application:

- [ ] Syntax check passes (`python3 -m py_compile`)
- [ ] All imports available
- [ ] No unused imports (or intentionally suppressed)
- [ ] Thread safety verified (GUI apps)
- [ ] Division by zero protected
- [ ] None values handled
- [ ] Dictionary access uses `.get()` with defaults
- [ ] Error handling is specific and logged
- [ ] No XXE vulnerabilities (XML hardened)
- [ ] No path traversal possible
- [ ] No command injection possible
- [ ] No hardcoded secrets
- [ ] All variables defined before use
- [ ] Function calls match signatures
- [ ] Return values handled
- [ ] Regression tests pass
- [ ] All original features preserved

---

*Last updated: 2026-02-01*
