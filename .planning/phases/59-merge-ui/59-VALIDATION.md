---
phase: 59
slug: merge-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual UI testing via Playwright screenshots |
| **Config file** | N/A (Svelte components, visual verification) |
| **Quick run command** | `python3 -m pytest tests/test_merge_api.py -x -q` (backend regression) |
| **Full suite command** | `python3 -m pytest tests/test_merge_api.py tests/test_transfer_adapter.py tests/test_match_types.py tests/test_folder_merge.py -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Verify component imports and render
- **After every plan wave:** Run backend regression suite
- **Before `/gsd:verify-work`:** Full suite + visual verification
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 59-01-01 | 01 | 1 | UI-03,UI-04,UI-05 | manual+import | `node -e "..."` component import check | ❌ W0 | ⬜ pending |
| 59-02-01 | 02 | 2 | UI-01,UI-02 | manual | Visual verification of toolbar + context menu | N/A | ⬜ pending |
| 59-03-01 | 03 | 2 | UI-06,UI-07,UI-08,UI-09 | manual | Visual verification of multi-language UI | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. No new test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal phase transitions (configure→preview→execute→done) | UI-03 | Visual flow | Open modal, step through all phases |
| SSE progress bar animation | UI-05 | Real-time visual | Execute merge, watch progress bar fill |
| Right-click context menu | UI-02 | Browser event | Right-click folder in explorer |
| Multi-language detection display | UI-06 | Visual layout | Open modal in multi-lang mode |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
