# Tribunal + GSD Integration Guide

> **Quick start:** Use tribunal at 3 phase gates to auto-resolve architectural decisions. No manual approval needed in FULL AUTO mode.

---

## TL;DR: Three Integration Points

| Phase | When | How | Output |
|-------|------|-----|--------|
| **Plan** | Before `execute-phase` | Scan PLAN.md for ambiguity keywords | Decisions.md + task list |
| **Execute** | When teammate blocked (non-technical) | Call tribunal with parent_decision_id | Verdict + context for teammate |
| **Validate** | When gate fails | Tribunal decides: fix, defer, or accept risk | Go/no-go verdict |

---

## PHASE 2: PLAN

### Step 1: Scan PLAN.md for Ambiguity Keywords

After writing `.planning/phases/2/PLAN.md`, scan for decision keywords:

```bash
# TBD: CLI tool (v2.0 feature)
# For now, manual scan:

grep -iE "(split|refactor|rewrite|endpoint|schema|version|breaking|auth|encrypt|validate|test|strategy|slow|bottleneck|cache|index|mvp|scope|phase|defer)" \
  .planning/phases/2/PLAN.md
```

**Example findings:**
```
Line 42: "Should we split mega_index.py into modules?"  ← architecture
Line 89: "API endpoint design: REST vs GraphQL?"        ← api-design
Line 145: "Validate user input on login?"               ← security
Line 203: "Test strategy: unit vs integration?"         ← testing
Line 267: "Can we defer PDF export to Phase 4?"         ← feature-scope
```

### Step 2: Create Tribunal Requests for Each Ambiguity

**File:** `.planning/phases/2/DECISIONS.md` (create new)

```markdown
# Phase 2 Plan — Tribunal Decisions

## Decision 1: Architecture Split (dec-arch-001)

**Question:** Should we split mega_index.py into separate modules or keep monolithic?

**Submitted to tribunal:**
```json
{
  "decision": {
    "question": "Should we split mega_index.py into separate modules or keep monolithic?",
    "decision_type": "architecture",
    "urgency": "HIGH",
    "context": {
      "phase_name": "Phase 2 Plan",
      "tags": ["refactoring", "performance", "maintenance"]
    },
    "persona_selection": {
      "strategy": "AUTO",
      "max_personas": 5
    },
    "models": {
      "personas": "sonnet",
      "queen": "opus"
    },
    "side_effects": {
      "store_in_memory": true
    }
  }
}
```

**Tribunal Verdict:**
```
DECISION_ID: dec-20260322-143022-abc123

SUMMARY: Split into 3 modules (index-builder, index-cache, index-search) for maintainability.

DETAIL: Current 3000-line file violates SRP. Proposed split:
- index_builder.py: DataLoader, batching, error handling
- index_cache.py: Redis + in-memory cache management
- index_search.py: QueryEngine, result formatting

Benefits: Reduces cognitive load, improves testability, enables parallel work.

ACTIONS:
1. Create index_builder.py with DataLoader class and factory methods (HIGH)
2. Create index_cache.py with RedisCache and MemoryCache context managers (HIGH)
3. Create index_search.py with QueryEngine and result formatting (HIGH)
4. Write tests for module boundaries (NORMAL)

Confidence: 0.91 | Personas: 3/3 responded | Total: 63s
```

**Decision used in:** Execute Phase Task E-1.1

---

## Step 3: Link Decisions in PLAN.md

Update `.planning/phases/2/PLAN.md` sections to reference decisions:

```markdown
# Architecture

Should we split mega_index.py?
<!-- tribunal: dec-20260322-143022-abc123 -->

**Verdict:** Yes, split into 3 modules (index-builder, index-cache, index-search).
See .planning/phases/2/DECISIONS.md for full tribunal reasoning.

**Implementation:** Tasks E-1.1, E-1.2, E-1.3

---

# API Contract

Design endpoint schema: REST vs GraphQL?
<!-- tribunal: dec-20260322-144500-xyz789 -->

**Verdict:** REST with OpenAPI 3.1 contract. 2 resources: /index/{id}, /search.
See .planning/phases/2/DECISIONS.md for expert reasoning.

**Implementation:** Task E-2.1, E-2.2
```

### Step 4: Create Execute Phase Tasks from Tribunal Actions

Tribunal generates actions (HIGH priority) → create Execute phase tasks:

| Tribunal Action | Execute Task | Assigned To | Depends On |
|---|---|---|---|
| Create index_builder.py | E-1.1 | Backend Team | — |
| Create index_cache.py | E-1.2 | Backend Team | E-1.1 |
| Create index_search.py | E-1.3 | Backend Team | E-1.1 |
| Write module boundary tests | E-1.4 | QA Team | E-1.1, E-1.2, E-1.3 |

**Before `/gsd:execute-phase 3`:** All decisions in DECISIONS.md, all tasks created, all references linked.

---

## PHASE 3: EXECUTE (1, 2, 3)

### Step 1: When Teammate Is Blocked

Teammate encounters non-technical blocker:

```
Task E-2.3: Implement async context manager for IndexCache
Status: BLOCKED
Blocker: "Should IndexCache use Redis or in-memory? Depends on deployment target."
Assigned to: Backend Team
```

### Step 2: Teammate Calls Tribunal with Ancestry

Instead of waiting for lead decision, teammate triggers tribunal:

```json
{
  "decision": {
    "question": "IndexCache backend: Redis or in-memory? Consider: latency, dev-vs-prod, cost, persistence needs.",
    "decision_type": "architecture",
    "urgency": "NORMAL",
    "context": {
      "phase_name": "Phase 3 Execute",
      "task_id": "e-2.3",
      "parent_decision_id": "dec-20260322-143022-abc123"
    },
    "persona_selection": {
      "strategy": "AUTO",
      "max_personas": 3
    },
    "constraints": {
      "max_wait_seconds": 60,
      "partial_response_ok": true
    }
  }
}
```

**Key:** `parent_decision_id` tells tribunal: "Load context from Phase 2 planning decision."

Queen will inject parent context:
```
Earlier Decision (dec-20260322-143022-abc123):
  Question: "Split mega_index.py?"
  Verdict: "Yes, 3 modules (builder, cache, search)."

Now, for cache implementation, ensure consistency with this architecture.
```

### Step 3: Tribunal Returns Verdict + Context

**Response:**
```json
{
  "decision_id": "dec-20260322-150000-def456",
  "status": "COMPLETE",
  "verdict": {
    "summary": "Use in-memory with optional Redis fallback.",
    "detail": "For LocaNext: in-memory is fast (dev, single-server). Add env var for Redis (scales to multi-server). Implements both, switches via config.",
    "expert_opinions": {
      "postgres-pro": "Redis adds operational overhead. In-memory simpler for MVP.",
      "architecture-designer": "In-memory + fallback pattern is sound. Clear boundaries."
    },
    "queen_synthesis": {
      "recommendation": "Implement MemoryCache first (fast), add RedisCache as optional fallback."
    }
  },
  "metadata": {
    "parent_decision_id": "dec-20260322-143022-abc123",
    "decision_ancestry_path": ["dec-20260322-143022-abc123", "dec-20260322-150000-def456"]
  }
}
```

### Step 4: Teammate Continues with Verdict

Teammate implements using verdict as rationale:

```python
# index_cache.py
class IndexCache:
    """Cache backend per tribunal verdict (dec-20260322-150000-def456).

    Use in-memory first, add Redis fallback for multi-server deployments.
    """

    def __init__(self, use_redis: bool = False):
        if use_redis:
            self.backend = RedisCache()
        else:
            self.backend = MemoryCache()
```

**No approval needed.** Tribunal verdict = automatic go-ahead (FULL AUTO mode).

### Step 5: Log Verdict in Task Record

Update task status with verdict reference:

```markdown
# Task E-2.3: Implement async context manager for IndexCache

## Status: COMPLETE

## Tribunal Verdict Used:
- **Decision ID:** dec-20260322-150000-def456
- **Question:** Redis or in-memory?
- **Verdict:** In-memory + optional Redis fallback
- **Parent Decision:** dec-20260322-143022-abc123 (Phase 2 architecture split)

## Implementation:
- Created MemoryCache context manager (fast, dev/single-server)
- Created RedisCache context manager (fallback, scales)
- Uses env var CACHE_BACKEND to switch
- Tests added for both (100% coverage)

## PR Link: #45
```

---

## PHASE 4: VALIDATE

### Step 1: Run Verification Gates

```bash
/gsd:verify-work
```

**Output:**
```
Phase 4 Validation Results:
├─ Gate 1: Requirement Coverage
│  Status: FAIL (8/10 features implemented, goal needs 10)
│
├─ Gate 2: Test Coverage
│  Status: PASS (89% coverage, target 85%)
│
├─ Gate 3: Security Audit
│  Status: FAIL (3 findings, all low severity)
│
├─ Gate 4: Performance Baseline
│  Status: WARN (Query latency +15%, target +10%)
│
└─ Gate 5: Code Quality
   Status: PASS (No violations from review)
```

### Step 2: Tribunal for Failed Gates

For EACH failed gate, call tribunal:

```json
{
  "decision": {
    "question": "Gate: Requirement Coverage. 8/10 features implemented. Should we: (A) rework remaining 2 features, (B) defer to Phase 5, or (C) adjust goal to 8/10?",
    "decision_type": "feature-scope",
    "urgency": "NORMAL",
    "context": {
      "phase_name": "Phase 4 Validate",
      "tags": ["verification", "requirement-coverage"]
    },
    "persona_selection": {
      "strategy": "MANUAL",
      "persona_names": ["architecture-designer", "tdd", "code-reviewer"]
    },
    "side_effects": {
      "store_in_memory": true
    }
  }
}
```

**Response:**
```json
{
  "verdict": {
    "summary": "Rework remaining 2 features if timeline allows. Otherwise defer to Phase 5 (hotfix).",
    "detail": "Both missing features are on critical path (user login, data export). Cannot defer. Recommend 3-day sprint to implement (Task V-1.1, V-1.2).",
    "actions": [
      { "action": "Implement OAuth login flow (Feature #7)", "priority": "CRITICAL" },
      { "action": "Implement CSV export (Feature #8)", "priority": "CRITICAL" }
    ]
  }
}
```

**Decision:** REWORK. Create Execute Phase 4 tasks V-1.1, V-1.2.

---

### Step 3: Compile Go/No-Go Decision

**File:** `.planning/phases/4/VALIDATION_DECISIONS.md`

```markdown
# Phase 4 Validation — Gate Verdicts

## Gate 1: Requirement Coverage — FAIL
- **Tribunal Verdict:** Rework 2 missing features (OAuth, CSV export)
- **Decision:** REWORK
- **Tasks Created:** V-1.1 (OAuth), V-1.2 (CSV export)
- **Timeline Impact:** +3 days

## Gate 2: Test Coverage — PASS
- **Status:** 89% (exceeds target)
- **Decision:** ACCEPT
- **No tribunal needed**

## Gate 3: Security Audit — FAIL (Low Severity)
- **Tribunal Verdict:** Acceptable risk. 3 low-severity findings defer to Phase 5.
- **Decision:** DEFER
- **Hotfix Issues:** security-001, security-002, security-003
- **Timeline Impact:** None (post-release)

## Gate 4: Performance Baseline — WARN
- **Tribunal Verdict:** Query latency +15% acceptable for MVP. Optimize in Phase 5 (backlog item).
- **Decision:** ACCEPT
- **Backlog Item:** perf-001 (query latency optimization)

## Final Go/No-Go: CONDITIONAL GO
- **Execute V-1 for 2 missing features (3 days)**
- **Re-run Gate 1 after V-1 complete**
- **All other gates passed (or deferred with tribunal approval)**
```

### Step 4: Proceed or Loop

- **If all gates pass:** Go to Phase 5 (SHIP)
- **If gates have rework:** Return to Execute phase for rework tasks
- **If gates deferred:** Document in VALIDATION_DECISIONS.md, proceed with acceptance

---

## PHASE 5: SHIP

### When: Known Bugs Before Release

If known bugs exist before shipping:

```json
{
  "decision": {
    "question": "Known bugs before release. Prioritize by severity and impact.",
    "decision_type": "priority",
    "urgency": "HIGH",
    "context": {
      "phase_name": "Phase 5 Ship",
      "tags": ["triage", "release-blocking"]
    },
    "persona_selection": {
      "strategy": "MANUAL",
      "persona_names": ["code-reviewer", "secure-code-guardian", "tdd"]
    },
    "side_effects": {
      "create_ruflo_tasks": true,
      "propose_consensus": true
    }
  }
}
```

**Tribunal returns:** Ranked bugs by severity. CRITICAL bugs block release. NORMAL bugs become hotfix queue post-release.

---

## AUTO-TRIGGER: How to Implement in v2.0

### CLI Tool

```bash
# Phase 2 (after writing PLAN.md)
tribunal --phase "Phase 2 Plan" --plan-file ".planning/phases/2/PLAN.md" --auto-trigger

# Output:
# Found 5 ambiguities, submitting tribunal requests...
# dec-arch-001: Architecture split
# dec-api-001: API design
# dec-sec-001: Input validation
# dec-test-001: Testing strategy
# dec-scope-001: Feature scope
# All verdicts written to: .planning/phases/2/DECISIONS.md
# PLAN.md updated with decision IDs
```

### Python Integration

```python
# In GSD execute code:
from tribunal import tribunal_autotrigger

# Phase 2: Auto-trigger on planning
verdicts = tribunal_autotrigger(
    phase="Plan",
    plan_file=".planning/phases/2/PLAN.md",
    output_dir=".planning/phases/2/",
)

# Verdicts dict → integrate into task creation
for verdict in verdicts:
    if verdict["urgency"] == "HIGH":
        create_task(verdict["actions"][0])

# Phase 3: On blocker, load parent context
parent_verdict = tribunal.get_decision(task.parent_decision_id)
response = tribunal.decide(
    question=blocker_reason,
    decision_type="architecture",
    parent_decision_id=task.parent_decision_id,
)
```

---

## FULL AUTO MODE: No Lead Approval

**Default:** Tribunal verdict = automatic decision (no lead approval).

**When to override:** Complex trade-offs, high-stakes decisions.

```json
{
  "decision": {
    "urgency": "CRITICAL",
    "context": {
      "require_lead_approval": true  ← NEW (v2.1)
    }
  }
}
```

**Verdict status:** `PENDING_APPROVAL` (lead must call `/approve-verdict`)

---

## MEMORY & REASONING GRAPH: Across Sessions

All tribunal decisions auto-persist to SQLite (`.claude/mcp-servers/tribunal/decisions.db`).

**Query decisions from prior sessions:**

```bash
# Get all decisions for Phase 2
tribunal --list --phase "Phase 2 Plan"

# Get ancestry tree
tribunal --tree --decision-id "dec-arch-001"
# Output:
# dec-arch-001 (Phase 2 Plan)
# ├─ dec-cache-001 (Phase 3 Execute, task E-2.3)
# ├─ dec-search-001 (Phase 3 Execute, task E-2.5)
# └─ dec-perf-001 (Phase 4 Validate, performance gate)

# Get similar decisions (decision reuse)
tribunal --similar --decision-type "architecture" --tags "caching"
# Output:
# Found 2 similar decisions from prior phases
# Use as context? (y/n)
```

---

## CHECKLIST: Phase-by-Phase

### Phase 2 (Plan)

- [ ] Write PLAN.md with architecture decisions
- [ ] Scan for ambiguity keywords
- [ ] Submit tribunal requests for each ambiguity
- [ ] Write `.planning/phases/2/DECISIONS.md` with verdicts
- [ ] Link tribunal IDs in PLAN.md comments
- [ ] Create Execute tasks from tribunal actions
- [ ] Approve plan (tribunal decisions + user approval)

### Phase 3 (Execute 1, 2, 3)

- [ ] When teammate blocked (non-technical), call tribunal
- [ ] Include `parent_decision_id` for context
- [ ] Teammate implements using verdict (FULL AUTO, no approval needed)
- [ ] Log tribunal verdict in task record
- [ ] Continue to next task

### Phase 4 (Validate)

- [ ] Run `/gsd:verify-work` to check gates
- [ ] For each failed gate, call tribunal
- [ ] Write `.planning/phases/4/VALIDATION_DECISIONS.md`
- [ ] Decide: ACCEPT, REWORK, DEFER
- [ ] Go/no-go decision (tribunal + user)

### Phase 5 (Ship)

- [ ] Triage known bugs using tribunal
- [ ] Create hotfix queue
- [ ] Ship or hold (user decision)

---

## EXAMPLES

### Example 1: Simple GO/NO-GO

```
Phase 4 Validate: Test Coverage FAIL (72%, target 85%)

→ tribunal_decide(
    question="Test coverage at 72%. Implement missing tests or accept gap?",
    decision_type="testing"
)

← Tribunal: "Test 3 critical modules (index_builder, index_search, index_cache).
              Skip coverage for deprecated LegacyAPI. New target: 82% (achievable)."

Decision: REWORK. Create task V-1.1 (cover index_builder), V-1.2 (cover index_search),
          V-1.3 (cover index_cache). Timeline: +2 days.
```

### Example 2: Ancestry Chaining

```
Phase 2 Plan: "Split mega_index.py?"
→ Verdict: "Yes, 3 modules"
→ Decision ID: dec-arch-001

Phase 3 Execute (Task E-2.3, blocked): "Redis or in-memory for cache?"
→ tribunal_decide(parent_decision_id="dec-arch-001")
→ Queen injects Phase 2 context: "You decided to split into 3 modules. Cache should fit this pattern."
→ Verdict: "In-memory + optional Redis (consistent with split architecture)"
→ Ancestry path: [dec-arch-001 → current-decision]
```

### Example 3: Multi-Decision Gate

```
Phase 4 Validate: 5 gates, 3 fail

→ For each failed gate:
  tribunal_decide(gate_name, decision_type)

→ Verdicts:
  - Gate 1 (coverage): REWORK (3 days)
  - Gate 2 (security): DEFER (hotfix queue)
  - Gate 3 (perf): ACCEPT (backlog item)

→ Compilation:
  Go/no-go = CONDITIONAL GO
  Rework: 3 days
  Ship: 1 day
  Timeline impact: +3 days
```

---

## FAQ

**Q: What if tribunal returns multiple options?**
A: Queen returns SINGLE recommendation (not a list). If truly ambiguous, queen notes disagreement + rationale.

**Q: What if all personas timeout?**
A: Falls back to `DEFAULT_PERSONAS` (architecture-designer, code-reviewer, tdd). Might be slower/less accurate.

**Q: What if question is out-of-scope for all personas?**
A: Tribunal will return lowest-scoring match or DEFAULT_PERSONAS. Always returns SOMETHING.

**Q: Can tribunal decisions be overridden?**
A: Yes. Verdict is a recommendation, not a law. Lead/team can override with justification.

**Q: How long does a tribunal call take?**
A: 60-120s (3-5 personas in parallel + queen synthesis). Faster for LOW urgency (haiku models).

**Q: What if teammate doesn't wait for tribunal?**
A: Document the decision they made. Next time, encourage tribunal use via feedback/retraining.

---

## NEXT STEPS

1. **v2.0 roadmap:** Implement unified API contract (OpenAPI 3.1)
2. **v2.0 CLI:** `tribunal --auto-trigger` for Phase 2 scanning
3. **v2.0 GSD:** Integrate tribunal into `/gsd:execute-phase` blocker handling
4. **v2.0 Memory:** SQLite persistence + ancestry querying
5. **v2.1:** Lead approval gates (optional) + consistency checking

---

**Questions?** See `docs/reference/TRIBUNAL_UNIVERSAL_ARCHITECTURE.md` for full technical details.
