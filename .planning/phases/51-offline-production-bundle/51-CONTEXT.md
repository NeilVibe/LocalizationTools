# Phase 51: Offline Production Bundle - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a self-contained offline bundle: SQLite-only mode (no PostgreSQL), Model2Vec in light build (no Qwen), vgmstream-cli bundled for WEM→WAV, Factory/Repo pattern audit for offline correctness, fresh-machine smoke test. GameData/Codex/MegaIndex is already offline by design (file-based). This phase ensures LDM translation data works offline via SQLite and the packaging is correct.

</domain>

<decisions>
## Implementation Decisions

### SQLite-Only Mode
- Factory already detects offline mode via header/environment — verify it works
- All 9 SQLite repos must function without PostgreSQL available
- MegaIndex is file-based — already offline, no changes needed
- Settings persistence: verify settings.json works without DB

### Model2Vec Bundling
- Create tools/download_model2vec.py to pre-download model weights at build time
- Bundle potion-multilingual-128M (embeddings.safetensors + config.json + tokenizer.json) into resources/models/Model2Vec/
- Update electron-builder extraResources to include model directory
- is_light_mode() detection already works — verify

### vgmstream Bundling
- Copy vgmstream-cli.exe + 11 DLLs from MapDataGenerator/tools/ to resources/bin/vgmstream/
- Update electron-builder extraResources
- MediaConverter must find vgmstream in bundled location

### Factory/Repo Audit
- Verify all 9 repos: Project, Folder, File, Row, TM, QA, Trash, Platform, Capability
- Test offline header detection → SQLite path
- Test all CRUD operations in SQLite mode
- Verify no service assumes PostgreSQL is available

### Smoke Test
- Script that starts app in SQLite-only mode, verifies all pages load, performs basic operations
- NOT a full E2E test suite — just a sanity check for packaging

### Claude's Discretion
- Smoke test implementation details
- Exact electron-builder config changes
- Whether to add a "light build" CI variant

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/repositories/factory.py` — 3-mode detection (Offline/SQLite/PostgreSQL)
- `server/repositories/sqlite/` — all SQLite repo implementations
- `server/tools/shared/embedding_engine.py` — is_light_mode() detection
- `tools/install_deps.py --light` — existing light install script
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/tools/` — vgmstream-cli + DLLs

### Integration Points
- electron-builder config for extraResources
- PyInstaller spec file for bundling
- CI/CD build pipeline (if adding light build variant)

</code_context>

<specifics>
## Specific Ideas

- The offline bundle challenge is really: SQLite mode works for LDM + bundle Model2Vec weights + vgmstream binaries
- GameData/Codex/MegaIndex is inherently offline — no changes needed there

</specifics>

<deferred>
## Deferred Ideas

- Light build CI variant (can be done later)
- Automated fresh-machine test in CI

</deferred>
