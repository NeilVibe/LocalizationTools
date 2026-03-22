# Tribunal Reasoning Graph — Persistent Decision Traceability

**Date:** 2026-03-22
**Status:** Architecture DRAFT (implementation pending)
**Purpose:** Transform tribunal verdicts from transient strings into a queryable, auditable reasoning graph with contradiction detection, verdict reuse, and decision lineage tracing.

---

## Problem

Current tribunal stack:
```
tribunal_decide → 3-5 personas (parallel) → queen verdict → Ruflo memory (opaque string)
                                                                         ↓
                                                              Lost after session ends
                                                    No contradiction detection
                                                    No verdict reuse discovery
                                                    No decision ancestry
                                                    No quality audit trail
```

**Issues:**
1. Verdicts stored as opaque strings in Ruflo — no structure
2. No contradiction detection between Phase 1 and Phase 3 decisions
3. No way to query "similar question answered before?" (verdict reuse)
4. No ancestry tracking ("which decision led to this bug?")
5. No expert quality audit ("which personas are overconfident?")
6. Session restart = verdicts lost (not persisted across sessions)

---

## Solution: Persistent PostgreSQL Graph + Vector Index

Three-layer stack:

```
┌─ Layer 1: CORE TABLES (PostgreSQL) ──────────────────┐
│  ├─ tribunal_verdicts       (id, question, verdict, confidence, personas, phase, task_id, parent_id)
│  ├─ tribunal_edges          (source_id → target_id, edge_type: REFINES, CONTRADICTS, ENABLES, BLOCKS, REUSES)
│  └─ tribunal_contradictions (verdict_a, verdict_b, severity, details, detected_at)
│
├─ Layer 2: VECTOR INDEX (HNSW) ───────────────────────┤
│  ├─ question_embedding (question text → 256-dim)
│  ├─ verdict_summary_embedding (verdict text → 256-dim)
│  └─ Similarity queries (< 50ms, < 100 results)
│
└─ Layer 3: ASYNC PERSISTENCE ─────────────────────────┘
   ├─ tribunal_automaton calls: INSERT async (non-blocking)
   ├─ Background contradiction detector (batch hourly)
   └─ Cross-session query API
```

---

## Schema Design

### Table 1: `tribunal_verdicts`

**Purpose:** Store every verdict ever made. Survive session restarts. Track lineage.

```sql
CREATE TABLE tribunal_verdicts (
    verdict_id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    question_embedding vector(256),  -- Model2Vec 256-dim
    verdict_text TEXT NOT NULL,
    verdict_summary TEXT,            -- First 300 chars (for vector embedding)
    verdict_embedding vector(256),   -- Of summary
    confidence FLOAT DEFAULT 0.5,    -- Queen's confidence (0-1, parsed from verdict)
    personas TEXT[] NOT NULL,        -- ["architect-db", "security-reviewer", ...] ARRAY
    persona_models TEXT DEFAULT '',  -- "haiku" or "sonnet" (models used)
    queen_model TEXT DEFAULT 'sonnet',
    phase_number INT,                -- GSD phase number (1=research, 2=planning, 3=execute, ...)
    task_id TEXT,                    -- FK to Ruflo task (if action-driven)
    parent_decision_id BIGINT REFERENCES tribunal_verdicts(verdict_id),  -- What verdict led to this?
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    total_ms INT,                    -- Wall-clock time for tribunal_decide
    response_status VARCHAR(16) DEFAULT 'success',  -- 'success', 'partial', 'failed'
    session_id TEXT,                 -- UUID of Claude session (for cross-session queries)
    INDEX idx_question_embedding ON tribunal_verdicts USING ivfflat (question_embedding vector_cosine_ops) WITH (lists = 100),
    INDEX idx_verdict_embedding ON tribunal_verdicts USING ivfflat (verdict_embedding vector_cosine_ops) WITH (lists = 100),
    INDEX idx_phase ON tribunal_verdicts(phase_number),
    INDEX idx_task_id ON tribunal_verdicts(task_id)
);
```

**Vector Search (< 50ms query):**
```sql
-- Find similar question (verdict reuse candidate)
SELECT verdict_id, question, confidence, personas, created_at
FROM tribunal_verdicts
WHERE question_embedding <-> $1 < 0.15  -- cosine distance, threshold 0.15
ORDER BY question_embedding <-> $1
LIMIT 5;
```

### Table 2: `tribunal_edges`

**Purpose:** Build decision graph. Trace causality, reuse, and conflicts.

```sql
CREATE TABLE tribunal_edges (
    edge_id BIGSERIAL PRIMARY KEY,
    source_verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,
    target_verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,
    edge_type VARCHAR(32) NOT NULL,  -- 'REFINES', 'CONTRADICTS', 'ENABLES', 'BLOCKS', 'REUSES'
    severity VARCHAR(16),             -- For CONTRADICTS: 'warn', 'error', 'critical'
    reason TEXT,                      -- Why are they related? (e.g., "both about module splitting")
    created_at TIMESTAMP DEFAULT now(),
    detected_by VARCHAR(64),          -- Algorithm that detected edge: 'manual', 'contradiction_scanner', 'reuse_detector', 'parent_link'
    confidence FLOAT DEFAULT 0.5,     -- How confident is this edge? (0-1)
    INDEX idx_source ON tribunal_edges(source_verdict_id),
    INDEX idx_target ON tribunal_edges(target_verdict_id),
    INDEX idx_edge_type ON tribunal_edges(edge_type)
);
```

**Graph Traversal Examples:**
```sql
-- Trace ancestry: What decided led to this verdict?
WITH RECURSIVE ancestors AS (
    SELECT verdict_id, question, parent_decision_id, 1 AS depth
    FROM tribunal_verdicts WHERE verdict_id = $1
    UNION ALL
    SELECT v.verdict_id, v.question, v.parent_decision_id, a.depth + 1
    FROM tribunal_verdicts v
    JOIN ancestors a ON v.verdict_id = a.parent_decision_id
    WHERE a.depth < 10  -- Limit recursion
)
SELECT * FROM ancestors ORDER BY depth;

-- What verdicts does this one enable/block/refine?
SELECT t.verdict_id, t.question, e.edge_type, e.reason, t.confidence
FROM tribunal_verdicts t
JOIN tribunal_edges e ON t.verdict_id = e.target_verdict_id
WHERE e.source_verdict_id = $1
ORDER BY e.created_at DESC;
```

### Table 3: `tribunal_contradictions`

**Purpose:** Detect and track conflicts between verdicts.

```sql
CREATE TABLE tribunal_contradictions (
    contradiction_id BIGSERIAL PRIMARY KEY,
    verdict_a_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id),
    verdict_b_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id),
    severity VARCHAR(16) NOT NULL,  -- 'warn' (minor), 'error' (major), 'critical' (blocking)
    conflict_type VARCHAR(64),      -- 'opposite_confidence', 'incompatible_actions', 'conflicting_personas'
    details TEXT,                   -- Human-readable explanation
    detected_at TIMESTAMP DEFAULT now(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,
    INDEX idx_verdict_a ON tribunal_contradictions(verdict_a_id),
    INDEX idx_verdict_b ON tribunal_contradictions(verdict_b_id),
    INDEX idx_severity ON tribunal_contradictions(severity),
    INDEX idx_resolved ON tribunal_contradictions(resolved)
);
```

---

## Storage Strategy

### What to Store (CRITICAL DECISION)

**FULL VERDICT TEXT** — Never summaries.

Why:
1. Post-hoc analysis (audit trail, quality review) needs full context
2. Contradiction detection needs semantic richness (not just summary)
3. Verdict reuse needs complete recommendation for adaptation
4. Expert performance audit needs exact wording (tone, confidence indicators)
5. PostgreSQL storage is cheap (1 verdict ≈ 1KB, 1M verdicts ≈ 1GB)

**Schema includes:**
- Full `verdict_text` (required)
- 300-char `verdict_summary` (for lighter embedding, updates weekly)
- 256-dim embeddings (both full + summary)

### Async Persistence (Non-Blocking)

Tribunal must not slow down. Store async:

```python
async def tribunal_automaton(...):
    # ... decide, parse, create tasks ...

    # Async fire-and-forget: store in PostgreSQL
    asyncio.create_task(_persist_verdict_async(
        question=params.question,
        verdict=verdict,
        personas=names,
        phase_number=phase_num,
        task_id=task_ids[0] if task_ids else None,
        parent_decision_id=context.get('parent_verdict_id'),
        total_ms=tr['total_ms']
    ))

    # Return immediately (don't wait for DB)
    return formatted_output
```

**Database insertion:** PostgreSQL native JSON + JSONB for personas array.

---

## Contradiction Detection Algorithm

**When:** After every verdict (real-time) + batch scanner (hourly).

**Real-time:** Top 5 recent verdicts (fast, < 100ms).
**Batch:** All verdicts in current phase + recent phase (slow, hourly).

### Algorithm: Conflict Scoring

```python
def detect_contradictions(new_verdict: Dict) -> List[Contradiction]:
    """Check new verdict against recent verdicts.

    Scoring:
    1. Question similarity: cosine(new_q, recent_q) > 0.8 (similar topic)
    2. Confidence opposition: |new_conf - recent_conf| > 0.6 AND opposite actions
    3. Persona conflict: shared persona with opposite recommendation
    4. Action incompatibility: new actions BLOCK recent actions

    Return: [Contradiction(...), ...] sorted by severity (CRITICAL first)
    """
    candidates = query_recent_verdicts(limit=5)  # Query within 24h
    conflicts = []

    for recent in candidates:
        # Score: similarity (0-1)
        q_sim = cosine(embed(new_verdict.question), embed(recent.question))
        if q_sim < 0.75:
            continue  # Skip dissimilar questions

        # Score: confidence opposition
        conf_delta = abs(new_verdict.confidence - recent.confidence)

        # Parse actions
        new_actions = parse_actions(new_verdict.verdict_text)
        recent_actions = parse_actions(recent.verdict_text)

        # Check action compatibility
        incompatible_pairs = []
        for na in new_actions:
            for ra in recent_actions:
                if are_incompatible(na, ra):  # "split X" vs "keep X monolithic"
                    incompatible_pairs.append((na, ra))

        # Shared personas?
        shared_personas = set(new_verdict.personas) & set(recent.personas)

        # Severity assignment
        if incompatible_pairs and q_sim > 0.85:
            severity = "CRITICAL" if conf_delta > 0.5 else "ERROR"
        elif shared_personas and conf_delta > 0.6:
            severity = "ERROR"
        elif q_sim > 0.80 and conf_delta > 0.4:
            severity = "WARN"
        else:
            severity = None

        if severity:
            conflicts.append(Contradiction(
                verdict_a_id=recent.id,
                verdict_b_id=new_verdict.id,
                severity=severity,
                conflict_type=classify_conflict(incompatible_pairs, shared_personas, conf_delta),
                details=f"Q-similarity: {q_sim:.2f}, conf-delta: {conf_delta:.2f}, incompatible actions: {len(incompatible_pairs)}"
            ))

    return sorted(conflicts, key=lambda c: {'CRITICAL': 0, 'ERROR': 1, 'WARN': 2}[c.severity])
```

**Performance:** O(5 × 256-dim dot product) = < 1ms per verdict. Real-time is safe.

---

## Verdict Reuse Strategy

### When to Reuse

Query: Find verdicts with **question similarity > 0.85** and **created within last 90 days**.

```sql
SELECT verdict_id, question, verdict_text, confidence, personas, created_at
FROM tribunal_verdicts
WHERE question_embedding <-> $1 < 0.15  -- Very similar question
  AND created_at > now() - interval '90 days'
  AND confidence > 0.7  -- Only confident verdicts
ORDER BY question_embedding <-> $1
LIMIT 3;
```

### Reuse Decision Tree

```
New question arrives
  │
  ├─ Vector search: similarity > 0.85?
  │  └─ NO → Ask tribunal (no cached answer)
  │  └─ YES → Proceed
  │
  ├─ Confidence > 0.7?
  │  └─ NO → Ask tribunal (low confidence verdict)
  │  └─ YES → Proceed
  │
  ├─ Same phase or adjacent?
  │  └─ NO → Ask tribunal (phase context differs)
  │  └─ YES → Proceed
  │
  ├─ Any contradictions with new question?
  │  └─ YES → Ask tribunal (detected conflict)
  │  └─ NO → Reuse
  │
  └─ REUSE VERDICT
     ├─ Response: "Similar question answered {days_ago}. Reusing with confidence penalty (0.7x)."
     ├─ Citation: Link to original verdict + personas
     ├─ Adaptation: "Updated for current context: {minor_tweaks}"
     └─ Create edge: REUSES (source=old, target=new, confidence=0.85)
```

### Confidence Penalty

Reused verdict confidence = `original_confidence × 0.7` (decay by 30%).

Why: Same question != identical context. 7 days old adds uncertainty.

---

## Audit & Quality Tracking

### Table 4: `tribunal_audits` (Extended Schema)

```sql
CREATE TABLE tribunal_audits (
    audit_id BIGSERIAL PRIMARY KEY,
    verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id),

    -- Post-phase assessment (human or automated)
    accuracy FLOAT,                    -- 0-1: "Did this verdict prove correct?"
    was_acted_on BOOLEAN,              -- Did we implement the verdict's actions?
    implementation_result VARCHAR(32), -- 'success', 'partial', 'failed', 'deferred'

    -- Persona performance (per expert)
    persona_name TEXT,
    persona_accuracy FLOAT,            -- Was THIS persona's opinion correct?
    persona_confidence_vs_actual INT,  -- +1: overconfident, 0: calibrated, -1: underconfident

    -- Decision quality
    decision_lifecycle VARCHAR(32),    -- 'created', 'used', 'validated', 'superseded', 'archived'
    notes TEXT,
    assessed_at TIMESTAMP DEFAULT now(),

    INDEX idx_verdict_accuracy ON tribunal_audits(verdict_id, accuracy),
    INDEX idx_persona_performance ON tribunal_audits(persona_name, persona_accuracy)
);
```

### Quality Metrics

**Persona Accuracy Over Time:**
```sql
-- Which personas are most reliable?
SELECT persona_name,
       COUNT(*) as verdicts,
       AVG(persona_accuracy) as avg_accuracy,
       AVG(persona_confidence_vs_actual) as confidence_calibration,
       MAX(assessed_at) as last_audit
FROM tribunal_audits
WHERE persona_name IS NOT NULL AND assessed_at IS NOT NULL
GROUP BY persona_name
ORDER BY avg_accuracy DESC;
```

**Decision Quality Lifecycle:**
```sql
-- Verdict adoption rate: How many verdicts are actually used?
SELECT
    phase_number,
    COUNT(*) as verdicts_created,
    COUNT(CASE WHEN a.verdict_id IS NOT NULL THEN 1 END) as verdicts_acted_on,
    AVG(CASE WHEN a.implementation_result = 'success' THEN 1.0 ELSE 0.0 END) as success_rate
FROM tribunal_verdicts v
LEFT JOIN tribunal_audits a ON v.verdict_id = a.verdict_id
GROUP BY phase_number;
```

---

## Cross-Session Query API

### Use Case 1: Ancestry Trace (Root Cause Analysis)

**Question:** "This bug appeared in Phase 3. What decisions led here?"

```python
def trace_ancestry(verdict_id: int, max_depth: int = 10) -> List[Dict]:
    """Recursively walk backward from verdict to root causes."""
    query = """
    WITH RECURSIVE ancestors AS (
        SELECT verdict_id, question, parent_decision_id, phase_number, created_at, 1 AS depth
        FROM tribunal_verdicts WHERE verdict_id = $1
        UNION ALL
        SELECT v.verdict_id, v.question, v.parent_decision_id, v.phase_number, v.created_at, a.depth + 1
        FROM tribunal_verdicts v
        JOIN ancestors a ON v.verdict_id = a.parent_decision_id
        WHERE a.depth < $2
    )
    SELECT * FROM ancestors ORDER BY depth;
    """
    return db.execute(query, [verdict_id, max_depth])

# Example trace:
# Phase 1, Verdict 42: "Use Ruflo for memory" (parent: None)
#  └─ Phase 2, Verdict 88: "Implement tribunal_automaton" (parent: 42)
#     └─ Phase 3, Verdict 105: "Add PostgreSQL persistence" (parent: 88)
#        └─ Bug discovered: "Verdicts lost on session restart"
```

### Use Case 2: Contradiction Detection (Decision Validation)

**Question:** "Are there unresolved conflicts in Phase 3 planning?"

```python
def find_active_contradictions(phase_number: int) -> List[Dict]:
    """Find unresolved contradictions in a phase."""
    query = """
    SELECT c.contradiction_id, c.severity, c.conflict_type,
           v_a.question as verdict_a_question, v_b.question as verdict_b_question,
           c.details, c.detected_at
    FROM tribunal_contradictions c
    JOIN tribunal_verdicts v_a ON c.verdict_a_id = v_a.verdict_id
    JOIN tribunal_verdicts v_b ON c.verdict_b_id = v_b.verdict_id
    WHERE v_a.phase_number = $1 AND v_b.phase_number = $1
      AND c.resolved = FALSE
    ORDER BY c.severity DESC, c.detected_at DESC;
    """
    return db.execute(query, [phase_number])

# Example output:
# [
#   {severity: 'CRITICAL', conflict_type: 'incompatible_actions',
#    verdict_a: 'Split mega_index.py',
#    verdict_b: 'Keep mega_index monolithic for performance',
#    details: 'Phase 2 split decision contradicts Phase 2 perf optimization'
#   }
# ]
```

### Use Case 3: Verdict Reuse (Avoid Redundant Decisions)

**Question:** "We're asked about module splitting. Has this been answered?"

```python
def find_reusable_verdicts(new_question: str, similarity_threshold: float = 0.85) -> List[Dict]:
    """Find previously answered similar questions."""
    new_embedding = embed(new_question)  # Model2Vec
    query = """
    SELECT verdict_id, question, verdict_text, confidence, personas, created_at,
           (1 - (question_embedding <-> $1)) as similarity
    FROM tribunal_verdicts
    WHERE question_embedding <-> $1 < (1 - $2)  -- Convert similarity to distance
      AND created_at > now() - interval '90 days'
      AND confidence > 0.7
    ORDER BY similarity DESC
    LIMIT 3;
    """
    return db.execute(query, [new_embedding, similarity_threshold])

# Example output:
# [{
#   verdict_id: 42,
#   question: "How should we split mega_index.py?",
#   verdict_text: "Split into 4 modules: builder, lookup, cache, export",
#   confidence: 0.9,
#   personas: ['architecture-designer', 'python-pro'],
#   created_at: '2026-03-15T10:30:00Z',
#   similarity: 0.92
# }]
```

---

## Implementation Roadmap

### Phase 1: Core Schema (1 hour)
1. Create PostgreSQL database: `tribunal_reasoning`
2. Create 4 tables + IVFFLAT indexes
3. Test CRUD + vector search (< 50ms)

### Phase 2: Async Persistence (1 hour)
1. Add `_persist_verdict_async()` to `tribunal/server.py`
2. Integrate into `tribunal_automaton` (non-blocking)
3. Test: INSERT doesn't block responses

### Phase 3: Contradiction Detection (1 hour)
1. Implement `detect_contradictions()` (real-time + batch)
2. Add to `tribunal_automaton` post-verdict
3. Alert on severity (log, return in response)

### Phase 4: Query API (30 min)
1. Create `/api/verdicts/ancestry`, `/api/verdicts/contradictions`, `/api/verdicts/reuse`
2. Wire into tribunal skill (citation + reuse suggestions)
3. Test cross-session persistence

### Phase 5: Audit Integration (30 min)
1. Add `tribunal_audits` table
2. Create post-phase assessment workflow
3. Build quality dashboards

**Total: 4 hours. Can be done in parallel phases if teammates available.**

---

## Performance Guarantees

| Operation | Target | Method | Notes |
|-----------|--------|--------|-------|
| Verdict INSERT | < 10ms | PostgreSQL native + JSONB | Async, non-blocking |
| Vector search (similarity) | < 50ms | IVFFLAT HNSW | 256-dim, 100K verdicts |
| Contradiction detection | < 100ms | In-memory scoring (no DB calls) | Real-time, top 5 recent |
| Ancestry trace | < 500ms | Recursive CTE | Max 10 levels |
| Audit queries | < 200ms | Indexed (verdict_id, phase_number) | Standard SQL |

---

## Example: Full Flow (New Session)

```python
# User asks a question
user_question = "Should we split mega_index.py or use dependency injection?"

# 1. Tribunal checks for reusable verdict
reusable = find_reusable_verdicts(user_question, similarity=0.85)
if reusable:
    return f"✓ Similar question answered {reusable[0]['created_at']}:\n{reusable[0]['verdict_text']}"

# 2. No reuse found, run tribunal
verdict_id = await tribunal_automaton(
    question=user_question,
    parent_decision_id=context.get('last_verdict_id')  # Link to previous decision
)

# 3. Async persistence (non-blocking)
asyncio.create_task(_persist_verdict_async(
    question=user_question,
    verdict=verdict_text,
    personas=names,
    parent_decision_id=context.get('last_verdict_id'),
    task_id=task_ids[0] if task_ids else None
))

# 4. Contradiction detector runs in background
contradictions = detect_contradictions(new_verdict_dict)
if contradictions:
    for c in contradictions:
        if c.severity == 'CRITICAL':
            logger.error(f"CRITICAL CONFLICT: {c.conflict_type} — {c.details}")

# 5. Return verdict + context
return f"{verdict_output}\n\nRelated: {contradictions or 'none'}"

# 6. End-of-phase: Run audit assessment (human + automated)
# Mark verdicts as success/partial/failed
# Assess persona accuracy
# Archive superseded verdicts
```

---

## Storage Footprint Estimate

Assuming 1000 verdicts over 6 months:

- **tribunal_verdicts:** 1000 × 2KB (text) + 256 vectors = ~2.5MB
- **tribunal_edges:** 500 edges × 200B = ~100KB
- **tribunal_contradictions:** 50 contradictions × 500B = ~25KB
- **tribunal_audits:** 1000 assessments × 300B = ~300KB

**Total: ~3MB for 6 months of heavy tribunal usage.**

PostgreSQL comfortable at millions of rows. No storage concerns.

---

## Open Questions (Answered Below)

### Q: Store full verdict or summary?
**A:** Full verdict text. Summaries lose context needed for audit, contradiction detection, and expert performance evaluation.

### Q: Can contradiction detection run at < 100ms?
**A:** Yes. Limit to top 5 recent verdicts, use in-memory cosine scoring (no DB calls during real-time). Batch detector runs hourly for deep analysis.

### Q: When to reuse vs re-ask?
**A:** Reuse when: question_similarity > 0.85 + confidence > 0.7 + no contradictions detected + same/adjacent phase.

### Q: How to handle session restarts?
**A:** All verdicts live in PostgreSQL. On session start, `session_id` UUID set. Verdicts survive restarts. Queries can filter by session or aggregate across all sessions.

### Q: False positives in contradiction detection?
**A:** Possible. Use multi-level filtering: question_similarity (75%) → confidence opposition (0.6) → action incompatibility check. High precision, low recall. Manual review for CRITICAL/ERROR.

---

## Files to Create

1. **`docs/reference/TRIBUNAL_REASONING_GRAPH.md`** — This doc (reference)
2. **`docs/superpowers/specs/2026-03-22-tribunal-reasoning-graph-schema.sql`** — SQL DDL
3. **`.claude/mcp-servers/tribunal/reasoning_graph.py`** — Graph persistence + query API
4. **`.claude/skills/tribunal-graph-explorer/SKILL.md`** — UI skill for querying graph

---

## Conclusion

This reasoning graph transforms tribunal from a **stateless decision factory** into a **persistent knowledge base** that:

1. ✓ Traces decisions backward ("what led to this bug?")
2. ✓ Detects contradictions real-time (< 100ms)
3. ✓ Reuses verdicts intelligently (avoid redundant decisions)
4. ✓ Audits expert quality (who's overconfident?)
5. ✓ Survives session restarts (PostgreSQL persistence)

Next: Implement Phase 1 (schema) + Phase 2 (async persistence).
