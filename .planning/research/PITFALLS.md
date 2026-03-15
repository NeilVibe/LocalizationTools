# Domain Pitfalls

**Domain:** Game Dev Platform + AI Intelligence for localization tool
**Researched:** 2026-03-15
**Milestone:** v3.0

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Mock Data XML Incompatible with XMLParsingEngine
**What goes wrong:** Mock data generator produces XML that looks correct but fails parsing by XMLParsingEngine due to subtle format differences (attribute order, encoding declarations, namespace handling, `<br/>` tag format).
**Why it happens:** QACompiler generators write Excel output, not XML. The mock generator must produce XML that matches what the *game* outputs, not what QACompiler reads. The XML format comes from the game engine, and XMLParsingEngine was built to parse that specific format.
**Consequences:** Every UI feature built on mock data silently shows wrong/empty data. Discovered late.
**Prevention:** Write a round-trip integration test FIRST: generate XML -> parse with XMLParsingEngine -> assert all fields extracted correctly. Run this test before any UI work begins.
**Detection:** Empty grids, missing attributes, parsing errors in loguru output.

### Pitfall 2: d3-zoom Fighting Svelte Reactivity
**What goes wrong:** Using d3's DOM manipulation (`.append()`, `.attr()`) to create SVG elements instead of letting Svelte render them. Results in elements that don't update when state changes, memory leaks from orphaned DOM nodes.
**Why it happens:** Most d3 tutorials show d3 managing the DOM. In Svelte, d3 should only provide the math (transforms, scales, forces).
**Consequences:** Map stops updating when data changes. Duplicate nodes. Memory leaks in Electron.
**Prevention:** Strict rule: d3-zoom provides the `transform` object via callback. Svelte applies it via `transform={transform}` attribute. d3 never calls `.append()` or `.attr()` on SVG elements.
**Detection:** Console warnings about duplicate elements. Map not reflecting state changes.

### Pitfall 3: AI Suggestions Without Rate Limiting
**What goes wrong:** Every string selection triggers an Ollama call. At 117 tok/s, Qwen3 takes 2-5 seconds per suggestion. Rapid navigation queues dozens of requests, freezing the UI.
**Why it happens:** Optimistic UI pattern (instant response) conflicts with slow LLM inference.
**Consequences:** UI freezes. Ollama queue backs up. GPU memory pressure.
**Prevention:** Debounce suggestion requests (500ms). Cancel in-flight requests when user navigates away. Show "loading" indicator. Cache results per source text. Limit concurrent Ollama requests to 1.
**Detection:** UI lag when navigating quickly. High GPU utilization from queued requests.

## Moderate Pitfalls

### Pitfall 4: WorldPosition Coordinate Scale Mismatch
**What goes wrong:** Region XML `WorldPosition` values are in game engine units (could be anything: meters, arbitrary scale). Mapping directly to SVG viewport without normalization produces maps where all nodes cluster in one corner or overlap.
**Prevention:** Analyze actual WorldPosition values from sample data. Normalize to SVG viewport using min/max scaling. Add padding. Test with edge cases (negative coordinates, extreme ranges).

### Pitfall 5: Category Clustering False Positives
**What goes wrong:** LanguageDataExporter's keyword-based clustering misclassifies files when folder structure differs from expected patterns. A file in an unexpected path gets "Uncategorized".
**Prevention:** Port the `TwoTierCategoryMapper` with its fallback chain intact. Add a "manual override" mechanism for misclassified entries. Test with mock data that includes edge-case folder names.

### Pitfall 6: QA Pipeline Performance on Large Files
**What goes wrong:** Building Aho-Corasick automaton on every file open. For a glossary with 5000+ terms, automaton build takes noticeable time.
**Prevention:** Cache the automaton per glossary version. Rebuild only when glossary changes. The automaton is the expensive step; scanning is O(text_length) and fast.

### Pitfall 7: Piper-TTS in PyInstaller Build
**What goes wrong:** piper-tts uses ONNX Runtime which has complex native dependencies. PyInstaller may miss shared libraries or voice model files.
**Prevention:** Make piper-tts entirely optional. Placeholder audio MVP = silence WAV generated with Python's `wave` module (zero dependencies). Add piper-tts as an enhancement after build pipeline is validated.

### Pitfall 8: Game Dev CRUD XML Write-Back Corruption
**What goes wrong:** Writing modified XML back to disk changes formatting, attribute order, or encoding in ways that break other tools reading the same file.
**Prevention:** For v3.0 MVP, consider read + edit-in-memory only (no disk write-back). If write-back is needed, use lxml's `etree.tostring()` with `xml_declaration=True, encoding='utf-8'` and round-trip test against the original.

## Minor Pitfalls

### Pitfall 9: Codex Image Loading Waterfall
**What goes wrong:** Codex pages load entity images one-by-one, causing visible waterfall loading.
**Prevention:** Use intersection observer for lazy loading. Preload images for visible entities. Use placeholder colors while loading.

### Pitfall 10: Mock Data Inconsistent Cross-References
**What goes wrong:** Mock data has StringIDs referenced across files that do not match. Character in one file references a region that does not exist in region files.
**Prevention:** Generate mock data in dependency order: regions first, then characters (with valid region references), then items, then skills. Validate cross-references after generation.

### Pitfall 11: SVG Rendering Performance with Many Nodes
**What goes wrong:** World map with 200+ region nodes and connection lines renders slowly on zoom/pan.
**Prevention:** At 200 nodes this is unlikely. If it happens: simplify path rendering during zoom, use CSS `will-change: transform` on the map group, consider level-of-detail.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Mock Data Generator | XML format incompatibility (#1) | Round-trip integration test before ANY UI work |
| Mock Data Generator | Cross-reference inconsistency (#10) | Generate in dependency order, validate refs |
| Game Dev Grid | XML write-back corruption (#8) | Start read-only, add write carefully with tests |
| World Map | d3 DOM manipulation (#2) | d3 for math only, Svelte for DOM |
| World Map | Coordinate scale mismatch (#4) | Normalize WorldPosition to viewport |
| AI Suggestions | Rate limiting / UI freeze (#3) | Debounce, cancel, cache, max 1 concurrent |
| QA Pipeline | Automaton build perf (#6) | Cache per glossary version |
| Placeholder Audio | PyInstaller compatibility (#7) | Make piper-tts optional, silence WAV as fallback |
| Category Clustering | False positives (#5) | Port full fallback chain, add manual override |

## Sources

- v2.0 post-milestone review (11 issues found) -- learned to test round-trips
- QuickCheck source code -- Aho-Corasick performance characteristics
- d3-zoom documentation -- transform API design
- piper-tts GitHub issues -- PyInstaller compatibility reports
- QACompiler generators -- cross-reference patterns between XML files
