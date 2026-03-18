# Swarm + GSD + Viking Integration Guide

> **How the mega swarm, GSD project management, and Viking knowledge base work together.**

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        GSD (The Brain)                           │
│  Decides WHAT to build: roadmap → phases → plans → verification  │
│  Commands: /gsd:plan-phase, /gsd:execute-phase, /gsd:verify-work │
└──────────┬───────────────────────────────────────────────────────┘
           │ spawns execution
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                 AGENT TEAMS (The Workforce)                       │
│  Decides HOW to build: team lead → teammates → parallel work     │
│  Each teammate = full Claude Code instance + own git worktree    │
│  TeammateTool: spawn, message, assign tasks, shutdown            │
└──────────┬───────────────────────────────────────────────────────┘
           │ enhanced by
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    RUFLO (The Power Plant)                        │
│  SUPERCHARGES execution: queen validation, WASM boost, memory    │
│  175+ MCP tools available to ALL agents (lead + teammates)       │
│  Self-learning: patterns improve with every execution            │
└──────────────────────────────────────────────────────────────────┘
           │ context from
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    VIKING (The Memory)                            │
│  93+ docs indexed, semantic search, project knowledge            │
│  Available to ALL agents via MCP (viking_search, viking_read)    │
│  Architecture, decisions, patterns, history — all searchable     │
└──────────────────────────────────────────────────────────────────┘
           │ patterns from
           ▼
┌──────────────────────────────────────────────────────────────────┐
│              BRAINS-TRUST SKILL (The Playbook)                   │
│  42 agent patterns: delegation, fan-out, pipeline, swarm         │
│  Teaches Claude HOW to decompose and coordinate agent work       │
└──────────────────────────────────────────────────────────────────┘
```

---

## How They Wire Together

### MCP = Universal Access Layer

Every MCP server is available to **every agent** — the lead, all teammates, and all subagents. This means:

| MCP Server | What Every Agent Gets |
|-----------|----------------------|
| **Viking** | Semantic search over 93+ project docs, architecture, decisions |
| **Ruflo** | 175+ orchestration tools, WASM booster, shared memory |
| **Playwright** | Browser automation for UI testing |
| **Chrome DevTools** | CDP inspection and Lighthouse |
| **Stitch** | Screen generation |
| **DBHub** | Database access |

**No extra wiring needed.** When GSD spawns a teammate, that teammate automatically has Viking + Ruflo + everything.

### GSD Phases → Agent Team Execution

GSD already supports **wave-based parallel execution** (independent plans run simultaneously). With Agent Teams, this becomes much more powerful:

**Before (subagents only):**
```
GSD Phase 5 has 4 plans:
  Plan A (independent) ──→ subagent (fire and forget, reports back)
  Plan B (independent) ──→ subagent (fire and forget, reports back)
  Plan C (depends on A) ──→ waits...
  Plan D (depends on B) ──→ waits...
```

**After (agent teams):**
```
GSD Phase 5 has 4 plans:
  TEAM LEAD coordinates all work
  ├── Teammate "plan-a" ──→ works independently in own worktree
  ├── Teammate "plan-b" ──→ works independently in own worktree
  ├── (plan-a finishes, messages lead)
  ├── Teammate "plan-c" ──→ picks up, can MESSAGE plan-a for context
  ├── (plan-b finishes, messages lead)
  └── Teammate "plan-d" ──→ picks up, can MESSAGE plan-b for context

  Lead synthesizes, verifies, merges worktrees
```

**Key improvement:** Teammates can talk to each other. Plan C can ask Plan A's teammate about edge cases it discovered. This was impossible with subagents.

---

## Usage Modes

### Mode 1: GSD + Agent Teams (Standard Power)

Use GSD normally but request agent teams for execution:

```
/gsd:execute-phase 5

When executing, create an agent team. Assign each plan to a separate
teammate. Each teammate should:
1. viking_search for relevant context before starting
2. Work in their own worktree
3. Message the lead when blocked or when they discover something
   other teammates should know
4. Commit atomically per task (GSD standard)

Require plan approval for any plan that modifies shared files.
```

**When to use:** Most GSD work. Good balance of parallel speed + coordination.

### Mode 2: GSD + Agent Teams + Ruflo (Maximum Power)

For complex phases with many plans:

```
/gsd:execute-phase 5

Execute using ruflo swarm with hierarchical topology.
Queen coordinator validates all outputs before commits.

Wave 1 (Research — all parallel):
  Researcher teammates: viking_search + codebase exploration for each plan

Wave 2 (Implementation — parallel by plan):
  Coder teammates: one per plan, working in isolated worktrees
  Route simple transforms (var-to-const, add-types) through WASM booster

Wave 3 (Verification — parallel):
  Tester teammate: run all tests, check coverage
  Reviewer teammate: code quality, security, CLAUDE.md adherence

Queen validates wave results before advancing to next wave.
Store all findings in ruflo shared memory for cross-wave access.
```

**When to use:** Large phases (4+ plans), cross-cutting concerns, phases where quality gate matters.

### Mode 3: Ruflo Standalone (Outside GSD)

For tasks that don't need GSD project management:

```bash
# Quick codebase analysis
claude-flow hive init --topology star --agents 5
claude-flow agent spawn --type researcher --name "API-Scout"
claude-flow agent spawn --type researcher --name "DB-Scout"
claude-flow agent spawn --type researcher --name "UI-Scout"
claude-flow agent spawn --type analyst --name "Pattern-Finder"
claude-flow agent spawn --type architect --name "Synthesizer"
```

**When to use:** Ad-hoc research, one-off audits, debugging sessions, tasks that don't belong to a GSD milestone.

---

## GSD Phase Execution with Swarm — Step by Step

### 1. Pre-Execution Context Gathering

Before spawning the swarm, the lead should:
```
1. Read the phase PLAN.md (what to build)
2. viking_search("phase N context") for relevant project knowledge
3. Read .planning/STATE.md for current project state
4. Check .planning/config.json for workflow preferences
```

### 2. Team Composition by Phase Type

| Phase Type | Recommended Team |
|-----------|-----------------|
| **Research phase** | 3-4 researcher teammates, each investigating different aspect |
| **Implementation phase** | 1 teammate per plan + 1 reviewer teammate |
| **Bug fix phase** | 3-5 teammates with competing hypotheses |
| **UI/UX phase** | 1 frontend teammate per component + 1 audit teammate |
| **Testing phase** | 1 test-writer per subsystem + 1 coverage analyst |
| **Refactor phase** | 1 coder per module + 1 architect for cross-cutting |

### 3. Task Assignment Strategy

GSD plans already break work into tasks. Map them to the swarm:

```
PLAN.md tasks → Shared task list (Agent Teams)
  ├── Independent tasks → Assigned to different teammates (parallel)
  ├── Dependent tasks → blockedBy array (auto-unblocks when upstream done)
  └── Shared-file tasks → Same teammate (avoid merge conflicts)
```

**Rule: Each teammate owns distinct files.** If Plan A and Plan B both touch `server/api/routes.py`, assign them to the same teammate or sequence them.

### 4. Viking Context Injection

Every teammate should start with Viking context:

```
Spawn prompt template:
"You are working on Phase N, Plan X of the LocaNext project.

Before starting:
1. viking_search('Phase N Plan X requirements')
2. viking_search('existing implementation patterns for [topic]')
3. Read the plan at .planning/phases/N-name/PLAN.md

Your files to own: [list]
Your tasks: [from plan]

Constraints (from CLAUDE.md):
- Svelte 5 Runes only ($state, $derived, $effect)
- Optimistic UI mandatory
- Logger only (loguru, never print)
- XML newlines: <br/> tags only
"
```

### 5. Ruflo Enhancement (When Using Mode 2)

Layer Ruflo on top for:

```
# WASM Booster — route simple transforms automatically
- var-to-const, add-types, async-await → <1ms, no LLM call
- Saves tokens for complex work

# Shared Memory — cross-teammate knowledge
- Teammate A discovers edge case → stored in ruflo memory
- Teammate B queries memory before implementing related code

# Queen Validation — quality gate
- Every commit goes through queen before merge
- Prevents drift from plan objectives
- Catches inconsistencies between teammates' work

# Pattern Learning — improves over time
- Successful patterns stored and reused
- Next phase execution is smarter than the last
```

### 6. Post-Execution Verification

GSD already has verification (`/gsd:verify-work`). With swarm:

```
After all teammates finish:
1. Lead runs /gsd:verify-work (goal-backward verification)
2. Spawn verification team:
   - Teammate: integration-checker (do all pieces connect?)
   - Teammate: test-runner (do all tests pass?)
   - Teammate: code-reviewer (quality, security, conventions)
3. If issues found → spawn fix teammates
4. Final commit + phase transition
```

---

## When to Use What

| Situation | Approach |
|-----------|----------|
| Simple bug fix | Single session (no swarm) |
| Single plan phase | Single session + subagents |
| Multi-plan phase (2-3 plans) | Agent Teams (Mode 1) |
| Large phase (4+ plans) | Agent Teams + Ruflo (Mode 2) |
| Cross-cutting refactor | Agent Teams + Ruflo + queen validation |
| Research / investigation | Agent Teams (3-5 researchers) |
| Ad-hoc task (outside GSD) | Ruflo standalone (Mode 3) |
| Codebase audit | Ruflo star topology (5+ specialists) |
| Competing debug hypotheses | Agent Teams (5 investigators, debate pattern) |

---

## Configuration for Maximum Power

### .planning/config.json
```json
{
  "mode": "yolo",
  "granularity": "standard",
  "parallelization": true,
  "commit_docs": true,
  "model_profile": "quality",
  "workflow": {
    "research": false,
    "plan_check": true,
    "verifier": true,
    "nyquist_validation": true,
    "_auto_chain_active": true
  },
  "swarm": {
    "enabled": true,
    "default_topology": "hierarchical",
    "max_teammates": 5,
    "queen_validation": true,
    "wasm_boost": true,
    "viking_context": true,
    "ruflo_memory": true
  }
}
```

### ~/.claude/settings.json (already configured)
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

---

## Token Cost Awareness

| Mode | Token Multiplier | When Worth It |
|------|-----------------|---------------|
| Single session | 1x | Simple tasks, single-file changes |
| 3 subagents | ~2x | Quick parallel research |
| 3 teammates | ~3-4x | Multi-plan phases, needs coordination |
| 5 teammates + ruflo | ~5-7x | Large phases, quality-critical work |
| Full swarm (8+ agents) | ~8-10x | Major milestones, cross-cutting refactors |

**Rule of thumb:** If the phase has N independent plans, N teammates is worth it. If plans have many dependencies, fewer teammates + sequential is cheaper.

---

## Quick Reference Prompts

### Start a GSD phase with agent team
```
/gsd:execute-phase N

Use agent teams for parallel execution. Spawn one teammate per plan.
Each teammate: viking_search for context, work in own worktree,
commit atomically. Require plan approval for shared-file changes.
```

### Start a GSD phase with full swarm
```
/gsd:execute-phase N

Deploy ruflo swarm, hierarchical topology, queen coordinator.
Wave 1: research (viking + codebase). Wave 2: implement (one per plan).
Wave 3: verify (tester + reviewer). WASM boost for simple transforms.
Queen validates before merge.
```

### Ad-hoc swarm (no GSD)
```
Create an agent team with 4 teammates to [task].
Teammate 1: [specific role + files]
Teammate 2: [specific role + files]
Teammate 3: [specific role + files]
Teammate 4: [synthesizer/reviewer]
All teammates: use viking_search before starting for project context.
```

---

## Files Created by Swarm

| File/Dir | Created By | gitignore? |
|----------|-----------|------------|
| `.swarm/memory.db` | Ruflo memory init | YES |
| `.swarm/` | Ruflo | YES |
| `~/.claude/teams/` | Agent Teams | N/A (user home) |
| `~/.claude/tasks/` | Agent Teams | N/A (user home) |

---

*Created: 2026-03-16 | Systems: GSD + Agent Teams + Ruflo + Viking + brains-trust*
