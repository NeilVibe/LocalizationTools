# Agent Orchestration Patterns

> How to effectively use multiple Claude agents for complex tasks.

---

## The Conductor Pattern

The **Conductor Pattern** is the primary orchestration model for multi-agent workflows.

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN CLAUDE (Conductor)                  │
│                                                             │
│  - Understands the full context                             │
│  - Decides when to spawn agents                             │
│  - Assigns focused tasks to each agent                      │
│  - Aggregates results from all agents                       │
│  - Synthesizes findings into action items                   │
│  - Dispatches follow-up agents as needed                    │
└─────────────────────────────────────────────────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
     ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
     │Agent 1 │    │Agent 2 │    │Agent 3 │    │Agent N │
     │        │    │        │    │        │    │        │
     │Focused │    │Focused │    │Focused │    │Focused │
     │Task A  │    │Task B  │    │Task C  │    │Task N  │
     └────────┘    └────────┘    └────────┘    └────────┘
          │              │              │              │
          └──────────────┴──────────────┴──────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Results Aggregation    │
                    │  by Main Claude         │
                    └─────────────────────────┘
```

**Key Principle:** Main Claude is the single point of coordination. Agents complete their focused tasks and return results. Main Claude synthesizes everything.

---

## When to Spawn Agents

### Debugging Sessions: 3-7 Agents per Bug

Complex bugs benefit from parallel investigation:

| Agent Role | Focus Area |
|------------|------------|
| **Agent 1** | Read the error logs, trace the stack |
| **Agent 2** | Examine the failing function/module |
| **Agent 3** | Check related database queries |
| **Agent 4** | Review recent changes to affected files |
| **Agent 5** | Analyze test coverage gaps |
| **Agent 6** | Check for similar past bugs |
| **Agent 7** | Validate fix approach |

**Example - folder_repo.py debugging session:** 9 agents deployed
- 3 agents: Trace different code paths
- 2 agents: Analyze database operations
- 2 agents: Review test failures
- 1 agent: Check API contracts
- 1 agent: Propose and validate fix

### Documentation Review: 1 Agent per File

For large documentation overhauls:

```
Main Claude identifies 10 docs needing review
     │
     ├─→ Agent 1: Review ARCHITECTURE.md
     ├─→ Agent 2: Review API_REFERENCE.md
     ├─→ Agent 3: Review TESTING_GUIDE.md
     ├─→ Agent 4: Review DEPLOYMENT.md
     ├─→ Agent 5: Review SECURITY.md
     ├─→ Agent 6: Review TROUBLESHOOTING.md
     ├─→ Agent 7: Review CHANGELOG.md
     ├─→ Agent 8: Review CONTRIBUTING.md
     ├─→ Agent 9: Review MIGRATION.md
     └─→ Agent 10: Review GLOSSARY.md
            │
            ▼
     Main Claude aggregates all findings
     Spawns fix agents for each issue found
```

### Feature Implementation: Plan → Explore → Code → Review

Structured workflow for new features:

| Phase | Agent Count | Purpose |
|-------|-------------|---------|
| **Plan** | 1-2 agents | Analyze requirements, propose architecture |
| **Explore** | 2-4 agents | Investigate existing code, find integration points |
| **Code** | 1-3 agents | Implement different components in parallel |
| **Review** | 2-3 agents | Review code, check edge cases, validate tests |

---

## Agent Communication

### Critical Rule: Agents Do NOT Talk to Each Other

```
❌ WRONG: Agent 1 → Agent 2 (direct communication)

✅ CORRECT:
   Agent 1 → Main Claude → Agent 2
```

### Communication Flow

```
1. Main Claude spawns Agent A with specific task
2. Agent A completes task, returns results to Main Claude
3. Main Claude analyzes results
4. If follow-up needed, Main Claude spawns Agent B with new context
5. Agent B has NO knowledge of Agent A (unless Main Claude provides it)
```

### Why This Matters

- **Consistency:** Main Claude maintains single source of truth
- **Context Control:** Each agent gets exactly the context it needs
- **No Confusion:** Agents don't have conflicting information
- **Traceable:** All decisions flow through Main Claude

---

## Result Aggregation

### The Aggregation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: COLLECT                                             │
│                                                             │
│   Agent 1 returns: "Found null check missing in line 45"    │
│   Agent 2 returns: "Database query returns empty list"      │
│   Agent 3 returns: "Test mock doesn't match real behavior"  │
│   Agent 4 returns: "Similar bug fixed in commit abc123"     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: SYNTHESIZE                                          │
│                                                             │
│   Main Claude correlates findings:                          │
│   - Root cause: Missing null check causes empty list        │
│   - Similar fix exists in commit abc123                     │
│   - Test needs updating to catch this case                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: ACTION ITEMS                                        │
│                                                             │
│   1. Add null check at line 45                              │
│   2. Update database query to handle empty case             │
│   3. Fix test mock to match real behavior                   │
│   4. Add regression test for this scenario                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: DISPATCH FIX AGENTS                                 │
│                                                             │
│   Fix Agent 1 → Implement null check                        │
│   Fix Agent 2 → Update database query                       │
│   Fix Agent 3 → Correct test mock                           │
│   Fix Agent 4 → Write regression test                       │
└─────────────────────────────────────────────────────────────┘
```

### Aggregation Best Practices

| Practice | Description |
|----------|-------------|
| **Categorize** | Group findings by type (bugs, improvements, questions) |
| **Prioritize** | Order by severity/impact |
| **Deduplicate** | Multiple agents may find same issue |
| **Validate** | Cross-check conflicting findings |
| **Track** | Note which agent found what (for follow-up) |

---

## Real Examples

### Example 1: folder_repo.py Debugging Session (9 Agents)

**Problem:** Folder operations failing intermittently

**Agent Deployment:**

| Agent | Task | Finding |
|-------|------|---------|
| 1 | Trace error logs | `IntegrityError` on folder creation |
| 2 | Analyze folder_repo.py | Race condition in get_or_create |
| 3 | Check database schema | Foreign key constraint issue |
| 4 | Review recent commits | New validation added without migration |
| 5 | Examine test failures | 3 tests timing-dependent |
| 6 | Check API layer | Missing transaction wrapper |
| 7 | Analyze concurrent access | No locking mechanism |
| 8 | Propose fix | Add SELECT FOR UPDATE |
| 9 | Validate fix approach | Confirmed safe for SQLite and PostgreSQL |

**Synthesized Action:**
```
1. Add row-level locking to get_or_create
2. Wrap folder operations in transaction
3. Add migration for missing constraint
4. Fix timing-dependent tests
```

### Example 2: Documentation Cleanup (10 Review Agents)

**Problem:** Docs outdated after major refactor

**Agent Deployment:**
- 1 agent per documentation file
- Each agent: Check accuracy, flag outdated sections, suggest updates

**Aggregated Findings:**
```
- ARCHITECTURE.md: 3 diagrams outdated
- API_REFERENCE.md: 12 endpoints missing
- TESTING_GUIDE.md: Old test commands
- DEPLOYMENT.md: Accurate (no changes)
- SECURITY.md: 2 new auth methods missing
```

**Follow-up Agents:**
- Fix Agent 1: Update architecture diagrams
- Fix Agent 2: Document missing endpoints
- Fix Agent 3: Update test commands
- Fix Agent 4: Add new auth methods

### Example 3: Schema Mismatch Resolution (5-Agent Pipeline)

**Problem:** Frontend and backend schema diverged

**Sequential Pipeline:**

```
Agent 1 (Analyze)
   │ Task: Compare frontend types with backend models
   │ Result: 8 mismatches identified
   ▼
Agent 2 (Discuss)
   │ Task: Determine which schema is correct for each
   │ Result: Backend correct for 5, Frontend correct for 3
   ▼
Agent 3 (Conclude)
   │ Task: Create reconciliation plan
   │ Result: Migration steps documented
   ▼
Agent 4 (Document)
   │ Task: Update type definitions and docs
   │ Result: Types updated, changelog written
   ▼
Agent 5 (Fix)
   │ Task: Implement changes, run tests
   │ Result: All tests pass, PR ready
```

---

## Agent Spawning Guidelines

### When to Use Single Agent

- Simple, focused task
- No parallel investigation needed
- Quick lookup or verification

### When to Use Multiple Agents

- Complex debugging (unknown root cause)
- Large-scale review (many files)
- Parallel investigation paths
- Divide-and-conquer problems

### Agent Count Guidelines

| Task Type | Recommended Agents |
|-----------|-------------------|
| Simple bug | 1-2 |
| Complex bug | 3-7 |
| Feature (small) | 2-4 |
| Feature (large) | 5-10 |
| Documentation review | 1 per file |
| Code review | 2-4 per PR |
| Refactoring | 3-6 |

---

## Anti-Patterns

### What NOT to Do

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Agent Explosion** | 20+ agents, chaos | Limit to 10, batch if needed |
| **Vague Tasks** | "Look at this file" | Specific question or goal |
| **No Aggregation** | Raw agent dumps | Synthesize before acting |
| **Agent Chaining** | A spawns B spawns C | Main Claude controls all |
| **Duplicate Work** | Multiple agents same task | Clear task boundaries |

---

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRATION                       │
├─────────────────────────────────────────────────────────────┤
│  1. Main Claude is the CONDUCTOR                            │
│  2. Agents get FOCUSED, SPECIFIC tasks                      │
│  3. Agents NEVER communicate directly                       │
│  4. Main Claude AGGREGATES all results                      │
│  5. Main Claude SYNTHESIZES action items                    │
│  6. Main Claude DISPATCHES fix agents                       │
│  7. REPEAT until problem solved                             │
└─────────────────────────────────────────────────────────────┘
```

---

*This document describes patterns observed in LocaNext development sessions.*
