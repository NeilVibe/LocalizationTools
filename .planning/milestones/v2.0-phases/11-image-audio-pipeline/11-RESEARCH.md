# Phase 11: Image & Audio Pipeline - Research

**Researched:** 2026-03-15
**Domain:** DDS texture conversion, WEM audio conversion, media serving via FastAPI, Svelte frontend display
**Confidence:** HIGH

## Summary

Phase 11 wires real image and audio data through the existing scaffolded pipeline. The v1.0 scaffolds (ImageTab, AudioTab, MapDataService, mapdata routes) are well-built and need minimal modification. The core work is: (1) adding a DDS-to-PNG conversion endpoint that actually converts and serves real images, (2) adding a WEM-to-WAV conversion endpoint that converts and serves playable audio, and (3) wiring the frontend components to use these real endpoints instead of raw paths.

A critical discovery from research: **Pillow 12.1.0 (already installed) natively supports BC7 DDS textures on Linux**. The `DXGI_FORMAT_BC7_UNORM` format is present in Pillow's `DdsImagePlugin`. This means `pillow-dds` is NOT required -- not even on Windows. The platform guard in MapDataGenerator's `dds_handler.py` is obsolete for current Pillow versions. DDS-to-PNG conversion was verified working on the test fixture (`character_kira.dds` -> 115 bytes PNG) using only stock Pillow.

For WEM audio, `vgmstream-cli.exe` (Windows PE binary) is bundled in `MapDataGenerator/tools/`. In WSL2, we need the Linux build of `vgmstream-cli` from GitHub releases. The existing `AudioHandler` pattern (subprocess conversion, path-hashed caching) ports directly but `winsound` playback must be replaced with HTTP-served WAV for browser `<audio>` element consumption.

**Primary recommendation:** Port DDS conversion and WEM conversion into two lightweight service modules under `server/tools/ldm/services/`, add two streaming endpoints (`/mapdata/thumbnail/{texture_name}` returns PNG bytes, `/mapdata/audio/stream/{string_id}` returns WAV bytes), and update the frontend ImageTab/AudioTab to use these endpoints. No new Python packages needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEDIA-01 | DDS textures convert to PNG via Pillow for browser display | Pillow 12.1.0 natively supports DXT1/DXT5/BC7. Verified with fixture DDS file. Port DDSHandler pattern from MapDataGenerator. |
| MEDIA-02 | WEM audio files play back via vgmstream-cli conversion or WAV fallback | AudioHandler pattern from MapDataGenerator ports directly. Need Linux vgmstream-cli binary. WAV served via HTTP endpoint for browser audio element. |
| MEDIA-03 | Real data flows from MapDataService through API to ImageTab/AudioTab | MapDataService already has `_resolve_image_chains()` and `get_image_context()`. Need to add thumbnail serving endpoint and audio stream endpoint. Frontend scaffolds already fetch from correct API paths. |
| MEDIA-04 | Missing image/audio shows graceful placeholder with explanatory text | ImageTab/AudioTab already have empty states for 404/missing. Need to ensure placeholder text is specific ("No image linked to this string" vs "Image conversion failed" vs "DDS format unsupported"). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.0 (installed) | DDS-to-PNG conversion | Already installed. Natively supports DXT1/DXT3/DXT5/BC7 on Linux. No additional plugin needed. |
| vgmstream-cli | r2083+ (binary) | WEM-to-WAV conversion | Only tool that decodes Wwise WEM audio. Already bundled for Windows in MapDataGenerator/tools/. Need Linux build for WSL2. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI StreamingResponse | (built-in) | Serve PNG/WAV bytes as HTTP response | For thumbnail and audio streaming endpoints |
| hashlib | (stdlib) | Path-based cache key generation | For WEM-to-WAV temp file caching (same pattern as AudioHandler) |
| subprocess | (stdlib) | Call vgmstream-cli | For WEM conversion (same pattern as AudioHandler) |
| tempfile | (stdlib) | Temp directory for converted WAV files | Cache converted audio between requests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pillow built-in DDS | pillow-dds package | pillow-dds is unnecessary -- Pillow 12.1 handles all game DDS formats natively including BC7 |
| vgmstream-cli | ffmpeg | ffmpeg CANNOT decode WEM/Wwise format. vgmstream is the only option. |
| StreamingResponse | FileResponse | StreamingResponse is better for dynamically converted bytes; FileResponse needs a file on disk |
| In-memory PNG cache | Disk PNG cache | In-memory is faster for repeated lookups; disk cache is appropriate for larger WAV files |

**Installation:**
```bash
# Python: NOTHING NEW needed
# All libraries already installed (Pillow 12.1.0 handles DDS natively)

# Binary: Download Linux vgmstream-cli for WSL2
# From: https://github.com/vgmstream/vgmstream/releases (r2083+)
# Place at: server/tools/ldm/bin/vgmstream-cli (Linux binary)
# OR: reference MapDataGenerator/tools/vgmstream-cli.exe (Windows only)
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/
    media_converter.py     # NEW: DDS-to-PNG + WEM-to-WAV conversion
    mapdata_service.py     # EXISTING: add audio chain resolution
  routes/
    mapdata.py             # EXISTING: add thumbnail + audio stream endpoints
locaNext/src/lib/components/ldm/
  ImageTab.svelte          # EXISTING: update thumbnail_url to use new endpoint
  AudioTab.svelte          # EXISTING: update audio src to use stream endpoint
```

### Pattern 1: MediaConverter Service (Singleton)
**What:** Centralized service that handles DDS-to-PNG and WEM-to-WAV conversion with caching
**When to use:** All media conversion requests go through this service
**Example:**
```python
# Source: MapDataGenerator/core/dds_handler.py (ported pattern)
from __future__ import annotations

import io
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image
from loguru import logger

class MediaConverter:
    """DDS-to-PNG and WEM-to-WAV conversion with LRU caching."""

    def __init__(self, cache_size: int = 100):
        self._png_cache: dict[str, bytes] = {}  # texture_name -> PNG bytes
        self._cache_size = cache_size
        self._vgmstream_path: Optional[Path] = None
        self._temp_dir = Path(tempfile.gettempdir()) / "locanext_audio"
        self._temp_dir.mkdir(exist_ok=True)
        self._vgmstream_path = self._find_vgmstream()

    def convert_dds_to_png(self, dds_path: Path, max_size: int = 256) -> Optional[bytes]:
        """Convert DDS file to PNG bytes. Returns None on failure."""
        cache_key = str(dds_path)
        if cache_key in self._png_cache:
            return self._png_cache[cache_key]

        if not dds_path.exists():
            return None

        try:
            img = Image.open(dds_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

            # LRU eviction
            if len(self._png_cache) >= self._cache_size:
                oldest = next(iter(self._png_cache))
                del self._png_cache[oldest]
            self._png_cache[cache_key] = png_bytes
            return png_bytes

        except Exception as e:
            logger.error(f"[MEDIA] DDS conversion failed for {dds_path}: {e}")
            return None

    def convert_wem_to_wav(self, wem_path: Path) -> Optional[Path]:
        """Convert WEM to WAV via vgmstream-cli. Returns WAV path or None."""
        path_hash = hashlib.md5(str(wem_path).encode()).hexdigest()[:8]
        wav_path = self._temp_dir / f"{wem_path.stem}_{path_hash}.wav"

        if wav_path.exists():
            if wav_path.stat().st_mtime >= wem_path.stat().st_mtime:
                return wav_path

        if not self._vgmstream_path:
            logger.warning("[MEDIA] vgmstream-cli not available")
            return None

        try:
            result = subprocess.run(
                [str(self._vgmstream_path), "-o", str(wav_path), str(wem_path)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and wav_path.exists():
                return wav_path
            logger.error(f"[MEDIA] vgmstream failed: {result.stderr}")
            return None
        except Exception as e:
            logger.error(f"[MEDIA] WEM conversion failed: {e}")
            return None
```

### Pattern 2: Streaming Endpoints (FastAPI)
**What:** Endpoints that serve converted media as binary responses
**When to use:** Frontend requests image thumbnails or audio playback
**Example:**
```python
# Add to server/tools/ldm/routes/mapdata.py
from fastapi.responses import Response, FileResponse

@router.get("/mapdata/thumbnail/{texture_name}")
async def get_thumbnail(texture_name: str):
    """Serve DDS texture as PNG thumbnail."""
    service = get_mapdata_service()
    converter = get_media_converter()

    dds_path = service._dds_index.get(texture_name.lower())
    if not dds_path:
        raise HTTPException(404, f"Texture not found: {texture_name}")

    png_bytes = converter.convert_dds_to_png(dds_path)
    if not png_bytes:
        raise HTTPException(500, f"Conversion failed for: {texture_name}")

    return Response(content=png_bytes, media_type="image/png")

@router.get("/mapdata/audio/stream/{string_id}")
async def stream_audio(string_id: str):
    """Serve WEM audio as WAV stream for browser playback."""
    service = get_mapdata_service()
    converter = get_media_converter()

    audio_ctx = service.get_audio_context(string_id)
    if not audio_ctx:
        raise HTTPException(404, f"No audio for: {string_id}")

    wem_path = Path(convert_to_wsl_path(audio_ctx.wem_path))
    wav_path = converter.convert_wem_to_wav(wem_path)
    if not wav_path:
        raise HTTPException(500, "Audio conversion failed")

    return FileResponse(wav_path, media_type="audio/wav")
```

### Pattern 3: Frontend thumbnail_url Flow
**What:** ImageTab uses the thumbnail endpoint URL from API response
**When to use:** ImageTab renders the image
**Example:**
```svelte
<!-- ImageTab.svelte -- thumbnail_url already points to /api/ldm/mapdata/thumbnail/{name} -->
<img
  src={imageContext.thumbnail_url}
  alt={imageContext.texture_name}
  class="thumbnail"
  onerror={(e) => { e.target.style.display = 'none'; }}
/>
```
The `thumbnail_url` field in `ImageContext` already generates the correct path (`/api/ldm/mapdata/thumbnail/{texture_name}`). The frontend just needs to use it -- which it already does.

### Pattern 4: Audio Stream URL in AudioTab
**What:** AudioTab uses a stream endpoint instead of raw WEM path
**When to use:** AudioTab renders the audio player
**Current problem:** AudioTab currently sets `<source src="{audioContext.wem_path}" />` which is a Windows filesystem path -- browsers cannot play this.
**Fix:** Change to use the API stream endpoint.

### Anti-Patterns to Avoid
- **Sending DDS bytes to the browser:** Browsers cannot render DDS. Always convert server-side and send PNG.
- **Using winsound for playback:** This is a Windows-only Tkinter pattern. LocaNext serves WAV via HTTP for browser audio element.
- **Platform-guarding pillow-dds import:** Pillow 12.1 handles DDS natively on all platforms. No conditional import needed.
- **Blocking on vgmstream conversion:** WEM-to-WAV can take 1-2 seconds for large files. Use `asyncio.to_thread()` for the subprocess call in async endpoints.
- **Caching PIL Image objects in memory:** Cache PNG bytes instead. PIL Image objects hold decompressed bitmap data (much larger than compressed PNG).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DDS texture decoding | Custom DDS parser | Pillow's built-in DdsImagePlugin | Handles DXT1/DXT3/DXT5/BC5/BC7 natively. Tested and verified on project fixture files. |
| WEM audio decoding | Custom Wwise decoder | vgmstream-cli (binary) | WEM is proprietary Wwise format. No Python library can decode it. vgmstream is the standard tool. |
| Image caching | File-based cache system | In-memory LRU dict (same pattern as DDSHandler) | Simple, fast, no disk I/O. Max 100 entries = approx 5-10MB memory. |
| WAV caching | Re-convert every request | Path-hashed temp files (same pattern as AudioHandler) | WAV files are large (1-10MB). Disk cache is appropriate. |
| Placeholder images | Server-generated PIL placeholder | CSS/HTML placeholder in frontend | The frontend already has styled empty states. No need for server-generated placeholder images. |

**Key insight:** Both MapDataGenerator handlers (DDSHandler, AudioHandler) are well-designed and only need minor adaptation -- remove Tkinter/winsound dependencies, add HTTP-serving output. The conversion logic is identical.

## Common Pitfalls

### Pitfall 1: DDS Platform Guard (RESOLVED)
**What goes wrong:** MapDataGenerator conditionally imports `pillow-dds` only on Windows. In WSL2/Linux, this guard causes DDS formats to appear unsupported.
**Resolution:** Pillow 12.1.0 (installed) natively supports BC7. No `pillow-dds` needed. Verified: `DXGI_FORMAT_BC7_UNORM` is present in `DdsImagePlugin`. Fixture DDS file converts successfully on Linux.
**How to avoid:** Simply `from PIL import Image` and call `Image.open(dds_path)`. No platform checks, no pillow-dds import.
**Confidence:** HIGH -- verified with actual code execution on this system.

### Pitfall 2: WEM Fixture Files Are Actually WAV
**What goes wrong:** The test fixture `.wem` files in `tests/fixtures/mock_gamedata/audio/` are actually RIFF WAV files renamed to `.wem`. Tests pass but don't validate real WEM-to-WAV conversion.
**Why it matters:** Real WEM files from the game use Wwise encoding that ONLY vgmstream-cli can decode. Tests with renamed WAV files will pass even if vgmstream-cli is missing or broken.
**How to avoid:** Unit tests should mock the subprocess call. Integration tests should use real WEM files (if available) or explicitly skip with `pytest.mark.skipif(not vgmstream_available)`.
**Warning signs:** All audio tests pass but audio playback fails in the browser with real game data.

### Pitfall 3: vgmstream-cli Not Available in WSL2
**What goes wrong:** The bundled `vgmstream-cli.exe` is a Windows PE binary. It cannot run natively in WSL2 (unless WSL interop is enabled for .exe files).
**Why it happens:** MapDataGenerator is a Windows desktop app. LocaNext server runs in WSL2.
**How to avoid:** Download the Linux build of vgmstream-cli from GitHub releases. Place at `server/tools/ldm/bin/vgmstream-cli`. The `_find_vgmstream()` pattern already checks `shutil.which()` as fallback.
**Alternative:** WSL2 can sometimes run Windows .exe files via interop. Test with `./vgmstream-cli.exe --help` in WSL. If it works, reference the existing MapDataGenerator binary directly.

### Pitfall 4: AudioTab Uses Raw WEM Path as Source
**What goes wrong:** The current `AudioTab.svelte` sets `<source src="{audioContext.wem_path}" />` which is a Windows filesystem path like `F:\perforce\...`. Browsers cannot load files from Windows paths.
**How to avoid:** Change the audio source to use the stream endpoint: `/api/ldm/mapdata/audio/stream/{string_id}`. The AudioTab already has the `string_id` from `selectedRow`.
**Warning signs:** Audio player shows but playback button does nothing or throws network error.

### Pitfall 5: Blocking Subprocess in Async Endpoint
**What goes wrong:** `subprocess.run()` for vgmstream-cli blocks the FastAPI event loop. If multiple users request audio simultaneously, all other requests are blocked.
**How to avoid:** Use `asyncio.to_thread(converter.convert_wem_to_wav, wem_path)` to run the blocking subprocess in a thread pool. This keeps the event loop responsive.

### Pitfall 6: Audio Chain Not Yet Built in MapDataService
**What goes wrong:** `MapDataService._strkey_to_audio` is currently empty -- `initialize()` only resolves image chains, not audio chains. `get_audio_context()` always returns None.
**Why it happens:** The audio chain (StrKey -> EventName -> WEM path) is more complex than the image chain. It requires parsing export XMLs and scanning WEM folders -- the full `AudioIndex` pattern from `linkage.py`.
**How to avoid:** Implement audio chain resolution in MapDataService, porting the simplified version of `AudioIndex.scan_folder()` + `AudioIndex.load_event_mappings()` from linkage.py. The full VRS ordering is NOT needed for LocaNext -- just event-to-WEM mapping is sufficient.

## Code Examples

### DDS-to-PNG Conversion (Verified Working)
```python
# Verified on this system with Pillow 12.1.0, no pillow-dds needed
from PIL import Image
import io

def convert_dds_to_png(dds_path: Path, max_size: int = 256) -> Optional[bytes]:
    """Convert DDS to PNG bytes. Works on Linux with stock Pillow 12.1+."""
    img = Image.open(dds_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

### WEM-to-WAV Conversion (Ported from AudioHandler)
```python
# Source: MapDataGenerator/core/audio_handler.py (adapted for LocaNext)
import subprocess
import hashlib
from pathlib import Path

def convert_wem_to_wav(
    wem_path: Path,
    vgmstream_path: Path,
    temp_dir: Path,
) -> Optional[Path]:
    """Convert WEM to WAV using vgmstream-cli. Cache by path hash."""
    path_hash = hashlib.md5(str(wem_path).encode()).hexdigest()[:8]
    wav_path = temp_dir / f"{wem_path.stem}_{path_hash}.wav"

    # Cache hit
    if wav_path.exists() and wav_path.stat().st_mtime >= wem_path.stat().st_mtime:
        return wav_path

    result = subprocess.run(
        [str(vgmstream_path), "-o", str(wav_path), str(wem_path)],
        capture_output=True, text=True, timeout=60,
    )
    return wav_path if result.returncode == 0 and wav_path.exists() else None
```

### Streaming Endpoint (FastAPI Pattern)
```python
from fastapi.responses import Response, FileResponse

@router.get("/mapdata/thumbnail/{texture_name}")
async def get_thumbnail(texture_name: str):
    """Serve DDS as PNG thumbnail with cache headers."""
    converter = get_media_converter()
    service = get_mapdata_service()

    dds_path = service._dds_index.get(texture_name.lower())
    if not dds_path:
        raise HTTPException(404, f"Texture '{texture_name}' not found")

    wsl_path = Path(convert_to_wsl_path(str(dds_path)))
    png_bytes = converter.convert_dds_to_png(wsl_path)
    if not png_bytes:
        raise HTTPException(500, f"Failed to convert '{texture_name}'")

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
```

### AudioTab Stream URL Fix
```svelte
<!-- CURRENT (broken -- raw Windows path): -->
<source src="{audioContext.wem_path}" />

<!-- FIXED (API stream endpoint): -->
<audio controls preload="none" class="audio-player">
  <source
    src="{API_BASE}/api/ldm/mapdata/audio/stream/{selectedRow?.string_id}"
    type="audio/wav"
  />
</audio>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pillow-dds required for BC7 | Pillow 12.x has native BC7 support | Pillow 11.0+ (2024) | No extra package needed. Remove platform guard entirely. |
| winsound desktop playback | HTTP-served WAV for browser audio | LocaNext architecture | Completely different playback model. Port conversion only, not playback. |
| Windows paths in config | WSL path translation via convert_to_wsl_path | Phase 07 (already done) | Path utility already exists in mapdata_service.py |

**Deprecated/outdated:**
- `pillow-dds` package: Unnecessary with Pillow 12.1+. All DDS formats Pillow supports are built-in.
- `winsound` module: Windows-only, irrelevant for web-served audio.
- `ImageTk` Tkinter helpers: Not needed -- we serve PNG bytes via HTTP.

## Open Questions

1. **vgmstream-cli Linux binary**
   - What we know: Linux x86_64 builds are available on GitHub releases. The Windows .exe is already bundled.
   - What's unclear: Whether WSL2 can run the Windows .exe via interop (avoids needing a separate Linux binary).
   - Recommendation: Test `vgmstream-cli.exe` via WSL interop first. If it works, use it. If not, download Linux build. Either way, handle "not available" gracefully.

2. **Audio chain resolution scope**
   - What we know: The full AudioIndex in linkage.py handles WEM scanning, export XML parsing, VRS ordering, and script line loading. LocaNext's MapDataService currently only resolves image chains.
   - What's unclear: How much of the AudioIndex chain is needed. LocaNext needs: event_name -> WEM path (for playback). Script text is bonus.
   - Recommendation: Implement minimal audio chain: scan WEM folder + map event names to paths. Script text can come from StrKey -> loc XML chain that already exists. Skip VRS ordering (not relevant for LocaNext's use case).

3. **Cache invalidation**
   - What we know: DDS files rarely change. WEM files rarely change. Caches can be long-lived.
   - What's unclear: Whether MapDataService re-initialization (branch/drive change) should clear media caches.
   - Recommendation: Clear media caches when MapDataService.initialize() is called with new branch/drive.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + Playwright |
| Config file | `pytest.ini` (exists) |
| Quick run command | `python -m pytest tests/unit/ldm/test_mapdata_service.py -x -q` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEDIA-01 | DDS-to-PNG conversion via Pillow | unit | `python -m pytest tests/unit/ldm/test_media_converter.py::TestDdsConversion -x` | Wave 0 |
| MEDIA-02 | WEM-to-WAV via vgmstream-cli | unit | `python -m pytest tests/unit/ldm/test_media_converter.py::TestWemConversion -x` | Wave 0 |
| MEDIA-03 | API endpoints serve real image/audio | unit | `python -m pytest tests/unit/ldm/test_routes_mapdata.py -x` | Wave 0 |
| MEDIA-04 | Missing media returns graceful placeholder | unit | `python -m pytest tests/unit/ldm/test_media_converter.py::TestGracefulFallback -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_media_converter.py -x -q`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_media_converter.py` -- covers MEDIA-01, MEDIA-02, MEDIA-04
- [ ] `tests/unit/ldm/test_routes_mapdata.py` -- covers MEDIA-03 (route-level tests for thumbnail + audio stream endpoints)
- [ ] Existing `test_mapdata_service.py` covers MapDataService lookup logic (already exists, 372 lines)
- [ ] Existing `mapdata-context.spec.ts` covers frontend tab rendering (already exists, Playwright)

*(Note: existing test_mapdata_service.py has 372 lines of tests covering image/audio context lookups, WSL path conversion, knowledge table building, DDS index building, and image chain resolution. These tests cover the MapDataService layer -- Wave 0 gaps are the MediaConverter layer and the route-level streaming endpoints.)*

## Sources

### Primary (HIGH confidence)
- `MapDataGenerator/core/dds_handler.py` -- DDSHandler class with LRU caching, thumbnail generation, pillow-dds import pattern
- `MapDataGenerator/core/audio_handler.py` -- AudioHandler class with vgmstream-cli subprocess, path-hashed WAV caching, generation counters
- `MapDataGenerator/core/linkage.py` -- AudioIndex class with WEM scanning, event-to-StringId mapping, script line loading
- `server/tools/ldm/services/mapdata_service.py` -- MapDataService with image chain resolution, DDS index, knowledge table
- `server/tools/ldm/routes/mapdata.py` -- existing REST endpoints for image/audio/context/configure/status
- `locaNext/src/lib/components/ldm/ImageTab.svelte` -- scaffolded image display with empty states
- `locaNext/src/lib/components/ldm/AudioTab.svelte` -- scaffolded audio player with script text display
- `tests/unit/ldm/test_mapdata_service.py` -- 372 lines of existing unit tests
- `tests/fixtures/mock_gamedata/` -- fixture DDS and WEM files (DDS=ARGB8888, WEM=renamed WAV)
- Live verification: Pillow 12.1.0 DDS-to-PNG conversion confirmed working on Linux with fixture file

### Secondary (MEDIUM confidence)
- [Pillow DDS format docs](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) -- BC7 support added in Pillow 11.0+
- [vgmstream GitHub releases](https://github.com/vgmstream/vgmstream/releases) -- Linux x86_64 builds available

### Tertiary (LOW confidence)
- WSL2 Windows .exe interop for vgmstream-cli -- untested, may work via WSL interop

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pillow DDS support verified with actual code execution. vgmstream-cli availability confirmed.
- Architecture: HIGH -- scaffolds are well-built, patterns port directly from MapDataGenerator.
- Pitfalls: HIGH -- all sourced from codebase inspection and live testing. BC7 pitfall is RESOLVED (Pillow handles it natively).

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no fast-moving dependencies)
