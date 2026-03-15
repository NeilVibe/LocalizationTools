# Domain Pitfalls

**Domain:** Localization platform — wiring real XML parsing, media conversion, merge logic, and LLM integration to existing scaffolded system
**Researched:** 2026-03-15
**Milestone:** v2.0 Real Data + Dual Platform

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or major architectural issues.

### Pitfall 1: br-tag Corruption During Merge/Export Round-Trip

**What goes wrong:** Newlines in XML language data use `<br/>` tags. During merge or export, these get double-escaped (`&amp;lt;br/&amp;gt;`), stripped, converted to `\n`, or mangled into wrong variants (`<br>`, `<BR/>`). Corrupted files break the game client.

**Why it happens:** Three different representations exist at different layers:
- On disk: `&lt;br/&gt;` (XML-escaped)
- In memory (after lxml parse): `<br/>` (unescaped)
- In Excel cells: `<br/>` (literal text)

Developers who don't understand this write code that breaks at boundary crossings. Copy-paste from XML files into Excel creates double-escaping. Standard `html.escape()` or manual escaping on top of lxml's auto-escaping produces `&amp;lt;br/&amp;gt;`.

**Consequences:** Corrupted game data files. Newlines disappear from translations. Game client crashes or shows garbled text. Silent corruption (no error, just wrong output).

**Prevention:**
- Reuse QuickTranslate's three-layer defense exactly: `_convert_linebreaks_for_xml()`, `_normalize_newlines()` (7-step postprocess), `_has_wrong_newlines()` (detection)
- NEVER manually escape `<br/>` — let lxml handle XML escaping automatically
- Run `cleanup_wrong_newlines_on_tree()` after EVERY merge/transfer operation
- Test with strings containing `<br/>` at start, end, middle, consecutive (`<br/><br/>`), and mixed with other content
- Add a round-trip test: parse XML -> merge -> write XML -> parse again -> compare

**Detection:** Strings that had newlines before merge no longer have them after. `grep -c 'lt;br' output.xml` shows more `&lt;br` than expected (double-escaping). Postprocess step 1 fixing counts are non-zero on clean data.

**Phase:** Must be addressed in Translator Merge phase (TMERGE). Gate: zero br-tag corruption in round-trip tests.

---

### Pitfall 2: xml_handler.py Uses stdlib ET, Not lxml — Parse Divergence

**What goes wrong:** The existing LocaNext XML handler (`server/tools/ldm/file_handlers/xml_handler.py`) uses `xml.etree.ElementTree` (stdlib). All NewScripts (QuickTranslate, QACompiler, MapDataGenerator) use `lxml.etree`. These parse differently: lxml has recovery mode, handles malformed XML, preserves attribute order. Stdlib ET chokes on malformed game data, silently drops attributes, and reorders them.

**Why it happens:** v1.0 scaffolds were built for demo with clean test data. Real game XML files are often malformed (bare `&` in attributes, control characters, unclosed tags). The sanitizer in QuickTranslate (`sanitize_xml_content()`) was built specifically to handle these cases — but it targets lxml's parser.

**Consequences:** Real game files fail to parse where test fixtures succeeded. Attribute ordering changes between read/write cycles, creating false diffs. Recovery mode differences mean lxml recovers from corruption that stdlib ET rejects entirely.

**Prevention:**
- Migrate `xml_handler.py` to lxml with `recover=True` parser, matching QuickTranslate's `_parse_target_xml()` pattern
- Port `sanitize_xml_content()` from QuickTranslate — it handles control characters, bad `&` entities, bare `<` in attributes
- Use the 3-stage validation pattern from QuickTranslate: (1) read raw bytes, (2) strict parse, (3) recovery parse as fallback
- Test with intentionally malformed XML (missing closing tags, bare `&`, control chars `\x00-\x08`)

**Detection:** Parse failures on real game files that worked in v1.0 with fixtures. Attribute order changes visible in git diffs after save.

**Phase:** Must be addressed FIRST in XML Parsing phase (XML-04). All downstream features depend on reliable parsing.

---

### Pitfall 3: Encoding Detection Cascade Failure

**What goes wrong:** Game XML files use mixed encodings: UTF-8, UTF-16, CP1252 (for legacy European text), Shift-JIS (Japanese files). The current handler tries `['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']` in sequence. This misdetects CP1252 files as ISO-8859-1 (they overlap but differ for bytes 0x80-0x9F), corrupting characters like curly quotes and em-dashes. Korean text in non-UTF-8 files is silently destroyed.

**Why it happens:** Many encodings are supersets of ASCII so the first few bytes decode fine in any encoding. The cascade approach picks whichever encoding doesn't throw an error, not the correct one. XML declaration `<?xml encoding="..."?>` is ignored.

**Consequences:** Korean/CJK text becomes mojibake. Round-trip parse-write changes character encoding silently. Translations appear corrupted but the file "looks fine" in logs.

**Prevention:**
- Parse the XML declaration FIRST to extract declared encoding
- Use `chardet` or `charset-normalizer` as a fallback detector, not a blind cascade
- For LocStr XML files: Korean content = always UTF-8 (this is the project standard)
- Add encoding preservation: read in detected encoding, write back in same encoding
- Test with files containing Korean + European special chars (accented characters)

**Detection:** Characters like `\u2019` (right single quote) appearing as `\xc3\xa2\xc2\x80\xc2\x99` after round-trip. Korean text showing as `?` or boxes.

**Phase:** XML Parsing phase (XML-04, XML-06). Must be solid before any merge/export work.

---

### Pitfall 4: Match-Type Confusion in Translator Merge (Strict vs StringID vs StrOrigin vs Fuzzy)

**What goes wrong:** QuickTranslate's merge logic has four distinct match types: (1) Strict = StringID + StrOrigin both match, (2) StringID-only = same StringID, different source text, (3) StrOrigin-only = same source text, different StringID, (4) Fuzzy = Model2Vec similarity above threshold. Implementing these incorrectly causes wrong translations applied to wrong strings, or correct translations overwritten by stale ones.

**Why it happens:** Developers implement "merge" as simple StringID lookup and call it done. They miss that StrOrigin matching is critical for strings that were re-keyed (new StringID, same text). They miss that StringID-only matching should NOT overwrite when the source text changed significantly (the translation is for a different source). Match priority order matters: strict wins over partial, partial over fuzzy.

**Consequences:** Wrong translations applied to strings. "Last-wins" in lookup dict means a bad fuzzy match can overwrite a good strict match if processed in wrong order. Translations for deleted/renamed strings leak into current data. Silent data corruption — no errors, just wrong text in the game.

**Prevention:**
- Port QuickTranslate's exact match hierarchy: strict first, then StringID-only, then StrOrigin-only, then fuzzy
- Build correction lookup as `dict[string_id] -> correction` and `dict[normalized_strorigin] -> correction`, not a flat list
- Use `normalize_for_matching()` from QuickTranslate's `text_utils.py` for StrOrigin comparison (strips whitespace, normalizes Unicode)
- Skip Korean-only entries (untranslated source text) — they are NOT corrections
- Skip "no translation" entries — transferring them overwrites real translations
- Add match-type tracking in results so users can see WHY each string was matched
- Test with: same StringID different source, same source different StringID, near-duplicate sources with different translations

**Detection:** Match type distribution is suspicious (e.g., 90% fuzzy matches on a file that should have 90% exact). Translation quality drops after merge. Postprocess "no translation replaced" count is high.

**Phase:** Translator Merge phase (TMERGE-01 through TMERGE-03). This is the core logic — get it wrong and everything downstream is wrong.

---

### Pitfall 5: DDS Conversion Platform Gap (WSL2 vs Windows)

**What goes wrong:** The existing `DDSHandler` conditionally imports `pillow_dds` only on Windows (`if sys.platform == "win32"`). LocaNext's FastAPI server runs in WSL2 (Linux). DDS files live on the Windows filesystem (`F:\perforce\...`). The handler silently skips `pillow_dds` registration on Linux, then `Image.open()` fails with "cannot identify image file" for any DDS format that Pillow doesn't natively support (DXT1, DXT5, BC7 — the most common game texture formats).

**Why it happens:** MapDataGenerator was built as a Windows desktop app (Tkinter). LocaNext runs the server in WSL2 but needs to display images in a browser. The platform check made sense for a Windows-only tool but breaks in WSL2.

**Consequences:** All DDS images show as broken/placeholder in the browser. The feature works in testing (mock PNGs) but fails with real DDS files. No error in logs — just "No Image" placeholder everywhere.

**Prevention:**
- Remove the `sys.platform == "win32"` guard — install `pillow-dds` unconditionally
- Convert DDS to PNG server-side and serve PNGs to the browser (browsers can't display DDS anyway)
- Cache converted PNGs on disk (DDS files don't change often)
- Handle DDS formats that even `pillow-dds` can't decode (some BC7 variants) — return placeholder with specific error message
- Test with real DDS files from each compression format: DXT1 (no alpha), DXT5 (with alpha), BC7 (modern), uncompressed

**Detection:** Image tab shows all placeholders. Server logs show `PIL.UnidentifiedImageError`. `python3 -c "import pillow_dds"` fails in WSL2.

**Phase:** Image & Audio Pipeline phase (MEDIA-01). Must be validated early — visual impact is huge for demos.

---

### Pitfall 6: WEM Audio Conversion Requires External Binary

**What goes wrong:** `AudioHandler` uses `vgmstream-cli` — an external binary that must be manually placed in `tools/`. It's not pip-installable. The handler also uses `winsound` for playback, which only exists on Windows. In WSL2, both `vgmstream-cli.exe` (Windows binary) and `winsound` are unavailable. Audio playback silently fails.

**Why it happens:** MapDataGenerator was Windows-only. LocaNext needs to serve audio to a browser, which is a fundamentally different playback model (HTTP streaming, not OS audio API).

**Consequences:** Audio tab shows "Audio unavailable" for every entry. No WEM-to-WAV conversion possible. A key demo feature is dead.

**Prevention:**
- Compile or download `vgmstream-cli` Linux binary for WSL2 (available from vgmstream GitHub releases)
- Replace `winsound` playback with HTTP-served WAV: convert WEM -> WAV server-side, serve via API endpoint, play in browser `<audio>` element
- Cache converted WAV files (same hash-based caching pattern from existing `AudioHandler`)
- Handle missing `vgmstream-cli` gracefully: return structured error with setup instructions, not silent failure
- Add `is_available` health check endpoint so the UI can show appropriate state

**Detection:** `shutil.which("vgmstream-cli")` returns None. Audio tab shows "unavailable" badge. Server startup log says "vgmstream-cli not found".

**Phase:** Image & Audio Pipeline phase (MEDIA-02). Requires binary setup before any audio work.

---

### Pitfall 7: Dual UI State Leaks Between Modes

**What goes wrong:** When switching between Translator mode and Game Dev mode (based on file type), Svelte component state from the previous mode persists. Column configurations, selected rows, filter states, sort orders from Translator mode bleed into Game Dev mode. The virtual grid renders wrong columns, crashes on missing data fields, or shows stale data.

**Why it happens:** Both modes share the same virtual grid infrastructure (DUAL-05 requirement). If mode switching reuses the same component instance, `$state` values from the previous mode persist. Svelte 5's reactivity system tracks mutations — switching mode doesn't automatically reset all derived state.

**Consequences:** Game Dev mode shows "Match%" column (Translator-only). Translator mode shows "Children count" column (Game Dev-only). Filters reference non-existent fields, causing JavaScript errors. Selected row indices from a 500-row Translator file persist when opening a 50-row Game Dev file, causing out-of-bounds access.

**Prevention:**
- Use `{#key fileType}` to force full component remount on mode switch — cleanest approach
- If reusing component: create a `resetGridState()` function that explicitly clears ALL `$state` variables
- Column configs should be `$derived` from file type, not manually set
- Test the exact sequence: open Translator file -> select row 400 -> open Game Dev file with 50 rows -> verify no crash
- Test: open Translator file -> apply filter -> open Game Dev file -> verify filter is cleared

**Detection:** Console errors about undefined properties. Columns showing data from wrong mode. Grid crashes when switching between files of different types.

**Phase:** Dual UI phase (DUAL-01 through DUAL-05). Architecture decision needed early — it affects all grid work.

---

## Moderate Pitfalls

### Pitfall 8: Position-Based vs Match-Type Merge Confusion (Game Dev)

**What goes wrong:** Game Dev merge (GMERGE) is fundamentally different from Translator merge (TMERGE). Game Dev merge is position-based (preserving XML document order at node/attribute/children depth). Translator merge is match-type based (StringID, StrOrigin, fuzzy). Developers who implement Translator merge first then try to "adapt" it for Game Dev end up with a broken hybrid.

**Prevention:**
- Keep two completely separate merge implementations — no shared base class that tries to abstract both
- Game Dev merge operates on XML tree structure (parent -> children -> sub-children), not on flat row lists
- Test with: node additions, node deletions, attribute value changes, child reordering, new nested children
- Use `lxml`'s tree comparison, not string comparison

**Phase:** Game Dev Merge phase (GMERGE). Implement AFTER Translator Merge is stable — don't try to generalize.

---

### Pitfall 9: LLM Timeout and Failure Handling

**What goes wrong:** Ollama/Qwen3 inference takes 1-3 seconds per summary. If the UI blocks waiting for AI summaries, the entire editor feels sluggish. If multiple strings are selected rapidly, pending requests pile up. If Ollama crashes or runs out of VRAM, every pending request hangs until timeout.

**Prevention:**
- Fire-and-forget pattern: request summary on row select, display when ready, show spinner meanwhile
- Cancel pending requests when user selects a different row (generation counter pattern from `AudioHandler`)
- Set aggressive timeout (5s) — better to show "Summary unavailable" than freeze
- Cache summaries per StringID in SQLite (AISUM-04) — never re-generate what's already cached
- Check Ollama health at startup, set `ai_available` flag, skip all AI calls if unavailable
- Rate-limit requests: max 1 concurrent Ollama call, queue with dedup

**Detection:** UI freezes for 2+ seconds when selecting rows. Multiple identical requests in server logs. Ollama process consuming 12GB VRAM and swapping.

**Phase:** AI Summaries phase (AISUM). Design the async pattern BEFORE implementing the LLM calls.

---

### Pitfall 10: LLM Prompt Engineering for Structured Output

**What goes wrong:** Qwen3-4B/8B produces inconsistent JSON output. Sometimes it wraps JSON in markdown code blocks. Sometimes it adds explanatory text before/after. Sometimes the JSON keys differ from what the code expects. Parsing fails silently and summaries show as empty.

**Prevention:**
- Use Ollama's `format: "json"` parameter to force JSON mode
- Define explicit JSON schema in the prompt: `{"summary": "...", "context": "..."}`
- Add robust JSON extraction: try `json.loads()` first, then regex for JSON within markdown blocks, then fallback
- Test with edge cases: strings containing quotes, strings with `<br/>` tags, very long strings (>500 chars), empty strings
- Keep prompts SHORT for small models — Qwen3-4B degrades with long system prompts

**Phase:** AI Summaries phase (AISUM-01, AISUM-02). Prototype prompts early with real game data, not Lorem ipsum.

---

### Pitfall 11: Cross-Reference Chain Resolution Across Files

**What goes wrong:** XML cross-references (StrKey -> KnowledgeKey -> UITextureName -> DDS path) span multiple XML files. If one file in the chain is missing, moved, or has a different schema version, the entire chain breaks silently. The code returns `None` for image/audio and the UI shows placeholders — but the user doesn't know WHY.

**Prevention:**
- Implement chain resolution with explicit step tracking: log which step succeeded/failed
- Return partial results: "Found KnowledgeKey but UITextureName missing" is more useful than "No Image"
- Cache resolved chains (they're expensive to compute, data changes rarely)
- Handle missing intermediate files gracefully: skip that chain, try next candidate
- QACompiler's `_find_knowledge_key()` is the reference implementation — port it exactly

**Detection:** Image tab shows placeholder but the DDS file exists on disk. Chain resolution logs show "KnowledgeKey not found" for keys that exist in a different XML file.

**Phase:** XML Parsing phase (XML-01, XML-03, XML-05). Must be solid before Image & Audio Pipeline.

---

### Pitfall 12: File Path Translation WSL2 to Windows

**What goes wrong:** Game data lives on Windows filesystem (`F:\perforce\cd\mainline\...`). LocaNext server runs in WSL2 where the path is `/mnt/f/perforce/cd/mainline/...`. Path templates in `mapdata_service.py` use Windows-style backslash paths. `Path()` objects constructed with Windows paths don't resolve in Linux. `os.path.exists()` returns False for valid Windows paths when called from WSL2.

**Prevention:**
- Create a `path_translator` utility that converts `F:\path\to\file` to `/mnt/f/path/to/file`
- Normalize all paths at the API boundary — store as POSIX internally
- Handle drive letter case insensitivity (`F:` vs `f:`)
- Handle `\\?\` long path prefix that Windows sometimes adds
- Test with paths containing spaces, Korean characters, and deeply nested directories
- The existing `PATH_TEMPLATES` in `mapdata_service.py` need a WSL2 translation layer

**Detection:** `FileNotFoundError` for paths that exist when accessed from Windows Explorer. `os.path.exists()` returns False but `ls /mnt/f/...` shows the file.

**Phase:** XML Parsing phase (early). Every file operation depends on correct path resolution.

---

### Pitfall 13: Postprocess Pipeline Not Applied to Game Dev Merge Output

**What goes wrong:** The 7-step postprocess pipeline (newline normalization, apostrophe cleanup, invisible chars, etc.) is built for Translator mode LocStr elements. Game Dev merge operates on arbitrary XML nodes with arbitrary attributes — not just `Str`/`Desc`. If postprocess is applied to Game Dev output, it corrupts non-localization attributes (e.g., normalizing a hyphen in an XML attribute that's a formula or coordinate). If it's NOT applied, br-tags in Game Dev text fields are corrupted.

**Prevention:**
- Game Dev merge needs its OWN postprocess that only touches text-content attributes (Name, DESC, etc.), not structural attributes (coordinates, IDs, formulas)
- Define which attributes are "text content" per XML schema (QACompiler generators know this)
- Default to NO postprocessing for unknown attributes — safer to leave them untouched
- Test: merge a file with both text attributes and numeric/formula attributes, verify only text is postprocessed

**Phase:** Game Dev Merge phase (GMERGE). Must be designed alongside the merge logic, not bolted on after.

---

### Pitfall 14: Korean Regex Missing Jamo and Compatibility Jamo

**What goes wrong:** Korean detection uses only syllable range `[\uac00-\ud7af]`, missing Jamo (`\u1100-\u11ff`) and Compatibility Jamo (`\u3130-\u318f`). Text containing decomposed Korean characters (individual consonants/vowels) is classified as "not Korean" and gets processed as a translation — overwriting real translations with source text.

**Prevention:**
- Use the complete regex from MEMORY.md: `[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]`
- This is already documented as a critical cross-project rule — enforce it in code review
- Test with: composed syllables (`\uac00`), individual Jamo (`\u1100`), compatibility consonants (`\u3131`)

**Detection:** `is_korean_text()` returns False for strings containing Korean consonants/vowels without syllable blocks.

**Phase:** XML Parsing / Translator Merge. Affects both Korean text detection and merge skip logic.

---

### Pitfall 15: Optimistic UI Revert Failures on Merge Operations

**What goes wrong:** Optimistic UI is mandatory — the UI updates instantly, server syncs in background. For cell edits this is simple (revert one cell). For merge operations affecting hundreds of rows, the "revert on failure" path is catastrophic: you need to undo hundreds of row changes atomically. If the revert itself fails (network error during revert), you have a half-merged state that's neither the original nor the merged result.

**Prevention:**
- Merge operations should NOT be optimistic — they're batch operations, not interactive edits
- Show a progress indicator during merge, commit all changes at once on success
- Use database transactions: either all rows merge or none do
- Store pre-merge snapshot for rollback (not row-by-row undo, but full state snapshot)
- Keep optimistic UI for individual cell edits only

**Detection:** Merge fails halfway, some rows updated and some not. UI shows mixed state. Refresh shows different data than what's displayed.

**Phase:** Translator Merge and Game Dev Merge phases. Architecture decision needed before implementing any merge UI.

---

## Minor Pitfalls

### Pitfall 16: Excel Library Mismatch (xlsxwriter vs openpyxl)

**What goes wrong:** Using `openpyxl` for writing (it's slower and produces larger files) or `xlsxwriter` for reading (it can't read at all). This is a project-wide rule but easy to violate when adding export features.

**Prevention:** Cross-project rule: `xlsxwriter` for writing, `openpyxl` only for reading. Add to linter/review checklist.

**Phase:** Translator Merge phase (TMERGE-06). Export to Excel.

---

### Pitfall 17: Missing `from __future__ import annotations` in New Files

**What goes wrong:** Python 3.9 compatibility breaks when using `list[str]` or `dict[str, Any]` type hints without the future import. Works fine in Python 3.10+ (developer's machine) but fails in CI or on user machines with 3.9.

**Prevention:** Add `from __future__ import annotations` as the first import in EVERY new Python file. Enforce via pre-commit hook or CI check.

**Phase:** All phases. Every new file.

---

### Pitfall 18: StringIdConsumer Not Fresh Per Language

**What goes wrong:** QACompiler's `StringIdConsumer` tracks seen StringIDs for deduplication. If the same consumer instance is reused across languages, it incorrectly deduplicates strings that should exist in each language independently.

**Prevention:** Create a fresh `StringIdConsumer` per language, matching QACompiler's pattern (XML-07). Port the pattern exactly, don't "optimize" by sharing consumers.

**Phase:** XML Parsing phase (XML-07). Affects correctness of language table extraction.

---

### Pitfall 19: FAISS Index Stale After Merge

**What goes wrong:** After a merge operation changes hundreds of rows, the FAISS vector index still contains embeddings for the old text. Semantic search returns stale results. TM match percentages are wrong because they're computed against pre-merge embeddings.

**Prevention:** Trigger FAISS re-indexing after merge completion. Use incremental update (remove old vectors, add new ones) rather than full rebuild. Queue re-indexing as a background task — don't block the merge response.

**Phase:** Translator Merge phase. Must be coordinated with existing FAISS infrastructure.

---

### Pitfall 20: Svelte 5 Runes Misuse in New Components

**What goes wrong:** Developers familiar with Svelte 4 use `export let` instead of `$state`, `$:` instead of `$derived`, or forget `(item.id)` keys in `{#each}` blocks. Components appear to work but have subtle reactivity bugs: updates don't propagate, lists re-render entirely instead of diffing, or stale closures capture old values.

**Prevention:** Every new Svelte component must use Runes exclusively. Review checklist: no `export let`, no `$:`, every `{#each}` has a key. Use `$state` for mutable state, `$derived` for computed values, `$effect` for side effects.

**Phase:** All phases with UI work (Dual UI, Merge UI, AI Summaries UI).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dual UI Detection | File type detection regex too brittle | Use lxml tree inspection for `<LocStr>` nodes, not regex on raw text |
| Dual UI Detection | State leaks between modes (Pitfall 7) | Use `{#key fileType}` for full remount, or explicit state reset |
| XML Parsing | Malformed game files crash parser (Pitfall 2) | Port `sanitize_xml_content()` + lxml `recover=True` before ANY real file work |
| XML Parsing | Path templates hardcoded to Windows (Pitfall 12) | Build path translator utility first — every file operation depends on it |
| XML Parsing | Encoding misdetection (Pitfall 3) | Parse XML declaration first, use chardet as fallback |
| Image Pipeline | DDS formats not supported in WSL2 (Pitfall 5) | Remove platform guard, install pillow-dds unconditionally, test with real DDS |
| Audio Pipeline | vgmstream-cli missing in WSL2 (Pitfall 6) | Download Linux binary from GitHub releases, add to setup script |
| Translator Merge | br-tag corruption (Pitfall 1) | Port the three-layer defense from QuickTranslate — all three layers, not just one |
| Translator Merge | Wrong match priority order (Pitfall 4) | Strict > StringID-only > StrOrigin-only > Fuzzy, with dedup at each level |
| Translator Merge | "no translation" entries transferred | Port the skip guards from `xml_io.py` and `xml_transfer.py` |
| Translator Merge | Optimistic UI on batch ops (Pitfall 15) | Use transactional commit, not optimistic pattern, for merge operations |
| Game Dev Merge | Position-based merge loses attribute order (Pitfall 8) | Use lxml (preserves attribute order), not stdlib ET |
| Game Dev Merge | Postprocess corrupts non-text attributes (Pitfall 13) | Separate text-content postprocess from structural attribute preservation |
| AI Summaries | Ollama unavailable at demo time (Pitfall 9) | Health check + cache + graceful fallback badge — test the failure path |
| AI Summaries | Prompt produces inconsistent JSON (Pitfall 10) | Use `format: "json"`, short prompts, robust extraction with fallback |
| AI Summaries | Concurrent requests overwhelm GPU | Rate limit to 1 concurrent, queue with dedup, cancel on row change |
| CLI/Testing | Mock paths don't match real data structure | Integration tests with real XML fixtures (anonymized if needed) |
| Bug Fixes | Offline TM visibility fix breaks online TMs | Test both modes after every TM change — use existing repository pattern |

---

## Integration-Specific Warnings (Scaffold-to-Real Transition)

These pitfalls are specific to the v1.0 -> v2.0 transition where mock fixtures are replaced with real data.

### Data Shape Mismatch

v1.0 rows have `string_id`, `source`, `target`, `extra_data`. Real XML LocStr elements have 10+ attributes (`StringId`, `StrOrigin`, `Str`, `Desc`, `DescOrigin`, `KR`, `JP`, `EN`, etc.). The `extra_data` JSON blob must carry all non-core attributes faithfully. If `extra_data` serialization drops attributes, XML reconstruction loses data.

**Prevention:** Test round-trip: parse real XML -> store in DB -> reconstruct XML -> diff with original. Zero-diff is the goal.

### Test Fixture Drift

v1.0 tests use mock data that doesn't match real XML structure. As real parsing is wired in, tests pass with mocks but fail with real data. Dual test strategy needed: unit tests with controlled fixtures (fast, deterministic) AND integration tests with real XML samples (slow, but catches real-world issues).

### API Contract Changes

Adding dual UI mode, new column configs, and merge endpoints changes the API surface. The Svelte frontend depends on exact API response shapes. If backend adds new fields or changes field names without updating the frontend types, the UI silently drops data or crashes.

**Prevention:** Define TypeScript interfaces that match Python response models. Generate them from OpenAPI schema if possible. Add API contract tests.

---

## Sources

- QuickTranslate `LINEBREAK_SAFEGUARDS.md` — three-layer br-tag defense (HIGH confidence, project source of truth)
- QuickTranslate `postprocess.py` — 7-step postprocess pipeline (HIGH confidence, production code)
- QuickTranslate `xml_transfer.py` — merge match types and linebreak conversion (HIGH confidence, production code)
- QuickTranslate `xml_io.py` — correction parsing with skip guards (HIGH confidence, production code)
- MapDataGenerator `dds_handler.py` — DDS conversion with platform check (HIGH confidence, production code)
- MapDataGenerator `audio_handler.py` — WEM conversion via vgmstream-cli (HIGH confidence, production code)
- LocaNext `xml_handler.py` — current parser using stdlib ET (HIGH confidence, codebase inspection)
- LocaNext `mapdata_service.py` — Windows path templates (HIGH confidence, codebase inspection)
- LocaNext `ARCHITECTURE_SUMMARY.md` — repository pattern, offline/online modes (HIGH confidence, project docs)
- Project MEMORY.md — cross-project rules, Korean regex, Excel libs (HIGH confidence, enforced rules)

---

*Researched: 2026-03-15 for v2.0 milestone planning*
*Last updated: 2026-03-15*
