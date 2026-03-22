# Tribunal Reasoning Graph — Implementation Roadmap

**Status:** DRAFT (architecture complete, implementation pending)
**Target:** 4 hours, can run in parallel phases with teammates
**Spec:** `docs/superpowers/specs/2026-03-22-tribunal-reasoning-graph.md`
**Schema:** `docs/reference/tribunal-reasoning-graph-schema.sql`
**Code Reference:** `docs/reference/tribunal-reasoning-graph-implementation.py`

---

## Overview

Transform tribunal from **transient decision factory** into **persistent knowledge base** with:
- ✓ Full verdict text storage (PostgreSQL)
- ✓ Vector similarity search (HNSW, IVFFLAT, 256-dim Model2Vec)
- ✓ Real-time contradiction detection (< 100ms)
- ✓ Intelligent verdict reuse (avoid redundant decisions)
- ✓ Expert quality audit (persona accuracy tracking)
- ✓ Cross-session persistence (verdicts survive restarts)

---

## Phase 1: Core Schema (1 hour)

### Task 1.1: Create PostgreSQL Database & Tables

```bash
# SSH to server with PostgreSQL access, run:
psql -U postgres -d template1 -c "CREATE DATABASE tribunal_reasoning;"

# Load schema
psql -U postgres -d tribunal_reasoning < docs/reference/tribunal-reasoning-graph-schema.sql

# Verify tables + indexes
psql -U postgres -d tribunal_reasoning -c "
    SELECT tablename FROM pg_tables WHERE schemaname='public'
    UNION ALL
    SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_%';
"
```

**Success criteria:**
- 4 tables exist: `tribunal_verdicts`, `tribunal_edges`, `tribunal_contradictions`, `tribunal_audits`
- IVFFLAT indexes on `question_embedding`, `verdict_embedding`
- All functions created: `find_reusable_verdicts()`, `trace_verdict_ancestry()`, `expert_performance_summary()`, etc.

### Task 1.2: Test Vector Search

```bash
psql -U postgres -d tribunal_reasoning -c "
-- Insert test verdict
INSERT INTO tribunal_verdicts (question, verdict_text, confidence, personas) VALUES
    ('Should we split mega_index.py?', 'Split into 4 modules', 0.9, ARRAY['architect-db', 'python-pro']);

-- Test similarity search (should be fast)
SELECT question, confidence,
       1 - (question_embedding <-> '...'::vector) as similarity
FROM tribunal_verdicts
ORDER BY similarity DESC LIMIT 3;
"
```

**Success criteria:** Vector queries return results in < 50ms

---

## Phase 2: Async Persistence Layer (1 hour)

### Task 2.1: Integrate `reasoning_graph.py` into Tribunal MCP

Copy `/docs/reference/tribunal-reasoning-graph-implementation.py` → `~/.claude/mcp-servers/tribunal/reasoning_graph.py`

```bash
# Add dependencies to tribunal/requirements.txt
echo "asyncpg==0.30.0" >> ~/.claude/mcp-servers/tribunal/requirements.txt

# Install
cd ~/.claude/mcp-servers/tribunal && pip install -r requirements.txt
```

### Task 2.2: Wire into `tribunal_automaton`

In `~/.claude/mcp-servers/tribunal/server.py`, add to `tribunal_automaton()`:

```python
from reasoning_graph import VerdictGraph, VerdictInput

# At module level (once, not per request):
_graph = None

async def _init_graph():
    global _graph
    if _graph is None:
        _graph = VerdictGraph(db_url=os.getenv('TRIBUNAL_DB_URL', 'postgresql://localhost/tribunal_reasoning'))
        await _graph.connect()

# In tribunal_automaton():
await _init_graph()

# After verdict is generated (non-blocking):
asyncio.create_task(_graph.persist_verdict_async(VerdictInput(
    question=params.question,
    verdict_text=verdict,
    confidence=tr['queen']['confidence'],
    personas=names,
    persona_models=params.model_personas,
    queen_model=params.model_queen,
    phase_number=context.get('phase_number'),
    task_id=task_ids[0] if task_ids else None,
    parent_decision_id=context.get('parent_verdict_id'),
    session_id=context.get('session_id'),
    total_ms=tr['total_ms']
)))

# Return verdict immediately (don't wait for DB insert)
return formatted_output
```

**Success criteria:**
- `tribunal_automaton` calls `_persist_verdict_async()`
- Response returned instantly (< 1ms delay from persistence)
- Verdicts appear in PostgreSQL within 100ms

### Task 2.3: Test Async Persistence

```python
# In Claude Code:
import asyncio
from reasoning_graph import VerdictGraph, VerdictInput

graph = VerdictGraph()
await graph.connect()

# Fire async
asyncio.create_task(graph.persist_verdict_async(VerdictInput(
    question="Test question?",
    verdict_text="Test verdict",
    confidence=0.8,
    personas=["test-persona"]
)))

# Return immediately
print("Response sent")

# 1 second later, verify in DB
await asyncio.sleep(1)
verdicts = await graph.find_reusable_verdicts("Test question?")
assert len(verdicts) > 0, "Verdict not persisted!"
```

**Success criteria:** Verdicts appear in database despite async persistence

---

## Phase 3: Contradiction Detection (1 hour)

### Task 3.1: Real-Time Detection

Add to `tribunal_automaton()` after persistence:

```python
# Real-time contradiction detection (top 5 recent)
new_verdict_dict = {
    'verdict_id': verdict_id_just_inserted,
    'question': params.question,
    'verdict_text': verdict,
    'confidence': tr['queen']['confidence'],
    'personas': names
}

conflicts = await _graph.detect_contradictions_realtime(new_verdict_dict)

if conflicts:
    for c in conflicts:
        if c.severity == 'CRITICAL':
            logger.error(f"CRITICAL CONFLICT: {c.conflict_type} between verdicts {c.verdict_a_id} and {c.verdict_b_id}")
        lines.append(f"\n⚠️  {c.severity} CONFLICT: {c.conflict_type}")
        lines.append(f"   vs: {c.question_a[:80]}")
        lines.append(f"   Details: {c.details}")
```

**Success criteria:**
- Contradictions detected in < 100ms
- CRITICAL conflicts logged
- User sees contradiction warnings in response

### Task 3.2: Test Contradiction Detection

```bash
# Insert two contradictory verdicts
psql -U postgres -d tribunal_reasoning -c "
INSERT INTO tribunal_verdicts (question, verdict_text, confidence, personas) VALUES
    ('How to organize mega_index.py?', 'Split into 4 modules: builder, lookup, cache, export', 0.9, ARRAY['architect']),
    ('How to organize mega_index.py?', 'Keep as monolithic module for performance', 0.85, ARRAY['architect']);
"

# Run contradiction detector
# Should find CRITICAL conflict (split vs keep monolithic)
```

**Success criteria:** Contradictions correctly identified and stored

---

## Phase 4: Verdict Reuse (1 hour)

### Task 4.1: Check Reusability in `tribunal_decide`

Modify `tribunal_decide()` to check for reusable verdicts BEFORE running tribunal:

```python
# Check for reuse
if context.get('check_reusable', True):
    reusable = await _graph.find_reusable_verdicts(
        params.question,
        similarity_threshold=0.85,
        days_old=90
    )
    if reusable:
        r = reusable[0]
        lines = [
            "=" * 60,
            " ✓ REUSED VERDICT (similar question answered before)",
            "=" * 60,
            f"\nOriginal Q: {r['question']}",
            f"Answered: {r['created_at']}",
            f"Confidence: {r['confidence']} (decay penalty: 0.7x = {r['confidence'] * 0.7:.2f})",
            f"Personas: {', '.join(r['personas'])}",
            f"\n{r['verdict_text']}",
            f"\nSimilarity: {r['similarity']:.2f}",
            "=" * 60
        ]
        return "\n".join(lines)

# No reuse found, proceed to tribunal
names = _select_personas(params.question, params.max_personas)
...
```

**Success criteria:**
- Reusable verdicts found and returned
- No redundant tribunal calls for similar questions
- Confidence decay applied (0.7x)

### Task 4.2: Test Reuse Pipeline

```python
# Store verdict A
await graph.persist_verdict_async(VerdictInput(
    question="Should we split mega_index.py?",
    verdict_text="Split into builder, lookup, cache, export modules",
    confidence=0.9,
    personas=["architect-db"]
))

await asyncio.sleep(1)

# Query with similar question (should reuse)
reusable = await graph.find_reusable_verdicts(
    "How should we split mega_index.py?",  # Slight variation
    similarity_threshold=0.80
)

assert len(reusable) > 0
assert reusable[0]['similarity'] > 0.80
```

**Success criteria:** Similar questions trigger verdict reuse

---

## Phase 5: Audit & Quality Integration (1 hour)

### Task 5.1: End-of-Phase Assessment Workflow

Create post-phase script that marks verdicts as success/partial/failed:

```python
async def assess_phase_verdicts(phase_number: int, results: Dict):
    """After GSD phase execution, assess verdict accuracy."""
    async with _graph.pool.acquire() as conn:
        # Get all verdicts from this phase
        verdicts = await conn.fetch(
            "SELECT verdict_id, question FROM tribunal_verdicts WHERE phase_number = $1",
            phase_number
        )

        for v in verdicts:
            # Human assessment (or automated heuristics)
            actual_success = results.get(v['question'], 'unknown')

            await conn.execute(
                """
                INSERT INTO tribunal_audits (
                    verdict_id, accuracy, was_acted_on, implementation_result
                ) VALUES ($1, $2, $3, $4)
                """,
                v['verdict_id'],
                0.9 if actual_success == 'success' else 0.5,  # Example
                True,
                actual_success
            )
```

### Task 5.2: Quality Dashboard

Query expert performance:

```python
experts = await _graph.expert_performance_summary()
# Output:
# persona_name: 'architecture-designer'
# total_verdicts: 12
# avg_accuracy: 0.85
# confidence_calibration: 0.1 (slightly overconfident)
# last_audit: 2026-03-22T10:30:00Z
```

**Success criteria:**
- Phase assessment complete
- Expert accuracy tracked
- Quality metrics visible

---

## Phase 6: Cross-Session Query API (30 min)

### Task 6.1: Add REST Endpoints to Tribunal MCP

New endpoints (or Skill tool):

```
GET /api/verdicts/ancestry/{verdict_id}
    → Trace decision lineage

GET /api/verdicts/contradictions?phase={N}
    → Find unresolved conflicts

GET /api/verdicts/reusable?question={Q}
    → Find similar questions

GET /api/verdicts/quality/experts
    → Expert performance summary

GET /api/verdicts/quality/phases
    → Phase verdict adoption rates
```

### Task 6.2: Wire into Skill

Update `decision-tribunal` skill to expose queries:

```
/tribunal-graph:ancestry {verdict_id}
    Trace what led to this verdict

/tribunal-graph:contradictions {phase_number}
    Show conflicts in phase

/tribunal-graph:experts
    Show expert performance leaderboard
```

**Success criteria:** Queries accessible from Claude Code

---

## Implementation Order (Parallel Possible)

**Solo flow (4 hours):**
1. Phase 1: Schema (1h) → verify with sample data
2. Phase 2: Async persistence (1h) → test non-blocking INSERT
3. Phase 3: Contradiction detection (1h) → test with conflicting verdicts
4. Phase 4: Verdict reuse (1h) → test similarity search

**Team flow (2 hours with 2 teammates):**
- Teammate A: Phase 1 + Phase 2 (schema + persistence)
- Teammate B: Phase 3 + Phase 4 (contradictions + reuse)
- Lead: Phase 5 + Phase 6 (audit + API)
- Sync: Test end-to-end integration

---

## Verification Checklist

- [ ] PostgreSQL database created + all 4 tables present
- [ ] IVFFLAT vector indexes created + confirm with `\d tribunal_verdicts`
- [ ] Model2Vec embeddings loading (test with `embed_text()`)
- [ ] Async INSERT non-blocking (tribunal response < 1ms delay)
- [ ] Verdict persisted within 100ms (check with follow-up query)
- [ ] Contradictions detected in < 100ms (log timing)
- [ ] Verdict reuse works (similar question returns cached verdict)
- [ ] Confidence decay applied (0.7x)
- [ ] Expert performance queries return data
- [ ] Phase quality metrics accurate
- [ ] Cross-session queries work (verdicts survive session restart)
- [ ] Test with real tribunal verdicts (not just synthetic data)

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Model2Vec embedding slow (> 500ms) | Medium | Cache embeddings, batch weekly update |
| Vector index grows slow (millions of rows) | Low | PostgreSQL IVFFLAT scales to millions |
| Contradiction detection false positives | Medium | Manual review for CRITICAL, tune thresholds |
| Database connection pool exhaustion | Low | Max 10 connections, timeout 60s |
| Async persistence race condition | Low | asyncpg handles atomicity, no conflicts |

---

## Success Criteria (Overall)

✓ All verdicts stored persistently (survive session restart)
✓ Contradiction detection working (0 false negatives on CRITICAL)
✓ Verdict reuse found (> 80% of similar questions identified)
✓ Expert quality tracked (accuracy > 0.75 on average)
✓ Queries < 100ms (vector search, ancestry trace, contradiction detection)
✓ Non-blocking persistence (tribunal response < 1ms delay from DB)
✓ Cross-session persistence (verdicts queryable days later)

---

## Files Created/Modified

| File | Status | Purpose |
|------|--------|---------|
| `docs/superpowers/specs/2026-03-22-tribunal-reasoning-graph.md` | ✓ Complete | Architecture spec |
| `docs/reference/tribunal-reasoning-graph-schema.sql` | ✓ Complete | PostgreSQL DDL |
| `docs/reference/tribunal-reasoning-graph-implementation.py` | ✓ Complete | Python API |
| `~/.claude/mcp-servers/tribunal/server.py` | PENDING | Add async persistence + queries |
| `~/.claude/skills/tribunal-graph-explorer/SKILL.md` | PENDING | New skill for graph queries |

---

## Next Steps

1. **Approval:** User reviews architecture + roadmap
2. **Setup:** Create PostgreSQL database + load schema
3. **Implementation:** Run phases 1-6 (solo or team)
4. **Integration:** Sync with tribunal_automaton
5. **Testing:** Verify all verdicts persisted + queries work
6. **Deployment:** Enable reasoning graph by default in tribunal_automaton
