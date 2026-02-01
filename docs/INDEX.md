# Documentation Index

> **Single source of truth for all LocaNext documentation.**

---

## Quick Links

| Need | Location |
|------|----------|
| **Current bugs/issues** | [current/ISSUES_TO_FIX.md](current/ISSUES_TO_FIX.md) |
| **Session context** | [current/SESSION_CONTEXT.md](current/SESSION_CONTEXT.md) |
| **System architecture** | [architecture/ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) |
| **Offline mode design** | [architecture/OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) |
| **Debug protocol (GDP)** | [protocols/GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) |
| **How to build** | [reference/cicd/HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md) |
| **CI/CD troubleshooting** | [reference/cicd/TROUBLESHOOTING.md](reference/cicd/TROUBLESHOOTING.md) |

---

## CI/CD Workflows (CRITICAL!)

| Project | CI Platform | Trigger File | Push To |
|---------|-------------|--------------|---------|
| **LocaNext** | Gitea Actions | `GITEA_TRIGGER.txt` | GitHub + Gitea |
| **LanguageDataExporter** | GitHub Actions | `LANGUAGEDATAEXPORTER_BUILD.txt` | GitHub only |
| **QACompilerNEW** | GitHub Actions | `QACOMPILER_BUILD.txt` | GitHub only |

**Full docs:** [reference/cicd/HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md)

---

## Claude Agents

Custom agents in `.claude/agents/`:

| Agent | Purpose |
|-------|---------|
| **ci-specialist** | CI/CD workflows, build triggers, release management |
| **languagedataexporter-specialist** | LanguageDataExporter project |
| **qacompiler-specialist** | QACompilerNEW project |
| **gdp-debugger** | Granular Debug Protocol for all debugging (frontend, backend, Windows) |
| **dev-tester** | DEV mode testing at localhost:5173 |
| **code-reviewer** | Code review for patterns/bugs |
| **security-auditor** | Security vulnerability scanning |
| **quicksearch-specialist** | QuickSearch tool specialist |

---

## Structure

```
docs/
├── INDEX.md              ← YOU ARE HERE
│
├── architecture/         # HOW THE SYSTEM WORKS
│   ├── ARCHITECTURE_SUMMARY.md    # Main architecture reference
│   ├── OFFLINE_ONLINE_MODE.md     # Offline/Online design
│   ├── TM_HIERARCHY_PLAN.md       # TM system design
│   └── ...
│
├── protocols/            # HOW TO DO THINGS (for Claude)
│   └── GRANULAR_DEBUG_PROTOCOL.md # GDP - microscopic logging
│
├── current/              # ACTIVE WORK
│   ├── ISSUES_TO_FIX.md          # Current bugs
│   └── SESSION_CONTEXT.md        # Session state
│
├── reference/            # STABLE REFERENCE DOCS
│   ├── enterprise/               # Enterprise deployment
│   ├── cicd/                     # CI/CD pipeline ← WORKFLOWS HERE
│   │   ├── HOW_TO_BUILD.md       # How to trigger builds
│   │   ├── TROUBLESHOOTING.md    # Debug CI issues
│   │   ├── CI_CD_HUB.md          # Pipeline overview
│   │   └── ...
│   ├── security/                 # Security docs
│   └── api/                      # API reference (empty - placeholder)
│
├── guides/               # USER GUIDES
│   ├── tools/                    # Tool guides (LDM, XLSTransfer)
│   └── getting-started/          # Onboarding
│
└── archive/              # OLD DOCS (kept for reference)
    └── ...
```

---

## Architecture

| Doc | Description |
|-----|-------------|
| [ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) | Complete system overview |
| [OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) | Offline/Online mode design |
| [OFFLINE_ONLINE_SYNC.md](architecture/OFFLINE_ONLINE_SYNC.md) | Sync mechanism |
| [TM_HIERARCHY_PLAN.md](architecture/TM_HIERARCHY_PLAN.md) | TM assignment system |
| [BACKEND_PRINCIPLES.md](architecture/BACKEND_PRINCIPLES.md) | Backend design patterns |
| [ASYNC_PATTERNS.md](architecture/ASYNC_PATTERNS.md) | Async code patterns |

---

## CI/CD Reference

| Doc | Description |
|-----|-------------|
| [HOW_TO_BUILD.md](reference/cicd/HOW_TO_BUILD.md) | **Start here** - Trigger builds for all projects |
| [CI_CD_HUB.md](reference/cicd/CI_CD_HUB.md) | Pipeline overview and architecture |
| [TROUBLESHOOTING.md](reference/cicd/TROUBLESHOOTING.md) | Debug CI failures |
| [PIPELINE_ARCHITECTURE.md](reference/cicd/PIPELINE_ARCHITECTURE.md) | Detailed pipeline design |
| [VERSION_SYSTEM.md](reference/cicd/VERSION_SYSTEM.md) | Version format (YY.MMDD.HHMM) |
| [RUNNER_SERVICE_SETUP.md](reference/cicd/RUNNER_SERVICE_SETUP.md) | Runner configuration |
| [GITEA_SAFETY_PROTOCOL.md](reference/cicd/GITEA_SAFETY_PROTOCOL.md) | Gitea CPU management |

---

## Protocols

| Protocol | Purpose |
|----------|---------|
| [GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) | GDP - Microscopic logging for bug hunting |
| [QUICK_DEBUG_REFERENCE.md](protocols/QUICK_DEBUG_REFERENCE.md) | Quick reference for common debug scenarios |
| [DEBUG_AND_SUBAGENTS.md](protocols/DEBUG_AND_SUBAGENTS.md) | Using subagents for parallel debugging |
| [PARALLEL_AGENT_PROTOCOL.md](protocols/PARALLEL_AGENT_PROTOCOL.md) | **NEW** - How to use agents in parallel |
| [AGENT_ORCHESTRATION.md](protocols/AGENT_ORCHESTRATION.md) | **NEW** - Conductor pattern for agent management |

**Agent Quick Reference** → [reference/AGENT_QUICK_REFERENCE.md](reference/AGENT_QUICK_REFERENCE.md)

**Testing protocols** → See `testing_toolkit/` at project root

---

## Reference

### Enterprise Deployment
See [reference/enterprise/](reference/enterprise/) for full deployment guide.

### Security
See [reference/security/](reference/security/) for security hardening.

---

## Guides

| Guide | Description |
|-------|-------------|
| [LDM_GUIDE.md](guides/tools/LDM_GUIDE.md) | Language Data Manager usage |
| [XLSTRANSFER_GUIDE.md](guides/tools/XLSTRANSFER_GUIDE.md) | XLSTransfer tool usage |

---

## Related (Outside docs/)

| Location | Purpose |
|----------|---------|
| `CLAUDE.md` | Claude navigation hub (project root) |
| `Roadmap.md` | Current priorities (project root) |
| `.claude/agents/` | Custom Claude agents |
| `testing_toolkit/` | Testing protocols and tools |
| `scripts/` | Shell wrappers and utilities |
| `RessourcesForCodingTheProject/NewScripts/` | Mini-projects |

---

## NewScripts Projects

| Project | CI/CD | Description |
|---------|-------|-------------|
| **LanguageDataExporter** | GitHub Actions | XML → Excel with VRS ordering |
| **QACompilerNEW** | GitHub Actions | QA datasheet generation |
| QuickTranslate | Manual | Korean translation lookup |
| WordCountMaster | Manual | Word count reports |
| GlossarySniffer | Manual | Glossary extraction |

---

*Last updated: 2026-02-01*
