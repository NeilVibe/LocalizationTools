# Tribunal — Multi-Expert Decision Engine

**Status:** Production v3.0 (2026-03-25)
**MCP Server:** `~/.claude/mcp-servers/tribunal/server.py`
**Skill:** `~/.claude/skills/decision-tribunal/SKILL.md`
**Skills indexed:** 111 auto-discovered from `~/.claude/skills/`

---

## Architecture (v3 — Agent-Based)

v3 split Tribunal into two complementary layers:

| Layer | What | Purpose |
|-------|------|---------|
| **MCP** (`tribunal_match`, `tribunal_personas`) | Instant persona matching engine | Find the RIGHT experts |
| **Skill** (`/decision-tribunal`) | 5-step orchestration workflow | Run the experts, synthesize verdict |

**Why two layers?** MCP is fast but dumb (matching only). The Skill teaches Claude HOW to use the matches — spawn agents, synthesize, store. Neither works at full power alone.

```
                  ┌─────────────────────────────────────────┐
                  │         /decision-tribunal SKILL         │
                  │         (orchestration workflow)          │
                  │                                          │
                  │  Step 1: tribunal_match ──→ MCP (instant)│
                  │  Step 2: Validate picks  ──→ Claude brain│
                  │  Step 3: Fan out agents  ──→ Agent tool  │
                  │  Step 4: Queen synthesis ──→ Claude brain│
                  │  Step 5: Store verdict   ──→ Ruflo MCP   │
                  └─────────────────────────────────────────┘
```

---

## MCP Tools (2 tools)

| Tool | Purpose | Speed | Cost |
|------|---------|-------|------|
| `tribunal_match` | Find best expert personas for a question (Viking + TF-IDF) | <1s | Free |
| `tribunal_personas` | List all 111 available personas | <1s | Free |

These are **matching tools only** — they find experts but don't run them.

### tribunal_match

```
tribunal_match(question="Should we use SQLite or PostgreSQL?", max_personas=5)
```

Returns ranked personas with scores:
- **Viking score** — semantic similarity (understands meaning)
- **KW-IDF score** — keyword term frequency (matches domain words)
- **Combined score** — merged ranking with dual-match bonus

### tribunal_personas

```
tribunal_personas()
```

Returns all 111 skill personas with keyword counts and descriptions.

---

## Skill: /decision-tribunal (Full Pipeline)

The skill orchestrates the complete decision workflow. Invoke with:
- User says "tribunal", "ask experts", "get opinions"
- Claude hits a design fork with 2+ valid options
- During `/grill-me` when hard tradeoffs surface

### The 5 Steps

**Step 1 — Match Personas** (MCP)
```
tribunal_match(question="...", max_personas=5)
```
Instant. Returns ranked personas with scores.

**Step 2 — Validate Picks** (Claude brain)
- Do the matched skills actually have relevant expertise?
- Are there S-tier/A-tier skills that were MISSED?
- Override bad picks — `tribunal_match` uses keywords, it can miss skills where expertise is in the content, not the name.

**Step 3 — Fan Out Parallel Agents** (Agent tool)
Spawn 3-5 parallel Agent calls, one per expert. ALL in one message:
```
Agent(prompt="You are a [SKILL] expert. Answer from YOUR perspective.
Be specific, opinionated, concrete. Under 200 words. Lead with recommendation.
QUESTION: [question]
DO NOT write code or edit files. Just give your expert opinion.")
```

**Step 4 — Queen Synthesis** (Claude brain)
Claude IS the queen. Synthesize:
1. Tally — who agrees, who dissents
2. Resolve disagreements — explain why one side wins
3. VERDICT — one clear recommendation with WHY
4. Format as a table for scanability

**Step 5 — Bridge to Ruflo** (Ruflo MCP)
```
ruflo memory_store(
  key: "tribunal-20260325-topic",
  value: "VERDICT: [condensed, max 500 chars]",
  tags: ["tribunal", "decision", "topic-keywords"]
)
```

---

## When to Use

| Scenario | What to use |
|----------|-------------|
| "Which skill for X?" | `tribunal_match` alone (step 1 only) |
| Hard design decision, 2+ valid options | Full `/decision-tribunal` (all 5 steps) |
| Architecture tradeoff (Redis vs PG, etc.) | Full pipeline, consider forcing specific experts |
| GSD discuss/plan phase — open questions | Full pipeline |
| During `/grill-me` — hard tradeoff surfaces | Full pipeline |
| Simple factual question | Don't use tribunal — just answer it |
| Task that just needs doing | Don't use tribunal — just do it |

## When NOT to Use

- Simple factual questions (just answer them)
- Tasks with one obvious answer
- Questions that need doing, not deciding

---

## Force Specific Experts

If `tribunal_match` gives bad picks, override manually in Step 2:
- Check the skill tier list (`~/.claude/rules/skill-tier-list.md`)
- Name the experts directly when spawning agents in Step 3
- Example: for "GSAP vs CSS animations?" force `gsap-master`, `awwwards-animations`, `frontend-design`

---

## Persona Selection Engine

Two-signal merge with scoring:

1. **Viking semantic search** — understands meaning ("real-time sync" → websocket-engineer)
2. **TF-IDF keyword scoring** — matches domain terms, weights rare words higher
3. **Skill-name 3x boost** — "websocket" in question → `websocket-engineer` scores 3x
4. **Dual-match bonus** (+0.2) — skills found by BOTH signals rank highest

### Match Quality (Verified)

| Query Domain | #1 Match |
|-------------|----------|
| WebSocket | websocket-engineer |
| Database | sql-expert |
| 3D Particles | particles-gpu |
| Svelte | svelte-code-writer |
| Security | secure-code-guardian |
| Animation | gsap-master |
| FastAPI backend | fastapi-expert |

---

## Integration with GSD

| GSD Phase | Tribunal Use |
|-----------|-------------|
| `/gsd:discuss-phase` | Full pipeline for open design questions |
| `/gsd:plan-phase` | `tribunal_match` to preview expert coverage |
| `/gsd:execute-phase` | Full pipeline for implementation decisions |
| Architecture review | Full pipeline with deep expert framing |

---

## Integration with Other Tools

| Tool | How it pairs with Tribunal |
|------|---------------------------|
| `/grill-me` | Grill surfaces the hard questions → Tribunal answers them |
| Ruflo `memory_store` | Step 5 persists verdicts for future recall |
| Ruflo `memory_search` | Search past tribunal decisions before re-asking |
| Viking `viking_search` | Powers the semantic matching in `tribunal_match` |

---

## Key Design Decisions

1. **Synthesis, not voting** — Queen combines best parts of expert opinions. Expertise is hierarchical, not democratic.
2. **Opus IS the queen** — No subprocess needed. Claude synthesizes directly. Faster, zero failures.
3. **MCP + Skill split** — MCP handles fast matching (no LLM). Skill handles orchestration (needs Claude's brain). Clean separation.
4. **Parallel agents** — All expert agents spawn in one message. ~12-15s total vs 60-90s with old sequential `claude -p`.
5. **Excluded personas** — `autoresearch`, `decision-tribunal`, `find-skills`, `skill-creator`, `write-a-skill` never selected (meta-skills that would recurse).

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Wrong personas selected | Generic query terms | Use `tribunal_match` to debug, then override in Step 2 |
| Experts give shallow answers | Too little context | Add project context to the Agent prompt in Step 3 |
| Ruflo store fails | Ruflo MCP not running | Expected gracefully — verdict still works, just not persisted |
| Viking returns no matches | Viking server down | Falls back to keyword-only matching (still works) |

---

## History

| Version | Date | Architecture |
|---------|------|-------------|
| v1.0 | 2026-03 | Sequential `claude -p` subprocesses, HTTP Ruflo |
| v2.0 | 2026-03-22 | `tribunal_decide` + `tribunal_automaton` MCP tools (removed) |
| v3.0 | 2026-03-25 | MCP matching only + Skill orchestration + Agent tool fan-out |
