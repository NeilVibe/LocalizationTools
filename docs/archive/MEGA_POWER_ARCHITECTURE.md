# Mega Power Architecture — Full System Reference

> **The 5-System Stack:** GSD (Brain) + Queen/Hive (Muscle) + MCP Trio (Thinking+Memory+Viking) + Autoresearch (Ideas) + Ralph (Persistence)
> **Last updated:** 2026-03-29

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEGA POWER STACK                              │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   GSD    │  │ Queen/Hive   │  │ Autoresearch│  │  Ralph  │ │
│  │  (Brain) │  │  (Muscle)    │  │   (Ideas)   │  │ (Loop)  │ │
│  │          │  │              │  │             │  │         │ │
│  │ 38 cmds  │  │ 62 workers   │  │ Competing   │  │ Stop    │ │
│  │ 15 agents│  │ 175+ tools   │  │ approaches  │  │ hook    │ │
│  │ 3 hooks  │  │ WASM boost   │  │ Converge    │  │ loop    │ │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘  └────┬────┘ │
│       │               │                 │               │      │
│  ┌────┴───────────────┴─────────────────┴───────────────┴────┐ │
│  │                MCP TRIO (MANDATORY — every task)           │ │
│  │  sequential-thinking │ memory (knowledge graph) │ Viking   │ │
│  │  Think first → Remember → Search context → Act            ��� │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    MCP LAYER (11 servers, 300+ tools)      │ │
│  │  tribunal │ context7 │ exa │ firecrawl │ fal-ai           │ │
│  │  Playwright │ Chrome DevTools │ Ruflo │ dbhub             │ │
│  │  Gmail │ Google Calendar                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 SKILLS LAYER (111+ skills)                 │ │
│  │  15 UI/UX │ 10 Frontend │ 5 Backend │ 5 Review │ 4 Test   │ │
│  │  6 Anim   │ 3 Database  │ 3 Data    │ 4 DevOps │ 4 Research│ │
│  │  + Pocock (17) + ECC (40+) + SPARC (15+)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 RULES LAYER (always active)                │ │
│  │  power-stack.md │ screenshot-directory.md │ skill-tier-list│ │
│  │  korean-regex.md │ playwright-efficiency.md                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: GSD — The Brain (WHAT to do)

**Purpose:** Structured project management — phases, plans, requirements, verification.
**Install:** `~/.claude/skills/gsd/` + `~/.claude/commands/gsd/` (38 commands) + `~/.claude/agents/gsd-*.md` (15 agents)

### Key Commands

| Command | Purpose |
|---------|---------|
| `/gsd:new-project` | Initialize project: questioning → research → requirements → roadmap |
| `/gsd:discuss-phase N` | Gather implementation decisions → CONTEXT.md |
| `/gsd:plan-phase N` | Create executable PLAN.md files with verify loop |
| `/gsd:execute-phase N` | Wave-based parallel execution |
| `/gsd:verify-work N` | Conversational UAT validation |
| `/gsd:progress` | Show current position, route to next action |
| `/gsd:autonomous` | Run all remaining phases: discuss → plan → execute per phase |
| `/gsd:quick` | Small tasks with GSD guarantees but skip optional agents |
| `/gsd:do "text"` | Route natural language to the right GSD command |
| `/gsd:debug` | Systematic hypothesis-driven debugging |

### Pipeline

```
discuss → research → plan → verify-plan → execute → verify-work
   │          │         │        │            │          │
CONTEXT.md  RESEARCH.md PLAN.md  checker    SUMMARY.md  UAT.md
```

### File Structure

```
.planning/
  PROJECT.md          — Vision, core value, requirements
  ROADMAP.md          — Milestones + phases + plans
  STATE.md            — Live position, progress, decisions
  REQUIREMENTS.md     — Categorized requirements with checkboxes
  MILESTONES.md       — Shipped milestone summaries
  DEFERRED_IDEAS.md   — Future ideas (indexed by Viking)
  config.json         — Workflow toggles
  phases/XX-name/     — Per-phase: CONTEXT, PLAN, RESEARCH, SUMMARY, VERIFICATION
```

### This Project's Stats
16 milestones (v1.0→v14.0), 95+ phases, 168+ plans shipped. v14.0 near-complete.

---

## Layer 2: Queen/Hive/Ruflo — The Muscle (HOW to do it)

**Purpose:** Parallel multi-agent execution, shared memory, quality validation.
**Install:** Ruflo MCP server (175+ tools), `hive-mind_init` at session start.

### Architecture

```
Queen (coordinator)
  ├── Scout workers (lightweight recon)
  ├── Specialist workers (deep expertise)
  └── General workers (implementation)
      │
      └── All share: Vector memory (HNSW), Consensus (Byzantine), Broadcasts
```

### Key Capabilities

| Capability | How |
|-----------|-----|
| **Parallel research** | Spawn 3-5 scouts, each explores different aspect |
| **Parallel execution** | 1 agent per GSD plan, own worktree |
| **Shared memory** | HNSW vector index, sub-ms semantic search |
| **Quality gate** | Queen validates between waves |
| **Self-learning** | Patterns extracted, confidence-scored, temporally decayed |
| **WASM boost** | 352x faster for simple code transforms (<1ms) |

### Scaling

Automatic. No config. Just `hive-mind_spawn(count=N)`. This session grew to 62 workers.

### Worker Types

| Type | Use For |
|------|---------|
| **scout** | Fast reads, Viking searches, file discovery |
| **specialist** | Security audit, architecture review, deep analysis |
| **worker** | Feature coding, test writing, refactoring |

### Integration with GSD

| GSD Phase Size | Hive Mode |
|----------------|-----------|
| 1 plan | Single session, no swarm |
| 2-3 plans | 1 teammate per plan (parallel) |
| 4+ plans | Teammates + Queen validation + WASM |
| Research | 3-5 researcher scouts in parallel |
| Bug hunt | 3-5 competing hypothesis scouts |

---

## Layer 3: Autoresearch — The Ideas (WHICH approach)

**Purpose:** Competing prototypes, benchmark, converge on proven approach before coding.
**Install:** `~/.claude/skills/autoresearch/` (Karpathy-inspired)

### How It Differs from Regular Research

| Regular Research | Autoresearch |
|-----------------|-------------|
| Each agent explores different AREA | Each agent tries different SOLUTION |
| Results combined additively | Results COMPETE — best wins |
| Output is knowledge | Output is PROVEN approach with evidence |

### The Loop

```
modify → verify → keep/discard → repeat
```

### The Full Protocol

1. **CONTEXT** — Viking search + Ruflo memory
2. **RESEARCH SWARM** — 5+ agents explore problem space
3. **AUTORESEARCH** — Competing approaches: prototype, benchmark, compare
4. **CONVERGE** — Synthesize ONE proven approach
5. **PLAN** — GSD plan based on proven approach (not guesses)
6. **EXECUTE** — Code the proven approach
7. **REVIEW SWARM** — 5+ review agents check quality
8. **VERIFY** — GSD verifier confirms goals met

### When to Use

- Multiple valid approaches exist
- Architecture decisions
- Performance-critical paths
- Novel features with no existing pattern
- **NOT** for: trivial tasks, single-file changes, well-understood patterns

---

## Layer 4: Ralph Wiggum — The Persistence (KEEP GOING)

**Purpose:** Autonomous iteration loop — Claude keeps working until done or max iterations.
**Install:** `ralph-wiggum@anthropics/claude-code` (user-level plugin)

### How It Works

```
User: /ralph-loop "Fix all issues" --max-iterations 30 --completion-promise "ALL_FIXED"
  │
  ├── Iteration 1: Claude works, tries to exit
  │   └── Stop hook BLOCKS exit, feeds SAME PROMPT back
  ├── Iteration 2: Claude sees previous work in files, continues
  │   └── Stop hook BLOCKS again
  ├── ...
  └── Iteration N: Claude outputs <promise>ALL_FIXED</promise>
      └── Stop hook ALLOWS exit — loop complete
```

### Parameters

| Parameter | Purpose |
|-----------|---------|
| `--max-iterations N` | Safety limit (0 = unlimited) |
| `--completion-promise "TEXT"` | Exact string that signals genuine completion |

### When to Use

- Fix-all-issues loops (fix → test → see failures → fix more)
- Polish passes (iterate until it looks right)
- Verification cycles (keep testing until all green)
- Tasks with **automatic verification** (tests, linters)

---

## Layer 5: Skills — The Expertise (111+ skills)

### By Domain

| Domain | Count | Key Skills |
|--------|-------|------------|
| **UI/UX Polish** | 15 | bolder, polish, critique, colorize, delight, adapt, distill, harden, audit |
| **Frontend** | 10 | svelte-code-writer, svelte5-best-practices, frontend-design, ui-ux-pro-max |
| **Animation** | 6 | animate, gsap-master, threejs-animation, animated-component-libraries |
| **Backend** | 5 | python-pro, fastapi-expert, modern-python, websocket-engineer |
| **Database** | 3 | postgres-pro, database-optimizer, sql-expert |
| **Data Formats** | 3 | xml-localization, xlsx, docx, pdf, pptx |
| **Review** | 5 | code-reviewer, differential-review, security-reviewer, secure-code-guardian |
| **Testing** | 4 | test-master, playwright-skill, tdd (Pocock), test-generator |
| **Research** | 4 | deep-research, autoresearch, brains-trust, llm-integration |
| **DevOps** | 4 | build, github-expert, devops-engineer, debug-locanext |
| **Planning** | 5 | grill-me, write-a-prd, prd-to-issues, prd-to-plan, feature-forge |
| **Meta/Self** | 4 | self-improving-agent, skill-creator, write-a-skill, find-skills |
| **SPARC** | 15+ | sparc (orchestrator), code, debug, tdd, architect, etc. |
| **ECC** | 40+ | plan, tdd, e2e, security-review, claw, learn-eval, etc. |

### Skill Layering Order

```
CONTEXT → BRAINSTORM → DOMAIN SKILL → IMPLEMENT → REVIEW → VERIFY
(Viking)  (superpowers) (specialist)    (code)     (agents)  (test)
```

### Superpowers (Meta-Skills)

| Superpower | When |
|-----------|------|
| `brainstorming` | Before any creative/feature work |
| `writing-plans` | Single-session planning |
| `executing-plans` | Structured plan execution |
| `systematic-debugging` | Before proposing bug fixes |
| `test-driven-development` | Before writing implementation |
| `verification-before-completion` | Before claiming work is done |

---

## Layer 6: MCP Servers — The Tools (11 servers, 300+ tools)

### MANDATORY TRIO (use EVERY task, EVERY session)

| # | Server | Package | Purpose | USE WHEN |
|---|--------|---------|---------|----------|
| 1 | **sequential-thinking** | `@modelcontextprotocol/server-sequential-thinking` | Step-by-step reasoning with revision and branching | **ALWAYS before code changes, debugging, planning** |
| 2 | **memory** | `@modelcontextprotocol/server-memory` | Knowledge graph persistent memory (entities, relations, observations) | **Cross-session knowledge, pattern storage** |
| 3 | **openviking** | Local Python MCP (:1933) | Semantic search over 727+ project doc embeddings | **Project knowledge lookup — ALWAYS check first** |

**Trio Workflow:** `Think (sequential) → Remember (memory) → Search context (Viking) → Act`

### SPECIALIST SERVERS

| # | Server | Tools | Purpose | USE WHEN |
|---|--------|-------|---------|----------|
| 4 | **tribunal** | 3 | Expert matching across 111 skills, persona debates | Decision-making, reviews, architecture choices |
| 5 | **context7** | 2 | Library/framework documentation lookup | Any framework/API question (React, FastAPI, etc.) |
| 6 | **exa** | 3 | Neural web search (semantic, not keyword) | External research, finding examples |
| 7 | **firecrawl** | 10+ | Web scraping, crawling, extraction | Deep web content analysis |
| 8 | **fal-ai** | 12 | 600+ AI models (image, video, audio generation) | Media generation ($0.04-0.29/use) |

### TESTING & DEBUGGING SERVERS

| # | Server | Tools | Purpose | USE WHEN |
|---|--------|-------|---------|----------|
| 9 | **Playwright** | 20+ | Browser automation (DEV at localhost:5173) | UI testing, screenshots, form filling |
| 10 | **Chrome DevTools** | 25+ | CDP-based Windows app debugging | Installed app testing, console/network inspection |
| 11 | **dbhub** | 2 | Direct SQL database access | Quick DB queries |

### PRODUCTIVITY SERVERS

| # | Server | Tools | Purpose |
|---|--------|-------|---------|
| 12 | **Gmail** | 6 | Email management |
| 13 | **Google Calendar** | 8 | Scheduling |

**Key principle:** Every agent (teammates, subagents, Ruflo workers) inherits ALL MCP servers automatically. A 5-agent team = 5x the tools.

### MCP Usage Protocol

```
EVERY TASK:
  1. sequential-thinking → reason about approach (BEFORE touching code)
  2. memory search_nodes → check if we've seen this before
  3. viking_search → find relevant project context
  4. [work the task]
  5. memory add_observations → store what we learned
  6. sequential-thinking → verify our work makes sense

EVERY SESSION START:
  1. Ping all 3 mandatory MCPs (sequential-thinking, memory, viking)
  2. memory read_graph → load cross-session knowledge
  3. Viking status check

EVERY SESSION END:
  1. memory create_entities/add_observations → persist key learnings
  2. self-improving-agent skill → curate memory
```

---

## Layer 7: Rules — The Guardrails (always active)

| Rule | Enforces |
|------|----------|
| `power-stack.md` | Maximum tool usage, playbooks, anti-lazy patterns, parallelization |
| `screenshot-directory.md` | Playwright saves to `screenshots/` not project root |

---

## How the 4 Systems Combine

### Pattern 1: Standard Phase (most common)
```
GSD plan → Hive scouts research → GSD execute (Hive parallel) → Hive review
```

### Pattern 2: Novel Feature
```
Autoresearch (competing prototypes) → Converge → GSD plan → Hive execute
```

### Pattern 3: Fix-Everything Loop
```
Ralph wraps: Hive scouts find issues → fix → test → repeat until green
```

### Pattern 4: Full Stack (complex + unknown)
```
GSD structure → Autoresearch (find approach) → GSD re-plan →
Hive execute (parallel) → Ralph verification loop → Hive review
```

### Why Each Is Necessary

| Without... | You Get... |
|-----------|-----------|
| GSD | No structure, agents work on undefined goals |
| Hive | Sequential execution, slow, no parallelism |
| Autoresearch | First approach used (may be wrong) |
| Ralph | Human must manually re-invoke after each attempt |

---

## Quick Reference: Task → Stack

| Task | Minimum Stack |
|------|--------------|
| Quick fix | GSD:quick + relevant skill |
| Standard feature | GSD + Hive (1 teammate per plan) |
| Complex feature | GSD + Hive + Autoresearch |
| Fix-all loop | GSD + Hive + Ralph |
| Unknown territory | GSD + Hive + Autoresearch + Ralph (all 4) |
| Code review | Hive (3+ review scouts in parallel) |
| Research | Hive scouts + Viking + deep-research skill |
| Bug investigation | GSD:debug + Hive (competing hypotheses) |

---

*Architecture documented by the Hive — 2026-03-18, updated 2026-03-29*
*11 MCP servers, 111+ skills, 300+ tools, 15+ GSD agents*
