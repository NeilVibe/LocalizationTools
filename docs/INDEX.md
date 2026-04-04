# Documentation Index

> **Single source of truth for all LocaNext documentation.**
> Active docs: 63 files. Archive: 217 files (historical, don't load unless asked).

---

## Quick Links

| Need | Location |
|------|----------|
| **Current bugs** | [current/ISSUES_TO_FIX.md](current/ISSUES_TO_FIX.md) |
| **Session context** | [current/SESSION_CONTEXT.md](current/SESSION_CONTEXT.md) |
| **Architecture** | [architecture/ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) |
| **Offline/Online mode** | [architecture/OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) |
| **Debug protocol (GDP)** | [protocols/GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) |
| **How to build** | [reference/cicd/HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md) |
| **CI/CD troubleshoot** | [reference/cicd/TROUBLESHOOTING.md](reference/cicd/TROUBLESHOOTING.md) |
| **Enterprise deploy** | [reference/enterprise/HUB.md](reference/enterprise/HUB.md) |
| **Claude memory** | `~/.claude/projects/.../memory/MEMORY.md` (see Memory System below) |

---

## CI/CD Workflows

| Project | CI Platform | Trigger | Push To |
|---------|-------------|---------|---------|
| **LocaNext** | GitHub Actions | `BUILD_TRIGGER.txt` ("Build Admin" / "Build User") | GitHub + Gitea |
| **QACompilerNEW** | GitHub Actions | `QACOMPILER_BUILD.txt` | GitHub only |
| **ExtractAnything** | GitHub Actions | Starts with "Build" | GitHub only |
| **LanguageDataExporter** | GitHub Actions | `LANGUAGEDATAEXPORTER_BUILD.txt` | GitHub only |

**Full docs:** [reference/cicd/HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md)

---

## Architecture (11 docs)

| Doc | Description |
|-----|-------------|
| [ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) | System overview — 99% client, 1% DB sync |
| [OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) | Offline/Online design |
| [CLIENT_SERVER_PROCESSING.md](architecture/CLIENT_SERVER_PROCESSING.md) | What runs where |
| [DB_ABSTRACTION_LAYER.md](architecture/DB_ABSTRACTION_LAYER.md) | Factory pattern, 3-mode |
| [PLATFORM_PATTERN.md](architecture/PLATFORM_PATTERN.md) | Platform abstraction pattern |
| [TM_HIERARCHY_PLAN.md](architecture/TM_HIERARCHY_PLAN.md) | TM folder system |
| [BACKEND_PRINCIPLES.md](architecture/BACKEND_PRINCIPLES.md) | Backend design patterns |
| [ASYNC_PATTERNS.md](architecture/ASYNC_PATTERNS.md) | Async code patterns |
| [STATS_DASHBOARD_SPEC.md](architecture/STATS_DASHBOARD_SPEC.md) | Admin dashboard stats specification |

---

## Protocols (7 docs)

| Protocol | Purpose |
|----------|---------|
| [GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) | GDP — microscopic logging for bug hunting |
| [PRXR.md](protocols/PRXR.md) | Plan-Review-Execute-Review for non-trivial changes |
| [QUICK_DEBUG_REFERENCE.md](protocols/QUICK_DEBUG_REFERENCE.md) | Common debug scenarios |
| [AGENT_PROTOCOL.md](protocols/AGENT_PROTOCOL.md) | Unified agent guide: types, conductor, parallel, debug, case studies |

---

## Reference

### CI/CD (7 docs)
[HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md) | [TROUBLESHOOTING.md](reference/cicd/TROUBLESHOOTING.md) | [CI_CD_HUB.md](reference/cicd/CI_CD_HUB.md) | [PIPELINE_ARCHITECTURE.md](reference/cicd/PIPELINE_ARCHITECTURE.md) | [VERSION_SYSTEM.md](reference/cicd/VERSION_SYSTEM.md) | [RUNNER_SERVICE_SETUP.md](reference/cicd/RUNNER_SERVICE_SETUP.md) | [GITEA_SAFETY_PROTOCOL.md](reference/cicd/GITEA_SAFETY_PROTOCOL.md)

### Enterprise (14 docs)
Full deployment guide: [reference/enterprise/HUB.md](reference/enterprise/HUB.md)

### Security (3 docs)
[SECURITY_STATE.md](reference/security/SECURITY_STATE.md) | [SECURITY_HARDENING.md](reference/security/SECURITY_HARDENING.md) | [SECURITY_AND_LOGGING.md](reference/security/SECURITY_AND_LOGGING.md)

### Other
[AI_POWER_STACK.md](reference/AI_POWER_STACK.md) — What's installed (models, MCP servers)
[AGENT_SWARM_SETUP.md](reference/AGENT_SWARM_SETUP.md) — Agent swarm setup guide
[SWARM_GSD_INTEGRATION.md](reference/SWARM_GSD_INTEGRATION.md) — GSD + Swarm wiring
[TRIBUNAL_MCP.md](reference/TRIBUNAL_MCP.md) — Tribunal usage

---

## Security (4 docs — all in reference/security/)

See [reference/security/](reference/security/) above. Includes LAN_SERVER_SECURITY_KR.md (Korean).

---

## Presentations (12 files)

Executive demo materials and architecture diagrams. Generator scripts + output PDFs.

| File | Description |
|------|-------------|
| `presentations/LocaNext_Executive_Overview.pdf` | Executive overview deck |
| `presentations/LocaNext_Backend_Architecture.pdf` | Backend architecture diagram |
| `presentations/LocaNext_Database_Architecture.pdf` | Database architecture diagram |
| `presentations/LocaNext_Security_Architecture.pdf` | Security architecture diagram |
| `presentations/how-to-code-with-ai-flowchart.html` | AI coding flowchart (EN) |
| `presentations/how-to-code-with-ai-flowchart-kr.html` | AI coding flowchart (KR) |
| `presentations/generate_*.py` | PDF generator scripts (6 files) |

---

## Guides (9 docs)

| Guide | Description |
|-------|-------------|
| [LDM_GUIDE.md](guides/tools/LDM_GUIDE.md) | Language Data Manager |
| [LDM_TEXT_SEARCH.md](guides/tools/LDM_TEXT_SEARCH.md) | LDM text search feature |
| [XLSTRANSFER_GUIDE.md](guides/tools/XLSTRANSFER_GUIDE.md) | XLSTransfer tool |
| [QUICK_START_GUIDE.md](guides/getting-started/QUICK_START_GUIDE.md) | Getting started |
| [ADMIN_SETUP.md](guides/getting-started/ADMIN_SETUP.md) | Admin setup |
| [PROJECT_STRUCTURE.md](guides/getting-started/PROJECT_STRUCTURE.md) | Project structure |

---

## Memory System

Claude's persistent memory lives at `~/.claude/projects/-home-neil1988-LocalizationTools/memory/`.

```
memory/
├── MEMORY.md          (70 lines — trunk index, always loaded)
├── user/profile.md    (who Neil is, preferences)
├── rules/             (6 domain files + checklist — behavioral rules)
│   ├── _INDEX.md      (quick-scan checklist)
│   ├── coding.md, builds.md, ui.md, workflow.md, tools.md, testing.md
├── active/            (current work — phase 113, Z-Image, build types)
│   └── _INDEX.md      (status, blockers, next steps)
├── reference/         (stable facts — architecture, security, XML patterns)
└── archive/           (compressed history — phases 93-112, NewScripts)
```

**How it works:**
- MEMORY.md loads every session (57 lines, fully fits in context)
- Rules _INDEX.md is a pre-action checklist
- All 25 files indexed in Viking for semantic search
- Before any action: scan relevant _INDEX.md + `viking_search` memories

---

## Claude Agents

Custom agents in `.claude/agents/`:

| Agent | Purpose |
|-------|---------|
| ci-specialist | CI/CD workflows, build triggers |
| qacompiler-specialist | QACompilerNEW project |
| extractanything-specialist | ExtractAnything project |
| quicktranslate-specialist | QuickTranslate project |
| gdp-debugger | Granular Debug Protocol |
| dev-tester | DEV mode testing (localhost:5173) |
| code-reviewer | Code review |
| security-auditor | Security scanning |
| quicksearch-specialist | QuickSearch tool |
| mapdatagenerator-specialist | MapDataGenerator reference |
| languagedataexporter-specialist | LanguageDataExporter |

---

## Related (Outside docs/)

| Location | Purpose |
|----------|---------|
| `CLAUDE.md` | Claude navigation hub (project root) |
| Memory `active/_INDEX.md` | Current phase, blockers, next steps |
| `PARADIGMS.md` | Development paradigms |
| `.claude/agents/` | Custom Claude agents |
| `testing_toolkit/` | Testing protocols and tools |
| `scripts/` | Shell wrappers and utilities |
| `RFC/NewScripts/` | Mini-projects (QACompiler, ExtractAnything, etc.) |

---

*Last updated: 2026-04-04*
