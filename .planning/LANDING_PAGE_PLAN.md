# Landing Page — CRAFT Phase Plan

> Content complete. Now building the rocket piece by piece.
> Each piece = deep research → autoresearch loop → implement → verify → commit.
> Latest stable: 9874e836 (2026-03-19)

## COMPLETED (6/10 pieces + infra)
- [x] Phase A: Performance (WebP 90% reduction, conditional Three.js, preconnect)
- [x] Phase B: Entrance animation (opacity fade 2.5s, camera pullback 3s, rotation ramp 4s, mesh gradient fade)
- [x] Phase E: Accessibility (cursor fix, aria-labels, contrast #7a7a82)
- [x] Swarm redesign (Queen/Hive/Ralph/Autoresearch + 12 outer nodes + galaxy bg)
- [x] Subtle polish (Lenis, twinkle, color temp, scroll Z drift, CSS refinements)
- [x] Piece 1: Blur-to-sharp section reveals (10px blur, 0.98 scale, 1.2s power3.out)
- [x] Piece 2: Scroll particle color shift (copper→blue, 6% max, quadratic ease)
- [x] Piece 3: Animated gradient borders (CSS @property, hover-only, 6s rotation)
- [x] Piece 4: Magnetic buttons with inner text parallax (0.3 strength, elastic snap)
- [x] Piece 5: Hero background depth layer (second gradient, 45s drift, 3% opacity)
- [x] Piece 6: Animated grain (stepped CSS animation, 4 frames/0.5s)
- [x] AI Power Stack documentation (200 lines, 5-scout research)
- [x] fal-ai MCP configured (restart to activate)

## REMAINING CRAFT PIECES

### Piece 7: Typography motion
Key headings with word-by-word slide-up reveal (Korean word-based split).
GSAP 3.13 SplitText (now free) or manual split function.

### Piece 8: Closing section cinematic
Final section grand finale — particles reconverge, warm glow crescendo.
The "wow this was incredible" moment before the page ends.

### Piece 9: Performance + Lighthouse audit
Run full Lighthouse audit, fix any remaining issues.
Target: 90+ performance, 100 accessibility.

### Piece 10: Mobile polish pass
Ensure premium feel without particles. Typography, spacing, timing.

## AI VIDEO GENERATION (fal-ai MCP — needs restart)

### Hero Video
1. Generate dark atmospheric hero image with Nano Banana 2
2. Animate with Kling 3.0 image-to-video (5s subtle drift)
3. ffmpeg reverse-loop → compress to 720p WebM <2MB
4. Embed as `<video autoplay muted loop playsinline poster="frame.webp">`
5. Layer BEHIND Three.js particles for depth

### Swarm Section Video
Potential: generate animated swarm visualization background with Kling

## QWEN3-VL DEEP RESEARCH (TODO — separate task)

### What We Know
- Model loaded (6.1GB Ollama), configured in OpenViking
- Tested: reads Korean from screenshots, identifies UI elements
- API: POST localhost:11434/api/chat with images: [base64]

### What We Need to Research
- [ ] Optimal image size (512px? 1080px? what's the sweet spot?)
- [ ] Multi-image comparison (send 2 images, ask "what changed?")
- [ ] Speed vs size tradeoff (WebP timed out at 120s, PNG worked — why?)
- [ ] Prompt engineering for structured UI review output
- [ ] OpenViking integration (index screenshots → searchable visual knowledge)
- [ ] Batch pipeline (automated UI audit from multiple screenshots)
- [ ] Output depth (can it identify CSS issues? color contrast? layout problems?)
- [ ] Korean OCR accuracy (how well does it read Korean text in images?)

### Potential Use Cases
1. Automated landing page design review (screenshot → critique)
2. LocaNext UI regression testing (before/after comparison)
3. Game art description for alt text generation
4. Visual documentation of app features
5. Design system compliance checking

## RESEARCH TOOLS
- Autoresearch (5+ competing agents per piece)
- UI/UX Pro Max (design critique before implementing)
- fal-ai MCP (Nano Banana 2, Kling 3.0, Seedance, Veo 3 — 600+ models)
- Stitch MCP (prototype screens)
- Qwen3-VL (local vision analysis)
- brains-trust (second opinion on design decisions)
- Critique skill (audit after each piece)

## FUTURE: Build Local Model MCP Wrappers (ONLY if fal.ai too expensive)
Priority order for building custom MCPs using `mcp-builder` skill:
1. **Z-Image Turbo** (Alibaba, Apache 2.0, 12GB) — free image gen, replaces Nano Banana 2
2. **Wan 2.2 1.3B** (Alibaba, Apache 2.0, 8.2GB) — free video gen, replaces Kling 3.0
3. **ACE-Step 1.5** (Apache 2.0, <4GB) — music gen, UNIQUE (fal.ai can't do this)
4. **Hunyuan3D Mini** (Tencent, Apache 2.0, 5-6GB) — 3D mesh gen, UNIQUE
5. **AudioLDM 2** (Apache 2.0, ~8GB) — sound FX from text, UNIQUE
6. **CosyVoice 2** (Alibaba, Apache 2.0, ~6GB) — streaming TTS with emotions
Each = ~1 hour (Python wrapper + MCP tool definition).
**NOT PRIORITY FOR LANDING PAGE** — fal.ai covers images + video.
Build in a dedicated "local power" session when needed.

## SKIP LIST
- Cursor trail particles (conflicts with existing cursor)
- Radial ambient pulse (conflicts with mesh gradient + sphere)
- Progressive disclosure blur (usability tax)
- defer on scripts (breaks inline execution — learned the hard way)
