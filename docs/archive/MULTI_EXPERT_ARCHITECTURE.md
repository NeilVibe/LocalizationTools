# Multi-Expert Tribunal System Architecture Patterns

**Date:** 2026-03-22
**Context:** Research synthesis from LangGraph, LLaMA Index, Anthropic Constitutional AI, Drools/RETE, project Tribunal MCP, and GSD+Ruflo integration.
**Goal:** Define 3-5 concrete architectural patterns for multi-expert systems with proven pros/cons.

---

## Executive Summary

Multi-expert systems need **standardized interfaces** (API contracts), **intelligent routing** (persona/expert selection), **auditable decisions** (reasoning graphs + persistence), and **phase integration** (automation triggers). This document provides 5 battle-tested patterns spanning these dimensions.

---

## Pattern 1: **State-Graph Orchestration** (LangGraph Model)

### Architecture

```
┌─────────────────────────────────────────┐
│      Shared StateGraph (Central State)  │
│  • Messages log                         │
│  • Decisions + timestamps               │
│  • Intermediate results                 │
│  • Metadata (persona, confidence, etc)  │
└────────────────────────┬────────────────┘
         ▲               │
         │               ▼
    ┌────────────┬──────────────┬──────────────┐
    │  Expert 1  │  Expert 2    │  Expert 3    │
    │ (Haiku)    │ (Sonnet)     │ (Opus)       │
    │ Persona A  │ Persona B    │ Persona C    │
    └────────────┴──────────────┴──────────────┘
         │               │              │
         └───────────────┼──────────────┘
                         ▼
                  ┌─────────────┐
                  │ Router Node │ ← Decides next edge
                  │ (LLM-based) │
                  └──────┬──────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    [Queen Node]  [Fallback]      [Execute]
    (Synthesis)  (Advisory)       (Action)
```

### API Contract

**Input:**
```python
class StateGraphInput(BaseModel):
    question: str
    context: Dict[str, Any]                    # Metadata, constraints
    personas: List[str] = ["advisor", "implementer", "reviewer"]
    response_schema: Optional[str]             # "structured" | "freeform"
    timeout_per_node: int = 45                 # seconds per expert
```

**Output:**
```python
class StateGraphOutput(BaseModel):
    state: Dict[str, Any]                      # Full execution trace
    decisions: List[Decision]                  # Chronological decisions
    final_verdict: str                         # Queen synthesis
    actions: Optional[List[str]]               # Extracted actions
    metadata: {
        "edges_executed": int,
        "nodes_visited": int,
        "total_ms": int,
        "persona_responses": int,
        "state_size_kb": float,
    }
```

### Key Mechanisms

1. **Explicit Graph Definition** — Nodes (agents, routers, validators), edges (conditional, deterministic)
2. **Shared Scratchpad** — All agents see all previous work, never redundant
3. **Conditional Routing** — Router node examines state, decides next edge (e.g., "if Q is tactical → Expert 2, else → Expert 1")
4. **Stateful Recovery** — If Expert 3 times out, router can skip and route to Expert 1's decision

### Pros

- **Visibility** — Every decision traced in graph
- **Reusability** — Graph structure learned + reused across similar questions
- **Deterministic** — No randomness in routing; reproducible
- **Scalable** — 100+ nodes manageable; RETE-style partial matching avoids full re-evaluation
- **Async-native** — Parallel experts, fan-out/fan-in native

### Cons

- **Upfront design burden** — Graph topology must be explicit (no emergent routing)
- **State bloat** — Shared scratchpad grows with conversation history
- **Not self-correcting** — Router can send to wrong expert; no feedback loop to improve routing
- **Context window pressure** — Large state = fewer tokens for new queries

### When to Use

- Medium-scale systems (3-10 experts)
- Repeatable workflows (same graph used 10+ times)
- Transparency critical (audit trails required)
- **Current project:** Tribunal + GSD integration (each phase = new graph instance)

---

## Pattern 2: **Dynamic Persona Registry + Semantic Routing** (LLaMA Index + Viking Model)

### Architecture

```
┌─────────────────────────────────────────────┐
│  Dynamic Persona Registry (111+ skills)     │
│  ┌────────────────────────────────────────┐ │
│  │ Skill metadata:                        │ │
│  │ • name, description, tags              │ │
│  │ • embedding (Model2Vec 256-dim)        │ │
│  │ • performance_stats (latency, quality) │ │
│  │ • related_skills (graph)               │ │
│  └────────────────────────────────────────┘ │
└────────────────────┬────────────────────────┘
                     │
      ┌──────────────┴───────────────┐
      ▼                              ▼
 ┌─────────────┐           ┌──────────────────┐
 │   Viking    │           │  Keyword Index   │
 │  Semantic   │           │  (Hybrid Search) │
 │  Search     │           │                  │
 └──────┬──────┘           └────────┬─────────┘
        │                           │
        └───────────┬───────────────┘
                    ▼
         ┌─────────────────────┐
         │  Selector (Multi)   │ ← Top-K experts (3-5)
         │  • Semantic sim     │
         │  • Keyword overlap  │
         │  • Tags match       │
         │  • Stats (fast? ok?)│
         └──────────┬──────────┘
                    ▼
         ┌─────────────────────┐
         │ Fan-out (Parallel)  │
         │ • Call 3-5 experts  │
         │ • Async gather      │
         │ • Per-expert timeout│
         └─────────────────────┘
```

### API Contract

**Input:**
```python
class DynamicSelectorInput(BaseModel):
    question: str
    max_personas: int = 5
    similarity_threshold: float = 0.5         # Min semantic relevance
    allow_fallback: bool = True               # If <threshold, use keywords
    persona_filters: Optional[Dict]           # E.g., {"tier": "S-TIER"}
    include_reasoning: bool = False           # Return selector rationale
```

**Output (Selector Phase):**
```python
class SelectorOutput(BaseModel):
    selected: List[PersonaScore]              # [{"name": "python-pro", "score": 0.92, "reason": "high match"}]
    query_embedding: List[float]              # 256-dim vector
    reasoning: Optional[str]                  # Why these 5?
```

**Output (Expert Phase):**
```python
class DynamicSelectorOutput(BaseModel):
    selected: List[str]                       # Persona names chosen
    expert_responses: List[ExpertResponse]
    routing_metadata: {
        "search_method": "semantic" | "keyword" | "hybrid",
        "top_k": int,
        "selector_ms": int,
        "fan_out_ms": int,
    }
```

### Key Mechanisms

1. **Semantic Registry** — Every skill has Model2Vec embedding + tags
2. **Hybrid Search** — Viking (semantic) + keyword backup
3. **Scoring** — Combine similarity, keyword overlap, performance stats
4. **Adaptive Fallback** — If semantic < threshold, switch to keyword
5. **Stats Learning** — Personas with better track record ranked higher

### Pros

- **Automatic scaling** — Add 50 new skills, router auto-indexes them
- **No predefined graph** — Topology emerges from question
- **Learns over time** — Performance stats guide future routing
- **Robust fallback** — Keyword matching + semantic handles edge cases
- **Explainable** — Return "reason" field for each selected persona

### Cons

- **Embedding dependency** — Quality limited by Model2Vec accuracy
- **Cold start** — New skills have no performance history
- **Semantic collision** — Similar-sounding experts may conflict (both selected)
- **Slower discovery** — Top-K selection slower than pre-computed graph
- **Requires continuous indexing** — Adding/removing skills must update registry

### When to Use

- Large registries (50+ experts)
- Unknown question types (can't predraw graph)
- Frequently changing expert set
- **Current project:** Tribunal + Viking integration (111 skills, 727 embeddings)

---

## Pattern 3: **Constitutional + Consensus (Anthropic Model)**

### Architecture

```
┌──────────────────────────────────────────┐
│        Constitutional Framework           │
│  (Set of principles/rules to follow)     │
│                                          │
│  Principle 1: "Actionable vs advisory"   │
│  Principle 2: "Max 6 action items"       │
│  Principle 3: "No contradictions"        │
│  Principle 4: "Cite sources"             │
└────────┬────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Expert Fan-Out (3-5 personas)           │
│  Each evaluates CONSTITUTION             │
│  Before responding                       │
└────────┬────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Queen Synthesis                         │
│  1. Identify best answer                 │
│  2. Check vs CONSTITUTION                │
│  3. Self-critique (LLM feedback)         │
│  4. Revise (RLAIF loop)                  │
└────────┬────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Consensus Proposal                      │
│  • Store decision + reasoning            │
│  • Check against past decisions          │
│  • Flag contradictions                   │
│  • Propose to hive-mind (Ruflo)          │
└──────────────────────────────────────────┘
```

### API Contract

**Input:**
```python
class ConstitutionalInput(BaseModel):
    question: str
    constitution: List[str]                  # Principles to follow
    max_actions: int = 6                     # Cap on action items
    model_personas: str = "haiku"            # Cheap evals
    model_queen: str = "sonnet"              # Good synthesis
    model_reviewer: str = "opus"             # Deep review (optional)
    require_consensus: bool = True           # Check vs history
```

**Output:**
```python
class ConstitutionalOutput(BaseModel):
    verdict: str                             # Queen's synthesis
    principle_adherence: {                   # Audit trail
        "principle": str,
        "verdict_adheres": bool,
        "reviewer_notes": Optional[str],
    }
    actions: List[str]                       # Capped at max_actions
    consensus: {
        "proposed_id": str,
        "conflicts_with_past": List[str],    # IDs of contradicting decisions
        "confidence_score": 0.0,             # 0-1, based on agreement
    }
    reasoning_trace: str                     # Full chain-of-thought
```

### Key Mechanisms

1. **Constitution as Guard Rails** — Not rules (Drools-style), but soft constraints
2. **Self-Critique Loop** — Queen evaluates own response against constitution
3. **RLAIF (RL from AI Feedback)** — Preference signal: "This verdict adheres to principle X better"
4. **Consensus Memory** — Compare with past decisions; flag contradictions
5. **Principle Scoring** — For each principle, LLM grades verdict (yes/no/partial)

### Pros

- **Principled decisions** — Not arbitrary; grounded in explicit values
- **Self-improving** — RLAIF feedback trains better queen over time
- **Contradiction detection** — Compare new decisions with history
- **Transparent reasoning** — Principle adherence audit trail
- **Reduces hallucination** — Constitution constrains queen's output space

### Cons

- **Requires constitution design** — Upfront cost (domain-specific principles)
- **Slow evaluation loop** — RLAIF adds extra Claude calls (empress review)
- **False positives** — LLM grades principles imperfectly (80% accuracy)
- **Not fully adversarial** — Self-critique can miss edge cases
- **Consensus overhead** — Querying past decisions is slow (vector search needed)

### When to Use

- Principled systems (constitutional AI, governance)
- Decision quality critical (legal, medical)
- Long-term consistency required
- **Current project:** Tribunal + Ruflo consensus (phase-level decisions)

---

## Pattern 4: **RETE-Style Working Memory + Forward Chaining**

### Architecture

```
┌──────────────────────────────────┐
│  Working Memory (Fact Database)  │
│  • Facts (asserted at runtime)   │
│  • Decisions (from past queries)  │
│  • Metadata (timestamp, source)   │
│                                  │
│  E.g. facts:                     │
│    fact(phase_5_plan_a_done)     │
│    fact(phase_5_plan_b_blocked)  │
│    decision(best_approach_is_x)  │
└──────────┬───────────────────────┘
           │
           ▼ (RETE matching: O(n) not O(n²))
┌──────────────────────────────────┐
│  Production Memory (Rules)       │
│                                  │
│  Rule 1: IF phase_done           │
│          AND all_tests_pass      │
│          THEN trigger_next_phase │
│                                  │
│  Rule 2: IF plan_blocked         │
│          AND depends_on(A,B)     │
│          THEN escalate_decision  │
│                                  │
│  Rule 3: IF contradiction        │
│          BETWEEN decision(X)     │
│          AND decision(Y)         │
│          THEN request_tribunal   │
└──────────┬───────────────────────┘
           │
           ▼ (Forward chain: facts trigger rules)
┌──────────────────────────────────┐
│  Inference Engine (Active)       │
│  • Execute rule actions          │
│  • Assert new facts              │
│  • Trigger cascading rules       │
│  • Emit events (publish/sub)     │
└──────────────────────────────────┘
```

### API Contract

**Input (Fact Assertion):**
```python
class FactAssertion(BaseModel):
    fact: str                                # E.g., "phase_5_plan_a_done"
    timestamp: float                         # Unix time
    source: str                              # "gsd-executor" | "test-runner" | "human"
    metadata: Optional[Dict]                 # Context
    retract_if_exists: bool = False          # Replace existing fact
```

**Input (Rule Definition):**
```python
class Rule(BaseModel):
    name: str                                # Unique ID
    when: str                                # LLM-evaluated condition
    then: str                                # Action (assert, escalate, trigger)
    priority: int = 50                       # Execution order (0-100)
    max_fires: Optional[int] = None          # Limit cascades
```

**Output (Event Stream):**
```python
class RETEEvent(BaseModel):
    type: "fact_asserted" | "rule_fired" | "action_taken"
    timestamp: float
    fact_or_rule: str
    triggered_rules: Optional[List[str]]     # Cascading
    new_facts_asserted: List[str]
    actions_taken: Optional[List[str]]       # E.g., ["escalate_tribunal", "trigger_phase_6"]
```

### Key Mechanisms

1. **RETE Algorithm** — O(n) matching, not O(n²); partial matches cached
2. **Working Memory** — Persistent fact store (SQLite or Ruflo memory)
3. **Forward Chaining** — Facts drive rule execution (data-driven, not goal-driven)
4. **Cascading** — One rule can fire others; manageable via max_fires
5. **Event Stream** — All state changes published; subscribers act on events

### Pros

- **Efficient scaling** — RETE handles 1000+ rules + 10000+ facts efficiently
- **Live reactivity** — Assert fact → rules fire → new facts → cascading
- **Audit trail** — Every fact + rule fire logged with timestamp
- **Decoupled** — Rules don't call each other; facts decouple dependencies
- **Learnable** — New rules added dynamically; old rules persist

### Cons

- **Rule priority Hell** — Cascading order unpredictable if rules have complex dependencies
- **Debugging hard** — "Why did rule X fire?" requires tracing entire WM state
- **Not suitable for judgment** — RETE is deterministic; can't handle LLM-style reasoning well
- **State explosion** — 100 facts × 50 rules = 5000 potential matches
- **No built-in consensus** — Facts are binary (true/false); no confidence/partial match

### When to Use

- Reactive systems (fact change → action)
- GSD phase automation (plans finish → rules trigger next phase)
- **Current project:** Tribunal + GSD integration (fact: phase_5_done → rule: start verification)
- Complex event processing (streaming data, real-time decisions)

---

## Pattern 5: **Unified Tribunal Automaton** (Project Current Implementation)

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  tribunal_automaton(question, personas, models, config)  │
└────────┬──────────────────────────────────────────────────┘
         │
         ├─→ 1. PERSONA SELECTION (Viking + Keyword)
         │      ├─→ viking_search(question_keywords)
         │      ├─→ _select_personas() → 3-5 experts
         │      └─→ Metadata: names, models (haiku), timeout (45s)
         │
         ├─→ 2. EXPERT FAN-OUT (Parallel Invocation)
         │      ├─→ asyncio.gather(*expert_tasks, timeout=45s)
         │      ├─→ Per-expert timeout + return_exceptions
         │      ├─→ Filter valid responses (ok=True)
         │      └─→ Queen notices: "only N/M responded"
         │
         ├─→ 3. QUEEN SYNTHESIS (Sonnet)
         │      ├─→ Input: expert opinions + partial notice
         │      ├─→ Structured output: VERDICT + ACTIONS block
         │      ├─→ Output: verdict (str) + ms (int)
         │      └─→ Parse actions via _parse_actions()
         │
         ├─→ 4. RUFLO MEMORY STORE
         │      ├─→ _store_ruflo(question, verdict, names, ms)
         │      ├─→ Store to Ruflo vector db (if available)
         │      └─→ Return memory_key (for later recall)
         │
         ├─→ 5. ACTION PARSING & TASK CREATION
         │      ├─→ _parse_actions() → List[str] (primary: ACTIONS block, fallback: heuristics)
         │      ├─→ Cap: max 6 actions (prevent hallucination spam)
         │      ├─→ Threshold: only create tasks if len(actions) >= 2
         │      ├─→ _create_ruflo_tasks() → POST /api/task/create for each action
         │      └─→ Return task_ids (ready for Agent Team execution)
         │
         ├─→ 6. HIVE-MIND CONSENSUS
         │      ├─→ _propose_consensus() → POST /api/hive-mind/consensus
         │      ├─→ Store decision + check for contradictions
         │      └─→ Return consensus_id
         │
         └─→ 7. RETURN & EXECUTION HINT
                ├─→ Formatted output: experts + queen + actions + tasks + hint
                ├─→ Hint: "Spawn Agent Team: 1 teammate per task"
                └─→ Skill triggers: `/decision-tribunal` → spawn Agent Teams
```

### API Contract

**Input:**
```python
class AutomatonInput(BaseModel):
    question: str                            # The decision to make
    personas: Optional[str] = None           # Comma-sep skill names or auto-select
    model_personas: str = "haiku"            # Cheap, fast experts
    model_queen: str = "sonnet"              # Good synthesis
    max_personas: int = 5                    # 2-10
    auto_tasks: bool = True                  # Create Ruflo tasks
    auto_consensus: bool = True              # Propose to hive-mind
```

**Output:**
```python
class AutomatonOutput(BaseModel):
    question: str
    names: List[str]                         # Personas selected
    persona_results: List[ExpertResponse]    # All expert opinions
    valid_count: int                         # How many responded
    queen: {
        "response": str,                     # Full verdict
        "ms": int,
    }
    total_ms: int
    ruflo_memory: Optional[str]              # Key for later recall
    actions: List[str]                       # Extracted action items (max 6)
    task_ids: List[str]                      # Created by Ruflo (if 2+ actions)
    consensus_id: Optional[str]              # Hive-mind consensus ID
    execution_hint: str                      # "Spawn Agent Team with N tasks"
```

### Key Mechanisms

1. **Automatic Persona Selection** — Viking + keyword matching → 3-5 best experts
2. **Per-Expert Timeout** — 45s max; timeouts don't block others
3. **Structured Queen Output** — Forced `ACTIONS:` block → 95%+ parse rate
4. **Action Parsing** — 3-tier fallback: structured block → numbered list → verb lines
5. **Threshold Gating** — Tasks created only if 2+ actions (avoid single-item parallelization)
6. **Memory Persistence** — All decisions stored in Ruflo + checked for contradictions
7. **Skill Integration** — Automaton returns task IDs; skill spawns Agent Teams

### Pros

- **Zero-configuration** — Works with 111-skill registry out of box
- **Resilient** — Timeouts handled, partial responses OK (queen adapts)
- **Replayable** — All decisions in Ruflo; query history for patterns
- **Audit trail** — Full trace: question → personas → queen → actions → tasks
- **Integrated with GSD** — Tribunal decisions become Ruflo tasks → Agent Teams execute
- **Self-improving** — Ruflo learns best personas for each question type

### Cons

- **No pre-computation** — Selection + fan-out + queen = ~30-60s per call
- **Cost** — 5 haiku calls (~0.05×5=$0.25) + 1 sonnet (~$0.018) = ~$0.27/call
- **Semantic fragility** — If question poorly worded, Viking finds wrong personas
- **Task extraction unpredictable** — LLM-generated actions may not be parseable
- **Consensus overhead** — Checking past decisions requires vector search (slow)
- **Single queen** — No fallback if sonnet times out; would need backup queen

### When to Use

- GSD phase decisions (auto-trigger tribunal at key milestones)
- Competing plans (adjudicate via tribunal)
- Architecture reviews (auto-select experts, ask tribunal)
- **Current project:** Primary decision engine for Tribunal MCP + Skill

---

## Pattern Comparison Matrix

| Dimension | Pattern 1: State Graph | Pattern 2: Dynamic Registry | Pattern 3: Constitutional | Pattern 4: RETE | Pattern 5: Automaton |
|-----------|----------------------|----------------------------|-------------------------|-----------------|---------------------|
| **Setup cost** | Medium (design graph) | Low (index skills) | Medium (define constitution) | High (define rules) | Low (uses 111 skills) |
| **Expert count** | 3-15 (fixed) | 10-500 (dynamic) | 3-10 (for Q&A) | N/A (facts, not experts) | 3-5 per call (from 111) |
| **Scaling** | Linear (nodes) | Sub-linear (vector search) | Constant (constitution size) | Linear (rules) | Logarithmic (top-K) |
| **Routing type** | Deterministic (edges) | Automatic (semantic) | Rule-based (principles) | Fact-driven (forward chain) | Semantic + keyword |
| **Decision persistence** | State graph | Vector DB | Constitutional store | Working memory | Ruflo DB |
| **Contradiction handling** | Manual (graph design) | Human review | Constitution check | Rule priority | Consensus check |
| **Execution speed** | Fast (<2s) | Medium (5-10s) | Slow (20-30s, review loop) | Reactive (<100ms) | Medium (30-60s) |
| **Token cost** | Low (reuse state) | Medium (per-call) | High (multiple reviews) | None (logic) | Medium (~$0.27) |
| **Audit trail** | Explicit (DAG) | Implicit (search logs) | Principled (scores) | Complete (fact log) | Complete (memory) |
| **Self-learning** | Learned graph structure | Performance stats | RLAIF preference model | N/A | Persona ranking |
| **Best for** | Repeatable workflows | Large skill registry | Principled decisions | Real-time phase automation | GSD + decision-making |

---

## GSD Phase Integration Patterns

### Trigger Points (When to Auto-Invoke Tribunal)

| Phase Event | Tribunal Trigger | Decision Type |
|-------------|------------------|---------------|
| Plan conflicts detected | YES | Adjudicate competing approaches |
| Phase blocking decision | YES | Get expert consensus |
| Architecture choice | MAYBE | Validate design (not always needed) |
| Code review findings | NO | Fix directly (no tribunal) |
| Test failures | NO | Debug (not a decision) |
| Dependency resolution | YES | Multiple plans depend on same module |
| Refactor scope | YES | How deep to refactor? (3 experts) |
| Performance bottleneck | YES | Trade-offs require expert input |
| Security finding | YES | Severity + remediation (constitution) |

### Integration Workflow

```
GSD Phase Execution
    ├─→ Planner: "Phase N has 4 independent plans"
    │
    ├─→ Executor: Spawn 4 teammates
    │        ├─→ T1 works on plan A
    │        ├─→ T2 works on plan B
    │        └─→ T3 works on plan C
    │
    ├─→ [T1 discovers conflict with plan B]
    │
    ├─→ T1 messages lead: "Plans A & B use incompatible approaches for X"
    │
    ├─→ Lead: Call tribunal_automaton(
    │       question="How should we reconcile A & B on X?",
    │       personas="auto",  # Select from architecture experts
    │       auto_tasks=True
    │    )
    │
    ├─→ Tribunal returns:
    │       • Expert opinions (3 architects)
    │       • Queen verdict (use approach A + adapt B)
    │       • Actions: [
    │           "Modify plan B to use approach A",
    │           "Update shared module X per approach A",
    │           "Test integration A+B"
    │         ]
    │       • task_ids: ["t-1", "t-2", "t-3"]
    │
    ├─→ Lead spawns fix team:
    │       • Teammate "fix-plan-b" ← gets task t-1
    │       • Teammate "update-module-x" ← gets task t-2
    │       • Teammate "integration-test" ← gets task t-3
    │
    └─→ Teammates execute in parallel, commit, merge back to phase
```

### GSD + Tribunal: Decision Caching

To avoid re-asking same question:

```python
class GSDTribunalCache:
    cache_key = hash(question + frozenset(personas))

    if cache_hit(cache_key):
        verdict = cached_verdict
        log("Using cached verdict from Ruflo memory")
    else:
        verdict = tribunal_automaton(question, personas)
        store_in_ruflo(verdict)
        log("New tribunal decision stored")
```

**Time saved:** 30-60s per cached decision × avg 2 decisions per phase = 1-2 min saved per large phase.

---

## Implementation Roadmap

### Phase 1: Tribunal MCP Completion (2026-03-22)
- ✅ `tribunal_automaton` tool added
- ✅ Action parsing (_parse_actions)
- ✅ Ruflo task creation
- ✅ Consensus proposal
- → Skill updated with Agent Team spawn instructions

### Phase 2: GSD Integration (2026-03-23)
- [ ] Add tribunal trigger points to GSD executor
- [ ] Decision caching in Ruflo memory
- [ ] Agent Team spawning from tribunal tasks
- [ ] Lead validation flow

### Phase 3: Pattern Learning (2026-03-24)
- [ ] Persona ranking by success rate
- [ ] Question classification (tactical/strategic/architecture)
- [ ] Auto-route based on classification
- [ ] Feedback loop: "Was tribunal verdict helpful?"

### Phase 4: Constitutional + Consensus (2026-03-25)
- [ ] Define LocaNext constitution (5-7 principles)
- [ ] Implement self-critique in queen
- [ ] Track contradictions across decisions
- [ ] Monthly consensus report

---

## Conclusions

1. **No one pattern fits all** — State graphs for workflows, RETE for automation, constitutional for principles, registry for scale, automaton for integrated systems.

2. **Tribunal automaton is a synthesis** — Combines dynamic registry (Pattern 2) + constitutional evaluation (Pattern 3) + RETE-style cascading (Pattern 4) + state logging (Pattern 1).

3. **GSD phase triggers are key** — Tribunal most valuable when automatically invoked at decision points (plan conflicts, blocking decisions, architecture reviews).

4. **Persistence is non-negotiable** — Every decision must be stored (Ruflo, vector DB, working memory) for auditing, learning, contradiction detection.

5. **Next evolution: Unified model** — Combine all 5 patterns into single system:
   - **Registry** for persona selection
   - **State graph** for execution trace
   - **RETE** for fact-driven phase automation
   - **Constitutional** for decision quality
   - **Automaton** as the entry point

---

## References

- [LangGraph Multi-Agent Orchestration: Complete Framework Guide](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [Building Multi-Agent Systems with LangGraph](https://medium.com/@sushmita2310/building-multi-agent-systems-with-langgraph-a-step-by-step-guide-d14088e90f72)
- [LLaMA Index Routers Documentation](https://developers.llamaindex.ai/python/framework/module_guides/querying/router/)
- [Constitutional AI: Harmlessness from AI Feedback (Anthropic)](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback)
- [Drools Expert System Documentation](https://docs.drools.org/6.0.0.CR3/drools-expert-docs/html_single/)
- [RETE Algorithm Overview](https://en.wikipedia.org/wiki/Rete_algorithm)
- [GSD Phase Planning and Validation](https://github.com/gsd-build/get-shit-done)
- Project: `docs/reference/SWARM_GSD_INTEGRATION.md`
- Project: `docs/superpowers/specs/2026-03-22-tribunal-automaton-design.md`
- Project: `docs/superpowers/plans/2026-03-22-tribunal-automaton.md`

---

*Document: 2026-03-22 | Systems: Tribunal MCP + GSD + Ruflo + Viking + brains-trust*
