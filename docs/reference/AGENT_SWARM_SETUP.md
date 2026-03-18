# Agent Swarm Setup Guide

> **Goal:** Enable maximum multi-agent power in our Claude Code environment.
> **Three layers:** Native Agent Teams (Top 1) + Sub-Agent Patterns Skill (Top 2) + Ruflo (Top 4).

---

## Architecture Overview

```
Layer 3: RUFLO (Enterprise Orchestration)
  - 60+ specialized agents, self-learning, WASM booster
  - Queen/Worker hierarchy, anti-drift, shared memory
  - MCP integration (175+ tools injected into Claude Code)
  |
Layer 2: SUB-AGENT PATTERNS SKILL (Knowledge Layer)
  - Teaches Claude Code advanced delegation patterns
  - Fan-out, pipeline, self-organizing swarm patterns
  - Built-in + custom agent type awareness
  |
Layer 1: NATIVE AGENT TEAMS (Foundation)
  - Official Anthropic experimental feature
  - TeammateTool (13 operations), shared task list, messaging
  - Git worktree isolation per teammate
  - 3-5 teammates recommended, each = full Claude Code instance
```

---

## Phase 1: Native Agent Teams (Foundation)

### What It Is
Official Claude Code feature. One session = team lead. Spawns N teammates, each a full Claude Code instance with own context window, own git worktree, shared task list, and inter-agent messaging.

### Prerequisites
- Claude Code v2.1.32+
- Claude Opus 4.6 access (Pro or Max plan)
- Optional: tmux for split-pane visibility (`sudo apt install tmux`)

### Enable

**Option A — settings.json (persistent, recommended):**
```bash
# Find your settings file
cat ~/.claude/settings.json
```

Add to `~/.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

**Option B — shell environment (session only):**
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Verify
After enabling, start Claude Code. You should be able to say:
```
Create an agent team with 3 teammates to research X, Y, Z
```
If Claude creates the team, it's working.

### Display Modes

| Mode | Config | When |
|------|--------|------|
| **in-process** | Default outside tmux | All teammates in main terminal, Shift+Down to cycle |
| **split-pane** | `"teammateMode": "tmux"` | Each teammate gets own tmux pane |

Set in `~/.claude/settings.json`:
```json
{
  "teammateMode": "in-process"
}
```

Or per-session: `claude --teammate-mode in-process`

### How Teams Work

```
YOU ──→ TEAM LEAD (your main Claude session)
            ├── creates shared task list
            ├── spawns teammates (each = separate Claude Code instance)
            ├── assigns/delegates tasks
            └── synthesizes results

TEAMMATE A ──→ owns files in own git worktree
TEAMMATE B ──→ messages A directly (no lead relay needed)
TEAMMATE C ──→ self-claims next unblocked task when idle
```

**Key operations:**
- **Shift+Down** — cycle between teammates (in-process mode)
- **Ctrl+T** — toggle task list view
- Messages auto-deliver between agents
- Tasks have dependency tracking (blocked/unblocked)

### Task System
- Lead creates tasks, teammates self-claim
- Tasks: pending → in_progress → completed
- Dependencies: `blockedBy` arrays auto-unblock when upstream completes
- File locking prevents race conditions on claim

### Best Practices
1. **3-5 teammates** optimal (diminishing returns beyond)
2. **5-6 tasks per teammate** keeps everyone productive
3. **Each teammate owns different files** — avoid same-file edits
4. **Give enough context in spawn prompt** — teammates don't inherit lead's conversation
5. **Require plan approval for risky work**: "Require plan approval before changes"
6. **Always clean up**: ask lead to shut down teammates, then "Clean up the team"

### Limitations
- No session resumption (`/resume` doesn't restore teammates)
- One team per session
- No nested teams (teammates can't spawn sub-teams)
- Lead is fixed for session lifetime
- Split panes not supported in VS Code terminal

### Use Case Patterns

**Parallel Code Review:**
```
Create an agent team to review the auth module. Spawn 3 reviewers:
- Security focused
- Performance focused
- Test coverage focused
Have them each review and report findings.
```

**Competing Hypotheses (Debug):**
```
Users report X crash. Spawn 5 teammates to investigate different hypotheses.
Have them message each other to disprove theories. Update findings when
consensus emerges.
```

**Parallel Feature Dev:**
```
Create a team: one teammate for backend API, one for Svelte UI, one for tests.
Each owns their own files. Coordinate via task list.
```

---

## Phase 2: Sub-Agent Patterns Skill (Knowledge Layer)

### What It Is
A skill that teaches Claude Code advanced agent delegation patterns — fan-out, pipeline, self-organizing swarm, research-then-implement. Makes the Agent tool and TeammateTool much more effective.

### Install
```bash
npx skills add jezweb/claude-skills@sub-agent-patterns -g -y
```

### What It Adds

**Orchestration patterns:**

| Pattern | Description |
|---------|-------------|
| **Parallel Specialists** | Spawn N reviewers simultaneously for concurrent analysis |
| **Pipeline** | Sequential stages with task dependencies that auto-unblock |
| **Self-Organizing Swarm** | Workers continuously poll and claim available tasks |
| **Research → Implementation** | Separate investigation from execution phases |

**Agent type awareness:**
- Built-in: Explore (read-only), Bash (commands), Plan (architecture), general-purpose (full)
- Plugin: security-sentinel, performance-oracle, best-practices-researcher, git-history-analyzer
- Custom agent creation patterns

**Key knowledge:**
- When to use subagents vs teammates
- Context window management (keep main context clean)
- Task decomposition strategies
- Message routing (targeted `write` over expensive `broadcast`)
- Graceful shutdown sequences

### How It Combines with Agent Teams
The skill doesn't add new tools — it teaches Claude Code **how to use existing tools better**. After installing:
- Claude Code will decompose tasks more effectively
- Agent teams will be organized using proven patterns
- Task dependencies will be structured optimally
- Communication between teammates will be more focused

---

## Phase 3: Ruflo (Enterprise Power Layer)

### What It Is
Full enterprise orchestration platform. 60+ agent types, self-learning neural routing, WASM code transforms, queen/worker hierarchy, shared vector memory. Integrates as an MCP server — injects 175+ tools directly into Claude Code.

### Prerequisites
- Node.js 18+ (LTS recommended, 20+ for full features)
- npm 9+ (`npm install -g npm@latest`)
- Claude Code installed globally (`npm install -g @anthropic-ai/claude-code`)

### Install

**Option A — One-line full install (recommended):**
```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ruvnet/claude-flow@main/scripts/install.sh | bash -s -- --full
```
This installs Ruflo + configures MCP + runs diagnostics.

**Option B — Step by step:**
```bash
npm install -g ruflo@latest
npx ruflo@latest init --wizard    # Interactive setup
```

**Option C — Docker:**
```bash
docker pull ruvnet/claude-flow:v2-alpha
docker run -it --name claude-flow \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ruvnet/claude-flow:v2-alpha
```

### MCP Integration (Critical Step)
This is what connects Ruflo to Claude Code — injects 175+ tools:
```bash
claude mcp add ruflo -- npx -y ruflo@latest mcp start
```

Verify:
```bash
claude mcp list          # Should show "ruflo"
claude-flow mcp tools list  # List all available tools
```

### Initialize Memory & Intelligence
```bash
claude-flow memory init
claude-flow config set memory.retention 30d
claude-flow config set memory.maxSize 1GB
```

### Start Background Daemon
```bash
npx ruflo@latest daemon start
# Runs 12 workers, auto-triggers on file changes and patterns
```

### Enable Hooks (Optional but Powerful)
```bash
claude-flow hooks enable --all
claude-flow hooks set post-edit "prettier --write {file}"
claude-flow hooks set post-task "claude-flow metrics collect"
```

### What It Adds

**Agent Types (8 core + specializations):**

| Agent | Role |
|-------|------|
| **Coordinator** | Orchestrates multi-agent workflows, task distribution |
| **Researcher** | Gathers info, analyzes requirements |
| **Coder** | Implements features, writes production code |
| **Analyst** | Analyzes data patterns, provides insights |
| **Architect** | Designs system architecture, technical solutions |
| **Tester** | Creates and executes tests for QA |
| **Reviewer** | Evaluates code quality, security, standards |
| **Optimizer** | Enhances performance and efficiency |

**Agent Hierarchy (Queen/Worker):**
```
QUEEN (3 types: Strategic, Tactical, Adaptive)
  └── validates outputs, prevents drift, enforces alignment
WORKERS (8 types with specialized domains)
  └── Coder, Tester, Reviewer, Architect, Security, Docs, Researcher, Optimizer
CONSENSUS
  └── Byzantine fault-tolerant (2/3 majority required)
```

**Team Size Templates:**

| Project Size | Team Composition |
|-------------|-----------------|
| Small feature | 1 coder + 1 tester + 1 reviewer |
| Medium project | 1 coordinator + 2-3 coders + 1 architect + 1-2 testers + 1 reviewer |
| Large project | Multiple coordinators + 5+ coders + 2+ architects + 3+ testers + 2+ reviewers |

**Task Routing (Automatic):**

| Complexity | Routed To | Latency |
|-----------|-----------|---------|
| Simple (var rename, add types) | Agent Booster (WASM) | <1ms |
| Medium (refactor, review) | Haiku/Sonnet | ~500ms |
| Complex (architecture, full feature) | Opus + full swarm | 2-5s |

**Swarm Topologies:**

| Topology | When | Agents |
|----------|------|--------|
| **Hierarchical** | Default. Queen validates, prevents drift. | 6-8 |
| **Mesh** | Peer-to-peer. Agents talk directly. Max flexibility. | Any |
| **Ring** | Sequential pipeline. Each agent passes to next. | Linear chain |
| **Star** | Central hub routes all. Coordination-heavy tasks. | Hub + spokes |

**Execution Strategies (5 modes):**

| Mode | Description |
|------|-------------|
| **Parallel** | Independent tasks run simultaneously (max 8 concurrent) |
| **Sequential** | Tasks in order with dependency management |
| **Adaptive** | Strategy adjusts based on available resources |
| **Balanced** | Load distributed evenly across agents |
| **Stream-Chained** | Real-time output piping between agents (40-60% less latency) |

**Parallel Processing Patterns:**

| Pattern | How |
|---------|-----|
| **Map-Reduce** | Distribute data across agents, aggregate results |
| **Pipeline** | Chain operations, each stage runs in parallel |
| **Fork-Join** | Split work, process independently, synchronize at convergence |

**Intelligence Layer (RuVector):**
- SONA self-optimization (<0.05ms adaptation)
- HNSW vector search (sub-millisecond retrieval)
- Pattern learning from every execution
- 9 reinforcement learning algorithms
- EWC++ prevents catastrophic forgetting
- Flash Attention (2-7x speedup)

**Cost Optimization:**
- WASM Booster: 352x faster than LLM for code transforms
- Token reduction: 30-50% via cached reasoning retrieval
- Extends Claude Code usage by up to 250%
- WASM transforms: `var-to-const`, `add-types`, `async-await`, `add-error-handling`, `add-logging`, `remove-console`

### Ruflo Key Commands
```bash
# === Setup ===
ruflo init --wizard                                  # Interactive setup
claude mcp add ruflo -- npx -y ruflo@latest mcp start  # MCP integration
claude-flow memory init                              # Initialize memory

# === Agents ===
claude-flow agent spawn --type coder --name "Auth-Developer"   # Spawn agent
claude-flow agent list                               # View active agents
claude-flow agent info <agent-id>                    # Agent details
claude-flow agent hierarchy                          # View org structure
claude-flow agent ecosystem                          # Full agent network
claude-flow agent terminate <agent-id>               # Stop agent

# === Swarm ===
claude-flow hive init --topology hierarchical --agents 5  # Init swarm
claude-flow hive status                              # Swarm status
npx claude-flow task orchestrate --strategy parallel --max-concurrent 8
npx claude-flow swarm init --topology star --agents "coder:5,tester:3"

# === Intelligence ===
ruflo hooks intelligence --status                    # Check AI layer
claude-flow memory usage --action store --key workflow-state

# === Daemon ===
npx ruflo@latest daemon start                        # Start 12 workers
npx ruflo@latest daemon stop                         # Stop workers

# === Debug ===
claude-flow mcp tools list                           # List all MCP tools
claude-flow sparc modes                              # Available SPARC modes
```

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Permission errors | `sudo chown -R $(whoami) ~/.npm` |
| Memory DB errors | `claude-flow memory reset --force && claude-flow memory init` |
| MCP server issues | `claude-flow mcp restart` |
| Agent stuck | `claude-flow agent terminate <id>` then respawn |

---

## Anti-Patterns (Things That Waste Tokens)

| Anti-Pattern | Why It Fails | Do Instead |
|-------------|-------------|------------|
| Lead implements instead of delegating | Defeats the purpose of having a team | Restrict lead to coordination-only |
| "Build me an app" as single task | Too vague, teammates flail | Break into specific, file-scoped tasks |
| Using teams for sequential work | Coordination overhead > benefit | Use single session or subagents |
| Broadcasting every message | Token cost scales with team size | Use targeted `write` to specific teammates |
| Same-file edits by multiple teammates | Overwrites, merge conflicts | Each teammate owns distinct files |
| Letting team run unattended too long | Wasted effort on wrong approaches | Check in, redirect, steer |
| Over-engineering simple tasks | 5 agents for a config change | Match agent count to actual complexity |
| Not giving context in spawn prompts | Teammates don't inherit lead's conversation | Include specific task details, file paths, constraints |

---

## Deployment Plan

### Step 1: Enable Native Agent Teams

```bash
# 1a. Edit settings
nano ~/.claude/settings.json
# Add: "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" }

# 1b. Install tmux for split-pane visibility
sudo apt install tmux

# 1c. Verify Claude Code version
claude --version   # Must be v2.1.32+
```

**Test — Simple research team:**
```
Create an agent team with 3 teammates to investigate our server/ directory.
Teammate 1: catalog all API endpoints and their auth requirements.
Teammate 2: find all database queries and check for N+1 problems.
Teammate 3: identify all WebSocket events and their handlers.
Synthesize findings into a summary.
```
Pass if: 3 teammates spawn, work independently, report back to lead.

### Step 2: Install Sub-Agent Patterns

```bash
npx skills add jezweb/claude-skills@sub-agent-patterns -g -y
```
No config needed — it's a knowledge layer that improves how Claude Code delegates.

**Test — Pattern-driven team:**
```
Using the parallel specialists pattern, create an agent team to review
the locaNext/src/lib/ directory. Spawn specialists for:
- Component architecture patterns
- State management approaches
- Error handling coverage
Have each specialist produce a focused report.
```
Pass if: Claude uses structured delegation patterns from the skill.

### Step 3: Test Layers 1+2 Combined

```
Create an agent team using the research-then-implementation pattern.
Phase 1 (research): 3 teammates each investigate a different aspect of
  our XML parsing in server/api/ — correctness, performance, edge cases.
Phase 2 (implementation): based on research findings, spawn 2 implementation
  teammates to fix any issues found. Each owns different files.
Require plan approval before any implementation changes.
```
Pass if: research phase completes before implementation begins, plan approval works.

### Step 4: Install Ruflo

```bash
# 4a. Install
curl -fsSL https://cdn.jsdelivr.net/gh/ruvnet/claude-flow@main/scripts/install.sh | bash -s -- --full

# 4b. If curl install fails, manual:
npm install -g ruflo@latest
npx ruflo@latest init --wizard

# 4c. MCP integration
claude mcp add ruflo -- npx -y ruflo@latest mcp start
claude mcp list   # Verify ruflo appears

# 4d. Memory system
claude-flow memory init
claude-flow config set memory.retention 30d
claude-flow config set memory.maxSize 1GB

# 4e. Start daemon
npx ruflo@latest daemon start

# 4f. Verify everything
claude-flow hive status
ruflo hooks intelligence --status
claude-flow mcp tools list
```

**Test — Ruflo standalone:**
```bash
claude-flow agent spawn --type researcher --name "API-Researcher"
claude-flow agent spawn --type coder --name "API-Developer"
claude-flow agent list
claude-flow agent hierarchy
```

### Step 5: Test All Three Layers Combined (MAXIMUM POWER)

```
Deploy a ruflo swarm with hierarchical topology for a full analysis of
the LocaNext codebase. Configure:

Queen: Strategic coordinator for the entire operation.

Wave 1 (Research — parallel):
  - Researcher: map all server/ API endpoints and data flows
  - Researcher: analyze all locaNext/src/ Svelte components and state
  - Analyst: identify performance bottlenecks across frontend and backend

Wave 2 (Planning — after research completes):
  - Architect: design improvements based on research findings

Wave 3 (Review — parallel):
  - Reviewer: security audit of proposed changes
  - Tester: test coverage gap analysis

Use stream-chained execution so downstream agents start as soon as
upstream results are available. Route simple code transforms through
WASM booster. Store all findings in shared memory for cross-agent access.
```
Pass if: hierarchical swarm deploys, waves execute in order, queen validates outputs.

---

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Agent Teams enabled | `grep AGENT_TEAMS ~/.claude/settings.json` | `"1"` |
| Claude Code version | `claude --version` | v2.1.32+ |
| Sub-agent skill installed | `ls ~/.claude/skills/` | sub-agent-patterns present |
| Ruflo installed | `ruflo --version` or `npx ruflo@latest --version` | Version number |
| Ruflo MCP connected | `claude mcp list` | ruflo in list |
| Ruflo daemon running | `ruflo hooks intelligence --status` | Status output |
| tmux available (optional) | `which tmux` | Path to tmux |

---

## Risk Notes

| Risk | Mitigation |
|------|------------|
| **Token cost explosion** | Each teammate = separate Claude instance. Start with 3, scale up. |
| **Same-file conflicts** | Assign each teammate different files/directories. |
| **No session resume** | Teams don't survive `/resume`. Finish work before ending session. |
| **Ruflo daemon resources** | 12 background workers. Stop with `ruflo daemon stop` when not needed. |
| **Experimental feature** | Agent teams may change/break between Claude Code versions. |
| **Orphaned tmux sessions** | `tmux ls` + `tmux kill-session -t <name>` to clean up. |

---

## Quick Reference

```bash
# === ENABLE ===
# settings.json: "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
npx skills add jezweb/claude-skills@sub-agent-patterns -g -y
npm install -g ruflo@latest
claude mcp add ruflo -- npx -y ruflo@latest mcp start
claude-flow memory init
npx ruflo@latest daemon start

# === USE ===
# In Claude Code, just describe what you want:
# "Create an agent team with 4 teammates to..."
# "Use ruflo swarm to..."

# === CLEANUP ===
# "Clean up the team" (in Claude Code)
npx ruflo@latest daemon stop
tmux kill-server  # if orphaned sessions
```

---

## How Layers Interact

```
┌─────────────────────────────────────────────────────┐
│                  YOU (prompt)                        │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│          CLAUDE CODE (Team Lead)                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  Sub-Agent Patterns Skill (Layer 2)          │    │
│  │  = Knowledge of HOW to decompose & delegate  │    │
│  └─────────────────────────────────────────────┘    │
│                  │                                   │
│  ┌───────────────▼─────────────────────────────┐    │
│  │  Native Agent Teams (Layer 1)                │    │
│  │  = TeammateTool, shared tasks, messaging     │    │
│  │  = Each teammate = full Claude Code instance │    │
│  └───────────────┬─────────────────────────────┘    │
│                  │                                   │
│  ┌───────────────▼─────────────────────────────┐    │
│  │  Ruflo MCP Server (Layer 3)                  │    │
│  │  = 175+ tools injected into each agent       │    │
│  │  = Queen/Worker hierarchy                    │    │
│  │  = WASM booster for simple transforms        │    │
│  │  = Shared vector memory across all agents    │    │
│  │  = Self-learning from every execution        │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Layer 1 alone:** Good. Native parallel agents with messaging.
**Layer 1 + 2:** Better. Smarter decomposition, proven orchestration patterns.
**Layer 1 + 2 + 3:** Maximum. Self-learning, queen validation, WASM boost, shared memory, 60+ agent types.

---

## Sources

- [Official Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams)
- [Addy Osmani — Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/)
- [Sub-Agent Patterns Skill](https://skills.sh/jezweb/claude-skills/sub-agent-patterns)
- [Ruflo GitHub](https://github.com/ruvnet/ruflo)
- [Ruflo Installation Guide](https://github.com/ruvnet/ruflo/wiki/Installation-Guide)
- [Ruflo Agent Usage Guide](https://github.com/ruvnet/ruflo/wiki/Agent-Usage-Guide)
- [Ruflo Workflow Orchestration](https://github.com/ruvnet/ruflo/wiki/Workflow-Orchestration)
- [Swarm Orchestration Skill (Gist)](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)

---

*Created: 2026-03-16 | Layers: Native Teams + Sub-Agent Patterns + Ruflo*
