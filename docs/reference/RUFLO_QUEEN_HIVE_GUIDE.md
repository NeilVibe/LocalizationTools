# Ruflo Queen + Hive — Practical Guide

> **One doc. Everything you need.** Replaces scattered references across memory files + 3 other docs.
>
> **Key insight:** Ruflo = coordination layer (state, memory, consensus). Claude Agent tool = execution layer (code, files, tests). Always pair them.

---

## Quick Start (Copy-Paste Pattern)

```
# 1. Init swarm + queen
mcp__ruflo__swarm_init(topology="hierarchical", maxAgents=8)
mcp__ruflo__hive-mind_init(queenId="queen-coordinator", topology="hierarchical")

# 2. Spawn workers in hive
mcp__ruflo__hive-mind_spawn(count=4, prefix="worker", role="specialist")

# 3. Create tracked tasks
mcp__ruflo__task_create(type="research", description="...", assignTo=["worker-1"], priority="high")
mcp__ruflo__task_create(type="feature", description="...", assignTo=["worker-2"])

# 4. Orchestrate strategy
mcp__ruflo__coordination_orchestrate(task="Polish map", strategy="parallel", agents=["worker-1","worker-2"])

# 5. Execute (Claude Agent tool does actual work — in parallel)
Agent(description="task 1", subagent_type="...", prompt="...")
Agent(description="task 2", subagent_type="...", prompt="...")

# 6. On each return → store findings + complete task
mcp__ruflo__memory_store(key="task1-result", namespace="project", value={...})
mcp__ruflo__task_complete(taskId="...", result={...})

# 7. Consensus + broadcast
mcp__ruflo__hive-mind_consensus(action="propose", type="design", value="chosen approach")
mcp__ruflo__hive-mind_broadcast(message="Decision: ...", fromId="queen", priority="high")

# 8. Shutdown
mcp__ruflo__swarm_shutdown(graceful=true)
```

---

## When to Use What

| Situation | Tool | Why |
|-----------|------|-----|
| Single file edit | Direct Edit | No overhead needed |
| 2-3 parallel searches | Agent tool (parallel) | Lightweight, no swarm |
| 4+ parallel agents | **Ruflo + Agent tool** | Track tasks, store findings |
| Multi-session project | **Ruflo memory** | Findings persist across sessions |
| Architecture decisions | **Ruflo consensus** | Propose/vote/broadcast |
| GSD phase (2-3 plans) | Agent Teams | 1 teammate per plan |
| GSD phase (4+ plans) | **Agent Teams + Ruflo** | Queen validates, WASM boost |
| Bug investigation | Agent tool (5 competing) | Ruflo tracks hypotheses |
| Autoresearch loop | Autoresearch skill | No swarm needed (single agent) |

---

## Ruflo MCP Tools Reference

### Swarm Lifecycle
| Tool | Purpose |
|------|---------|
| `swarm_init(topology, maxAgents)` | Start swarm. Topologies: hierarchical, mesh, ring, star |
| `swarm_status()` | Check swarm health |
| `swarm_shutdown(graceful=true)` | Clean shutdown |

### Queen + Hive-Mind
| Tool | Purpose |
|------|---------|
| `hive-mind_init(queenId, topology)` | Create queen coordinator |
| `hive-mind_spawn(count, prefix, role)` | Spawn workers into hive |
| `hive-mind_status()` | Queen/worker status |
| `hive-mind_memory(action, key, value)` | Shared hive memory (get/set/list) |
| `hive-mind_consensus(action, type, value)` | Propose/vote on decisions |
| `hive-mind_broadcast(message, fromId, priority)` | Announce to all workers |

### Task Tracking
| Tool | Purpose |
|------|---------|
| `task_create(type, description, assignTo, priority)` | Create tracked task |
| `task_update(taskId, progress, status)` | Update progress (0-100) |
| `task_complete(taskId, result)` | Mark done with results |
| `task_assign(taskId, agentIds)` | Reassign task |
| `task_list()` | List all tasks |
| `task_status(taskId)` | Check single task |

### Persistent Memory (HNSW Vector Store)
| Tool | Purpose |
|------|---------|
| `memory_store(key, value, namespace, tags)` | Store with embedding |
| `memory_search(query, namespace, limit)` | Semantic search |
| `memory_retrieve(key, namespace)` | Get by key |
| `memory_delete(key, namespace)` | Remove entry |

### Coordination
| Tool | Purpose |
|------|---------|
| `coordination_orchestrate(task, strategy, agents)` | Set execution strategy |
| `coordination_sync()` | Synchronize agent state |
| `coordination_load_balance()` | Rebalance work |

### Agent Management
| Tool | Purpose |
|------|---------|
| `agent_spawn(agentType, task, model)` | Spawn with model routing |
| `agent_status(agentId)` | Check agent |
| `agent_health()` | Health check all agents |
| `agent_terminate(agentId)` | Stop agent |

---

## The Critical Rule

> **MCP coordinates. Agent tool executes. Always pair them in the same message.**

```
❌ WRONG: Only use Ruflo MCP tools (no actual work gets done)
❌ WRONG: Only use Agent tool (no tracking, no memory, no coordination)

✅ RIGHT: In the same message:
   1. mcp__ruflo__task_create(...)     ← track the work
   2. Agent(prompt="...", ...)          ← DO the work
   3. After return: task_complete(...)  ← record results
```

---

## Full Workflow Example: Map Polish Session

```
STEP 1: INIT
  swarm_init(topology="hierarchical", maxAgents=6)
  hive-mind_init(queenId="queen-map-polish", topology="hierarchical")

STEP 2: SPAWN WORKERS
  hive-mind_spawn(count=4, prefix="reviewer", role="specialist")

STEP 3: CREATE TASKS (one per review scope)
  task_create(type="review", description="Code quality review", assignTo=["reviewer-1"])
  task_create(type="review", description="UI/UX critique", assignTo=["reviewer-2"])
  task_create(type="review", description="Silent failure hunt", assignTo=["reviewer-3"])
  task_create(type="review", description="Code simplification", assignTo=["reviewer-4"])

STEP 4: ORCHESTRATE
  coordination_orchestrate(task="Review map changes", strategy="parallel",
    agents=["reviewer-1","reviewer-2","reviewer-3","reviewer-4"])

STEP 5: EXECUTE (4 parallel Agent calls in ONE message)
  Agent(subagent_type="feature-dev:code-reviewer", prompt="Review map code...")
  Agent(subagent_type="feature-dev:code-reviewer", prompt="UI/UX critique...")
  Agent(subagent_type="pr-review-toolkit:silent-failure-hunter", prompt="Hunt failures...")
  Agent(subagent_type="code-simplifier:code-simplifier", prompt="Simplify code...")

STEP 6: STORE FINDINGS (after agents return)
  memory_store(key="review-code", namespace="map-polish", value={issues: [...]})
  memory_store(key="review-uiux", namespace="map-polish", value={issues: [...]})
  memory_store(key="review-failures", namespace="map-polish", value={issues: [...]})
  memory_store(key="review-simplify", namespace="map-polish", value={changes: [...]})

STEP 7: COMPLETE TASKS
  task_complete(taskId="...", result={found: 6, fixed: 0})
  task_complete(taskId="...", result={found: 8, fixed: 0})
  ...

STEP 8: CONSENSUS (choose fix priority)
  hive-mind_consensus(action="propose", type="fix-plan",
    value="Fix 3 critical + 4 important issues first")

STEP 9: BROADCAST
  hive-mind_broadcast(message="Fixing 7 issues: rAF crash, SVG filter, D3 proxy...",
    fromId="queen-map-polish", priority="high")

STEP 10: FIX (create fix tasks + execute)
  task_create(type="bugfix", description="Fix rAF crash + container guard")
  Agent(prompt="Fix the rAF issue...")
  task_complete(...)

STEP 11: SHUTDOWN
  swarm_shutdown(graceful=true)
```

---

## GSD + Swarm Integration

| GSD Phase Type | Swarm Mode |
|---------------|------------|
| Simple (1 plan) | Single session, no swarm |
| Standard (2-3 plans) | Agent Teams: 1 teammate per plan |
| Large (4+ plans) | Agent Teams + Ruflo queen validation |
| Research phase | 3-5 researcher agents in parallel |
| Bug investigation | 3-5 competing hypothesis agents |

### GSD Prompt Template
```
/gsd:execute-phase N

Deploy ruflo swarm, hierarchical topology, queen coordinator.
Wave 1: research (viking_search + codebase). Wave 2: implement (one per plan).
Wave 3: verify (tester + reviewer). Queen validates before merge.
```

---

## Topologies

| Topology | Shape | Best For |
|----------|-------|----------|
| **Hierarchical** | Queen → Workers | Default. Quality gates, validation. |
| **Mesh** | All ↔ All | Peer research, brainstorming. |
| **Ring** | A → B → C → A | Sequential pipeline. |
| **Star** | Hub ↔ Spokes | Central coordinator, many specialists. |

---

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Only MCP calls (no Agent tool) | Always pair MCP + Agent in same message |
| 20+ agents | Max 8, batch if more needed |
| Vague task descriptions | Specific files, goals, constraints |
| Skip memory_store after work | Always store findings for future reference |
| Let agents run without tracking | task_create → task_update → task_complete |
| Same file in parallel agents | Each agent owns distinct files |
| Queen implements (should coordinate) | Queen validates, workers implement |

---

## Token Cost

| Mode | Cost Multiplier | When Worth It |
|------|----------------|---------------|
| Single session | 1x | Simple tasks |
| 3 parallel subagents | ~2x | Quick research |
| 4 agents + Ruflo | ~4-5x | Multi-plan phases |
| Full swarm (8 agents) | ~8-10x | Major milestones |

**Rule:** If phase has N independent plans, N agents is worth it.

---

## Supersedes

This guide consolidates and replaces:
- `docs/reference/AGENT_SWARM_SETUP.md` (setup instructions — keep for install steps)
- `docs/reference/SWARM_GSD_INTEGRATION.md` (GSD wiring — merged here)
- `docs/protocols/AGENT_ORCHESTRATION.md` (patterns — merged here)
- `memory/reference_multi_agent_systems.md` (overview — merged here)
- `memory/reference_ruflo_deep.md` (deep ref — merged here)

---

*Created: 2026-03-17 | Consolidated from 5 sources*
