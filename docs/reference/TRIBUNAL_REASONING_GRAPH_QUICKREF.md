# Tribunal Reasoning Graph — Quick Reference

**Task:** Transform tribunal verdicts from transient strings into persistent, queryable decision graph.

**Status:** Architecture COMPLETE (2026-03-22) — Ready for implementation.

## The 3-Layer Stack

```
┌────────────────────────────────────────────────────┐
│ Layer 3: ASYNC PERSISTENCE (non-blocking)          │
│ - INSERT async (< 10ms, fire-and-forget)           │
│ - Contradiction detection real-time (< 100ms)      │
│ - Batch audits hourly                              │
└────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────┐
│ Layer 2: VECTOR INDEX (HNSW)                       │
│ - Model2Vec 256-dim (79x faster than SBERT)        │
│ - IVFFLAT index (< 50ms similarity search)         │
│ - Query: "verdict_similarity > 0.85" → reuse       │
└────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────┐
│ Layer 1: CORE TABLES (PostgreSQL)                  │
│ - tribunal_verdicts      (id, question, verdict)   │
│ - tribunal_edges         (source→target, type)     │
│ - tribunal_contradictions (verdict_a, verdict_b)   │
│ - tribunal_audits        (accuracy, adoption)      │
└────────────────────────────────────────────────────┘
```

## Storage Strategy

| What | Why |
|------|-----|
| FULL verdict text (required) | Needed for audit, contradiction detection, expert eval |
| Verdict summary (300 chars, optional) | Lighter embedding, faster weekly updates |
| 256-dim embeddings (both) | Model2Vec: fast, small, 79x SBERT |
| Confidence score (0-1) | Queen's verdict confidence |
| Personas array | Which experts were consulted |
| Phase number | GSD phase context |
| Task ID | Link to Ruflo task (if action-driven) |
| Parent verdict ID | Lineage: "what decided led to this?" |

## Key Algorithms

### Contradiction Detection (< 100ms)

```
For each recent verdict (top 5):
  1. Question similarity: cosine > 0.75?
     NO → skip
     YES → proceed

  2. Confidence opposition: |conf_delta| > 0.6?
     (incompatible actions detected?)
     YES → CRITICAL (if q_sim > 0.85)
     YES → ERROR (if shared personas)
     YES → WARN (if q_sim > 0.70)
```

**Result:** CRITICAL conflicts prevent deployment, ERROR logged, WARN noted.

### Verdict Reuse Decision Tree

```
New question arrives
  │
  ├─ Question similarity > 0.85?
  │  └─ NO → Ask tribunal
  │  └─ YES → Proceed
  │
  ├─ Confidence > 0.7?
  │  └─ NO → Ask tribunal
  │  └─ YES → Proceed
  │
  ├─ Same/adjacent phase?
  │  └─ NO → Ask tribunal
  │  └─ YES → Proceed
  │
  ├─ Any contradictions?
  │  └─ YES → Ask tribunal
  │  └─ NO → REUSE
  │
  └─ Response:
     "✓ Reused: {question} ({days_ago}d ago)"
     "Confidence: {original × 0.7}"
     "Personas: {list}"
     "Verdict: {text}"
```

**Confidence penalty:** 0.7x (30% decay due to time + context uncertainty)

## Query Examples

### 1. Trace Root Cause
```sql
SELECT * FROM trace_verdict_ancestry(verdict_id=105, max_depth=10);
-- "What decisions led to this bug?"
```

### 2. Find Contradictions
```sql
SELECT * FROM find_phase_contradictions(phase_number=3) WHERE resolved=FALSE;
-- "Are there conflicts in Phase 3?"
```

### 3. Reuse Verdict
```sql
SELECT * FROM find_reusable_verdicts(
  question='Should we split mega_index.py?',
  similarity_threshold=0.85
);
-- "Has this been answered before?"
```

### 4. Expert Performance
```sql
SELECT * FROM expert_performance_summary();
-- "Which personas are most reliable?"
```

### 5. Phase Quality
```sql
SELECT * FROM phase_verdict_quality_summary();
-- "What's the verdict adoption rate?"
```

## Performance Guarantees

| Operation | Target | Notes |
|-----------|--------|-------|
| INSERT verdict | < 10ms | PostgreSQL native async |
| Vector search | < 50ms | IVFFLAT on 100K+ verdicts |
| Contradiction detect | < 100ms | In-memory scoring, top 5 |
| Ancestry trace | < 500ms | Recursive CTE, max 10 |
| Audit queries | < 200ms | Indexed lookups |

## Integration Checklist

- [ ] PostgreSQL database created
- [ ] Schema loaded (DDL from .sql file)
- [ ] IVFFLAT indexes verified
- [ ] Model2Vec embeddings accessible (Ollama running)
- [ ] `reasoning_graph.py` copied to tribunal MCP
- [ ] Dependencies installed (asyncpg)
- [ ] `tribunal_automaton` wired for async persistence
- [ ] Contradiction detection integrated
- [ ] Verdict reuse checks in `tribunal_decide`
- [ ] Post-phase audit workflow added
- [ ] Query API / skill tool created
- [ ] End-to-end test with real verdicts

## Files

| File | Purpose |
|------|---------|
| `docs/superpowers/specs/2026-03-22-tribunal-reasoning-graph.md` | Full architecture spec (629 lines) |
| `docs/reference/tribunal-reasoning-graph-schema.sql` | PostgreSQL DDL (432 lines) |
| `docs/reference/tribunal-reasoning-graph-implementation.py` | Python API (639 lines) |
| `docs/superpowers/plans/2026-03-22-tribunal-reasoning-graph-roadmap.md` | Implementation plan (444 lines) |
| `docs/reference/TRIBUNAL_REASONING_GRAPH_QUICKREF.md` | This file |

## Decision Log

| Decision | Why |
|----------|-----|
| Full verdict text (not summary) | Context needed for audit, expert eval, contradiction detection |
| Model2Vec 256-dim (not SBERT) | 79x faster, 12x smaller, sufficient for semantic search |
| IVFFLAT index (not exact) | Speed (< 50ms) vs precision trade-off, good for reuse detection |
| Async persistence | Tribunal response must be < 1ms delay from DB |
| Real-time contradictions (top 5) | Catches conflicts immediately, batch handles deeper analysis |
| Confidence decay 0.7x | 30% penalty for time + context drift (7 days old) |
| Phase-aware reuse | Same phase = exact context, adjacent phase = probably reusable |
| Manual CRITICAL review | False positive cost too high, human validation necessary |

## Storage Estimate

```
1000 verdicts (6 months heavy use):
  tribunal_verdicts:        ~2.5MB (text + vectors)
  tribunal_edges:           ~100KB
  tribunal_contradictions:  ~25KB
  tribunal_audits:          ~300KB
  ─────────────────────────────────
  TOTAL:                    ~3MB

PostgreSQL comfortable at millions of rows.
```

## Success Criteria

✓ Verdicts persisted to PostgreSQL
✓ Vector search < 50ms
✓ Contradictions detected < 100ms
✓ Verdict reuse working (> 80% similar questions found)
✓ Expert accuracy tracked
✓ Phase quality metrics visible
✓ Cross-session persistence verified
✓ No tribunal response delay (< 1ms from persistence)

---

**Next step:** Phase 1 (create PostgreSQL database + load schema). ~1 hour.
