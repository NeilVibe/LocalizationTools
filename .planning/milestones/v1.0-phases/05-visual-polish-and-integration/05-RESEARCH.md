# Phase 5: Visual Polish and Integration - Research

**Researched:** 2026-03-14
**Domain:** Svelte 5 UI components, MapDataGenerator data integration, Settings management, Visual polish
**Confidence:** HIGH

## Summary

Phase 5 has two distinct domains: (1) Settings UI for configuring branches/drives/metadata reading, and (2) MapDataGenerator integration into the translation grid's RightPanel Image and Audio tabs. The existing codebase is well-prepared -- the RightPanel already has placeholder tabs for Image, Audio, and AI Context. The MapDataGenerator NewScript has a mature `LinkageResolver` that maps game entities (characters, locations, items) to DDS texture files and WEM audio files via `StrKey`/`StringID` lookups.

The critical insight is that MapDataGenerator operates on `StrKey` values from game staticinfo XML, while LocaNext's translation grid rows have `string_id` fields. The linkage between them is that `string_id` in translation rows maps to the same `StrKey`/`StringID` used in MapDataGenerator's knowledge lookup. The backend needs a new API endpoint that, given a `string_id`, returns associated image paths and audio paths from MapDataGenerator's data. The frontend then renders these in the RightPanel's Image and Audio tabs when a row is selected.

**Primary recommendation:** Build a lightweight MDG context service on the backend that pre-indexes the StrKey-to-image/audio mappings at startup (using MapDataGenerator's `LinkageResolver` pattern), expose via REST API, and wire into the existing RightPanel tabs with lazy-loading thumbnails and audio player controls.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-04 | Settings UI for branches, drives, metadata reading | MapDataGenerator config.py has `KNOWN_BRANCHES`, `Settings` dataclass, drive/branch path templates. Existing `PreferencesModal.svelte` and `ReferenceSettingsModal.svelte` provide patterns for Carbon modal-based settings. |
| UI-05 | Overall visual polish matches cinematic quality of landing page | Existing CSS patterns in VirtualGrid, RightPanel, TMTab established in Phases 2-4. Carbon Design System tokens (--cds-*) used consistently. Polish = spacing, transitions, typography alignment pass. |
| MAP-01 | Image mapping visible directly in translation grid | MapDataGenerator LinkageResolver builds StrKey->UITextureName->DDS path chain. DDSHandler converts DDS to PIL Image. Backend serves pre-indexed lookup; frontend renders in RightPanel Image tab. |
| MAP-02 | Audio mapping visible directly in translation grid | MapDataGenerator AudioIndex maps event_name->WEM path, with StringId chain. AudioHandler converts WEM->WAV via vgmstream-cli. Backend serves audio metadata; frontend renders player in RightPanel Audio tab. |
| MAP-03 | MapDataGenerator data integrated organically | RightPanel tabs already exist with placeholder content. Integration means: auto-loading context when row selected, smooth transitions, loading states, graceful fallbacks for missing assets. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | Current | Frontend framework | Project standard, Runes syntax mandatory |
| Carbon Components Svelte | Current | UI component library | Project standard (Modal, Select, Toggle, Tag, etc.) |
| FastAPI | Current | Backend API | Project standard, async endpoints |
| Pydantic | Current | API schema validation | Project standard for request/response models |
| Pillow (PIL) | Current | Image processing | Already used by MapDataGenerator DDSHandler for DDS->PNG/RGBA conversion |
| lxml | Current | XML parsing | Already used by MapDataGenerator xml_parser for staticinfo reading |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pillow-dds | Current | DDS format support for Pillow | Required on Windows for loading DDS textures |
| carbon-icons-svelte | Current | Icons for tabs and buttons | Image, Music, Settings, etc. icons already imported in RightPanel |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Serving DDS directly | Convert to PNG/WebP on backend | DDS needs pillow-dds; convert to web format on backend for browser compatibility |
| Streaming WEM audio | Convert WEM->WAV->base64 on backend | WEM needs vgmstream-cli; serve converted WAV or stream bytes |
| Custom settings store | Extend existing preferences.js store | Use existing pattern - just add fields to defaultPreferences |

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/routes/
  mapdata.py              # New: MDG context API endpoints

server/tools/ldm/services/
  mapdata_service.py      # New: MDG context service (wraps LinkageResolver logic)

locaNext/src/lib/components/
  SettingsModal.svelte    # New: Branch/drive/metadata settings (or extend existing)

locaNext/src/lib/components/ldm/
  ImageTab.svelte         # New: Image context tab for RightPanel
  AudioTab.svelte         # New: Audio context tab for RightPanel
  RightPanel.svelte       # Modified: Wire ImageTab and AudioTab into existing tabs
```

### Pattern 1: MDG Context Service (Backend)
**What:** A service that pre-indexes MapDataGenerator data at startup and provides fast lookups by StringID
**When to use:** When a user selects a row, the frontend needs image/audio context instantly

The service reuses MapDataGenerator's proven `LinkageResolver` pattern but adapted for LocaNext's server context:

```python
# server/tools/ldm/services/mapdata_service.py
from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path

@dataclass
class ImageContext:
    """Image context for a translation row."""
    texture_name: str
    dds_path: str          # Windows path to DDS file
    thumbnail_url: str     # Relative URL for serving thumbnail
    has_image: bool

@dataclass
class AudioContext:
    """Audio context for a translation row."""
    event_name: str
    wem_path: str          # Windows path to WEM file
    script_kr: str         # Korean script line
    script_eng: str        # English script line
    duration_seconds: Optional[float]

class MapDataService:
    """Pre-indexed MapDataGenerator context for translation rows."""

    def __init__(self):
        self._strkey_to_image: Dict[str, ImageContext] = {}
        self._strkey_to_audio: Dict[str, AudioContext] = {}
        self._loaded = False

    def initialize(self, settings: dict):
        """Build indexes from staticinfo XML (called at startup or settings change)."""
        # Reuse LinkageResolver's knowledge lookup + DDS index pattern
        ...

    def get_image_context(self, string_id: str) -> Optional[ImageContext]:
        """Look up image context for a string_id."""
        return self._strkey_to_image.get(string_id)

    def get_audio_context(self, string_id: str) -> Optional[AudioContext]:
        """Look up audio context for a string_id."""
        return self._strkey_to_audio.get(string_id)
```

### Pattern 2: RightPanel Tab Integration (Frontend)
**What:** Replace placeholder tabs with real components that fetch context when selectedRow changes
**When to use:** When user clicks a row in VirtualGrid

```svelte
<!-- ImageTab.svelte -->
<script>
  let { selectedRow = null } = $props();

  let imageContext = $state(null);
  let loading = $state(false);

  $effect(() => {
    if (selectedRow?.string_id) {
      fetchImageContext(selectedRow.string_id);
    } else {
      imageContext = null;
    }
  });

  async function fetchImageContext(stringId) {
    loading = true;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/mapdata/image/${stringId}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) imageContext = await res.json();
      else imageContext = null;
    } finally {
      loading = false;
    }
  }
</script>
```

### Pattern 3: Settings Modal (Branch/Drive Configuration)
**What:** A Carbon Modal that configures branch (mainline/cd_beta/etc.), drive letter, and metadata reading paths
**When to use:** User needs to point LocaNext at different Perforce workspace branches

The existing `ReferenceSettingsModal.svelte` provides the exact pattern: Carbon Modal with `$bindable(false)` for open/close, form fields, save to preferences store. The MapDataGenerator `config.py` already has `KNOWN_BRANCHES`, `Settings` dataclass, and `generate_default_paths()` function.

### Anti-Patterns to Avoid
- **Copying MapDataGenerator code into LocaNext:** Instead, import/reference the existing patterns but write LocaNext-native code. MapDataGenerator is a Tkinter desktop app; LocaNext is FastAPI+Svelte.
- **Loading all DDS images eagerly:** DDS files are large (768x768+). Serve thumbnails via API endpoint, load on demand when tab is visible.
- **Blocking startup on MDG indexing:** Initialize the MapData service lazily or in a background task. Don't block the server startup.
- **Serving raw DDS to browser:** Browsers can't render DDS. Convert to PNG/WebP on the backend before serving.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DDS image loading | Custom DDS parser | Pillow + pillow-dds (`DDSHandler` pattern from MapDataGenerator) | DDS has 50+ format variants; pillow-dds handles them all |
| WEM audio conversion | Custom audio decoder | vgmstream-cli (already bundled in MapDataGenerator/tools/) | WEM is Wwise proprietary format; vgmstream is the standard converter |
| XML parsing with sanitization | Custom XML parser | MapDataGenerator's `xml_parser.py` (battle-tested sanitize_xml) | Game XML is notoriously malformed; this parser handles all edge cases |
| Settings persistence | Custom config file handler | Extend existing `preferences.js` store (localStorage) + backend settings API | Consistency with existing patterns |
| Image caching | Custom cache | LRU cache pattern from DDSHandler | Proven memory-bounded caching |

**Key insight:** MapDataGenerator has already solved the hard problems (DDS loading, WEM conversion, XML sanitization, knowledge-to-texture linkage). The task is adapting these patterns for a web context (FastAPI serving images via HTTP, Svelte rendering in browser).

## Common Pitfalls

### Pitfall 1: StringID vs StrKey Mismatch
**What goes wrong:** LocaNext rows have `string_id` (e.g., "STR_QUEST_001"). MapDataGenerator uses `StrKey` from KnowledgeInfo. These may not always be identical -- some entries use `KnowledgeKey` as an intermediary.
**Why it happens:** The game data has multiple key systems (StrKey, StringID, KnowledgeKey, EventName).
**How to avoid:** Build a multi-key index in the MDG service: index by StrKey, StringID, and KnowledgeKey. Try all keys when looking up context.
**Warning signs:** Image/audio context returns null for rows that should have associated media.

### Pitfall 2: DDS File Access from WSL
**What goes wrong:** MapDataGenerator paths are Windows paths (F:\perforce\...) but LocaNext server runs in WSL.
**Why it happens:** The Perforce workspace is on a Windows drive; LocaNext backend runs in WSL2.
**How to avoid:** Convert Windows paths to WSL paths: `F:\perforce\...` -> `/mnt/f/perforce/...`. The `config.py` has `_apply_drive_letter()` -- add a WSL path conversion layer.
**Warning signs:** FileNotFoundError when trying to load DDS/WEM files from the backend.

### Pitfall 3: Image Serving Performance
**What goes wrong:** Each row selection triggers a DDS->PNG conversion, causing visible lag.
**Why it happens:** DDS conversion is CPU-bound; doing it on every request is wasteful.
**How to avoid:** Pre-generate PNG thumbnails during initialization and cache them. Serve from a `/static/` endpoint or memory cache. Use ETags/304 for browser caching.
**Warning signs:** Noticeable delay (>500ms) when clicking between rows.

### Pitfall 4: Audio Playback in Browser
**What goes wrong:** WEM files can't play in browser; WAV files are huge; need conversion pipeline.
**Why it happens:** WEM is Wwise proprietary format. Browsers support WAV/MP3/OGG but not WEM.
**How to avoid:** Convert WEM->WAV on the backend (using vgmstream-cli), serve via streaming endpoint. Consider caching converted WAV files. Provide play/pause controls in AudioTab.
**Warning signs:** Audio player shows "unsupported format" or extremely slow loading.

### Pitfall 5: Settings UI Scope Creep
**What goes wrong:** Settings modal becomes a dumping ground for every preference.
**Why it happens:** There are already multiple settings modals (PreferencesModal, ReferenceSettingsModal, GridColumnsModal).
**How to avoid:** Keep the new settings modal focused on branch/drive/metadata paths only. Follow the existing compartmentalized pattern from UI-002.
**Warning signs:** Modal growing beyond 3-4 form fields.

## Code Examples

### Existing RightPanel Tab Structure (from Phase 3)
```svelte
// Source: locaNext/src/lib/components/ldm/RightPanel.svelte
const tabs = [
  { id: 'tm', label: 'TM', icon: DataBase },
  { id: 'image', label: 'Image', icon: Image },
  { id: 'audio', label: 'Audio', icon: Music },
  { id: 'context', label: 'AI Context', icon: MachineLearningModel }
];

// Image and Audio tabs currently show placeholders:
{:else if activeTab === 'image'}
  <div class="placeholder-tab">
    <Image size={32} />
    <span class="placeholder-title">Image Context</span>
    <span class="placeholder-desc">Coming in Phase 5</span>
  </div>
```

### MapDataGenerator DataEntry Structure (source of truth for context data)
```python
# Source: RFC/NewScripts/MapDataGenerator/core/linkage.py
@dataclass
class DataEntry:
    strkey: str
    name_kr: str          # Korean name (from Knowledge lookup)
    desc_kr: str          # Description
    ui_texture_name: str  # UITextureName -> maps to DDS file
    dds_path: Optional[Path]  # Resolved DDS file path
    has_image: bool

    # MAP mode: WorldPosition
    position: Optional[Tuple[float, float, float]] = None

    # CHARACTER mode
    use_macro: str = ""   # Race/Gender
    age: str = ""
    job: str = ""

    # ITEM mode
    string_id: str = ""

    # AUDIO mode
    export_path: str = ""
    xml_order: int = 0
```

### MapDataGenerator Config Settings Pattern
```python
# Source: RFC/NewScripts/MapDataGenerator/config.py
KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"]

_PATH_TEMPLATES = {
    'faction_folder':    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    'loc_folder':        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    'knowledge_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    'texture_folder':    r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    'character_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    'audio_folder':      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    # ... more paths
}

def generate_default_paths(drive: str, branch: str) -> dict:
    """Rebuild all default paths from templates."""
    result = {}
    for key, template in _PATH_TEMPLATES.items():
        path = _apply_drive_letter(template, drive)
        path = _apply_branch(path, branch)
        result[key] = path
    return result
```

### RowResponse Schema (what the frontend gets per row)
```python
# Source: server/tools/ldm/schemas/row.py
class RowResponse(BaseModel):
    id: int
    file_id: int
    row_num: int
    string_id: Optional[str]  # <-- This is the key for MDG lookup
    source: Optional[str]
    target: Optional[str]
    status: str
    updated_at: Optional[datetime] = None
    qa_checked_at: Optional[datetime] = None
    qa_flag_count: int = 0
```

### Existing Carbon Modal Pattern (from ReferenceSettingsModal)
```svelte
// Source: locaNext/src/lib/components/ReferenceSettingsModal.svelte
<script>
  import { Modal, RadioButtonGroup, RadioButton, InlineNotification, Button, Tag } from "carbon-components-svelte";

  let { open = $bindable(false) } = $props();
  let saved = $state(false);

  // Form state
  let referenceFileId = $state(null);
  let referenceMatchMode = $state('stringIdOnly');
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MapDataGenerator as standalone Tkinter app | Integrated context within LocaNext grid | Phase 5 | Users see image/audio context alongside translations without switching tools |
| Scattered settings files (mdg_settings.json, settings.json) | Unified settings modal in LocaNext UI | Phase 5 | Single source of truth for branch/drive config |
| Placeholder RightPanel tabs | Functional Image and Audio tabs | Phase 5 | Full context available during translation |

## Open Questions

1. **Perforce Path Availability**
   - What we know: MapDataGenerator paths assume Windows Perforce workspace (F:\perforce\...)
   - What's unclear: Will the LocaNext backend always have access to these paths from WSL? Are DDS/WEM files always present?
   - Recommendation: Implement graceful degradation -- if paths not configured or files not found, show "Configure paths in Settings" prompt in Image/Audio tabs instead of errors.

2. **Image Serving Strategy**
   - What we know: DDS files are large (768x768 textures). Browser can't render DDS natively.
   - What's unclear: Should we pre-convert all images at startup, or convert on-demand with caching?
   - Recommendation: On-demand conversion with disk cache. Pre-converting thousands of DDS files would be slow; on-demand with cache gives instant response for revisited images.

3. **Audio Playback Architecture**
   - What we know: WEM->WAV conversion requires vgmstream-cli binary. AudioHandler from MapDataGenerator uses winsound (Windows-only).
   - What's unclear: Will vgmstream-cli be available in the LocaNext deployment? Should audio conversion happen on-demand or pre-cached?
   - Recommendation: Check for vgmstream-cli availability. If not present, show "Audio playback requires vgmstream-cli" message. Convert on-demand and cache WAV files. Serve via streaming endpoint for HTML5 `<audio>` element playback.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Playwright (E2E) |
| Config file | `pytest.ini` (backend), `locaNext/playwright.config.ts` (E2E) |
| Quick run command | `pytest tests/unit/ldm/ -x --no-header -q` |
| Full suite command | `pytest tests/ -x --no-header` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-04 | Settings UI saves and loads branch/drive config | E2E | `npx playwright test settings-modal.spec.ts` | No - Wave 0 |
| UI-05 | Visual polish consistent across views | E2E (screenshot) | `npx playwright test visual-polish.spec.ts` | No - Wave 0 |
| MAP-01 | Image context API returns data for known StringID | unit | `pytest tests/unit/ldm/test_mapdata_service.py -x` | No - Wave 0 |
| MAP-02 | Audio context API returns metadata for known StringID | unit | `pytest tests/unit/ldm/test_mapdata_service.py -x` | No - Wave 0 |
| MAP-03 | RightPanel Image/Audio tabs render context on row select | E2E | `npx playwright test mapdata-context.spec.ts` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/ldm/test_mapdata_service.py -x --no-header -q`
- **Per wave merge:** `pytest tests/ -x --no-header && cd locaNext && npx playwright test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_mapdata_service.py` -- covers MAP-01, MAP-02 (mock file paths, test lookup logic)
- [ ] `locaNext/tests/settings-modal.spec.ts` -- covers UI-04 (Playwright E2E for settings modal)
- [ ] `locaNext/tests/mapdata-context.spec.ts` -- covers MAP-01, MAP-02, MAP-03 (E2E for RightPanel tabs)

## Sources

### Primary (HIGH confidence)
- MapDataGenerator source code (`RFC/NewScripts/MapDataGenerator/`) -- core/linkage.py, core/dds_handler.py, core/audio_handler.py, config.py
- LocaNext frontend source (`locaNext/src/lib/components/ldm/`) -- RightPanel.svelte, VirtualGrid.svelte, PreferencesModal.svelte, ReferenceSettingsModal.svelte
- LocaNext backend source (`server/tools/ldm/`) -- router.py, routes/settings.py, schemas/row.py
- LocaNext stores (`locaNext/src/lib/stores/preferences.js`) -- existing settings persistence pattern

### Secondary (MEDIUM confidence)
- MapDataGenerator config patterns (KNOWN_BRANCHES, Settings dataclass, path templates) -- verified in source

### Tertiary (LOW confidence)
- None -- all findings verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use in the project
- Architecture: HIGH -- extends proven existing patterns (RightPanel tabs, Carbon modals, FastAPI routes)
- Pitfalls: HIGH -- identified from reading actual source code and understanding data flow
- MapDataGenerator data model: HIGH -- read full linkage.py, config.py, dds_handler.py, audio_handler.py

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable -- internal project, no external dependency changes expected)
