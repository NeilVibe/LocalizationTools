# Tribunal MCP — Universal Decision Engine Design

**Status:** Design Phase | **Date:** 2026-03-22 | **Audience:** Architecture + GSD integration

---

## Executive Summary

Evolve Tribunal from a **decision tool** into the **cognitive backbone** for all GSD phases, planning sessions, and architecture decisions. The key innovation: standardized API contract + persistent reasoning graph + auto-triggered GSD integration.

**Current State:** 4 tools, 111 skill personas, Ruflo memory (opaque string storage), Viking semantic search.
**Target State:** Universal decision engine with:
- Unified API contract across all calls
- Persistent reasoning graph (verdicts → causal edges → confidence decay)
- Auto-triggered GSD integration (phase events as calls)
- Dynamic persona selection (auto + manual + hybrid)
- Composition system (2 skills = 1 composite expert)
- Tiered registry (generalist/domain/project-specific)

---

## 5-Dimensional Design

### 1. API Contract — Unified Input/Output Schema

**PROBLEM:** Current tools have different input shapes (DecideInput vs AutomatonInput). No consistency.

**SOLUTION:** Single standardized contract. Every tribunal call has these fields:

#### Request Contract (TribunalRequest)
```python
class TribunalRequest(BaseModel):
    # ─── Core Question ───
    question: str  # The decision to make
    context: Optional[Dict[str, str]]  # Metadata: phase, task_id, project, user_role

    # ─── Persona Control ───
    personas: Optional[List[str]]  # Manual override: ["skill-a", "skill-b"]
    persona_hints: Optional[Dict[str, float]]  # Soft guidance: {"python-pro": 1.5, "security-reviewer": 0.5}
    persona_mode: Literal["auto", "manual", "hybrid"]  # auto=keyword+viking, manual=personas only, hybrid=hints+auto
    max_personas: int  # 2-10, default 5

    # ─── Routing Control ───
    verdict_id: Optional[str]  # Track lineage: "verdict-abc-123" (contradictions, refinements)
    confidence_threshold: float  # Min 0.0-1.0 to include persona response
    reasoning_depth: Literal["fast", "standard", "deep"]  # fast=haiku, standard=sonnet, deep=opus

    # ─── Execution ───
    auto_tasks: bool  # Create Ruflo tasks from actions (default: true)
    auto_consensus: bool  # Propose hive-mind consensus (default: true)

    # ─── Metadata ───
    gsd_event: Optional[Literal["phase_start", "plan_conflict", "assumption_challenge", "milestone_gate"]]
    tags: Optional[List[str]]  # "critical", "research", "refactor", "security"
    ttl: Optional[int]  # Time-to-live in seconds (for cache/expiry)

class Context(BaseModel):
    phase: Optional[str]  # e.g., "research", "planning", "execution"
    phase_number: Optional[int]  # GSD phase number
    task_id: Optional[str]  # Parent task/epic
    project: Optional[str]  # LocaNext, NewScripts, etc.
    user_role: Optional[str]  # "architect", "developer", "tester"
    prior_verdict_id: Optional[str]  # Previous verdict this decision refines/contradicts
```

#### Response Contract (TribunalResponse)
```python
class TribunalResponse(BaseModel):
    # ─── Verdict Identity ───
    verdict_id: str  # UUID-based, globally unique
    timestamp: str  # ISO-8601
    question: str  # Echo back
    context: Context  # Echo back

    # ─── Expert Opinions ───
    personas: List[str]  # ["python-pro", "architecture-designer", "security-reviewer"]
    opinions: List[PersonaOpinion]  # Full response + confidence + model used + latency

    # ─── Queen Synthesis ───
    verdict: str  # Final recommendation
    confidence: float  # 0.0-1.0 (based on persona agreement, response quality)
    reasoning_chain: List[str]  # ["opinion-A supports", "opinion-B contradicts", "queen resolves via pattern XYZ"]

    # ─── Actions ───
    actions: List[Action]  # Parsed from verdict with confidence scores

    # ─── Persistence ───
    ruflo_key: Optional[str]  # "tribunal-20260322-143522"
    task_ids: List[str]  # Ruflo task IDs if auto_tasks=true
    consensus_id: Optional[str]  # Hive-mind consensus ID if proposed

    # ─── Reasoning Graph ───
    graph_node_id: str  # Node ID in persistent reasoning graph
    causal_edges: List[CausalEdge]  # Links to prior verdicts
    contradictions: List[Contradiction]  # Detected contradictions with prior verdicts

class PersonaOpinion(BaseModel):
    name: str
    response: str
    confidence: float  # Based on response clarity, decisiveness, alignment with other experts
    model: str  # haiku, sonnet, opus
    latency_ms: int
    ok: bool

class Action(BaseModel):
    text: str
    confidence: float  # High if 2+ personas mentioned it, or queen emphasized it
    verb: str  # create, fix, implement, refactor, etc.

class CausalEdge(BaseModel):
    source_verdict_id: str  # Prior verdict this depends on
    relationship: Literal["refines", "contradicts", "extends", "validates", "invalidates"]
    strength: float  # 0.0-1.0 confidence in the link

class Contradiction(BaseModel):
    prior_verdict_id: str
    prior_recommendation: str
    current_recommendation: str
    severity: Literal["low", "medium", "high", "critical"]
    explanation: str
```

#### Key Design Points:
- **persona_mode: hybrid** = let Viking + keyword guide selection, but allow persona_hints to boost/suppress
- **confidence** = computed from persona alignment + response quality (not user-provided)
- **reasoning_chain** = traceable path from question → persona opinions → queen logic → verdict
- **causal_edges** = link verdicts into a DAG (directed acyclic graph)
- **contradiction detection** = automatic during queen synthesis (queens checks prior graph)

---

### 2. Persona Selection — Viking + Keyword + Hints + Manual

**PROBLEM:** Current system only supports auto-select or manual names. No gradient.

**SOLUTION:** Layered persona selection with optional overrides.

#### Algorithm: Hybrid Mode (persona_mode="hybrid")

```python
async def _select_personas_hybrid(
    question: str,
    persona_hints: Optional[Dict[str, float]],  # {"skill-a": 1.5, "skill-b": 0.5}
    max_personas: int = 5,
) -> Tuple[List[str], Dict[str, float]]:
    """
    Step 1: Compute auto scores (Viking + keyword)
    Step 2: Apply persona_hints boost/suppress
    Step 3: Rank and select top N
    """
    # Step 1: Auto-select (current logic)
    viking_scores = await _viking_search_skills(question)
    keyword_scores = _keyword_select(question)
    auto_scores = _merge_scores(viking_scores, keyword_scores)

    # Step 2: Apply hints (multiplicative boost/suppress)
    if persona_hints:
        for name, hint_weight in persona_hints.items():
            if name in auto_scores:
                auto_scores[name] *= hint_weight  # boost/suppress
            elif hint_weight > 1.0:
                # Manual add if hint says "boost this"
                auto_scores[name] = hint_weight

    # Step 3: Rank, dedupe, select
    ranked = sorted(auto_scores.items(), key=lambda x: -x[1])
    selected = [name for name, _ in ranked[:max_personas] if name not in EXCLUDED_PERSONAS]

    return selected, {n: auto_scores[n] for n in selected}
```

#### persona_mode Options:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **auto** | Viking + keyword only. Ignore hints. | Unbiased expert selection |
| **manual** | Use personas list only. Ignore Viking/keyword. | Fixed expert panel |
| **hybrid** | Viking + keyword, boosted/suppressed by persona_hints | Default: guided search |

#### Example: GSD Phase Conflict
```python
# Q: Should we split this feature into 2 phases?
request = TribunalRequest(
    question="Should we split feature X into 2 phases?",
    context=Context(phase="planning", gsd_event="plan_conflict"),
    persona_mode="hybrid",
    persona_hints={
        "architecture-designer": 1.5,  # Boost architecture expert
        "tdd": 0.8,  # Suppress test focus (not relevant here)
    }
)
# Result: auto-select finds [code-reviewer, improve-codebase-architecture, ...]
# then boosts architecture-designer to top 1, suppresses tdd below cutoff
```

---

### 3. GSD Integration — Phase Events as Triggers

**PROBLEM:** Tribunal is manual. GSD phases don't auto-consult tribunal.

**SOLUTION:** Define trigger points in GSD where tribunal auto-fires.

#### Trigger Events (gsd_event field)

| Event | When | Auto-Personas | Typical Q | Response Use |
|-------|------|---------------|-----------|--------------|
| **phase_start** | GSD begins a new phase | architecture-designer, planning specialist | "Is this phase scope clear? Any hidden assumptions?" | Validate phase goal before proceeding |
| **plan_conflict** | Two plans conflict in same phase | code-reviewer, improve-codebase-architecture | "Plan A vs Plan B: which is better? Can they coexist?" | Merge/choose winner |
| **assumption_challenge** | Phase assumption flagged as risky | security-reviewer, tdd | "What's the risk if assumption X is wrong? Mitigations?" | Risk matrix update |
| **milestone_gate** | Before shipping a milestone | code-reviewer, security-reviewer, testing-specialist | "Are we ready to ship? What's the smallest missing piece?" | Go/no-go decision |

#### GSD Trigger Contract

```python
class GSDTrigger(BaseModel):
    gsd_event: Literal["phase_start", "plan_conflict", "assumption_challenge", "milestone_gate"]
    phase_number: int
    phase_goal: str  # What the phase must achieve

    # Event-specific data
    plan_a: Optional[str]  # For plan_conflict
    plan_b: Optional[str]
    assumption: Optional[str]  # For assumption_challenge
    risk_level: Optional[Literal["low", "medium", "high"]]

    # Auto-select personas based on event type
    @property
    def auto_personas(self) -> Dict[str, float]:
        if self.gsd_event == "phase_start":
            return {"architecture-designer": 1.0, "tdd": 0.9}
        elif self.gsd_event == "plan_conflict":
            return {"code-reviewer": 1.0, "improve-codebase-architecture": 1.2}
        # ... etc
```

#### Integration Point: GSD Executor

```python
# In gsd-executor before executing a phase:
await tribunal.call(TribunalRequest(
    question=f"Phase {phase_num}: {phase_goal} — Validate scope & assumptions",
    context=Context(phase=phase_name, phase_number=phase_num),
    gsd_event="phase_start",
    reasoning_depth="standard",
    auto_tasks=False,  # Just advisory
))

# Store verdict in phase STATE.md
# If confidence < 0.7, flag for user review
```

---

### 4. Reasoning Graph — Persistent Causal History

**PROBLEM:** Verdicts are stored as opaque strings. No way to trace decisions or detect contradictions.

**SOLUTION:** Persistent directed graph in Ruflo: nodes=verdicts, edges=causal links, metadata=confidence+decay.

#### Schema (PostgreSQL / Ruflo)

```sql
-- Tribunal verdicts as nodes
CREATE TABLE tribunal_verdicts (
    verdict_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence FLOAT,  -- 0.0-1.0
    personas TEXT[],  -- Array of skill names
    timestamp TIMESTAMPTZ,
    context JSONB,  -- phase, task_id, user_role, etc.
    reasoning_chain TEXT[],
    actions JSONB[],
    model_queen TEXT,
    latency_ms INT,

    -- Decay metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    confidence_decay FLOAT DEFAULT 1.0,  -- Multiplier for age

    -- Indexing
    gsd_event TEXT,  -- phase_start, plan_conflict, etc.
    tags TEXT[],  -- critical, research, security, etc.
);

-- Causal edges between verdicts
CREATE TABLE tribunal_edges (
    edge_id TEXT PRIMARY KEY,
    source_verdict_id TEXT REFERENCES tribunal_verdicts(verdict_id),
    target_verdict_id TEXT REFERENCES tribunal_verdicts(verdict_id),
    relationship TEXT,  -- refines, contradicts, extends, validates, invalidates
    strength FLOAT,  -- 0.0-1.0
    created_at TIMESTAMPTZ DEFAULT NOW(),
);

-- Detected contradictions
CREATE TABLE tribunal_contradictions (
    contradiction_id TEXT PRIMARY KEY,
    verdict_id_1 TEXT REFERENCES tribunal_verdicts(verdict_id),
    verdict_id_2 TEXT REFERENCES tribunal_verdicts(verdict_id),
    severity TEXT,  -- low, medium, high, critical
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_verdict_id TEXT,  -- Points to final verdict that resolved it
);
```

#### Confidence Decay Formula

```python
def compute_verdict_confidence(verdict: TribunalVerdictRow) -> float:
    """
    Confidence = original_confidence * decay_factor

    Decay = 1.0 initially, decreases over time.
    Half-life = 30 days. After 30 days, confidence = 0.5x original.
    After 60 days, confidence = 0.25x original.
    Capped at 0.1 (minimum).
    """
    import math
    from datetime import datetime, timedelta

    age_days = (datetime.utcnow() - verdict.created_at).days
    half_life = 30
    decay = 0.5 ** (age_days / half_life)
    decay = max(decay, 0.1)  # Min 0.1

    return verdict.confidence * decay
```

#### Contradiction Detection (in queen synthesis)

```python
async def _detect_contradictions(
    question: str,
    new_verdict: str,
    personas: List[str],
) -> List[Contradiction]:
    """
    Query reasoning graph for prior verdicts on SIMILAR questions.
    Use Viking semantic search to find related past decisions.
    Compare recommendations; if opposite or incompatible, flag contradiction.
    """
    # Step 1: Semantic search for related verdicts
    related = await _query_reasoning_graph(
        semantic_query=question,
        limit=5,
    )

    # Step 2: Compare each related verdict
    contradictions = []
    for prior in related:
        if _are_contradictory(prior.verdict, new_verdict):
            contradictions.append(Contradiction(
                prior_verdict_id=prior.verdict_id,
                prior_recommendation=prior.verdict,
                current_recommendation=new_verdict,
                severity=_assess_severity(prior, new_verdict),
                explanation=f"Recommends opposite action vs {prior.verdict_id}",
            ))

    return contradictions

def _are_contradictory(verdict_a: str, verdict_b: str) -> bool:
    """Heuristic: check for opposite action verbs or explicit disagreement."""
    verbs_a = extract_action_verbs(verdict_a)
    verbs_b = extract_action_verbs(verdict_b)

    # Extract main recommendation (what should we DO?)
    rec_a = _semantic_recommendation(verdict_a)
    rec_b = _semantic_recommendation(verdict_b)

    # Simple heuristic: semantic similarity < 0.3 = contradiction
    similarity = _cosine_similarity(rec_a, rec_b)
    return similarity < 0.3
```

#### Query Patterns

```python
# Q1: Get all verdicts on "should we split this feature?"
async def query_verdicts_by_question_semantic(question: str) -> List[TribunalVerdictRow]:
    """Use Viking to find semantically similar past questions."""
    return await _query_reasoning_graph(semantic_query=question)

# Q2: Trace decision lineage for feature X
async def query_verdict_lineage(verdict_id: str) -> List[TribunalVerdictRow]:
    """Follow causal edges backwards to source decisions."""
    current = verdict_id
    chain = []
    visited = set()
    while current and current not in visited:
        visited.add(current)
        verdict = get_verdict(current)
        chain.append(verdict)
        # Find what caused this verdict
        incoming = query_edges(target=current, direction="incoming")
        current = incoming[0].source_verdict_id if incoming else None
    return chain

# Q3: Check if verdict X contradicts any prior verdict
async def query_contradictions_for_verdict(verdict_id: str) -> List[Contradiction]:
    """Return all detected contradictions involving this verdict."""
    return query_table(
        "tribunal_contradictions",
        where="verdict_id_1 = ? OR verdict_id_2 = ?",
        params=[verdict_id, verdict_id],
    )

# Q4: Get all verdicts tagged "critical" from last 30 days
async def query_critical_verdicts_recent() -> List[TribunalVerdictRow]:
    """Find recent critical decisions."""
    return query_table(
        "tribunal_verdicts",
        where="'critical' = ANY(tags) AND created_at > NOW() - INTERVAL '30 days'",
    )
```

---

### 5. Scaling to 111+ Personas — Registry, Composition, Tiers

**PROBLEM:** All 111 skills loaded at startup. No composition. No tiering.

**SOLUTION:** Dynamic registry with lazy loading, composition system, and tier classification.

#### Registry Design

```python
class PersonaRegistry(BaseModel):
    """Central registry for all 111 personas + compositions + tiers."""

    # ─── Persisted in ~/.tribunal/registry.json ───
    personas: Dict[str, PersonaEntry]  # name → PersonaEntry
    compositions: Dict[str, CompositionEntry]  # "expert-pair-123" → CompositionEntry
    tiers: Dict[str, List[str]]  # "generalist", "domain", "project" → list of persona names

class PersonaEntry(BaseModel):
    name: str  # "python-pro"
    description: str
    skill_path: str  # ~/.claude/skills/python-pro/SKILL.md
    tier: Literal["generalist", "domain", "project-specific"]
    keywords: Set[str]  # [python, async, testing, ...]

    # Lazy loading
    content: Optional[str] = None  # Loaded on-demand
    last_loaded: Optional[datetime] = None

    # Metadata
    approval_confidence: float  # How much queen trusts this persona (0.0-1.0)
    usage_count: int  # Tracks popularity
    avg_response_time_ms: int

class CompositionEntry(BaseModel):
    """Meta-persona: combine 2 personas into 1 expert."""
    composition_id: str  # "expert-security-arch-v1"
    personas: List[str]  # ["secure-code-guardian", "architecture-designer"]
    combined_description: str  # "Security architect"
    tier: Literal["generalist", "domain", "project-specific"]

    # How to invoke: in parallel or sequential?
    invocation_strategy: Literal["parallel", "sequential"]

    # Post-process: how to combine their responses?
    synthesis_template: str  # Custom prompt for queen

class RegistryTiers(BaseModel):
    """Tier classification for scaling."""
    generalist: List[str]  # Applies broadly: code-reviewer, architecture-designer, tdd
    domain: List[str]  # Domain-specific: python-pro, fastapi-expert, sql-expert
    project_specific: List[str]  # LocaNext-only: debug-locanext, websocket-engineer
```

#### Tier Classification (Manual)

```python
PERSONA_TIERS = {
    "generalist": [
        "architecture-designer",
        "code-reviewer",
        "tdd",
        "deep-research",
        "grill-me",
        "improve-codebase-architecture",
        "test-master",
        "security-reviewer",
    ],
    "domain": [
        "python-pro",
        "fastapi-expert",
        "sql-expert",
        "postgres-pro",
        "typescript-pro",
        "svelte-code-writer",
        "r3f-animation",
        "gsap-master",
        "llm-integration",
        # ... ~50 more
    ],
    "project_specific": [
        "debug-locanext",
        "websocket-engineer",  # Socket.IO used in LocaNext
        "xml-localization",  # Core to all projects
        "xlsx",  # Core to all projects
    ],
}
```

#### Dynamic Loading Strategy

```python
async def load_persona(name: str, prefer_tier: Optional[str] = None) -> PersonaEntry:
    """
    Load persona skill on-demand.
    If prefer_tier, prefer from that tier first.
    """
    entry = REGISTRY.personas[name]

    # Already loaded?
    if entry.content and (datetime.now() - entry.last_loaded).seconds < 3600:
        return entry

    # Load from disk
    path = Path(entry.skill_path)
    entry.content = path.read_text()
    entry.last_loaded = datetime.now()
    return entry
```

#### Composition System

```python
# Define a composite expert
REGISTRY.compositions["expert-security-arch-v1"] = CompositionEntry(
    composition_id="expert-security-arch-v1",
    personas=["secure-code-guardian", "architecture-designer"],
    combined_description="Security architect with system design expertise",
    tier="domain",
    invocation_strategy="parallel",  # Call both, then queen merges
    synthesis_template="""
    You're the queen. Two experts: Security and Architecture.
    - Security says: <SECURITY_OPINION>
    - Architecture says: <ARCH_OPINION>

    Synthesize into ONE integrated design that satisfies both security AND scalability.
    Lead with the combined recommendation.
    """,
)

# Use in a request
request = TribunalRequest(
    question="How should we design the auth system for multi-tenant?",
    personas=["expert-security-arch-v1"],  # Composition ID, not skill name
)
```

#### Scaling with Tiers

```python
async def _select_personas_tiered(
    question: str,
    prefer_tier: Optional[str] = None,
    max_personas: int = 5,
) -> List[str]:
    """
    Auto-select, but prefer a tier.

    Prefer tier: "generalist" = broad expertise, fast
    Prefer tier: "domain" = deep expertise, slower
    Prefer tier: "project_specific" = LocaNext knowledge, very deep
    """
    # Step 1: Auto-select from all personas
    candidates = await _select_personas_hybrid(question, max_personas=max_personas*2)

    # Step 2: If prefer_tier, sort by tier membership
    if prefer_tier:
        tier_personas = REGISTRY.tiers.get(prefer_tier, [])
        candidates_tiered = [
            (name, score * 1.5 if name in tier_personas else score)
            for name, score in candidates
        ]
        candidates = sorted(candidates_tiered, key=lambda x: -x[1])

    # Step 3: Select top N, load on-demand
    selected = []
    for name, _ in candidates[:max_personas]:
        await load_persona(name, prefer_tier)
        selected.append(name)

    return selected
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      GSD Phase (e.g., Planning)                 │
│  phase_start event triggers → TribunalRequest                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────┐
        │    Tribunal Request (Unified Contract)   │
        │  - question, context, gsd_event         │
        │  - persona_mode (auto/manual/hybrid)     │
        │  - persona_hints, reasoning_depth        │
        └──────────────────────┬───────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
        ▼                                             ▼
    ┌─────────────────────┐              ┌──────────────────────┐
    │  Persona Selection  │              │  Reasoning Graph     │
    │  (Viking+Keyword)   │              │  Query prior verdicts│
    │  + persona_hints    │              │  + contradiction scan│
    └──────────┬──────────┘              └──────────┬───────────┘
               │                                    │
               ▼                                    ▼
        ┌──────────────────────────────────────────────────────┐
        │         Registry (Tiers + Compositions)              │
        │  Generalist: architecture-designer, code-reviewer    │
        │  Domain: python-pro, fastapi-expert, sql-expert      │
        │  Project: debug-locanext, websocket-engineer         │
        │  Compositions: expert-security-arch-v1               │
        └──────────────────────┬───────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
        ▼                        (Parallel Fan-Out)   ▼
    ┌─────────────────┐                      ┌──────────────┐
    │ Persona 1       │                      │ Persona N    │
    │ (skill.md load) │  ─┐                ┌─│ (skill.md)   │
    │ + opinion       │   │                │  │ + opinion    │
    └─────────────────┘   ├──────────────┬─┘  └──────────────┘
                          │              │
                          ▼              ▼
                     ┌──────────────────────────┐
                     │  Queen Synthesis         │
                     │  - Merge opinions        │
                     │  - Parse actions         │
                     │  - Compute confidence    │
                     │  - Detect contradictions │
                     └────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
    ┌────────────┐        ┌───────────────┐        ┌───────────────┐
    │ TribunalResponse    │ Ruflo Memory  │        │ Reasoning     │
    │ - verdict_id        │ - Store text  │        │ Graph Update  │
    │ - verdict           │ - Store key   │        │ - Insert node │
    │ - confidence        │               │        │ - Add edges   │
    │ - causal_edges      └───────────────┘        │ - Find contra │
    │ - actions           ┌───────────────┐        │   dictions    │
    └────────────┘        │ Ruflo Tasks   │        └───────────────┘
                          │ (if auto)     │
                          └───────────────┘
```

---

## Key Design Decisions (ADRs)

### ADR-001: Unified API Contract
**Status:** Accepted
**Decision:** All tribunal calls use TribunalRequest + TribunalResponse
**Rationale:** Enables consistent logging, composition, reasoning graph integration
**Trade-off:** Slightly more fields per request, but eliminates tool-specific parameter sprawl
**Consequence:** Tools become simple wrappers around _run_tribunal_unified()

### ADR-002: Persistent Reasoning Graph (PostgreSQL / Ruflo)
**Status:** Accepted
**Decision:** Store verdict nodes + causal edges in relational DB (not just Ruflo string keys)
**Rationale:** Enable queries like "contradict previous verdict on X?", trace decision lineage, detect contradictions
**Trade-off:** Requires schema migration, ~500ms query per tribunal call
**Consequence:** Tribunal becomes stateful; must handle graph consistency

### ADR-003: Hybrid Persona Selection (Auto + Hints)
**Status:** Accepted
**Decision:** Default to auto-select (Viking + keyword), but allow persona_hints to boost/suppress
**Rationale:** Unbiased by default, but GSD phases can guide (e.g., "focus on security")
**Trade-off:** More algorithm complexity, but avoids lock-in to fixed expert panels
**Consequence:** Personas can be swapped without changing phase logic

### ADR-004: Composition as First-Class Citizens
**Status:** Accepted
**Decision:** Meta-personas (2 skills = 1 composite) get registry entries, can be invoked directly
**Rationale:** "Security architect" = "secure-code-guardian + architecture-designer" should be one call
**Trade-off:** More registry overhead, but eliminates ad-hoc persona pairing
**Consequence:** Queen gets expert blends, not separate opinions

### ADR-005: Confidence Decay (30-day half-life)
**Status:** Accepted
**Decision:** Verdict confidence = original * 0.5^(age_days/30), min 0.1
**Rationale:** Older decisions less relevant (code changes, requirements shift)
**Trade-off:** Stale verdicts still accessible, but with lower weight
**Consequence:** Long-lived decisions must be re-validated periodically

### ADR-006: Contradiction Detection (Semantic, Not Exact)
**Status:** Accepted
**Decision:** Contradictions flagged if recommendation cosine similarity < 0.3 (not just opposite words)
**Rationale:** Semantic differences matter (e.g., "split into 2 phases" vs "keep as 1 but phased" ≠ contradiction)
**Trade-off:** Heuristic-based (can have false positives/negatives), but avoids brittle exact matching
**Consequence:** Contradiction severity is a spectrum (low, medium, high, critical)

---

## Integration Path: GSD + Tribunal + Ruflo + Viking

**Phase 1: Core API (1-2 days)**
- Implement TribunalRequest/Response contracts
- Unify DecideInput + AutomatonInput into single _run_tribunal_unified()
- Update 4 tools to use new contract

**Phase 2: Reasoning Graph (2-3 days)**
- Create PostgreSQL schema (verdicts, edges, contradictions)
- Implement contradiction detection in queen
- Add graph queries (lineage, semantic search)

**Phase 3: GSD Integration (1-2 days)**
- Define GSDTrigger contract
- Add phase_start, plan_conflict, assumption_challenge, milestone_gate triggers
- Wire tribunal calls into gsd-executor

**Phase 4: Registry + Composition (1 day)**
- Build PersonaRegistry with tiers
- Implement composition system (meta-personas)
- Dynamic loading for lazy persona loading

**Phase 5: Verification (1 day)**
- Test end-to-end: GSD phase → tribunal trigger → verdict → reasoning graph → next phase
- Load test with 111+ personas
- Verify contradiction detection accuracy

---

## Critical Questions Answered

### Q1: "What happens if queen disagrees with all personas?"
**A:** Confidence is low (~0.3). Verdict is still produced, but marked with causal edge to next decision ("needs refinement").

### Q2: "How do we prevent tribunal from becoming a bottleneck?"
**A:** Persona calls are parallel (async fan-out). Queen is sequential, but ~10s total. Caching possible (store verdicts for identical questions for 1 hour).

### Q3: "What if 111+ personas take forever to load?"
**A:** Lazy loading on-demand. Only load personas for selected call. Tier system reduces scope (prefer "generalist" = 8 personas = fast).

### Q4: "How do we handle "I changed my mind" verdicts?"
**A:** Create new verdict. Reason graph tracks it as "refines previous verdict X". Old verdict still queryable with confidence decay.

### Q5: "What's the minimum team to implement this?"
**A:** 1 person, ~7 days (assuming PostgreSQL already set up). 3 phases: core API (phase 1), reasoning graph (phase 2), GSD integration (phase 3).

---

## Next Step: Grill-Me Recommendations

**Should we start with Phase 1 (Core API)?**
YES — It's the foundation. All other phases depend on it. Block size: ~1 day.

**Should we keep the 4 existing tools, or replace them?**
Replace. The new tools are backward-compatible (same inputs map to new contract). Old code auto-upgrades.

**Should Ruflo memory move into the reasoning graph?**
Gradually. New verdicts go into PostgreSQL. Old Ruflo keys stay but marked as "legacy".

**Should tribunal auto-save every verdict, or only "important" ones?**
Auto-save all. Confidence + tags + context let users filter. Filter at query time (e.g., "critical verdicts from last 30 days").

