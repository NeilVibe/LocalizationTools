---
phase: 61-merge-internalization
plan: 01
subsystem: merge-engine
tags: [internalization, pyinstaller-safe, package-refactor]
dependency_graph:
  requires: []
  provides: [server.services.merge]
  affects: [server/services/transfer_adapter.py]
tech_stack:
  added: []
  patterns: [dataclass-config, relative-imports, package-init-exports]
key_files:
  created:
    - server/services/merge/__init__.py
    - server/services/merge/_config.py
    - server/services/merge/text_utils.py
    - server/services/merge/korean_detection.py
    - server/services/merge/matching.py
    - server/services/merge/xml_parser.py
    - server/services/merge/xml_io.py
    - server/services/merge/category_mapper.py
    - server/services/merge/language_loader.py
    - server/services/merge/eventname_resolver.py
    - server/services/merge/excel_io.py
    - server/services/merge/tmx_tools.py
    - server/services/merge/source_scanner.py
    - server/services/merge/postprocess.py
    - server/services/merge/xml_transfer.py
  modified: []
decisions:
  - MergeConfig dataclass instead of types.ModuleType for config -- type-safe, IDE-friendly
  - Lazy get_config() pattern instead of module-level config vars -- defer until runtime
  - Keep all 14 QT modules verbatim with only import changes -- minimize divergence risk
metrics:
  duration: 7min
  completed: 2026-03-23
---

# Phase 61 Plan 01: Create Merge Package Summary

Self-contained `server.services.merge` Python package with 15 files -- all 14 QT core modules internalized with `_config.py` replacing `sys.modules['config']` injection, all imports converted to relative syntax, PyInstaller-safe.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Create _config.py and leaf modules | f1ad5e4d | MergeConfig dataclass, configure/get_config/reconfigure, 4 leaf modules copied verbatim |
| 2 | Copy mid/top-level modules, convert imports, wire __init__.py | 1290a98d | 9 modules copied, 3 config conversions (xml_transfer, source_scanner, excel_io), __init__.py with 30+ exports |

## Verification Results

All 6 plan verifications passed:
1. `grep "import config"` -- 0 matches (PASS)
2. `grep "from core."` -- 0 matches (PASS)
3. `grep "sys.path"` -- 0 code matches (1 comment only) (PASS)
4. `grep "importlib"` -- 0 matches (PASS)
5. Full import test with configure + all public functions -- exits 0 (PASS)
6. File count: 15 .py files in server/services/merge/ (PASS)

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all modules are complete, functional copies of QT core with only import changes.

## Self-Check: PASSED
