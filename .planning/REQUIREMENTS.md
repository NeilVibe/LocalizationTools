# Requirements: LocaNext v5.0

**Defined:** 2026-03-21
**Core Value:** Self-sufficient offline bundle with full Codex (Audio/Item/Character/Region) powered by proven NewScripts logic.

## v5.0 Requirements

### INFRA -- Shared Infrastructure

- [x] **INFRA-01**: PerforcePathService with drive/branch config resolves data paths for all Codex types (ported from MapDataGenerator config.py)
- [x] **INFRA-02**: AICapabilityService detects Model2Vec/FAISS/Ollama/TTS availability at startup and exposes runtime status
- [x] **INFRA-03**: AI capability badges shown in settings page; AI-dependent UI sections hide gracefully when engines unavailable

### AUDIO -- Audio Codex

- [x] **AUDIO-01**: Audio Codex page with card grid, search, and category tree navigation
- [x] **AUDIO-02**: AudioIndex chain resolves WEM->EventName->StringId->StrOrigin/KOR/ENG script lines (ported from MapDataGenerator linkage.py)
- [x] **AUDIO-03**: Inline WEM->WAV streaming playback with play/stop/duration and script text overlay
- [x] **AUDIO-04**: Category tree from export folder hierarchy (Dialog/QuestDialog, etc.) for audio browsing

### ITEM -- Item Codex

- [x] **ITEM-01**: Item Codex page with card grid showing DDS images, Korean/translated names, and category badges
- [x] **ITEM-02**: ItemGroupInfo hierarchy for category/group navigation tabs (ported from QACompiler item.py)
- [x] **ITEM-03**: Item detail panel with knowledge resolution (3 passes + InspectData) displayed as tabs
- [x] **ITEM-04**: Text search across Korean name, translated name, StrKey, and description fields

### CHAR -- Character Codex

- [x] **CHAR-01**: Character Codex page with card grid showing portraits, names, and category tabs
- [x] **CHAR-02**: Filename-based grouping (NPC, MONSTER, etc.) for category navigation (ported from QACompiler character.py)
- [x] **CHAR-03**: Character detail panel with Race/Gender/Age/Job fields and knowledge panel
- [x] **CHAR-04**: Text search across character names, StrKey, and attribute fields

### REGION -- Region Codex + Interactive Map

- [x] **REGION-01**: Region Codex page with FactionGroup->Faction->FactionNode tree navigation
- [x] **REGION-02**: Region detail panel with WorldPosition, DisplayName, and knowledge cross-references
- [x] **REGION-03**: Interactive map with real WorldPosition coordinates via d3-zoom (extends existing WorldMap page)
- [x] **REGION-04**: FactionGroup tabs for filtering regions by faction hierarchy

### STRID -- StringID->Audio Integration

- [x] **STRID-01**: Reverse lookup from StringID->AudioIndex->WEM file path for any string with available audio
- [x] **STRID-02**: Inline audio player in LDM translation grid when selecting a row with available audio

### OFFLINE -- Offline Production Bundle

- [ ] **OFFLINE-01**: SQLite-only mode with no PostgreSQL dependency for disconnected machines
- [ ] **OFFLINE-02**: Model2Vec bundled in light build (no Qwen 0.6B, no heavy AI engines)
- [ ] **OFFLINE-03**: vgmstream-cli bundled in Electron extraResources for WEM->WAV conversion
- [ ] **OFFLINE-04**: Factory/Abstraction/Repo pattern audit -- verify all gamedata paths work offline with SQLite
- [ ] **OFFLINE-05**: Fresh-machine smoke test passing (PyInstaller bundle, all core features functional without AI)

## v6.0 Requirements (Deferred)

### Audio Enhancement

- **AUDIO-VRS-01**: VRS chronological ordering for audio entries (quest-order playback)
- **AUDIO-LANG-01**: Multi-language audio folder switching in UI (EN/KR/ZH)

### Region Enhancement

- **REGION-SHOP-01**: Shop + SceneObjectData positions on region map overlay
- **REGION-POS-01**: 3-hop Knowledge_Contents position chain (KnowledgeInfo->UIMapTextureInfo->LevelGimmickSceneObjectInfo)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Audio editing/waveform UI | CAT tool, not audio editor -- simple play/stop/duration only |
| CRUD operations on Codex entities | Read-only encyclopedia; Game Dev Grid handles editing (built in v3.0) |
| Perforce VCS integration (sync/checkout) | Just parse path patterns for file resolution, no VCS coupling |
| Full Qwen AI in offline bundle | 2.3GB defeats light bundle purpose; Model2Vec only |
| Multi-language audio folder switching | 1 project = 1 language; auto-detect from Perforce path |
| MapDataGenerator tkinter GUI porting | Port DATA LOGIC only, build new Svelte 5 UI |
| Real-time audio recording | TTS auto-gen already exists in v3.5 as fallback |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 45 | Complete |
| INFRA-02 | Phase 45 | Complete |
| INFRA-03 | Phase 45 | Complete |
| AUDIO-01 | Phase 48 | Complete |
| AUDIO-02 | Phase 48 | Complete |
| AUDIO-03 | Phase 48 | Complete |
| AUDIO-04 | Phase 48 | Complete |
| ITEM-01 | Phase 46 | Complete |
| ITEM-02 | Phase 46 | Complete |
| ITEM-03 | Phase 46 | Complete |
| ITEM-04 | Phase 46 | Complete |
| CHAR-01 | Phase 47 | Complete |
| CHAR-02 | Phase 47 | Complete |
| CHAR-03 | Phase 47 | Complete |
| CHAR-04 | Phase 47 | Complete |
| REGION-01 | Phase 49 | Complete |
| REGION-02 | Phase 49 | Complete |
| REGION-03 | Phase 49 | Complete |
| REGION-04 | Phase 49 | Complete |
| STRID-01 | Phase 50 | Complete |
| STRID-02 | Phase 50 | Complete |
| OFFLINE-01 | Phase 51 | Pending |
| OFFLINE-02 | Phase 51 | Pending |
| OFFLINE-03 | Phase 51 | Pending |
| OFFLINE-04 | Phase 51 | Pending |
| OFFLINE-05 | Phase 51 | Pending |

**Coverage:**
- v5.0 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Traceability updated: 2026-03-21*
