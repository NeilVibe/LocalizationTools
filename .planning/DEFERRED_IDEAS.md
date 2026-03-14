# Deferred Ideas — Future Phases / Milestones

> Ideas captured during planning sessions. Not in scope for current work, but documented so nothing gets lost.

---

## AI-Powered Translation & Content (v2+ Milestone)

### 1. AI Translation Suggestions
AI analyzes context, character tone, game genre and proposes **ranked translation options with confidence scores**. Not just TM matching — actual AI-generated alternatives. Goes beyond fuzzy matching into creative suggestion territory.

### 2. AI Naming Suggestions for Game Devs
Auto-suggest item/character name alternatives for original text authors working on multilingual content. Targets game developers writing new data, not just translators.

### 3. Context Summary Generation
AI generates a **2-line contextual summary** for each string: quest context, tone, genre, where it appears in-game. Gives translators instant understanding without hunting through game files.

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

*Captured: 2026-03-14 during Phase 1 planning session*
*Source: User vision dump*
*Status: Documented for future milestone planning*
