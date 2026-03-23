# Tribunal MCP — Decision Engine

**Status:** Production v2.0 (2026-03-22)
**Code:** `~/.claude/mcp-servers/tribunal/server.py` (780 lines)
**Skills:** 111 auto-discovered from `~/.claude/skills/`

---

## What It Does

Tribunal = multi-expert decision engine. Ask a question → it picks the best expert personas → runs them in parallel → queen synthesizes a verdict → optionally creates tasks.

```
Question → Viking + TF-IDF persona selection (3-5 experts)
    → Parallel claude -p calls (haiku/sonnet, 60-90s)
    → Queen synthesis (sonnet/opus)
    → Parse ACTIONS block → Ruflo tasks (optional)
    → Hive-mind consensus (optional)
```

---

## 4 Tools

| Tool | Purpose | Speed | Cost |
|------|---------|-------|------|
| `tribunal_match` | Dry-run: preview persona selection with scores | <1s | Free |
| `tribunal_personas` | List all 111 available personas | <1s | Free |
| `tribunal_decide` | Decision only (experts → queen → verdict) | 60-90s | ~$0.10 |
| `tribunal_automaton` | Full pipeline (decide → tasks → consensus) | 60-90s | ~$0.05 |

---

## Recommended Defaults

| Parameter | Automaton | Decide |
|-----------|-----------|--------|
| `model_personas` | `haiku` | `sonnet` |
| `model_queen` | `sonnet` | `opus` |
| `max_personas` | 3-5 | 3-5 |
| `full_knowledge` | `false` | `false` (or `true` for deep analysis) |

**Why:** Automaton has queen refinement, so cheap personas suffice. Decide is standalone — invest in persona quality.

---

## Usage Examples

### Quick Decision
```python
tribunal_decide(
    question="Should we use SQLite or PostgreSQL for offline-first desktop?",
    max_personas=3
)
```

### Architecture Decision (Deep)
```python
tribunal_decide(
    question="Design the real-time sync protocol for multi-user editing",
    model_personas="sonnet",
    model_queen="opus",
    full_knowledge=True  # sends complete SKILL.md to personas
)
```

### Full Pipeline (Decision → Tasks)
```python
tribunal_automaton(
    question="How should we implement the particle morphing system?",
    max_personas=4
)
# Returns: verdict + parsed actions + Ruflo task IDs
```

### Dry Run (Free, Fast)
```python
tribunal_match(
    question="WebSocket real-time sync",
    max_personas=5
)
# Returns: scored persona ranking (Viking + keyword TF-IDF)
```

### Force Specific Experts
```python
tribunal_decide(
    question="Should we use GSAP or CSS animations?",
    personas="gsap-master,awwwards-animations,frontend-design"
)
```

---

## Persona Selection (v2)

Two-signal merge with scoring:

1. **Viking semantic search** — understands meaning ("real-time sync" → websocket-engineer)
2. **TF-IDF keyword scoring** — matches domain terms, weights rare words higher
3. **Skill-name 3x boost** — "websocket" in question → `websocket-engineer` scores 3x
4. **Dual-match bonus** (+0.2) — skills found by BOTH signals rank highest
5. **Min score threshold** (2.0) — filters noise matches

### Match Quality (Verified)

| Query Domain | #1 Match |
|-------------|----------|
| WebSocket | websocket-engineer |
| Database | sql-expert |
| 3D Particles | particles-gpu |
| Svelte | svelte-code-writer |
| Security | secure-code-guardian |
| Animation | gsap-master |

---

## Integration with GSD

| GSD Phase | Tribunal Use |
|-----------|-------------|
| `/gsd:discuss-phase` | `tribunal_decide` for open design questions |
| `/gsd:plan-phase` | `tribunal_match` to preview expert coverage |
| `/gsd:execute-phase` | `tribunal_automaton` for implementation decisions |
| Architecture review | `tribunal_decide` with `full_knowledge=True` |

---

## Key Design Decisions

1. **Synthesis, not voting** — Queen combines best parts of expert opinions. Expertise is hierarchical, not democratic.
2. **Prompt truncation** (3K chars default) — First 3K of SKILL.md has description, workflow, and key constraints. Enough for a 200-word opinion. `full_knowledge=True` sends everything.
3. **Process group kill** — `start_new_session=True` + `os.killpg(SIGKILL)` prevents zombie `claude -p` processes on timeout.
4. **Excluded personas** — `autoresearch`, `decision-tribunal`, `find-skills`, `skill-creator`, `write-a-skill` never selected (meta-skills that would recurse).
5. **Ruflo integration** — Best-effort HTTP calls to store verdicts + create tasks. Silently fails if Ruflo unavailable (stdio-only MCP).

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| All personas timeout | API congestion or zombie processes | Kill stale `claude -p`: `ps aux \| grep "claude -p" \| awk '{print $2}' \| xargs kill -9` |
| Wrong personas selected | Generic query terms | Use `tribunal_match` to debug, or specify `personas=` explicitly |
| Ruflo "not available" | Ruflo is stdio MCP, no HTTP API | Expected. Verdicts still work, just not persisted to Ruflo memory |
| Queen verdict too short | <2 experts responded | Increase `max_personas` or check API status |
