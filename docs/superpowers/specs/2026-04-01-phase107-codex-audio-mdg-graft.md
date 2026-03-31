# Phase 107 Spec: Codex Audio — Full MDG Graft

> **Date:** 2026-04-01
> **Source:** MDG (MapDataGenerator) audio system comparison via 6-agent exploration
> **Status:** SPEC — needs plan before execution

---

## Goal

Make the Codex Audio page a PERFECT copy of MapDataGenerator's audio system. Two-panel layout: category tree + list on left, dedicated audio player panel on right.

## Current State (60-70% of MDG)

What works:
- Category tree hierarchy (export_path based)
- Search and filtering
- Basic script display (KOR + ENG)
- Audio playback via WEM streaming
- UI layout (sidebar + list + detail)

## Missing from MDG (CRITICAL)

### 1. Multi-Language Folder Switching
- MDG has 3 audio folders: English(US), Korean, Chinese(PRC)
- User can switch between languages via dropdown
- Each folder has different WEM files
- Codex only supports 1 folder — no language selector

### 2. Dedicated Audio Player Panel (Right Side)
- MDG: dedicated right-side panel with full controls
- Play/Stop/Prev/Next buttons
- Progress bar + elapsed time display
- Auto-play toggle checkbox
- KOR script (60% height) + ENG script (40% height) in colored backgrounds
- Event name header + duration label

### 3. Player Navigation
- Prev/Next buttons to go through events without going back to list
- Keyboard shortcuts for navigation
- Auto-play next on completion

### 4. Cache Management
- Cleanup cache button for temp WAV files
- Async duration fetching (background thread)

### 5. VRS (VoiceRecordingSheet) Ordering
- MDG can apply chronological reordering from VRS
- Events sorted by recording order, not just alphabetical

## Reference Files

| MDG File | Purpose |
|----------|---------|
| `MapDataGenerator/gui/audio_viewer.py` (570 lines) | Full audio player panel |
| `MapDataGenerator/gui/export_tree.py` | Category tree builder |
| `MapDataGenerator/core/linkage.py` | Audio indexing + VRS ordering |
| `locaNext/src/lib/components/pages/AudioCodexPage.svelte` | Current Codex Audio |
| `locaNext/src/lib/components/ldm/AudioCodexDetail.svelte` | Current detail component |
| `server/tools/ldm/routes/codex_audio.py` | Backend audio codex routes |
