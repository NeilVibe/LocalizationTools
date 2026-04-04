# Design Spec: Deep Sea Swarm Trails + 3D LocaNext Logo

**Status:** Open (Layer 12 attempted then reverted 2026-03-20, Layer 13 not started)

> Landing page Layers 12 & 13. Careful, layer-by-layer implementation.

## Layer 12: Deep Sea Bioluminescent Swarm Trails

### What
60-80 boid "fish" particles swimming in formation behind the swarm section canvas, leaving glowing light trails that slowly fade — like long exposure photography of bioluminescent deep sea creatures.

### Where
Behind the existing swarm canvas (`#swarmCanvas`), visible in the AI Swarm section (Part C). A separate Three.js canvas layered behind the 2D swarm canvas, or rendered as a CSS background layer.

### Visual Design

**Bioluminescent Color Palette:**
| Role | Hex | Use |
|------|-----|-----|
| Core glow (brightest) | `#00FFE5` | Particle center, trail head |
| Primary trail | `#00D4FF` | Active trail body |
| Secondary trail | `#007EFF` | Trail fade-out |
| Ambient halo | `#9AFFF7` | Faint outer glow |
| Rare purple (5%) | `#958CF9` | Accent boids for variety |
| Abyss background | `#000208` | Deep sea darkness |

**Movement — Boids Algorithm (Craig Reynolds):**
- Separation: steer away from close neighbors
- Alignment: match velocity of nearby boids
- Cohesion: steer toward center of flock
- MAX_SPEED: 0.8 (slow, drifting — deep sea feel)
- PERCEPTION_RADIUS: 60 (loose flocking)
- SEPARATION_DIST: 15 (generous spacing)
- Vertical sine drift for organic undulation
- Gentle random wandering force

**Light Trails — Ring Buffer:**
- Each boid stores last 20 positions in a ring buffer
- All trails rendered as single BufferGeometry Points (~1400 total points)
- Alpha decreases with age: `alpha = (TRAIL_LENGTH - age) / TRAIL_LENGTH`
- Gaussian falloff in fragment shader for soft glow
- Additive blending (`THREE.AdditiveBlending`)

**Glow Effects:**
- UnrealBloomPass (strength: 1.2, radius: 0.6, threshold: 0.3)
- Pulsing intensity: `0.7 + 0.3 * sin(t * 2.0 + phase)` per boid
- Bloom makes particles glow naturally — no extra work

### Architecture

```
swarm-section container (relative)
  ├── NEW: <canvas id="swarmBioCanvas"> (position: absolute, z-index: 0)
  │   └── Three.js scene: boids + trails + bloom
  └── EXISTING: <canvas id="swarmCanvas"> (position: absolute, z-index: 1)
      └── 2D canvas: 22 agent nodes + connections
```

Separate Three.js canvas for the boids (NOT the hero canvas — different section, different viewport). Lightweight scene: just Points geometry + bloom post-processing.

### Performance Budget
- 60-80 boids: trivial CPU (brute force neighbor search = 3600-6400 distance checks)
- ~1400 trail points: single draw call, trivial for GPU
- Bloom pass: ~2ms overhead
- Total: <4ms per frame — well within 16ms budget
- Boid logic at 30fps, render at 60fps (interpolated positions)

### Implementation Steps
1. Add `<canvas id="swarmBioCanvas">` behind swarmCanvas
2. Init Three.js scene with OrthographicCamera (2D feel in 3D)
3. Create boid class with position, velocity, trail ring buffer
4. Implement boids algorithm (separation/alignment/cohesion)
5. Render all trails as single Points geometry with ShaderMaterial
6. Add UnrealBloomPass
7. Animate at 60fps, update boid logic at 30fps
8. Vision review with Qwen3-VL

---

## Layer 13: 3D LocaNext Logo

### What
"LocaNext" text rendered as 3D geometry in Three.js, materializing in the closing section. Warm emissive glow, scroll-driven rotation.

### Where
Closing section — the text emerges as the user scrolls past the supernova particle morph. Grand finale effect.

### Visual Design

**3D Text:**
- TextGeometry with "LocaNext" (Latin letters)
- Font: Helvetiker (ships with Three.js) or convert Pretendard to Three.js font
- Warm emissive glow matching `--warm: #d49a5c`
- Metallic material with environment reflection
- Depth: moderate extrusion (not paper-thin, not chunky)

**Animation:**
- Opacity: 0 → 1 (fade in as section enters viewport)
- Scale: 0.5 → 1.0 (grow into view)
- Rotation.y: gentle continuous spin + scroll-driven acceleration
- Position.y: float upward slightly
- Existing particles scatter around the text

**Optional Enhancement:**
- Generate a holographic globe/crystal with Hunyuan3D 2 Mini
- Place behind the text as ambient decoration
- Only if TextGeometry alone feels insufficient

### Architecture

Add to the existing hero Three.js scene (NOT a new canvas). The camera path already travels from z=260 to z=500 — position the 3D text at coordinates that become visible at the closing section scroll position.

```
Existing heroCanvas (Three.js)
  ├── Existing: 2500 morph particles
  ├── Existing: bloom + chromatic aberration
  └── NEW: TextGeometry "LocaNext" mesh
      └── Visible only at closing section scroll progress
      └── GSAP ScrollTrigger drives opacity/scale/rotation
```

### Implementation Steps
1. Load font JSON (Helvetiker from Three.js examples, ~100KB)
2. Create TextGeometry "LocaNext" with MeshStandardMaterial (emissive warm glow)
3. Position in scene at coordinates visible during closing section
4. GSAP ScrollTrigger: opacity, scale, rotation driven by scroll
5. Ensure text doesn't appear during other sections (visibility gate)
6. Vision review with Qwen3-VL
7. Optional: Generate Hunyuan3D object, load .glb, place behind text

### Performance Budget
- TextGeometry: ~500-2000 triangles (trivial)
- Font JSON: ~100KB network (one-time load)
- Material: standard PBR, no extra shader passes
- Total: <1ms per frame impact

---

## Implementation Order

**Layer 12 FIRST** (deep sea swarm) → test → commit → **Layer 13** (3D logo) → test → commit

Each layer gets:
1. Implement
2. Screenshot → Qwen3-VL review (free)
3. Fix issues
4. Screenshot → Gemini review (paid, milestone check)
5. Commit

---

## Power Stack

| Tool | Role |
|------|------|
| `particles-gpu` skill | Particle system patterns |
| `gsap-master` skill | ScrollTrigger, animation timing |
| `threejs-pro` skill | Scene setup, TextGeometry, materials |
| `shader-fundamentals` skill | Fragment shader for boid glow |
| `vision-review` skill | Qwen3-VL + Gemini after each layer |
| `code-reviewer` agent | Code quality after implementation |

## Skip List
- Video background for swarm (real-time is better — interactive, no bandwidth)
- Hunyuan3D for text logo (text-to-3D quality is poor)
- React Three Fiber (landing page is vanilla JS)
- Second WebGL context for logo (add to existing scene instead)
