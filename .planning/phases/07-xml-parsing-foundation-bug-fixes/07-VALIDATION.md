---
phase: 07
slug: xml-parsing-foundation-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio |
| **Config file** | `pytest.ini` (root) |
| **Quick run command** | `python -m pytest tests/unit/ldm/ -x --no-header -q` |
| **Full suite command** | `python -m pytest tests/unit/ldm/ tests/stability/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ldm/ -x --no-header -q`
- **After every plan wave:** Run `python -m pytest tests/unit/ldm/ tests/stability/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | XML-04 | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_sanitizer -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | XML-06 | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_language_table -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | XML-07 | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_stringid_consumer -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | XML-05 | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_cross_reference -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | XML-01 | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_knowledge_chain -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | XML-02 | unit | `python -m pytest tests/unit/ldm/test_glossary_service.py::test_build_from_real_data -x` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | XML-03 | unit | `python -m pytest tests/unit/ldm/test_context_service.py::test_chain_resolution -x` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 1 | FIX-01 | integration | `python -m pytest tests/unit/ldm/test_routes_tm_crud.py -x -k offline` | ❌ W0 | ⬜ pending |
| 07-02-04 | 02 | 1 | FIX-02 | integration | `python -m pytest tests/unit/ldm/test_tm_paste.py -x` | ❌ W0 | ⬜ pending |
| 07-02-05 | 02 | 1 | FIX-03 | integration | `python -m pytest tests/unit/ldm/test_routes_folders.py -x -k create_then_get` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_xml_parsing.py` — stubs for XML-01, XML-04, XML-05, XML-06, XML-07
- [ ] `tests/unit/ldm/test_glossary_service.py` — new tests for XML-02 with real fixture data
- [ ] `tests/unit/ldm/test_context_service.py` — new tests for XML-03 chain resolution
- [ ] `tests/unit/ldm/test_routes_tm_crud.py` — new test for FIX-01 offline TM visibility
- [ ] `tests/unit/ldm/test_tm_paste.py` — covers FIX-02 (new file)
- [ ] `tests/unit/ldm/test_routes_folders.py` — new test for FIX-03 create-then-get
- [ ] `tests/fixtures/xml/` — XML fixture files (malformed, KnowledgeInfo, LocStr, language tables)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Offline TMs visible in online TM tree UI | FIX-01 | Requires both SQLite+PostgreSQL running with UI | Login online, check TM tree shows offline TMs |
| TM paste UI flow | FIX-02 | Requires clipboard + UI interaction | Copy TM entry, paste into target file, verify transfer |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
