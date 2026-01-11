# Factorization Protocol

**DRY Principle** | **Single Source of Truth** | **Wrapper Patterns** | **Pipeline Automation**

---

## What is Factorization?

**Factorization** = Extracting common patterns into a single reusable component.

Instead of repeating the same code in 10 places, you create ONE source that controls everything.

```
BEFORE (Copy-Paste Hell):
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ File A  │ │ File B  │ │ File C  │ │ File D  │
│ v=1.0.0 │ │ v=1.0.0 │ │ v=1.0.0 │ │ v=1.0.0 │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
     ↑           ↑           ↑           ↑
   Manual     Manual     Manual     Manual
   Update     Update     Update     Update

AFTER (Factorized):
              ┌─────────────┐
              │   SOURCE    │
              │  v=1.0.0    │
              └──────┬──────┘
       ┌──────┬──────┼──────┬──────┐
       ↓      ↓      ↓      ↓      ↓
    File A  File B  File C  File D  ...
    (auto)  (auto)  (auto)  (auto)
```

---

## The Factor Power Principle

**"If you change it in more than one place, it's not factored."**

### Signs You Need Factorization:
1. Same value appears in multiple files
2. Same code pattern repeated in multiple functions
3. Changing one thing requires updating many places
4. Forgetting to update one place causes bugs

### Benefits:
- **Single Point of Change** - Update once, propagates everywhere
- **No Sync Issues** - Impossible to have mismatched values
- **Pipeline Ready** - Automation can control one variable
- **Less Human Error** - No "forgot to update X" bugs

---

## Factorization Patterns

### Pattern 1: Single Source Variable

**Problem:** Version appears in 8 different files
```
version.py:      VERSION = "2512131540"
package.json:    "version": "1.4.0"
installer.iss:   #define MyAppVersion "2512131540"
README.md:       **Version:** 2512131540
... (4 more files)
```

**Solution:** One source, others import/derive
```python
# version.py - THE SINGLE SOURCE
VERSION = "25.1213.1540"  # YY.MMDD.HHMM format

# All other files:
# - Import from version.py, OR
# - CI/CD extracts and injects, OR
# - Build script propagates
```

---

### Pattern 2: Wrapper Functions

**Problem:** Same try/catch/logging in every function
```python
# BEFORE - Repeated in EVERY function
async def create_dictionary():
    operation_id = generate_id()
    start_operation(operation_id, 'XLSTransfer', 'Create Dict')
    try:
        # actual work
        update_progress(operation_id, 50, 'Processing...')
        # more work
        complete_operation(operation_id, True, 'Done!')
    except Exception as e:
        complete_operation(operation_id, False, str(e))
        raise

async def translate_file():
    operation_id = generate_id()
    start_operation(operation_id, 'XLSTransfer', 'Translate')
    try:
        # actual work
        update_progress(operation_id, 50, 'Processing...')
        # more work
        complete_operation(operation_id, True, 'Done!')
    except Exception as e:
        complete_operation(operation_id, False, str(e))
        raise
```

**Solution:** Factor into wrapper
```python
# AFTER - Wrapper handles all boilerplate
def with_progress(tool: str, operation: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_id = generate_id()
            start_operation(op_id, tool, operation)
            try:
                result = await func(*args, progress=ProgressUpdater(op_id), **kwargs)
                complete_operation(op_id, True, 'Done!')
                return result
            except Exception as e:
                complete_operation(op_id, False, str(e))
                raise
        return wrapper
    return decorator

# Usage - just the actual work
@with_progress('XLSTransfer', 'Create Dict')
async def create_dictionary(progress):
    # actual work only
    progress.update(50, 'Processing...')

@with_progress('XLSTransfer', 'Translate')
async def translate_file(progress):
    # actual work only
    progress.update(50, 'Processing...')
```

---

### Pattern 3: Configuration Cascade

**Problem:** Same config in multiple environments
```yaml
# dev config
database_url: postgres://localhost:5432/dev

# test config
database_url: postgres://localhost:5432/test

# prod config
database_url: postgres://prod-server:5432/prod
```

**Solution:** Base config + environment overrides
```python
# config.py - Factored
BASE_CONFIG = {
    'database_host': 'localhost',
    'database_port': 5432,
}

ENV_OVERRIDES = {
    'dev':  {'database_name': 'dev'},
    'test': {'database_name': 'test'},
    'prod': {'database_host': 'prod-server', 'database_name': 'prod'},
}

def get_config(env):
    return {**BASE_CONFIG, **ENV_OVERRIDES.get(env, {})}
```

---

## Real Example: Version Factorization

### The Problem We Had:
- `VERSION = "2512131540"` (DateTime format for humans)
- `SEMANTIC_VERSION = "1.4.0"` (X.Y.Z for electron-builder)
- Two variables = sync issues, manual updates, build failures

### The Factored Solution:
```python
# version.py - SINGLE SOURCE
VERSION = "25.1213.1540"  # YY.MMDD.HHMM

# This ONE variable:
# - Is valid semver (25.1213.1540 = X.Y.Z)
# - Is human readable (Dec 13, 2025, 15:40)
# - Auto-increments with time
# - Works everywhere (electron, CI, installer, UI)
```

### Pipeline Integration:
```
BUILD TRIGGER
     ↓
Generate: YY.MMDD.HHMM (e.g., 25.1213.1540)
     ↓
Inject into version.py
     ↓
CI/CD extracts and uses everywhere:
├── package.json version
├── Installer version
├── Release tag
├── Auto-updater manifest
└── UI display
```

---

## When to Factor

### DO Factor When:
- Same value in 3+ places
- Same code pattern in 3+ functions
- Changing something requires "find and replace all"
- You've had bugs from forgetting to update something

### DON'T Over-Factor When:
- Only 2 places use it (might change independently)
- The "common" pattern is actually different in subtle ways
- Factoring adds more complexity than it removes

---

## Checklist Before Adding New Code

1. **Does this value exist elsewhere?**
   - Yes → Import from existing source
   - No → Consider if it should be factored for future

2. **Is this pattern repeated?**
   - 3+ times → Create wrapper/utility
   - 2 times → Watch it, factor if it grows

3. **Will changing this require multiple updates?**
   - Yes → Factor it NOW
   - No → Proceed, but document the source

---

## Summary

```
FACTORIZATION = One Source → Many Consumers

Benefits:
├── No sync bugs
├── Pipeline automation
├── Single point of change
└── Self-documenting (the source IS the truth)

Rule of Three:
├── 1 place → Just write it
├── 2 places → Note it, watch it
└── 3+ places → FACTOR IT
```

---

*Created: 2025-12-13 | Pattern from P18.6 Centralized Progress Module*
