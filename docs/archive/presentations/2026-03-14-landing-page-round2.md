# Landing Page Round 2 — Feedback Implementation Plan

**Goal:** Fix 3 issues from executive feedback: dull Translator page, game-like Codex, incomplete AI stack.

**Reference:** Game Dev page ("게임 개발자가 직접 작성합니다") = the gold standard. Everything must match this quality.

---

## Task 1: Rebuild Translator Mockup (THE BIG ONE)

The current translator section uses the old mockup from v3. It needs to be as detailed and impressive as the Game Dev grid.

**What to build:** A massive 3-panel translator interface mockup similar to the Game Dev grid structure:

- **Left panel: File Explorer**
  - Simple tree: Platform → Project → `languagedata_ENG.xml`
  - Show file list with language codes (KR, EN, CN, TW, etc.)
  - Active file highlighted

- **Center panel: Translation Grid** (bigger, more detailed)
  - More columns visible: StringID, Category, StrOrigin (KR), Str (EN), Status, TM Match%
  - 10+ rows of data with varied status badges
  - Active row with pulsing copper glow
  - Inline QA indicators per cell (✓ spell, ✓ grammar, ⚠ glossary)

- **Right panel: Context + AI Assistant** (split into sub-sections)
  - Image tab: Nano Banana game scene with metadata
  - Audio tab: waveform + KR/EN scripts
  - AI tab: translation suggestions with scores + context summary
  - QA summary: spell check ✓, grammar ✓, glossary 80%, term consistency ✓

**Animation:** Row selection walks, tab cycling, TM scores counting up, QA checks appearing

**CSS:** Match the Game Dev grid's 3-column layout, copper border glow, perspective tilt, deep shadow

### Steps:
- [ ] Replace the current `#showcase` section's mockup HTML with the new 3-panel layout
- [ ] Add file explorer on the left (simple: platform/project/file)
- [ ] Expand translation grid with more columns and rows
- [ ] Add AI/QA panel on the right (tabbed: Image, Audio, AI, QA)
- [ ] Add GSAP workflow animation
- [ ] Apply bolder CSS (copper glow, perspective, deep shadow)

---

## Task 2: Rebuild Codex as Professional Svelte-like UI

Replace the RPG-style Nano Banana images with a clean, professional HTML mockup that matches the Game Dev page aesthetic.

**What to build:**

- **Top: Search bar + category tabs** (keep existing HTML — already good)
- **Left panel: Interactive Map** — NOT an RPG image. Build as HTML/CSS with:
  - Region nodes as styled divs with Korean labels
  - Connection lines as CSS/SVG
  - Hover highlighting
  - Clean, data-driven aesthetic (like a network graph, not a fantasy map)
- **Right panel: Encyclopedia Entry** — Build as HTML like the Game Dev grid:
  - Character/item profile card
  - Stats grid (gender, age, job, race)
  - Connected quests/items list
  - Voice lines section
  - File path breadcrumb (staticinfo > characterinfo > NPC_ELDER)
- **Bottom: File Relationship Graph** (keep existing HTML — already professional)
- **Cards below:** Replace Nano Banana image cards with cleaner styled cards (icon + text, no full images)

### Steps:
- [ ] Replace `gen-codex-full.png` hero with HTML network map
- [ ] Replace `gen-codex-map.png` with HTML/CSS region graph
- [ ] Build encyclopedia entry as HTML right panel
- [ ] Restyle cards to be icon-based, not image-based
- [ ] Apply same bolder CSS as Game Dev section

---

## Task 3: Expand AI Tool Ecosystem

Add more tools to the orbit visualization and restructure to show full breadth.

**Add to orbit/list:**
- UI/UX Pro Max (67 styles, 96 palettes)
- ElevenLabs (voice synthesis)
- GetShitDone (GSD project management)
- Superpowers Skills (brainstorming, planning, reviewing)
- Code-reviewer agents
- Playwright (testing/verification)
- Deep Research (web research synthesis)

**Approach:** The 6-node orbit may be too small. Consider:
- Option A: Increase to 8-10 nodes in the orbit
- Option B: Keep orbit small (core 6) + add a "full stack" list/table below showing all tools
- Option C: Two orbit rings — inner (core AI engines) + outer (development tools)

### Steps:
- [ ] Add ElevenLabs + UI/UX Pro Max to orbit nodes (minimum)
- [ ] Add a "full stack" section below orbit listing all tools with categories
- [ ] Update synergy cards to reference more tools

---

## Task 4: Polish Pass (after Tasks 1-3)

- [ ] Run `polish` skill for spacing/alignment consistency
- [ ] Run `audit` skill for accessibility
- [ ] Run `code-reviewer agent` on new code
- [ ] Playwright verification at 1440px
- [ ] Copy to Desktop for browser testing

---

## Synergy Stack (per power-stack.md playbook)

```
DESIGN:  ui-ux-pro-max → frontend-design
BUILD:   frontend-design → animated-component-libraries
EFFECTS: animate → GSAP scroll animations
IMAGES:  nano-banana (only for accent images, NOT for UI mockups)
POLISH:  bolder → polish → critique
REVIEW:  code-reviewer agent + audit skill
VERIFY:  Playwright MCP
CONTEXT: Viking (QACompiler research, power-stack playbook)
```
