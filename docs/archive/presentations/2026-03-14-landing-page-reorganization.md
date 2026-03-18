# Landing Page Reorganization — WOW First + Meta Retrospective

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the LocaNext landing page so the full product WOW comes first (merged UI + Context Engine), followed by supporting sections, ending with a meta-retrospective showing how AI tools built the page itself.

**Architecture:** Single-file HTML page (`landing-page/index.html`, ~4890 lines). CSS in `<style>`, HTML in `<main>`, JS in `<script>`. GSAP ScrollTrigger for animations, Three.js for hero particles. Nano Banana (python3.11 + Gemini 3 Pro Image) for asset generation, Stitch MCP for UI prototypes.

**Tech Stack:** HTML/CSS/JS, GSAP 3.12, Three.js 0.160, Nano Banana (gemini-3-pro-image-preview), Stitch MCP, Playwright for verification.

**Spec:** `docs/superpowers/specs/2026-03-14-landing-page-reorganization-design.md`

---

## Chunk 1: Asset Generation + Section Reorganization

### Task 1: Generate new Nano Banana assets

**Files:**
- Create: `landing-page/gen-ai-suggestion.png` (AI generating a translation suggestion)
- Create: `landing-page/gen-missing-asset.png` (placeholder → generated image transition)
- Create: `landing-page/gen-voice-synth.png` (audio waveform being generated)

- [ ] **Step 1: Generate AI suggestion visualization image**

```bash
python3.11 -c "
from google import genai
from google.genai import types
import os
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
response = client.models.generate_content(
    model='gemini-3-pro-image-preview',
    contents='A futuristic holographic UI panel showing AI translation suggestions for a game localization tool. Dark background (#050508), warm copper accent lines. Three floating suggestion cards with Korean and English text, confidence percentage bars glowing amber. Translucent panels, no glassmorphism, clean data-driven aesthetic. 16:9, cinematic UI concept art.',
    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE']),
)
for part in response.candidates[0].content.parts:
    if part.inline_data:
        with open('landing-page/gen-ai-suggestion.png', 'wb') as f:
            f.write(part.inline_data.data)
        print('SUCCESS')
"
```

- [ ] **Step 2: Generate missing-asset auto-generation visualization**

```bash
python3.11 -c "
from google import genai
from google.genai import types
import os
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
response = client.models.generate_content(
    model='gemini-3-pro-image-preview',
    contents='A split-screen visualization showing AI image generation process. Left side: a grayed-out placeholder with question mark and metadata text (item name, category). Right side: a fully rendered fantasy game sword materializing from particles. Warm copper/amber glow on dark near-black background. Data flowing from left to right. Cinematic, futuristic UI style. 16:9.',
    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE']),
)
for part in response.candidates[0].content.parts:
    if part.inline_data:
        with open('landing-page/gen-missing-asset.png', 'wb') as f:
            f.write(part.inline_data.data)
        print('SUCCESS')
"
```

- [ ] **Step 3: Generate voice synthesis visualization**

```bash
python3.11 -c "
from google import genai
from google.genai import types
import os
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
response = client.models.generate_content(
    model='gemini-3-pro-image-preview',
    contents='A futuristic audio synthesis interface. Dark background (#050508). A glowing amber waveform being generated in real-time from Korean script text floating above. Sound waves emanating from a holographic speaker icon. Progress bar at 67%. Clean, dark UI with warm copper accents. Cinematic concept art style. 16:9.',
    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE']),
)
for part in response.candidates[0].content.parts:
    if part.inline_data:
        with open('landing-page/gen-voice-synth.png', 'wb') as f:
            f.write(part.inline_data.data)
        print('SUCCESS')
"
```

- [ ] **Step 4: Verify all images generated**

```bash
ls -lh landing-page/gen-ai-suggestion.png landing-page/gen-missing-asset.png landing-page/gen-voice-synth.png
```
Expected: 3 files, each 400KB-1MB.

- [ ] **Step 5: Commit assets**

```bash
git add landing-page/gen-ai-suggestion.png landing-page/gen-missing-asset.png landing-page/gen-voice-synth.png
git commit -m "feat: generate Nano Banana assets for AI suggestions + missing asset visualization"
```

### Task 2: Reorganize HTML sections — merge UI Showcase + Context Engine

The core reorganization. Move the Context Engine HTML (Section 05, watermark "05") to directly follow the UI Showcase (Section 02, watermark "02"), making them one continuous section. Then move Problem/Solution (currently Section 01, watermark "01") to after the merged showcase.

**Files:**
- Modify: `landing-page/index.html` (HTML structure: lines ~2880-3620)

- [ ] **Step 1: Read current section boundaries**

Read the file to identify exact line numbers for:
- Section "01" Problem/Solution: `id="problems"`
- Section "02" UI Showcase: `id="showcase"`
- Section "03" Pipeline: `id="pipeline"`
- Section "04" Architecture: `id="arch"`
- Section "05" Context Engine: `id="ctxEngine"`
- Section "06" Analytics: `id="analytics"`
- Section "07" Power Stack: `id="powerStack"`

- [ ] **Step 2: Cut Context Engine section from position 05**

Remove the entire Context Engine section (from `<!-- CONTEXT ENGINE -->` comment through closing `</section>`) including its `<div class="divider-diagonal"></div>`.

Save the cut content to a temporary reference — we'll paste it into position.

- [ ] **Step 3: Paste Context Engine immediately after UI Showcase**

Insert the Context Engine HTML right after the UI Showcase `</section>` tag, before Pipeline. This creates the mega showcase flow:
- Hero → Ticker → **UI Showcase → Context Engine (merged)** → Problem/Solution → Pipeline → ...

- [ ] **Step 4: Move Problem/Solution after the merged showcase**

Cut the Problem/Solution section and paste it after the Context Engine, before Pipeline. New order:
- Hero → Ticker → **UI Showcase → Context Engine** → Problem/Solution → Pipeline → Architecture → Analytics → Power Stack → Closing

- [ ] **Step 5: Renumber watermarks**

Update all `<div class="section-watermark">` numbers:
- UI Showcase: 01 (was 02)
- Context Engine: stays within 01 (no watermark, or "01" continued)
- Problem/Solution: 02 (was 01)
- Pipeline: 03 (unchanged)
- Architecture: 04 (unchanged)
- Analytics: 05 (was 06)
- Power Stack: 06 (was 07)

- [ ] **Step 6: Verify HTML structure is valid**

Open in browser, check no broken nesting. Scroll through all sections.

```bash
cd landing-page && python3 -m http.server 8765 &
```

- [ ] **Step 7: Commit reorganization**

```bash
git add landing-page/index.html
git commit -m "refactor: reorganize landing page — WOW showcase first, Problem/Solution after"
```

### Task 3: Fix GSAP ScrollTrigger references after reorganization

After moving sections, ScrollTrigger selectors that reference `#ctxEngine`, `#showcase`, etc. may fire in wrong order or with wrong start positions.

**Files:**
- Modify: `landing-page/index.html` (JS: lines ~4100-4800)

- [ ] **Step 1: Audit all ScrollTrigger triggers**

Search for all `trigger:` references in the JS and verify each still points to an element that exists in the new DOM order.

```bash
grep -n "trigger:" landing-page/index.html | grep -v "//"
```

- [ ] **Step 2: Adjust start percentages if needed**

Context Engine animations previously triggered at `start: 'top 55%'`. Since it's now earlier in the page (right after UI Showcase), the start values should still work since they're relative to the element's own position.

Verify by scrolling through in browser — each animation should trigger as the section enters viewport.

- [ ] **Step 3: Commit fixes**

```bash
git add landing-page/index.html
git commit -m "fix: adjust ScrollTrigger references after section reorganization"
```

---

## Chunk 2: New Sub-Scenes + Retrospective

### Task 4: Build AI Auto-Suggestions sub-scene

New content within the merged showcase section, after Entity Detection and before Character Profile.

**Files:**
- Modify: `landing-page/index.html` (CSS: add ~80 lines, HTML: add ~60 lines, JS: add ~20 lines)

- [ ] **Step 1: Add CSS for suggestion cards**

Insert after the existing `.ctx-scene` styles. New classes:
- `.suggestion-card` — translation/naming suggestion card
- `.suggestion-score` — confidence percentage
- `.context-summary` — AI-generated context summary box
- `.category-cluster` — category visualization tags

- [ ] **Step 2: Add HTML for AI suggestions sub-scene**

Insert as a new `.ctx-scene` after Scene 02 (Entity Detection), before Scene 03 (Audio). Structure:
- Left: description text + tags
- Right: visual panel with:
  - 3 translation suggestion cards (KR→EN with confidence scores)
  - 2 naming suggestion cards for game devs
  - Context summary box (2-line AI-generated summary)
  - Category cluster tags

- [ ] **Step 3: Add scroll-reveal animation**

The existing `.ctx-scene` gsap reveal applies to all scenes automatically (line ~4540):
```js
document.querySelectorAll('.ctx-scene').forEach(function(scene) {
    gsap.to(scene, { opacity: 1, y: 0, ... });
});
```
No additional JS needed — the new scene inherits the animation.

- [ ] **Step 4: Verify in browser**

Scroll to the new sub-scene. Cards should fade in on scroll.

- [ ] **Step 5: Commit**

```bash
git add landing-page/index.html
git commit -m "feat: add AI auto-suggestions sub-scene with translation + naming cards"
```

### Task 5: Build Missing Asset Auto-Generation sub-scene

Shows how LocaNext auto-generates missing images (via Nano Banana) and missing audio (via AI voice synthesis).

**Files:**
- Modify: `landing-page/index.html` (CSS: ~60 lines, HTML: ~80 lines, JS: ~30 lines)

- [ ] **Step 1: Add CSS for auto-generation visualization**

- `.autogen-panel` — split panel (before/after)
- `.autogen-before` — grayed placeholder with metadata
- `.autogen-after` — generated result with glow
- `.autogen-badge` — "AI-GENERATED" tag
- `.autogen-arrow` — animated arrow from before→after

- [ ] **Step 2: Add HTML for auto-generation sub-scene**

Two sub-panels:
1. **Image generation:** metadata input → Nano Banana → generated image (use `gen-missing-asset.png`)
2. **Voice synthesis:** script text → AI engine → waveform (use `gen-voice-synth.png`)

Each has: "NOT AVAILABLE" placeholder on left, animated arrow, generated result on right with "AI-GENERATED" badge.

- [ ] **Step 3: Add entrance animation with staggered reveal**

Left panel appears first, arrow animates, right panel fades in with the generated result. Use GSAP timeline triggered on scroll.

- [ ] **Step 4: Verify in browser**

- [ ] **Step 5: Commit**

```bash
git add landing-page/index.html
git commit -m "feat: add missing asset auto-generation sub-scene (Nano Banana + voice synthesis)"
```

### Task 6: Build "How We Built This" retrospective section

Replace the abstract AI Power Stack with a storytelling retrospective.

**Files:**
- Modify: `landing-page/index.html` (CSS: ~100 lines, HTML: ~120 lines, JS: ~40 lines)

- [ ] **Step 1: Add CSS for retrospective timeline**

- `.retro-timeline` — vertical timeline with steps
- `.retro-step` — individual step (icon + title + description + tool badge)
- `.retro-image-grid` — grid showing all 6+ Nano Banana generated images
- `.retro-bridge` — transition section connecting to product value
- `.retro-stat` — "half a day" / "6 images" / "1 dashboard" stats

- [ ] **Step 2: Rewrite Power Stack section HTML**

Keep the orbit visualization and synergy cards (they still work). Add ABOVE them:

**Part A: The Retrospective**
- Headline: "이 페이지는 반나절 만에 완성되었습니다"
- Timeline: 6 steps (Brainstorm → Prototype → Generate Art → Build → Review → Deploy)
- Each step shows tool used (Claude Code, Stitch, Nano Banana, Viking, Reviewer Agent)
- Image grid: thumbnails of all generated Nano Banana images

**Part B: The Bridge**
- "The same AI synergy powers LocaNext for your team"
- 3 cards: Translators / Designers / Game Devs — each with specific value proposition

- [ ] **Step 3: Add timeline animation**

Steps reveal one by one on scroll. Image grid fades in with stagger. Bridge cards slide up.

- [ ] **Step 4: Verify in browser at 1440px**

- [ ] **Step 5: Commit**

```bash
git add landing-page/index.html
git commit -m "feat: add retrospective section — how AI tools built this page in half a day"
```

### Task 7: Final polish, responsive fixes, and review

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Verify responsive at 1440px, 1024px, 768px**

Use Playwright to resize and screenshot at each breakpoint.

- [ ] **Step 2: Run code-reviewer agent on changes**

Dispatch the superpowers:code-reviewer agent focused on the new/modified code.

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Take final full-page screenshot**

```bash
# Start server, navigate with Playwright, take fullPage screenshot
```

- [ ] **Step 5: Update memory files**

Update `landing_page_session.md` and `session_handoff_20260314b.md` with final state.

- [ ] **Step 6: Final commit**

```bash
git add landing-page/index.html
git commit -m "polish: responsive fixes and review cleanup for landing page v5"
```
