# Power Arsenal — Full Reference Guide

> Master documentation for all skills, plugins, MCP servers, agents, and workflows available in this project.

---

## 1. WORKFLOW ENGINES (When to use what)

### GSD (Get Shit Done)
**For:** Multi-phase projects with milestones, roadmaps, persistent state across sessions.

| Command | When to Use |
|---------|-------------|
| `/gsd:new-project` | Starting a brand new project from scratch |
| `/gsd:plan-phase` | Planning a specific phase with research + detailed PLAN.md |
| `/gsd:execute-phase` | Execute all plans with wave-based parallel agents |
| `/gsd:progress` | Check where we are, route to next action |
| `/gsd:quick` | Quick task with GSD guarantees but skip heavy planning |
| `/gsd:debug` | Systematic debugging with persistent state |
| `/gsd:verify-work` | Validate features through conversational UAT |
| `/gsd:map-codebase` | Parallel agents analyze codebase structure |
| `/gsd:pause-work` | Save context for resuming later |
| `/gsd:resume-work` | Resume with full context restoration |

**GSD creates:** `.planning/` directory with PROJECT.md, ROADMAP.md, phase plans, research docs.
**GSD agents:** Researchers, planners, executors, verifiers, integration checkers — all specialized.

### Superpowers
**For:** Single-session feature development with brainstorm → plan → execute → review cycle.

| Skill | When to Use |
|-------|-------------|
| `/brainstorm` | Before ANY creative work — explore ideas, generate spec |
| `/write-plan` | After spec approved — create implementation plan |
| `/execute-plan` | Execute plan in separate session with review checkpoints |
| `/subagent-driven-development` | Execute plan with parallel agents in CURRENT session |
| `/dispatching-parallel-agents` | 2+ independent tasks that need no shared state |
| `/code-review` | After completing work — verify quality |
| `/systematic-debugging` | Bug found — investigate before fixing |
| `/test-driven-development` | Write tests BEFORE implementation |
| `/verification-before-completion` | Before claiming "done" — run tests, verify |
| `/finishing-a-development-branch` | Decide how to integrate (merge, squash, PR) |
| `/using-git-worktrees` | Isolate feature work from main workspace |

### GSD vs Superpowers — Decision Matrix

| Scenario | Use |
|----------|-----|
| Multi-day project with phases | **GSD** |
| Single feature, one session | **Superpowers** |
| Need persistent state across sessions | **GSD** |
| Quick brainstorm → build → ship | **Superpowers** |
| Complex project with research needed | **GSD** |
| Landing page, one-off creation | **Superpowers** (or GSD:quick) |

---

## 2. DESIGN & UI SKILLS

### Impeccable (NEW — pbakaus/impeccable)
**The design quality enforcer.** 18 skills, 17 `/i-` commands. Curated anti-patterns for premium frontend design.

| Command | What It Does |
|---------|-------------|
| `/i-critique` | Tear apart current design — find every weakness |
| `/i-polish` | Refine to premium level (spacing, typography, consistency) |
| `/i-animate` | Add purposeful motion/animation |
| `/i-bolder` | Make design more daring, less AI-safe |
| `/i-colorize` | Fix/improve color system |
| `/i-distill` | Remove unnecessary elements — less is more |
| `/i-delight` | Add subtle delightful details |
| `/i-audit` | Full accessibility + quality audit |
| `/i-optimize` | Performance optimization |
| `/i-harden` | Production-readiness checks |
| `/i-normalize` | Consistency pass across all elements |
| `/i-clarify` | Improve information hierarchy |
| `/i-adapt` | Responsive/adaptive improvements |
| `/i-extract` | Extract reusable design patterns |
| `/i-quieter` | Tone down overdesign |
| `/i-frontend-design` | Core design skill (enhanced Anthropic frontend-design) |
| `/i-onboard` | Learn the design system |
| `/i-teach-impeccable` | Learn Impeccable commands |

**Killer combo for any UI work:** `/i-critique` → `/i-polish` → `/i-animate` → `/i-bolder`

### Core Design Skills

| Skill | Trigger | Power |
|-------|---------|-------|
| **ui-ux-pro-max** | UI/UX design tasks | 67 styles, 96 palettes, 57 font pairings, 25 charts, 13 stacks |
| **frontend-design** | Production UI code | Distinctive, production-grade frontend interfaces |
| **threejs-animation** | 3D, WebGL, animation | Keyframe, skeletal, morph targets, animation mixing |
| **award-winning-website** | Landing pages | GSAP scroll animations, 3D effects, video storytelling |
| **animated-component-libraries** | Motion components | Magic UI (150+ components), Framer Motion, GSAP |
| **frontend-magic-ui** | Magic UI specifics | Glassmorphism, spotlight, advanced effects |
| **canvas-design** | Algorithmic art | Procedural visuals in PNG/PDF |
| **algorithmic-art** | p5.js generative art | Seeded randomness, interactive parameters |
| **theme-factory** | Styling artifacts | Slides, docs, HTML pages, reportings |
| **brand-guidelines** | Anthropic branding | Official colors & typography |
| **web-artifacts-builder** | Multi-component web | Elaborate HTML artifacts |

---

## 3. CODE & ARCHITECTURE SKILLS

| Skill | Trigger |
|-------|---------|
| **typescript-pro** | Advanced TS type systems, branded types |
| **python-pro** | Python 3.11+ type safety, async, error handling |
| **modern-python** | uv, ruff, ty tooling setup |
| **fastapi-expert** | FastAPI + Pydantic V2 APIs |
| **architecture-designer** | High-level system architecture |
| **api-designer** | REST/GraphQL API design, OpenAPI specs |
| **websocket-engineer** | Real-time WebSocket/Socket.IO |
| **database-optimizer** | Query optimization, PostgreSQL/MySQL |
| **postgres-pro** | Advanced PostgreSQL features |
| **sql-expert** | SQL queries, schema design |
| **mcp-builder** | Create MCP servers |

---

## 4. QUALITY & SECURITY SKILLS

| Skill | Trigger |
|-------|---------|
| **code-reviewer** | PR complexity & risk analysis |
| **security-reviewer** | Vulnerability audit with severity ratings |
| **secure-code-guardian** | Auth, input validation, OWASP Top 10 |
| **differential-review** | Security-focused diff review |
| **test-master** | Test architecture, mocking strategies |
| **test-generator** | Auto-suggest tests for new code |
| **playwright-pro** | Production Playwright E2E tests |
| **webapp-testing** | Local web app testing with Playwright |

---

## 5. DOCUMENT & CONTENT SKILLS

| Skill | Trigger |
|-------|---------|
| **pdf** | Read/create/manipulate PDFs |
| **docx** | Word document creation/editing |
| **pptx** | PowerPoint creation/editing |
| **xlsx** | Spreadsheet I/O |
| **code-documenter** | Docstrings, OpenAPI, JSDoc |
| **doc-coauthoring** | Collaborative documentation workflow |
| **internal-comms** | Internal communications |

---

## 6. DEVOPS & CI/CD SKILLS

| Skill | Trigger |
|-------|---------|
| **devops-engineer** | Dockerfiles, K8s, Terraform, CI/CD |
| **github-expert** | GitHub Actions, automation |
| **git-commit-helper** | Conventional commit messages |
| **build** | LocaNext/NewScripts CI trigger |
| **dev-server** | LocaNext DEV server management |

---

## 7. IMAGE GENERATION

| Skill | Status | Power |
|-------|--------|-------|
| **nano-banana** | Needs GEMINI_API_KEY (quota exhausted, needs billing) | Gemini 3 Pro — text-to-image, editing, composition, 4K |

---

## 8. MCP SERVERS (External Tool Connections)

| Server | Status | What it Does |
|--------|--------|-------------|
| **dbhub** | Connected | Query PostgreSQL directly, inspect schema, run SQL |
| **playwright** | Connected | Browser automation, screenshots, testing |
| **chrome-devtools** | Connected | CDP for Windows app testing |
| **stitch** | Connected | Generate UI screens from text descriptions |
| **Gmail** | Connected | Read/send emails |
| **Google Calendar** | Connected | Calendar management |

---

## 9. AGENT TYPES (Subagents)

Agents are spawned via the `Agent` tool for parallel/specialized work.

| Agent Type | When to Use |
|------------|-------------|
| **general-purpose** | Complex multi-step tasks, research |
| **Explore** | Codebase exploration (quick/medium/thorough) |
| **Plan** | Architecture & implementation planning |
| **feature-dev:code-explorer** | Deep feature analysis, trace execution paths |
| **feature-dev:code-architect** | Design feature architecture with implementation blueprints |
| **feature-dev:code-reviewer** | Bug/security/quality review with confidence filtering |
| **pr-review-toolkit:silent-failure-hunter** | Find silent failures, bad error handling |
| **pr-review-toolkit:code-reviewer** | Style guide & best practice compliance |
| **pr-review-toolkit:comment-analyzer** | Comment accuracy & maintainability |
| **pr-review-toolkit:type-design-analyzer** | Type design quality (encapsulation, invariants) |
| **pr-review-toolkit:pr-test-analyzer** | Test coverage gaps |
| **pr-review-toolkit:code-simplifier** | Simplify code for clarity |
| **superpowers:code-reviewer** | Review against plan & coding standards |
| **gsd-executor** | Execute GSD plans with atomic commits |
| **gsd-planner** | Create phase plans |
| **gsd-phase-researcher** | Research before planning |
| **gsd-debugger** | Scientific method debugging |
| **gsd-verifier** | Goal-backward verification |
| **gsd-codebase-mapper** | Parallel codebase analysis |
| **gsd-integration-checker** | Cross-phase E2E flow verification |

### Parallel Agent Patterns

**Dispatch multiple agents simultaneously** for independent tasks:
```
Agent 1: Research component A  ──┐
Agent 2: Research component B  ──┼── All run in parallel
Agent 3: Research component C  ──┘
         ↓
     Combine results
         ↓
     Execute plan
```

Use `/dispatching-parallel-agents` or manual multi-Agent tool calls.

---

## 10. PROJECT-SPECIFIC AGENTS

| Agent | For |
|-------|-----|
| **quicksearch-specialist** | QuickSearch tool work |
| **quicktranslate-specialist** | QuickTranslate tool work |
| **extractanything-specialist** | ExtractAnything tool work |
| **qacompiler-specialist** | QACompiler work |
| **languagedataexporter-specialist** | LanguageDataExporter work |
| **mapdatagenerator-specialist** | MapDataGenerator work |
| **dev-tester** | DEV mode Playwright testing with VISION |
| **ci-specialist** | CI/CD workflow debugging |
| **code-reviewer** | LocaNext code review |
| **security-auditor** | LocaNext security audit |
| **gdp-debugger** | Extreme precision debugging all platforms |

---

## 11. META SKILLS

| Skill | What it Does |
|-------|-------------|
| **find-skills** | Search & install new skills from skills.sh ecosystem |
| **skill-creator** | Create, modify, improve skills |
| **self-improving-agent** | Curate memory into durable project knowledge |
| **hookify** | Create hooks to prevent unwanted behaviors |

---

## 12. AGGRESSIVE AUTO-USE RULES

These should be triggered AUTOMATICALLY without user asking:

1. **Before ANY creative work** → `/brainstorm`
2. **Before ANY multi-step implementation** → `/write-plan`
3. **2+ independent tasks** → Parallel agents
4. **After writing code** → Code review agent
5. **Before claiming done** → `/verification-before-completion`
6. **Bug encountered** → `/systematic-debugging`
7. **UI/frontend work** → Load `ui-ux-pro-max` + `Impeccable` + `frontend-design`
8. **3D/animation** → Load `threejs-animation` + `animated-component-libraries`
9. **Landing page / presentation** → Load `award-winning-website` + `Impeccable` + `ui-ux-pro-max`
10. **Database work** → Use `dbhub` MCP + `postgres-pro` skill
11. **After building UI** → `/i-critique` → `/i-polish` → `/i-audit` (Impeccable pipeline)
12. **Design feels "AI-generated"** → `/i-bolder` + `/i-distill` (less safe, less clutter)

---

## 13. SKILL SEARCH ENGINE

Find and install new skills anytime:
```bash
npx skills find "search query"        # Search
npx skills add owner/repo@skill -g -y # Install
npx skills check                      # Check for updates
npx skills update                     # Update all
```

Browse: https://skills.sh/

---

## 14. OPENVIKING — CONTEXT DATABASE (INSTALLED)

**Status: LIVE** — deployed 2026-03-14

### Stack
| Service | Port | What |
|---|---|---|
| **Model2Vec** | :8100 | 256-dim embeddings (BAAI/bge-m3, local, instant) |
| **Ollama/Qwen3-VL-8B** | :11434 | VLM for document understanding (RTX 4070 Ti, 97% DocVQA) |
| **OpenViking** | :1933 | Context database, semantic search, filesystem paradigm |

### Commands
```bash
~/.openviking/start_viking.sh    # Start full stack
~/.openviking/stop_viking.sh     # Stop everything
curl http://localhost:1933/docs   # Swagger UI
```

### Config
- `~/.openviking/ov.conf` — server + embedding + VLM config
- `~/.openviking/ovcli.conf` — CLI config
- `~/.openviking/model2vec_server/server.py` — embedding API

### Key API Endpoints
- `POST /api/v1/resources` — index documents
- `POST /api/v1/search/search` — semantic search
- `GET /api/v1/fs/ls` — browse filesystem
- `GET /api/v1/content/read` — read content

### Remaining Setup
- [ ] Add as MCP server in Claude Code
- [ ] Index project docs (CLAUDE.md, architecture, roadmap)
- [ ] Wire into GSD research/planning agents
- [ ] Create `/viking` convenience skill

---

## 14b. DEEP RESEARCH SKILL (INSTALLED)

**Status: INSTALLED** — `~/.agents/skills/deep-research/` (needs session restart to activate)
**Source:** `199-biotechnologies/claude-deep-research-skill` (2K installs, most popular)
**Cost:** Free — uses WebSearch + Agent tools only

8-phase pipeline: SCOPE → PLAN → RETRIEVE → TRIANGULATE → SYNTHESIZE → CRITIQUE → REFINE → PACKAGE

Modes: Quick (2-5 min) | Standard (5-10 min) | Deep (10-20 min) | UltraDeep (20-45 min)

---

## 14c. EXPLORED — FUTURE POWER-UPS

### PromptFoo (promptfoo/promptfoo)
**What:** LLM evaluation & red-teaming framework. Test prompts, agents, RAG systems.
**How it helps us:** Could eval/test AI translation prompts for quality, compare different LLM providers for translation tasks.
**Status:** Useful if we expand AI translation features.

---

## 15. SYNERGY ARCHITECTURE — MAXIMUM POWER

How all the systems fuse together for different task types:

### Landing Page / Presentation Work
```
ui-ux-pro-max + Impeccable + award-winning-website + threejs-animation
     ↓ critique → polish → animate → bolder
     ↓ GSAP scroll + Three.js particles + glassmorphism
```

### LocaNext Feature Development
```
Deep Research (web research on approach/tech)
     ↓ feeds into
GSD:plan-phase → Superpowers:write-plan → Superpowers:subagent-driven-development
     ↓ Viking: query past decisions, architecture context, similar bugs
     ↓ parallel agents: implementer + spec-reviewer + code-reviewer
     ↓ Impeccable: /i-critique → /i-polish (for UI components)
     ↓ test-master + playwright-pro (for testing)
     ↓ GSD:verify-work → finishing-a-development-branch
     ↓ Viking: index phase learnings for future sessions
```

### Bug Hunting
```
GDP (Granular Debug Protocol) + systematic-debugging + gdp-debugger agent
     ↓ dev-tester agent (Playwright screenshots, VISION)
     ↓ pr-review-toolkit:silent-failure-hunter
```

### NewScripts Tool Development
```
Specialist agent (quicktranslate/qacompiler/etc.) + GSD:quick
     ↓ modern-python + python-pro
     ↓ test-generator → code-reviewer
     ↓ build skill → ci-specialist
```

### Design Review Pipeline
```
/i-critique (find weaknesses)
     ↓ /i-clarify (fix hierarchy)
     ↓ /i-colorize (fix colors)
     ↓ /i-animate (add motion)
     ↓ /i-polish (final refinement)
     ↓ /i-audit (accessibility check)
     ↓ /i-harden (production-ready)
```

### Full Project Lifecycle (MAXIMUM POWER)
```
Deep Research → thorough web research on domain/tech
     ↓
GSD:new-project → GSD:plan-phase → GSD:execute-phase
     ↓ Viking: index all .planning/ docs, research, roadmap
     ↓ Each phase: query Viking for relevant past context
     ↓ Each phase: Superpowers:subagent-driven-development
     ↓ Each task: implementer → spec-review → code-review
     ↓ UI tasks: + Impeccable pipeline
     ↓ GSD:verify-work → Viking: index phase learnings
     ↓ GSD:complete-milestone
     ↓ Viking: accumulated knowledge persists across ALL sessions
```

### The Power Loop
```
Session 1: Research + Plan + Execute → Viking indexes everything
Session 2: Viking recalls context → Continue seamlessly → Index more
Session 3: Viking knows full project history → Faster, smarter decisions
     ...
Session N: Zero context loss. Full project memory. Maximum velocity.
```

---

*Last updated: 2026-03-14*
