# Phase 74: Mock Data Foundation - Research

**Researched:** 2026-03-24
**Domain:** Perforce path resolution, mock gamedata fixtures, DDS/WEM/XML asset pipeline
**Confidence:** HIGH

## Summary

Phase 74 requires the mock gamedata directory at `tests/fixtures/mock_gamedata/` to mirror the real Perforce folder structure so that `PerforcePathService.configure_for_mock_gamedata()` resolves DDS textures, WEM audio, and XML language data identically to production. The codebase already has substantial mock data infrastructure -- a generator script (`tools/generate_mega_index_mockdata.py`), 30+ knowledge entries, 5 characters, 5 items, etc. -- but there are three concrete gaps: (1) DDS stubs are 4-byte "DDS " headers that Pillow cannot open as real images, (2) WEM files are 0-byte stubs that vgmstream cannot convert, and (3) Korean/Chinese audio folders do not exist.

The existing `configure_for_mock_gamedata()` method already maps all 11 PATH_TEMPLATES to the mock directory. The DEV mode startup in `server/main.py` calls this automatically. The thumbnail endpoint (`/mapdata/thumbnail/{texture_name}`) already has a fallback to `textures/` PNG files. So the primary work is: create valid DDS files (or extend the PNG fallback), create valid WEM stubs (or provide WAV alternatives), add Korean/Chinese audio folders, and ensure `.loc.xml` files include JP language content alongside EN/KR.

**Primary recommendation:** Generate real 64x64 PNG images (already exist in `textures/`) and valid minimal DDS files (128-byte DDS with proper headers). For WEM, generate minimal valid WAV files and either rename to .wem or teach the audio endpoint to serve WAV directly (it already can). Add missing Korean/Chinese audio directories with copies of English WEM/WAV stubs. Add JP language data to existing .loc.xml files.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOCK-09 | Mock gamedata structure mirrors real Perforce paths exactly (F:\perforce\cd\mainline\...) | `configure_for_mock_gamedata()` already maps all 11 templates. Gaps: missing `sound/windows/Korean/` and `sound/windows/Chinese(PRC)/` directories. No `StaticInfo/questinfo/` XMLs populated. |
| MOCK-10 | Mock DDS textures resolvable via PerforcePathService with correct drive/branch substitution | DDS files exist at `texture/image/` (correct path). Current stubs are 4-byte "DDS " headers -- Pillow `Image.open()` fails on them. Need valid DDS or extend PNG fallback. PNG versions already exist in `textures/`. |
| MOCK-11 | Mock WEM audio files present at expected audio folder paths per language | English WEM stubs exist (10 files, 0 bytes each). Korean and Chinese folders missing entirely. Need valid audio content or WAV fallback. |
| MOCK-12 | Mock language data XML files (.loc.xml) with realistic content at loc folder paths | `loc/` has `languagedata_ENG.xml`, `languagedata_KOR.xml`, `showcase_dialogue.loc.xml`. No JP language data. `export__/` has `.loc.xml` files per entity type. Content is realistic with `<br/>` tags properly escaped as `&lt;br/&gt;`. |
</phase_requirements>

## Architecture Patterns

### How PerforcePathService Works

The service is a singleton with 11 path templates. In production, `configure(drive, branch)` substitutes the drive letter and branch name into Windows paths, then converts to WSL paths. In DEV mode, `configure_for_mock_gamedata(mock_dir)` bypasses all of this and directly maps template keys to subdirectories of the mock data root:

```python
# Production: F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo
#           -> /mnt/f/perforce/cd/mainline/resource/GameData/StaticInfo/characterinfo

# Mock:      tests/fixtures/mock_gamedata/StaticInfo/characterinfo
```

Key mapping in `configure_for_mock_gamedata()`:

| Template Key | Production Path Suffix | Mock Path |
|-------------|----------------------|-----------|
| `knowledge_folder` | `StaticInfo/knowledgeinfo` | `mock_gamedata/StaticInfo/knowledgeinfo` |
| `character_folder` | `StaticInfo/characterinfo` | `mock_gamedata/StaticInfo/characterinfo` |
| `faction_folder` | `StaticInfo/factioninfo` | `mock_gamedata/StaticInfo/factioninfo` |
| `texture_folder` | `texture/image` | `mock_gamedata/texture/image` |
| `audio_folder` | `sound/windows/English(US)` | `mock_gamedata/sound/windows/English(US)` |
| `audio_folder_kr` | `sound/windows/Korean` | `mock_gamedata/sound/windows/Korean` |
| `audio_folder_zh` | `sound/windows/Chinese(PRC)` | `mock_gamedata/sound/windows/Chinese(PRC)` |
| `export_folder` | `export__` | `mock_gamedata/export__` |
| `loc_folder` | `loc` | `mock_gamedata/loc` |
| `waypoint_folder` | `StaticInfo/factioninfo/NodeWaypointInfo` | `mock_gamedata/StaticInfo/factioninfo/NodeWaypointInfo` |
| `vrs_folder` | `localization` | `mock_gamedata/localization` |

### How DEV Mode Auto-Initializes

In `server/main.py` startup:
1. `configure_for_mock_gamedata()` is called with the mock directory
2. `MegaIndex.build()` runs, which calls `_scan_dds_textures()` and `_scan_wem_files()` from resolved paths
3. MapDataService is initialized -- it populates `_strkey_to_image` by parsing StaticInfo XMLs and matching UITextureName to PNG files in `textures/`
4. The thumbnail endpoint has a fallback: if DDS index misses, it checks `mock_gamedata/textures/` for `.png`, `.dds`, `.jpg` by stem name

### How DDS Conversion Works

`MediaConverter.convert_dds_to_png()` uses `Pillow Image.open()` on the DDS file. Pillow can read DDS files natively but requires a valid DDS header (128 bytes minimum: 4-byte magic "DDS " + 124-byte header struct). The current mock stubs are only 4 bytes (`DDS `) -- Pillow will fail with "cannot identify image file."

### How WEM Conversion Works

`MediaConverter.convert_wem_to_wav()` uses `vgmstream-cli` subprocess. Current WEM stubs are 0-byte files -- vgmstream will fail. The audio streaming endpoint already has a WAV passthrough: if `source_path.suffix == ".wav"` it serves directly without conversion.

### How .loc.xml Files Are Parsed

MegaIndex's `_parse_export_loc()` scans `export_folder.rglob("*.loc.xml")`. Each file has `<LocStr StringId="..." StrOrigin="..." Str="..."/>` elements. The `loc_folder` contains standalone language data files (`languagedata_ENG.xml`, `languagedata_KOR.xml`). The `<br/>` tags in XML attribute values are escaped as `&lt;br/&gt;` per project rules.

## Current State Analysis

### What Exists and Works
- **Directory structure:** All 11 template key directories exist and map correctly
- **StaticInfo XMLs:** characterinfo, iteminfo, skillinfo, gimmickinfo, factioninfo, knowledgeinfo, regioninfo, questinfo -- all populated with realistic game data
- **Export XMLs:** 5 entity type folders (Character, Item, Skill, Gimmick, Dialog) with both `.xml` and `.loc.xml` files
- **Language data:** ENG + KOR language files with proper `<br/>` encoding
- **PNG textures:** 30+ real PNG images in `textures/` directory (used as fallback by thumbnail endpoint)
- **DDS stubs:** 26 files in `texture/image/` with "DDS " 4-byte header
- **WEM stubs:** 10 files in `sound/windows/English(US)/` with 0-byte content
- **Generator script:** `tools/generate_mega_index_mockdata.py` with central registry of all entities

### Gaps to Fill

| Gap | Impact | Fix Effort |
|-----|--------|------------|
| DDS files are 4-byte stubs (Pillow rejects them) | MOCK-10: DDS-to-PNG conversion fails | LOW: Generate valid 64x64 DDS files with Pillow, or copy PNGs with .dds extension plus valid header |
| WEM files are 0-byte stubs | MOCK-11: Audio conversion fails | LOW: Generate minimal WAV files and rename to .wem, or provide .wav alongside .wem |
| Korean audio folder missing | MOCK-11: `resolve_audio_folder("kor")` returns nonexistent path | LOW: Create directory + copy WEM stubs |
| Chinese audio folder missing | MOCK-11: `resolve_audio_folder("zho-cn")` returns nonexistent path | LOW: Create directory + copy WEM stubs |
| No JP language data | MOCK-12: Success criteria says "EN/KR/JP minimum" | LOW: Add `languagedata_JPN.xml` to loc/ |
| Existing test (`test_mock_media_stubs.py`) checks `AUDIO_DIR = MOCK_DIR / "audio"` but actual path is `sound/windows/English(US)` | Test path mismatch -- test may be failing silently | LOW: Fix test path |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Valid DDS file generation | Custom DDS binary writer | `Pillow Image.save(format="DDS")` | DDS format has complex header; Pillow handles it |
| Valid WAV file generation | Custom WAV binary writer | `wave` stdlib module | WAV is simple but has headers that must be correct |
| Path mapping logic | Custom path resolver | Existing `configure_for_mock_gamedata()` | Already implemented and tested, just needs correct directory structure |

## Common Pitfalls

### Pitfall 1: DDS Stub Files That Pillow Cannot Open
**What goes wrong:** The existing 4-byte DDS stubs cause `Image.open()` to throw "cannot identify image file" errors. The `convert_dds_to_png()` method returns None, and thumbnails 404.
**Why it happens:** DDS format requires a 128-byte minimum header (4-byte magic + 124-byte DDS_HEADER struct with width, height, pixel format, etc.).
**How to avoid:** Generate DDS files using Pillow: create a 64x64 RGBA image, save as DDS format. Pillow's DDS writer handles the header correctly.
**Warning signs:** `[MEGAINDEX] DDS scan` logs find files but thumbnail API returns 404.

### Pitfall 2: WEM Files That vgmstream Rejects
**What goes wrong:** 0-byte WEM files cause vgmstream-cli to fail with "file too small" errors.
**Why it happens:** WEM is a Wwise container format requiring RIFF/RIFX headers. Empty files are not valid.
**How to avoid:** Two options: (a) Generate tiny valid WAV files (44-byte header + minimal samples) and name them `.wem` -- vgmstream won't parse them but the audio endpoint already has WAV passthrough. (b) Better: place `.wav` files alongside `.wem` files and ensure the audio chain prefers WAV when WEM conversion fails.
**Warning signs:** Audio stream endpoint returns 500 errors.

### Pitfall 3: Test Path Mismatch
**What goes wrong:** `test_mock_media_stubs.py` references `MOCK_DIR / "audio"` but WEM files are at `MOCK_DIR / "sound" / "windows" / "English(US)"`. The `texture` test references `TEXTURES_DIR = MOCK_DIR / "textures"` (PNGs) but DDS files are at `MOCK_DIR / "texture" / "image"`.
**Why it happens:** Tests were written before the directory structure was aligned to Perforce paths.
**How to avoid:** Update test paths to match actual directory structure, or ensure both paths have files.

### Pitfall 4: Missing Japanese Language Data
**What goes wrong:** Success criteria requires EN/KR/JP minimum, but only EN and KR exist.
**Why it happens:** The mock data generator focuses on the showcase universe which was Korean-centric.
**How to avoid:** Add `languagedata_JPN.xml` with Japanese translations for all existing StringIds.

### Pitfall 5: br-tag Encoding in XML Attributes
**What goes wrong:** Writing `<br/>` literally in XML attributes produces invalid XML. Must use `&lt;br/&gt;`.
**Why it happens:** XML attribute values are parsed by the XML parser -- literal `<` is not allowed.
**How to avoid:** Always use `&lt;br/&gt;` in .loc.xml attribute values. The existing files do this correctly -- maintain the pattern.

## Code Examples

### Generating Valid DDS Files with Pillow

```python
# Source: Pillow documentation + existing MediaConverter.convert_dds_to_png()
from PIL import Image
import struct

def create_mock_dds(output_path, width=64, height=64, color=(100, 150, 200, 255)):
    """Create a valid DDS file that Pillow can open."""
    img = Image.new("RGBA", (width, height), color)
    img.save(output_path, format="DDS")
```

### Generating Valid WAV Files with stdlib

```python
# Source: Python wave module documentation
import wave
import struct

def create_mock_wav(output_path, duration_ms=100, sample_rate=22050):
    """Create a minimal valid WAV file."""
    num_samples = int(sample_rate * duration_ms / 1000)
    with wave.open(str(output_path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        # Generate silence (or a simple tone)
        samples = struct.pack(f'<{num_samples}h', *([0] * num_samples))
        wav.writeframes(samples)
```

### PerforcePathService Mock Configuration

```python
# Source: server/tools/ldm/services/perforce_path_service.py:140-161
from pathlib import Path
from server.tools.ldm.services.perforce_path_service import get_perforce_path_service

path_svc = get_perforce_path_service()
mock_dir = Path("tests/fixtures/mock_gamedata")
path_svc.configure_for_mock_gamedata(mock_dir)

# All template keys now resolve to mock subdirectories
assert path_svc.resolve("texture_folder") == mock_dir / "texture" / "image"
assert path_svc.resolve("audio_folder") == mock_dir / "sound" / "windows" / "English(US)"
assert path_svc.resolve_audio_folder("kor") == mock_dir / "sound" / "windows" / "Korean"
```

### Adding JP Language Data

```xml
<?xml version='1.0' encoding='UTF-8'?>
<LanguageData>
  <LocStr StringId="CHAR_ELDERVARON_NAME" StrOrigin="長老バロン" Str="長老バロン"/>
  <LocStr StringId="CHAR_ELDERVARON_DESC" StrOrigin="封印された図書館の守護者である長老バロンは、300年以上もの間、古代の知識を守ってきた。&lt;br/&gt;彼は賢者の結社を率い、聖なる炎の秘密を後世に伝授している。" Str="封印された図書館の守護者である長老バロンは、300年以上もの間、古代の知識を守ってきた。&lt;br/&gt;彼は賢者の結社を率い、聖なる炎の秘密を後世に伝授している。"/>
  <!-- ... more entries matching KOR/ENG StringIds ... -->
</LanguageData>
```

## Recommended Task Structure

### Task 1: Fix DDS and WEM Stubs
- Replace 4-byte DDS stubs with valid Pillow-generated DDS files (64x64, colored per entity type)
- Replace 0-byte WEM stubs with valid WAV files renamed to .wem (or place .wav alongside)
- Update `generate_mega_index_mockdata.py` to generate valid media files instead of stubs

### Task 2: Add Missing Audio Language Folders
- Create `sound/windows/Korean/` with WEM/WAV stubs matching English filenames
- Create `sound/windows/Chinese(PRC)/` with WEM/WAV stubs matching English filenames
- Verify `resolve_audio_folder("kor")` and `resolve_audio_folder("zho-cn")` return valid directories

### Task 3: Add Japanese Language Data
- Create `loc/languagedata_JPN.xml` with Japanese translations for all existing StringIds
- Ensure `<br/>` tags are correctly escaped as `&lt;br/&gt;`
- Add JP entries to any `.loc.xml` files that need multi-language content

### Task 4: Verify End-to-End Path Resolution
- Write/update test that calls `configure_for_mock_gamedata()`, then resolves all 11 template keys and verifies each directory exists and contains expected files
- Fix `test_mock_media_stubs.py` path references (`audio` -> `sound/windows/English(US)`, etc.)
- Verify DDS -> PNG conversion works with new stubs
- Verify audio endpoint can serve from mock data

## Open Questions

1. **Pillow DDS write support**
   - What we know: Pillow can read DDS. The `DdsImagePlugin` exists.
   - What's unclear: Whether `Image.save(format="DDS")` works in all Pillow versions. May need to verify.
   - Recommendation: Test locally. If Pillow DDS write fails, generate proper DDS headers manually (128-byte struct) followed by raw RGBA pixel data.

2. **WAV vs WEM for mock audio**
   - What we know: The audio endpoint already has WAV passthrough (serves `.wav` directly without vgmstream conversion).
   - What's unclear: Whether MegaIndex's `_scan_wem_files()` only scans for `.wem` extension -- if so, WAV files won't be indexed.
   - Recommendation: Use `.wem` extension on valid WAV content. vgmstream can actually handle raw WAV inside .wem containers. Alternatively, add `.wav` scanning to `_scan_wem_files()` for DEV mode.

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/perforce_path_service.py` -- all 11 templates, configure_for_mock_gamedata(), WSL conversion
- `server/main.py:158-181` -- DEV mode auto-initialization flow
- `server/tools/ldm/services/media_converter.py` -- DDS/WEM conversion implementation
- `server/tools/ldm/routes/mapdata.py:95-186` -- thumbnail/audio endpoints with fallbacks
- `server/tools/ldm/services/mega_index.py:327-349` -- DDS/WEM scanning logic
- `tools/generate_mega_index_mockdata.py` -- mock data generator central registry

### Secondary (MEDIUM confidence)
- `tests/unit/test_mock_media_stubs.py` -- existing test expectations (path mismatch noted)
- `tests/fixtures/mock_gamedata/` -- actual file inventory via filesystem inspection

## Metadata

**Confidence breakdown:**
- Architecture/path resolution: HIGH - read all source code directly
- DDS/WEM gap analysis: HIGH - verified file contents with xxd, confirmed Pillow/vgmstream requirements
- Language data format: HIGH - read actual XML files, confirmed br-tag encoding
- Pillow DDS write capability: MEDIUM - Pillow DDS read is confirmed; write support needs local verification

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain, mock data rarely changes)
