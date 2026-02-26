# PRXR — Plan-Review-Execute-Review Protocol

> The protocol that catches bugs **before they're written**.

---

## Why PRXR Exists

Most implementation bugs come from two moments:
1. **Bad plan** — wrong approach, missed edge case, incomplete understanding
2. **Bad execution** — plan was fine, but implementation drifted or introduced errors

PRXR attacks both moments with review gates. No code ships without being examined twice — once as a plan, once as code.

---

## The 7 Steps

```
1. PLAN         Explore codebase, write a detailed implementation plan
2. REVIEW       5 review agents examine the plan (correctness, edge cases, patterns)
3. FIX PLAN     Apply review findings — update plan before writing any code
4. EXECUTE      Implement exactly as planned
5. REVIEW       5 review agents examine the implementation
6. FIX          Apply review findings to the code
7. FINAL CHECK  Re-read all changes, run tests, verify consistency
```

### Step Details

**Step 1 — PLAN:**
- Use Plan Mode (`EnterPlanMode`) for structured exploration
- Read every file you'll touch. No guessing.
- Write step-by-step changes with exact file paths, line numbers, code snippets
- The plan should be specific enough that another agent could execute it blindly

**Step 2 & 5 — REVIEW (5-Agent):**
- Launch 5 `code-reviewer` Task agents in parallel
- Each agent gets the full context + specific review focus:
  - Agent 1: **Correctness** — Does the logic do what it claims?
  - Agent 2: **Edge Cases** — Empty inputs, None values, boundary conditions
  - Agent 3: **Pattern Consistency** — Does it match existing code patterns in the codebase?
  - Agent 4: **Integration** — Will it break anything upstream/downstream?
  - Agent 5: **Completeness** — Are all paths covered? Missing cleanup? Missing error handling?
- Collect all findings. No finding is too small.

**Review Agent Prompt Template:**
```
Review [PLAN/CODE] for: [feature name]

Context: [1-2 sentence description of what this feature does]

Files changed:
- [path/to/file1.py] — [what changed and why]
- [path/to/file2.py] — [what changed and why]

Compare against: [reference file or existing pattern to match]

Your focus: [CORRECTNESS / EDGE CASES / PATTERN CONSISTENCY / INTEGRATION / COMPLETENESS]

Specific pitfalls to watch for:
- [known issue 1]
- [known issue 2]

Classify findings as: CRITICAL (blocks ship) / WARNING (should fix) / SUGGESTION (nice to have)
```

**Step 3 & 6 — FIX:**
- Address every review finding. Don't dismiss without reason.
- If a finding reveals a design flaw, go back to Step 1 (plan) not forward.
- If findings conflict between agents, the more conservative finding wins (data safety > convenience).
- If you restart from Step 1 more than twice, STOP and discuss with the user — the approach may be fundamentally wrong.

**Step 4 — EXECUTE:**
- Implement file-by-file in the order the plan specifies.
- After each file: quick self-check — does it match the plan? If drift is detected, stop and reconcile.
- If implementation reveals the plan was wrong mid-execution: STOP. Go back to Step 1 with what you learned. Don't improvise a different approach.
- Do NOT commit yet — wait until Step 7 passes.

**Step 7 — FINAL CHECK:**
- Re-read all changed files end-to-end (full file, not just diffs)
- Verify consistency across files (same variable names, same patterns)
- Check nothing was accidentally left incomplete
- **Run tests:** Playwright for UI, unit tests for logic. Get hard evidence — screenshots, passing test output.
- Only after tests pass: commit and follow CLAUDE.md dual-push rules.

---

## What Makes PRXR Powerful

### 1. Parallel Review Agents
5 agents examining the same code from different angles catch things a single pass misses. One agent might focus on logic while another catches a naming inconsistency.

### 2. Plan Review (Step 2) Prevents Wasted Work
Catching a wrong approach at the plan stage costs minutes. Catching it after implementation costs the entire session. **Review the plan, not just the code.**

### 3. Specificity of Review Prompts
Generic "review this code" finds nothing. Each agent needs:
- The exact files changed
- What the feature does (business context)
- What pattern to compare against (existing code)
- Specific things to watch for (known pitfalls)

### 4. The Plan Is the Contract
A detailed plan with exact line numbers and code snippets means:
- Review agents know exactly what to examine
- Implementation has no ambiguity
- Drift between plan and code is immediately visible

---

## When to Use

| Use PRXR | Skip PRXR |
|----------|-----------|
| Multi-file features | Single-line fixes |
| Core logic changes | Typo/docs-only changes |
| New filter/pipeline stages | Config value changes |
| Anything touching transfer/generate paths | Adding a log line |
| Changes to matching/parsing logic | Trivial UI tweaks |

**Rule of thumb:** If you'd feel nervous pushing without testing, use PRXR.

---

## Anti-Patterns

- **Skipping plan review** — "The plan is obvious, just review the code." Plans have bugs too.
- **Generic review prompts** — "Review this file" finds nothing. Be specific about what to check.
- **Ignoring review findings** — If you dismiss a finding, document why. Don't silently skip.
- **PRXR for trivial changes** — Adding a comment doesn't need 5 review agents. Use judgment.
- **Rushing Step 7** — The final check catches the bugs that slipped through everything else.
- **Infinite loops** — If plan review keeps finding fundamental flaws, escalate to user after 2 restarts.
- **Skipping tests** — Step 7 is not just a re-read. Run actual tests. Screenshots = proof.

---

*Protocol doc — referenced from CLAUDE.md glossary*
