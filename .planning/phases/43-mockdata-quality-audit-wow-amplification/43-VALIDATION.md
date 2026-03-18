---
phase: 43
slug: mockdata-quality-audit-wow-amplification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual XML validation + API curl checks |
| **Config file** | none — data-only phase, no code tests |
| **Quick run command** | `python3 -c "import lxml.etree; lxml.etree.parse('tests/fixtures/mock_gamedata/StaticInfo/skillinfo/skillinfo_showcase.staticinfo.xml')"` |
| **Full suite command** | `bash testing_toolkit/api_test_protocol.sh` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Validate XML well-formedness with lxml parse
- **After every plan wave:** Verify cross-ref resolution via codex API endpoints
- **Before `/gsd:verify-work`:** Full API test + Playwright screenshots
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | MOCK-AUDIT-01 | file | `test -f tests/fixtures/mock_gamedata/StaticInfo/skillinfo/skillinfo_showcase.staticinfo.xml` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 1 | MOCK-AUDIT-01 | file | `test -f tests/fixtures/mock_gamedata/StaticInfo/regioninfo/regioninfo_showcase.staticinfo.xml` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 1 | MOCK-AUDIT-01 | file | `test -f tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_showcase.staticinfo.xml` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 1 | MOCK-AUDIT-02 | api | `curl -s http://localhost:8888/api/ldm/codex/relationships \| python3 -c "import sys,json; d=json.load(sys.stdin); print(len([l for l in d['links'] if l['rel_type']!='related']))"` | ✅ | ⬜ pending |
| 43-03-01 | 03 | 2 | MOCK-AUDIT-03 | file | `ls tests/fixtures/mock_gamedata/textures/region_*.png \| wc -l` | ✅ | ⬜ pending |
| 43-04-01 | 04 | 2 | MOCK-AUDIT-04 | grep | `grep -c "source" server/tools/ldm/services/mock_tm_loader.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/mock_gamedata/StaticInfo/skillinfo/` — directory must exist
- [ ] `tests/fixtures/mock_gamedata/StaticInfo/regioninfo/` — directory must exist
- [ ] `tests/fixtures/mock_gamedata/StaticInfo/questinfo/` — directory must exist

*Existing infrastructure covers API testing — no new test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Region textures look appropriate | MOCK-AUDIT-03 | Visual quality | Open each PNG, verify biome matches region name |
| Relationship graph tells coherent story | MOCK-AUDIT-02 | Visual layout | Open Codex graph, verify Sage Order vs Dark Cult clusters |
| Korean translations are natural | MOCK-AUDIT-04 | Language quality | Review Korean text in browser, check for awkward phrasing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
