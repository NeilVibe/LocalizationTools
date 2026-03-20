# Free Local AI Models — Full Autonomy MCP Build Plan

> **Deep research: 2026-03-19 (updated with live benchmarks, real VRAM numbers, diffusers code)**
> **Goal:** Every AI generation capability running FREE on our RTX 4070 Ti (12GB VRAM), callable from Claude Code via MCP.

---

## How Claude Code Generates Things TODAY

**Critical distinction:** Claude Code can only use tools that have an MCP connection.

| Service | Claude Code Access? | How |
|---------|-------------------|-----|
| **fal.ai** | **YES** — MCP installed | `mcp__fal-ai__generate` etc. — images, video, audio directly from conversation |
| **Google Gemini** | **NO** — no MCP, no plugin | Only inside LocaNext Python backend (`ai_image_service.py`). Claude Code can't call it. |
| **Local models** (what we're building) | **YES** — after MCP built | New capabilities Claude Code can't access ANY other way |

**This means:**
- fal.ai is NOT just a "proxy" — it's Claude Code's **only way to generate images/video right now**
- Google Gemini is invisible to Claude Code — it only works inside the running LocaNext app
- Local MCPs give Claude Code **brand new superpowers** (music, SFX, 3D) that don't exist on fal.ai OR Google

---

## Decision: Who Does What

| Use Case | Tool | Why |
|----------|------|-----|
| **Claude Code image gen** (landing page, mockups, dev work) | **fal.ai** now, **Z-Image Turbo** later (test quality first) | fal.ai works today; Z-Image = future free replacement |
| **LocaNext Codex** (RPG portraits, items — user-facing) | **Google Gemini API direct** (`gemini-3-pro-image-preview`) | Already integrated, cheapest for Pro, `GEMINI_API_KEY` in .zshrc |
| **Cinematic video** (landing page hero) | **Kling 3.0 via fal.ai** | Best quality, no local alternative for cinematic |
| **Ambient/background video** (looping drift) | **Wan 2.2 TI2V-5B** (local, FREE) | Good enough for non-cinematic, $0.00 |
| **Music generation** | **ACE-Step 1.5** (local, FREE) | **UNIQUE** — fal.ai can't, Google can't |
| **Sound effects** | **AudioLDM 2** (local, FREE) | **UNIQUE** — fal.ai can't, Google can't |
| **3D mesh generation** | **Hunyuan3D 2 Mini** (local, FREE) | **UNIQUE + WOW FACTOR** — interactive 3D on landing page |
| **TTS with emotions** | **CosyVoice 2** (local, FREE) | Upgrade over Qwen3-TTS when needed |

**fal.ai: KEEP.** It's Claude Code's image/video generation bridge. Use for anything not available locally.
**Google Gemini: KEEP for LocaNext Codex only.** User-facing Pro quality, cheaper direct than via fal.ai.
**Local MCPs: BUILD for unique capabilities.** Music, SFX, 3D — stuff money can't buy on fal.ai/Google.
**Z-Image Turbo: TEST for quality.** Future fal.ai image replacement, not urgent.

---

## The Stack At A Glance

| # | Model | What It Does | VRAM | Replaces (Paid) | Savings |
|---|-------|-------------|------|-----------------|---------|
| 1 | **Z-Image Turbo** | Image generation | ~7GB (Q4) / 12GB (bf16) | fal.ai Nano Banana ($0.08/img) | **100%** |
| 2 | **Wan 2.2 TI2V-5B** | Image-to-video | ~8GB | Kling for ambient use ($0.03/sec) | **100%** |
| 3 | **ACE-Step 1.5** | Music generation | <4GB | NOTHING (unique) | **N/A** |
| 4 | **Hunyuan3D 2 Mini** | 3D mesh generation | 5-6GB | NOTHING (unique) | **N/A** |
| 5 | **AudioLDM 2** | Sound FX generation | ~8GB | NOTHING (unique) | **N/A** |
| 6 | **CosyVoice 2** | Streaming TTS + emotions | ~6GB | Qwen3-TTS (upgrade) | **N/A** |

**All Apache 2.0 licensed. All run on our GPU. All free forever.**

---

## Model 1: Z-Image Turbo — FREE Image Generation

### Why This Is Priority #1

Z-Image Turbo is our **default image generator for everything** — landing page, mockups, social, testing, dev work. 85-90% of Nano Banana Pro quality, runs locally, costs $0.00. The only exception is LocaNext Codex (user-facing RPG art) which stays on Google Gemini direct because users deserve Pro quality and Google direct is cheaper than fal.ai anyway.

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | Alibaba Tongyi-MAI |
| **Architecture** | S3-DiT (Scalable Single-Stream Diffusion Transformer), 6B params |
| **License** | Apache 2.0 |
| **HuggingFace** | `Tongyi-MAI/Z-Image-Turbo` |
| **GitHub** | `github.com/Tongyi-MAI/Z-Image` |
| **VRAM (bf16)** | ~12GB (tight fit on our card) |
| **VRAM (Q4_K_M)** | ~6.9GB (comfortable, recommended) |
| **Speed** | ~3.4s per 1280x800 image (RTX 4070 class) |
| **Steps** | Exactly 8 NFEs (distilled model, fixed) |
| **Quality vs Nano Banana 2** | 85-90% — more raw/filmic aesthetic vs NB2's clean commercial look |
| **Text rendering** | Bilingual (English + Chinese), good but not NB2-level |

### Installation (Full Autonomy)

```bash
# 1. Install diffusers from source (required for ZImagePipeline)
pip install git+https://github.com/huggingface/diffusers
pip install transformers accelerate safetensors

# 2. Model auto-downloads on first use (~6GB from HuggingFace)
# No manual download needed — diffusers handles caching
```

### Python Pipeline

```python
import torch
from diffusers import ZImagePipeline

pipe = ZImagePipeline.from_pretrained(
    "Tongyi-MAI/Z-Image-Turbo",
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=False
)
pipe.to("cuda")

# Optional: quantize to fit comfortably in 12GB
# pipe.enable_model_cpu_offload()  # if VRAM tight

image = pipe(
    prompt="Dark cosmic nebula with copper and blue tones, cinematic, 8k",
    num_inference_steps=8,       # FIXED — distilled model
    guidance_scale=3.5,          # default for turbo
    width=1280,
    height=800,
).images[0]

image.save("output.png")
```

### Quality Comparison

| Aspect | Z-Image Turbo | Nano Banana 2 |
|--------|---------------|---------------|
| Photorealism | RAW/filmic (Kodak Portra vibe) | Clean commercial |
| Skin tones | Good, slightly gritty | Perfect |
| Lighting | Natural, lens-driven | Balanced, studio-like |
| Text in images | Good (EN + CN) | Excellent (multi-lang) |
| 4K support | Up to 2048px | Up to 4K |
| Speed | ~3.4s local | ~2-3s fal.ai |
| Cost | **$0.00** | $0.08/image |

**Verdict:** For 80% of tasks (landing page, social, mockups), Z-Image is optimal. Reserve Nano Banana for commercial photography needs.

---

## Model 2: Wan 2.2 TI2V-5B — FREE Video Generation

### Why This Matters

Kling 3.0 costs ~$0.03/sec ($0.15 for a 5s clip). Wan 2.2 runs locally for free. The 5B model fits in 12GB VRAM.

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | Alibaba Wan-AI |
| **Architecture** | MoE (27B total, 14B active for 14B; 5B for small) |
| **License** | Apache 2.0 |
| **HuggingFace** | `Wan-AI/Wan2.2-TI2V-5B-Diffusers` (image-to-video) |
| **GitHub** | `github.com/Wan-Video/Wan2.2` |
| **VRAM (5B model)** | ~8GB (fits comfortably) |
| **Resolution** | 720P @ 24fps |
| **Speed** | ~6-9 min for 5s clip on consumer GPU |
| **Quality vs Kling 3.0** | ~70-75% — good for ambient/background, not cinematic close-ups |
| **Wan2GP** | GPU-poor fork with GGUF support for tight VRAM |

### Installation (Full Autonomy)

```bash
# 1. Install diffusers from source (already done for Z-Image)
pip install git+https://github.com/huggingface/diffusers

# 2. Model auto-downloads on first use (~10GB)
# OR use Wan2GP for better VRAM management:
git clone https://github.com/deepbeepmeep/Wan2GP.git
cd Wan2GP && pip install -r requirements.txt
```

### Python Pipeline (Diffusers)

```python
import torch
from diffusers import WanPipeline, AutoencoderKLWan, UniPCMultistepScheduler
from diffusers.utils import export_to_video, load_image

# Load 5B model
pipe = WanPipeline.from_pretrained(
    "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()  # essential for 12GB VRAM

image = load_image("hero_image.png").resize((832, 480))

output = pipe(
    prompt="Slow cosmic drift, nebula particles floating, cinematic, atmospheric",
    image=image,
    num_frames=61,               # ~2.5s at 24fps
    guidance_scale=5.0,
).frames[0]

export_to_video(output, "hero_video.mp4", fps=24)
```

### VRAM Strategy

| Approach | VRAM Needed | Speed |
|----------|------------|-------|
| bf16 + CPU offload | ~8-10GB | ~9 min/5s clip |
| GGUF via Wan2GP | ~6-8GB | ~12 min/5s clip |
| bf16 no offload | ~24GB | ~6 min (too much for us) |

**Recommended:** Use `enable_model_cpu_offload()` — fits in 12GB, acceptable speed.

### When to Use Wan 2.2 vs Kling

| Use Case | Wan 2.2 (Free) | Kling 3.0 (Paid) |
|----------|----------------|-------------------|
| Landing page ambient bg | YES | Overkill |
| Product demo video | Decent | Better |
| Cinematic hero section | Passable | YES |
| Looping drift animations | YES (perfect) | Expensive for loops |

**Strategy:** Use Wan 2.2 for ambient/background. Keep Kling for the ONE cinematic hero video (one-time $0.15).

---

## Model 3: ACE-Step 1.5 — FREE Music Generation (UNIQUE)

### Why This Is Special

fal.ai has NO music generation. This is a capability we literally cannot buy. ACE-Step generates full songs with vocals in 20 seconds.

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | ACE Studio + StepFun |
| **Version** | 1.5 (latest, February 2026) |
| **License** | Apache 2.0 |
| **GitHub** | `github.com/ace-step/ACE-Step-1.5` |
| **VRAM** | <4GB (runs alongside anything) |
| **Speed** | ~20s for 4 min song (A100), ~45s (RTX 4070 class) |
| **Quality** | Best open-source music gen in 2026. Rivals commercial alternatives |
| **Features** | All genres, lyrics support, LoRA fine-tuning from few songs |
| **Devices** | CUDA, Mac, AMD, Intel |

### Installation (Full Autonomy)

```bash
# Option A: uv (recommended — auto-manages deps)
git clone https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5
pip install uv  # if not installed
uv sync

# Launch Gradio UI (models auto-download on first run)
uv run acestep          # http://localhost:7860
# OR launch API
uv run acestep-api      # http://localhost:8001

# Option B: pip
pip install ace-step
```

### Python Pipeline

```python
# Via the API endpoint (after launching acestep-api)
import requests

response = requests.post("http://localhost:8001/generate", json={
    "prompt": "Ambient electronic, warm pads, subtle bass, dreamy atmosphere",
    "duration": 30,          # seconds
    "seed": 42,
})
# Returns audio file path or base64

# OR via direct Python import
from ace_step import ACEStep

model = ACEStep.from_pretrained()
audio = model.generate(
    prompt="Calm ambient drone, low frequency, warm tones",
    duration=60,
)
audio.save("ambient.wav")
```

### Use Cases for Us

| Use Case | Details |
|----------|---------|
| **Landing page Piece 11** | Ambient soundscape (warm drone, barely audible, opt-in) |
| **UI sound design** | Generate click/hover/transition sounds |
| **Demo videos** | Background music for product showcases |
| **LoRA training** | Train on specific music style from a few reference tracks |

---

## Model 4: Hunyuan3D 2 Mini — FREE 3D Mesh Generation (UNIQUE)

### Why This Is Special

No paid equivalent in our stack. Generate 3D objects from text or images — usable directly in Three.js scenes.

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | Tencent |
| **License** | Apache 2.0 (Tencent Hunyuan Community License for full; Mini is Apache) |
| **GitHub** | `github.com/Tencent-Hunyuan/Hunyuan3D-2` |
| **HuggingFace** | `tencent/Hunyuan3D-2mini` |
| **VRAM (Mini)** | 5-6GB (shape generation only) |
| **VRAM (Full)** | 12-16GB (shape + texture) |
| **Output** | .glb, .obj files with PBR textures (albedo, normal, roughness) |
| **Quality** | State of the art for open-source 3D generation |

### Installation (Full Autonomy)

```bash
git clone https://github.com/Tencent/Hunyuan3D-2.git
cd Hunyuan3D-2

# PyTorch with CUDA
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt

# Compile custom texture CUDA kernels (required for texture gen)
cd hy3dgen/texgen/custom_rasterizer && pip install -e . && cd ../../..
cd hy3dgen/texgen/differentiable_renderer && pip install -e . && cd ../../..
```

### Python Pipeline

```python
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline

# Shape generation only (5-6GB VRAM) — use Mini
shape_pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    "tencent/Hunyuan3D-2mini",
    low_vram_mode=True,
)

mesh = shape_pipe(prompt="A copper sphere with cosmic texture")[0]
mesh.export("sphere.glb")

# With textures (12GB+ VRAM) — may need CPU offload
paint_pipe = Hunyuan3DPaintPipeline.from_pretrained("tencent/Hunyuan3D-2mini")
textured_mesh = paint_pipe(mesh, prompt="Copper metallic with blue nebula patterns")
textured_mesh.export("sphere_textured.glb")
```

### Use Cases for Us

| Use Case | Details |
|----------|---------|
| **Three.js scenes** | Generate custom 3D objects for landing page/LocaNext |
| **Game asset previews** | Show 3D previews of game items in QACompiler |
| **Product visualization** | 3D rendered product shots |

---

## Model 5: AudioLDM 2 — FREE Sound Effects (UNIQUE)

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | Haohe Liu et al. |
| **License** | Apache 2.0 |
| **GitHub** | `github.com/haoheliu/AudioLDM2` |
| **HuggingFace** | `cvssp/audioldm2` (diffusers) |
| **VRAM** | ~8GB |
| **Quality** | Most versatile — speech, SFX, music, ambient |
| **Output** | WAV audio files |

### Installation (Full Autonomy)

```bash
# Option A: pip
pip install audioldm2

# Option B: diffusers (already installed for Z-Image)
# Uses: AudioLDM2Pipeline from diffusers

# CLI usage:
audioldm2 --model_name "audioldm_48k" --device cuda \
  -t "Soft whoosh sound effect, digital, clean" \
  -s "output.wav"
```

### Python Pipeline

```python
from diffusers import AudioLDM2Pipeline
import torch, scipy

pipe = AudioLDM2Pipeline.from_pretrained(
    "cvssp/audioldm2",
    torch_dtype=torch.float16,
)
pipe.to("cuda")

audio = pipe(
    prompt="Gentle click sound, digital interface, clean and crisp",
    num_inference_steps=50,
    audio_length_in_s=2.0,
).audios[0]

scipy.io.wavfile.write("click.wav", rate=16000, data=audio)
```

### Use Cases for Us

| Use Case | Details |
|----------|---------|
| **Landing page Piece 11** | UI sound effects (click on swarm nodes, whoosh on reveals) |
| **Notification sounds** | Custom sounds for LocaNext alerts |
| **Ambient audio** | Rain, wind, office ambiance for demo videos |

---

## Model 6: CosyVoice 2 — Streaming TTS Upgrade (LOW PRIORITY)

### Specs

| Attribute | Detail |
|-----------|--------|
| **Developer** | Alibaba FunAudioLLM |
| **License** | Apache 2.0 |
| **HuggingFace** | `FunAudioLLM/CosyVoice2-0.5B` |
| **GitHub** | `github.com/FunAudioLLM/CosyVoice` |
| **VRAM** | ~6GB |
| **Latency** | 150ms streaming (vs Qwen3-TTS batch) |
| **Features** | Emotion control (happy/sad/angry), accent, role style |
| **Quality** | Excellent Korean, multi-lingual |

### Why Low Priority

Qwen3-TTS already works great for us (1.755% WER Korean). CosyVoice 2 adds streaming + emotions — nice to have, not essential right now.

### Installation (Full Autonomy)

```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt

# Download model
python -c "
from modelscope import snapshot_download
snapshot_download('FunAudioLLM/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')
"
```

---

## MCP Architecture: One Server, All Models

### The Design

```
local-models MCP server (FastMCP 3.0)
│
├── tool: generate_image      → Z-Image Turbo
│   params: prompt, width, height, seed, output_path
│   returns: { path: "/tmp/gen/img_001.png", time_ms: 3400 }
│
├── tool: generate_video      → Wan 2.2 TI2V-5B
│   params: prompt, image_path, num_frames, seed, output_path
│   returns: { path: "/tmp/gen/vid_001.mp4", time_ms: 540000 }
│
├── tool: generate_music      → ACE-Step 1.5
│   params: prompt, duration_sec, genre, seed, output_path
│   returns: { path: "/tmp/gen/music_001.wav", time_ms: 45000 }
│
├── tool: generate_3d         → Hunyuan3D 2 Mini
│   params: prompt, image_path, with_texture, output_path
│   returns: { path: "/tmp/gen/mesh_001.glb", time_ms: 120000 }
│
├── tool: generate_sfx        → AudioLDM 2
│   params: prompt, duration_sec, seed, output_path
│   returns: { path: "/tmp/gen/sfx_001.wav", time_ms: 8000 }
│
└── tool: generate_speech     → CosyVoice 2
    params: text, language, emotion, speaker, output_path
    returns: { path: "/tmp/gen/speech_001.wav", time_ms: 2000 }
```

### FastMCP 3.0 Server Skeleton

```python
# scripts/mcp/local_models_mcp.py
from fastmcp import FastMCP
import torch
import os

mcp = FastMCP("Local AI Models")
OUTPUT_DIR = "/tmp/gen"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Lazy loading — models only load when called
_pipelines = {}

def _get_pipeline(name: str):
    """Load model on-demand, unload others to free VRAM."""
    if name in _pipelines:
        return _pipelines[name]

    # Unload any existing model first
    for key in list(_pipelines.keys()):
        del _pipelines[key]
    torch.cuda.empty_cache()

    if name == "z_image":
        from diffusers import ZImagePipeline
        pipe = ZImagePipeline.from_pretrained(
            "Tongyi-MAI/Z-Image-Turbo",
            torch_dtype=torch.bfloat16,
        ).to("cuda")
    elif name == "audioldm2":
        from diffusers import AudioLDM2Pipeline
        pipe = AudioLDM2Pipeline.from_pretrained(
            "cvssp/audioldm2",
            torch_dtype=torch.float16,
        ).to("cuda")
    # ... more models ...

    _pipelines[name] = pipe
    return pipe


@mcp.tool
def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: int = -1,
) -> dict:
    """Generate an image from text using Z-Image Turbo (free, local GPU)."""
    import time
    start = time.time()

    pipe = _get_pipeline("z_image")
    generator = torch.Generator("cuda").manual_seed(seed) if seed >= 0 else None

    image = pipe(
        prompt=prompt,
        num_inference_steps=8,
        width=width,
        height=height,
        generator=generator,
    ).images[0]

    path = f"{OUTPUT_DIR}/img_{int(time.time())}.png"
    image.save(path)

    return {
        "path": path,
        "time_ms": int((time.time() - start) * 1000),
        "model": "Z-Image Turbo",
        "resolution": f"{width}x{height}",
    }


@mcp.tool
def generate_sfx(
    prompt: str,
    duration_sec: float = 3.0,
    seed: int = -1,
) -> dict:
    """Generate a sound effect from text using AudioLDM 2 (free, local GPU)."""
    import time, scipy
    start = time.time()

    pipe = _get_pipeline("audioldm2")
    generator = torch.Generator("cuda").manual_seed(seed) if seed >= 0 else None

    audio = pipe(
        prompt=prompt,
        num_inference_steps=50,
        audio_length_in_s=duration_sec,
        generator=generator,
    ).audios[0]

    path = f"{OUTPUT_DIR}/sfx_{int(time.time())}.wav"
    scipy.io.wavfile.write(path, rate=16000, data=audio)

    return {
        "path": path,
        "time_ms": int((time.time() - start) * 1000),
        "model": "AudioLDM 2",
        "duration_sec": duration_sec,
    }

# Add more @mcp.tool functions for video, music, 3d, speech...

if __name__ == "__main__":
    mcp.run()
```

### Registration in Claude Code

```json
// Add to ~/.claude.json → mcpServers
"local-models": {
    "command": "python3",
    "args": ["/home/neil1988/LocalizationTools/scripts/mcp/local_models_mcp.py"],
    "env": {
        "CUDA_VISIBLE_DEVICES": "0"
    }
}
```

---

## VRAM Budget (RTX 4070 Ti = 12GB)

**Rule: One generation model at a time. Lazy load, generate, unload.**

| Model | VRAM | Can Coexist With Ollama? |
|-------|------|-------------------------|
| Z-Image Turbo (Q4) | ~7GB | YES if Ollama model unloaded |
| Z-Image Turbo (bf16) | ~12GB | NO — needs full GPU |
| Wan 2.2 5B (offload) | ~8-10GB | YES if Ollama unloaded |
| ACE-Step 1.5 | <4GB | YES with Qwen3-4B (~3GB) |
| Hunyuan3D Mini (shape) | 5-6GB | YES if Ollama unloaded |
| AudioLDM 2 | ~8GB | YES if Ollama unloaded |
| CosyVoice 2 | ~6GB | YES if Ollama unloaded |

**Strategy:** The MCP server's `_get_pipeline()` function unloads previous model before loading new one. Ollama auto-manages its own VRAM. No conflicts as long as we don't call Ollama AND a generation model simultaneously.

---

## Build Order & Progress

**Priority = UNIQUE capabilities first, then cost optimization.**
**Server:** `scripts/mcp/local_models_mcp.py` (FastMCP 3.0, lazy loading, one model at a time)

| Step | Model | Status | Time | Landing Page Impact |
|------|-------|--------|------|-------------------|
| **1** | **Z-Image Turbo** | **DONE** — MCP tool built, needs restart + model download | 1 hour | Future fal.ai replacement |
| **2** | **Hunyuan3D 2 Mini** (13.2k stars) | **NEXT** — add tool to MCP server | 1.5 hours | HUGE — rotatable 3D models in Three.js |
| **3** | **ACE-Step 1.5** | TODO | 1 hour | HIGH — ambient soundscape (Piece 11) |
| **4** | **AudioLDM 2** | TODO | 45 min | MEDIUM — UI sound effects |
| **5** | **Wan 2.2 5B** | TODO | 1.5 hours | LOW (Kling is cheap enough) |
| **6** | **CosyVoice 2** | TODO (low priority) | 1 hour | NONE for landing page |

**Minimum WOW stack (1-4):** ~4 hours for images + 3D + music + sound FX.
**Full stack (all 6):** ~7 hours across 2-3 sessions.

---

## Quality Testing Protocol

For each model after MCP build:

```
1. GENERATE 3 test outputs with the same prompt
2. COMPARE vs paid equivalent (if one exists):
   - Z-Image vs Nano Banana 2: same prompt, side-by-side
   - Wan 2.2 vs Kling: same image input, compare motion quality
3. BENCHMARK speed: must complete in <60s for images, <10min for video
4. VERIFY Claude Code can call end-to-end:
   - Call MCP tool
   - Receive file path
   - Open/display the file
5. DECISION: if quality is acceptable, mark paid model as DEPRECATED
```

---

## What This Means for Paid Services

### fal.ai — KEEP for images + video (Claude Code's generation bridge)

| fal.ai Model | Status | Why |
|--------------|--------|-----|
| Nano Banana 2 | **KEEP for now** | Claude Code's only image gen today. Replace with Z-Image LATER after testing |
| Nano Banana Pro | **KEEP for now** | Premium quality when needed |
| Kling 3.0 | **KEEP** | Cinematic video — no local alternative good enough |
| Seedance | **KEEP** | Motion control unique to fal.ai |
| Veo 3 | **AVOID** | Too expensive ($0.29/sec), Kling covers most cases |

**fal.ai role: Claude Code's generation bridge for anything not available locally.**

### Google Gemini API — APP-ONLY (LocaNext Codex)

| Google Model | Status | Why |
|-------------|--------|-----|
| `gemini-3-pro-image-preview` | **KEEP for LocaNext Codex** | User-facing RPG portraits/items/skills deserve Pro quality |
| Imagen 4 Fast ($0.02/img) | **Consider for bulk** | If Codex needs cheap batch generation |

**Google bill: unchanged** — only used inside LocaNext app for user-facing images.
**Key: Google direct is ALWAYS cheaper than fal.ai for the same Google model.** Never use fal.ai to proxy Google models.
**No Google MCP exists** — Claude Code cannot call Google Gemini. Only the running LocaNext app can.

### Local MCPs — UNIQUE capabilities (the real value)

| Model | Capability | Available on fal.ai? | Available on Google? |
|-------|-----------|---------------------|---------------------|
| **ACE-Step 1.5** | Music generation | NO | NO |
| **AudioLDM 2** | Sound effects | NO | NO |
| **Hunyuan3D 2 Mini** | 3D mesh generation | NO | NO |
| **CosyVoice 2** | Emotional TTS | NO | NO |

**This is the real unlock.** These give Claude Code capabilities that money can't buy.

### Summary: Monthly Cost Evolution

| Phase | fal.ai | Google | Local |
|-------|--------|--------|-------|
| **Now** | Images + video (active) | Codex only | Qwen text/vision/TTS |
| **After unique MCPs** | Images + video (active) | Codex only | + Music + SFX + 3D |
| **After Z-Image tested** | Video only (images → local) | Codex only | + Images |
| **After Wan 2.2 tested** | Cinematic only | Codex only | + Ambient video |

---

## References

- Z-Image Turbo: [HuggingFace](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) | [GitHub](https://github.com/Tongyi-MAI/Z-Image) | [Diffusers docs](https://huggingface.co/docs/diffusers/main/api/pipelines/z_image)
- Wan 2.2: [HuggingFace 5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers) | [GitHub](https://github.com/Wan-Video/Wan2.2) | [Wan2GP](https://github.com/deepbeepmeep/Wan2GP)
- ACE-Step 1.5: [GitHub](https://github.com/ace-step/ACE-Step-1.5) | [HuggingFace](https://huggingface.co/ACE-Step/ACE-Step-v1-3.5B)
- Hunyuan3D 2: [GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) | [HuggingFace Mini](https://huggingface.co/tencent/Hunyuan3D-2mini)
- AudioLDM 2: [GitHub](https://github.com/haoheliu/AudioLDM2) | [Diffusers docs](https://huggingface.co/docs/diffusers/main/en/api/pipelines/audioldm2)
- CosyVoice 2: [GitHub](https://github.com/FunAudioLLM/CosyVoice) | [HuggingFace](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B)
- FastMCP 3.0: [GitHub](https://github.com/jlowin/fastmcp) | [Docs](https://gofastmcp.com)
- fal.ai (paid): `~/.claude.json` mcpServers → fal-ai
- AI Power Stack: `docs/reference/AI_POWER_STACK.md`
