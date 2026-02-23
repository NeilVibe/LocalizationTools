# MapDataGenerator User Guide

**Version 2.0** | February 2026

---

## Table of Contents

1. [What is MapDataGenerator?](#1-what-is-mapdatagenerator)
2. [Installation](#2-installation)
3. [First-Run Configuration](#3-first-run-configuration)
4. [MAP Mode](#4-map-mode)
5. [CHARACTER Mode](#5-character-mode)
6. [ITEM Mode](#6-item-mode)
7. [AUDIO Mode](#7-audio-mode)
8. [Search](#8-search)
9. [UI Features](#9-ui-features)
10. [Settings Reference](#10-settings-reference)
11. [Required Folder Structure](#11-required-folder-structure)
12. [Troubleshooting](#12-troubleshooting)
13. [File Format Reference](#13-file-format-reference)

---

## 1. What is MapDataGenerator?

MapDataGenerator is a desktop tool for browsing and visualizing game data used by
localization teams. It reads XML game data files directly from your Perforce workspace
and presents them in a searchable, visual interface.

### What it does

- **Search** game entries by name, description, or internal key across 14 languages
- **View DDS textures** linked to map locations, characters, and items
- **Visualize maps** showing node positions on a 2D scatter plot
- **Play WEM audio** files with Korean and English script text side by side
- **Browse** thousands of entries with pagination, sorting, and filtering

### Who it is for

- Localization translators who need to look up game content in context
- QA testers verifying translated text against visual and audio assets
- Content reviewers who need to browse game data without launching the game engine

### The four data modes

| Mode | What it shows | Visual output |
|------|---------------|---------------|
| **MAP** | FactionNode map locations | DDS image + interactive 2D map |
| **CHARACTER** | Character entries with metadata | DDS image (portrait/model) |
| **ITEM** | Knowledge/item entries | DDS image (icon/artwork) |
| **AUDIO** | WEM audio files with scripts | KOR + ENG text + audio playback |

---

## 2. Installation

### 2.1 From Setup Installer (Recommended)

1. Download `MapDataGenerator_Setup_X.X.X.exe` from the release page.
2. Run the installer. It does not require administrator privileges.
3. Choose an install location (default: Desktop\MapDataGenerator).
4. Optionally create a desktop shortcut.
5. Click "Install" and wait for completion.
6. The application launches automatically after installation.

The installer creates two working directories inside the install folder:

```
MapDataGenerator/
  MapDataGenerator.exe   <-- Main application
  tools/
    vgmstream-cli.exe    <-- Audio decoder (bundled)
  logs/                  <-- Created on first run
  cache/                 <-- Created on first run
  settings.json          <-- Created on first run
```

### 2.2 From Portable ZIP

1. Download `MapDataGenerator_Portable.zip` from the release page.
2. Extract the entire ZIP to any folder (e.g., Desktop, USB drive).
3. Run `MapDataGenerator.exe` from the extracted folder.
4. No installation or uninstallation needed. Delete the folder to remove.

### 2.3 From Source (Python 3.10+)

For developers or users who want to run from source code:

```
pip install -r requirements.txt
pip install pillow-dds     (Windows only, for DDS image support)
python main.py
```

**Dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| lxml | 4.9+ | XML parsing |
| Pillow | 10.0+ | Image handling |
| pillow-dds | 1.0+ | DDS texture format support (Windows) |
| matplotlib | 3.7+ | Map visualization |
| openpyxl | 3.1+ | VoiceRecordingSheet Excel reading |

---

## 3. First-Run Configuration

When you launch MapDataGenerator for the first time, it needs to know where your
Perforce workspace lives. The application reads game data directly from your local
Perforce files.

### 3.1 Perforce Drive Letter

Most developers have Perforce synced to `F:\perforce\...`. If your workspace is on a
different drive, you need to change the drive letter.

1. Open **File > Settings** from the menu bar.
2. In the **Perforce Configuration** section, select your drive letter from the
   dropdown (A through Z).
3. The **Preview** line at the bottom updates in real time to show the resolved path.
4. Click **Save**.

Example: If your Perforce root is at `D:\perforce\`, select drive letter `D`.

### 3.2 Branch Selection

The application defaults to the `mainline` branch. If you are working on a different
branch, change it here.

1. Open **File > Settings**.
2. In the **Branch** dropdown, select or type your branch name.
3. Known branches appear in the dropdown: `mainline`, `cd_beta`, `cd_alpha`,
   `cd_lambda`.
4. You can type a custom branch name if yours is not listed.
5. Click **Save**. The application reloads data automatically.

The branch name is substituted into all folder paths. For example:

```
mainline:   F:\perforce\cd\mainline\resource\GameData\...
cd_beta:    F:\perforce\cd\cd_beta\resource\GameData\...
```

### 3.3 Settings File (settings.json)

All settings are stored in `settings.json` next to the executable. This file is
created automatically on first run with sensible defaults.

If you need to pre-configure settings before first launch (for example, for team
deployment), create this file manually:

```json
{
  "drive_letter": "F",
  "branch": "mainline"
}
```

Place it in the same folder as `MapDataGenerator.exe`. On launch, the application
reads these values and calculates all folder paths automatically.

**Migration note:** If you have an older `mdg_settings.json` file from a previous
version, the application automatically migrates it to `settings.json` on first launch.

---

## 4. MAP Mode

MAP mode displays FactionNode entries from the game's region/faction data. Each entry
represents a location on the game world map.

### 4.1 What You See

When you switch to MAP mode, the application loads:

- **FactionNode XMLs** from the factioninfo folder (~3,400 entries)
- **KnowledgeInfo XMLs** for names, descriptions, and image linkage
- **DDS textures** from the common texture folder (~9,300 files indexed)
- **Language tables** for translations (English + Korean by default)

### 4.2 Result Grid Columns

| Column | Content | Example |
|--------|---------|---------|
| Name (KR) | Korean name from Knowledge lookup | "칼페온 수도" |
| Name (Translated) | Translation in selected language | "Calpheon Capital" |
| Description | Location description | "발레노스 서쪽에..." |
| Position | World coordinates (X, Y, Z) | "(1234.5, 100.0, -567.8)" |
| StrKey | Internal unique identifier | "FN_Town_Calpheon" |

### 4.3 Image Display

Selecting a row shows the linked DDS texture in the right panel:

```
Linkage chain:
  FactionNode.StrKey
    -> FactionNode.KnowledgeKey
      -> KnowledgeInfo.UITextureName
        -> .dds file in texture folder
          -> Displayed as image
```

Click the image to open it in a full-size popup window. Press Escape or click "Close"
to dismiss the popup.

### 4.4 Map Visualization

The "Show Map" checkbox in the toolbar opens a separate map window showing all nodes
as dots on a 2D scatter plot.

```
+------------------------------------------+
| Map View                            [_][X]|
|                                           |
|        *              *                   |
|   *         *    *                        |
|      *   *         *     *               |
|         *     [*]           *            |
|    *        *       *                     |
|       *  *     *         *               |
|                                           |
| [Pan] [Zoom] [Home] [Save]               |
+------------------------------------------+

  * = Node (green = has image, red = no image)
  [*] = Selected node (yellow highlight)
```

**Map interactions:**

- **Hover** over a dot to see the node name, position, and image status
- **Click** a dot to select it (updates the result grid and image viewer)
- **Pan** by clicking the pan tool in the toolbar, then dragging
- **Zoom** by clicking the zoom tool, then dragging a rectangle
- **Home** button resets the view to show all nodes
- **Save** button exports the map as a PNG image

The map window positions itself next to the main window and can be moved independently.

### 4.5 Stats Display

The toolbar shows real-time statistics:

```
Total: 3410 | With Image: 1634 | DDS Files: 9300
```

- **Total** = all loaded FactionNode entries
- **With Image** = entries that have a valid DDS texture file
- **DDS Files** = total number of indexed texture files

---

## 5. CHARACTER Mode

CHARACTER mode displays character entries from CharacterInfo XML files.

### 5.1 What You See

Each entry represents a game character with metadata about their race, gender, age,
and job.

### 5.2 Result Grid Columns

| Column | Content | Example |
|--------|---------|---------|
| Name (KR) | Korean character name | "클리프" |
| Name (Translated) | Translation in selected language | "Cliff" |
| Race/Gender | Formatted from UseMacro attribute | "Human Male" |
| Age | Character age category | "Adult" |
| Job | Character occupation | "Scholar" |

The Race/Gender column is automatically formatted from the internal UseMacro string:

```
Raw:       "Macro_NPC_Human_Male"
Displayed: "Human Male"

Raw:       "Macro_NPC_Unique_Shai_Female"
Displayed: "Shai Female"
```

### 5.3 Image Display

Character images follow the same Knowledge linkage chain as MAP mode. The right panel
shows the character portrait or model texture.

### 5.4 Detail Panel

The collapsible detail panel below the result grid shows full character information:

```
+------------------------------------------+
| Details                        [Collapse] |
|                                           |
| Name:    클리프 / Cliff                    |
| Description:                              |
|   Race/Gender: Human Male                 |
|   Age: Adult                              |
|   Job: Scholar                            |
| Group:  characterinfo_npc_001             |
| StrKey: CI_NPC_Cliff_001                  |
+------------------------------------------+
```

---

## 6. ITEM Mode

ITEM mode displays Knowledge entries treated as items from KnowledgeInfo XML files.

### 6.1 What You See

Each entry represents a game item, region knowledge entry, or other Knowledge-type
content. This mode uses the KnowledgeInfo data directly (the same data that MAP and
CHARACTER modes use for image linkage).

### 6.2 Result Grid Columns

| Column | Content | Example |
|--------|---------|---------|
| Name (KR) | Korean item name | "연금술사의 돌" |
| Name (Translated) | Translation in selected language | "Alchemist's Stone" |
| StrKey | Knowledge entry key | "KI_Item_AlchemistStone" |
| StringID | Language table identifier | "82001" |

### 6.3 Image Display

Items display their UITextureName image in the right panel. This is typically an
item icon or artwork texture.

---

## 7. AUDIO Mode

AUDIO mode lets you browse and play WEM audio files while viewing their Korean and
English script text.

### 7.1 Overview

Audio data comes from three sources combined:

```
WEM audio files (e.g., 12345678.wem)
       |
Export XMLs: map WEM filename -> SoundEventName -> StrOrigin
       |
Language XMLs: StrOrigin -> Korean script + English script
       |
vgmstream-cli: WEM -> WAV conversion for playback
       |
winsound: Audio playback (Windows)
```

### 7.2 Export Category Tree (Left Panel)

In AUDIO mode, a folder hierarchy tree appears above the search panel on the left
side. This tree mirrors the export folder structure and lets you browse audio entries
by category.

```
+--------------------------------------+
| Export Categories                     |
| +----------------------------------+ |
| | v All Audio (12,500)             | |
| |   v Dialog (8,200)              | |
| |     v QuestDialog (3,100)       | |
| |       > MainQuest (1,200)       | |
| |       > SubQuest (900)          | |
| |       > DailyQuest (500)        | |
| |       > ...                     | |
| |     v NPCDialog (2,800)        | |
| |       > ...                     | |
| |   v Ambient (2,100)            | |
| |     > ...                       | |
| |   v Combat (2,200)             | |
| |     > ...                       | |
| +----------------------------------+ |
+--------------------------------------+
```

**How to use the tree:**

- Click a category to filter the result grid to show only entries from that folder
- The number in parentheses shows how many audio entries are in that category
  (including subcategories)
- The first two levels expand automatically on load
- Right-click the tree for "Expand All" / "Collapse All" options
- Click "All Audio" at the top to show everything

**Important:** When you type a search query, the search takes priority over the
category filter. Clear the search box to go back to category browsing.

### 7.3 Audio Playback (WEM via vgmstream-cli)

The right panel in AUDIO mode shows the Audio Player:

```
+--------------------------------------------------+
| Audio Player                                      |
+--------------------------------------------------+
| Event Name                                        |
| +----------------------------------------------+ |
| | narrator_quest_calpheon_001         3.2s      | |
| +----------------------------------------------+ |
+--------------------------------------------------+
| Script Line (KOR)                                 |
| +----------------------------------------------+ |
| | 칼페온으로 향하는 길은 멀고 험하다.               | |
| | 하지만 포기하지 마십시오.                         | |
| +----------------------------------------------+ |
+--------------------------------------------------+
| Script Line (ENG)                                 |
| +----------------------------------------------+ |
| | The road to Calpheon is long and treacherous. | |
| | But do not give up.                           | |
| +----------------------------------------------+ |
+--------------------------------------------------+
| [< Prev] [> Play] [# Stop] [Next >]  | Auto-play |
| [===============>       ] 1.8s / 3.2s  Cleanup    |
+--------------------------------------------------+
| File: 12345678.wem                                |
+--------------------------------------------------+
```

**Playback controls:**

| Button | Action |
|--------|--------|
| **Play** | Convert WEM to WAV and start playback |
| **Stop** | Stop current playback |
| **Prev** | Select the previous entry in the grid |
| **Next** | Select the next entry in the grid |
| **Auto-play** | When checked, audio plays automatically when you select a new row |
| **Cleanup cache** | Delete temporary WAV files from the system temp folder |

The progress bar shows elapsed time versus total duration. Duration is fetched
asynchronously and appears after a brief "..." loading indicator.

**Double-click** a row in the result grid to immediately play that audio file.

### 7.4 VRS Ordering (VoiceRecordingSheet Chronological Ordering)

When VoiceRecordingSheet Excel files are available in the configured VRS folder,
audio entries within each category are sorted in their recording order rather than
alphabetically. This helps translators and voice directors review audio in the
intended sequence.

The VRS folder is configured automatically based on your drive letter and branch:

```
F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__\
```

### 7.5 Keyboard Shortcuts

These shortcuts work when the search box is NOT focused:

| Key | Action |
|-----|--------|
| **Space** | Toggle play/stop for current audio |
| **Left Arrow** | Select previous entry in the grid |
| **Right Arrow** | Select next entry in the grid |

If you are typing in the search box, these keys work normally (Space types a space,
arrows move the cursor).

### 7.6 Cleanup (Cached WAV Temp Files)

When you play a WEM file, the application converts it to a temporary WAV file stored
in your system temp folder (`%TEMP%\mapdatagenerator_audio\`). These files are cached
so replaying the same audio is instant.

Over time, these cached files can accumulate. Use the **Cleanup cache** button to
delete all cached WAV files. The status bar briefly shows how many files were removed.

The application also automatically cleans up temp files when you close it.

### 7.7 Result Grid Columns (AUDIO Mode)

| Column | Content | Example |
|--------|---------|---------|
| Event Name | SoundEventName identifier | "narrator_quest_001" |
| Script (KOR) | Korean voice script text | "안녕하세요..." |
| Script (ENG) | English voice script text | "Hello..." |

### 7.8 Audio Availability

Audio playback requires two things:

1. **vgmstream-cli.exe** must be present in the `tools/` folder (bundled with
   installer; if missing, a red warning appears in the Audio Player header)
2. **Windows** operating system (uses `winsound` for playback)

If either requirement is not met, you can still browse audio entries and read scripts,
but the Play button will be disabled.

---

## 8. Search

### 8.1 Search Modes

The search bar offers three matching strategies:

| Mode | How it matches | Best for |
|------|----------------|----------|
| **Contains** | Query appears anywhere in any field | General browsing: "castle", "orc" |
| **Exact** | Query matches a field value exactly | Finding by exact StrKey: "FN_Town_001" |
| **Fuzzy** | Finds approximate matches (ratio >= 0.6) | Misspelled names: "Calphoen" finds "Calpheon" |

**What gets searched:**

- Korean name
- Translated name (in the selected language)
- Description (first 200 characters)
- Translated description
- Group/category name
- StrKey (internal identifier)

**Search priority:** Results with images appear first, followed by results without
images. Within each group, results are sorted by match score and then by name length.

**Direct StrKey lookup:** If your query exactly matches a StrKey, only that single
result is returned instantly (no scanning required).

### 8.2 Language Selection

The language dropdown (to the right of the search options) controls which language
is used for the "Translated" column.

**Available languages (14 total):**

| Code | Language |
|------|----------|
| eng | English |
| fre | French |
| ger | German |
| spa-es | Spanish (Spain) |
| spa-mx | Spanish (Mexico) |
| por-br | Portuguese (Brazil) |
| ita | Italian |
| rus | Russian |
| tur | Turkish |
| pol | Polish |
| zho-cn | Chinese (Simplified) |
| zho-tw | Chinese (Traditional) |
| jpn | Japanese |
| kor | Korean (source language, always loaded) |

**Lazy loading:** English and Korean are loaded at startup. All other languages are
loaded on-demand the first time you select them. You will see a brief "Loading
language..." message in the status bar. Once loaded, switching back to that language
is instant.

Your language selection is saved to settings and restored on next launch.

### 8.3 Pagination

Results are loaded in pages (default: 100 results per page) to keep the interface
responsive even with thousands of matches.

- The result count header shows `Results: 100 / 3410` when there are more pages.
- Click the **Load More** button below the result grid to load the next page.
- Results accumulate -- you can keep loading more without losing previous results.
- The page size is configurable in **File > Settings > Results per page** (10-500).

### 8.4 Search Tips

| Goal | Query | Mode |
|------|-------|------|
| Find all entries mentioning a town | "calpheon" | Contains |
| Find a specific internal key | "FN_Town_Calpheon_001" | Exact |
| Find a misspelled name | "Haydl" | Fuzzy (finds "Heidel") |
| Browse all entries | (leave search empty) | - |
| Filter audio by category | (use Export Category Tree) | - |

---

## 9. UI Features

### 9.1 Application Layout

```
+---------------------------------------------------------------+
| File                                                          |
+---------------------------------------------------------------+
| Select Mode: (o) MAP  ( ) CHARACTER  ( ) ITEM  ( ) AUDIO     |
|              [x] Show Map                    Total: 3410 ...  |
+---------------------------------------------------------------+
|                                |                              |
| [Export Category Tree]         |   IMAGE VIEWER               |
| (AUDIO mode only)             |   or                         |
|                                |   AUDIO PLAYER               |
| Search: [_______________] [Go] |   (mode-dependent)           |
| Match: (o)Contains ()Exact     |                              |
|        ()Fuzzy                 |   +---------------------+    |
| Language: [English (eng) v]    |   |                     |    |
|                                |   |   DDS Texture       |    |
| Results: 100 / 3410           |   |   or                 |    |
| Show: [x]Name [x]Trans [x]Pos |   |   Audio Player       |    |
| +----------------------------+ |   |   with scripts       |    |
| | Name  | Trans | Pos | Key  | |   |                     |    |
| |-------+-------+-----+------| |   +---------------------+    |
| | ...   | ...   | ... | ...  | |   Size: 512x512              |
| | ...   | ...   | ... | ...  | |   Click to enlarge           |
| +----------------------------+ |                              |
| +--Details------------------+  |                              |
| | Name: ...                 |  |                              |
| | Description: ...         |  |                              |
| | Position: ...            |  |                              |
| | StrKey: ...              |  |                              |
| +---------------------------+  |                              |
| [Load More]                    |                              |
+--------------------------------+------------------------------+
| [==========>       ] Ready                                    |
+---------------------------------------------------------------+
```

The main window is divided into:

- **Left panel (35%):** Export tree (AUDIO only), search panel, result grid, detail panel
- **Right panel (65%):** Image viewer or Audio player depending on mode
- **Toolbar (top):** Mode selector, map toggle, statistics
- **Status bar (bottom):** Progress bar + status messages

The panel divider is resizable -- drag the border between left and right to adjust.

### 9.2 Cell Copy (Ctrl+C)

Click any cell in the result grid to select it. Then press **Ctrl+C** to copy the
**full, untruncated** text to your clipboard.

This is important because long text values are truncated in the grid display (at 80
characters with "..." appended). Ctrl+C always copies the complete original value.

The header area shows a preview of the selected cell:

```
Results: 100     [Ctrl+C to copy: "칼페온 수도의 중심부에 위치한..."]
```

After copying:

```
Results: 100     [Copied: "칼페온 수도의 중심부에 위치한 거대한 성곽 도시..."]
```

### 9.3 Column Toggles

The "Show:" checkboxes in the result header let you hide or show individual columns.
These checkboxes change based on the current mode:

- **MAP mode:** Name (KR), Name (Translated), Description, Position, StrKey
- **CHARACTER mode:** Name (KR), Name (Translated), Race/Gender, Age, Job
- **ITEM mode:** Name (KR), Name (Translated), StrKey, StringID
- **AUDIO mode:** Event Name, Script (KOR), Script (ENG)

By default, the Description column is hidden in non-AUDIO modes to save space. Check
the box to show it.

### 9.4 Column Sorting

Click any column header to sort the results by that column. Click the same header
again to reverse the sort direction. Sorting is alphabetical (case-insensitive).

### 9.5 Tooltips

Hover your mouse over a truncated cell (one that ends with "...") for 500
milliseconds to see the full text in a yellow tooltip popup. The tooltip wraps long
text at 400 pixels width.

### 9.6 Detail Panel

The collapsible detail panel below the result grid shows the full information for
the selected entry without truncation. Click "Collapse" to hide it and give more
space to the result grid.

The detail panel adapts to the current mode:

| Mode | Shows |
|------|-------|
| MAP | Name (KR + translated), Description, Position (X,Y,Z), StrKey |
| CHARACTER | Name, Race/Gender + Age + Job, Group, StrKey |
| ITEM | Name (KR + translated), Description, Group, StrKey |
| AUDIO | Event Name, KOR Script, ENG Script, StrKey |

### 9.7 Window State Persistence

The application remembers your window size and position between sessions. The
geometry string (e.g., "1600x1000+100+50") is saved to `settings.json` when you
close the application.

The default window size is 1600x1000 with a minimum of 900x600.

### 9.8 Status Bar

The status bar at the bottom shows:

| State | Message |
|-------|---------|
| Starting up | "Auto-loading data..." |
| Loading textures | "Scanning texture folder for DDS files..." |
| Loading data | "Loading MAP data (FactionNodes + Knowledge)..." |
| Loading language | "Loading English..." |
| Ready | "Loaded 3410 verified entries. Ready to search." |
| Search results | "Found 42 results" |
| No results | "No results found" |
| Error | "Texture folder not found - check File > Settings" |
| Language loading | "Loading language..." |

The progress bar animates during data loading and stops when loading is complete.

---

## 10. Settings Reference

Open **File > Settings** to access all configurable options.

### Perforce Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Drive Letter | F | The drive where your Perforce workspace is synced |
| Branch | mainline | Branch name (substituted into all folder paths) |

### UI Language

| Setting | Default | Description |
|---------|---------|-------------|
| UI Language | English | Interface language: English or Korean |

All menu labels, button text, column headers, and status messages change to the
selected language. Restart is not required.

### Search Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Results per page | 100 | 10-500 | Number of results loaded per page |
| Fuzzy threshold | 0.6 | 0.1-1.0 | Minimum match ratio for fuzzy search (higher = stricter) |

### Default Mode

| Setting | Default | Description |
|---------|---------|-------------|
| Default Mode | MAP | Which mode to activate on startup |

### Stored Automatically

These are saved automatically and do not appear in the Settings dialog:

| Setting | Description |
|---------|-------------|
| window_geometry | Window size and position (e.g., "1600x1000+100+50") |
| selected_language | Last-used translation language (e.g., "eng") |
| font_family | UI font (default: "Malgun Gothic") |
| font_size | UI font size (default: 10) |
| All folder paths | Calculated from drive letter + branch |

### Settings File Location

The settings file is always located in the same directory as the executable:

```
Installed:  C:\...\MapDataGenerator\settings.json
Portable:   [extraction folder]\settings.json
From source: [project folder]\settings.json
```

### Example settings.json

```json
{
  "drive_letter": "F",
  "branch": "mainline",
  "ui_language": "English",
  "selected_language": "eng",
  "search_limit": 100,
  "fuzzy_threshold": 0.6,
  "current_mode": "map",
  "window_geometry": "1600x1000",
  "font_family": "Malgun Gothic",
  "font_size": 10,
  "faction_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\factioninfo",
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "knowledge_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\knowledgeinfo",
  "waypoint_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\factioninfo\\NodeWaypointInfo",
  "texture_folder": "F:\\perforce\\common\\mainline\\commonresource\\ui\\texture\\image",
  "character_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\characterinfo",
  "audio_folder": "F:\\perforce\\cd\\mainline\\resource\\sound\\windows\\English(US)",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__"
}
```

---

## 11. Required Folder Structure

MapDataGenerator reads data from your Perforce workspace. Below is the complete folder
structure it expects. Replace `F:` with your drive letter and `mainline` with your
branch name.

### Folder Map

```
F:\perforce\
  |
  +-- cd\
  |   +-- mainline\
  |       +-- resource\
  |           +-- GameData\
  |           |   +-- StaticInfo\
  |           |   |   +-- factioninfo\           <-- MAP mode: FactionNode XMLs
  |           |   |   |   +-- NodeWaypointInfo\  <-- MAP mode: Waypoint XMLs
  |           |   |   +-- knowledgeinfo\         <-- ITEM mode + image linkage
  |           |   |   +-- characterinfo\         <-- CHARACTER mode
  |           |   +-- stringtable\
  |           |       +-- loc\                   <-- Language data XMLs
  |           |       |   +-- LanguageData_eng.xml
  |           |       |   +-- LanguageData_kor.xml
  |           |       |   +-- LanguageData_fre.xml
  |           |       |   +-- ... (14 language files)
  |           |       +-- export__\              <-- AUDIO mode: event mappings
  |           +-- sound\
  |           |   +-- windows\
  |           |       +-- English(US)\           <-- AUDIO mode: WEM files (EN)
  |           |       +-- Korean\                <-- AUDIO mode: WEM files (KR)
  |           |       +-- Chinese(PRC)\          <-- AUDIO mode: WEM files (ZH)
  |           +-- editordata\
  |               +-- VoiceRecordingSheet__\     <-- AUDIO mode: VRS ordering
  |
  +-- common\
      +-- mainline\
          +-- commonresource\
              +-- ui\
                  +-- texture\
                      +-- image\                 <-- DDS texture files (~9,300)
                          +-- *.dds
                          +-- subfolder\*.dds
```

### Which folders are needed per mode

| Folder | MAP | CHARACTER | ITEM | AUDIO |
|--------|-----|-----------|------|-------|
| factioninfo | Required | - | - | - |
| NodeWaypointInfo | Optional | - | - | - |
| knowledgeinfo | Required | Required | Required | - |
| characterinfo | - | Required | - | - |
| loc (language data) | Required | Required | Required | Required |
| texture/image (DDS) | Required | Required | Required | - |
| export__ | - | - | - | Required |
| sound/windows/* | - | - | - | Required |
| VoiceRecordingSheet__ | - | - | - | Optional |

### What happens if a folder is missing

- The status bar shows a specific error: "Texture folder not found - check File > Settings"
- The application still launches but the mode with missing data will not load
- Other modes that have their data available still work normally

---

## 12. Troubleshooting

### 12.1 Application does not start

**Symptom:** Double-clicking the EXE does nothing, or a brief console flash appears.

**Solutions:**
- Check the `logs/` folder for error details. Each launch creates a timestamped log
  file (e.g., `mapdatagenerator_20260223_143052.log`).
- Make sure you are on a 64-bit Windows system (the application requires x64).
- If running from source, verify Python 3.10+ is installed: `python --version`

### 12.2 "Texture folder not found" on startup

**Symptom:** Status bar shows "Texture folder not found - check File > Settings."

**Solution:** Open File > Settings and verify:
1. The drive letter matches your Perforce workspace drive.
2. The branch name matches your synced branch.
3. The Preview path looks correct.
4. The folders actually exist on disk (have you synced the latest Perforce files?).

### 12.3 No images displayed (all entries show placeholder)

**Symptom:** Results load but the right panel always shows "No Image Selected."

**Possible causes:**
- DDS files are not synced in Perforce. Check that
  `F:\perforce\common\mainline\commonresource\ui\texture\image\` contains `.dds` files.
- The `pillow-dds` library is not installed (source installs only). Run:
  `pip install pillow-dds`
- Some entries legitimately have no image (entries with names like `createicon` or
  `AbyssGate_*` are expected to be missing).

### 12.4 Korean text displays as empty boxes or question marks

**Symptom:** Korean characters show as rectangles, squares, or "?" symbols.

**Solution:** The application requires a Korean-capable font. It looks for these fonts
in order: Malgun Gothic, NanumGothic, Noto Sans CJK KR, AppleGothic. On Windows,
Malgun Gothic is installed by default. If none are found, install a Korean font.

### 12.5 Audio does not play

**Symptom:** Play button is grayed out, or clicking Play does nothing.

**Possible causes:**

1. **vgmstream-cli.exe is missing:** Check that `tools\vgmstream-cli.exe` exists in the
   application folder. The installer bundles it; if using portable or source, you need
   to place it there manually.
2. **Not on Windows:** Audio playback uses `winsound` which is Windows-only.
3. **WEM file does not exist:** The WEM file referenced by the export XML may not be
   synced. Check the file path shown at the bottom of the Audio Player panel.

### 12.6 Audio conversion takes a long time

**Symptom:** After clicking Play, the status shows "Converting..." for many seconds.

**Explanation:** The first time you play a WEM file, it must be converted to WAV format.
This conversion is cached, so replaying the same file is instant. Very large WEM files
(multiple minutes of audio) may take several seconds to convert. The conversion times
out after 60 seconds.

### 12.7 Search returns no results even though the entry exists

**Symptom:** You know an entry exists but searching for it returns empty.

**Possible causes:**
- **Wrong mode:** Each mode only searches its own entries. A character name will not
  appear in MAP mode. Switch to CHARACTER mode.
- **Wrong match type:** "Exact" requires the full field value to match. Try "Contains"
  for partial matches.
- **Wrong language:** If you search for "Castle" but the English translation is not
  loaded yet, the search will not find it. Select English in the language dropdown
  and wait for it to load, then search again.
- **Special characters:** Try searching without special characters or punctuation.

### 12.8 Language loading takes a long time

**Symptom:** Selecting a new language shows "Loading language..." for several seconds.

**Explanation:** Each language file contains approximately 95,000 entries. Loading and
indexing takes 2-5 seconds depending on your disk speed. This happens only once per
language per session. English and Korean are preloaded at startup to avoid this delay
for the most common languages.

### 12.9 Results are slow to display with thousands of entries

**Symptom:** Loading all entries or searching with broad terms is sluggish.

**Solution:** Reduce the "Results per page" setting in File > Settings. The default of
100 is a good balance. Going above 300 may cause noticeable delays when populating the
grid.

### 12.10 Map window appears blank

**Symptom:** The map opens but shows "No nodes with positions."

**Solution:** This happens if:
- You are not in MAP mode (the map button only appears in MAP mode)
- FactionNode XMLs have not loaded yet (wait for loading to complete)
- The FactionNode data does not contain WorldPosition attributes

### 12.11 Application crashes with "TclError"

**Symptom:** An error dialog appears mentioning "TclError" or "unknown option."

**Explanation:** This is a known class of bugs related to the difference between `tk`
and `ttk` widgets. If you encounter this, please report it with the full error text
from the log file. The log file location is printed at the top of each log.

### 12.12 Settings lost after reinstall

**Symptom:** After installing a new version, your drive letter and branch are reset.

**Solution:** The installer may overwrite `settings.json`. Before upgrading, back up
your `settings.json` file. After installing, copy it back to the application folder.
Alternatively, the application will detect the old `mdg_settings.json` and migrate it
automatically.

### 12.13 "Load failed" error on mode switch

**Symptom:** Switching between modes shows an error dialog.

**Possible causes:**
- The data folders for the new mode do not exist on disk.
- A folder path is malformed (check settings.json for incorrect backslash escaping).
- The XML files in the folder are corrupted or incomplete.

Check the log file for the specific error message and stack trace.

### 12.14 Cleanup button reports "0 cached files"

**Symptom:** Clicking "Cleanup cache" says "Cleaned 0 cached files."

**Explanation:** This is normal if you have not played any audio yet, or if you already
cleaned up recently. Cached WAV files accumulate in `%TEMP%\mapdatagenerator_audio\`
only after audio playback.

### 12.15 Progress bar keeps animating after loading completes

**Symptom:** The indeterminate progress bar at the bottom never stops.

**Solution:** This indicates the loading thread encountered a silent error. Check the
log file for details. A common cause is a network drive becoming temporarily
unavailable during loading.

---

## 13. File Format Reference

### DDS (DirectDraw Surface)

- **Extension:** `.dds`
- **Content:** Game textures (icons, portraits, artwork)
- **Typical sizes:** 128x128, 256x256, 512x512, 1024x1024
- **Formats used:** DXT1, DXT5, BC7 (handled by pillow-dds)
- **Location:** `common\mainline\commonresource\ui\texture\image\`
- **Count:** Approximately 9,300 files

### WEM (Wwise Encoded Media)

- **Extension:** `.wem`
- **Content:** Encoded audio files (voice lines, sound effects)
- **Codec:** Wwise Vorbis or Wwise Opus
- **Conversion:** vgmstream-cli converts WEM to standard WAV for playback
- **Location:** `cd\mainline\resource\sound\windows\[Language]\`

### XML (Game Data)

All game data is stored in XML format. The application uses the `lxml` library with
recovery mode to handle occasional malformed markup in the source files.

| File Pattern | Content | Mode |
|--------------|---------|------|
| `FactionNode*.xml` | Map locations with world positions | MAP |
| `KnowledgeInfo*.xml` | Knowledge entries with UITextureName | MAP, CHARACTER, ITEM |
| `KnowledgeGroupInfo*.xml` | Knowledge group containers | MAP, CHARACTER, ITEM |
| `CharacterInfo*.xml` | Character metadata | CHARACTER |
| `NodeWaypointInfo*.xml` | Waypoint connections between nodes | MAP |
| `LanguageData_[code].xml` | Localization text (one per language) | All modes |
| `export__\*.xml` | Audio event name to StrOrigin mappings | AUDIO |

### XLSX (VoiceRecordingSheet)

- **Extension:** `.xlsx`
- **Content:** Voice recording order and metadata
- **Location:** `cd\mainline\resource\editordata\VoiceRecordingSheet__\`
- **Used for:** Ordering audio entries chronologically within categories

### JSON (Settings)

- **File:** `settings.json`
- **Content:** Application configuration (drive, branch, UI preferences)
- **Encoding:** UTF-8
- **Location:** Same directory as the executable

---

## Quick Reference Card

```
KEYBOARD SHORTCUTS
  Space ............. Play/Stop audio (AUDIO mode, when not in search box)
  Left Arrow ........ Previous entry (AUDIO mode)
  Right Arrow ....... Next entry (AUDIO mode)
  Ctrl+C ............ Copy selected cell (full untruncated text)
  Enter ............. Execute search (when in search box)
  Escape ............ Close image popup / close dialogs

MODES
  MAP ............... FactionNodes + map visualization + DDS images
  CHARACTER ......... CharacterInfo + DDS images
  ITEM .............. KnowledgeInfo + DDS images
  AUDIO ............. WEM audio + KOR/ENG scripts + category tree

SEARCH
  Contains .......... Partial match anywhere in any field
  Exact ............. Full field value must match
  Fuzzy ............. Approximate matching (threshold: 0.6)

SETTINGS
  File > Settings ... Drive letter, branch, language, search limits
  settings.json ..... All settings stored here (editable)

LOGS
  logs/ ............. Timestamped log files for debugging
```

---

*MapDataGenerator v2.0 -- Internal tool for the LocaNext localization project.*
*Last updated: February 2026*
