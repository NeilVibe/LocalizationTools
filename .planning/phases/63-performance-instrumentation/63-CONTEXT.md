# Phase 63: Performance Instrumentation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add duration logging to all hot paths (embedding, FAISS search, TM CRUD, merge operations, file upload) and expose a performance summary API endpoint. Pure infrastructure — no behavioral changes.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.
- Structured logging with duration_ms fields using loguru
- Performance metrics collection pattern (in-memory ring buffer vs simple list)
- API endpoint design for GET /api/performance/summary
- Which operations to instrument (guided by PERF-01 through PERF-06 requirements)
- Timer decorator or context manager pattern for duration measurement

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- loguru logger used everywhere (CLAUDE.md: "Never print(), always loguru")
- server/tools/ldm/indexing/ — embedding + FAISS operations (Phase 62 just updated)
- server/services/merge/ — merge pipeline (Phase 61 just internalized)
- server/api/merge.py — merge endpoints with SSE streaming
- server/tools/ldm/routes/ — TM CRUD and upload endpoints

### Established Patterns
- FastAPI APIRouter for endpoints
- asyncio.to_thread() for blocking operations
- TrackedOperation context manager in server/utils/progress_tracker.py

### Integration Points
- All hot paths already use loguru — add structured duration fields
- New API router for /api/performance/ endpoints
- server/main.py for router registration

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
