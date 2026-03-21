# Technology Stack — v5.0 Offline Bundle + Full Codex

**Project:** LocaNext v5.0
**Researched:** 2026-03-21
**Scope:** NEW capabilities only. Existing stack (Electron, Svelte 5, FastAPI, SQLite/PG, FAISS, Model2Vec, Qwen3, lxml, Carbon) validated and NOT re-researched.

---

## Recommended Stack Additions

### Offline Bundle / Build System

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Model2Vec (bundled weights) | 0.7.0 | Offline embeddings | Already installed. `potion-multilingual-128M` is ~128MB. Bundle `embeddings.safetensors` + `config.json` + `tokenizer.json` into `resources/models/Model2Vec/`. No HuggingFace download needed at runtime. |
| model2vec (pip package) | 0.7.0 | StaticModel loader | Already a dependency. Pure Python + numpy + tokenizers. NO torch dependency. Light build safe. |
| faiss-cpu | 1.8.0 | Vector search offline | Already installed. Numpy-only, no CUDA. Light build safe. |
| vgmstream-cli | r1999+ | WEM-to-WAV decoder | Already bundled in MapDataGenerator (`tools/` folder, 15 DLLs + exe). Bundle into `resources/bin/vgmstream/` for Electron. Windows-only binary, ~8MB total. |
| pillow | 12.1.0 | DDS-to-PNG conversion | Already installed. Supports DDS natively since Pillow 9.x (no `pillow-dds` plugin needed). Verified working in `media_converter.py`. |

**NO new Python packages needed for the light build.** The existing `install_deps.py --light` already skips torch/transformers/sentence-transformers. Model2Vec's dependencies (safetensors, tokenizers, numpy, joblib, jinja2) are all lightweight.

### Light Build vs Full Build

| Component | Light Build | Full Build | Size Impact |
|-----------|-------------|------------|-------------|
| Model2Vec | YES (128MB model) | YES | +128MB |
| FAISS | YES | YES | +15MB |
| Qwen3-Embedding-0.6B | NO | YES | +1.2GB |
| torch | NO | YES | +2.0GB |
| sentence-transformers | NO | YES | +50MB |
| transformers | NO | YES | +100MB |
| vgmstream-cli + DLLs | YES | YES | +8MB |
| **Total additional** | **~151MB** | **~3.5GB** | |

The light/full split is **already implemented** in `tools/install_deps.py` (line 58-68) and `server/tools/shared/embedding_engine.py` (line 38-54 `is_light_mode()`). No new mechanism needed.

**Action:** Pre-download Model2Vec weights at build time, bundle into installer. Create `tools/download_model2vec.py` (similar to existing `download_model.py` but for Model2Vec).

### Audio Pipeline (WEM Playback)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| vgmstream-cli | r1999+ | WEM-to-WAV conversion | Battle-tested in MapDataGenerator. Subprocess call, 60s timeout, MD5-based cache. Pattern already in `server/tools/ldm/services/media_converter.py`. |
| HTML5 `<audio>` | Browser native | WAV playback in Svelte | WAV from vgmstream plays directly. Use `{#key url}` + `?v=${Date.now()}` per project rules. |

**Do NOT use:** pyvgmstream (Python bindings) -- adds complexity, subprocess is simpler and proven. wasm-vgmstream -- experimental, not production ready.

**vgmstream bundling for Electron:** Copy from `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/tools/` into Electron `extraResources`. Required files (all must be co-located):
- `vgmstream-cli.exe`
- 11 DLLs: `libvorbis.dll`, `libmpg123-0.dll`, `libg719_decode.dll`, `avcodec-vgmstream-59.dll`, `avformat-vgmstream-59.dll`, `avutil-vgmstream-57.dll`, `swresample-vgmstream-4.dll`, `libatrac9.dll`, `libcelt-0061.dll`, `libcelt-0110.dll`, `libspeex-1.dll`

### Perforce Path Resolution

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pathlib` (stdlib) | Python 3.10+ | Path manipulation | Already used everywhere. Template-based drive/branch substitution pattern from MapDataGenerator `config.py`. |
| settings.json | -- | Drive/branch config | Same pattern as MapDataGenerator and QACompiler. User sets drive letter (F/D/C) and branch (mainline/cd_beta/cd_alpha/cd_lambda). |

**Pattern already proven** in both QACompiler (`config.py` lines 68-80) and MapDataGenerator (`config.py` lines 87-97):
1. Path templates with `F:` as base drive
2. `_apply_drive_letter()` swaps drive letter
3. `_apply_branch()` swaps branch name
4. Settings loaded from `settings.json` at module init

**For LocaNext:** The `server/tools/ldm/services/mapdata_service.py` already has `PATH_TEMPLATES` and `KNOWN_BRANCHES` (line 24-38). Extend these with QACompiler paths and add drive/branch selection UI.

### Map Rendering (Region Codex)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| d3-zoom | 3.0.0 | Pan/zoom for SVG map | Already installed and used for World Map. |
| d3-force | 3.0.0 | Node layout | Already installed. Force-directed graph for region nodes. |
| d3-selection | 3.0.0 | SVG manipulation | Already installed. |
| d3-drag | 3.0.0 | Node dragging | Already installed. |

**No new frontend packages needed.** The entire d3 stack for interactive maps is already in `locaNext/package.json`.

### Offline Gamedata Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite (via aiosqlite) | Already installed | Offline entity cache | Store parsed XML entity data (items, characters, regions) in SQLite for instant offline access. Same DB used for TM, auth, settings. |
| JSON files | -- | Entity metadata cache | For pre-parsed entity indexes. Faster cold start than re-parsing XML every time. |

**Pattern:** On first load with Perforce access, parse XML and cache into SQLite/JSON. On subsequent loads (or offline), serve from cache. Invalidation: compare file mtimes or Perforce changelist numbers.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| WEM decoding | vgmstream-cli (subprocess) | pyvgmstream (Python bindings) | Subprocess is simpler, already proven in MapDataGenerator, no build complexity |
| WEM decoding | vgmstream-cli | ffmpeg | ffmpeg doesn't support WEM/Wwise natively |
| Offline embeddings | Model2Vec bundled weights | ONNX Runtime export | Model2Vec StaticModel is already tiny (128MB), ONNX adds complexity for no gain |
| Map rendering | d3-zoom + SVG | Leaflet.js | d3-zoom already works for 14 nodes, Leaflet is overkill (tile-based) |
| Map rendering | d3-zoom + SVG | Canvas/WebGL | SVG is simpler for <100 nodes, supports DOM events natively |
| Entity cache | SQLite | IndexedDB (frontend) | Backend SQLite enables API-based access, consistent with existing patterns |
| Light build packaging | pip install --light | PyInstaller frozen exe | Electron already bundles Python via `extraResources`, PyInstaller would double-package |
| DDS support | Pillow 12.1 native | pillow-dds plugin | Pillow has built-in DDS since 9.x, already working in media_converter.py |

---

## What NOT to Add

| Do Not Add | Reason |
|------------|--------|
| **Leaflet.js** | d3-zoom is sufficient for the node map. Leaflet needs tile servers. |
| **PyInstaller for LocaNext** | Electron handles Python bundling via `extraResources`. PyInstaller is for standalone NewScripts only. |
| **pillow-dds** | Pillow 12.1 handles DDS natively. MapDataGenerator spec still lists it as hiddenimport but it's not needed for LocaNext. |
| **p4python (Perforce API)** | LocaNext reads files from Perforce workspace on disk. No P4 commands needed. Path resolution is pure string manipulation. |
| **pydub / soundfile** | Not needed. vgmstream outputs standard WAV that plays in browser `<audio>`. |
| **electron-forge** | Already using electron-builder. No reason to switch. |
| **Any new MCP server** | v5.0 is about bundling and Codex UIs, not new dev tooling. |
| **torch for light build** | Explicitly excluded. Model2Vec works without torch. |

---

## Installation Changes

### Light Build (v5.0 default for offline)

```bash
# No new packages needed! Existing install_deps.py --light covers it.
# Only addition: pre-download Model2Vec weights

python3 tools/download_model2vec.py  # New script, downloads ~128MB model
# Saves to: models/Model2Vec/
#   - config.json
#   - embeddings.safetensors  (~128MB)
#   - tokenizer.json
```

### Electron Builder Changes (package.json)

```json
{
  "extraResources": [
    {
      "from": "../models/Model2Vec",
      "to": "models/Model2Vec",
      "filter": ["**/*"]
    },
    {
      "from": "../bin/vgmstream",
      "to": "bin/vgmstream",
      "filter": ["**/*"]
    }
  ]
}
```

### vgmstream Setup

```bash
# Copy from MapDataGenerator (already in repo)
mkdir -p bin/vgmstream
cp RessourcesForCodingTheProject/NewScripts/MapDataGenerator/tools/vgmstream-cli.exe bin/vgmstream/
cp RessourcesForCodingTheProject/NewScripts/MapDataGenerator/tools/*.dll bin/vgmstream/
```

---

## Integration Points

### Embedding Engine (already handles light mode)

`server/tools/shared/embedding_engine.py` has:
- `is_light_mode()` -- returns True when torch unavailable (line 38-54)
- `Model2VecEngine._find_local_model_path()` -- checks `LOCANEXT_MODELS_PATH` env var and `models/Model2Vec/` relative to server (line 140-151)
- Automatic fallback from Qwen to Model2Vec when light mode detected (line 427-431)

**No changes needed** to the embedding engine for light build support.

### Media Converter (already handles vgmstream)

`server/tools/ldm/services/media_converter.py` has:
- `_find_vgmstream()` -- checks PATH then `bin/vgmstream-cli` relative to server (line 162-184)
- MD5-based WAV cache in temp dir (line 107-108)
- 60s subprocess timeout (line 126-131)

**Change needed:** Update `_find_vgmstream()` to also check `resources/bin/vgmstream/` for packaged Electron app. One line addition.

### MapData Service (path templates ready)

`server/tools/ldm/services/mapdata_service.py` already has:
- `PATH_TEMPLATES` dict with all Perforce paths (line 26-38)
- `KNOWN_BRANCHES` list (line 24)

**Changes needed:**
1. Add drive letter substitution (port from MapDataGenerator `config.py`)
2. Add settings API for drive/branch selection
3. Extend path templates with QACompiler paths (characterinfo, iteminfo, etc.)

---

## Version Pinning Summary

| Package | Pinned Version | Source |
|---------|---------------|--------|
| model2vec | 0.7.0 | `pip show model2vec` (currently installed) |
| faiss-cpu | 1.8.0 | `pip show faiss-cpu` (currently installed) |
| pillow | 12.1.0 | `pip show pillow` (currently installed) |
| vgmstream-cli | r1999+ | `MapDataGenerator/tools/` (already in repo, avcodec v59 DLLs) |
| d3-zoom | ^3.0.0 | `locaNext/package.json` (already installed) |
| d3-force | ^3.0.0 | `locaNext/package.json` (already installed) |
| d3-selection | ^3.0.0 | `locaNext/package.json` (already installed) |
| d3-drag | ^3.0.0 | `locaNext/package.json` (already installed) |
| electron-builder | ^26.0.0 | `locaNext/package.json` (already installed) |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Light build mechanism | HIGH | Verified in source: `install_deps.py`, `embedding_engine.py` already implement it |
| Model2Vec bundling | HIGH | `_find_local_model_path()` already checks for bundled model, just need to pre-download |
| vgmstream integration | HIGH | Already working in MapDataGenerator and `media_converter.py`, just need to bundle binaries |
| Perforce path resolution | HIGH | Same pattern verified in both QACompiler and MapDataGenerator config.py |
| d3 map rendering | HIGH | Already installed and working for World Map page |
| Offline entity caching | MEDIUM | Pattern is standard (SQLite cache), but schema design needs phase-specific work |
| Electron extraResources | HIGH | Already used for server/, tools/, verified in package.json |

---

## Sources

- Model2Vec: [GitHub - MinishLab/model2vec](https://github.com/MinishLab/model2vec), [PyPI](https://pypi.org/project/model2vec/)
- vgmstream: [GitHub - vgmstream/vgmstream](https://github.com/vgmstream/vgmstream), [vgmstream.org](https://vgmstream.org/)
- electron-builder extraResources: [electron.build/contents](https://www.electron.build/contents.html)
- Existing source code: `server/tools/shared/embedding_engine.py`, `server/tools/ldm/services/media_converter.py`, `server/tools/ldm/services/mapdata_service.py`, `tools/install_deps.py`, `locaNext/package.json`, `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/config.py`, `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/config.py`
