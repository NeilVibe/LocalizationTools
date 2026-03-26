# Domain Pitfalls -- v13.0 Production Path Resolution

**Domain:** Game localization tool -- path resolution wiring
**Researched:** 2026-03-26
**Milestone:** v13.0

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: C6/C7 Korean Text Matching Fragility

**What goes wrong:** The StringId-to-entity bridge (C6/C7) relies on normalizing Korean text from entity name/desc and matching against StrOrigin text in languagedata files. When entity name text differs even slightly from the StrOrigin (added suffixes, different formatting, br-tag differences), the match fails silently.

**Why it happens:** Korean text normalization strips `<br/>` tags, collapses whitespace, and removes placeholder suffixes -- but cannot handle semantic differences (e.g., entity name = "검은 별의 검" vs StrOrigin = "검은 별의 검에 대한 설명입니다").

**Consequences:** StringIds that should resolve to images/audio return 404. Users see "No Image/Audio Context" for rows that DO have associated media. The system appears broken.

**Prevention:** Add StrKey-based matching as the PRIMARY chain. Export XML filenames often contain entity StrKeys (e.g., `characterinfo_showcase.staticinfo.xml` -> entity source_file). Match by source_file + StringId membership in D17, rather than by text content.

**Detection:** If C7 dict (stringid_to_entity) is significantly smaller than expected, the text matching is losing data. Log the match rate during build.

### Pitfall 2: C2 Audio Chain is Dead Code

**What goes wrong:** `_build_strkey_to_audio_path()` checks `wem_by_event.get(strkey.lower())`. WEM files are named after sound events (`play_varon_greeting_01`), NOT entity StrKeys (`CharacterInfo_Varon`). This chain produces near-zero matches.

**Why it happens:** The original implementation assumed WEM filenames would match entity identifiers, but Wwise audio events use a completely different naming convention.

**Consequences:** C2 dict is effectively empty. Code that falls through to C2 always gets None. Not harmful (C3 is the real chain), but confusing and wasteful.

**Prevention:** Either remove C2 or rewrite it to trace entity -> export events -> event_name -> WEM. Currently C3 does this correctly for StringId-based lookups.

**Detection:** Log `len(self.strkey_to_audio_path)` after build -- if near zero, confirms C2 is dead.

### Pitfall 3: MegaIndex Rebuild Performance on Real Data

**What goes wrong:** Changing branch+drive triggers `MapDataService.initialize()` -> `MegaIndex.build()`. With real Perforce data (potentially thousands of XML files, thousands of DDS/WEM files), the full 7-phase rebuild could take 30+ seconds.

**Why it happens:** MegaIndex.build() re-parses ALL XML files from scratch. No incremental update, no caching between rebuilds.

**Consequences:** User changes branch, UI freezes for 30+ seconds with no feedback. Or worse, async rebuild races with user interactions.

**Prevention:** Show a progress indicator during rebuild. Consider caching parsed data per branch. Or separate path re-resolution (fast) from XML re-parse (slow).

**Detection:** Time the build with real data: `mega._build_time` is logged. If > 5s, add progress UI.

## Moderate Pitfalls

### Pitfall 4: Mock Paths Use Absolute Paths

**What goes wrong:** `configure_for_mock_gamedata(mock_gamedata_dir)` stores absolute Path objects. If the project directory moves or tests run from different locations, paths break.

**Prevention:** Make mock paths relative to project root or use Path resolution relative to `__file__`.

### Pitfall 5: onScrollToRow Delegate Race in SearchEngine

**What goes wrong:** SemanticSearch result click calls `onScrollToRow?.()` which may be null if the $effect in VirtualGrid hasn't fired yet. The click silently does nothing.

**Prevention:** Use a prop pattern or ensure delegate is set synchronously during component initialization, not in an $effect.

### Pitfall 6: visibleColumns Dead Code Causes Wasted Reactivity

**What goes wrong:** `let visibleColumns = $derived(getVisibleColumns($preferences, allColumns))` recomputes on every preference change but the result is never used.

**Prevention:** Remove immediately. Dead $derived creates unnecessary reactive subscriptions and re-computation.

## Minor Pitfalls

### Pitfall 7: onSaveComplete Prop is Dead

**What goes wrong:** InlineEditor declares `onSaveComplete` as a prop but VirtualGrid never passes it. If someone later tries to use it, they will wonder why it never fires.

**Prevention:** Either wire it (if save-complete events are needed by consumers) or remove the prop.

### Pitfall 8: tmSuggestions Trapped in StatusColors

**What goes wrong:** StatusColors fetches TM suggestions but never exports them. If another component needs suggestion data (e.g., for display in a panel), it cannot access them.

**Prevention:** Verify whether v12.0 TM Intelligence superseded this need. If yes, document that tmSuggestions is intentionally internal. If no, add a getter.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Branch+Drive UI | User enters invalid path, no feedback | PATH-02 validation with InlineNotification |
| Path validation | Checking file existence is slow on network drives | Async validation with loading state |
| Image chain wiring | C6 text matching misses entities | Add StrKey-based matching, log match rate |
| Audio chain wiring | C2 is dead, C3 depends on export XML events | Use C3 exclusively, verify export XMLs have events |
| Mock path testing | Absolute paths break in CI | Use relative paths from project root |
| MegaIndex split | Circular imports between split modules | Use lazy imports or dependency injection |
