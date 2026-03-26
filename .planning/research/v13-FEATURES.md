# Feature Landscape -- v13.0 Production Path Resolution

**Domain:** Game localization tool -- path resolution wiring
**Researched:** 2026-03-26
**Confidence:** HIGH

## Table Stakes

Features required for production path resolution to be useful.

| Feature | Why Expected | Complexity | Status |
|---------|--------------|------------|--------|
| Branch+Drive selector UI | Users must configure Perforce workspace before anything works | Low | NOT BUILT |
| Path validation feedback | Users need to know if configured paths actually exist | Low | NOT BUILT |
| Image display for selected row | Already works in DEV mock mode; needs production wiring | Already Done | WORKING |
| Audio playback for selected row | Already works in DEV mock mode; needs production wiring | Already Done | WORKING |
| Mock testing infrastructure | Validate chains work before real Perforce data | Medium | PARTIAL (fixtures exist, tests needed) |

## Differentiators

Features that set the path resolution apart from basic file browsers.

| Feature | Value Proposition | Complexity | Status |
|---------|-------------------|------------|--------|
| 3-tier image resolution (direct, C7 bridge, fuzzy) | Finds images even when StringId does not match StrKey exactly | Already Done | WORKING |
| 5-tier audio resolution (cache, C3, C2, lazy WAV, fuzzy) | Multiple fallback chains maximize audio coverage | Already Done | WORKING |
| Automatic entity detection from StringId | C7 bridge identifies which game entity a translation belongs to | Medium | FRAGILE |
| Script text display with audio | Shows Korean/English script alongside audio player | Already Done | WORKING |

## Anti-Features

Features to explicitly NOT build in v13.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-branch simultaneous view | Overcomplicates UI for single-user desktop app | One branch active at a time, re-configure to switch |
| Real-time Perforce sync | Desktop app, not CI pipeline | User manually re-configures after Perforce sync |
| Custom path template editing | 11 templates cover all known use cases | Add templates to KNOWN_BRANCHES if new branches appear |
| DDS/WEM format auto-detection | Already handled by MediaConverter | Keep existing Pillow (DDS) + vgmstream (WEM) approach |

## Feature Dependencies

```
Branch+Drive Selector UI (PATH-01)
  --> Path Validation (PATH-02) [needs config before validating]
  --> Image Chain Wiring (PATH-03) [needs paths before resolving images]
  --> Audio Chain Wiring (PATH-04) [needs paths before resolving audio]

FIX-01 (Code Review) --> independent, no downstream deps

MOCK-01 (Mock Paths) --> MOCK-02 (E2E Tests) [needs mock structure before testing]

ARCH-02 (MegaIndex Split) --> independent, no downstream deps
```

## MVP Recommendation

Prioritize:
1. FIX-01: Code review issues (cleanup debt)
2. PATH-01 + PATH-02: Branch+Drive selector + validation (enables production use)
3. PATH-03 + PATH-04 + MOCK-01 + MOCK-02: Chain wiring + testing (the core value)

Defer: ARCH-02 (mega_index.py split) -- pure refactoring, can be done later without affecting functionality.
