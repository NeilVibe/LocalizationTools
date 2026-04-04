# Powering Up Claude Code

> Master list of power-ups: skills, plugins, MCP servers, and community frameworks.
> Goal: systematically upgrade Claude Code capabilities for our workflow.

---

## The Three Power-Up Types

| Type | What | How to Install | Scope |
|------|------|----------------|-------|
| **Skills** | Single `/command` workflows (`SKILL.md`) | Drop in `~/.claude/skills/` or `.claude/skills/` | Personal or project |
| **Plugins** | Bundles of skills + agents + hooks | `plugin.json` + marketplace | Cross-project |
| **MCP Servers** | External tool integrations via protocol | Configure in `claude_code_config.json` | Per-project or global |

---

## Current Power Level

### Installed Custom Skills (3 original + 11 community + 3 custom + 3 power = 20 total)

#### Original Project Skills
| Skill | Location | What It Does | Status |
|-------|----------|-------------|--------|
| `/build` | `~/.claude/skills/build/` | Commit + push + trigger CI + check status. Supports ALL 9 NewScript projects | DONE |
| `/sync` | `~/.claude/skills/sync/` | Dual push GitHub + Gitea with auto stop/start | DONE |
| `/versions` | `~/.claude/skills/versions/` | Show GitHub release versions table (datetime-based) | DONE |

#### Community Skills (installed 2026-03-13)
| Skill | Source | What It Does | Status |
|-------|--------|-------------|--------|
| **xlsx** | Anthropic official | Excel I/O: read, edit, create .xlsx/.xlsm/.csv, formulas, formatting | ACTIVE |
| **webapp-testing** | Anthropic official | Playwright server lifecycle, element discovery, screenshots | ACTIVE |
| **skill-creator** | Anthropic official | Meta-skill: create, test, evaluate, optimize new skills | ACTIVE |
| **playwright-pro** | alirezarezvani | 55+ Playwright templates, flaky test fixing, CI integration | ACTIVE |
| **code-reviewer** | alirezarezvani | PR analysis, security scanning, quality scoring (0-100) | ACTIVE |
| **self-improving-agent** | alirezarezvani | Auto-memory curation, pattern promotion, skill extraction | ACTIVE |
| **modern-python** | trailofbits | Modern Python tooling: uv, ruff, ty, pytest best practices | ACTIVE |
| **differential-review** | trailofbits | Security-focused diff review, blast radius, git history analysis | ACTIVE |

#### Custom Skills (built in-house)
| Skill | Location | What It Does | Status |
|-------|----------|-------------|--------|
| **xml-localization** | `~/.claude/skills/xml-localization/` | .loc.xml parsing, broken XML repair, Unicode safety, `<br/>` handling, lxml patterns | ACTIVE |
| **dev-server** | `~/.claude/skills/dev-server/` | Start/stop/fix DEV servers, WSL2 port forwarding, binding troubleshooting | ACTIVE |
| **debug-locanext** | `~/.claude/skills/debug-locanext/` | Full debug: DEV (Playwright) + Windows (CDP), GDP protocol, install/update, log analysis | ACTIVE |

#### Power Skills (installed 2026-03-13)
| Skill | Source | What It Does | Status |
|-------|--------|-------------|--------|
| **GSD** | [ctsstc/get-shit-done-skills](https://github.com/ctsstc/get-shit-done-skills) | Spec-driven dev, PLAN.md, atomic commits, fresh contexts, 30+ commands | ACTIVE |
| **UI UX PRO MAX** | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 67 UI styles, 96 palettes, 57 font pairings, design system generator | ACTIVE |
| **Nano Banana** | [devonjones/skill-nano-banana](https://github.com/devonjones/skill-nano-banana) | AI image generation via Google Gemini 3 Pro (text-to-image, editing, composition) | ACTIVE (needs Gemini quota) |

### Installed MCP Servers

| Server | Command | What It Does | Status |
|--------|---------|-------------|--------|
| **playwright** | `npx @playwright/mcp@latest --headless` | Browser automation: navigate, click, fill, screenshot, snapshot (25+ tools) | CONNECTED |
| **chrome-devtools** | `npx chrome-devtools-mcp@latest` | Chrome debugging: console logs, network, DOM inspection, performance | CONNECTED |
| **stitch** | `npx @_davideast/stitch-mcp@latest` | Google design-with-AI: generate HTML/CSS from descriptions | NEEDS AUTH |
| **Gmail** | Anthropic hosted | Email read/draft/search | CONNECTED |
| **Google Calendar** | Anthropic hosted | Calendar events/scheduling | CONNECTED |

### Installed Plugins

| Plugin | Marketplace | What It Does | Status |
|--------|-------------|-------------|--------|
| **skill-creator** | claude-plugins-official | Create/improve skills, run evals | ENABLED |
| **code-review** | claude-plugins-official | Multi-agent automated code review for PRs | ENABLED |
| **feature-dev** | claude-plugins-official | Full feature dev workflow: explore, design, quality review | ENABLED |
| **pr-review-toolkit** | claude-plugins-official | Specialized PR review agents (comments, tests, errors) | ENABLED |
| **security-guidance** | claude-plugins-official | Security warnings when editing sensitive files | ENABLED |
| **hookify** | claude-plugins-official | Create hooks to enforce rules | ENABLED |
| **code-simplifier** | claude-plugins-official | Simplify/refine code for clarity | ENABLED |
| **superpowers** | claude-plugins-official | TDD enforcement, brainstorming, 7-phase dev workflow, 20+ skills | ENABLED |

### Marketplaces

| Marketplace | Source | Status |
|-------------|--------|--------|
| **claude-plugins-official** | anthropics/claude-plugins-official | ACTIVE |
| **superpowers-dev** | obra/superpowers-marketplace | ACTIVE |

### Existing Capabilities (Built-In)

| Capability | How | Power Level |
|------------|-----|-------------|
| **Parallel agents** | Up to 5 concurrent subagents (PRXR review, Explore, etc.) | Good |
| **Vision** | Read tool on screenshots/images | Basic |
| **13 specialized agents** | dev-tester, code-reviewer, gdp-debugger, ci-specialist, etc. | Strong |
| **Memory system** | Persistent file-based memory across sessions | Good |
| **PRXR protocol** | Plan + 5-agent review + execute + review | Strong |

---

## Power-Up Catalog

### HIGH PRIORITY — Evaluate & Install

#### GSD (Get Shit Done) — Spec-Driven Development
- **GitHub:** [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)
- **Multi-CLI fork:** [shoootyou/get-shit-done-multi](https://github.com/shoootyou/get-shit-done-multi)
- **Skills version:** [ctsstc/get-shit-done-skills](https://github.com/ctsstc/get-shit-done-skills)
- **What:** Meta-prompting + spec-driven development. Forces work into small, checkable PLAN.md files. Spawns fresh subagent contexts per task (clean 200K token window each). Atomic git commits per task.
- **Key features:**
  - Goal-backward planning — derives required truths from goals
  - PLAN.md as executable prompts
  - Fresh context per task (prevents context rot)
  - Automated phase verification
  - Parallel execution support
  - Codebase mapping
  - Enforceable atomic commits
- **Install:** `npx skills add https://github.com/ctsstc/get-shit-done-skills --skill gsd`
- **Why for us:** Our PRXR protocol does planning but doesn't enforce fresh contexts or atomic commits. GSD adds the execution discipline we lack.
- **Priority:** HIGH
- **Status:** INSTALLED (v1.22.4, `npx get-shit-done-cc --claude --global`)

#### Superpowers — TDD + Debugging Methodology
- **GitHub:** [obra/superpowers](https://github.com/obra/superpowers)
- **Marketplace:** [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace)
- **What:** Agentic skills framework + software dev methodology. Enforced TDD (red-green-refactor), 4-phase debugging, Socratic brainstorming before coding.
- **Key features:**
  - Enforced TDD: tests must fail before implementation
  - 4-phase debugging: investigate root cause before fixing
  - Brainstorming skill: refines requirements before coding
  - Subagent-driven development with built-in review
  - Auto-activating skills (trigger on context)
  - In official Anthropic marketplace (Jan 2026)
- **Install:** Already in marketplace as `superpowers-dev`. Install plugin: `/plugin install obra/superpowers`
- **Why for us:** Enforces discipline. Our current flow sometimes skips tests. Brainstorming would help before non-trivial features.
- **Priority:** HIGH
- **Status:** INSTALLED (`claude plugin install superpowers`)

#### Everything Claude Code (ECC) — Agent Harness + Security
- **GitHub:** [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code)
- **What:** Agent harness performance optimization. 9 agents, 11 skills, 11 commands, 10 hooks. Built at Cerebral Valley x Anthropic hackathon.
- **Key features:**
  - AgentShield security scanner — scans Claude Code config for vulnerabilities, misconfigs, injection risks
  - 1282 tests, 98% coverage, 102 static analysis rules
  - Hook reliability overhaul (session management)
  - Multi-platform: Claude Code, OpenCode, Cursor
  - Research-first development methodology
- **Install:** Plugin install from GitHub
- **Why for us:** AgentShield would catch config security issues. The hook system and session management could improve our agent workflows.
- **Priority:** HIGH
- **Status:** TO EVALUATE

#### VoltAgent 500+ — Curated Agent Skills
- **GitHub:** [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- **Subagents:** [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (100+ subagents)
- **What:** 500+ real-world agent skills from official dev teams (Anthropic, Google Labs, Vercel, Stripe, Cloudflare, Netlify, Trail of Bits, Sentry, Expo, Hugging Face) + community.
- **Key features:**
  - Official skills from leading teams (not AI-generated bulk)
  - Cross-framework: Claude Code, Codex, Gemini CLI, Cursor
  - 100+ specialized subagents (separate repo)
  - Categorized and curated
- **Install:** Cherry-pick individual SKILL.md files from repo
- **Why for us:** Browse for localization-relevant, Excel, testing, or CI skills. The subagents repo might have specialized debugging agents.
- **Priority:** HIGH (browse & cherry-pick)
- **Status:** TO EVALUATE

### MEDIUM PRIORITY

#### Skills (Community)

| Name | GitHub | What It Does | Priority | Status |
|------|--------|-------------|----------|--------|
| **Anthropic Official** | [anthropics/skills](https://github.com/anthropics/skills/) | Official skills from Anthropic | Medium | PARTIALLY INSTALLED |
| **Claude Code Skills** | [levnikolaevich/claude-code-skills](https://github.com/levnikolaevich/claude-code-skills) | Production-ready: research, code review, delivery workflow | Medium | TO EVALUATE |
| **180+ Skills** | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | Engineering, marketing, product, compliance | Medium | PARTIALLY INSTALLED |
| **UI UX Pro Max** | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 67 UI styles, 96 palettes. Design intelligence for Svelte/React/Vue | High | INSTALLED |

### LOW PRIORITY

| Name | GitHub | What It Does | Priority | Status |
|------|--------|-------------|----------|--------|
| **Nano Banana** | [devonjones/skill-nano-banana](https://github.com/devonjones/skill-nano-banana) | AI image generation via Google Gemini 3 Pro | Medium | INSTALLED (needs Gemini quota) |
| **Ralph** | [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) | Autonomous dev loop: continuous iterations until PRD complete | Low | SKIPPED |
| **Ruflo** | [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | Enterprise multi-agent swarm orchestration. 87+ MCP tools | Low | SKIPPED |

### MCP Servers

| Name | GitHub | What It Does | Priority | Status |
|------|--------|-------------|----------|--------|
| **Playwright MCP** | [@playwright/mcp](https://github.com/playwright-community/playwright-mcp) | Browser automation (25+ tools) | High | INSTALLED |
| **Chrome DevTools MCP** | [chrome-devtools-mcp](https://github.com/nichochar/chrome-devtools-mcp) | Chrome debugging | High | INSTALLED |
| **Google Stitch MCP** | [davideast/stitch-mcp](https://github.com/davideast/stitch-mcp) | Google design-with-AI | Medium | INSTALLED (needs auth) |

### Discovery Hubs

| Name | GitHub | What It Does |
|------|--------|-------------|
| **Awesome Claude Code** | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | Curated list of skills, hooks, slash commands, orchestrators, plugins |
| **LobeHub Skills Marketplace** | [lobehub.com/skills](https://lobehub.com/skills) | Browseable marketplace for Claude Code skills |
| **skills.sh** | [skills.sh](https://skills.sh) | Another skills registry, npm-style install |

---

## Custom Skills Roadmap

| Skill | What It Would Do | Status |
|-------|-----------------|--------|
| `/build` | Commit + push + trigger CI + check status — ALL 9 NewScript projects | DONE |
| `/sync` | Push to both GitHub + Gitea | DONE |
| `/versions` | Show GitHub release versions table | DONE |
| `/xlsx` | Excel I/O: read, edit, create, formulas, formatting | DONE (community) |
| `/webapp-testing` | Playwright server lifecycle + element discovery | DONE (community) |
| `/skill-creator` | Create, test, evaluate, optimize new skills | DONE (community) |
| `/playwright-pro` | 55+ Playwright templates, flaky test fixing | DONE (community) |
| `/code-reviewer` | PR analysis, security scanning, quality scoring | DONE (community) |
| `/self-improving-agent` | Auto-memory curation, pattern promotion | DONE (community) |
| `/modern-python` | uv, ruff, ty, pytest best practices | DONE (community) |
| `/differential-review` | Security-focused diff review, blast radius | DONE (community) |
| `/xml-localization` | .loc.xml parsing, repair, Unicode, br-tags, lxml | DONE (custom-built) |
| `/dev-server` | Start/stop/fix DEV servers, WSL2 port forwarding, binding | DONE (custom-built) |
| `/debug-locanext` | Full debug: DEV (Playwright) + Windows (CDP), GDP, logs, screenshots | DONE (custom-built) |
| `/gsd` | GSD spec-driven development — fresh contexts, atomic commits, PLAN.md | DONE |
| `/superpowers` | Enforced TDD, 4-phase debugging, brainstorming | DONE |
| `/ui-ux-pro-max` | 67 UI styles, 96 palettes, design system generator | DONE |
| `/nano-banana` | AI image generation via Gemini 3 Pro | DONE (needs quota) |
| `/prxr` | Full PRXR workflow: Plan + 5-agent review + fix + execute + review | EXISTS (upgrade planned) |

---

## GSD vs Superpowers vs ECC vs Our Current Setup

| Feature | Our Current | GSD | Superpowers | ECC |
|---------|-------------|-----|-------------|-----|
| **Planning** | PRXR (manual) | PLAN.md (spec-driven) | Brainstorming skill | Research-first |
| **Execution** | Single context | Fresh subagent per task | TDD-enforced | Agent harness |
| **Testing** | Ad-hoc Playwright | Verification phases | Red-green-refactor TDD | 1282 tests built-in |
| **Debugging** | GDP protocol | — | 4-phase methodology | — |
| **Security** | Manual review | — | — | AgentShield scanner |
| **Context rot** | Memory system | Fresh 200K per task | — | Session management |
| **Commits** | Manual | Atomic per task | Per TDD cycle | — |
| **Best for** | Review, debug | Large features | Quality enforcement | Security, config |

**Recommendation:** Install GSD for large features (spec-driven + fresh contexts). Install Superpowers for quality enforcement (TDD + debugging). Keep our custom skills for LocaNext-specific workflows. Evaluate ECC for AgentShield security scanning.

---

## Installation Notes

### Skills
```bash
# Personal skill (all projects)
mkdir -p ~/.claude/skills/my-skill
# Write SKILL.md with frontmatter + instructions

# Project skill (this repo only)
mkdir -p .claude/skills/my-skill

# From npm-style registry
npx skills add https://github.com/<user>/<repo> --skill <name>
```

### Plugins (Marketplace)
```bash
# Add marketplace
/plugin marketplace add <publisher>/<marketplace-name>

# Install plugin
/plugin install <publisher>/<plugin-name>
```

### MCP Servers
Add to `~/.claude/claude_code_config.json` or project `.claude/claude_code_config.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["server-package"]
    }
  }
}
```

---

## Evaluation Criteria

Before installing anything, check:
1. **Relevance** — Does it help our actual workflow (localization, XML, Excel, CI)?
2. **Context cost** — Skills load descriptions into every conversation. Too many = bloat.
3. **Quality** — Stars, tests, active maintenance?
4. **Security** — Does it run arbitrary code? MCP servers have full tool access.
5. **Overlap** — Do we already have something similar (agents, CLAUDE.md)?

---

## Power-Up Roadmap

### Phase 1 — Foundation (DONE)
- [x] `/build` skill — commit, push, trigger for all projects
- [x] `/sync` skill — dual push GitHub + Gitea
- [x] `/versions` skill — release version table
- [x] Playwright MCP — browser automation (headless, 25+ tools)
- [x] Chrome DevTools MCP — debugging/inspection
- [x] Stitch MCP — installed, needs Google Cloud auth
- [x] 7 official plugins — code-review, feature-dev, skill-creator, pr-review-toolkit, security-guidance, hookify, code-simplifier
- [x] Superpowers marketplace — added for future plugin discovery

### Phase 1.5 — Custom Debug Skills (DONE, 2026-03-13)
- [x] `/dev-server` skill — server management, WSL2 portproxy, binding
- [x] `/debug-locanext` skill — full GDP + Playwright + CDP + install/update workflow
- [x] 8 community skills installed (xlsx, webapp-testing, playwright-pro, etc.)

### Phase 2 — Power Tools (DONE, 2026-03-13)
- [x] **GSD v1.22.4** — spec-driven dev, 30+ commands, hooks configured
- [x] **Superpowers** — TDD enforcement, brainstorming, 7-phase workflow (plugin)
- [x] **UI UX PRO MAX** — 67 styles, 96 palettes, design system generator
- [x] **Nano Banana** — AI image gen via Gemini 3 Pro (needs API quota)
- [x] **Stitch MCP** — Google design-with-AI (needs Google Cloud auth)
- [ ] **Evaluate ECC** — AgentShield security scanner, agent harness
- [ ] **Browse VoltAgent 500+** — cherry-pick localization/testing/CI skills

### Phase 3 — Advanced
- [ ] Custom `/prxr` skill upgrade — integrate GSD + Superpowers patterns
- [ ] Evaluate OpenClaw Skills Registry (5,400+ skills via VoltAgent)
- [ ] n8n MCP — workflow automation (if needed)
- [ ] Obsidian Skills — vault management (if needed)

---

*Created: 2026-03-13. Updated: 2026-03-13 (Phase 2 complete — GSD, Superpowers, UI UX PRO MAX, Nano Banana, Stitch installed). Living document.*
