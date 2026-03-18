# Landing Page Reorganization — WOW First + Meta Retrospective

## Problem

The current landing page splits the LocaNext interface showcase across Section 02 (UI mockup) and Section 05 (Context Engine), diluting the impact. The AI Power Stack section showcases tools abstractly rather than demonstrating them in action. Users should see the full product WOW immediately, then learn how it was built.

## New Page Structure

### Section 01: Hero (unchanged)
Three.js particle sphere, typewriter title, language constellation, CTA.

### Section 02: THE MEGA SHOWCASE (merged + expanded)
One continuous scroll-pinned cinematic experience combining the current UI Showcase and Context Engine into a unified product demo.

**Sub-scenes (scroll-triggered transitions):**

1. **Translation Grid** — full interface mockup with sidebar, tabs, translation rows, status badges. TM matches panel auto-populates as user "selects" a row.

2. **Context Engine** — the selected string triggers:
   - Image tab: Nano Banana game scene (existing `gen-ruins-scene.png`)
   - Audio tab: waveform player with KR/EN scripts
   - AI tab: FAISS vector search results with similarity scores

3. **Entity Detection** — Aho-Corasick highlights entities in the string. Resolution arrows show each entity mapping to image/audio/profile. Inline Nano Banana thumbnails.

4. **AI Auto-Suggestions** — new sub-scene:
   - Translation suggestion cards (3-4 options with confidence scores)
   - Naming suggestions for game devs (item/character name alternatives)
   - Context summary: AI-generated 2-line summary of the game context
   - Category clustering visualization

5. **Missing Asset Auto-Generation** — new sub-scene:
   - "Image not available" → Nano Banana generates a placeholder from metadata
   - Show: metadata input → loading animation → generated image appears
   - "Audio not available" → AI voice synthesis creates voice line from script
   - Show: script text → waveform generating → playback ready
   - Tag: "AI-GENERATED" badge on auto-created assets

6. **Character Profile** — existing Scene 01 (Elder Varon with Nano Banana portrait)

7. **5-Tier Cascade Search** — existing Scene 04 (T1-T5 visualization)

**Scroll behavior:** Section 02 is NOT scroll-pinned. Each sub-scene is a separate block that scroll-reveals (opacity+y, like current scenes). Transitions: fade-in on enter (gsap `once:true`). On mobile (<768px), sub-scenes stack vertically with reduced spacing. This avoids the complexity and mobile issues of a long pinned section.

### Section 03: Problem → Solution (moved from position 01)
Same content. Moved after the WOW so visitors already know what LocaNext does before seeing the problems it solves. The "solution" column now references what they just saw.

### Section 04: Pipeline (5-step horizontal flow)
Unchanged. Shows data flow from input to export.

### Section 05: Architecture (client/server + tech stack + licensing)
Unchanged. Stats, tech table, MIT/Apache licensing.

### Section 06: Analytics Dashboard (enterprise monitoring)
Unchanged. Stitch preview + 7 animated cards + Nano Banana holographic bg.

### Section 07: "How We Built This" — Meta Retrospective + AI Synergy
Reframe from abstract tool list to storytelling:

**Part A: The Retrospective**
- Headline: "이 페이지는 반나절 만에 완성되었습니다" (This page was built in half a day)
- Timeline visualization: concept → design → images → code → review → deploy
- Each step shows which tool was used:
  - Brainstorming: Claude Code + Superpowers skills
  - UI Prototyping: Stitch MCP → 2560px dashboard generated
  - Game Art: Nano Banana → 6 images generated (show grid of all generated images)
  - Context Research: Viking semantic search → 93 docs, 727 embeddings
  - Design Review: Automated code-reviewer agent
  - Implementation: Claude Code CLI with 13+ design skills

**Part B: The Bridge**
- "The same AI synergy powers LocaNext for your team"
- Translators: auto-suggestions, context summaries, TM matching
- Designers: auto-generated missing assets, visual context
- Game Devs: naming suggestions, entity detection, glossary management

**Part C: Orbit Visualization** (existing, enhanced)
- Keep the 6-node orbit with LocaNext hub
- Add Nano Banana cosmic background
- Synergy workflow cards at bottom

### Section 08: Closing (grand finale)
Unchanged. CTA + LocaNext watermark.

## Implementation Approach

### Phase 1: Generate new assets FIRST
- Nano Banana: "asset generation in progress" animation frame
- Nano Banana: AI-generated game item from metadata context
- Stitch: timeline/retrospective mockup
- These are needed before building the sub-scenes that reference them

### Phase 2: Reorganize existing sections
- Move Context Engine content into Section 02 (after UI Showcase)
- Move Problem/Solution to Section 03
- Renumber watermarks (01→01, 02→02, etc.)
- Remove old Section 05 Context Engine (content moved to 02)
- Adjust all ScrollTrigger references

### Phase 3: Build new sub-scenes
- AI Auto-Suggestions sub-scene (translation cards, naming cards, context summary)
- Missing Asset Auto-Generation sub-scene (Nano Banana + voice synthesis visualization)

### Phase 4: Build retrospective section
- Timeline visualization
- Tool showcase with generated image grid
- Bridge content connecting to product value

### Phase 5: Polish + review
- Run design critique agent
- Verify responsive breakpoints
- Screenshot verification with Playwright

## Tools Used (Full Synergy)
- **Viking**: Context research before building
- **Nano Banana**: Generate all missing visual assets
- **Stitch MCP**: Generate UI prototypes for new sub-scenes
- **UI/UX Pro Max + design skills**: Design quality
- **Code-reviewer agent**: Automated review
- **Playwright**: Visual verification

## Success Criteria
- Single continuous WOW experience in Section 02
- Retrospective section tells the story of building this page
- All CSS placeholder scenes replaced with Nano Banana images
- Responsive at 1440px, 1024px, 768px
- GSAP animations smooth (no layout thrash)
- Page loads under 3s on broadband (lazy-load images)
