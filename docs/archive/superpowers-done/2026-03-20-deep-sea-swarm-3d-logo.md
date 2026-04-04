# AI-Generated Web Assets — Iterative Plan v3

> **Status:** Layer 12 attempted then reverted (2026-03-20). Layer 13 not started. OPEN.
> **v3:** Try-and-revert iterative approach. Each attempt is cheap. If it doesn't look premium, revert and try the next approach.
> **Stable revision:** `9290e310` — always revert to this if an attempt fails.
> **Lesson learned:** `memory/feedback_cheap_3d_effects.md`

---

## Philosophy: Try → Review → Keep or Revert

```
For each approach:
  1. Generate asset (image/video/3D)
  2. Vision review with Qwen3-VL (quick, free)
  3. If 7+ rating → integrate into page
  4. Vision review integrated result with Gemini (deep, paid)
  5. If 8+ rating → commit as new stable
  6. If < 8 → git revert → try next approach

Total budget per attempt: $0.15-3.00
Always revertable. Never stuck with bad work.
```

---

## Phase 0: Hero Video Upgrade (Test Run)

**Purpose:** Test fal.ai video quality before investing in deep sea or 3D work.
**Current:** Hero has a Kling 3.0 video at 12% opacity behind Three.js particles.

### Attempt 0A: Kling 3.0 (best value)

| Detail | Value |
|--------|-------|
| Model | `fal-ai/kling-video/v3/pro` |
| Cost | ~$0.15 per 5s clip |
| Access | fal.ai MCP (ready) |

**Prompts to try:**
1. "Slow abstract nebula in deep space, copper and blue gas clouds drifting, particle dust catching light, ultra cinematic, no camera movement, seamless loop, 4K"
2. "Dark cosmic void with slow-moving aurora of warm golden light and cool blue mist, abstract, ethereal, seamless loop"
3. "Extreme macro of liquid metal and light refracting through dark crystal, copper and blue tones, abstract luxury, slow motion"

**If quality is good:** Swap into hero, commit. Move to Phase 1.
**If quality is meh:** Try 0B.

### Attempt 0B: Seedance 1.5 Pro (better motion)

| Detail | Value |
|--------|-------|
| Model | `fal-ai/seedance-1-0-pro` (or 1.5 if available) |
| Cost | ~$0.26 per 5s clip |
| Access | fal.ai MCP (ready) |

Same prompts as 0A but with camera direction (Seedance follows camera instructions well):
- "slow dolly forward through dark abstract space, volumetric copper fog, cool blue highlights, cinematic, 4K"

**If quality is good:** Swap into hero, commit. Move to Phase 1.
**If quality is meh:** Try 0C.

### Attempt 0C: Veo 3.1 (highest quality, most expensive)

| Detail | Value |
|--------|-------|
| Model | `fal-ai/veo-3` |
| Cost | ~$1-3 per clip |
| Access | fal.ai MCP (ready) |

Same prompts. This is the premium option — if Veo can't do it, video approach won't work.

**If quality is good:** Use for hero + deep sea. Worth the cost.
**If quality is bad:** Video approach is not the answer. Skip to Phase 1 Attempt B (premium shaders).

### Decision Gate After Phase 0

| Result | Next Step |
|--------|-----------|
| One model produced premium video | Use that model for Phase 1 (deep sea) |
| All videos look generic/AI-ish | Skip video for deep sea, use premium shaders instead |
| Video is good but not hero-worthy | Keep current hero, but use video for deep sea background (lower bar) |

---

## Phase 1: Deep Sea Swarm Background

### Attempt 1A: AI Video (using winning model from Phase 0)

**Prompts for deep sea:**
1. "Cinematic macro shot of bioluminescent deep sea creatures drifting through pure black ocean void. Tiny glowing cyan and blue organisms leaving soft luminous trails. Slow elegant movement. Photorealistic, 4K"
2. "Abstract deep ocean darkness. School of bioluminescent jellyfish trailing cyan light through black water. Long exposure photography effect. Ethereal, dreamlike"
3. "Close-up bioluminescent plankton swarm in pitch black deep sea. Thousands of tiny blue-green lights moving in organic flowing patterns. Marine snow particles catching the glow"

**Integration:**
- ffmpeg: reverse-loop → compress to 720p WebM <1.5MB
- `<video autoplay muted loop playsinline>` behind `#swarmCanvas`
- Opacity: 0.15-0.25
- z-index: 0 (behind the 2D canvas at z-index: 1)

**If quality is good:** Commit as new stable.
**If quality is meh:** Try 1B.

### Attempt 1B: Wan-Alpha v2.0 (transparent video, FREE)

| Detail | Value |
|--------|-------|
| Model | Wan-Alpha v2.0 (open source, CVPR 2026) |
| Cost | FREE (local GPU) |
| Access | Needs install from GitHub |
| Special | Generates video WITH alpha channel |

**Why this could be better:** Transparent bioluminescent creatures floating OVER the swarm canvas, not behind it. The alpha channel means no opacity hack needed — just layer naturally.

**Risk:** Needs install + testing. May not run on RTX 4070 Ti 12GB. Research VRAM requirements first.

**If it works:** Game-changer. Use for deep sea + potentially other sections.
**If too heavy or bad quality:** Try 1C.

### Attempt 1C: Premium Shader (code-based, FREE)

Last resort if video approaches all fail. But done PROPERLY this time:

- NOT Points geometry — use InstancedMesh with actual fish/jellyfish shapes
- Body deformation via vertex shader (sinusoidal spine, fin flutter)
- TubeGeometry ribbon trails (not dot trails)
- Volumetric glow: custom fragment shader with inner core + outer halo
- Depth fog: particles fade with z-distance
- Reference: [Codrops High-Speed Light Trails](https://tympanus.net/codrops/2019/11/13/high-speed-light-trails-in-three-js/)
- Reference: [Codrops Dreamy GPGPU Particles](https://tympanus.net/codrops/2024/12/19/crafting-a-dreamy-particle-effect-with-three-js-and-gpgpu/)

**Estimated effort:** 3-4x more than v1. Needs brainstorming + proper shader skill invocation.
**If quality is good:** Commit.
**If still cheap-looking:** Accept that deep sea is too ambitious, pick a different visual direction.

---

## Phase 2: 3D Object for Closing Section

### Attempt 2A: Hunyuan3D Symbolic Object (FREE, infinite iterations)

| Detail | Value |
|--------|-------|
| Model | `local_generate_3d` MCP tool (Hunyuan3D 2 Mini, local GPU) |
| Cost | FREE |
| Input | Nano Banana 2 generated image (~$0.05) |
| Output | .glb mesh file |

**Step 1: Generate input images** (try 5-10 different prompts):
1. "Glowing crystal polyhedron with language symbols orbiting, dark background, sci-fi holographic, centered, high detail"
2. "Luminous data nexus sphere with connecting light threads, dark space, futuristic, centered"
3. "Floating holographic translation orb emitting warm golden light, abstract tech, minimal, centered on pure black"
4. "Abstract gem with facets reflecting different language scripts, warm amber glow, dark background"
5. "Futuristic communication device hovering in void, warm copper light, clean geometry, centered"

**Step 2: Generate 3D from best image**
- `local_generate_3d(image_path, octree_resolution=384, num_inference_steps=50)`
- Try each good image → pick best mesh

**Step 3: Optimize for web**
- Install gltf-transform: `npm install -g @gltf-transform/cli`
- Optimize: `gltf-transform optimize input.glb output.glb --compress draco --texture-compress webp`
- Target: <500KB final .glb

**Step 4: Integrate into Three.js**
- GLTFLoader in existing hero scene
- Position visible during closing section scroll
- NO rotation — subtle scroll parallax only (slight tilt, scale breathing)
- Custom emissive material matching `--warm: #d49a5c`

**If quality is premium (8+ from Gemini):** Commit.
**If quality is meh after 10 iterations:** Try 2B.

### Attempt 2B: Code-Generated Logo with Pretendard Font (FREE)

- Convert Pretendard to Three.js font JSON using `facetype.js`
- TextGeometry with the actual brand font
- Custom ShaderMaterial (warm gradient emission, NOT generic MeshStandardMaterial)
- NO rotation — static with subtle scroll parallax
- Entrance: particles converge to form text (use existing morph system)

**If quality is premium:** Commit.
**If still cheap-looking:** Try 2C.

### Attempt 2C: Enhanced Closing Without 3D

Skip 3D entirely. The closing already scored 9/10 from Gemini. Instead:
- GSAP SplitText character-by-character reveal animation
- Parallax depth effect on background image layers
- Subtle glow animation on the `로카넥스트` brand watermark
- Enhanced typography motion

**This is the safe option.** The closing is already strong.

---

## Technical Reference

### ffmpeg Commands

**Reverse-loop for seamless playback:**
```bash
ffmpeg -i input.mp4 -filter_complex "[0:v]reverse[r];[0:v][r]concat=n=2:v=1[v]" -map "[v]" -an looped.mp4
```

**Compress to 720p WebM:**
```bash
ffmpeg -i looped.mp4 -c:v libvpx-vp9 -b:v 1000k -an -s 1280x720 -t 10 output.webm
```

**Extract poster frame:**
```bash
ffmpeg -i output.webm -frames:v 1 -q:v 2 poster.webp
```

### Web Video Targets

| Metric | Target |
|--------|--------|
| Resolution | 1280x720 (720p) |
| Codec | VP9 (WebM) + H.264 fallback (MP4) |
| Bitrate | 700-1200 kbps |
| File size | <1.5MB for 10s loop |
| Opacity on page | 0.12-0.25 |
| Mobile | Static poster image only (no video) |

### Models Available via fal.ai MCP

| Model | App ID | Cost/clip |
|-------|--------|-----------|
| Kling 3.0 Standard | `fal-ai/kling-video/v3/standard` | ~$0.15/5s |
| Kling 3.0 Pro | `fal-ai/kling-video/v3/pro` | ~$0.30/5s |
| Seedance 1.0 Pro | `fal-ai/seedance-1-0-pro` | ~$0.26/5s |
| Veo 3 | `fal-ai/veo-3` | ~$1-3/clip |
| Nano Banana 2 | `fal-ai/nano-banana-2` | ~$0.05/image |

### 3D Pipeline

```
Nano Banana 2 (image) → Hunyuan3D 2 Mini (mesh) → gltf-transform (optimize) → Three.js (render)
         $0.05              FREE (local GPU)              FREE                    FREE
```

---

## Cost Summary

| Phase | Attempts | Max Cost |
|-------|----------|----------|
| Phase 0: Hero test | 3-6 clips | $0.50-3.00 |
| Phase 1: Deep sea | 3-5 clips | $0.50-3.00 |
| Phase 2: 3D object | 5-10 images + meshes | $0.25-0.50 |
| Vision reviews | All phases | FREE (Qwen) + $0.20 (Gemini) |
| **Total max** | | **~$4-7** |

All revertable. No wasted money on bad results.
