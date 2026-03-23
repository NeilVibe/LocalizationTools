# Phase 61: Merge Internalization - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Internalize QuickTranslate's merge-related core modules into LocaNext's server/services/ as a proper Python package. Eliminate all sys.path injection, importlib hacks, and runtime dependency on the QT source tree. The merge API interface (transfer_adapter.py's public functions) stays identical.

</domain>

<decisions>
## Implementation Decisions

### Module Internalization Strategy (Tribunal: 4/4 unanimous)
- Copy ~14 needed QT core modules into server/services/merge/ as a proper Python package
- Skip ~6 unused files (failure_report, missing_translation_finder, checker, quality_checker, fuzzy_matching, indexing)
- Convert all `from core.xyz import` to relative imports (`from .xyz import`)
- Add `__init__.py` exposing the public API surface

### Config Handling
- Replace `import config` shim pattern with dependency injection (pass config as parameter)
- OR create internal config module within server/services/merge/ that reads from LocaNext's own config
- Eliminate sys.modules['config'] injection hack

### Adapter Interface
- Keep transfer_adapter.py's public interface identical (execute_transfer, execute_multi_language_transfer, TransferAdapter class)
- Rewire internals from importlib/sys.path loading to normal imports from server.services.merge
- SSE streaming, progress callbacks unchanged

### Claude's Discretion
- Exact dependency graph tracing (which of the ~10 internal deps are actually needed)
- Whether to keep transfer_adapter.py as wrapper or merge it into the new package's __init__.py
- Internal module organization within server/services/merge/

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- server/services/transfer_adapter.py — current adapter with clean public API
- server/services/transfer_config_shim.py — config injection logic (to be replaced)
- server/api/merge.py — FastAPI endpoints (unchanged by this phase)

### Established Patterns
- asyncio.to_thread() for blocking merge operations
- SSE streaming via sse_starlette for progress events
- Config shim via sys.modules injection
- MATCH_MODES constant dict for match type validation

### Integration Points
- server/api/merge.py imports from transfer_adapter (execute_transfer, execute_multi_language_transfer, MATCH_MODES)
- server/api/xlstransfer_async.py imports TransferAdapter
- server/services/__init__.py registers transfer_adapter
- QT core modules: xml_transfer, postprocess, source_scanner, language_loader (4 direct) + text_utils, xml_io, xml_parser, category_mapper, matching, korean_detection, excel_io, eventname_resolver, tmx_tools (~10 transitive)

</code_context>

<specifics>
## Specific Ideas

- Integration test: run merge through both old (sys.path) and new (package) paths, assert byte-identical output on all 3 match types
- Origin comments in each copied file: `# Origin: QuickTranslate/core/{name}.py`
- PyInstaller traces static imports natively — zero hiddenimports needed after this change

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
