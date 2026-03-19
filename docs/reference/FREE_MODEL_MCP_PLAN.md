# Free Open-Source Model MCP Build Plan

> Result of 5-scout deep research (240K+ tokens, 2026-03-19)
> Goal: Make the best free AI models usable from Claude Code via custom MCPs

## Why This Plan Exists

fal.ai gives us 600+ models via one API key. But:
- It costs money per generation
- Some models (music, 3D, sound FX) aren't on fal.ai at all
- Going fully local = zero cost, zero dependency, infinite generations

This plan documents the best free models found by autoresearch and how to make each one Claude Code native.

---

## Tier 1: UNIQUE — fal.ai CAN'T do these (build first)

These add capabilities that don't exist anywhere in our current stack.

### 1. ACE-Step 1.5 — Music Generation
| Attribute | Detail |
|-----------|--------|
| **What** | Generate full songs from text prompts (4 minutes in 20 seconds) |
| **Developer** | ACE-Step team |
| **License** | Apache 2.0 |
| **VRAM** | <4GB (fits easily alongside other models) |
| **Quality** | Best open-source music gen in 2026. All genres. LoRA fine-tune from few songs |
| **Install** | `pip install ace-step` or clone from GitHub |
| **Use case for us** | Landing page ambient soundscape (Piece 11), demo videos, product showcase |
| **MCP build effort** | ~1 hour |
| **Priority** | HIGHEST — nothing else does this |

### 2. Hunyuan3D Mini — 3D Mesh Generation
| Attribute | Detail |
|-----------|--------|
| **What** | Text/image → 3D mesh with PBR textures (albedo, normal, roughness) |
| **Developer** | Tencent |
| **License** | Apache 2.0 |
| **VRAM** | 5-6GB |
| **Quality** | State of the art for open-source 3D. Outputs .glb/.obj files |
| **Install** | GitHub clone + pip install |
| **Use case for us** | Generate 3D objects for Three.js scenes, product visualization, game asset previews |
| **MCP build effort** | ~1.5 hours |
| **Priority** | HIGH — no paid alternative exists in our stack |

### 3. AudioLDM 2 — Sound Effect Generation
| Attribute | Detail |
|-----------|--------|
| **What** | Generate any sound from text ("whoosh", "click", "ambient hum", "rain on metal roof") |
| **Developer** | Liu et al. (academic) |
| **License** | Apache 2.0 |
| **VRAM** | ~8GB |
| **Quality** | Most versatile audio gen — speech, SFX, music, ambient |
| **Install** | `pip install audioldm2` or HuggingFace diffusers |
| **Use case for us** | UI sound effects for landing page, demo audio, notification sounds |
| **MCP build effort** | ~1 hour |
| **Priority** | HIGH — pairs with ACE-Step for complete audio stack |

---

## Tier 2: BACKUP — fal.ai already does these (build only if expensive)

These replace paid fal.ai models with free local alternatives.

### 4. Z-Image Turbo — Image Generation
| Attribute | Detail |
|-----------|--------|
| **What** | Text-to-image, 4-7 seconds per image |
| **Developer** | Alibaba (Tongyi-MAI) |
| **License** | Apache 2.0 |
| **VRAM** | 12GB native (fits exactly on RTX 4070 Ti) |
| **Quality** | ~95% of Nano Banana 2. #1 on Arena AI leaderboard (Elo 1080) |
| **Replaces** | fal.ai `fal-ai/nano-banana-2` |
| **Install** | HuggingFace download + diffusers pipeline |
| **MCP build effort** | ~1 hour |
| **Priority** | MEDIUM — only build if fal.ai image costs are high |

### 5. Wan 2.2 1.3B — Video Generation
| Attribute | Detail |
|-----------|--------|
| **What** | Text/image → video, 720p, up to 8 seconds |
| **Developer** | Alibaba (Wan-AI) |
| **License** | Apache 2.0 |
| **VRAM** | 8.2GB |
| **Quality** | ~60-65% of Kling 3.0. Good for backgrounds/ambient, not cinematic |
| **Replaces** | fal.ai `fal-ai/kling-video/v3/pro` |
| **Install** | HuggingFace + diffusers or Wan2GP launcher |
| **MCP build effort** | ~1.5 hours |
| **Priority** | MEDIUM — only build if fal.ai video costs are high |

### 6. CosyVoice 2 — Streaming TTS with Emotions
| Attribute | Detail |
|-----------|--------|
| **What** | Text-to-speech with emotion control, 150ms streaming latency |
| **Developer** | Alibaba |
| **License** | Apache 2.0 |
| **VRAM** | ~6GB |
| **Quality** | Excellent Korean. Streaming. Emotion disentanglement (happy/sad/angry) |
| **Replaces/Upgrades** | Qwen3-TTS (adds streaming + emotion control) |
| **Install** | `pip install cosyvoice` |
| **MCP build effort** | ~1 hour |
| **Priority** | LOW — Qwen3-TTS already works great |

---

## Scalability & Usability Tier List

### Can Test RIGHT AWAY (Ollama pull, no MCP needed)
| Model | Command | VRAM | Claude Code Usable? |
|-------|---------|------|---------------------|
| Qwen3-8B | Already running | 5.2GB | YES (API) |
| Qwen3-VL:8B | Already running | 6.1GB | YES (API) |
| Qwen3-TTS | Already installed | 6-8GB | YES (Python script) |
| DeepSeek-R1:14b | `ollama pull deepseek-r1:14b` | ~10GB | YES (API) |

### Need MCP Wrapper (~1 hour each)
| Model | Why Worth It | Test First? |
|-------|-------------|-------------|
| **ACE-Step 1.5** | UNIQUE music gen, <4GB, insanely fast | YES — test immediately |
| **AudioLDM 2** | UNIQUE sound FX, completes audio stack | YES — test with ACE-Step |
| **Hunyuan3D Mini** | UNIQUE 3D gen, only 5GB | YES — generate test mesh |

### Only Build If Needed (fal.ai backup)
| Model | When to Build |
|-------|--------------|
| Z-Image Turbo | fal.ai image bill > $20/month |
| Wan 2.2 | fal.ai video bill > $30/month |
| CosyVoice 2 | Need streaming TTS or emotion control |

---

## How to Build Each MCP

### Step-by-Step (using `mcp-builder` skill)

```
1. RESEARCH — deep research the model's Python API
   - Find the simplest inference script
   - Identify input params (prompt, seed, output format)
   - Test manually via Python to confirm it works

2. WRAPPER SCRIPT — write Python CLI
   scripts/mcp/generate_{model}.py
   - argparse: --prompt, --output, --seed, etc.
   - Load model (lazy, only when called)
   - Generate → save to file → print path
   - Error handling + timeout

3. MCP TOOL DEFINITION — create MCP server
   scripts/mcp/local_models_mcp.py (FastMCP)
   - One server, multiple tools (one per model)
   - Tool: name, description, parameters
   - Handler calls the wrapper script
   - Returns file path or base64

4. REGISTER — add to ~/.claude.json mcpServers
   "local-models": {
     "command": "python3",
     "args": ["scripts/mcp/local_models_mcp.py"]
   }

5. TEST — verify from Claude Code
   - Call each tool with test prompt
   - Verify output file exists and is valid
   - Benchmark speed (<60s target)
   - Compare quality vs fal.ai equivalent
```

### Architecture: One MCP Server, Multiple Models

```
local-models MCP server
├── tool: generate_music     → ACE-Step 1.5
├── tool: generate_sfx       → AudioLDM 2
├── tool: generate_3d        → Hunyuan3D Mini
├── tool: generate_image     → Z-Image Turbo (if installed)
├── tool: generate_video     → Wan 2.2 (if installed)
└── tool: generate_speech    → CosyVoice 2 (if installed)
```

Models loaded on-demand (lazy loading). Only the called model uses VRAM.

---

## VRAM Budget (RTX 4070 Ti = 12GB)

Can NOT run simultaneously. Load one at a time:

| Combo | Total VRAM | Works? |
|-------|-----------|--------|
| Qwen3-8B (5.2GB) + ACE-Step (<4GB) | ~9GB | YES |
| Qwen3-VL (6.1GB) + AudioLDM 2 (8GB) | ~14GB | NO — swap needed |
| Hunyuan3D Mini (5GB) alone | 5GB | YES, plenty of room |
| Z-Image Turbo (12GB) alone | 12GB | YES, tight but fits |
| Wan 2.2 (8.2GB) alone | 8.2GB | YES |

**Strategy:** Ollama manages model loading/unloading automatically. For non-Ollama models (ACE-Step, AudioLDM, Hunyuan3D), the MCP wrapper should load→generate→unload to free VRAM.

---

## Timeline

| Session | What | Est. Time |
|---------|------|-----------|
| **Session 1** | ACE-Step + AudioLDM 2 MCPs (complete audio stack) | 2-3 hours |
| **Session 2** | Hunyuan3D Mini MCP (3D generation) | 1-2 hours |
| **Session 3** | Z-Image + Wan 2.2 MCPs (only if fal.ai expensive) | 2-3 hours |
| **Session 4** | CosyVoice 2 MCP (only if streaming TTS needed) | 1 hour |

**Total if building all 6:** ~2-3 sessions.
**Minimum for unique capabilities (Tier 1 only):** 1 session.

---

## References

- Full model research: `docs/reference/AI_POWER_STACK.md`
- MCP builder skill: `mcp-builder` (installed)
- fal.ai MCP (current paid stack): `~/.claude.json` → fal-ai
- Ollama models (current free stack): `http://localhost:11434/api/tags`
