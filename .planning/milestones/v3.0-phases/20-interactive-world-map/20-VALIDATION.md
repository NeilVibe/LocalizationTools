---
phase: 20
slug: interactive-world-map
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `tests/conftest.py` (backend) |
| **Quick run command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/unit/ldm/ -x -q --tb=short` |
| **Full suite command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/ -x -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ldm/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -x -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | MAP-01, MAP-04 | unit | `pytest tests/unit/ldm/test_worldmap_service.py` | No -- W0 | pending |
| 20-01-02 | 01 | 1 | MAP-01, MAP-02, MAP-04 | unit | `pytest tests/unit/ldm/test_worldmap_route.py` | No -- W0 | pending |
| 20-02-01 | 02 | 2 | MAP-01, MAP-04, MAP-05 | type-check | `npx svelte-check` | N/A | pending |
| 20-02-02 | 02 | 2 | MAP-02, MAP-03 | type-check | `npx svelte-check` | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_worldmap_service.py` -- covers MAP-01 (coordinate parsing), MAP-04 (waypoint routes)
- [ ] `tests/unit/ldm/test_worldmap_route.py` -- covers MAP-01/02/04 (API contract)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Region nodes at correct positions | MAP-01 | Visual spatial verification | Open map, verify nodes match expected layout |
| Tooltip on hover | MAP-02 | Visual UI verification | Hover node, verify tooltip with name/description/NPCs |
| Click opens detail panel with Codex links | MAP-03 | Interaction flow | Click node, verify detail panel and Codex links |
| Route connections rendered | MAP-04 | Visual path verification | Verify lines between connected regions |
| Pan and zoom | MAP-05 | Interaction flow | Drag to pan, scroll to zoom, verify smooth |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
