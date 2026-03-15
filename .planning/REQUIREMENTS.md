# Requirements: LocaNext v2.0

**Defined:** 2026-03-15
**Core Value:** Real, working localization workflows -- real XML parsing, real merge logic, real image/audio, AI summaries -- all local, dual-mode for translators and game developers.

## v2.0 Requirements

Requirements for v2.0 milestone. Each maps to roadmap phases.

### Dual UI

- [x] **DUAL-01**: System detects file type (LocStr nodes = Translator, other nodes = Game Dev) and switches UI mode automatically
- [x] **DUAL-02**: Translator mode shows translation-specific columns (Source, Target, Status, Match%, TM Source)
- [x] **DUAL-03**: Game Dev mode shows XML-structure columns (NodeName, Attributes, Values, Children count)
- [x] **DUAL-04**: Mode indicator visible in editor header showing current file type
- [x] **DUAL-05**: Both modes share the same virtual grid infrastructure with different column configs

### XML Parsing

- [x] **XML-01**: MapDataService parses real KnowledgeInfo XMLs and builds StrKey→UITextureName→DDS chains
- [x] **XML-02**: GlossaryService wires to real game data and builds Aho-Corasick automaton from staticinfo
- [x] **XML-03**: ContextService resolves multi-pass KnowledgeKey chains with full metadata
- [x] **XML-04**: XML sanitizer + recovery pattern handles malformed game data files gracefully
- [x] **XML-05**: Cross-reference chain resolution works across multiple XML files (join keys)
- [x] **XML-06**: Language table parsing extracts all language columns from loc.xml files correctly
- [x] **XML-07**: StringIdConsumer pattern provides fresh consumer per language for deduplication

### Image & Audio Pipeline

- [x] **MEDIA-01**: DDS textures convert to PNG via Pillow+pillow-dds for browser display
- [x] **MEDIA-02**: WEM audio files play back via vgmstream-cli conversion or WAV fallback
- [x] **MEDIA-03**: Real data flows from MapDataService → API endpoint → ImageTab/AudioTab components
- [x] **MEDIA-04**: Missing image/audio shows graceful placeholder (not broken icon)

### Translator Merge

- [x] **TMERGE-01**: Exact StringID match transfers translation values between files
- [x] **TMERGE-02**: StrOrigin match (source text match) transfers when StringID differs
- [x] **TMERGE-03**: Fuzzy matching via Model2Vec finds similar source strings above threshold
- [x] **TMERGE-04**: Postprocessing pipeline applies 7-step CJK-safe cleanup after transfer
- [x] **TMERGE-05**: Export produces correct XML with br-tag preservation
- [x] **TMERGE-06**: Export produces Excel format with correct column structure
- [x] **TMERGE-07**: Export produces plain tabulated text (StringID + source + translation)

### Game Dev Merge

- [x] **GMERGE-01**: Global export identifies all changed nodes across entire file
- [x] **GMERGE-02**: Merge operates at node level (add/remove/modify nodes)
- [x] **GMERGE-03**: Merge operates at attribute value level within nodes
- [x] **GMERGE-04**: Merge handles parent→children→sub-children depth correctly
- [x] **GMERGE-05**: Position-based merge preserves XML document order (not match-type based)

### AI Summaries

- [x] **AISUM-01**: Qwen3-4B/8B endpoint via Ollama responds with structured JSON
- [x] **AISUM-02**: Character/item/region metadata generates 2-line contextual summary
- [ ] **AISUM-03**: Summary appears in ContextTab for selected string
- [x] **AISUM-04**: Summaries cache per StringID to avoid re-generation
- [x] **AISUM-05**: Graceful fallback when Ollama is unavailable (show "AI unavailable" badge)

### CLI & Testing

- [ ] **CLI-01**: CLI commands cover merge operations (translator + game dev modes)
- [ ] **CLI-02**: CLI commands cover export in all formats (XML, Excel, text)
- [ ] **CLI-03**: CLI commands verify dual UI file type detection
- [ ] **CLI-04**: E2E tests validate full merge→export→verify round-trip

### Bug Fixes

- [x] **FIX-01**: Offline TMs appear in online TM tree (architectural fix for SQLite→PostgreSQL visibility)
- [x] **FIX-02**: TM Paste UI flow works correctly end-to-end
- [x] **FIX-03**: Folder fetch returns 200 (not 404) after creation

## v3.0 Requirements (Deferred)

### Game World Codex

- **CODEX-01**: Interactive world map with regions, cities, NPCs
- **CODEX-02**: Character codex pages with images, relationships, quest appearances
- **CODEX-03**: Item codex pages with stats, similar items via embeddings
- **CODEX-04**: Full-text semantic search across all codex entities

### AI Translation & Content

- **AITRANS-01**: AI-generated translation suggestions with confidence scores
- **AITRANS-02**: AI naming suggestions for game dev entity creation
- **AITRANS-03**: AI autocorrection and writing quality feedback
- **AITRANS-04**: Real-time glossary inconsistency detection while typing

### Auto-Generation

- **AUTOGEN-01**: Auto-generate missing images via Nano Banana
- **AUTOGEN-02**: Auto-generate missing audio via voice synthesis

### Game Dev Grid (Full CRUD)

- **GDEV-01**: Game dev can create new parent/children nodes in XML
- **GDEV-02**: Game dev can nest new children under existing parents
- **GDEV-03**: XML schema validation before save

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full MT engine integration (Google/DeepL) | LOCAL AI only -- no cloud dependency |
| WYSIWYG in-context preview | MapDataGenerator provides context |
| Plugin/extension marketplace | Core must work first |
| Automated workflow orchestration | Enterprise TMS feature |
| Mobile app | Desktop-first |
| Multi-language UI | Not planned |
| OAuth/SSO login | Email/password sufficient |
| Real-time collaborative editing | Single-user focus for now |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| XML-01 | Phase 07 | Complete |
| XML-02 | Phase 07 | Complete |
| XML-03 | Phase 07 | Complete |
| XML-04 | Phase 07 | Complete |
| XML-05 | Phase 07 | Complete |
| XML-06 | Phase 07 | Complete |
| XML-07 | Phase 07 | Complete |
| FIX-01 | Phase 07 | Complete |
| FIX-02 | Phase 07 | Complete |
| FIX-03 | Phase 07 | Complete |
| DUAL-01 | Phase 08 | Complete |
| DUAL-02 | Phase 08 | Complete |
| DUAL-03 | Phase 08 | Complete |
| DUAL-04 | Phase 08 | Complete |
| DUAL-05 | Phase 08 | Complete |
| TMERGE-01 | Phase 09 | Complete |
| TMERGE-02 | Phase 09 | Complete |
| TMERGE-03 | Phase 09 | Complete |
| TMERGE-04 | Phase 09 | Complete |
| TMERGE-05 | Phase 10 | Complete |
| TMERGE-06 | Phase 10 | Complete |
| TMERGE-07 | Phase 10 | Complete |
| MEDIA-01 | Phase 11 | Complete |
| MEDIA-02 | Phase 11 | Complete |
| MEDIA-03 | Phase 11 | Complete |
| MEDIA-04 | Phase 11 | Complete |
| GMERGE-01 | Phase 12 | Complete |
| GMERGE-02 | Phase 12 | Complete |
| GMERGE-03 | Phase 12 | Complete |
| GMERGE-04 | Phase 12 | Complete |
| GMERGE-05 | Phase 12 | Complete |
| AISUM-01 | Phase 13 | Complete |
| AISUM-02 | Phase 13 | Complete |
| AISUM-03 | Phase 13 | Pending |
| AISUM-04 | Phase 13 | Complete |
| AISUM-05 | Phase 13 | Complete |
| CLI-01 | Phase 14 | Pending |
| CLI-02 | Phase 14 | Pending |
| CLI-03 | Phase 14 | Pending |
| CLI-04 | Phase 14 | Pending |

**Coverage:**
- v2.0 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after roadmap creation*
