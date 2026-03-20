# Landing Page — CRAFT Phase Plan

> Content complete. Now layering WOW effects one at a time.
> Each layer = hive research → brainstorm → implement → verify → commit.
> **STABLE REVISION: 5664e549 (2026-03-20)** — User approved. Full cinematic pipeline + hero animations.
> Previous stable: ed6832ee (2026-03-19)

## COMPLETED

### Original Pieces (Sessions 2026-03-18/19)
- [x] Phase A: Performance (WebP 90% reduction, conditional Three.js, preconnect)
- [x] Phase B: Entrance animation (opacity fade 2.5s, camera pullback 3s, rotation ramp 4s)
- [x] Phase E: Accessibility (cursor fix, aria-labels, contrast #7a7a82)
- [x] Swarm redesign (Queen/Hive/Ralph/Autoresearch + 22 nodes + galaxy bg)
- [x] Subtle polish (Lenis, twinkle, color temp, scroll Z drift, CSS refinements)
- [x] Piece 1: Blur-to-sharp section reveals
- [x] Piece 2: Scroll particle color shift (copper→blue)
- [x] Piece 3: Animated gradient borders
- [x] Piece 4: Magnetic buttons with inner text parallax
- [x] Piece 5: Hero background depth layer
- [x] Piece 6: Animated grain
- [x] Infra: fal-ai MCP, Local Models MCP, Z-Image Turbo, dependencies

### Cinematic Pipeline (Session 2026-03-20) — 7 commits
- [x] Task 1: ESM import map + bloom post-processing (EffectComposer + UnrealBloomPass)
- [x] Task 2: Chromatic aberration lens shader (radial RGB offset, edge-weighted)
- [x] Task 3: Custom ShaderMaterial (dual-target morph + simplex noise + repulsion)
- [x] Task 4: Morph target generators (text canvas sampling, globe, network, converge)
- [x] Task 5: Scroll-driven particle morphing across all sections
- [x] Task 6: Mouse repulsion via raycaster (80-unit radius, spring-back)
- [x] Task 7: Closing supernova bloom spike + typography motion word reveals

---

## COMPLETED LAYERS (Session 2026-03-20)

### Layer A: Hero Video Generation — DONE (commit 8901e9f1, fixed e35939d8)
**Goal:** Cinematic atmospheric video behind the Three.js particles in the hero section.
**WOW factor:** Adds depth — particles float OVER a subtly moving dark landscape/nebula.

**Power Stack:**
| Tool | Role |
|------|------|
| `fal-ai MCP → mcp__fal-ai__generate` | Generate hero image (Nano Banana 2) |
| `fal-ai MCP → mcp__fal-ai__generate` | Animate image to 5s video (Kling 3.0) |
| `ffmpeg` (bash) | Reverse-loop + compress to 720p WebM <2MB |
| `ui-ux-pro-max` skill | Design review of image prompt + placement |
| `critique` skill | Audit visual integration with particles |

**Steps:**
1. Generate dark atmospheric hero image with Nano Banana 2 (copper/blue palette, abstract)
2. Animate with Kling 3.0 image-to-video (5s subtle drift/nebula motion)
3. ffmpeg reverse-loop → compress to 720p WebM <2MB
4. Embed as `<video autoplay muted loop playsinline poster="frame.webp">`
5. Layer BEHIND Three.js canvas (z-index -1) with low opacity (~0.15)
6. Critique skill: verify it enhances without competing with particles

---

### Layer B: Constellation Glow Field — DONE (commit b4b097f8)
**Goal:** Language nodes in hero react to cursor proximity — glow, energy pulses, attraction.
**WOW factor:** Hero becomes immediately interactive, users discover it and play.

**Power Stack:**
| Tool | Role |
|------|------|
| `gsap-master` skill | ScrollTrigger + proximity animation patterns |
| `awwwards-animations` skill | Award-winning interaction reference |
| `ui-ux-pro-max` skill | Interaction design review |
| `animate` skill | Micro-interaction design |

**Steps:**
1. Cursor proximity detection on 12 language nodes (distance-based intensity)
2. Glow bloom on nearest node (CSS radial gradient, opacity = 1 - distance/maxRadius)
3. SVG connection lines animate with flowing energy pulses toward hovered node
4. Nearby Three.js particles attracted toward hovered node (reverse repulsion)
5. Hovered node label scales up with sample translation tooltip

---

### Layer C: Scroll Velocity Parallax — DONE (commit 795965a6)
**Goal:** Page responds to HOW you scroll — fast = dramatic, slow = gentle.
**WOW factor:** Makes the page feel alive and responsive to user behavior.

**Power Stack:**
| Tool | Role |
|------|------|
| `awwwards-animations` skill | Velocity-aware scroll patterns |
| `gsap-master` skill | ScrollTrigger velocity API |
| Lenis (already loaded) | `lenis.velocity` data source |

**Steps:**
1. Read `lenis.velocity` each frame
2. Modulate particle spread (fast scroll = particles scatter wider)
3. Modulate chromatic aberration (fast scroll = stronger lens distortion)
4. Modulate bloom intensity (fast scroll = brighter glow)
5. Content sections get subtle parallax offset based on velocity

---

### Layer D: Cinematic Camera Path
**Goal:** Scroll drives the Three.js camera along a 3D spline through the particle cloud.
**WOW factor:** Makes it feel like you're flying THROUGH the universe, not looking at it.

**Power Stack:**
| Tool | Role |
|------|------|
| `threejs-pro` skill | CatmullRomCurve3 camera animation |
| `threejs-webgl` skill | Camera path + lookAt targeting |
| `gsap-master` skill | ScrollTrigger scrub for camera progress |
| `shader-fundamentals` skill | Vertex displacement during camera movement |
| `brains-trust` skill | Second opinion on camera path design |

**Steps:**
1. Define CatmullRomCurve3 spline through the scene (hero inside → pull out → orbit → pull way back)
2. GSAP ScrollTrigger maps scroll progress (0→1) to `curve.getPointAt(progress)` for camera
3. Camera lookAt follows a separate slower spline (smooth tracking)
4. Section transitions get dramatic camera angle shifts
5. Performance gate: if camera + morph + bloom > 14ms, simplify path

---

### Layer E: Performance + Lighthouse Audit (Piece 9)
**Goal:** 90+ performance, 100 accessibility on Lighthouse.

**Power Stack:**
| Tool | Role |
|------|------|
| `optimize` skill | Loading speed, rendering, bundle size |
| `audit` skill | Accessibility, performance, responsive |
| Chrome DevTools MCP | Lighthouse audit |
| `harden` skill | Error states, edge cases |

---

### Layer F: Mobile Polish (Piece 10)
**Goal:** Premium feel on mobile without particles. Typography, spacing, timing.

**Power Stack:**
| Tool | Role |
|------|------|
| `adapt` skill | Cross-device responsive design |
| `ui-ux-pro-max` skill | Mobile-specific design review |
| `polish` skill | Alignment, spacing, consistency |
| Playwright MCP | Mobile viewport screenshots |

---

## FUTURE LAYERS (deferred)

### Piece 11: Ambient Soundscape
- Subtle ambient drone (opt-in only, 🔇 toggle, NEVER autoplay)
- Generate with: fal.ai audio models OR ACE-Step (music) + AudioLDM 2 (SFX)

### Swarm Section Video
- Generate animated swarm visualization background with Kling/Seedance

### 3D Product Model
- Hunyuan3D 2 Mini → 3D mesh of LocaNext UI → rotate on scroll
- `local_generate_3d` MCP tool ready

---

## POWER STACK REFERENCE

### Generation (paid — state of the art)
- **fal.ai MCP** — Nano Banana 2 (images), Kling 3.0 (video), Seedance (video), Veo 3 (video)
- **Stitch MCP** — UI layout mockups for design iteration

### Generation (free — local GPU)
- **Z-Image Turbo** — local image gen (10s/image, 6GB VRAM)
- **Hunyuan3D 2 Mini** — local 3D mesh gen (11-29s, 4GB VRAM)

### Design Skills
- `ui-ux-pro-max` — full design intelligence (67 styles, 96 palettes)
- `frontend-design` — production-grade interfaces
- `awwwards-animations` — award-winning scroll/reveal patterns
- `gsap-master` — full GSAP v3 + ScrollTrigger mastery
- `animate` / `bolder` / `polish` / `critique` / `colorize` / `delight` — design polish chain

### 3D/Shader Skills
- `threejs` / `threejs-pro` / `threejs-webgl` — Three.js mastery
- `particles-gpu` — GPU instanced particle systems
- `shader-fundamentals` / `shadertoy` — GLSL shaders
- `r3f-shaders` / `r3f-animation` / `r3f-interaction` — React Three Fiber

### Review Chain (after each layer)
- `critique` skill → `audit` skill → `optimize` skill → `polish` skill

### Vision (local, free)
- Qwen3-VL via OpenViking — screenshot analysis, UI review, Korean OCR

---

## SKIP LIST
- Cursor trail particles (conflicts with existing cursor)
- Radial ambient pulse (conflicts with mesh gradient + sphere)
- Progressive disclosure blur (usability tax)
- defer on scripts (breaks inline execution)
- Ray marching / volumetric fog (too expensive for landing page)
- Fluid simulation (competes with particles visually)
- WebGPU features (not widely supported yet)
