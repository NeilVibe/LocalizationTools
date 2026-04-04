# Parallel Agent Protocol

> **Philosophy:** Share the work. Agents work in parallel. Never do sequentially what can be done in parallel.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Agent Types](#agent-types)
3. [When to Use Multiple Agents](#when-to-use-multiple-agents)
4. [Parallel Patterns](#parallel-patterns)
5. [Real Examples](#real-examples)
6. [Anti-Patterns](#anti-patterns)
7. [Invocation Reference](#invocation-reference)

---

## Philosophy

```
SEQUENTIAL (WRONG)                    PARALLEL (RIGHT)
─────────────────                     ────────────────
Agent 1: Bug A → Bug B → Bug C        Agent 1: Bug A
Total: 30 min                         Agent 2: Bug B
                                      Agent 3: Bug C
                                      Total: 10 min (3x faster)
```

**Core Principles:**

1. **Share the Work** - If you have 5 bugs, spawn 5 agents
2. **Independence** - Each agent works on isolated concerns
3. **Parallel by Default** - Only go sequential when there are dependencies
4. **Specialize** - Use the right agent type for each task

---

## Agent Types

### Core Agents

| Agent | Purpose | Best For |
|-------|---------|----------|
| `Bash` | Command execution | Git, npm, system commands |
| `Explore` | Fast codebase exploration | Finding files, understanding structure |
| `Plan` | Design implementation strategies | Architecture decisions, feature planning |
| `general-purpose` | Multi-step complex tasks | Tasks requiring multiple tools |

### Debug Agents

| Agent | Purpose | Best For |
|-------|---------|----------|
| `gdp-debugger` | EXTREME precision debugging | Critical bugs, data corruption |
| `vite-debugger` | Frontend debugging | Svelte, HMR, bundle issues |
| `nodejs-debugger` | Backend debugging | Server, API, database issues |
| `code-reviewer` | Check for bugs and patterns | Code quality, finding issues |

### Specialist Agents

| Agent | Purpose | Best For |
|-------|---------|----------|
| `quicksearch-specialist` | QuickSearch tool expertise | Search functionality |
| `qacompiler-specialist` | QA Compiler expertise | Quality assurance tools |
| `xls-transfer-specialist` | XLS Transfer expertise | Excel data handling |
| `tm-specialist` | Translation Memory expertise | TM operations |

---

## When to Use Multiple Agents

### Bug Hunting (3-5 agents per bug)

```
1 Bug = Multiple Investigation Angles

Agent 1: Check frontend code
Agent 2: Check backend code
Agent 3: Check database queries
Agent 4: Check API endpoints
Agent 5: Check logs
```

### Feature Development

```
1 Feature = Plan + Explore + Review

Agent 1 (Plan): Design the implementation
Agent 2 (Explore): Find related code
Agent 3 (code-reviewer): Check existing patterns
```

### Documentation

```
Multiple Docs = 1 Agent Per File

Agent 1: Write README.md
Agent 2: Write API_DOCS.md
Agent 3: Write CONTRIBUTING.md
```

### Code Review

```
Large PR = Multiple Reviewers

Agent 1: Check for security issues
Agent 2: Check for performance issues
Agent 3: Check for code style
Agent 4: Check for test coverage
Agent 5: Check for documentation
Agent 6: Check for accessibility
```

---

## Parallel Patterns

### Pattern 1: One Agent Per Issue

```
Issues: [BUG-001, BUG-002, BUG-003]

Spawn:
  Agent 1 → BUG-001
  Agent 2 → BUG-002
  Agent 3 → BUG-003

Wait for all → Collect results
```

### Pattern 2: One Agent Per File

```
Files to analyze: [file1.ts, file2.ts, file3.ts]

Spawn:
  Agent 1 → Analyze file1.ts
  Agent 2 → Analyze file2.ts
  Agent 3 → Analyze file3.ts

Wait for all → Merge findings
```

### Pattern 3: One Agent Per Concern

```
Task: Fix a complex bug

Phase 1 (Parallel):
  Agent 1 (Analyze): Deep dive into the issue
  Agent 2 (Discuss): Consider alternative explanations
  Agent 3 (Explore): Find related code

Phase 2 (Sequential, after Phase 1):
  Agent 4 (Conclude): Synthesize findings

Phase 3 (Parallel):
  Agent 5 (Document): Write the analysis
  Agent 6 (Fix): Implement the solution
```

### Pattern 4: Fan-Out Verification

```
After a fix, verify from multiple angles:

Agent 1: Run unit tests
Agent 2: Run integration tests
Agent 3: Check TypeScript types
Agent 4: Check ESLint
Agent 5: Manual verification
Agent 6: Check logs
Agent 7: Check database state
Agent 8: Check UI rendering
Agent 9: Check API responses
```

---

## Real Examples

### Example 1: 7 Debug Agents for Folder Issue

```
Problem: Folders not showing correctly

Spawned:
  Agent 1: Check FolderTree.svelte component
  Agent 2: Check folder API endpoints
  Agent 3: Check database queries
  Agent 4: Check folder store
  Agent 5: Check WebSocket sync
  Agent 6: Check error handling
  Agent 7: Check console logs

Result: Found issue in 10 minutes instead of 70 minutes
```

### Example 2: Analyze-Discuss-Conclude-Document-Fix Pattern

```
Problem: Complex state management bug

Phase 1 (Parallel):
  Agent 1 (Analyze): "Examine the state flow"
  Agent 2 (Discuss): "Consider race conditions"
  Agent 3 (Explore): "Find all state mutations"

Phase 2:
  Agent 4 (Conclude): "Root cause is X because..."

Phase 3 (Parallel):
  Agent 5 (Document): Write ISSUE_ANALYSIS.md
  Agent 6 (Fix): Implement the solution
```

### Example 3: 9 Parallel Agents for Verification

```
After fixing a critical bug:

  Agent 1: npx playwright test --project=chromium
  Agent 2: npx playwright test --project=firefox
  Agent 3: npx playwright test --project=webkit
  Agent 4: npm run typecheck
  Agent 5: npm run lint
  Agent 6: python -m pytest tests/unit/
  Agent 7: python -m pytest tests/integration/
  Agent 8: Check error logs
  Agent 9: Manual UI verification

All pass → Safe to merge
```

---

## Anti-Patterns

### WRONG: Single Agent for Multiple Issues

```
❌ BAD:
  Agent 1: Fix BUG-001, then BUG-002, then BUG-003
  (Sequential, slow, context switching)

✅ GOOD:
  Agent 1: Fix BUG-001
  Agent 2: Fix BUG-002
  Agent 3: Fix BUG-003
  (Parallel, fast, focused)
```

### WRONG: Sequential When Parallel is Possible

```
❌ BAD:
  1. Run tests
  2. Wait...
  3. Run linter
  4. Wait...
  5. Run typecheck
  6. Wait...

✅ GOOD:
  Parallel: [tests, linter, typecheck]
  Wait for all (once)
```

### WRONG: Not Sharing Work

```
❌ BAD:
  Claude: "I'll review all 20 files myself"
  (Takes forever, misses things)

✅ GOOD:
  Claude: "Spawning 6 agents to review files in parallel"
  Agent 1: Files 1-4
  Agent 2: Files 5-8
  Agent 3: Files 9-12
  Agent 4: Files 13-16
  Agent 5: Files 17-20
  Agent 6: Overall architecture review
```

### WRONG: Over-Parallelization

```
❌ BAD:
  Spawning 50 agents for trivial tasks
  (Overhead exceeds benefit)

✅ GOOD:
  Match agent count to task complexity
  Simple task: 1-2 agents
  Medium task: 3-5 agents
  Complex task: 6-10 agents
```

---

## Invocation Reference

### Basic Agent Invocation

```
Use the Task tool to spawn agents:

Task: "Analyze the folder API endpoints"
Agent: code-reviewer
```

### Parallel Agent Batch

```
Spawn multiple agents in one message:

Task 1: "Check FolderTree.svelte for bugs"
Task 2: "Check folder.py API routes"
Task 3: "Check folder database queries"
Task 4: "Check WebSocket folder sync"
```

### Agent with Specific Instructions

```
Task: "Debug the folder deletion issue using GDP protocol"
Agent: gdp-debugger
Instructions: |
  1. Follow GRANULAR_DEBUG_PROTOCOL.md
  2. Add microscopic logging
  3. Trace the exact failure point
  4. Report findings with evidence
```

### Chained Agents (Dependencies)

```
Phase 1 (Parallel):
  Task A: "Analyze problem"
  Task B: "Explore codebase"

Phase 2 (After Phase 1):
  Task C: "Synthesize findings from A and B"

Phase 3 (Parallel):
  Task D: "Write documentation"
  Task E: "Implement fix"
```

---

## Decision Matrix

| Scenario | Agent Count | Agent Types |
|----------|-------------|-------------|
| Single trivial bug | 1 | general-purpose |
| Single complex bug | 3-5 | gdp-debugger, Explore, code-reviewer |
| Multiple bugs | 1 per bug | Varies by bug type |
| New feature | 3-4 | Plan, Explore, code-reviewer, general-purpose |
| Code review | 5-6 | code-reviewer (different concerns) |
| Documentation | 1 per file | general-purpose |
| Verification | 5-9 | Bash (tests), Explore (logs), general-purpose |

---

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│  PARALLEL AGENT PROTOCOL - KEY TAKEAWAYS                    │
├─────────────────────────────────────────────────────────────┤
│  1. Share the work - spawn agents for independent tasks     │
│  2. Use specialized agents - right tool for the job         │
│  3. Parallel by default - only sequential when dependent    │
│  4. Match count to complexity - don't over/under-parallelize│
│  5. Verify in parallel - multiple checks simultaneously     │
└─────────────────────────────────────────────────────────────┘
```

---

*Last updated: 2026-02-01*
