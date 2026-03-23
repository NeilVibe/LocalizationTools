# Ruflo Intelligence Guide — Feeding the Brain

> How to make Ruflo smarter, more powerful, and continuously learning from your project.

## Architecture

Ruflo's intelligence layer (RuVector v3.0) has 6 components:

| Component | What It Does | Status |
|-----------|-------------|--------|
| **SONA** | Self-Optimizing Neural Architecture — learns from task trajectories | Active |
| **MoE** | Mixture of Experts — routes tasks to 8 specialist experts | Active (8 experts) |
| **HNSW** | Vector index for semantic pattern search (150x-12,500x faster) | Active |
| **Flash Attention** | O(N) memory attention (2.49x-7.47x speedup) | Active |
| **EWC++** | Elastic Weight Consolidation — prevents catastrophic forgetting | Active |
| **LoRA** | Low-Rank Adaptation — 128x memory compression (rank=8) | Active |

## Feeding Ruflo — The 3 Food Groups

### 1. Pattern Storage (Knowledge Food)

Store project patterns Ruflo can search semantically later.

```
mcp__ruflo__hooks_intelligence_pattern-store
  pattern: "Description of the pattern"
  type: "architecture|workflow|domain-knowledge|coding-standards|debugging|testing"
  confidence: 0.95  (0.0 to 1.0)
  metadata: {"project": "LocaNext", "domain": "frontend"}
```

**What to feed:**
- Architecture patterns (component structures, service layer patterns, data flows)
- Domain knowledge (regex patterns, XML rules, localization conventions)
- Workflow patterns (how to plan, review, test — /grill-me pipeline)
- Coding standards (Svelte 5 runes, loguru, Excel lib choices)
- Debugging solutions (resolved bugs, root causes, fix patterns)
- Testing patterns (what to test, how to verify, edge cases)

**Good patterns are:**
- Specific (include actual regex, function names, file paths)
- Confidence-rated (0.99 for hard rules, 0.7-0.8 for heuristics)
- Metadata-tagged (project, domain, source file)

### 2. Trajectory Recording (Experience Food)

Record task execution trajectories so SONA can learn what works.

```
# Start a trajectory
mcp__ruflo__hooks_intelligence_trajectory-start
  trajectoryId: "phase-73-planning"
  metadata: {"phase": 73, "type": "planning"}

# Record steps
mcp__ruflo__hooks_intelligence_trajectory-step
  trajectoryId: "phase-73-planning"
  step: "researched existing ColorText pattern"
  result: "success"
  confidence: 0.95

# End trajectory
mcp__ruflo__hooks_intelligence_trajectory-end
  trajectoryId: "phase-73-planning"
  outcome: "success"
  summary: "Phase 73 planned in 2 plans, 1 wave"
```

**When to record trajectories:**
- GSD phase planning and execution
- Bug investigation and resolution
- Research → implementation cycles
- Code review findings

### 3. Learning Cycles (Digestion)

Force SONA to learn from recorded trajectories:

```
mcp__ruflo__hooks_intelligence_learn
  consolidate: true  (run EWC++ to prevent forgetting)
```

**When to trigger:**
- After completing a GSD phase
- After resolving a complex bug
- End of session (before /clear)
- After storing 5+ new patterns

## Searching Ruflo's Brain

```
mcp__ruflo__hooks_intelligence_pattern-search
  query: "how to render inline tags in Svelte"
  topK: 5
  minConfidence: 0.6
```

Returns semantically similar patterns ranked by similarity score. Use this:
- Before planning (what does Ruflo know about this domain?)
- Before coding (any existing patterns to follow?)
- When debugging (has this been seen before?)

## MoE Expert Routing

Ruflo routes tasks to 8 experts. Each expert specializes:

| Expert | Domain |
|--------|--------|
| coder | Implementation, code writing |
| tester | Testing, verification |
| reviewer | Code review, quality |
| architect | Design, patterns, structure |
| security | Vulnerabilities, auth, input validation |
| performance | Speed, memory, optimization |
| researcher | Investigation, exploration |
| coordinator | Multi-agent orchestration |

Routing happens automatically via:
```
mcp__ruflo__hooks_model-route
  task: "description of what needs doing"
```

## Intelligence Status Check

```
mcp__ruflo__hooks_intelligence_stats
  detailed: true
```

Shows: patterns stored, trajectories recorded, learning cycles completed, expert usage distribution.

## Recommended Feeding Schedule

### Per Session
1. **Start:** Check intelligence stats (`hooks_intelligence_stats`)
2. **During:** Store patterns as you discover them (domain knowledge, architecture decisions)
3. **After each GSD phase:** Record trajectory + trigger learning cycle
4. **End:** Final learning cycle with consolidation

### Per Milestone
1. Bulk-store all architectural patterns from the milestone
2. Store all debugging solutions discovered
3. Run comprehensive learning cycle
4. Review and prune low-confidence patterns

### Pattern Quality Checklist
- [ ] Specific enough to be actionable (not "use good patterns")
- [ ] Includes concrete values (regex, function names, file paths)
- [ ] Has appropriate confidence (0.99 for rules, 0.8 for heuristics, 0.6 for hunches)
- [ ] Tagged with metadata (project, domain, source)
- [ ] Distinct from existing patterns (search first!)

## Example: Seeding a New Project

```javascript
// 1. Architecture patterns
pattern-store: "Service layer extraction: thick modules → service classes, route handlers ≤10 lines"
  type: "architecture", confidence: 0.95

// 2. Domain knowledge
pattern-store: "XML newlines MUST use <br/> tags, never &#10;"
  type: "domain-knowledge", confidence: 0.99

// 3. Coding standards
pattern-store: "Always loguru, never print(). Excel: xlsxwriter write, openpyxl read."
  type: "coding-standards", confidence: 0.98

// 4. Workflow
pattern-store: "grill-me → Tribunal → auto-decide → document decisions in STATE.md"
  type: "workflow", confidence: 0.95

// 5. Trigger learning
intelligence_learn: consolidate: true
```

## Advanced: Attention Patterns

Track what Ruflo pays attention to:
```
mcp__ruflo__hooks_intelligence_attention
  query: "what patterns get accessed most?"
```

Use this to identify which knowledge is most valuable and should be promoted to higher confidence.

---

*Guide created: 2026-03-23. Feed Ruflo well and he grows smarter every session.*
