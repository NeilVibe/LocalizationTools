# Power Upgrade TODO — Next Session

> After `/clear`, say: **"Read docs/current/POWER_UPGRADE_TODO.md and execute"**

## 1. OpenViking Install (Context DB for persistent agent memory)
```bash
pip install openviking --upgrade
# Then configure MCP server or use as library
# Docs: https://github.com/volcengine/OpenViking
# Claude memory plugin: https://github.com/volcengine/OpenViking/tree/main/examples/claude-memory-plugin
```
**Why:** Replaces flat memory files with semantic RAG search. Agent can QUERY context instead of reading files.

## 2. Run Self-Improving Agent on Memory
Use `/self-improving-agent` skill to:
- Audit MEMORY.md for patterns worth promoting to permanent knowledge
- Clean stale entries
- Consolidate topic files

## 3. Impeccable Design Pipeline on Landing Page
```
/i-critique    → find all weaknesses
/i-polish      → premium refinement
/i-animate     → purposeful motion
/i-bolder      → less AI-safe
/i-audit       → accessibility check
```
**File:** `landing-page/index.html` (3228 lines, 116KB)

## 4. PromptFoo (LLM eval — future)
```bash
npx skills add daymade/claude-code-skills  # includes promptfoo-evaluation
```
**Why:** Eval AI translation prompts, compare models, test quality.

## 5. Synergy Architecture (documented in POWER_ARSENAL.md section 15)
Always fuse:
- **GSD** for multi-phase work (plan → execute → verify)
- **Superpowers** for single-session execution
- **Impeccable** for UI quality enforcement
- **Self-improving-agent** for memory optimization
- **OpenViking** (once installed) for semantic context

## 6. Keep Searching for More Power
```bash
npx skills find "memory"        # Memory management skills
npx skills find "context"       # Context management
npx skills find "agent"         # Agent orchestration
npx skills find "optimization"  # Performance skills
npx skills check                # Update existing skills
```

## Reference Docs
- `docs/reference/POWER_ARSENAL.md` — full skill/plugin/agent reference + synergy architecture
- `memory/landing_page_session.md` — landing page state
- `docs/current/LANDING_PAGE_TODO.md` — landing page next steps
