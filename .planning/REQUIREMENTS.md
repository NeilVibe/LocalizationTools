# Requirements: LocaNext

**Defined:** 2026-03-26
**Core Value:** Real, working localization workflows with zero cloud dependency

## v12.0 Requirements

Requirements for TM Intelligence milestone. Each maps to roadmap phases.

### TM UI (Threshold + Display)

- [x] **TMUI-01**: Dual threshold system — right panel TM suggestions automatically use 62% context threshold, pretranslation automatically uses 92% threshold (both hardcoded, not user-configurable)
- [x] **TMUI-02**: Translator sees prominent match percentage with color-coded badges on every TM result in the right panel

### AC Context Search

- [x] **ACCTX-01**: System builds Aho-Corasick automatons (whole + line) from loaded TM on TM index load
- [ ] **ACCTX-02**: When translator selects a row, AC scans Korean source text and shows where terms appear elsewhere in the TM
- [x] **ACCTX-03**: System uses character n-gram Jaccard (n={2,3,4,5}, space-stripped Korean) for fuzzy matches below AC exact threshold (>=62%)
- [ ] **ACCTX-04**: Context search results appear in the right panel with match tier indicator and score

### Performance

- [ ] **PERF-01**: AC context search completes within 100ms per row-select (no perceptible delay)

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Architecture

- **ARCH-02**: Split mega_index.py (1310 lines) into domain services
- **LDE2E-03**: Language data with images/audio resolves from Perforce-like paths

### Infrastructure

- **LAN-01 through LAN-07**: LAN Server Mode — installer sets up machine as PostgreSQL LAN server

## Out of Scope

| Feature | Reason |
|---------|--------|
| Word-level n-grams | Korean doesn't split on spaces reliably; char n-grams sufficient |
| English source support for AC | Korean-only for now; can add later if needed |
| Jamo decomposition | Destroys semantic density; only useful for typo correction |
| Particle stripping | Optional optimization; defer to performance testing |
| AI re-ranking of AC results | Existing AI suggestion tab is separate concern |
| File/category-aware TM ranking | Current cascade is sufficient; not requested |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMUI-01 | Phase 86 | Complete |
| TMUI-02 | Phase 86 | Complete |
| ACCTX-01 | Phase 87 | Complete |
| ACCTX-02 | Phase 88 | Pending |
| ACCTX-03 | Phase 87 | Complete |
| ACCTX-04 | Phase 88 | Pending |
| PERF-01 | Phase 87 | Pending |

**Coverage:**
- v12.0 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 after v12.0 roadmap creation*
