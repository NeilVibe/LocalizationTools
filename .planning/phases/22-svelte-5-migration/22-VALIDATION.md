---
phase: 22
slug: svelte-5-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep-based verification (no runtime test framework needed for this migration) |
| **Config file** | none — grep commands verify zero legacy patterns |
| **Quick run command** | `grep -r "createEventDispatcher" locaNext/src/ --include="*.svelte" \| wc -l` |
| **Full suite command** | `grep -r "createEventDispatcher" locaNext/src/ --include="*.svelte" \| wc -l && grep -rP " on:\w+" locaNext/src/ --include="*.svelte" \| grep -v "carbon-components" \| wc -l && grep -r "e\.detail" locaNext/src/ --include="*.svelte" \| wc -l` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (createEventDispatcher count)
- **After every plan wave:** Run full suite command (all 3 pattern counts)
- **Before `/gsd:verify-work`:** All 3 counts must be 0
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | SV5-01 | grep | `grep "createEventDispatcher" locaNext/src/lib/components/ldm/VirtualGrid.svelte` | N/A | ⬜ pending |
| 22-01-02 | 01 | 1 | SV5-02 | grep | `grep "on:" locaNext/src/lib/components/apps/LDM.svelte` | N/A | ⬜ pending |
| 22-01-03 | 01 | 1 | SV5-03 | grep | `grep "createEventDispatcher" locaNext/src/lib/components/ldm/*.svelte` | N/A | ⬜ pending |
| 22-02-01 | 02 | 1 | SV5-04 | grep | `grep "createEventDispatcher" locaNext/src/lib/components/pages/*.svelte` | N/A | ⬜ pending |
| 22-02-02 | 02 | 1 | SV5-05 | grep | `grep -r "createEventDispatcher" locaNext/src/ --include="*.svelte"` | N/A | ⬜ pending |
| 22-02-03 | 02 | 1 | SV5-06 | grep | `grep -rP " on:\w+" locaNext/src/ --include="*.svelte" \| grep -v carbon` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — grep-based verification needs no setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Carbon on: interop | SV5-06 | Carbon library requires on: syntax | Verify remaining on: directives are Carbon-only |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
