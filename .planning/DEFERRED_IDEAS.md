# Deferred Ideas — Future Phases / Milestones

> Ideas captured during planning sessions. Not in scope for current work, but documented so nothing gets lost.
> **For GSD:** Use `/gsd:discuss-phase` with these ideas as input when planning future milestones.
> **For Viking:** These ideas are indexed — `viking_search("game dev grid codex")` will find them.
> **Last cleaned:** 2026-03-18

## Status Key
- DONE = implemented in a shipped milestone
- PARTIAL = partially implemented
- OPEN = not started
- DROPPED = no longer needed

---

## Status of Original Ideas

| # | Idea | Status | Where |
|---|------|--------|-------|
| 1 | AI Translation Suggestions | **DONE** | v3.0 Phase 17 |
| 2 | AI Naming Suggestions | **DONE** | v3.0 Phase 21 |
| 3 | Context Summary Generation | **DONE** | v2.0 Phase 13 |
| 4 | AI Autocorrection & Writing Quality | **OPEN** | — |
| 5 | Auto-Generate Missing Images | **PARTIAL** | v3.2 Phase 31 (Codex only) |
| 6 | Auto-Generate Missing Audio (TTS) | **PARTIAL** | v3.5 Phase 41 (backend only) |
| 7 | Auto Glossary Analysis | **PARTIAL** | v4.0 Phase 44 (33 entities, on row select) |
| 8 | Game Dev Grid | **DONE** | v3.0 Phase 18 |
| 9 | Codex Encyclopedia | **DONE** | v3.0 Phase 19 + v3.5 Phase 39 |
| 10 | Interactive World Map | **DONE** | v3.0 Phase 20 + v3.5 Phase 38 |

## DROPPED Ideas
- ~~Multilingual stringtable (6 languages)~~ — NOT NEEDED. Architecture: 1 project per language, each with language-specific languagedata files.

---

## AI-Powered Translation & Content (v2+ Milestone)

### 1. AI Translation Suggestions
AI analyzes context, character tone, game genre and proposes **ranked translation options with confidence scores**. Not just TM matching — actual AI-generated alternatives. Goes beyond fuzzy matching into creative suggestion territory.

**How it works:**
- Use **Model2Vec embeddings** to find similar items/weapons/descriptions in the indexed data
- Use **LLM endpoint** (Llama/Qwen/DeepSeek distilled — any free powerful model) to analyze context and generate alternatives
- Confidence scores based on embedding similarity + LLM certainty
- Show in editor as ranked suggestions with scores

### 2. AI Naming Suggestions for Game Devs
Auto-suggest item/character name alternatives for original text authors working on multilingual content. Targets game developers writing new data, not just translators.

**Coherence through context:**
- When a game dev creates a new item/weapon/character, vector embeddings check for **similar existing entities** (similar weapons, similar items, similar descriptions)
- AI suggests names that are **coherent** with existing naming patterns in the game
- Prevents naming inconsistencies across thousands of entities

### 3. Context Summary Generation
AI generates a **2-line contextual summary** for each string: quest context, tone, genre, where it appears in-game. Gives translators instant understanding without hunting through game files.

**Parent node context inheritance:**
- A NODE within a bigger REGION already has a description/context
- AI summarizes the **full parent hierarchy** — the region, the quest chain, the character involvement
- Both translators AND game devs get immediate context for any string they're working on
- Fully summarized by AI to help game devs **write coherently** within the established world

### 4. AI Autocorrection & Writing Quality for Game Devs
When a game dev writes or modifies data, AI provides **real-time quality feedback**:
- Spell check, grammar check, writing quality check
- Glossary inconsistency detection (via Aho-Corasick — is this name already used differently?)
- Style consistency (does this description match the tone of similar items?)
- AI-suggested corrections with explanations

---

## Auto-Generation for Missing Assets (v2+ Milestone)

### 5. Auto-Generate Missing Images with Nano Banana
If an image/texture isn't available for a StringID, automatically generate a **placeholder from metadata + context** using Gemini image generation (Nano Banana skill). Visual context even when assets are incomplete.

### 6. Auto-Generate Missing Audio with AI Voice Synthesis
If voice audio isn't available, generate it from the **script text using a state-of-the-art fast voice synthesis engine**. Translators hear the tone/delivery even before recording happens.

---

## Glossary & Entity Detection Expansion

### 7. Auto-Implementation of Glossary Analysis
Aho-Corasick runs **automatically on every string**, not just on demand. Benefits BOTH translators AND game developers writing new data in XML. Real-time entity/glossary detection as you type.

---

## QA Pipeline Integration

### 8. QuickCheck Integration (Term Check + Line Check)
Integrate QuickCheck's proven QA capabilities directly into the LocaNext pipeline:
- **Term Check:** Glossary term in source but missing in translation → flagged (dual Aho-Corasick + noise filter)
- **Line Check:** Same source translated differently → flagged as inconsistency
- Both run automatically in the editor, not as a separate tool
- Results shown in a dedicated QA panel/tab within the editor
- **Research:** `RFC/NewScripts/QuickCheck/core/term_check.py` and `core/line_check.py`

> Note: Already partially planned in Phase 5.1 (CTX requirements). This deferred idea expands the scope to include the full QA pipeline for game devs too, not just translators.

---

## Game Dev Platform (Major Expansion — New Milestone)

### 9. Game Dev Grid
A specialized interface **designed for game developers**, allowing them to open complex XML staticinfo data type files directly. NOT just a translation grid — a full game dev authoring experience.

**What game devs do (that's different from translators):**
- **CREATE** new parent or children items/knowledge data (not just edit existing)
- **Write** Name, DESC, and other attributes for new entities
- **Modify** existing knowledge data (change names, descriptions, attributes)
- **Nest** new children under parent knowledge data (e.g., new item under a category)
- Need to understand the **full XML structure** — not just strings

**Concrete wow-effect demo scenario:**
1. Game dev opens a staticinfo XML file in Game Dev Grid
2. Sees existing knowledge data with Name, DESC, attributes beautifully displayed
3. **Modifies** a name or description of existing data → sees AI suggestions, spell check, glossary consistency warnings in real-time
4. **Creates** a new child knowledge data under a parent → writes Name, DESC, other attributes
5. AI shows context from parent hierarchy, suggests coherent naming, checks for duplicates
6. QA capabilities active: spell check, grammar, writing quality, glossary inconsistency
7. Images and audio shown inline for context (auto-generated if missing)
8. All changes validated against XML schema before save

**Research starting point — CRITICAL:**
- `RFC/NewScripts/QACompilerNEW/` — data generators (Item, Character, Region, Skill)
- **Deep-dive QACompiler generators** to understand XML staticinfo parsing patterns
- How we read complex nested XML structures
- Join key resolution across multiple XML files
- Staticinfo indexing patterns (reusable for Game Dev Grid)
- The generators already know the schema — what attributes exist, what's required, what's optional

**Key Questions for /gsd:discuss-phase (Matrix):**
- Which XML data type to demo first? (Items are visual, Characters have rich metadata)
- Full CRUD or read + edit only for v1?
- How does parent/child creation work in the XML structure?
- Validation rules: what does QACompiler already enforce?
- How to show the parent hierarchy visually?
- Should Game Dev Grid reuse the same grid component as translation or be its own component?
- Permission model: same as translators or separate roles?

---

### 10. Game World Codex (Interactive Encyclopedia)

A **shared interface for both game devs and translators** — a beautifully designed interactive encyclopedia of the game world.

**World Map:**
- Graphically pleasing, interactive **MAP of the game world**
- Cities, villages, regions all displayed with proper positioning
- **Hover** over any location → tooltip with name, description, key NPCs
- **Click** any location → full detail panel with images, linked quests, connected characters
- Data sourced from parsed XML staticinfo (QACompiler Region generator knows all locations)

**Character Codex:**
- Browse/search all characters
- Each character page: name, image, gender, age, job, race, quest appearances, relationships
- Audio samples if available
- All strings where this character appears
- **Search** by name → instant results with full context

**Item Codex:**
- Browse/search all items, weapons, equipment
- Each item page: name, image, description, category, stats
- Similar items shown via Model2Vec embedding similarity
- **Search** by name or description → semantic search finds related items

**Shared Features:**
- Both game devs AND translators can access the Codex
- Game devs use it for **reference while writing** (check existing lore, naming patterns)
- Translators use it for **context while translating** (who is this character? where is this place?)
- All data parsed from staticinfo using QACompiler generator patterns
- Real-time search with Model2Vec embeddings + FAISS index

**Research starting point:**
- QACompiler Region generator for location/map data
- QACompiler Character generator for character metadata
- QACompiler Item generator for item data
- MapDataGenerator for image/audio asset mapping
- Model2Vec for semantic search across all entities

---

## AI Infrastructure (Shared Foundation for All AI Features)

### LLM API Endpoint
All AI features (suggestions, naming, summaries, autocorrection) need a **local LLM endpoint** for analysis:
- **Model options:** Llama, Qwen, DeepSeek (distilled) — any powerful free model
- **Requirement:** Must work offline for demo (local inference)
- **Purpose:** Context analysis, translation suggestions, coherence checking, naming suggestions, description analysis, writing quality assessment
- Zero cloud dependency — consistent with LocaNext's offline-first architecture

### Vector Embedding + Indexing Pipeline
Shared infrastructure across AI features:
- **Model2Vec embeddings** for semantic similarity (already proven in TM matching — 79x faster)
- **FAISS indexing** of all game data (items, characters, regions, skills) — reuse QACompiler staticinfo indexing patterns
- **Aho-Corasick automaton** for real-time entity detection (already planned in Phase 5.1)
- Combined pipeline: Aho-Corasick detects entities → Model2Vec finds similar → LLM analyzes context → suggestions generated

### Mock Data for Demo
Need enough **realistic mock data** to simulate the full AI pipeline:
- Parsed game data (items, characters, regions, skills) from QACompiler generators
- Indexed embeddings for similarity search
- AI auto-analysis producing suggestions
- End-to-end demo scenarios:
  - **Translator:** Opens file → sees AI context summaries → gets translation suggestions → QA flags inconsistencies
  - **Game dev:** Opens staticinfo → modifies data → AI checks coherence → creates new entity → gets naming suggestions
  - **Both:** Browse Codex → search for character → see full context with images/audio

---

## Technology Stack Summary

```
QACompiler Data Generators → Parse XML game data (Item, Character, Region, Skill)
         ↓
Aho-Corasick Automaton → Real-time entity detection (glossary, names, locations)
         ↓
Model2Vec + FAISS → Semantic similarity / embedding index (find similar items/chars)
         ↓
LLM Endpoint (local) → Context analysis, suggestions, summaries, quality checks
         ↓
LocaNext UI → Three interfaces:
  ├── Translation Grid (translators) — existing, enhanced with AI
  ├── Game Dev Grid (game devs) — NEW, XML staticinfo authoring
  └── Codex (both) — NEW, interactive encyclopedia with world map
```

All pieces exist in the codebase or are proven technology. Implementation is assembly + UI, not invention.

---

## Implementation Priority Suggestion

| Priority | Feature | Wow Factor | Effort | Dependencies |
|----------|---------|------------|--------|--------------|
| 1 | Game Dev Grid (basic edit) | HIGH | MEDIUM | QACompiler research |
| 2 | Codex - Character/Item pages | VERY HIGH | MEDIUM | Staticinfo parsing |
| 3 | Codex - World Map | EXTREME | HIGH | Region data + map design |
| 4 | AI Suggestions (translation) | HIGH | MEDIUM | LLM endpoint |
| 5 | AI Naming + Coherence | HIGH | MEDIUM | Embedding index |
| 6 | Auto-gen images/audio | VERY HIGH | HIGH | Nano Banana + voice API |
| 7 | Full QA pipeline | HIGH | LOW | QuickCheck already built |

---

---

## Local AI Generation Models — Remaining Installs (Deferred 2026-03-19)

> **Z-Image Turbo and Hunyuan3D 2 Mini are DONE and production-ready.**
> Remaining models deferred — install when actually needed.

| # | Model | What | VRAM | Install When |
|---|-------|------|------|-------------|
| 3 | **ACE-Step 1.5** | Music generation (full songs, vocals) | <4GB | Landing page Piece 11 (ambient soundscape) |
| 4 | **AudioLDM 2** | Sound effects (whoosh, click, rain) | ~8GB | When adding UI sounds to landing page |
| 5 | **Wan 2.2 5B** | Image-to-video (ambient loops) | ~8GB | When Kling costs too much for ambient video |
| 6 | **CosyVoice 2** | Emotional TTS upgrade | ~6GB | Low priority — Qwen3-TTS works fine |

**Reference:** `docs/reference/FREE_MODEL_MCP_PLAN.md` has full specs, code samples, VRAM budgets for each.
**MCP server:** `scripts/mcp/local_models_mcp.py` — add tools here when installing.
**All Apache 2.0 licensed, all run on RTX 4070 Ti (12GB), all free forever.**

---

---

## UI Polish — LanguageData Grid Default Colors (Noted 2026-03-21)

**Current:** Default row color is yellow (unchecked state) — feels noisy, like everything needs attention.

**Desired:**
- **Grey** (standard/default) — normal, untouched rows. No status set. This is the baseline.
- **Yellow** (needs confirmation) — only when explicitly set by user via hotkey. Means "someone flagged this for review."
- **Blue-green** (confirmed) — confirmed/approved rows. The satisfying "done" color.

**Key change:** Yellow should NOT appear automatically. It must be a deliberate user action (hotkey or button). Default = grey = neutral.

---

*Captured: 2026-03-14 during Phase 1 planning session*
*Updated: 2026-03-14 with Game Dev Grid concrete demo scenario, Codex interactive encyclopedia, world map, QA pipeline integration, and implementation priority*
*Source: User vision dumps (3 sessions)*
*Status: Documented for future milestone planning (/gsd:new-milestone)*
