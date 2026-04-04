# PLAN: Memory Architecture Restructure

> **Created:** 2026-04-04 | **Status:** COMPLETE | **Priority:** HIGH | **Completed:** 2026-04-04
> **Why:** Claude repeatedly forgets what's installed, ignores docs, wastes time reinstalling things. Root cause: flat unstructured memory with no retrieval discipline.

---

## Problem Statement

156 memory files in a flat directory. No hierarchy, no cross-references, no freshness tracking, no semantic search integration. MEMORY.md is 380 lines (truncated at 200 in context — half is never loaded). Result: Claude operates blind, rediscovers things every session, and makes destructive mistakes.

## Current Architecture (BROKEN)

```
memory/
├── MEMORY.md              (380 lines, truncated, session history dump)
├── feedback_*.md           (62 files, rules — good content, never read)
├── project_*.md            (62 files, 80% stale handoffs from phases 99-112)
├── reference_*.md          (20 files, some outdated)
├── user_*.md               (0 files — knows nothing about user)
└── misc *.md               (12 files, uncategorized)
```

**Failure modes:**
1. MEMORY.md too long → context truncation → critical info lost
2. Stale project files → misleading context → wrong decisions
3. No Viking indexing → can't semantically search memories
4. No cross-references → can't follow related chains
5. No retrieval discipline → memories exist but aren't read
6. No user profile → can't tailor behavior

## Target Architecture (NEURAL WEB)

```
memory/
├── MEMORY.md                    (<100 lines, trunk index ONLY)
│
├── user/                        (WHO — user profile, preferences)
│   └── profile.md               (role, expertise, communication style)
│
├── rules/                       (HOW — behavioral rules, always-apply)
│   ├── _INDEX.md                (quick-scan checklist of all rules)
│   ├── coding.md                (backward compat, no loguru in NewScripts, etc)
│   ├── builds.md                (trigger format, offline, version injection, etc)
│   ├── ui.md                    (Svelte 5, optimistic UI, Carbon, etc)
│   ├── workflow.md              (never kill servers, plan before code, etc)
│   ├── tools.md                 (read docs first, check memory, verify agents, etc)
│   └── testing.md               (playwright patterns, API-first, etc)
│
├── active/                      (WHAT — current work, actively referenced)
│   ├── _INDEX.md                (current phase, blockers, next steps)
│   ├── phase113_lan_fix.md      (current phase details)
│   ├── zimage_mcp.md            (Z-Image status)
│   └── ai_stack.md              (what's installed, what's active)
│
├── reference/                   (WHERE — stable facts, rarely change)
│   ├── architecture.md          (client/server split, factory pattern)
│   ├── build_pipeline.md        (CI/CD, Gitea, GitHub)
│   ├── xml_patterns.md          (parsing patterns across projects)
│   └── security.md              (OWASP status, audit results)
│
└── archive/                     (PAST — historical, don't load into context)
    ├── phases_93_109.md          (compressed: one line per phase)
    ├── qacompiler_history.md     (compressed)
    └── quicktranslate_history.md (compressed)
```

### Key Principles

1. **Trunk (MEMORY.md):** <100 lines. Links to branches. Never contains details.
2. **Branches (directories):** Semantic categories. Each has `_INDEX.md` for quick scan.
3. **Leaves (files):** Focused, single-topic. Cross-reference related leaves.
4. **Wiring:** Every memory file has a `## Related` section linking to connected memories.
5. **Freshness:** Every file has `last_verified: YYYY-MM-DD` in frontmatter.
6. **Viking:** ALL memory files indexed in Viking for semantic search.
7. **Retrieval:** Before ANY action, search Viking memories + scan relevant _INDEX.md.

### Rules Consolidation

62 feedback files → ~6 consolidated rule files by domain:

| New File | Consolidates | Count |
|---|---|---|
| `rules/coding.md` | backward compat, no loguru, electron cherrypick, state_raw, etc | ~12 |
| `rules/builds.md` | trigger format, offline, version injection, CI autoloop, etc | ~10 |
| `rules/ui.md` | Svelte 5, dev parity, Carbon, status colors, etc | ~8 |
| `rules/workflow.md` | plan before code, never kill servers, grill yourself, etc | ~12 |
| `rules/tools.md` | read docs first, check memory, mandatory MCP trio, Viking, etc | ~10 |
| `rules/testing.md` | playwright patterns, API-first, verify agents, etc | ~5 |

Each rule keeps: the rule itself, WHY (incident that caused it), WHEN to apply.

### Project File Cleanup

62 project files → ~5 active + 1 compressed archive:

| Keep (active/) | Archive (one-liner summary) |
|---|---|
| phase113_lan_fix.md | phases 93-112 → one compressed file |
| zimage_mcp.md | qacompiler history → one file |
| ai_stack.md | quicktranslate history → one file |
| tm_architecture.md | audio codex history → one file |
| build_types.md | — |

---

## Execution Plan

### Phase 1: User Profile (15 min)
- Create `user/profile.md` from conversation history
- What we know: senior dev, game localization, Korean, wants maximum power, hates when I forget things

### Phase 2: Rules Consolidation (45 min)
- Read all 62 feedback files
- Group by domain
- Write 6 consolidated rule files with cross-references
- Create `rules/_INDEX.md` checklist
- Verify no rules lost

### Phase 3: Project Cleanup (30 min)
- Move phases 93-109 content to `archive/phases_93_109.md` (one line each)
- Move QACompiler/QuickTranslate memories to archive
- Keep only active project files in `active/`
- Update cross-references

### Phase 4: MEMORY.md Rewrite (20 min)
- Rewrite to <100 lines
- Trunk structure: links to branches only
- No session history, no phase details

### Phase 5: Viking Integration (20 min)
- Index all memory files into Viking
- Test semantic search: "what's installed" → finds ai_stack.md
- Test: "how to trigger build" → finds rules/builds.md

### Phase 6: Retrieval Discipline (10 min)
- Update `feedback_read_docs_before_acting.md` → now in `rules/tools.md`
- Add to CLAUDE.md or rules: "Before ANY action, Viking search memories"

---

## Success Criteria

1. MEMORY.md < 100 lines, loads fully in context
2. `rules/_INDEX.md` scannable in 10 seconds
3. Zero stale project files in active memory
4. Viking can find any memory by semantic query
5. Claude can answer "what's installed?" without hallucinating
6. Next session starts clean with full context

---

## NOT in Scope

- Changing how Claude Code's memory system works (that's Anthropic's job)
- Building a custom MCP for memory (overkill, Viking already works)
- Reorganizing project docs (separate effort, docs/ has its own structure)
