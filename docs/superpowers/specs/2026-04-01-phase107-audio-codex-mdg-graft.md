# Phase 107: Audio Codex — Full MDG Graft

**Date:** 2026-04-01
**Status:** SPEC APPROVED
**Goal:** Replicate MapDataGenerator's Audio mode in LocaNext's AudioCodexPage with 3-panel layout, matching ALL MDG functionality.

---

## Overview

Replace the current flat-list AudioCodexPage with a full MDG-style 3-panel layout:

| MDG (tkinter) | LocaNext (Svelte) |
|---|---|
| Export Tree on **top** | Export Tree in **left panel** (250px) |
| Result Grid in **center** | Result Grid in **center panel** (flex) |
| Audio Viewer on **right** | Audio Player in **right panel** (350px) |

Same data, same ordering, same features, same playback — adapted to LocaNext's left/center/right layout with Carbon dark theme.

---

## Architecture

### State Ownership (AudioCodexPage.svelte — orchestrator)

All state lives in the page. Child components are props-driven, stateless consumers.

```
selectedEvent: string | null         // Currently selected row
playingEvent: string | null          // Currently playing audio (only 1 at a time)
audioElement: HTMLAudioElement       // Hidden, controlled programmatically
currentTime: number                  // Progress bar current position
duration: number                     // Progress bar total length
activeCategory: string | null        // Export tree filter
searchQuery: string                  // Text search
selectedLanguage: 'eng'|'kor'|'zho-cn'  // Audio folder language
allItems: AudioCardResponse[]        // Bulk-loaded from API
categories: AudioCategoryNode[]      // Tree from API
```

### Component Hierarchy

```
AudioCodexPage.svelte (orchestrator + state owner)
├── Header (title + language selector dropdown)
├── AudioExportTree.svelte (LEFT — category sidebar)
├── AudioResultGrid.svelte (CENTER — EventName | KOR | ENG grid)
└── AudioPlayerPanel.svelte (RIGHT — player + scripts + metadata)
```

### Data Flow

```
User clicks category in tree → activeCategory updates → filteredItems derived → grid re-renders
User clicks row in grid → selectedEvent updates → detail fetched → right panel updates
User clicks Play in grid → playingEvent set → audioElement.src set → playback starts
User presses Arrow Up/Down → selectedEvent moves → right panel updates
User clicks Prev/Next in player → same as arrow keys
```

---

## Components

### 1. AudioExportTree.svelte (LEFT PANEL)

**Props:** `categories`, `activeCategory`, `totalEvents`, `onselect`

**MDG-exact behavior:**
- "All" root node showing total count
- Hierarchical tree from D20 export_path (Dialog → QuestDialog → SubFolder)
- Collapsible nodes with ChevronRight/ChevronDown icons
- Count badges per node (rolled up: own + children)
- Auto-expand first 2 levels on mount
- Active category highlighted with left border accent
- Click node = filter grid to that category prefix

**Extracted from current AudioCodexPage sidebar** — same styling, improved structure.

### 2. AudioResultGrid.svelte (CENTER PANEL)

**Props:** `items`, `selectedEvent`, `playingEvent`, `onselect`, `onplay`, `onstop`

**Columns:**
| # | Column | Width | Content |
|---|--------|-------|---------|
| 1 | Play/Stop | 40px | Circle button, blue=play, red=stop |
| 2 | EventName | 200px | Event identifier, mono font |
| 3 | KOR Script | flex | Korean dialogue text (truncated) |
| 4 | ENG Script | flex | English translation (truncated, lighter color) |

**MDG-exact behavior:**
- Sorted by xml_order (D21), fallback alphabetical
- has_wem dot indicator (green = audio exists, grey = no file)
- Click row = select (updates right panel)
- Click Play button = play that audio (only 1 at a time)
- **Arrow Up/Down keyboard navigation** — moves selection, scrolls into view
- Selected row highlighted with accent background
- Playing row has pulsing indicator
- Scrollable with sticky header

### 3. AudioPlayerPanel.svelte (RIGHT PANEL)

**Props:** `audio` (detail object), `playing`, `currentTime`, `duration`, `onplay`, `onstop`, `onprev`, `onnext`

**Layout (top to bottom):**
1. **Event name header** — Music icon + event name + duration (mm:ss)
2. **Progress bar** — horizontal bar showing currentTime/duration, click to seek
3. **Controls** — Play/Stop + Prev/Next buttons (centered)
4. **KOR Script section** — label + full text, pre-line whitespace
5. **ENG Script section** — label + full text, lighter color
6. **Metadata section** — StringId, Category, WEM Path, XML Order

**MDG-exact behavior:**
- Prev/Next buttons call parent callback (same as Arrow Up/Down in grid)
- Progress bar updates in real-time via requestAnimationFrame
- Duration displayed as formatted mm:ss
- Play/Stop buttons mirror grid state
- No auto-play — click only

**Replaces AudioCodexDetail.svelte** (which gets deleted).

### 4. AudioCodexPage.svelte (REWRITE — orchestrator)

**Layout:**
```
+----------------------------------------------------------+
| Audio Codex                    [Language: eng ▼] [Search] |
+----------+---------------------------+-------------------+
| Export    | Play | EventName | KOR | ENG |  Event: xxx   |
| Tree     | ▶    | npc_greet | 안녕 | Hi  |  ━━━━━●━━━━  |
|           | ■    | npc_quest | 퀘스 | Qu  |  [◀][▶/■][▶] |
| Dialog    | ▶    | npc_taunt | 도발 | Ta  |  KOR: 안녕... |
|  ├ Quest  |      |           |      |     |  ENG: Hello.. |
|  └ Battle |      |           |      |     |  StringId:... |
| Ambient   |      |           |      |     |  Category:... |
+----------+---------------------------+-------------------+
```

**Responsibilities:**
- Fetch categories + all items on mount
- Manage ALL state (selected, playing, category, search, language)
- Hidden `<audio>` element for playback control
- Wire callbacks between child components
- Language selector in header (eng/kor/zho-cn dropdown)
- Search bar in header
- requestAnimationFrame loop for progress bar updates

---

## Backend Changes

### 1. Language parameter on stream endpoint

**Current:** `GET /codex/audio/stream/{event_name}` — uses D10 (English only)
**New:** `GET /codex/audio/stream/{event_name}?language=eng` — uses D10a/b/c based on language

Lookup: `mega.get_audio_path_by_event_for_lang(event_name, language)` (already exists in mega_index_api.py)

### 2. Language parameter on list endpoint

**Current:** `GET /codex/audio` — `has_wem` only checks English
**New:** `GET /codex/audio?language=eng` — `has_wem` checks language-specific folder

### 3. Language parameter on detail endpoint

**Current:** `GET /codex/audio/{event_name}` — English only
**New:** `GET /codex/audio/{event_name}?language=eng` — language-aware WEM path + stream URL

---

## Bug Fixes (included)

1. **Vite proxy** — add `/api/ldm/codex/audio/stream` to vite.config.js proxy
2. **Remove `crossorigin="anonymous"`** — causes playback failures (Phase 106 fix)
3. **Fix `preload` attribute** — use `preload="auto"` for smooth playback
4. **Cache-bust URLs** — `?v=${Date.now()}` on all stream URLs (media-cache-bust rule)

---

## Deleted Files

- `AudioCodexDetail.svelte` — replaced by AudioPlayerPanel

---

## Plan Breakdown

### Wave 1 (parallel — 3 independent components)
- **Plan 1:** Bug fixes + backend language support (vite proxy, codex_audio.py routes, crossorigin)
- **Plan 2:** AudioExportTree.svelte (left panel, extracted + enhanced)
- **Plan 3:** AudioPlayerPanel.svelte (right panel, new component)

### Wave 2 (sequential — tight coupling)
- **Plan 4:** AudioResultGrid.svelte + AudioCodexPage.svelte rewrite + delete AudioCodexDetail

---

## Success Criteria

1. Export tree shows exact MDG hierarchy with counts
2. Result grid shows EventName | KOR | ENG sorted by xml_order
3. Click Play = audio plays, click Stop = stops
4. Arrow Up/Down navigates between rows
5. Right panel shows full scripts + metadata + progress bar
6. Language switcher changes audio folder (eng/kor/zho-cn)
7. Search filters across all fields
8. Works in DEV (localhost:5173) and Windows app (Electron)
9. No crossorigin issues, proper Vite proxy
