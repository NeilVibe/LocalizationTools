# Codex Vision — Interactive Game Encyclopedia

**Source:** User request (2026-03-26)
**Inspiration:** crimsondesert.gg interactive map/encyclopedia

## Concept

Full interactive Codex for each generator type in QACompiler — Quest, Item, Character, Region. Each with dedicated tabs matching QACompiler's tab structure. Plus an interactive world map using Region + WorldPosition data.

## Data Sources (Already Exist)

### QACompiler Generators (tab structure = Codex sections)
- **Item Generator** — tabs already separate items by type (weapon, armor, consumable, etc.)
- **Character Generator** — tabs for NPCs, monsters, bosses, etc.
- **Quest Generator** — quest chains, prerequisites, rewards
- **Region Generator** — areas, sub-regions, connected zones
- **Skill/Knowledge Generator** — abilities, passives, knowledge entries
- **Gimmick Generator** — interactive objects, triggers

### Map Data (Already Exist)
- **Region + WorldPosition** — every entity has coordinates
- **MapPlot** — defines region boundaries/frontiers
- **Route connections** — paths between regions (already rendered in World Map page)

## Architecture

### Per-Generator Codex Page
```
Codex: Items
├─ Tab: Weapons (from QACompiler Item generator weapon tab)
├─ Tab: Armor
├─ Tab: Consumables
├─ Tab: Materials
└─ Each entry shows:
   - Name (KR + EN)
   - DDS image (from Perforce path)
   - Description text
   - Stats/attributes
   - Related entities (cross-refs)
   - Where found (Region + WorldPosition → map pin)
```

### Interactive Map (Enhanced World Map)
```
World Map
├─ Region boundaries (from MapPlot frontier data)
├─ Entity pins (from WorldPosition)
│   ├─ Color-coded by type (item=blue, character=red, quest=gold, region=green)
│   ├─ Click → Codex card popup
│   └─ Filter by entity type
├─ Region labels (from Region generator)
└─ Zoom levels: World → Region → Sub-region
```

## Existing Infrastructure to Reuse
- World Map page (`MapCanvas.svelte`) — already has d3-zoom, nodes, routes
- Codex pages (Item, Character, Audio, Region) — already exist from v3.0
- EntityCard component — already renders entity data
- GameDataSearcher — 6-tier cascade for entity lookup
- MegaIndex — 35 dicts, cross-references all entity types

## What's NEW
- Tab structure matching QACompiler generators (more granular than current Codex)
- Region boundary polygons from MapPlot data
- Entity pins on map from WorldPosition
- Per-generator Codex navigation (not just by entity type)
- crimsondesert.gg-style visual quality

## Priority
- This is a FUTURE milestone feature (v14.0+), NOT v13.0
- v13.0 focuses on path resolution which ENABLES this (images/audio need Perforce paths working)
- Captured here for planning purposes
