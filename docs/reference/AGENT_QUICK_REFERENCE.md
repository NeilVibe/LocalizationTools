# Agent Quick Reference Card

> Cheat sheet for selecting the right agent type for any task.

---

## Agent Types

| Agent Type | Use When | Example Task |
|------------|----------|--------------|
| **Bash** | Run commands | Check server status, git operations |
| **gdp-debugger** | ANY bug hunting | Find exact line of failure |
| **code-reviewer** | After writing code | Check for bugs, security issues |
| **Explore** | Understanding codebase | "How does X work?" |
| **Plan** | Before implementation | Design feature approach |
| **vite-debugger** | Frontend bugs | UI issues, Svelte reactivity |
| **nodejs-debugger** | Backend bugs | API, IPC, Electron main process |
| **general-purpose** | Complex multi-step | Research + action combined |
| **quicksearch-specialist** | QuickSearch project | Term checks, dictionary ops |
| **qacompiler-specialist** | QACompiler project | Generator, tracker issues |
| **security-auditor** | Security review | OWASP, injection risks |

---

## Parallel vs Sequential

### Use Parallel When:
- Tasks are **independent** (no data dependencies)
- Searching multiple areas of codebase
- Running multiple read-only operations
- Code review + security audit simultaneously

### Use Sequential When:
- Task B needs output from Task A
- Build must complete before test
- Fix must be applied before verification
- Database migration before schema check

---

## Agent Count by Task Type

| Task Type | Recommended Agents | Notes |
|-----------|-------------------|-------|
| **Simple bug fix** | 1-2 | gdp-debugger + code-reviewer |
| **Feature implementation** | 2-3 | Plan first, then Explore + implement |
| **Code review** | 2-4 | code-reviewer + security-auditor (parallel) |
| **Investigation** | 3-6 | Multiple Explore agents (parallel) |
| **Full audit** | 4-6 | security-auditor + code-reviewer per module |
| **Refactoring** | 2-3 | Explore + Plan + implement |

---

## Common Combinations

### Bug Hunting
```
1. gdp-debugger     → Find root cause
2. code-reviewer    → Verify fix correctness
```

### New Feature
```
1. Plan             → Design approach
2. Explore          → Understand existing code
3. general-purpose  → Implement
4. code-reviewer    → Review implementation
```

### Security Review
```
1. security-auditor → OWASP checks (parallel)
2. code-reviewer    → Logic review (parallel)
3. general-purpose  → Fix findings
```

### Frontend Issue
```
1. vite-debugger    → Debug UI/reactivity
2. code-reviewer    → Review Svelte 5 patterns
```

### Backend Issue
```
1. nodejs-debugger  → Debug API/IPC
2. gdp-debugger     → Trace execution flow
```

### Codebase Understanding
```
1. Explore (x3-6)   → Parallel investigation
2. Plan             → Synthesize findings
```

---

## Decision Flowchart

```
Is it a bug?
├─ YES → gdp-debugger
│        ├─ Frontend? → + vite-debugger
│        └─ Backend?  → + nodejs-debugger
│
└─ NO → Is it new code?
        ├─ YES → Plan → Explore → general-purpose → code-reviewer
        │
        └─ NO → Is it understanding?
                ├─ YES → Explore (parallel, 3-6 agents)
                │
                └─ NO → Is it security?
                        ├─ YES → security-auditor + code-reviewer
                        │
                        └─ NO → general-purpose
```

---

## Quick Rules

1. **Always use gdp-debugger for bugs** - Never guess, always trace
2. **Parallel for reads, sequential for writes** - Multiple searches OK, one fix at a time
3. **Plan before complex features** - 10 min planning saves 2 hours debugging
4. **Code review after every change** - Catch issues before they become bugs
5. **Security audit for user input** - Any endpoint accepting data needs audit

---

## Project-Specific Agents

| Project | Primary Agent | Secondary |
|---------|---------------|-----------|
| LocaNext (main) | general-purpose | vite-debugger, nodejs-debugger |
| QuickSearch | quicksearch-specialist | code-reviewer |
| QACompiler | qacompiler-specialist | code-reviewer |
| MapDataGenerator | mapdatagenerator-specialist | code-reviewer |

---

*Quick reference - see full docs for detailed protocols*
