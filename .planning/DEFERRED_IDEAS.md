# Deferred Ideas — Future Phases / Milestones

> Ideas captured during planning sessions. Not in scope for current work, but documented so nothing gets lost.

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

---

## Auto-Generation for Missing Assets (v2+ Milestone)

### 4. Auto-Generate Missing Images with Nano Banana
If an image/texture isn't available for a StringID, automatically generate a **placeholder from metadata + context** using Gemini image generation (Nano Banana skill). Visual context even when assets are incomplete.

### 5. Auto-Generate Missing Audio with AI Voice Synthesis
If voice audio isn't available, generate it from the **script text using a state-of-the-art fast voice synthesis engine**. Translators hear the tone/delivery even before recording happens.

---

## Glossary & Entity Detection Expansion

### 6. Auto-Implementation of Glossary Analysis
Aho-Corasick runs **automatically on every string**, not just on demand. Benefits BOTH translators AND game developers writing new data in XML. Real-time entity/glossary detection as you type.

---

## Game Dev Platform (Major Expansion — New Milestone)

### 7. Game Dev Grid
A grid mode **designed for game developers**, allowing them to open complex XML staticinfo data type files directly. Targets the game dev workflow, not just localization.

**Research starting point:** QACompiler data generators already know how to parse and read XML game data files. Use that knowledge:
- `RFC/NewScripts/QACompilerNEW/` — data generators (Item, Character, Region, Skill)
- XML staticinfo parsing patterns
- Complex nested data structures
- Join key resolution across multiple XML files
- **Staticinfo indexing** — QACompiler generators index staticinfo data, same approach reusable here

**Vision:** LocaNext expands from **Localization Team Platform (CAT Tool)** to also serve as a **Game Dev Platform Tool** for working directly on game data files.

**Key Questions to Explore (Matrix for future discussion):**
- Which XML data types should Game Dev Grid support first? (Items? Characters? Skills?)
- Read-only view or full edit+save capability?
- How does Game Dev Grid interact with the existing File Explorer and TM tree?
- Should Game Dev Grid show relationships between entities (e.g., item used in quest, character appears in region)?
- Does this need its own app/tab or integrate into the existing editor view?
- Validation rules for game data (required fields, valid ranges, FK integrity)?
- How do game devs authenticate vs localization team? Same permissions model?

---

## AI Infrastructure (Shared Foundation for All AI Features)

### LLM API Endpoint
All AI features (suggestions, naming, summaries) need a **local LLM endpoint** for analysis:
- **Model options:** Llama, Qwen, DeepSeek (distilled) — any powerful free model
- **Requirement:** Must work offline for demo (local inference)
- **Purpose:** Context analysis, translation suggestions, coherence checking, naming suggestions, description analysis
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
- End-to-end demo: game dev opens a file → sees AI context summaries → gets naming suggestions → coherence warnings for similar items

---

## Technology Stack Summary

```
QACompiler Data Generators → Parse XML game data
         ↓
Aho-Corasick Automaton → Real-time entity detection
         ↓
Model2Vec + FAISS → Semantic similarity / embedding index
         ↓
LLM Endpoint (local) → Context analysis, suggestions, summaries
         ↓
LocaNext UI → Show suggestions, context panels, coherence warnings
```

All pieces exist in the codebase or are proven technology. Implementation is assembly + UI, not invention.

---

*Captured: 2026-03-14 during Phase 1 planning session*
*Updated: 2026-03-14 with expanded AI infrastructure details, Game Dev coherence vision, LLM endpoint requirements, and mock data strategy*
*Source: User vision dumps (2 sessions)*
*Status: Documented for future milestone planning (/gsd:new-milestone)*
