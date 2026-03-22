# Phase 58: Merge API - Research

**Researched:** 2026-03-23
**Domain:** FastAPI endpoints for merge preview (dry-run) and execution (SSE streaming)
**Confidence:** HIGH

## Summary

Phase 58 creates FastAPI endpoints that expose the Phase 57 transfer_adapter functions to the frontend. Two main endpoints are needed: a synchronous `POST /api/merge/preview` for dry-run summaries, and a `POST /api/merge/execute` that streams progress via Server-Sent Events (SSE).

The project already has `sse-starlette` v3.3.2 installed (dependency of `mcp`), providing `EventSourceResponse` which accepts an async generator and streams `text/event-stream` responses. The existing `StreamingResponse` usage in the codebase is for file downloads (BytesIO), not SSE. This phase introduces the first SSE endpoint in the project.

The transfer_adapter.py from Phase 57 provides three key functions: `execute_transfer()` (single language), `execute_multi_language_transfer()` (multi-language), and `scan_source_languages()` (folder scanning). All three accept `progress_callback` and `log_callback` parameters where `progress_callback(message: str)` receives plain string messages like "Parsing file.xml... (1/5)" and `log_callback(message: str, level: str)` receives log messages with severity. The dry-run preview uses `dry_run=True` which computes matches without writing files.

**Primary recommendation:** Create `server/api/merge.py` with router prefix `/api/merge`, two POST endpoints (`/preview` and `/execute`), Pydantic models for request/response, and register in `server/main.py`. Use `EventSourceResponse` from `sse-starlette` for the execute endpoint. Run `transfer_folder_to_folder` in a thread via `asyncio.to_thread()` since QuickTranslate functions are synchronous and blocking.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | POST /api/merge/preview returns dry-run summary (files, entries, matches, overwrites) | `execute_transfer(dry_run=True)` returns dict with matched/updated/not_found/skipped counts; `execute_multi_language_transfer(dry_run=True)` adds per-language breakdown |
| API-02 | POST /api/merge/execute streams progress via SSE (file-by-file + postprocess steps) | `sse-starlette` v3.3.2 installed; `EventSourceResponse` accepts async generator; `progress_callback` receives per-file messages from QT engine |
| API-03 | Merge summary report returned on completion (matched, skipped, overwritten counts) | Final SSE event contains full result dict from `transfer_folder_to_folder` with all aggregate counters |
| API-04 | POST /api/merge/preview supports multi-language mode (scans folder, returns per-language breakdown) | `scan_source_languages()` returns `{languages: {code: [files]}, total_files, language_count}`; `execute_multi_language_transfer(dry_run=True)` returns per_language breakdown |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (project version) | API framework | Already in use, all endpoints use FastAPI |
| sse-starlette | 3.3.2 | SSE streaming responses | Already installed (mcp dependency), provides EventSourceResponse |
| Pydantic | v2 (project version) | Request/response models | Already in use, `from_attributes = True` pattern |
| asyncio | stdlib | Thread offloading for blocking QT calls | `asyncio.to_thread()` for running sync code without blocking event loop |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | (project version) | Logging | Project mandate: never print(), always loguru |
| server.services.transfer_adapter | Phase 57 | Transfer engine wrapper | All merge operations delegate to this |
| server.api.settings | Phase 56 | WSL path translation | Reuse `translate_wsl_path()` for DEV_MODE paths |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sse-starlette | Raw StreamingResponse with text/event-stream | sse-starlette handles ping, reconnect, proper event formatting. No reason to hand-roll since it's already installed |
| asyncio.to_thread | BackgroundTasks | BackgroundTasks can't stream progress back. Thread offload keeps the event loop free while QuickTranslate runs |
| Separate /preview and /preview/multi | Single /preview with mode param | Two endpoints is cleaner but adds surface area. Single endpoint with optional `multi_language: bool` field is simpler -- recommended |

## Architecture Patterns

### Recommended Project Structure

```
server/api/
    merge.py             # NEW: Merge API endpoints (preview + execute)
    settings.py          # EXISTING: Path validation (Phase 56)
    schemas.py           # EXISTING: Shared schemas (NOT used here -- merge schemas in merge.py)
server/services/
    transfer_adapter.py  # EXISTING: QuickTranslate wrapper (Phase 57)
    transfer_config_shim.py  # EXISTING: Config shim (Phase 57)
server/main.py           # MODIFIED: Add merge router registration
```

### Pattern 1: Router Registration (Follow Existing Pattern)

**What:** All API routers in this project use `APIRouter(prefix=..., tags=[...])` and are registered in `main.py` with `app.include_router(router)`.

**When to use:** Always for new API modules.

**Example (from server/api/settings.py):**
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/merge", tags=["Merge"])
```

**Registration in main.py (after settings_api, before ldm_router):**
```python
# Include Merge API (Phase 58: Merge preview + execute)
from server.api import merge as merge_api
app.include_router(merge_api.router)
```

### Pattern 2: Pydantic Models Co-located in Route File

**What:** The settings.py pattern defines request/response models in the same file as endpoints (not in schemas.py). This is the newer Phase 56 pattern.

**When to use:** For self-contained API modules with few models.

```python
from pydantic import BaseModel

class MergePreviewRequest(BaseModel):
    source_path: str          # Path to correction files folder
    target_path: str          # LOC folder with languagedata_*.xml
    export_path: str          # EXPORT folder for category lookups
    match_mode: str = "strict"  # "stringid_only" | "strict" | "strorigin_filename"
    only_untranslated: bool = False
    stringid_all_categories: bool = False
    multi_language: bool = False  # True = scan folder for languages

class MergePreviewResponse(BaseModel):
    files_processed: int = 0
    total_corrections: int = 0
    total_matched: int = 0
    total_updated: int = 0
    total_not_found: int = 0
    total_skipped: int = 0
    total_skipped_translated: int = 0
    overwrite_warnings: list[str] = []
    errors: list[str] = []
    # Multi-language specific
    per_language: dict | None = None
    scan: dict | None = None

class MergeExecuteRequest(BaseModel):
    source_path: str
    target_path: str
    export_path: str
    match_mode: str = "strict"
    only_untranslated: bool = False
    stringid_all_categories: bool = False
    multi_language: bool = False
```

### Pattern 3: SSE Streaming with EventSourceResponse

**What:** Use `sse-starlette`'s `EventSourceResponse` to stream progress events from the blocking QuickTranslate engine. The QT engine runs in a thread; progress messages are sent via an asyncio Queue.

**When to use:** For the `/api/merge/execute` endpoint.

```python
import asyncio
import json
from sse_starlette.sse import EventSourceResponse

@router.post("/execute")
async def execute_merge(body: MergeExecuteRequest):
    queue: asyncio.Queue = asyncio.Queue()

    def progress_cb(message: str):
        # Called from sync thread -- use put_nowait on threadsafe queue
        queue.put_nowait({"event": "progress", "data": message})

    def log_cb(message: str, level: str = "info"):
        queue.put_nowait({"event": "log", "data": json.dumps({"message": message, "level": level})})

    async def run_transfer():
        """Run blocking transfer in thread, then signal completion."""
        try:
            if body.multi_language:
                result = await asyncio.to_thread(
                    execute_multi_language_transfer,
                    source_path=translated_source,
                    target_path=translated_target,
                    export_path=translated_export,
                    match_mode=body.match_mode,
                    only_untranslated=body.only_untranslated,
                    stringid_all_categories=body.stringid_all_categories,
                    dry_run=False,
                    progress_callback=progress_cb,
                    log_callback=log_cb,
                )
            else:
                result = await asyncio.to_thread(
                    execute_transfer,
                    source_path=translated_source,
                    target_path=translated_target,
                    export_path=translated_export,
                    match_mode=body.match_mode,
                    only_untranslated=body.only_untranslated,
                    stringid_all_categories=body.stringid_all_categories,
                    dry_run=False,
                    progress_callback=progress_cb,
                    log_callback=log_cb,
                )
            queue.put_nowait({"event": "complete", "data": json.dumps(result, default=str)})
        except Exception as exc:
            queue.put_nowait({"event": "error", "data": str(exc)})

    async def event_generator():
        task = asyncio.create_task(run_transfer())
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "keepalive"}
                continue
            yield msg
            if msg["event"] in ("complete", "error"):
                break
        await task  # Ensure task is fully done

    return EventSourceResponse(event_generator())
```

### Pattern 4: WSL Path Translation (Reuse Phase 56)

**What:** In DEV_MODE, the frontend sends Windows paths (e.g., `C:\Users\MYCOM\...`) which must be translated to WSL `/mnt/c/...` paths. Phase 56's `translate_wsl_path()` handles this.

```python
from server.api.settings import translate_wsl_path

translated_source = translate_wsl_path(body.source_path)
translated_target = translate_wsl_path(body.target_path)
translated_export = translate_wsl_path(body.export_path)
```

### Pattern 5: Overwrite Warning Extraction from Dry-Run Results

**What:** The dry-run result from `transfer_folder_to_folder` includes `total_skipped_translated` (entries that already have translations and would be overwritten if scope is "Transfer All"). Extract these as overwrite warnings for the preview.

```python
def extract_overwrite_warnings(result: dict) -> list[str]:
    warnings = []
    file_results = result.get("file_results", {})
    for fname, fdata in file_results.items():
        if isinstance(fdata, dict):
            skipped = fdata.get("skipped_translated", 0)
            matched = fdata.get("matched", 0)
            if matched > 0 and not only_untranslated:
                warnings.append(
                    f"{fname}: {matched} entries will be overwritten"
                )
    return warnings
```

### Anti-Patterns to Avoid

- **NEVER run QuickTranslate functions directly in the async endpoint handler.** They are synchronous and blocking (XML parsing, file I/O). Always use `asyncio.to_thread()`.
- **NEVER use `queue.put()` from the sync callback thread.** `asyncio.Queue.put()` is a coroutine. Use `put_nowait()` which is thread-safe for this use case (queue is unbounded).
- **NEVER serialize Path objects directly in JSON.** QuickTranslate result dicts contain Path objects in `file_results` keys. Use `default=str` in `json.dumps()`.
- **NEVER forget WSL path translation.** Every path from the frontend must go through `translate_wsl_path()` before being passed to the adapter.
- **NEVER add auth/permissions to these endpoints.** The existing pattern in settings.py has no auth. This is a local desktop app (Electron), not a multi-user server. Merge endpoints should follow the same pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE event formatting | Manual `text/event-stream` with StreamingResponse | `sse-starlette` EventSourceResponse | Handles ping, reconnect ID, proper newline formatting, connection cleanup |
| Merge logic | Any merge code in the API layer | `transfer_adapter.execute_transfer()` / `execute_multi_language_transfer()` | Phase 57 adapter wraps QuickTranslate's 3064-line engine |
| Language scanning | Custom folder scanning | `transfer_adapter.scan_source_languages()` | Wraps QuickTranslate's battle-tested scanner |
| Path translation | Custom Windows-to-WSL conversion | `settings.translate_wsl_path()` | Phase 56 already handles drive letter detection + DEV_MODE check |
| Result aggregation | Custom counter accumulation | Use raw result dict from `transfer_folder_to_folder` | Already has all counters: matched, updated, not_found, skipped_*, errors |

**Key insight:** The API layer is thin. It translates paths, dispatches to the adapter, and streams progress. All merge logic lives in the adapter (Phase 57) which delegates to QuickTranslate (Sacred Script).

## Common Pitfalls

### Pitfall 1: asyncio Queue Thread Safety

**What goes wrong:** `asyncio.Queue.put()` is a coroutine -- calling it from a sync thread (inside `asyncio.to_thread`) raises "cannot await in non-async context."
**Why it happens:** The progress_callback runs in the thread pool, not the event loop.
**How to avoid:** Use `queue.put_nowait()` which is synchronous and safe from any thread. The queue is unbounded so it won't raise QueueFull.
**Warning signs:** RuntimeError about "cannot await" or "got Future attached to a different loop."

### Pitfall 2: Path Objects in JSON Serialization

**What goes wrong:** `json.dumps(result)` fails with `TypeError: Object of type PosixPath is not JSON serializable`.
**Why it happens:** `transfer_folder_to_folder` returns Path objects in `file_results` keys and some nested values.
**How to avoid:** Always use `json.dumps(result, default=str)` when serializing the merge result dict.
**Warning signs:** TypeError on the `complete` SSE event.

### Pitfall 3: SSE Connection Timeout

**What goes wrong:** Large merges (many files, slow disk) can take minutes. If no events are sent, the client or proxy may close the connection.
**Why it happens:** QuickTranslate only calls `progress_callback` when processing each file. Between files (during XML parsing), there may be long silence.
**How to avoid:** The event_generator includes a 30-second timeout that sends a ping event. `sse-starlette` also has a built-in `ping` parameter, but explicit timeout handling is more reliable.

### Pitfall 4: Config Shim Race Condition

**What goes wrong:** If two merge operations run simultaneously with different paths, the shared `sys.modules["config"]` gets overwritten.
**Why it happens:** The config shim is a global singleton injected into sys.modules.
**How to avoid:** For v6.0 demo, this is acceptable -- only one merge at a time. Document as known limitation. For production, would need per-request config isolation (e.g., thread-local or process-based).
**Warning signs:** Wrong language files being merged.

### Pitfall 5: Forgetting DEV_MODE Path Translation

**What goes wrong:** In DEV_MODE (WSL), the frontend sends Windows paths like `C:\Users\MYCOM\Desktop\test123`. The adapter expects Linux paths.
**Why it happens:** The frontend stores paths as-entered by the user (from Windows Settings UI).
**How to avoid:** Apply `translate_wsl_path()` to ALL three paths (source, target, export) before passing to the adapter.

### Pitfall 6: Multi-Language vs Single-Language Mode

**What goes wrong:** Calling `execute_transfer()` for multi-language source folders processes only the first detected language. Calling `execute_multi_language_transfer()` for single files adds unnecessary scanning overhead.
**Why it happens:** The two adapter functions serve different use cases.
**How to avoid:** Use the `multi_language` flag in the request body. Single-language = `execute_transfer()`, multi-language = `execute_multi_language_transfer()`.

## Code Examples

### SSE Event Format (what the frontend receives)

```
event: progress
data: Parsing corrections_FRE.xml... (1/3)

event: progress
data: Processing languagedata_FRE.xml (1/2)

event: log
data: {"message": "Pre-filter: 5/12 target files skipped", "level": "info"}

event: progress
data: Running postprocess on languagedata_FRE.xml...

event: complete
data: {"match_mode": "strict", "files_processed": 3, "total_matched": 45, "total_updated": 42, "total_not_found": 3, ...}
```

### Dry-Run Preview Response (single language)

```json
{
    "files_processed": 2,
    "total_corrections": 150,
    "total_matched": 45,
    "total_updated": 0,
    "total_not_found": 105,
    "total_skipped": 0,
    "total_skipped_translated": 12,
    "overwrite_warnings": [
        "languagedata_FRE.xml: 45 entries will be overwritten"
    ],
    "errors": [],
    "per_language": null,
    "scan": null
}
```

### Multi-Language Preview Response

```json
{
    "files_processed": 4,
    "total_corrections": 300,
    "total_matched": 120,
    "total_updated": 0,
    "total_not_found": 180,
    "total_skipped": 0,
    "total_skipped_translated": 20,
    "overwrite_warnings": [],
    "errors": [],
    "per_language": {
        "FRE": {"matched": 60, "updated": 0, "not_found": 90, "skipped": 0, "errors": 0},
        "ENG": {"matched": 60, "updated": 0, "not_found": 90, "skipped": 0, "errors": 0}
    },
    "scan": {
        "languages": {"FRE": ["/path/corrections_FRE.xml"], "ENG": ["/path/corrections_ENG.xml"]},
        "total_files": 2,
        "language_count": 2,
        "unrecognized": [],
        "warnings": []
    }
}
```

### Transfer Adapter Function Signatures (from Phase 57)

```python
# server/services/transfer_adapter.py

def execute_transfer(
    source_path: str,
    target_path: str,
    export_path: str,
    match_mode: str = "strict",
    only_untranslated: bool = False,
    stringid_all_categories: bool = False,
    dry_run: bool = False,
    progress_callback=None,   # callback(message: str)
    log_callback=None,        # callback(message: str, level: str)
) -> dict

def scan_source_languages(
    source_path: str,
    target_path: str | None = None,
) -> dict

def execute_multi_language_transfer(
    source_path: str,
    target_path: str,
    export_path: str,
    match_mode: str = "strict",
    only_untranslated: bool = False,
    stringid_all_categories: bool = False,
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
) -> dict
```

### progress_callback Signature (from QuickTranslate source)

```python
# Called with a single string argument:
progress_callback("Parsing corrections_FRE.xml... (1/3)")
progress_callback("Processing languagedata_FRE.xml (1/2)")
progress_callback("Pre-filtering 12 target files...")
progress_callback("Resolving EventNames to StringIDs...")
progress_callback("Extracting StringIDs from all source files for filtering...")
```

### log_callback Signature (from QuickTranslate source)

```python
# Called with message string and level string:
log_callback("WARNING: 5 entries contain formula-like text (skipped)", 'warning')
log_callback("FRE: 150 corrections -> 2 XML files", 'header')
log_callback("Pre-filter: 5/12 target files skipped (zero matching corrections)", 'info')
```

## State of the Art

| Old Approach (v2.0) | Current Approach (v6.0 Phase 58) | Impact |
|---------------------|----------------------------------|--------|
| Synchronous POST endpoint returns result | SSE streaming with per-file progress updates | Real-time feedback in UI |
| No preview/dry-run | Dry-run mode computes matches without writing | User can review before committing |
| No multi-language support | Per-language breakdown in preview and execution | Batch processing visibility |
| No overwrite warnings | Extract skipped_translated from dry-run as warnings | User sees what will be overwritten |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in project) |
| Config file | existing pytest config |
| Quick run command | `python3 -m pytest tests/test_merge_api.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | POST /api/merge/preview returns dry-run summary | integration | `pytest tests/test_merge_api.py::test_preview_dry_run -x` | Wave 0 |
| API-02 | POST /api/merge/execute streams SSE progress | integration | `pytest tests/test_merge_api.py::test_execute_sse_stream -x` | Wave 0 |
| API-03 | Merge summary on completion | integration | `pytest tests/test_merge_api.py::test_execute_completion_summary -x` | Wave 0 |
| API-04 | Multi-language preview mode | integration | `pytest tests/test_merge_api.py::test_preview_multi_language -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_merge_api.py -x -q`
- **Per wave merge:** Full suite
- **Phase gate:** All 4 API tests green before verify

### Wave 0 Gaps
- [ ] `tests/test_merge_api.py` -- covers API-01 through API-04
- [ ] Test fixtures: mock transfer_adapter functions (avoid needing real QT modules for API tests)

## Open Questions

1. **SSE client disconnect handling**
   - What we know: `sse-starlette` handles client disconnects gracefully (stops the generator).
   - What's unclear: Whether the background `asyncio.to_thread` task should be cancelled when the client disconnects, or if it should complete (merge is already modifying files).
   - Recommendation: Let the merge complete even if client disconnects. Files are already being modified -- stopping mid-merge would leave corrupted data. The result can be logged server-side.

2. **Concurrent merge prevention**
   - What we know: Config shim is a global singleton. Two simultaneous merges would corrupt each other.
   - What's unclear: Whether the frontend needs a server-side lock or if UI-level prevention is sufficient.
   - Recommendation: Add a simple module-level `_merge_in_progress` flag. Return 409 Conflict if a merge is already running. Reset on completion/error. This is cheap and prevents corruption.

## Sources

### Primary (HIGH confidence)
- `server/services/transfer_adapter.py` -- read in full, all function signatures verified
- `server/services/transfer_config_shim.py` -- read in full, config shim lifecycle understood
- `server/api/settings.py` -- read in full, router pattern + WSL path translation verified
- `server/main.py` -- read router registration section, pattern confirmed
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py` -- read progress_callback and log_callback usage (lines 1717-2660+), result dict structure verified
- `sse-starlette` v3.3.2 -- verified installed, EventSourceResponse signature checked via inspect

### Secondary (MEDIUM confidence)
- `server/api/schemas.py` -- read in full, confirmed Pydantic v2 patterns
- `server/tools/ldm/router.py` -- read for router aggregation pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- sse-starlette verified installed, all project patterns observed in existing code
- Architecture: HIGH -- follows established project patterns (router, Pydantic models, main.py registration)
- Pitfalls: HIGH -- identified from direct analysis of threading model, config shim globals, and QT callback signatures

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- all components are project-internal or already installed)
