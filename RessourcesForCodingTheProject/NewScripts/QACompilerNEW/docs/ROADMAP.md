# QACompiler - Roadmap

> Track new datasheet development and the path to generator consolidation.

---

## Strategy

**Phase 1:** Build NEW generators alongside existing ones (separate output) — **DONE**
**Phase 2:** Validate new generators in production — **IN PROGRESS**
**Phase 3:** Consolidate — replace old generators with new ones, trim redundant sheets

---

## New Generators (Phase 1 — DONE)

| # | Generator | Old Equivalent | Status | Notes |
|---|-----------|----------------|--------|-------|
| 1 | **newitem.py** | item.py | DONE | Row-per-text, 4-step pass |
| 2 | **newcharacter.py** | character.py | DONE | Row-per-text, 5 rows/char |
| 3 | **newregion.py** | region.py | DONE | Delegates writing to region.py |
| 4 | **newskill.py** | skill.py | DONE | 3 tabs: SkillGroup, SkillTree, SkillPC |

---

## Phase 3 — Future Consolidation (NOT YET — validate first)

Once new generators are proven in production, consolidate:

1. **Remove old generators** — delete `item.py`, `character.py`, `region.py`, `skill.py`
2. **Rename new → standard** — `newitem.py` → `item.py`, `newskill.py` → `skill.py`, etc.
3. **Trim sheets** — once we know which tabs/views are actually useful, remove the rest
   - e.g. newskill.py has 3 tabs (SkillGroup, SkillTree, SkillPC) — might keep just 1
   - e.g. item.py has primary (hierarchical) + secondary (flat) — might keep just 1
4. **Update all imports** — config.py, generators/__init__.py, main.py, populate_new.py, coverage.py
5. **Update GUI** — remove old buttons, rename new buttons to replace them

**Rule:** Don't consolidate until the new generators have been used in real QA cycles and confirmed correct. The old generators are the safety net until then.

---

---

## Recent Fixes (2026-03-03)

- **System category bug fixed** — `Username_System` folders were silently ignored during master build. `WORKER_GROUPS["system"]` was missing `"System"` after Skill consolidation removed it. Fixed: `["System", "Help"]`.
- **Skill Knowledge children** — inline children + sub-skill nesting implemented. Awaiting production verification.

---

*Last updated: 2026-03-03*
