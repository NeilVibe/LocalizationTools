# Particle Morphing Cinematic Pipeline — Implementation Plan

**Status:** Completed (2026-03-19)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the existing 2500-particle sphere into a scroll-driven morphing system with post-processing (bloom + chromatic aberration) and mouse interactivity.

**Architecture:** The current `PointsMaterial` + CPU-side position updates get replaced with a custom `ShaderMaterial` whose vertex shader lerps between two position buffer attributes (`posA` / `posB`) per section. An `EffectComposer` adds bloom and chromatic aberration. Mouse position is unprojected into 3D for particle repulsion. All driven by GSAP ScrollTrigger with `scrub`. Dual-target morph model avoids buffer-swap race conditions — when transitioning between shapes, `posA` gets the current baked positions and `posB` gets the new target, then `uMorph` scrubs from 0→1.

**Tech Stack:** Three.js r160 via import map + `<script type="module">` (required — r160 only ships ESM addons), GSAP 3.12.5 + ScrollTrigger (classic `<script>` tags, accessed via `window.gsap`/`window.ScrollTrigger`), vanilla JS.

**Key Constraint:** The landing page is a single `index.html` (~6800 lines). GSAP/Lenis remain as classic `<script>` tags. The Three.js section becomes a `<script type="module">` block at the bottom. Module scripts can access globals (`gsap`, `ScrollTrigger`, `Lenis`) set by classic scripts above.

**Performance Budget:** After Task 1 (bloom), measure frame time. If >14ms average, halve bloom resolution. After Task 3 (custom shader), measure again. If >14ms, disable chromatic aberration. Never exceed 16ms per frame.

---

## File Map

| File | Action | What |
|------|--------|------|
| `landing-page/index.html` | Modify | CSS additions + Three.js migration to ESM module + new particle system |

Single file. All changes scoped inside the existing `<style>` block and the `<script>` blocks at the bottom.

---

## Task 1: Migrate Three.js to Import Map + Add Bloom Post-Processing

**What:** Replace the classic `<script>` Three.js loader with an import map + `<script type="module">`. Add `EffectComposer` with `UnrealBloomPass`. This is the single highest-return visual upgrade — particles go from flat dots to glowing embers.

**Why first:** Required migration to access post-processing addons. Instant cinematic quality.

**Files:**
- Modify: `landing-page/index.html`
  - Add import map in `<head>` (after existing `<script>` tags for GSAP/Lenis)
  - Replace the Three.js loader IIFE (find `/* ---- THREE.JS — conditional desktop-only load ---- */`)
  - Convert `initParticles()` and its animation loop to module scope
  - Replace `renderer.render(scene, cam)` with `composer.render()`

### Steps

- [ ] **Step 1: Add import map to `<head>`**

Add after the Lenis `<script>` tag and before `<style>`:
```html
<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>
```

- [ ] **Step 2: Replace the Three.js loader IIFE with a module script**

Find the block starting with `/* ---- THREE.JS — conditional desktop-only load ---- */` and the entire `function initParticles() { ... }` that follows it (through the closing `})();` of the animation loop).

Replace the IIFE loader AND the `initParticles` function with a `<script type="module">` block:
```js
</script>
<script type="module">
  // Three.js module — post-processing requires ESM imports
  import * as THREE from 'three';
  import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
  import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
  import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
  import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

  // Access globals from classic scripts above
  var gsap = window.gsap;
  var ScrollTrigger = window.ScrollTrigger;
  var isMob = window.innerWidth < 768;
  var noMo = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!isMob && !noMo) initParticles();

  function initParticles() {
    // ... (move existing initParticles body here, unchanged for now)
  }
</script>
<script>
```

The key: close the classic `<script>`, open the module, do Three.js work, close the module, reopen classic `<script>` for any remaining non-module code below.

- [ ] **Step 3: Add EffectComposer with bloom inside `initParticles()`**

After the renderer setup (find `renderer.setSize(W, H)`), add:
```js
// Post-processing — graceful fallback if perf is bad
var useComposer = true;
var composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, cam));

var bloomPass = new UnrealBloomPass(
  new THREE.Vector2(W, H),
  0.8,   // strength — subtle glow, not nuclear
  0.4,   // radius — how far bloom spreads
  0.85   // threshold — only bright particles bloom
);
composer.addPass(bloomPass);
```

- [ ] **Step 4: Replace render call with composer + perf gate**

Replace `renderer.render(scene, cam)` with:
```js
if (useComposer) {
  composer.render();
} else {
  renderer.render(scene, cam);
}
```

- [ ] **Step 5: Add performance measurement after first 60 frames**

In the animation loop, after the first 60 frames, check average frame time:
```js
if (frameCount === 60 && useComposer) {
  var avgMs = (performance.now() - perfStart) / 60;
  if (avgMs > 14) {
    // Halve bloom resolution for performance
    bloomPass.resolution.set(W/2, H/2);
    console.log('Bloom resolution halved for performance (' + avgMs.toFixed(1) + 'ms avg)');
  }
  if (avgMs > 18) {
    // Disable composer entirely
    useComposer = false;
    console.log('Post-processing disabled for performance (' + avgMs.toFixed(1) + 'ms avg)');
  }
}
```

Add `var perfStart = performance.now();` at the start of the first animation frame.

- [ ] **Step 6: Update resize handler**

In the resize handler (find `renderer.setSize(W,H)`), add:
```js
if (useComposer) {
  composer.setSize(W, H);
  bloomPass.resolution.set(W, H);
}
```

- [ ] **Step 7: Visual verification — screenshot hero with bloom**

Open http://localhost:9999 in Playwright. Take screenshot. Particles should have a soft glow halo, especially bright copper/hot ones. Check console for errors. If import map fails, browser will show module import error.

- [ ] **Step 8: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 1 — migrate Three.js to ESM import map + bloom post-processing"
```

---

## Task 2: Add Chromatic Aberration Shader Pass

**What:** A custom `ShaderPass` that offsets RGB channels slightly, creating a cinematic lens effect. Strongest at screen edges (radial), subtle at center.

**Why second:** Builds on the EffectComposer from Task 1. Adds premium lens feel.

**Files:**
- Modify: `landing-page/index.html` — add shader definition + pass in the module block

### Steps

- [ ] **Step 1: Define chromatic aberration shader object**

Add inside the module block, before `initParticles()`:
```js
var ChromaticAberrationShader = {
  uniforms: {
    tDiffuse: { value: null },
    uIntensity: { value: 0.0015 },
    uTime: { value: 0 }
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uIntensity;
    varying vec2 vUv;
    void main() {
      vec2 center = vUv - 0.5;
      float dist = length(center);
      float strength = uIntensity * dist * dist;
      vec2 offset = center * strength;
      float r = texture2D(tDiffuse, vUv + offset).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv - offset).b;
      gl_FragColor = vec4(r, g, b, 1.0);
    }
  `
};
```

Note: Inside `<script type="module">` we can use template literals (backticks) for multi-line GLSL — much cleaner than `.join('\n')`.

- [ ] **Step 2: Add the shader pass to composer**

After `composer.addPass(bloomPass)`:
```js
var chromaticPass = new ShaderPass(ChromaticAberrationShader);
composer.addPass(chromaticPass);
```

- [ ] **Step 3: Animate chromatic intensity in anim loop**

Before `composer.render()`:
```js
chromaticPass.uniforms.uIntensity.value = 0.001 + Math.sin(t * 0.3) * 0.0005;
```

- [ ] **Step 4: Visual verification — check lens effect at edges**

Screenshot. Faint red/blue fringing at screen edges on bright particles. SUBTLE — reduce to 0.0008 base if too obvious.

- [ ] **Step 5: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 2 — chromatic aberration lens shader pass"
```

---

## Task 3: Replace PointsMaterial with Custom ShaderMaterial

**What:** Replace `THREE.PointsMaterial` with a custom `THREE.ShaderMaterial` that supports dual-target morphing (`posA`/`posB`), simplex noise displacement, and mouse repulsion — all in the vertex shader.

**Why third:** Foundation for all morphing. Visual result should be identical to current (bloom + soft circles) — we're just migrating rendering.

**Files:**
- Modify: `landing-page/index.html` — replace material + geometry setup, update anim loop

### Steps

- [ ] **Step 1: Define the custom ShaderMaterial**

Replace the `PointsMaterial` creation (find `new THREE.PointsMaterial`) with a `THREE.ShaderMaterial`.

**Vertex shader** (template literal, include full simplex noise):
- Attributes: `posA` (vec3), `posB` (vec3), `aRandom` (float), built-in `color` (vec3)
- Uniforms: `uSize` (float), `uOpacity` (float), `uMorph` (float, 0→1), `uTime` (float), `uMouse3D` (vec3), `uRepelStrength` (float)
- Logic:
  1. `vec3 pos = mix(posA, posB, uMorph);`
  2. Noise displacement: `float noiseAmt = sin(uMorph * 3.14159) * 20.0;` then `pos += snoise(pos * 0.01 + uTime * 0.2 + aRandom * 10.0) * noiseAmt;`
  3. Mouse repulsion: if distance to `uMouse3D` < 80, apply outward force scaled by `uRepelStrength`
  4. Point size: `uSize * (300.0 / -mvPos.z)`, clamped min 1.0
- Varyings out: `vColor`, `vOpacity`

Include the full ashima/webgl-noise simplex3D GLSL (public domain, ~60 lines). This is the standard reference implementation used by Three.js examples.

**Fragment shader:**
- Soft circle: `float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard;`
- Alpha: `1.0 - smoothstep(0.2, 0.5, d)` multiplied by `vOpacity`
- Output: `gl_FragColor = vec4(vColor, alpha);`

Material settings: `transparent: true, blending: THREE.AdditiveBlending, depthWrite: false`.

- [ ] **Step 2: Set up dual-target geometry attributes**

Replace the single `position` attribute with the dual-target system:
```js
// Dual morph targets: posA = current state, posB = target state
var posA = new Float32Array(pos);     // starts as sphere
var posB = new Float32Array(pos);     // starts as sphere (no morph yet)
var aRandom = new Float32Array(N);
for (var i = 0; i < N; i++) aRandom[i] = Math.random();

geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));    // keep for Three.js internals
geo.setAttribute('posA', new THREE.BufferAttribute(posA, 3));
geo.setAttribute('posB', new THREE.BufferAttribute(posB, 3));
geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
geo.setAttribute('aRandom', new THREE.BufferAttribute(aRandom, 1));
```

- [ ] **Step 3: Update animation loop to use uniforms**

Replace CPU-driven opacity with:
```js
mat.uniforms.uTime.value = t;
mat.uniforms.uOpacity.value = 0.65 * birthProgress;
```

Keep existing breathing/twinkle/color CPU code — it updates the `color` attribute array which the shader reads.

- [ ] **Step 4: Performance gate — measure frame time**

After 60 frames, check: if avg >14ms with custom shader + bloom, disable chromatic aberration. If >18ms, fall back to `renderer.render()`.

- [ ] **Step 5: Visual verification — should look identical to pre-Task-3**

Screenshot. Particles should appear the same but with soft-circle fragments (from the fragment shader `smoothstep`). Check console for GLSL compilation errors.

- [ ] **Step 6: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 3 — custom ShaderMaterial with dual-target morph + simplex noise"
```

---

## Task 4: Generate Morph Target Positions (Text + Shapes)

**What:** Pre-compute target position arrays for key morph formations: text sampling, globe, network graph, convergence point.

**Why fourth:** The shader can morph — now we need targets to morph to.

**Files:**
- Modify: `landing-page/index.html` — add generator functions inside module block

### Steps

- [ ] **Step 1: Create `textToPositions(text, count, spread)` function**

1. Create hidden 512x128 canvas
2. Render text in `bold 80px "Pretendard Variable", sans-serif`
3. `getImageData`, collect pixel coords where alpha > 128
4. Randomly sample `count` positions from filled pixels
5. Map to 3D: `x = (px - 256) * spread`, `y = -(py - 64) * spread`, `z = random * 30 - 15`
6. Return Float32Array(count * 3)

- [ ] **Step 2: Create `globePositions(count, radius)`**

Sphere surface distribution with 30% chance of snapping theta to 30-degree meridians and phi to 22.5-degree parallels — creates a wireframe globe look.

- [ ] **Step 3: Create `networkPositions(count, spread)`**

8 random cluster centers. 70% of particles clustered (gaussian spread ~30 units), 30% on bridge lines between random pairs of nodes (linear interpolation + 8-unit jitter).

- [ ] **Step 4: Create `convergencePositions(count)`**

All particles within radius 15 of origin. Tight ball for the supernova moment.

- [ ] **Step 5: Generate and store all targets**

```js
var morphTargets = {
  sphere: new Float32Array(pos),
  text: textToPositions('LocaNext', N, 0.7),
  globe: globePositions(N, 160),
  network: networkPositions(N, 200),
  converge: convergencePositions(N)
};
```

- [ ] **Step 6: Verify — no visual change, no console errors**

- [ ] **Step 7: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 4 — morph target generators (text, globe, network, converge)"
```

---

## Task 5: Wire ScrollTrigger to Drive Morph Transitions

**What:** Connect GSAP ScrollTrigger to the dual-target morph system. Each section transition bakes the current state into `posA`, loads the new target into `posB`, and scrubs `uMorph` from 0→1.

**Why fifth:** Everything is ready — now connect scroll to drive morphing.

**Files:**
- Modify: `landing-page/index.html` — morph controller, canvas CSS, ScrollTrigger bindings

### Steps

- [ ] **Step 1: Update canvas CSS to fixed fullscreen**

Find `.hero-canvas` in the `<style>` block. Change to:
```css
.hero-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}
```

Key properties:
- `position: fixed` — persists across all sections during scroll
- `z-index: 0` — below all content (sections use default `z-index: auto` which stacks above)
- `pointer-events: none` — all clicks/hovers pass through to content below

- [ ] **Step 2: Move canvas element out of hero section**

Move `<canvas class="hero-canvas" id="heroCanvas" aria-hidden="true"></canvas>` from inside the hero section to just after `<main>`, before the hero:
```html
<main>
<canvas class="hero-canvas" id="heroCanvas" aria-hidden="true"></canvas>

<!-- ================================================================
     HERO
     ================================================================ -->
<section class="hero" id="hero">
```

- [ ] **Step 3: Create the dual-target morph transition controller**

```js
var currentShape = 'sphere';

function transitionTo(targetName) {
  if (targetName === currentShape) return;
  var target = morphTargets[targetName];
  if (!target) return;

  // Bake current morph result into posA
  var posAArr = geo.attributes.posA.array;
  var posBArr = geo.attributes.posB.array;
  var morph = mat.uniforms.uMorph.value;
  for (var i = 0; i < posAArr.length; i++) {
    posAArr[i] = posAArr[i] + (posBArr[i] - posAArr[i]) * morph;
  }
  geo.attributes.posA.needsUpdate = true;

  // Load new target into posB
  geo.attributes.posB.array.set(target);
  geo.attributes.posB.needsUpdate = true;

  // Reset morph to 0 — ScrollTrigger will scrub it to 1
  mat.uniforms.uMorph.value = 0;
  currentShape = targetName;
}
```

- [ ] **Step 4: Create ScrollTrigger bindings per section**

```js
var morphSections = [
  { trigger: '#showcase',   target: 'text',     start: 'top 80%', end: 'top 20%' },
  { trigger: '#gamedevGrid', target: 'globe',    start: 'top 80%', end: 'top 20%' },
  { trigger: '#codex',      target: 'network',  start: 'top 80%', end: 'top 20%' },
  { trigger: '#closing',    target: 'converge', start: 'top 80%', end: 'top 30%' }
];

morphSections.forEach(function(sec) {
  ScrollTrigger.create({
    trigger: sec.trigger,
    start: sec.start,
    end: sec.end,
    scrub: 1.5,
    onEnter: function() { transitionTo(sec.target); },
    onLeaveBack: function() {
      var idx = morphSections.indexOf(sec);
      transitionTo(idx > 0 ? morphSections[idx-1].target : 'sphere');
    },
    onUpdate: function(self) {
      mat.uniforms.uMorph.value = self.progress;
    }
  });
});

// Return to sphere when back at hero
ScrollTrigger.create({
  trigger: '#hero',
  start: 'top top',
  end: 'bottom 80%',
  onEnterBack: function() {
    transitionTo('sphere');
    mat.uniforms.uMorph.value = 0;
  }
});
```

- [ ] **Step 5: Replace aggressive canvas fade with gentle opacity**

Find the existing canvas fade (the `gsap.to(canvas, { opacity: 0.06, ...` block). Replace with:
```js
// Canvas opacity: full in hero, reduced during content, bright for closing
gsap.to(canvas, {
  opacity: 0.35, ease: 'none',
  scrollTrigger: { trigger: '#hero', start: 'top top', end: 'bottom top', scrub: 0.5 }
});
gsap.to(canvas, {
  opacity: 0.8, ease: 'power2.in',
  scrollTrigger: { trigger: '#closing', start: 'top 80%', end: 'top 30%', scrub: 1 }
});
```

- [ ] **Step 6: Visual verification — scroll through all sections**

Playwright: navigate to page, scroll slowly through each section. Verify:
- Hero: sphere formation
- Showcase: particles form "LocaNext" text (with noise displacement during transition)
- Game Dev: globe wireframe shape
- Codex: network clusters with bridges
- Closing: tight convergence ball
- Scrolling back: shapes reverse correctly

Check that all buttons, links, and interactive elements remain clickable (canvas has `pointer-events: none`).

- [ ] **Step 7: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 5 — scroll-driven particle morphing with dual-target system"
```

---

## Task 6: Add Mouse Repulsion

**What:** Unproject mouse into 3D space, feed to vertex shader. Particles near cursor get pushed away.

**Why sixth:** Polish layer. Morphing is backbone, mouse adds tactility.

**Files:**
- Modify: `landing-page/index.html` — add raycaster, update anim loop

### Steps

- [ ] **Step 1: Add 3D mouse tracking via plane intersection**

```js
var mouse3D = new THREE.Vector3(9999, 9999, 9999);
var mouseNDC = new THREE.Vector2();
var raycaster = new THREE.Raycaster();
var mousePlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
var mouseIntersect = new THREE.Vector3();

document.addEventListener('mousemove', function(e) {
  mouseNDC.x = (e.clientX / W) * 2 - 1;
  mouseNDC.y = -(e.clientY / H) * 2 + 1;
  raycaster.setFromCamera(mouseNDC, cam);
  if (raycaster.ray.intersectPlane(mousePlane, mouseIntersect)) {
    mouse3D.copy(mouseIntersect);
  }
});
```

- [ ] **Step 2: Feed mouse position to shader each frame**

In animation loop, before render:
```js
mat.uniforms.uMouse3D.value.copy(mouse3D);
mat.uniforms.uRepelStrength.value = 1.0;
```

- [ ] **Step 3: Visual verification**

Move cursor over particles. They should push outward in a ~80 unit radius void, then drift back organically via noise when cursor leaves.

- [ ] **Step 4: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 6 — mouse repulsion on 3D particles via raycaster"
```

---

## Task 7: Closing Supernova + Typography Motion

**What:** Bloom intensity spike when particles converge at closing. Key headings get word-by-word slide-up reveals.

**Why last:** Grand finale. Everything else must work first.

**Files:**
- Modify: `landing-page/index.html` — closing bloom anim + typography CSS/JS

### Steps

- [ ] **Step 1: Add supernova bloom spike on closing**

```js
ScrollTrigger.create({
  trigger: '#closing',
  start: 'top 40%',
  end: 'top 10%',
  scrub: 1,
  onUpdate: function(self) {
    var p = self.progress;
    bloomPass.strength = 0.8 + p * 2.5;           // 0.8 → 3.3
    chromaticPass.uniforms.uIntensity.value = 0.001 + p * 0.004;
  }
});
ScrollTrigger.create({
  trigger: '#powerStack',
  start: 'top top',
  onEnterBack: function() {
    gsap.to(bloomPass, { strength: 0.8, duration: 1 });
    chromaticPass.uniforms.uIntensity.value = 0.001;
  }
});
```

- [ ] **Step 2: Add typography motion CSS**

In the `<style>` block:
```css
.word-reveal {
  display: inline-block;
  overflow: hidden;
  vertical-align: bottom;
  padding-bottom: 0.05em;
}
.word-reveal-inner {
  display: inline-block;
  transform: translateY(110%);
  will-change: transform;
}
```

- [ ] **Step 3: Add word-splitting function**

In the classic `<script>` block (not the module — this runs on DOM elements):

`splitWords(selector)` function:
1. Query all matching elements
2. Skip if `el.dataset.split` already set
3. Walk through child nodes (text + elements)
4. Wrap each text word in `<span class="word-reveal"><span class="word-reveal-inner">word</span></span>`
5. Preserve existing `<span>`, `<br>` tags as-is
6. Set `el.dataset.split = 'true'`

**Safety note:** This only processes our own static headings — no user input. Safe DOM manipulation of known content.

- [ ] **Step 4: Apply typography motion to key headings**

```js
splitWords('.closing-tag, #showcase .t-display, #gamedevGrid .t-display, #codex .t-display');

document.querySelectorAll('[data-split]').forEach(function(el) {
  var words = el.querySelectorAll('.word-reveal-inner');
  if (!words.length) return;
  ScrollTrigger.create({
    trigger: el,
    start: 'top 85%',
    once: true,
    onEnter: function() {
      gsap.to(words, {
        y: '0%',
        duration: 0.7,
        stagger: 0.06,
        ease: 'power3.out'
      });
    }
  });
});
```

- [ ] **Step 5: Visual verification — scroll to closing section**

Particles converge, bloom intensifies to bright glow, chromatic aberration strengthens. Headings throughout page slide up word-by-word. Closing text reveals dramatically.

- [ ] **Step 6: Commit**

```bash
git add landing-page/index.html
git commit -m "feat(landing): Task 7 — closing supernova bloom + typography motion reveals"
```

---

## Post-Implementation Verification

After all 7 tasks:

- [ ] Full page scroll-through screenshot (Playwright, full-page)
- [ ] Performance: open DevTools → Performance → record 10s of scrolling → verify <16ms frames
- [ ] Mobile: resize to 375px → confirm no Three.js loads, page works, no broken layout
- [ ] Lighthouse: target 90+ performance, 100 accessibility
- [ ] Cross-browser: check Chrome + Firefox (import maps supported in both)
- [ ] Deploy to Netlify: `npx netlify-cli deploy --dir=landing-page --prod`

---

## Summary

| Task | What | Risk | Visual Impact |
|------|------|------|---------------|
| 1 | ESM migration + bloom | Medium (migration) | Particles glow cinematically |
| 2 | Chromatic aberration | Low | Cinematic lens feel |
| 3 | Custom ShaderMaterial | Medium (GLSL) | Foundation (same visual) |
| 4 | Morph target generators | Low | Data only (no visual) |
| 5 | Scroll morph controller | Medium (timing) | Particles morph per section |
| 6 | Mouse repulsion | Low | Cursor pushes particles |
| 7 | Supernova + typography | Low | Grand finale |

**Total: ~400 lines of new/modified JS, ~10 lines CSS.**
**Dependencies: None new — Three.js r160 ESM addons loaded via import map from same CDN.**
