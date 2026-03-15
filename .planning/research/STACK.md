# Technology Stack

**Project:** LocaNext v2.0 — Real Data + Dual Platform
**Researched:** 2026-03-15
**Scope:** NEW additions only. Existing stack (Electron, Svelte 5, FastAPI, SQLite/PostgreSQL, FAISS, Model2Vec, Carbon Components, WebSocket) is validated and unchanged.

## Stack Additions for v2.0

### XML Parsing (Already Available)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| lxml | >=4.9.0 (installed) | XML parsing for all game data | Already in requirements.txt and used by ALL 8 NewScripts projects. Battle-tested with sanitizer+recovery pattern. No version bump needed. |

**No action required.** lxml is already a dependency. The work is porting parsing patterns from NewScripts, not adding libraries.

### Image Pipeline (DDS to PNG)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pillow | >=10.0.0 (installed) | DDS texture loading and PNG conversion | Already in requirements.txt. Built-in `DdsImagePlugin` handles DXT1, DXT3, DXT5, BC2, BC3, BC5 reading. |
| pillow-dds | >=1.0.0 (NEW, Windows build only) | Extended DDS format support (BC7) | Game textures use BC7 compression. Pillow's built-in DDS plugin does NOT support BC7 reading per official docs. pillow-dds registers as a Pillow plugin via side-effect import, extending format coverage. MapDataGenerator already uses this exact pattern. |

**Integration approach:** Port `DDSHandler` from `MapDataGenerator/core/dds_handler.py` into `server/tools/ldm/services/`. Convert DDS to PNG on the backend, serve as base64 or cached file via the existing `/mapdata/image/{string_id}` endpoint. The frontend receives PNG — no DDS handling in the browser.

**Key detail:** pillow-dds is Windows-only (DDS files come from game builds on Windows). In LocaNext's Electron deployment, the embedded Python backend runs on Windows where pillow-dds is available. In WSL dev mode, DDS files are accessed via `/mnt/c/` paths but pillow-dds may not install cleanly — use Pillow's built-in DDS support (DXT1/DXT5) for dev testing, with pillow-dds only required in the Windows build.

```python
# Pattern from MapDataGenerator — import for side-effect registration
import sys
if sys.platform == "win32":
    try:
        import pillow_dds  # noqa: F401
    except ImportError:
        pass

from PIL import Image
img = Image.open(dds_path)  # Works with both built-in and pillow-dds formats
png_bytes = io.BytesIO()
img.convert("RGBA").save(png_bytes, format="PNG")
```

### Audio Pipeline (WEM to WAV)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| vgmstream-cli | r2083+ (bundled binary) | WEM to WAV conversion | External binary, NOT a Python package. WEM is Wwise proprietary audio — no Python library can decode it. vgmstream is the standard tool, already bundled in MapDataGenerator/tools/. |

**Integration approach:** Port `AudioHandler` from `MapDataGenerator/core/audio_handler.py` into `server/tools/ldm/services/`. Key changes from MapDataGenerator:
1. Remove `winsound` playback (MapDataGenerator is a Tkinter desktop app) — LocaNext serves WAV bytes via HTTP endpoint instead
2. Keep the subprocess-based WEM-to-WAV conversion (same `vgmstream-cli -o output.wav input.wem` pattern)
3. Keep the path-hashed temp file caching (avoids re-conversion)
4. Serve converted WAV via streaming endpoint for `<audio>` element playback in the browser

**No Python dependencies needed.** vgmstream-cli is a standalone binary bundled with the app. The AudioHandler just calls it via `subprocess.run()`.

**Binary location:** Bundle `vgmstream-cli.exe` in `server/tools/ldm/bin/` (or reference from MapDataGenerator's `tools/` folder during dev). The `_find_vgmstream()` pattern from MapDataGenerator handles discovery.

### AI Summaries (Qwen3 via Ollama)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | 0.27.0 (installed) | HTTP client for Ollama REST API | Already a dependency. Use httpx directly against `http://localhost:11434/api/generate` — simpler than adding the `ollama` Python package. Zero new dependencies. |

**Do NOT install the `ollama` Python package.** httpx is already in requirements.txt and provides everything needed. The Ollama REST API is simple:

```python
import httpx

async def generate_summary(prompt: str, model: str = "qwen3:4b") -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 200}
            }
        )
        return response.json()["response"]
```

**Why httpx over `ollama` package:**
1. httpx is already a dependency (0 new packages)
2. We only need `/api/generate` — one endpoint, one POST call
3. The `ollama` package (0.6.1) adds httpx as its own dependency anyway — circular waste
4. Full control over timeout, retry, error handling (FastAPI patterns)
5. Async-native (matches FastAPI's async handlers)

**Model choice:** Qwen3-4B for speed (117 tok/s on RTX 4070 Ti). Fall back gracefully when Ollama is unavailable — return `{"summary": null, "status": "ai_unavailable"}`. Cache summaries per StringID in the database (add `ai_summary` column to rows table or a dedicated `ai_cache` table).

### Translator Merge (QuickTranslate Logic)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Model2Vec | >=0.3.0 (installed) | Fuzzy matching for merge | Already used for TM search. Same embeddings used for source-text similarity when StringID match fails. |
| xlsxwriter | 3.2.0 (installed) | Excel export | Already a dependency. Used for translator export (LanguageDataExporter column format). |
| openpyxl | 3.1.5 (installed) | Excel reading (import) | Already a dependency. Read-only for importing Excel translations back. |

**No new dependencies.** The merge logic is algorithmic — porting QuickTranslate's match types (exact StringID, StrOrigin match, fuzzy via embeddings) and 7-step postprocessing pipeline. All supporting libraries already exist.

### Game Dev Merge (Position-Aware XML)

**No new dependencies.** Position-aware merge uses lxml (already installed) with custom comparison logic. This is pure algorithmic code — compare XML trees by node position, detect add/remove/modify at node, attribute, and children levels.

## Summary: What to Install

### Python (server/)

```bash
# NOTHING NEW for pip install in development.
# All required libraries already in requirements.txt:
#   lxml>=4.9.0, Pillow>=10.0.0, httpx==0.27.0,
#   model2vec>=0.3.0, xlsxwriter==3.2.0, openpyxl==3.1.5

# Windows build ONLY — add to build step (not requirements.txt):
pip install pillow-dds
```

### Binary (bundled)

```bash
# vgmstream-cli — bundle in server/tools/ldm/bin/ or reference MapDataGenerator/tools/
# Download: https://github.com/vgmstream/vgmstream/releases (r2083+)
# Only vgmstream-cli.exe needed (2.4MB)
```

### Frontend (locaNext/)

```bash
# No new npm packages needed for v2.0.
# DDS→PNG conversion happens on backend, served as PNG to frontend.
# Audio served as WAV stream, played with native <audio> element.
# AI summaries fetched via existing API pattern (fetch → JSON).
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Ollama client | httpx (direct REST) | `ollama` Python package (0.6.1) | Already have httpx. ollama pkg adds dependency for 1 endpoint call. |
| DDS conversion | Pillow + pillow-dds | `pydds`, `texconv`, `DirectXTex` | Pillow is already installed. pillow-dds is proven in MapDataGenerator. pydds is less maintained. |
| WEM conversion | vgmstream-cli (binary) | `ffmpeg`, `pysox` | ffmpeg cannot decode WEM. vgmstream is the ONLY tool that handles Wwise WEM files. |
| AI summaries | Direct Ollama REST | LangChain, LlamaIndex | Massive overkill. We need one prompt-in, text-out call. No chains, no agents, no RAG. |
| Excel export | xlsxwriter | pandas to_excel | xlsxwriter is already a project rule (MEMORY.md). Lighter, more control over formatting. |
| XML parsing | lxml | xml.etree.ElementTree | lxml handles malformed XML (recovery mode), has XPath, proven in all NewScripts. ElementTree crashes on malformed data. |

## What NOT to Add

| Package | Why Not |
|---------|---------|
| `ollama` Python package | httpx does the same thing, already installed |
| `langchain` / `llama-index` | Absurd overhead for a single generate call |
| `ffmpeg-python` | Cannot decode WEM format |
| `pydds` | pillow-dds is proven in MapDataGenerator, no reason to switch |
| `diff-match-patch` | Already handled in v1.0 with custom LCS diff (CJK syllable-level) |
| `pandas` for XML | lxml + manual parsing is the NewScripts pattern, proven and faster |
| Any cloud API SDK (google-cloud, boto3, deepl) | LOCAL ONLY — zero cloud dependency is a core constraint |

## Version Verification

| Package | In requirements.txt | Latest on PyPI | Action |
|---------|-------------------|----------------|--------|
| lxml | >=4.9.0 | 5.3.1 (2025-12) | No change — floor version is fine, pip resolves latest |
| Pillow | >=10.0.0 | 12.1.1 (2026-02) | No change — floor version is fine |
| httpx | 0.27.0 | 0.28.1 (2025-12) | Pinned at 0.27.0, works fine for Ollama REST calls |
| Model2Vec | >=0.3.0 | 0.4.0+ | No change — floor version is fine |
| xlsxwriter | 3.2.0 | 3.2.2 (2025) | Minor patch, no breaking changes. Keep pinned. |
| openpyxl | 3.1.5 | 3.1.5 | Current |

**Confidence:** HIGH — all libraries verified against existing requirements.txt, MapDataGenerator source code, and official documentation.

## Sources

- [Pillow DDS format documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) — built-in DDS support (DXT1/DXT3/DXT5/BC2/BC3/BC5, NOT BC7)
- [Pillow DdsImagePlugin source](https://github.com/python-pillow/Pillow/blob/main/src/PIL/DdsImagePlugin.py) — BC7 support status
- [vgmstream releases](https://github.com/vgmstream/vgmstream/releases) — r2083 (2026-01-25)
- [Ollama Python library on PyPI](https://pypi.org/project/ollama/) — v0.6.1
- [Ollama REST API docs](https://docs.ollama.com/api/introduction) — `/api/generate` endpoint
- MapDataGenerator source: `core/dds_handler.py`, `core/audio_handler.py` — proven patterns
- LocaNext `requirements.txt` — existing dependency inventory
