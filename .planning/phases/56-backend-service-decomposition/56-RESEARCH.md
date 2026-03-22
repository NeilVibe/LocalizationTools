# Phase 56: Backend Service Decomposition - Research

**Researched:** 2026-03-22
**Domain:** Python backend refactoring (FastAPI services, module decomposition)
**Confidence:** HIGH

## Summary

Phase 56 decomposes three monolithic backend service files into focused, single-responsibility modules. The three targets are mega_index.py (1310 lines), codex_service.py (586 lines), and gamedata_context_service.py (534 lines). All three follow the singleton pattern and are consumed by route files and other services via well-defined import paths.

The decomposition is straightforward because each file already has clear internal section boundaries marked with comment headers and follows a build-then-query pattern. The primary risk is breaking import paths -- 11 files import from mega_index, 3 from codex_service, and 2 from gamedata_context_service. Backward-compatible re-exports from the original module paths eliminate this risk entirely.

**Primary recommendation:** Split each file along its existing section boundaries, create `__init__.py` packages that re-export all public symbols from the original import path, and verify with `python -c "from server.tools.ldm.services.mega_index import get_mega_index"` after each split.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SVC-01 | mega_index.py split into builder (XML parsing), indexes (35 dict construction), and lookup (O(1) retrieval API) | File has clear 7-phase build pipeline (lines 210-321), reverse/composed builders (lines 902-1084), and public API (lines 1086-1296). Split along these boundaries. 11 import sites identified -- all use `get_mega_index` singleton. |
| SVC-02 | codex_service.py split into entity registry and search modules | Entity registry = population + cross-ref + related + public CRUD (lines 50-586). Search = FAISS index build + search method (lines 282-379). Singleton lives in routes/codex.py, not in service file itself. |
| SVC-03 | gamedata_context_service.py split into reverse index and cross-ref resolver | Reverse index = build + walk methods (lines 73-152). Cross-ref resolver = get_cross_refs + get_related + get_tm_suggestions + get_media + generate_ai_summary (lines 158-520). Singleton at bottom of file (lines 522-534). |
</phase_requirements>

## Standard Stack

No new libraries needed. This is pure refactoring using existing Python module patterns.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ | Runtime | Already in use |
| FastAPI | existing | HTTP framework | Already in use |
| loguru | existing | Logging | Project rule: never print(), always loguru |
| lxml | existing | XML parsing (mega_index builder) | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | existing | Validation after split | Run existing tests to verify no regression |
| pytest-asyncio | existing | Async test support | gamedata_context_service has async methods |

**Installation:** None required. All dependencies already installed.

## Architecture Patterns

### Current File Structure (BEFORE)
```
server/tools/ldm/services/
    mega_index.py            # 1310 lines (MONOLITH)
    mega_index_schemas.py    # 166 lines (keep as-is)
    codex_service.py         # 586 lines (MONOLITH)
    gamedata_context_service.py  # 534 lines (MONOLITH)
```

### Target File Structure (AFTER)
```
server/tools/ldm/services/
    mega_index/
        __init__.py          # Re-exports: get_mega_index, MegaIndex (backward compat)
        builder.py           # MegaIndex class: __init__, build(), _parse_*, _scan_* (~480 lines)
        indexes.py           # _build_* reverse/composed dict methods (mixin or standalone) (~200 lines)
        lookup.py            # Public API methods + singleton (~250 lines)
        _helpers.py          # Constants + helper functions (~80 lines)
    mega_index_schemas.py    # 166 lines (UNCHANGED)
    codex/
        __init__.py          # Re-exports: CodexService (backward compat)
        entity_registry.py   # CodexService core: populate, cross-ref, CRUD, relationships (~420 lines)
        search.py            # FAISS search index build + search method (~100 lines)
    gamedata_context/
        __init__.py          # Re-exports: GameDataContextService, get_gamedata_context_service
        reverse_index.py     # build_reverse_index, _walk_for_reverse_index, get_cross_refs (~200 lines)
        crossref_resolver.py # get_related, get_tm_suggestions, get_media, generate_ai_summary (~310 lines)
```

### Pattern 1: Package-as-Module (Backward-Compatible Split)
**What:** Convert a single `.py` file into a package directory with `__init__.py` that re-exports all public symbols.
**When to use:** Splitting a module that has many external importers.
**Example:**
```python
# server/tools/ldm/services/mega_index/__init__.py
"""MegaIndex package -- backward-compatible re-exports."""
from server.tools.ldm.services.mega_index.lookup import MegaIndex, get_mega_index

__all__ = ["MegaIndex", "get_mega_index"]
```

All 11 existing import sites continue to work unchanged:
```python
# These all keep working without modification:
from server.tools.ldm.services.mega_index import get_mega_index
from ..services.mega_index import get_mega_index
```

### Pattern 2: Mixin Classes for Decomposed Methods
**What:** Split a large class into multiple files using mixin inheritance or composition.
**When to use:** When a class has 1000+ lines with distinct method groups.
**Example (Recommended: Composition via module-level functions):**
```python
# builder.py
class MegaIndex:
    """Core class with __init__ and build pipeline."""
    def __init__(self): ...
    def build(self, preload_langs=None): ...
    # All _parse_* and _scan_* methods
    # All _build_* reverse/composed methods (they operate on self)

# lookup.py
from server.tools.ldm.services.mega_index.builder import MegaIndex
# Re-export with additional lookup methods attached
# OR: keep all methods on MegaIndex in builder.py, just split the file logically

# Alternative: keep MegaIndex as ONE class in builder.py with ALL methods,
# but physically split the _build_* methods into indexes.py as standalone
# functions that take the MegaIndex instance as first arg.
```

**Recommended approach for mega_index:** Keep MegaIndex as a single class for simplicity. Split the file into:
- `_helpers.py`: Constants, regex patterns, helper functions (lines 1-141)
- `builder.py`: MegaIndex class with `__init__`, `build()`, all `_parse_*` and `_scan_*` methods, all `_build_*` methods. This keeps the class intact.
- `lookup.py`: Public API methods extracted as a mixin or attached. Plus singleton.

**SIMPLER ALTERNATIVE (recommended):** Since mega_index has clear sections, use the "extract private methods as module functions" pattern:

```python
# _helpers.py -- shared constants and utilities
STRINGID_ATTRS = [...]
_BR_TAG_RE = ...
def _get_stringid(elem): ...
def _normalize_strorigin(text): ...
def _safe_parse_xml(xml_path): ...

# builder.py -- MegaIndex.__init__ + build() + _parse_* + _scan_*
from ._helpers import ...
class MegaIndex:
    def __init__(self): ...
    def build(self, ...): ...
    # Include _build_* methods here too (they need self)
    # Include public API methods (they're thin wrappers on self.dict.get())

# lookup.py -- just the singleton + optional convenience functions
from .builder import MegaIndex
_mega_index = None
def get_mega_index(): ...
```

Wait -- this makes builder.py still large. Better approach:

### Pattern 3: Method Registry (Best for mega_index)
**What:** Keep ONE MegaIndex class but split method definitions across files using import-time method attachment.
**When to use:** When you need to split a class but keep it as one class for consumers.
**REJECTED -- too clever.** Instead, use the straightforward approach below.

### FINAL RECOMMENDED PATTERN for mega_index
```python
# _helpers.py (~80 lines)
# Constants, regex, helper functions

# builder.py (~480 lines)
# MegaIndex class with __init__, build(), all _parse_* and _scan_* (Phases 1-5)
# Also contains _build_* methods (Phases 6-7) since they mutate self

# lookup.py (~250 lines)
# Subclass or same class? SAME CLASS -- but we move the public API methods here.
# PROBLEM: methods need self, can't easily split a class across files.

# SOLUTION: Keep builder.py as the full class (all private methods).
# lookup.py contains ONLY the singleton + re-exports.
# The "split" for SVC-01 is:
#   builder.py = _parse_*, _scan_*, _build_* (build pipeline)
#   indexes.py = property access, stats, entity_counts (thin read-only wrapper)
#   lookup.py = public API methods (get_*, find_*, all_entities) + singleton
```

**The cleanest approach for a class with 1310 lines:**

```python
# mega_index/_helpers.py
# All module-level constants, regex, helper functions

# mega_index/_parsers.py (~400 lines)
# Standalone functions: parse_knowledge_info(mi, folder), parse_character_info(mi, folder), etc.
# Each takes a MegaIndex instance as first arg

# mega_index/_builders.py (~200 lines)
# Standalone functions: build_name_kr_to_strkeys(mi), build_knowledge_key_to_entities(mi), etc.

# mega_index/builder.py (~250 lines)
# MegaIndex class: __init__ (all dict declarations), build() method
# build() calls functions from _parsers and _builders

# mega_index/lookup.py (~230 lines)
# All public get_*, find_*, all_entities, stats, entity_counts methods
# These are methods on MegaIndex class -- use a mixin:
class MegaIndexLookupMixin:
    def get_knowledge(self, strkey): ...
    def get_character(self, strkey): ...
    # etc.

# mega_index/builder.py
from .lookup import MegaIndexLookupMixin
class MegaIndex(MegaIndexLookupMixin):
    ...

# mega_index/__init__.py
from .builder import MegaIndex
_mega_index = None
def get_mega_index(): ...
```

### Anti-Patterns to Avoid
- **Circular imports:** Never import between split modules that both define parts of the same class. Use one-directional dependency: `__init__` imports from `builder`, `builder` imports from `lookup` (mixin), `lookup` has no imports from builder.
- **Breaking the singleton:** The `get_mega_index()` singleton MUST remain accessible from `server.tools.ldm.services.mega_index`. Put it in `__init__.py`.
- **Splitting CodexService too aggressively:** At 586 lines, codex_service is borderline. The split into entity_registry + search is sufficient. Do NOT split further.
- **Moving schemas:** mega_index_schemas.py stays where it is. Do NOT move it into the package.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Backward-compatible imports | Manual import path updates in 11+ files | Package `__init__.py` re-exports | Zero consumer changes needed |
| Class decomposition | Complex metaclass/decorator patterns | Mixin classes or standalone functions | Simple, readable, debuggable |
| Import verification | Manual grep | `python -c "from X import Y"` | Catches actual import errors |

**Key insight:** The goal is to make each file under 500 lines while changing ZERO import statements in consuming code. Package `__init__.py` achieves this automatically.

## Common Pitfalls

### Pitfall 1: Circular Import Between Split Modules
**What goes wrong:** Module A imports from Module B which imports from Module A at module level.
**Why it happens:** When splitting a class, the lookup methods need the class definition, and the builder needs lookup methods.
**How to avoid:** One-directional dependency chain: `__init__.py` -> `builder.py` -> `_parsers.py` / `_builders.py` -> `_helpers.py`. Never backward.
**Warning signs:** `ImportError: cannot import name X from partially initialized module Y`

### Pitfall 2: Singleton Duplication
**What goes wrong:** Each split module creates its own singleton, or the singleton gets imported from the wrong location.
**Why it happens:** The singleton pattern (`_mega_index = None; def get_mega_index()`) must live in exactly ONE place.
**How to avoid:** Singleton always in `__init__.py`. All internal modules import the CLASS, never the singleton.
**Warning signs:** Multiple instances of the service, stale data, inconsistent state.

### Pitfall 3: Lazy Imports Lost in Split
**What goes wrong:** mega_index.py and codex_service.py use lazy imports (`from X import Y` inside methods) to avoid circular dependencies. These get accidentally moved to module-level imports in the new files.
**Why it happens:** Refactoring tools or copy-paste moves imports to the top.
**How to avoid:** Audit every `from ... import` that appears INSIDE a method body. These are intentionally lazy. Keep them lazy in the split files.
**Warning signs:** `ImportError` at startup, circular import errors.
**Specific locations:**
  - `codex_service.py:75` -- lazy import of `get_mega_index` inside `initialize()`
  - `codex_service.py:100` -- lazy import of `get_mega_index` inside `_populate_from_mega_index()`
  - `gamedata_context_service.py:130` -- lazy import of `normalize_for_hash`
  - `gamedata_context_service.py:173` -- lazy import of `normalize_for_hash`
  - `gamedata_context_service.py:343` -- lazy import of `get_mapdata_service`

### Pitfall 4: codex_service Singleton Lives in Routes, Not Service
**What goes wrong:** Assuming the CodexService singleton is in codex_service.py and moving it.
**Why it happens:** Unlike mega_index and gamedata_context_service, CodexService has NO singleton in its service file. The singleton lives in `routes/codex.py:37` (`_codex_service`) and is accessed via `routes/codex.py:46` (`_get_codex_service()`).
**How to avoid:** Do NOT add a singleton to the new codex package. The singleton pattern stays in routes/codex.py.
**Warning signs:** `naming_coherence_service.py` imports from `routes.codex._get_codex_service` -- this must keep working.

### Pitfall 5: gamedata_context_service Route Usage Pattern
**What goes wrong:** Breaking the 3 route call sites in gamedata.py.
**Why it happens:** The route calls `get_gamedata_context_service()` and then calls methods like `.get_cross_refs()`, `.get_related()`, `.get_media()`, `.generate_ai_summary()` on the returned object.
**How to avoid:** The GameDataContextService class must remain a single class (or facade) even if its internal methods are split. The singleton returns the same type.
**Warning signs:** AttributeError on the service instance.

## Code Examples

### Example 1: mega_index package __init__.py
```python
# server/tools/ldm/services/mega_index/__init__.py
"""MegaIndex - Unified game data index with 35 dicts and O(1) lookups.

Backward-compatible package. All public symbols available at original import path.
"""
from server.tools.ldm.services.mega_index.builder import MegaIndex
from server.tools.ldm.services.mega_index.lookup import (
    get_mega_index,
    # Re-export any other public names used externally
)

__all__ = ["MegaIndex", "get_mega_index"]
```

### Example 2: Standalone parser functions pattern
```python
# server/tools/ldm/services/mega_index/_parsers.py
"""XML parsing functions for MegaIndex build pipeline (Phases 1-3, 5)."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .builder import MegaIndex

from ._helpers import _safe_parse_xml, _get_stringid, _find_knowledge_key, ...
from server.tools.ldm.services.mega_index_schemas import (
    CharacterEntry, KnowledgeEntry, ...
)

def parse_knowledge_info(mi: "MegaIndex", knowledge_folder: Path) -> None:
    """D1+D15: Parse KnowledgeInfo and KnowledgeGroupInfo in single pass."""
    # Exact same code as MegaIndex._parse_knowledge_info, but operates on `mi` instead of `self`
    ...
```

### Example 3: GameDataContextService facade pattern
```python
# server/tools/ldm/services/gamedata_context/__init__.py
"""GameData Context Intelligence Service - backward-compatible package."""
from server.tools.ldm.services.gamedata_context.reverse_index import ReverseIndexMixin
from server.tools.ldm.services.gamedata_context.crossref_resolver import CrossRefResolverMixin

class GameDataContextService(ReverseIndexMixin, CrossRefResolverMixin):
    """Context intelligence for gamedata entities.

    Composed from ReverseIndexMixin and CrossRefResolverMixin.
    """
    def __init__(self):
        self._reverse_index = {}
        self._entity_names = {}
        self._ai_cache = {}

# Singleton
_context_service_instance = None

def get_gamedata_context_service():
    global _context_service_instance
    if _context_service_instance is None:
        _context_service_instance = GameDataContextService()
    return _context_service_instance
```

### Example 4: Import verification commands
```bash
# Run after EACH file split to verify no breakage
python -c "from server.tools.ldm.services.mega_index import get_mega_index; print('OK')"
python -c "from server.tools.ldm.services.codex_service import CodexService; print('OK')"
python -c "from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service; print('OK')"
```

## Import Dependency Map (CRITICAL)

### mega_index consumers (11 sites)
| File | Import | Symbol Used |
|------|--------|-------------|
| server/main.py:162 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` |
| codex_service.py:75,100 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` (lazy) |
| mapdata_service.py:103,169,244,321 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` (lazy) |
| routes/mega_index.py:23 | `from ..services.mega_index import get_mega_index` | `get_mega_index` |
| routes/codex_audio.py:32 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` |
| routes/codex_items.py:29 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` |
| routes/codex_regions.py:30 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` |
| routes/codex_characters.py:28 | `from server.tools.ldm.services.mega_index import get_mega_index` | `get_mega_index` |

### codex_service consumers (3 sites)
| File | Import | Symbol Used |
|------|--------|-------------|
| routes/codex.py:28 | `from server.tools.ldm.services.codex_service import CodexService` | `CodexService` |
| worldmap_service.py:195 | `from server.tools.ldm.services.codex_service import CodexService` | `CodexService` |
| naming_coherence_service.py:42 | `from server.tools.ldm.routes.codex import _get_codex_service` | Indirect |

### gamedata_context_service consumers (2 sites)
| File | Import | Symbol Used |
|------|--------|-------------|
| server/main.py:139 | `from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service` | `get_gamedata_context_service` |
| routes/gamedata.py:64 | `from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service` | `get_gamedata_context_service` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pytest.ini` (root) |
| Quick run command | `python -m pytest tests/unit/ldm/ -x -q --no-header --no-cov` |
| Full suite command | `python -m pytest tests/unit/ldm/ -v --no-cov` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SVC-01 | mega_index imports resolve after split | smoke | `python -c "from server.tools.ldm.services.mega_index import get_mega_index, MegaIndex"` | N/A |
| SVC-01 | Each split file under 500 lines | lint | `wc -l server/tools/ldm/services/mega_index/*.py` | N/A |
| SVC-02 | codex_service imports resolve after split | smoke | `python -c "from server.tools.ldm.services.codex_service import CodexService"` | N/A |
| SVC-02 | Existing codex tests pass | unit | `python -m pytest tests/unit/ldm/test_codex_service.py tests/unit/ldm/test_codex_route.py -x --no-cov` | YES (267+173 lines) |
| SVC-03 | gamedata_context imports resolve after split | smoke | `python -c "from server.tools.ldm.services.gamedata_context_service import get_gamedata_context_service"` | N/A |
| SVC-03 | Context panel cross-refs work | integration | DEV server start + manual check | N/A |
| ALL | DEV server starts without errors | smoke | `timeout 10 python -c "from server.main import app; print('OK')"` | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/ -x -q --no-header --no-cov`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -v --no-cov`
- **Phase gate:** Full unit suite green + DEV server startup check

### Wave 0 Gaps
- None -- existing test infrastructure covers codex_service (267 lines of tests). No existing mega_index or gamedata_context_service unit tests, but those are Phase 60 scope (TEST-02). This phase only needs import smoke tests and existing test pass-through.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single mega_index.py 1310 lines | Package with 4+ files under 500 each | This phase | Maintainability, testability |
| Monolithic codex_service.py | entity_registry + search modules | This phase | Clear separation of CRUD vs search |
| Monolithic context_service | reverse_index + crossref_resolver | This phase | Independent evolution of indexing vs resolution |

## Open Questions

1. **mega_index_schemas.py location**
   - What we know: Currently at `services/mega_index_schemas.py` (166 lines). Multiple files import from it.
   - What's unclear: Should it move into the `mega_index/` package?
   - Recommendation: Leave it where it is. Moving it would require updating imports in other files for no benefit. The schemas are consumed by codex_service too.

2. **codex_service backward-compatible path**
   - What we know: Import path is `server.tools.ldm.services.codex_service`. Converting to a package means the file becomes a directory.
   - What's unclear: Whether to create `codex/` package or keep `codex_service.py` as a thin re-export facade.
   - Recommendation: Create `codex_service/` directory (NOT `codex/`) to preserve the exact import path `from server.tools.ldm.services.codex_service import CodexService`. Python treats `codex_service/__init__.py` identically to `codex_service.py` for imports.

3. **gamedata_context_service backward-compatible path**
   - Same pattern as above. Create `gamedata_context_service/` directory.
   - Recommendation: `gamedata_context_service/__init__.py` re-exports `GameDataContextService` and `get_gamedata_context_service`.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `server/tools/ldm/services/mega_index.py` (1310 lines, read in full)
- Direct codebase analysis: `server/tools/ldm/services/codex_service.py` (586 lines, read in full)
- Direct codebase analysis: `server/tools/ldm/services/gamedata_context_service.py` (534 lines, read in full)
- Import dependency grep across all `/server` files
- Existing test infrastructure: `tests/unit/ldm/` (55 test files, conftest.py present)

### Secondary (MEDIUM confidence)
- Python package import mechanics (well-established, no verification needed)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pure refactoring, no new libraries
- Architecture: HIGH - file contents analyzed line by line, split boundaries verified
- Pitfalls: HIGH - import dependencies fully mapped, lazy imports identified, singleton patterns documented

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable codebase, no external dependencies)
